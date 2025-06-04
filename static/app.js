// Global variables
let videos = [];
let currentVideoId = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    loadVideos();
    setupDragAndDrop();
    setupEnterKey();
});

// Setup drag and drop functionality
function setupDragAndDrop() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('videoFile');

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            document.getElementById('videoTitle').value = files[0].name.split('.')[0];
        }
    });

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            document.getElementById('videoTitle').value = e.target.files[0].name.split('.')[0];
        }
    });
}

// Setup enter key for chat
function setupEnterKey() {
    document.getElementById('chatInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
}

// Upload video
async function uploadVideo() {
    const fileInput = document.getElementById('videoFile');
    const title = document.getElementById('videoTitle').value;
    const uploadBtn = document.getElementById('uploadBtn');

    if (!fileInput.files[0]) {
        alert('Please select a video file');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    if (title) formData.append('title', title);

    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';

    try {
        const response = await fetch('/api/videos/upload', {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            showSuccess('Video uploaded successfully! Processing started.');
            fileInput.value = '';
            document.getElementById('videoTitle').value = '';
            loadVideos();
            startStatusPolling(result.id);
        } else {
            const error = await response.json();
            showError('Upload failed: ' + error.detail);
        }
    } catch (error) {
        showError('Upload failed: ' + error.message);
    } finally {
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload & Process';
    }
}

// Process YouTube video
async function processYouTube() {
    const url = document.getElementById('youtubeUrl').value;
    const title = document.getElementById('youtubeTitle').value;

    if (!url) {
        alert('Please enter a YouTube URL');
        return;
    }

    try {
        const response = await fetch('/api/videos/youtube', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                title: title || null
            })
        });

        if (response.ok) {
            const result = await response.json();
            showSuccess('YouTube video processing started!');
            document.getElementById('youtubeUrl').value = '';
            document.getElementById('youtubeTitle').value = '';
            loadVideos();
            startStatusPolling(result.id);
        } else {
            const error = await response.json();
            showError('Processing failed: ' + error.detail);
        }
    } catch (error) {
        showError('Processing failed: ' + error.message);
    }
}

// Load videos list
async function loadVideos() {
    try {
        const response = await fetch('/api/videos/');
        const data = await response.json();
        videos = data.videos || [];
        
        updateVideosList();
        updateVideoSelect();
    } catch (error) {
        console.error('Failed to load videos:', error);
    }
}

// Update videos list display
function updateVideosList() {
    const container = document.getElementById('videosList');
    
    if (videos.length === 0) {
        container.innerHTML = '<div class="col-12"><p class="text-muted text-center">No videos yet. Upload a video or process a YouTube URL to get started.</p></div>';
        return;
    }

    container.innerHTML = videos.map(video => `
        <div class="col-md-4 mb-3">
            <div class="card video-card">
                <div class="card-body">
                    <h6 class="card-title">${video.id}</h6>
                    <div class="mb-2">
                        <span class="badge ${getStatusBadgeClass(video.status)}">${video.status}</span>
                    </div>
                    ${video.status === 'processing' ? `
                        <div class="progress mb-2">
                            <div class="progress-bar" style="width: ${video.progress * 100}%"></div>
                        </div>
                        <small class="text-muted">${Math.round(video.progress * 100)}% complete</small>
                    ` : ''}
                    <div class="mt-2">
                        <button class="btn btn-sm btn-outline-primary" onclick="selectVideoForChat('${video.id}')">
                            <i class="fas fa-comments"></i> Chat
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteVideo('${video.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

// Update video select dropdown
function updateVideoSelect() {
    const select = document.getElementById('selectedVideo');
    select.innerHTML = '<option value="">Select a video to chat about</option>' +
        videos.map(video => `<option value="${video.id}">${video.id} (${video.status})</option>`).join('');
}

// Get status badge class
function getStatusBadgeClass(status) {
    switch (status) {
        case 'completed': return 'bg-success';
        case 'processing': return 'bg-warning';
        case 'failed': return 'bg-danger';
        default: return 'bg-secondary';
    }
}

// Start polling for status updates
function startStatusPolling(videoId) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/videos/${videoId}/status`);
            if (response.ok) {
                const status = await response.json();
                
                // Update the video in the list
                const videoIndex = videos.findIndex(v => v.id === videoId);
                if (videoIndex !== -1) {
                    videos[videoIndex] = {
                        id: videoId,
                        status: status.status,
                        progress: status.progress
                    };
                    updateVideosList();
                }

                // Stop polling if completed or failed
                if (status.status === 'completed' || status.status === 'failed') {
                    clearInterval(pollInterval);
                    if (status.status === 'completed') {
                        showSuccess(`Video ${videoId} processing completed!`);
                    } else {
                        showError(`Video ${videoId} processing failed: ${status.message}`);
                    }
                }
            }
        } catch (error) {
            console.error('Status polling error:', error);
        }
    }, 2000); // Poll every 2 seconds
}

// Select video for chat
function selectVideoForChat(videoId) {
    currentVideoId = videoId;
    document.getElementById('selectedVideo').value = videoId;
    
    // Clear chat
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.innerHTML = `
        <div class="message assistant-message">
            Selected video: ${videoId}. Ask me anything about this video!
        </div>
    `;
}

// Send chat message
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    const videoId = document.getElementById('selectedVideo').value;

    if (!message) return;
    if (!videoId) {
        alert('Please select a video first');
        return;
    }

    // Add user message to chat
    addMessageToChat(message, 'user');
    input.value = '';

    try {
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                video_id: videoId,
                message: message,
                chat_history: []
            })
        });

        if (response.ok) {
            const result = await response.json();
            addMessageToChat(result.response, 'assistant');
        } else {
            addMessageToChat('Sorry, I encountered an error processing your message.', 'assistant');
        }
    } catch (error) {
        addMessageToChat('Sorry, I encountered an error processing your message.', 'assistant');
    }
}

// Add message to chat
function addMessageToChat(message, sender) {
    const chatContainer = document.getElementById('chatContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.textContent = message;
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Delete video
async function deleteVideo(videoId) {
    if (!confirm('Are you sure you want to delete this video?')) return;

    try {
        const response = await fetch(`/api/videos/${videoId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showSuccess('Video deleted successfully');
            loadVideos();
        } else {
            showError('Failed to delete video');
        }
    } catch (error) {
        showError('Failed to delete video: ' + error.message);
    }
}

// Show success message
function showSuccess(message) {
    // You can implement a toast notification here
    alert(message);
}

// Show error message
function showError(message) {
    // You can implement a toast notification here
    alert(message);
}
