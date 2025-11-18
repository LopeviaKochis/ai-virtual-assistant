from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Union
from datetime import datetime

class Contact(BaseModel):
    id: Union[int, str]
    first_name: Optional[str] = Field(None, alias="firstName")
    last_name: Optional[str] = Field(None, alias="lastName")
    phone: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = None
    profile_pic: Optional[str] = Field(None, alias="profilePic")
    country_code: Optional[str] = Field(None, alias="countryCode")
    status: Optional[str] = None
    assignee: Optional[Dict[str, Any]] = None
    created_at: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="customFields")
    
    class Config:
        populate_by_name = True

class Message(BaseModel):
    id: Union[int, str]
    type: str
    text: Optional[str] = None
    timestamp: Optional[Union[datetime, int]] = None
    channel: Optional[str] = None
    channel_id: Optional[Union[int, str]] = Field(None, alias="channelId")
    
    class Config:
        populate_by_name = True

class Conversation(BaseModel):
    id: Optional[Union[int, str]] = None
    source: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[Union[int, str, Dict[str, Any]]] = None
    conversation_opened_at: Optional[int] = Field(None, alias="conversationOpenedAt")
    first_incoming_message: Optional[str] = Field(None, alias="firstIncomingMessage")
    first_incoming_message_channel_id: Optional[int] = Field(None, alias="firstIncomingMessageChannelId")
    
    class Config:
        populate_by_name = True

class MessageReceivedData(BaseModel):
    conversation: Optional[Conversation] = None
    contact: Optional[Contact] = None
    message: Optional[Message] = None

class WebhookEvent(BaseModel):
    """
    Schema flexible para eventos de Respond.io.
    Soporta tanto payloads de prueba como de producción.
    """
    # El campo principal del evento (puede venir como 'event' o 'event_type')
    event: str
    event_type: Optional[str] = None
    event_id: Optional[str] = None
    
    # Campos opcionales para producción
    timestamp: Optional[datetime] = None
    workspace_id: Optional[str] = None
    
    # Data puede ser un dict flexible o un objeto estructurado
    data: Optional[Union[Dict[str, Any], MessageReceivedData]] = None
    
    # Campos que vienen directamente en el root (formato de prueba)
    contact: Optional[Contact] = None
    conversation: Optional[Conversation] = None
    message: Optional[Message] = None
    
    @field_validator('event', mode='before')
    @classmethod
    def normalize_event(cls, v, info):
        """Normaliza el campo event desde event_type si es necesario"""
        if not v and info.data.get('event_type'):
            return info.data['event_type']
        return v
    
    class Config:
        populate_by_name = True
        extra = 'allow'  # Permite campos adicionales sin fallar
    
    def get_contact(self) -> Optional[Contact]:
        """Helper para obtener el contacto sin importar la estructura"""
        if self.contact:
            return self.contact
        if self.data and isinstance(self.data, dict):
            contact_data = self.data.get('contact')
            if contact_data:
                return Contact(**contact_data)
        if isinstance(self.data, MessageReceivedData) and self.data.contact:
            return self.data.contact
        return None
    
    def get_message(self) -> Optional[Message]:
        """Helper para obtener el mensaje sin importar la estructura"""
        if self.message:
            return self.message
        if self.data and isinstance(self.data, dict):
            message_data = self.data.get('message')
            if message_data:
                return Message(**message_data)
        if isinstance(self.data, MessageReceivedData) and self.data.message:
            return self.data.message
        return None
    
    def get_conversation(self) -> Optional[Conversation]:
        """Helper para obtener la conversación sin importar la estructura"""
        if self.conversation:
            return self.conversation
        if self.data and isinstance(self.data, dict):
            conv_data = self.data.get('conversation')
            if conv_data:
                return Conversation(**conv_data)
        if isinstance(self.data, MessageReceivedData) and self.data.conversation:
            return self.data.conversation
        return None