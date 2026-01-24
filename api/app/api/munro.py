from fastapi import APIRouter, HTTPException
from app.services.institution_service import InstitutionService

router = APIRouter()
institution_service = InstitutionService()

@router.get("/trades")
def get_munro_trades(limit: int = 10):
    """
    Returns Munro Partners top buys and sells based on latest 13F filings.
    """
    data = institution_service.get_munro_trades(limit=limit)
    if "error" in data:
         raise HTTPException(status_code=500, detail=data["error"])
    return data
