import httpx
import logging
from typing import Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class RespondIOClient:
    """Cliente para enviar mensajes mediante la API de Respond.io."""
    
    def __init__(self):
        self.base_url = settings.RESPONDIO_API_URL
        self.token = settings.RESPONDIO_API_TOKEN
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
        endpoint = f"{self.base_url}/messages"
        
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
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Message sent to contact {contact_id}")
                    return True
                else:
                    logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            return False

# Cliente singleton
respondio_client = RespondIOClient()