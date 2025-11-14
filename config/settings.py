import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()  # Carga variables de entorno y secretos automáticamente desde .env


class Settings(BaseModel):
    TELEGRAM_TOKEN: str = Field(..., min_length=10)
    AZURE_ENDPOINT: str
    AZURE_QUERYKEY: str
    OPENAI_API_KEY: str
    AZURE_INDEX_DEUDA: Optional[str] = None  # Índice dedicado para las consultas de deuda.
    AZURE_INDEX_OTP: Optional[str] = None    # Índice dedicado para la recuperación de claves OTP.
    AZURE_INDEX: Optional[str] = None        # Compatibilidad hacia atrás con una sola configuración.
    APP_ENV: str = "production"  # default si no está definido

    class Config:
        extra = "ignore"  # Ignora claves desconocidas


def load_settings():
    try:
        return Settings(
            TELEGRAM_TOKEN=os.getenv("TELEGRAM_TOKEN"),
            AZURE_ENDPOINT=os.getenv("AZURE_ENDPOINT"),
            AZURE_QUERYKEY=os.getenv("AZURE_QUERYKEY"),
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
            AZURE_INDEX_DEUDA=os.getenv("AZURE_INDEX_DEUDA") or os.getenv("AZURE_INDEX"),
            AZURE_INDEX_OTP=os.getenv("AZURE_INDEX_OTP"),
            AZURE_INDEX=os.getenv("AZURE_INDEX"),
            APP_ENV=os.getenv("APP_ENV", "production")
        )
    except ValidationError as e:
        raise RuntimeError(f"Error cargando configuración: {e}")


settings = load_settings()
