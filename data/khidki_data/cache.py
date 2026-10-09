"""Cache every outdoor fetch with a timestamp; on failure, serve the last good copy and say how stale it is.

`Cache` is a protocol so the cloud can back it with S3 and local mode with files.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from khidki_data.http import FetchError


class Cache(Protocol):
    def get(self, key: str) -> tuple[Any, float] | None: ...

    def put(self, key: str, value: Any, at: float) -> None: ...


class FileCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / (key.replace("/", "_") + ".json")

    def get(self, key: str) -> tuple[Any, float] | None:
        p = self._path(key)
        if not p.exists():
            return None
        d = json.loads(p.read_text())
        return d["value"], float(d["at"])

    def put(self, key: str, value: Any, at: float) -> None:
        self._path(key).write_text(json.dumps({"at": at, "value": value}))


class MemoryCache:
    def __init__(self) -> None:
        self._d: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> tuple[Any, float] | None:
        return self._d.get(key)

    def put(self, key: str, value: Any, at: float) -> None:
        self._d[key] = (value, at)


@dataclass(frozen=True)
class Fetched:
    value: Any
    fetched_at: float
    stale: bool
    """True when the live fetch failed and this is the last good copy."""

    def age_min(self, now: float | None = None) -> float:
        return ((now or time.time()) - self.fetched_at) / 60.0


def fetch_with_cache(cache: Cache, key: str, fetch: Callable[[], Any], now: float | None = None) -> Fetched:
    now = now or time.time()
    try:
        value = fetch()
    except FetchError:
        hit = cache.get(key)
        if hit is None:
            raise
        return Fetched(value=hit[0], fetched_at=hit[1], stale=True)
    cache.put(key, value, now)
    return Fetched(value=value, fetched_at=now, stale=False)
