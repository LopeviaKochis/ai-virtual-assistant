# Servicio para iniciar el flujo RAG, envía un esquema de payload a OpenAI para generar la respuesta al usuario
import json
from clients.openai_client import openai_client

def build_personalized_answer(user_msg: str, df, user_name: str = None, reason=None) -> str:
    """
    Genera una respuesta personalizada a partir de los datos de Azure Search.
    
    Args:
        user_msg (str): Mensaje del usuario.
        df (pd.DataFrame): Resultados de Azure Search para el DNI del usuario.
        user_name (str, optional): Nombre del usuario, para personalizar el saludo.
        
    Returns:
        str: Respuesta textual segura para el usuario.
    """
    if df.empty:
        return "No encontré información para tu DNI."

    payload = df.to_dict(orient="records")

    if not openai_client:
        r = payload[0]
        if reason == "total_debt":
            return f"{r['Firstname']}: Tu deuda total es de S/ {r['TotalDebt']}."
        elif reason == "due_date":
            return f"{r['Firstname']}: Tu deuda vence el {r['actual_agreement_due_date']}."
        else:
            return f"{r['Firstname']}: Estado {r['Status']}, Total S/ {r['TotalDebt']}."
    
    system_msg = (
        "Eres un asistente financiero amable. Usa SOLO los datos proporcionados para responder.\n"
        "Si la pregunta es sobre monto total de deuda, responde con el monto y un mensaje claro.\n"
        "Si es sobre fecha de vencimiento, responde con la fecha y un mensaje claro.\n"
        "No inventes datos."
    )
    user = f"Pregunta: {user_msg}\nDatos: {json.dumps(payload, ensure_ascii=False)}\nTipo de consulta: {reason}"

    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user}
        ]
    )
    try:
        return resp.choices[0].message.content.strip()
    except Exception:
        # Fallback seguro si falla OpenAI
        r = payload[0]
        return (
            f"{name}: Estado {r.get('Estado','Desconocido')}, "
            f"vence {r.get('Vencimiento','-')}, total S/ {r.get('TotalDeuda','-')}."
        )
