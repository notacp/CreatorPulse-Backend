"""
Draft generation service using RAG and style matching.

This service implements the core draft generation logic using:
- Vector similarity search for style matching
- RAG (Retrieval-Augmented Generation) with user's style vectors
- Gemini API integration for content generation
- Content ranking and filtering
"""

import asyncio
import hashlib
import logging
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_, desc
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import CreatorPulseException
from app.models.style import StyleVector, UserStylePost
from app.models.source_content import SourceContent
from app.models.draft import GeneratedDraft
from app.models.user import User
from app.core.security import generate_feedback_token

logger = logging.getLogger(__name__)


class DraftGenerator:
    """Service for generating personalized LinkedIn drafts using RAG and AI."""
    
    def __init__(self):
        """Initialize the draft generator."""
        self.gemini_model = None
        if settings.gemini_api_key:
            try:
                genai.configure(api_key=settings.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
                logger.info("Gemini API initialized for draft generation")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini API: {e}")
                self.gemini_model = None
        else:
            logger.warning("GEMINI_API_KEY not configured, draft generation will be limited")
    
    async def generate_content_embeddings(
        self, 
        content_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate embeddings for content items using the same method as style training.
        
        Args:
            content_items: List of content items to generate embeddings for
            
        Returns:
            Content items with embeddings added
        """
        try:
            for item in content_items:
                # Create a combined text for embedding
                combined_text = f"{item.get('title', '')} {item.get('content', '')}"
                
                # Generate embedding (using same method as style training)
                embedding = await self._generate_embedding(combined_text)
                item['embedding'] = embedding
            
            return content_items
            
        except Exception as e:
            logger.error(f"Error generating content embeddings: {e}")
            raise CreatorPulseException(f"Failed to generate content embeddings: {str(e)}")
    
    async def find_style_matched_content(
        self,
        session: AsyncSession,
        user_id: str,
        content_items: List[Dict[str, Any]],
        max_matches: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[Dict[str, Any], float, List[Dict[str, Any]]]]:
        """
        Find content that matches the user's writing style using vector similarity.
        
        Args:
            session: Database session
            user_id: User ID
            content_items: Content items with embeddings
            max_matches: Maximum number of content matches to return
            similarity_threshold: Minimum similarity score (0-1)
            
        Returns:
            List of tuples (content_item, similarity_score, matching_style_examples)
        """
        try:
            # Get user's style vectors
            result = await session.execute(
                select(StyleVector)
                .where(StyleVector.user_id == (uuid.UUID(user_id) if isinstance(user_id, str) else user_id))
                .options(selectinload(StyleVector.style_post))
            )
            style_vectors = result.scalars().all()
            
            if not style_vectors:
                logger.warning(f"No style vectors found for user {user_id}")
                return []
            
            logger.info(f"Matching content against {len(style_vectors)} style vectors")
            
            matched_content = []
            
            for content_item in content_items:
                content_embedding = content_item.get('embedding')
                if not content_embedding:
                    continue
                
                # Calculate similarity with all style vectors
                similarities = []
                for style_vector in style_vectors:
                    if style_vector.embedding is None or len(style_vector.embedding) == 0:
                        continue
                    
                    similarity = self._calculate_cosine_similarity(
                        content_embedding, 
                        list(style_vector.embedding)  # Ensure it's a list
                    )
                    
                    # Ensure similarity is a float, not a numpy type or other
                    if hasattr(similarity, 'item'):
                        similarity = float(similarity.item())
                    else:
                        similarity = float(similarity)
                    
                    similarities.append({
                        'similarity': similarity,
                        'style_vector': style_vector,
                        'style_post': style_vector.style_post
                    })
                
                if not similarities:
                    continue
                
                # Get average similarity and best matches
                avg_similarity = sum(s['similarity'] for s in similarities) / len(similarities)
                best_matches = sorted(similarities, key=lambda x: x['similarity'], reverse=True)[:3]
                
                # Only include if above threshold
                if avg_similarity >= similarity_threshold:
                    # Create style examples for context
                    style_examples = []
                    for match in best_matches:
                        if match['style_post'] and match['style_post'].content:
                            style_examples.append({
                                'content': match['style_post'].content,
                                'similarity': match['similarity'],
                                'word_count': match['style_post'].word_count
                            })
                    
                    # Ensure avg_similarity is a proper float
                    avg_similarity = float(avg_similarity) if avg_similarity is not None else 0.0
                    matched_content.append((content_item, avg_similarity, style_examples))
            
            # Sort by similarity score and return top matches  
            matched_content.sort(key=lambda x: float(x[1]), reverse=True)
            
            logger.info(f"Found {len(matched_content)} content items matching style (threshold: {similarity_threshold})")
            
            return matched_content[:max_matches]
            
        except Exception as e:
            logger.error(f"Error finding style-matched content: {e}")
            raise CreatorPulseException(f"Failed to match content with style: {str(e)}")
    
    async def generate_linkedin_draft(
        self,
        content_item: Dict[str, Any],
        style_examples: List[Dict[str, Any]],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a LinkedIn post draft using content and style examples.
        
        Args:
            content_item: Source content to base the draft on
            style_examples: User's style examples for reference
            user_profile: Optional user profile information
            
        Returns:
            Generated draft with metadata
        """
        try:
            if not self.gemini_model:
                # Fallback to template-based generation
                return self._generate_template_draft(content_item, style_examples)
            
            # Prepare style context
            style_context = self._prepare_style_context(style_examples)
            
            # Prepare content context
            content_context = self._prepare_content_context(content_item)
            
            # Generate prompt
            prompt = self._create_generation_prompt(content_context, style_context, user_profile)
            
            # Generate draft using Gemini
            response = await self._call_gemini_api(prompt)
            
            # Process and validate response
            draft_content = self._process_gemini_response(response)
            
            # Create draft metadata
            draft_data = {
                'content': draft_content,
                'source_content': content_item,
                'style_examples_used': len(style_examples),
                'generation_method': 'gemini_rag',
                'character_count': len(draft_content),
                'word_count': len(draft_content.split()),
                'metadata': {
                    'source_title': content_item.get('title', ''),
                    'source_url': content_item.get('url', ''),
                    'source_type': content_item.get('source_type', ''),
                    'style_similarity': max(ex.get('similarity', 0) for ex in style_examples) if style_examples else 0,
                    'generation_timestamp': datetime.utcnow().isoformat(),
                    'prompt_tokens': len(prompt.split()),  # Rough estimate
                }
            }
            
            logger.info(f"Generated LinkedIn draft ({len(draft_content)} chars) using Gemini RAG")
            return draft_data
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn draft: {e}")
            # Fallback to template generation
            return self._generate_template_draft(content_item, style_examples)
    
    async def generate_multiple_drafts(
        self,
        session: AsyncSession,
        user_id: str,
        max_drafts: int = 5,
        content_age_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple drafts for a user based on recent content.
        
        Args:
            session: Database session
            user_id: User ID
            max_drafts: Maximum number of drafts to generate
            content_age_hours: Only use content from the last N hours
            
        Returns:
            List of generated drafts
        """
        try:
            logger.info(f"Generating up to {max_drafts} drafts for user {user_id}")
            
            # Get recent content for the user
            cutoff_time = datetime.utcnow() - timedelta(hours=content_age_hours)
            
            from app.models.source import Source
            result = await session.execute(
                select(SourceContent, Source.type, Source.name)
                .join(Source, SourceContent.source_id == Source.id)
                .where(
                    and_(
                        Source.user_id == (uuid.UUID(user_id) if isinstance(user_id, str) else user_id),
                        SourceContent.created_at >= cutoff_time
                    )
                )
                .order_by(desc(SourceContent.created_at))
                .limit(50)  # Get more content to have better selection
            )
            query_results = result.fetchall()
            
            if not query_results:
                logger.info(f"No recent content found for user {user_id}")
                return []
            
            logger.info(f"Found {len(query_results)} recent content items for user {user_id}")
            
            # Convert to dict format and generate embeddings
            content_items = []
            for row in query_results:
                content, source_type, source_name = row
                content_items.append({
                    'id': str(content.id),
                    'title': content.title or 'Untitled',
                    'content': content.content,
                    'url': content.url or '',
                    'source_type': source_type or 'unknown',
                    'source_name': source_name or 'Unknown Source',
                    'published_at': content.published_at or content.created_at,
                    'metadata': {}
                })
            
            # Generate embeddings for content
            content_items = await self.generate_content_embeddings(content_items)
            
            # Find style-matched content
            matched_content = await self.find_style_matched_content(
                session=session,
                user_id=user_id,
                content_items=content_items,
                max_matches=max_drafts * 2,  # Get more matches to have variety
                similarity_threshold=0.5  # Lower threshold for more variety
            )
            
            if not matched_content:
                logger.info(f"No style-matched content found for user {user_id}")
                return []
            
            # Generate drafts
            generated_drafts = []
            
            # Use the top matches up to max_drafts
            for content_item, similarity_score, style_examples in matched_content[:max_drafts]:
                try:
                    draft = await self.generate_linkedin_draft(
                        content_item=content_item,
                        style_examples=style_examples
                    )
                    
                    # Add similarity score to metadata
                    draft['metadata']['style_similarity'] = similarity_score
                    # Ensure source_content_id is a proper UUID string
                    if 'id' in content_item:
                        draft['source_content_id'] = str(content_item['id'])
                    else:
                        draft['source_content_id'] = None
                    
                    generated_drafts.append(draft)
                    
                except Exception as e:
                    logger.error(f"Error generating individual draft: {e}")
                    continue
            
            logger.info(f"Successfully generated {len(generated_drafts)} drafts for user {user_id}")
            return generated_drafts
            
        except Exception as e:
            logger.error(f"Error generating multiple drafts: {e}")
            raise CreatorPulseException(f"Failed to generate drafts: {str(e)}")
    
    async def save_generated_drafts(
        self,
        session: AsyncSession,
        user_id: str,
        drafts: List[Dict[str, Any]]
    ) -> List[GeneratedDraft]:
        """
        Save generated drafts to the database.
        
        Args:
            session: Database session
            user_id: User ID
            drafts: List of generated draft data
            
        Returns:
            List of saved draft objects
        """
        try:
            saved_drafts = []
            
            for draft_data in drafts:
                # Generate feedback token
                feedback_token = generate_feedback_token()
                
                # Create draft object  
                source_content_id = draft_data.get('source_content_id')
                if source_content_id and not isinstance(source_content_id, str):
                    source_content_id = str(source_content_id)
                
                draft = GeneratedDraft(
                    user_id=(uuid.UUID(user_id) if isinstance(user_id, str) else user_id),
                    content=draft_data['content'],
                    source_content_id=source_content_id,
                    status='pending',
                    feedback_token=feedback_token,
                    character_count=draft_data['character_count'],
                    generation_metadata=draft_data.get('metadata', {})
                )
                
                session.add(draft)
                saved_drafts.append(draft)
            
            await session.commit()
            
            # Refresh to get IDs
            for draft in saved_drafts:
                await session.refresh(draft)
            
            logger.info(f"Saved {len(saved_drafts)} drafts to database for user {user_id}")
            
            return saved_drafts
            
        except Exception as e:
            logger.error(f"Error saving drafts: {e}")
            await session.rollback()
            raise CreatorPulseException(f"Failed to save drafts: {str(e)}")
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            import math
            
            if len(vec1) != len(vec2):
                return 0.0
            
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = math.sqrt(sum(a * a for a in vec1))
            magnitude2 = math.sqrt(sum(a * a for a in vec2))
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return dot_product / (magnitude1 * magnitude2)
            
        except Exception:
            return 0.0
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (same method as style training)."""
        try:
            # For consistency with style training, use the same mock embedding approach
            # In production, this would use a proper embedding API
            import hashlib
            import random
            
            text_hash = hashlib.md5(text.encode()).hexdigest()
            random.seed(text_hash)
            embedding = [random.uniform(-1, 1) for _ in range(768)]
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return a zero vector as fallback
            return [0.0] * 768
    
    def _prepare_style_context(self, style_examples: List[Dict[str, Any]]) -> str:
        """Prepare style context from user's examples."""
        if not style_examples:
            return "No specific style examples available."
        
        context_parts = ["Here are examples of the user's writing style:"]
        
        for i, example in enumerate(style_examples[:3], 1):
            content = example.get('content', '')[:300]  # Limit length
            similarity = example.get('similarity', 0)
            context_parts.append(f"\nExample {i} (similarity: {similarity:.2f}):\n{content}")
        
        return "\n".join(context_parts)
    
    def _prepare_content_context(self, content_item: Dict[str, Any]) -> str:
        """Prepare content context from source material."""
        title = content_item.get('title', '')
        content = content_item.get('content', '')
        source_type = content_item.get('source_type', '')
        source_name = content_item.get('source_name', '')
        
        context = f"Source: {source_name} ({source_type})\n"
        if title:
            context += f"Title: {title}\n"
        context += f"Content: {content}"
        
        return context
    
    def _create_generation_prompt(
        self, 
        content_context: str, 
        style_context: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a prompt for Gemini to generate a LinkedIn post."""
        
        prompt = f"""You are a professional LinkedIn content creator. Your task is to create an engaging LinkedIn post based on the provided source content, while matching the user's writing style.

WRITING STYLE TO MATCH:
{style_context}

SOURCE CONTENT TO TRANSFORM:
{content_context}

INSTRUCTIONS:
1. Create a LinkedIn post that transforms the source content into the user's style
2. Keep the post engaging, professional, and LinkedIn-appropriate
3. Include relevant insights, questions, or calls-to-action
4. Use emojis sparingly and naturally (like in the style examples)
5. Keep the post between 150-300 words for optimal engagement
6. Make sure to add value beyond just summarizing the content
7. Use the user's tone, sentence structure, and formatting preferences
8. Include 2-3 relevant hashtags at the end

OUTPUT FORMAT:
Provide only the LinkedIn post content, without any additional explanation or formatting.

LinkedIn Post:"""

        return prompt
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API with the generation prompt."""
        try:
            response = self.gemini_model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
    
    def _process_gemini_response(self, response: str) -> str:
        """Process and validate Gemini response."""
        if not response:
            raise Exception("Empty response from Gemini")
        
        # Clean up the response
        content = response.strip()
        
        # Remove any extra formatting or prefixes
        if content.startswith("LinkedIn Post:"):
            content = content[len("LinkedIn Post:"):].strip()
        
        # Validate length (LinkedIn has character limits)
        if len(content) > 3000:
            content = content[:2950] + "..."
        
        if len(content) < 50:
            raise Exception("Generated content too short")
        
        return content
    
    def _generate_template_draft(
        self, 
        content_item: Dict[str, Any], 
        style_examples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a draft using templates when Gemini is not available."""
        
        title = content_item.get('title', 'Interesting article')
        content = content_item.get('content', '')[:200]  # Truncate
        source_name = content_item.get('source_name', 'a source')
        
        # Simple template-based generation
        templates = [
            f"Just read an insightful piece from {source_name} about {title.lower()}.\n\n{content}...\n\nWhat are your thoughts on this? 🤔\n\n#insights #learning #growth",
            f"Interesting perspective from {source_name}:\n\n{content}...\n\nThis made me think about how we approach similar challenges in our field.\n\n#leadership #innovation #thoughtleadership",
            f"Found this valuable insight from {source_name}:\n\n{content}...\n\nHow do you see this applying to your work? Let me know in the comments! 💭\n\n#professional #development #insights"
        ]
        
        draft_content = random.choice(templates)
        
        return {
            'content': draft_content,
            'source_content': content_item,
            'style_examples_used': len(style_examples),
            'generation_method': 'template',
            'character_count': len(draft_content),
            'word_count': len(draft_content.split()),
            'metadata': {
                'source_title': content_item.get('title', ''),
                'source_url': content_item.get('url', ''),
                'source_type': content_item.get('source_type', ''),
                'generation_timestamp': datetime.utcnow().isoformat(),
                'fallback_reason': 'gemini_unavailable'
            }
        }


# Global service instance
draft_generator = DraftGenerator()
