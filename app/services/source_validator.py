"""
Source validation and health checking service.
"""
import asyncio
import re
import time
from typing import Optional
from urllib.parse import urlparse
import httpx
import feedparser
from datetime import datetime

from app.schemas.source import SourceValidationResult, SourceHealthCheck
from app.core.logging import get_logger

logger = get_logger(__name__)


class SourceValidator:
    """Service for validating and health checking sources."""
    
    def __init__(self):
        self.timeout = 10.0  # 10 second timeout
        self.user_agent = "CreatorPulse/1.0 (Content Aggregator)"
    
    async def validate_source(self, url: str, source_type: str) -> SourceValidationResult:
        """
        Validate a source URL and return validation result.
        
        Args:
            url: The source URL or Twitter handle
            source_type: Either 'rss' or 'twitter'
            
        Returns:
            SourceValidationResult with validation status and suggested name
        """
        try:
            if source_type == "twitter":
                return await self._validate_twitter_handle(url)
            elif source_type == "rss":
                return await self._validate_rss_feed(url)
            else:
                return SourceValidationResult(
                    is_valid=False,
                    error_message=f"Unknown source type: {source_type}"
                )
                
        except Exception as e:
            logger.error(f"Error validating source {url}: {e}")
            return SourceValidationResult(
                is_valid=False,
                error_message=f"Validation error: {str(e)}"
            )
    
    async def _validate_twitter_handle(self, handle: str) -> SourceValidationResult:
        """Validate a Twitter handle."""
        # Clean the handle
        if handle.startswith('@'):
            handle = handle[1:]
        
        # Validate format
        if not re.match(r'^[a-zA-Z0-9_]{1,15}$', handle):
            return SourceValidationResult(
                is_valid=False,
                error_message="Invalid Twitter handle format. Must be 1-15 characters, letters, numbers, and underscores only."
            )
        
        # For now, we'll assume the handle is valid if it meets format requirements
        # In a production system, you might want to check if the account exists via Twitter API
        return SourceValidationResult(
            is_valid=True,
            suggested_name=f"@{handle}"
        )
    
    async def _validate_rss_feed(self, url: str) -> SourceValidationResult:
        """Validate an RSS feed URL."""
        # Basic URL format validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return SourceValidationResult(
                    is_valid=False,
                    error_message="Invalid URL format"
                )
            
            if parsed.scheme not in ('http', 'https'):
                return SourceValidationResult(
                    is_valid=False,
                    error_message="URL must use HTTP or HTTPS protocol"
                )
        except Exception:
            return SourceValidationResult(
                is_valid=False,
                error_message="Invalid URL format"
            )
        
        # Try to fetch and parse the RSS feed
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent}
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Parse the feed
                feed = feedparser.parse(response.content)
                
                if feed.bozo and feed.bozo_exception:
                    # Feed has parsing errors
                    return SourceValidationResult(
                        is_valid=False,
                        error_message=f"Invalid RSS feed format: {feed.bozo_exception}"
                    )
                
                if not hasattr(feed, 'feed') or not feed.feed:
                    return SourceValidationResult(
                        is_valid=False,
                        error_message="No valid RSS feed found at this URL"
                    )
                
                # Extract suggested name
                suggested_name = getattr(feed.feed, 'title', None) or parsed.netloc
                
                return SourceValidationResult(
                    is_valid=True,
                    suggested_name=suggested_name
                )
                
        except httpx.TimeoutException:
            return SourceValidationResult(
                is_valid=False,
                error_message="Request timed out - feed may be slow or unavailable"
            )
        except httpx.HTTPStatusError as e:
            return SourceValidationResult(
                is_valid=False,
                error_message=f"HTTP error {e.response.status_code}: {e.response.reason_phrase}"
            )
        except Exception as e:
            return SourceValidationResult(
                is_valid=False,
                error_message=f"Unable to access feed: {str(e)}"
            )
    
    async def check_source_health(self, url: str, source_type: str) -> SourceHealthCheck:
        """
        Check the health of a source.
        
        Args:
            url: The source URL or Twitter handle
            source_type: Either 'rss' or 'twitter'
            
        Returns:
            SourceHealthCheck with health status and metrics
        """
        try:
            if source_type == "twitter":
                return await self._check_twitter_health(url)
            elif source_type == "rss":
                return await self._check_rss_health(url)
            else:
                return SourceHealthCheck(
                    is_healthy=False,
                    error_message=f"Unknown source type: {source_type}"
                )
                
        except Exception as e:
            logger.error(f"Error checking source health {url}: {e}")
            return SourceHealthCheck(
                is_healthy=False,
                error_message=f"Health check error: {str(e)}"
            )
    
    async def _check_twitter_health(self, handle: str) -> SourceHealthCheck:
        """Check Twitter handle health."""
        # For now, we'll assume Twitter handles are healthy if they're valid format
        # In production, you'd use Twitter API to check if account exists and is accessible
        if handle.startswith('@'):
            handle = handle[1:]
        
        if re.match(r'^[a-zA-Z0-9_]{1,15}$', handle):
            return SourceHealthCheck(
                is_healthy=True,
                response_time_ms=100,  # Mock response time
                content_count=None  # Would need Twitter API to get actual count
            )
        else:
            return SourceHealthCheck(
                is_healthy=False,
                error_message="Invalid Twitter handle format"
            )
    
    async def _check_rss_health(self, url: str) -> SourceHealthCheck:
        """Check RSS feed health."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={'User-Agent': self.user_agent}
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                response_time_ms = int((time.time() - start_time) * 1000)
                
                # Parse the feed
                feed = feedparser.parse(response.content)
                
                if feed.bozo and feed.bozo_exception:
                    return SourceHealthCheck(
                        is_healthy=False,
                        error_message=f"Feed parsing error: {feed.bozo_exception}",
                        response_time_ms=response_time_ms
                    )
                
                # Count entries and get last content date
                content_count = len(feed.entries) if hasattr(feed, 'entries') else 0
                last_content_date = None
                
                if feed.entries:
                    # Get the most recent entry date
                    try:
                        latest_entry = feed.entries[0]
                        if hasattr(latest_entry, 'published_parsed') and latest_entry.published_parsed:
                            last_content_date = datetime(*latest_entry.published_parsed[:6])
                        elif hasattr(latest_entry, 'updated_parsed') and latest_entry.updated_parsed:
                            last_content_date = datetime(*latest_entry.updated_parsed[:6])
                    except Exception:
                        pass  # Ignore date parsing errors
                
                return SourceHealthCheck(
                    is_healthy=True,
                    response_time_ms=response_time_ms,
                    content_count=content_count,
                    last_content_date=last_content_date
                )
                
        except httpx.TimeoutException:
            response_time_ms = int((time.time() - start_time) * 1000)
            return SourceHealthCheck(
                is_healthy=False,
                error_message="Request timed out",
                response_time_ms=response_time_ms
            )
        except httpx.HTTPStatusError as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return SourceHealthCheck(
                is_healthy=False,
                error_message=f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
                response_time_ms=response_time_ms
            )
        except Exception as e:
            response_time_ms = int((time.time() - start_time) * 1000)
            return SourceHealthCheck(
                is_healthy=False,
                error_message=f"Connection error: {str(e)}",
                response_time_ms=response_time_ms
            )
