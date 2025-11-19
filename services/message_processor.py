import logging
import json
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
    NUEVA ESTRUCTURA: Extrae datos del payload actualizado.
    
    Args:
        event_data: Datos completos del evento webhook
    """

    # NUEVO: Log inicial del evento completo
    logger.info("="*60)
    logger.info("PROCESANDO EVENTO EN MESSAGE_PROCESSOR")
    logger.info(f"Event data keys: {list(event_data.keys())}")
    logger.info(f"Event data completo: {json.dumps(event_data, indent=2, default=str)}")
    logger.info("="*60)

    # Extraer datos del nuevo formato
    contact = event_data.get("contact", {})
    message_data = event_data.get("message", {})
    channel_data = event_data.get("channel", {})
    
    # NUEVO: Log de extracción
    logger.info(f"Contact data: {contact}")
    logger.info(f"Message data: {message_data}")
    logger.info(f"Channel data: {channel_data}")

    # IDs importantes
    contact_id = str(contact.get("id", ""))
    channel_id = str(channel_data.get("id", ""))

    logger.info(f"🆔 Extracted contact_id: '{contact_id}'")
    logger.info(f"🆔 Extracted channel_id: '{channel_id}'")
    
    # Contenido del mensaje
    message_content = message_data.get("message", {})
    message_text = message_content.get("text", "").strip()
    
    logger.info(f"Message content structure: {message_content}")
    logger.info(f"Extracted message_text: '{message_text}'")

    # Validaciones
    if not contact_id:
        logger.warning("Missing contact_id in webhook event")
        logger.warning(f"Contact dict was: {contact}")
        return
    
    if not message_text:
        logger.warning(f"Empty message text for contact {contact_id}")
        logger.warning(f"Message data was: {message_data}")
        logger.warning(f"Message content was: {message_content}")
        return
    
    logger.info(f"Validation passed - processing message from contact {contact_id}: '{message_text[:50]}...'")
    
    # Procesar mensaje usando lógica interna
    response_text = await process_message_internal(
        contact_id=contact_id,
        message_text=message_text,
        contact_name=contact.get("firstName"),
        contact_phone=contact.get("phone")
    )
    
    # Enviar respuesta vía API de Respond.io
    logger.info(f"Sending response to contact {contact_id}")
    logger.info(f"Response text: {response_text}")
    logger.info(f"Using channel_id: {channel_id}")

    success = await respondio_client.send_message(
        contact_id=contact_id,
        message_text=response_text,
        channel_id=channel_id
    )
    
    if success:
        logger.info(f"Response sent successfully to contact {contact_id}")
    else:
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
    """
    logger.info(f"Processing message internally for contact {contact_id}")
    
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
    
    logger.info(f"Response ready for contact {contact_id}")
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
    