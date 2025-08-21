#!/usr/bin/env python3
"""
Debug script to test individual authentication components.
"""

import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from dotenv import load_dotenv
load_dotenv()

async def test_database_connection():
    """Test database connection."""
    print("🔍 Testing database connection...")
    try:
        from app.core.database import get_db
        from app.models.user import User
        from sqlalchemy import select
        
        async for db in get_db():
            result = await db.execute(select(User).limit(1))
            users = result.scalars().all()
            print(f"✅ Database connection OK. Found {len(users)} users.")
            break
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    return True

def test_supabase_connection():
    """Test Supabase connection."""
    print("🔍 Testing Supabase connection...")
    try:
        from app.core.supabase import get_supabase
        
        supabase = get_supabase()
        # Test a simple operation
        result = supabase.table('users').select('*').limit(1).execute()
        print(f"✅ Supabase connection OK.")
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def test_environment_variables():
    """Test required environment variables."""
    print("🔍 Testing environment variables...")
    
    import os
    required_vars = [
        'DATABASE_URL', 'SUPABASE_URL', 'SUPABASE_KEY', 
        'SUPABASE_SERVICE_KEY', 'JWT_SECRET_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing variables: {missing}")
        return False
    
    print("✅ All environment variables present.")
    return True

def test_jwt_functionality():
    """Test JWT token creation."""
    print("🔍 Testing JWT functionality...")
    try:
        from app.core.security import create_access_token, verify_token
        
        # Test token creation
        token = create_access_token(data={"sub": "test-user-id"})
        print(f"✅ JWT token created: {token[:20]}...")
        
        # Test token verification
        payload = verify_token(token)
        if payload.get("sub") == "test-user-id":
            print("✅ JWT token verification OK.")
            return True
        else:
            print("❌ JWT token verification failed.")
            return False
            
    except Exception as e:
        print(f"❌ JWT functionality failed: {e}")
        return False

async def test_supabase_auth():
    """Test Supabase Auth functionality."""
    print("🔍 Testing Supabase Auth...")
    try:
        from app.core.supabase import get_supabase
        
        supabase = get_supabase()
        
        # Try to sign up a test user (use a real-looking email)
        test_email = "testuser123@gmail.com"
        test_password = "testpassword123"
        
        try:
            response = supabase.auth.sign_up({
                "email": test_email,
                "password": test_password
            })
            
            if response.user:
                print(f"✅ Supabase Auth signup worked. User ID: {response.user.id}")
                
                # Try to sign in
                signin_response = supabase.auth.sign_in_with_password({
                    "email": test_email,
                    "password": test_password
                })
                
                if signin_response.user:
                    print("✅ Supabase Auth signin worked.")
                    return True
                else:
                    print("❌ Supabase Auth signin failed.")
                    return False
            else:
                print("❌ Supabase Auth signup failed - no user returned.")
                return False
                
        except Exception as auth_e:
            if "User already registered" in str(auth_e):
                print("⚠️  User already exists, trying signin...")
                
                signin_response = supabase.auth.sign_in_with_password({
                    "email": test_email,
                    "password": test_password
                })
                
                if signin_response.user:
                    print("✅ Supabase Auth signin worked.")
                    return True
                else:
                    print("❌ Supabase Auth signin failed.")
                    return False
            else:
                print(f"❌ Supabase Auth error: {auth_e}")
                return False
        
    except Exception as e:
        print(f"❌ Supabase Auth test failed: {e}")
        return False

def test_user_model():
    """Test User model creation."""
    print("🔍 Testing User model...")
    try:
        from app.models.user import User
        
        # Test creating a user instance
        user = User(
            id="550e8400-e29b-41d4-a716-446655440000",
            email="test@example.com",
            timezone="UTC",
            active=True
        )
        
        print(f"✅ User model creation OK: {user.email}")
        return True
        
    except Exception as e:
        print(f"❌ User model test failed: {e}")
        return False

def test_schemas():
    """Test Pydantic schemas."""
    print("🔍 Testing schemas...")
    try:
        from app.schemas.auth import RegisterRequest, LoginRequest
        
        # Test RegisterRequest
        register_req = RegisterRequest(
            email="test@example.com",
            password="testpassword123",
            timezone="UTC"
        )
        print(f"✅ RegisterRequest schema OK: {register_req.email}")
        
        # Test LoginRequest  
        login_req = LoginRequest(
            email="test@example.com",
            password="testpassword123"
        )
        print(f"✅ LoginRequest schema OK: {login_req.email}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

async def main():
    """Run all debug tests."""
    print("🔧 CreatorPulse Authentication Debug")
    print("=" * 40)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("JWT Functionality", test_jwt_functionality),
        ("User Model", test_user_model),
        ("Schemas", test_schemas),
        ("Database Connection", test_database_connection),
        ("Supabase Connection", test_supabase_connection),
        ("Supabase Auth", test_supabase_auth),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{name}:")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} crashed: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 40)
    print("📊 Debug Results:")
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
    
    failed_tests = [name for name, result in results if not result]
    if failed_tests:
        print(f"\n⚠️  Failed tests: {', '.join(failed_tests)}")
        print("Fix these issues before testing the API endpoints.")
    else:
        print("\n🎉 All tests passed! API endpoints should work.")

if __name__ == "__main__":
    asyncio.run(main())
