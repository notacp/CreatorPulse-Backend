#!/usr/bin/env python3
"""
Test Task 13: FastAPI Project Setup and Core Infrastructure

This script tests the core infrastructure components without requiring
full database or external service connections.
"""

import sys
import os
import importlib.util
from pathlib import Path

def test_project_structure():
    """Test that the project has the correct directory structure."""
    print("🔍 Testing project structure...")
    
    required_files = [
        "app/__init__.py",
        "app/main.py",
        "app/core/__init__.py", 
        "app/core/config.py",
        "app/core/database.py",
        "app/core/exceptions.py",
        "app/core/logging.py",
        "app/core/middleware.py",
        "app/api/__init__.py",
        "app/api/health.py",
        "app/api/v1/__init__.py",
        "app/api/v1/api.py",
        "requirements.txt",
        "docker-compose.yml",
        "Dockerfile",
        "pytest.ini",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All required files exist")
    return True

def test_config_loading():
    """Test that configuration can be loaded."""
    print("🔍 Testing configuration loading...")
    
    try:
        # Add the current directory to Python path
        sys.path.insert(0, str(Path.cwd()))
        
        # Mock environment variables to avoid issues
        os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')
        os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
        os.environ.setdefault('JWT_SECRET_KEY', 'test-secret')
        
        from app.core.config import settings
        
        # Test that settings object exists and has required attributes
        required_attrs = [
            'environment', 'debug', 'database_url', 'redis_url', 
            'jwt_secret_key', 'cors_origins'
        ]
        
        for attr in required_attrs:
            if not hasattr(settings, attr):
                print(f"❌ Missing configuration attribute: {attr}")
                return False
        
        print("✅ Configuration loads successfully")
        print(f"   Environment: {settings.environment}")
        print(f"   Debug mode: {settings.debug}")
        return True
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_app_import():
    """Test that the FastAPI app can be imported."""
    print("🔍 Testing FastAPI app import...")
    
    try:
        from app.main import app
        
        # Test that it's a FastAPI instance
        from fastapi import FastAPI
        if not isinstance(app, FastAPI):
            print("❌ app is not a FastAPI instance")
            return False
        
        print("✅ FastAPI app imports successfully")
        print(f"   App title: {app.title}")
        print(f"   App version: {app.version}")
        return True
        
    except Exception as e:
        print(f"❌ App import failed: {e}")
        return False

def test_api_routes():
    """Test that API routes are properly configured."""
    print("🔍 Testing API routes configuration...")
    
    try:
        from app.main import app
        
        # Get all routes
        routes = [route.path for route in app.routes]
        
        required_routes = [
            "/",           # Root endpoint
            "/health/",    # Health check
            "/v1/",        # API v1 info
        ]
        
        missing_routes = []
        for route in required_routes:
            if route not in routes:
                missing_routes.append(route)
        
        if missing_routes:
            print(f"❌ Missing routes: {missing_routes}")
            return False
        
        print("✅ All required routes are configured")
        print(f"   Available routes: {sorted(routes)}")
        return True
        
    except Exception as e:
        print(f"❌ Route testing failed: {e}")
        return False

def test_basic_functionality():
    """Test basic app functionality using FastAPI TestClient."""
    print("🔍 Testing basic app functionality...")
    
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        # Test root endpoint
        response = client.get("/")
        if response.status_code != 200:
            print(f"❌ Root endpoint failed: {response.status_code}")
            return False
        
        data = response.json()
        if data.get("message") != "CreatorPulse API":
            print(f"❌ Unexpected root response: {data}")
            return False
        
        # Test health endpoint
        response = client.get("/health/")
        if response.status_code != 200:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
        
        health_data = response.json()
        if not health_data.get("success"):
            print(f"❌ Health check failed: {health_data}")
            return False
        
        # Test API v1 info endpoint
        response = client.get("/v1/")
        if response.status_code != 200:
            print(f"❌ API v1 endpoint failed: {response.status_code}")
            return False
        
        v1_data = response.json()
        if v1_data.get("message") != "CreatorPulse API v1":
            print(f"❌ Unexpected v1 response: {v1_data}")
            return False
        
        print("✅ All endpoints work correctly")
        print(f"   Root: {data.get('message')} v{data.get('version')}")
        print(f"   Health: {health_data['data']['status']}")
        print(f"   API v1: {v1_data.get('message')} v{v1_data.get('version')}")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_docker_configuration():
    """Test Docker configuration files."""
    print("🔍 Testing Docker configuration...")
    
    try:
        # Test Dockerfile exists and has basic structure
        dockerfile_path = Path("Dockerfile")
        if not dockerfile_path.exists():
            print("❌ Dockerfile not found")
            return False
        
        dockerfile_content = dockerfile_path.read_text()
        required_docker_elements = ["FROM", "COPY", "RUN", "EXPOSE", "CMD"]
        
        for element in required_docker_elements:
            if element not in dockerfile_content:
                print(f"❌ Dockerfile missing {element}")
                return False
        
        # Test docker-compose.yml exists and has basic structure
        compose_path = Path("docker-compose.yml")
        if not compose_path.exists():
            print("❌ docker-compose.yml not found")
            return False
        
        compose_content = compose_path.read_text()
        required_compose_elements = ["version:", "services:", "api:", "db:", "redis:"]
        
        for element in required_compose_elements:
            if element not in compose_content:
                print(f"❌ docker-compose.yml missing {element}")
                return False
        
        print("✅ Docker configuration is valid")
        return True
        
    except Exception as e:
        print(f"❌ Docker configuration test failed: {e}")
        return False

def main():
    """Run all Task 13 tests."""
    print("🚀 Testing Task 13: FastAPI Project Setup and Core Infrastructure")
    print("=" * 70)
    
    tests = [
        test_project_structure,
        test_config_loading,
        test_app_import,
        test_api_routes,
        test_basic_functionality,
        test_docker_configuration,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("=" * 70)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Task 13 PASSED: FastAPI project setup and core infrastructure working!")
        return True
    else:
        print("⚠️  Task 13 PARTIAL: Some components need attention")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
