import asyncio
import logging
from time import perf_counter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.logging_config import configure_logging

from src.api.schemas import ChatRequest, ChatResponse
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
    description="Accepts a list of chat messages and returns a concise assistant reply.",
    tags=["Chat"],
)
async def chat(request: ChatRequest):
    """
    Generate a reply from the assistant based on prior messages.

    Parameters
    ----------
    request : ChatRequest
        The chat request payload including an ordered list of messages.

    Returns
    -------
    ChatResponse | JSONResponse
        JSON containing the assistant's reply text under the 'reply' field, or a structured error with cause.
    """
    total_start = perf_counter()
    try:
        # Route-level time budget: 13s. We always complete or fail fast within SLA.
        reply_text = await asyncio.wait_for(
            generate_reply(request.messages, response_style=request.response_style),
            timeout=13.0,
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
