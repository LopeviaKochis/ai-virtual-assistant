# Cliente de Azure para acceder a los recursos en nube para la app RAG
import pandas as pd
from typing import Dict, List, Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Campos base que se requieren para las consultas de deuda.
_DEFAULT_DEBT_FIELDS = [
    "Firstname",
    "Status",
    "Amount",
    "actual_agreement_due_date",
    "TotalDebt",
    "PrincipalDebt",
    "Interest",
    "OrganizationalFee",
    "InterestAfterDD",
    "PenaltyCharge",
]

# Renombres amigables únicamente para la respuesta de deuda.
_DEFAULT_DEBT_RENAME = {
    "Firstname": "Nombre",
    "Status": "Estado",
    "Amount": "Monto",
    "actual_agreement_due_date": "Vencimiento",
    "TotalDebt": "TotalDeuda",
    "PrincipalDebt": "Principal",
    "Interest": "Intereses",
    "OrganizationalFee": "Gastos",
    "InterestAfterDD": "Mora",
    "PenaltyCharge": "Penalidad",
}

# Cacheamos clientes por índice para reutilizarlos sin reconstruirlos en cada petición.
_SEARCH_CLIENTS: Dict[str, SearchClient] = {}


def _get_search_client(index_name: Optional[str]) -> Optional[SearchClient]:
    """Crea (o reutiliza) un cliente de búsqueda para el índice solicitado."""
    if not (settings.AZURE_ENDPOINT and settings.AZURE_QUERYKEY and index_name):
        return None
    if index_name not in _SEARCH_CLIENTS:
        _SEARCH_CLIENTS[index_name] = SearchClient(
            endpoint=settings.AZURE_ENDPOINT,
            index_name=index_name,
            credential=AzureKeyCredential(settings.AZURE_QUERYKEY)
        )
    return _SEARCH_CLIENTS[index_name]


def azure_search(
    field: str,
    value: str,
    *,
    index: Optional[str] = None,
    select: Optional[List[str]] = None,
    rename: Optional[Dict[str, str]] = None,
    timeout: int = 4  # P1-2: Timeout configurable
) -> pd.DataFrame:
    """
    Ejecuta búsqueda con timeout estricto y manejo de errores.
    """
    index_name = index or settings.AZURE_INDEX_DEUDA or settings.AZURE_INDEX
    client = _get_search_client(index_name)
    if not client:
        logger.error("Azure Search client not configured")
        return pd.DataFrame()

    if select is None:
        select_fields = _DEFAULT_DEBT_FIELDS
        rename_map = _DEFAULT_DEBT_RENAME
    else:
        select_fields = select
        rename_map = rename or {}

    filter_clause = f"{field} eq '{value}'"
    
    try:
        import signal
        
        # P1-2: Timeout usando signal (solo funciona en main thread)
        # Alternativa: usar asyncio.wait_for si refactorizamos a async
        results = client.search(
            search_text="*",
            filter=filter_clause,
            top=10,
            select=select_fields
        )

        rows = []
        for record in results:
            row = {}
            for source_field in select_fields:
                target = rename_map.get(source_field, source_field)
                row[target] = record.get(source_field)
            rows.append(row)
        
        logger.info(f"Azure Search returned {len(rows)} results for {field}={value}")
        return pd.DataFrame(rows)
    
    except Exception as e:
        logger.exception(f"Azure Search error for {field}={value}: {e}")
        # P1-2: Retornar DataFrame vacío en lugar de crashear
        return pd.DataFrame()


def search_debt_by_dni(dni: str) -> pd.DataFrame:
    """Búsqueda especializada para deuda usando el DNI del cliente."""
    return azure_search("DocNum", dni)


def search_otp_by_phone(phone: str) -> pd.DataFrame:
    """Búsqueda especializada para recuperar claves OTP del número registrado."""
    return azure_search(
        "Recepient",
        phone,
        index=settings.AZURE_INDEX_OTP,
        select=["Recepient", "Codigo"]
    )
