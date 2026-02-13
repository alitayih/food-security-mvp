from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


CACHE_DIR = Path("app_data/cache")


def _cache_file(cache_dir: Path, key: str) -> Path:
    return cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()}.json"


def cache_get(cache_dir: Path, key: str, ttl_seconds: int) -> Any | None:
    path = _cache_file(cache_dir, key)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if time.time() - payload["stored_at"] > ttl_seconds:
        return None
    return payload["data"]


def cache_set(cache_dir: Path, key: str, data: Any) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    _cache_file(cache_dir, key).write_text(
        json.dumps({"stored_at": time.time(), "data": data}), encoding="utf-8"
    )


def fetch_with_cache(
    url: str,
    *,
    ttl_seconds: int = 60 * 60 * 24,
    as_json: bool = True,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> Any:
    cached = cache_get(CACHE_DIR, url, ttl_seconds)
    if cached is not None:
        return cached

    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            import requests

            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data: Any = resp.json() if as_json else resp.text
            cache_set(CACHE_DIR, url, data)
            return data
        except Exception as exc:  # network/runtime variability
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(backoff_seconds * (2**attempt))
    if last_exc:
        raise last_exc
    raise RuntimeError("fetch failed")
