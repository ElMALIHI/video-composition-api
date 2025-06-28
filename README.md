# Video Composition API

![CI Status](https://github.com/yourusername/video-composition-api/workflows/CI/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)

A powerful, production-ready API for creating video compositions from images, audio, and video clips. Built with FastAPI, SQLAlchemy, and Redis for high performance and scalability.

## Features

### Core Functionality
- **Video Composition**: Create complex videos from images, audio, and video clips
- **Scene Management**: Multi-scene compositions with custom durations
- **Text & Image Overlays**: Add dynamic text and image overlays to scenes
- **Audio Mixing**: Background audio, per-scene audio, and audio effects
- **Transitions**: Smooth transitions between scenes (fade, slide, zoom, etc.)
- **Multiple Output Formats**: MP4, WebM, AVI, MOV, GIF support

### API Features
- **FastAPI Backend**: High-performance async API with automatic OpenAPI documentation
- **Authentication**: API key-based authentication with Bearer token support
- **Rate Limiting**: Redis-backed rate limiting per API key
- **File Management**: Secure file upload/download with validation and metadata extraction
- **Job Management**: Async job processing with status tracking and progress updates
- **Webhook Support**: Configurable webhooks for job completion notifications

### Infrastructure
- **Database**: Async SQLAlchemy with PostgreSQL/SQLite support
- **Caching**: Redis for job queues and caching
- **Containerized**: Docker and docker-compose for easy deployment
- **Monitoring**: Health checks, metrics, and structured logging
- **Security**: Input validation, file type checking, and secure file handling

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/video-composition-api.git
   cd video-composition-api
   ```

2. **Setup development environment**
   ```bash
   make setup-dev
   ```

3. **Start the development environment**
   ```bash
   make dev
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Manual Installation

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run the API**
   ```bash
   python -m uvicorn main:app --reload
   ```

## Usage Examples

### Authentication
All endpoints require an API key passed as a Bearer token:
```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8000/health
```

### Upload a File
```bash
curl -X POST \
  -H "Authorization: Bearer your-api-key" \
  -F "file=@example.jpg" \
  http://localhost:8000/upload
```

### Submit a Video Composition Job
```bash
curl -X POST \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Video",
    "scenes": [
      {
        "duration": 3.0,
        "image_file_id": "uploaded-image-id",
        "text_overlays": [
          {
            "text": "Hello World!",
            "x": 0.5,
            "y": 0.5,
            "font_size": 48,
            "font_color": "white"
          }
        ]
      }
    ],
    "video_settings": {
      "resolution": "1920x1080",
      "fps": 30,
      "quality": "high"
    }
  }' \
  http://localhost:8000/compose
```

### Check Job Status
```bash
curl -H "Authorization: Bearer your-api-key" \
  http://localhost:8000/jobs/job-id-here
```

## API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/supported-formats` | GET | Supported file formats |
| `/upload` | POST | Upload single file |
| `/upload-multiple` | POST | Upload multiple files |
| `/compose` | POST | Submit composition job |
| `/jobs/{job_id}` | GET | Get job status |
| `/jobs` | GET | List jobs |
| `/jobs/{job_id}` | DELETE | Delete job |
| `/download/{job_id}` | GET | Download result |

## Documentation

- **[API Guide](docs/API_GUIDE.md)**: Detailed API documentation and examples
- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)**: Setup and development workflow
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Production deployment instructions
- **[Interactive Docs](http://localhost:8000/docs)**: Auto-generated OpenAPI documentation

## Development

### Setup Development Environment
```bash
# Quick setup
make setup-dev

# Manual setup
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
pre-commit install
```

### Available Commands
```bash
make help           # Show all available commands
make test           # Run tests with coverage
make lint           # Run linting checks
make format         # Format code
make dev            # Start development environment
make build          # Build Docker image
make up             # Start production environment
```

### Running Tests
```bash
# All tests
make test

# Specific test
pytest tests/test_main.py -v

# With coverage report
pytest tests/ --cov=./ --cov-report=html
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PostgreSQL    │    │     Redis       │
│                 │◄──►│   Database      │    │   Job Queue     │
│  • Async/Await  │    │                 │    │   Rate Limit    │
│  • OpenAPI      │    │  • Jobs         │    │   Caching       │
│  • Validation   │    │  • Files        │    │                 │
│  • Auth         │    │  • Usage        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                ┌─────────────────▼─────────────────┐
                │       Video Processing           │
                │                                  │
                │  • MoviePy (Video editing)       │
                │  • Pillow (Image processing)     │
                │  • OpenCV (Computer vision)      │
                │  • FFmpeg (Media conversion)     │
                └──────────────────────────────────┘
```

## Production Deployment

### Using Docker Compose
```bash
# Production deployment
docker compose up -d

# With custom configuration
cp .env.example .env
# Edit .env for production settings
docker compose up -d
```

### Environment Variables
Key environment variables for production:
```env
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/video_composition
REDIS_URL=redis://redis:6379/0
API_KEYS=your-secure-api-keys
CORS_ORIGINS=["https://yourdomain.com"]
```

## Performance Considerations

- **Async Processing**: All database and Redis operations are async
- **Connection Pooling**: Configurable database connection pools
- **Rate Limiting**: Prevents API abuse and ensures fair usage
- **File Validation**: Early validation prevents processing invalid files
- **Caching**: Redis caching for frequently accessed data
- **Resource Limits**: Configurable memory and processing limits

## Security Features

- **API Key Authentication**: Secure token-based authentication
- **Input Validation**: Comprehensive input validation using Pydantic
- **File Type Validation**: Strict file type and size validation
- **Path Traversal Protection**: Secure file handling prevents directory traversal
- **Rate Limiting**: Protection against abuse and DoS attacks
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Security Headers**: Automatic security headers in responses

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make pre-commit`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 **Documentation**: Check the [docs](docs/) directory
- 🐛 **Bug Reports**: Use the GitHub issue tracker
- 💬 **Discussions**: Use GitHub Discussions for questions
- 📧 **Email**: contact@yourdomain.com

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.

---

Built with ❤️ using FastAPI, SQLAlchemy, and Redis.
