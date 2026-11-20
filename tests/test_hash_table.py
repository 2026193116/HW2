import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_insert_lookup_update_and_missing_key(self):
        table = HashTable()
        table.put("first", 1)
        table.put("first", 2)

        self.assertEqual(table.get("first"), 2)
        self.assertTrue(table.contains("first"))
        self.assertIsNone(table.get("missing"))
        self.assertFalse(table.contains("missing"))
        self.assertEqual(len(table), 1)

    def test_collisions_are_kept_and_counted(self):
        table = HashTable(capacity=8)
        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(table.probe_count("q"), 2)

    def test_resizes_before_exceeding_default_load_factor(self):
        table = HashTable(capacity=8)
        for value in range(6):
            table.put(f"key-{value}", value)
        self.assertEqual(table.capacity, 8)

        table.put("key-6", 6)

        self.assertGreaterEqual(table.capacity, 16)
        for value in range(7):
            self.assertEqual(table.get(f"key-{value}"), value)

    def test_items_contains_all_entries(self):
        table = HashTable()
        table.put("one", 1)
        table.put("two", 2)

        self.assertCountEqual(list(table.items()), [("one", 1), ("two", 2)])


if __name__ == "__main__":
    unittest.main()
