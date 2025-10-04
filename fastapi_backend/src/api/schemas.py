from enum import Enum
from typing import List, Optional, Literal, Any, Dict

from pydantic import BaseModel, Field, ValidationError, constr


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
    response_style: Optional[Literal['list', 'plain', 'guided']] = Field(
        default=None,
        description="Optional hint to bias the reply style. 'list' favors bullet/concise lists; 'plain' favors short prose; 'guided' breaks how-to into steps with an example when appropriate."
    )
    # Sanity note:
    # - The 'messages' list should be ordered oldest->newest, each item like:
    #   {\"role\":\"user|assistant|system\",\"content\":\"...\"}.


# PUBLIC_INTERFACE
class ChatResponse(BaseModel):
    """Response model containing the assistant's reply as plain text."""
    reply: str = Field(..., description="The assistant's reply.")


# PUBLIC_INTERFACE
class ChatRequestLegacy(BaseModel):
    """Compatibility request model for legacy payloads that send a single 'message' string."""
    message: constr(min_length=1, max_length=5000) = Field(  # type: ignore[valid-type]
        ..., description="Legacy single user message content."
    )


# PUBLIC_INTERFACE
def normalize_to_chat_request(data: Dict[str, Any]) -> ChatRequest:
    """Normalize incoming payload to ChatRequest.

    This function accepts either:
    - Current shape: {"messages": [{ "role": "user" | "assistant" | "system", "content": "..." }], "response_style"?: "plain"|"list"|"guided"}
    - Legacy shape: {"message": "..."}

    Returns
    -------
    ChatRequest
        A validated ChatRequest instance constructed from the input.

    Raises
    ------
    ValueError
        If the payload does not match either accepted shape.
    """
    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object.")

    # Lightweight compatibility shim: if a frontend sends {text: "..."} or {query: "..."},
    # treat it as the legacy minimal shape.
    if "message" not in data and "messages" not in data:
        if "text" in data and isinstance(data["text"], (str, int, float)):
            # normalize to string
            data = {**data, "message": str(data["text"])}
        elif "query" in data and isinstance(data["query"], (str, int, float)):
            data = {**data, "message": str(data["query"])}

    # Prefer modern shape when messages key is present
    if "messages" in data:
        try:
            # Validate that content fields are strings (avoid non-string types)
            msgs = data.get("messages")
            if not isinstance(msgs, list) or not msgs:
                raise ValidationError.from_exception_data(
                    title="ChatRequest",
                    line_errors=[
                        {
                            "type": "list_too_short",
                            "loc": ("messages",),
                            "msg": "messages must be a non-empty array",
                            "input": msgs,
                            "ctx": {"min_length": 1},
                        }
                    ],
                )
            # Ensure each message.content is a string with non-whitespace
            for idx, m in enumerate(msgs):
                if not isinstance(m, dict):
                    raise ValidationError.from_exception_data(
                        title="ChatRequest",
                        line_errors=[
                            {
                                "type": "model_type",
                                "loc": ("messages", idx),
                                "msg": "Each message must be an object",
                                "input": m,
                            }
                        ],
                    )
                content = m.get("content")
                if not isinstance(content, str):
                    raise ValidationError.from_exception_data(
                        title="ChatRequest",
                        line_errors=[
                            {
                                "type": "string_type",
                                "loc": ("messages", idx, "content"),
                                "msg": "content must be a string",
                                "input": content,
                            }
                        ],
                    )
                if not content.strip():
                    raise ValidationError.from_exception_data(
                        title="ChatRequest",
                        line_errors=[
                            {
                                "type": "string_too_short",
                                "loc": ("messages", idx, "content"),
                                "msg": "content must be a non-empty string",
                                "input": content,
                                "ctx": {"min_length": 1},
                            }
                        ],
                    )
            return ChatRequest.model_validate(data)
        except ValidationError as ve:
            # Re-raise a friendlier error with compact details
            errs = ve.errors()
            raise ValueError(f"Invalid 'messages' payload. Errors: {errs}") from ve

    # Accept legacy/minimal shape
    if "message" in data:
        try:
            msg_val = data.get("message")
            # Allow basic non-string (number/bool) but coerce to string, then validate non-empty trimmed
            if isinstance(msg_val, (int, float, bool)):
                msg_val = str(msg_val)
            if not isinstance(msg_val, str):
                raise ValidationError.from_exception_data(
                    title="ChatRequestLegacy",
                    line_errors=[
                        {
                            "type": "string_type",
                            "loc": ("message",),
                            "msg": "Message must be a string",
                            "input": msg_val,
                        }
                    ],
                )
            if not msg_val.strip():
                raise ValidationError.from_exception_data(
                    title="ChatRequestLegacy",
                    line_errors=[
                        {
                            "type": "string_too_short",
                            "loc": ("message",),
                            "msg": "Message must be a non-empty string",
                            "input": msg_val,
                            "ctx": {"min_length": 1},
                        }
                    ],
                )
            legacy = ChatRequestLegacy.model_validate({"message": msg_val})
        except ValidationError as ve:
            raise ValueError(f"Invalid legacy 'message' payload. Errors: {ve.errors()}") from ve
        # Convert into modern ChatRequest with a single user message
        return ChatRequest(messages=[Message(role=RoleEnum.user, content=legacy.message)])

    # Neither shape present
    raise ValueError("Missing required field: provide either 'messages' or 'message'.")
