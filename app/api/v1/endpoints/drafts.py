"""
Draft generation and management API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from app.core.database import get_db
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.draft import GeneratedDraft
from app.models.source_content import SourceContent
from app.schemas.draft import (
    GeneratedDraftResponse,
    DraftGenerationRequest,
    DraftGenerationResponse,
    DraftStatusResponse
)
from app.services.content_fetcher import content_fetcher
from app.services.draft_generator import draft_generator
from app.tasks.content_generation_tasks import (
    fetch_user_content,
    generate_user_drafts,
    daily_content_pipeline
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=List[GeneratedDraftResponse])
async def get_user_drafts(
    status: Optional[str] = Query(None, description="Filter by draft status"),
    limit: int = Query(20, ge=1, le=100, description="Number of drafts to return"),
    offset: int = Query(0, ge=0, description="Number of drafts to skip"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get user's generated drafts with optional filtering.
    
    Returns a list of generated drafts for the authenticated user,
    ordered by creation date (newest first).
    """
    try:
        # Build query
        query = select(GeneratedDraft).where(GeneratedDraft.user_id == current_user.id)
        
        # Add status filter if provided
        if status:
            query = query.where(GeneratedDraft.status == status)
        
        # Add ordering, limit, and offset
        query = query.order_by(desc(GeneratedDraft.created_at)).limit(limit).offset(offset)
        
        # Execute query
        result = await session.execute(query)
        drafts = result.scalars().all()
        
        # Convert to response format
        response_drafts = []
        for draft in drafts:
            response_drafts.append(GeneratedDraftResponse(
                id=str(draft.id),
                user_id=str(draft.user_id),
                content=draft.content,
                source_content_id=str(draft.source_content_id) if draft.source_content_id else None,
                status=draft.status,
                feedback_token=draft.feedback_token,
                email_sent_at=draft.email_sent_at,
                character_count=draft.character_count,
                engagement_score=draft.engagement_score,
                generation_metadata=draft.generation_metadata or {},
                created_at=draft.created_at,
                updated_at=draft.updated_at
            ))
        
        return response_drafts
        
    except Exception as e:
        logger.error(f"Error getting user drafts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get drafts")


@router.get("/{draft_id}", response_model=GeneratedDraftResponse)
async def get_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get a specific draft by ID.
    
    Returns the draft if it belongs to the authenticated user.
    """
    try:
        # Get draft
        result = await session.execute(
            select(GeneratedDraft).where(
                and_(
                    GeneratedDraft.id == draft_id,
                    GeneratedDraft.user_id == current_user.id
                )
            )
        )
        draft = result.scalar_one_or_none()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        return GeneratedDraftResponse(
            id=str(draft.id),
            user_id=str(draft.user_id),
            content=draft.content,
            source_content_id=str(draft.source_content_id) if draft.source_content_id else None,
            status=draft.status,
            feedback_token=draft.feedback_token,
            email_sent_at=draft.email_sent_at,
            character_count=draft.character_count,
            engagement_score=draft.engagement_score,
            generation_metadata=draft.generation_metadata or {},
            created_at=draft.created_at,
            updated_at=draft.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting draft {draft_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get draft")


@router.post("/generate", response_model=DraftGenerationResponse)
async def generate_drafts(
    request: DraftGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Generate new drafts for the user.
    
    This endpoint can either generate drafts immediately (for small numbers)
    or queue them as background tasks (for larger batches).
    """
    try:
        max_drafts = min(request.max_drafts or 5, 20)  # Limit to 20 max
        
        if max_drafts <= 3:
            # Generate immediately for small batches
            drafts = await draft_generator.generate_multiple_drafts(
                session=session,
                user_id=str(current_user.id),
                max_drafts=max_drafts,
                content_age_hours=request.content_age_hours or 48
            )
            
            if not drafts:
                return DraftGenerationResponse(
                    message="No suitable content found for draft generation",
                    drafts_requested=max_drafts,
                    drafts_generated=0,
                    processing_async=False
                )
            
            # Save drafts
            saved_drafts = await draft_generator.save_generated_drafts(
                session=session,
                user_id=str(current_user.id),
                drafts=drafts
            )
            
            return DraftGenerationResponse(
                message=f"Successfully generated {len(saved_drafts)} drafts",
                drafts_requested=max_drafts,
                drafts_generated=len(saved_drafts),
                processing_async=False,
                draft_ids=[str(draft.id) for draft in saved_drafts]
            )
        
        else:
            # Queue as background task for larger batches
            task = generate_user_drafts.delay(str(current_user.id), max_drafts)
            
            return DraftGenerationResponse(
                message=f"Draft generation queued for {max_drafts} drafts",
                drafts_requested=max_drafts,
                drafts_generated=0,
                processing_async=True,
                task_id=task.id
            )
        
    except Exception as e:
        logger.error(f"Error generating drafts: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate drafts")


