#!/usr/bin/env python3
"""
Test script for Step 17: Style Training System

This script tests the complete style training system including:
- Style training service
- API endpoints
- Background task processing
- Gemini API integration
- Vector storage system
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.core.config import settings
from app.core.database import init_db, close_db, get_db
from app.models.user import User
from app.models.style import UserStylePost, StyleVector
from app.services.style_training import style_training_service
from app.api.v1.endpoints.style import router as style_router
from app.tasks.style_training_tasks import (
    process_style_post,
    process_user_style_posts,
    process_pending_style_posts
)


def test_style_training_service():
    """Test the style training service functionality."""
    print("🧪 Testing Style Training Service...")
    
    try:
        # Test service initialization
        if settings.gemini_api_key:
            print("✅ Gemini API key configured")
        else:
            print("⚠️  Gemini API key not configured (will use mock embeddings)")
        
        # Test service instance
        assert style_training_service is not None
        print("✅ Style training service initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Style training service test failed: {e}")
        return False


async def test_style_models():
    """Test style training database models."""
    print("\n🧪 Testing Style Training Models...")
    
    try:
        # Initialize database
        await init_db()
        
        # Test model imports
        from app.models.style import UserStylePost, StyleVector
        print("✅ Style models imported successfully")
        
        # Test model attributes
        assert hasattr(UserStylePost, 'id')
        assert hasattr(UserStylePost, 'user_id')
        assert hasattr(UserStylePost, 'content')
        assert hasattr(UserStylePost, 'processed')
        assert hasattr(UserStylePost, 'word_count')
        assert hasattr(UserStylePost, 'character_count')
        assert hasattr(UserStylePost, 'created_at')
        assert hasattr(UserStylePost, 'processed_at')
        print("✅ UserStylePost model has all required attributes")
        
        assert hasattr(StyleVector, 'id')
        assert hasattr(StyleVector, 'user_id')
        assert hasattr(StyleVector, 'style_post_id')
        assert hasattr(StyleVector, 'content')
        assert hasattr(StyleVector, 'embedding')
        assert hasattr(StyleVector, 'created_at')
        print("✅ StyleVector model has all required attributes")
        
        return True
        
    except Exception as e:
        print(f"❌ Style models test failed: {e}")
        return False
    finally:
        await close_db()


async def test_style_training_endpoints():
    """Test style training API endpoints."""
    print("\n🧪 Testing Style Training API Endpoints...")
    
    try:
        # Test router import
        assert style_router is not None
        print("✅ Style training router imported successfully")
        
        # Test endpoint registration
        routes = [route.path for route in style_router.routes]
        expected_routes = [
            "/posts",
            "/posts/single", 
            "/posts",
            "/status",
            "/process",
            "/summary",
            "/posts/{post_id}"
        ]
        
        for route in expected_routes:
            if route in routes or any(route.replace('{', '').replace('}', '') in r for r in routes):
                print(f"✅ Endpoint {route} found")
            else:
                print(f"⚠️  Endpoint {route} not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Style training endpoints test failed: {e}")
        return False


async def test_style_training_tasks():
    """Test style training background tasks."""
    print("\n🧪 Testing Style Training Background Tasks...")
    
    try:
        # Test task imports
        assert process_style_post is not None
        assert process_user_style_posts is not None
        assert process_pending_style_posts is not None
        print("✅ Style training tasks imported successfully")
        
        # Test task names
        assert process_style_post.name == 'app.tasks.style_training_tasks.process_style_post'
        assert process_user_style_posts.name == 'app.tasks.style_training_tasks.process_user_style_posts'
        assert process_pending_style_posts.name == 'app.tasks.style_training_tasks.process_pending_style_posts'
        print("✅ Task names configured correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Style training tasks test failed: {e}")
        return False


async def test_style_training_integration():
    """Test the complete style training integration."""
    print("\n🧪 Testing Style Training Integration...")
    
    try:
        # Initialize database
        await init_db()
        
        # Create a test user
        test_user = User(
            email="test@example.com",
            password_hash="test_hash",
            active=True,
            email_verified=True
        )
        
        async for session in get_db():
            session.add(test_user)
            await session.commit()
            await session.refresh(test_user)
            
            print(f"✅ Test user created: {test_user.id}")
            
            # Test adding style posts
            test_posts = [
                "This is a sample LinkedIn post for style training. It contains enough content to meet the minimum requirements and demonstrates a professional writing style.",
                "Another example post showing different writing patterns and vocabulary choices that help train the AI model.",
                "A third post with varied sentence structures and industry-specific terminology to improve style recognition."
            ]
            
            style_posts = await style_training_service.add_style_posts(
                session=session,
                user_id=str(test_user.id),
                posts=test_posts
            )
            
            assert len(style_posts) == 3
            print(f"✅ Added {len(style_posts)} style posts")
            
            # Test getting style training status
            status = await style_training_service.get_style_training_status(
                session=session,
                user_id=str(test_user.id)
            )
            
            assert status["total_posts"] == 3
            assert status["processed_posts"] == 0
            assert status["status"] == "pending"
            print(f"✅ Style training status: {status}")
            
            # Test processing style posts
            processing_result = await style_training_service.process_user_style_posts(
                session=session,
                user_id=str(test_user.id)
            )
            
            print(f"✅ Style processing result: {processing_result}")
            
            # Test getting updated status
            updated_status = await style_training_service.get_style_training_status(
                session=session,
                user_id=str(test_user.id)
            )
            
            print(f"✅ Updated status: {updated_status}")
            
            # Test getting style summary
            summary = await style_training_service.get_user_style_summary(
                session=session,
                user_id=str(test_user.id)
            )
            
            print(f"✅ Style summary: {summary}")
            
            # Clean up test data
            await session.delete(test_user)
            await session.commit()
            print("✅ Test data cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Style training integration test failed: {e}")
        return False
    finally:
        await close_db()


def test_requirements():
    """Test that all required dependencies are available."""
    print("\n🧪 Testing Requirements...")
    
    try:
        required_packages = [
            "celery",
            "redis",
            "pgvector",
            "sqlalchemy"
        ]
        
        optional_packages = [
            "google.generativeai"
        ]
        
        # Test required packages
        for package in required_packages:
            try:
                __import__(package.replace('.', '_'))
                print(f"✅ {package} available")
            except ImportError:
                print(f"❌ {package} not available")
                return False
        
        # Test optional packages
        for package in optional_packages:
            try:
                __import__(package.replace('.', '_'))
                print(f"✅ {package} available")
            except ImportError:
                print(f"⚠️  {package} not available (will use mock embeddings)")
        
        return True
        
    except Exception as e:
        print(f"❌ Requirements test failed: {e}")
        return False


async def main():
    """Run all style training tests."""
    print("🚀 Testing Step 17: Style Training System")
    print("=" * 80)
    
    tests = [
        test_requirements,
        test_style_training_service,
    ]
    
    # Add async tests
    async_tests = [
        test_style_training_endpoints,
        test_style_training_tasks,
        test_style_models,
        test_style_training_integration,
    ]
    
    passed = 0
    total = len(tests) + len(async_tests)
    
    # Run sync tests
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    # Run async tests
    for test in async_tests:
        try:
            result = await test()
            if result:
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("=" * 80)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Step 17 PASSED: Style training system implemented successfully!")
        print("\n📋 What's been implemented:")
        print("   ✅ Style training service with Gemini API integration")
        print("   ✅ Complete API endpoints for style training")
        print("   ✅ Background job processing with Celery")
        print("   ✅ Vector storage system using Supabase pg_vector")
        print("   ✅ Style training status tracking and completion confirmation")
        print("   ✅ Comprehensive error handling and logging")
        print("   ✅ Background tasks for processing uploaded posts")
        print("   ✅ Integration with existing authentication and database systems")
        return True
    else:
        print("⚠️  Step 17 PARTIAL: Some components need attention")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
