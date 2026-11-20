import unittest

from src.hash_table import HashTable


class HashTableEdgeCaseTests(unittest.TestCase):
    def test_empty_lookup_and_probe_counts(self):
        table = HashTable(capacity=8, max_load=None)
        self.assertIsNone(table.get("missing"))
        self.assertEqual(table.probe_count("missing"), 0)

        table.put("a", "first")
        table.put("i", "second")
        self.assertEqual(table.probe_count("a"), 1)
        self.assertEqual(table.probe_count("i"), 2)
        self.assertEqual(table.probe_count("q"), 2)

    def test_keys_are_case_sensitive(self):
        table = HashTable()
        table.put("Key", 1)
        table.put("key", 2)

        self.assertEqual(len(table), 2)
        self.assertEqual(table.get("Key"), 1)
        self.assertEqual(table.get("key"), 2)

    def test_non_string_keys_are_rejected(self):
        table = HashTable()
        with self.assertRaises(TypeError):
            table.put(1, "value")
        with self.assertRaises(TypeError):
            table.get(1)

    def test_full_table_at_load_factor_one_rejects_new_keys(self):
        table = HashTable(capacity=2, max_load=1.0)
        table.put("a", 1)
        table.put("c", 2)

        with self.assertRaises(OverflowError):
            table.put("e", 3)

        table.put("c", 4)
        self.assertEqual(table.get("c"), 4)
        self.assertEqual(len(table), 2)


if __name__ == "__main__":
    unittest.main()
