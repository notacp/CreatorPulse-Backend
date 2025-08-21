#!/usr/bin/env python3
"""
Test Supabase Auth configuration and signup flow.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from dotenv import load_dotenv
load_dotenv()

def test_supabase_auth_detailed():
    """Test Supabase Auth with detailed error reporting."""
    print("🔍 Testing Supabase Auth Configuration")
    print("=" * 50)
    
    try:
        from app.core.supabase import get_supabase
        import os
        
        # Show configuration
        print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
        print(f"SUPABASE_KEY: {os.getenv('SUPABASE_KEY')[:20]}...")
        print(f"SUPABASE_SERVICE_KEY: {os.getenv('SUPABASE_SERVICE_KEY')[:20]}...")
        print()
        
        supabase = get_supabase()
        
        # Test different email formats
        test_emails = [
            "testuser@gmail.com",
            "user123@test.com", 
            "demo@example.org",
            "auth-test@protonmail.com"
        ]
        
        for email in test_emails:
            print(f"Testing email: {email}")
            try:
                response = supabase.auth.sign_up({
                    "email": email,
                    "password": "TestPassword123!"
                })
                
                if response.user:
                    print(f"  ✅ Signup successful! User ID: {response.user.id}")
                    
                    # Try to sign in
                    signin_response = supabase.auth.sign_in_with_password({
                        "email": email,
                        "password": "TestPassword123!"
                    })
                    
                    if signin_response.user:
                        print(f"  ✅ Signin successful!")
                        return True
                    else:
                        print(f"  ❌ Signin failed")
                        
                elif response.session:
                    print(f"  ✅ Signup successful with session!")
                    return True
                else:
                    print(f"  ❌ Signup failed - no user or session returned")
                    print(f"  Response: {response}")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"  ❌ Error: {error_msg}")
                
                # Check for common issues
                if "Email address" in error_msg and "invalid" in error_msg:
                    print("    💡 Supabase considers this email format invalid")
                elif "User already registered" in error_msg:
                    print("    💡 User already exists, trying signin...")
                    try:
                        signin_response = supabase.auth.sign_in_with_password({
                            "email": email,
                            "password": "TestPassword123!"
                        })
                        if signin_response.user:
                            print("    ✅ Signin with existing user successful!")
                            return True
                    except Exception as signin_e:
                        print(f"    ❌ Signin also failed: {signin_e}")
                elif "signup is disabled" in error_msg.lower():
                    print("    💡 Signup is disabled in Supabase settings")
                elif "email domain" in error_msg.lower():
                    print("    💡 Email domain may be restricted")
                elif "weak password" in error_msg.lower():
                    print("    💡 Password too weak")
                
            print()
        
        print("❌ All email formats failed")
        return False
        
    except Exception as e:
        print(f"❌ Supabase Auth setup failed: {e}")
        return False

def check_supabase_settings():
    """Check Supabase project settings."""
    print("🔍 Checking Supabase Settings")
    print("=" * 30)
    
    print("To fix Supabase Auth issues:")
    print("1. Go to your Supabase Dashboard")
    print("2. Navigate to Authentication → Settings")
    print("3. Check these settings:")
    print("   ✓ Enable email confirmations: Can be OFF for testing")
    print("   ✓ Enable email signup: Must be ON")
    print("   ✓ Site URL: Should include your domain")
    print("   ✓ Email authentication: Must be enabled")
    print("4. In Authentication → Providers:")
    print("   ✓ Email provider: Must be enabled")
    print("5. Check if you have any domain restrictions")
    print()

if __name__ == "__main__":
    check_supabase_settings()
    success = test_supabase_auth_detailed()
    
    if not success:
        print("\n🔧 Troubleshooting Steps:")
        print("1. Check Supabase Dashboard → Authentication → Settings")
        print("2. Ensure 'Enable email signup' is ON")
        print("3. Try disabling 'Enable email confirmations' for testing")
        print("4. Check if email domains are restricted")
        print("5. Verify your Supabase project is not paused")
        print("\n💡 You can also test auth directly in Supabase Dashboard")
        sys.exit(1)
    else:
        print("\n🎉 Supabase Auth is working!")
        print("You can now test the API endpoints successfully.")
