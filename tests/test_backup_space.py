"""A full copy of the Cursor database is skipped when the disk cannot hold it."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cursor_saves import db


class BackupSpaceTests(unittest.TestCase):
    def test_skips_copy_when_the_volume_is_short(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "state.vscdb"
            db_path.write_bytes(b"x" * 1024)
            with patch.object(db.shutil, "disk_usage", return_value=SimpleNamespace(free=0)):
                result = db.backup_db(db_path)
            self.assertIsNone(result)
            self.assertEqual(list(Path(tmp).glob("state.vscdb.backup_*")), [])


if __name__ == "__main__":
    unittest.main()