@router.post("/fetch-content")
async def fetch_content(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Manually trigger content fetching from user's sources.
    
    This endpoint allows users to manually refresh their content
    without waiting for the scheduled task.
    """
    try:
        # Queue content fetching as background task
        task = fetch_user_content.delay(str(current_user.id), 25)
        
        return {
            "message": "Content fetching initiated",
            "task_id": task.id,
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Error triggering content fetch: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger content fetch")


@router.post("/run-pipeline")
async def run_content_pipeline(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Run the complete content pipeline for the user.
    
    This endpoint runs the full pipeline:
    1. Fetch new content from sources
    2. Generate drafts based on content
    """
    try:
        # Queue pipeline as background task
        task = daily_content_pipeline.delay(str(current_user.id))
        
        return {
            "message": "Content pipeline initiated",
            "task_id": task.id,
            "user_id": str(current_user.id)
        }
        
    except Exception as e:
        logger.error(f"Error triggering content pipeline: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger content pipeline")


@router.get("/status", response_model=DraftStatusResponse)
async def get_draft_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Get draft generation status and statistics for the user.
    
    Returns information about the user's drafts, including counts by status,
    recent activity, and content availability.
    """
    try:
        # Count drafts by status
        status_counts = {}
        status_result = await session.execute(
            select(GeneratedDraft.status, func.count(GeneratedDraft.id))
            .where(GeneratedDraft.user_id == current_user.id)
            .group_by(GeneratedDraft.status)
        )
        
        for status, count in status_result:
            status_counts[status] = count
        
        # Get recent content count
        content_result = await session.execute(
            select(func.count(SourceContent.id))
            .where(
                and_(
                    SourceContent.user_id == current_user.id,
                    SourceContent.fetched_at >= func.now() - func.interval('24 hours')
                )
            )
        )
        recent_content_count = content_result.scalar() or 0
        
        # Get latest draft
        latest_draft_result = await session.execute(
            select(GeneratedDraft.created_at)
            .where(GeneratedDraft.user_id == current_user.id)
            .order_by(desc(GeneratedDraft.created_at))
            .limit(1)
        )
        latest_draft = latest_draft_result.scalar_one_or_none()
        
        return DraftStatusResponse(
            total_drafts=sum(status_counts.values()),
            pending_drafts=status_counts.get('pending', 0),
            sent_drafts=status_counts.get('sent', 0),
            recent_content_count=recent_content_count,
            last_generation=latest_draft,
            status_breakdown=status_counts
        )
        
    except Exception as e:
        logger.error(f"Error getting draft status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get draft status")


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Delete a specific draft.
    
    Removes a draft from the user's collection. This action cannot be undone.
    """
    try:
        # Get draft to verify ownership
        result = await session.execute(
            select(GeneratedDraft).where(
                and_(
                    GeneratedDraft.id == draft_id,
                    GeneratedDraft.user_id == current_user.id
                )
            )
        )
        draft = result.scalar_one_or_none()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Delete the draft
        await session.delete(draft)
        await session.commit()
        
        logger.info(f"User {current_user.id} deleted draft {draft_id}")
        
        return {"message": "Draft deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting draft {draft_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete draft")


@router.put("/{draft_id}/status")
async def update_draft_status(
    draft_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Update draft status.
    
    Allows updating the status of a draft (e.g., marking as sent, approved, etc.).
    """
    try:
        # Validate status
        valid_statuses = ['pending', 'approved', 'rejected', 'sent', 'scheduled']
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        # Get draft to verify ownership
        result = await session.execute(
            select(GeneratedDraft).where(
                and_(
                    GeneratedDraft.id == draft_id,
                    GeneratedDraft.user_id == current_user.id
                )
            )
        )
        draft = result.scalar_one_or_none()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Update status
        draft.status = status
        draft.updated_at = func.now()
        
        await session.commit()
        
        logger.info(f"User {current_user.id} updated draft {draft_id} status to {status}")
        
        return {"message": f"Draft status updated to {status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating draft status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update draft status")
