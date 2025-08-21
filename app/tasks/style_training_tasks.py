"""
Celery tasks for style training background processing.
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.style_training import style_training_service
from app.core.logging import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, name='app.tasks.style_training_tasks.process_style_post')
def process_style_post(self, post_id: str, user_id: str) -> Dict[str, Any]:
    """
    Process a single style post and generate embeddings.
    
    This is a Celery task that runs asynchronously to process style posts
    and generate vector embeddings for similarity search.
    
    Args:
        post_id: ID of the style post to process
        user_id: ID of the user who owns the post
        
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Starting to process style post {post_id} for user {user_id}")
        
        # Create async database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def process_post():
            async with async_session() as session:
                # Get the style post
                from app.models.style import UserStylePost
                from sqlalchemy import select
                
                result = await session.execute(
                    select(UserStylePost).where(UserStylePost.id == post_id)
                )
                style_post = result.scalar_one_or_none()
                
                if not style_post:
                    logger.error(f"Style post {post_id} not found")
                    return {
                        "success": False,
                        "error": "Style post not found",
                        "post_id": post_id
                    }
                
                # Process the post
                style_vector = await style_training_service.process_style_post(
                    session=session,
                    style_post=style_post
                )
                
                if style_vector:
                    logger.info(f"Successfully processed style post {post_id}")
                    return {
                        "success": True,
                        "post_id": post_id,
                        "vector_id": str(style_vector.id),
                        "message": "Style post processed successfully"
                    }
                else:
                    logger.error(f"Failed to process style post {post_id}")
                    return {
                        "success": False,
                        "error": "Failed to process style post",
                        "post_id": post_id
                    }
        
        # Run the async function
        result = asyncio.run(process_post())
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=result
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing style post {post_id}: {e}")
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={
                "success": False,
                "error": str(e),
                "post_id": post_id
            }
        )
        
        # Re-raise to mark task as failed
        raise
    
    finally:
        # Clean up engine
        if 'engine' in locals():
            engine.dispose()


@shared_task(bind=True, name='app.tasks.style_training_tasks.process_user_style_posts')
def process_user_style_posts(self, user_id: str) -> Dict[str, Any]:
    """
    Process all unprocessed style posts for a user.
    
    This is a Celery task that runs asynchronously to process all pending
    style posts for a specific user and generate vector embeddings.
    
    Args:
        user_id: ID of the user whose posts should be processed
        
    Returns:
        Dictionary with processing results summary
    """
    try:
        logger.info(f"Starting to process style posts for user {user_id}")
        
        # Create async database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def process_posts():
            async with async_session() as session:
                # Process all unprocessed posts for the user
                result = await style_training_service.process_user_style_posts(
                    session=session,
                    user_id=user_id
                )
                
                return result
        
        # Run the async function
        result = asyncio.run(process_posts())
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=result
        )
        
        logger.info(f"Completed processing style posts for user {user_id}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error processing style posts for user {user_id}: {e}")
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
        )
        
        # Re-raise to mark task as failed
        raise
    
    finally:
        # Clean up engine
        if 'engine' in locals():
            engine.dispose()


@shared_task(bind=True, name='app.tasks.style_training_tasks.process_pending_style_posts')
def process_pending_style_posts(self) -> Dict[str, Any]:
    """
    Process all pending style posts across all users.
    
    This is a periodic task that runs every 5 minutes to process any
    unprocessed style posts in the system.
    
    Returns:
        Dictionary with processing results summary
    """
    try:
        logger.info("Starting periodic processing of pending style posts")
        
        # Create async database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def process_all_pending():
            async with async_session() as session:
                # Get all users with unprocessed posts
                from app.models.style import UserStylePost
                from sqlalchemy import select, distinct
                
                result = await session.execute(
                    select(distinct(UserStylePost.user_id))
                    .where(UserStylePost.processed == False)
                )
                user_ids = [str(row[0]) for row in result.fetchall()]
                
                if not user_ids:
                    logger.info("No pending style posts found")
                    return {
                        "total_users": 0,
                        "processed_users": 0,
                        "message": "No pending style posts found"
                    }
                
                logger.info(f"Found {len(user_ids)} users with pending style posts")
                
                # Process posts for each user
                processed_users = 0
                total_posts_processed = 0
                
                for user_id in user_ids:
                    try:
                        result = await style_training_service.process_user_style_posts(
                            session=session,
                            user_id=user_id
                        )
                        
                        if result["status"] in ["completed", "partial"]:
                            processed_users += 1
                            total_posts_processed += result["processed_posts"]
                        
                        logger.info(f"Processed posts for user {user_id}: {result}")
                        
                    except Exception as e:
                        logger.error(f"Error processing posts for user {user_id}: {e}")
                        continue
                
                return {
                    "total_users": len(user_ids),
                    "processed_users": processed_users,
                    "total_posts_processed": total_posts_processed,
                    "message": f"Processed posts for {processed_users}/{len(user_ids)} users"
                }
        
        # Run the async function
        result = asyncio.run(process_all_pending())
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=result
        )
        
        logger.info(f"Completed periodic processing: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in periodic style post processing: {e}")
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={
                "success": False,
                "error": str(e)
            }
        )
        
        # Re-raise to mark task as failed
        raise
    
    finally:
        # Clean up engine
        if 'engine' in locals():
            engine.dispose()


@shared_task(bind=True, name='app.tasks.style_training_tasks.cleanup_old_style_vectors')
def cleanup_old_style_vectors(self, days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old style vectors that are no longer needed.
    
    This task removes style vectors for posts that have been deleted or
    are older than a specified number of days.
    
    Args:
        days_old: Remove vectors older than this many days (default: 30)
        
    Returns:
        Dictionary with cleanup results
    """
    try:
        logger.info(f"Starting cleanup of style vectors older than {days_old} days")
        
        # Create async database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def cleanup_vectors():
            async with async_session() as session:
                from app.models.style import StyleVector
                from sqlalchemy import delete, text
                from datetime import datetime, timedelta
                
                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                # Delete old vectors
                result = await session.execute(
                    delete(StyleVector).where(
                        StyleVector.created_at < cutoff_date
                    )
                )
                
                deleted_count = result.rowcount
                await session.commit()
                
                logger.info(f"Deleted {deleted_count} old style vectors")
                
                return {
                    "success": True,
                    "deleted_count": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                    "message": f"Deleted {deleted_count} old style vectors"
                }
        
        # Run the async function
        result = asyncio.run(cleanup_vectors())
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=result
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning up old style vectors: {e}")
        
        # Update task state
        self.update_state(
            state='FAILURE',
            meta={
                "success": False,
                "error": str(e)
            }
        )
        
        # Re-raise to mark task as failed
        raise
    
    finally:
        # Clean up engine
        if 'engine' in locals():
            engine.dispose()
