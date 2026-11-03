#!/usr/bin/env python3
"""Read-only native Quiet Home build checks. Never accesses or changes a TV."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ("Tizen.NUI", "Tizen.Applications.Common", "Tizen.System", "Tizen")
PROJECTS = (
    ("launcher/src/Home.csproj", "net6.0", "BixbyPromotion", True),
    ("launcher/src/QuickLaunch.csproj", "net6.0", "QuickLaunch", True),
    ("launcher/probe/Probe.csproj", "net6.0", None, False),
)
PACKAGE_DLLS = ("BixbyPromotion.dll", "QuickLaunch.dll", "Probe.dll")


def check_source(root):
    problems = []
    required = (
        "launcher/src/Home.cs", "launcher/src/AppLibrary.cs",
        "launcher/src/QuickLaunch.cs", "launcher/probe/Probe.cs",
        "tools/build.py", "recipes/install-launcher.sh",
        "recipes/restore-launcher.sh", "launcher/assets/apps.json",
    )
    for relative in required:
        if not (root / relative).is_file():
            problems.append("Missing source file: " + relative)

    for relative, framework, assembly, needs_refs in PROJECTS:
        project = root / relative
        if not project.is_file():
            problems.append("Missing project: " + relative)
            continue
        try:
            xml = ET.parse(project).getroot()
        except ET.ParseError as exc:
            problems.append(f"Invalid XML in {relative}: {exc}")
            continue
        properties = xml.find("PropertyGroup")
        if properties is None or properties.findtext("TargetFramework") != framework:
            problems.append(f"{relative}: expected {framework}")
        if assembly and (properties is None or properties.findtext("AssemblyName") != assembly):
            problems.append(f"{relative}: expected assembly name {assembly}")
        if needs_refs:
            found = {r.get("Include"): r for r in xml.findall(".//Reference")}
            for name in REFERENCES:
                node = found.get(name)
                if node is None:
                    problems.append(f"{relative}: missing reference {name}")
                elif node.findtext("Private", "").strip().lower() != "false":
                    problems.append(f"{relative}: {name} must have Private=false")
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        problems.append("Missing .gitignore")
    else:
        ignored = set(gitignore.read_text(encoding="utf-8").splitlines())
        for pattern in (".local/", "*.dll"):
            if pattern not in ignored:
                problems.append(f".gitignore should exclude {pattern}")
    return problems


def looks_like_managed_dll(path):
    try:
        if path.stat().st_size < 512:
            return False
        with path.open("rb") as stream:
            sample = stream.read(16 * 1024 * 1024)
        return sample[:2] == b"MZ" and b"BSJB" in sample
    except OSError:
        return False


def check_framework(directory):
    problems = []
    for name in REFERENCES:
        path = directory / (name + ".dll")
        if not path.is_file():
            problems.append("Missing TV reference: " + name + ".dll")
        elif not looks_like_managed_dll(path):
            problems.append("Invalid or unsupported managed DLL: " + name + ".dll")
    return problems


def check_dotnet():
    executable = shutil.which("dotnet")
    if not executable:
        return ["Missing dotnet CLI (use a .NET 6 SDK environment)"]
    try:
        output = subprocess.run([executable, "--list-sdks"], check=True,
                                capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return ["Could not query dotnet SDK versions"]
    if not any(line.lstrip().startswith("6.") for line in output.splitlines()):
        return ["A .NET 6 SDK is required to match the tested native build"]
    return []


def check_package(root, package):
    problems = []
    for filename in PACKAGE_DLLS:
        path = package / filename
        if not path.is_file():
            problems.append("Missing built output: " + filename)
        elif not looks_like_managed_dll(path):
            problems.append("Invalid compiled output: " + filename)
    for name in REFERENCES:
        if (package / (name + ".dll")).exists():
            problems.append("Proprietary reference must NOT ship in package: " + name + ".dll")
    catalog = package / "quiet-home/apps.json"
    if not catalog.is_file():
        problems.append("Missing packaged app catalog: quiet-home/apps.json")
    else:
        try:
            apps = json.loads(catalog.read_text(encoding="utf-8"))
            if not isinstance(apps, list):
                raise ValueError("app catalog must be a list")
            ids = set()
            for app in apps:
                app_id, asset = app["Id"], app["Asset"]
                if app_id in ids:
                    problems.append("Duplicate app ID: " + str(app_id))
                ids.add(app_id)
                rel = Path(asset)
                if rel.is_absolute() or ".." in rel.parts or not (catalog.parent / rel).is_file():
                    problems.append("Missing/unsafe app artwork: " + str(asset))
        except (ValueError, KeyError, TypeError) as exc:
            problems.append("Invalid packaged app catalog: " + str(exc))
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("source", "framework", "package"),
                        nargs="?", default="source")
    parser.add_argument("--framework", type=Path, default=ROOT / ".local/tv-framework")
    parser.add_argument("--package", type=Path, default=ROOT / ".local/package")
    parser.add_argument("--json", action="store_true", help="Emit a local, non-device report")
    args = parser.parse_args()
    problems = check_source(ROOT)
    if args.stage == "framework":
        problems.extend(check_dotnet())
        problems.extend(check_framework(args.framework))
    elif args.stage == "package":
        problems.extend(check_package(ROOT, args.package))
    result = {
        "stage": args.stage,
        "ok": not problems,
        "problems": problems,
        "scope": "Local source/files only; NO SDB, root, TV install, or TV compatibility verification",
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Native build preflight ({args.stage}): " + ("PASS" if result["ok"] else "BLOCKED"))
        for problem in problems:
            print(" - " + problem)
        print(result["scope"])
    return 0 if not problems else 2


if __name__ == "__main__":
    sys.exit(main())
