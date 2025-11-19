import re
import logging
from typing import Optional, Dict, Any
from utils.regex_utils import DNI_RE, PHONE_RE
from utils.parsing import capture_name

logger = logging.getLogger(__name__)

def extract_dni(text: str) -> Optional[str]:
    """
    Extrae un DNI del texto (8 dígitos exactos).
    
    Args:
        text: Texto del mensaje
        
    Returns:
        DNI extraído o None
    """
    if match := DNI_RE.search(text):
        dni = match.group(0)
        logger.debug(f"DNI extracted: {dni}")
        return dni
    return None

def extract_phone(text: str) -> Optional[str]:
    """
    Extrae y normaliza un número de teléfono móvil peruano.
    Formato esperado: 9 dígitos que empiezan en 9.
    
    Args:
        text: Texto del mensaje
        
    Returns:
        Teléfono normalizado o None
    """
    # Eliminar espacios para facilitar búsqueda
    compact = re.sub(r"\s+", "", text)
    
    if match := PHONE_RE.search(compact):
        # Extraer solo dígitos
        digits = re.sub(r"\D", "", match.group(0))
        # Tomar últimos 9 dígitos
        normalized = digits[-9:]
        
        # Validar que empiece en 9
        if len(normalized) == 9 and normalized.startswith("9"):
            logger.debug(f"Phone extracted: {normalized}")
            return normalized
    
    return None

def normalize_phone_from_contact(phone_raw: str) -> Optional[str]:
    """
    Normaliza un teléfono que viene del campo de contacto de Respond.io.
    Puede venir con prefijos internacionales (+51, 51, etc).
    
    Args:
        phone_raw: Teléfono raw del contacto
        
    Returns:
        Teléfono normalizado (9 dígitos) o None
    """
    if not phone_raw:
        return None
    
    # Extraer solo dígitos
    digits = re.sub(r"\D", "", phone_raw)
    
    # Si tiene código de país (51), ignorarlo
    if digits.startswith("51") and len(digits) >= 11:
        digits = digits[2:]  # Remover el 51
    
    # Tomar últimos 9 dígitos
    normalized = digits[-9:]
    
    # Validar formato
    if len(normalized) == 9 and normalized.startswith("9"):
        logger.debug(f"Phone normalized from contact: {normalized}")
        return normalized
    
    logger.warning(f"Invalid phone format from contact: {phone_raw}")
    return None

def extract_name(text: str, contact_name: Optional[str] = None) -> Optional[str]:
    """
    Extrae el nombre del usuario.
    Prioridad: contact_name > mensaje del usuario.
    
    Args:
        text: Texto del mensaje
        contact_name: Nombre del contacto en Respond.io
        
    Returns:
        Nombre extraído (solo primer nombre) o None
    """
    # Prioridad 1: Nombre del contacto
    if contact_name:
        first_name = contact_name.split()[0].strip().title()
        logger.debug(f"Name from contact: {first_name}")
        return first_name
    
    # Prioridad 2: Capturar del mensaje (ej: "soy Juan")
    if name := capture_name(text):
        logger.debug(f"Name from message: {name}")
        return name
    
    return None

def enrich_session_from_message(
    session: Dict[str, Any],
    message_text: str,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enriquece la sesión extrayendo datos del mensaje y contacto.
    
    Args:
        session: Sesión actual del usuario
        message_text: Texto del mensaje
        contact_name: Nombre del contacto (opcional)
        contact_phone: Teléfono del contacto (opcional)
        
    Returns:
        Sesión enriquecida con nuevos datos
    """
    updates = {}
    
    # Extraer nombre si no lo tenemos
    if "name" not in session:
        if name := extract_name(message_text, contact_name):
            updates["name"] = name
    
    # Extraer DNI del mensaje
    if dni := extract_dni(message_text):
        updates["dni"] = dni
    
    # Extraer/normalizar teléfono
    # Prioridad 1: Del contacto
    if contact_phone:
        if phone := normalize_phone_from_contact(contact_phone):
            updates["phone"] = phone
    
    # Prioridad 2: Del mensaje (si no lo obtuvimos del contacto)
    if "phone" not in updates:
        if phone := extract_phone(message_text):
            updates["phone"] = phone
    
    # Aplicar actualizaciones
    if updates:
        session.update(updates)
        logger.info(f"Session enriched with: {list(updates.keys())}")
    
    return session

def format_response_with_name(name: Optional[str], text: str) -> str:
    """
    Añade el nombre al inicio del mensaje de forma natural.
    Evita duplicaciones si el nombre ya está al inicio.
    
    Args:
        name: Nombre del usuario
        text: Texto de la respuesta
        
    Returns:
        Respuesta personalizada
    """
    if not name or text.startswith(name):
        return text
    
    # Añadir nombre de forma natural
    return f"{name}, {text.lstrip()}"