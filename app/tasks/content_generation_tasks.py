"""
Celery tasks for content generation and processing.

This module contains background tasks for:
- Fetching content from sources
- Generating drafts
- Processing content pipelines
- Scheduling daily generation
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_, desc

from app.core.config import settings
from app.services.content_fetcher import content_fetcher
from app.services.draft_generator import draft_generator
from app.models.user import User
from app.models.source import Source
from app.models.source_content import SourceContent
from app.models.draft import GeneratedDraft
from app.core.logging import get_logger

logger = get_logger(__name__)


@shared_task(bind=True, name='app.tasks.content_generation_tasks.fetch_user_content')
def fetch_user_content(self, user_id: str, max_items_per_source: int = 20) -> Dict[str, Any]:
    """
    Fetch content from all sources for a specific user.
    
    Args:
        user_id: User ID to fetch content for
        max_items_per_source: Maximum items to fetch per source
        
    Returns:
        Dictionary with fetching results
    """
    try:
        logger.info(f"Starting content fetch for user {user_id}")
        
        # Create async database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def fetch_content():
            async with async_session() as session:
                # Fetch content from all user sources
                content_items = await content_fetcher.fetch_all_user_content(
                    session=session,
                    user_id=user_id,
                    max_items_per_source=max_items_per_source,
                    since_hours=24
                )
                
                if not content_items:
                    return {
                        "success": True,
                        "message": "No new content found",
                        "content_count": 0,
                        "saved_count": 0
                    }
                
                # Deduplicate content
                unique_content = await content_fetcher.deduplicate_content(
                    session=session,
                    content_items=content_items,
                    user_id=user_id
                )
                
                # Save new content to database
                saved_count = 0
                for item in unique_content:
                    try:
                        source_content = SourceContent(
                            user_id=user_id,
                            source_id=item.get('source_id'),
                            title=item['title'],
                            content=item['content'],
                            url=item['url'],
                            author=item.get('author'),
                            published_at=item['published_at'],
                            source_type=item['source_type'],
                            source_name=item['source_name'],
                            content_hash=item['content_hash'],
                            metadata=item.get('metadata', {})
                        )
                        
                        session.add(source_content)
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error saving content item: {e}")
                        continue
                
                await session.commit()
                
                return {
                    "success": True,
                    "message": f"Successfully fetched and saved content",
                    "content_count": len(content_items),
                    "unique_count": len(unique_content),
                    "saved_count": saved_count
                }
        
        # Run the async function
        result = asyncio.run(fetch_content())
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=result
        )
        
        logger.info(f"Content fetch completed for user {user_id}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching content for user {user_id}: {e}")
        
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
        # Engine cleanup is handled automatically when the process ends
        pass


@shared_task(bind=True, name='app.tasks.content_generation_tasks.generate_user_drafts')
def generate_user_drafts(self, user_id: str, max_drafts: int = 5) -> Dict[str, Any]:
    """
    Generate LinkedIn drafts for a specific user.
    
    Args:
        user_id: User ID to generate drafts for
        max_drafts: Maximum number of drafts to generate
        
    Returns:
        Dictionary with generation results
    """
    try:
        logger.info(f"Starting draft generation for user {user_id}")
        
        # Create async database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def generate_drafts():
            async with async_session() as session:
                # Generate multiple drafts
                drafts = await draft_generator.generate_multiple_drafts(
                    session=session,
                    user_id=user_id,
                    max_drafts=max_drafts,
                    content_age_hours=48  # Use content from last 48 hours
                )
                
                if not drafts:
                    return {
                        "success": True,
                        "message": "No suitable content found for draft generation",
                        "drafts_generated": 0,
                        "drafts_saved": 0
                    }
                
                # Save drafts to database
                saved_drafts = await draft_generator.save_generated_drafts(
                    session=session,
                    user_id=user_id,
                    drafts=drafts
                )
                
                return {
                    "success": True,
                    "message": f"Successfully generated and saved drafts",
                    "drafts_generated": len(drafts),
                    "drafts_saved": len(saved_drafts),
                    "draft_ids": [str(draft.id) for draft in saved_drafts]
                }
        
        # Run the async function
        result = asyncio.run(generate_drafts())
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=result
        )
        
        logger.info(f"Draft generation completed for user {user_id}: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating drafts for user {user_id}: {e}")
        
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
        # Engine cleanup is handled automatically when the process ends
        pass


@shared_task(bind=True, name='app.tasks.content_generation_tasks.daily_content_pipeline')
def daily_content_pipeline(self, user_id: str) -> Dict[str, Any]:
    """
    Run the complete daily content pipeline for a user.
    
    This task:
    1. Fetches new content from sources
    2. Generates drafts based on the content
    3. Returns summary of operations
    
    Args:
        user_id: User ID to run pipeline for
        
    Returns:
        Dictionary with pipeline results
    """
    try:
        logger.info(f"Starting daily content pipeline for user {user_id}")
        
        # Step 1: Fetch content
        fetch_result = fetch_user_content.apply(args=[user_id, 15]).get()
        
        if not fetch_result["success"]:
            return {
                "success": False,
                "error": "Content fetching failed",
                "fetch_result": fetch_result
            }
        
        # Step 2: Generate drafts (only if we have new content or existing content)
        draft_result = generate_user_drafts.apply(args=[user_id, 3]).get()
        
        pipeline_result = {
            "success": True,
            "message": "Daily content pipeline completed",
            "user_id": user_id,
            "execution_time": datetime.utcnow().isoformat(),
            "fetch_result": fetch_result,
            "draft_result": draft_result,
            "summary": {
                "content_fetched": fetch_result.get("content_count", 0),
                "content_saved": fetch_result.get("saved_count", 0),
                "drafts_generated": draft_result.get("drafts_generated", 0),
                "drafts_saved": draft_result.get("drafts_saved", 0)
            }
        }
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=pipeline_result
        )
        
        logger.info(f"Daily pipeline completed for user {user_id}: {pipeline_result['summary']}")
        return pipeline_result
        
    except Exception as e:
        logger.error(f"Error in daily pipeline for user {user_id}: {e}")
        
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


@shared_task(bind=True, name='app.tasks.content_generation_tasks.run_daily_pipelines')
def run_daily_pipelines(self) -> Dict[str, Any]:
    """
    Run daily content pipelines for all active users.
    
    This is the main scheduled task that runs daily to:
    1. Find all active users
    2. Run content pipeline for each user
    3. Collect and return summary statistics
    
    Returns:
        Dictionary with overall execution results
    """
    try:
        logger.info("Starting daily content pipelines for all users")
        
        # Create async database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def run_all_pipelines():
            async with async_session() as session:
                # Get all active users
                result = await session.execute(
                    select(User)
                    .where(User.active == True)
                )
                active_users = result.scalars().all()
                
                if not active_users:
                    return {
                        "success": True,
                        "message": "No active users found",
                        "users_processed": 0,
                        "successful_pipelines": 0,
                        "failed_pipelines": 0
                    }
                
                logger.info(f"Found {len(active_users)} active users for daily pipeline")
                
                # Run pipeline for each user
                successful_pipelines = 0
                failed_pipelines = 0
                user_results = []
                
                for user in active_users:
                    try:
                        # Run pipeline for this user
                        pipeline_result = daily_content_pipeline.apply(
                            args=[str(user.id)]
                        ).get(timeout=300)  # 5 minute timeout per user
                        
                        if pipeline_result.get("success", False):
                            successful_pipelines += 1
                        else:
                            failed_pipelines += 1
                        
                        user_results.append({
                            "user_id": str(user.id),
                            "user_email": user.email,
                            "success": pipeline_result.get("success", False),
                            "summary": pipeline_result.get("summary", {})
                        })
                        
                    except Exception as e:
                        failed_pipelines += 1
                        logger.error(f"Pipeline failed for user {user.id}: {e}")
                        
                        user_results.append({
                            "user_id": str(user.id),
                            "user_email": user.email,
                            "success": False,
                            "error": str(e)
                        })
                
                return {
                    "success": True,
                    "message": "Daily pipelines execution completed",
                    "execution_time": datetime.utcnow().isoformat(),
                    "users_processed": len(active_users),
                    "successful_pipelines": successful_pipelines,
                    "failed_pipelines": failed_pipelines,
                    "user_results": user_results,
                    "summary_stats": {
                        "total_content_fetched": sum(
                            r.get("summary", {}).get("content_fetched", 0) 
                            for r in user_results
                        ),
                        "total_drafts_generated": sum(
                            r.get("summary", {}).get("drafts_generated", 0) 
                            for r in user_results
                        )
                    }
                }
        
        # Run the async function
        result = asyncio.run(run_all_pipelines())
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=result
        )
        
        logger.info(f"Daily pipelines completed: {result['users_processed']} users, {result['successful_pipelines']} successful")
        return result
        
    except Exception as e:
        logger.error(f"Error running daily pipelines: {e}")
        
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
        # Engine cleanup is handled automatically when the process ends
        pass


@shared_task(bind=True, name='app.tasks.content_generation_tasks.cleanup_old_content')
def cleanup_old_content(self, days_old: int = 30) -> Dict[str, Any]:
    """
    Clean up old content and drafts to keep the database manageable.
    
    Args:
        days_old: Remove content older than this many days
        
    Returns:
        Dictionary with cleanup results
    """
    try:
        logger.info(f"Starting cleanup of content older than {days_old} days")
        
        # Create async database session
        engine = create_async_engine(settings.database_url)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async def cleanup_content():
            async with async_session() as session:
                from sqlalchemy import delete
                
                # Calculate cutoff date
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                # Clean up old source content
                content_result = await session.execute(
                    delete(SourceContent).where(
                        SourceContent.fetched_at < cutoff_date
                    )
                )
                content_deleted = content_result.rowcount
                
                # Clean up old drafts (keep sent ones longer)
                draft_result = await session.execute(
                    delete(GeneratedDraft).where(
                        and_(
                            GeneratedDraft.created_at < cutoff_date,
                            GeneratedDraft.email_sent_at.is_(None)  # Only delete unsent drafts
                        )
                    )
                )
                drafts_deleted = draft_result.rowcount
                
                await session.commit()
                
                return {
                    "success": True,
                    "cutoff_date": cutoff_date.isoformat(),
                    "content_deleted": content_deleted,
                    "drafts_deleted": drafts_deleted,
                    "message": f"Cleaned up {content_deleted} content items and {drafts_deleted} drafts"
                }
        
        # Run the async function
        result = asyncio.run(cleanup_content())
        
        # Update task state
        self.update_state(
            state='SUCCESS',
            meta=result
        )
        
        logger.info(f"Cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error cleaning up old content: {e}")
        
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
        # Engine cleanup is handled automatically when the process ends
        pass
