#!/bin/bash
# OCR Document Reading System Production Deployment Script

echo "====================================================="
echo "   Deploying OCR Document Reading System             "
echo "====================================================="

# Stop existing containers if running
echo "[1/3] Stopping legacy containers..."
docker-compose down --remove-orphans

# Rebuild containers with latest code and dependencies
echo "[2/3] Building production containers..."
docker-compose build --no-cache

# Launch services in detached mode
echo "[3/3] Launching OCR Document Reading System services..."
docker-compose up -d

echo "====================================================="
echo "   Deployment Complete!                              "
echo "   Frontend Web UI:  http://localhost:80             "
echo "   Backend OCR API:  http://localhost:8000           "
echo "   API Swagger Docs: http://localhost:8000/docs      "
echo "====================================================="
