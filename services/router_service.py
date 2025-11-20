import json
import logging
from typing import Dict, Any
from clients.openai_client import openai_client
from models.user_profile import UserProfile

logger = logging.getLogger(__name__)

# Keywords para detección de intención
OTP_KEYWORDS = ("clave", "otp", "código", "codigo", "no me llegó", "no me llego")
DEBT_KEYWORDS = ("deuda", "saldo", "prestamo", "préstamo", "cuánto debo", "cuanto debo")
DUE_DATE_KEYWORDS = ("vence", "fecha de vencimiento", "cuando vence", "cuándo vence")

def route_message(user_msg: str) -> dict:
    """
    Enruta mensaje usando OpenAI o fallback heurístico.
    
    Args:
        user_msg: Mensaje del usuario
        
    Returns:
        Diccionario con intent, requires_identity, reason, etc.
    """
    if not openai_client:
        # Fallback heurístico básico
        low = user_msg.lower()
        needs_id = any(x in low for x in ["deuda", "saldo", "prestamo", "préstamo"])
        return {
            "intent": "debt" if needs_id else "general",
            "requires_identity": needs_id,
            "concise_answer": "" if needs_id else "¿En qué puedo ayudarte?",
            "followup_question": "¿Me compartes tu DNI, teléfono o email?" if needs_id else "",
            "reason": "heuristic"
        }

    system_msg = (
        "Eres un asistente financiero. Responde SOLO en JSON con los campos: "
        "{intent, requires_identity, reason, concise_answer, followup_question}.\n"
        "intent puede ser: 'debt', 'otp', 'general'."
    )

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]
        )

        data = json.loads(resp.choices[0].message.content)
        
        # Validar que tenga campos requeridos
        if "intent" not in data:
            data["intent"] = "general"
        if "requires_identity" not in data:
            data["requires_identity"] = False
        
        return data
    
    except Exception as e:
        logger.exception(f"Error parsing JSON from OpenAI: {e}")
        return {
            "intent": "general",
            "requires_identity": True,
            "concise_answer": "",
            "followup_question": "¿Me das tu DNI o teléfono?",
            "reason": "fallback_error"
        }

def route_message_with_profile(
    user_msg: str, 
    profile: UserProfile,
    session: Dict[str, Any]
) -> dict:
    """
    Enruta mensaje considerando perfil y sesión.
    
    Args:
        user_msg: Mensaje del usuario
        profile: Perfil del usuario desde Cosmos DB
        session: Sesión actual (opcional)
        
    Returns:
        {
            "intent": "debt" | "otp" | "general",
            "requires_identity": bool,
            "has_identity": bool,
            "missing_data": ["dni", "phone"],
            "reason": str,
            "concise_answer": str,
            "followup_question": str
        }
    """
    # Analizar intención
    low = user_msg.lower()
    
    # Determinar qué datos faltan
    missing = []
    if not profile.dni:
        missing.append("dni")
    if not profile.phone:
        missing.append("phone")
    
    # Detectar intención
    if any(kw in low for kw in OTP_KEYWORDS):
        intent = "otp"
        requires_identity = True
        has_identity = bool(profile.phone)
    elif any(kw in low for kw in DEBT_KEYWORDS):
        intent = "debt"
        requires_identity = True
        has_identity = bool(profile.dni)
    else:
        intent = "general"
        requires_identity = False
        has_identity = True
    
    return {
        "intent": intent,
        "requires_identity": requires_identity,
        "has_identity": has_identity,
        "missing_data": missing,
        "reason": f"{intent}_detected",
        "concise_answer": "",
        "followup_question": _generate_followup(intent, missing)
    }

def _generate_followup(intent: str, missing_data: list) -> str:
    """Genera pregunta de seguimiento según datos faltantes."""
    if intent == "otp" and "phone" in missing_data:
        return "Para encontrar tu clave OTP, necesito tu número de celular (9 dígitos que empiece en 9)."
    
    if intent == "debt" and "dni" in missing_data:
        return "Para consultar tu deuda, necesito tu DNI (8 dígitos)."
    
    if missing_data:
        missing_str = " y ".join(missing_data)
        return f"Para ayudarte necesito tu {missing_str}."
    
    return ""
