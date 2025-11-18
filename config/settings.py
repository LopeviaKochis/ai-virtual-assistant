import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()  # Carga variables de entorno y secretos automáticamente desde .env


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'  # Esto corrige el error de "Extra inputs are not permitted"
    )
    
    # Azure (Campos requeridos sin valor por defecto)
    AZURE_ENDPOINT: str
    AZURE_QUERYKEY: str
    
    # Azure (Campos opcionales con = None)
    AZURE_INDEX: Optional[str] = None
    AZURE_INDEX_DEUDA: Optional[str] = None
    AZURE_INDEX_OTP: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None

    # Telegram
    TELEGRAM_TOKEN: Optional[str] = None
    
    # Respond.io (Campos requeridos sin valor por defecto)
    RESPONDIO_WEBHOOK_SECRET: str
    RESPONDIO_API_TOKEN: str
    RESPONDIO_WORKSPACE_ID: str
    
    # Respond.io (Campos opcionales con valor por defecto)
    RESPONDIO_API_URL: str = "https://api.respond.io/v2"
    RESPONDIO_CHANNEL_ID: Optional[str] = None
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_QUEUE_NAME: str = "respondio:events"
    
    # Servidor
    WEBHOOK_HOST: str = "0.0.0.0"
    WEBHOOK_PORT: int = 8000

settings = Settings()
