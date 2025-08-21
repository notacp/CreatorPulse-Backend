"""
Database initialization utilities.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.core.database import engine, AsyncSessionLocal
from app.models import *  # Import all models to register them

logger = logging.getLogger(__name__)


async def create_tables():
    """Create all database tables."""
    try:
        # Import all models to ensure they're registered
        from app.models import (
            User, Source, SourceContent, UserStylePost, 
            StyleVector, GeneratedDraft, DraftFeedback, EmailDeliveryLog
        )
        
        async with engine.begin() as conn:
            # Create all tables
            from app.core.database import Base
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        return False


async def init_extensions():
    """Initialize required PostgreSQL extensions."""
    try:
        async with AsyncSessionLocal() as session:
            # Enable UUID extension
            await session.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            
            # Enable pg_vector extension
            await session.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
            
            await session.commit()
            
        logger.info("Database extensions initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize extensions: {e}")
        return False


async def create_indexes():
    """Create database indexes for performance."""
    try:
        async with AsyncSessionLocal() as session:
            # Users indexes
            await session.execute(text('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
            '''))
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_users_active ON users(active) WHERE active = true;
            '''))
            
            # Sources indexes
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_sources_user_id_active ON sources(user_id, active);
            '''))
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_sources_last_checked ON sources(last_checked) WHERE active = true;
            '''))
            
            # Source content indexes
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_source_content_source_id ON source_content(source_id);
            '''))
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_source_content_processed ON source_content(processed) WHERE processed = false;
            '''))
            
            # Style vectors indexes (for similarity search)
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_style_vectors_user_id ON style_vectors(user_id);
            '''))
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_style_vectors_embedding ON style_vectors USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
            '''))
            
            # Generated drafts indexes
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_generated_drafts_user_id ON generated_drafts(user_id);
            '''))
            await session.execute(text('''
                CREATE INDEX IF NOT EXISTS idx_generated_drafts_status ON generated_drafts(status);
            '''))
            
            await session.commit()
            
        logger.info("Database indexes created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")
        return False


async def create_functions():
    """Create PostgreSQL functions for vector similarity search."""
    try:
        async with AsyncSessionLocal() as session:
            # Function to find similar style vectors
            await session.execute(text('''
                CREATE OR REPLACE FUNCTION find_similar_style(
                    query_embedding VECTOR(768),
                    target_user_id UUID,
                    limit_count INTEGER DEFAULT 5
                )
                RETURNS TABLE(content TEXT, similarity FLOAT)
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        sv.content,
                        1 - (sv.embedding <=> query_embedding) AS similarity
                    FROM style_vectors sv
                    WHERE sv.user_id = target_user_id
                      AND sv.embedding IS NOT NULL
                    ORDER BY sv.embedding <=> query_embedding
                    LIMIT limit_count;
                END;
                $$ LANGUAGE plpgsql;
            '''))
            
            # Function to get user style summary
            await session.execute(text('''
                CREATE OR REPLACE FUNCTION get_user_style_summary(target_user_id UUID)
                RETURNS TABLE(
                    total_posts INTEGER,
                    processed_posts INTEGER,
                    total_vectors INTEGER,
                    avg_word_count FLOAT,
                    last_training_at TIMESTAMP WITH TIME ZONE
                )
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        COUNT(usp.id)::INTEGER AS total_posts,
                        COUNT(CASE WHEN usp.processed THEN 1 END)::INTEGER AS processed_posts,
                        COUNT(sv.id)::INTEGER AS total_vectors,
                        AVG(usp.word_count) AS avg_word_count,
                        MAX(usp.processed_at) AS last_training_at
                    FROM user_style_posts usp
                    LEFT JOIN style_vectors sv ON sv.style_post_id = usp.id
                    WHERE usp.user_id = target_user_id;
                END;
                $$ LANGUAGE plpgsql;
            '''))
            
            await session.commit()
            
        logger.info("Database functions created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create functions: {e}")
        return False


async def init_database():
    """Initialize the complete database schema."""
    logger.info("Starting database initialization...")
    
    # Initialize extensions first
    if not await init_extensions():
        return False
    
    # Create tables
    if not await create_tables():
        return False
    
    # Create indexes
    if not await create_indexes():
        return False
    
    # Create functions
    if not await create_functions():
        return False
    
    logger.info("Database initialization completed successfully")
    return True


async def check_database_health():
    """Check database connectivity and basic functionality."""
    try:
        async with AsyncSessionLocal() as session:
            # Test basic query
            result = await session.execute(text("SELECT 1"))
            if not result.scalar():
                return False
            
            # Check if tables exist
            result = await session.execute(text('''
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name IN 
                ('users', 'sources', 'source_content', 'user_style_posts', 
                 'style_vectors', 'generated_drafts', 'draft_feedback', 'email_delivery_log')
            '''))
            table_count = result.scalar()
            
            if table_count < 8:  # Should have all 8 tables
                logger.warning(f"Expected 8 tables, found {table_count}")
                return False
            
            # Check if pg_vector extension is installed
            result = await session.execute(text('''
                SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')
            '''))
            has_vector = result.scalar()
            
            if not has_vector:
                logger.warning("pg_vector extension not installed")
                return False
            
        logger.info("Database health check passed")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


if __name__ == "__main__":
    # Allow running this script directly for development
    async def main():
        success = await init_database()
        if success:
            print("✅ Database initialized successfully")
        else:
            print("❌ Database initialization failed")
            
        health = await check_database_health()
        if health:
            print("✅ Database health check passed")
        else:
            print("❌ Database health check failed")
    
    asyncio.run(main())
