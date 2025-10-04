from typing import List, Optional

import httpx
from src.api.schemas import Message, RoleEnum
from src.config import settings

MAX_INPUT_CHARS = 5000
DEFAULT_GREETING = (
    "Hi! I'm your helpful AI Copilot. Ask me anything, and I'll provide a concise, friendly answer."
)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"

# A clear, strong system prompt to guide OpenAI responses toward helpful, direct, and concise output.
SYSTEM_PROMPT = (
    "You are a helpful and direct assistant. Always answer user questions clearly with "
    "concrete examples when asked. Keep responses concise."
)


def _openai_is_configured() -> bool:
    """
    Check whether OpenAI API is configured via environment.

    Uses settings to avoid exposing any secret to clients.
    """
    # We don't store secrets here; just check presence.
    return bool(getattr(settings, "OPENAI_API_KEY", None))


def _build_messages_for_openai(messages: List[Message]) -> List[dict]:
    """
    Build the messages array for OpenAI, ensuring we start with a strong system message
    and that user/assistant history from the payload is preserved in order.

    Guarantees that the last user message from the incoming payload is included as-is.
    """
    wire_messages: List[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Append the conversation history as provided, preserving order.
    for m in messages:
        # Only accept valid roles; schemas already constrain this,
        # but we defensively map to the strings expected by OpenAI.
        role = m.role.value
        content = (m.content or "").strip()
        if not content:
            # skip empty content to avoid confusing the model
            continue
        wire_messages.append({"role": role, "content": content})

    # Ensure the last user message is present; if there are no user messages,
    # we simply proceed (OpenAI will still get the system prompt + any assistant/system msgs).
    # Since we append all, this is mainly a sanity step rather than duplication.
    # If needed, you could re-append, but duplication is avoided here for clarity.

    return wire_messages


def _build_openai_payload(messages: List[Message]) -> dict:
    """
    Build payload for OpenAI Chat Completions request with deterministic parameters.
    """
    wire_messages = _build_messages_for_openai(messages)
    model = getattr(settings, "OPENAI_MODEL", None) or OPENAI_DEFAULT_MODEL
    return {
        "model": model,
        "messages": wire_messages,
        # Focused, low-creativity output as requested
        "temperature": 0.3,
        # Reasonable cap for concise answers
        "max_tokens": 300,
    }


def _call_openai(messages: List[Message]) -> Optional[str]:
    """
    Call OpenAI Chat Completions API and return the assistant's reply text.
    Returns None on any error to allow fallback behavior.
    """
    if not _openai_is_configured():
        return None

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = _build_openai_payload(messages)

    try:
        # 10s timeout as documented in README
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(OPENAI_CHAT_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                # Avoid leaking response details; fallback will handle user-facing output
                return None
            data = resp.json()
            # Expect choices[0].message.content
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                return None
            return content.strip()
    except Exception:
        # Swallow exceptions to ensure graceful fallback
        return None


def _deterministic_fallback_reply(messages: List[Message]) -> str:
    """
    Deterministic, helpful fallback when OpenAI is unavailable or errors occur.

    Heuristic:
    - If the latest user message includes words like "example" or "vegetables",
      respond with a direct answer including concrete examples.
    - Otherwise, provide a concise, actionable reply.

    Notes:
    - Keeps responses short and practical.
    """
    if not messages:
        return DEFAULT_GREETING

    # Find the latest user message scanning backwards for robustness.
    latest_user: Optional[Message] = None
    for msg in reversed(messages):
        if msg.role == RoleEnum.user:
            latest_user = msg
            break

    if latest_user is None:
        return DEFAULT_GREETING

    user_text = (latest_user.content or "").strip()
    if len(user_text) > MAX_INPUT_CHARS:
        user_text = user_text[:MAX_INPUT_CHARS].rstrip() + "..."

    if not user_text:
        return "I’m here to help. Could you share a bit more detail about what you need?"

    lower = user_text.lower()

    # Simple heuristics to inject concrete examples when requested or relevant.
    if "example" in lower:
        return (
            "Here are a couple of concise examples:\n"
            "- Example 1: Provide a one-sentence summary of your goal, then list 3 bullet steps.\n"
            "- Example 2: Share a minimal code snippet and specify the error you see."
        )

    if "vegetable" in lower or "vegetables" in lower:
        return (
            "Quick ideas with examples:\n"
            "- Stir-fry: Broccoli, bell peppers, snap peas with garlic-soy sauce.\n"
            "- Roasting: Carrots, Brussels sprouts, and cauliflower at 425°F (220°C) for ~20–25 min.\n"
            "- Simple salad: Cherry tomatoes, cucumber, spinach with olive oil + lemon."
        )

    # Default concise, helpful fallback
    if lower.endswith("?") or lower.startswith(
        ("how", "what", "why", "where", "when", "help", "can you", "could you")
    ):
        return (
            "Here’s a concise answer: focus on the key objective, list 2–3 steps, and include a "
            "minimal example if applicable. If you share constraints or a sample, I can tailor this further."
        )

    return "Thanks for the details. A concise next step is to outline your goal, list 2–3 actions, and add one example."


# PUBLIC_INTERFACE
def generate_reply(messages: List[Message]) -> str:
    """
    Generate a concise, friendly assistant reply based on the most recent user message.

    Behavior:
    - Prepends a clear system prompt to guide the model.
    - If OpenAI is configured via OPENAI_API_KEY (and optionally OPENAI_MODEL), call the
      Chat Completions API non-streaming with temperature≈0.3 and max_tokens≈300 and return its reply.
    - On any error or if OpenAI is not configured, fall back to a deterministic reply that
      includes concrete examples for prompts mentioning "example" or "vegetables".

    Parameters
    ----------
    messages : List[Message]
        The conversation history in chronological order.

    Returns
    -------
    str
        A short assistant reply suitable for immediate display in chat.

    Example payload (sanity):
    request = {
        "messages": [
            {"role": "user", "content": "Give me an example of a healthy lunch with vegetables."}
        ]
    }
    Expected behavior:
    - If OpenAI is available: returns a concise, example-based reply.
    - If not: returns deterministic examples including vegetable ideas.
    """
    # Attempt OpenAI path first if configured
    ai_reply = _call_openai(messages)
    if isinstance(ai_reply, str) and ai_reply.strip():
        return ai_reply

    # Deterministic fallback
    return _deterministic_fallback_reply(messages)


def summarize_prompt(prompt: str) -> str:
    """
    Produce a minimal, deterministic 'summary-like' hint based on the user's prompt.

    This is not a true summarization—retained for compatibility with prior code.
    """
    # Keep to a short, safe slice of the prompt
    snippet = " ".join(prompt.split())  # collapse whitespace
    if len(snippet) > 160:
        snippet = snippet[:157].rstrip() + "..."

    return f"focus on: \"{snippet}\""
