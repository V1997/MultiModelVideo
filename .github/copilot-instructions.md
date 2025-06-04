<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# AI-Powered Video Analysis System - Copilot Instructions

## Project Overview
This is an AI-powered video analysis system that enables conversational interaction with videos through multimodal RAG, timestamped navigation, and visual content search.

## Key Technologies
- **Backend**: FastAPI with Python
- **AI Models**: Google Gemini for multimodal understanding
- **Vector Database**: ChromaDB for embeddings
- **Video Processing**: OpenCV, MoviePy, yt-dlp
- **Transcription**: YouTube Transcript API

## Code Style Guidelines
- Use Python type hints consistently
- Follow PEP 8 style guidelines
- Use async/await for I/O operations
- Implement proper error handling with try-catch blocks
- Use Pydantic models for data validation
- Document functions with docstrings

## Architecture Patterns
- Implement service layer pattern for business logic
- Use dependency injection for external services
- Separate API routes, business logic, and data models
- Use factory pattern for creating AI model instances
- Implement observer pattern for video processing events

## AI Integration Guidelines
- Use Google Gemini API for multimodal video understanding
- Implement RAG with ChromaDB for semantic search
- Process videos in chunks for efficient analysis
- Store embeddings for both text and visual content
- Use proper prompt engineering for video queries

## Video Processing Best Practices
- Handle multiple video formats (MP4, MOV, AVI, WebM)
- Implement progress tracking for long video processing
- Use frame sampling for visual analysis
- Generate thumbnails for visual search results
- Implement proper memory management for large videos

## API Design
- Use RESTful endpoints with proper HTTP methods
- Implement request/response models with Pydantic
- Add proper error handling and status codes
- Use streaming responses for long-running operations
- Implement proper authentication and rate limiting

## Frontend Integration
- Design responsive web interface with timestamp navigation
- Implement real-time chat interface
- Add drag-and-drop video upload functionality
- Create visual search results with thumbnail previews
- Implement video player with timestamp jumping
