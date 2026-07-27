import tempfile
from pathlib import Path
import unittest

from scripts.migrate_storage_paths import PathMigrationError, rewrite_storage_path


class StoragePathMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_root = Path(self.temp_dir.name).resolve()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _file(self, relative: str) -> Path:
        target = self.storage_root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"test")
        return target

    def test_rewrites_windows_storage_path(self):
        target = self._file("raw/classes/1/lecture.pdf")
        rewritten = rewrite_storage_path(
            r"C:\work\backend\storage\raw\classes\1\lecture.pdf",
            storage_root=self.storage_root,
        )
        self.assertEqual(rewritten, target.as_posix())

    def test_preserves_relative_chat_image_path(self):
        self._file("raw/chat_images/1/abc.png")
        rewritten = rewrite_storage_path(
            "1/abc.png",
            storage_root=self.storage_root,
            chat_image=True,
        )
        self.assertEqual(rewritten, "1/abc.png")

    def test_converts_absolute_chat_image_to_relative(self):
        self._file("raw/chat_images/1/abc.png")
        rewritten = rewrite_storage_path(
            r"C:\work\backend\storage\raw\chat_images\1\abc.png",
            storage_root=self.storage_root,
            chat_image=True,
        )
        self.assertEqual(rewritten, "1/abc.png")

    def test_rejects_missing_file(self):
        with self.assertRaises(PathMigrationError):
            rewrite_storage_path(
                r"C:\work\backend\storage\raw\classes\1\missing.pdf",
                storage_root=self.storage_root,
            )

    def test_rejects_path_outside_storage(self):
        with self.assertRaises(PathMigrationError):
            rewrite_storage_path(
                r"C:\work\outside\secret.txt",
                storage_root=self.storage_root,
            )
