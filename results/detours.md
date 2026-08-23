# DecBench C++ target validation result — Microsoft Detours

## Target metadata

| Field | Value |
|---|---|
| Target | Microsoft Detours |
| Upstream | `microsoft/Detours` |
| Release/tag | `v4.0.1` |
| Resolved commit | `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833` |
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

This target requires `cl.exe` (MSVC) and `link.exe` under a Wine or native Windows
environment, plus the Windows SDK. The current validation host is macOS 26.5.1 on
arm64. Neither Wine nor MSVC are installed.

The DecBench PR #36 direction describes using `cl.exe` under Wine (`msvc-wine`), but
that infrastructure is not available here. A native Windows machine or a properly
configured Wine+MSVC container would be required.

```text
Environment check:
  wine     : not found
  cl.exe   : not found
  link.exe : not found
  Windows SDK : not installed
```

## Static config validation

The TOML at `targets/windows/detours.toml` is well-formed and consistent with the
upstream repository:

- **Source commit** `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833` matches the
  upstream `v4.0.1` tag on `microsoft/Detours`.
- **Core source files** listed in `[source].include` (`detours.cpp`, `modules.cpp`,
  `disasm.cpp`, `image.cpp`, `creatwth.cpp`) are present in `src/` of that commit.
- **Linked PE targets** (`withdll.exe`, `dumpe.exe`, `disas.exe`, `findfunc.exe`)
  correspond to upstream samples under `samples/`.
- **Optimization mode mapping** is correct:
  - O0 → `/Od /Ob0 /Zi` + `/DEBUG`
  - O2 → `/O2 /Zi` + `/DEBUG`
  - O2-noinline → `/O2 /Ob0 /Zi` + `/DEBUG`
- The config correctly notes that upstream makefiles default to `/Od`; benchmark
  integration must explicitly override rather than trusting upstream defaults.
- `require_linked_pe = true` and `measure_short_name_collisions = true` are set
  correctly.

**No config errors found during static review.**

## Optimization control

Not measured (BLOCKED). When a working environment becomes available:

- Verify that the NMAKE build does not silently inherit `/Od` for O2 and O2-noinline
  modes.
- Confirm that each sample PE is compiled with exactly the flag set declared above.
- Record the exact final `cl.exe` command line from the build log.

## Linked images

Not measured (BLOCKED). Expected when environment is available:

```text
O0:         withdll.exe, dumpe.exe, disas.exe, findfunc.exe  (+ Detours-linked PDB)
O2:         same set
O2-noinline: same set
```

## Source ownership filter

Planned (not measured):

```text
Included: src/detours.cpp, src/modules.cpp, src/disasm.cpp, src/image.cpp, src/creatwth.cpp
          + selected sample PE wrapper (withdll, dumpe, etc.)
Excluded: samples/**, tests/**
```

## Short-name collision details

Not measured (BLOCKED).

Expected notable candidates based on source review:
- Detours API names are relatively distinctive (`DetourAttach`, `DetourDetach`,
  `DetourFindFunction`, etc.) — low collision risk expected.
- Internal helpers may produce some collisions (e.g. `RoundToBoundary`, `AlignUp`).
- Must be measured from actual PDB rather than assumed from source.

## Preprocessed source / oracle notes

For MSVC/PDB targets:

- PDB generated for exact image: BLOCKED
- source/compiland information available: BLOCKED
- procedure/RVA extraction method: pdbparse or llvm-pdbutil (when environment available)

## Final status

Status: **BLOCKED**

Decision rationale:

```text
No MSVC/Wine/Windows SDK environment available on the macOS arm64 validation host.
Runtime validation cannot proceed without cl.exe + link.exe + Windows SDK.
Static config review passed with no errors found.
```

Remaining blockers:

```text
1. Wine or native Windows environment with MSVC Build Tools
2. Windows SDK (for Win32 headers and libs required by Detours)
3. DecBench MSVC adapter (PR #36-style) or equivalent build driver
4. pdbparse / llvm-pdbutil for PDB ground-truth extraction
```
