# Enrutador para iniciar la interacción con el cliente de OpenAI
import json
import logging
from clients.openai_client import openai_client

def route_message(user_msg: str) -> dict:
    if not openai_client:
        # fallback heurístico básico
        low = user_msg.lower()
        if any(x in low for x in ["deuda", "saldo", "prestamo", "cuánto debo"]):
            return {
                "requires_identity": True,
                "concise_answer": "",
                "followup_question": "Para ayudarte, necesito tu DNI (8 dígitos), por favor.",
                "reason": "heuristic_debt"
            }
        if any(x in low for x in ["vence", "fecha de vencimiento", "cuando vence"]):
            return {
                "requires_identity": True,
                "concise_answer": "",
                "followup_question": "Para verificar fechas, por favor ingresa tu DNI (8 dígitos).",
                "reason": "heuristic_due_date"
            }
        # Default fallback
        return {
            "requires_identity": False,
            "concise_answer": "Hola, ¿en qué puedo ayudarte hoy?",
            "followup_question": "",
            "reason": "heuristic_default"
        }

    system_msg = (
        "Eres un asistente financiero amable y claro. "
        "Recibes una pregunta del usuario y respondes SOLO en JSON con estas claves:\n"
        " - requires_identity: booleano, si necesitas que el usuario se identifique con DNI.\n"
        " - reason: texto corto explicando la razón de la respuesta.\n"
        " - concise_answer: respuesta breve y clara para preguntas que no requieren identidad.\n"
        " - followup_question: pregunta para pedir DNI u otro dato si se necesita.\n\n"
        "Prioriza identificar estas intenciones:\n"
        "1) Consultas sobre monto total de deuda (requiere DNI).\n"
        "2) Consultas sobre fecha de vencimiento de deuda (requiere DNI).\n"
        "3) Otras consultas generales que no requieren identidad.\n\n"
        "Ejemplo:\n"
        '{"requires_identity": true, "reason": "total_debt", "concise_answer": "", "followup_question": "Para ayudarte, por favor ingresa tu DNI (8 dígitos)."}\n'
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
        # Validar claves
        for key in ["requires_identity", "reason", "concise_answer", "followup_question"]:
            if key not in data:
                raise ValueError(f"Missing key {key}")
        return data
    except Exception:
        logging.exception("Error parsing JSON from route_message")
        # fallback seguro
        return {
            "requires_identity": True,
            "concise_answer": "",
            "followup_question": "Para continuar, por favor ingresa tu DNI (8 dígitos).",
            "reason": "fallback"
        }
