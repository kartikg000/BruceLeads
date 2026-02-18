"""
Rate Limiter Utility
Provides rate limiting for scraping and API calls.
"""

import time
import random
from functools import wraps
from typing import Optional, Callable
from datetime import datetime, timedelta


class RateLimiter:
    """
    Token bucket rate limiter with optional jitter.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 20,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        jitter: bool = True
    ):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
            min_delay: Minimum delay between requests (seconds)
            max_delay: Maximum delay between requests (seconds)
            jitter: Add random variation to delays
        """
        self.requests_per_minute = requests_per_minute
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.jitter = jitter
        
        self._last_request_time: Optional[datetime] = None
        self._request_count = 0
        self._window_start = datetime.now()
    
    def wait(self):
        """
        Wait appropriate time before next request.
        Blocks until it's safe to proceed.
        """
        now = datetime.now()
        
        # Reset window if minute has passed
        if (now - self._window_start) > timedelta(minutes=1):
            self._window_start = now
            self._request_count = 0
        
        # Check if we've exceeded rate limit
        if self._request_count >= self.requests_per_minute:
            # Wait until window resets
            sleep_time = 60 - (now - self._window_start).total_seconds()
            if sleep_time > 0:
                time.sleep(sleep_time)
            self._window_start = datetime.now()
            self._request_count = 0
        
        # Apply minimum delay between requests
        if self._last_request_time:
            elapsed = (now - self._last_request_time).total_seconds()
            
            # Calculate required delay
            if self.jitter:
                required_delay = random.uniform(self.min_delay, self.max_delay)
            else:
                required_delay = self.min_delay
            
            if elapsed < required_delay:
                time.sleep(required_delay - elapsed)
        
        # Update tracking
        self._last_request_time = datetime.now()
        self._request_count += 1
    
    def get_delay(self) -> float:
        """Get the delay that would be applied."""
        if self.jitter:
            return random.uniform(self.min_delay, self.max_delay)
        return self.min_delay
    
    @property
    def requests_remaining(self) -> int:
        """Get number of requests remaining in current window."""
        return max(0, self.requests_per_minute - self._request_count)
    
    def reset(self):
        """Reset the rate limiter state."""
        self._last_request_time = None
        self._request_count = 0
        self._window_start = datetime.now()


# Global rate limiters for different services
_rate_limiters = {}


def get_rate_limiter(name: str, **kwargs) -> RateLimiter:
    """
    Get or create a named rate limiter.
    
    Args:
        name: Unique name for the rate limiter
        **kwargs: Arguments for RateLimiter if creating new
        
    Returns:
        RateLimiter instance
    """
    if name not in _rate_limiters:
        _rate_limiters[name] = RateLimiter(**kwargs)
    return _rate_limiters[name]


def rate_limited(
    name: str = "default",
    requests_per_minute: int = 20,
    min_delay: float = 2.0,
    max_delay: float = 5.0
) -> Callable:
    """
    Decorator for rate-limiting function calls.
    
    Usage:
        @rate_limited("google_maps", requests_per_minute=10)
        def scrape_business(url):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter = get_rate_limiter(
                name,
                requests_per_minute=requests_per_minute,
                min_delay=min_delay,
                max_delay=max_delay
            )
            limiter.wait()
            return func(*args, **kwargs)
        return wrapper
    return decorator


class ExponentialBackoff:
    """
    Exponential backoff for retry logic.
    """
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        max_attempts: int = 5
    ):
        """
        Initialize backoff calculator.
        
        Args:
            initial_delay: Starting delay in seconds
            max_delay: Maximum delay in seconds
            multiplier: Multiplier for each subsequent retry
            max_attempts: Maximum number of attempts
        """
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.max_attempts = max_attempts
        self._attempt = 0
    
    def get_delay(self) -> float:
        """Get delay for current attempt."""
        delay = self.initial_delay * (self.multiplier ** self._attempt)
        return min(delay, self.max_delay)
    
    def wait(self):
        """Wait for current backoff delay."""
        delay = self.get_delay()
        time.sleep(delay)
        self._attempt += 1
    
    def should_retry(self) -> bool:
        """Check if more attempts are allowed."""
        return self._attempt < self.max_attempts
    
    def reset(self):
        """Reset attempt counter."""
        self._attempt = 0
    
    @property
    def attempt(self) -> int:
        """Get current attempt number."""
        return self._attempt
