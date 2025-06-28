# Deployment Guide: Video Composition API

## Overview
This guide covers deploying the Video Composition API to production using Docker and Docker Compose. The API is designed to be scalable and easy to manage, with support for wired technologies such as Redis, PostgreSQL, and FastAPI.

## Requirements
- Docker
- Docker Compose

Ensure that Docker and Docker Compose are installed and running on your server before proceeding.

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/video-composition-api.git
cd video-composition-api
```

### 2. Create Environment Variables
Create an `.env` file containing your production configurations. Example:
```env
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://username:password@postgres:5432/video_composition
REDIS_URL=redis://redis:6379/0
API_KEYS=your-api-key
CORS_ORIGINS=["https://yourdomain.com"]
```

### 3. Build Docker Images
Build the API Docker image:
```bash
docker build -t video-composition-api .
```

### 4. Configure Docker Compose
Ensure the `docker-compose.yml` has your desired configurations, including environment variables and ports.

### 5. Start Services
Start the services using Docker Compose:
```bash
docker-compose up -d
```
This will start the API, PostgreSQL database, and Redis server.

### 6. Verify Deployment
Check the health endpoint to ensure the API is running correctly:
```bash
curl -f http://localhost:8000/health
```
You should see a JSON response indicating server health.

## Maintenance

### Updating the API
1. Pull the latest changes from the repository:
   ```bash
   git pull origin main
   ```
2. Rebuild the Docker image:
   ```bash
   docker-compose build
   ```
3. Restart the services with zero downtime:
   ```bash
   docker-compose up -d
   ```

### Logs
View logs for troubleshooting:
```bash
docker-compose logs -f
```

To view logs for specific services, use:
```bash
docker-compose logs -f api
```

### Backups
For database backups, consider using Postgres tools or third-party services. Example using `pg_dump`:
```bash
pg_dump -U postgres video_composition > backup.sql
```

## Scaling
To scale the application, consider using orchestration tools like Kubernetes or Swarm for advanced deployment scenarios.

---
For further details, refer to the [API Guide](./API_GUIDE.md) and [Development Guide](./DEVELOPMENT_GUIDE.md).
