// System Operations JavaScript for OpsBuddy UI

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadServicesStatus();
    setupEventListeners();
});

// Load all services status
async function loadServicesStatus() {
    try {
        const response = await axios.get('/api/services/status');
        displayServicesStatus(response.data);
    } catch (error) {
        console.error('Error loading services status:', error);
        showError('Failed to load services status');
    }
}

// Display services status in dashboard
function displayServicesStatus(services) {
    const container = document.getElementById('servicesStatus');
    if (!container) return;

    container.innerHTML = Object.entries(services).map(([serviceName, service]) => {
        const statusClass = service.status === 'healthy' ? 'success' :
                           service.status === 'unhealthy' ? 'danger' : 'warning';

        return `
            <div class="col-md-6 mb-3">
                <div class="service-status-card ${service.status}">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${formatServiceName(serviceName)}</h6>
                            <small class="text-muted">
                                Status: <strong>${service.status.toUpperCase()}</strong>
                            </small>
                        </div>
                        <span class="status-indicator status-${service.status}"></span>
                    </div>
                    ${service.error ? `<small class="text-danger">${service.error}</small>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// Setup event listeners
function setupEventListeners() {
    // Add enter key support for system command input
    const systemCommand = document.getElementById('systemCommand');
    if (systemCommand) {
        systemCommand.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                executeSystemCommand();
            }
        });
    }
}

// Execute system command
async function executeSystemCommand() {
    const command = document.getElementById('systemCommand')?.value;
    const timeout = document.getElementById('commandTimeout')?.value;

    if (!command) {
        showError('Please enter a command');
        return;
    }

    const button = event.target;
    const originalText = button.innerHTML;

    button.innerHTML = '<span class="loading me-2"></span>Executing...';
    button.disabled = true;

    try {
        const formData = new FormData();
        formData.append('command', command);
        formData.append('timeout', timeout || 30);

        const response = await axios.post('/api/system/execute', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });

        displaySystemCommandOutput(response.data);
        logResponse('System Command Executed', response.data);

        // Clear command input
        document.getElementById('systemCommand').value = '';

    } catch (error) {
        console.error('Error executing system command:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to execute command';
        showError(`Command execution failed: ${errorMessage}`);
        logResponse('System Command Error', { error: errorMessage, command: command.substring(0, 100) + '...' });
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Display system command output
function displaySystemCommandOutput(output) {
    const outputDiv = document.getElementById('systemCommandOutput');
    const outputContent = document.getElementById('systemCommandOutputContent');

    if (outputDiv && outputContent) {
        outputContent.textContent = JSON.stringify(output, null, 2);
        outputDiv.style.display = 'block';
    }
}

// Set quick command for system operations
function setQuickCommand(command) {
    const systemCommand = document.getElementById('systemCommand');
    if (systemCommand) {
        systemCommand.value = command;
        systemCommand.focus();
    }
}

// Get detailed system information
async function getDetailedSystemInfo() {
    const systemInfoDiv = document.getElementById('detailedSystemInfo');
    const systemInfoContent = document.getElementById('detailedSystemInfoContent');

    if (!systemInfoDiv || !systemInfoContent) return;

    const button = event.target;
    const originalText = button.innerHTML;

    button.innerHTML = '<span class="loading me-2"></span>Loading...';
    button.disabled = true;

    try {
        const response = await axios.get('/api/system/info');
        displayDetailedSystemInfo(response.data);
        logResponse('Detailed System Info Retrieved', response.data);
    } catch (error) {
        console.error('Error getting detailed system info:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to get system info';
        showError(`Failed to get system info: ${errorMessage}`);
        logResponse('System Info Error', { error: errorMessage });
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Display detailed system information
function displayDetailedSystemInfo(systemInfo) {
    const systemInfoDiv = document.getElementById('detailedSystemInfo');
    const systemInfoContent = document.getElementById('detailedSystemInfoContent');

    if (systemInfoDiv && systemInfoContent) {
        systemInfoContent.textContent = JSON.stringify(systemInfo, null, 2);
        systemInfoDiv.style.display = 'block';
    }
}

// Individual service health checks
async function checkGateway() {
    await checkIndividualService('gateway', 'Gateway');
}

async function checkFileService() {
    await checkIndividualService('file-service', 'File Service');
}

async function checkUtilityService() {
    await checkIndividualService('utility-service', 'Utility Service');
}

async function checkUIService() {
    await checkIndividualService('ui-service', 'UI Service');
}

// Check individual service
async function checkIndividualService(serviceName, displayName) {
    try {
        let url;
        switch (serviceName) {
            case 'gateway':
                url = `${SERVICE_URLS.gateway}/health`;
                break;
            case 'file-service':
                url = `${SERVICE_URLS['file-service']}/health`;
                break;
            case 'utility-service':
                url = `${SERVICE_URLS['utility-service']}/health`;
                break;
            case 'ui-service':
                url = '/health';
                break;
        }

        const response = await axios.get(url);
        const status = response.data.status === 'healthy' || response.data.status === 'running' ? 'healthy' : 'unhealthy';

        displayHealthResult(displayName, status, response.data);
        logResponse(`${displayName} Health Check`, response.data);

    } catch (error) {
        console.error(`Error checking ${serviceName}:`, error);
        const errorMessage = error.response?.data?.detail || error.message || 'Health check failed';
        displayHealthResult(displayName, 'error', { error: errorMessage });
        logResponse(`${displayName} Health Check Error`, { error: errorMessage });
    }
}

// Display health check result
function displayHealthResult(serviceName, status, data) {
    const resultsDiv = document.getElementById('healthResults');
    const resultsContent = document.getElementById('healthResultsContent');

    if (resultsDiv && resultsContent) {
        const statusClass = status === 'healthy' ? 'success' : status === 'error' ? 'danger' : 'warning';
        const timestamp = new Date().toLocaleTimeString();

        resultsContent.innerHTML = `
            <div class="alert alert-${statusClass} mb-2">
                <strong>${serviceName}:</strong> ${status.toUpperCase()}
                ${data.error ? `<br><small>Error: ${data.error}</small>` : ''}
                <br><small class="text-muted">Checked at ${timestamp}</small>
            </div>
        `;

        resultsDiv.style.display = 'block';
    }
}

// Refresh all services status
async function refreshAllServices() {
    const button = event.target;
    const originalText = button.innerHTML;

    button.innerHTML = '<span class="loading me-2"></span>Refreshing...';
    button.disabled = true;

    try {
        await loadServicesStatus();
        showSuccess('All services status refreshed');
    } catch (error) {
        showError('Failed to refresh services status');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Format service name for display
function formatServiceName(name) {
    return name.split('-').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
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

// Service URLs (matching main.py)
const SERVICE_URLS = {
    gateway: 'http://api-gateway:8000',
    'file-service': 'http://file-service:8001',
    'utility-service': 'http://utility-service:8002'
};