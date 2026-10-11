"""Single-table storage interface (mirrors the DynamoDB design in docs/SPEC.md §12).

Items are plain JSON-able dicts addressed by (pk, sk). `MemoryStore` backs local mode and tests; a DynamoDB
implementation backs the cloud.
"""

from __future__ import annotations

import bisect
import copy
import threading
from typing import Any, Protocol

Item = dict[str, Any]


class Store(Protocol):
    def put(self, pk: str, sk: str, item: Item) -> None: ...

    def get(self, pk: str, sk: str) -> Item | None: ...

    def query(
        self,
        pk: str,
        sk_prefix: str = "",
        limit: int | None = None,
        newest_first: bool = False,
        sk_from: str | None = None,
    ) -> list[Item]: ...

    def update(self, pk: str, sk: str, fields: Item) -> None:
        """Write only these fields, leaving the rest of the item as another writer may just have set it."""
        ...

    def delete(self, pk: str, sk: str) -> None: ...


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, dict[str, Item]] = {}
        self._keys: dict[str, list[str]] = {}
        self._lock = threading.RLock()

    def put(self, pk: str, sk: str, item: Item) -> None:
        with self._lock:
            part = self._data.setdefault(pk, {})
            if sk not in part:
                bisect.insort(self._keys.setdefault(pk, []), sk)
            part[sk] = copy.deepcopy({**item, "pk": pk, "sk": sk})

    def get(self, pk: str, sk: str) -> Item | None:
        with self._lock:
            item = self._data.get(pk, {}).get(sk)
            return copy.deepcopy(item) if item is not None else None

    def query(
        self,
        pk: str,
        sk_prefix: str = "",
        limit: int | None = None,
        newest_first: bool = False,
        sk_from: str | None = None,
    ) -> list[Item]:
        with self._lock:
            keys = [
                k
                for k in self._keys.get(pk, [])
                if k.startswith(sk_prefix) and (sk_from is None or k >= sk_from)
            ]
            if newest_first:
                keys.reverse()
            if limit is not None:
                keys = keys[:limit]
            return [copy.deepcopy(self._data[pk][k]) for k in keys]

    def update(self, pk: str, sk: str, fields: Item) -> None:
        with self._lock:
            current = self._data.get(pk, {}).get(sk) or {}
            self.put(pk, sk, {**current, **fields})

    def delete(self, pk: str, sk: str) -> None:
        with self._lock:
            if self._data.get(pk, {}).pop(sk, None) is not None:
                self._keys[pk].remove(sk)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self._keys.clear()
