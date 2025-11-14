# Cliente de Azure para acceder a los recursos en nube para la app RAG
import pandas as pd
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from config.settings import settings

def get_azure_client():
    if not (settings.AZURE_ENDPOINT and settings.AZURE_INDEX and settings.AZURE_QUERYKEY):
        return None
    
    return SearchClient(
        endpoint=settings.AZURE_ENDPOINT,
        index_name=settings.AZURE_INDEX,
        credential=AzureKeyCredential(settings.AZURE_QUERYKEY)
    )

search_client = get_azure_client()


def azure_search(field: str, value: str) -> pd.DataFrame:
    if not search_client:
        return pd.DataFrame()

    flt = f"{field} eq '{value}'"
    results = search_client.search(
        search_text="*",
        filter=flt,
        top=10,
        select=(
            "Firstname,Status,Amount,actual_agreement_due_date,TotalDebt,"
            "PrincipalDebt,Interest,OrganizationalFee,InterestAfterDD,PenaltyCharge"
        )
    )
    rows = []
    for r in results:
        rows.append({
            "Nombre":      r.get("Firstname"),
            "Estado":      r.get("Status"),
            "Monto":       r.get("Amount"),
            "Vencimiento": r.get("actual_agreement_due_date"),
            "TotalDeuda":  r.get("TotalDebt"),
            "Principal":   r.get("PrincipalDebt"),
            "Intereses":   r.get("Interest"),
            "Gastos":      r.get("OrganizationalFee"),
            "Mora":        r.get("InterestAfterDD"),
            "Penalidad":   r.get("PenaltyCharge"),
        })
    return pd.DataFrame(rows)
