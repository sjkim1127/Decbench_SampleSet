# DecBench C++ Target Validation — Summary

**Validation date:** 2026-08-24  
**DecBench revision:** `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`  
**Tracks:** GCC/DWARF/`.ii` and native MSVC/PDB/CodeView  
**Permanent evidence:** `results/evidence/`

## Target status

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Current identity diagnostic | Status |
|---|---|---|---|---|---|---|---|---|
| Snappy 1.2.2 | GCC/DWARF | PASS | PASS | PASS | `libsnappy.so.1.2.2` | DWARF + `.ii` | 52.87% / 53.16% / 51.97% project `DW_AT_name` collision | **VALIDATED** |
| double-conversion v3.3.1 | GCC/DWARF | PASS | PASS | PASS | `libdouble-conversion.so.3.3.0` | DWARF + `.ii` | 7.87% / 15.58% / 8.06% project `DW_AT_name` collision | **VALIDATED** |
| Ninja v1.13.1 | GCC/DWARF | PASS | PASS | PASS | `ninja` | DWARF + `.ii` | 26.70% / 32.38% / 27.55% project `DW_AT_name` collision | **VALIDATED WITH CAVEATS** |
| Detours v4.0.1 | native MSVC/PDB | PASS | PASS | PASS | `withdll.exe` | PDB / CodeView | 5.88% / 5.88% / 5.88% PDB raw-name diagnostic | **VALIDATED** |
| DirectXTex may2026 | native MSVC/PDB | PASS | PASS | PASS | `DirectXTex.dll` | PDB / CodeView | 12.92% / 17.65% / 13.27% PDB raw-name diagnostic | **VALIDATED** |
| WinSparkle v0.9.4 | native MSVC/PDB | PASS | PASS | PASS | `WinSparkle.dll` | PDB / CodeView | 18.26% / 14.79% / 18.84% PDB raw-name diagnostic | **VALIDATED** |

Values are ordered `O0 / O2 / O2-noinline`.

The GCC metric is the DecBench-aligned project-source `DW_AT_name` collision
exposure. The MSVC values are separate PDB/CodeView procedure-name diagnostics and
must **not** be interpreted as numerically equivalent to the DWARF metric.

## GCC/DWARF qualification

The three GCC targets were first qualified locally on aarch64 and then re-qualified
through the pinned DecBench compile path on GitHub-hosted x86_64 Linux.

```text
workflow run: 32632337105
artifact id:  9491409143
artifact sha256:
60fef5ba7bb9a252e0d8155cd7b775a54679ed2ff4b92b2d6152e7e54f01ccc2
workflow commit:
3c48841470ed64370b4541a721c12fc1df430dd3
compiler: GCC/G++ 13.3.0
```

All 9 target/mode combinations pass the build/link/oracle checks. Final linked
images are `EM_X86_64`, expected optimization flags are visible in producer
metadata, and no `-flto`, `-fltrans`, `-fwpa`, or `-fwhole-program` markers were
observed.

| Target | `.ii` units/mode | x86_64 project functions O0/O2/O2-noinline | Collision O0/O2/O2-noinline |
|---|---:|---|---|
| Snappy | 4 | 157 / 79 / 152 | 52.87% / 53.16% / 51.97% |
| double-conversion | 8 | 127 / 77 / 124 | 7.87% / 15.58% / 8.06% |
| Ninja | 33 | 412 / 210 / 265 | 26.70% / 32.38% / 27.55% |

Permanent evidence:

```text
results/evidence/x86_64/qualification-summary.json
```

## Native MSVC/PDB qualification

The Windows track uses native Visual Studio/MSVC, full PDBs, `llvm-readobj` for PE
validation, and `llvm-pdbutil` for CodeView provenance and procedure extraction.

The common gates are:

1. native x86_64 PE is produced;
2. the intended linked image and matching PDB exist;
3. optimization switches are controlled explicitly;
4. project-owned compilands are selected from target source provenance;
5. selected `S_COMPILE3` records exist;
6. selected LTCG-marked `S_COMPILE3` records must be zero;
7. project-owned procedures and PDB identity diagnostics are extracted;
8. compact artifact-derived evidence is preserved in Git.

### Detours v4.0.1

```text
target commit: e4bfd6b03e50de46b47abfbd1e46b384f0c5f833
linked image:  withdll.exe
modes:
  O0          /Od /Ob0 /Zi
  O2          /O2 /Zi
  O2-noinline /O2 /Ob0 /Zi
```

| Gate / diagnostic | O0 | O2 | O2-noinline |
|---|---:|---:|---:|
| Selected `S_COMPILE3` | 5 | 5 | 5 |
| Selected LTCG `S_COMPILE3` | 0 | 0 | 0 |
| Project procedures | 136 | 136 | 136 |
| Raw-name collision | 5.88% | 5.88% | 5.88% |

Permanent evidence:

```text
results/evidence/msvc/detours/qualification-summary.json
```

### DirectXTex may2026

```text
target commit:   4feb3e11a020f35b796fc769a74216a555d4f5ef
workflow run:    32684847948
workflow commit: 040e7dfc3a08ed94179b3a15746296d8be3d0dbe
linked image:    DirectXTex.dll
runner image:    win25-vs2026 / 20260818.207.1
```

Per-mode artifacts:

