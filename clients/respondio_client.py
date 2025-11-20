import httpx
import logging
from typing import Optional, Any
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
    
    def _format_identifier(self, identifier: str) -> str:
        """
        Formatea el identificador según el formato requerido por Respond.io API.
        
        Según la documentación oficial:
        - Telegram ID numérico: "id:7986242435"
        - Email: "email:user@example.com"
        - Teléfono: "phone:+60121233112"
        - Contact ID: "id:347713428"
        
        Args:
            identifier: Identificador raw (puede ser ID, email o teléfono)
            
        Returns:
            Identificador formateado con prefijo correcto
        """
        # Si ya tiene prefijo, devolverlo tal cual
        if identifier.startswith(("id:", "email:", "phone:")):
            return identifier
        
        # Detectar tipo de identificador
        if "@" in identifier:
            # Es un email
            return f"email:{identifier}"
        elif identifier.startswith("+") or (identifier.startswith("9") and len(identifier) == 9):
            # Es un teléfono (con o sin código de país)
            phone = identifier if identifier.startswith("+") else f"+51{identifier}"
            return f"phone:{phone}"
        else:
            # Es un ID numérico (Telegram ID o Contact ID)
            return f"id:{identifier}"

    async def send_message(
        self,
        contact_id: str,
        message_text: str,
        channel_id: Optional[str] = None
    ) -> bool:
        """
        Envía un mensaje de texto a un contacto vía Respond.io.
        
        Args:
            contact_id: ID del contacto en Respond.io (ID, email o teléfono)
            message_text: Texto del mensaje a enviar
            channel_id: ID del canal (opcional, usa default si no se provee)
            
        Returns:
            True si se envió correctamente
        """
        # Formateo identificador con prefijo correcto "id:"
        formatted_identifier = self._format_identifier(contact_id)

        # Endpoint correcto según documentación oficial
        endpoint = f"{self.base_url}/contact/{formatted_identifier}/message"
        
        # Usar channel_id provisto o el configurado por defecto
        target_channel_id = channel_id or settings.RESPONDIO_CHANNEL_ID
        
        # Payload según documentación oficial
        payload: dict[str, Any] = {
            "message": {
                "type": "text",
                "text": message_text
            }
        }
        
        # Agregar channelId solo si está disponible (opcional según docs)
        if target_channel_id:
            payload["channelId"] = int(target_channel_id)

        logger.debug(f"Original identifier: {contact_id}")
        logger.debug(f"Formatted identifier: {formatted_identifier}")        
        logger.debug(f"Sending message to endpoint: {endpoint}")
        logger.debug(f"Sending message payload: {payload}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Message sent to {formatted_identifier} via channel {target_channel_id}")
                    return True
                else:
                    logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            return False

# Cliente singleton
respondio_client = RespondIOClient()
