"""
Data models for video processing and analysis.
"""
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class VideoStatus(str, Enum):
    """Video processing status enumeration."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TRANSCRIPT_ONLY = "transcript_only"


class VideoMetadata(BaseModel):
    """Video metadata model."""
    id: str
    title: str
    file_path: Optional[str] = None
    source_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    status: VideoStatus = VideoStatus.UPLOADED
    upload_date: str
    duration: Optional[float] = None
    file_size: Optional[int] = None
    format: Optional[str] = None
    resolution: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)


class YouTubeRequest(BaseModel):
    """Request model for YouTube video processing."""
    url: str
    title: Optional[str] = None
    download_video: bool = True
    extract_transcript: bool = True


class ProcessingStatus(BaseModel):
    """Video processing status model."""
    video_id: str
    status: str
    progress: float = Field(ge=0.0, le=1.0)
    message: Optional[str] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


class VideoChapter(BaseModel):
    """Video chapter model."""
    id: str
    title: str
    start_time: float
    end_time: float
    description: Optional[str] = None
    thumbnail_path: Optional[str] = None


class VideoOutlineResponse(BaseModel):
    """Video outline response model."""
    video_id: str
    title: str
    duration: float
    chapters: List[VideoChapter] = []
    summary: str
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


class FrameData(BaseModel):
    """Video frame data model."""
    id: str
    frame_path: str
    timestamp: float
    scene_description: Optional[str] = None
    objects_detected: List[str] = []
    confidence_scores: Dict[str, float] = {}


class TranscriptChunk(BaseModel):
    """Transcript chunk model."""
    id: str
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None
    speaker: Optional[str] = None


class VideoAnalysisResult(BaseModel):
    """Complete video analysis result."""
    video_id: str
    metadata: VideoMetadata
    transcript_chunks: List[TranscriptChunk] = []
    frames: List[FrameData] = []
    chapters: List[VideoChapter] = []
    summary: str
    processing_time: Optional[float] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)


# Legacy aliases for backward compatibility
VideoTranscript = TranscriptChunk
VideoFrame = FrameData


class SearchResult(BaseModel):
    """Search result model for RAG queries."""
    id: str
    content: str
    score: float
    timestamp: Optional[float] = None
    video_id: str
    type: str  # "transcript" or "frame"
    metadata: Dict[str, Any] = {}


class VisualSearchRequest(BaseModel):
    """Request model for visual search."""
    query: str = Field(..., description="Natural language query for visual content")
    video_id: str = Field(..., description="ID of the video to search")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of results to return")
    time_range: Optional[Dict[str, float]] = Field(
        default=None, 
        description="Optional time range filter with 'start' and 'end' keys in seconds"
    )


class VisualSearchResponse(BaseModel):
    """Response model for visual search."""
    query: str
    results: List[SearchResult]
    total_results: int
    video_id: str


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Role of the message sender (user, assistant)")
    content: str = Field(..., description="Content of the message")
    timestamp: Optional[float] = Field(default=None, description="Timestamp reference for video content")


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    video_id: str = Field(..., description="ID of the video context")
    chat_history: List[ChatMessage] = Field(default=[], description="Previous chat messages")


class ChatResponse(BaseModel):
    """Chat response model."""
    response: str = Field(..., description="AI assistant response")
    timestamp_references: List[float] = Field(
        default=[], 
        description="Referenced timestamps in the video (in seconds)"
    )
    confidence: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Confidence score of the response"
        )
    sources_used: List[str] = Field(
        default=[], 
        description="IDs of sources used to generate the response"
    )
    
    @field_validator('timestamp_references')
    @classmethod
    def validate_timestamps(cls, v: List[float]) -> List[float]:
        """Validate that all timestamps are non-negative."""
        if v and any(t < 0 for t in v):
            raise ValueError("Timestamps must be non-negative")
        return sorted(v)  # Return sorted timestamps


class QueryResult(BaseModel):
    """Result model for RAG queries."""
    response: str = Field(..., description="The generated response")
    sources: List[SearchResult] = Field(
        default_factory=list, 
        description="Source search results used to generate the response"
    )
    confidence: float = Field(
        ge=0.0, 
        le=1.0, 
        description="Confidence score of the response"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata including processing time, model used, etc."
    )
    timestamp_references: List[float] = Field(
        default=[], 
        description="Extracted timestamp references from the query (in seconds)"
    )
    query_type: str = Field(
        default="general", 
        description="Type of query: 'general', 'visual', 'transcript', 'temporal'"
    )
    
    @field_validator('timestamp_references')
    @classmethod
    def validate_timestamps(cls, v: List[float]) -> List[float]:
        """Validate that all timestamps are non-negative."""
        if v and any(t < 0 for t in v):
            raise ValueError("Timestamps must be non-negative")
        return sorted(v)
