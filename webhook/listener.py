from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import json
import logging
from typing import Optional

from webhook.validator import validate_webhook_signature
from webhook.schemas import WebhookEvent
from clients.queue_client import enqueue_event

logger = logging.getLogger(__name__)

app = FastAPI(title="Respond.io Webhook Listener")

@app.post("/webhook")
async def webhook_handler(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Endpoint que recibe eventos de Respond.io.
    Valida firma HMAC y encola para procesamiento asíncrono.
    """
    # 1. Leer raw body (necesario para validación)
    raw_body = await request.body()
    
    # 2. Validar firma HMAC
    if not validate_webhook_signature(raw_body, x_webhook_signature):
        logger.warning("Invalid webhook signature received")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # 3. Parsear JSON
    try:
        payload = json.loads(raw_body)
        event = WebhookEvent(**payload)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    
    # 4. Encolar evento para procesamiento asíncrono
    try:
        enqueue_event(event.model_dump())
        logger.info(f"Event {event.event} enqueued successfully (id: {payload.get('data', {}).get('message', {}).get('id', 'unknown')})")
    except Exception as e:
        logger.error(f"Failed to enqueue event: {e}")
        # Aún así devolvemos 200 para evitar reintentos innecesarios
    
    # 5. Responder 200 OK inmediatamente (< 5 segundos)
    return JSONResponse(
        status_code=200,
        content={"status": "received"}
    )

@app.get("/health")
async def health_check():
    """Health check para monitoreo"""
    return {"status": "healthy"}