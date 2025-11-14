# Creacion de enrutador para 
import json
import logging
from clients.openai_client import openai_client

def route_message(user_msg: str) -> dict:
    if not openai_client:
        # fallback sencillo para soluciones rápidas
        low = user_msg.lower()
        needs_id = any(x in low for x in ["deuda", "saldo", "prestamo"])
        return {
            "requires_identity": needs_id,
            "concise_answer": "" if needs_id else "¿En qué puedo ayudarte?",
            "followup_question": "¿Me compartes tu DNI, teléfono o email?",
            "reason": "heuristic"
        }

    system_msg = (
        "Eres un asistente financiero. Responde SOLO en JSON con los campos: "
        "{requires_identity, reason, concise_answer, followup_question}."
    )

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]
    )

    try:
        data = json.loads(resp.choices[0].message.content)
        return data
    except Exception:
        logging.exception("Error parseando JSON")
        return {
            "requires_identity": True,
            "concise_answer": "",
            "followup_question": "¿Me das tu DNI o teléfono?",
            "reason": "fallback"
        }
