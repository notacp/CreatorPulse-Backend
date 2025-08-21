#!/bin/bash

# Source Management Endpoints Test Script
# Requires: curl, jq (for JSON parsing)

BASE_URL="http://127.0.0.1:8001"
EMAIL="fresh-test@gmail.com"
PASSWORD="TestPassword123!"

echo "🧪 Testing CreatorPulse Source Management Endpoints"
echo "=================================================="

# Function to make authenticated requests
make_request() {
    local method="$1"
    local endpoint="$2"
    local data="$3"
    
    if [ "$method" = "GET" ]; then
        curl -s -X GET \
            -H "Authorization: Bearer $TOKEN" \
            -H "Accept: application/json" \
            "$BASE_URL$endpoint"
    elif [ "$method" = "POST" ]; then
        curl -s -X POST \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint"
    elif [ "$method" = "PUT" ]; then
        curl -s -X PUT \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint"
    elif [ "$method" = "DELETE" ]; then
        curl -s -X DELETE \
            -H "Authorization: Bearer $TOKEN" \
            -H "Accept: application/json" \
            "$BASE_URL$endpoint"
    fi
}

# Step 1: Login to get token
echo "🔐 Step 1: Authenticating user..."
LOGIN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
    "$BASE_URL/v1/auth/login")

# Extract token (requires jq for clean parsing, fallback to grep/sed)
if command -v jq &> /dev/null; then
    TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.data.token // empty')
    SUCCESS=$(echo "$LOGIN_RESPONSE" | jq -r '.success // false')
else
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*"' | sed 's/"token":"\(.*\)"/\1/')
    SUCCESS=$(echo "$LOGIN_RESPONSE" | grep -o '"success":[^,}]*' | sed 's/"success":\(.*\)/\1/')
fi

if [ "$SUCCESS" = "true" ] && [ -n "$TOKEN" ]; then
    echo "✅ Authentication successful"
    echo "   Token: ${TOKEN:0:20}..."
else
    echo "❌ Authentication failed"
    echo "   Response: $LOGIN_RESPONSE"
    exit 1
fi

# Step 2: Test GET /sources (empty)
echo ""
echo "📋 Step 2: Getting sources (should be empty)..."
SOURCES_RESPONSE=$(make_request "GET" "/v1/sources/")
echo "Response: $SOURCES_RESPONSE"

# Step 3: Create RSS source
echo ""
echo "➕ Step 3: Creating RSS source..."
RSS_DATA='{
    "type": "rss",
    "url": "https://feeds.feedburner.com/TechCrunch", 
    "name": "TechCrunch"
}'
RSS_RESPONSE=$(make_request "POST" "/v1/sources/" "$RSS_DATA")
echo "Response: $RSS_RESPONSE"

# Extract source ID for further tests
if command -v jq &> /dev/null; then
    RSS_SOURCE_ID=$(echo "$RSS_RESPONSE" | jq -r '.data.id // empty')
else
    RSS_SOURCE_ID=$(echo "$RSS_RESPONSE" | grep -o '"id":"[^"]*"' | head -1 | sed 's/"id":"\(.*\)"/\1/')
fi

# Step 4: Create Twitter source
echo ""
echo "➕ Step 4: Creating Twitter source..."
TWITTER_DATA='{
    "type": "twitter",
    "url": "@elonmusk",
    "name": "Elon Musk"
}'
TWITTER_RESPONSE=$(make_request "POST" "/v1/sources/" "$TWITTER_DATA")
echo "Response: $TWITTER_RESPONSE"

# Step 5: Test invalid source
echo ""
echo "🚫 Step 5: Testing invalid source (should fail)..."
INVALID_DATA='{
    "type": "rss",
    "url": "not-a-valid-url",
    "name": "Invalid Source"
}'
INVALID_RESPONSE=$(make_request "POST" "/v1/sources/" "$INVALID_DATA")
echo "Response: $INVALID_RESPONSE"

# Step 6: Get all sources
echo ""
echo "📋 Step 6: Getting all sources..."
ALL_SOURCES_RESPONSE=$(make_request "GET" "/v1/sources/")
echo "Response: $ALL_SOURCES_RESPONSE"

if [ -n "$RSS_SOURCE_ID" ]; then
    # Step 7: Get individual source
    echo ""
    echo "🔍 Step 7: Getting individual source..."
    SINGLE_SOURCE_RESPONSE=$(make_request "GET" "/v1/sources/$RSS_SOURCE_ID")
    echo "Response: $SINGLE_SOURCE_RESPONSE"
    
    # Step 8: Update source
    echo ""
    echo "✏️ Step 8: Updating source..."
    UPDATE_DATA='{
        "name": "TechCrunch Updated",
        "active": false
    }'
    UPDATE_RESPONSE=$(make_request "PUT" "/v1/sources/$RSS_SOURCE_ID" "$UPDATE_DATA")
    echo "Response: $UPDATE_RESPONSE"
    
    # Step 9: Check source status
    echo ""
    echo "🩺 Step 9: Checking source health..."
    STATUS_RESPONSE=$(make_request "GET" "/v1/sources/$RSS_SOURCE_ID/status")
    echo "Response: $STATUS_RESPONSE"
    
    # Step 10: Trigger health check
    echo ""
    echo "🔄 Step 10: Triggering manual health check..."
    CHECK_RESPONSE=$(make_request "POST" "/v1/sources/$RSS_SOURCE_ID/check")
    echo "Response: $CHECK_RESPONSE"
    
    # Step 11: Delete source
    echo ""
    echo "🗑️ Step 11: Deleting source..."
    DELETE_RESPONSE=$(make_request "DELETE" "/v1/sources/$RSS_SOURCE_ID")
    echo "Response: $DELETE_RESPONSE"
else
    echo "⚠️ Skipping individual source tests - no valid source ID"
fi

# Step 12: Test unauthorized access
echo ""
echo "🔒 Step 12: Testing unauthorized access..."
UNAUTH_RESPONSE=$(curl -s -X GET \
    -H "Accept: application/json" \
    "$BASE_URL/v1/sources/")
echo "Response: $UNAUTH_RESPONSE"

echo ""
echo "✅ Test script completed!"
echo "Check the responses above to verify functionality."
