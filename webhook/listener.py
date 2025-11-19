from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import json
import logging
from typing import Optional

from webhook.validator import validate_webhook_signature
from webhook.schemas import WebhookEvent
from clients.queue_client import enqueue_event
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhook"])

@router.post("/webhook/conversation-opened")
async def conversation_opened_handler(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Endpoint para evento conversation.opened de Respond.io.
    Usa RESPONDIO_WEBHOOK_CHAT_OPEN_SECRET para validación.
    """
    raw_body = await request.body()
    
    logger.debug("="*20 + " CONVERSATION OPENED EVENT " + "="*20)
    logger.debug(f"RAW BODY: {raw_body.decode('utf-8', errors='replace')}")
    
    # Validar firma con secreto de conversation.opened
    if not validate_webhook_signature(raw_body, x_webhook_signature, webhook_type="conversation"):
        logger.warning("Invalid signature for conversation.opened")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    logger.info("Signature validated for conversation.opened")
    
    try:
        payload = json.loads(raw_body)
        event = WebhookEvent(**payload)
        
        # Encolar para procesamiento
        enqueue_event(event.model_dump())
        logger.info(f"Event {event.event_type} enqueued (id: {event.event_id})")
        
    except Exception as e:
        logger.error(f"Failed to parse conversation.opened payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    
    return JSONResponse(status_code=200, content={"status": "received", "event": event.event_type})

@router.post("/webhook/message-received")
async def message_received_handler(
    request: Request,
    x_webhook_signature: Optional[str] = Header(None)
):
    """
    Endpoint para evento message.received de Respond.io.
    Usa RESPONDIO_WEBHOOK_INCOMING_MESSAGE_SECRET para validación.
    Este es el endpoint PRINCIPAL para mensajes entrantes.
    """
    raw_body = await request.body()
    
    logger.debug("="*20 + " MESSAGE RECEIVED EVENT " + "="*20)
    logger.debug(f"RAW BODY: {raw_body.decode('utf-8', errors='replace')}")
    logger.debug(f"SIGNATURE: {x_webhook_signature}")
    
    # Validar firma con secreto de message.received
    if not validate_webhook_signature(raw_body, x_webhook_signature, webhook_type="message"):
        logger.warning("Invalid signature for message.received")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    logger.info("Signature validated for message.received")
    
    payload = None
    try:
        payload = json.loads(raw_body)
        
        # NUEVO: Log completo del payload para debugging
        logger.info("="*60)
        logger.info("PAYLOAD COMPLETO RECIBIDO:")
        logger.info(json.dumps(payload, indent=2, ensure_ascii=False))
        logger.info("="*60)
        
        # NUEVO: Log de campos específicos
        logger.info(f"event_type: {payload.get('event_type')}")
        logger.info(f"event_id: {payload.get('event_id')}")
        logger.info(f"contact keys: {list(payload.get('contact', {}).keys())}")
        logger.info(f"message keys: {list(payload.get('message', {}).keys())}")
        logger.info(f"channel keys: {list(payload.get('channel', {}).keys())}")

        # Verificar que sea un mensaje entrante (no saliente)
        traffic = payload.get("message", {}).get("traffic")
        if traffic != "incoming":
            logger.info(f"Ignoring outgoing message (traffic={traffic})")
            return JSONResponse(status_code=200, content={"status": "ignored", "reason": "outgoing_message"})
        
        event = WebhookEvent(**payload)

        # NUEVO: Log del objeto parseado
        logger.info(f"WebhookEvent created successfully")
        logger.info(f"   - Contact: {event.get_contact()}")
        logger.info(f"   - Message: {event.get_message()}")
        logger.info(f"   - Channel: {event.get_channel()}")
        
        # Encolar para procesamiento asíncrono
        event_dict = event.model_dump()
        logger.info(f"Enqueuing event: {json.dumps(event_dict, indent=2, default=str)}")
        enqueue_event(event_dict)

        message = event.get_message()
        message_id = message.messageId if message else "unknown"
        logger.info(f"Message {message_id} enqueued for processing")
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        logger.error(f"Raw body was {raw_body.decode('utf-8', errors='replace')[:500]}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.exception(f"Failed to parse message.received payload: {e}")
        logger.error(f"Payload keys: {list(payload.keys()) if payload is not None else 'N/A'}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    
    return JSONResponse(status_code=200, content={"status": "received", "event": "message.received"})

@router.get("/webhook/health")
async def health_check():
    """Health check para monitoreo"""
    return {
        "status": "healthy",
        "endpoints": {
            "conversation_opened": "/webhook/conversation-opened",
            "message_received": "/webhook/message-received"
        },
        "secrets_configured": {
            "conversation": bool(settings.RESPONDIO_WEBHOOK_CHAT_OPEN_SECRET),
            "message": bool(settings.RESPONDIO_WEBHOOK_INCOMING_MESSAGE_SECRET)
        }
    }

@router.get("/webhook-test")
async def webhook_test():
    """Endpoint de prueba sin validación"""
    return {
        "status": "ok",
        "message": "Webhook endpoints are reachable",
        "configuration": {
            "api_token": bool(settings.RESPONDIO_API_TOKEN),
            "workspace_id": settings.RESPONDIO_WORKSPACE_ID,
            "channel_id": settings.RESPONDIO_CHANNEL_ID
        }
    }
