# 🚀 Real-Time Price Alert System

A production-ready microservices system that tracks 50+ financial instruments (BTC, NIFTY, GOLD) and triggers alerts to users when price conditions are met.

![Architecture](https://img.shields.io/badge/Architecture-Microservices-blue)
![Kafka](https://img.shields.io/badge/Message_Queue-Apache_Kafka-orange)
![Python](https://img.shields.io/badge/Python-3.11-green)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Ingestor  │────▶│   Kafka     │────▶│  Evaluator  │
│  (Fetcher)  │     │  (Queue)    │     │  (Matcher)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
      │                                        │
      │ CoinGecko                              │ Kafka
      │ Yahoo Finance                          ▼
      │                               ┌─────────────┐
      │                               │  Notifier   │
      │                               │ (Email/SMS) │
      │                               └─────────────┘
      │
      └──────────────────────────────────────────────┐
                                                     │
┌─────────────┐     ┌─────────────┐     ┌───────────┴───┐
│   Gateway   │────▶│  PostgreSQL │     │  Prometheus   │
│  (REST API) │     │  (Database) │     │   + Grafana   │
└─────────────┘     └─────────────┘     └───────────────┘
```

## ✨ Features

- **50+ Instruments**: Crypto (BTC, ETH, SOL...), Stocks (AAPL, RELIANCE...), Indices (NIFTY, S&P500), Commodities (GOLD, SILVER)
- **4 Alert Types**: Above, Below, Crosses, Range
- **Multi-Channel Notifications**: Email (SMTP) and SMS (Twilio)
- **Real-Time Streaming**: WebSocket for live price updates
- **Scalable**: Kafka handles price spikes, horizontal scaling ready
- **Observable**: Prometheus metrics + Grafana dashboards

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) SMTP credentials for email
- (Optional) Twilio account for SMS

### One-Command Setup

```bash
# Clone and start
cd price-alert-system
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### Manual Setup

```bash
# Start infrastructure
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Run tests
chmod +x scripts/test-alerts.sh
./scripts/test-alerts.sh
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Register new user |
| `/auth/login` | POST | Login, get JWT token |
| `/alerts` | GET | List user's alerts |
| `/alerts` | POST | Create new alert |
| `/alerts/{id}` | PATCH | Update alert |
| `/alerts/{id}` | DELETE | Delete alert |
| `/prices` | GET | Get current prices |
| `/prices/ws` | WS | Real-time price stream |

### Example: Create Alert

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -d "username=user@example.com&password=secret123" | jq -r '.access_token')

# Create alert: Notify when BTC goes above $60,000
curl -X POST http://localhost:8000/alerts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTC","condition":"above","target_price":60000}'
```

## 📊 Observability

| Service | URL | Credentials |
|---------|-----|-------------|
| API Docs | http://localhost:8000/docs | - |
| Kafka UI | http://localhost:8080 | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |

### Key Metrics

- `kafka_consumergroup_lag` - Consumer lag (should stay low!)
- `evaluator_alerts_triggered_total` - Alerts triggered per condition
- `notifier_notifications_sent_total` - Notifications sent (success/failed)
- `ingestor_fetch_latency_seconds` - API latency to price sources

## 🔧 Configuration

Create `.env` from `.env.example`:

```env
# JWT (required)
JWT_SECRET=your-secret-key

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# SMS (optional)
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_PHONE_NUMBER=+1234567890
```

## 📁 Project Structure

```
price-alert-system/
├── docker-compose.yml      # One-command deployment
├── ingestor/               # Price fetching service
│   └── providers/          # CoinGecko, Yahoo Finance
├── evaluator/              # Alert matching service
├── notifier/               # Email/SMS service
├── gateway/                # REST API + WebSocket
├── shared/                 # Common utilities
├── prometheus/             # Metrics config
├── grafana/                # Dashboards
└── scripts/                # Setup & test scripts
```

## 🎯 Resume Highlights

This project demonstrates:

- **Microservices Architecture**: 4 independent services with clear boundaries
- **Event-Driven Design**: Kafka for decoupled, scalable communication
- **Real-Time Processing**: Sub-second price updates via WebSocket
- **Observability**: Prometheus metrics, Grafana dashboards, Kafka lag monitoring
- **Production Patterns**: Rate limiting, cooldowns, retry logic, health checks
- **DevOps Ready**: Docker Compose, one-command deployment

## 📝 License

MIT
