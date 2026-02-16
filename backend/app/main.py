from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import campaigns
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AdsAgent API",
    description="Google Ads Campaign Analysis Agent powered by Gemini AI",
    version="1.0.0",
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns.router)


@app.get("/")
def root():
    return {
        "name": "AdsAgent API",
        "version": "1.0.0",
        "docs": "/docs",
    }
