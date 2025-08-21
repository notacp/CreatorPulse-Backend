#!/usr/bin/env python3
"""
Test Task 14: Implement database schema and models

This script tests the database schema, models, and validation implementation.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path.cwd()))

# Mock environment variables for testing
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost/test')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('JWT_SECRET_KEY', 'test-secret')


def test_model_imports():
    """Test that all database models can be imported."""
    print("🔍 Testing database model imports...")
    
    try:
        from app.models import (
            User, Source, SourceContent, UserStylePost, 
            StyleVector, GeneratedDraft, DraftFeedback, EmailDeliveryLog
        )
        
        models = [User, Source, SourceContent, UserStylePost, 
                 StyleVector, GeneratedDraft, DraftFeedback, EmailDeliveryLog]
        
        print(f"   ✅ Successfully imported {len(models)} models")
        for model in models:
            print(f"      - {model.__name__}")
        
        return True
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        return False


def test_schema_imports():
    """Test that all Pydantic schemas can be imported."""
    print("🔍 Testing Pydantic schema imports...")
    
    try:
        from app.schemas import (
            User, UserCreate, UserUpdate, UserSettings,
            Source, SourceCreate, SourceUpdate, SourceStatus,
            SourceContent, SourceContentCreate,
            Draft, GenerateDraftsRequest, GenerateDraftsResponse,
            StylePost, StyleTrainingRequest, StyleTrainingStatus,
            LoginRequest, RegisterRequest, AuthResponse,
            ApiResponse, PaginatedResponse
        )
        
        schemas = [
            User, UserCreate, UserUpdate, UserSettings,
            Source, SourceCreate, SourceUpdate, SourceStatus,
            SourceContent, SourceContentCreate,
            Draft, GenerateDraftsRequest, GenerateDraftsResponse,
            StylePost, StyleTrainingRequest, StyleTrainingStatus,
            LoginRequest, RegisterRequest, AuthResponse,
            ApiResponse, PaginatedResponse
        ]
        
        print(f"   ✅ Successfully imported {len(schemas)} schemas")
        return True
    except Exception as e:
        print(f"❌ Schema import failed: {e}")
        return False


def test_model_attributes():
    """Test that models have required attributes matching frontend interfaces."""
    print("🔍 Testing model attributes...")
    
    try:
        from app.models import User, Source, GeneratedDraft, SourceContent
        
        # Test User model attributes
        user_attrs = ['id', 'email', 'password_hash', 'timezone', 'delivery_time', 
                     'active', 'email_verified', 'created_at', 'updated_at']
        
        for attr in user_attrs:
            if not hasattr(User, attr):
                print(f"❌ User model missing attribute: {attr}")
                return False
        
        # Test Source model attributes
        source_attrs = ['id', 'user_id', 'type', 'url', 'name', 'active', 
                       'last_checked', 'error_count', 'last_error', 'created_at', 'updated_at']
        
        for attr in source_attrs:
            if not hasattr(Source, attr):
                print(f"❌ Source model missing attribute: {attr}")
                return False
        
        # Test GeneratedDraft model attributes
        draft_attrs = ['id', 'user_id', 'content', 'source_content_id', 'status', 
                      'feedback_token', 'email_sent_at', 'character_count', 'engagement_score']
        
        for attr in draft_attrs:
            if not hasattr(GeneratedDraft, attr):
                print(f"❌ GeneratedDraft model missing attribute: {attr}")
                return False
        
        # Test SourceContent model attributes
        content_attrs = ['id', 'source_id', 'title', 'content', 'url', 
                        'published_at', 'processed', 'content_hash', 'created_at']
        
        for attr in content_attrs:
            if not hasattr(SourceContent, attr):
                print(f"❌ SourceContent model missing attribute: {attr}")
                return False
        
        print("   ✅ All models have required attributes")
        return True
    except Exception as e:
        print(f"❌ Model attribute test failed: {e}")
        return False


def test_schema_validation():
    """Test Pydantic schema validation."""
    print("🔍 Testing schema validation...")
    
    try:
        from app.schemas import UserCreate, SourceCreate, Draft
        from pydantic import ValidationError
        
        # Test valid user creation
        valid_user = UserCreate(
            email="test@example.com",
            password="password123",
            timezone="America/New_York"
        )
        assert valid_user.email == "test@example.com"
        
        # Test invalid email
        try:
            invalid_user = UserCreate(
                email="invalid-email",
                password="password123"
            )
            print("❌ Should have failed validation for invalid email")
            return False
        except ValidationError:
            pass  # Expected
        
        # Test valid source creation
        valid_source = SourceCreate(
            type="rss",
            url="https://example.com/feed",
            name="Test Feed"
        )
        assert valid_source.type == "rss"
        
        # Test invalid source type
        try:
            invalid_source = SourceCreate(
                type="invalid",
                url="https://example.com",
                name="Test"
            )
            print("❌ Should have failed validation for invalid source type")
            return False
        except ValidationError:
            pass  # Expected
        
        print("   ✅ Schema validation working correctly")
        return True
    except Exception as e:
        print(f"❌ Schema validation test failed: {e}")
        return False


def test_database_connection():
    """Test database connection utilities."""
    print("🔍 Testing database connection utilities...")
    
    try:
        from app.core.database import get_db, engine, AsyncSessionLocal
        
        # Test that database utilities exist
        assert get_db is not None
        assert engine is not None
        assert AsyncSessionLocal is not None
        
        print("   ✅ Database utilities available")
        return True
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False


def test_migration_files():
    """Test that migration files exist."""
    print("🔍 Testing migration files...")
    
    try:
        migration_file = Path("migrations/001_initial_schema.sql")
        if not migration_file.exists():
            print("❌ Initial schema migration file not found")
            return False
        
        # Check if file has content
        content = migration_file.read_text()
        required_elements = [
            "CREATE TABLE users",
            "CREATE TABLE sources", 
            "CREATE TABLE source_content",
            "CREATE TABLE user_style_posts",
            "CREATE TABLE style_vectors",
            "CREATE TABLE generated_drafts",
            "CREATE TABLE draft_feedback",
            "CREATE TABLE email_delivery_log",
            "CREATE EXTENSION IF NOT EXISTS vector",
            "CREATE OR REPLACE FUNCTION find_similar_style"
        ]
        
        for element in required_elements:
            if element not in content:
                print(f"❌ Migration missing: {element}")
                return False
        
        print("   ✅ Migration files complete")
        return True
    except Exception as e:
        print(f"❌ Migration file test failed: {e}")
        return False


def test_database_initialization():
    """Test database initialization utilities."""
    print("🔍 Testing database initialization...")
    
    try:
        from app.core.db_init import (
            create_tables, init_extensions, create_indexes, 
            create_functions, init_database, check_database_health
        )
        
        # Test that all functions exist
        functions = [create_tables, init_extensions, create_indexes, 
                    create_functions, init_database, check_database_health]
        
        for func in functions:
            assert callable(func), f"{func.__name__} is not callable"
        
        print("   ✅ Database initialization utilities available")
        return True
    except Exception as e:
        print(f"❌ Database initialization test failed: {e}")
        return False


def test_vector_support():
    """Test PostgreSQL vector support."""
    print("🔍 Testing vector support...")
    
    try:
        from pgvector.sqlalchemy import Vector
        from app.models import StyleVector
        
        # Test that StyleVector model has embedding column
        if not hasattr(StyleVector, 'embedding'):
            print("❌ StyleVector missing embedding column")
            return False
        
        print("   ✅ Vector support configured")
        return True
    except Exception as e:
        print(f"❌ Vector support test failed: {e}")
        return False


async def test_model_creation():
    """Test basic model creation (in-memory)."""
    print("🔍 Testing model creation...")
    
    try:
        from app.models import User
        from datetime import time
        
        # Test creating a user model instance
        user = User(
            email="test@example.com",
            password_hash="hashed_password",
            timezone="UTC",
            delivery_time=time(8, 0),
            active=True
        )
        
        assert user.email == "test@example.com"
        assert user.timezone == "UTC"
        assert user.active is True
        
        print("   ✅ Model creation working")
        return True
    except Exception as e:
        print(f"❌ Model creation test failed: {e}")
        return False


def main():
    """Run all Task 14 tests."""
    print("🚀 Testing Task 14: Implement database schema and models")
    print("=" * 80)
    
    tests = [
        test_model_imports,
        test_schema_imports,
        test_model_attributes,
        test_schema_validation,
        test_database_connection,
        test_migration_files,
        test_database_initialization,
        test_vector_support,
    ]
    
    # Add async test
    async_tests = [test_model_creation]
    
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
            result = asyncio.run(test())
            if result:
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()
    
    print("=" * 80)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Task 14 PASSED: Database schema and models implemented!")
        print("\n📋 What's been implemented:")
        print("   ✅ Complete database schema with all tables")
        print("   ✅ PostgreSQL pg_vector extension support")
        print("   ✅ All database models matching frontend interfaces")
        print("   ✅ Pydantic schemas for API request/response validation")
        print("   ✅ Database connection utilities and session management")
        print("   ✅ Vector similarity search functions")
        print("   ✅ Database initialization and health check utilities")
        print("   ✅ Comprehensive SQL migrations")
        return True
    else:
        print("⚠️  Task 14 PARTIAL: Some components need attention")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
