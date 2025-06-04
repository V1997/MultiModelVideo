"""
Main entry point for the AI-Powered Video Analysis System.
Run this file to start the FastAPI server.
"""
# Load environment variables FIRST before any other imports
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from src.api.routes import videos
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI-Powered Video Analysis System",
    description="Conversational video analysis with multimodal RAG",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])

# Try to include chat routes if available
try:
    from src.api.routes import chat
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    logger.info("Chat routes loaded successfully")
except ImportError as e:
    logger.warning(f"Chat routes not found: {e}")

# Serve static files if they exist
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Root endpoint - redirect to web interface."""
    from fastapi.responses import FileResponse
    
    # Check if static files exist
    index_path = Path("static/index.html")
    if index_path.exists():
        return FileResponse("static/index.html")
    else:
        # Fallback to API info
        return {
            "message": "AI-Powered Video Analysis System API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "note": "Web interface not found. Please create static/index.html"
        }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Video analysis system is running"
    }

if __name__ == "__main__":
    logger.info("Starting AI-Powered Video Analysis System...")
    
    # Ensure required directories exist
    try:
        from src.utils.file_utils import ensure_directory
        ensure_directory(Path(settings.upload_dir))
        ensure_directory(Path(settings.storage_dir))
    except ImportError as e:
        logger.warning(f"File utils not found: {e}")
        # Create directories manually as fallback
        Path(settings.upload_dir).mkdir(exist_ok=True)
        Path(settings.storage_dir).mkdir(exist_ok=True)
    
    # Run the server
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
