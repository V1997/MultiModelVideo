"""
Search API routes for visual and semantic content search.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from src.models.video_data import VisualSearchRequest, VisualSearchResponse, SearchResult
from src.services.ai_service import ai_service
from src.services.rag_service import rag_service
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.post("/visual", response_model=VisualSearchResponse)
async def visual_search(request: VisualSearchRequest):
    """Search for visual content in videos."""
    try:
        start_time = None
        if hasattr(request, 'time_range') and request.time_range:
            start_time = request.time_range.get('start', 0)
        
        # Get all frames for the video (in production, filter by time range)
        # This is a simplified implementation
        transcript_chunks, frames = await rag_service.retrieve_relevant_content(
            query=request.query,
            video_id=request.video_id,
            max_results=request.max_results * 2,  # Get more to filter
            content_types=["visual"]
        )
        
        # Perform visual search using AI service
        search_results = await ai_service.visual_search(request.query, frames)
          # Apply time range filter if specified
        if request.time_range:
            start_time = request.time_range.get('start', 0)
            end_time = request.time_range.get('end', float('inf'))
            search_results = [
                result for result in search_results
                if start_time <= result.timestamp <= end_time
            ]
        
        # Limit results
        search_results = search_results[:request.max_results]
        
        response = VisualSearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            video_id=request.video_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in visual search: {e}")
        raise HTTPException(status_code=500, detail=f"Visual search error: {str(e)}")


@router.get("/semantic")
async def semantic_search(
    query: str = Query(..., description="Search query"),
    video_ids: Optional[List[str]] = Query(None, description="List of video IDs to search"),
    content_type: Optional[str] = Query(None, description="Content type filter"),
    max_results: int = Query(20, description="Maximum number of results")
):
    """Perform semantic search across video content."""
    try:
        # Perform semantic search using RAG service
        search_results = await rag_service.search_similar_content(
            query=query,
            video_ids=video_ids,
            content_type=content_type,
            max_results=max_results
        )
        
        return {
            "query": query,
            "results": [
                {
                    "video_id": result.video_id,
                    "timestamp": result.timestamp,
                    "relevance_score": result.relevance_score,
                    "content_type": result.content_type,
                    "content": result.content,
                    "thumbnail_path": result.thumbnail_path
                }
                for result in search_results
            ],
            "total_results": len(search_results)
        }
        
    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/suggestions/{video_id}")
async def get_search_suggestions(video_id: str):
    """Get search suggestions for a video."""
    try:
        suggestions = [
            "Show me when someone speaks",
            "Find scenes with text or writing",
            "Look for outdoor scenes",
            "Find people in the video",
            "Show me any charts or graphs",
            "Find action scenes",
            "Look for close-up shots",
            "Find scenes with multiple people"
        ]
        
        return {"video_id": video_id, "suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Error getting search suggestions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/objects/{video_id}")
async def get_detected_objects(video_id: str):
    """Get all objects detected in a video."""
    try:
        return {
            "video_id": video_id,
            "objects": [],
            "message": "Object detection will be available after video processing completes"
        }
        
    except Exception as e:
        logger.error(f"Error getting detected objects: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
