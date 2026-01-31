"""
Simple startup script for BioLoupe backend with minimal dependencies
"""
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BioLoupe Backend",
    description="Biological Research Platform API",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoint
@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "message": "BioLoupe backend is running"}

@app.get("/")
async def root():
    return {"message": "Welcome to BioLoupe API", "docs": "/docs", "health": "/api/v1/health"}

if __name__ == "__main__":
    logger.info("Starting BioLoupe backend server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
    )