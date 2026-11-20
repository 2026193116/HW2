"""A string-keyed hash table using separate chaining."""

from collections.abc import Iterator
from typing import Generic, TypeVar

Value = TypeVar("Value")


class HashTable(Generic[Value]):
    def __init__(self, capacity: int = 8, max_load_factor: float = 0.75) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if not 0 < max_load_factor <= 1:
            raise ValueError("max_load_factor must be greater than 0 and at most 1")
        self._buckets: list[list[tuple[str, Value]]] = [
            [] for _ in range(capacity)
        ]
        self._size = 0
        self._max_load_factor = max_load_factor

    @property
    def capacity(self) -> int:
        return len(self._buckets)

    def _require_key(self, key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def hash_details(self, key: str) -> tuple[int, list[tuple[str, int, int]]]:
        """Return the bucket index and each Horner-hash calculation step."""
        self._require_key(key)
        value = 0
        steps = []
        for character in key:
            previous = value
            value = (31 * value + ord(character)) % self.capacity
            steps.append((character, previous, value))
        return value, steps

    def _bucket_index(self, key: str) -> int:
        return self.hash_details(key)[0]

    def _find(self, key: str) -> tuple[list[tuple[str, Value]], int | None, int]:
        bucket = self._buckets[self._bucket_index(key)]
        for position, (stored_key, _) in enumerate(bucket):
            if stored_key == key:
                return bucket, position, position + 1
        return bucket, None, len(bucket)

    def put(self, key: str, value: Value) -> None:
        self._require_key(key)
        bucket, position, _ = self._find(key)
        if position is not None:
            bucket[position] = (key, value)
            return

        if (self._size + 1) / self.capacity > self._max_load_factor:
            self._resize(self.capacity * 2)
            bucket = self._buckets[self._bucket_index(key)]
        bucket.append((key, value))
        self._size += 1

    def get(self, key: str) -> Value | None:
        self._require_key(key)
        bucket, position, _ = self._find(key)
        if position is None:
            return None
        return bucket[position][1]

    def contains(self, key: str) -> bool:
        self._require_key(key)
        _, position, _ = self._find(key)
        return position is not None

    def probe_count(self, key: str) -> int:
        """Return the number of keys compared while searching for key."""
        self._require_key(key)
        return self._find(key)[2]

    def items(self) -> Iterator[tuple[str, Value]]:
        for bucket in self._buckets:
            yield from bucket

    def __len__(self) -> int:
        return self._size

    def _resize(self, capacity: int) -> None:
        old_items = list(self.items())
        self._buckets = [[] for _ in range(capacity)]
        self._size = 0
        for key, value in old_items:
            self._buckets[self._bucket_index(key)].append((key, value))
            self._size += 1
