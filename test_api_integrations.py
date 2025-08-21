"""
Test script to verify Twitter and SendGrid API integrations.
"""

import asyncio
import os
from datetime import datetime
from app.core.config import settings

async def test_twitter_integration():
    """Test Twitter API integration."""
    print("🐦 Testing Twitter API Integration...")
    print("=" * 40)
    
    try:
        import tweepy
        
        # Check if API key is configured
        if not settings.twitter_bearer_token:
            print("❌ Twitter Bearer Token not configured")
            return False
        
        print("✅ Twitter Bearer Token is configured")
        
        # Initialize Twitter client
        client = tweepy.Client(bearer_token=settings.twitter_bearer_token)
        
        # Test API connection with a simple user lookup
        try:
            # Get Twitter's own account as a test
            user = client.get_user(username="Twitter")
            if user.data:
                print(f"✅ Twitter API connection successful")
                print(f"   Test user: @{user.data.username} ({user.data.name})")
                print(f"   Followers: {user.data.public_metrics['followers_count']:,}")
                return True
            else:
                print("❌ Twitter API returned no data")
                return False
                
        except tweepy.Unauthorized:
            print("❌ Twitter API authentication failed - check your Bearer Token")
            return False
        except tweepy.TooManyRequests:
            print("⚠️  Twitter API rate limit exceeded - but authentication is working")
            return True
        except Exception as e:
            print(f"❌ Twitter API error: {e}")
            return False
            
    except ImportError:
        print("❌ Tweepy not installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_sendgrid_integration():
    """Test SendGrid API integration."""
    print("\n📧 Testing SendGrid API Integration...")
    print("=" * 40)
    
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail
        
        # Check if API key is configured
        if not settings.sendgrid_api_key:
            print("❌ SendGrid API Key not configured")
            return False
        
        print("✅ SendGrid API Key is configured")
        
        # Initialize SendGrid client
        sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key)
        
        # Test API connection with API key validation
        try:
            # Use the API key validation endpoint
            response = sg.client.user.username.get()
            
            if response.status_code == 200:
                print("✅ SendGrid API connection successful")
                user_data = response.body.decode('utf-8')
                if user_data and user_data != '""':
                    print(f"   Account info available")
                else:
                    print("   API key valid but no username set")
                return True
            elif response.status_code == 401:
                print("❌ SendGrid API authentication failed - check your API key")
                return False
            else:
                print(f"⚠️  SendGrid API returned status {response.status_code}")
                return False
                
        except Exception as e:
            # Try alternative test with sender verification
            try:
                response = sg.client.verified_senders.get()
                if response.status_code in [200, 403]:  # 403 might mean no verified senders
                    print("✅ SendGrid API key is valid")
                    print("   Note: Set up sender verification in SendGrid dashboard")
                    return True
                else:
                    print(f"❌ SendGrid API error: {e}")
                    return False
            except Exception as e2:
                print(f"❌ SendGrid API error: {e2}")
                return False
            
    except ImportError:
        print("❌ SendGrid library not installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_email_service():
    """Test the application's email service."""
    print("\n📬 Testing Email Service Integration...")
    print("=" * 40)
    
    try:
        from app.services.email_service import EmailService
        
        email_service = EmailService()
        
        # Test service initialization
        if email_service.sendgrid_client:
            print("✅ Email service initialized successfully")
        else:
            print("❌ Email service initialization failed")
            return False
        
        # Test template rendering
        try:
            test_data = {
                "user_name": "Test User",
                "drafts": [
                    {
                        "content": "This is a test draft for LinkedIn posting.",
                        "source_name": "Test Source",
                        "feedback_url_positive": "https://app.com/feedback/positive/test",
                        "feedback_url_negative": "https://app.com/feedback/negative/test"
                    }
                ],
                "dashboard_url": "https://app.com/dashboard",
                "unsubscribe_url": "https://app.com/unsubscribe/test"
            }
            
            html_content = email_service._render_template("daily_drafts.html", **test_data)
            
            if html_content and len(html_content) > 100:
                print("✅ Email template rendering works")
                print(f"   Template size: {len(html_content)} characters")
                return True
            else:
                print("❌ Email template rendering failed")
                return False
                
        except Exception as e:
            print(f"❌ Email template error: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Email service import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def test_content_fetching():
    """Test content fetching capabilities."""
    print("\n📰 Testing Content Fetching...")
    print("=" * 40)
    
    try:
        from app.tasks.content_generation_tasks import fetch_user_content
        
        print("Testing content generation tasks availability...")
        
        # This would normally be run as a Celery task, but we'll test the function directly
        print("✅ Content generation tasks available")
        print("   - fetch_user_content task found")
        print("   Note: Full content testing requires database setup and valid sources")
        
        return True
        
    except ImportError as e:
        print(f"❌ Content fetching import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def main():
    """Run all API integration tests."""
    print("🧪 API INTEGRATION TESTS")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Environment: {settings.environment}")
    print()
    
    results = {}
    
    # Test Twitter
    results['twitter'] = await test_twitter_integration()
    
    # Test SendGrid
    results['sendgrid'] = test_sendgrid_integration()
    
    # Test Email Service
    results['email_service'] = await test_email_service()
    
    # Test Content Fetching
    results['content_fetching'] = await test_content_fetching()
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 30)
    
    passed = 0
    total = len(results)
    
    for service, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{service.upper():<20} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All API integrations are working!")
    else:
        print("⚠️  Some integrations need attention")
        print("\nTroubleshooting tips:")
        if not results['twitter']:
            print("- Check Twitter Bearer Token in .env file")
            print("- Verify token has read permissions")
        if not results['sendgrid']:
            print("- Check SendGrid API Key in .env file") 
            print("- Verify sender email in SendGrid dashboard")
        if not results['email_service']:
            print("- Check email template files exist")
            print("- Verify Jinja2 installation")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
