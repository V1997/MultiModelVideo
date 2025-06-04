"""
RAG (Retrieval-Augmented Generation) service for video content indexing.
"""
import uuid
from typing import List, Tuple, Dict, Any, Optional

from src.core.database import get_database
from src.services.ai_service import ai_service
from src.models.video_data import VideoTranscript, VideoFrame, SearchResult, QueryResult, TranscriptChunk, FrameData
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class RAGService:
    """Service for RAG-based video content indexing and retrieval."""

    def __init__(self):
        """Initialize RAG service."""
        self.indexes = {}
        self.db = get_database()
        self.ai_service = ai_service
    
    @property
    def collection(self):
        """Get the ChromaDB collection instance."""
        if hasattr(self.db, 'collection') and self.db.collection:
            return self.db.collection
        return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            return await self.db.get_stats()
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"total_embeddings": 0}
    
    async def get_available_videos(self) -> List[Dict[str, Any]]:
        """Get list of available videos in the database."""
        try:
            if not self.db.client:
                await self.db.initialize()
            
            collection = self.db.get_collection()
            
            # Get all documents to find unique video IDs
            all_docs = collection.get(
                include=["metadatas"]
            )
            
            video_ids = set()
            if all_docs and all_docs.get('metadatas'):
                for metadata in all_docs['metadatas']:
                    if metadata and 'video_id' in metadata:
                        video_ids.add(metadata['video_id'])
            
            # Return list of video info
            available_videos = []
            for video_id in video_ids:
                available_videos.append({
                    "video_id": video_id,
                    "status": "processed"  # Assume processed if in database
                })
            
            return available_videos
            
        except Exception as e:
            logger.error(f"Error getting available videos: {e}")
            return []
    
    async def get_video_stats(self, video_id: str) -> Dict[str, Any]:
        """Get statistics for a specific video."""
        try:
            if not self.db.client:
                await self.db.initialize()
            
            collection = self.db.get_collection()
            
            # Get all documents for this video
            video_docs = collection.get(
                where={"video_id": video_id},
                include=["metadatas"]
            )
            
            transcript_count = 0
            frame_count = 0
            
            if video_docs and video_docs.get('metadatas'):
                for metadata in video_docs['metadatas']:
                    if metadata:
                        content_type = metadata.get('content_type', '')
                        if content_type == 'transcript':
                            transcript_count += 1
                        elif content_type == 'visual':
                            frame_count += 1
            
            return {
                "video_id": video_id,
                "transcript_chunks": transcript_count,
                "frame_descriptions": frame_count,
                "total_content": transcript_count + frame_count
            }
            
        except Exception as e:
            logger.error(f"Error getting video stats for {video_id}: {e}")
            return {"transcript_chunks": 0, "frame_descriptions": 0, "total_content": 0}

    async def index_video_content(
        self,
        video_id: str,
        transcript_chunks: List[VideoTranscript],
        frames: List[VideoFrame],
    ) -> bool:
        """Index video content for semantic search."""
        try:
            # Prepare data for indexing
            ids = []
            embeddings = []
            metadatas = []
            documents = []

            # Index transcript chunks
            transcript_texts = [chunk.text for chunk in transcript_chunks]
            if transcript_texts:
                transcript_embeddings = await ai_service.generate_text_embeddings(
                    transcript_texts
                )

                for i, (chunk, embedding) in enumerate(
                    zip(transcript_chunks, transcript_embeddings)
                ):
                    ids.append(f"{video_id}_transcript_{i}")
                    embeddings.append(embedding)
                    metadatas.append(
                        {
                            "video_id": video_id,
                            "content_type": "transcript",
                            "start_time": chunk.start_time,
                            "end_time": chunk.end_time,
                            "chunk_id": chunk.id,
                        }
                    )
                    documents.append(chunk.text)

            # Index frame descriptions
            frame_descriptions = []
            frame_data = []

            for frame in frames:
                if hasattr(frame, "scene_description") and frame.scene_description:
                    frame_descriptions.append(frame.scene_description)
                    frame_data.append(frame)

            if frame_descriptions:
                frame_embeddings = await ai_service.generate_text_embeddings(
                    frame_descriptions
                )

                for i, (frame, embedding) in enumerate(zip(frame_data, frame_embeddings)):
                    ids.append(f"{video_id}_frame_{i}")
                    embeddings.append(embedding)
                    metadatas.append(
                        {
                            "video_id": video_id,
                            "content_type": "visual",
                            "timestamp": frame.timestamp,
                            "frame_id": frame.id,
                            "frame_path": frame.frame_path,
                            "thumbnail_path": frame.thumbnail_path,
                        }
                    )
                    documents.append(frame.scene_description)

            # Add to vector database
            if ids:
                await self.db.add_embeddings(ids, embeddings, metadatas, documents)
                logger.info(f"Indexed {len(ids)} content pieces for video {video_id}")
                return True
            else:
                logger.warning(f"No content to index for video {video_id}")
                return False

        except Exception as e:
            logger.error(f"Error indexing video content: {e}")
            return False

    async def retrieve_relevant_content(
        self,
        query: str,
        video_id: str,
        max_results: int = 10,
        content_types: List[str] = None,
    ) -> Tuple[List[VideoTranscript], List[VideoFrame]]:
        """Retrieve relevant content for a query."""
        try:
            # Generate query embedding
            query_embeddings = await ai_service.generate_text_embeddings([query])

            # Prepare filter
            where_filter = {"video_id": video_id}
            if content_types:
                where_filter["content_type"] = {"$in": content_types}

            # Query vector database
            results = await self.db.query_embeddings(
                query_embeddings=query_embeddings,
                n_results=max_results,
                where=where_filter,
            )

            # Process results
            transcript_chunks = []
            frames = []

            if results and "metadatas" in results and results["metadatas"]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    content_type = metadata.get("content_type")
                    document = results["documents"][0][i] if i < len(results["documents"][0]) else ""

                    if content_type == "transcript":
                        transcript = VideoTranscript(
                            id=metadata.get("chunk_id", f"temp_{uuid.uuid4()}"),
                            video_id=video_id,
                            text=document,
                            start_time=metadata.get("start_time", 0),
                            end_time=metadata.get("end_time", 0),
                        )
                        transcript_chunks.append(transcript)

                    elif content_type == "visual":
                        frame = VideoFrame(
                            id=metadata.get("frame_id", f"temp_{uuid.uuid4()}"),
                            video_id=video_id,
                            timestamp=metadata.get("timestamp", 0),
                            frame_path=metadata.get("frame_path", ""),
                            thumbnail_path=metadata.get("thumbnail_path", ""),
                            scene_description=document,
                        )
                        frames.append(frame)

            logger.info(
                f"Retrieved {len(transcript_chunks)} transcript chunks and {len(frames)} frames for query: {query}"
            )
            return transcript_chunks, frames

        except Exception as e:
            logger.error(f"Error retrieving relevant content: {e}")
            return [], []

    async def search_similar_content(
        self,
        query: str,
        video_ids: List[str] = None,
        content_type: str = None,
        max_results: int = 20,
    ) -> List[SearchResult]:
        """Search for similar content across videos."""
        try:
            # Generate query embedding
            query_embeddings = await ai_service.generate_text_embeddings([query])

            # Prepare filter
            where_filter = {}
            if video_ids:
                where_filter["video_id"] = {"$in": video_ids}
            if content_type:
                where_filter["content_type"] = content_type

            # Query vector database
            results = await self.db.query_embeddings(
                query_embeddings=query_embeddings,
                n_results=max_results,
                where=where_filter if where_filter else None,
            )

            # Convert to SearchResult objects
            search_results = []

            if results and "metadatas" in results and results["metadatas"]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    distance = results["distances"][0][i] if i < len(results["distances"][0]) else 1.0
                    document = results["documents"][0][i] if i < len(results["documents"][0]) else ""

                    # Convert distance to similarity score
                    relevance_score = max(0, 1 - distance)

                    # Determine timestamp
                    timestamp = metadata.get("timestamp", 0)
                    if not timestamp and "start_time" in metadata:
                        timestamp = metadata["start_time"]

                    result = SearchResult(
                        video_id=metadata.get("video_id", ""),
                        timestamp=timestamp,
                        relevance_score=relevance_score,
                        content_type=metadata.get("content_type", "unknown"),
                        content=document,
                        thumbnail_path=metadata.get("thumbnail_path"),
                        frame_path=metadata.get("frame_path"),
                    )
                    search_results.append(result)

            # Sort by relevance
            search_results.sort(key=lambda x: x.relevance_score, reverse=True)

            logger.info(f"Found {len(search_results)} similar content pieces for query: {query}")
            return search_results

        except Exception as e:
            logger.error(f"Error searching similar content: {e}")
            return []    async def get_content_around_timestamp(
        self,
        video_id: str,
        timestamp: float,
        window_seconds: float = 30,
    ) -> Tuple[List[VideoTranscript], List[VideoFrame]]:
        """Get content around a specific timestamp."""
        try:
            start_time = max(0, timestamp - window_seconds)
            end_time = timestamp + window_seconds

            # Get all content for the video and filter by time
            all_results = await self.db.query_embeddings(
                query_embeddings=[[0] * 384],  # Dummy embedding for metadata-only query
                n_results=1000,
                where={"video_id": video_id},
            )

            transcript_chunks = []
            frames = []

            if all_results and "metadatas" in all_results and all_results["metadatas"]:
                for i, metadata in enumerate(all_results["metadatas"][0]):
                    content_type = metadata.get("content_type")
                    document = all_results["documents"][0][i] if i < len(all_results["documents"][0]) else ""

                    # Check if content is in time range
                    if content_type == "transcript":
                        start = metadata.get("start_time", 0)
                        end = metadata.get("end_time", 0)
                        if start >= start_time and end <= end_time:
                            transcript = VideoTranscript(
                                id=metadata.get("chunk_id", f"temp_{uuid.uuid4()}"),
                                video_id=video_id,
                                text=document,
                                start_time=start,
                                end_time=end,
                            )
                            transcript_chunks.append(transcript)

                    elif content_type == "visual":
                        ts = metadata.get("timestamp", 0)
                        if start_time <= ts <= end_time:
                            frame = VideoFrame(
                                id=metadata.get("frame_id", f"temp_{uuid.uuid4()}"),
                                video_id=video_id,
                                timestamp=ts,
                                frame_path=metadata.get("frame_path", ""),
                                thumbnail_path=metadata.get("thumbnail_path", ""),
                                scene_description=document,
                            )
                            frames.append(frame)

            # Sort by timestamp
            transcript_chunks.sort(key=lambda x: x.start_time)
            frames.sort(key=lambda x: x.timestamp)

            logger.info(
                f"Retrieved content around timestamp {timestamp}s: {len(transcript_chunks)} transcripts, {len(frames)} frames"
            )
            return transcript_chunks, frames

        except Exception as e:
            logger.error(f"Error getting content around timestamp: {e}")
            return [], []    async def delete_video_index(self, video_id: str) -> bool:
        """Delete all indexed content for a video."""
        try:
            await self.db.delete_video_embeddings(video_id)
            logger.info(f"Deleted index for video {video_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting video index: {e}")
            return False

    async def get_context_for_query(self, video_id: str, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Get contextual information for a query."""
        try:
            # Retrieve relevant content
            transcript_chunks, frames = await self.retrieve_relevant_content(
                query=query,
                video_id=video_id,
                max_results=max_results
            )
            
            return {
                "transcript_chunks": transcript_chunks,
                "frames": frames,
                "formatted_context": self._format_context_string(transcript_chunks, frames)
            }
            
        except Exception as e:
            logger.error(f"Error getting context for query: {e}")
            return {
                "transcript_chunks": [],
                "frames": [],
                "formatted_context": "Error retrieving context."
            }
    
    def _format_context_string(self, transcript_chunks: List[VideoTranscript], frames: List[VideoFrame]) -> str:
        """Format transcript chunks and frames into a readable context string."""
        context_parts = []
        
        # Add transcript context
        for chunk in transcript_chunks:
            context_parts.append(f"Transcript ({chunk.start_time:.1f}s): {chunk.text}")
        
        # Add visual context
        for frame in frames:
            if hasattr(frame, 'scene_description') and frame.scene_description:
                context_parts.append(f"Visual ({frame.timestamp:.1f}s): {frame.scene_description}")
        
        return "\n\n".join(context_parts) if context_parts else "No relevant context found."

    async def query(
        self, 
        query: str, 
        video_id: Optional[str] = None,
        include_visual: bool = True, 
        max_results: int = 5
    ) -> QueryResult:
        """Query the RAG system for relevant video content."""
        try:
            if not self.db.client:
                await self.db.initialize()
            
            # Generate embeddings for the query
            query_embeddings = await self.ai_service.generate_text_embeddings([query])
            if not query_embeddings or not query_embeddings[0]:
                raise Exception("Failed to generate query embeddings")
            
            # Build metadata filter for video-specific search
            where_filter = {}
            if video_id:
                where_filter["video_id"] = video_id
                logger.info(f"Filtering search to video_id: {video_id}")
            
            # Search in ChromaDB
            collection = self.db.get_collection()
            
            search_params = {
                "query_embeddings": [query_embeddings[0]],
                "n_results": max_results,
                "include": ["documents", "metadatas", "distances"]
            }
            
            if where_filter:
                search_params["where"] = where_filter
            
            results = collection.query(**search_params)
            
            logger.info(f"ChromaDB search returned {len(results.get('documents', [[]])[0])} results")
            
            # Process results
            sources = []
            context_chunks = []
            
            if results and results.get('documents') and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0] if results.get('metadatas') else [],
                    results['distances'][0] if results.get('distances') else []
                )):
                    
                    if metadata:
                        source = SearchResult(
                            content=doc,
                            timestamp=metadata.get('timestamp', 0),
                            confidence=1.0 - distance if distance else 0.8,
                            video_id=metadata.get('video_id', 'unknown'),
                            metadata=metadata
                        )
                        sources.append(source)
                        context_chunks.append(f"[{metadata.get('timestamp', 0)}s] {doc}")
            
            # Generate response using AI
            if context_chunks:
                context = "\n".join(context_chunks[:max_results])
                response = await self._generate_response(query, context, video_id)
            else:
                response = f"I couldn't find relevant content in the video to answer your question: '{query}'"
            
            return QueryResult(
                response=response,
                sources=sources,
                confidence=0.8 if sources else 0.2,
                metadata={
                    "query": query,
                    "video_id": video_id,
                    "results_found": len(sources),
                    "processing_time": 0
                }
            )
            
        except Exception as e:
            logger.error(f"RAG query error: {str(e)}")
            raise Exception(f"Failed to process query: {str(e)}")

    async def _generate_response(self, query: str, context: str, video_id: Optional[str] = None) -> str:
        """Generate AI response based on query and context."""
        try:
            video_info = f" from video {video_id}" if video_id else ""
            
            prompt = f"""Based on the following video content{video_info}, answer the user's question.

Video Content:
{context}

User Question: {query}

Please provide a helpful and accurate answer based on the video content.

Answer:"""

            # Use chat_with_video method from AI service
            response, _ = await self.ai_service.chat_with_video(
                video_id=video_id or "unknown",
                user_message=query,
                transcript_chunks=[],
                frames=[],
                conversation_history=[]
            )
            return response.strip()
            
        except Exception as e:
            logger.error(f"Response generation error: {str(e)}")
            return f"I found relevant content but encountered an error generating the response: {str(e)}"

# Global RAG service instance
rag_service = RAGService()
