"""
Supabase-native source management endpoints.
This version uses Supabase API directly instead of SQLAlchemy ORM.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from app.core.exceptions import ValidationException
from app.models.user import User
from app.schemas.source import (
    SourceCreate,
    SourceUpdate, 
    Source as SourceSchema,
    SourceStatus
)
from app.schemas.common import ApiResponse
from app.api.v1.endpoints.auth import get_current_user
from app.core.logging import get_logger
from app.core.supabase import get_supabase
from app.services.source_validator import SourceValidator

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=ApiResponse[List[SourceSchema]])
async def get_sources(
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Get all sources for the current user using Supabase API."""
    try:
        # Use Supabase API directly with RLS (Row Level Security)
        # RLS ensures users only see their own sources
        response = supabase.table('sources').select('*').execute()
        
        if response.data is None:
            logger.warning("Supabase returned null data for sources query")
            sources_data = []
        else:
            sources_data = response.data
        
        # Convert to schemas
        sources = []
        for source_data in sources_data:
            # Convert string timestamps to datetime objects
            source_data['created_at'] = datetime.fromisoformat(source_data['created_at'].replace('Z', '+00:00'))
            if source_data.get('updated_at'):
                source_data['updated_at'] = datetime.fromisoformat(source_data['updated_at'].replace('Z', '+00:00'))
            if source_data.get('last_checked'):
                source_data['last_checked'] = datetime.fromisoformat(source_data['last_checked'].replace('Z', '+00:00'))
            
            sources.append(SourceSchema(**source_data))
        
        logger.info(f"Retrieved {len(sources)} sources for user {current_user.email} via Supabase")
        
        return ApiResponse(
            success=True,
            data=sources
        )
        
    except Exception as e:
        logger.error(f"Error retrieving sources from Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sources"
        )


