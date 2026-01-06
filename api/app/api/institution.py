from fastapi import APIRouter, HTTPException
from app.services.institution_service import InstitutionService

router = APIRouter()
institution_service = InstitutionService()

@router.get("/trades")
def get_vanguard_trades():
    """
    Returns Vanguard's top buys and sells based on latest 13F filings.
    """
    data = institution_service.get_vanguard_trades()
    if "error" in data:
         # Depending on error, usually return 500 or 503, but 200 with error field is safer for simple clients
         raise HTTPException(status_code=500, detail=data["error"])
    return data
