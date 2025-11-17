import hmac
import hashlib
from typing import Optional
from config.settings import settings

def validate_webhook_signature(raw_body: bytes, signature: Optional[str]) -> bool:
    """
    Valida la firma HMAC-SHA256 del webhook de Respond.io.
    
    Args:
        raw_body: Cuerpo raw del request (bytes)
        signature: Valor de cabecera X-Webhook-Signature
        
    Returns:
        True si la firma es válida, False en caso contrario
    """
    if not signature:
        return False
    
    expected_signature = hmac.new(
        key=settings.RESPONDIO_WEBHOOK_SECRET.encode('utf-8'),
        msg=raw_body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)
