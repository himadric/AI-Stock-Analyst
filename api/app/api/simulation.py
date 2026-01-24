from fastapi import APIRouter, HTTPException
from app.services.simulation import SimulationService
from pydantic import BaseModel
from typing import Optional

router = APIRouter()
service = SimulationService()

class SimulationRequest(BaseModel):
    ticker: str
    wacc: Optional[float] = 0.09
    growth_rate_mean: Optional[float] = None
    simulations: int = 10000
    bear_case: bool = False

@router.post("/run")
async def run_simulation(req: SimulationRequest):
    result = service.run_dcf_simulation(
        req.ticker, 
        wacc=req.wacc,
        growth_rate_mean=req.growth_rate_mean,
        num_simulations=req.simulations,
        bear_case=req.bear_case
    )
    if not result:
        raise HTTPException(status_code=500, detail="Simulation failed")
        
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result
