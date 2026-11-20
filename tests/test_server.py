import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.server import create_server


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server("127.0.0.1", 0)
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


if __name__ == "__main__":
    unittest.main()
