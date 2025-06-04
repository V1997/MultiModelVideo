"""
Main application entry point.
"""
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config.settings import settings
from src.api import router as api_router
from src.core.database import initialize_database
from src.utils.logger import setup_logger

# Setup logging
logger = setup_logger(__name__)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="AI Video Analysis System",
        description="Multimodal video analysis with chat, timestamps, and visual search",
        version="1.0.0",
        debug=settings.debug
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Serve static files
    static_path = Path("static")
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup."""
        logger.info("Starting AI Video Analysis System...")
        try:
            await initialize_database()
            logger.info("System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            raise
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Shutting down AI Video Analysis System...")
    
    @app.get("/")
    async def read_index():
        """Serve the main HTML page."""
        from fastapi.responses import FileResponse
        return FileResponse('static/index.html')
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "ai-video-analysis"}
    
    return app

def main():
    """Run the application."""
    app = create_app()
    
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )

# Create the app instance for uvicorn
app = create_app()

if __name__ == "__main__":
    main()
