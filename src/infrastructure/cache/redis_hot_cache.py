import redis
import json
import logging
from typing import Optional, List, Dict
from src.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

class RedisHotCache:
    def __init__(self):
        settings = get_settings()
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self.ttl = settings.cache_ttl_seconds
        
    def get_chunk_text(self, chunk_id: str) -> Optional[str]:
        try:
            return self.client.get(f"chunk_payload:{chunk_id}")
        except Exception as e:
            logger.warning(f"Redis failed (get_chunk_text): {e}. Falling back to Postgres.")
            return None
            
    def set_chunk_text(self, chunk_id: str, text: str):
        try:
            self.client.setex(f"chunk_payload:{chunk_id}", self.ttl, text)
        except Exception as e:
            logger.warning(f"Redis failed (set_chunk_text): {e}.")
            
    def get_multiple_chunks(self, chunk_ids: List[str]) -> Dict[str, str]:
        results = {}
        try:
            keys = [f"chunk_payload:{cid}" for cid in chunk_ids]
            values = self.client.mget(keys)
            for cid, val in zip(chunk_ids, values):
                if val is not None:
                    results[cid] = val
        except Exception as e:
            logger.warning(f"Redis failed (get_multiple_chunks): {e}. Falling back to Postgres.")
        return results
