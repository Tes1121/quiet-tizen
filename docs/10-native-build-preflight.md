# Native Quiet Home build readiness (no TV changes)

This guide prepares **the existing native C#/.NET/NUI Quiet Home**. It does
not convert it to a WGT/TPK, sign an app, replace Samsung Home, or contact a TV.

## What is actually buildable

| Component | Build result | Requires TV-matched private references |
|---|---|---|
| `launcher/src/Home.csproj` | `BixbyPromotion.dll` | Yes |
| `launcher/src/QuickLaunch.csproj` | `QuickLaunch.dll` | Yes |
| `launcher/probe/Probe.csproj` | `Probe.dll` | No |
| `vendor/payload-source/*.csproj` | Access helper DLLs | No |

The resulting `.local/package/` is a **native DLL/resource staging directory**,
**not** a Tizen `.tpk` or `.wgt`. On the one tested Samsung TV the vendor's
existing `com.samsung.tv.bixby-promotion` container was reused. That is not a
general-purpose app installation mechanism. See [launcher procedure](04-launcher.md).

## Phase 1 — source-only, read-only checks

This phase works without a television, root access or Samsung private files.

```sh
python3 tools/native_preflight.py source
python3 -m unittest discover -s tests -v
```

The separate **Native build readiness (offline)** GitHub Actions workflow
runs these checks and compiles `Probe.csproj` only. It publishes a JSON
readiness report, **not** a deployable launcher. This workflow has no network
access to a TV and does not read or distribute private Samsung assemblies.

## Phase 2 — private build prerequisites (when available)

Use an isolated computer/build host with Python 3.12+, an appropriate **.NET
6 SDK**, and Samsung SDB. .NET 6 is end-of-support, so keep this build
environment isolated and do not assume it is appropriate for unrelated work.

Obtain these four matching files from **the TV you own and have already
identified** (or a legitimately permitted compatible SDK):

- `Tizen.NUI.dll`
- `Tizen.Applications.Common.dll`
- `Tizen.System.dll`
- `Tizen.dll`

Store them privately as `.local/tv-framework/NAME.dll`. The `.local/`
directory and `*.dll` are gitignored. **Never commit, attach to a PR,
upload to Actions, or distribute these vendor assemblies.** The source CI
cannot build the full launcher without them. If their origin/version does
not match the target TV runtime, stop rather than substituting random SDK
files. The preflight can check that these look like managed DLLs; it cannot
prove runtime/firmware compatibility.

```sh
python3 tools/native_preflight.py framework --framework .local/tv-framework
```

An absent DLL or .NET 6 SDK blocks the full native build. This is an
expected prerequisite, not a reason to disable the check.

## Phase 3 — local native build and offline package verification

Do this only when Phase 2 passes:

```sh
python3 tools/build.py launcher --framework .local/tv-framework
python3 tools/native_preflight.py package --package .local/package
tar -czf .local/package.tar.gz -C .local/package .
tar -tzf .local/package.tar.gz
sha256sum .local/package.tar.gz
```

The preflight checks the expected output DLLs, the local app catalog and
referenced artwork, and ensures the four proprietary reference DLL names
are not present in the staging package. It is a structural check,
**not** a guarantee of a compatible or working TV app.

Do not rename `.local/package.tar.gz` to `.tpk` or `.wgt`; archive
contents do not become a signed Tizen application by changing extensions.

## Phase 4 — installation plan for a future, separately approved session

**No commands below should run merely to prepare a build.** They are a
checklist for a later TV-specific compatibility review, not a universal
installer. The existing procedure is in
[04-launcher.md](04-launcher.md), [02-access.md](02-access.md), and
[09-recovery.md](09-recovery.md).

1. Record TV model and firmware from *About This TV*, plus runtime,
   installed package IDs, current app permissions, HDMI input mapping,
   and the original Home/startup selectors. The documented example was
   `UN75U8000FFXZA` / `T-KSU2EFAKUC-0090-1300.9`, **not** a Samsung-wide
   compatibility guarantee.
2. If another launcher (for example APL Launcher) or system modification
   (for example Vetro) is installed, inventory its Home routing and modified
   Samsung packages before planning a change; do not overwrite it blindly.
3. Establish whether Developer Mode/SDB and temporary access work on
   **that exact firmware**. Do not use another model's exploit.
4. Take on-TV and separate off-TV snapshots, including the original
   `com.samsung.tv.bixby-promotion` files, registry and routing settings;
   prepare and review the corresponding restore recipes.
5. Only after compatibility, recovery and a separate install decision:
   install the compiled DLL/resources **without assigning Home/startup**;
   manually verify keys, picture/audio, HDMI, apps and settings.
6. Only after those checks, consider Home/startup and the optional settings
   bridge as distinct changes, with rollback between phases.

The existing install recipe can alter vendor files and registry state,
requires verified temporary root, and is **not atomic**. It has no
hardware-level unbrick recovery. A successful local build or a source CI
check must not be represented as an installation test.

## Outcome interpretation

- `source: PASS` — project metadata and tracked sources look complete;
  **not** proof that C# compiles against Samsung private APIs.
- `framework: PASS` — .NET 6 SDK and expected local DLL signatures exist;
  **not** proof they match your TV.
- `package: PASS` — local staged files look complete;
  **not** a TPK/WGT, install confirmation or TV runtime test.

No step in this guide performs `sdb connect`, `sdb push`, root,
vendor-file replacement or Home/Startup modification by itself.
