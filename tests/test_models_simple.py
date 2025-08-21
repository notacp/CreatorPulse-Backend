"""
Simple synchronous tests for database models and schemas.
"""
import pytest
from datetime import datetime, time
from decimal import Decimal
import uuid

from app.models import (
    User, Source, SourceContent, UserStylePost, 
    StyleVector, GeneratedDraft, DraftFeedback, EmailDeliveryLog
)
from app.schemas import (
    UserCreate, SourceCreate, Draft, 
    StylePost, LoginRequest, RegisterRequest
)
from pydantic import ValidationError


class TestModelInstantiation:
    """Test that models can be instantiated correctly."""
    
    def test_user_model_creation(self):
        """Test User model instantiation."""
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
    
    def test_source_model_creation(self):
        """Test Source model instantiation."""
        user_id = uuid.uuid4()
        source = Source(
            user_id=user_id,
            type="rss",
            url="https://example.com/feed",
            name="Test Feed",
            active=True,
            error_count=0
        )
        
        assert source.user_id == user_id
        assert source.type == "rss"
        assert source.url == "https://example.com/feed"
        assert source.active is True
    
    def test_source_content_model_creation(self):
        """Test SourceContent model instantiation."""
        source_id = uuid.uuid4()
        content = SourceContent(
            source_id=source_id,
            title="Test Article",
            content="This is test content",
            url="https://example.com/article",
            processed=False
        )
        
        assert content.source_id == source_id
        assert content.title == "Test Article"
        assert content.processed is False
    
    def test_generated_draft_model_creation(self):
        """Test GeneratedDraft model instantiation."""
        user_id = uuid.uuid4()
        draft = GeneratedDraft(
            user_id=user_id,
            content="This is a generated LinkedIn post",
            status="pending",
            character_count=32,
            engagement_score=Decimal("7.5")
        )
        
        assert draft.user_id == user_id
        assert draft.status == "pending"
        assert draft.character_count == 32
        assert draft.engagement_score == Decimal("7.5")
    
    def test_style_post_model_creation(self):
        """Test UserStylePost model instantiation."""
        user_id = uuid.uuid4()
        style_post = UserStylePost(
            user_id=user_id,
            content="Sample post content for style training",
            processed=False,
            word_count=7,
            character_count=43
        )
        
        assert style_post.user_id == user_id
        assert style_post.processed is False
        assert style_post.word_count == 7


class TestSchemaValidation:
    """Test Pydantic schema validation."""
    
    def test_user_create_schema_valid(self):
        """Test valid UserCreate schema."""
        user_data = UserCreate(
            email="test@example.com",
            password="password123",
            timezone="America/New_York"
        )
        
        assert user_data.email == "test@example.com"
        assert user_data.timezone == "America/New_York"
    
    def test_user_create_schema_invalid_email(self):
        """Test UserCreate schema with invalid email."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid-email",
                password="password123"
            )
    
    def test_user_create_schema_short_password(self):
        """Test UserCreate schema with short password."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="short"  # Less than 8 characters
            )
    
    def test_source_create_schema_valid(self):
        """Test valid SourceCreate schema."""
        source_data = SourceCreate(
            type="rss",
            url="https://example.com/feed",
            name="Test Feed"
        )
        
        assert source_data.type == "rss"
        assert source_data.url == "https://example.com/feed"
        assert source_data.name == "Test Feed"
    
    def test_source_create_schema_invalid_type(self):
        """Test SourceCreate schema with invalid type."""
        with pytest.raises(ValidationError):
            SourceCreate(
                type="invalid_type",
                url="https://example.com",
                name="Test"
            )
    
    def test_login_request_schema_valid(self):
        """Test valid LoginRequest schema."""
        login_data = LoginRequest(
            email="test@example.com",
            password="password123"
        )
        
        assert login_data.email == "test@example.com"
        assert login_data.password == "password123"
    
    def test_register_request_schema_valid(self):
        """Test valid RegisterRequest schema."""
        register_data = RegisterRequest(
            email="test@example.com",
            password="password123",
            timezone="UTC"
        )
        
        assert register_data.email == "test@example.com"
        assert register_data.timezone == "UTC"


class TestModelAttributes:
    """Test that models have all required attributes."""
    
    def test_user_model_attributes(self):
        """Test User model has all required attributes."""
        required_attrs = [
            'id', 'email', 'password_hash', 'timezone', 'delivery_time',
            'active', 'email_verified', 'created_at', 'updated_at'
        ]
        
        for attr in required_attrs:
            assert hasattr(User, attr), f"User model missing {attr}"
    
    def test_source_model_attributes(self):
        """Test Source model has all required attributes."""
        required_attrs = [
            'id', 'user_id', 'type', 'url', 'name', 'active',
            'last_checked', 'error_count', 'last_error', 'created_at', 'updated_at'
        ]
        
        for attr in required_attrs:
            assert hasattr(Source, attr), f"Source model missing {attr}"
    
    def test_generated_draft_model_attributes(self):
        """Test GeneratedDraft model has all required attributes."""
        required_attrs = [
            'id', 'user_id', 'content', 'source_content_id', 'status',
            'feedback_token', 'email_sent_at', 'character_count', 
            'engagement_score', 'created_at', 'updated_at'
        ]
        
        for attr in required_attrs:
            assert hasattr(GeneratedDraft, attr), f"GeneratedDraft model missing {attr}"
    
    def test_source_content_model_attributes(self):
        """Test SourceContent model has all required attributes."""
        required_attrs = [
            'id', 'source_id', 'title', 'content', 'url',
            'published_at', 'processed', 'content_hash', 'created_at'
        ]
        
        for attr in required_attrs:
            assert hasattr(SourceContent, attr), f"SourceContent model missing {attr}"


class TestSchemaFromAttributes:
    """Test schema from_attributes functionality."""
    
    def test_user_schema_from_model(self):
        """Test creating User schema from model."""
        # Create a mock user model instance
        user_model = User(
            email="test@example.com",
            password_hash="hashed",
            timezone="UTC",
            active=True
        )
        user_model.id = uuid.uuid4()
        user_model.created_at = datetime.utcnow()
        
        # This tests that the schema can work with model attributes
        from app.schemas import User as UserSchema
        
        # Test that the schema class exists and has from_attributes config
        assert hasattr(UserSchema.model_config, 'from_attributes') or hasattr(UserSchema.Config, 'from_attributes')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
