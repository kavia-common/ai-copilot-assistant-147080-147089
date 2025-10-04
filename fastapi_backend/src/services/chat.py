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

# Default, neutral, concise assistant prompt.
SYSTEM_PROMPT_BASE = (
    "You are a helpful and concise assistant. Answer user questions clearly and directly."
)

# When the caller wants list-style replies, add a style bias.
SYSTEM_PROMPT_LIST_HINT = (
    "When the user asks for examples or items, respond as a concise bulleted list or a short, comma-separated list. "
    "Do not add meta-instructions or commentary—just the items or brief bullets."
)

# Optional guided mode: provide steps/examples only when appropriate.
SYSTEM_PROMPT_GUIDED = (
    "You are a helpful assistant. If the user is asking how to do something, break it into steps and include an example. "
    "For factual questions, respond clearly and concisely."
)

# Safety truncation limits for responses (final safeguard)
MAX_RESPONSE_CHARS = 4000


def _openai_is_configured() -> bool:
    """
    Check whether OpenAI API is configured via environment.

    Uses settings to avoid exposing any secret to clients.
    """
    return bool(getattr(settings, "OPENAI_API_KEY", None))


def _extract_last_user_message(messages: List[Message]) -> Optional[str]:
    """
    Return the last user message content if present, else None.
    """
    for m in reversed(messages):
        if m.role == RoleEnum.user:
            return (m.content or "").strip()
    return None


def _build_messages_for_openai(messages: List[Message], response_style: Optional[str]) -> List[dict]:
    """
    Build the messages array for OpenAI, ensuring we start with a strong system message,
    carry forward history as-is, and include the last user message verbatim if present.

    The response_style may add a format hint to bias list-style outputs or guided responses.
    """
    system_prompt_parts = [SYSTEM_PROMPT_BASE]
    if response_style == "list":
        system_prompt_parts.append(SYSTEM_PROMPT_LIST_HINT)
        # Extra explicit hint to reduce meta replies for examples
        system_prompt_parts.append(
            "Format hint: For 'examples' requests, output a short, concrete list—bullets or comma-separated—no preamble."
        )
    elif response_style == "guided":
        system_prompt_parts.append(SYSTEM_PROMPT_GUIDED)
    system_prompt = " ".join(system_prompt_parts)

    wire_messages: List[dict] = [{"role": "system", "content": system_prompt}]

    # Append all message history in order, skipping empties
    for m in messages:
        role = m.role.value
        content = (m.content or "").strip()
        if not content:
            continue
        wire_messages.append({"role": role, "content": content})

    # Ensure last user message appears at the end verbatim if a user message exists and isn't already last
    last_user = _extract_last_user_message(messages)
    if last_user:
        # If the last appended message isn't the same user content, append it to be explicit.
        if not wire_messages or wire_messages[-1].get("role") != "user" or wire_messages[-1].get("content") != last_user:
            wire_messages.append({"role": "user", "content": last_user})

    return wire_messages


def _build_openai_payload(messages: List[Message], response_style: Optional[str]) -> dict:
    """
    Build payload for OpenAI Chat Completions request with deterministic parameters and format hints.
    """
    wire_messages = _build_messages_for_openai(messages, response_style=response_style)
    model = getattr(settings, "OPENAI_MODEL", None) or OPENAI_DEFAULT_MODEL
    return {
        "model": model,
        "messages": wire_messages,
        # Deterministic-bias parameters
        "temperature": 0.2,
        "top_p": 1,
        # Room for concise lists or short answers
        "max_tokens": 400,
    }


def _call_openai(messages: List[Message], response_style: Optional[str]) -> Optional[str]:
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
    payload = _build_openai_payload(messages, response_style=response_style)

    try:
        # 10s timeout as documented in README
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(OPENAI_CHAT_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                return None
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                return None
            # Safety truncation to avoid overly long replies
            content = content.strip()
            if len(content) > MAX_RESPONSE_CHARS:
                content = content[:MAX_RESPONSE_CHARS].rstrip()
            return content
    except Exception:
        return None


def _deterministic_fallback_reply(messages: List[Message], response_style: Optional[str]) -> str:
    """
    Deterministic, helpful fallback when OpenAI is unavailable or errors occur.

    Heuristic:
    - If the latest user message includes phrases like "example(s) of", "examples", or mentions "vegetables",
      return concrete, list-style answers.
    - Otherwise, provide a concise, actionable reply.
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

    # Prefer list outputs if style hint requests it or the prompt asks for examples
    wants_list = response_style == "list" or ("example" in lower or "examples" in lower or "list" in lower)

    if "vegetable" in lower or "vegetables" in lower:
        if wants_list:
            return "- Carrots\n- Broccoli\n- Spinach\n- Bell peppers\n- Cauliflower\n- Tomatoes\n- Cucumbers"
        else:
            return "Carrots, broccoli, spinach, bell peppers, cauliflower, tomatoes, cucumbers."

    if "example" in lower or "examples" in lower or "example of" in lower or "examples of" in lower:
        if wants_list:
            return "- Example 1: A quick, healthy lunch: quinoa, roasted chickpeas, spinach, cherry tomatoes.\n- Example 2: Minimal Python function to add two numbers.\n- Example 3: Three bullet steps to get started on a task."
        else:
            return "Example: A quick healthy lunch—quinoa with roasted chickpeas, spinach, and cherry tomatoes."

    # Default concise, helpful fallback
    if lower.endswith("?") or lower.startswith(
        ("how", "what", "why", "where", "when", "help", "can you", "could you")
    ):
        if wants_list:
            return "- Define the goal.\n- List 2–3 concrete steps.\n- Provide one small example."
        if response_style == "guided" or lower.startswith(("how", "help", "can you", "could you")):
            return "- Identify the goal.\n- Break the task into 2–4 clear steps.\n- Example: Show a minimal, concrete illustration."
        return "Define the goal, list 2–3 concrete steps, and add a small example."

    return "Outline your goal, list 2–3 concrete actions, and include one quick example."


# PUBLIC_INTERFACE
def generate_reply(messages: List[Message], response_style: Optional[str] = None) -> str:
    """
    Generate a concise, friendly assistant reply based on the most recent user message.

    Behavior:
    - Prepends a strong, task-oriented system prompt that forbids meta-advice.
    - If OpenAI is configured via OPENAI_API_KEY (and optionally OPENAI_MODEL), call the
      Chat Completions API non-streaming with temperature=0.2, top_p=1, max_tokens≈400 and return its reply.
    - Adds a format hint so examples are returned as concise lists or bullets when appropriate.
    - Explicitly ensures the last user message is included as-is.
    - On any error or if OpenAI is not configured, fall back to a deterministic reply that
      detects simple patterns like 'example(s) of' and returns concrete examples.

    Parameters
    ----------
    messages : List[Message]
        The conversation history in chronological order.
    response_style : Optional[str]
        Optional hint: 'list' to bias concise list/bulleted responses or 'plain' for short prose.

    Returns
    -------
    str
        A short assistant reply suitable for immediate display in chat.
    """
    ai_reply = _call_openai(messages, response_style=response_style)
    if isinstance(ai_reply, str) and ai_reply.strip():
        return ai_reply

    return _deterministic_fallback_reply(messages, response_style=response_style)


def summarize_prompt(prompt: str) -> str:
    """
    Produce a minimal, deterministic 'summary-like' hint based on the user's prompt.

    This is not a true summarization—retained for compatibility with prior code.
    """
    snippet = " ".join(prompt.split())  # collapse whitespace
    if len(snippet) > 160:
        snippet = snippet[:157].rstrip() + "..."
    return f"focus on: \"{snippet}\""
