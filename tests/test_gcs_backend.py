"""GCS backend tests using a fake bucket. No Google credentials required."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cursor_saves.backends import GCSBackend, normalize_gcs_bucket


class FakeBlob:
    def __init__(self, name: str, data: bytes = b"", updated: datetime | None = None):
        self.name = name
        self._data = data
        self.updated = updated or datetime.now(timezone.utc)
        self.size = len(data)

    def download_to_filename(self, path: str) -> None:
        Path(path).write_bytes(self._data)

    def upload_from_filename(self, path: str) -> None:
        self._data = Path(path).read_bytes()
        self.size = len(self._data)
        self.updated = datetime.now(timezone.utc)


class FakeBucket:
    def __init__(self):
        self.blobs: dict[str, FakeBlob] = {}

    def exists(self) -> bool:
        return True

    def list_blobs(self, prefix: str = ""):
        return [blob for name, blob in self.blobs.items() if name.startswith(prefix)]

    def blob(self, name: str) -> FakeBlob:
        if name not in self.blobs:
            self.blobs[name] = FakeBlob(name)
        return self.blobs[name]


def _set_mtime(path: Path, when: datetime) -> None:
    stamp = when.timestamp()
    os.utime(path, (stamp, stamp))


class GCSBackendTests(unittest.TestCase):
    def test_normalize_bucket_name(self):
        self.assertEqual(normalize_gcs_bucket("gs://my-bucket/"), "my-bucket")
        self.assertEqual(normalize_gcs_bucket("my-bucket"), "my-bucket")
        with self.assertRaises(ValueError):
            normalize_gcs_bucket("gs://my-bucket/prefix")

    def test_push_and_pull_round_trip(self):
        bucket = FakeBucket()
        backend = GCSBackend(bucket="gs://my-bucket", prefix="snapshots")
        backend._bucket = bucket

        with tempfile.TemporaryDirectory() as src_name, tempfile.TemporaryDirectory() as dst_name:
            src = Path(src_name)
            dst = Path(dst_name)
            snapshot = src / "proj" / "chat.json.gz"
            snapshot.parent.mkdir()
            snapshot.write_bytes(b"chat-body")

            self.assertTrue(backend.push(src))
            stored = bucket.blobs["snapshots/proj/chat.json.gz"]
            self.assertEqual(stored._data, b"chat-body")

            self.assertTrue(backend.push(src))
            self.assertTrue(backend.pull(dst))
            self.assertEqual((dst / "proj" / "chat.json.gz").read_bytes(), b"chat-body")

    def test_push_skips_unchanged_object(self):
        bucket = FakeBucket()
        backend = GCSBackend(bucket="my-bucket", prefix="snapshots/")
        backend._bucket = bucket
        uploads = {"count": 0}
        original_upload = FakeBlob.upload_from_filename

        def counting_upload(blob, path: str) -> None:
            uploads["count"] += 1
            original_upload(blob, path)

        FakeBlob.upload_from_filename = counting_upload
        try:
            with tempfile.TemporaryDirectory() as src_name:
                src = Path(src_name)
                snapshot = src / "chat.json.gz"
                snapshot.write_bytes(b"same")
                remote_time = datetime.now(timezone.utc) - timedelta(days=1)
                bucket.blobs["snapshots/chat.json.gz"] = FakeBlob(
                    "snapshots/chat.json.gz", b"same", updated=remote_time
                )
                _set_mtime(snapshot, remote_time - timedelta(minutes=1))

                self.assertTrue(backend.push(src))
                self.assertEqual(uploads["count"], 0)
        finally:
            FakeBlob.upload_from_filename = original_upload

    def test_pull_skips_local_copy_that_matches(self):
        bucket = FakeBucket()
        backend = GCSBackend(bucket="my-bucket")
        backend._bucket = bucket
        downloads = {"count": 0}
        original_download = FakeBlob.download_to_filename

        def counting_download(blob, path: str) -> None:
            downloads["count"] += 1
            original_download(blob, path)

        FakeBlob.download_to_filename = counting_download
        try:
            with tempfile.TemporaryDirectory() as dst_name:
                dst = Path(dst_name)
                local = dst / "chat.json.gz"
                local.write_bytes(b"same")
                remote_time = datetime.now(timezone.utc) - timedelta(hours=1)
                _set_mtime(local, remote_time + timedelta(seconds=30))
                bucket.blobs["snapshots/chat.json.gz"] = FakeBlob(
                    "snapshots/chat.json.gz", b"same", updated=remote_time
                )
                self.assertTrue(backend.pull(dst))
                self.assertEqual(downloads["count"], 0)
        finally:
            FakeBlob.download_to_filename = original_download


if __name__ == "__main__":
    unittest.main()
