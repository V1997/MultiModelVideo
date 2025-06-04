"""
Video management API routes.
"""
import asyncio
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse

from config.settings import settings
from src.models.video_data import (
    VideoMetadata, YouTubeRequest, VideoOutlineResponse, 
    ProcessingStatus, VideoAnalysisResult, VideoStatus
)
from src.services.video_processor import video_processor
from src.services.ai_service import ai_service
from src.services.rag_service import rag_service
from src.utils.file_utils import validate_video_file, ensure_directory
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()

# Store processing status
processing_status = {}

def _update_metadata_status(video_id: str, status: str, error: str = None):
    """Update video metadata with processing status."""
    metadata_path = Path(settings.storage_dir) / video_id / "metadata.json"
    if metadata_path.exists():
        try:
            import json
            with open(metadata_path, "r") as f:
                metadata_dict = json.load(f)
            
            metadata_dict["status"] = status
            metadata_dict["updated_at"] = datetime.now().isoformat()
            if error:
                metadata_dict["error"] = error
            
            with open(metadata_path, "w") as f:
                json.dump(metadata_dict, f, indent=2)
            
            logger.info(f"Updated metadata for video {video_id} with {status} status")
        except Exception as e:
            logger.error(f"Error updating metadata for {video_id}: {e}")

async def process_video_pipeline(video_id: str, metadata: VideoMetadata):
    """Background task to process video through the full pipeline."""
    try:
        # Import VideoStatus here to avoid NameError
        from src.models.video_data import VideoStatus
        
        processing_status[video_id] = {
            "status": "processing",
            "progress": 0.1,
            "message": "Starting video processing..."
        }
        
        frames = []
        
        # Handle transcript-only videos differently
        if metadata.status == VideoStatus.TRANSCRIPT_ONLY:
            processing_status[video_id].update({
                "progress": 0.3,
                "message": "Processing transcript-only video..."
            })
            logger.info(f"Processing transcript-only video {video_id}")
        else:
            # Extract frames for regular videos
            logger.info(f"Extracting frames for video {video_id}")
            if metadata.file_path and Path(metadata.file_path).exists():
                frames = await video_processor.extract_frames(metadata.file_path, video_id)
                processing_status[video_id].update({
                    "progress": 0.3,
                    "message": "Frames extracted, analyzing content..."
                })                # Analyze frames with AI using simplified processing
                await _analyze_frames_with_ai(frames, video_id, processing_status)
            else:
                logger.warning(f"Video file not found for {video_id}, processing as transcript-only")
        
        processing_status[video_id].update({
            "progress": 0.6,
            "message": "Extracting transcript..."
        })
          # Extract transcript
        transcript_chunks = []
        if metadata.source_url:  # YouTube video
            transcript_chunks = await video_processor.extract_youtube_transcript(
                metadata.source_url, video_id
            )
        
        processing_status[video_id].update({
            "progress": 0.7,
            "message": "Processing video content..."
        })
        
        # If no transcript was found, but we have video frames with descriptions,
        # generate a pseudo-transcript from frame descriptions
        if not transcript_chunks and (metadata.status != VideoStatus.TRANSCRIPT_ONLY):
            # First process video frames
            frames = []
            
            # Only analyze frames if we have the video file
            if metadata.file_path and Path(metadata.file_path).exists():
                processing_status[video_id].update({
                    "message": "No transcript found. Analyzing video frames..."
                })
                
                # Sample frames (limited number to avoid processing too many)
                sampled_frames = await video_processor.extract_video_frames(
                    metadata.file_path, video_id, max_frames=20, sample_rate=0.05
                )
                
                # Process frames with AI to get descriptions
                if sampled_frames:
                    processing_status[video_id].update({
                        "message": "Generating frame descriptions..."
                    })
                    frames = await video_processor.analyze_video_frames(sampled_frames, video_id)
                    
                    # Generate pseudo-transcript from frame descriptions
                    if frames:
                        transcript_chunks = await video_processor.generate_pseudo_transcript_from_frames(
                            video_id, frames
                        )
                        logger.info(f"Generated pseudo-transcript with {len(transcript_chunks)} chunks from visual content")
        
        processing_status[video_id].update({
            "progress": 0.8,
            "message": "Generating chapters..."
        })
        
        # Generate chapters
        if metadata.status != VideoStatus.TRANSCRIPT_ONLY and metadata.file_path:
            chapters = await video_processor.generate_video_chapters(
                metadata.file_path, video_id, transcript_chunks
            )
        else:
            # Generate chapters from transcript only
            chapters = await video_processor.generate_chapters_from_transcript(
                video_id, transcript_chunks
            )
        
        processing_status[video_id].update({
            "progress": 0.8,
            "message": "Creating embeddings and indexing..."
        })
          # Index content for RAG
        indexed = await rag_service.index_video_content(video_id, transcript_chunks, frames)
        
        # Add a note if no transcript was found
        if not transcript_chunks:
            processing_status[video_id].update({
                "note": "No transcripts were found for this video. Limited search capabilities may be available based on visual content."
            })
        
        processing_status[video_id].update({
            "progress": 0.9,
            "message": "Generating summary..."
        })
        
        # Generate summary
        summary = await ai_service.generate_video_summary(transcript_chunks, frames)
        
        # Create thumbnail
        thumbnail_path = await video_processor.create_video_thumbnail(
            metadata.file_path, video_id
        )
        metadata.thumbnail_path = thumbnail_path
          # Update final status
        processing_status[video_id] = {
            "status": "completed",
            "progress": 1.0,
            "message": "Video processing completed successfully"
        }
        
        # Update metadata to include processing completion status
        metadata_path = Path(settings.storage_dir) / video_id / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    import json
                    metadata_dict = json.load(f)
                
                # Update metadata
                metadata_dict["status"] = "completed"
                metadata_dict["updated_at"] = datetime.now().isoformat()
                
                with open(metadata_path, "w") as f:
                    json.dump(metadata_dict, f, indent=2)
                    
                logger.info(f"Updated metadata for video {video_id} with completed status")
            except Exception as e:                logger.error(f"Error updating metadata for {video_id}: {e}")
        
        # Clean up temp files
        await video_processor.cleanup_temp_files(video_id)
        
        logger.info(f"Video {video_id} processing completed successfully")
    
    except Exception as e:
        logger.error(f"Error processing video {video_id}: {e}")
        processing_status[video_id] = {
            "status": "failed",
            "progress": 0.0,
            "message": f"Processing failed: {str(e)}"
        }
        
        # Update metadata to include failure status
        metadata_path = Path(settings.storage_dir) / video_id / "metadata.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    import json
                    metadata_dict = json.load(f)
                
                # Update metadata
                metadata_dict["status"] = "failed"
                metadata_dict["updated_at"] = datetime.now().isoformat()
                metadata_dict["error"] = str(e)
                
                with open(metadata_path, "w") as f:
                    json.dump(metadata_dict, f, indent=2)
                    
                logger.info(f"Updated metadata for video {video_id} with failure status")
            except Exception as err:
                logger.error(f"Error updating metadata for {video_id}: {err}")


