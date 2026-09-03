# MedIntel AI ? Medical Document OCR Production Deployment Script (PowerShell)

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   Deploying MedIntel AI ? Medical OCR System       " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Stop existing containers if running
Write-Host "[1/3] Stopping existing containers..." -ForegroundColor Yellow
docker-compose down --remove-orphans

# Rebuild containers
Write-Host "[2/3] Building production containers..." -ForegroundColor Yellow
docker-compose build --no-cache

# Launch services
Write-Host "[3/3] Launching MedIntel OCR services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "=====================================================" -ForegroundColor Green
Write-Host "   Deployment Complete!                              " -ForegroundColor Green
Write-Host "   Frontend Web UI:  http://localhost:80             " -ForegroundColor Green
Write-Host "   Backend OCR API:  http://localhost:8000           " -ForegroundColor Green
Write-Host "   API Swagger Docs: http://localhost:8000/docs      " -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
