#!/bin/bash
# Test script for Price Alert System

set -e

BASE_URL="http://localhost:8000"
EMAIL="test-$(date +%s)@example.com"
PASSWORD="testpass123"

echo "🧪 Testing Price Alert System..."
echo ""

# 1. Register user
echo "1️⃣ Registering user: $EMAIL"
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
echo "   Response: $REGISTER_RESPONSE"
echo ""

# 2. Login
echo "2️⃣ Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$EMAIL&password=$PASSWORD")
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')
echo "   Token: ${TOKEN:0:50}..."
echo ""

# 3. Create alert
echo "3️⃣ Creating BTC alert (price above 50000)..."
ALERT_RESPONSE=$(curl -s -X POST "$BASE_URL/alerts" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"symbol":"BTC","condition":"above","target_price":50000}')
ALERT_ID=$(echo $ALERT_RESPONSE | jq -r '.id')
echo "   Created alert ID: $ALERT_ID"
echo ""

# 4. List alerts
echo "4️⃣ Listing alerts..."
curl -s "$BASE_URL/alerts" \
    -H "Authorization: Bearer $TOKEN" | jq
echo ""

# 5. Get prices
echo "5️⃣ Getting current prices..."
curl -s "$BASE_URL/prices?symbols=BTC,ETH,NIFTY50" | jq
echo ""

# 6. List available symbols
echo "6️⃣ Listing available symbols..."
curl -s "$BASE_URL/prices/symbols" | jq '.count'
echo ""

# 7. Check health
echo "7️⃣ Health check..."
for service in "localhost:8000" "localhost:8001" "localhost:8002" "localhost:8003"; do
    STATUS=$(curl -s "http://$service/health" | jq -r '.status' 2>/dev/null || echo "unreachable")
    echo "   $service: $STATUS"
done
echo ""

echo "✅ All tests completed!"
echo ""
echo "💡 Monitor Kafka lag: open http://localhost:3000 (Grafana)"
echo "💡 View Kafka topics: open http://localhost:8080 (Kafka UI)"
