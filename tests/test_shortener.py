import unittest

from src.shortener import URLShortener


class URLShortenerTests(unittest.TestCase):
    def test_codes_use_incrementing_ids_and_duplicates_reuse_the_code(self):
        for strategy in ("chaining", "linear"):
            with self.subTest(strategy=strategy):
                shortener = URLShortener(strategy=strategy)
                first_url = "https://example.com/first"
                second_url = "https://example.com/second"

                first_code = shortener.shorten(first_url)
                self.assertEqual(first_code, "0")
                self.assertEqual(shortener.shorten(first_url), first_code)
                self.assertEqual(shortener.shorten(second_url), "1")
                self.assertEqual(shortener.expand("0"), first_url)
                self.assertEqual(shortener.expand("1"), second_url)

    def test_rejects_invalid_urls_and_unknown_codes(self):
        shortener = URLShortener()
        for url in ("", "ftp://example.com", "https:///missing-host"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

        with self.assertRaises(KeyError):
            shortener.expand("missing")

    def test_rejects_non_string_urls(self):
        shortener = URLShortener()
        with self.assertRaises(TypeError):
            shortener.shorten(None)


if __name__ == "__main__":
    unittest.main()
