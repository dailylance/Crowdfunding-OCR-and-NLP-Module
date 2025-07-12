#!/usr/bin/env python3
"""
Simple OCR service server for testing
"""

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

import uvicorn
from fastapi import FastAPI
from ocr_service.core.config import settings
from ocr_service.app.api.v1 import endpoints

# Create FastAPI application
app = FastAPI(
    title="OCR Enhancement Service",
    version="1.0.0",
    description="OCR service for crowdfunding data enhancement with translation"
)

# Include routes
app.include_router(endpoints.router, prefix="/v1")

@app.get("/")
async def root():
    return {"message": "OCR Enhancement Service is running", "version": "1.0.0"}

if __name__ == "__main__":
    print("🚀 Starting OCR Enhancement Service on port 5002...")
    uvicorn.run(app, host="0.0.0.0", port=5002, log_level="info")
