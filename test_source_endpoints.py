#!/usr/bin/env python3
"""
Test script for Source Management Endpoints (Task 16)
"""
import asyncio
import json
import httpx
from typing import Optional, Dict, Any

# Test configuration
BASE_URL = "http://127.0.0.1:8001"
TEST_USER = {
    "email": "test-confirmed@gmail.com",
    "password": "TestPassword123!"
}

# Test data
TEST_SOURCES = [
    {
        "type": "rss",
        "url": "https://feeds.feedburner.com/TechCrunch",
        "name": "TechCrunch"
    },
    {
        "type": "rss", 
        "url": "https://rss.cnn.com/rss/edition.rss",
        "name": "CNN News"
    },
    {
        "type": "twitter",
        "url": "@elonmusk",
        "name": "Elon Musk"
    },
    {
        "type": "twitter",
        "url": "openai",  # Test without @ prefix
        "name": "OpenAI"
    }
]

INVALID_SOURCES = [
    {
        "type": "rss",
        "url": "not-a-valid-url",
        "name": "Invalid RSS"
    },
    {
        "type": "twitter",
        "url": "@invalid-handle-with-special-chars!",
        "name": "Invalid Twitter"
    },
    {
        "type": "rss",
        "url": "https://nonexistent-domain-12345.com/rss",
        "name": "Nonexistent RSS"
    }
]


