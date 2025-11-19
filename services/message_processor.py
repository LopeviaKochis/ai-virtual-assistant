import logging
from typing import Dict, Any, Optional

from services.router_service import route_message
from services.rag_service import build_personalized_answer
from services.session_service import get_session, save_session, set_pending_intent, clear_pending_intent
from services.extraction_service import enrich_session_from_message, format_response_with_name
from clients.azure_client import search_debt_by_dni, search_otp_by_phone
from clients.respondio_client import respondio_client

logger = logging.getLogger(__name__)

async def process_message_for_webhook(event_data: Dict[str, Any]) -> None:
    """
    Procesa un evento message.received del webhook de Respond.io.
    Usado por el worker asíncrono.
    
    Args:
        event_data: Datos completos del evento webhook
    """
    data = event_data.get("data", {})
    contact = data.get("contact", {})
    message = data.get("message", {})
    conversation = data.get("conversation", {})
    
    contact_id = str(contact.get("id", ""))
    message_text = message.get("text", "").strip()
    conversation_id = conversation.get("id")
    
    if not contact_id or not message_text:
        logger.warning("Missing contact_id or message_text in webhook event")
        return
    
    # Procesar mensaje
    response_text = await process_message_internal(
        contact_id=contact_id,
        message_text=message_text,
        contact_name=contact.get("first_name"),
        contact_phone=contact.get("phone")
    )
    
    # Enviar respuesta vía API de Respond.io
    success = await respondio_client.send_message(
        contact_id=contact_id,
        message_text=response_text,
        conversation_id=conversation_id
    )
    
    if not success:
        logger.error(f"Failed to send response to contact {contact_id}")

async def process_message_for_api(
    contact_id: str,
    message_text: str,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None
) -> Dict[str, Any]:
    """
    Procesa un mensaje desde el endpoint HTTP de la API.
    Usado por el endpoint REST.
    
    Args:
        contact_id: ID del contacto
        message_text: Texto del mensaje
        contact_name: Nombre del contacto (opcional)
        contact_phone: Teléfono del contacto (opcional)
        
    Returns:
        Diccionario con respuesta y metadata
    """
    response_text = await process_message_internal(
        contact_id=contact_id,
        message_text=message_text,
        contact_name=contact_name,
        contact_phone=contact_phone
    )
    
    session = get_session(contact_id)
    
    return {
        "response_text": response_text,
        "session": session,
        "contact_id": contact_id
    }

async def process_message_internal(
    contact_id: str,
    message_text: str,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None
) -> str:
    """
    Lógica interna de procesamiento de mensajes (core).
    
    Args:
        contact_id: ID del contacto
        message_text: Texto del mensaje
        contact_name: Nombre del contacto (opcional)
        contact_phone: Teléfono del contacto (opcional)
        
    Returns:
        Texto de la respuesta personalizada
    """
    logger.info(f"Processing message from {contact_id}: {message_text[:50]}...")
    
    # 1. Obtener y enriquecer sesión
    session = get_session(contact_id)
    session = enrich_session_from_message(
        session, 
        message_text,
        contact_name,
        contact_phone
    )
    
    # 2. Enrutar mensaje
    route = route_message(message_text)
    intent = route.get("intent", "general")
    requires_identity = route.get("requires_identity", False)
    reason = route.get("reason")
    
    logger.info(f"Intent: {intent}, requires_identity: {requires_identity}")
    
    response_text = ""
    
    # 3. Procesar según intención
    if intent == "general" or not requires_identity:
        response_text = route.get("concise_answer", "¿En qué puedo ayudarte?")
        clear_pending_intent(contact_id)
    
    elif intent == "debt":
        response_text = await _process_debt_intent(
            contact_id, session, message_text, route, reason
        )
    
    elif intent == "otp":
        response_text = await _process_otp_intent(
            contact_id, session, message_text, route, reason
        )
    
    else:
        response_text = "Puedo ayudarte con consultas de deuda o claves OTP. ¿Qué necesitas?"
        clear_pending_intent(contact_id)
    
    # 4. Personalizar con nombre
    response_text = format_response_with_name(session.get("name"), response_text)
    
    # 5. Guardar sesión actualizada
    save_session(contact_id, session)
    
    logger.info(f"Response ready for {contact_id}")
    return response_text

async def _process_debt_intent(
    contact_id: str,
    session: Dict[str, Any],
    message_text: str,
    route: Dict[str, Any],
    reason: Optional[str]
) -> str:
    """Procesa intención de consulta de deuda."""
    dni = session.get("dni")
    
    if dni:
        logger.info(f"Searching debt for DNI: {dni}")
        df = search_debt_by_dni(dni)
        
        if df.empty:
            clear_pending_intent(contact_id)
            return f"No encontré información para el DNI {dni}. Por favor verifica que sea correcto."
        
        clear_pending_intent(contact_id)
        return build_personalized_answer(
            message_text,
            df,
            session.get("name"),
            reason,
            intent="debt"
        )
    else:
        # DNI faltante - marcar como pendiente
        set_pending_intent(contact_id, "debt", reason, message_text)
        return route.get("followup_question", "Para consultar tu deuda, necesito tu DNI (8 dígitos).")

async def _process_otp_intent(
    contact_id: str,
    session: Dict[str, Any],
    message_text: str,
    route: Dict[str, Any],
    reason: Optional[str]
) -> str:
    """Procesa intención de consulta de clave OTP."""
    phone = session.get("phone")
    
    if phone:
        logger.info(f"Searching OTP for phone: {phone}")
        df = search_otp_by_phone(phone)
        
        if df.empty:
            clear_pending_intent(contact_id)
            return f"No encontré una clave OTP activa para el número {phone}. ¿Puedes verificarlo?"
        
        clear_pending_intent(contact_id)
        return build_personalized_answer(
            message_text,
            df,
            session.get("name"),
            reason,
            intent="otp",
            phone=phone
        )
    else:
        # Teléfono faltante - marcar como pendiente
        set_pending_intent(contact_id, "otp", reason, message_text)
        return route.get("followup_question", "Para encontrar tu clave OTP, necesito tu número de celular (9 dígitos).")