"""
Test script to verify the exact imports that were failing in Render.
"""

def test_pgvector_import():
    """Test pgvector import that was failing."""
    print("🔍 Testing pgvector import...")
    try:
        from pgvector.sqlalchemy import Vector
        print("✅ pgvector.sqlalchemy.Vector imported successfully")
        return True
    except ImportError as e:
        print(f"❌ pgvector import failed: {e}")
        return False

def test_style_models():
    """Test style models import."""
    print("🔍 Testing style models import...")
    try:
        from app.models.style import UserStylePost, StyleVector
        print("✅ Style models imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Style models import failed: {e}")
        return False

def test_models_init():
    """Test models __init__ import."""
    print("🔍 Testing models __init__ import...")
    try:
        from app.models import UserStylePost, StyleVector
        print("✅ Models __init__ imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Models __init__ import failed: {e}")
        return False

def test_auth_endpoint():
    """Test auth endpoint import."""
    print("🔍 Testing auth endpoint import...")
    try:
        from app.api.v1.endpoints.auth import router
        print("✅ Auth endpoint imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Auth endpoint import failed: {e}")
        return False

def test_api_router():
    """Test API router import."""
    print("🔍 Testing API router import...")
    try:
        from app.api.v1.api import api_router
        print("✅ API router imported successfully")
        return True
    except ImportError as e:
        print(f"❌ API router import failed: {e}")
        return False

def test_main_app():
    """Test main app import."""
    print("🔍 Testing main app import...")
    try:
        from app.main import app
        print("✅ Main app imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Main app import failed: {e}")
        return False

def main():
    """Run all import tests."""
    print("🧪 RENDER IMPORT TESTS")
    print("=" * 30)
    print("Testing the exact import path that failed in Render:")
    print("File \"/app/app/models/style.py\", line 8")
    print("from pgvector.sqlalchemy import Vector")
    print("=" * 30)
    print()
    
    tests = [
        ("pgvector import", test_pgvector_import),
        ("style models", test_style_models),
        ("models __init__", test_models_init),
        ("auth endpoint", test_auth_endpoint),
        ("API router", test_api_router),
        ("main app", test_main_app),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("📊 TEST SUMMARY")
    print("=" * 20)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All imports working! Ready for Render deployment.")
    else:
        print("⚠️  Some imports failed. Check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
