"""Tests for hishel cache configuration.

This module contains tests to verify that the cache configuration is safe
and does not cache dangerous operations like POST requests.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestCacheConfiguration:
    """Tests for cache configuration safety."""

    def test_post_requests_not_cached(self) -> None:
        """POST requests should never be cached as they may be order placements."""
        from utils.hishel_config import controller

        # Verify POST is not in cacheable methods
        assert "POST" not in controller._cacheable_methods

    def test_only_get_requests_cached(self) -> None:
        """Only GET requests should be cached."""
        from utils.hishel_config import controller

        # GET should be the only cacheable method
        assert "GET" in controller._cacheable_methods
        assert len(controller._cacheable_methods) == 1

    def test_delete_requests_not_cached(self) -> None:
        """DELETE requests should not be cached."""
        from utils.hishel_config import controller

        assert "DELETE" not in controller._cacheable_methods

    def test_put_requests_not_cached(self) -> None:
        """PUT requests should not be cached."""
        from utils.hishel_config import controller

        assert "PUT" not in controller._cacheable_methods

    def test_only_200_status_cached(self) -> None:
        """Only 200 OK responses should be cached."""
        from utils.hishel_config import controller

        assert 200 in controller._cacheable_status_codes
        # Don't cache error responses
        assert 400 not in controller._cacheable_status_codes
        assert 401 not in controller._cacheable_status_codes
        assert 429 not in controller._cacheable_status_codes
        assert 500 not in controller._cacheable_status_codes

    def test_cache_ttl_is_reasonable(self) -> None:
        """Cache TTL should be reasonable (not too long)."""
        from utils.hishel_config import storage

        # TTL should be set and not exceed 5 minutes (300 seconds)
        # This is important because market data can change frequently
        assert hasattr(storage, "_ttl")
        assert storage._ttl is not None
        assert storage._ttl <= 300
