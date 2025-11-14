# Cliente para usar el Bot Father de Telegram
from telegram.ext import ApplicationBuilder
from config.settings import settings

def build_application():
    return ApplicationBuilder().token(settings.TELEGRAM_TOKEN).build()
