"""
Celery tasks for email delivery and management.

This module contains background tasks for:
- Sending daily draft emails
- Processing email delivery status updates
- Managing email schedules
- Handling email delivery retries
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_, desc, func, text
import pytz

from app.core.config import settings
from app.core.logging import get_logger
from app.services.email_service import email_service
from app.models.user import User
from app.models.draft import GeneratedDraft
from app.models.feedback import EmailDeliveryLog
from app.core.security import generate_feedback_token

logger = get_logger(__name__)


@shared_task(bind=True, name='app.tasks.email_delivery_tasks.send_daily_drafts_email')
def send_daily_drafts_email(self, user_id: str, max_drafts: int = 5) -> Dict[str, Any]:
    """
    Send daily drafts email to a specific user.
    
    This task:
    1. Gets the user's pending drafts
    2. Generates feedback tokens
    3. Sends email via SendGrid
    4. Logs delivery status
    
    Args:
        user_id: User ID to send email to
        max_drafts: Maximum number of drafts to include
        
    Returns:
        Dictionary with send results
    """
    async def _send_email():
        """Async implementation of email sending."""
        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                # Get user
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user or not user.active:
                    return {
                        "success": False,
                        "error": "User not found or inactive",
                        "user_id": user_id
                    }
                
                # Get pending drafts for the user
                drafts_result = await session.execute(
                    select(GeneratedDraft)
                    .where(
                        and_(
                            GeneratedDraft.user_id == user_id,
                            GeneratedDraft.status == "pending",
                            GeneratedDraft.created_at > datetime.utcnow() - timedelta(days=7)  # Last 7 days
                        )
                    )
                    .order_by(desc(GeneratedDraft.created_at))
                    .limit(max_drafts)
                )
                drafts = drafts_result.scalars().all()
                
                if not drafts:
                    return {
                        "success": False,
                        "error": "No pending drafts found",
                        "user_id": user_id
                    }
                
                # Generate feedback tokens for drafts that don't have them
                for draft in drafts:
                    if not draft.feedback_token:
                        draft.feedback_token = generate_feedback_token()
                
                await session.commit()
                
                # Prepare draft data for email
                draft_data = []
                for draft in drafts:
                    # Get source name (simplified for now)
                    source_name = "Unknown Source"
                    if draft.generation_metadata:
                        source_name = draft.generation_metadata.get("source_name", source_name)
                    
                    draft_data.append({
                        "id": draft.id,
                        "content": draft.content,
                        "source_name": source_name,
                        "character_count": draft.character_count or len(draft.content),
                        "feedback_token": draft.feedback_token
                    })
                
                # Send email
                email_result = await email_service.send_daily_drafts_email(
                    user_email=user.email,
                    user_name=user.email.split('@')[0],  # Use email prefix as name for now
                    user_id=user_id,
                    drafts=draft_data
                )
                
                # Log email delivery
                email_log = EmailDeliveryLog(
                    user_id=user.id,
                    email_type="daily_drafts",
                    sendgrid_message_id=email_result.get("sendgrid_message_id"),
                    status="sent" if email_result["success"] else "failed",
                    draft_ids=[draft.id for draft in drafts],
                    error_message=email_result.get("error") if not email_result["success"] else None
                )
                session.add(email_log)
                
                # Update drafts email_sent_at timestamp
                if email_result["success"]:
                    for draft in drafts:
                        draft.email_sent_at = datetime.utcnow()
                
                await session.commit()
                
                result = {
                    "success": email_result["success"],
                    "user_id": user_id,
                    "email": user.email,
                    "drafts_sent": len(drafts),
                    "sendgrid_message_id": email_result.get("sendgrid_message_id"),
                    "email_log_id": str(email_log.id)
                }
                
                if not email_result["success"]:
                    result["error"] = email_result.get("error", "Unknown email error")
                
                logger.info(f"Daily email sent to {user.email}: {result}")
                return result
                
        except Exception as e:
            logger.error(f"Failed to send daily email to user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
        finally:
            await engine.dispose()
    
    # Run async function
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Preparing email delivery'})
        result = asyncio.run(_send_email())
        
        if result["success"]:
            self.update_state(state='SUCCESS', meta=result)
        else:
            self.update_state(state='FAILURE', meta=result)
        
        return result
        
    except Exception as e:
        logger.error(f"Task execution failed for user {user_id}: {e}")
        error_result = {
            "success": False,
            "error": str(e),
            "user_id": user_id
        }
        self.update_state(state='FAILURE', meta=error_result)
        return error_result


@shared_task(bind=True, name='app.tasks.email_delivery_tasks.send_daily_emails_batch')
def send_daily_emails_batch(self, delivery_hour: int = None) -> Dict[str, Any]:
    """
    Send daily emails to all users scheduled for a specific hour.
    
    This task runs every hour and sends emails to users whose
    preferred delivery time matches the current hour.
    
    Args:
        delivery_hour: Specific hour to send emails for (0-23)
        
    Returns:
        Dictionary with batch send results
    """
    async def _send_batch():
        """Async implementation of batch email sending."""
        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                current_time = datetime.utcnow()
                target_hour = delivery_hour if delivery_hour is not None else current_time.hour
                
                # Get users who should receive emails at this hour
                # For now, we'll get all active users - in production, this would
                # filter by user's preferred delivery time and timezone
                users_result = await session.execute(
                    select(User).where(
                        and_(
                            User.active == True,
                            User.email_verified == True
                        )
                    )
                )
                users = users_result.scalars().all()
                
                if not users:
                    return {
                        "success": True,
                        "message": "No users found for email delivery",
                        "target_hour": target_hour,
                        "users_processed": 0
                    }
                
                # Filter users who have drafts to send
                eligible_users = []
                for user in users:
                    # Check if user has pending drafts
                    drafts_result = await session.execute(
                        select(func.count(GeneratedDraft.id))
                        .where(
                            and_(
                                GeneratedDraft.user_id == user.id,
                                GeneratedDraft.status == "pending",
                                GeneratedDraft.created_at > current_time - timedelta(days=7)
                            )
                        )
                    )
                    draft_count = drafts_result.scalar()
                    
                    if draft_count > 0:
                        eligible_users.append(user)
                
                logger.info(f"Found {len(eligible_users)} users eligible for daily emails at hour {target_hour}")
                
                # Send emails to eligible users
                successful_sends = 0
                failed_sends = 0
                results = []
                
                for user in eligible_users:
                    try:
                        # Use apply_async for non-blocking task execution
                        task_result = send_daily_drafts_email.apply_async(
                            args=[str(user.id)],
                            countdown=0  # Send immediately
                        )
                        
                        results.append({
                            "user_id": str(user.id),
                            "email": user.email,
                            "task_id": task_result.id,
                            "status": "queued"
                        })
                        
                        successful_sends += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to queue email for user {user.id}: {e}")
                        results.append({
                            "user_id": str(user.id),
                            "email": user.email,
                            "error": str(e),
                            "status": "failed"
                        })
                        failed_sends += 1
                
                return {
                    "success": True,
                    "target_hour": target_hour,
                    "users_processed": len(eligible_users),
                    "successful_queues": successful_sends,
                    "failed_queues": failed_sends,
                    "results": results
                }
                
        except Exception as e:
            logger.error(f"Batch email task failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "target_hour": target_hour
            }
        finally:
            await engine.dispose()
    
    try:
        self.update_state(state='PROGRESS', meta={'status': 'Processing batch email delivery'})
        result = asyncio.run(_send_batch())
        
        self.update_state(state='SUCCESS', meta=result)
        return result
        
    except Exception as e:
        logger.error(f"Batch email task execution failed: {e}")
        error_result = {
            "success": False,
            "error": str(e)
        }
        self.update_state(state='FAILURE', meta=error_result)
        return error_result


@shared_task(bind=True, name='app.tasks.email_delivery_tasks.retry_failed_emails')
def retry_failed_emails(self, max_retries: int = 3) -> Dict[str, Any]:
    """
    Retry failed email deliveries.
    
    This task finds email logs with failed status and retries them
    up to the maximum retry limit.
    
    Args:
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary with retry results
    """
    async def _retry_emails():
        """Async implementation of email retries."""
        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                # Find failed emails from the last 24 hours
                failed_emails_result = await session.execute(
                    select(EmailDeliveryLog)
                    .where(
                        and_(
                            EmailDeliveryLog.status == "failed",
                            EmailDeliveryLog.sent_at > datetime.utcnow() - timedelta(hours=24)
                        )
                    )
                    .order_by(EmailDeliveryLog.sent_at)
                )
                failed_emails = failed_emails_result.scalars().all()
                
                if not failed_emails:
                    return {
                        "success": True,
                        "message": "No failed emails to retry",
                        "retries_attempted": 0
                    }
                
                retries_attempted = 0
                successful_retries = 0
                failed_retries = 0
                
                for email_log in failed_emails:
                    try:
                        # Queue retry task for the user
                        task_result = send_daily_drafts_email.apply_async(
                            args=[str(email_log.user_id)],
                            countdown=30  # Wait 30 seconds before retry
                        )
                        
                        retries_attempted += 1
                        successful_retries += 1
                        
                        logger.info(f"Queued email retry for user {email_log.user_id}, task: {task_result.id}")
                        
                    except Exception as e:
                        logger.error(f"Failed to queue email retry for user {email_log.user_id}: {e}")
                        failed_retries += 1
                
                return {
                    "success": True,
                    "failed_emails_found": len(failed_emails),
                    "retries_attempted": retries_attempted,
                    "successful_retries": successful_retries,
                    "failed_retries": failed_retries
                }
                
        except Exception as e:
            logger.error(f"Email retry task failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            await engine.dispose()
    
    try:
        result = asyncio.run(_retry_emails())
        self.update_state(state='SUCCESS', meta=result)
        return result
        
    except Exception as e:
        logger.error(f"Email retry task execution failed: {e}")
        error_result = {
            "success": False,
            "error": str(e)
        }
        self.update_state(state='FAILURE', meta=error_result)
        return error_result


@shared_task(bind=True, name='app.tasks.email_delivery_tasks.update_email_status')
def update_email_status(
    self,
    sendgrid_message_id: str,
    status: str,
    delivered_at: str = None,
    error_message: str = None
) -> Dict[str, Any]:
    """
    Update email delivery status from SendGrid webhook.
    
    This task is called by SendGrid webhooks to update the
    delivery status of sent emails.
    
    Args:
        sendgrid_message_id: SendGrid message ID
        status: New delivery status
        delivered_at: Delivery timestamp (ISO format)
        error_message: Error message if status is failed
        
    Returns:
        Dictionary with update results
    """
    async def _update_status():
        """Async implementation of status update."""
        engine = create_async_engine(settings.database_url, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        try:
            async with async_session() as session:
                # Find email log by SendGrid message ID
                email_log_result = await session.execute(
                    select(EmailDeliveryLog).where(
                        EmailDeliveryLog.sendgrid_message_id == sendgrid_message_id
                    )
                )
                email_log = email_log_result.scalar_one_or_none()
                
                if not email_log:
                    return {
                        "success": False,
                        "error": "Email log not found",
                        "sendgrid_message_id": sendgrid_message_id
                    }
                
                # Update status
                email_log.status = status
                if error_message:
                    email_log.error_message = error_message
                
                if delivered_at:
                    try:
                        email_log.delivered_at = datetime.fromisoformat(delivered_at.replace('Z', '+00:00'))
                    except ValueError:
                        logger.warning(f"Invalid delivered_at format: {delivered_at}")
                
                await session.commit()
                
                logger.info(f"Updated email status: {sendgrid_message_id} -> {status}")
                
                return {
                    "success": True,
                    "sendgrid_message_id": sendgrid_message_id,
                    "status": status,
                    "email_log_id": str(email_log.id)
                }
                
        except Exception as e:
            logger.error(f"Failed to update email status: {e}")
            return {
                "success": False,
                "error": str(e),
                "sendgrid_message_id": sendgrid_message_id
            }
        finally:
            await engine.dispose()
    
    try:
        result = asyncio.run(_update_status())
        self.update_state(state='SUCCESS', meta=result)
        return result
        
    except Exception as e:
        logger.error(f"Email status update task failed: {e}")
        error_result = {
            "success": False,
            "error": str(e),
            "sendgrid_message_id": sendgrid_message_id
        }
        self.update_state(state='FAILURE', meta=error_result)
        return error_result
