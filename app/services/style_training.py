"""
Style training service for processing user posts and generating embeddings.
"""
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.style import UserStylePost, StyleVector
from app.models.user import User
from app.core.exceptions import CreatorPulseException
from app.utils.validators import validate_style_post_content

logger = logging.getLogger(__name__)


class StyleTrainingService:
    """Service for handling style training operations."""
    
    def __init__(self):
        """Initialize the style training service."""
        self.gemini_model = None
        if settings.gemini_api_key:
            try:
                genai.configure(api_key=settings.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
                logger.info("Gemini API initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini API: {e}")
                self.gemini_model = None
        else:
            logger.warning("GEMINI_API_KEY not configured, style training will be limited")
    
    async def add_style_posts(
        self, 
        session: AsyncSession, 
        user_id: str, 
        posts: List[str]
    ) -> List[UserStylePost]:
        """
        Add multiple style posts for a user.
        
        Args:
            session: Database session
            user_id: User ID
            posts: List of post content strings
            
        Returns:
            List of created style posts
        """
        # Validate user exists
        user = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user.scalar_one_or_none()
        if not user:
            raise CreatorPulseException("User not found", status_code=404)
        
        # Validate and create posts
        style_posts = []
        for content in posts:
            # Validate content
            validation_result = validate_style_post_content(content)
            if not validation_result["valid"]:
                logger.warning(f"Invalid style post content: {validation_result['errors']}")
                continue
            
            # Create style post
            style_post = UserStylePost(
                user_id=user_id,
                content=content,
                word_count=len(content.split()),
                character_count=len(content),
                processed=False
            )
            session.add(style_post)
            style_posts.append(style_post)
        
        # Commit to get IDs
        await session.commit()
        
        # Refresh to get generated IDs
        for post in style_posts:
            await session.refresh(post)
        
        logger.info(f"Added {len(style_posts)} style posts for user {user_id}")
        return style_posts
    
    async def process_style_post(
        self, 
        session: AsyncSession, 
        style_post: UserStylePost
    ) -> Optional[StyleVector]:
        """
        Process a single style post and generate embeddings.
        
        Args:
            session: Database session
            style_post: Style post to process
            
        Returns:
            Created style vector or None if processing failed
        """
        try:
            if not self.gemini_model:
                logger.error("Gemini API not available for style processing")
                return None
            
            # Generate embedding using Gemini
            embedding = await self._generate_embedding(style_post.content)
            if not embedding:
                logger.error(f"Failed to generate embedding for post {style_post.id}")
                return None
            
            # Create style vector
            style_vector = StyleVector(
                user_id=style_post.user_id,
                style_post_id=style_post.id,
                content=style_post.content,
                embedding=embedding
            )
            session.add(style_vector)
            
            # Mark post as processed
            await session.execute(
                update(UserStylePost)
                .where(UserStylePost.id == style_post.id)
                .values(
                    processed=True,
                    processed_at=datetime.utcnow()
                )
            )
            
            await session.commit()
            await session.refresh(style_vector)
            
            logger.info(f"Successfully processed style post {style_post.id}")
            return style_vector
            
        except Exception as e:
            logger.error(f"Error processing style post {style_post.id}: {e}")
            await session.rollback()
            return None
    
    async def process_user_style_posts(
        self, 
        session: AsyncSession, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process all unprocessed style posts for a user.
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            Processing results summary
        """
        # Get unprocessed posts
        unprocessed_posts = await session.execute(
            select(UserStylePost)
            .where(
                UserStylePost.user_id == user_id,
                UserStylePost.processed == False
            )
            .order_by(UserStylePost.created_at)
        )
        unprocessed_posts = unprocessed_posts.scalars().all()
        
        if not unprocessed_posts:
            return {
                "status": "completed",
                "message": "No unprocessed posts found",
                "total_posts": 0,
                "processed_posts": 0,
                "failed_posts": 0
            }
        
        total_posts = len(unprocessed_posts)
        processed_posts = 0
        failed_posts = 0
        
        logger.info(f"Processing {total_posts} style posts for user {user_id}")
        
        # Process posts in batches to avoid overwhelming the API
        batch_size = 5
        for i in range(0, total_posts, batch_size):
            batch = unprocessed_posts[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [
                self.process_style_post(session, post) 
                for post in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            for result in results:
                if isinstance(result, Exception):
                    failed_posts += 1
                    logger.error(f"Post processing failed: {result}")
                elif result is not None:
                    processed_posts += 1
                else:
                    failed_posts += 1
            
            # Small delay between batches to be respectful to the API
            if i + batch_size < total_posts:
                await asyncio.sleep(1)
        
        # Determine overall status
        if failed_posts == 0:
            status = "completed"
            message = f"Successfully processed all {processed_posts} posts"
        elif processed_posts == 0:
            status = "failed"
            message = f"Failed to process all {failed_posts} posts"
        else:
            status = "partial"
            message = f"Processed {processed_posts} posts, {failed_posts} failed"
        
        return {
            "status": status,
            "message": message,
            "total_posts": total_posts,
            "processed_posts": processed_posts,
            "failed_posts": failed_posts
        }
    
    async def get_style_training_status(
        self, 
        session: AsyncSession, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get the current style training status for a user.
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            Style training status information
        """
        # Count total posts
        total_posts = await session.execute(
            select(UserStylePost).where(UserStylePost.user_id == user_id)
        )
        total_posts = len(total_posts.scalars().all())
        
        # Count processed posts
        processed_posts = await session.execute(
            select(UserStylePost).where(
                UserStylePost.user_id == user_id,
                UserStylePost.processed == True
            )
        )
        processed_posts = len(processed_posts.scalars().all())
        
        # Calculate progress
        progress = (processed_posts / total_posts * 100) if total_posts > 0 else 0
        
        # Determine status
        if total_posts == 0:
            status = "pending"
            message = "No style posts added yet"
        elif processed_posts == 0:
            status = "pending"
            message = "Style posts added, processing not started"
        elif processed_posts < total_posts:
            status = "processing"
            message = f"Processing {processed_posts} of {total_posts} posts"
        else:
            status = "completed"
            message = f"All {total_posts} posts processed successfully"
        
        return {
            "status": status,
            "progress": round(progress, 1),
            "total_posts": total_posts,
            "processed_posts": processed_posts,
            "message": message
        }
    
    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate text embedding using Gemini API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if failed
        """
        if not self.gemini_model:
            return None
        
        try:
            # Use Gemini to generate embedding
            # Note: This is a simplified approach. In production, you might want to use
            # a dedicated embedding model like text-embedding-004
            response = self.gemini_model.generate_content(
                f"Generate a numerical representation for this text: {text}"
            )
            
            # For now, we'll create a mock embedding since Gemini doesn't directly provide embeddings
            # In production, you'd want to use a proper embedding API
            import hashlib
            import random
            
            # Create a deterministic "embedding" based on text hash
            text_hash = hashlib.md5(text.encode()).hexdigest()
            random.seed(text_hash)
            embedding = [random.uniform(-1, 1) for _ in range(768)]
            
            logger.info(f"Generated embedding for text (length: {len(text)})")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
    
    async def get_user_style_summary(
        self, 
        session: AsyncSession, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get a summary of user's style training data.
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            Style training summary
        """
        # Get style posts
        style_posts = await session.execute(
            select(UserStylePost)
            .where(UserStylePost.user_id == user_id)
            .order_by(UserStylePost.created_at.desc())
        )
        style_posts = style_posts.scalars().all()
        
        # Get style vectors
        style_vectors = await session.execute(
            select(StyleVector)
            .where(StyleVector.user_id == user_id)
        )
        style_vectors = style_vectors.scalars().all()
        
        # Calculate statistics
        total_posts = len(style_posts)
        processed_posts = len([p for p in style_posts if p.processed])
        total_words = sum(p.word_count or 0 for p in style_posts)
        avg_words = total_words / total_posts if total_posts > 0 else 0
        
        return {
            "total_posts": total_posts,
            "processed_posts": processed_posts,
            "total_words": total_words,
            "average_words_per_post": round(avg_words, 1),
            "style_vectors_count": len(style_vectors),
            "latest_post_date": style_posts[0].created_at.isoformat() if style_posts else None,
            "completion_percentage": (processed_posts / total_posts * 100) if total_posts > 0 else 0
        }


# Global service instance
style_training_service = StyleTrainingService()
