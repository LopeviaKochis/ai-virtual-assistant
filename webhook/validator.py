import hmac
import hashlib
import base64
from typing import Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

def validate_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """
    Valida la firma HMAC-SHA256 del webhook de Respond.io.
    
    Respond.io envía la firma en formato base64 en el header X-Webhook-Signature.
    
    Args:
        raw_body: Cuerpo raw del request (bytes)
        signature: Valor de cabecera X-Webhook-Signature
        
    Returns:
        True si la firma es válida, False en caso contrario
    """
    if not signature:
        logger.warning("No signature provided in request")
        return False
    
    if not settings.RESPONDIO_WEBHOOK_SECRET:
        logger.error("RESPONDIO_WEBHOOK_SECRET not configured")
        return False
    
    try:
        # Calcular HMAC-SHA256
        calculated_hmac = hmac.new(
            key=settings.RESPONDIO_WEBHOOK_SECRET.encode('utf-8'),
            msg=raw_body,
            digestmod=hashlib.sha256
        )
        
        # Respond.io envía la firma en base64
        expected_signature = base64.b64encode(calculated_hmac.digest()).decode('utf-8')
        
        # Log para debugging (remover en producción)
        logger.debug(f"Expected signature: {expected_signature}")
        logger.debug(f"Received signature: {signature}")
        logger.debug(f"Secret (first 10 chars): {settings.RESPONDIO_WEBHOOK_SECRET[:10]}...")
        logger.debug(f"Raw body length: {len(raw_body)}")
        
        # Comparación segura contra timing attacks
        is_valid = hmac.compare_digest(expected_signature, signature)
        
        if not is_valid:
            logger.warning(f"Signature mismatch! Expected: {expected_signature}, Got: {signature}")
        
        return is_valid
        
    except Exception as e:
        logger.exception(f"Error validating signature: {e}")
        return False