@router.post("/upload", response_model=VideoMetadata)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None)
):
    """Upload and process a video file."""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Save uploaded file temporarily
        upload_dir = Path(settings.upload_dir)
        ensure_directory(upload_dir)
        
        temp_path = upload_dir / f"temp_{uuid.uuid4()}_{file.filename}"
        
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Validate video file
        validation = validate_video_file(str(temp_path))
        if not validation["valid"]:
            temp_path.unlink()  # Clean up
            raise HTTPException(status_code=400, detail=validation["error"])
        
        # Process video
        metadata = await video_processor.process_uploaded_video(
            str(temp_path), title or file.filename
        )
        
        # Start background processing
        background_tasks.add_task(process_video_pipeline, metadata.id, metadata)
        
        # Clean up temp file
        temp_path.unlink()
        
        return metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/youtube", response_model=VideoMetadata)
async def process_youtube_video(
    request: YouTubeRequest,
    background_tasks: BackgroundTasks
):
    """Process a YouTube video."""
    try:
        # Process YouTube video
        metadata = await video_processor.process_youtube_video(
            request.url, request.title
        )
        
        # Start background processing
        background_tasks.add_task(process_video_pipeline, metadata.id, metadata)
        
        return metadata
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error processing YouTube video: {error_message}")
        
        # Provide more specific error messages based on the error type
        if "403" in error_message or "Forbidden" in error_message:
            detail = "YouTube video download failed due to access restrictions. This video may be age-restricted, region-locked, or protected by YouTube's anti-bot measures. Try using a different video or upload the video file directly."
        elif "404" in error_message or "not found" in error_message.lower():
            detail = "YouTube video not found. Please check that the URL is correct and the video is publicly accessible."
        elif "transcript" in error_message.lower() and "download" not in error_message.lower():
            detail = "Video download failed, but transcript extraction might still be possible. Please try again or use a different video."
        elif "precondition check failed" in error_message.lower() or "bot" in error_message.lower() or "sign in to confirm" in error_message.lower():
            detail = "YouTube is asking for authentication. The system will try to use your browser cookies for authentication. If this fails, please upload the video file directly."
        else:
            detail = f"Error processing YouTube video: {error_message}"
        
        raise HTTPException(status_code=500, detail=detail)


