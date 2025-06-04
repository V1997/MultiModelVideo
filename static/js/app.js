// Configuration for API endpoints
const API_CONFIG = {
    // For same-server setup (default)
    baseURL: window.location.origin,
    // For separate server setup, uncomment and modify:
    // baseURL: 'http://localhost:8000'
};

class VideoAnalysisApp {
    constructor() {
        this.currentVideoId = null;
        this.isProcessing = false;
        this.chatHistory = [];
        
        // Initialize API base URL
        this.apiBaseURL = API_CONFIG.baseURL;
        
        this.initializeEventListeners();
        this.setupDragAndDrop();
        
        // Debug: Log when YouTube URL input gets focus/blur
        const youtubeInput = document.getElementById('youtubeUrl');
        youtubeInput.addEventListener('input', (e) => {
            console.log('YouTube URL input value:', e.target.value);
        });
        youtubeInput.addEventListener('focus', () => {
            console.log('YouTube URL input focused');
        });
    }

    initializeEventListeners() {
        // File upload
        document.getElementById('videoFileInput').addEventListener('change', this.handleFileUpload.bind(this));
        document.getElementById('dropZone').addEventListener('click', () => {
            document.getElementById('videoFileInput').click();
        });

        // YouTube processing
        document.getElementById('processYouTubeBtn').addEventListener('click', this.handleYouTubeUpload.bind(this));
        document.getElementById('youtubeUrl').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleYouTubeUpload();
            }
        });

        // Chat functionality
        document.getElementById('sendChatBtn').addEventListener('click', this.sendChatMessage.bind(this));
        document.getElementById('chatInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendChatMessage();
            }
        });

        // Search functionality
        document.getElementById('searchBtn').addEventListener('click', this.performVisualSearch.bind(this));
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performVisualSearch();
            }
        });
    }

    setupDragAndDrop() {
        const dropZone = document.getElementById('dropZone');
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('border-blue-400', 'bg-blue-50');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-400', 'bg-blue-50');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-blue-400', 'bg-blue-50');
            
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type.startsWith('video/')) {
                this.processVideoFile(files[0]);
            } else {
                this.showNotification('Please drop a valid video file', 'error');
            }
        });
    }

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('video/')) {
            await this.processVideoFile(file);
        } else {
            this.showNotification('Please select a valid video file', 'error');
        }
    }

    async handleYouTubeUpload() {
        const url = document.getElementById('youtubeUrl').value.trim();
        if (!url) {
            this.showNotification('Please enter a YouTube URL', 'error');
            return;
        }

        if (!this.isValidYouTubeUrl(url)) {
            this.showNotification('Please enter a valid YouTube URL', 'error');
            return;
        }

        await this.processYouTubeVideo(url);
    }

    async processVideoFile(file) {
        if (this.isProcessing) return;
        
        this.isProcessing = true;
        this.showProcessingStatus(true);
        this.updateProcessingText('Uploading video...');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/videos/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.currentVideoId = result.video_id;
            
            // Start processing
            await this.startVideoProcessing();
            
        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Failed to upload video: ' + error.message, 'error');
        } finally {
            this.isProcessing = false;
            this.showProcessingStatus(false);
        }
    }    async processYouTubeVideo(url) {
        if (this.isProcessing) return;
        
        this.isProcessing = true;
        this.showProcessingStatus(true);
        
        try {
            // First validate the URL
            this.updateProcessingText('Validating YouTube URL...');
            const validateResponse = await fetch('/api/videos/youtube/validate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            if (validateResponse.ok) {
                const validation = await validateResponse.json();
                if (!validation.valid) {
                    throw new Error(`Invalid YouTube URL: ${validation.error}`);
                }
                
                // Show video info
                this.updateProcessingText(`Processing: ${validation.title}`);
            }

            // Process the video
            this.updateProcessingText('Downloading and processing YouTube video...');
            const response = await fetch('/api/videos/youtube', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = errorData.detail || `Processing failed: ${response.statusText}`;
                throw new Error(errorMessage);
            }

            const result = await response.json();
            this.currentVideoId = result.id;
            
            // Start processing pipeline
            await this.startVideoProcessing();
            
        } catch (error) {
            console.error('YouTube processing error:', error);
            
            // Provide helpful error messages
            let userMessage = error.message;
            if (error.message.includes('403') || error.message.includes('Forbidden')) {
                userMessage = 'YouTube blocked the download. This video may be restricted or protected. Try uploading the video file directly instead.';
            } else if (error.message.includes('404') || error.message.includes('not found')) {
                userMessage = 'YouTube video not found. Please check the URL and try again.';
            } else if (error.message.includes('precondition check failed')) {
                userMessage = 'YouTube is temporarily blocking downloads. Please try again later or upload the video file directly.';
            }
            
            this.showNotification(userMessage, 'error');
        } finally {
            this.isProcessing = false;
            this.showProcessingStatus(false);
        }
    }

    async startVideoProcessing() {
        this.updateProcessingText('Analyzing video content...');
        this.updateProgressBar(20);

        try {
            // Process the video
            const processResponse = await fetch(`/api/videos/${this.currentVideoId}/process`, {
                method: 'POST'
            });

            if (!processResponse.ok) {
                throw new Error(`Processing failed: ${processResponse.statusText}`);
            }

            this.updateProcessingText('Extracting frames and features...');
            this.updateProgressBar(50);

            // Wait a bit for processing to complete
            await new Promise(resolve => setTimeout(resolve, 2000));

            this.updateProcessingText('Generating embeddings...');
            this.updateProgressBar(80);

            // Get video details
            const videoResponse = await fetch(`/api/videos/${this.currentVideoId}`);
            if (videoResponse.ok) {
                const videoData = await videoResponse.json();
                this.displayVideo(videoData);
                this.enableChat();
                this.enableSearch();
            }

            this.updateProgressBar(100);
            this.updateProcessingText('Processing complete!');
            
            // Hide processing status after a delay
            setTimeout(() => {
                this.showProcessingStatus(false);
            }, 1500);

        } catch (error) {
            console.error('Processing error:', error);
            this.showNotification('Failed to process video: ' + error.message, 'error');
        }
    }

    displayVideo(videoData) {
        // Show video player section
        const videoSection = document.getElementById('videoPlayerSection');
        videoSection.classList.remove('hidden');

        // Set video source
        const videoPlayer = document.getElementById('videoPlayer');
        videoPlayer.src = videoData.file_path || videoData.url;

        // Display video information
        const videoDetails = document.getElementById('videoDetails');
        videoDetails.innerHTML = `
            <div><strong>Title:</strong> ${videoData.title || 'Unknown'}</div>
            <div><strong>Duration:</strong> ${this.formatDuration(videoData.duration)}</div>
            <div><strong>Format:</strong> ${videoData.format || 'Unknown'}</div>
            <div><strong>Size:</strong> ${videoData.file_size ? this.formatFileSize(videoData.file_size) : 'Unknown'}</div>
        `;

        // Display chapters if available
        if (videoData.chapters && videoData.chapters.length > 0) {
            this.displayChapters(videoData.chapters);
        }

        // Initialize chat with welcome message
        this.addChatMessage('system', 'Video processed successfully! You can now ask me questions about the content.');
    }

    displayChapters(chapters) {
        const chapterSection = document.getElementById('chapterSection');
        const chapterList = document.getElementById('chapterList');
        
        chapterSection.classList.remove('hidden');
        
        chapterList.innerHTML = chapters.map(chapter => `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer"
                 onclick="app.jumpToTimestamp(${chapter.start_time})">
                <div>
                    <div class="font-medium text-gray-800">${chapter.title}</div>
                    <div class="text-sm text-gray-600">${chapter.description || ''}</div>
                </div>
                <div class="text-sm text-blue-600 font-mono">
                    ${this.formatTimestamp(chapter.start_time)}
                </div>
            </div>
        `).join('');
    }

    async sendChatMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message || !this.currentVideoId) return;

        input.value = '';
        this.addChatMessage('user', message);        try {
            const response = await fetch('/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_id: this.currentVideoId,
                    message: message
                })
            });

            if (!response.ok) {
                throw new Error(`Chat failed: ${response.statusText}`);
            }

            const result = await response.json();
            this.addChatMessage('assistant', result.response, result.timestamp_citations);

        } catch (error) {
            console.error('Chat error:', error);
            this.addChatMessage('system', 'Sorry, I encountered an error. Please try again.');
        }
    }

    async performVisualSearch() {
        const input = document.getElementById('searchInput');
        const query = input.value.trim();
        
        if (!query || !this.currentVideoId) return;

        try {
            const response = await fetch('/api/search/visual', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_id: this.currentVideoId,
                    query: query
                })
            });

            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`);
            }

            const results = await response.json();
            this.displaySearchResults(results.results);

        } catch (error) {
            console.error('Search error:', error);
            this.showNotification('Search failed: ' + error.message, 'error');
        }
    }

    displaySearchResults(results) {
        const searchResults = document.getElementById('searchResults');
        const searchThumbnails = document.getElementById('searchThumbnails');
        
        if (results.length === 0) {
            searchResults.classList.add('hidden');
            this.showNotification('No visual matches found for your search', 'info');
            return;
        }

        searchResults.classList.remove('hidden');
        
        searchThumbnails.innerHTML = results.map(result => `
            <div class="thumbnail-item" onclick="app.jumpToTimestamp(${result.timestamp})">
                <img src="${result.thumbnail_path}" alt="Frame at ${this.formatTimestamp(result.timestamp)}" 
                     class="w-full h-24 object-cover">
                <div class="p-2 bg-white">
                    <div class="text-xs font-mono text-blue-600">${this.formatTimestamp(result.timestamp)}</div>
                    <div class="text-xs text-gray-600 mt-1">${result.description || 'Visual match'}</div>
                    <div class="text-xs text-green-600 mt-1">Score: ${(result.similarity_score * 100).toFixed(1)}%</div>
                </div>
            </div>
        `).join('');
    }

    addChatMessage(role, content, citations = null) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message mb-4 ${role === 'user' ? 'text-right' : ''}`;

        let citationsHtml = '';
        if (citations && citations.length > 0) {
            citationsHtml = `
                <div class="mt-2 text-xs text-gray-500">
                    <strong>Referenced timestamps:</strong>
                    ${citations.map(ts => `
                        <span class="timestamp-link ml-2" onclick="app.jumpToTimestamp(${ts})">
                            ${this.formatTimestamp(ts)}
                        </span>
                    `).join('')}
                </div>
            `;
        }

        messageDiv.innerHTML = `
            <div class="inline-block max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                role === 'user' 
                    ? 'bg-blue-600 text-white' 
                    : role === 'system'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-gray-200 text-gray-800'
            }">
                <div class="text-sm">${this.formatMessage(content)}</div>
                ${citationsHtml}
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    jumpToTimestamp(timestamp) {
        const videoPlayer = document.getElementById('videoPlayer');
        if (videoPlayer) {
            videoPlayer.currentTime = timestamp;
            videoPlayer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    enableChat() {
        document.getElementById('chatInput').disabled = false;
        document.getElementById('sendChatBtn').disabled = false;
    }

    enableSearch() {
        document.getElementById('searchInput').disabled = false;
        document.getElementById('searchBtn').disabled = false;
    }

    showProcessingStatus(show) {
        const status = document.getElementById('processingStatus');
        if (show) {
            status.classList.remove('hidden');
        } else {
            status.classList.add('hidden');
        }
    }

    updateProcessingText(text) {
        document.getElementById('processingText').textContent = text;
    }

    updateProgressBar(percentage) {
        document.getElementById('progressBar').style.width = `${percentage}%`;
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 px-6 py-3 rounded-lg text-white z-50 ${
            type === 'error' ? 'bg-red-600' : 
            type === 'success' ? 'bg-green-600' : 
            'bg-blue-600'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    formatMessage(content) {
        // Simple markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    formatDuration(seconds) {
        if (!seconds) return 'Unknown';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    formatTimestamp(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    formatFileSize(bytes) {
        if (!bytes) return 'Unknown';
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    isValidYouTubeUrl(url) {
        const regex = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)/;
        return regex.test(url);
    }
}

// Initialize the application
const app = new VideoAnalysisApp();

// Export for global access
window.app = app;
