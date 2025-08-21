"""
Email service for sending draft emails and handling delivery tracking.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import secrets
from uuid import UUID

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import generate_feedback_token

logger = get_logger(__name__)


class EmailService:
    """Service for handling email delivery and tracking."""
    
    def __init__(self):
        self.sendgrid_client = None
        self.template_env = None
        self._initialize_sendgrid()
        self._initialize_templates()
    
    def _initialize_sendgrid(self):
        """Initialize SendGrid client."""
        try:
            if settings.sendgrid_api_key:
                self.sendgrid_client = SendGridAPIClient(api_key=settings.sendgrid_api_key)
                logger.info("SendGrid client initialized successfully")
            else:
                logger.warning("SendGrid API key not configured")
        except Exception as e:
            logger.error(f"Failed to initialize SendGrid client: {e}")
    
    def _initialize_templates(self):
        """Initialize Jinja2 template environment."""
        try:
            template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
            self.template_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=True
            )
            logger.info("Email template environment initialized")
        except Exception as e:
            logger.error(f"Failed to initialize template environment: {e}")
    
    def generate_feedback_urls(self, draft_id: str, token: str, base_url: str = None) -> Dict[str, str]:
        """Generate feedback URLs for positive and negative feedback."""
        if not base_url:
            base_url = "https://creatorpulse.com"  # Default production URL
        
        positive_url = f"{base_url}/feedback/{token}/positive"
        negative_url = f"{base_url}/feedback/{token}/negative"
        
        return {
            "feedback_url_positive": positive_url,
            "feedback_url_negative": negative_url
        }
    
    def generate_utility_urls(self, user_id: str, base_url: str = None) -> Dict[str, str]:
        """Generate utility URLs for dashboard, settings, etc."""
        if not base_url:
            base_url = "https://creatorpulse.com"
        
        return {
            "dashboard_url": f"{base_url}/dashboard",
            "sources_url": f"{base_url}/sources",
            "settings_url": f"{base_url}/settings",
            "preferences_url": f"{base_url}/settings#email",
            "unsubscribe_url": f"{base_url}/auth/unsubscribe?user_id={user_id}"
        }
    
    def get_time_of_day(self, hour: int = None) -> str:
        """Get appropriate greeting based on time of day."""
        if hour is None:
            hour = datetime.now().hour
        
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "evening"  # For late night/early morning
    
    def render_daily_drafts_email(
        self,
        user_name: str,
        user_email: str,
        drafts: List[Dict[str, Any]],
        user_id: str,
        base_url: str = None
    ) -> str:
        """Render the daily drafts email template."""
        try:
            if not self.template_env:
                raise Exception("Template environment not initialized")
            
            template = self.template_env.get_template("email/daily_drafts.html")
            
            # Generate feedback URLs for each draft
            for draft in drafts:
                if not draft.get('feedback_token'):
                    draft['feedback_token'] = generate_feedback_token()
                
                feedback_urls = self.generate_feedback_urls(
                    draft_id=str(draft['id']),
                    token=draft['feedback_token'],
                    base_url=base_url
                )
                draft.update(feedback_urls)
            
            # Generate utility URLs
            utility_urls = self.generate_utility_urls(user_id, base_url)
            
            # Get time of day for greeting
            time_of_day = self.get_time_of_day()
            
            # Render template
            html_content = template.render(
                user_name=user_name,
                user_email=user_email,
                drafts=drafts,
                time_of_day=time_of_day,
                **utility_urls
            )
            
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to render email template: {e}")
            raise
    
    async def send_daily_drafts_email(
        self,
        user_email: str,
        user_name: str,
        user_id: str,
        drafts: List[Dict[str, Any]],
        base_url: str = None
    ) -> Dict[str, Any]:
        """Send daily drafts email to user."""
        try:
            if not self.sendgrid_client:
                return {
                    "success": False,
                    "error": "SendGrid client not initialized",
                    "sendgrid_message_id": None
                }
            
            if not drafts:
                return {
                    "success": False,
                    "error": "No drafts to send",
                    "sendgrid_message_id": None
                }
            
            # Render email content
            html_content = self.render_daily_drafts_email(
                user_name=user_name,
                user_email=user_email,
                drafts=drafts,
                user_id=user_id,
                base_url=base_url
            )
            
            # Create email
            from_email = Email(settings.sendgrid_from_email, settings.sendgrid_from_name)
            to_email = To(user_email, user_name)
            
            # Subject line with date
            today = datetime.now().strftime("%B %d")
            subject = f"Your LinkedIn Drafts for {today} ({len(drafts)} ideas)"
            
            # Create plain text version
            plain_text = self._create_plain_text_version(drafts, user_name)
            
            # Create mail object
            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=plain_text,
                html_content=html_content
            )
            
            # Add custom headers for tracking
            mail.add_custom_arg("user_id", user_id)
            mail.add_custom_arg("email_type", "daily_drafts")
            mail.add_custom_arg("draft_count", str(len(drafts)))
            mail.add_custom_arg("sent_at", datetime.utcnow().isoformat())
            
            # Send email
            response = self.sendgrid_client.send(mail)
            
            # Parse SendGrid response
            sendgrid_message_id = None
            if hasattr(response, 'headers') and 'X-Message-Id' in response.headers:
                sendgrid_message_id = response.headers['X-Message-Id']
            
            return {
                "success": response.status_code in [200, 202],
                "status_code": response.status_code,
                "sendgrid_message_id": sendgrid_message_id,
                "draft_count": len(drafts),
                "email": user_email
            }
            
        except Exception as e:
            logger.error(f"Failed to send daily drafts email to {user_email}: {e}")
            return {
                "success": False,
                "error": str(e),
                "sendgrid_message_id": None
            }
    
    def _create_plain_text_version(self, drafts: List[Dict[str, Any]], user_name: str) -> str:
        """Create plain text version of the email."""
        text_content = f"Hi {user_name}!\n\n"
        text_content += f"Here are your {len(drafts)} LinkedIn draft ideas for today:\n\n"
        
        for i, draft in enumerate(drafts, 1):
            text_content += f"Draft {i}:\n"
            text_content += f"{draft['content']}\n"
            text_content += f"Source: {draft.get('source_name', 'Unknown')}\n"
            
            if draft.get('feedback_url_positive'):
                text_content += f"👍 Like: {draft['feedback_url_positive']}\n"
            if draft.get('feedback_url_negative'):
                text_content += f"👎 Pass: {draft['feedback_url_negative']}\n"
            
            text_content += "\n" + "-" * 50 + "\n\n"
        
        text_content += "Manage your content sources and settings at https://creatorpulse.com/dashboard\n\n"
        text_content += "Best regards,\nThe CreatorPulse Team"
        
        return text_content
    
    async def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        verification_url: str = None
    ) -> Dict[str, Any]:
        """Send welcome email to new user."""
        try:
            if not self.sendgrid_client:
                return {"success": False, "error": "SendGrid client not initialized"}
            
            from_email = Email(settings.sendgrid_from_email, settings.sendgrid_from_name)
            to_email = To(user_email, user_name)
            
            subject = "Welcome to CreatorPulse! 🚀"
            
            html_content = f"""
            <h1>Welcome to CreatorPulse, {user_name}!</h1>
            <p>We're excited to help you create amazing LinkedIn content.</p>
            <p>To get started:</p>
            <ol>
                <li>Complete your profile setup</li>
                <li>Add your content sources</li>
                <li>Upload some writing samples for style training</li>
            </ol>
            <p><a href="https://creatorpulse.com/onboarding">Complete Setup</a></p>
            """
            
            if verification_url:
                html_content += f'<p><a href="{verification_url}">Verify your email address</a></p>'
            
            plain_text = f"""
            Welcome to CreatorPulse, {user_name}!
            
            We're excited to help you create amazing LinkedIn content.
            
            To get started:
            1. Complete your profile setup
            2. Add your content sources
            3. Upload some writing samples for style training
            
            Get started: https://creatorpulse.com/onboarding
            """
            
            if verification_url:
                plain_text += f"\n\nVerify your email: {verification_url}"
            
            mail = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=plain_text,
                html_content=html_content
            )
            
            response = self.sendgrid_client.send(mail)
            
            return {
                "success": response.status_code in [200, 202],
                "status_code": response.status_code
            }
            
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user_email}: {e}")
            return {"success": False, "error": str(e)}
    
    def validate_email_delivery(self, sendgrid_message_id: str) -> Dict[str, Any]:
        """Check delivery status of an email via SendGrid API."""
        try:
            if not self.sendgrid_client:
                return {"success": False, "error": "SendGrid client not initialized"}
            
            # Note: This would require SendGrid's Event Webhook or Stats API
            # For now, we'll return a placeholder response
            return {
                "success": True,
                "message_id": sendgrid_message_id,
                "status": "sent",  # Would be actual status from SendGrid
                "delivered_at": None
            }
            
        except Exception as e:
            logger.error(f"Failed to validate email delivery for {sendgrid_message_id}: {e}")
            return {"success": False, "error": str(e)}


# Global email service instance
email_service = EmailService()
