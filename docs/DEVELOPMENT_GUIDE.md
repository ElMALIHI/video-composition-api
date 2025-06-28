# Development Guide: Video Composition API

## Overview
This guide covers setting up the development environment for the Video Composition API. The API is built with FastAPI, SQLAlchemy, and Redis for optimal performance and maintainability.

## Requirements
- Python 3.11+
- Docker & Docker Compose
- Git

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/video-composition-api.git
cd video-composition-api
```

### 2. Setup Development Environment
Use the Makefile for quick setup:
```bash
make setup-dev
```

This will:
- Install all dependencies
- Create `.env` file from example
- Set up pre-commit hooks

### 3. Start Development Services
```bash
make dev
```

This starts the API with auto-reload and development database.

### 4. Access the API
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Redis Commander: http://localhost:8081

## Project Structure
```
video-composition-api/
├── api/                    # API endpoints
│   └── endpoints/         # Individual endpoint modules
├── core/                  # Core functionality
│   ├── database.py       # Database configuration
│   ├── redis.py          # Redis configuration
│   └── settings.py       # Application settings
├── models/               # Data models
│   ├── api.py           # Pydantic models
│   └── database.py      # SQLAlchemy models
├── services/            # Business logic
│   ├── auth.py         # Authentication service
│   ├── file_service.py # File handling service
│   ├── job_service.py  # Job management service
│   └── video_service.py # Video composition service
├── tests/              # Test files
├── utils/              # Utility functions
├── docs/               # Documentation
├── docker/             # Docker configurations
└── main.py            # Application entry point
```

## Development Commands

### Using Makefile
```bash
make help                 # Show available commands
make install-dev         # Install development dependencies
make test                # Run tests with coverage
make lint                # Run linting checks
make format              # Format code
make run                 # Run API locally
make dev                 # Run with Docker
```

### Manual Commands
```bash
# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run tests
pytest tests/ -v --cov=./

# Run linting
flake8 . --max-line-length=88
mypy . --ignore-missing-imports

# Format code
black .
isort .

# Run API
python -m uvicorn main:app --reload
```

## Database Management

### Migrations (if using Alembic)
```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Direct Database Access
```bash
# Access PostgreSQL (production)
make db-shell

# Access SQLite (development)
sqlite3 dev.db
```

## Testing

### Running Tests
```bash
# All tests
make test

# Specific test file
pytest tests/test_main.py -v

# With coverage
pytest tests/ --cov=./ --cov-report=html
```

### Test Types
- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test API endpoints and database interactions
- **Authentication tests**: Test API key validation and rate limiting

## Code Quality

### Pre-commit Hooks
Automatically run on each commit:
- Black (code formatting)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking)
- bandit (security checks)

### Manual Quality Checks
```bash
make lint           # Run all linting
make format-check   # Check formatting without changing
make security-check # Run security scans
```

## Environment Variables
Create a `.env` file for local development:
```env
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=sqlite+aiosqlite:///./dev.db
REDIS_URL=redis://localhost:6379/0
API_KEYS=dev-key-123,test-key-456
CORS_ORIGINS=["*"]
```

## Debugging

### API Debugging
- Use `/docs` for interactive API testing
- Check logs in Docker: `docker-compose logs -f api-dev`
- Access container: `docker-compose exec api-dev bash`

### Database Debugging
- View tables: `.tables` (SQLite) or `\dt` (PostgreSQL)
- Query data: Standard SQL commands
- Check connections: Health endpoint shows database status

## Contributing

### Code Style
- Follow PEP 8 with line length of 88 characters
- Use type hints for all functions
- Write docstrings for classes and functions
- Add tests for new features

### Pull Request Process
1. Create feature branch from `develop`
2. Make changes with tests
3. Run quality checks: `make pre-commit`
4. Push and create pull request
5. Ensure CI passes

## Troubleshooting

### Common Issues
1. **Database connection errors**: Check PostgreSQL/SQLite setup
2. **Redis connection errors**: Ensure Redis is running
3. **Import errors**: Verify all dependencies are installed
4. **Permission errors**: Check file permissions for uploads/outputs

### Getting Help
- Check the [API Guide](./API_GUIDE.md) for endpoint details
- Review error logs for specific issues
- Use the issue tracker for bug reports

---
For deployment information, see the [Deployment Guide](./DEPLOYMENT_GUIDE.md).
