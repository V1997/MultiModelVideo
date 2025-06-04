"""
Database initialization and utilities.
"""
import chromadb
import time
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
from typing import Optional
import threading

from config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global client instance and lock for thread safety
_global_client = None
_client_lock = threading.Lock()

def get_chromadb_client():
    """Get or create a singleton ChromaDB client with consistent settings."""
    global _global_client
    
    with _client_lock:
        if _global_client is None:
            try:
                # Ensure ChromaDB directory exists
                Path(settings.chromadb_path).mkdir(parents=True, exist_ok=True)
                
                # Create client with consistent settings
                _global_client = chromadb.PersistentClient(
                    path=settings.chromadb_path,
                    settings=ChromaSettings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                        is_persistent=True
                    )
                )
                logger.info(f"ChromaDB client initialized at: {settings.chromadb_path}")
                
            except Exception as e:
                logger.error(f"Failed to create ChromaDB client: {e}")
                raise
                
        return _global_client

def reset_chromadb_client():
    """Reset the global ChromaDB client (for testing purposes only)."""
    global _global_client
    with _client_lock:
        _global_client = None
        logger.info("ChromaDB client reset")

def get_or_create_collection(name: str, metadata: Optional[dict] = None):
    """Get or create a collection with consistent settings."""
    client = get_chromadb_client()
    
    # Default metadata with consistent settings
    default_metadata = {
        "hnsw:space": "cosine",  # Consistent distance metric
        "created_at": str(time.time())
    }
    
    if metadata:
        default_metadata.update(metadata)
    
    return client.get_or_create_collection(
        name=name,
        metadata=default_metadata
    )

class DatabaseManager:
    """Database manager for ChromaDB operations."""
    
    def __init__(self):
        self.client: Optional[chromadb.Client] = None
        self.collection = None

    async def initialize(self):
        """Initialize ChromaDB client and collections."""
        try:
            # Use the singleton client
            self.client = get_chromadb_client()
            
            # Get or create collection with consistent settings
            self.collection = get_or_create_collection(
                name=settings.vector_db_collection,
                metadata={
                    "description": "Video embeddings for multimodal RAG"
                }
            )
            
            logger.info(f"ChromaDB initialized with collection: {settings.vector_db_collection}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_collection(self):
        """Get the main collection."""
        if not self.collection:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.collection
    
    async def add_embeddings(self, 
                           ids: list,
                           embeddings: list,
                           metadatas: list,
                           documents: list):
        """Add embeddings to the collection."""
        try:
            collection = self.get_collection()
            collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents
            )
            logger.info(f"Added {len(ids)} embeddings to collection")
            
        except Exception as e:
            logger.error(f"Failed to add embeddings: {e}")
            raise
    
    async def query_embeddings(self,
                             query_embeddings: list,
                             n_results: int = 5,
                             where: Optional[dict] = None):
        """Query embeddings from the collection."""
        try:
            collection = self.get_collection()
            results = collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            return results
            
        except Exception as e:
            logger.error(f"Failed to query embeddings: {e}")
            raise
    
    async def delete_video_embeddings(self, video_id: str):
        """Delete all embeddings for a specific video."""
        try:
            collection = self.get_collection()
            collection.delete(where={"video_id": video_id})
            logger.info(f"Deleted embeddings for video: {video_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete embeddings for video {video_id}: {e}")
            raise
    
    async def get_stats(self):
        """Get collection statistics."""
        try:
            collection = self.get_collection()
            count = collection.count()
            return {
                "total_embeddings": count,
                "collection_name": settings.vector_db_collection,
                "database_path": settings.chromadb_path
            }
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

# Global database manager instance
db_manager = DatabaseManager()

async def initialize_database():
    """Initialize the database."""
    await db_manager.initialize()

def get_database() -> DatabaseManager:
    """Get database manager instance."""
    return db_manager
