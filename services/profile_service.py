import logging
from typing import Optional, Dict, Any
from clients.cosmos_client import cosmos_client
from models.user_profile import UserProfile
from services.extraction_service import extract_dni, extract_phone

logger = logging.getLogger(__name__)

class ProfileService:
    """Servicio para gestionar perfiles de usuario."""
    
    def load_or_create_profile(
        self, 
        contact_id: str,
        contact_data: Dict[str, Any],
        channel_data: Dict[str, Any]
    ) -> UserProfile:
        """
        Carga perfil existente o crea uno nuevo.
        """
        # Intentar cargar de Cosmos DB
        profile_data = cosmos_client.get_profile(contact_id)
        
        if profile_data:
            profile = UserProfile(**profile_data)
            logger.info(f"Profile loaded for {contact_id}")
        else:
            # Crear nuevo perfil
            profile = UserProfile(
                contactId=contact_id,
                firstName=contact_data.get("firstName"),
                lastName=contact_data.get("lastName"),
                phone=contact_data.get("phone"),
                email=contact_data.get("email"),
                channelId=str(channel_data.get("id")),
                channelSource=channel_data.get("source")
            )
            logger.info(f"New profile created for {contact_id}")
        
        return profile
    
    def enrich_profile_from_message(
        self, 
        profile: UserProfile, 
        message_text: str
    ) -> UserProfile:
        """
        Enriquece perfil extrayendo datos del mensaje.
        """
        # Extraer DNI si no lo tiene
        if not profile.dni:
            if dni := extract_dni(message_text):
                profile.dni = dni
                logger.info(f"DNI extracted: {dni}")
        
        # Extraer teléfono si no lo tiene
        if not profile.phone:
            if phone := extract_phone(message_text):
                profile.phone = phone
                logger.info(f"Phone extracted: {phone}")
        
        return profile
    
    def verify_profile(self, profile: UserProfile) -> bool:
        """
        Verifica si el perfil tiene datos suficientes.
        """
        return bool(profile.dni or profile.phone)
    
    def save_profile(self, profile: UserProfile) -> None:
        """
        Guarda perfil en Cosmos DB.
        """
        from datetime import datetime
        profile.updatedAt = datetime.utcnow()
        profile.totalMessages += 1
        profile.lastInteractionAt = datetime.utcnow()
        
        cosmos_client.upsert_profile(profile.model_dump())
        logger.info(f"Profile saved for {profile.contactId}")

profile_service = ProfileService()
