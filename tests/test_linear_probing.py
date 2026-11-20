import unittest

from src.linear_probing import LinearProbingHashTable


class LinearProbingTests(unittest.TestCase):
    def test_insert_lookup_update_and_missing_key(self):
        table = LinearProbingHashTable()
        table.put("first", 1)
        table.put("first", 2)

        self.assertEqual(table.get("first"), 2)
        self.assertTrue(table.contains("first"))
        self.assertIsNone(table.get("missing"))
        self.assertFalse(table.contains("missing"))
        self.assertEqual(len(table), 1)

    def test_collisions_and_wraparound_are_counted(self):
        table = LinearProbingHashTable(capacity=4, max_load=None)
        for key in ("c", "g", "k"):
            table.put(key, key)

        self.assertEqual(table.get("c"), "c")
        self.assertEqual(table.get("g"), "g")
        self.assertEqual(table.get("k"), "k")
        self.assertEqual(table.probe_path("k"), [3, 0, 1])
        self.assertEqual(table.probe_count("k"), 3)
        self.assertEqual(table.probe_path("o"), [3, 0, 1, 2])
        self.assertEqual(table.probe_count("o"), 4)

    def test_resizes_before_exceeding_default_load_factor(self):
        table = LinearProbingHashTable(capacity=8)
        for value in range(7):
            table.put(f"key-{value}", value)

        self.assertGreaterEqual(table.capacity, 16)
        for value in range(7):
            self.assertEqual(table.get(f"key-{value}"), value)

    def test_full_table_at_load_factor_one_rejects_new_keys(self):
        table = LinearProbingHashTable(capacity=2, max_load=1.0)
        table.put("a", 1)
        table.put("c", 2)

        with self.assertRaises(OverflowError):
            table.put("e", 3)

        table.put("c", 4)
        self.assertEqual(table.get("c"), 4)
        self.assertEqual(len(table), 2)

    def test_items_and_none_load_factor(self):
        table = LinearProbingHashTable(capacity=2, max_load=None)
        table.put("one", 1)
        table.put("two", 2)

        self.assertEqual(table.capacity, 2)
        self.assertCountEqual(list(table.items()), [("one", 1), ("two", 2)])

    def test_keys_are_case_sensitive(self):
        table = LinearProbingHashTable()
        table.put("Key", 1)
        table.put("key", 2)

        self.assertEqual(len(table), 2)
        self.assertEqual(table.get("Key"), 1)
        self.assertEqual(table.get("key"), 2)

    def test_empty_lookup_and_non_string_keys(self):
        table = LinearProbingHashTable()
        self.assertIsNone(table.get("missing"))
        self.assertFalse(table.contains("missing"))
        self.assertEqual(table.probe_count("missing"), 1)

        with self.assertRaises(TypeError):
            table.put(1, "value")
        with self.assertRaises(TypeError):
            table.get(1)


if __name__ == "__main__":
    unittest.main()
