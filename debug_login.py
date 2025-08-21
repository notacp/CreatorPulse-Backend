#!/usr/bin/env python3
"""
Debug login functionality
"""
import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client
from app.core.config import settings

# Load environment variables
load_dotenv()

async def test_login():
    """Test direct Supabase login"""
    
    print("🔐 Testing Direct Supabase Login")
    print("=" * 50)
    
    # Test Supabase client
    try:
        supabase = create_client(settings.supabase_url, settings.supabase_service_key)
        print(f"✅ Supabase client created")
        print(f"   URL: {settings.supabase_url}")
        
        # Test login
        email = "testuser4@gmail.com"
        password = "TestPassword123!"
        
        print(f"\n🧪 Testing login with: {email}")
        
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if auth_response.user:
            print(f"✅ Login successful!")
            print(f"   User ID: {auth_response.user.id}")
            print(f"   Email: {auth_response.user.email}")
            print(f"   Email confirmed: {auth_response.user.email_confirmed_at}")
        else:
            print(f"❌ Login failed - no user returned")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"   Type: {type(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_login())
