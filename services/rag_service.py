# Servicio para iniciar el flujo RAG, envía un esquema de payload a OpenAI para generar la respuesta al usuario
import json
from typing import Optional, Dict, Any
from clients.openai_client import openai_client

def build_personalized_answer(
    user_msg: str,
    df,
    session: Dict[str, Any],  # Cambiar de user_name a session completa
    reason: str | None = None,
    intent: str = "debt",
    phone: str | None = None
) -> str:
    """
    Genera respuesta usando nombre original para búsqueda, preferido para saludo.
    
    Args:
        session: Sesión completa (contiene name y preferred_name)
    """
    if df.empty:
        display_name = session.get("preferred_name") or session.get("name") or "Cliente"
        if intent == "otp":
            return f"{display_name}, no encontré una clave OTP activa. ¿Podemos revisar el número?"
        return f"{display_name}, no encontré información para tu DNI."
    
    # Para OTP: usar nombre preferido
    if intent == "otp":
        record = df.iloc[0]
        code = record.get("Codigo")
        if not code:
            return "No pude recuperar la clave OTP en este momento."
        
        digits = "".join(filter(str.isdigit, str(record.get("Recepient") or ""))) or phone or ""
        display_name = session.get("preferred_name") or session.get("name") or "Listo"
        suffix = f" asociada al número que termina en {digits[-4:]}" if digits else ""
        
        return f"{display_name}, tu clave OTP{suffix} es **{code}**. ¿Necesitas algo más?"
    
    # Para DEBT: usar nombre original (del perfil) para búsqueda en AI Search
    # pero nombre preferido para saludo
    payload = df.to_dict(orient="records")
    record = payload[0]
    
    search_name = session.get("name") or record.get("Firstname") or "Cliente"  # Para prompt de OpenAI
    display_name = session.get("preferred_name") or search_name  # Para saludo

    if not openai_client:
        total = record.get("TotalDeuda") or record.get("TotalDebt")
        due_date = record.get("Vencimiento") or record.get("actual_agreement_due_date")
        status = record.get("Estado") or record.get("Status")
        if reason in {"total_debt", "heuristic_debt"} and total is not None:
            return f"{display_name}: tu deuda total es S/ {total}."
        if reason in {"due_date", "heuristic_due_date"} and due_date:
            return f"{display_name}: tu deuda vence el {due_date}."
        return f"{display_name}: estado {status or 'desconocido'}, total pendiente S/ {total or '--'}."

    system_msg = (
        "Eres un asistente financiero amable. Usa SOLO los datos proporcionados para responder.\n"
        "Si la pregunta es sobre monto total de deuda, responde con el monto y un mensaje claro.\n"
        "Si es sobre fecha de vencimiento, responde con la fecha y un mensaje claro.\n"
        "No inventes datos."
    )
    user = (
        f"Pregunta: {user_msg}\n"
        f"Datos: {json.dumps(payload, ensure_ascii=False)}\n"
        f"Tipo de consulta: {reason}"
    )

    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user}
            ]
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        total = record.get("TotalDeuda") or record.get("TotalDebt")
        due_date = record.get("Vencimiento") or record.get("actual_agreement_due_date")
        status = record.get("Estado") or record.get("Status") or "desconocido"
        pieces = [f"{display_name}: estado {status}"]
        if due_date:
            pieces.append(f"vence el {due_date}")
        if total:
            pieces.append(f"total S/ {total}")
        return ", ".join(pieces) + "."
