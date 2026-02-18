"""
Data Validation Utilities
Provides validation and cleaning functions for lead data.
"""

import re
from typing import Optional
from urllib.parse import urlparse


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email format is valid
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL format is valid
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """
    Normalize URL by adding https:// if missing.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    if not url:
        return ""
    
    url = url.strip()
    
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return url


def validate_phone(phone: str) -> bool:
    """
    Basic phone number validation.
    
    Args:
        phone: Phone number to validate
        
    Returns:
        True if phone appears to be valid
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove common formatting characters
    digits = re.sub(r'[\s\-\(\)\.\+]', '', phone)
    
    # Check if we have a reasonable number of digits (7-15)
    return 7 <= len(digits) <= 15 and digits.isdigit()


def clean_phone(phone: str) -> str:
    """
    Clean and format phone number.
    
    Args:
        phone: Raw phone number
        
    Returns:
        Cleaned phone number
    """
    if not phone:
        return ""
    
    # Keep only digits, plus, and leading country code
    cleaned = re.sub(r'[^\d\+]', '', phone)
    return cleaned


def clean_business_name(name: str) -> str:
    """
    Clean and normalize business name.
    
    Args:
        name: Raw business name
        
    Returns:
        Cleaned business name
    """
    if not name or not isinstance(name, str):
        return ""
    
    # Remove extra whitespace
    name = ' '.join(name.split())
    
    # Remove common suffixes that don't add value
    suffixes_to_remove = [
        ' - Google Maps',
        ' | Google Maps',
        ' - Official Site',
        ' | Official Site'
    ]
    
    for suffix in suffixes_to_remove:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    
    return name.strip()


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL.
    
    Args:
        url: Full URL
        
    Returns:
        Domain name or None
    """
    if not url:
        return None
    
    try:
        parsed = urlparse(normalize_url(url))
        domain = parsed.netloc
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except Exception:
        return None


def extract_emails_from_text(text: str) -> list:
    """
    Extract email addresses from text content.
    
    Args:
        text: Text to search for emails
        
    Returns:
        List of found email addresses
    """
    if not text:
        return []
    
    # Email pattern
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    emails = re.findall(pattern, text)
    
    # Filter out common false positives
    excluded_patterns = [
        'example.com',
        'email.com',
        'domain.com',
        'yoursite.com',
        'company.com',
        '.png',
        '.jpg',
        '.gif'
    ]
    
    return [
        email for email in emails
        if not any(pattern in email.lower() for pattern in excluded_patterns)
    ]


def score_email_quality(email: str, business_name: str = "") -> int:
    """
    Score an email address quality (1-10).
    Higher score = more likely to be the right contact.
    
    Args:
        email: Email address to score
        business_name: Business name for comparison
        
    Returns:
        Quality score 1-10
    """
    if not validate_email(email):
        return 0
    
    score = 5  # Base score for valid email
    
    email_lower = email.lower()
    
    # Generic addresses are less valuable
    generic_prefixes = ['info@', 'contact@', 'hello@', 'support@', 'admin@', 'sales@']
    if any(email_lower.startswith(prefix) for prefix in generic_prefixes):
        score -= 1
    
    # Personal addresses are more valuable
    personal_prefixes = ['ceo@', 'founder@', 'owner@']
    if any(email_lower.startswith(prefix) for prefix in personal_prefixes):
        score += 2
    
    # Name-based emails are good
    if re.match(r'^[a-zA-Z]+\.?[a-zA-Z]*@', email_lower):
        score += 1
    
    # Free email providers are less valuable for business
    free_providers = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com']
    domain = email_lower.split('@')[1] if '@' in email_lower else ''
    if domain in free_providers:
        score -= 1
    
    # Check if domain matches business name
    if business_name:
        biz_words = set(business_name.lower().split())
        domain_words = set(domain.replace('.', ' ').split())
        if biz_words & domain_words:
            score += 2
    
    return max(1, min(10, score))
