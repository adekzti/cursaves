"""Prefix lookups must use the key index, not a full-table LIKE scan."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from cursor_saves.db import CursorDB, _prefix_range


class PrefixRangeTests(unittest.TestCase):
    def test_bounds_cover_only_the_prefix(self):
        start, end = _prefix_range("composer.content.")
        self.assertEqual(start, "composer.content.")
        self.assertTrue("composer.content.abc" >= start)
        self.assertTrue("composer.content.abc" < end)
        self.assertFalse("composer.contents" < end and "composer.contents" >= start)

    def test_list_keys_returns_prefix_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "state.vscdb"
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE cursorDiskKV (key TEXT PRIMARY KEY, value BLOB)")
            conn.executemany(
                "INSERT INTO cursorDiskKV (key, value) VALUES (?, ?)",
                [
                    ("composer.content.aaa", b"a"),
                    ("composer.content.bbb", b"b"),
                    ("bubbleId:other", b"c"),
                ],
            )
            conn.commit()
            conn.close()

            cdb = CursorDB(db_path)
            keys = cdb.list_keys("composer.content.")
            cdb.close()

        self.assertEqual(keys, ["composer.content.aaa", "composer.content.bbb"])


if __name__ == "__main__":
    unittest.main()
