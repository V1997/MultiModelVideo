"""
API package initialization.
"""

from fastapi import APIRouter
from .routes import videos, chat, search

# Create main API router
router = APIRouter()

# Include all route modules
router.include_router(videos.router, prefix="/videos", tags=["videos"])
router.include_router(chat.router, prefix="/chat", tags=["chat"])
router.include_router(search.router, prefix="/search", tags=["search"])
