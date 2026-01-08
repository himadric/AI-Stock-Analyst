from fastapi import APIRouter, HTTPException, Query
from app.services.congress_service import CongressService

router = APIRouter()
congress_service = CongressService()

@router.get("/trades")
def get_congress_trades(limit: int = 100):
    """
    Returns recent stock trading activity by US Congress members.
    """
    data = congress_service.get_recent_trades(limit=limit)
    if "error" in data:
         # If missing API key, returning 500 is ok, or 400.
         # service returns "error": key not found
         raise HTTPException(status_code=500, detail=data["error"])
    return data
