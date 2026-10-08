from dotenv import load_dotenv

import os
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import router

# docs/openapi/redoc live under /api so vercel.json's "/api/:path*" rewrite
# reaches them in production - FastAPI's defaults (/docs, /openapi.json) sit
# at the app root, which only the Vercel rewrite for /api/* ever forwards to
# this function, so the root-level paths 404 on the deployed site even
# though they work fine hitting uvicorn directly in local dev.
app = FastAPI(
    title="AI Analyst API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Analyst API"}
