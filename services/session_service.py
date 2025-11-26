import json
import logging
from typing import Dict, Any, Optional
from clients.queue_client import get_redis_client

logger = logging.getLogger(__name__)

SESSION_TTL = 86400  # 24 horas

def get_session(contact_id: str) -> Dict[str, Any]:
    """
    Recupera la sesión de un usuario desde Redis.
    
    Args:
        contact_id: ID del contacto en Respond.io
        
    Returns:
        Diccionario con datos de la sesión o dict vacío
    """
    try:
        client = get_redis_client()
        key = f"session:{contact_id}"
        data = client.get(key)
        
        if data:
            # Decode bytes to string before loading JSON
            data_str = data.decode('utf-8') if isinstance(data, bytes) else str(data)
            session = json.loads(data_str)
            logger.debug(f"Session loaded for contact {contact_id}")
            return session
        
        logger.debug(f"No session found for contact {contact_id}, returning empty")
        return {}
        
    except Exception as e:
        logger.warning(f"Error retrieving session for {contact_id}: {e}")
        return {}

def save_session(contact_id: str, session: Dict[str, Any]) -> bool:
    """
    Guarda la sesión de un usuario en Redis con TTL de 24 horas.
    
    Args:
        contact_id: ID del contacto
        session: Diccionario con datos de la sesión
        
    Returns:
        True si se guardó correctamente
    """
    try:
        client = get_redis_client()
        key = f"session:{contact_id}"
        serialized = json.dumps(session)
        client.setex(key, SESSION_TTL, serialized)
        logger.debug(f"Session saved for contact {contact_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving session for {contact_id}: {e}")
        return False

def update_session(contact_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Actualiza campos específicos de la sesión sin sobrescribir toda la sesión.
    
    Args:
        contact_id: ID del contacto
        updates: Diccionario con campos a actualizar
        
    Returns:
        Sesión actualizada completa
    """
    session = get_session(contact_id)
    session.update(updates)
    save_session(contact_id, session)
    return session

def clear_session(contact_id: str) -> bool:
    """
    Elimina la sesión de un usuario.
    
    Args:
        contact_id: ID del contacto
        
    Returns:
        True si se eliminó correctamente
    """
    try:
        client = get_redis_client()
        key = f"session:{contact_id}"
        deleted = client.delete(key)
        logger.info(f"Session cleared for contact {contact_id}: {bool(deleted)}")
        return bool(deleted)
        
    except Exception as e:
        logger.error(f"Error clearing session for {contact_id}: {e}")
        return False

def set_pending_intent(contact_id: str, intent: str, reason: Optional[str], user_msg: str) -> None:
    """
    Marca una intención como pendiente mientras esperamos más datos del usuario.
    
    Args:
        contact_id: ID del contacto
        intent: Intención pendiente (debt/otp)
        reason: Razón de la intención
        user_msg: Mensaje original del usuario
    """
    updates = {
        "pending_intent": intent,
        "pending_reason": reason,
        "pending_user_msg": user_msg
    }
    update_session(contact_id, updates)
    logger.info(f"Pending intent set for {contact_id}: {intent}")

def clear_pending_intent(contact_id: str) -> None:
    """
    Limpia la intención pendiente de la sesión.
    
    Args:
        contact_id: ID del contacto
    """
    session = get_session(contact_id)
    session.pop("pending_intent", None)
    session.pop("pending_reason", None)
    session.pop("pending_user_msg", None)
    save_session(contact_id, session)
    logger.debug(f"Pending intent cleared for {contact_id}")