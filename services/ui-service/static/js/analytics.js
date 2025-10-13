// Analytics Service JavaScript for OpsBuddy UI

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadStatistics();
});

// Setup event listeners
function setupEventListeners() {
    const logQueryForm = document.getElementById('logQueryForm');
    if (logQueryForm) {
        logQueryForm.addEventListener('submit', handleLogQuery);
    }

    const manualLogForm = document.getElementById('manualLogForm');
    if (manualLogForm) {
        manualLogForm.addEventListener('submit', handleManualLogEntry);
    }
}

// Load service statistics
async function loadStatistics() {
    const statsContainer = document.getElementById('serviceStats');
    if (!statsContainer) return;

    try {
        const response = await axios.get('/api/analytics/stats');
        displayStatistics(response.data);
    } catch (error) {
        console.error('Error loading statistics:', error);
        showError('Failed to load statistics');
    }
}

// Display service statistics
function displayStatistics(stats) {
    const statsContainer = document.getElementById('serviceStats');
    if (!statsContainer) return;

    if (stats.error) {
        statsContainer.innerHTML = '<div class="col-12"><div class="alert alert-warning">Unable to load statistics</div></div>';
        return;
    }

    const statistics = stats.statistics || {};
    const totalLogs = statistics.total_logs_24h || 0;
    const errorCount = statistics.error_count_24h || 0;
    const errorRate = statistics.error_rate_24h || 0;

    statsContainer.innerHTML = `
        <div class="col-md-3">
            <div class="service-status-card">
                <div class="text-center">
                    <i class="fas fa-file-alt fa-2x text-primary mb-2"></i>
                    <h4 class="mb-1">${totalLogs.toLocaleString()}</h4>
                    <small class="text-muted">Total Logs (24h)</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="service-status-card">
                <div class="text-center">
                    <i class="fas fa-exclamation-triangle fa-2x text-warning mb-2"></i>
                    <h4 class="mb-1">${errorCount.toLocaleString()}</h4>
                    <small class="text-muted">Errors (24h)</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="service-status-card">
                <div class="text-center">
                    <i class="fas fa-percentage fa-2x text-info mb-2"></i>
                    <h4 class="mb-1">${errorRate.toFixed(2)}%</h4>
                    <small class="text-muted">Error Rate</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="service-status-card">
                <div class="text-center">
                    <i class="fas fa-chart-pie fa-2x text-success mb-2"></i>
                    <h4 class="mb-1">${Object.keys(statistics.service_breakdown || {}).length}</h4>
                    <small class="text-muted">Active Services</small>
                </div>
            </div>
        </div>
    `;
}

// Handle log query
async function handleLogQuery(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const queryData = {
        service: formData.get('service') || undefined,
        level: formData.get('level') || undefined,
        limit: parseInt(formData.get('limit')) || 100
    };

    try {
        const response = await axios.get('/api/analytics/logs', { params: queryData });
        displayLogResults(response.data);
        logResponse('Log Query Results', response.data);
    } catch (error) {
        console.error('Error querying logs:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Query failed';
        showError(`Log query failed: ${errorMessage}`);
        logResponse('Log Query Error', { error: errorMessage });
    }
}

// Display log query results
function displayLogResults(data) {
    const resultsContainer = document.getElementById('queryResults');
    if (!resultsContainer) return;

    const logs = data.logs || [];

    if (logs.length === 0) {
        resultsContainer.innerHTML = '<p class="text-muted mb-0">No logs found matching criteria</p>';
        return;
    }

    resultsContainer.innerHTML = `
        <div class="mb-2">
            <small class="text-muted">Found ${logs.length} log entries</small>
        </div>
        ${logs.map(log => `
            <div class="log-entry mb-2 p-2 border rounded">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="d-flex gap-2 mb-1">
                            <span class="badge bg-${getLogLevelBadgeClass(log.level)}">${log.level}</span>
                            <small class="text-muted">${formatTimestamp(log.timestamp)}</small>
                        </div>
                        <strong class="d-block">${log.service}</strong>
                        <code class="small">${log.message}</code>
                        ${log.operation ? `<br><small class="text-primary">Operation: ${log.operation}</small>` : ''}
                    </div>
                </div>
            </div>
        `).join('')}
    `;
}

// Handle manual log entry
async function handleManualLogEntry(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const logData = {
        timestamp: new Date().toISOString(),
        level: formData.get('level'),
        logger: 'manual_entry',
        message: formData.get('message'),
        service: formData.get('service'),
        operation: formData.get('operation') || undefined,
        data: formData.get('data') || undefined
    };

    const submitButton = e.target.querySelector('button[type="submit"]');
    const originalText = submitButton.innerHTML;

    submitButton.innerHTML = '<span class="loading me-2"></span>Sending...';
    submitButton.disabled = true;

    try {
        const response = await axios.post('/api/analytics/logs', logData);
        logResponse('Manual Log Entry Sent', response.data);
        showSuccess('Log entry sent successfully');

        // Reset form
        e.target.reset();

        // Refresh statistics
        loadStatistics();

    } catch (error) {
        console.error('Error sending log entry:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to send log entry';
        showError(`Failed to send log entry: ${errorMessage}`);
        logResponse('Manual Log Entry Error', { error: errorMessage });
    } finally {
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    }
}

// Load metrics
async function loadMetrics() {
    const metricsDiv = document.getElementById('metricsDisplay');
    const metricsContent = document.getElementById('metricsContent');

    if (!metricsDiv || !metricsContent) return;

    try {
        const response = await axios.get('/api/analytics/metrics');
        displayMetrics(response.data);
        logResponse('Metrics Loaded', response.data);
    } catch (error) {
        console.error('Error loading metrics:', error);
        const errorMessage = error.response?.data?.detail || error.message || 'Failed to load metrics';
        showError(`Failed to load metrics: ${errorMessage}`);
        logResponse('Metrics Load Error', { error: errorMessage });
    }
}

// Display metrics
function displayMetrics(data) {
    const metricsDiv = document.getElementById('metricsDisplay');
    const metricsContent = document.getElementById('metricsContent');

    if (metricsDiv && metricsContent) {
        metricsContent.textContent = JSON.stringify(data, null, 2);
        metricsDiv.style.display = 'block';
    }
}

// Refresh statistics
async function refreshStatistics() {
    const button = event.target;
    const originalText = button.innerHTML;

    button.innerHTML = '<span class="loading me-2"></span>Refreshing...';
    button.disabled = true;

    try {
        await loadStatistics();
        showSuccess('Statistics refreshed');
    } catch (error) {
        showError('Failed to refresh statistics');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Clear log results
function clearLogResults() {
    const resultsContainer = document.getElementById('queryResults');
    if (resultsContainer) {
        resultsContainer.innerHTML = '<p class="text-muted mb-0">Query results will appear here...</p>';
    }
}

// Utility functions
function getLogLevelBadgeClass(level) {
    const levelMap = {
        'DEBUG': 'secondary',
        'INFO': 'primary',
        'WARNING': 'warning',
        'ERROR': 'danger',
        'CRITICAL': 'dark'
    };
    return levelMap[level] || 'secondary';
}

function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';
    try {
        return new Date(timestamp).toLocaleString();
    } catch (e) {
        return timestamp;
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