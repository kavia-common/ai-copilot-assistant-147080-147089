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


def _openai_is_configured() -> bool:
    """
    Check whether OpenAI API is configured via environment.

    Uses settings to avoid exposing any secret to clients.
    """
    # We don't store secrets here; just check presence.
    return bool(getattr(settings, "OPENAI_API_KEY", None))


def _build_openai_payload(messages: List[Message]) -> dict:
    """
    Build payload for OpenAI Chat Completions request based on incoming messages.
    """
    # Convert our Message models to the wire format expected by OpenAI
    wire_messages = [{"role": m.role.value, "content": m.content} for m in messages]

    model = getattr(settings, "OPENAI_MODEL", None) or OPENAI_DEFAULT_MODEL
    return {
        "model": model,
        "messages": wire_messages,
        "temperature": 0.7,
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
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(OPENAI_CHAT_URL, headers=headers, json=payload)
            if resp.status_code != 200:
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


# PUBLIC_INTERFACE
def generate_reply(messages: List[Message]) -> str:
    """
    Generate a concise, friendly assistant reply based on the most recent user message.

    Behavior:
    - If OpenAI is configured via OPENAI_API_KEY (and optionally OPENAI_MODEL), call the
      Chat Completions API non-streaming and return its reply.
    - On any error or if OpenAI is not configured, fall back to the deterministic reply.

    Parameters
    ----------
    messages : List[Message]
        The conversation history in chronological order.

    Returns
    -------
    str
        A short assistant reply suitable for immediate display in chat.
    """
    # Attempt OpenAI path first if configured
    ai_reply = _call_openai(messages)
    if isinstance(ai_reply, str) and ai_reply.strip():
        return ai_reply

    # Fallback to deterministic logic below
    if not messages:
        return DEFAULT_GREETING

    # Find the latest user message scanning backwards for robustness
    latest_user: Optional[Message] = None
    for msg in reversed(messages):
        if msg.role == RoleEnum.user:
            latest_user = msg
            break

    if latest_user is None:
        return DEFAULT_GREETING

    # Safety: truncate overly long content to avoid excessive processing or echo
    user_text = (latest_user.content or "").strip()
    if len(user_text) > MAX_INPUT_CHARS:
        user_text = user_text[:MAX_INPUT_CHARS].rstrip() + "..."

    if not user_text:
        return "I’m here to help. Could you share a bit more detail about what you need?"

    # Simple deterministic, friendly response template
    # Keep it concise and helpful without external AI calls
    # Add minimal task-like guidance if the user phrased a question
    lower = user_text.lower()
    if lower.endswith("?") or lower.startswith(("how", "what", "why", "where", "when", "help", "can you", "could you")):
        return (
            f"Great question! In short: {summarize_prompt(user_text)} "
            f"If you can provide any constraints or examples, I can tailor the next steps."
        )

    # Provide a brief acknowledgement for statements/requests
    return (
        f"Thanks for the context. Here's a concise next step: {summarize_prompt(user_text)} "
        f"Let me know if you'd like a deeper breakdown or a quick checklist."
    )


def summarize_prompt(prompt: str) -> str:
    """
    Produce a minimal, deterministic 'summary-like' hint based on the user's prompt.

    This is not a true summarization—just a placeholder to keep the assistant reply
    feeling contextual and helpful without external dependencies.
    """
    # Keep to a short, safe slice of the prompt
    snippet = " ".join(prompt.split())  # collapse whitespace
    if len(snippet) > 160:
        snippet = snippet[:157].rstrip() + "..."

    # Heuristic: reflect a concise actionable takeaway
    # Aim to sound helpful but not fabricate details.
    return f"focus on: \"{snippet}\""
