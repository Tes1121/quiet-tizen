#!/usr/bin/env python3
"""Build native DLLs and a local tarball; never connects to a TV."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

from native_preflight import (ROOT, check_dotnet, check_framework,
                              check_package, check_source)


def make_archive(package, destination):
    """Create a local tarball of checked staging files, without following symlinks."""
    package = package.resolve()
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".tar.gz",
                                     delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with tarfile.open(temporary, "w:gz") as archive:
            for path in sorted(package.rglob("*")):
                if path.is_symlink():
                    raise ValueError("Refusing to package a symlink: " + str(path))
                if path.is_file():
                    archive.add(path, arcname=path.relative_to(package).as_posix(),
                                recursive=False)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--framework", type=Path, default=ROOT / ".local/tv-framework")
    parser.add_argument("--archive", type=Path, default=ROOT / ".local/package.tar.gz")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check dependencies and show plan; never build or write")
    args = parser.parse_args()

    issues = check_source(ROOT) + check_dotnet() + check_framework(args.framework)
    if issues:
        print("Native build BLOCKED:")
        for issue in issues:
            print(" - " + issue)
        print("No compile, package or device action taken.")
        return 2

    if args.dry_run:
        print("Native build DRY RUN PASS: source, .NET 6 SDK and local reference signatures.")
        print("Would run tools/build.py launcher, validate .local/package, and create a local tar.gz.")
        print("Would NOT contact a TV, root, install or change Home settings.")
        return 0

    subprocess.run([sys.executable, str(ROOT / "tools/build.py"), "launcher",
                    "--framework", str(args.framework.resolve())],
                   check=True, cwd=ROOT)
    package = ROOT / ".local/package"
    issues = check_package(ROOT, package)
    if issues:
        print("Build completed, but package validation BLOCKED:")
        for issue in issues:
            print(" - " + issue)
        return 2
    digest = make_archive(package, args.archive)
    print("Local native staging archive: " + str(args.archive))
    print("SHA-256: " + digest)
    print("This is NOT a signed .tpk/.wgt and has NOT been installed or tested on a TV.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
