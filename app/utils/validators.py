"""
Validation utilities.
"""
import re
import validators
from typing import Dict, List
from email_validator import validate_email, EmailNotValidError


def validate_user_email(email: str) -> bool:
    """
    Validate email format and deliverability.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email is valid
    """
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def validate_timezone(timezone: str) -> bool:
    """
    Validate IANA timezone identifier.
    
    Args:
        timezone: Timezone string to validate
        
    Returns:
        bool: True if timezone is valid
    """
    try:
        import zoneinfo
        zoneinfo.ZoneInfo(timezone)
        return True
    except Exception:
        return False


def validate_time_format(time_str: str) -> bool:
    """
    Validate time format (HH:MM:SS).
    
    Args:
        time_str: Time string to validate
        
    Returns:
        bool: True if time format is valid
    """
    pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]$'
    return bool(re.match(pattern, time_str))


def validate_rss_feed(url: str) -> Dict[str, any]:
    """
    Validate RSS feed URL.
    
    Args:
        url: RSS feed URL to validate
        
    Returns:
        dict: Validation result with 'valid' boolean and optional 'error' message
    """
    if not validators.url(url):
        return {"valid": False, "error": "Invalid URL format"}
    
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            
            if response.status_code != 200:
                return {"valid": False, "error": "Feed not accessible"}
            
            content_type = response.headers.get('content-type', '').lower()
            if 'xml' not in content_type and 'rss' not in content_type:
                return {"valid": False, "error": "Not a valid RSS feed"}
            
            return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def validate_twitter_handle(handle: str) -> Dict[str, any]:
    """
    Validate Twitter handle format.
    
    Args:
        handle: Twitter handle to validate
        
    Returns:
        dict: Validation result with 'valid' boolean and optional 'error' message
    """
    # Remove @ if present
    handle = handle.lstrip('@')
    
    # Twitter handle validation pattern
    pattern = r'^[A-Za-z0-9_]{1,15}$'
    
    if not re.match(pattern, handle):
        return {"valid": False, "error": "Invalid Twitter handle format"}
    
    return {"valid": True}


def validate_style_post_content(content: str) -> Dict[str, any]:
    """
    Validate style post content.
    
    Args:
        content: Post content to validate
        
    Returns:
        dict: Validation result with 'valid' boolean and optional 'errors' list
    """
    errors = []
    
    if not content or not isinstance(content, str):
        errors.append("Content is required")
        return {"valid": False, "errors": errors}
    
    content = content.strip()
    
    if len(content) < 50:
        errors.append("Content must be at least 50 characters long")
    
    if len(content) > 3000:
        errors.append("Content must be less than 3000 characters")
    
    # Check for excessive links
    if content.count('http') > 3:
        errors.append("Too many links in content")
    
    # Basic spam detection
    spam_patterns = [
        r'(buy now|click here|limited time)',
        r'(\$\d+|\d+% off)',
        r'(urgent|act now|don\'t miss)',
    ]
    
    for pattern in spam_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            errors.append("Content appears to be promotional or spam")
            break
    
    return {"valid": len(errors) == 0, "errors": errors}


def is_english_content(content: str) -> bool:
    """
    Basic English language detection.
    
    Args:
        content: Text content to check
        
    Returns:
        bool: True if content appears to be in English
    """
    # Simple heuristic: check for common English words
    english_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'among', 'is', 'are', 'was',
        'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
        'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
        'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
        'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
    }
    
    words = re.findall(r'\b[a-zA-Z]+\b', content.lower())
    if not words:
        return False
    
    english_word_count = sum(1 for word in words if word in english_words)
    return english_word_count / len(words) > 0.3  # At least 30% English words