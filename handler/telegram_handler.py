# Manejo de lógica de Telegram y asistente (controller)
from telegram import Update
from telegram.ext import ContextTypes
from services.router_service import route_message
from services.rag_service import build_personalized_answer
from clients.azure_client import azure_search
from utils.parsing import capture_name, DNI_RE

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (update.message.text or "").strip()
    chat = context.user_data

    # Capturar nombre para personalizar, pero sin condicionar flujo
    if "name" not in chat:
        if name := capture_name(msg):
            chat["name"] = name

    # Obtener DNI si ya está guardado
    dni = chat.get("dni")

    # Si no tenemos DNI, validamos y pedimos
    if not dni:
        if DNI_RE.match(msg):
            chat["dni"] = msg
            await update.message.reply_text(
                f"¡Genial{', ' + chat.get('name') if 'name' in chat else ''}! Ya puedo consultar tu deuda con tu DNI."
            )
        else:
            # Pedir DNI de forma amable
            await update.message.reply_text(
                "¡Hola! Para poder ayudarte, por favor ingresa tu DNI (8 dígitos)."
            )
        return

    # Ya tenemos DNI, enrutamos el mensaje
    route = route_message(msg)

    # Si la intención no requiere identidad, respondemos directo
    if not route.get("requires_identity", False):
        concise = route.get("concise_answer") or "¿En qué más puedo ayudarte?"
        await update.message.reply_text(concise)
        return

    # Si la intención requiere identidad, hacemos la consulta con DNI
    df = azure_search("DocNum", dni)

    if df.empty:
        await update.message.reply_text(
            f"No encontré información para el DNI {dni}. ¿Podrías verificarlo, por favor?"
        )
        return

    # Construimos la respuesta personalizada pasando el 'reason' para mejor contexto
    reason = route.get("reason", None)
    answer = build_personalized_answer(msg, df, chat.get("name"), reason)

    await update.message.reply_text(answer)