@router.post("/", response_model=ApiResponse[SourceSchema])
async def create_source(
    source_data: SourceCreate,
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Create a new source using Supabase API."""
    try:
        # Validate the source URL
        validator = SourceValidator()
        validation_result = await validator.validate_source(source_data.url, source_data.type)
        
        if not validation_result.is_valid:
            raise ValidationException(f"Invalid source: {validation_result.error_message}")
        
        # Prepare source data for insertion
        insert_data = {
            "user_id": str(current_user.id),
            "type": source_data.type,
            "url": source_data.url,
            "name": source_data.name or validation_result.suggested_name,
            "active": source_data.active,
            "error_count": 0
        }
        
        # Insert using Supabase API
        # RLS ensures the user_id is automatically validated
        response = supabase.table('sources').insert(insert_data).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create source - no data returned"
            )
        
        source_result = response.data[0]
        
        # Convert timestamps
        source_result['created_at'] = datetime.fromisoformat(source_result['created_at'].replace('Z', '+00:00'))
        if source_result.get('updated_at'):
            source_result['updated_at'] = datetime.fromisoformat(source_result['updated_at'].replace('Z', '+00:00'))
        
        source_schema = SourceSchema(**source_result)
        
        logger.info(f"Created source {source_schema.name} for user {current_user.email} via Supabase")
        
        return ApiResponse(
            success=True,
            data=source_schema,
            message="Source added successfully"
        )
        
    except ValidationException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating source in Supabase: {e}")
        
        # Check for unique constraint violation
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise ValidationException("This source is already added to your account")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create source"
        )


@router.get("/{source_id}", response_model=ApiResponse[SourceSchema])
async def get_source(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Get a specific source by ID using Supabase API."""
    try:
        # Use Supabase API with RLS - user can only access their own sources
        response = supabase.table('sources').select('*').eq('id', str(source_id)).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        source_data = response.data[0]
        
        # Convert timestamps
        source_data['created_at'] = datetime.fromisoformat(source_data['created_at'].replace('Z', '+00:00'))
        if source_data.get('updated_at'):
            source_data['updated_at'] = datetime.fromisoformat(source_data['updated_at'].replace('Z', '+00:00'))
        if source_data.get('last_checked'):
            source_data['last_checked'] = datetime.fromisoformat(source_data['last_checked'].replace('Z', '+00:00'))
        
        source_schema = SourceSchema(**source_data)
        
        return ApiResponse(
            success=True,
            data=source_schema
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving source {source_id} from Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve source"
        )


@router.put("/{source_id}", response_model=ApiResponse[SourceSchema])
async def update_source(
    source_id: UUID,
    source_data: SourceUpdate,
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Update a source using Supabase API."""
    try:
        # Validate new URL if provided
        if source_data.url and source_data.type:
            validator = SourceValidator()
            validation_result = await validator.validate_source(source_data.url, source_data.type)
            
            if not validation_result.is_valid:
                raise ValidationException(f"Invalid source URL: {validation_result.error_message}")
        
        # Prepare update data (only include non-None fields)
        update_data = {}
        if source_data.name is not None:
            update_data["name"] = source_data.name
        if source_data.url is not None:
            update_data["url"] = source_data.url
        if source_data.active is not None:
            update_data["active"] = source_data.active
        if source_data.type is not None:
            update_data["type"] = source_data.type
        
        if not update_data:
            # No fields to update
            return await get_source(source_id, current_user, supabase)
        
        # Update using Supabase API with RLS
        response = supabase.table('sources').update(update_data).eq('id', str(source_id)).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        source_result = response.data[0]
        
        # Convert timestamps
        source_result['created_at'] = datetime.fromisoformat(source_result['created_at'].replace('Z', '+00:00'))
        if source_result.get('updated_at'):
            source_result['updated_at'] = datetime.fromisoformat(source_result['updated_at'].replace('Z', '+00:00'))
        if source_result.get('last_checked'):
            source_result['last_checked'] = datetime.fromisoformat(source_result['last_checked'].replace('Z', '+00:00'))
        
        source_schema = SourceSchema(**source_result)
        
        logger.info(f"Updated source {source_schema.name} for user {current_user.email} via Supabase")
        
        return ApiResponse(
            success=True,
            data=source_schema,
            message="Source updated successfully"
        )
        
    except ValidationException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating source {source_id} in Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update source"
        )


@router.delete("/{source_id}", response_model=ApiResponse[dict])
async def delete_source(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Delete a source using Supabase API."""
    try:
        # Delete using Supabase API with RLS
        response = supabase.table('sources').delete().eq('id', str(source_id)).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        deleted_source = response.data[0]
        
        logger.info(f"Deleted source {deleted_source.get('name', source_id)} for user {current_user.email} via Supabase")
        
        return ApiResponse(
            success=True,
            data={"deleted": True, "id": str(source_id)},
            message="Source deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source {source_id} from Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete source"
        )


@router.get("/{source_id}/status", response_model=ApiResponse[SourceStatus])
async def get_source_status(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Get the health status of a specific source."""
    try:
        # Get source using Supabase API
        response = supabase.table('sources').select('*').eq('id', str(source_id)).execute()
        
        if not response.data or len(response.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        source_data = response.data[0]
        
        # Check source health
        validator = SourceValidator()
        health_check = await validator.check_source_health(source_data['url'], source_data['type'])
        
        status_data = SourceStatus(
            source_id=source_id,
            is_healthy=health_check.is_healthy,
            last_checked=datetime.utcnow(),
            error_message=health_check.error_message,
            response_time_ms=health_check.response_time_ms,
            content_count=health_check.content_count
        )
        
        # Update source status in Supabase
        update_data = {
            "last_checked": datetime.utcnow().isoformat(),
        }
        
        if health_check.is_healthy:
            # Reset error count on successful check
            update_data["error_count"] = 0
            update_data["last_error"] = None
        else:
            # Increment error count
            update_data["error_count"] = source_data['error_count'] + 1
            if health_check.error_message:
                update_data["last_error"] = health_check.error_message
        
        supabase.table('sources').update(update_data).eq('id', str(source_id)).execute()
        
        return ApiResponse(
            success=True,
            data=status_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking source status {source_id} in Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check source status"
        )


@router.post("/{source_id}/check", response_model=ApiResponse[SourceStatus])
async def trigger_source_check(
    source_id: UUID,
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Manually trigger a health check for a source."""
    # This endpoint reuses the same logic as get_source_status
    # but is semantically different (POST vs GET)
    return await get_source_status(source_id, current_user, supabase)


# Additional Supabase-specific endpoints

@router.get("/stats/summary", response_model=ApiResponse[dict])
async def get_sources_summary(
    current_user: User = Depends(get_current_user),
    supabase: Client = Depends(get_supabase)
):
    """Get sources summary statistics using Supabase."""
    try:
        # Get all sources for the user
        response = supabase.table('sources').select('*').execute()
        
        sources = response.data or []
        
        # Calculate statistics
        total_sources = len(sources)
        active_sources = len([s for s in sources if s.get('active', True)])
        rss_sources = len([s for s in sources if s.get('type') == 'rss'])
        twitter_sources = len([s for s in sources if s.get('type') == 'twitter'])
        sources_with_errors = len([s for s in sources if s.get('error_count', 0) > 0])
        
        summary = {
            "total_sources": total_sources,
            "active_sources": active_sources,
            "inactive_sources": total_sources - active_sources,
            "rss_sources": rss_sources,
            "twitter_sources": twitter_sources,
            "sources_with_errors": sources_with_errors,
            "healthy_sources": active_sources - sources_with_errors
        }
        
        logger.info(f"Retrieved sources summary for user {current_user.email}: {summary}")
        
        return ApiResponse(
            success=True,
            data=summary
        )
        
    except Exception as e:
        logger.error(f"Error getting sources summary from Supabase: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sources summary"
        )
