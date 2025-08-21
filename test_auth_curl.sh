#!/bin/bash

# Test authentication endpoints with curl
echo "🧪 Testing CreatorPulse Authentication Endpoints"
echo "================================================"

BASE_URL="http://localhost:8001"

echo
echo "1. 📝 Testing Registration..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "testpassword123",
    "timezone": "UTC"
  }')

echo "Registration Response:"
echo "$REGISTER_RESPONSE" | python3 -m json.tool

echo
echo "2. 🔐 Testing Login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com", 
    "password": "testpassword123"
  }')

echo "Login Response:"
echo "$LOGIN_RESPONSE" | python3 -m json.tool

# Extract JWT token
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['token'])" 2>/dev/null)

if [ -n "$TOKEN" ]; then
    echo
    echo "3. 👤 Testing Get Current User (with JWT)..."
    curl -s -X GET "$BASE_URL/v1/auth/me" \
      -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
    
    echo
    echo "4. 📤 Testing Logout..."
    curl -s -X POST "$BASE_URL/v1/auth/logout" \
      -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
else
    echo "❌ No token received from login"
fi

echo
echo "5. 🔄 Testing Password Reset..."
curl -s -X POST "$BASE_URL/v1/auth/reset-password" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com"
  }' | python3 -m json.tool

echo
echo "✅ Authentication tests completed!"
