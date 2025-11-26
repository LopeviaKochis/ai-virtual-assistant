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
    
    TELEGRAM: Puede venir como ID numérico o teléfono con código (+51...)
    WHATSAPP: Siempre viene con código de país (+51987654321)
    
    Args:
        phone_raw: Teléfono raw del contacto
        
    Returns:
        Teléfono normalizado (9 dígitos) o None
    """
    if not phone_raw:
        return None
    
    # Eliminar espacios y caracteres no numéricos excepto el +
    phone_raw = phone_raw.strip()
    
    # Extraer solo dígitos
    digits = re.sub(r"\D", "", phone_raw)
    
    # Si tiene código de país (51), removerlo
    # WhatsApp: +51987654321 → 51987654321 → 987654321
    if digits.startswith("51") and len(digits) >= 11:
        digits = digits[2:]  # Remover el 51
    
    # Tomar últimos 9 dígitos
    normalized = digits[-9:]
    
    # Validar formato peruano (9 dígitos que empiezan en 9)
    if len(normalized) == 9 and normalized.startswith("9"):
        logger.debug(f"Phone normalized: {phone_raw} → {normalized}")
        return normalized
    
    logger.warning(f"Invalid phone format: {phone_raw}")
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

def extract_preferred_name(text: str) -> Optional[str]:
    """
    Detecta cuando el usuario corrige su nombre.
    
    Patrones:
    - "Me llamo X"
    - "Soy X" (no seguido de "de", "del")
    - "Dime X"
    - "Llámame X"
    
    Returns:
        Nombre preferido o None
    """
    text = text.lower().strip()
    
    patterns = [
        r"(?:me llamo|mi nombre es)\s+([a-záéíóúñ]+)",
        r"(?:^|\s)soy\s+([a-záéíóúñ]+)(?:\s|$|,)",  # Evita "soy de Lima"
        r"(?:dime|llamame|llámame)\s+([a-záéíóúñ]+)",
    ]
    
    for pattern in patterns:
        if match := re.search(pattern, text):
            name = match.group(1).strip().title()
            # Validar que no sea una palabra común (ciudad, verbo, etc.)
            if len(name) >= 3 and name not in ["Lima", "Peru", "Bien", "Aquí"]:
                logger.info(f"Preferred name detected: {name}")
                return name
    
    return None


def enrich_session_from_message(
    session: Dict[str, Any],
    message_text: str,
    contact_name: Optional[str] = None,
    contact_phone: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enriquece la sesión extrayendo datos del mensaje y contacto
    priorizando nombre preferido (si existe).
    
    Args:
        session: Sesión actual del usuario
        message_text: Texto del mensaje
        contact_name: Nombre del contacto (opcional)
        contact_phone: Teléfono del contacto (opcional)
        
    Returns:
        Sesión enriquecida con nuevos datos
    """
    updates = {}
    
    # P1-1: Detectar nombre preferido
    if preferred := extract_preferred_name(message_text):
        updates["preferred_name"] = preferred
        logger.info(f"User prefers to be called: {preferred}")
    
    # Nombre original (para búsquedas)
    if "name" not in session and contact_name:
        first_name = contact_name.split()[0].strip().title()
        updates["name"] = first_name
    
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


def format_response_with_name(
    session: Dict[str, Any],  # Ahora recibe toda la sesión
    text: str
) -> str:
    """
    Formatea respuesta usando nombre preferido > nombre original.
    
    Args:
        session: Sesión completa (contiene preferred_name y name)
        text: Texto de la respuesta
        
    Returns:
        Respuesta personalizada
    """
    # Prioridad: preferred_name > name > sin nombre
    name = session.get("preferred_name") or session.get("name")
    
    if not name or text.lower().startswith(name.lower()):
        return text
    
    return f"{name}, {text.lstrip()}"
