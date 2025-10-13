// File Service JavaScript for OpsBuddy UI

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupFileForm();
    setupEventListeners();
});

// Setup file upload form
function setupFileForm() {
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleFileUpload);
    }

    const createConfigForm = document.getElementById('createConfigForm');
    if (createConfigForm) {
        createConfigForm.addEventListener('submit', handleCreateConfig);
    }

    const commandForm = document.getElementById('commandForm');
    if (commandForm) {
        commandForm.addEventListener('submit', handleCommandExecution);
    }
}

// Handle file upload
async function handleFileUpload(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const submitButton = e.target.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;

    submitButton.innerHTML = '<span class="loading me-2"></span>Uploading...';
    submitButton.disabled = true;

    try {
        const response = await fetch('/api/files/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const responseData = await response.json();
        logResponse('File Upload Success', responseData);
        showSuccess('File uploaded successfully');

        // Reset form
        e.target.reset();

        // Refresh file list
        loadFiles();

    } catch (error) {
        console.error('Upload error:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Upload failed';
        logResponse('File Upload Error', { error: errorMessage });
        showError(`Upload failed: ${errorMessage}`);
    } finally {
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    }
}

// Load files list
async function loadFiles() {
    const filesList = document.getElementById('filesList');
    if (!filesList) return;

    filesList.innerHTML = '<div class="text-center"><div class="loading me-2"></div>Loading files...</div>';

    try {
        const response = await fetch('/api/files');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        displayFiles(data.files || []);
    } catch (error) {
        console.error('Error loading files:', error);
        filesList.innerHTML = '<p class="text-danger mb-0">Error loading files</p>';
        showError('Failed to load files');
    }
}

// Display files in the list
function displayFiles(files) {
    const filesList = document.getElementById('filesList');
    if (!filesList) return;

    if (!files || files.length === 0) {
        filesList.innerHTML = '<p class="text-muted mb-0">No files found</p>';
        return;
    }

    filesList.innerHTML = files.map(file => `
        <div class="file-item">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-1">${file.filename || 'Unknown File'}</h6>
                    <small class="text-muted">
                        ID: ${file.file_id || 'N/A'} |
                        Size: ${formatFileSize(file.size || 0)} |
                        Uploaded: ${formatDate(file.created_at || new Date())}
                    </small>
                    ${file.tags ? `<br><small class="text-primary">Tags: ${JSON.stringify(file.tags)}</small>` : ''}
                </div>
                <div class="ms-2">
                    <button class="btn btn-sm btn-outline-primary" onclick="getFileInfo('${file.file_id}')">
                        <i class="fas fa-info-circle"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteFile('${file.file_id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

// Get file information
async function getFileInfo(fileId = null) {
    const fileIdInput = document.getElementById('fileIdInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileInfoContent = document.getElementById('fileInfoContent');

    if (!fileId) {
        fileId = fileIdInput?.value;
    }

    if (!fileId) {
        showError('Please enter a file ID');
        return;
    }

    try {
        const response = await fetch(`/api/files/${fileId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        displayFileInfo(data);
        logResponse('File Info Retrieved', data);
    } catch (error) {
        console.error('Error getting file info:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to get file info';
        showError(`Failed to get file info: ${errorMessage}`);
        logResponse('File Info Error', { error: errorMessage, fileId });
    }
}

// Display file information
function displayFileInfo(fileInfo) {
    const fileInfoDiv = document.getElementById('fileInfo');
    const fileInfoContent = document.getElementById('fileInfoContent');

    if (fileInfoDiv && fileInfoContent) {
        fileInfoContent.textContent = JSON.stringify(fileInfo, null, 2);
        fileInfoDiv.style.display = 'block';
    }
}

// Delete file
async function deleteFile(fileId = null) {
    const fileIdInput = document.getElementById('fileIdInput');

    if (!fileId) {
        fileId = fileIdInput?.value;
    }

    if (!fileId) {
        showError('Please enter a file ID');
        return;
    }

    if (!confirm(`Are you sure you want to delete file ${fileId}?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/files/${fileId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const responseData = await response.json();
        logResponse('File Deleted', responseData);
        showSuccess('File deleted successfully');

        // Clear file info display
        const fileInfoDiv = document.getElementById('fileInfo');
        if (fileInfoDiv) {
            fileInfoDiv.style.display = 'none';
        }

        // Refresh file list
        loadFiles();

    } catch (error) {
        console.error('Error deleting file:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to delete file';
        showError(`Failed to delete file: ${errorMessage}`);
        logResponse('File Delete Error', { error: errorMessage, fileId });
    }
}

// Setup event listeners
function setupEventListeners() {
    // Add enter key support for file ID input
    const fileIdInput = document.getElementById('fileIdInput');
    if (fileIdInput) {
        fileIdInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                getFileInfo();
            }
        });
    }
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    try {
        return new Date(dateString).toLocaleString();
    } catch (e) {
        return dateString;
    }
}

// Log response to the response area
function logResponse(title, data) {
    const responseLog = document.getElementById('responseLog');
    if (!responseLog) return;

    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = 'mb-2';
    logEntry.innerHTML = `
        <small class="text-muted">[${timestamp}] ${title}:</small>
        <pre class="mt-1 mb-0"><code>${JSON.stringify(data, null, 2)}</code></pre>
    `;

    responseLog.appendChild(logEntry);
    responseLog.scrollTop = responseLog.scrollHeight;
}

// Clear response log
function clearLog() {
    const responseLog = document.getElementById('responseLog');
    if (responseLog) {
        responseLog.innerHTML = '<p class="text-muted mb-0">Responses will appear here...</p>';
    }
}

// Show notifications
function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'danger');
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}