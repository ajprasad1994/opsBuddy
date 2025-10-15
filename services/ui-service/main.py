from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests
import redis
import json
import threading
import time
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app, origins=app.config['CORS_ORIGINS'])

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS'])

@app.route('/')
def index():
    """Serve the main React application"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "ui-service"})

@app.route('/api/services')
def get_services():
    """Get all service statuses"""
    try:
        response = requests.get(f"{app.config['GATEWAY_URL']}/status")
        gateway_data = response.json()

        # Transform gateway data to UI-friendly format
        services_data = []
        if 'services' in gateway_data:
            for service_name, service_info in gateway_data['services'].items():
                services_data.append({
                    'name': service_name.title(),
                    'port': 8000 + (services_data.__len__() % 4),  # Assign ports based on service index
                    'status': service_info.get('status', 'unknown'),
                    'response_time': service_info.get('response_time', 0),
                    'uptime': service_info.get('uptime', 0),
                    'description': f'{service_name.title()} service for opsBuddy platform'
                })

        return jsonify(services_data)
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/logs', methods=['POST'])
def query_logs():
    """Query logs from analytics service"""
    try:
        data = request.get_json()
        response = requests.post(f"{app.config['ANALYTICS_SERVICE_URL']}/logs/query", json=data)
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/metrics')
def get_metrics():
    """Get analytics metrics"""
    try:
        response = requests.get(f"{app.config['ANALYTICS_SERVICE_URL']}/metrics")
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/files')
def list_files():
    """List files from file service"""
    try:
        response = requests.get(f"{app.config['FILE_SERVICE_URL']}/files")
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/utility/health')
def utility_health():
    """Get utility service health"""
    try:
        response = requests.get(f"{app.config['UTILITY_SERVICE_URL']}/health")
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/incidents')
def get_incidents():
    """Get incidents from incident service"""
    try:
        response = requests.get(f"{app.config['INCIDENT_SERVICE_URL']}/incidents")
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/errors/<service>')
def get_service_errors(service):
    """Get errors for specific service"""
    try:
        response = requests.get(f"{app.config['INCIDENT_SERVICE_URL']}/errors/{service}")
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/monitor/services')
def get_monitor_services():
    """Get service health data from monitor service"""
    try:
        response = requests.get(f"{app.config['MONITOR_SERVICE_URL']}/services")
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/monitor/services/<service_name>')
def get_monitor_service(service_name):
    """Get specific service health data from monitor service"""
    try:
        response = requests.get(f"{app.config['MONITOR_SERVICE_URL']}/services/{service_name}")
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/monitor/system/health')
def get_system_health():
    """Get overall system health from monitor service"""
    try:
        response = requests.get(f"{app.config['MONITOR_SERVICE_URL']}/system/health")
        return jsonify(response.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/services/status')
def get_all_services_status():
    """Get comprehensive status of all services"""
    try:
        # Get gateway status
        gateway_response = requests.get(f"{app.config['GATEWAY_URL']}/status")
        gateway_data = gateway_response.json()

        # Get individual service health
        services = {
            'gateway': {'url': f"{app.config['GATEWAY_URL']}/health", 'port': 8000},
            'file-service': {'url': f"{app.config['FILE_SERVICE_URL']}/health", 'port': 8001},
            'utility-service': {'url': f"{app.config['UTILITY_SERVICE_URL']}/health", 'port': 8002},
            'analytics-service': {'url': f"{app.config['ANALYTICS_SERVICE_URL']}/health", 'port': 8003},
            'incident-service': {'url': f"{app.config['INCIDENT_SERVICE_URL']}/health", 'port': 8004},
            'ui-service': {'url': '/health', 'port': 3000}
        }

        services_status = {}
        for service_name, service_info in services.items():
            try:
                if service_name == 'ui-service':
                    # Local health check
                    status = 'healthy'
                    response_time = 0
                else:
                    response = requests.get(service_info['url'], timeout=5)
                    data = response.json()
                    status = data.get('status', 'unknown')
                    response_time = response.elapsed.total_seconds() * 1000
            except:
                status = 'unhealthy'
                response_time = 0

            services_status[service_name] = {
                'name': service_name.replace('-', ' ').title(),
                'port': service_info['port'],
                'status': status,
                'response_time': response_time
            }

        return jsonify({
            'services': services_status,
            'gateway': gateway_data,
            'timestamp': time.time()
        })
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

# SocketIO events for real-time updates
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'msg': 'Connected to opsBuddy UI'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('request_update')
def handle_update_request(data):
    """Handle real-time update requests"""
    try:
        # Get current service statuses
        services_response = requests.get(f"{app.config['GATEWAY_URL']}/status")
        gateway_data = services_response.json()

        # Transform gateway data to UI-friendly format
        services_data = []
        if 'services' in gateway_data:
            for service_name, service_info in gateway_data['services'].items():
                services_data.append({
                    'name': service_name.title(),
                    'port': 8000 + (len(services_data) % 4),  # Assign ports based on service index
                    'status': service_info.get('status', 'unknown'),
                    'response_time': service_info.get('response_time', 0),
                    'uptime': service_info.get('uptime', 0),
                    'description': f'{service_name.title()} service for opsBuddy platform'
                })

        # Get current metrics
        metrics_response = requests.get(f"{app.config['ANALYTICS_SERVICE_URL']}/metrics")
        metrics_data = metrics_response.json()

        # Emit real-time update
        emit('update', {
            'services': services_data,
            'metrics': metrics_data,
            'timestamp': data.get('timestamp')
        })
    except Exception as e:
        emit('error', {'error': str(e)})

# Redis subscriber for real-time incident updates
def redis_subscriber():
    """Background thread to listen for Redis pub/sub messages"""
    try:
        redis_client = redis.Redis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            db=app.config['REDIS_DB'],
            password=app.config['REDIS_PASSWORD'] if app.config['REDIS_PASSWORD'] else None,
            decode_responses=True
        )

        # Subscribe to incident and service health channels
        pubsub = redis_client.pubsub()
        pubsub.subscribe('incidents', 'error_logs', 'analytics_updates', 'service_health', 'websocket_updates')

        print("Redis subscriber started, listening for updates...")

        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    channel = message['channel']

                    print(f"Received update on {channel}: {data.get('service', 'unknown')}")

                    # Handle different types of updates with proper SocketIO context
                    if channel == 'service_health':
                        # Use SocketIO's context manager for thread-safe emission
                        with app.app_context():
                            socketio.emit('service_health_update', {
                                'channel': channel,
                                'data': data,
                                'timestamp': time.time()
                            })
                            print(f"Emitted service_health_update for {data.get('service', 'unknown')}")
                    elif channel in ['incidents', 'error_logs', 'analytics_updates']:
                        # Use SocketIO's context manager for thread-safe emission
                        with app.app_context():
                            socketio.emit('incident_update', {
                                'channel': channel,
                                'data': data,
                                'timestamp': time.time()
                            })
                    else:
                        # Generic update for other channels
                        with app.app_context():
                            socketio.emit('generic_update', {
                                'channel': channel,
                                'data': data,
                                'timestamp': time.time()
                            })
                except json.JSONDecodeError as e:
                    print(f"Error parsing Redis message: {e}")
                except Exception as e:
                    print(f"Error processing Redis message: {e}")

    except Exception as e:
        print(f"Redis subscriber error: {e}")

# Start Redis subscriber in background thread
def start_redis_subscriber():
    """Start the Redis subscriber thread"""
    subscriber_thread = threading.Thread(target=redis_subscriber, daemon=True)
    subscriber_thread.start()
    print("Redis subscriber thread started")

if __name__ == '__main__':
    # Start Redis subscriber before starting the server
    start_redis_subscriber()

    socketio.run(app, host='0.0.0.0', port=app.config['PORT'], debug=app.config['DEBUG'], allow_unsafe_werkzeug=True)