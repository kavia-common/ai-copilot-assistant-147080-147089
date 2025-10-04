from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, constr


# PUBLIC_INTERFACE
class RoleEnum(str, Enum):
    """Enumeration of chat message roles."""
    user = "user"
    assistant = "assistant"
    system = "system"


# PUBLIC_INTERFACE
class Message(BaseModel):
    """Represents a single chat message with a role and content."""
    role: RoleEnum = Field(..., description="The role of the message sender: user, assistant, or system.")
    content: constr(min_length=1, max_length=5000) = Field(  # type: ignore[valid-type]
        ..., description="The textual content of the message (1-5000 characters)."
    )


# PUBLIC_INTERFACE
class ChatRequest(BaseModel):
    """Request model for generating an assistant reply from a list of prior messages."""
    messages: List[Message] = Field(..., description="Ordered list of chat messages forming the conversation.")
    stream: Optional[bool] = Field(
        default=False,
        description="Whether the response should be streamed. Placeholder, not implemented in this version."
    )


# PUBLIC_INTERFACE
class ChatResponse(BaseModel):
    """Response model containing the assistant's reply as plain text."""
    reply: str = Field(..., description="The assistant's reply.")
