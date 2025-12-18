# LeColaz Platform - WP6 Backend (Ingestion MVP)

This repository contains a minimal but production-grade ingestion backend for WP6.

## What is implemented

### Infrastructure (Docker)
- PostgreSQL 16 (metadata storage)
- MinIO (S3-compatible object storage)
- FastAPI backend

### Backend features
- Health check endpoint
- File upload to MinIO
- File metadata persistence in PostgreSQL
- File listing API

### Files download
Direct browser downloads via MinIO presigned URLs are intentionally disabled
during early development.
Reason:
- Presigned URLs require a stable public hostname
- This will be introduced later via Nginx / reverse proxy

### APIs
- `GET /health`
- `POST /upload`
- `GET /files`
- `GET /files/{id}/download`

---

## How to run (development)

### Prerequisites
- Docker + Docker Compose

### Start the platform
```bash
cd infra
docker compose -p lecolaz up -d --build
```

### Stop the platform
```bash
docker compose -p lecolaz down
```
### Backend Logs (Development)

The backend runs inside a Docker container.
To view its logs in real time, use:

```bash
docker logs -f lecolaz-backend
```

### Access
- Backend: FastAPI docs at http://localhost:8000/docs
- MinIO: UI at http://localhost:9001 (user `lecolaz`, password `lecolaz123`)
- PostgreSQL: Connect with any client (e.g. DBeaver) using host `localhost`, port `5432`, database `lecolaz`, user `lecolaz`, password `lecolaz`
