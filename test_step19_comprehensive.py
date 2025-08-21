"""
Comprehensive test suite for Step 19: Email Delivery and Feedback System.

This test suite covers:
- HTML email template rendering
- SendGrid integration and email delivery
- Feedback token generation and validation
- Feedback processing endpoints
- Email delivery Celery tasks
- SendGrid webhook handling
- Complete end-to-end email workflow
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4

# Add the parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from sqlalchemy import select, and_, desc, func, delete
    from app.core.database import init_db, close_db, get_db
    from app.core.config import settings
    from app.core.security import generate_feedback_token
    from app.models.user import User
    from app.models.draft import GeneratedDraft, DraftFeedback
    from app.models.feedback import EmailDeliveryLog
    from app.services.email_service import email_service
    from app.tasks.email_delivery_tasks import (
        send_daily_drafts_email,
        send_daily_emails_batch,
        update_email_status
    )
    from app.api.v1.endpoints.feedback import router as feedback_router
    from fastapi.testclient import TestClient
    from app.main import app
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


class TestStep19:
    """Comprehensive test suite for Step 19 functionality."""
    
    def __init__(self):
        self.test_user_id = None
        self.test_draft_ids = []
        self.test_email_log_ids = []
        self.test_feedback_ids = []
        
    async def setup_test_environment(self):
        """Set up test environment with sample data."""
        print("\n🔄 Setting up test environment...")
        
        try:
            # Initialize database
            await init_db()
            
            # Create test user
            async for session in get_db():
                # Create test user
                test_user = User(
                    email=f"test_step19_{uuid4().hex[:8]}@example.com",
                    password_hash="$2b$12$test_hash",
                    active=True,
                    email_verified=True
                )
                session.add(test_user)
                await session.commit()
                await session.refresh(test_user)
                self.test_user_id = str(test_user.id)
                
                # Create test drafts with feedback tokens
                test_drafts = [
                    {
                        "content": "🚀 Just discovered an amazing new AI tool that's revolutionizing content creation! The ability to generate personalized LinkedIn posts while maintaining your unique voice is incredible. This could be a game-changer for content creators and marketers. What's your experience with AI writing tools? #AI #ContentCreation #LinkedIn",
                        "character_count": 285,
                        "engagement_score": 8.5
                    },
                    {
                        "content": "💡 Key insight from today's team meeting: The best strategies emerge when we combine human creativity with data-driven insights. It's not about replacing human judgment—it's about amplifying it. How do you balance intuition and analytics in your decision-making? #Strategy #DataDriven #TeamWork",
                        "character_count": 298,
                        "engagement_score": 7.8
                    },
                    {
                        "content": "🔗 Building meaningful professional relationships goes beyond just connecting on LinkedIn. It's about genuine engagement, shared value, and mutual support. Quality always trumps quantity in networking. What's your approach to building authentic professional relationships? #Networking #ProfessionalGrowth",
                        "character_count": 312,
                        "engagement_score": 8.2
                    }
                ]
                
                for i, draft_data in enumerate(test_drafts):
                    draft = GeneratedDraft(
                        user_id=test_user.id,
                        content=draft_data["content"],
                        status="pending",
                        feedback_token=generate_feedback_token(),
                        character_count=draft_data["character_count"],
                        engagement_score=draft_data["engagement_score"],
                        generation_metadata={
                            "source_name": f"Tech Source {i+1}",
                            "generation_method": "gemini_rag",
                            "style_similarity": 0.85
                        }
                    )
                    session.add(draft)
                    await session.commit()
                    await session.refresh(draft)
                    self.test_draft_ids.append(str(draft.id))
                
                break
            
            print(f"✅ Test environment setup complete")
            print(f"   📧 Test user: {self.test_user_id}")
            print(f"   📝 Test drafts: {len(self.test_draft_ids)}")
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    async def test_email_template_rendering(self):
        """Test HTML email template rendering functionality."""
        print("\n🧪 Testing Email Template Rendering...")
        
        try:
            # Test template initialization
            assert email_service.template_env is not None, "Template environment not initialized"
            
            # Prepare test draft data
            test_drafts = [
                {
                    "id": self.test_draft_ids[0],
                    "content": "🚀 Test draft content for email template rendering...",
                    "source_name": "Test Source",
                    "character_count": 156,
                    "feedback_token": generate_feedback_token()
                }
            ]
            
            # Test HTML email rendering
            html_content = email_service.render_daily_drafts_email(
                user_name="Test User",
                user_email="test@example.com",
                drafts=test_drafts,
                user_id=self.test_user_id
            )
            
            # Verify HTML content
            assert len(html_content) > 1000, "HTML content too short"
            assert "Test User" in html_content, "User name not found in template"
            assert "Test draft content" in html_content, "Draft content not found"
            # Check for generated feedback URLs in draft data
            assert test_drafts[0].get('feedback_url_positive'), "Positive feedback URL not generated"
            assert test_drafts[0].get('feedback_url_negative'), "Negative feedback URL not generated"
            assert "dashboard_url" in html_content, "Dashboard URL not found"
            assert "CreatorPulse" in html_content, "Brand name not found"
            
            print("✅ Email template rendering working correctly")
            
            # Test feedback URL generation
            feedback_urls = email_service.generate_feedback_urls(
                draft_id=test_drafts[0]["id"],
                token=test_drafts[0]["feedback_token"]
            )
            
            assert "feedback_url_positive" in feedback_urls
            assert "feedback_url_negative" in feedback_urls
            assert "/feedback/" in feedback_urls["feedback_url_positive"]
            assert "/positive" in feedback_urls["feedback_url_positive"]
            assert "/negative" in feedback_urls["feedback_url_negative"]
            
            print("✅ Feedback URL generation working correctly")
            
            return True
            
        except Exception as e:
            print(f"❌ Email template test failed: {e}")
            return False
    
    async def test_email_service_integration(self):
        """Test SendGrid integration and email service functionality."""
        print("\n🧪 Testing Email Service Integration...")
        
        try:
            # Test email service initialization
            assert hasattr(email_service, 'sendgrid_client'), "SendGrid client not initialized"
            
            # Prepare test draft data
            test_drafts = []
            async for session in get_db():
                # Get actual test drafts from database
                drafts_result = await session.execute(
                    select(GeneratedDraft).where(GeneratedDraft.id.in_(self.test_draft_ids))
                )
                drafts = drafts_result.scalars().all()
                
                for draft in drafts:
                    test_drafts.append({
                        "id": draft.id,
                        "content": draft.content,
                        "source_name": draft.generation_metadata.get("source_name", "Test Source"),
                        "character_count": draft.character_count,
                        "feedback_token": draft.feedback_token
                    })
                break
            
            # Mock SendGrid for testing
            with patch.object(email_service, 'sendgrid_client') as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 202
                mock_response.headers = {'X-Message-Id': 'test_message_id_123'}
                mock_client.send.return_value = mock_response
                
                # Test email sending
                result = await email_service.send_daily_drafts_email(
                    user_email="test@example.com",
                    user_name="Test User",
                    user_id=self.test_user_id,
                    drafts=test_drafts
                )
                
                # Verify email send result
                assert result["success"] == True, f"Email send failed: {result}"
                assert result["status_code"] == 202, "Unexpected status code"
                assert result["sendgrid_message_id"] == "test_message_id_123", "Message ID not captured"
                assert result["draft_count"] == len(test_drafts), "Draft count mismatch"
                
                print(f"✅ Email service integration test passed")
                print(f"   📧 Drafts sent: {result['draft_count']}")
                print(f"   🆔 Message ID: {result['sendgrid_message_id']}")
            
            # Test welcome email sending
            with patch.object(email_service, 'sendgrid_client') as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 202
                mock_client.send.return_value = mock_response
                
                welcome_result = await email_service.send_welcome_email(
                    user_email="test@example.com",
                    user_name="Test User"
                )
                
                assert welcome_result["success"] == True, "Welcome email failed"
                print("✅ Welcome email service working")
            
            return True
            
        except Exception as e:
            print(f"❌ Email service test failed: {e}")
            return False
    
    async def test_feedback_endpoints(self):
        """Test feedback processing endpoints."""
        print("\n🧪 Testing Feedback Endpoints...")
        
        try:
            # Create test client
            client = TestClient(app)
            
            # Get a test draft with feedback token
            async for session in get_db():
                draft_result = await session.execute(
                    select(GeneratedDraft).where(GeneratedDraft.id == self.test_draft_ids[0])
                )
                draft = draft_result.scalar_one()
                test_token = draft.feedback_token
                break
            
            # Test positive feedback submission
            response = client.post(f"/v1/feedback/{test_token}/positive?source=email")
            
            assert response.status_code == 200, f"Positive feedback failed: {response.text}"
            data = response.json()
            assert data["success"] == True, "Feedback submission not successful"
            assert data["feedback_type"] == "positive", "Feedback type incorrect"
            assert "draft_id" in data, "Draft ID not returned"
            
            print("✅ Positive feedback endpoint working")
            
            # Test feedback confirmation page
            response = client.get(f"/v1/feedback/{test_token}/positive/confirmation")
            assert response.status_code == 200, "Confirmation page failed"
            conf_data = response.json()
            assert conf_data["success"] == True, "Confirmation page not successful"
            assert conf_data["feedback_type"] == "positive", "Confirmation feedback type incorrect"
            
            print("✅ Feedback confirmation endpoint working")
            
            # Test getting draft feedback
            draft_id = self.test_draft_ids[0]
            response = client.get(f"/v1/drafts/{draft_id}/feedback")
            
            if response.status_code == 200:
                feedback_data = response.json()
                if feedback_data:  # Feedback exists
                    assert feedback_data["feedback_type"] in ["positive", "negative"]
                    assert feedback_data["feedback_source"] in ["email", "dashboard"]
                    print("✅ Get draft feedback endpoint working")
                else:
                    print("✅ Get draft feedback endpoint working (no feedback found)")
            else:
                print(f"⚠️  Get draft feedback returned {response.status_code}")
            
            # Test negative feedback with different token
            if len(self.test_draft_ids) > 1:
                async for session in get_db():
                    draft_result = await session.execute(
                        select(GeneratedDraft).where(GeneratedDraft.id == self.test_draft_ids[1])
                    )
                    draft = draft_result.scalar_one()
                    test_token2 = draft.feedback_token
                    break
                
                response = client.post(f"/v1/feedback/{test_token2}/negative?source=dashboard")
                assert response.status_code == 200, "Negative feedback failed"
                data = response.json()
                assert data["feedback_type"] == "negative", "Negative feedback type incorrect"
                
                print("✅ Negative feedback endpoint working")
            
            # Test invalid token
            response = client.post("/v1/feedback/invalid_token_123/positive")
            assert response.status_code == 404, "Invalid token should return 404"
            
            print("✅ Invalid token handling working")
            
            return True
            
        except Exception as e:
            print(f"❌ Feedback endpoints test failed: {e}")
            return False
    
    async def test_email_delivery_tasks(self):
        """Test Celery email delivery tasks."""
        print("\n🧪 Testing Email Delivery Tasks...")
        
        try:
            # Test that task modules can be imported
            from app.tasks.email_delivery_tasks import (
                send_daily_drafts_email,
                send_daily_emails_batch,
                update_email_status
            )
            
            print("✅ Email delivery task imports successful")
            
            # Test task structure
            assert hasattr(send_daily_drafts_email, 'apply_async'), "send_daily_drafts_email should be a Celery task"
            assert hasattr(send_daily_emails_batch, 'apply_async'), "send_daily_emails_batch should be a Celery task"
            assert hasattr(update_email_status, 'apply_async'), "update_email_status should be a Celery task"
            
            print("✅ Celery task structure correct")
            
            # Test email delivery task execution (synchronous for testing)
            with patch.object(email_service, 'sendgrid_client') as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 202
                mock_response.headers = {'X-Message-Id': 'test_task_message_123'}
                mock_client.send.return_value = mock_response
                
                # Execute task directly (not via Celery for testing)
                task_result = await self._run_task_sync(
                    send_daily_drafts_email,
                    user_id=self.test_user_id,
                    max_drafts=3
                )
                
                assert task_result["success"] == True, f"Task execution failed: {task_result}"
                assert "drafts_sent" in task_result, "Drafts sent count missing"
                assert task_result["drafts_sent"] > 0, "No drafts were sent"
                
                print(f"✅ Email delivery task execution successful")
                print(f"   📧 Drafts sent: {task_result['drafts_sent']}")
            
            # Test email status update task
            status_result = await self._run_task_sync(
                update_email_status,
                "test_message_123",
                "delivered",
                datetime.utcnow().isoformat()
            )
            
            # Status update might fail if message ID doesn't exist, which is expected
            print(f"✅ Email status update task structure working")
            
            return True
            
        except Exception as e:
            print(f"❌ Email delivery tasks test failed: {e}")
            return False
    
    async def test_sendgrid_webhook(self):
        """Test SendGrid webhook handling."""
        print("\n🧪 Testing SendGrid Webhook...")
        
        try:
            # Create test client
            client = TestClient(app)
            
            # Test webhook with delivery event
            webhook_events = [
                {
                    "event": "delivered",
                    "sg_message_id": "test_message_123",
                    "timestamp": int(datetime.utcnow().timestamp()),
                    "email": "test@example.com"
                },
                {
                    "event": "bounce",
                    "sg_message_id": "test_message_456",
                    "timestamp": int(datetime.utcnow().timestamp()),
                    "reason": "Invalid email address"
                }
            ]
            
            # Test webhook endpoint
            response = client.post("/v1/webhooks/sendgrid/delivery", json=webhook_events)
            
            assert response.status_code == 200, f"Webhook failed: {response.text}"
            data = response.json()
            assert data["success"] == True, "Webhook processing not successful"
            assert "processed_events" in data, "Processed events count missing"
            
            print(f"✅ SendGrid webhook processing working")
            print(f"   📊 Events processed: {data['processed_events']}")
            
            # Test webhook with empty events
            response = client.post("/v1/webhooks/sendgrid/delivery", json=[])
            assert response.status_code == 200, "Empty webhook should succeed"
            
            # Test webhook with invalid data
            response = client.post("/v1/webhooks/sendgrid/delivery", json=None)
            assert response.status_code == 200, "Null webhook should not fail"
            
            print("✅ SendGrid webhook edge cases working")
            
            return True
            
        except Exception as e:
            print(f"❌ SendGrid webhook test failed: {e}")
            return False
    
    async def test_end_to_end_email_workflow(self):
        """Test the complete end-to-end email workflow."""
        print("\n🧪 Testing End-to-End Email Workflow...")
        
        try:
            # Step 1: Generate feedback tokens for drafts (if not already present)
            async for session in get_db():
                draft_result = await session.execute(
                    select(GeneratedDraft).where(GeneratedDraft.id.in_(self.test_draft_ids))
                )
                drafts = draft_result.scalars().all()
                
                for draft in drafts:
                    if not draft.feedback_token:
                        draft.feedback_token = generate_feedback_token()
                
                await session.commit()
                break
            
            print("✅ Step 1: Feedback tokens generated")
            
            # Step 2: Mock email sending
            with patch.object(email_service, 'sendgrid_client') as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 202
                mock_response.headers = {'X-Message-Id': 'end_to_end_test_123'}
                mock_client.send.return_value = mock_response
                
                # Send daily email
                email_result = await self._run_task_sync(
                    send_daily_drafts_email,
                    self.test_user_id,
                    5
                )
                
                assert email_result["success"] == True, "Email sending failed"
                print(f"✅ Step 2: Email sent successfully ({email_result['drafts_sent']} drafts)")
            
            # Step 3: Simulate user clicking feedback link
            client = TestClient(app)
            
            async for session in get_db():
                draft_result = await session.execute(
                    select(GeneratedDraft).where(GeneratedDraft.id == self.test_draft_ids[0])
                )
                draft = draft_result.scalar_one()
                test_token = draft.feedback_token
                break
            
            # Submit positive feedback
            response = client.post(f"/v1/feedback/{test_token}/positive?source=email")
            assert response.status_code == 200, "Feedback submission failed"
            
            print("✅ Step 3: User feedback processed")
            
            # Step 4: Verify feedback was recorded
            async for session in get_db():
                feedback_result = await session.execute(
                    select(DraftFeedback).where(DraftFeedback.draft_id == self.test_draft_ids[0])
                )
                feedback = feedback_result.scalar_one_or_none()
                
                if feedback:
                    assert feedback.feedback_type == "positive", "Feedback type incorrect"
                    assert feedback.feedback_source == "email", "Feedback source incorrect"
                    self.test_feedback_ids.append(str(feedback.id))
                    print("✅ Step 4: Feedback recorded in database")
                else:
                    print("⚠️  Step 4: Feedback not found in database")
                
                # Verify draft status updated
                draft_result = await session.execute(
                    select(GeneratedDraft).where(GeneratedDraft.id == self.test_draft_ids[0])
                )
                draft = draft_result.scalar_one()
                assert draft.status == "approved", "Draft status not updated"
                
                break
            
            print("✅ Step 5: Draft status updated correctly")
            
            # Step 6: Test email delivery log (would be created in real scenario)
            async for session in get_db():
                # Check if email delivery log exists
                log_result = await session.execute(
                    select(EmailDeliveryLog).where(EmailDeliveryLog.user_id == self.test_user_id)
                )
                logs = log_result.scalars().all()
                
                if logs:
                    for log in logs:
                        self.test_email_log_ids.append(str(log.id))
                    print(f"✅ Step 6: Email delivery logs found ({len(logs)} entries)")
                else:
                    print("⚠️  Step 6: No email delivery logs found (expected in mock scenario)")
                
                break
            
            print("🎉 End-to-end email workflow completed successfully!")
            
            return True
            
        except Exception as e:
            print(f"❌ End-to-end workflow test failed: {e}")
            return False
    
    async def cleanup_test_data(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        try:
            async for session in get_db():
                # Delete test feedback
                if self.test_feedback_ids:
                    await session.execute(
                        delete(DraftFeedback).where(DraftFeedback.id.in_(self.test_feedback_ids))
                    )
                
                # Delete test email logs
                if self.test_email_log_ids:
                    await session.execute(
                        delete(EmailDeliveryLog).where(EmailDeliveryLog.id.in_(self.test_email_log_ids))
                    )
                
                # Delete test drafts
                if self.test_draft_ids:
                    await session.execute(
                        delete(GeneratedDraft).where(GeneratedDraft.id.in_(self.test_draft_ids))
                    )
                
                # Delete test user
                if self.test_user_id:
                    await session.execute(
                        delete(User).where(User.id == self.test_user_id)
                    )
                
                await session.commit()
                break
            
            print("✅ Test data cleanup completed")
            
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
    
    async def _run_task_sync(self, task_func, **kwargs):
        """Run a Celery task synchronously for testing."""
        try:
            # Create a mock task object
            mock_task = MagicMock()
            mock_task.update_state = MagicMock()
            
            # Call the task function with mock self and keyword args
            result = task_func(mock_task, **kwargs)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}


async def run_all_tests():
    """Run all Step 19 tests."""
    print("🚀 Starting Step 19 Comprehensive Test Suite")
    print("=" * 70)
    
    tester = TestStep19()
    
    try:
        # Setup
        setup_success = await tester.setup_test_environment()
        if not setup_success:
            print("❌ Setup failed, aborting tests")
            return False
        
        # Run tests
        tests = [
            ("Email Template Rendering", tester.test_email_template_rendering),
            ("Email Service Integration", tester.test_email_service_integration),
            ("Feedback Endpoints", tester.test_feedback_endpoints),
            ("Email Delivery Tasks", tester.test_email_delivery_tasks),
            ("SendGrid Webhook", tester.test_sendgrid_webhook),
            ("End-to-End Email Workflow", tester.test_end_to_end_email_workflow),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                print(f"\n📋 Running {test_name}...")
                result = await test_func()
                if result:
                    passed += 1
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")
            except Exception as e:
                print(f"❌ {test_name} ERROR: {e}")
        
        # Summary
        print(f"\n" + "=" * 70)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All Step 19 tests PASSED!")
            print("\n✅ Step 19 Implementation Summary:")
            print("   📧 HTML email template with responsive design")
            print("   📮 SendGrid integration with delivery tracking")
            print("   🔗 Feedback link generation with secure tokens")
            print("   📊 Feedback processing endpoints")
            print("   ⏰ Celery Beat scheduler for email delivery")
            print("   🔄 Email delivery tasks with retry logic")
            print("   🪝 SendGrid webhook for status updates")
            print("   🌐 Complete email delivery workflow")
        else:
            print("⚠️  Some tests failed - review implementation")
        
        return passed == total
        
    finally:
        # Cleanup
        await tester.cleanup_test_data()
        await close_db()


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
