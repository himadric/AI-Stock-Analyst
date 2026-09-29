from fastapi import APIRouter, Depends
from app.api import health, finance, sec, ai, sentiment, institution, congress, house, senate, simulation, watchlist, munro, agent
from app.auth import require_auth

router = APIRouter()

# Health stays public; every other router requires a valid session token
protected = [Depends(require_auth)]

router.include_router(health.router, tags=["health"])
router.include_router(finance.router, prefix="/finance", tags=["finance"], dependencies=protected)
router.include_router(sec.router, prefix="/sec", tags=["sec"], dependencies=protected)
router.include_router(ai.router, prefix="/ai", tags=["ai"], dependencies=protected)
router.include_router(sentiment.router, prefix="/sentiment", tags=["sentiment"], dependencies=protected)
router.include_router(institution.router, prefix="/vanguard", tags=["vanguard"], dependencies=protected)
router.include_router(congress.router, prefix="/congress", tags=["congress"], dependencies=protected)
router.include_router(house.router, prefix="/house", tags=["house"], dependencies=protected)
router.include_router(senate.router, prefix="/senate", tags=["senate"], dependencies=protected)
router.include_router(simulation.router, prefix="/simulation", tags=["simulation"], dependencies=protected)
router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"], dependencies=protected)
router.include_router(munro.router, prefix="/munro", tags=["munro"], dependencies=protected)
router.include_router(agent.router, prefix="/agent", tags=["agent"], dependencies=protected)
