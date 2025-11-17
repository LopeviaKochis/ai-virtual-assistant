import logging
from typing import Dict, Any, Optional

from services.router_service import route_message
from services.rag_service import build_personalized_answer
from clients.azure_client import search_debt_by_dni, search_otp_by_phone
from clients.respondio_client import respondio_client
from utils.parsing import capture_name
from utils.regex_utils import DNI_RE, PHONE_RE
import re

logger = logging.getLogger(__name__)

# Almacenamiento temporal de sesiones (en producción usar Redis)
_sessions: Dict[str, Dict[str, Any]] = {}

async def process_message_received(event_data: Dict[str, Any]) -> None:
    """
    Procesa un evento message.received de Respond.io.
    
    Args:
        event_data: Datos completos del evento webhook
    """
    data = event_data.get("data", {})
    contact = data.get("contact", {})
    message = data.get("message", {})
    conversation = data.get("conversation", {})
    
    contact_id = contact.get("id")
    message_text = message.get("text", "").strip()
    conversation_id = conversation.get("id")
    
    if not contact_id or not message_text:
        logger.warning("Missing contact_id or message_text")
        return
    
    # Obtener o crear sesión
    session = _sessions.get(contact_id, {})
    
    # Capturar nombre si está disponible
    if "name" not in session:
        if name := (contact.get("first_name") or capture_name(message_text)):
            session["name"] = name
    
    # Extraer DNI/teléfono del mensaje
    if dni_match := DNI_RE.search(message_text):
        session["dni"] = dni_match.group(0)
    
    phone_raw = contact.get("phone", "")
    if phone_raw:
        # Normalizar teléfono (últimos 9 dígitos)
        digits = re.sub(r"\D", "", phone_raw)
        if len(digits) >= 9:
            session["phone"] = digits[-9:]
    
    # Enrutar mensaje
    route = route_message(message_text)
    intent = route.get("intent", "general")
    requires_identity = route.get("requires_identity", False)
    
    response_text = ""
    
    if intent == "general" or not requires_identity:
        response_text = route.get("concise_answer", "¿En qué puedo ayudarte?")
    
    elif intent == "debt":
        if dni := session.get("dni"):
            df = search_debt_by_dni(dni)
            if df.empty:
                response_text = f"No encontré información para el DNI {dni}."
            else:
                response_text = build_personalized_answer(
                    message_text,
                    df,
                    session.get("name"),
                    route.get("reason"),
                    intent="debt"
                )
        else:
            response_text = route.get("followup_question", "Por favor proporciona tu DNI (8 dígitos).")
    
    elif intent == "otp":
        if phone := session.get("phone"):
            df = search_otp_by_phone(phone)
            if df.empty:
                response_text = f"No encontré una clave OTP para el número {phone}."
            else:
                response_text = build_personalized_answer(
                    message_text,
                    df,
                    session.get("name"),
                    route.get("reason"),
                    intent="otp",
                    phone=phone
                )
        else:
            response_text = route.get("followup_question", "Por favor proporciona tu número de celular (9 dígitos).")
    
    # Personalizar con nombre si está disponible
    if name := session.get("name"):
        if not response_text.startswith(name):
            response_text = f"{name}, {response_text}"
    
    # Enviar respuesta
    success = await respondio_client.send_message(
        contact_id=contact_id,
        message_text=response_text,
        conversation_id=conversation_id
    )
    
    if success:
        _sessions[contact_id] = session
    else:
        logger.error(f"Failed to send response to contact {contact_id}")