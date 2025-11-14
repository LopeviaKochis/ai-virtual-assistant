# Cliente de OpenAI para usar sus servicios
from openai import OpenAI
from config.settings import settings

def get_openai_client():
    if not settings.OPENAI_API_KEY:
        return None
    return OpenAI(api_key=settings.OPENAI_API_KEY)

openai_client = get_openai_client()
