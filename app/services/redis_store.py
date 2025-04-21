import redis

from app.core.config import Config
from app.core.state import CVState


class RedisStore:
    def __init__(self, host: str = Config.REDIS_HOST, port: int = Config.REDIS_PORT):
        self.client = redis.Redis(
            host=host, port=port, db=Config.REDIS_DB, decode_responses=True
        )

    def save_state(self, session_id: str, state: CVState) -> None:
        """Save CV state to Redis."""
        try:
            self.client.setex(
                f"cv_session:{session_id}", Config.REDIS_TTL, state.model_dump_json()
            )
        except redis.exceptions.RedisError as err:
            raise RuntimeError(f"Failed to save state: {err}") from err

    def load_state(self, session_id: str) -> CVState:
        """Load CV state from Redis."""
        try:
            state_json = self.client.get(f"cv_session:{session_id}")
            if not state_json:
                raise ValueError(f"No state found for session: {session_id}")
            state = CVState.model_validate_json(state_json)
            assert isinstance(state, CVState)  # Type guard for mypy
            return state
        except redis.exceptions.RedisError as err:
            raise RuntimeError(f"Failed to load state: {err}") from err
        except ValueError as err:
            raise ValueError(str(err)) from err
