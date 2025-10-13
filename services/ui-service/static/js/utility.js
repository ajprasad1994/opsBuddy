// Utility Service JavaScript for OpsBuddy UI

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Add enter key support for command input
    const commandInput = document.getElementById('commandInput');
    if (commandInput) {
        commandInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                executeCommand();
            }
        });
    }
}

// Load configurations
async function loadConfigurations() {
    const configsList = document.getElementById('configsList');
    if (!configsList) return;

    configsList.innerHTML = '<div class="text-center"><div class="loading me-2"></div>Loading configurations...</div>';

    try {
        const response = await axios.get('/api/configs');
        displayConfigurations(response.data.configs || []);
    } catch (error) {
        console.error('Error loading configurations:', error);
        configsList.innerHTML = '<p class="text-danger mb-0">Error loading configurations</p>';
        showError('Failed to load configurations');
    }
}

// Display configurations
function displayConfigurations(configs) {
    const configsList = document.getElementById('configsList');
    if (!configsList) return;

    if (!configs || configs.length === 0) {
        configsList.innerHTML = '<p class="text-muted mb-0">No configurations found</p>';
        return;
    }

    configsList.innerHTML = configs.map(config => `
        <div class="config-item">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <h6 class="mb-1">${config.name || 'Unnamed'}</h6>
                    <small class="text-muted">
                        Category: ${config.category || 'N/A'} |
                        ${config.is_active ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-secondary">Inactive</span>'}
                    </small>
                    ${config.description ? `<br><small class="text-primary">${config.description}</small>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

// Create configuration
async function createConfiguration() {
    const name = document.getElementById('configName')?.value;
    const category = document.getElementById('configCategory')?.value;
    const value = document.getElementById('configValue')?.value;
    const description = document.getElementById('configDescription')?.value;

    if (!name || !category || !value) {
        showError('Please fill in all required fields');
        return;
    }

    const submitButton = document.querySelector('#createConfigForm button[type="submit"]');
    const originalText = submitButton.innerHTML;

    submitButton.innerHTML = '<span class="loading me-2"></span>Creating...';
    submitButton.disabled = true;

    try {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('category', category);
        formData.append('value', value);
        formData.append('description', description);

        const response = await axios.post('/api/configs', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });

        logResponse('Configuration Created', response.data);
        showSuccess('Configuration created successfully');

        // Reset form
        document.getElementById('createConfigForm').reset();

        // Refresh configurations list
        loadConfigurations();

    } catch (error) {
        console.error('Error creating configuration:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to create configuration';
        showError(`Failed to create configuration: ${errorMessage}`);
        logResponse('Create Configuration Error', { error: errorMessage });
    } finally {
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    }
}

// Get system information
async function getSystemInfo() {
    const systemInfoDiv = document.getElementById('systemInfo');
    const systemInfoContent = document.getElementById('systemInfoContent');

    if (!systemInfoDiv || !systemInfoContent) return;

    try {
        const response = await axios.get('/api/system/info');
        displaySystemInfo(response.data);
        logResponse('System Info Retrieved', response.data);
    } catch (error) {
        console.error('Error getting system info:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to get system info';
        showError(`Failed to get system info: ${errorMessage}`);
        logResponse('System Info Error', { error: errorMessage });
    }
}

// Display system information
function displaySystemInfo(systemInfo) {
    const systemInfoDiv = document.getElementById('systemInfo');
    const systemInfoContent = document.getElementById('systemInfoContent');

    if (systemInfoDiv && systemInfoContent) {
        systemInfoContent.textContent = JSON.stringify(systemInfo, null, 2);
        systemInfoDiv.style.display = 'block';
    }
}

// Clear system info display
function clearSystemInfo() {
    const systemInfoDiv = document.getElementById('systemInfo');
    if (systemInfoDiv) {
        systemInfoDiv.style.display = 'none';
    }
}

// Execute command
async function executeCommand() {
    const command = document.getElementById('commandInput')?.value;
    const timeout = document.getElementById('timeoutInput')?.value;

    if (!command) {
        showError('Please enter a command');
        return;
    }

    const submitButton = document.querySelector('#commandForm button[type="submit"]');
    const originalText = submitButton.innerHTML;

    submitButton.innerHTML = '<span class="loading me-2"></span>Executing...';
    submitButton.disabled = true;

    try {
        const formData = new FormData();
        formData.append('command', command);
        formData.append('timeout', timeout || 30);

        const response = await axios.post('/api/system/execute', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });

        displayCommandOutput(response.data);
        logResponse('Command Executed', response.data);

        // Clear command input
        document.getElementById('commandInput').value = '';

    } catch (error) {
        console.error('Error executing command:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to execute command';
        showError(`Command execution failed: ${errorMessage}`);
        logResponse('Command Execution Error', { error: errorMessage, command: command.substring(0, 100) + '...' });
    } finally {
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    }
}

// Display command output
function displayCommandOutput(output) {
    const commandOutputDiv = document.getElementById('commandOutput');
    const commandOutputContent = document.getElementById('commandOutputContent');

    if (commandOutputDiv && commandOutputContent) {
        commandOutputContent.textContent = JSON.stringify(output, null, 2);
        commandOutputDiv.style.display = 'block';
    }
}

// Set quick command
function setQuickCommand(command) {
    const commandInput = document.getElementById('commandInput');
    if (commandInput) {
        commandInput.value = command;
        commandInput.focus();
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