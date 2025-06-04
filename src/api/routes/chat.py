"""
Chat API routes for conversational video interaction.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from src.models.video_data import ChatRequest, ChatResponse, ChatMessage
from src.services.ai_service import ai_service
from src.services.rag_service import rag_service, RAGService
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

def get_rag_service() -> RAGService:
    """Dependency function to get RAG service instance."""
    return rag_service

def _get_no_video_guidance_message(user_message: str) -> str:
    """Generate guidance message when no videos are available."""
    return (
        f"I'd love to help you with '{user_message}', but I don't have any video content to work with yet. "
        f"Please upload a video first, and I'll be able to answer questions about it, "
        f"provide summaries, find specific moments, and help you navigate through the content."
    )

def _get_video_id_match(video_id: str, available_videos: List[Dict[str, Any]]) -> Optional[str]:
    """Find matching video ID, handling prefix variations."""
    video_ids = [v.get('video_id') for v in available_videos]
    
    if video_id in video_ids:
        return video_id
    
    # Try with youtube_ prefix
    if f"youtube_{video_id}" in video_ids:
        return f"youtube_{video_id}"
    
    # Try without youtube_ prefix
    if video_id.startswith("youtube_") and video_id[8:] in video_ids:
        return video_id[8:]
    
    return None

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(request: ChatRequest):
    """Send a chat message about a video."""
    try:
        logger.info(f"Chat request for video {request.video_id}: {request.message}")
        
        # Check if video exists in database
        available_videos = await rag_service.get_available_videos()
        target_video_id = _get_video_id_match(request.video_id, available_videos)
        
        if not target_video_id:
            video_ids = [v.get('video_id') for v in available_videos]
            return ChatResponse(
                response=f"Video '{request.video_id}' not found. Available videos: {video_ids}",
                timestamp_references=[],
                confidence=0.0
            )
        
        # Get context from RAG service
        context = await rag_service.get_context_for_query(
            video_id=target_video_id,
            query=request.message
        )
        
        transcript_chunks = context.get("transcript_chunks", [])
        frames = context.get("frames", [])
        
        # Format chat history for context
        chat_history = []
        for msg in request.chat_history[-5:]:  # Last 5 messages for context
            chat_history.append({"role": msg.role, "content": msg.content})
        
        # Generate response using AI service
        response_text, timestamp_refs = await ai_service.chat_with_video(
            video_id=target_video_id,
            user_message=request.message,
            transcript_chunks=transcript_chunks,
            frames=frames,
            conversation_history=chat_history
        )
        
        return ChatResponse(
            response=response_text,
            timestamp_references=timestamp_refs,
            confidence=0.8 if transcript_chunks or frames else 0.3
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{video_id}/history")
async def get_chat_history(video_id: str):
    """Get chat history for a video."""
    try:
        # Mock implementation
        return {
            "video_id": video_id,
            "messages": [],
            "total_messages": 0
        }
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{video_id}/history")
async def clear_chat_history(video_id: str):
    """Clear chat history for a video."""
    try:
        # Mock implementation
        return {"message": f"Chat history cleared for video {video_id}"}
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_video(
    request: ChatRequest,
    rag_service_instance: RAGService = Depends(get_rag_service)
) -> ChatResponse:
    """Chat with video content using RAG."""
    try:
        logger.info(f"Chat request - Video ID: {request.video_id}, Message: {request.message}")
        
        # Get database statistics and available videos
        stats = await rag_service_instance.get_stats()
        available_videos = await rag_service_instance.get_available_videos()
        total_embeddings = stats.get("total_embeddings", 0)
        
        # If no video content exists at all
        if total_embeddings == 0:
            return ChatResponse(
                response="I don't have any video content in my database yet. Please upload and process a video first.",
                timestamp_references=[],
                confidence=1.0,
                sources_used=[]
            )
        
        # If a specific video is requested, validate it exists
        if request.video_id:
            target_video_id = _get_video_id_match(request.video_id, available_videos)
            
            if not target_video_id:
                available_ids = [v.get("video_id", "unknown") for v in available_videos]
                return ChatResponse(
                    response=f"Video '{request.video_id}' not found. Available videos: {available_ids}",
                    timestamp_references=[],
                    confidence=0.8,
                    sources_used=[]
                )
            
            request.video_id = target_video_id
            
            # Check if video has transcript content
            try:
                video_stats = await rag_service_instance.get_video_stats(request.video_id)
                if video_stats.get("transcript_chunks", 0) == 0:
                    return ChatResponse(
                        response=f"Video '{request.video_id}' exists but has no transcript content. It may still be processing.",
                        timestamp_references=[],
                        confidence=0.7,
                        sources_used=[]
                    )
            except Exception as stats_error:
                logger.warning(f"Could not get video stats for {request.video_id}: {stats_error}")
        
        # Query the RAG service
        result = await rag_service_instance.query(
            query=request.message,
            video_id=request.video_id,
            include_visual=getattr(request, 'include_visual', True),
            max_results=getattr(request, 'max_results', 10)
        )
        
        # Check for meaningful results
        if not result.response or "No video content was provided" in result.response:
            return ChatResponse(
                response=f"I found the video but couldn't retrieve specific content for your question. Please try asking 'Summarize this video'.",
                timestamp_references=[],
                confidence=0.3,
                sources_used=[]
            )
        
        return ChatResponse(
            response=result.response,
            timestamp_references=result.timestamp_references,
            confidence=result.confidence,
            sources_used=[source.id for source in result.sources]
        )
            
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )
