"""BruceLeads Utility Modules"""

import sys
import shutil
from pathlib import Path


def get_python_executable() -> list:
    """
    Get the command prefix to run a Python worker script.
    In frozen (PyInstaller) mode, returns [exe_path, '--worker'] so the
    EXE runs the script in its built-in Python environment.
    In dev mode, returns [sys.executable] (normal Python).
    Returns a list to be used as cmd prefix: cmd = get_python_executable() + [script, args...]
    """
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--worker']
    return [sys.executable]


from .validators import (
    validate_email, 
    validate_url, 
    validate_phone, 
    clean_business_name,
    normalize_url,
    extract_emails_from_text,
    score_email_quality,
    clean_phone,
    extract_domain
)
from .rate_limiter import RateLimiter, rate_limited
from . import license_manager

__all__ = [
    "get_python_executable",
    "validate_email", 
    "validate_url", 
    "validate_phone", 
    "clean_business_name",
    "normalize_url",
    "extract_emails_from_text",
    "score_email_quality",
    "clean_phone",
    "extract_domain",
    "RateLimiter",
    "rate_limited",
    "license_manager"
]

