import asyncio
import logging
from time import perf_counter
from typing import Any, Dict

from fastapi import FastAPI, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.logging_config import configure_logging

from src.api.schemas import ChatRequest, ChatResponse, normalize_to_chat_request
from src.config import settings
from src.services.chat import generate_reply

# Initialize logging first so any early logs are captured
configure_logging()

# Initialize FastAPI app with basic metadata (can be expanded later)
app = FastAPI(
    title="AI Copilot Backend",
    description="Backend API for the AI Copilot application",
    version="0.1.0",
)

logger = logging.getLogger(__name__)

# Configure CORS to allow the frontend origin
# FRONTEND_ORIGIN comes from centralized settings (env-backed).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", summary="Health Check", tags=["Health"])
def health_check():
    """
    Health check endpoint.

    Returns
    -------
    dict
        Simple JSON indicating the service is healthy.
    """
    return {"message": "Healthy"}

# PUBLIC_INTERFACE
@app.options(
    "/api/chat",
    summary="CORS preflight for chat",
    description="Handle CORS preflight checks for the chat endpoint.",
    tags=["Chat"],
)
def chat_preflight():
    """
    Handle CORS preflight request for /api/chat.
    Returns an empty 200 so browsers can proceed with the POST.
    """
    return {}

# PUBLIC_INTERFACE
@app.post(
    "/api/chat",
    response_model=ChatResponse,
    summary="Generate assistant reply",
    description="Accepts either a minimal {'message': string} or a full {'messages': [...], 'response_style'?} payload and returns a concise assistant reply.",
    tags=["Chat"],
)
async def chat(
    body: Dict[str, Any] = Body(
        ...,
        description="Minimal: {'message': '...'}; or Rich: {'messages': [{role,content}], 'response_style'?: 'plain'|'list'|'guided'}",
    )
):
    """
    Generate a reply from the assistant based on prior messages.

    Parameters
    ----------
    body : dict
        The raw chat request payload. Accepted shapes:
        - Minimal: {'message': '...'}
        - Rich: {'messages': [{role:'user'|'assistant'|'system', content:'...'}, ...], 'response_style'?: 'plain'|'list'|'guided'}

    Example payloads
    ----------------
    1) {'message':'What is water?'}
    2) {'messages':[{'role':'user','content':'Give me examples of vegetables'}], 'response_style':'list'}

    Returns
    -------
    ChatResponse | JSONResponse
        JSON containing the assistant's reply text under the 'reply' field, or a structured error with cause.
    """
    total_start = perf_counter()
    try:
        # Normalize incoming payload to ChatRequest model.
        try:
            normalized: ChatRequest = normalize_to_chat_request(body)
        except ValueError as ve:
            # Provide precise 400 with accepted shapes and validation details
            logger.debug("Invalid chat payload received: %s", body)
            detail = {
                "code": "invalid_payload",
                "message": "Invalid payload for /api/chat.",
                "accepted_shapes": [
                    {"messages": [{"role": "user|assistant|system", "content": "string"}], "response_style": "plain|list|guided (optional)"},
                    {"message": "string"},
                ],
                "hint": "Ensure 'content' is a non-empty string (1-5000 chars) and 'role' is one of user|assistant|system.",
                "validation": str(ve),
                "route": "/api/chat",
            }
            raise HTTPException(status_code=400, detail=detail) from ve

        # Route-level time budget: 13s. We always complete or fail fast within SLA.
        try:
            reply_text = await asyncio.wait_for(
                generate_reply(normalized.messages, response_style=normalized.response_style),
                timeout=13.0,
            )
        except Exception as upstream:
            # Treat unexpected upstream errors as Bad Gateway, not as 400.
            total_ms = int((perf_counter() - total_start) * 1000)
            logger.exception("Upstream chat service error after %d ms: %s", total_ms, str(upstream))
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "code": "bad_gateway",
                        "message": "Failed to obtain a reply from the AI service.",
                        "hint": "Please try again soon.",
                        "duration_ms": total_ms,
                        "route": "/api/chat",
                    }
                },
            )

        total_ms = int((perf_counter() - total_start) * 1000)
        logger.info("Route /api/chat total duration=%d ms", total_ms)
        return ChatResponse(reply=reply_text)
    except asyncio.TimeoutError:
        total_ms = int((perf_counter() - total_start) * 1000)
        logger.warning("Route /api/chat timed out after %d ms", total_ms)
        return JSONResponse(
            status_code=504,
            content={
                "error": {
                    "code": "gateway_timeout",
                    "message": "The assistant took too long to respond. Please try again.",
                    "hint": "This may be due to an upstream AI timeout.",
                    "duration_ms": total_ms,
                    "route": "/api/chat",
                }
            },
        )
    except HTTPException as he:
        # Already sanitized 400
        total_ms = int((perf_counter() - total_start) * 1000)
        logger.info("Route /api/chat returned %d after %d ms", he.status_code, total_ms)
        raise
    except Exception as e:
        total_ms = int((perf_counter() - total_start) * 1000)
        logger.exception("Route /api/chat failed after %d ms: %s", total_ms, str(e))
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Something went wrong while generating a reply.",
                    "hint": "Please try again.",
                    "duration_ms": total_ms,
                    "route": "/api/chat",
                }
            },
        )
