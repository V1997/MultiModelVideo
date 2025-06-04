"""
Video processing service for handling video uploads, YouTube downloads, and analysis.
"""
import uuid
import asyncio
import re
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import cv2
import json

# Import checks
try:
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
    YOUTUBE_TRANSCRIPT_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_AVAILABLE = False

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

from src.models.video_data import VideoMetadata, VideoStatus, FrameData, TranscriptChunk, VideoChapter
from config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class VideoProcessor:
    """Service for video processing operations."""
    
    def __init__(self):
        """Initialize video processor."""
        self.storage_dir = Path(settings.storage_dir)
        self.upload_dir = Path(settings.upload_dir)
    
    def _save_metadata(self, metadata: VideoMetadata, video_dir: Path) -> None:
        """Save video metadata to JSON file."""
        try:
            metadata_dict = metadata.dict()
            # Convert datetime objects to strings for JSON serialization
            for key in ['created_at', 'updated_at']:
                if metadata_dict.get(key):
                    metadata_dict[key] = metadata_dict[key].isoformat()
            
            with open(video_dir / "metadata.json", "w") as f:
                json.dump(metadata_dict, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            raise
    
    async def process_uploaded_video(self, file_path: str, title: str) -> VideoMetadata:
        """Process an uploaded video file."""
        try:
            video_id = str(uuid.uuid4())
            video_dir = self.storage_dir / video_id
            video_dir.mkdir(parents=True, exist_ok=True)
            
            # Move file to permanent location
            new_path = video_dir / "video.mp4"
            shutil.move(file_path, str(new_path))
            
            # Create metadata
            metadata = VideoMetadata(
                id=video_id,
                title=title,
                file_path=str(new_path),
                status=VideoStatus.UPLOADED,
                upload_date=datetime.now().isoformat()
            )
            
            # Save metadata
            self._save_metadata(metadata, video_dir)
            logger.info(f"Processed uploaded video: {video_id}")
            return metadata
            
        except Exception as e:
            logger.error(f"Error processing uploaded video: {e}")
            raise
      async def process_youtube_video(self, url: str, title: Optional[str] = None) -> VideoMetadata:
        """Process a YouTube video from URL."""
        try:
            # Extract video ID from URL
            match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
            if not match:
                raise ValueError(f"Invalid YouTube URL: {url}")
            
            video_id = f"youtube_{match.group(1)}"
            video_dir = self.storage_dir / video_id
            video_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure yt-dlp
            ydl_opts = {
                'format': 'best[height<=720]',
                'outtmpl': str(video_dir / '%(title)s.%(ext)s'),
                'writeinfojson': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
            }
            
            video_path = None
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Download video if requested
                if getattr(settings, 'download_youtube_videos', False):
                    ydl.download([url])
                    for file in video_dir.glob("*"):
                        if file.suffix in ['.mp4', '.webm', '.mkv']:
                            video_path = str(file)
                            break
                
                # Create metadata
                metadata = VideoMetadata(
                    id=video_id,
                    title=info.get('title', title or "YouTube Video"),
                    source_url=url,
                    status=VideoStatus.PROCESSING if video_path else VideoStatus.TRANSCRIPT_ONLY,
                    upload_date=info.get('upload_date', datetime.now().strftime('%Y%m%d')),
                    duration=info.get('duration', 0),
                    description=info.get('description', ''),
                    file_path=video_path
                )
                
                # Save metadata
                self._save_metadata(metadata, video_dir)
                logger.info(f"Processed YouTube video: {video_id}")
                return metadata
                
        except Exception as e:
            logger.error(f"Error processing YouTube video: {e}")
            raise
      async def extract_frames(self, video_path: str, video_id: str, max_frames: int = 20) -> List[FrameData]:
        """Extract frames from video for analysis."""
        return await self.extract_video_frames(video_path, video_id, max_frames)    async def extract_youtube_transcript(self, url: str, video_id: str) -> List[TranscriptChunk]:
        """Extract transcript from YouTube video with robust error handling."""
        if not YOUTUBE_TRANSCRIPT_AVAILABLE:
            logger.warning("YouTube transcript API not available")
            return []
            
        try:
            # Extract video ID from URL
            match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
            if not match:
                logger.error(f"Could not extract video ID from URL: {url}")
                return []
            
            yt_video_id = match.group(1)
            logger.info(f"Extracting transcript for YouTube video ID: {yt_video_id}")
            
            # Try different transcript strategies
            transcript_list = self._get_best_transcript(yt_video_id)
            if not transcript_list:
                logger.error("All transcript extraction strategies failed")
                return []
            
            # Convert to our format
            chunks = []
            for i, entry in enumerate(transcript_list):
                try:
                    chunk = TranscriptChunk(
                        id=f"{video_id}_transcript_{i}",
                        text=entry.get('text', '').strip(),
                        start_time=float(entry.get('start', 0)),
                        end_time=float(entry.get('start', 0)) + float(entry.get('duration', 0))
                    )
                    if chunk.text:
                        chunks.append(chunk)
                except Exception as e:
                    logger.warning(f"Error processing transcript entry {i}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(chunks)} transcript chunks for video {video_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting transcript: {e}")
            return []
    
    def _get_best_transcript(self, yt_video_id: str):
        """Get the best available transcript using multiple strategies."""
        strategies = [
            ('English', ['en']),
            ('English variants', ['en-US', 'en-GB']),
            ('Auto-generated', None),
            ('Any available', None)
        ]
        
        for strategy_name, languages in strategies:
            try:
                logger.info(f"Trying strategy: {strategy_name}")
                
                if languages:
                    return YouTubeTranscriptApi.get_transcript(yt_video_id, languages=languages)
                elif strategy_name == 'Auto-generated':
                    return self._get_auto_transcript(yt_video_id)
                else:
                    return self._get_any_transcript(yt_video_id)
                    
            except (NoTranscriptFound, TranscriptsDisabled, Exception) as e:
                logger.info(f"{strategy_name} failed: {e}")
                continue
        
        return []
    
    def _get_auto_transcript(self, yt_video_id: str):
        """Get auto-generated transcript."""
        common_languages = ['en', 'es', 'fr', 'de', 'pt', 'it']
        for lang in common_languages:
            try:
                return YouTubeTranscriptApi.get_transcript(yt_video_id, languages=[lang])
            except:
                continue
        return []
    
    def _get_any_transcript(self, yt_video_id: str):
        """Get any available transcript."""
        try:
            transcript_obj = YouTubeTranscriptApi.list_transcripts(yt_video_id)
            
            # Try translatable transcripts first
            for transcript in transcript_obj:
                if hasattr(transcript, 'is_translatable') and transcript.is_translatable:
                    return transcript.translate('en').fetch()
            
            # Fall back to any available
            for transcript in transcript_obj:
                return transcript.fetch()
                
        except Exception:
            pass
        return []
      async def generate_video_chapters(self, video_id: str, transcript_chunks: Optional[List[TranscriptChunk]] = None) -> List[VideoChapter]:
        """Generate video chapters from content analysis."""
        try:
            if transcript_chunks:
                return self._generate_chapters_from_transcript(video_id, transcript_chunks)
            else:
                return self._generate_default_chapters(video_id)
                
        except Exception as e:
            logger.error(f"Error generating chapters: {e}")
            return []
    
    def _generate_chapters_from_transcript(self, video_id: str, transcript_chunks: List[TranscriptChunk]) -> List[VideoChapter]:
        """Generate chapters from transcript."""
        chapters = []
        for i, chunk in enumerate(transcript_chunks[:3]):
            chapters.append(VideoChapter(
                id=f"transcript_chapter_{i}",
                title=f"Section {i + 1}",
                start_time=chunk.start_time,
                end_time=chunk.end_time,
                description=chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text
            ))
        
        logger.info(f"Generated {len(chapters)} chapters from transcript for video {video_id}")
        return chapters
    
    def _generate_default_chapters(self, video_id: str) -> List[VideoChapter]:
        """Generate default chapters."""
        chapters = [
            VideoChapter(
                id=f"chapter_{i}",
                title=f"Chapter {i + 1}",
                start_time=i * 120.0,
                end_time=(i + 1) * 120.0,
                description=f"Video content - part {i + 1}"
            )
            for i in range(3)
        ]
        
        logger.info(f"Generated {len(chapters)} default chapters for video {video_id}")
        return chapters
      async def create_video_thumbnail(self, video_path: Optional[str], video_id: str) -> Optional[str]:
        """Create video thumbnail."""
        try:
            if not video_path or not Path(video_path).exists():
                return None
            
            thumbnail_dir = self.storage_dir / video_id
            thumbnail_dir.mkdir(parents=True, exist_ok=True)
            thumbnail_path = thumbnail_dir / "thumbnail.jpg"
            
            # Extract thumbnail from video
            cap = cv2.VideoCapture(str(video_path))
            if cap.isOpened():
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 10)  # 10% into video
                
                ret, frame = cap.read()
                if ret:
                    thumbnail = cv2.resize(frame, (320, 180))
                    cv2.imwrite(str(thumbnail_path), thumbnail)
                
                cap.release()
                logger.info(f"Created thumbnail for video {video_id}")
                return str(thumbnail_path)
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return None
    
    async def cleanup_temp_files(self, video_id: str):
        """Clean up temporary files."""
        try:
            temp_dir = Path(settings.temp_dir) / video_id
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp files for video {video_id}")
        except Exception as e:
            logger.error(f"Error cleaning up temp files: {e}")
      async def generate_pseudo_transcript_from_frames(self, video_id: str, frames: List[FrameData]) -> List[TranscriptChunk]:
        """Generate pseudo-transcript from frame descriptions when no captions are available."""
        try:
            if not frames:
                logger.warning(f"No frames available to generate pseudo-transcript for video {video_id}")
                return []
            
            # Analyze frames if needed
            analyzed_frames = await self.analyze_video_frames(frames, video_id)
            if not analyzed_frames:
                return []
            
            # Generate transcript chunks from frame descriptions
            chunks = []
            sorted_frames = sorted(analyzed_frames, key=lambda x: x.timestamp)
            
            for i, frame in enumerate(sorted_frames):
                if hasattr(frame, "scene_description") and frame.scene_description:
                    end_time = (sorted_frames[i+1].timestamp if i < len(sorted_frames) - 1 
                               else frame.timestamp + 5.0)
                    
                    chunk = TranscriptChunk(
                        id=f"{video_id}_visual_transcript_{i}",
                        text=f"Visual: {frame.scene_description}",
                        start_time=frame.timestamp,
                        end_time=end_time
                    )
                    chunks.append(chunk)
            
            logger.info(f"Generated {len(chunks)} pseudo-transcript chunks from frames for video {video_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error generating pseudo-transcript: {e}")
            return []
      async def extract_video_frames(self, video_path: str, video_id: str, max_frames: int = 20, sample_rate: float = 0.1) -> List[FrameData]:
        """Extract video frames with specified sampling rate."""
        try:
            if not Path(video_path).exists():
                logger.error(f"Video file not found: {video_path}")
                return []
            
            frames_dir = self.storage_dir / video_id / "frames"
            frames_dir.mkdir(parents=True, exist_ok=True)
            
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Could not open video: {video_path}")
                return []
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            if duration == 0 or total_frames == 0:
                cap.release()
                return []
            
            logger.info(f"Extracting frames from video: {duration:.2f}s, {fps:.2f} fps")
            
            # Calculate frames to extract
            frames_to_sample = min(max_frames, max(1, int(total_frames * sample_rate)))
            interval = total_frames / frames_to_sample if frames_to_sample > 0 else total_frames
            
            extracted_frames = []
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            for i in range(frames_to_sample):
                position = int(i * interval)
                cap.set(cv2.CAP_PROP_POS_FRAMES, position)
                
                ret, frame = cap.read()
                if not ret:
                    continue
                
                timestamp = position / fps
                frame_filename = f"frame_{i:04d}_{timestamp:.2f}.jpg"
                frame_path = frames_dir / frame_filename
                thumbnail_path = frames_dir / f"thumb_{frame_filename}"
                
                # Save frame and thumbnail
                cv2.imwrite(str(frame_path), frame)
                thumbnail = cv2.resize(frame, (320, 180))
                cv2.imwrite(str(thumbnail_path), thumbnail)
                
                frame_data = FrameData(
                    id=f"{video_id}_frame_{i}",
                    video_id=video_id,
                    timestamp=timestamp,
                    frame_path=str(frame_path),
                    thumbnail_path=str(thumbnail_path),
                    width=video_width,
                    height=video_height
                )
                
                extracted_frames.append(frame_data)
            
            cap.release()
            logger.info(f"Extracted {len(extracted_frames)} frames from video {video_id}")
            return extracted_frames
            
        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            return []
    
    async def analyze_video_frames(self, frames: List[FrameData], video_id: str) -> List[FrameData]:
        """Analyze video frames to generate descriptions."""
        try:
            from src.services.ai_service import ai_service
            
            if not frames:
                logger.warning(f"No frames to analyze for video {video_id}")
                return []
            
            analyzed_frames = []
            batch_size = 3
            
            for i in range(0, len(frames), batch_size):
                batch = frames[i:i+batch_size]
                logger.info(f"Analyzing batch {i//batch_size + 1} of {len(batch)} frames")
                
                for frame in batch:
                    if not hasattr(frame, 'frame_path') or not Path(frame.frame_path).exists():
                        continue
                    
                    try:
                        frame_description = await ai_service.analyze_image(frame.frame_path)
                        frame.scene_description = frame_description
                        analyzed_frames.append(frame)
                        await asyncio.sleep(1)  # Rate limiting
                    except Exception as e:
                        logger.error(f"Error analyzing frame: {e}")
                        continue
                
                # Delay between batches
                if i + batch_size < len(frames):
                    await asyncio.sleep(2)
            
            logger.info(f"Analyzed {len(analyzed_frames)} frames for video {video_id}")
            return analyzed_frames
            
        except Exception as e:
            logger.error(f"Error analyzing video frames: {e}")
            return frames
            
        
        

# Global instance
video_processor = VideoProcessor()
