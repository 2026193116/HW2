"""In-memory URL shortener web server."""

import argparse
import html
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT_DIRECTORY = Path(__file__).resolve().parents[1]
if str(ROOT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(ROOT_DIRECTORY))

from src.base62 import encode
from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable

MAX_REQUEST_BYTES = 16_384


class URLShortener:
    def __init__(self, strategy: str = "chaining") -> None:
        if strategy == "chaining":
            self.table: HashTable[str] | LinearProbingHashTable[str] = HashTable()
        elif strategy == "linear":
            self.table = LinearProbingHashTable()
        else:
            raise ValueError("strategy must be 'chaining' or 'linear'")
        self.strategy = strategy

    def shorten(self, url: str) -> str:
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if not is_http_url(url):
            raise ValueError("url must be an absolute HTTP or HTTPS URL")
        existing_code = self.table.get(url)
        if existing_code is not None:
            return existing_code

        code = encode(len(self.table))
        self.table.put(url, code)
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


def page(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font: 16px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 1000px; padding: 0 1rem; color: #202124; }}
    a {{ color: #0759a5; }}
    input[type=url] {{ box-sizing: border-box; max-width: 42rem; padding: .65rem; width: 100%; }}
    button {{ cursor: pointer; margin-top: .75rem; padding: .6rem 1rem; }}
    code {{ overflow-wrap: anywhere; }}
    .error {{ color: #a11; }}
    .result, .node {{ border: 1px solid #ccd2d8; border-radius: .5rem; padding: .8rem; }}
    .chain {{ align-items: center; display: flex; flex-wrap: wrap; gap: .55rem; margin: .5rem 0 1rem; }}
    .node {{ background: #f7f9fb; max-width: 100%; }}
    .node p {{ margin: .2rem 0; }}
    .arrow {{ color: #586574; font-weight: bold; }}
    .hash-steps {{ max-height: 18rem; overflow: auto; }}
    .hash-steps li {{ margin: .2rem 0; }}
    nav {{ display: flex; gap: 1rem; margin: 1rem 0; }}
  </style>
</head>
<body>
  <h1>{html.escape(title)}</h1>
  <nav><a href="/">URL 줄이기</a><a href="/table">해시 테이블</a></nav>
  {content}
</body>
</html>
"""


def render_form(url: str = "", error: str | None = None) -> str:
    error_content = (
        f'<p class="error">{html.escape(error)}</p>' if error is not None else ""
    )
    content = f"""{error_content}
<form action="/shorten" method="post">
  <label for="url">원래 URL</label><br>
  <input id="url" name="url" type="url" required value="{html.escape(url, quote=True)}" placeholder="https://example.com/">
  <br><button type="submit">줄이기</button>
</form>"""
    return page("URL 단축기", content)


def render_result(url: str, code: str) -> str:
    short_path = f"/r/{html.escape(code, quote=True)}"
    content = f"""<section class="result">
  <p>짧은 링크: <a href="{short_path}">{short_path}</a></p>
  <p>원래 URL: <code>{html.escape(url)}</code></p>
</section>
<p><a href="/">다른 URL 줄이기</a></p>"""
    return page("단축 완료", content)


def render_table(shortener: URLShortener) -> str:
    if isinstance(shortener.table, LinearProbingHashTable):
        return render_linear_table(shortener)

    buckets: list[list[tuple[str, str]]] = [
        [] for _ in range(shortener.table.capacity)
    ]
    for bucket_index, url, code in shortener.table.bucket_items():
        buckets[bucket_index].append((url, code))

    capacity = shortener.table.capacity
    load_factor = len(shortener.table) / capacity
    content = [
        f"<p>칸 수: {capacity} · 저장된 URL: {len(shortener.table)} · 적재율: {load_factor:.3f}</p>"
    ]
    for bucket_index, entries in enumerate(buckets):
        content.append('<div class="chain">')
        content.append(f'<strong>칸 {bucket_index}</strong><span class="arrow">→</span>')
        if not entries:
            content.append("<span>∅</span>")
        else:
            for url, code in entries:
                bucket, steps = shortener.table.hash_details(url)
                content.append('<article class="node">')
                content.append(f"<p>URL 키: <code>{html.escape(url)}</code></p>")
                content.append(f"<p>짧은 코드: <code>{html.escape(code)}</code></p>")
                short_path = f"/r/{html.escape(code, quote=True)}"
                content.append(
                    f'<p>짧은 링크: <a href="{short_path}">{short_path}</a></p>'
                )
                content.append(
                    f"<p>성공 탐색 비교 노드: {shortener.table.probe_count(url)}</p>"
                )
                content.append(
                    f"<details><summary>Horner 해시 계산 보기 (칸 {bucket})</summary><ol class=\"hash-steps\">"
                )
                for character, previous, result in steps:
                    character_text = html.escape(repr(character))
                    content.append(
                        f"<li><code>({previous} × 31 + {ord(character)}) % {capacity} = {result}</code> "
                        f"<span>문자 {character_text}</span></li>"
                    )
                content.append("</ol></details></article>")
                content.append('<span class="arrow">→</span>')
            content.append("<span>∅</span>")
        content.append("</div>")

    return page("현재 해시 테이블", "\n".join(content))


def render_linear_table(shortener: URLShortener) -> str:
    table = shortener.table
    if not isinstance(table, LinearProbingHashTable):
        raise TypeError("linear table rendering requires linear probing")

    capacity = table.capacity
    load_factor = len(table) / capacity
    content = [
        f"<p>방식: 선형 탐지 · 칸 수: {capacity} · 저장된 URL: {len(table)} · 적재율: {load_factor:.3f}</p>"
    ]
    for slot_index, slot in table.slot_items():
        content.append('<div class="chain">')
        content.append(f'<strong>칸 {slot_index}</strong><span class="arrow">→</span>')
        if slot is None:
            content.append("<span>∅ (비어 있음)</span>")
        else:
            url, code = slot
            home, steps = table.hash_details(url)
            path = table.probe_path(url)
            content.append('<article class="node">')
            content.append(f"<p>URL 키: <code>{html.escape(url)}</code></p>")
            content.append(f"<p>짧은 코드: <code>{html.escape(code)}</code></p>")
            short_path = f"/r/{html.escape(code, quote=True)}"
            content.append(
                f'<p>짧은 링크: <a href="{short_path}">{short_path}</a></p>'
            )
            content.append(
                f"<p>성공 탐색 확인 칸 수: {table.probe_count(url)}</p>"
            )
            content.append(
                f"<p>탐색한 칸: {' → '.join(str(index) for index in path)}</p>"
            )
            content.append(
                f"<p>계산 근거: 시작 칸은 Horner 해시 {home}; 충돌 시 "
                f"(현재 칸 + 1) % {capacity}로 이동합니다.</p>"
            )
            content.append(
                f"<details><summary>Horner 해시 계산 보기 (시작 칸 {home})</summary>"
                '<ol class="hash-steps">'
            )
            for character, previous, result in steps:
                character_text = html.escape(repr(character))
                content.append(
                    f"<li><code>({previous} × 31 + {ord(character)}) % {capacity} = {result}</code> "
                    f"<span>문자 {character_text}</span></li>"
                )
            content.append("</ol></details></article>")
            content.append('<span class="arrow">→</span><span>∅</span>')
        content.append("</div>")

    return page("현재 해시 테이블", "\n".join(content))


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    def _shortener(self) -> URLShortener:
        if not isinstance(self.server, ShortenerHTTPServer):
            raise RuntimeError("request handler requires ShortenerHTTPServer")
        return self.server.shortener

    def _send_html(self, content: str, status: int = 200) -> None:
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/":
            self._send_html(render_form())
            return
        if path == "/table":
            self._send_html(render_table(self._shortener()))
            return
        if path.startswith("/r/"):
            code = path.removeprefix("/r/")
            try:
                url = self._shortener().expand(code)
            except KeyError:
                self.send_error(404, "Short URL not found")
                return
            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_error(404, "Page not found")

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/shorten":
            self.send_error(404, "Page not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400, "Invalid Content-Length")
            return
        if content_length <= 0:
            self.send_error(400, "Request body is required")
            return
        if content_length > MAX_REQUEST_BYTES:
            self.send_error(413, "Request body is too large")
            return

        try:
            body = self.rfile.read(content_length).decode("utf-8")
        except UnicodeDecodeError:
            self.send_error(400, "Request body must be UTF-8")
            return
        try:
            form = parse_qs(body, keep_blank_values=True, max_num_fields=16)
        except ValueError:
            self.send_error(400, "Too many form fields")
            return
        url = form.get("url", [""])[0]
        if not is_http_url(url):
            self._send_html(
                render_form(url, "HTTP 또는 HTTPS 주소를 입력해 주세요."), 400
            )
            return

        code = self._shortener().shorten(url)
        self._send_html(render_result(url, code))


class ShortenerHTTPServer(HTTPServer):
    def __init__(self, address: tuple[str, int], strategy: str = "chaining") -> None:
        self.shortener = URLShortener(strategy)
        super().__init__(address, ShortenerRequestHandler)


def create_server(
    host: str = "0.0.0.0", port: int = 8000, strategy: str = "chaining"
) -> ShortenerHTTPServer:
    return ShortenerHTTPServer((host, port), strategy)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--strategy", choices=("chaining", "linear"), default="chaining"
    )
    args = parser.parse_args()

    with create_server(port=args.port, strategy=args.strategy) as server:
        print(f"Serving on http://0.0.0.0:{server.server_port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()
