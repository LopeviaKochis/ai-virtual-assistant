# Funciones puras auxiliares reutilizables
from .regex_utils import EMAIL_RE, PHONE_RE, DNI_RE
import re

def parse_identifier(text: str):
    if m := EMAIL_RE.search(text):
        return "Email", m.group(0).lower()
    if m := PHONE_RE.search(text):
        return "PhoneNumber", re.sub(r"\D+", "", m.group(0))
    if m := DNI_RE.search(text):
        return "DocNum", m.group(0)
    return None, None


def capture_name(text: str):
    m = re.search(r"\bsoy\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip().split()[0].title()
