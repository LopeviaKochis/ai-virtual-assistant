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
            contact_id: ID del contacto en Respond.io
            message_text: Texto del mensaje a enviar
            channel_id: ID del canal (OBLIGATORIO para multi-canal)
            
        Returns:
            True si se envió correctamente
        """
        # Formatear identificador
        formatted_identifier = self._format_identifier(contact_id)

        # Endpoint correcto
        endpoint = f"{self.base_url}/contact/{formatted_identifier}/message"
        
        # NUEVO: Priorizar channel_id provisto sobre el default
        target_channel_id = channel_id or settings.RESPONDIO_CHANNEL_ID
        
        if not target_channel_id:
            logger.error(f"No channel_id provided and no default configured")
            return False
        
        # Payload
        payload: dict[str, Any] = {
            "message": {
                "type": "text",
                "text": message_text
            },
            "channelId": int(target_channel_id)  # SIEMPRE incluir channelId
        }

        logger.info(f"[Respond.io] Sending to {formatted_identifier} via channel {target_channel_id}")
        logger.debug(f"[Respond.io] Payload: {payload}")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Message sent successfully to {formatted_identifier}")
                    return True
                else:
                    logger.error(f" API Error {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.exception(f"Exception sending message: {e}")
            return False

    async def mark_message_read(
        self,
        message_id: str,
        channel_id: str
    ) -> bool:
        """
        Marca un mensaje como leído en Respond.io.
        Esto pone el doble check azul/gris inmediatamente.
        
        Args:
            message_id: ID del mensaje a marcar
            channel_id: ID del canal
            
        Returns:
            True si se marcó correctamente
        """
        endpoint = f"{self.base_url}/message/{message_id}/read"
        
        payload = {
            "channelId": int(channel_id)
        }
        
        logger.debug(f"Marking message {message_id} as read on channel {channel_id}")
        
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:  # Timeout corto
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code in [200, 201, 204]:
                    logger.debug(f"Message {message_id} marked as read")
                    return True
                else:
                    logger.warning(f"Failed to mark as read: {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Exception marking as read (non-critical): {e}")
            return False  # Fail silently

# Cliente singleton
respondio_client = RespondIOClient()
