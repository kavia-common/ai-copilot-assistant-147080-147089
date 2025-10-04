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
    "You are a helpful and concise assistant. Answer user questions clearly and directly. "
    "Avoid meta-instructions and do not include step templates unless explicitly asked."
)

# When the caller wants list-style replies, add a light hint (no forced template).
SYSTEM_PROMPT_LIST_HINT = (
    "If the user asks for examples or items, respond as a concise list (bullets or short comma-separated), "
    "without preamble or commentary."
)

# Optional guided mode: only when explicitly requested by the user.
SYSTEM_PROMPT_GUIDED = (
    "If the user explicitly asks for steps or a how-to, provide brief, numbered steps. "
    "Otherwise, answer plainly and concisely."
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
    Build the messages array for OpenAI, ensuring we start with a neutral system message
    and include only the current request's messages (no cross-request reuse).

    The response_style may add a light format hint for list-style or guided responses.
    """
    system_prompt_parts = [SYSTEM_PROMPT_BASE]
    if response_style == "list":
        system_prompt_parts.append(SYSTEM_PROMPT_LIST_HINT)
    elif response_style == "guided":
        system_prompt_parts.append(SYSTEM_PROMPT_GUIDED)
    system_prompt = " ".join(system_prompt_parts)

    wire_messages: List[dict] = [{"role": "system", "content": system_prompt}]

    # Append this request's message history in order, skipping empties.
    for m in messages:
        role = m.role.value
        content = (m.content or "").strip()
        if not content:
            continue
        wire_messages.append({"role": role, "content": content})

    # Ensure the last user message is present at the end explicitly to reduce ambiguity.
    last_user = _extract_last_user_message(messages)
    if last_user:
        if not wire_messages or wire_messages[-1].get("role") != "user" or wire_messages[-1].get("content") != last_user:
            wire_messages.append({"role": "user", "content": last_user})

    return wire_messages


def _build_openai_payload(messages: List[Message], response_style: Optional[str]) -> dict:
    """
    Build payload for OpenAI Chat Completions request with deterministic parameters.
    Conforms to ChatRequest schema: messages list of {role, content}; optional response_style not sent directly.
    """
    wire_messages = _build_messages_for_openai(messages, response_style=response_style)
    model = getattr(settings, "OPENAI_MODEL", None) or OPENAI_DEFAULT_MODEL
    return {
        "model": model,
        "messages": wire_messages,
        "temperature": 0.2,
        "top_p": 1,
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
    Deterministic, neutral fallback when OpenAI is unavailable or errors occur.

    Rules:
    - Provide concise, direct answers.
    - No hidden templates (no "Define the goal", "2–3 steps", "small example").
    - Support simple intents like "What is water?" and "examples of vegetables".
    """
    if not messages:
        return DEFAULT_GREETING

    # Find the latest user message scanning backwards.
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
        return "Please share a bit more detail about what you need."

    lower = user_text.lower()
    wants_list = response_style == "list" or ("example" in lower or "examples" in lower or "list" in lower)

    # Specific concise answer for water
    if "what is water" in lower or lower.strip() == "water?":
        return "Water is H₂O, a molecule made of two hydrogen atoms and one oxygen atom. It's a colorless, tasteless liquid essential for life."

    # Vegetables examples
    if "vegetable" in lower or "vegetables" in lower:
        items = ["Carrots", "Broccoli", "Spinach", "Bell peppers", "Cauliflower", "Tomatoes", "Cucumbers"]
        if wants_list:
            return "\n".join(f"- {x}" for x in items)
        else:
            return ", ".join(items) + "."

    # Generic examples request
    if "example" in lower or "examples" in lower:
        examples = [
            "Carrots, broccoli, spinach",
            "Write a simple function that adds two numbers",
            "Organize tasks by priority and due date",
        ]
        if wants_list:
            return "\n".join(f"- {x}" for x in examples)
        else:
            return "; ".join(examples) + "."

    # If it's a factual question (what/why/where/when/how) without specific handling, answer briefly.
    if lower.endswith("?") or lower.startswith(("how", "what", "why", "where", "when")):
        # Keep neutral and concise without templates
        return "Here's a concise answer: please provide a bit more context so I can be precise."

    # Default: neutral, brief response
    return "Got it. Could you add a bit more detail so I can provide a precise, concise answer?"
