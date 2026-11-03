"""Unit tests for the read-only native build readiness checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from native_preflight import (check_framework, check_package, check_source,
                              looks_like_managed_dll, REFERENCES, PACKAGE_DLLS)


def managed_fixture(path):
    # Synthetic signature only: NOT a real, deployable .NET assembly.
    path.write_bytes(b"MZ" + (b"\x00" * 700) + b"BSJB")


class NativePreflightTests(unittest.TestCase):
    def test_source_projects_and_ignore_rules(self):
        self.assertEqual(check_source(ROOT), [])

    def test_framework_must_contain_all_four_managed_assemblies(self):
        with tempfile.TemporaryDirectory() as directory:
            framework = Path(directory)
            self.assertEqual(len(check_framework(framework)), 4)
            for name in REFERENCES:
                managed_fixture(framework / (name + ".dll"))
            self.assertEqual(check_framework(framework), [])
            (framework / "Tizen.dll").write_bytes(b"not a DLL")
            self.assertTrue(any("Tizen.dll" in p for p in check_framework(framework)))

    def test_package_is_checked_without_running_or_installing(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            self.assertTrue(check_package(ROOT, package))
            for name in PACKAGE_DLLS:
                managed_fixture(package / name)
            assets = package / "quiet-home"
            assets.mkdir()
            (assets / "example.svg").write_text("<svg/>", encoding="utf-8")
            (assets / "apps.json").write_text(json.dumps([
                {"Id": "example.app", "Asset": "example.svg"}
            ]), encoding="utf-8")
            self.assertEqual(check_package(ROOT, package), [])
            (package / "Tizen.NUI.dll").write_bytes(b"leak")
            self.assertTrue(any("must NOT ship" in p for p in check_package(ROOT, package)))

    def test_invalid_artwork_path_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            for name in PACKAGE_DLLS:
                managed_fixture(package / name)
            assets = package / "quiet-home"
            assets.mkdir()
            (assets / "apps.json").write_text(json.dumps([
                {"Id": "example", "Asset": "../other.svg"}
            ]), encoding="utf-8")
            self.assertTrue(any("Missing/unsafe" in p for p in check_package(ROOT, package)))


if __name__ == "__main__":
    unittest.main()