class SourceEndpointTester:
    """Test runner for source management endpoints."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.created_sources = []
        
    async def setup(self):
        """Setup authentication for tests."""
        print("🔐 Setting up authentication...")
        
        # Login to get token
        login_response = await self.client.post(
            f"{BASE_URL}/v1/auth/login",
            headers={"Content-Type": "application/json"},
            json=TEST_USER
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"   Response: {login_response.text}")
            return False
            
        login_data = login_response.json()
        if not login_data.get("success"):
            print(f"❌ Login unsuccessful: {login_data}")
            return False
            
        self.token = login_data["data"]["token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        print(f"✅ Authentication successful")
        print(f"   Token: {self.token[:20]}...")
        return True
    
    async def cleanup(self):
        """Cleanup created test data."""
        print("\n🧹 Cleaning up test data...")
        
        for source_id in self.created_sources:
            try:
                response = await self.client.delete(
                    f"{BASE_URL}/v1/sources/{source_id}",
                    headers=self.headers
                )
                if response.status_code == 200:
                    print(f"   ✅ Deleted source {source_id}")
                else:
                    print(f"   ⚠️ Failed to delete source {source_id}: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error deleting source {source_id}: {e}")
        
        await self.client.aclose()
    
    async def test_get_empty_sources(self):
        """Test getting sources when none exist."""
        print("\n📋 Testing GET /sources (empty list)...")
        
        response = await self.client.get(
            f"{BASE_URL}/v1/sources/",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            sources = data.get("data", [])
            print(f"✅ GET /sources successful: {len(sources)} sources found")
            return True
        else:
            print(f"❌ GET /sources failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    async def test_create_valid_sources(self):
        """Test creating valid sources."""
        print("\n➕ Testing POST /sources (valid sources)...")
        success_count = 0
        
        for i, source_data in enumerate(TEST_SOURCES):
            print(f"   Testing source {i+1}: {source_data['name']} ({source_data['type']})")
            
            response = await self.client.post(
                f"{BASE_URL}/v1/sources/",
                headers=self.headers,
                json=source_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    source_id = data["data"]["id"]
                    self.created_sources.append(source_id)
                    print(f"   ✅ Created source: {data['data']['name']} (ID: {source_id})")
                    success_count += 1
                else:
                    print(f"   ❌ Creation unsuccessful: {data}")
            else:
                print(f"   ❌ Creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
        
        print(f"📊 Created {success_count}/{len(TEST_SOURCES)} valid sources")
        return success_count > 0
    
    async def test_create_invalid_sources(self):
        """Test creating invalid sources."""
        print("\n🚫 Testing POST /sources (invalid sources)...")
        rejection_count = 0
        
        for i, source_data in enumerate(INVALID_SOURCES):
            print(f"   Testing invalid source {i+1}: {source_data['name']}")
            
            response = await self.client.post(
                f"{BASE_URL}/v1/sources/",
                headers=self.headers,
                json=source_data
            )
            
            if response.status_code == 422:
                print(f"   ✅ Correctly rejected: {response.status_code}")
                rejection_count += 1
            elif response.status_code == 200:
                data = response.json()
                if not data.get("success"):
                    print(f"   ✅ Correctly rejected: {data.get('error', {}).get('message', 'Unknown error')}")
                    rejection_count += 1
                else:
                    # Clean up if somehow created
                    source_id = data["data"]["id"]
                    self.created_sources.append(source_id)
                    print(f"   ⚠️ Unexpectedly accepted invalid source")
            else:
                print(f"   ❌ Unexpected response: {response.status_code}")
                print(f"   Response: {response.text}")
        
        print(f"📊 Rejected {rejection_count}/{len(INVALID_SOURCES)} invalid sources")
        return rejection_count > 0
    
    async def test_get_sources_with_data(self):
        """Test getting sources when data exists."""
        print("\n📋 Testing GET /sources (with data)...")
        
        response = await self.client.get(
            f"{BASE_URL}/v1/sources/",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            sources = data.get("data", [])
            print(f"✅ GET /sources successful: {len(sources)} sources found")
            
            for source in sources:
                print(f"   - {source['name']} ({source['type']}): {source['url']}")
            
            return len(sources) > 0
        else:
            print(f"❌ GET /sources failed: {response.status_code}")
            return False
    
    async def test_get_individual_source(self):
        """Test getting individual source by ID."""
        print("\n🔍 Testing GET /sources/{id}...")
        
        if not self.created_sources:
            print("   ⚠️ No sources to test - skipping")
            return True
            
        source_id = self.created_sources[0]
        response = await self.client.get(
            f"{BASE_URL}/v1/sources/{source_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            source = data.get("data", {})
            print(f"✅ GET /sources/{source_id} successful")
            print(f"   Name: {source.get('name')}")
            print(f"   Type: {source.get('type')}")
            print(f"   URL: {source.get('url')}")
            return True
        else:
            print(f"❌ GET /sources/{source_id} failed: {response.status_code}")
            return False
    
    async def test_update_source(self):
        """Test updating a source."""
        print("\n✏️ Testing PUT /sources/{id}...")
        
        if not self.created_sources:
            print("   ⚠️ No sources to test - skipping")
            return True
            
        source_id = self.created_sources[0]
        update_data = {
            "name": "Updated Source Name",
            "active": False
        }
        
        response = await self.client.put(
            f"{BASE_URL}/v1/sources/{source_id}",
            headers=self.headers,
            json=update_data
        )
        
        if response.status_code == 200:
            data = response.json()
            source = data.get("data", {})
            print(f"✅ PUT /sources/{source_id} successful")
            print(f"   Updated name: {source.get('name')}")
            print(f"   Updated active: {source.get('active')}")
            return True
        else:
            print(f"❌ PUT /sources/{source_id} failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    async def test_source_status(self):
        """Test checking source status."""
        print("\n🩺 Testing GET /sources/{id}/status...")
        
        if not self.created_sources:
            print("   ⚠️ No sources to test - skipping")
            return True
            
        source_id = self.created_sources[0]
        response = await self.client.get(
            f"{BASE_URL}/v1/sources/{source_id}/status",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("data", {})
            print(f"✅ GET /sources/{source_id}/status successful")
            print(f"   Healthy: {status.get('is_healthy')}")
            print(f"   Response time: {status.get('response_time_ms')}ms")
            print(f"   Content count: {status.get('content_count')}")
            if status.get('error_message'):
                print(f"   Error: {status.get('error_message')}")
            return True
        else:
            print(f"❌ GET /sources/{source_id}/status failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    async def test_trigger_health_check(self):
        """Test manually triggering health check."""
        print("\n🔄 Testing POST /sources/{id}/check...")
        
        if not self.created_sources:
            print("   ⚠️ No sources to test - skipping")
            return True
            
        source_id = self.created_sources[0]
        response = await self.client.post(
            f"{BASE_URL}/v1/sources/{source_id}/check",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("data", {})
            print(f"✅ POST /sources/{source_id}/check successful")
            print(f"   Healthy: {status.get('is_healthy')}")
            print(f"   Response time: {status.get('response_time_ms')}ms")
            return True
        else:
            print(f"❌ POST /sources/{source_id}/check failed: {response.status_code}")
            return False
    
    async def test_delete_source(self):
        """Test deleting a source."""
        print("\n🗑️ Testing DELETE /sources/{id}...")
        
        if not self.created_sources:
            print("   ⚠️ No sources to test - skipping")
            return True
            
        # Test with last created source
        source_id = self.created_sources.pop()
        response = await self.client.delete(
            f"{BASE_URL}/v1/sources/{source_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ DELETE /sources/{source_id} successful")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print(f"❌ DELETE /sources/{source_id} failed: {response.status_code}")
            return False
    
    async def test_unauthorized_access(self):
        """Test endpoints without authentication."""
        print("\n🔒 Testing unauthorized access...")
        
        # Test without Authorization header
        response = await self.client.get(f"{BASE_URL}/v1/sources/")
        
        if response.status_code == 401:
            print("✅ Correctly rejected unauthorized request")
            return True
        else:
            print(f"❌ Unexpected response for unauthorized request: {response.status_code}")
            return False


async def run_tests():
    """Run all source endpoint tests."""
    print("🧪 Testing CreatorPulse Source Management Endpoints")
    print("=" * 60)
    
    tester = SourceEndpointTester()
    
    try:
        # Setup
        if not await tester.setup():
            print("❌ Setup failed - aborting tests")
            return
        
        # Run tests
        tests = [
            ("Unauthorized Access", tester.test_unauthorized_access),
            ("Get Empty Sources", tester.test_get_empty_sources),
            ("Create Valid Sources", tester.test_create_valid_sources),
            ("Create Invalid Sources", tester.test_create_invalid_sources),
            ("Get Sources With Data", tester.test_get_sources_with_data),
            ("Get Individual Source", tester.test_get_individual_source),
            ("Update Source", tester.test_update_source),
            ("Check Source Status", tester.test_source_status),
            ("Trigger Health Check", tester.test_trigger_health_check),
            ("Delete Source", tester.test_delete_source),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed += 1
            except Exception as e:
                print(f"❌ Test '{test_name}' crashed: {e}")
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Source management endpoints are working correctly.")
        else:
            print(f"⚠️ {total - passed} tests failed. Check the output above for details.")
        
    except Exception as e:
        print(f"❌ Test runner crashed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    asyncio.run(run_tests())
