import hashlib
import json
import time
from typing import Any, Optional

try:
    import redis  # type: ignore
except ImportError:  # pragma: no cover
    redis = None

from .config import settings


class _MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Optional[str]:
        item = self._data.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._data.pop(key, None)
            return None
        return value

    def setex(self, key: str, ttl: int, value: str) -> None:
        self._data[key] = (time.time() + ttl, value)


_memory = _MemoryStore()
_redis_client = None


def _get_store():
    global _redis_client
    if redis is None:
        return _memory
    if _redis_client is None:
        try:
            client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            client.ping()
            _redis_client = client
        except Exception:
            _redis_client = False  # type: ignore[assignment]  # sentinel: tried, failed
            return _memory
    if _redis_client is False:
        return _memory
    return _redis_client


def request_hash(method: str, path: str, key: str, user_id: int) -> str:
    raw = f"{method}:{path}:{key}:{user_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(hash_key: str) -> Optional[Any]:
    raw = _get_store().get(f"idempotency:{hash_key}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def set_cached(hash_key: str, payload: Any, ttl: int = 3600) -> None:
    _get_store().setex(f"idempotency:{hash_key}", ttl, json.dumps(payload, default=str))
