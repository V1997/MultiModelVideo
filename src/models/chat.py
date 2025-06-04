from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    """Request for chat with video."""
    message: str = Field(..., description="User's question or message")
    video_id: Optional[str] = Field(None, description="Specific video ID to query")
    include_visual: bool = Field(default=True, description="Include visual content in search")
    max_results: Optional[int] = Field(default=5, description="Maximum number of search results")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")