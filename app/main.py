from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger

import os
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="MedIntel AI — Medical Document OCR API",
    version="1.0.0",
    description="Production Medical OCR Engine combining OpenCV preprocessing, PaddleOCR layout detection, and TrOCR handwriting extraction.",
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("outputs/temp", exist_ok=True)
app.mount("/temp", StaticFiles(directory="outputs/temp"), name="temp")

@app.get("/health", tags=["System"])
async def health_check():
    """Returns 200 OK if MedIntel OCR server is running."""
    logger.info("Health check endpoint pinged")
    return {"status": "ok", "system": "MedIntel AI OCR Engine", "version": "1.0.0"}

from app.api.ocr import router as ocr_router
from app.api.auth import router as auth_router

app.include_router(ocr_router, prefix="/ocr", tags=["MedIntel OCR Engine"])
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

