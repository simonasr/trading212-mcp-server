"""Hishel cache configuration for Trading212 API client.

This module configures the HTTP response caching behavior. It's critical that
only safe, idempotent requests (GET) are cached. POST, DELETE, and other
modifying requests must NEVER be cached as they may include order placements.
"""

import hishel

__all__ = ["storage", "controller"]

# Cache storage with 5 minute TTL
# This is appropriate for market data that changes frequently
storage = hishel.FileStorage(ttl=300)

# Cache controller configuration
# IMPORTANT: Only cache GET requests. Never cache POST, DELETE, PUT, etc.
# as these may be order placements or other state-changing operations.
controller = hishel.Controller(
    # ONLY cache GET requests - this is critical for safety!
    # POST requests (like order placements) must NEVER be cached.
    cacheable_methods=["GET"],
    # Only cache successful responses
    cacheable_status_codes=[200],
    # Use stale response if there's a connection issue
    # This is safe for read-only GET requests
    allow_stale=True,
    # Force caching for GET requests even without cache headers
    force_cache=True,
)
