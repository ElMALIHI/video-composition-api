# API Guide: Video Composition API

## Overview
The Video Composition API allows users to create complex video compositions using images, audio, and video clips. The API is designed to be highly scalable, maintainable, and easy to deploy, with features including API key authentication, rate limiting, webhook notifications, and more.

## Base URL
- Development: `http://localhost:8000`
- Production: `https://yourdomain.com`

## Authentication
All endpoints except `/health` and `/docs` require authentication using API keys. Pass your API key as a Bearer token in the request header:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### 1. API Info
- **GET /**
  - Description: Get API information.
  - Response: `200 OK`, JSON with API details.

### 2. Health Check
- **GET /health**
  - Description: Check server health and connectivity.
  - Response: `200 OK`, JSON with health status.

### 3. Supported Formats
- **GET /supported-formats**
  - Description: Retrieve supported file formats for uploads and outputs.
  - Response: `200 OK`, JSON with format information.

### 4. File Uploads
- **POST /upload**
  - Description: Upload a single file (image, audio, or video).
  - Form Data: `file` (required)
  - Response: `200 OK`, JSON with file information.

- **POST /upload-multiple**
  - Description: Upload multiple files.
  - Form Data: `files[]` (required)
  - Response: `200 OK`, JSON with lists of uploaded and failed files.

### 5. Video Composition Jobs
- **POST /compose**
  - Description: Submit a video composition job.
  - JSON Body: `VideoCompositionRequest`
  - Response: `200 OK`, JSON with job details.

- **GET /jobs/{job_id}**
  - Description: Retrieve status and details for a specific job.
  - Response: `200 OK`, JSON with job information.

- **GET /jobs**
  - Description: List all submitted jobs for the authenticated API key.
  - Query Parameters: Filter by job status, priority, page, and sort order.
  - Response: `200 OK`, JSON with list of jobs.

- **DELETE /jobs/{job_id}**
  - Description: Delete a specific job and its resources.
  - Response: `200 OK`, JSON with success message.

## Request/Response Formats
All requests and responses use JSON format, except for file uploads which use multipart/form-data.

### Example Request
```json
{
  "title": "My Video",
  "scenes": [
    {
      "duration": 5.0,
      "image_file_id": "your-image-file-id",
      "text_overlays": [
        {
          "text": "Hello World",
          "x": 0.5,
          "y": 0.5
        }
      ]
    }
  ],
  "audio_settings": {
    "background_audio_file_id": "your-background-audio-file-id",
    "background_volume": 0.3
  },
  "video_settings": {
    "resolution": "1920x1080",
    "quality": "high"
  },
  "priority": "high",
  "webhook_url": "https://your-callback-url.com"
}
```

Review the [Swagger documentation](../swagger.json) for complete details on request and response models.

---

For more details, refer to the [Deployment Guide](./DEPLOYMENT_GUIDE.md) and [Development Guide](./DEVELOPMENT_GUIDE.md).
