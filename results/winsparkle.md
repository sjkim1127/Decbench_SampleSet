# DecBench C++ target validation result — WinSparkle

## Target metadata

| Field | Value |
|---|---|
| Target | WinSparkle |
| Upstream | `vslavik/winsparkle` |
| Release/tag | `v0.9.4` |
| Resolved commit | `a8986caf620262f7d4581b241436ceaa0cc9370f` |
| Track | MSVC/PDB |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Validation date | 2026-08-23 |
| Host | macOS 26.5.1, arm64 |
| Container / OS | N/A — Wine/MSVC not available on this host |
| Compiler | BLOCKED — cl.exe not found |
| Linker | BLOCKED — link.exe not found |
| Windows SDK | N/A — not installed |
| Wine/msvc-wine | N/A — wine not found on this host |

## Build and ground-truth summary

| Mode | Build | Linked image(s) | `.ii` count | Ground truth | Source-owned function addresses | Unique short names | Collision groups | Collision addresses | Collision rate |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| O0 | BLOCKED | — | N/A | PDB: BLOCKED | — | — | — | — | — |
| O2 | BLOCKED | — | N/A | PDB: BLOCKED | — | — | — | — | — |
| O2-noinline | BLOCKED | — | N/A | PDB: BLOCKED | — | — | — | — | — |

## Blocking reason

Same as for Detours and DirectXTex: `cl.exe`, `link.exe`, and the Windows SDK are
absent from this macOS 26.5.1 arm64 host. Wine is also absent.

WinSparkle uses MSBuild / Visual Studio `.vcxproj`, which additionally requires
MSBuild to be available — further deepening the Windows dependency.

```text
Environment check:
  wine      : not found
  cl.exe    : not found
  link.exe  : not found
  msbuild   : not found
  Windows SDK : not installed
```

## Static config validation

The TOML at `targets/windows/winsparkle.toml` is well-formed:

- **Source commit** `a8986caf620262f7d4581b241436ceaa0cc9370f` matches upstream tag
  `v0.9.4` on `vslavik/winsparkle`.
- **Build system** is correctly identified as Visual Studio / MSBuild targeting x64.
- **Linked images** `x64/Release/WinSparkle.dll` and `x64/Debug/WinSparkle.dll` are
  the expected PE DLL outputs.
- **PDB images** `x64/Release/WinSparkle.pdb` and `x64/Debug/WinSparkle.pdb` are
  correctly paired.
- **Optimization mode mapping** is correct:
  - O0 → `/Od /Ob0 /Zi` + `/DEBUG /LTCG:OFF`
  - O2 → `/O2 /Zi` + `/DEBUG /LTCG:OFF`
  - O2-noinline → `/O2 /Ob0 /Zi` + `/DEBUG /LTCG:OFF`
- `/LTCG:OFF` is correctly specified on the linker line for all modes — this is
  important because the upstream Release configuration enables WholeProgramOptimization.
- **Source filter** correctly restricts to `src/*.cpp`, `src/*.h`, `include/*.h` and
  excludes `3rdparty/**`, `examples/**`, `tests/**`.
- `collision_note` correctly calls out `Run` / `IsJoinable` / `UpdateChecker`
  hierarchy as a known medium-risk collision area.

**No config errors found during static review.**

## Optimization control

Not measured (BLOCKED). Key risk when environment becomes available:

- The upstream `WinSparkle.vcxproj` Release configuration enables
  `WholeProgramOptimization` (LTCG). The benchmark adapter MUST override this
  property for all three modes using `msbuild /p:WholeProgramOptimization=false` or
  by directly editing the project XML before building.
- Confirm that `/Ob0` for O2-noinline actually suppresses inlining when combined with
  `/O2`; MSVC may promote inlining despite `/Ob0` in some configurations.
- Record full `cl.exe` command lines from the build log.

## Linked images

Not measured (BLOCKED). Expected:

```text
O0:         WinSparkle.dll (x64) + WinSparkle.pdb
O2:         WinSparkle.dll (x64) + WinSparkle.pdb
O2-noinline: WinSparkle.dll (x64) + WinSparkle.pdb
```

## Source ownership filter

Planned (not measured):

```text
Included compilands: src/*.cpp (appcast.cpp, download.cpp, install.cpp, settings.cpp,
                     signatureverifier.cpp, threads.cpp, ui.cpp, updatechecker.cpp, ...)
                     include/*.h
Excluded compilands: 3rdparty/expat/**, 3rdparty/openssl/**, 3rdparty/wxwidgets/**,
                     3rdparty/ed25519/**
```

Third-party compilands will appear in the PDB. Filtering is critical here.

## Short-name collision details

Not measured (BLOCKED).

Known collision candidates based on source review of v0.9.4:

| Short name | Risk | Notes |
|---|---|---|
| `Run` | HIGH | Overridden in `Thread`, `UpdateCheckerThread`, possibly other subclasses |
| `IsJoinable` | MEDIUM | Virtual in `Thread` hierarchy |
| `DoCheck` | MEDIUM | Repeated in update-check logic |
| constructor/destructor forms | MEDIUM | Multiple classes produce `~ClassName` -> same short name |

The `Thread` base class and its subclasses (`UpdateCheckerThread`, etc.) intentionally
repeat virtual method names. Under DecBench's current unqualified name identity model,
these will produce collision groups. Must be measured from actual PDB.

## Preprocessed source / oracle notes

For MSVC/PDB targets:

- PDB generated for exact image: BLOCKED
- source/compiland information available: BLOCKED
- procedure/RVA extraction method: pdbparse or llvm-pdbutil (when environment available)
- Third-party compiland filtering: must use compiland source paths from PDB stream

## Final status

Status: **BLOCKED**

Decision rationale:

```text
No MSVC/Wine/Windows SDK/MSBuild environment available on the macOS arm64 validation
host. Runtime validation cannot proceed. Static config review passed with no errors.
The known Thread-hierarchy collision risk is documented and must be quantified from
a real PDB before treating this target as confirmed.
```

Remaining blockers:

```text
1. Wine or native Windows environment with MSVC Build Tools + MSBuild
2. Windows SDK (Win32 headers/libs, WinInet, etc. required by WinSparkle)
3. Third-party submodule resolution (expat, wxWidgets headers, etc.)
4. LTCG override verification (ensure /LTCG:OFF actually takes effect)
5. pdbparse / llvm-pdbutil for PDB ground-truth extraction
6. Compiland filtering script to exclude 3rdparty/ from collision measurement
```
