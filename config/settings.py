"""
Configuration settings for the video analysis system.
"""
import os
from pathlib import Path
from typing import List

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    
    # Directory Configuration
    upload_dir: str = "uploads"
    storage_dir: str = "storage"
    temp_dir: str = "temp"
    
    # AI Service Configuration
    openai_api_key: str = ""
    gemini_api_key: str = ""    # Database Configuration
    database_url: str = "sqlite:///./video_analysis.db"
    chromadb_path: str = "data/chromadb"
    vector_db_collection: str = "video_embeddings"
    
    # Application Configuration
    debug: bool = False
    
    # File Configuration
    max_file_size: int = 500 * 1024 * 1024  # 500MB
    max_video_size_mb: int = 500
    allowed_extensions: List[str] = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
      # Video Processing Configuration
    chunk_duration_seconds: int = 30
    frame_sample_rate: int = 1
    max_concurrent_processes: int = 4
    download_youtube_videos: bool = False  # Set to True to download for frame analysis
    
    # Text Processing Configuration
    text_chunk_size: int = 1000
    text_chunk_overlap: int = 200
    
    # AI Model Configuration
    gemini_text_model: str = "gemini-1.5-pro"
    gemini_vision_model: str = "gemini-1.5-pro-vision"
    gemini_embedding_model: str = "models/text-embedding-004"
    max_retries: int = 3
    request_timeout: int = 30
    
    # YouTube Configuration
    youtube_quality: str = "best[height<=720]"
    youtube_format: str = "mp4"
    
    # CORS Configuration
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow extra fields from environment variables
        extra = "ignore"

# Global settings instance
settings = Settings()

# Ensure directories exist
Path(settings.upload_dir).mkdir(exist_ok=True)
Path(settings.storage_dir).mkdir(exist_ok=True)
Path(settings.temp_dir).mkdir(exist_ok=True)
Path(settings.chromadb_path).mkdir(parents=True, exist_ok=True)
