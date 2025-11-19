import uvicorn
from fastapi import FastAPI
from utils.logging import setup_logging
from config.settings import settings

# Importar sub-aplicaciones
from webhook.listener import app as webhook_app
from api.rag_endpoint import app as rag_app

setup_logging()

# Crear aplicación principal
app = FastAPI(
    title="RAG - Respond.io Integration Server",
    version="1.0.0",
    description="Servidor unificado para integrar un sistema RAG con canales de comunicación de Respond.io y workflows."
)

# Montar sub-aplicaciones
app.mount("/webhook", webhook_app)
app.mount("/api", rag_app)

@app.get("/")
async def root():
    """Endpoint raíz con información del servicio"""
    return {
        "service": "Respond.io Integration Server",
        "version": "1.0.0",
        "endpoints": {
            "webhook": {
                "base": "/webhook",
                "test": "/webhook/health"
            },
            "rag_api": {
                "base": "/api",
                "process": "/api/process-message",
                "health": "/api/health"
            }
        },
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check global del servidor"""
    return {
        "status": "healthy",
        "webhook": "active",
        "rag_api": "active"
    }

if __name__ == "__main__":
    print("=" * 60)
    print("RESPOND.IO INTEGRATION SERVER")
    print("=" * 60)
    print(f"Host: {settings.WEBHOOK_HOST}")
    print(f"Port: {settings.WEBHOOK_PORT}")
    print("")
    print("Endpoints disponibles:")
    print(f"  • Webhook: http://localhost:{settings.WEBHOOK_PORT}/webhook")
    print(f"  • RAG API: http://localhost:{settings.WEBHOOK_PORT}/api/process-message")
    print(f"  • Health:  http://localhost:{settings.WEBHOOK_PORT}/health")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host=settings.WEBHOOK_HOST,
        port=settings.WEBHOOK_PORT,
        log_level="info"
    )