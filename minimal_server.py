#!/usr/bin/env python3
"""
Minimal FastAPI server for testing authentication endpoints only.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import only what we need for auth
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.api.v1.endpoints.auth import router as auth_router

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Create minimal FastAPI app
app = FastAPI(
    title="CreatorPulse Auth Test API",
    description="Minimal API for testing authentication endpoints",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router, prefix="/v1/auth", tags=["authentication"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CreatorPulse Auth Test API",
        "version": "1.0.0",
        "docs": "/docs",
        "auth_endpoints": "/v1/auth/"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "auth-test"}

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting minimal auth test server...")
    uvicorn.run(
        "minimal_server:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        log_level="info",
    )
