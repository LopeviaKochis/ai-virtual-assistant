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
        self.workspace_id = settings.RESPONDIO_WORKSPACE_ID
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def send_message(
        self,
        contact_id: str,
        message_text: str,
        channel_id: Optional[str] = None
    ) -> bool:
        """
        Envía un mensaje de texto a un contacto vía Respond.io.
        
        Args:
            contact_id: ID del contacto en Respond.io
            message_text: Texto del mensaje a enviar
            channel_id: ID del canal (opcional, usa default si no se provee)
            
        Returns:
            True si se envió correctamente
        """
        endpoint = f"{self.base_url}/message/send"
        
        # Usar channel_id provisto o el configurado por defecto
        target_channel_id = channel_id or settings.RESPONDIO_CHANNEL_ID
        
        payload = {
            "contactId": int(contact_id),
            "channelId": int(target_channel_id) if target_channel_id else None,
            "message": {
                "type": "text",
                "text": message_text
            }
        }
        
        logger.debug(f"Sending message payload: {payload}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Message sent to contact {contact_id} via channel {target_channel_id}")
                    return True
                else:
                    logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            return False

# Cliente singleton
respondio_client = RespondIOClient()
