import unittest

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable


class HashTableTests(unittest.TestCase):
    table_type = HashTable

    def make_table(self, *args, **kwargs):
        return self.table_type(*args, **kwargs)

    def test_insert_lookup_update_and_missing_key(self):
        table = self.make_table()
        table.put("first", 1)
        table.put("first", 2)

        self.assertEqual(table.get("first"), 2)
        self.assertTrue(table.contains("first"))
        self.assertIsNone(table.get("missing"))
        self.assertFalse(table.contains("missing"))
        self.assertEqual(len(table), 1)

    def test_collisions_are_kept_and_counted(self):
        table = self.make_table(capacity=8)
        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        expected_missing_probes = (
            3 if self.table_type is LinearProbingHashTable else 2
        )
        self.assertEqual(table.probe_count("q"), expected_missing_probes)

    def test_resizes_before_exceeding_default_load_factor(self):
        table = self.make_table(capacity=8)
        for value in range(6):
            table.put(f"key-{value}", value)
        self.assertEqual(table.capacity, 8)

        table.put("key-6", 6)

        self.assertGreaterEqual(table.capacity, 16)
        for value in range(7):
            self.assertEqual(table.get(f"key-{value}"), value)

    def test_none_max_load_disables_resizing(self):
        table = self.make_table(capacity=4, max_load=None)
        for value in range(4):
            table.put(f"key-{value}", value)

        self.assertEqual(table.capacity, 4)
        self.assertEqual(len(table), 4)
        for value in range(4):
            self.assertEqual(table.get(f"key-{value}"), value)

    def test_items_contains_all_entries(self):
        table = self.make_table()
        table.put("one", 1)
        table.put("two", 2)

        self.assertCountEqual(list(table.items()), [("one", 1), ("two", 2)])

    def test_full_table_at_load_factor_one_rejects_new_keys(self):
        table = self.make_table(capacity=2, max_load=1.0)
        table.put("a", 1)
        table.put("c", 2)

        with self.assertRaises(OverflowError):
            table.put("e", 3)

        table.put("c", 4)
        self.assertEqual(table.get("c"), 4)
        self.assertEqual(len(table), 2)


class LinearProbingTests(HashTableTests):
    table_type = LinearProbingHashTable

    def test_probe_wraps_from_last_slot_to_zero(self):
        table = self.make_table(capacity=4, max_load=None)
        for key in ("c", "g", "k"):
            table.put(key, key)

        self.assertEqual(table.probe_path("k"), [3, 0, 1])
        self.assertEqual(table.probe_count("k"), 3)
        self.assertEqual(table.probe_path("o"), [3, 0, 1, 2])
        self.assertEqual(table.probe_count("o"), 4)


if __name__ == "__main__":
    unittest.main()
