# Manejo de lógica de Telegram y asistente (controller)
import re
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from services.router_service import route_message
from services.rag_service import build_personalized_answer
from clients.azure_client import search_debt_by_dni, search_otp_by_phone
from utils.parsing import capture_name
from utils.regex_utils import DNI_RE, PHONE_RE

def _clear_pending(chat: dict) -> None:
    """Limpia la intención pendiente sin perder identificadores ya capturados."""
    for key in ("pending_intent", "pending_reason", "pending_user_msg"):
        chat.pop(key, None)


def _prepare_pending(chat: dict, intent: str, reason: Optional[str], user_msg: str) -> None:
    """Registra la intención y la pregunta original mientras esperamos más datos."""
    _clear_pending(chat)
    chat["pending_intent"] = intent
    chat["pending_reason"] = reason
    chat["pending_user_msg"] = user_msg


def _with_name(name: Optional[str], text: str) -> str:
    """Añade el nombre al mensaje si lo tenemos, manteniendo un tono natural."""
    if not name:
        return text
    return f"{name}, {text.lstrip()}"


def _extract_dni(text: str) -> Optional[str]:
    """Localiza un DNI en el mensaje respetando el patrón de 8 dígitos."""
    if match := DNI_RE.search(text):
        return match.group(0)
    return None


def _extract_phone(text: str) -> Optional[str]:
    """Normaliza el número móvil guardando los últimos 9 dígitos que empiezan en 9."""
    compact = re.sub(r"\s+", "", text)
    if match := PHONE_RE.search(compact):
        digits = re.sub(r"\D", "", match.group(0))
        normalized = digits[-9:]
        if len(normalized) == 9 and normalized.startswith("9"):
            return normalized
    return None


def _only_digits(text: str) -> str:
    """Extrae únicamente los dígitos para validar respuestas parciales del usuario."""
    return re.sub(r"\D", "", text)


async def _respond_with_debt(message, chat: dict, user_msg: str, reason: Optional[str]) -> None:
    """Consulta Azure para deuda y responde de forma personalizada."""
    df = search_debt_by_dni(chat["dni"])
    if df.empty:
        await message.reply_text(
            _with_name(chat.get("name"), f"No encontré información para el DNI {chat['dni']}. ¿Podrías revisarlo?")
        )
        _clear_pending(chat)
        return

    answer = build_personalized_answer(
        user_msg,
        df,
        chat.get("name"),
        reason,
        intent="debt"
    )
    await message.reply_text(answer)
    _clear_pending(chat)


async def _respond_with_otp(message, chat: dict, user_msg: str, reason: Optional[str]) -> None:
    """Consulta Azure para OTP y devuelve únicamente la clave necesaria."""
    phone = chat.get("phone")
    if not phone:
        await message.reply_text(
            _with_name(chat.get("name"), "Por favor proporciona tu número de celular para buscar la clave OTP.")
        )
        _clear_pending(chat)
        return

    df = search_otp_by_phone(phone)
    if df.empty:
        await message.reply_text(
            _with_name(chat.get("name"), "No encontré una clave OTP activa para ese número. ¿Lo verificamos?")
        )
        _clear_pending(chat)
        return

    answer = build_personalized_answer(
        user_msg,
        df,
        chat.get("name"),
        reason,
        intent="otp",
        phone=phone
    )
    await message.reply_text(answer)
    _clear_pending(chat)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not (message.text or "").strip():
        return  # Ignoramos mensajes vacíos o no textuales.

    msg = message.text.strip()
    chat = context.user_data

    # Capturamos el nombre una sola vez para personalizar respuestas amables.
    if "name" not in chat:
        if name := capture_name(msg):
            chat["name"] = name

    # Actualizamos identificadores cada vez que el usuario los comparta.
    if dni := _extract_dni(msg):
        chat["dni"] = dni
    if phone := _extract_phone(msg):
        chat["phone"] = phone

    # Si ya teníamos la intención pendiente y conseguimos el dato, respondemos de inmediato.
    if chat.get("pending_intent") == "debt" and chat.get("pending_user_msg") and chat.get("dni"):
        await _respond_with_debt(message, chat, chat["pending_user_msg"], chat.get("pending_reason"))
        return
    if chat.get("pending_intent") == "otp" and chat.get("pending_user_msg") and chat.get("phone"):
        await _respond_with_otp(message, chat, chat["pending_user_msg"], chat.get("pending_reason"))
        return

    # Validamos respuestas numéricas parciales para seguir guiando al usuario.
    if chat.get("pending_intent") == "debt" and chat.get("pending_user_msg") and not chat.get("dni"):
        if _only_digits(msg):
            await message.reply_text(_with_name(chat.get("name"), "Necesito un DNI válido de 8 dígitos."))
            return
    if chat.get("pending_intent") == "otp" and chat.get("pending_user_msg") and not chat.get("phone"):
        if _only_digits(msg):
            await message.reply_text(
                _with_name(chat.get("name"), "Recuerda que el número debe tener 9 dígitos y empezar en 9.")
            )
            return

    route = route_message(msg)
    intent = route.get("intent", "general")
    reason = route.get("reason")

    # Si el usuario cambió de tema (de deuda a OTP o viceversa), reiniciamos el estado previo.
    if chat.get("pending_intent") and intent in {"debt", "otp"} and chat["pending_intent"] != intent:
        _clear_pending(chat)

    if intent == "general" or not route.get("requires_identity", False):
        concise = route.get("concise_answer") or "Aquí estoy para ayudarte, dime qué necesitas."
        await message.reply_text(_with_name(chat.get("name"), concise))
        return

    if intent == "debt":
        if chat.get("dni"):
            await _respond_with_debt(message, chat, msg, reason)
        else:
            _prepare_pending(chat, "debt", reason, msg)
            followup = route.get("followup_question") or "Para ayudarte necesito tu DNI (8 dígitos)."
            await message.reply_text(_with_name(chat.get("name"), followup))
        return

    if intent == "otp":
        if chat.get("phone"):
            await _respond_with_otp(message, chat, msg, reason)
        else:
            _prepare_pending(chat, "otp", reason, msg)
            followup = route.get("followup_question") or (
                "Para ubicar tu clave OTP necesito tu número de celular (9 dígitos que empiece en 9)."
            )
            await message.reply_text(_with_name(chat.get("name"), followup))
        return
    # Fallback seguro en caso de una intención inesperada.
    fallback = route.get("concise_answer") or "Puedo ayudarte con consultas de deuda u OTP."
    await message.reply_text(_with_name(chat.get("name"), fallback))
