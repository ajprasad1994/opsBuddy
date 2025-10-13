// Main page JavaScript for OpsBuddy UI

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadServicesStatus();
    setupEventListeners();
});

// Load services status
async function loadServicesStatus() {
    try {
        const response = await axios.get('/api/services/status');
        displayServicesStatus(response.data);
    } catch (error) {
        console.error('Error loading services status:', error);
        showError('Failed to load services status');
    }
}

// Display services status in cards
function displayServicesStatus(services) {
    const container = document.getElementById('servicesContainer');

    container.innerHTML = Object.entries(services).map(([serviceName, service]) => {
        const statusClass = service.status === 'healthy' ? 'success' :
                           service.status === 'unhealthy' ? 'danger' : 'warning';

        return `
            <div class="col-md-6 col-lg-3 mb-4">
                <div class="card service-status-card ${service.status}">
                    <div class="card-body text-center">
                        <div class="mb-3">
                            <span class="status-indicator status-${service.status}"></span>
                            <h6 class="card-title mb-0">${formatServiceName(serviceName)}</h6>
                        </div>
                        <p class="card-text small text-muted">
                            Status: <strong class="${statusClass}-color">${service.status.toUpperCase()}</strong>
                        </p>
                        ${service.error ? `<p class="card-text small text-danger">${service.error}</p>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Format service name for display
function formatServiceName(name) {
    return name.split('-').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

// Setup event listeners
function setupEventListeners() {
    // Add click handlers for service cards if needed
    document.querySelectorAll('.service-card').forEach(card => {
        card.addEventListener('click', function() {
            // Add interaction if needed
        });
    });
}

// Check all services
async function checkAllServices() {
    const button = event.target;
    const originalText = button.innerHTML;

    button.innerHTML = '<span class="loading me-2"></span>Checking...';
    button.disabled = true;

    try {
        await loadServicesStatus();
        showSuccess('All services checked successfully');
    } catch (error) {
        showError('Failed to check services');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Refresh services status
async function refreshServices() {
    await loadServicesStatus();
    showSuccess('Services status refreshed');
}

// Utility functions for notifications
function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'danger');
}

function showNotification(message, type) {
    // Create a simple notification
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Add CSS classes for status colors
const style = document.createElement('style');
style.textContent = `
    .success-color { color: #28a745 !important; }
    .danger-color { color: #dc3545 !important; }
    .warning-color { color: #ffc107 !important; }
`;
document.head.appendChild(style);