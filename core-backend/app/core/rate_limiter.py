"""
Redis-based rate limiting middleware for FastAPI.

This module provides rate limiting functionality using Redis as the backend store.
"""

import time
import redis
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis.

    Limits the number of requests per client IP within a time window.
    """

    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        """Initialize the rate limiter middleware."""
        super().__init__(app)
        self.redis_client = redis_client or self._get_redis_client()
        self.requests_per_window = settings.RATE_LIMIT_REQUESTS
        self.window_size = settings.RATE_LIMIT_WINDOW

    def _get_redis_client(self) -> redis.Redis:
        """Create and return a Redis client."""
        try:
            return redis.from_url(
                settings.REDIS_URL, db=settings.REDIS_DB, decode_responses=True
            )
        except Exception:
            # Fallback to in-memory store if Redis is not available
            return None

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process the request and apply rate limiting."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = self._get_client_ip(request)

        # Check rate limit
        if not self._is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Too many requests",
                    "message": f"Rate limit exceeded. Try again in {self.window_size} seconds.",
                    "retry_after": self.window_size,
                },
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers
        remaining, reset_time = self._get_rate_limit_info(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_window)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for IP in various headers (in order of preference)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to client host
        return request.client.host if request.client else "unknown"

    def _is_allowed(self, client_ip: str) -> bool:
        """Check if the client is within rate limits."""
        if not self.redis_client:
            # If Redis is not available, allow all requests
            return True

        current_time = int(time.time())
        window_start = current_time - self.window_size

        # Use Redis pipeline for atomic operations
        pipe = self.redis_client.pipeline()
        key = f"rate_limit:{client_ip}"

        # Remove old requests outside the window
        pipe.zremrangebyscore(key, "-inf", window_start)

        # Count requests in current window
        pipe.zcard(key)

        # Add current request
        pipe.zadd(key, {str(current_time): current_time})

        # Set expiry for the key
        pipe.expire(key, self.window_size * 2)

        results = pipe.execute()
        request_count = results[1]

        return request_count < self.requests_per_window

    def _get_rate_limit_info(self, client_ip: str) -> tuple[int, int]:
        """Get rate limit information for the client."""
        if not self.redis_client:
            return self.requests_per_window, int(time.time()) + self.window_size

        current_time = int(time.time())
        window_start = current_time - self.window_size

        # Remove old requests
        self.redis_client.zremrangebyscore(
            f"rate_limit:{client_ip}", "-inf", window_start
        )

        # Get remaining requests
        request_count = self.redis_client.zcard(f"rate_limit:{client_ip}")
        remaining = max(0, self.requests_per_window - request_count)

        # Calculate reset time
        reset_time = current_time + self.window_size

        return remaining, reset_time


class InMemoryRateLimiter:
    """
    In-memory rate limiter for development/testing when Redis is not available.
    """

    def __init__(self):
        """Initialize in-memory rate limiter."""
        self.requests = {}
        self.requests_per_window = settings.RATE_LIMIT_REQUESTS
        self.window_size = settings.RATE_LIMIT_WINDOW

    def is_allowed(self, client_ip: str) -> bool:
        """Check if client is within rate limits."""
        current_time = time.time()
        window_start = current_time - self.window_size

        # Get or create client request history
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Remove old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip] if req_time > window_start
        ]

        # Check if under limit
        if len(self.requests[client_ip]) < self.requests_per_window:
            self.requests[client_ip].append(current_time)
            return True

        return False

    def get_remaining_requests(self, client_ip: str) -> int:
        """Get remaining requests for client."""
        current_time = time.time()
        window_start = current_time - self.window_size

        if client_ip not in self.requests:
            return self.requests_per_window

        # Remove old requests and count remaining
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip] if req_time > window_start
        ]

        return max(0, self.requests_per_window - len(self.requests[client_ip]))