@router.post("/youtube/validate")
async def validate_youtube_url(request: YouTubeRequest):
    """Validate a YouTube URL and get basic info without downloading."""
    try:
        import yt_dlp
        
        # Extract basic info without downloading
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False)
        
        return {
            "valid": True,
            "title": info.get('title', 'Unknown'),
            "duration": info.get('duration', 0),
            "description": info.get('description', '')[:200] + "..." if info.get('description', '') else "",
            "uploader": info.get('uploader', 'Unknown'),
            "view_count": info.get('view_count', 0),
            "availability": info.get('availability', 'unknown')
        }
        
    except Exception as e:
        logger.warning(f"YouTube URL validation failed: {e}")
        return {
            "valid": False,
            "error": str(e)
        }


@router.get("/{video_id}/status", response_model=ProcessingStatus)
async def get_processing_status(video_id: str):
    """Get video processing status."""
    # First check the in-memory status
    if video_id in processing_status:
        status_data = processing_status[video_id]
        return ProcessingStatus(
            video_id=video_id,
            status=status_data["status"],
            progress=status_data["progress"],
            message=status_data.get("message"),
            note=status_data.get("note")
        )
    
    # If not in memory, check if the video exists in storage
    video_dir = Path(settings.storage_dir) / video_id
    metadata_path = video_dir / "metadata.json"
    
    if video_dir.exists() and metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                import json
                metadata_dict = json.load(f)
                
            # Create a status entry for this video
            processing_status[video_id] = {
                "status": "completed" if metadata_dict.get("status") != "processing" else "processing",
                "progress": 1.0 if metadata_dict.get("status") != "processing" else 0.5,
                "message": "Video is available"
            }
            
            return ProcessingStatus(
                video_id=video_id,
                status=processing_status[video_id]["status"],
                progress=processing_status[video_id]["progress"],
                message=processing_status[video_id]["message"]
            )
        except Exception as e:
            logger.error(f"Error reading metadata for {video_id}: {e}")
    
    raise HTTPException(status_code=404, detail="Video not found")


