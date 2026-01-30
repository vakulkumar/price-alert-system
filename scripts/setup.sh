#!/bin/bash
# Setup script for Price Alert System

set -e

echo "🚀 Setting up Price Alert System..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if not exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please update .env with your SMTP and Twilio credentials"
fi

# Start infrastructure services first
echo "🔧 Starting infrastructure services (Kafka, PostgreSQL, Redis)..."
docker-compose up -d zookeeper kafka postgres redis

# Wait for Kafka to be ready
echo "⏳ Waiting for Kafka to be ready..."
sleep 15

# Start remaining services
echo "🚀 Starting application services..."
docker-compose up -d

echo ""
echo "✅ Price Alert System is starting!"
echo ""
echo "📊 Services:"
echo "   • API Gateway:    http://localhost:8000"
echo "   • API Docs:       http://localhost:8000/docs"
echo "   • Kafka UI:       http://localhost:8080"
echo "   • Prometheus:     http://localhost:9090"
echo "   • Grafana:        http://localhost:3000 (admin/admin)"
echo ""
echo "📝 Quick Start:"
echo "   1. Register: curl -X POST http://localhost:8000/auth/register -H 'Content-Type: application/json' -d '{\"email\":\"test@example.com\",\"password\":\"test123\"}'"
echo "   2. View Logs: docker-compose logs -f"
echo ""
