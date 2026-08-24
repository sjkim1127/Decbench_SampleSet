# DecBench C++ target validation result — Microsoft DirectXTex

## Status

**VALIDATED** on the native MSVC/PDB target-oracle qualification track.

This means the pinned target built in all three requested optimization modes on a
native Windows x86_64 MSVC toolchain, produced the intended AMD64 PE/PDB pair, and
passed the project-owned CodeView/PDB provenance, LTCG, procedure-extraction, and
identity-diagnostic gates.

It does **not** mean a full end-to-end DecBench GED/type/byte/decompiler benchmark
has been run for DirectXTex, and the PDB raw-name diagnostic below is not asserted
to be numerically equivalent to DecBench's GCC/DWARF `DW_AT_name` metric.

## Target metadata

| Field | Value |
|---|---|
| Target | Microsoft DirectXTex |
| Upstream | `microsoft/DirectXTex` |
| Release/tag | `may2026` |
| Resolved commit | `4feb3e11a020f35b796fc769a74216a555d4f5ef` |
| Track | native MSVC / PE / PDB / CodeView |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Linked image | `DirectXTex.dll` |
| Ground truth | matching native MSVC PDB / CodeView |
| Intended role | Windows graphics / image-processing / rich-C++ stress target |

## Executed CI evidence

```text
workflow run:    32684847948
workflow commit: 040e7dfc3a08ed94179b3a15746296d8be3d0dbe
runner OS:       Windows x64
runner image:    win25-vs2026
image version:   20260818.207.1
```

Per-mode artifacts:

| Mode | Artifact id | Artifact SHA-256 |
|---|---:|---|
| O0 | `9505320922` | `dd6fadd530a765a8ab5e38c1fd31bce0d3481805272ca7acd59a40e5dabab8c5` |
| O2 | `9505325453` | `1b1ad3fa76324aa577bb2b8f29adac27d011e3b84111b3540c0b1cd281ce5d62` |
| O2-noinline | `9505325181` | `8448cf1c351a373d1b53f385705c7928e97eb96625ad8fff1dcb8d92cb5381c5` |

Compact machine-readable evidence is committed at:

```text
results/evidence/msvc/directxtex/qualification-summary.json
```

## Controlled optimization modes

The adapter uses CMake/Ninja with native MSVC and explicitly disables IPO/LTCG:

```text
O0:          /Od /Ob0 /Zi /GL-
O2:          /O2 /Zi /GL-
O2-noinline: /O2 /Ob0 /Zi /GL-
link:        /DEBUG:FULL /INCREMENTAL:NO /LTCG:OFF
```

The build-log gate requires the explicit `/GL-` and `/LTCG:OFF` overrides. The
substantive final gate is the linked PDB: selected project compilands must contain
`S_COMPILE3` records and none may report LTCG.

## PDB module-ownership blocker and fix

The failed run before validation was not a DirectXTex build failure. The DLL/PDB
were produced, but the generic PDB ownership matcher failed to recognize the linked
CMake/Ninja object-module names.

The raw O0 artifact shows names in this form:

```text
D:\a\Decbench_SampleSet\Decbench_SampleSet\msvc-evidence\directxtex\O0\build-tree\CMakeFiles\DirectXTex.dir\DirectXTex\BC.cpp.obj
D:\a\Decbench_SampleSet\Decbench_SampleSet\msvc-evidence\directxtex\O0\build-tree\CMakeFiles\DirectXTex.dir\DirectXTex\DirectXTexCompress.cpp.obj
```

The analyzer already generated candidates such as `BC.cpp.obj` and
`DirectXTexCompress.cpp.obj`, but its Windows suffix check accidentally searched for
two literal backslashes before the candidate. PowerShell does not use backslash as
a string escape character, so the matcher could not match ordinary Windows paths.

Commit `7f227d52ea9fdc7295dd7560f3f0827417d2938c` changes that suffix check from a
two-backslash string to a one-backslash string. The ownership gate itself remains
in place; it now recognizes the actual CMake/Ninja module format while continuing
to exclude CRT, Windows SDK, and unrelated vendor modules.

The raw PDB also contains modules such as Windows SDK `uuid.lib` objects and MSVC
CRT objects under `D:\a\_work\...`; these do not match the DirectXTex source-derived
object candidates and are excluded from the project metric.

## Runtime qualification results

All three modes pass.

| Gate / diagnostic | O0 | O2 | O2-noinline |
|---|---:|---:|---:|
| AMD64 PE | PASS | PASS | PASS |
| Linked image / PDB | `DirectXTex.dll` / `DirectXTex.pdb` | same | same |
| Project source files considered | 21 | 21 | 21 |
| Selected project compilands | 17 | 17 | 17 |
| Selected `S_COMPILE3` records | 17 | 17 | 17 |
| Selected LTCG `S_COMPILE3` records | 0 | 0 | 0 |
| Project procedure records | 766 | 221 | 746 |
| Unique raw PDB names | 705 | 201 | 685 |
| Raw-name collision groups | 38 | 19 | 38 |
| Raw-name collision addresses | 99 | 39 | 99 |
| Raw PDB-name collision diagnostic | 12.92% | 17.65% | 13.27% |
| Leaf-name heuristic | 41.25% | 27.60% | 41.15% |

The difference between 21 discovered project source files and 17 selected linked
compilands is expected for this configured library build: optional DirectCompute,
GPU-compression, and D3D-specific translation units are not linked into this
concrete `DirectXTex.dll` configuration.

For O0, the raw PDB summary reports debug info, types, IDs, globals, and publics;
it is not incrementally linked and is not stripped. The PE CodeView record points
to the matching `DirectXTex.pdb`, and the PE machine is
`IMAGE_FILE_MACHINE_AMD64`.

## Identity caveat

The values above are **PDB/CodeView procedure-name diagnostics** over project-owned
linked compilands. They are useful for target qualification and for detecting
short-name ambiguity pressure, but they are not an apples-to-apples replacement
for DecBench's current GCC/DWARF `DW_AT_name` project-source collision metric.

## Current decision

DirectXTex is now suitable to present as an evidence-backed native Windows C++
candidate for the multi-language corpus. The remaining integration question is how
DecBench should consume PDB/CodeView ground truth and define C++ function identity
for actual benchmark scoring; that is separate from this target's build/oracle
qualification.
