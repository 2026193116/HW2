import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.server import URLShortener, create_server


class ServerTests(unittest.TestCase):
    strategy = "chaining"

    def setUp(self):
        self.server = create_server("127.0.0.1", 0, strategy=self.strategy)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port
        )
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = (
            response.status,
            response.getheader("Location"),
            response.read().decode("utf-8"),
        )
        connection.close()
        return result

    def shorten(self, url):
        body = urlencode({"url": url})
        return self.request(
            "POST",
            "/shorten",
            body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    def test_home_form_and_short_url_redirect(self):
        status, _, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn('action="/shorten"', body)
        self.assertIn('name="url"', body)

        url = "https://example.com/article?id=7"
        status, _, body = self.shorten(url)
        self.assertEqual(status, 200)
        self.assertIn('href="/r/0"', body)

        status, location, _ = self.request("GET", "/r/0")
        self.assertEqual(status, 302)
        self.assertEqual(location, url)

    def test_table_shows_chain_nodes_and_hash_steps(self):
        url = "https://example.com/a"
        self.shorten(url)

        status, _, body = self.request("GET", "/table")
        self.assertEqual(status, 200)
        self.assertIn("URL 키:", body)
        self.assertIn(url, body)
        self.assertIn("짧은 코드:", body)
        self.assertIn('href="/r/0"', body)
        self.assertIn("Horner 해시 계산 보기", body)
        self.assertIn("<details>", body)
        self.assertIn("→", body)

    def test_linear_strategy_and_table_show_probe_path(self):
        self.server.shortener = URLShortener(strategy="linear")
        table = self.server.shortener.table
        urls = [
            f"https://wrap.example/{index}"
            for index in range(100)
            if table.hash_details(f"https://wrap.example/{index}")[0] == 7
        ][:3]
        self.assertEqual(len(urls), 3)
        for url in urls:
            self.server.shortener.shorten(url)

        status, _, body = self.request("GET", "/table")
        self.assertEqual(status, 200)
        self.assertIn("선형 탐지", body)
        self.assertIn("탐색한 칸: 7 → 0 → 1", body)
        self.assertIn("(현재 칸 + 1) % 8", body)
        self.assertIn("Horner 해시 계산 보기", body)

    def test_shortener_validates_urls_and_unknown_codes_raise(self):
        shortener = URLShortener(strategy="linear")
        with self.assertRaises(ValueError):
            shortener.shorten("javascript:alert(1)")
        with self.assertRaises(ValueError):
            shortener.shorten("https:///missing-host")

        code = shortener.shorten("https://example.com/")
        self.assertEqual(shortener.expand(code), "https://example.com/")
        with self.assertRaises(KeyError):
            shortener.expand("unknown")

    def test_duplicate_urls_reuse_the_same_code(self):
        url = "https://example.com/repeated"
        first_status, _, first_body = self.shorten(url)
        second_status, _, second_body = self.shorten(url)

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertIn('href="/r/0"', first_body)
        self.assertIn('href="/r/0"', second_body)

    def test_invalid_url_and_unknown_short_code(self):
        status, _, _ = self.shorten("javascript:alert(1)")
        self.assertEqual(status, 400)

        status, _, _ = self.request("GET", "/r/unknown")
        self.assertEqual(status, 404)


class LinearServerTests(ServerTests):
    strategy = "linear"


if __name__ == "__main__":
    unittest.main()
