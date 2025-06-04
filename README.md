# AI-Powered Video Analysis System

An intelligent video analysis platform that enables conversational interaction with videos through multimodal RAG, timestamped navigation, and visual content search using Google Gemini's multimodal capabilities.

## ✨ Features

### 🎥 Chat with Videos
- Upload videos or provide YouTube links
- Ask natural language questions about video content
- Get accurate responses based on transcript and visual analysis
- Multimodal RAG with Google Gemini for comprehensive understanding
- Real-time conversational interface with context retention

### ⏰ Timestamped Navigation
- Automatic video outline generation with timestamps
- Clickable timestamp citations in responses
- Deep-linking to specific video moments
- Section summarization and chapter navigation
- YouTube transcript extraction with timing

### 🔍 Visual Content Search
- Natural language visual queries ("red car", "sunset background", "people talking")
- Frame-level object and scene detection using Gemini Vision
- Multi-instance search across long videos
- Timestamp-based result navigation with thumbnails
- Semantic search across both text and visual content

### 🤖 AI-Powered Analysis
- Google Gemini 1.5 Pro for multimodal understanding
- Real text embeddings for semantic search
- Frame analysis and description generation
- Video summarization from multiple modalities
- Intelligent content indexing with ChromaDB

## 🛠 Technical Stack

- **AI Models**: Google Gemini 1.5 Pro (text + vision) + embedding models
- **Backend**: FastAPI with async Python
- **Vector Database**: ChromaDB for semantic embeddings
- **Video Processing**: OpenCV, MoviePy, yt-dlp
- **Transcription**: YouTube Transcript API with fallback
- **Frontend**: Modern responsive web interface

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Google Gemini API key ([Get it here](https://makersuite.google.com/app/apikey))
- 4GB+ RAM (for video processing)
- FFmpeg (for video format support)

### Quick Setup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd MultiModelVideo
```

2. **Create and activate virtual environment**:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment**:
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

5. **Run the application**:
```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Open your browser** to `http://localhost:8000`

## 📖 Usage Guide

### Video Upload & Processing
1. **Upload**: Drag and drop video files or paste YouTube URLs
2. **Processing**: System extracts frames, generates transcripts, and creates embeddings
3. **Ready**: Chat interface becomes available when processing completes

### Chat Interface
- Ask questions about video content: "What is the main topic discussed?"
- Request specific information: "When do they mention AI?"
- Visual queries: "Show me when there are people on screen"
- Get timestamped responses with clickable navigation

### Visual Search
- Use natural language: "Find scenes with text or writing"
- Object detection: "Show me cars" or "Find outdoor scenes"
- Activity search: "When are people talking or presenting?"
- Get thumbnail results with precise timestamps

## 🔧 API Reference

### Video Management
- `POST /api/videos/upload` - Upload video file
- `POST /api/videos/youtube` - Process YouTube URL
- `GET /api/videos/{video_id}` - Get video metadata
- `DELETE /api/videos/{video_id}` - Delete video and data

### Chat & Search
- `POST /api/chat/message` - Send chat message about video
- `GET /api/chat/{video_id}/history` - Get chat history
- `POST /api/search/visual` - Visual content search
- `GET /api/search/semantic` - Semantic text search

## ⚙️ Configuration

### Environment Variables
- `GEMINI_API_KEY` - **Required**: Google Gemini API key
- `MAX_VIDEO_SIZE_MB` - Maximum video size (default: 500MB)
- `FRAME_SAMPLE_RATE` - Frame extraction interval (default: 1 second)
- `DOWNLOAD_YOUTUBE_VIDEOS` - Download videos for frame analysis (default: false)

### Advanced Settings
```env
# AI Model Configuration
GEMINI_TEXT_MODEL=gemini-1.5-pro
GEMINI_VISION_MODEL=gemini-1.5-pro-vision
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# Processing Configuration
CHUNK_DURATION_SECONDS=30
MAX_CONCURRENT_PROCESSES=4
TEXT_CHUNK_SIZE=1000
```

## 🏗 Architecture

```
src/
├── api/                    # FastAPI routes and endpoints
│   ├── routes/
│   │   ├── chat.py        # Chat conversation endpoints
│   │   ├── search.py      # Visual/semantic search
│   │   └── videos.py      # Video upload/management
├── services/              # Core business services
│   ├── ai_service.py      # Google Gemini integration
│   ├── video_processor.py # Video processing pipeline
│   └── rag_service.py     # RAG and vector operations
├── models/                # Data models and schemas
├── core/                  # Database and core logic
└── utils/                 # Utility functions
```

## 🔍 Key Features Implemented

✅ **Production-Ready Google Gemini Integration**
- Text generation and embeddings
- Vision analysis for video frames
- Multimodal chat capabilities
- Quota management and error handling

✅ **Real Video Processing**
- OpenCV frame extraction
- YouTube transcript API integration
- yt-dlp video downloading (optional)
- Thumbnail generation

✅ **Semantic Search & RAG**
- ChromaDB vector storage
- Real embedding generation
- Context-aware responses
- Multimodal content indexing

✅ **Production APIs**
- Async FastAPI endpoints
- Proper error handling
- Request/response validation
- CORS configuration
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Run the application:
```bash
python -m src.main
```

## Usage

1. **Upload Video**: Drag and drop video files or paste YouTube URLs
2. **Auto-Processing**: System automatically generates transcripts and embeddings
3. **Chat Interface**: Ask questions about video content
4. **Visual Search**: Use natural language to find specific scenes
5. **Navigate**: Click timestamps to jump to relevant moments

## API Endpoints

- `POST /api/videos/upload` - Upload video file
- `POST /api/videos/youtube` - Process YouTube URL
- `POST /api/chat` - Chat with video content
- `POST /api/search/visual` - Visual content search
- `GET /api/videos/{id}/outline` - Get video outline

## Configuration

Key settings in `config.py`:
- `GEMINI_API_KEY` - Google Gemini API key
- `MAX_VIDEO_SIZE` - Maximum video file size
- `CHUNK_DURATION` - Video chunking duration
- `EMBEDDING_MODEL` - Text embedding model

## Architecture

```
src/
├── api/           # FastAPI routes and endpoints
├── core/          # Core business logic
├── models/        # Data models and schemas
├── services/      # External service integrations
├── utils/         # Utility functions
└── web/           # Frontend assets
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details
