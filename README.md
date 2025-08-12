# Clyrdia Contract Intelligence Platform API

A production-ready FastAPI backend for AI-powered contract analysis and risk assessment, built specifically for the Lovable frontend.

## 🚀 Features

- **AI-Powered Analysis**: OpenAI GPT-4 integration for intelligent contract review
- **Document Processing**: Support for PDF, DOCX, and text files
- **Real-time Streaming**: Live analysis updates with Server-Sent Events
- **Risk Assessment**: Comprehensive legal, financial, and compliance risk scoring
- **Template Library**: Industry-specific contract templates
- **Background Processing**: Celery integration for async task handling
- **Caching Layer**: Redis-based performance optimization
- **Production Ready**: Comprehensive logging, monitoring, and error handling

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Redis Cache   │    │   Celery Tasks  │
│                 │    │                 │    │                 │
│ • API Endpoints │    │ • Response      │    │ • Background    │
│ • Authentication│    │   Caching       │    │   Analysis      │
│ • Rate Limiting │    │ • Session Store │    │ • Cleanup       │
│ • CORS Support  │    │ • Task Queue    │    │ • Monitoring    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  OpenAI GPT-4   │    │    Supabase     │    │   Monitoring    │
│                 │    │                 │    │                 │
│ • Contract      │    │ • Data          │    │ • Prometheus    │
│   Analysis      │    │   Persistence   │    │   Metrics       │
│ • Risk Scoring  │    │ • User          │    │ • Health Checks │
│ • Fix Generation│    │   Management    │    │ • Alerting      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Requirements

- Python 3.11+
- Redis 7+
- PostgreSQL 15+ (via Supabase)
- OpenAI API key

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd clyrdia-api
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment configuration
```bash
cp env.example .env
# Edit .env with your configuration values
```

### 5. Run with Docker Compose (Recommended)
```bash
docker-compose up -d
```

### 6. Or run locally
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 access | Required |
| `SUPABASE_URL` | Supabase project URL | Required |
| `SUPABASE_KEY` | Supabase anon key | Required |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `API_KEY` | API key for authentication | Required |
| `DEBUG` | Enable debug mode | `false` |
| `CORS_ORIGINS` | Allowed CORS origins | Lovable domains |

### API Authentication

The API uses API key authentication. Include your API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" \
     http://localhost:8000/api/v1/health
```

## 📚 API Endpoints

### Contract Analysis

#### POST `/api/v1/analyze`
Analyze a contract for issues and risks.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/analyze" \
     -H "X-API-Key: your-api-key" \
     -F "contract_text=Your contract text here" \
     -F "industry=technology" \
     -F "analysis_type=legal,financial,compliance"
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "contract_hash": "sha256-hash",
  "total_issues": 5,
  "overall_risk_score": 75.5,
  "risk_level": "high",
  "issues": [...],
  "summary": "Analysis summary",
  "recommendations": [...],
  "created_at": 1234567890,
  "processing_time": 2.5
}
```

#### POST `/api/v1/analyze/stream`
Stream contract analysis in real-time.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/analyze/stream" \
     -H "X-API-Key: your-api-key" \
     -F "file_upload=@contract.pdf" \
     -F "industry=healthcare"
```

**Response:** Server-Sent Events stream with real-time updates.

### Contract Fixes

#### POST `/api/v1/fix/{issue_id}`
Apply a fix to a specific contract issue.

**Request:**
```json
{
  "fix_description": "Fix description",
  "fix_code": "Optional fix code",
  "auto_apply": false
}
```

### Templates

#### GET `/api/v1/templates/{industry}`
Get industry-specific contract templates.

**Request:**
```bash
curl -H "X-API-Key: your-api-key" \
     "http://localhost:8000/api/v1/templates/technology?include_variables=true"
```

### Health & Monitoring

#### GET `/api/v1/health`
Comprehensive health check.

#### GET `/metrics`
Prometheus metrics for monitoring.

## 🔄 Background Tasks

The platform uses Celery for background task processing:

### Analysis Tasks
- `analyze_contract_async`: Background contract analysis
- `batch_analyze_contracts`: Process multiple contracts
- `reanalyze_contract`: Reanalyze with different parameters

### Maintenance Tasks
- `cleanup_expired_cache`: Cache maintenance
- `cleanup_old_analyses`: Database cleanup
- `optimize_database`: Performance optimization

### Monitoring Tasks
- `health_check`: Periodic health monitoring
- `performance_metrics`: System metrics collection
- `alert_check`: Alert condition monitoring

## 🐳 Docker Deployment

### Production Dockerfile
```bash
docker build -t clyrdia-api .
docker run -p 8000:8000 clyrdia-api
```

### Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

## 📊 Monitoring & Observability

### Metrics
- **Prometheus**: HTTP request metrics, response times, error rates
- **Health Checks**: Service dependency monitoring
- **Performance**: CPU, memory, disk usage tracking

### Logging
- **Structured Logging**: JSON-formatted logs with context
- **Log Levels**: Configurable logging verbosity
- **Request Tracking**: Full request/response logging

### Alerting
- **Resource Monitoring**: CPU, memory threshold alerts
- **Service Health**: Database, cache, OpenAI status alerts
- **Error Tracking**: Exception monitoring and alerting

## 🔒 Security Features

- **API Key Authentication**: Secure endpoint access
- **Rate Limiting**: Per-client request throttling
- **Input Sanitization**: XSS and injection protection
- **CORS Configuration**: Lovable frontend integration
- **Secure File Handling**: File type and size validation

## 🧪 Testing

### Run Tests
```bash
pytest tests/
```

### Test Coverage
```bash
pytest --cov=app tests/
```

## 📈 Performance

### Caching Strategy
- **Response Caching**: Analysis results cached for 1 hour
- **Template Caching**: Industry templates cached for 30 minutes
- **Redis Backend**: High-performance caching layer

### Optimization Features
- **Async Processing**: Non-blocking I/O operations
- **Background Tasks**: Heavy operations moved to Celery
- **Connection Pooling**: Database and Redis connection optimization

## 🚀 Production Deployment

### Environment Setup
1. Set `ENVIRONMENT=production`
2. Configure production Redis and Supabase instances
3. Set up monitoring and alerting
4. Configure reverse proxy (Nginx)

### Scaling
- **Horizontal Scaling**: Multiple API instances behind load balancer
- **Worker Scaling**: Scale Celery workers based on queue depth
- **Cache Scaling**: Redis cluster for high availability

### Monitoring
- **Application Metrics**: Prometheus + Grafana
- **Infrastructure**: CPU, memory, disk monitoring
- **Business Metrics**: Analysis volume, success rates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is proprietary software for Clyrdia Contract Intelligence Platform.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the API documentation at `/docs`

## 🔄 Changelog

### v1.0.0
- Initial release
- OpenAI GPT-4 integration
- Document processing (PDF, DOCX)
- Supabase integration
- Redis caching
- Celery background tasks
- Comprehensive monitoring
- Production-ready deployment 