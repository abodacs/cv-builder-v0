from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from redis.exceptions import RedisError

from app.core.state import CVState
from app.services.redis_store import RedisStore


@pytest.fixture
def mock_redis() -> Generator[Mock, None, None]:
    """Fixture providing a mocked Redis client."""
    with patch("redis.Redis") as mock_redis:
        mock_client = Mock()
        mock_redis.return_value = mock_client
        yield mock_client


@pytest.fixture
def store() -> RedisStore:
    """Fixture providing a RedisStore instance."""
    return RedisStore()


class TestRedisStore:
    """Test cases for Redis store operations."""

    def test_redis_store_save_success(
        self, mock_redis: Mock, store: RedisStore
    ) -> None:
        """Test successful state saving to Redis."""
        state = CVState(personal_info={"name": "John"})
        store.save_state("test-id", state)

        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "cv_session:test-id", "Key should match input ID"
        assert isinstance(args[2], str), "Stored value should be JSON string"

    def test_redis_store_save_failure(
        self, mock_redis: Mock, store: RedisStore
    ) -> None:
        """Test Redis save operation failure."""
        mock_redis.setex.side_effect = RedisError("Connection failed")

        with pytest.raises(RuntimeError, match="Failed to save state:.*"):
            store.save_state("test-id", CVState())

    def test_redis_store_load_success(
        self, mock_redis: Mock, store: RedisStore
    ) -> None:
        """Test successful state loading from Redis."""
        mock_redis.get.return_value = (
            '{"language":"ar","personal_info":{"name":"John"}}'
        )
        state = store.load_state("test-id")

        assert isinstance(state, CVState), "Should return CVState instance"
        assert state.language == "ar", "Should preserve language setting"
        assert state.personal_info["name"] == "John", "Should load personal info"

    def test_redis_store_load_missing(
        self, mock_redis: Mock, store: RedisStore
    ) -> None:
        """Test loading non-existent state."""
        mock_redis.get.return_value = None

        state = store.load_state("missing-id")
        assert isinstance(state, CVState), "Should return CVState instance"
