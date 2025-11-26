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
    SOPORTA: Telegram y WhatsApp (enrutamiento dinámico por channel_id).
    
    Args:
        event_data: Datos completos del evento webhook
    """
    import json

    logger.info("="*60)
    logger.info("PROCESANDO EVENTO EN MESSAGE_PROCESSOR")
    logger.info(f"Event data keys: {list(event_data.keys())}")
    logger.info("="*60)

    # Extraer datos del payload
    contact = event_data.get("contact", {})
    message_data = event_data.get("message", {})
    channel_data = event_data.get("channel", {})
    
    # NUEVO: Capturar channel_id explícitamente
    incoming_channel_id = str(channel_data.get("id", ""))
    channel_source = channel_data.get("source", "unknown")  # "telegram" o "whatsapp"
    
    # IDs
    contact_id = str(contact.get("id", ""))
    
    # NUEVO: Validar tipo de mensaje (solo texto por ahora)
    message_content = message_data.get("message", {})
    message_type = message_content.get("type", "text")
    
    if message_type != "text":
        logger.warning(f"Unsupported message type: {message_type} from {channel_source}")
        # Responder amablemente
        await respondio_client.send_message(
            contact_id=contact_id,
            message_text="Por el momento solo puedo procesar mensajes de texto. Por favor escribe tu consulta.",
            channel_id=incoming_channel_id
        )
        return
    
    message_text = message_content.get("text", "").strip()
    
    logger.info(f"Contact ID: {contact_id}")
    logger.info(f"Channel ID: {incoming_channel_id}")
    logger.info(f"Channel Source: {channel_source}")
    logger.info(f"Message text: '{message_text}'")

    # Validaciones
    if not contact_id:
        logger.warning("Missing contact_id in webhook event")
        return
    
    if not message_text:
        logger.warning(f"Empty message text for contact {contact_id}")
        return
    
    if not incoming_channel_id:
        logger.error(f"Missing channel_id for contact {contact_id}")
        return
    
    logger.info(f"✓ Validation passed - processing message from {channel_source}")
    
    # NUEVO: Normalizar teléfono según el canal
    contact_phone = contact.get("phone")
    if channel_source == "whatsapp" and contact_phone:
        # WhatsApp envía: "+51987654321"
        # Necesitamos: "987654321" (9 dígitos)
        from services.extraction_service import normalize_phone_from_contact
        contact_phone = normalize_phone_from_contact(contact_phone)
        logger.info(f"Normalized WhatsApp phone: {contact_phone}")
    
    # Procesar mensaje usando lógica interna
    response_text = await process_message_internal(
        contact_id=contact_id,
        message_text=message_text,
        contact_name=contact.get("firstName"),
        contact_phone=contact_phone,
        channel_source=channel_source  # NUEVO: Pasar origen del canal
    )
    
    # IMPORTANTE: Enviar respuesta por el MISMO canal por donde vino el mensaje
    logger.info(f"Sending response to {contact_id} via channel {incoming_channel_id} ({channel_source})")
    logger.info(f"Response: {response_text[:100]}...")

    success = await respondio_client.send_message(
        contact_id=contact_id,
        message_text=response_text,
        channel_id=incoming_channel_id  # USAR EL CANAL DE ORIGEN
    )
    
    if success:
        logger.info(f"✓ Response sent successfully via {channel_source}")
    else:
        logger.error(f"✗ Failed to send response via {channel_source}")

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
    contact_phone: Optional[str] = None,
    channel_source: str = "unknown"
) -> str:
    """Procesa mensaje con gestión de identidad mejorada."""
    
    logger.info(f"Processing message internally for {contact_id} via {channel_source}")
    
    # 1. Obtener y enriquecer sesión
    session = get_session(contact_id)
    session["last_channel"] = channel_source
    
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
    
    # 4. Personalizar con nombre preferido
    response_text = format_response_with_name(session, response_text)  # Ahora pasa sesión completa
    
    # 5. Guardar sesión actualizada
    save_session(contact_id, session)
    
    logger.info(f"Response ready for {contact_id} via {channel_source}")
    return response_text

async def _process_debt_intent(
    contact_id: str,
    session: Dict[str, Any],
    message_text: str,
    route: Dict[str, Any],
    reason: Optional[str]
) -> str:
    """Procesa deuda con fallback graceful."""
    
    dni = session.get("dni")
    
    if not dni:
        set_pending_intent(contact_id, "debt", reason, message_text)
        return route.get("followup_question", "Para consultar tu deuda, necesito tu DNI (8 dígitos).")
    
    logger.info(f"Searching debt for DNI: {dni}")
    
    try:
        df = search_debt_by_dni(dni)
        
        if df.empty:
            clear_pending_intent(contact_id)
            return f"No encontré información para el DNI {dni}. Por favor verifica que sea correcto."
        
        clear_pending_intent(contact_id)
        return build_personalized_answer(
            message_text,
            df,
            session,
            reason,
            intent="debt"
        )
    
    except Exception as e:
        logger.exception(f"Error processing debt intent: {e}")
        clear_pending_intent(contact_id)
        # P1-2: Respuesta de fallback en lugar de error genérico
        display_name = session.get("preferred_name") or session.get("name") or "Disculpa"
        return (
            f"{display_name}, estoy teniendo problemas para acceder a los datos de deuda en este momento. "
            f"Tu consulta ha sido registrada. ¿Puedes intentar nuevamente en unos minutos?"
        )


async def _process_otp_intent(
    contact_id: str,
    session: Dict[str, Any],
    message_text: str,
    route: Dict[str, Any],
    reason: Optional[str]
) -> str:
    """Procesa OTP con fallback graceful."""
    
    phone = session.get("phone")
    
    if not phone:
        set_pending_intent(contact_id, "otp", reason, message_text)
        return route.get("followup_question", "Para encontrar tu clave OTP, necesito tu número de celular (9 dígitos).")
    
    logger.info(f"Searching OTP for phone: {phone}")
    
    try:
        df = search_otp_by_phone(phone)
        
        if df.empty:
            clear_pending_intent(contact_id)
            return (
                f"No encontré una clave OTP activa para el número que termina en {phone[-4:]}. "
                f"¿Es correcto este número?"
            )
        
        clear_pending_intent(contact_id)
        return build_personalized_answer(
            message_text,
            df,
            session,
            reason,
            intent="otp",
            phone=phone
        )
    
    except Exception as e:
        logger.exception(f"Error processing OTP intent: {e}")
        clear_pending_intent(contact_id)
        # P1-2: Respuesta de fallback
        display_name = session.get("preferred_name") or session.get("name") or "Disculpa"
        return (
            f"{display_name}, estoy teniendo problemas para recuperar tu clave OTP en este momento. "
            f"Por favor intenta nuevamente en unos minutos."
        )
       