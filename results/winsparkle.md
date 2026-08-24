# DecBench C++ target validation result — WinSparkle

## Status

**VALIDATED** on the native MSVC/PDB target-oracle qualification track.

WinSparkle v0.9.4 now has artifact-backed native x86_64 MSVC evidence for all
three requested optimization modes. The pinned project builds a concrete
`WinSparkle.dll` + matching `WinSparkle.pdb`, the PE is AMD64, the selected
project compilands have CodeView `S_COMPILE3` records, and none of those selected
records reports LTCG.

This is **target/oracle qualification**, not a claim that the full DecBench
GED/type/byte/decompiler scoring pipeline has been run on WinSparkle. The PDB
raw-name collision values below are CodeView diagnostics and are not asserted to
be numerically equivalent to the GCC/DWARF `DW_AT_name` metric.

## Target metadata

| Field | Value |
|---|---|
| Target | WinSparkle v0.9.4 |
| Upstream | `vslavik/winsparkle` |
| Resolved commit | `a8986caf620262f7d4581b241436ceaa0cc9370f` |
| Track | native MSVC / PE / PDB / CodeView |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Linked image | `WinSparkle.dll` |
| Ground truth | matching native `WinSparkle.pdb` / CodeView |
| Build system | Visual Studio / MSBuild x64 |
| Role | Windows updater / networking / threading / UI-oriented C++ |

## Executed CI evidence

Authoritative qualification run:

```text
workflow run:    32686141551
workflow commit: 1325beadad2886496b6bd7c2f69a36d8bb4aa9de
runner OS:       Windows x64
runner image:    win25-vs2026
image version:   20260818.207.1
```

All three matrix qualification jobs completed successfully. The aggregate publish
job initially failed only because another workflow updated `main` between checkout
and `git push`, producing a non-fast-forward rejection. The generated evidence was
recovered directly from the successful artifacts and permanently committed.

Per-mode artifacts:

| Mode | Artifact id | Artifact SHA-256 |
|---|---:|---|
| O0 | `9505927922` | `46f3a77c53395821c390a3da3cbe085ec1c3d4b7d8386daef369980f02aacb93` |
| O2 | `9505868200` | `1e085f08a0873f0929ee5c63febcefb7d52607411f4c338c0b69557a81b9dc00` |
| O2-noinline | `9505923377` | `575239975dd9001d31b71ad34306b11bd75cbf654d3353c694146f125d9a855c` |

Permanent compact evidence:

```text
results/evidence/msvc/winsparkle/qualification-summary.json
```

## Controlled optimization modes

The adapter patches only the working checkout of the pinned Visual Studio project.
Upstream Release enables Whole Program Optimization, so qualification explicitly
disables it and adds final compiler/linker overrides:

```text
O0:          /Od /Ob0 /Zi /GL-
O2:          /O2 /Zi /GL-
O2-noinline: /O2 /Ob0 /Zi /GL-
link:        /DEBUG:FULL /INCREMENTAL:NO /LTCG:OFF
```

The build-log audit requires explicit `/GL-` and `/LTCG:OFF`. The authoritative
LTCG gate is the linked PDB: every selected project compiland must expose an
`S_COMPILE3` record and selected LTCG-marked records must be zero.

## Project ownership: provenance-first fix

An earlier successful workflow exposed a subtle ownership false positive. The
old generic analyzer derived object-name candidates from project sources and then
matched module basenames. WinSparkle has `src/settings.cpp`, while the linked wx
support code also contains a different `settings.cpp`; this caused
`WinSparkle_wx/settings.obj` to be incorrectly counted as project-owned merely
because the basename matched.

The raw PDB showed the problem directly: project source count was 12 while the old
matcher selected 13 compilands.

Commit:

```text
1325beadad2886496b6bd7c2f69a36d8bb4aa9de
```

changes the generic analyzer to use `llvm-pdbutil dump -modules -files` module/file
provenance as the primary ownership oracle. A module is project-owned when its PDB
file list contains an exact source path underneath the selected project source
roots. Object-name suffix matching is retained only as a fallback for PDBs without
usable module/file provenance.

The authoritative run reports:

```text
project_ownership_method:       pdb-module-file-provenance
project source files:           12
project provenance compilands:  12
selected project compilands:    12
```

The wx `WinSparkle_wx/settings.obj` false positive is therefore excluded while the
real WinSparkle `settings.obj` remains selected. Third-party wxWidgets, expat,
OpenSSL, ed25519, CRT, and other vendor compilands stay outside the project metric.

## Runtime qualification results

| Gate / diagnostic | O0 | O2 | O2-noinline |
|---|---:|---:|---:|
| Native x86_64 MSVC build | PASS | PASS | PASS |
| AMD64 PE + matching PDB | PASS | PASS | PASS |
| Project source files | 12 | 12 | 12 |
| Selected project compilands | 12 | 12 | 12 |
| Selected `S_COMPILE3` records | 12 | 12 | 12 |
| Selected LTCG `S_COMPILE3` records | 0 | 0 | 0 |
| Project procedure records | 2267 | 1048 | 2160 |
| Unique raw PDB names | 1974 | 930 | 1871 |
| Raw-name collision groups | 121 | 37 | 118 |
| Raw-name collision addresses | 414 | 155 | 407 |
| Raw PDB-name collision diagnostic | 18.26% | 14.79% | 18.84% |
| Leaf-name heuristic | 56.86% | 45.71% | 56.02% |

The project-owned compilands correspond to the 12 WinSparkle source translation
units selected from `src/*.cpp`: appcast, appcontroller, dll_api, dllmain,
download, error, settings, signatureverifier, threads, ui, updatechecker, and
updatedownloader.

## CI publish-race hardening

The qualification matrix itself succeeded, but its first permanent-evidence
publish attempt failed with:

```text
! [rejected] HEAD -> main (fetch first)
```

because another workflow updated `main` after the publish job checked out the
qualification commit. This was infrastructure contention, not a qualification
failure.

The status-probe workflow is now read-only and no longer commits transient status
snapshots to `main`. The WinSparkle evidence publisher now checks out full history
and uses `git fetch`, `git rebase origin/main`, and bounded push retries before
failing. Transient `run-status.json` was removed from permanent evidence.

## Current decision

WinSparkle is now an evidence-backed native Windows C++ candidate. Together with
Detours and DirectXTex, the Windows shortlist has actual PE/PDB runtime
qualification rather than static build assumptions.

The remaining benchmark-level work is separate: DecBench still needs a deliberate
PDB/CodeView ground-truth ingestion path and a C++ function-identity policy before
these Windows targets can be claimed as fully benchmarked end-to-end.
