import unittest

from src.hash_table import HashTable


class HashTableEdgeCaseTests(unittest.TestCase):
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
