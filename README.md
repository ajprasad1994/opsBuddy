# 🚀 OpsBuddy - Operations Management Platform

A comprehensive operations management platform with microservices architecture, time-series database integration, and modern REST API built with FastAPI.

## ✨ Features

- **Three Independent Services**: File Service, Utility Service, and Analytics Service
- **Time-Series Database**: Full InfluxDB integration (1.x and 2.x support)
- **Modern REST API**: Built with FastAPI, auto-generated documentation
- **CRUD Operations**: Complete Create, Read, Update, Delete operations for all services
- **Async Architecture**: Full async/await support for high performance
- **Structured Logging**: Comprehensive logging with JSON format support
- **Docker Support**: Multi-stage Docker builds with health checks
- **Environment Configuration**: Flexible configuration via environment variables

## 🏗️ Architecture

```
OpsBuddy/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── database/               # Database layer
│   │   ├── connection.py       # InfluxDB connection manager
│   │   └── models.py           # Database models
│   ├── services/               # Business logic services
│   │   ├── file_service.py     # File operations
│   │   ├── utility_service.py  # Utility operations
│   │   └── analytics_service.py # Analytics operations
│   ├── api/                    # API layer
│   │   ├── routes/             # REST endpoints
│   │   └── models/             # Pydantic models
│   └── utils/                  # Utilities
│       └── logger.py           # Logging configuration
├── tests/                      # Test suite
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Development environment
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- InfluxDB (optional, can be run via Docker)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd opsBuddy
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the application**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Docker Deployment

1. **Build and run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **Build Docker image manually**
   ```bash
   docker build -t opsbuddy .
   docker run -p 8000:8000 opsbuddy
   ```

3. **Docker commands**
   ```bash
   # Build image
   docker build -t opsbuddy .
   
   # Run container
   docker run -d --name opsbuddy-app -p 8000:8000 opsbuddy
   
   # View logs
   docker logs opsbuddy-app
   
   # Stop container
   docker stop opsbuddy-app
   ```

## 📊 Services Overview

### 1. File Service (`/api/v1/files/*`)

**Operations:**
- `POST /upload` - Upload files with metadata
- `GET /{file_id}` - Download files
- `GET /{file_id}/info` - Get file metadata
- `PUT /{file_id}` - Update file content/metadata
- `DELETE /{file_id}` - Delete files
- `GET /` - List files with filtering
- `GET /{file_id}/download` - Download as attachment
- `GET /{file_id}/preview` - Preview text files

**Features:**
- File type validation
- Size limits
- Tag-based organization
- Metadata support
- Safe file storage

### 2. Utility Service (`/api/v1/utilities/*`)

**Operations:**
- `POST /configs` - Create configurations
- `GET /configs/{config_id}` - Read configurations
- `PUT /configs/{config_id}` - Update configurations
- `DELETE /configs/{config_id}` - Delete configurations
- `GET /configs` - List configurations
- `GET /system/info` - System information
- `GET /health` - Health check
- `POST /execute` - Execute system commands

**Features:**
- Configuration management
- System monitoring
- Health checks
- Safe command execution
- Category organization

### 3. Analytics Service (`/api/v1/analytics/*`)

**Operations:**
- `POST /metrics` - Create metrics
- `GET /metrics/{metric_id}` - Read metrics
- `PUT /metrics/{metric_id}` - Update metrics
- `DELETE /metrics/{metric_id}` - Delete metrics
- `GET /metrics` - List metrics
- `POST /metrics/statistics` - Get statistics
- `POST /metrics/aggregate` - Aggregate data
- `POST /metrics/trends` - Trend analysis

**Features:**
- Time-series data management
- Statistical analysis
- Data aggregation
- Trend detection
- Flexible filtering

## 🗄️ Database Configuration

### InfluxDB 2.x (Recommended)

```bash
# Environment variables
INFLUXDB_HOST=localhost
INFLUXDB_PORT=8086
INFLUXDB_TOKEN=your_token_here
INFLUXDB_ORG=your_organization
INFLUXDB_DATABASE=opsbuddy
INFLUXDB_URL=http://localhost:8086
```

### InfluxDB 1.x (Legacy)

```bash
# Environment variables
INFLUXDB_HOST=localhost
INFLUXDB_PORT=8086
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=password
INFLUXDB_DATABASE=opsbuddy
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | Application host |
| `APP_PORT` | `8000` | Application port |
| `DEBUG` | `false` | Debug mode |
| `ENVIRONMENT` | `development` | Environment name |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | Log format |
| `MAX_FILE_SIZE` | `104857600` | Max file size (100MB) |
| `UPLOAD_DIRECTORY` | `./uploads` | File upload directory |
| `ALLOWED_FILE_TYPES` | `txt,log,json,csv,yaml,yml` | Allowed file types |

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `INFLUXDB_HOST` | `localhost` | InfluxDB host |
| `INFLUXDB_PORT` | `8086` | InfluxDB port |
| `INFLUXDB_TOKEN` | `None` | InfluxDB 2.x token |
| `INFLUXDB_ORG` | `None` | InfluxDB 2.x organization |
| `INFLUXDB_DATABASE` | `opsbuddy` | Database name |
| `INFLUXDB_URL` | `None` | InfluxDB URL |

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_file_service.py
```

### Test Structure

```
tests/
├── test_file_service.py
├── test_utility_service.py
└── test_analytics_service.py
```

## 📚 API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### API Endpoints

#### Core Endpoints
- `GET /` - Application information
- `GET /health` - Health check
- `GET /ping` - Simple ping
- `GET /info` - Detailed information
- `GET /api` - API information

#### File Service
- `POST /api/v1/files/upload` - Upload file
- `GET /api/v1/files/{file_id}` - Download file
- `GET /api/v1/files/{file_id}/info` - File metadata
- `PUT /api/v1/files/{file_id}` - Update file
- `DELETE /api/v1/files/{file_id}` - Delete file
- `GET /api/v1/files/` - List files

#### Utility Service
- `POST /api/v1/utilities/configs` - Create config
- `GET /api/v1/utilities/configs/{config_id}` - Read config
- `PUT /api/v1/utilities/configs/{config_id}` - Update config
- `DELETE /api/v1/utilities/configs/{config_id}` - Delete config
- `GET /api/v1/utilities/configs` - List configs
- `GET /api/v1/utilities/health` - Health check
- `GET /api/v1/utilities/system/info` - System info

#### Analytics Service
- `POST /api/v1/analytics/metrics` - Create metric
- `GET /api/v1/analytics/metrics/{metric_id}` - Read metric
- `PUT /api/v1/analytics/metrics/{metric_id}` - Update metric
- `DELETE /api/v1/analytics/metrics/{metric_id}` - Delete metric
- `GET /api/v1/analytics/metrics` - List metrics
- `POST /api/v1/analytics/metrics/statistics` - Get statistics
- `POST /api/v1/analytics/metrics/aggregate` - Aggregate data

## 🐳 Docker Commands

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

### Production

```bash
# Build production image
docker build -t opsbuddy:latest .

# Run production container
docker run -d \
  --name opsbuddy-prod \
  -p 8000:8000 \
  -e ENVIRONMENT=production \
  -e DEBUG=false \
  opsbuddy:latest

# Run with custom config
docker run -d \
  --name opsbuddy-prod \
  -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  opsbuddy:latest
```

## 🔒 Security Considerations

- **File Upload Validation**: File type and size restrictions
- **Command Execution**: Whitelist of allowed commands
- **Database Security**: Environment-based configuration
- **CORS Configuration**: Configurable cross-origin settings
- **Input Validation**: Pydantic model validation
- **Error Handling**: Secure error messages

## 📈 Monitoring & Logging

### Logging

- **Structured Logging**: JSON format for easy parsing
- **Operation Tracking**: All CRUD operations logged
- **Error Logging**: Comprehensive error tracking
- **Performance Metrics**: Request processing times

### Health Checks

- **Application Health**: Overall system status
- **Database Health**: Connection status
- **System Metrics**: CPU, memory, disk usage
- **Uptime Tracking**: Service uptime monitoring

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   export ENVIRONMENT=production
   export DEBUG=false
   export LOG_LEVEL=WARNING
   ```

2. **Database Setup**
   - Configure InfluxDB with proper authentication
   - Set up database backups
   - Configure monitoring

3. **Application Deployment**
   ```bash
   # Build production image
   docker build -t opsbuddy:prod .
   
   # Run with production config
   docker run -d \
     --name opsbuddy-prod \
     -p 8000:8000 \
     --env-file .env.production \
     opsbuddy:prod
   ```

### Load Balancer Configuration

```nginx
upstream opsbuddy {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name opsbuddy.example.com;
    
    location / {
        proxy_pass http://opsbuddy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check this README and API docs
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact the development team

## 🔮 Roadmap

- [ ] Redis caching integration
- [ ] GraphQL API support
- [ ] WebSocket real-time updates
- [ ] Advanced analytics dashboard
- [ ] Kubernetes deployment manifests
- [ ] CI/CD pipeline
- [ ] Performance benchmarking
- [ ] Security audit tools

---

**Built with ❤️ by the OpsBuddy Team**
