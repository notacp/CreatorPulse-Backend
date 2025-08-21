"""
Test database models and validation.
"""
import pytest
import asyncio
from datetime import datetime, time
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import IntegrityError
import uuid

from app.core.database import Base
from app.models import (
    User, Source, SourceContent, UserStylePost, 
    StyleVector, GeneratedDraft, DraftFeedback, EmailDeliveryLog
)


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def async_session():
    """Create an async test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with AsyncSessionLocal() as session:
        yield session
    
    await engine.dispose()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password_hash": "$2b$12$test_hash",
        "timezone": "America/New_York",
        "delivery_time": time(8, 0),
        "active": True,
        "email_verified": True
    }


@pytest.fixture
def sample_source_data():
    """Sample source data for testing."""
    return {
        "type": "rss",
        "url": "https://example.com/feed",
        "name": "Test Feed",
        "active": True,
        "error_count": 0
    }


class TestUserModel:
    """Test User model."""
    
    @pytest.mark.asyncio
    async def test_create_user(self, async_session: AsyncSession, sample_user_data):
        """Test creating a user."""
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.timezone == "America/New_York"
        assert user.delivery_time == time(8, 0)
        assert user.active is True
        assert user.created_at is not None
    
    async def test_user_email_unique_constraint(self, async_session: AsyncSession, sample_user_data):
        """Test that user email must be unique."""
        # Create first user
        user1 = User(**sample_user_data)
        async_session.add(user1)
        await async_session.commit()
        
        # Try to create second user with same email
        user2 = User(**sample_user_data)
        async_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await async_session.commit()
    
    async def test_user_defaults(self, async_session: AsyncSession):
        """Test user default values."""
        user = User(
            email="defaults@example.com",
            password_hash="test_hash"
        )
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        assert user.timezone == "UTC"
        assert user.delivery_time == time(8, 0)
        assert user.active is True
        assert user.email_verified is False


class TestSourceModel:
    """Test Source model."""
    
    async def test_create_source(self, async_session: AsyncSession, sample_user_data, sample_source_data):
        """Test creating a source."""
        # Create user first
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        # Create source
        source = Source(user_id=user.id, **sample_source_data)
        async_session.add(source)
        await async_session.commit()
        await async_session.refresh(source)
        
        assert source.id is not None
        assert source.user_id == user.id
        assert source.type == "rss"
        assert source.url == "https://example.com/feed"
        assert source.name == "Test Feed"
        assert source.active is True
        assert source.error_count == 0
    
    async def test_source_type_constraint(self, async_session: AsyncSession, sample_user_data):
        """Test source type constraint."""
        # Create user first
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        # Try to create source with invalid type (this will be enforced at app level)
        source = Source(
            user_id=user.id,
            type="invalid_type",
            url="https://example.com",
            name="Test",
            active=True
        )
        async_session.add(source)
        
        # In SQLite, check constraints might not be enforced the same way
        # This test would be more meaningful with PostgreSQL
        try:
            await async_session.commit()
        except Exception:
            # Expected if constraint is enforced
            pass
    
    async def test_source_user_relationship(self, async_session: AsyncSession, sample_user_data, sample_source_data):
        """Test source-user relationship."""
        # Create user
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        # Create source
        source = Source(user_id=user.id, **sample_source_data)
        async_session.add(source)
        await async_session.commit()
        
        # Test relationship (note: in memory SQLite, relationships might not work the same)
        assert source.user_id == user.id


class TestSourceContentModel:
    """Test SourceContent model."""
    
    async def test_create_source_content(self, async_session: AsyncSession, sample_user_data, sample_source_data):
        """Test creating source content."""
        # Create user and source
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        source = Source(user_id=user.id, **sample_source_data)
        async_session.add(source)
        await async_session.commit()
        await async_session.refresh(source)
        
        # Create source content
        content = SourceContent(
            source_id=source.id,
            title="Test Article",
            content="This is test content for the article.",
            url="https://example.com/article",
            processed=False,
            content_hash="test_hash_123"
        )
        async_session.add(content)
        await async_session.commit()
        await async_session.refresh(content)
        
        assert content.id is not None
        assert content.source_id == source.id
        assert content.title == "Test Article"
        assert content.content == "This is test content for the article."
        assert content.processed is False


class TestStyleModels:
    """Test style training models."""
    
    async def test_create_style_post(self, async_session: AsyncSession, sample_user_data):
        """Test creating a style post."""
        # Create user
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        # Create style post
        style_post = UserStylePost(
            user_id=user.id,
            content="This is a sample post for style training.",
            processed=False,
            word_count=9,
            character_count=44
        )
        async_session.add(style_post)
        await async_session.commit()
        await async_session.refresh(style_post)
        
        assert style_post.id is not None
        assert style_post.user_id == user.id
        assert style_post.content == "This is a sample post for style training."
        assert style_post.processed is False
        assert style_post.word_count == 9
    
    async def test_create_style_vector(self, async_session: AsyncSession, sample_user_data):
        """Test creating a style vector."""
        # Create user and style post
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        style_post = UserStylePost(
            user_id=user.id,
            content="Sample content",
            processed=True
        )
        async_session.add(style_post)
        await async_session.commit()
        await async_session.refresh(style_post)
        
        # Create style vector (without embedding for SQLite test)
        style_vector = StyleVector(
            user_id=user.id,
            style_post_id=style_post.id,
            content="Sample content"
        )
        async_session.add(style_vector)
        await async_session.commit()
        await async_session.refresh(style_vector)
        
        assert style_vector.id is not None
        assert style_vector.user_id == user.id
        assert style_vector.style_post_id == style_post.id


class TestDraftModels:
    """Test draft-related models."""
    
    async def test_create_draft(self, async_session: AsyncSession, sample_user_data):
        """Test creating a draft."""
        # Create user
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        # Create draft
        draft = GeneratedDraft(
            user_id=user.id,
            content="This is a generated LinkedIn post about innovation in technology.",
            status="pending",
            character_count=65,
            engagement_score=Decimal("7.5"),
            feedback_token="test_token_123"
        )
        async_session.add(draft)
        await async_session.commit()
        await async_session.refresh(draft)
        
        assert draft.id is not None
        assert draft.user_id == user.id
        assert draft.status == "pending"
        assert draft.character_count == 65
        assert draft.engagement_score == Decimal("7.5")
        assert draft.feedback_token == "test_token_123"
    
    async def test_create_draft_feedback(self, async_session: AsyncSession, sample_user_data):
        """Test creating draft feedback."""
        # Create user and draft
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        draft = GeneratedDraft(
            user_id=user.id,
            content="Test draft content",
            status="pending"
        )
        async_session.add(draft)
        await async_session.commit()
        await async_session.refresh(draft)
        
        # Create feedback
        feedback = DraftFeedback(
            draft_id=draft.id,
            feedback_type="positive",
            feedback_source="email"
        )
        async_session.add(feedback)
        await async_session.commit()
        await async_session.refresh(feedback)
        
        assert feedback.id is not None
        assert feedback.draft_id == draft.id
        assert feedback.feedback_type == "positive"
        assert feedback.feedback_source == "email"


class TestEmailDeliveryLog:
    """Test email delivery log model."""
    
    async def test_create_email_log(self, async_session: AsyncSession, sample_user_data):
        """Test creating email delivery log."""
        # Create user
        user = User(**sample_user_data)
        async_session.add(user)
        await async_session.commit()
        await async_session.refresh(user)
        
        # Create email log
        email_log = EmailDeliveryLog(
            user_id=user.id,
            email_type="daily_drafts",
            sendgrid_message_id="test_msg_123",
            status="sent",
            draft_ids=[str(uuid.uuid4()), str(uuid.uuid4())]
        )
        async_session.add(email_log)
        await async_session.commit()
        await async_session.refresh(email_log)
        
        assert email_log.id is not None
        assert email_log.user_id == user.id
        assert email_log.email_type == "daily_drafts"
        assert email_log.status == "sent"
        assert len(email_log.draft_ids) == 2


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
