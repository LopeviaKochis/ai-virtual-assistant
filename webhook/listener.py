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
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature")
):
    """
    Endpoint que recibe eventos de Respond.io.
    Valida firma HMAC y encola para procesamiento asíncrono.
    """
    # 1. Leer raw body (necesario para validación)
    raw_body = await request.body()
    
    # Log detallado para debugging
    logger.info("=" * 60)
    logger.info("NUEVO EVENTO RECIBIDO")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Raw body length: {len(raw_body)}")
    logger.info(f"Raw body preview: {raw_body[:200]}")
    logger.info(f"Signature header: {x_webhook_signature}")
    logger.info("=" * 60)
    
    # 2. Validar firma HMAC
    if not validate_webhook_signature(raw_body, x_webhook_signature):
        logger.warning("Invalid webhook signature received")
        logger.warning(f"Body hash preview: {raw_body[:100]}")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    logger.info("Signature validated successfully")
    
    # 3. Parsear JSON
    payload = None
    try:
        payload = json.loads(raw_body)
        logger.info(f"Event type: {payload.get('event_type') or payload.get('event')}")
        
        # Respond.io puede usar 'event' o 'event_type'
        event_field = payload.get('event') or payload.get('event_type')
        if not event_field:
            logger.error("No event type found in payload")
            raise HTTPException(status_code=400, detail="Missing event type")
        
        # Normalizar el formato
        if 'event' not in payload and 'event_type' in payload:
            payload['event'] = payload['event_type']
        
        event = WebhookEvent(**payload)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        if payload:
            logger.error(f"Payload was: {json.dumps(payload, indent=2)}")
        raise HTTPException(status_code=400, detail="Invalid payload format")
    
    # 4. Encolar evento para procesamiento asíncrono
    try:
        enqueue_event(event.model_dump())
        event_id = payload.get('event_id') or payload.get('data', {}).get('message', {}).get('id', 'unknown')
        logger.info(f"Event {event.event} enqueued successfully (id: {event_id})")
    except Exception as e:
        logger.error(f"Failed to enqueue event: {e}")
        # Aún así devolvemos 200 para evitar reintentos innecesarios
    
    # 5. Responder 200 OK inmediatamente (< 5 segundos)
    return JSONResponse(
        status_code=200,
        content={"status": "received", "event": event.event}
    )

@app.get("/health")
async def health_check():
    """Health check para monitoreo"""
    return {"status": "healthy"}

@app.get("/webhook-test")
async def webhook_test():
    """Endpoint de prueba sin validación de firma"""
    return {
        "status": "ok",
        "message": "Webhook endpoint is reachable",
        "secret_configured": bool(settings.RESPONDIO_WEBHOOK_SECRET)
    }

# Importar settings para el test endpoint
from config.settings import settings