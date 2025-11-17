# Inicia la aplicación
from utils.logging import setup_logging
from clients.telegram_client import build_application
from handler.telegram_handler import message_handler
from telegram.ext import MessageHandler, filters
from config.settings import settings

def main():
    setup_logging()

    if not settings.TELEGRAM_TOKEN:
        raise RuntimeError("Falta TELEGRAM_TOKEN")

    app = build_application()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    app.run_polling() # Long polling para recibir actualizaciones de mensajes de Telegram

if __name__ == "__main__":
    main()
