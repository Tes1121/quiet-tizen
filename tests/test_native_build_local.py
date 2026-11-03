"""Tests local archive creation; no Samsung device or real DLL is used."""
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_native_local import make_archive


class NativeLocalBuildTests(unittest.TestCase):
    def test_archive_contains_expected_relative_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            package = base / "package"
            (package / "quiet-home").mkdir(parents=True)
            (package / "BixbyPromotion.dll").write_bytes(b"synthetic")
            (package / "quiet-home/apps.json").write_text("[]", encoding="utf-8")
            output = base / "output/package.tar.gz"
            digest = make_archive(package, output)
            self.assertEqual(len(digest), 64)
            with tarfile.open(output) as archive:
                self.assertEqual(sorted(archive.getnames()),
                                 ["BixbyPromotion.dll", "quiet-home/apps.json"])

    def test_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            package = base / "package"
            package.mkdir()
            private = base / "private.txt"
            private.write_text("do not package", encoding="utf-8")
            (package / "bad-link").symlink_to(private)
            with self.assertRaisesRegex(ValueError, "symlink"):
                make_archive(package, base / "output.tar.gz")
            self.assertFalse((base / "output.tar.gz").exists())


if __name__ == "__main__":
    unittest.main()
