# Enrutador para iniciar la interacción con el cliente de OpenAI
import json
import logging
from clients.openai_client import openai_client

OTP_KEYWORDS = ("clave", "otp", "código", "codigo", "no me llegó", "no me llego")
DEBT_KEYWORDS = ("deuda", "saldo", "prestamo", "préstamo", "cuánto debo")
DUE_DATE_KEYWORDS = ("vence", "fecha de vencimiento", "cuando vence")


def route_message(user_msg: str) -> dict:
    if not openai_client:
        # fallback heurístico básico
        low = user_msg.lower()
        if any(keyword in low for keyword in OTP_KEYWORDS):
            return {
                "intent": "otp",
                "requires_identity": True,
                "concise_answer": "",
                "followup_question": "Para validar tu clave OTP necesito tu número de celular (9 dígitos que empiecen en 9).",
                "reason": "heuristic_otp"
            }
        if any(keyword in low for keyword in DEBT_KEYWORDS):
            return {
                "intent": "debt",
                "requires_identity": True,
                "concise_answer": "",
                "followup_question": "Para ayudarte, necesito tu DNI (8 dígitos), por favor.",
                "reason": "heuristic_debt"
            }
        if any(keyword in low for keyword in DUE_DATE_KEYWORDS):
            return {
                "intent": "debt",
                "requires_identity": True,
                "concise_answer": "",
                "followup_question": "Para verificar fechas, por favor ingresa tu DNI (8 dígitos).",
                "reason": "heuristic_due_date"
            }
        # Default fallback
        return {
            "intent": "general",
            "requires_identity": False,
            "concise_answer": "Hola, ¿en qué puedo ayudarte hoy?",
            "followup_question": "",
            "reason": "heuristic_default"
        }

    system_msg = (
        "Eres un asistente financiero amable y claro. "
        "Responde SOLO en JSON con estas claves:\n"
        ' - intent: "debt", "otp" o "general".\n'
        " - requires_identity: booleano, si necesitas un dato adicional (DNI o teléfono).\n"
        " - reason: texto corto explicando el motivo de la decisión.\n"
        " - concise_answer: respuesta breve para consultas sin identidad.\n"
        " - followup_question: pregunta para pedir el dato faltante.\n\n"
        "Identifica especialmente:\n"
        "1) Consultas sobre monto o estado de deuda (intención debt, requiere DNI).\n"
        "2) Consultas sobre la clave OTP o cuando no llega un código (intención otp, requiere teléfono móvil).\n"
        "3) Otras consultas generales que no necesitan datos.\n\n"
        "Ejemplo deuda:\n"
        '{"intent": "debt", "requires_identity": true, "reason": "total_debt", "concise_answer": "", "followup_question": "Para ayudarte, por favor ingresa tu DNI (8 dígitos)."}\n'
        "Ejemplo OTP:\n"
        '{"intent": "otp", "requires_identity": true, "reason": "otp_lookup", "concise_answer": "", "followup_question": "¿Cuál es tu número de celular (9 dígitos)?."}\n'
        "Responde solo JSON, sin texto adicional."
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
        for key in ["intent", "requires_identity", "reason", "concise_answer", "followup_question"]:
            if key not in data:
                raise ValueError(f"Missing key {key}")
        return data
    except Exception:
        logging.exception("Error parsing JSON from route_message")
        # fallback seguro
        return {
            "intent": "debt",
            "requires_identity": True,
            "concise_answer": "",
            "followup_question": "Para continuar, por favor ingresa tu DNI (8 dígitos).",
            "reason": "fallback"
        }
