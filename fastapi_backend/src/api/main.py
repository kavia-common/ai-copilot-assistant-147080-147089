from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import ChatRequest, ChatResponse
from src.config import settings
from src.services.chat import generate_reply

# Initialize FastAPI app with basic metadata (can be expanded later)
app = FastAPI(
    title="AI Copilot Backend",
    description="Backend API for the AI Copilot application",
    version="0.1.0",
)

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
def chat(request: ChatRequest) -> ChatResponse:
    """
    Generate a reply from the assistant based on prior messages.

    Parameters
    ----------
    request : ChatRequest
        The chat request payload including an ordered list of messages.

    Returns
    -------
    ChatResponse
        JSON containing the assistant's reply text under the 'reply' field.
    """
    reply_text = generate_reply(request.messages)
    return ChatResponse(reply=reply_text)
