"""
Data sanitization utilities.

This module provides functions for sanitizing and validating user input data.
"""

import os
import re
import html
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse


def sanitize_string(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input by removing HTML tags and escaping special characters.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not text:
        return ""

    # Remove HTML tags
    text = html.escape(text)

    # Remove potentially dangerous characters
    text = re.sub(r'[^\w\s\-_.@]', '', text)

    # Truncate if max_length is specified
    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def sanitize_email(email: str) -> str:
    """
    Sanitize email address.

    Args:
        email: Email address to sanitize

    Returns:
        Sanitized email address
    """
    if not email:
        return ""

    # Convert to lowercase and strip whitespace
    email = email.lower().strip()

    # Basic email validation
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError("Invalid email format")

    return email


def sanitize_username(username: str, min_length: int = 3, max_length: int = 50) -> str:
    """
    Sanitize username.

    Args:
        username: Username to sanitize
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Sanitized username
    """
    if not username:
        return ""

    # Remove HTML tags and escape
    username = html.escape(username)

    # Remove spaces and special characters, keep alphanumeric, underscore, and hyphen
    username = re.sub(r'[^\w\-_]', '', username)

    # Check length constraints
    if len(username) < min_length:
        raise ValueError(f"Username must be at least {min_length} characters long")

    if len(username) > max_length:
        username = username[:max_length]

    return username.strip()


def sanitize_phone(phone: str) -> Optional[str]:
    """
    Sanitize phone number.

    Args:
        phone: Phone number to sanitize

    Returns:
        Sanitized phone number or None if invalid
    """
    if not phone:
        return None

    # Remove all non-digit characters
    phone = re.sub(r'\D', '', phone)

    # Basic phone number validation (10 digits for US numbers)
    if len(phone) < 10 or len(phone) > 15:
        return None

    return phone


def sanitize_url(url: str) -> Optional[str]:
    """
    Sanitize URL.

    Args:
        url: URL to sanitize

    Returns:
        Sanitized URL or None if invalid
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)

        # Check if it's a valid URL
        if not parsed.scheme or not parsed.netloc:
            return None

        # Only allow http and https
        if parsed.scheme not in ['http', 'https']:
            return None

        return url.strip()
    except Exception:
        return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed_file"

    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*\'"\'\x00-\x1f]', '', filename)

    # Replace spaces with underscores
    filename = re.sub(r'\s+', '_', filename)

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext

    return filename.strip('_')


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize text input while preserving formatting.

    Args:
        text: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Escape HTML but preserve line breaks
    text = html.escape(text)

    # Convert line breaks to HTML
    text = text.replace('\n', '<br>')
    text = text.replace('\r', '')

    # Truncate if max_length is specified
    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def sanitize_json_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize dictionary data recursively.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_json_data(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list_data(value)
        elif isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        else:
            sanitized[key] = value

    return sanitized


def sanitize_list_data(data: List[Any]) -> List[Any]:
    """
    Sanitize list data recursively.

    Args:
        data: List to sanitize

    Returns:
        Sanitized list
    """
    if not isinstance(data, list):
        return data

    sanitized = []
    for item in data:
        if isinstance(item, dict):
            sanitized.append(sanitize_json_data(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list_data(item))
        elif isinstance(item, str):
            sanitized.append(sanitize_string(item))
        else:
            sanitized.append(item)

    return sanitized


def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength.

    Args:
        password: Password to validate

    Returns:
        Dictionary with validation results
    """
    if not password:
        return {
            "valid": False,
            "errors": ["Password is required"]
        }

    errors = []

    # Length check
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    # Character variety checks
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")

    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")

    # Common patterns to avoid
    common_patterns = ['123456', 'password', 'qwerty', 'abc123', 'admin']
    if any(pattern in password.lower() for pattern in common_patterns):
        errors.append("Password contains common patterns that are easily guessable")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "strength": "strong" if len(errors) == 0 else "weak"
    }


def sanitize_search_query(query: str) -> str:
    """
    Sanitize search query.

    Args:
        query: Search query to sanitize

    Returns:
        Sanitized search query
    """
    if not query:
        return ""

    # Remove HTML and escape
    query = html.escape(query)

    # Remove dangerous characters
    query = re.sub(r'[^\w\s\-_.,!@#$%^&*()]', '', query)

    # Limit length
    if len(query) > 100:
        query = query[:100]

    return query.strip()


def sanitize_tags(tags: List[str]) -> List[str]:
    """
    Sanitize list of tags.

    Args:
        tags: List of tags to sanitize

    Returns:
        Sanitized list of tags
    """
    if not tags:
        return []

    sanitized_tags = []
    for tag in tags:
        if isinstance(tag, str):
            # Sanitize each tag
            tag = sanitize_string(tag, max_length=50)
            if tag and tag not in sanitized_tags:
                sanitized_tags.append(tag)

    return sanitized_tags


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize metadata dictionary.

    Args:
        metadata: Metadata to sanitize

    Returns:
        Sanitized metadata
    """
    if not isinstance(metadata, dict):
        return {}

    sanitized = {}
    for key, value in metadata.items():
        # Sanitize key
        key = sanitize_string(key, max_length=100)

        if isinstance(value, str):
            # Sanitize string values
            value = sanitize_string(value, max_length=1000)
        elif isinstance(value, (int, float, bool)):
            # Keep numeric and boolean values
            pass
        elif isinstance(value, list):
            # Sanitize list values
            value = [sanitize_string(str(item), max_length=100) if isinstance(item, str) else item for item in value]
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            value = sanitize_metadata(value)

        if key:
            sanitized[key] = value

    return sanitized
