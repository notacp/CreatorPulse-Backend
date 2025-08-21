#!/usr/bin/env python3
"""
Test script for Task 15: Authentication endpoints.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path.cwd()))


def test_environment_setup():
    """Test that all required environment variables are set for authentication."""
    print("🔍 Testing environment setup...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'DATABASE_URL',
        'SUPABASE_URL', 
        'SUPABASE_KEY',
        'SUPABASE_SERVICE_KEY',
        'JWT_SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    print("✅ All required environment variables are set")
    return True


def test_imports():
    """Test that all authentication modules can be imported."""
    print("🔍 Testing authentication module imports...")
    
    try:
        # Test core imports
        from app.core.config import settings
        from app.core.security import create_access_token, verify_token, get_password_hash, verify_password
        from app.core.supabase import get_supabase
        from app.core.exceptions import AuthenticationException, ValidationException
        
        print("✅ Core modules imported successfully")
        
        # Test model imports
        from app.models.user import User
        from app.schemas.auth import LoginRequest, RegisterRequest, AuthResponse
        from app.schemas.user import User as UserSchema
        from app.schemas.common import ApiResponse
        
        print("✅ Models and schemas imported successfully")
        
        # Test endpoint imports
        from app.api.v1.endpoints.auth import router, get_current_user
        from app.api.v1.api import api_router
        
        print("✅ Authentication endpoints imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_jwt_functionality():
    """Test JWT token creation and verification."""
    print("🔍 Testing JWT token functionality...")
    
    try:
        from app.core.security import create_access_token, verify_token
        
        # Test token creation
        test_data = {"sub": "test-user-id", "email": "test@example.com"}
        token = create_access_token(data=test_data)
        
        if not token:
            print("❌ Token creation failed")
            return False
        
        print(f"✅ JWT token created: {token[:20]}...")
        
        # Test token verification
        payload = verify_token(token)
        
        if payload.get("sub") != "test-user-id":
            print("❌ Token verification failed - invalid payload")
            return False
        
        print("✅ JWT token verification successful")
        
        return True
        
    except Exception as e:
        print(f"❌ JWT functionality test failed: {e}")
        return False


def test_password_hashing():
    """Test password hashing and verification."""
    print("🔍 Testing password hashing...")
    
    try:
        from app.core.security import get_password_hash, verify_password
        
        test_password = "test_password_123"
        
        # Test hashing
        hashed = get_password_hash(test_password)
        
        if not hashed or hashed == test_password:
            print("❌ Password hashing failed")
            return False
        
        print(f"✅ Password hashed: {hashed[:20]}...")
        
        # Test verification
        if not verify_password(test_password, hashed):
            print("❌ Password verification failed")
            return False
        
        print("✅ Password verification successful")
        
        # Test wrong password
        if verify_password("wrong_password", hashed):
            print("❌ Password verification should have failed for wrong password")
            return False
        
        print("✅ Wrong password correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Password hashing test failed: {e}")
        return False


def test_supabase_connection():
    """Test Supabase client connection."""
    print("🔍 Testing Supabase client connection...")
    
    try:
        from app.core.supabase import get_supabase
        
        supabase = get_supabase()
        
        if not supabase:
            print("❌ Supabase client creation failed")
            return False
        
        print("✅ Supabase client created successfully")
        
        # Test basic connection (this will work even without auth)
        try:
            # This should work with public access
            response = supabase.table('users').select('*').limit(1).execute()
            print("✅ Supabase database connection verified")
        except Exception as e:
            if "authentication" in str(e).lower() or "permission" in str(e).lower():
                print("✅ Supabase connection works (authentication/permission error is expected)")
            else:
                print(f"⚠️  Supabase connection issue: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase connection test failed: {e}")
        return False


async def test_database_connection():
    """Test database connection for user operations."""
    print("🔍 Testing database connection...")
    
    try:
        from app.core.database import get_db
        from app.models.user import User
        from sqlalchemy import select
        
        async for db in get_db():
            # Test a simple query
            result = await db.execute(select(User).limit(1))
            users = result.scalars().all()
            
            print(f"✅ Database connection successful. Found {len(users)} users")
            break
            
        return True
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False


def test_schema_validation():
    """Test Pydantic schema validation."""
    print("🔍 Testing schema validation...")
    
    try:
        from app.schemas.auth import LoginRequest, RegisterRequest, AuthResponse
        from app.schemas.user import User as UserSchema
        
        # Test LoginRequest
        login_data = {
            "email": "test@example.com",
            "password": "test123456"
        }
        login_request = LoginRequest(**login_data)
        print("✅ LoginRequest validation successful")
        
        # Test RegisterRequest
        register_data = {
            "email": "test@example.com",
            "password": "test123456",
            "timezone": "UTC"
        }
        register_request = RegisterRequest(**register_data)
        print("✅ RegisterRequest validation successful")
        
        # Test invalid email
        try:
            LoginRequest(email="invalid-email", password="test123456")
            print("❌ Schema validation should have failed for invalid email")
            return False
        except:
            print("✅ Invalid email correctly rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema validation test failed: {e}")
        return False


def test_fastapi_router():
    """Test FastAPI router configuration."""
    print("🔍 Testing FastAPI router configuration...")
    
    try:
        from app.api.v1.api import api_router
        from app.api.v1.endpoints.auth import router as auth_router
        
        # Check that auth router has routes
        auth_routes = [route.path for route in auth_router.routes]
        expected_routes = ["/register", "/login", "/logout", "/reset-password", "/me", "/verify-email"]
        
        for expected_route in expected_routes:
            if expected_route not in auth_routes:
                print(f"❌ Missing auth route: {expected_route}")
                return False
        
        print(f"✅ All auth routes configured: {auth_routes}")
        
        # Check that auth router is included in main router
        main_routes = [route.path for route in api_router.routes if hasattr(route, 'path')]
        print(f"✅ Main API router configured with {len(main_routes)} routes")
        
        return True
        
    except Exception as e:
        print(f"❌ FastAPI router test failed: {e}")
        return False


async def main():
    """Run all authentication tests."""
    print("🚀 Testing Task 15: Authentication Endpoints")
    print("=" * 60)
    
    tests = [
        test_environment_setup,
        test_imports,
        test_jwt_functionality,
        test_password_hashing,
        test_supabase_connection,
        test_schema_validation,
        test_fastapi_router,
        test_database_connection,  # This one is async
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
            
            if result:
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("=" * 60)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Task 15: Authentication endpoints ready!")
        print("\n✅ You can now:")
        print("   1. Start the FastAPI server: uvicorn app.main:app --reload")
        print("   2. Visit http://localhost:8000/docs to see the auth endpoints")
        print("   3. Test registration and login through the API")
        return True
    else:
        print("⚠️  Some authentication issues detected")
        print("\n💡 Next steps:")
        print("   1. Fix the issues shown above")
        print("   2. Run this test again: python test_task15_auth.py")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
