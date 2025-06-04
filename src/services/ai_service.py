"""
AI service for video analysis using Google Gemini.
"""
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

import google.generativeai as genai
from PIL import Image
from dotenv import load_dotenv

from config.settings import settings
from src.models.video_data import FrameData, TranscriptChunk, VideoFrame, SearchResult
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class AIService:
    """Service for AI-powered video analysis using Google Gemini."""
    
    def __init__(self):
        """Initialize AI service."""
        self.gemini_text_model = None
        self.gemini_vision_model = None
        self.gemini_embedding_model = None
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini AI models."""
        try:
            load_dotenv()
            
            # Get API key from environment
            api_key = (os.getenv('GEMINI_API_KEY') or 
                      os.getenv('GOOGLE_API_KEY') or
                      getattr(settings, 'gemini_api_key', None))
            
            if not api_key:
                logger.error("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
                return
            
            genai.configure(api_key=api_key)
            
            # Initialize models
            self.gemini_text_model = genai.GenerativeModel('gemini-1.5-flash')
            self.gemini_vision_model = genai.GenerativeModel('gemini-1.5-pro')
            self.gemini_embedding_model = 'models/text-embedding-004'
            
            logger.info("Gemini AI models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini models: {e}")
            self.gemini_text_model = None
            self.gemini_vision_model = None    
    async def generate_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate text embeddings using Gemini."""
        try:
            if not self.gemini_embedding_model:
                logger.warning("Gemini embedding model not available")
                return [[0.0] * 384 for _ in texts]
            
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=self.gemini_embedding_model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result['embedding'])
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating text embeddings: {e}")
            return [[0.0] * 384 for _ in texts]
    
    async def analyze_image(self, image_path: str) -> str:
        """Analyze a single image to generate a description."""
        try:
            if not self.gemini_vision_model or not Path(image_path).exists():
                return "Image analysis not available"
            
            image = Image.open(image_path)
            prompt = """Describe what's happening in this video frame.
            Include people, main objects, actions, and setting.
            Keep it concise (1-2 sentences)."""
            
            response = self.gemini_vision_model.generate_content([image, prompt])
            return response.text.strip() if response else "Could not generate description"
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return f"Analysis failed: {str(e)}"    
    async def chat_with_video(
        self, 
        video_id: str,
        user_message: str, 
        transcript_chunks: List[TranscriptChunk] = None,
        frames: List[VideoFrame] = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> Tuple[str, List[float]]:
        """Chat with video content using multimodal RAG."""
        try:
            if not self.gemini_text_model:
                return "AI chat not available. Please configure Gemini API key.", []
            
            # Prepare context
            context_parts = []
            timestamps = []
            
            if transcript_chunks:
                context_parts.append("Transcript:")
                for chunk in transcript_chunks[:5]:
                    context_parts.append(f"[{chunk.start_time:.1f}s]: {chunk.text}")
                    timestamps.append(chunk.start_time)
            
            if frames:
                context_parts.append("Visual content:")
                for frame in frames[:3]:
                    if hasattr(frame, 'scene_description') and frame.scene_description:
                        context_parts.append(f"[{frame.timestamp:.1f}s]: {frame.scene_description}")
                        timestamps.append(frame.timestamp)
            
            # Conversation context
            conversation_context = ""
            if conversation_history:
                conversation_context = "\nPrevious conversation:\n"
                for msg in conversation_history[-3:]:
                    conversation_context += f"{msg['role']}: {msg['content']}\n"
            
            prompt = f"""You are analyzing video content. Use the provided information to answer accurately.
            
            Video Context:
            {chr(10).join(context_parts)}
            
            {conversation_context}
            
            User Question: {user_message}
            
            Answer based on the video content. Reference timestamps when relevant (format: [MM:SS]).
            """
            
            response = self.gemini_text_model.generate_content(prompt)
            response_text = response.text if response else "Unable to generate response"
            
            # Extract timestamps from response
            extracted_timestamps = self._extract_timestamps(response_text, timestamps)
            
            logger.info(f"Generated chat response for video {video_id}")
            return response_text, extracted_timestamps
            
        except Exception as e:
            logger.error(f"Error in chat with video: {e}")
            return f"Sorry, I encountered an error: {str(e)}", []
    
    def _extract_timestamps(self, response: str, available_timestamps: List[float]) -> List[float]:
        """Extract timestamp references from AI response."""
        timestamps = []
        pattern = r'\[(\d{1,2}):(\d{2})\]'
        matches = re.findall(pattern, response)
        
        for match in matches:
            minutes, seconds = int(match[0]), int(match[1])
            timestamp = minutes * 60 + seconds
            
            if available_timestamps:
                closest = min(available_timestamps, key=lambda x: abs(x - timestamp))
                if abs(closest - timestamp) <= 30:
                    timestamps.append(closest)
        
        return list(set(timestamps))    async def visual_search(self, query: str, frames: List[VideoFrame]) -> List[SearchResult]:
        """Perform visual search across video frames."""
        try:
            if not self.gemini_vision_model or not frames:
                return []
            
            search_results = []
            
            for frame in frames:
                if not hasattr(frame, 'frame_path') or not Path(frame.frame_path).exists():
                    continue
                
                # Analyze frame for the specific query
                image = Image.open(frame.frame_path)
                
                prompt = f"""Analyze this image for the following query: "{query}"
                
                Rate how well this image matches the query on a scale of 0-1.
                Provide a brief explanation of what you see that relates to the query.
                
                Format: SCORE: X.X | DESCRIPTION: your description
                """
                
                try:
                    response = self.gemini_vision_model.generate_content([prompt, image])
                    
                    # Parse response
                    score, description = self._parse_visual_search_response(response.text)
                    
                    if score > 0.3:  # Threshold for relevance
                        result = SearchResult(
                            id=f"visual_{frame.id}",
                            content=description,
                            score=score,
                            timestamp=frame.timestamp,
                            video_id=frame.video_id,
                            type="visual",
                            metadata={
                                "frame_path": frame.frame_path,
                                "thumbnail_path": getattr(frame, 'thumbnail_path', frame.frame_path),
                                "query": query
                            }
                        )
                        search_results.append(result)
                
                except Exception as e:
                    logger.warning(f"Error analyzing frame {frame.id}: {e}")
                    continue
            
            # Sort by relevance score
            search_results.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Visual search for '{query}' found {len(search_results)} matches")
            return search_results[:20]  # Return top 20 matches
            
        except Exception as e:
            logger.error(f"Error in visual search: {e}")
            return []
      def _parse_visual_search_response(self, response: str) -> Tuple[float, str]:
        """Parse visual search response to extract score and description."""
        try:
            # Look for SCORE: X.X pattern
            score_match = re.search(r'SCORE:\s*([0-9.]+)', response)
            desc_match = re.search(r'DESCRIPTION:\s*(.+)', response)
            
            score = float(score_match.group(1)) if score_match else 0.0
            description = desc_match.group(1).strip() if desc_match else response[:200]
            
            return score, description
            
        except Exception:
            # Fallback: estimate score based on response content
            response_lower = response.lower()
            if any(word in response_lower for word in ['yes', 'matches', 'visible', 'present']):
                return 0.7, response[:200]
            elif any(word in response_lower for word in ['no', 'not visible', 'absent']):
                return 0.1, response[:200]
            return 0.4, response[:200]
      async def generate_video_summary(self, transcript_chunks: List[TranscriptChunk], frames: List[FrameData]) -> str:
        """Generate video summary from transcript and frames."""
        try:
            if not self.gemini_text_model:
                return "Summary generation not available. Please configure Gemini API key."
            
            # Prepare content for summarization
            content_parts = []
            
            if transcript_chunks:
                transcript_text = " ".join([chunk.text for chunk in transcript_chunks[:10]])
                content_parts.append(f"Transcript: {transcript_text}")
            
            if frames:
                visual_descriptions = []
                for frame in frames[:5]:
                    if hasattr(frame, 'scene_description') and frame.scene_description:
                        visual_descriptions.append(frame.scene_description)
                if visual_descriptions:
                    content_parts.append(f"Visual content: {' '.join(visual_descriptions)}")
            
            if not content_parts:
                return "No content available for summary generation."
            
            prompt = f"""Create a comprehensive summary of this video based on the following content:
            
            {chr(10).join(content_parts)}
            
            Provide:
            1. Main topics covered (2-3 bullet points)
            2. Key visual elements or scenes
            3. Overall theme or purpose
            4. Duration and pacing notes
            
            Keep the summary concise but informative (3-4 sentences).
            """
            
            response = self.gemini_text_model.generate_content(prompt)
            
            summary = response.text.strip() if response else "Unable to generate summary"
            logger.info("Generated video summary")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Summary generation failed: {str(e)}"
      async def generate_detailed_frame_descriptions(self, frames: List[VideoFrame]) -> List[VideoFrame]:
        """Generate detailed scene descriptions for video frames."""
        if not frames:
            logger.warning("No frames provided for detailed analysis")
            return []
        
        try:
            # Sort frames by timestamp and select key frames
            sorted_frames = sorted(frames, key=lambda x: x.timestamp)
            total_frames = len(sorted_frames)
            
            # Select up to 10 key frames distributed across the video
            if total_frames <= 10:
                key_frames = sorted_frames
            else:
                step = total_frames // 10
                indices = [i * step for i in range(10)]
                if (total_frames - 1) not in indices:
                    indices[-1] = total_frames - 1
                key_frames = [sorted_frames[i] for i in indices]
            
            # Process each frame
            enhanced_frames = []
            for frame in key_frames:
                if not hasattr(frame, 'frame_path') or not frame.frame_path or not Path(frame.frame_path).exists():
                    logger.warning(f"Frame path not valid for frame at timestamp {frame.timestamp}")
                    enhanced_frames.append(frame)
                    continue
                
                try:
                    image = Image.open(frame.frame_path)
                    
                    prompt = """Provide a detailed description of this video frame, including:
                    1. All visible people, objects, and elements
                    2. Actions or activities occurring
                    3. Setting and environment
                    4. Text visible in the frame (if any)
                    5. Emotions or mood conveyed
                    
                    Format your answer as a detailed paragraph that could substitute for narration.
                    """
                    
                    response = self.gemini_vision_model.generate_content([image, prompt])
                    
                    if response and hasattr(response, 'text'):
                        frame.scene_description = response.text.strip()
                        logger.info(f"Generated detailed description for frame at {frame.timestamp:.2f}s")
                    else:
                        logger.warning(f"Failed to generate description for frame at {frame.timestamp:.2f}s")
                    
                except Exception as e:
                    logger.error(f"Error analyzing frame at {frame.timestamp:.2f}s: {e}")
                
                enhanced_frames.append(frame)
            
            logger.info(f"Generated {len(enhanced_frames)} enhanced frame descriptions")
            return enhanced_frames
            
        except Exception as e:
            logger.error(f"Error generating detailed frame descriptions: {e}")
            return frames

# Global instance
ai_service = AIService()
