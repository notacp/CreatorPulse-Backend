"""
Source management endpoints.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import ValidationException
from app.models.user import User
from app.models.source import Source
from app.schemas.source import (
    SourceCreate,
    SourceUpdate, 
    Source as SourceSchema,
    SourceStatus
)
from app.schemas.common import ApiResponse
from app.api.v1.endpoints.auth import get_current_user
from app.core.logging import get_logger
from app.services.source_validator import SourceValidator

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=ApiResponse[List[SourceSchema]])
async def get_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all sources for the current user."""
    try:
        result = await db.execute(
            select(Source).where(Source.user_id == current_user.id)
        )
        sources = result.scalars().all()
        
        source_schemas = [SourceSchema.from_orm(source) for source in sources]
        
        logger.info(f"Retrieved {len(sources)} sources for user {current_user.email}")
        
        return ApiResponse(
            success=True,
            data=source_schemas
        )
        
    except Exception as e:
        logger.error(f"Error retrieving sources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sources"
        )


@router.post("/", response_model=ApiResponse[SourceSchema])
async def create_source(
    source_data: SourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new source for the current user."""
    try:
        # Validate the source URL
        validator = SourceValidator()
        validation_result = await validator.validate_source(source_data.url, source_data.type)
        
        if not validation_result.is_valid:
            raise ValidationException(f"Invalid source: {validation_result.error_message}")
        
        # Check if source already exists for this user
        existing_result = await db.execute(
            select(Source).where(
                Source.user_id == current_user.id,
                Source.url == source_data.url
            )
        )
        existing_source = existing_result.scalar_one_or_none()
        
        if existing_source:
            raise ValidationException("This source is already added to your account")
        
        # Create new source
        source = Source(
            user_id=current_user.id,
            type=source_data.type,
            url=source_data.url,
            name=source_data.name or validation_result.suggested_name,
            active=True,
            last_checked=datetime.utcnow(),
            error_count=0
        )
        
        db.add(source)
        await db.commit()
        await db.refresh(source)
        
        logger.info(f"Created source {source.name} for user {current_user.email}")
        
        return ApiResponse(
            success=True,
            data=SourceSchema.from_orm(source),
            message="Source added successfully"
        )
        
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Error creating source: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create source"
        )


@router.get("/{source_id}", response_model=ApiResponse[SourceSchema])
async def get_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific source by ID."""
    try:
        result = await db.execute(
            select(Source).where(
                Source.id == source_id,
                Source.user_id == current_user.id
            )
        )
        source = result.scalar_one_or_none()
        
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        return ApiResponse(
            success=True,
            data=SourceSchema.from_orm(source)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving source {source_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve source"
        )


@router.put("/{source_id}", response_model=ApiResponse[SourceSchema])
async def update_source(
    source_id: UUID,
    source_data: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a source."""
    try:
        # Get existing source
        result = await db.execute(
            select(Source).where(
                Source.id == source_id,
                Source.user_id == current_user.id
            )
        )
        source = result.scalar_one_or_none()
        
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        # Validate new URL if provided
        if source_data.url and source_data.url != source.url:
            validator = SourceValidator()
            validation_result = await validator.validate_source(source_data.url, source_data.type or source.type)
            
            if not validation_result.is_valid:
                raise ValidationException(f"Invalid source URL: {validation_result.error_message}")
        
        # Update source fields
        update_data = {}
        if source_data.name is not None:
            update_data["name"] = source_data.name
        if source_data.url is not None:
            update_data["url"] = source_data.url
        if source_data.active is not None:
            update_data["active"] = source_data.active
        if source_data.type is not None:
            update_data["type"] = source_data.type
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            
            await db.execute(
                update(Source)
                .where(Source.id == source_id)
                .values(**update_data)
            )
            await db.commit()
            await db.refresh(source)
        
        logger.info(f"Updated source {source.name} for user {current_user.email}")
        
        return ApiResponse(
            success=True,
            data=SourceSchema.from_orm(source),
            message="Source updated successfully"
        )
        
    except ValidationException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update source"
        )


@router.delete("/{source_id}", response_model=ApiResponse[dict])
async def delete_source(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a source."""
    try:
        # Check if source exists and belongs to user
        result = await db.execute(
            select(Source).where(
                Source.id == source_id,
                Source.user_id == current_user.id
            )
        )
        source = result.scalar_one_or_none()
        
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        # Delete the source
        await db.execute(delete(Source).where(Source.id == source_id))
        await db.commit()
        
        logger.info(f"Deleted source {source.name} for user {current_user.email}")
        
        return ApiResponse(
            success=True,
            data={"deleted": True},
            message="Source deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source {source_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete source"
        )


@router.get("/{source_id}/status", response_model=ApiResponse[SourceStatus])
async def get_source_status(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the health status of a specific source."""
    try:
        # Get source
        result = await db.execute(
            select(Source).where(
                Source.id == source_id,
                Source.user_id == current_user.id
            )
        )
        source = result.scalar_one_or_none()
        
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source not found"
            )
        
        # Check source health
        validator = SourceValidator()
        health_check = await validator.check_source_health(source.url, source.type)
        
        status_data = SourceStatus(
            source_id=source.id,
            is_healthy=health_check.is_healthy,
            last_checked=datetime.utcnow(),
            error_message=health_check.error_message,
            response_time_ms=health_check.response_time_ms,
            content_count=health_check.content_count
        )
        
        # Update source status in database
        await db.execute(
            update(Source)
            .where(Source.id == source_id)
            .values(
                last_checked=status_data.last_checked,
                error_count=source.error_count + (1 if not health_check.is_healthy else 0)
            )
        )
        await db.commit()
        
        return ApiResponse(
            success=True,
            data=status_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking source status {source_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check source status"
        )


@router.post("/{source_id}/check", response_model=ApiResponse[SourceStatus])
async def trigger_source_check(
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually trigger a health check for a source."""
    # This endpoint reuses the same logic as get_source_status
    # but is semantically different (POST vs GET)
    return await get_source_status(source_id, db, current_user)
