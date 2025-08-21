"""
Content fetching service for RSS feeds and external sources.

This service handles fetching content from various sources like RSS feeds and Twitter,
with comprehensive error handling, content extraction, and deduplication logic.
"""

import asyncio
import hashlib
import logging
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
import aiohttp
import feedparser
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import CreatorPulseException
from app.models.source import Source
from app.models.source_content import SourceContent
from app.models.user import User
from app.services.source_validator import SourceValidator

logger = logging.getLogger(__name__)


class ContentFetcher:
    """Service for fetching and processing content from external sources."""
    
    def __init__(self):
        """Initialize the content fetcher."""
        self.source_validator = SourceValidator()
        self.session_timeout = aiohttp.ClientTimeout(total=30, connect=10)
        
    async def fetch_rss_feed(
        self, 
        url: str, 
        max_items: int = 20,
        since_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Fetch and parse RSS feed content.
        
        Args:
            url: RSS feed URL
            max_items: Maximum number of items to fetch
            since_hours: Only fetch items from the last N hours
            
        Returns:
            List of parsed content items
        """
        try:
            logger.info(f"Fetching RSS feed: {url}")
            
            # Fetch RSS content
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {response.reason}")
                    
                    feed_content = await response.text()
            
            # Parse RSS feed
            feed = feedparser.parse(feed_content)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"RSS feed parsing warning for {url}: {feed.bozo_exception}")
            
            # Extract feed metadata
            feed_title = getattr(feed.feed, 'title', 'Unknown Feed')
            feed_description = getattr(feed.feed, 'description', '')
            
            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(hours=since_hours)
            
            # Process feed entries
            content_items = []
            for entry in feed.entries[:max_items]:
                try:
                    # Extract entry data
                    title = getattr(entry, 'title', '')
                    description = getattr(entry, 'description', '') or getattr(entry, 'summary', '')
                    link = getattr(entry, 'link', '')
                    author = getattr(entry, 'author', '')
                    
                    # Parse publication date
                    pub_date = self._parse_entry_date(entry)
                    
                    # Skip old entries
                    if pub_date and pub_date < cutoff_time:
                        continue
                    
                    # Clean and extract content
                    clean_content = self._clean_html_content(description)
                    
                    # Skip if content is too short or empty
                    if not clean_content or len(clean_content.strip()) < 50:
                        continue
                    
                    # Create content hash for deduplication
                    content_hash = self._generate_content_hash(title, clean_content, link)
                    
                    content_item = {
                        'title': title.strip(),
                        'content': clean_content.strip(),
                        'url': link.strip(),
                        'author': author.strip(),
                        'published_at': pub_date or datetime.utcnow(),
                        'source_type': 'rss',
                        'source_name': feed_title,
                        'content_hash': content_hash,
                        'metadata': {
                            'feed_title': feed_title,
                            'feed_description': feed_description,
                            'original_description': description[:500] if description else None,
                            'word_count': len(clean_content.split()),
                            'character_count': len(clean_content)
                        }
                    }
                    
                    content_items.append(content_item)
                    
                except Exception as e:
                    logger.warning(f"Error processing RSS entry: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(content_items)} items from RSS feed: {url}")
            return content_items
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            raise CreatorPulseException(f"Failed to fetch RSS feed: {str(e)}")
    
    async def fetch_twitter_content(
        self, 
        handle: str, 
        max_tweets: int = 20,
        since_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent tweets from a Twitter handle.
        
        Args:
            handle: Twitter handle (without @)
            max_tweets: Maximum number of tweets to fetch
            since_hours: Only fetch tweets from the last N hours
            
        Returns:
            List of parsed tweet content
        """
        try:
            if not settings.twitter_bearer_token:
                logger.warning("Twitter Bearer Token not configured")
                return []
            
            logger.info(f"Fetching Twitter content for: @{handle}")
            
            # Clean handle
            handle = handle.lstrip('@').strip()
            
            # Calculate time window
            since_time = datetime.utcnow() - timedelta(hours=since_hours)
            since_iso = since_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # Twitter API v2 endpoint
            url = f"https://api.twitter.com/2/users/by/username/{handle}"
            user_fields = "created_at,description,public_metrics,verified"
            
            headers = {
                'Authorization': f'Bearer {settings.twitter_bearer_token}',
                'Content-Type': 'application/json'
            }
            
            # First, get user info
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # Get user ID
                async with session.get(
                    url, 
                    headers=headers,
                    params={'user.fields': user_fields}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Twitter API error {response.status}: {error_text}")
                    
                    user_data = await response.json()
                    
                    if 'errors' in user_data:
                        raise Exception(f"Twitter API errors: {user_data['errors']}")
                    
                    user_id = user_data['data']['id']
                    user_info = user_data['data']
                
                # Get user tweets
                tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
                tweet_fields = "created_at,public_metrics,context_annotations,entities,referenced_tweets"
                
                params = {
                    'max_results': min(max_tweets, 100),  # Twitter API limit
                    'tweet.fields': tweet_fields,
                    'start_time': since_iso,
                    'exclude': 'retweets,replies'  # Focus on original content
                }
                
                async with session.get(
                    tweets_url,
                    headers=headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Twitter tweets API error {response.status}: {error_text}")
                    
                    tweets_data = await response.json()
                    
                    if 'errors' in tweets_data:
                        logger.warning(f"Twitter API warnings: {tweets_data['errors']}")
                    
                    if 'data' not in tweets_data:
                        logger.info(f"No recent tweets found for @{handle}")
                        return []
            
            # Process tweets
            content_items = []
            tweets = tweets_data.get('data', [])
            
            for tweet in tweets:
                try:
                    text = tweet.get('text', '')
                    created_at = tweet.get('created_at')
                    tweet_id = tweet.get('id')
                    
                    # Parse creation date
                    pub_date = None
                    if created_at:
                        pub_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).replace(tzinfo=None)
                    
                    # Clean tweet text
                    clean_text = self._clean_tweet_text(text)
                    
                    # Skip if text is too short
                    if not clean_text or len(clean_text.strip()) < 30:
                        continue
                    
                    # Create content hash
                    content_hash = self._generate_content_hash(
                        f"Tweet by @{handle}", 
                        clean_text, 
                        f"https://twitter.com/{handle}/status/{tweet_id}"
                    )
                    
                    # Extract metrics
                    metrics = tweet.get('public_metrics', {})
                    
                    content_item = {
                        'title': f"Tweet by @{handle}",
                        'content': clean_text.strip(),
                        'url': f"https://twitter.com/{handle}/status/{tweet_id}",
                        'author': f"@{handle}",
                        'published_at': pub_date or datetime.utcnow(),
                        'source_type': 'twitter',
                        'source_name': f"@{handle}",
                        'content_hash': content_hash,
                        'metadata': {
                            'tweet_id': tweet_id,
                            'user_info': user_info,
                            'metrics': metrics,
                            'original_text': text,
                            'word_count': len(clean_text.split()),
                            'character_count': len(clean_text)
                        }
                    }
                    
                    content_items.append(content_item)
                    
                except Exception as e:
                    logger.warning(f"Error processing tweet: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(content_items)} tweets from @{handle}")
            return content_items
            
        except Exception as e:
            logger.error(f"Error fetching Twitter content for @{handle}: {e}")
            raise CreatorPulseException(f"Failed to fetch Twitter content: {str(e)}")
    
    async def fetch_source_content(
        self, 
        session: AsyncSession, 
        source: Source,
        max_items: int = 20,
        since_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Fetch content from a specific source.
        
        Args:
            session: Database session
            source: Source object to fetch content from
            max_items: Maximum number of items to fetch
            since_hours: Only fetch items from the last N hours
            
        Returns:
            List of content items
        """
        try:
            if not source.active:
                logger.info(f"Skipping inactive source: {source.name}")
                return []
            
            content_items = []
            
            if source.type == 'rss':
                content_items = await self.fetch_rss_feed(
                    source.url, 
                    max_items=max_items,
                    since_hours=since_hours
                )
            elif source.type == 'twitter':
                # Extract handle from URL or use name
                handle = self._extract_twitter_handle(source.url) or source.name
                content_items = await self.fetch_twitter_content(
                    handle,
                    max_tweets=max_items,
                    since_hours=since_hours
                )
            else:
                logger.warning(f"Unsupported source type: {source.type}")
                return []
            
            # Update source last_checked timestamp
            source.last_checked = datetime.utcnow()
            source.error_count = 0  # Reset error count on success
            source.last_error = None
            
            await session.commit()
            
            return content_items
            
        except Exception as e:
            # Update source error information
            source.last_checked = datetime.utcnow()
            source.error_count = (source.error_count or 0) + 1
            source.last_error = str(e)[:500]  # Truncate error message
            
            await session.commit()
            
            logger.error(f"Error fetching content from source {source.name}: {e}")
            raise
    
    async def fetch_all_user_content(
        self, 
        session: AsyncSession, 
        user_id: str,
        max_items_per_source: int = 20,
        since_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Fetch content from all active sources for a user.
        
        Args:
            session: Database session
            user_id: User ID
            max_items_per_source: Maximum items per source
            since_hours: Only fetch items from the last N hours
            
        Returns:
            List of all content items from all sources
        """
        try:
            # Get user's active sources
            result = await session.execute(
                select(Source)
                .where(
                    and_(
                        Source.user_id == (uuid.UUID(user_id) if isinstance(user_id, str) else user_id),
                        Source.active == True
                    )
                )
                .order_by(Source.created_at)
            )
            sources = result.scalars().all()
            
            if not sources:
                logger.info(f"No active sources found for user {user_id}")
                return []
            
            logger.info(f"Fetching content from {len(sources)} sources for user {user_id}")
            
            # Fetch content from all sources concurrently
            tasks = [
                self.fetch_source_content(
                    session, 
                    source, 
                    max_items=max_items_per_source,
                    since_hours=since_hours
                )
                for source in sources
            ]
            
            # Execute all tasks with error handling
            all_content = []
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                source = sources[i]
                if isinstance(result, Exception):
                    logger.error(f"Failed to fetch content from source {source.name}: {result}")
                    continue
                else:
                    # Add source information to each content item
                    for item in result:
                        item['source_id'] = str(source.id)
                        item['source_name'] = source.name
                        item['source_type'] = source.type
                    all_content.extend(result)
            
            # Sort by publication date (newest first)
            all_content.sort(key=lambda x: x['published_at'], reverse=True)
            
            logger.info(f"Successfully fetched {len(all_content)} total content items for user {user_id}")
            
            return all_content
            
        except Exception as e:
            logger.error(f"Error fetching content for user {user_id}: {e}")
            raise CreatorPulseException(f"Failed to fetch user content: {str(e)}")
    
    async def deduplicate_content(
        self, 
        session: AsyncSession, 
        content_items: List[Dict[str, Any]],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Remove duplicate content items based on content hash and existing database records.
        
        Args:
            session: Database session
            content_items: List of content items to deduplicate
            user_id: User ID for database queries
            
        Returns:
            List of unique content items
        """
        try:
            if not content_items:
                return []
            
            # Extract content hashes
            content_hashes = [item['content_hash'] for item in content_items]
            
            # Check for existing content in database
            from app.models.source import Source
            result = await session.execute(
                select(SourceContent.content_hash)
                .join(Source, SourceContent.source_id == Source.id)
                .where(
                    and_(
                        Source.user_id == (uuid.UUID(user_id) if isinstance(user_id, str) else user_id),
                        SourceContent.content_hash.in_(content_hashes)
                    )
                )
            )
            existing_hashes = {row[0] for row in result.fetchall()}
            
            # Filter out duplicates
            unique_items = []
            seen_hashes = set()
            
            for item in content_items:
                content_hash = item['content_hash']
                
                # Skip if already in database
                if content_hash in existing_hashes:
                    continue
                
                # Skip if already seen in this batch
                if content_hash in seen_hashes:
                    continue
                
                seen_hashes.add(content_hash)
                unique_items.append(item)
            
            logger.info(
                f"Deduplication: {len(content_items)} items -> {len(unique_items)} unique "
                f"(removed {len(existing_hashes)} existing, {len(content_items) - len(unique_items) - len(existing_hashes)} duplicates)"
            )
            
            return unique_items
            
        except Exception as e:
            logger.error(f"Error deduplicating content: {e}")
            raise CreatorPulseException(f"Failed to deduplicate content: {str(e)}")
    
    def _parse_entry_date(self, entry) -> Optional[datetime]:
        """Parse entry publication date from various possible fields."""
        try:
            # Try different date fields
            date_fields = ['published_parsed', 'updated_parsed']
            
            for field in date_fields:
                if hasattr(entry, field) and getattr(entry, field):
                    time_struct = getattr(entry, field)
                    if time_struct:
                        return datetime(*time_struct[:6])
            
            # Try string fields
            string_fields = ['published', 'updated']
            for field in string_fields:
                if hasattr(entry, field) and getattr(entry, field):
                    date_str = getattr(entry, field)
                    # This is a simple parser, could be enhanced
                    try:
                        # Remove timezone info for simple parsing
                        date_str = re.sub(r'\s*[\+\-]\d{4}$', '', date_str)
                        return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S')
                    except:
                        continue
            
            return None
            
        except Exception:
            return None
    
    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content and extract plain text."""
        if not html_content:
            return ""
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        import html
        clean_text = html.unescape(clean_text)
        
        # Clean up whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text)
        clean_text = clean_text.strip()
        
        return clean_text
    
    def _clean_tweet_text(self, text: str) -> str:
        """Clean tweet text by removing URLs and mentions if desired."""
        if not text:
            return ""
        
        # Remove URLs (optional, might want to keep for context)
        # text = re.sub(r'https?://\S+', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _generate_content_hash(self, title: str, content: str, url: str) -> str:
        """Generate a unique hash for content deduplication."""
        # Combine title, content, and URL for uniqueness
        combined = f"{title}|{content}|{url}".encode('utf-8')
        return hashlib.md5(combined).hexdigest()
    
    def _extract_twitter_handle(self, url: str) -> Optional[str]:
        """Extract Twitter handle from URL."""
        try:
            if not url:
                return None
            
            # Handle various Twitter URL formats
            patterns = [
                r'twitter\.com/([^/\?]+)',
                r'x\.com/([^/\?]+)',
                r'@([a-zA-Z0-9_]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    handle = match.group(1).strip()
                    # Remove @ if present
                    handle = handle.lstrip('@')
                    return handle
            
            return None
            
        except Exception:
            return None


# Global service instance
content_fetcher = ContentFetcher()
