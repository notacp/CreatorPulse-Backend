"""
Style training API endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.schemas.style import (
    StylePost,
    StyleTrainingRequest,
    AddStylePostRequest,
    StyleTrainingStatus,
    StyleTrainingJobResponse
)
from app.services.style_training import style_training_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/posts", response_model=List[StylePost])
async def add_style_posts(
    request: StyleTrainingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Add multiple style posts for training.
    
    This endpoint accepts a list of post content strings and adds them to the user's
    style training dataset. Posts are validated and stored in the database.
    
    The actual processing (embedding generation) happens asynchronously in the background.
    """
    try:
        # Add style posts
        style_posts = await style_training_service.add_style_posts(
            session=session,
            user_id=str(current_user.id),
            posts=request.posts
        )
        
        # Start background processing
        background_tasks.add_task(
            style_training_service.process_user_style_posts,
            session=session,
            user_id=str(current_user.id)
        )
        
        logger.info(f"User {current_user.id} added {len(style_posts)} style posts")
        
        # Convert to response schema
        response_posts = []
        for post in style_posts:
            response_posts.append(StylePost(
                id=str(post.id),
                user_id=str(post.user_id),
                content=post.content,
                processed=post.processed,
                word_count=post.word_count,
                created_at=post.created_at,
                processed_at=post.processed_at
            ))
        
        return response_posts
        
    except Exception as e:
        logger.error(f"Error adding style posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to add style posts")


@router.post("/posts/single", response_model=StylePost)
async def add_single_style_post(
    request: AddStylePostRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Add a single style post for training.
    
    This endpoint accepts a single post content string and adds it to the user's
    style training dataset. The post is validated and stored in the database.
    
    The actual processing (embedding generation) happens asynchronously in the background.
    """
    try:
        # Add single style post
        style_posts = await style_training_service.add_style_posts(
            session=session,
            user_id=str(current_user.id),
            posts=[request.content]
        )
        
        if not style_posts:
            raise HTTPException(status_code=400, detail="Failed to add style post")
        
        style_post = style_posts[0]
        
        # Start background processing
        background_tasks.add_task(
            style_training_service.process_style_post,
            session=session,
            style_post=style_post
        )
        
        logger.info(f"User {current_user.id} added single style post {style_post.id}")
        
        # Convert to response schema
        return StylePost(
            id=str(style_post.id),
            user_id=str(style_post.user_id),
            content=style_post.content,
            processed=style_post.processed,
            word_count=style_post.word_count,
            created_at=style_post.created_at,
            processed_at=style_post.processed_at
        )
        
    except Exception as e:
        logger.error(f"Error adding single style post: {e}")
        raise HTTPException(status_code=500, detail="Failed to add style post")


@router.get("/posts", response_model=List[StylePost])
async def get_style_posts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get all style posts for the current user.
    
    Returns a list of all style posts (both processed and unprocessed) for the
    authenticated user, ordered by creation date (newest first).
    """
    try:
        from app.models.style import UserStylePost
        from sqlalchemy import select
        
        # Get user's style posts
        result = await session.execute(
            select(UserStylePost)
            .where(UserStylePost.user_id == current_user.id)
            .order_by(UserStylePost.created_at.desc())
        )
        style_posts = result.scalars().all()
        
        # Convert to response schema
        response_posts = []
        for post in style_posts:
            response_posts.append(StylePost(
                id=str(post.id),
                user_id=str(post.user_id),
                content=post.content,
                processed=post.processed,
                word_count=post.word_count,
                created_at=post.created_at,
                processed_at=post.processed_at
            ))
        
        return response_posts
        
    except Exception as e:
        logger.error(f"Error getting style posts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get style posts")


@router.get("/status", response_model=StyleTrainingStatus)
async def get_style_training_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get the current style training status for the user.
    
    Returns information about the user's style training progress, including:
    - Current status (pending, processing, completed, failed)
    - Progress percentage
    - Total and processed post counts
    - Status message
    """
    try:
        status = await style_training_service.get_style_training_status(
            session=session,
            user_id=str(current_user.id)
        )
        
        return StyleTrainingStatus(
            status=status["status"],
            progress=status["progress"],
            total_posts=status["total_posts"],
            processed_posts=status["processed_posts"],
            message=status["message"]
        )
        
    except Exception as e:
        logger.error(f"Error getting style training status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get training status")


@router.post("/process", response_model=StyleTrainingJobResponse)
async def start_style_processing(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Manually trigger style processing for all unprocessed posts.
    
    This endpoint allows users to manually start or restart the processing of
    their unprocessed style posts. The processing happens asynchronously in
    the background.
    
    Returns a job ID that can be used to track the processing status.
    """
    try:
        import uuid
        
        job_id = str(uuid.uuid4())
        
        # Start background processing
        background_tasks.add_task(
            style_training_service.process_user_style_posts,
            session=session,
            user_id=str(current_user.id)
        )
        
        logger.info(f"Started style processing job {job_id} for user {current_user.id}")
        
        return StyleTrainingJobResponse(
            message="Style processing started successfully",
            job_id=job_id
        )
        
    except Exception as e:
        logger.error(f"Error starting style processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to start style processing")


@router.get("/summary")
async def get_style_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get a comprehensive summary of the user's style training data.
    
    Returns detailed statistics about the user's style training, including:
    - Total and processed post counts
    - Word count statistics
    - Style vector information
    - Completion percentage
    """
    try:
        summary = await style_training_service.get_user_style_summary(
            session=session,
            user_id=str(current_user.id)
        )
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting style summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get style summary")


@router.delete("/posts/{post_id}")
async def delete_style_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Delete a specific style post.
    
    Removes a style post and its associated style vector from the user's
    training dataset. This operation cannot be undone.
    """
    try:
        from app.models.style import UserStylePost, StyleVector
        from sqlalchemy import select, delete
        
        # Verify the post belongs to the current user
        result = await session.execute(
            select(UserStylePost).where(
                UserStylePost.id == post_id,
                UserStylePost.user_id == current_user.id
            )
        )
        style_post = result.scalar_one_or_none()
        
        if not style_post:
            raise HTTPException(status_code=404, detail="Style post not found")
        
        # Delete associated style vector first (due to foreign key constraint)
        await session.execute(
            delete(StyleVector).where(StyleVector.style_post_id == post_id)
        )
        
        # Delete the style post
        await session.execute(
            delete(UserStylePost).where(UserStylePost.id == post_id)
        )
        
        await session.commit()
        
        logger.info(f"User {current_user.id} deleted style post {post_id}")
        
        return {"message": "Style post deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting style post: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete style post")