@router.get("/{video_id}/outline", response_model=VideoOutlineResponse)
async def get_video_outline(video_id: str):
    """Get video outline with chapters."""
    try:
        # This is a simplified implementation
        # In production, you'd load from database
        if video_id not in processing_status:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # For now, return a mock outline
        # In production, load from storage
        return VideoOutlineResponse(
            video_id=video_id,
            title="Sample Video",
            duration=300.0,
            chapters=[],
            summary="Video outline will be available after processing completes."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video outline: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{video_id}/thumbnail")
async def get_video_thumbnail(video_id: str):
    """Get video thumbnail."""
    try:
        thumbnail_path = Path(settings.storage_dir) / video_id / "thumbnail.jpg"
        
        if not thumbnail_path.exists():
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        return FileResponse(
            path=str(thumbnail_path),
            media_type="image/jpeg",
            filename=f"{video_id}_thumbnail.jpg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving thumbnail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{video_id}/frame/{frame_id}")
async def get_video_frame(video_id: str, frame_id: str):
    """Get a specific video frame."""
    try:
        frame_path = Path(settings.storage_dir) / video_id / "frames" / f"{frame_id}.jpg"
        
        if not frame_path.exists():
            # Try thumbnail
            frame_path = Path(settings.storage_dir) / video_id / "frames" / f"{frame_id}_thumb.jpg"
        
        if not frame_path.exists():
            raise HTTPException(status_code=404, detail="Frame not found")
        
        return FileResponse(
            path=str(frame_path),
            media_type="image/jpeg",
            filename=f"{frame_id}.jpg"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving frame: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{video_id}")
async def delete_video(video_id: str):
    """Delete a video and all associated data."""
    try:
        # Delete from vector database
        await rag_service.delete_video_index(video_id)
        
        # Delete files
        video_dir = Path(settings.storage_dir) / video_id
        if video_dir.exists():
            import shutil
            shutil.rmtree(video_dir)
        
        # Remove from processing status
        if video_id in processing_status:
            del processing_status[video_id]
        
        return {"message": f"Video {video_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting video: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/")
async def list_videos():
    """List all videos."""
    try:
        # In production, this would query a proper database
        videos = []
        storage_dir = Path(settings.storage_dir)
        
        if storage_dir.exists():
            for video_dir in storage_dir.iterdir():
                if video_dir.is_dir():
                    video_id = video_dir.name
                    # Check if video is in processing status
                    if video_id in processing_status:
                        status = processing_status[video_id]
                        videos.append({
                            "id": video_id,
                            "status": status.get("status", "unknown"),
                            "progress": status.get("progress", 0.0)
                        })
                    else:
                        # Check if metadata exists
                        metadata_path = video_dir / "metadata.json"
                        if metadata_path.exists():
                            try:
                                with open(metadata_path, "r") as f:
                                    import json
                                    metadata_dict = json.load(f)
                                
                                # Update processing status for future reference
                                processing_status[video_id] = {
                                    "status": "completed" if metadata_dict.get("status") != "processing" else "processing",
                                    "progress": 1.0 if metadata_dict.get("status") != "processing" else 0.5,
                                    "message": f"Video {metadata_dict.get('title', 'Unknown')} is available"
                                }
                                
                                videos.append({
                                    "id": video_id,
                                    "status": processing_status[video_id]["status"],
                                    "progress": processing_status[video_id]["progress"],
                                    "title": metadata_dict.get("title", "Unknown")
                                })
                            except Exception as e:
                                logger.error(f"Error loading metadata for {video_id}: {e}")
                                videos.append({
                                    "id": video_id,
                                    "status": "unknown",
                                    "progress": 0.0
                                })
                        else:
                            videos.append({
                                "id": video_id,
                                "status": "unknown",
                                "progress": 0.0
                            })
        
        # Sort videos by ID
        videos.sort(key=lambda v: v["id"])
        
        return {"videos": videos}
        
    except Exception as e:
        logger.error(f"Error listing videos: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def _analyze_frames_with_ai(frames: List, video_id: str, processing_status: dict):
    """Analyze video frames with AI service."""
    try:
        total_frames = len(frames)
        processed_frames = 0
        
        for i, frame in enumerate(frames):
            try:
                # Analyze frame
                analysis = await ai_service.analyze_image(frame.frame_path)
                
                if analysis:
                    frame.scene_description = analysis.get("description", "")
                    frame.objects_detected = analysis.get("objects", [])
                else:
                    frame.scene_description = "Analysis failed"
                    frame.objects_detected = []
                
                processed_frames += 1
                
                # Update progress
                progress = 0.3 + (0.3 * processed_frames / total_frames)
                processing_status[video_id]["progress"] = progress
                
                # Small delay between frames
                if i < len(frames) - 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error analyzing frame {frame.id}: {e}")
                frame.scene_description = "Analysis failed"
                frame.objects_detected = []
                processed_frames += 1
                
    except Exception as e:
        logger.error(f"Error in frame analysis: {e}")




@router.post("/{video_id}/process")
async def process_specific_video(video_id: str, background_tasks: BackgroundTasks):
    """Process a specific video that has been uploaded."""
    try:
        # Check if the video exists
        video_dir = Path(settings.storage_dir) / video_id
        if not video_dir.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        video_path = video_dir / "video.mp4"
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video file not found")
        
        # Get or create metadata
        try:
            with open(video_dir / "metadata.json", "r") as f:
                import json
                metadata_dict = json.load(f)
                # Convert dict to VideoMetadata
                from src.models.video_data import VideoMetadata, VideoStatus
                metadata = VideoMetadata(**metadata_dict)
            logger.info(f"Loaded metadata for video {video_id}")
        except (FileNotFoundError, json.JSONDecodeError):
            # Create new metadata if not found
            metadata = VideoMetadata(
                id=video_id,
                title=f"Video {video_id}",
                file_path=str(video_path),
                thumbnail_path=str(video_dir / "thumbnail.jpg") if (video_dir / "thumbnail.jpg").exists() else None,
                status=VideoStatus.UPLOADED,  # Assuming VideoStatus is an Enum in video_data.py
                upload_date=datetime.now().isoformat(),
                duration=None  # Will be populated during processing
            )
            logger.info(f"Created new metadata for video {video_id}")
        
        # Start background processing
        background_tasks.add_task(process_video_pipeline, video_id, metadata)
        
        return {"message": f"Processing started for video {video_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing video {video_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{video_id}", response_model=VideoMetadata)
async def get_video_metadata(video_id: str):
    """Get video metadata."""
    try:
        # Check if the video directory exists
        video_dir = Path(settings.storage_dir) / video_id
        metadata_path = video_dir / "metadata.json"
        
        if not video_dir.exists() or not metadata_path.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Load metadata
        try:
            with open(metadata_path, "r") as f:
                import json
                metadata_dict = json.load(f)
            
            return VideoMetadata(**metadata_dict)
            
        except Exception as e:
            logger.error(f"Error loading metadata for {video_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Error loading metadata: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video metadata: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
