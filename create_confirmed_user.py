#!/usr/bin/env python3
"""
Create a confirmed test user for testing.
"""
import asyncio
import httpx
from supabase import create_client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

async def create_confirmed_user():
    """Create a confirmed test user."""
    
    print("🔧 Creating confirmed test user...")
    
    # Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        return None
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Test user credentials
    test_email = "test-confirmed@gmail.com"
    test_password = "TestPassword123!"
    
    try:
        # Create user in Supabase Auth
        auth_response = supabase.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True  # Immediately confirm email
        })
        
        if auth_response.user:
            print(f"✅ Created confirmed user: {test_email}")
            print(f"   User ID: {auth_response.user.id}")
            
            # Create user in our database
            user_data = {
                "id": auth_response.user.id,
                "email": test_email,
                "password_hash": "dummy_hash_for_testing",
                "timezone": "UTC",
                "delivery_time": "08:00:00",
                "active": True,
                "email_verified": True
            }
            
            print("✅ User ready for testing!")
            print(f"   Email: {test_email}")
            print(f"   Password: {test_password}")
            print(f"   Status: Email confirmed")
            
            return {
                "email": test_email,
                "password": test_password,
                "user_id": auth_response.user.id
            }
            
        else:
            print("❌ Failed to create user")
            return None
            
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(create_confirmed_user())
