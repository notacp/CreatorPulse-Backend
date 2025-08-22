"""
API v1 router configuration.
"""
from fastapi import APIRouter

# Import endpoint routers
from .endpoints import auth, style, drafts, feedback
from .endpoints import sources_supabase as sources

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(style.router, prefix="/style", tags=["style-training"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["draft-generation"])
api_router.include_router(feedback.router, tags=["feedback"])

# Placeholder for future routers
# api_router.include_router(users.router, prefix="/user", tags=["user-settings"])


@api_router.get("/")
async def api_info():
    """API v1 information endpoint."""
    return {
        "message": "CreatorPulse API v1",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/v1/auth",
            "sources": "/v1/sources", 
            "style": "/v1/style",
            "drafts": "/v1/drafts",
            "user": "/v1/user",
            "feedback": "/v1/feedback",
        }
    }