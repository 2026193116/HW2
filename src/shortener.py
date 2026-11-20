"""URL shortening logic backed by a selectable hash table."""

from urllib.parse import urlsplit

from src.base62 import encode
from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable


class URLShortener:
    def __init__(self, strategy: str = "chaining") -> None:
        if strategy == "chaining":
            self.table: HashTable[str] | LinearProbingHashTable[str] = HashTable()
        elif strategy == "linear":
            self.table = LinearProbingHashTable()
        else:
            raise ValueError("strategy must be 'chaining' or 'linear'")
        self.strategy = strategy
        self._next_id = 0

    def shorten(self, url: str) -> str:
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if not is_http_url(url):
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        existing_code = self.table.get(url)
        if existing_code is not None:
            return existing_code

        code = encode(self._next_id)
        self.table.put(url, code)
        self._next_id += 1
        return code

    def expand(self, code: str) -> str:
        for url, stored_code in self.table.items():
            if stored_code == code:
                return url
        raise KeyError(code)


def is_http_url(value: str) -> bool:
    if (
        not value
        or value != value.strip()
        or any(character.isspace() for character in value)
    ):
        return False

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError:
        return False

    return parsed.scheme.lower() in ("http", "https") and hostname is not None
