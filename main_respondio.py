import uvicorn
from utils.logging import setup_logging
from config.settings import settings
from webhook.listener import app

setup_logging()

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.WEBHOOK_HOST,
        port=settings.WEBHOOK_PORT,
        log_level="info"
    )
