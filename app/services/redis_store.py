import redis
from typing import Optional
from app.core.state import CVState
from app.core.config import Config

class RedisStore:
    def __init__(self, host: str = Config.REDIS_HOST, port: int = Config.REDIS_PORT):
        self.client = redis.Redis(host=host, port=port, db=Config.REDIS_DB, decode_responses=True)
    
    def save_state(self, session_id: str, state: CVState):
        try:
            self.client.setex(
                f"cv_session:{session_id}",
                Config.REDIS_TTL,
                state.model_dump_json()
            )
        except redis.exceptions.ConnectionError as e:
            print(f"Redis Error (save_state): {e}")
    
    def load_state(self, session_id: str) -> Optional[CVState]:
        try:
            state_json = self.client.get(f"cv_session:{session_id}")
            return CVState.model_validate_json(state_json) if state_json else None
        except Exception as e:
            print(f"Error loading state: {e}")
            return None