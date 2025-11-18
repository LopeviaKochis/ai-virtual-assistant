import httpx
import logging
from typing import Optional, Any, Dict
from config.settings import settings

logger = logging.getLogger(__name__)

class RespondIOClient:
    """Cliente para enviar mensajes mediante la API de Respond.io."""
    
    def __init__(self):
        self.base_url = settings.RESPONDIO_API_URL
        self.token = settings.RESPONDIO_API_TOKEN
        self.workspace_id = settings.RESPONDIO_WORKSPACE_ID
        self.channel_id = settings.RESPONDIO_CHANNEL_ID
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def send_message(
        self,
        contact_id: str,
        message_text: str,
        conversation_id: Optional[str] = None
    ) -> bool:
        """
        Envía un mensaje de texto a un contacto.
        
        Args:
            contact_id: ID del contacto en Respond.io
            message_text: Texto del mensaje a enviar
            conversation_id: ID de conversación (opcional)
            
        Returns:
            True si se envió correctamente
        """
        endpoint = f"{self.base_url}/message/send"
        
        payload = {
            "contactId": contact_id,
            "message": {
                "type": "text",
                "text": message_text
            }
        }
        
        if conversation_id:
            payload["conversationId"] = conversation_id
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Message sent to contact {contact_id}")
                    return True
                else:
                    logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            return False
        
    async def get_or_create_contact(
        self,
        telegram_user_id: int,
        phone: Optional[str] = None,
        name: Optional[str] = None
    ) -> Optional[str]:
        """
         Busca o crea un contacto en Respond.io usando el ID de Telegram.
        
        Args:
            telegram_user_id: ID único del usuario en Telegram
            name: Nombre del usuario (opcional)
            phone: Teléfono del usuario (opcional)
            
        Returns:
            contact_id de Respond.io o None si falla
        """

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                search_endpoint = f"{self.base_url}/contact/search"
                search_params = {
                    "q": str(telegram_user_id),
                    "field": "telegram_user_id",
                }

                response = await client.get(
                    search_endpoint,
                    params=search_params,
                    headers=self.headers
                )

                if response.status_code == 200:
                    data = response.json()
                    contacts = data.get("contacts", [])
                    if contacts:
                        contact_id = contacts[0].get("id")
                        logger.info(f"Found existing contact with ID {contact_id} from Telegram user ID {telegram_user_id}")
                        return contact_id
                    
                create_endpoint = f"{self.base_url}/contact/create"
                contact_data = {
                    "workspaceId": self.workspace_id,
                    "customFields": {
                        "telegram_user_id": str(telegram_user_id)
                    }
                }

                if name:
                    contact_data["name"] = name
                if phone:
                    contact_data["phone"] = phone

                response = await client.post(
                    create_endpoint,
                    json=contact_data,
                    headers=self.headers
                )

                if response.status_code in [200, 201]:
                    contact_id = response.json().get("id")
                    logger.info(f"Created new contact {contact_id} for Telegram users {telegram_user_id}")
                    return contact_id
                else:
                    logger.error(f"Failed to create contact: {response.status_code} - {response.text}")
                    return None
        except Exception as e:
            logger.exception(f"Error getting or creating contact: {e}")
            return None
    
    async def log_message(
        self,
        contact_id: str,
        message_text: str,
        direction: str = "incoming",
        channel_id: Optional[str] = None
    ) -> bool:
        """
        Registra un mensaje en el historial de Respond.io sin enviarlo.
        Útil para sincronizar conversaciones de otros canales.
        
        Args:
            contact_id: ID del contacto
            message_text: Contenido del mensaje
            direction: "incoming" (del usuario) o "outgoing" (del bot)
            channel_id: ID del canal en Respond.io
            
        Returns:
            True si se registró correctamente
        """
        endpoint = f"{self.base_url}/message/log"
        
        payload = {
            "contactId": contact_id,
            "message": {
                "type": "text",
                "text": message_text
            },
            "direction": direction
        }
        
        channel_id_value = channel_id or settings.RESPONDIO_CHANNEL_ID
        if channel_id_value:
            payload["channelId"] = [channel_id_value]  # Envuelto en una lista
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code in [200, 201]:
                    logger.debug(f"Message logged for contact {contact_id} ({direction})")
                    return True
                else:
                    logger.warning(f"Failed to log message: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Error logging message: {e}")
            return False

# Cliente singleton
respondio_client = RespondIOClient()

# Cliente singleton
respondio_client = RespondIOClient()
