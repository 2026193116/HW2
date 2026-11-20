"""A string-keyed hash table using linear probing."""

from collections.abc import Iterator
from typing import Generic, TypeVar

Value = TypeVar("Value")


class LinearProbingHashTable(Generic[Value]):
    def __init__(
        self,
        capacity: int = 8,
        max_load: float | None = 0.75,
        *,
        max_load_factor: float | None = None,
    ) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        if max_load_factor is not None:
            max_load = max_load_factor
        if max_load is not None and not 0 < max_load <= 1:
            raise ValueError("max_load must be greater than 0 and at most 1")
        self._slots: list[tuple[str, Value] | None] = [None for _ in range(capacity)]
        self._size = 0
        self._max_load_factor = max_load

    @property
    def capacity(self) -> int:
        return len(self._slots)

    def _require_key(self, key: str) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

    def hash_details(self, key: str) -> tuple[int, list[tuple[str, int, int]]]:
        """Return the home slot and each Horner-hash calculation step."""
        self._require_key(key)
        value = 0
        steps = []
        for character in key:
            previous = value
            value = (31 * value + ord(character)) % self.capacity
            steps.append((character, previous, value))
        return value, steps

    def _find(self, key: str) -> tuple[int | None, int, bool]:
        index = self.hash_details(key)[0]
        for probes in range(1, self.capacity + 1):
            slot = self._slots[index]
            if slot is None:
                return index, probes, False
            if slot[0] == key:
                return index, probes, True
            index = (index + 1) % self.capacity
        return None, self.capacity, False

    def put(self, key: str, value: Value) -> None:
        self._require_key(key)
        index, _, found = self._find(key)
        if found:
            assert index is not None
            self._slots[index] = (key, value)
            return

        if self._size == self.capacity and self._max_load_factor == 1:
            raise OverflowError("hash table is full")
        if (
            self._max_load_factor is not None
            and (self._size + 1) / self.capacity > self._max_load_factor
        ):
            self._resize(self.capacity * 2)
            index, _, _ = self._find(key)
        if index is None:
            raise OverflowError("hash table is full")

        self._slots[index] = (key, value)
        self._size += 1

    def get(self, key: str) -> Value | None:
        self._require_key(key)
        index, _, found = self._find(key)
        if not found or index is None:
            return None
        slot = self._slots[index]
        assert slot is not None
        return slot[1]

    def contains(self, key: str) -> bool:
        self._require_key(key)
        _, _, found = self._find(key)
        return found

    def probe_count(self, key: str) -> int:
        """Return the number of slots inspected while searching for key."""
        self._require_key(key)
        return self._find(key)[1]

    def probe_path(self, key: str) -> list[int]:
        """Return the slot indices inspected by a lookup for key."""
        self._require_key(key)
        index = self.hash_details(key)[0]
        path = []
        for _ in range(self.capacity):
            path.append(index)
            slot = self._slots[index]
            if slot is None or slot[0] == key:
                break
            index = (index + 1) % self.capacity
        return path

    def items(self) -> Iterator[tuple[str, Value]]:
        for slot in self._slots:
            if slot is not None:
                yield slot

    def bucket_items(self) -> Iterator[tuple[int, str, Value]]:
        for index, slot in enumerate(self._slots):
            if slot is not None:
                yield index, slot[0], slot[1]

    def slot_items(self) -> Iterator[tuple[int, tuple[str, Value] | None]]:
        for index, slot in enumerate(self._slots):
            yield index, slot

    def __len__(self) -> int:
        return self._size

    def _resize(self, capacity: int) -> None:
        old_items = list(self.items())
        self._slots = [None for _ in range(capacity)]
        self._size = 0
        for key, value in old_items:
            self.put(key, value)
