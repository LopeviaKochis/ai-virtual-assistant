from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class Contact(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)

class Message(BaseModel):
    id: str
    type: str
    text: Optional[str] = None
    timestamp: datetime
    channel: str

class Conversation(BaseModel):
    id: str
    status: str
    assignee: Optional[str] = None

class MessageReceivedData(BaseModel):
    conversation: Conversation
    contact: Contact
    message: Message

class WebhookEvent(BaseModel):
    event: str
    timestamp: datetime
    workspace_id: str
    data: Dict[str, Any]