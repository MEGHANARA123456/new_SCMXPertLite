# SCMXpertLite Backend Docker Setup

## Files Created

1. **`backend/Dockerfile`** - Dockerfile for backend service
2. **`docker-compose.yml`** - Compose file at project root

## Prerequisites

- Docker installed and running
- Docker Compose installed (usually comes with Docker Desktop)
- `.env` file at project root with all required variables

## Build & Run

### Option 1: Using docker-compose (Recommended)

```bash
# Navigate to project root
cd d:\scmxpertlite

# Build and start the backend service
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Option 2: Manual Docker build

```bash
# Build image
docker build -t scmxpertlite-backend ./backend

# Run container
docker run -d \
  -p 8000:8000 \
  --name scmxpertlite_backend \
  --env-file .env \
  scmxpertlite-backend

# View logs
docker logs -f scmxpertlite_backend

# Stop container
docker stop scmxpertlite_backend
```

## Environment Variables

The Docker setup automatically reads from your `.env` file. Key variables:

```
MONGO_URI=mongodb+srv://...
MONGO_DB=mymongodb
SECRET_KEY=...
RECAPTCHA_SITE_KEY=...
```

## Verification

Once running, test the backend:

```bash
curl http://localhost:8000/ping
```

Expected response:
```json
{"status":"ok"}
```

## Stopping & Cleanup

```bash
# Stop services
docker-compose down

# Stop and remove volumes (caution: removes data)
docker-compose down -v

# Remove image
docker rmi scmxpertlite-backend
```

## Notes

- Backend runs on `http://localhost:8000`
- Files in `./backend` are mounted as volumes, so changes are hot-reloaded
- Network isolation: backend runs on `scmxpertlite-network` for future multi-service setups
- MongoDB connection uses remote MongoDB Atlas (from `.env`)
