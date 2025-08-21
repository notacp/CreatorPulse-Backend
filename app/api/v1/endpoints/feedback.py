"""
Feedback processing endpoints for draft feedback collection.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from app.core.database import get_db
from app.models.draft import GeneratedDraft, DraftFeedback
from app.schemas.feedback import (
    FeedbackResponse,
    FeedbackTokenResponse,
    FeedbackAnalytics,
    EmailDeliveryStatusUpdate
)
from app.tasks.email_delivery_tasks import update_email_status
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/feedback/{token}/{feedback_type}")
async def submit_feedback_by_token(
    token: str = Path(..., description="Feedback token from email"),
    feedback_type: str = Path(..., pattern="^(positive|negative)$", description="Type of feedback"),
    source: str = Query(default="email", pattern="^(email|dashboard)$", description="Feedback source"),
    session: AsyncSession = Depends(get_db)
) -> FeedbackTokenResponse:
    """
    Submit feedback for a draft using email token.
    
    This endpoint is called when users click feedback links in emails.
    No authentication required as the token serves as authorization.
    """
    try:
        # Find draft by feedback token
        result = await session.execute(
            select(GeneratedDraft).where(
                and_(
                    GeneratedDraft.feedback_token == token,
                    GeneratedDraft.created_at > datetime.utcnow() - timedelta(days=30)  # Token expires after 30 days
                )
            )
        )
        draft = result.scalar_one_or_none()
        
        if not draft:
            raise HTTPException(
                status_code=404,
                detail="Invalid or expired feedback token"
            )
        
        # Check if feedback already exists for this draft
        existing_feedback_result = await session.execute(
            select(DraftFeedback).where(DraftFeedback.draft_id == draft.id)
        )
        existing_feedback = existing_feedback_result.scalar_one_or_none()
        
        if existing_feedback:
            # Update existing feedback
            existing_feedback.feedback_type = feedback_type
            existing_feedback.feedback_source = source
            existing_feedback.created_at = datetime.utcnow()
        else:
            # Create new feedback record
            feedback = DraftFeedback(
                draft_id=draft.id,
                feedback_type=feedback_type,
                feedback_source=source
            )
            session.add(feedback)
        
        # Update draft status based on feedback
        if feedback_type == "positive":
            draft.status = "approved"
        elif feedback_type == "negative":
            draft.status = "rejected"
        
        await session.commit()
        
        logger.info(f"Feedback recorded: draft_id={draft.id}, type={feedback_type}, source={source}")
        
        return FeedbackTokenResponse(
            success=True,
            message=f"Thank you for your {feedback_type} feedback!",
            draft_id=draft.id,
            feedback_type=feedback_type,
            redirect_url=f"https://creatorpulse.com/feedback/{token}/{feedback_type}/confirmation"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process feedback"
        )


@router.get("/feedback/{token}/{feedback_type}/confirmation")
async def feedback_confirmation(
    token: str = Path(..., description="Feedback token"),
    feedback_type: str = Path(..., pattern="^(positive|negative)$", description="Type of feedback"),
    session: AsyncSession = Depends(get_db)
) -> dict:
    """
    Show feedback confirmation page.
    
    This endpoint returns data for the frontend confirmation page.
    """
    try:
        # Verify token exists and get draft info
        result = await session.execute(
            select(GeneratedDraft).where(
                and_(
                    GeneratedDraft.feedback_token == token,
                    GeneratedDraft.created_at > datetime.utcnow() - timedelta(days=30)
                )
            )
        )
        draft = result.scalar_one_or_none()
        
        if not draft:
            raise HTTPException(
                status_code=404,
                detail="Invalid or expired feedback token"
            )
        
        return {
            "success": True,
            "feedback_type": feedback_type,
            "message": "Thank you for your feedback!" if feedback_type == "positive" else "Thanks for letting us know.",
            "draft_preview": draft.content[:100] + "..." if len(draft.content) > 100 else draft.content,
            "dashboard_url": "https://creatorpulse.com/dashboard",
            "sources_url": "https://creatorpulse.com/sources"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading confirmation page: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load confirmation page"
        )


@router.get("/drafts/{draft_id}/feedback")
async def get_draft_feedback(
    draft_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> Optional[FeedbackResponse]:
    """
    Get feedback for a specific draft.
    
    Used by the dashboard to show feedback status.
    """
    try:
        # Get feedback for the draft
        result = await session.execute(
            select(DraftFeedback).where(DraftFeedback.draft_id == draft_id)
        )
        feedback = result.scalar_one_or_none()
        
        if not feedback:
            return None
        
        return FeedbackResponse(
            id=feedback.id,
            draft_id=feedback.draft_id,
            feedback_type=feedback.feedback_type,
            feedback_source=feedback.feedback_source,
            created_at=feedback.created_at
        )
        
    except Exception as e:
        logger.error(f"Error getting draft feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get feedback"
        )


@router.get("/users/{user_id}/feedback/analytics")
async def get_user_feedback_analytics(
    user_id: UUID,
    days: int = Query(default=30, ge=1, le=365, description="Number of days to analyze"),
    session: AsyncSession = Depends(get_db)
) -> FeedbackAnalytics:
    """
    Get feedback analytics for a user.
    
    Returns summary statistics about user's draft feedback.
    """
    try:
        # Get feedback data for user's drafts in the specified period
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Query for all feedback on user's drafts
        feedback_query = """
        SELECT 
            df.feedback_type,
            df.feedback_source,
            COUNT(*) as count
        FROM draft_feedback df
        JOIN generated_drafts gd ON df.draft_id = gd.id
        WHERE gd.user_id = :user_id 
        AND df.created_at >= :since_date
        GROUP BY df.feedback_type, df.feedback_source
        """
        
        result = await session.execute(
            feedback_query,
            {"user_id": str(user_id), "since_date": since_date}
        )
        feedback_data = result.fetchall()
        
        # Calculate analytics
        total_feedback = 0
        positive_feedback = 0
        negative_feedback = 0
        email_feedback = 0
        dashboard_feedback = 0
        
        for row in feedback_data:
            feedback_type, feedback_source, count = row
            total_feedback += count
            
            if feedback_type == "positive":
                positive_feedback += count
            elif feedback_type == "negative":
                negative_feedback += count
                
            if feedback_source == "email":
                email_feedback += count
            elif feedback_source == "dashboard":
                dashboard_feedback += count
        
        # Calculate rates
        positive_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0
        negative_rate = (negative_feedback / total_feedback * 100) if total_feedback > 0 else 0
        email_rate = (email_feedback / total_feedback * 100) if total_feedback > 0 else 0
        
        return FeedbackAnalytics(
            total_feedback=total_feedback,
            positive_feedback=positive_feedback,
            negative_feedback=negative_feedback,
            positive_rate=round(positive_rate, 1),
            negative_rate=round(negative_rate, 1),
            email_feedback=email_feedback,
            dashboard_feedback=dashboard_feedback,
            email_engagement_rate=round(email_rate, 1),
            period_days=days
        )
        
    except Exception as e:
        logger.error(f"Error getting feedback analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get feedback analytics"
        )


@router.delete("/drafts/{draft_id}/feedback")
async def delete_draft_feedback(
    draft_id: UUID,
    session: AsyncSession = Depends(get_db)
) -> dict:
    """
    Delete feedback for a draft.
    
    This resets the draft status to pending.
    """
    try:
        # Get and delete feedback
        result = await session.execute(
            select(DraftFeedback).where(DraftFeedback.draft_id == draft_id)
        )
        feedback = result.scalar_one_or_none()
        
        if feedback:
            await session.delete(feedback)
            
            # Reset draft status to pending
            draft_result = await session.execute(
                select(GeneratedDraft).where(GeneratedDraft.id == draft_id)
            )
            draft = draft_result.scalar_one_or_none()
            
            if draft:
                draft.status = "pending"
            
            await session.commit()
            
            return {"success": True, "message": "Feedback deleted and draft reset to pending"}
        else:
            return {"success": True, "message": "No feedback found to delete"}
        
    except Exception as e:
        logger.error(f"Error deleting feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete feedback"
        )


@router.post("/webhooks/sendgrid/delivery")
async def sendgrid_webhook(
    events: list = None
) -> dict:
    """
    Handle SendGrid webhook events for email delivery status updates.
    
    This endpoint receives webhook events from SendGrid to track
    email delivery status, bounces, and other email events.
    """
    try:
        if not events:
            return {"success": True, "message": "No events to process"}
        
        processed_events = 0
        failed_events = 0
        
        for event in events:
            try:
                event_type = event.get("event")
                sendgrid_message_id = event.get("sg_message_id")
                
                if not sendgrid_message_id:
                    logger.warning(f"Event missing sg_message_id: {event}")
                    continue
                
                # Map SendGrid events to our status values
                status_mapping = {
                    "delivered": "delivered",
                    "bounce": "bounced",
                    "blocked": "failed",
                    "dropped": "failed",
                    "spamreport": "spam",
                    "unsubscribe": "failed"  # Treat unsubscribes as delivery failures
                }
                
                if event_type in status_mapping:
                    # Queue status update task
                    update_email_status.apply_async(
                        args=[
                            sendgrid_message_id,
                            status_mapping[event_type],
                            event.get("timestamp"),
                            event.get("reason")  # Error message for failed deliveries
                        ]
                    )
                    processed_events += 1
                else:
                    logger.info(f"Ignoring SendGrid event type: {event_type}")
                
            except Exception as e:
                logger.error(f"Failed to process SendGrid event: {e}")
                failed_events += 1
        
        logger.info(f"Processed {processed_events} SendGrid events, {failed_events} failed")
        
        result = {
            "success": True,
            "processed_events": processed_events,
            "failed_events": failed_events
        }
        
        return result
        
    except Exception as e:
        logger.error(f"SendGrid webhook error: {e}")
        # Don't return error to SendGrid, or it will retry
        return {"success": False, "error": "Internal processing error"}
