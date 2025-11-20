from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class UserProfile(BaseModel):
    """Perfil completo del usuario con historial."""
    
    # Identificadores
    contactId: str  # Respond.io Contact ID (partition key)
    dni: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    
    # Información personal
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    
    # Metadata de Respond.io
    channelId: Optional[str] = None
    channelSource: Optional[str] = None  # "telegram", "whatsapp", etc.
    
    # Estado de verificación
    isVerified: bool = False
    verifiedAt: Optional[datetime] = None
    
    # Historial de interacciones
    totalMessages: int = 0
    lastInteractionAt: Optional[datetime] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    
    # Preferencias
    preferredLanguage: str = "es"
    
    # Datos adicionales
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    