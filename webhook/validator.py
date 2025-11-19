import hmac
import hashlib
import base64
from typing import Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

def validate_webhook_signature(raw_body: bytes, signature: Optional[str], webhook_type: str = "message") -> bool:
    """
    Valida la firma HMAC-SHA256 del webhook de Respond.io.
    Soporta múltiples webhooks con secretos diferentes.
    
    Args:
        raw_body: Cuerpo raw del request (bytes)
        signature: Valor de cabecera X-Webhook-Signature
        webhook_type: Tipo de webhook ("message" o "conversation")
        
    Returns:
        True si la firma es válida, False en caso contrario
    """
    if not signature:
        logger.warning("No signature provided in request")
        return False
    
    # Seleccionar el secreto correcto según el tipo de webhook
    if webhook_type == "message":
        secret = settings.RESPONDIO_WEBHOOK_INCOMING_MESSAGE_SECRET
    elif webhook_type == "conversation":
        secret = settings.RESPONDIO_WEBHOOK_CHAT_OPEN_SECRET
    else:
        logger.error(f"Unknown webhook type: {webhook_type}")
        return False
    
    if not secret:
        logger.error(f"Secret not configured for webhook type: {webhook_type}")
        return False
    
    try:
        # Calcular HMAC-SHA256
        calculated_hmac = hmac.new(
            key=secret.encode('utf-8'),
            msg=raw_body,
            digestmod=hashlib.sha256
        )
        
        # Respond.io envía la firma en base64
        expected_signature = base64.b64encode(calculated_hmac.digest()).decode('utf-8')
        
        # Log para debugging (remover en producción)
        logger.debug(f"Expected signature: {expected_signature}")
        logger.debug(f"Received signature: {signature}")
        logger.debug(f"Webhook type: {webhook_type}")
        logger.debug(f"Secret (first 10 chars): {secret[:10]}...")
        
        # Comparación segura contra timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if not is_valid:
            logger.warning(f"Signature mismatch for {webhook_type}! Expected: {expected_signature}, Got: {signature}")
        
        return is_valid
        
    except Exception as e:
        logger.exception(f"Error validating signature: {e}")
        return False