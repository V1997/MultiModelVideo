"""
Data models package for the video analysis system.
"""

from .video_data import (
    VideoMetadata,
    VideoStatus,
    YouTubeRequest,
    ProcessingStatus,
    VideoOutlineResponse,
    VideoAnalysisResult,
    VideoChapter,
    FrameData,
    TranscriptChunk,
    QueryResult
)

__all__ = [
    "VideoMetadata",
    "VideoStatus", 
    "YouTubeRequest",
    "ProcessingStatus",
    "VideoOutlineResponse",
    "VideoAnalysisResult",
    "VideoChapter",
    "FrameData",
    "TranscriptChunk",
    "QueryResult"
]
