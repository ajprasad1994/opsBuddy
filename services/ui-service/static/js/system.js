// System Operations JavaScript for OpsBuddy UI
document.addEventListener('DOMContentLoaded', function() {
    loadServicesStatus();
    setupEventListeners();
});

// Load all services status
async function loadServicesStatus() {
    try {
        const response = await fetch('/api/services/status');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        displayServicesStatus(data);
    } catch (error) {
        console.error('Error loading services status:', error);
        showError(`Failed to load services status: ${error.message}`);
    }
}

// Display services status in dashboard
function displayServicesStatus(services) {
    const container = document.getElementById('servicesStatus');
    if (!container) return;

    // Clear existing content
    container.innerHTML = '';

    // Create service status cards for each service
    Object.entries(services).forEach(([serviceName, service]) => {
        // Handle different response formats
        let status = 'unknown';
        let statusText = 'Unknown';
        let errorMessage = '';

        if (serviceName === 'gateway' && service.response) {
            // Gateway has a different response structure
            if (service.response.services) {
                const gatewayServices = service.response.services;
                const hasUnhealthy = Object.values(gatewayServices).some(svc => svc.status === 'unhealthy');
                status = hasUnhealthy ? 'degraded' : 'healthy';
                statusText = hasUnhealthy ? 'DEGRADED' : 'HEALTHY';
                errorMessage = service.response.unhealthy_services ?
                    `Unhealthy: ${service.response.unhealthy_services.join(', ')}` : '';
            } else {
                status = service.status || 'unknown';
                statusText = status.toUpperCase();
            }
        } else if (service.response && service.response.status) {
            status = service.response.status;
            statusText = service.response.status.toUpperCase();
        } else if (service.status) {
            status = service.status;
            statusText = service.status.toUpperCase();
        }

        const statusClass = status === 'healthy' ? 'success' :
                            status === 'unhealthy' ? 'danger' : 'warning';

        // Map service names to display names and format them properly
        const displayName = formatServiceName(serviceName);

        const cardDiv = document.createElement('div');
        cardDiv.className = 'col-md-6 mb-3';
        cardDiv.innerHTML = `
            <div class="service-status-card ${status} clickable" onclick="checkIndividualService('${serviceName}', '${displayName}')" style="cursor: pointer;" title="Click to check ${displayName} health">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${displayName}</h6>
                        <small class="text-muted">
                            Status: <strong>${statusText}</strong>
                        </small>
                    </div>
                    <span class="status-indicator status-${status}"></span>
                </div>
                ${errorMessage ? `<small class="text-warning">${errorMessage}</small>` : ''}
            </div>
        `;

        container.appendChild(cardDiv);
    });

    // Ensure we have at least some content
    if (container.children.length === 0) {
        container.innerHTML = '<div class="col-12"><div class="alert alert-warning">No service status data available</div></div>';
    }
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

        const response = await fetch('/api/system/execute', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const responseData = await response.json();

        displaySystemCommandOutput(responseData);
        logResponse('System Command Executed', responseData);

        // Clear command input
        document.getElementById('systemCommand').value = '';

    } catch (error) {
        const errorMessage = error.message || 'Failed to execute command';
        showError(`Command execution failed: ${errorMessage}`);
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
        const response = await fetch('/api/system/info');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        displayDetailedSystemInfo(data);
        logResponse('Detailed System Info Retrieved', data);
    } catch (error) {
        const errorMessage = error.message || 'Failed to get system info';
        showError(`Failed to get system info: ${errorMessage}`);
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

async function checkAnalyticsService() {
    await checkIndividualService('analytics-service', 'Analytics Service');
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
            case 'analytics-service':
                url = `${SERVICE_URLS['analytics-service']}/health`;
                break;
            case 'ui-service':
                url = '/health';
                break;
            default:
                throw new Error(`Unknown service: ${serviceName}`);
        }

        const response = await fetch(url, {
            headers: {
                'Accept': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        const status = data.status === 'healthy' || data.status === 'running' ? 'healthy' : 'unhealthy';

        displayHealthResult(displayName, status, data);
        logResponse(`${displayName} Health Check`, data);

    } catch (error) {
        let errorMessage = 'Health check failed';
        let userFriendlyMessage = '';

        if (error.code === 'ECONNREFUSED') {
            errorMessage = 'Connection refused - service may not be running';
            userFriendlyMessage = `Cannot connect to ${displayName}. Please ensure the service is running and accessible.`;
        } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNRESET') {
            errorMessage = 'Service not found - check service URL or network';
            userFriendlyMessage = `${displayName} is not accessible. Check if the service is running on the correct port.`;
        } else if (error.response) {
            if (error.response.status === 404) {
                errorMessage = 'Service endpoint not found';
                userFriendlyMessage = `${displayName} health endpoint not found. Service may not be properly configured.`;
            } else if (error.response.status >= 500) {
                errorMessage = `Service error: ${error.response.status}`;
                userFriendlyMessage = `${displayName} is experiencing issues (HTTP ${error.response.status}).`;
            } else {
                errorMessage = `HTTP ${error.response.status}: ${error.response.statusText}`;
                userFriendlyMessage = `${displayName} returned an error: ${error.response.statusText}`;
            }
        } else if (error.message && error.message.includes('timeout')) {
            errorMessage = 'Request timeout - service may be overloaded';
            userFriendlyMessage = `${displayName} is not responding. The service may be busy or down.`;
        } else {
            errorMessage = error.message || 'Unknown error occurred';
            userFriendlyMessage = `An unexpected error occurred while checking ${displayName}.`;
        }

        displayHealthResult(displayName, 'error', {
            error: errorMessage,
            userMessage: userFriendlyMessage,
            details: `URL: ${SERVICE_URLS[serviceName] || 'unknown'}`
        });
    }
}

// Display health check result
function displayHealthResult(serviceName, status, data) {
    const resultsDiv = document.getElementById('healthResults');
    const resultsContent = document.getElementById('healthResultsContent');

    if (resultsDiv && resultsContent) {
        const statusClass = status === 'healthy' ? 'success' : status === 'error' ? 'danger' : 'warning';
        const timestamp = new Date().toLocaleTimeString();

        // Create new result entry
        const resultEntry = document.createElement('div');
        resultEntry.className = `alert alert-${statusClass} mb-2`;
        const errorHtml = data && data.error ? `<br><small class="text-warning">Error: ${data.error}</small>` : '';
        const userMessageHtml = data && data.userMessage ? `<br><small class="text-info">${data.userMessage}</small>` : '';
        const detailsHtml = data && data.details ? `<br><small class="text-muted">${data.details}</small>` : '';

        resultEntry.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <strong>${serviceName}:</strong> ${status.toUpperCase()}
                    ${errorHtml}
                    ${userMessageHtml}
                    ${detailsHtml}
                </div>
                <small class="text-muted">${timestamp}</small>
            </div>
        `;

        // Clear initial message if present
        const existingContent = resultsContent.innerHTML;
        if (existingContent.includes('No health checks performed yet') || existingContent.includes('No health checks performed yet...')) {
            resultsContent.innerHTML = '';
        }

        // Remove any previous entry for the same service
        const existingEntries = resultsContent.querySelectorAll('.alert');
        existingEntries.forEach(entry => {
            if (entry.textContent.includes(`${serviceName}:`)) {
                entry.remove();
            }
        });

        resultsContent.appendChild(resultEntry);
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
    if (!name) return 'Unknown Service';

    // Handle special cases
    const specialCases = {
        'file-service': 'File Service',
        'utility-service': 'Utility Service',
        'analytics-service': 'Analytics Service',
        'ui-service': 'UI Service',
        'api-gateway': 'API Gateway',
        'gateway': 'API Gateway'
    };

    if (specialCases[name.toLowerCase()]) {
        return specialCases[name.toLowerCase()];
    }

    // Default formatting for other services
    return name.split('-').map(word => {
        // Handle camelCase and regular words
        return word.replace(/([A-Z])/g, ' $1').trim();
    }).map(word =>
        word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
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

// Service URLs - Use localhost for direct access, with fallback for Docker
function getServiceURL(port) {
    // Get the current host (works for both IP and localhost)
    const host = window.location.hostname || 'localhost';
    return `http://${host}:${port}`;
}

const SERVICE_URLS = {
    gateway: getServiceURL(8000),
    'file-service': getServiceURL(8001),
    'utility-service': getServiceURL(8002),
    'analytics-service': getServiceURL(8003)
};