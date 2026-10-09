"""Tiny JSON-over-HTTP helper: timeout ≤ 8 s, bounded retries with backoff. No third-party deps."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "khidki/0.1 (+https://github.com/bhavya-jpg/khidki)"


class FetchError(RuntimeError):
    pass


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    timeout_s: float = 8.0,
    retries: int = 2,
    backoff_s: float = 1.0,
) -> Any:
    full = f"{url}?{urllib.parse.urlencode(params, doseq=True, safe=',[]')}" if params else url
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                full, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if isinstance(exc, urllib.error.HTTPError) and 400 <= exc.code < 500 and exc.code != 429:
                break
            if attempt < retries:
                time.sleep(backoff_s * (2**attempt))
    raise FetchError(f"GET {url} failed: {last}") from last