| Mode | Artifact id | SHA-256 |
|---|---:|---|
| O0 | `9505320922` | `dd6fadd530a765a8ab5e38c1fd31bce0d3481805272ca7acd59a40e5dabab8c5` |
| O2 | `9505325453` | `1b1ad3fa76324aa577bb2b8f29adac27d011e3b84111b3540c0b1cd281ce5d62` |
| O2-noinline | `9505325181` | `8448cf1c351a373d1b53f385705c7928e97eb96625ad8fff1dcb8d92cb5381c5` |

| Gate / diagnostic | O0 | O2 | O2-noinline |
|---|---:|---:|---:|
| Project compilands | 17 | 17 | 17 |
| Selected `S_COMPILE3` | 17 | 17 | 17 |
| Selected LTCG `S_COMPILE3` | 0 | 0 | 0 |
| Project procedures | 766 | 221 | 746 |
| Raw-name collision | 12.92% | 17.65% | 13.27% |

The earlier DirectXTex failure was not a build failure. Its CMake/Ninja PDB module
names are full Windows paths ending in names such as `BC.cpp.obj`; a PowerShell
suffix matcher accidentally required two literal path separators. Commit
`7f227d52ea9fdc7295dd7560f3f0827417d2938c` fixed the separator check while
retaining project ownership filtering.

Permanent evidence:

```text
results/evidence/msvc/directxtex/qualification-summary.json
```

### WinSparkle v0.9.4

```text
target commit:   a8986caf620262f7d4581b241436ceaa0cc9370f
workflow run:    32686141551
workflow commit: 1325beadad2886496b6bd7c2f69a36d8bb4aa9de
linked image:    WinSparkle.dll
runner image:    win25-vs2026 / 20260818.207.1
```

Per-mode artifacts:

| Mode | Artifact id | SHA-256 |
|---|---:|---|
| O0 | `9505927922` | `46f3a77c53395821c390a3da3cbe085ec1c3d4b7d8386daef369980f02aacb93` |
| O2 | `9505868200` | `1e085f08a0873f0929ee5c63febcefb7d52607411f4c338c0b69557a81b9dc00` |
| O2-noinline | `9505923377` | `575239975dd9001d31b71ad34306b11bd75cbf654d3353c694146f125d9a855c` |

The adapter explicitly forces:

```text
O0:          /Od /Ob0 /Zi /GL-
O2:          /O2 /Zi /GL-
O2-noinline: /O2 /Ob0 /Zi /GL-
link:        /DEBUG:FULL /INCREMENTAL:NO /LTCG:OFF
```

The authoritative run uses exact PDB module/file provenance for ownership. This was
necessary because both WinSparkle and wxWidgets contain a `settings.cpp`; the old
basename-only matcher incorrectly admitted `WinSparkle_wx/settings.obj` as
project-owned. Commit `1325beadad2886496b6bd7c2f69a36d8bb4aa9de` changed the
generic analyzer to provenance-first ownership with object-name matching only as a
fallback.

| Gate / diagnostic | O0 | O2 | O2-noinline |
|---|---:|---:|---:|
| Project source files | 12 | 12 | 12 |
| Project compilands | 12 | 12 | 12 |
| Selected `S_COMPILE3` | 12 | 12 | 12 |
| Selected LTCG `S_COMPILE3` | 0 | 0 | 0 |
| Project procedures | 2267 | 1048 | 2160 |
| Raw-name collision groups | 121 | 37 | 118 |
| Raw-name collision addresses | 414 | 155 | 407 |
| Raw-name collision | 18.26% | 14.79% | 18.84% |
| Leaf-name heuristic | 56.86% | 45.71% | 56.02% |

Permanent evidence:

```text
results/evidence/msvc/winsparkle/qualification-summary.json
```

The matrix qualification jobs succeeded. The first aggregate evidence-publish job
failed only because another workflow advanced `main` before its push. The compact
summary was recovered from the successful artifacts and committed separately. The
publisher is now race-safe (`fetch` + `rebase` + bounded push retry), and the
status probe no longer writes transient state to `main`.

## Evidence inventory

```text
# GCC/DWARF
results/evidence/environment.txt
results/evidence/compile_report.json
results/evidence/collision/*.json
results/evidence/x86_64/qualification-summary.json

# native MSVC/PDB
results/evidence/msvc/detours/qualification-summary.json
results/evidence/msvc/directxtex/qualification-summary.json
results/evidence/msvc/winsparkle/qualification-summary.json
```

## Recommendation

All six shortlisted C++ targets now have runtime qualification evidence at the
build/oracle level:

- **double-conversion v3.3.1** — low-collision GCC/DWARF numerical baseline;
- **Ninja v1.13.1** — real executable with architecture-sensitive optimized output;
- **Snappy 1.2.2** — compact collision-heavy GCC/DWARF stress target;
- **Detours v4.0.1** — native Windows systems target;
- **DirectXTex may2026** — graphics/image-processing rich-C++ Windows target;
- **WinSparkle v0.9.4** — updater/networking/threading/UI-oriented Windows target.

## Remaining caveats

This work is **target/oracle qualification**, not a full end-to-end DecBench scoring
run. It does not claim GED, type matching, byte matching, or every decompiler has
been executed on every function in these six targets.

The C++ function-identity problem also remains a benchmark-design issue. The GCC
short-name metric quantifies current `DW_AT_name` ambiguity; the PDB metrics are
separate CodeView diagnostics. A future signature/qualified-name identity model may
change both target difficulty and the appropriate corpus composition.
