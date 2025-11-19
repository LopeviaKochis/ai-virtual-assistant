from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Union
from datetime import datetime

class Contact(BaseModel):
    id: Union[int, str]
    firstName: Optional[str] = Field(None, alias="firstName")
    lastName: Optional[str] = Field(None, alias="lastName")
    phone: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None
    profilePic: Optional[str] = Field(None, alias="profilePic")
    countryCode: Optional[str] = Field(None, alias="countryCode")
    status: Optional[str] = None
    assignee: Optional[Dict[str, Any]] = None
    created_at: Optional[int] = None
    lifecycle: Optional[str] = None
    customFields: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="customFields")
    
    class Config:
        populate_by_name = True

class MessageContent(BaseModel):
    """Contenido del mensaje según el tipo"""
    type: str
    text: Optional[str] = None
    messageTag: Optional[str] = Field(None, alias="messageTag")
    
    class Config:
        populate_by_name = True
        extra = 'allow'

class IncomingMessage(BaseModel):
    """Schema para mensaje entrante de Respond.io"""
    messageId: Union[int, str]
    channelMessageId: Optional[Union[int, str]] = None
    contactId: Optional[Union[int, str]] = None
    channelId: Optional[Union[int, str]] = None
    traffic: str  # "incoming" o "outgoing"
    timestamp: int
    message: MessageContent
    
    class Config:
        populate_by_name = True

class Channel(BaseModel):
    """Información del canal de comunicación"""
    id: Union[int, str]
    name: str
    source: str  # "telegram", "whatsapp", "facebook", etc.
    meta: Optional[str] = None
    created_at: Optional[int] = None
    
    class Config:
        populate_by_name = True

class Conversation(BaseModel):
    id: Optional[Union[int, str]] = None
    source: Optional[str] = None
    status: Optional[str] = None
    conversationOpenedAt: Optional[int] = None
    firstIncomingMessage: Optional[str] = None
    firstIncomingMessageChannelId: Optional[int] = None
    
    class Config:
        populate_by_name = True

class MessageReceivedData(BaseModel):
    """Data específica para evento message.received"""
    contact: Optional[Contact] = None
    message: Optional[IncomingMessage] = None
    channel: Optional[Channel] = None

class ConversationOpenedData(BaseModel):
    """Data específica para evento conversation.opened"""
    contact: Optional[Contact] = None
    conversation: Optional[Conversation] = None

class WebhookEvent(BaseModel):
    """
    Schema flexible para eventos de Respond.io.
    Soporta múltiples tipos de eventos.
    """
    event_type: str
    event_id: str
    
    # Campos que pueden venir en el root o en data
    contact: Optional[Contact] = None
    message: Optional[IncomingMessage] = None
    channel: Optional[Channel] = None
    conversation: Optional[Conversation] = None
    
    @field_validator('event_type', mode='before')
    @classmethod
    def normalize_event_type(cls, v):
        """Normaliza el tipo de evento"""
        return v or "unknown"
    
    class Config:
        populate_by_name = True
        extra = 'allow'
    
    def get_contact(self) -> Optional[Contact]:
        """Helper para obtener el contacto"""
        return self.contact
    
    def get_message(self) -> Optional[IncomingMessage]:
        """Helper para obtener el mensaje"""
        return self.message
    
    def get_channel(self) -> Optional[Channel]:
        """Helper para obtener el canal"""
        return self.channel
    
    def get_conversation(self) -> Optional[Conversation]:
        """Helper para obtener la conversación"""
        return self.conversation