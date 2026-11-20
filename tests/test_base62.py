import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_zero_encodes_as_zero(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(decode("0"), 0)

    def test_alphabet_boundaries(self):
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)

    def test_round_trip_large_values(self):
        for value in (1, 12345, 2**64, 10**100):
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            encode(-1)
        with self.assertRaises(TypeError):
            encode(True)
        with self.assertRaises(ValueError):
            decode("")
        with self.assertRaises(ValueError):
            decode("a!")

    def test_rejects_wrong_input_types(self):
        with self.assertRaises(TypeError):
            encode(1.5)
        with self.assertRaises(TypeError):
            decode(62)


if __name__ == "__main__":
    unittest.main()
