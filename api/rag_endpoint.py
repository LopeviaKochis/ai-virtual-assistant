from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

from services.message_processor import process_message_for_api
from services.session_service import get_session, clear_session

logger = logging.getLogger(__name__)

app = FastAPI(
    title="RAG API for Respond.io Integration"
    )

# ==========================================
# SCHEMAS
# ==========================================

class MessageRequest(BaseModel):
    """Request que recibe desde Respond.io Workflow"""
    contact_id: str
    message_text: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None

class MessageResponse(BaseModel):
    """Response que se envía de vuelta a Respond.io"""
    response_text: str
    intent: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None

# ==========================================
# ENDPOINT PRINCIPAL
# ==========================================

@app.post("/process-message", 
          response_model=MessageResponse, 
          tags=["RAG Message Processing"]
          )
async def process_message_endpoint(request: MessageRequest):
    """
    Endpoint principal que procesa mensajes desde Respond.io.
    
    Flujo:
    1. Delega procesamiento a message_processor
    2. Retorna respuesta personalizada con metadata de sesión
    """
    logger.info(f"[API] Processing message from {request.contact_id}")
    
    try:
        result = await process_message_for_api(
            contact_id=request.contact_id,
            message_text=request.message_text,
            contact_name=request.contact_name,
            contact_phone=request.contact_phone
        )
        
        return MessageResponse(
            response_text=result["response_text"],
            intent=result.get("session", {}).get("pending_intent"),
            session_data=result.get("session")
        )
        
    except Exception as e:
        logger.exception(f"[API] Error processing message: {e}")
        
        # Respuesta de error amigable
        error_msg = "Disculpa, tuve un problema al procesar tu mensaje. ¿Puedes intentar nuevamente?"
        
        # Intentar personalizar con nombre de sesión
        try:
            session = get_session(request.contact_id)
            if name := session.get("name"):
                error_msg = f"{name}, {error_msg}"
        except:
            pass
        
        return MessageResponse(
            response_text=error_msg,
            intent="error"
        )

# ==========================================
# ENDPOINTS AUXILIARES
# ==========================================

@app.get("/health")
async def health_check():
    """Health check para monitoreo"""
    return {
        "status": "healthy",
        "service": "RAG API",
        "version": "1.0.0"
    }

@app.get("/session/{contact_id}", 
        tags=["Session Management"]
        )
async def get_session_endpoint(contact_id: str):
    """
    Endpoint de debug para ver sesiones.
    TODO: Agregar autenticación antes de producción.
    """
    session = get_session(contact_id)
    return {
        "contact_id": contact_id,
        "session": session
    }

@app.delete("/session/{contact_id}", 
            tags=["Session Management"]
            )
async def clear_session_endpoint(contact_id: str):
    """
    Limpia la sesión de un usuario.
    Útil para testing o reset manual.
    """
    try:
        success = clear_session(contact_id)
        if success:
            return {
                "status": "session cleared",
                "contact_id": contact_id
            }
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.exception(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
