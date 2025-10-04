from typing import List, Optional

from src.api.schemas import Message, RoleEnum


MAX_INPUT_CHARS = 5000
DEFAULT_GREETING = (
    "Hi! I'm your helpful AI Copilot. Ask me anything, and I'll provide a concise, friendly answer."
)


# PUBLIC_INTERFACE
def generate_reply(messages: List[Message]) -> str:
    """
    Generate a concise, friendly assistant reply based on the most recent user message.

    This function is deterministic and does not call any external AI services.
    It applies simple heuristics:
      - If a latest user message exists, acknowledge it and provide a short, helpful response.
      - If no user message is found, return a default greeting.
      - Inputs are truncated to a safe limit.

    Parameters
    ----------
    messages : List[Message]
        The conversation history in chronological order.

    Returns
    -------
    str
        A short assistant reply suitable for immediate display in chat.
    """
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
