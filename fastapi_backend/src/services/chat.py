from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import List, Optional

import httpx
from src.api.schemas import Message, RoleEnum
from src.config import settings

# Module-level logger
logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 5000
DEFAULT_GREETING = (
    "Hi! I'm your helpful AI Copilot. Ask me anything, and I'll provide a concise, friendly answer."
)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"

# Default, neutral, concise assistant prompt (kept short)
SYSTEM_PROMPT_BASE = (
    "You are a concise, helpful assistant. Answer clearly and directly."
)

# Light hints only when requested
SYSTEM_PROMPT_LIST_HINT = (
    "If the user wants examples or items, use a short list without preamble."
)
SYSTEM_PROMPT_GUIDED = (
    "If the user asks for steps/how-to, provide brief, numbered steps; otherwise answer plainly."
)

# Safety truncation limits for responses (final safeguard)
MAX_RESPONSE_CHARS = 4000

# Async call timeout in seconds (conservative)
OPENAI_CALL_TIMEOUT_S = 20.0


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
    Build a minimal messages array for OpenAI.

    Keep prompts short: system + minimal recent context and ensure the latest user
    message is present last.
    """
    system_prompt_parts = [SYSTEM_PROMPT_BASE]
    if response_style == "list":
        system_prompt_parts.append(SYSTEM_PROMPT_LIST_HINT)
    elif response_style == "guided":
        system_prompt_parts.append(SYSTEM_PROMPT_GUIDED)
    system_prompt = " ".join(system_prompt_parts)

    wire_messages: List[dict] = [{"role": "system", "content": system_prompt}]

    # Include up to the last 2-3 messages to keep context tiny (non-blocking size).
    # Always skip empty content.
    recent: List[Message] = []
    for m in reversed(messages):
        if (m.content or "").strip():
            recent.append(m)
        if len(recent) >= 3:
            break
    for m in reversed(recent):
        wire_messages.append({"role": m.role.value, "content": (m.content or "").strip()})

    # Ensure the final user message is last
    last_user = _extract_last_user_message(messages)
    if last_user:
        if not wire_messages or wire_messages[-1].get("role") != "user" or wire_messages[-1].get("content") != last_user:
            wire_messages.append({"role": "user", "content": last_user})

    return wire_messages


def _build_openai_payload(messages: List[Message], response_style: Optional[str]) -> dict:
    """
    Build payload for OpenAI Chat Completions request with deterministic parameters.
    """
    wire_messages = _build_messages_for_openai(messages, response_style=response_style)
    model = getattr(settings, "OPENAI_MODEL", None) or OPENAI_DEFAULT_MODEL
    return {
        "model": model,
        "messages": wire_messages,
        "temperature": 0.2,  # deterministic-ish
        "top_p": 1,
        "max_tokens": 400,
    }


async def _call_openai_async(messages: List[Message], response_style: Optional[str]) -> Optional[str]:
    """
    Async call to OpenAI Chat Completions API with an asyncio timeout.
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

    async def _do_request() -> Optional[str]:
        # Use async client to avoid blocking the event loop
        async with httpx.AsyncClient(timeout=OPENAI_CALL_TIMEOUT_S) as client:
            resp = await client.post(OPENAI_CHAT_URL, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.warning("OpenAI non-200: %s body=%s", resp.status_code, resp.text[:500])
                return None
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            message = choices[0].get("message") or {}
            content = message.get("content")
            if not isinstance(content, str) or not content.strip():
                return None
            content = content.strip()
            if len(content) > MAX_RESPONSE_CHARS:
                content = content[:MAX_RESPONSE_CHARS].rstrip()
            return content

    start = perf_counter()
    try:
        # Wrap in asyncio.wait_for for an extra guardrail
        result = await asyncio.wait_for(_do_request(), timeout=OPENAI_CALL_TIMEOUT_S)
        elapsed_ms = int((perf_counter() - start) * 1000)
        logger.info("OpenAI call completed in %d ms", elapsed_ms)
        return result
    except asyncio.TimeoutError:
        elapsed_ms = int((perf_counter() - start) * 1000)
        logger.warning("OpenAI call timed out after %d ms", elapsed_ms)
        # Friendly fallback handled by caller via None -> fallback message.
        return None
    except httpx.HTTPError as e:
        elapsed_ms = int((perf_counter() - start) * 1000)
        logger.exception("OpenAI HTTP error after %d ms: %s", elapsed_ms, str(e))
        return None
    except Exception as e:
        elapsed_ms = int((perf_counter() - start) * 1000)
        logger.exception("OpenAI unexpected error after %d ms: %s", elapsed_ms, str(e))
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


# PUBLIC_INTERFACE
async def generate_reply(messages: List[Message], response_style: Optional[str] = None) -> str:
    """
    Generate a reply for the assistant.

    This function is fully async and non-blocking. It uses an asyncio timeout around
    the OpenAI request, adds lightweight timing logs, and returns a friendly fallback
    if OpenAI is unavailable or times out.
    """
    # Attempt OpenAI path if configured
    reply: Optional[str] = None
    if _openai_is_configured():
        reply = await _call_openai_async(messages, response_style=response_style)

        # If timeout or error happened, provide a friendly immediate fallback message
        if reply is None:
            # Friendly timeout/error fallback
            return "AI took too long to respond. Please try again."

    # If not configured or reply still None, use deterministic fallback
    if not reply:
        return _deterministic_fallback_reply(messages, response_style=response_style)

    return reply
