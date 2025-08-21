#!/usr/bin/env python3
"""
Test script for authentication endpoints using requests.
"""

import requests
import json
import sys


BASE_URL = "http://localhost:8001"


def test_auth_flow():
    """Test the complete authentication flow."""
    print("🧪 Testing CreatorPulse Authentication Flow")
    print("=" * 50)
    
    # Test data (use real email format that Supabase accepts)
    test_user = {
        "email": "testuser2@gmail.com",
        "password": "TestPassword123!", 
        "timezone": "UTC"
    }
    
    try:
        # 1. Test Registration
        print("\n1. 📝 Testing Registration...")
        register_response = requests.post(
            f"{BASE_URL}/v1/auth/register",
            json=test_user,
            timeout=10
        )
        
        print(f"Status: {register_response.status_code}")
        print(f"Response: {json.dumps(register_response.json(), indent=2)}")
        
        if register_response.status_code == 200:
            print("✅ Registration successful!")
        else:
            print("❌ Registration failed")
        
        # 2. Test Login
        print("\n2. 🔐 Testing Login...")
        login_response = requests.post(
            f"{BASE_URL}/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            },
            timeout=10
        )
        
        print(f"Status: {login_response.status_code}")
        login_data = login_response.json()
        print(f"Response: {json.dumps(login_data, indent=2)}")
        
        if login_response.status_code == 200 and 'data' in login_data:
            token = login_data['data']['token']
            print("✅ Login successful!")
            print(f"JWT Token: {token[:50]}...")
            
            # 3. Test Get Current User
            print("\n3. 👤 Testing Get Current User...")
            headers = {"Authorization": f"Bearer {token}"}
            
            me_response = requests.get(
                f"{BASE_URL}/v1/auth/me",
                headers=headers,
                timeout=10
            )
            
            print(f"Status: {me_response.status_code}")
            print(f"Response: {json.dumps(me_response.json(), indent=2)}")
            
            if me_response.status_code == 200:
                print("✅ Get current user successful!")
            else:
                print("❌ Get current user failed")
            
            # 4. Test Logout
            print("\n4. 📤 Testing Logout...")
            logout_response = requests.post(
                f"{BASE_URL}/v1/auth/logout",
                headers=headers,
                timeout=10
            )
            
            print(f"Status: {logout_response.status_code}")
            print(f"Response: {json.dumps(logout_response.json(), indent=2)}")
            
            if logout_response.status_code == 200:
                print("✅ Logout successful!")
            else:
                print("❌ Logout failed")
                
        else:
            print("❌ Login failed")
            return
        
        # 5. Test Password Reset
        print("\n5. 🔄 Testing Password Reset...")
        reset_response = requests.post(
            f"{BASE_URL}/v1/auth/reset-password",
            json={"email": test_user["email"]},
            timeout=10
        )
        
        print(f"Status: {reset_response.status_code}")
        print(f"Response: {json.dumps(reset_response.json(), indent=2)}")
        
        if reset_response.status_code == 200:
            print("✅ Password reset successful!")
        else:
            print("❌ Password reset failed")
        
        print("\n🎉 Authentication flow test completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Make sure the server is running:")
        print("   uvicorn app.main:app --reload --port 8001")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_auth_flow()
