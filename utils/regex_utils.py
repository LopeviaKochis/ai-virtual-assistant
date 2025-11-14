# Regex descentralizado
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?51)?9\d{8}")
DNI_RE   = re.compile(r"\b\d{8}\b")
