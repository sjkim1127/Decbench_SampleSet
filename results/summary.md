# DecBench C++ Target Validation — Summary

**Validation date:** 2026-08-23  
**DecBench revision:** `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`  
**Tracks:** GCC/DWARF/`.ii` and native MSVC/PDB/CodeView  
**Raw/derived evidence:** `results/evidence/`

## Target status

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Current identity diagnostic | Status |
|---|---|---|---|---|---|---|---|---|
| Snappy 1.2.2 | GCC/DWARF | PASS | PASS | PASS | `libsnappy.so.1.2.2` | DWARF + `.ii` | x86_64 project collision: 52.87% / 53.16% / 51.97% | **VALIDATED** |
| double-conversion v3.3.1 | GCC/DWARF | PASS | PASS | PASS | `libdouble-conversion.so.3.3.0` | DWARF + `.ii` | x86_64 project collision: 7.87% / 15.58% / 8.06% | **VALIDATED** |
| Ninja v1.13.1 | GCC/DWARF | PASS | PASS | PASS | `ninja` | DWARF + `.ii` | x86_64 project collision: 26.70% / 32.38% / 27.55% | **VALIDATED WITH CAVEATS** |
| Detours v4.0.1 | native MSVC/PDB | PASS | PASS | PASS | `withdll.exe` | PDB / CodeView | PDB raw-name diagnostic: 5.88% / 5.88% / 5.88% | **VALIDATED** |
| DirectXTex may2026 | MSVC/PDB | — | — | — | expected `DirectXTex.dll` | PDB / CodeView | not measured | **PENDING** |
| WinSparkle v0.9.4 | MSVC/PDB | — | — | — | expected `WinSparkle.dll` | PDB / CodeView | not measured | **PENDING** |

The PDB value is a different diagnostic from the DecBench-aligned GCC/DWARF
`DW_AT_name` project collision metric and is not directly comparable numerically.

## GCC/DWARF qualification

The GCC targets were first validated locally on aarch64 and then re-qualified on
GitHub-hosted x86_64 Linux through DecBench's real compile path.

### x86_64 CI artifact

```text
workflow run: 32632337105
artifact id:  9491409143
artifact sha256:
60fef5ba7bb9a252e0d8155cd7b775a54679ed2ff4b92b2d6152e7e54f01ccc2
workflow commit:
3c48841470ed64370b4541a721c12fc1df430dd3
runner/toolchain: Ubuntu x86_64, GCC/G++ 13.3.0
```

All 9 target/mode entries record `ok: true`, one linked image, no compile errors,
and the expected preprocessed translation-unit count.

| Gate | Snappy | double-conversion | Ninja |
|---|---|---|---|
| O0/O2/O2-noinline build | PASS | PASS | PASS |
| Linked image per mode | 1 | 1 | 1 |
| `.ii` units per mode | 4 | 8 | 33 |
| `EM_X86_64` | yes | yes | yes |
| Expected producer flags | yes | yes | yes |
| LTO/WPA markers | none | none | none |
| Collision analysis | complete | complete | complete |

Validated modes:

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

Compact artifact-derived evidence:

```text
results/evidence/x86_64/qualification-summary.json
```

## GCC architecture comparison

Snappy and double-conversion reproduce the local aarch64 project counts and
collision rates exactly on x86_64. Ninja shows architecture-dependent optimized
function selection:

| Ninja mode | aarch64 project funcs / collision | x86_64 project funcs / collision |
|---|---:|---:|
| O0 | 412 / 26.70% | 412 / 26.70% |
| O2 | 355 / 30.42% | 210 / 32.38% |
| O2-noinline | 412 / 26.70% | 265 / 27.55% |

The x86_64 producer audit reports no LTO markers, so this difference is not caused
by accidental IPO/LTO in the final Ninja binary.

## Native MSVC/PDB Detours qualification

Detours v4.0.1 is no longer blocked. It was built on native Windows x86_64 with a
real Visual Studio/MSVC toolchain and analyzed through its linked PE/PDB.

```text
Target commit:   e4bfd6b03e50de46b47abfbd1e46b384f0c5f833
Runner OS:       Windows Server 2025 x64
Runner image:    windows-2025-vs2026 / win25-vs2026
Image version:   20260818.207.1
Visual Studio:   2026 Developer Command Prompt v18.9.1
cl.exe:          19.51.36256.0
link.exe:        14.51.36256.0
MSVC toolset:    14.51.36231
Linked image:    withdll.exe
Ground truth:    full native PDB / CodeView
```

Mode mapping:

```text
O0:          /Od /Ob0 /Zi
O2:          /O2 /Zi
O2-noinline: /O2 /Ob0 /Zi
link:        /DEBUG:FULL /INCREMENTAL:NO /SUBSYSTEM:CONSOLE
```

All three modes pass the substantive qualification gates:

| Gate | O0 | O2 | O2-noinline |
|---|---:|---:|---:|
| AMD64 PE | PASS | PASS | PASS |
| PDB has debug info/types/IDs/globals/publics | PASS | PASS | PASS |
| Selected `S_COMPILE3` records | 5 | 5 | 5 |
| Selected LTCG `S_COMPILE3` records | 0 | 0 | 0 |
| Detours-owned procedure records | 136 | 136 | 136 |
| Unique raw PDB procedure names | 132 | 132 | 132 |
| Collision groups | 4 | 4 | 4 |
| Collision addresses | 8 | 8 | 8 |
| Raw PDB-name collision diagnostic | 5.88% | 5.88% | 5.88% |

The four duplicate raw-name groups are `StringCopyWorkerA`, `StringLengthWorkerA`,
`StringValidateDestA`, and `StringValidateDestAndLengthA`.

The linked PDB contains the Detours-owned compilands actually selected into
`withdll.exe`: `detours.obj`, `modules.obj`, `disasm.obj`, and `creatwth.obj`, with
matching source provenance. Other static-library objects are not counted when they
are not pulled into this concrete linked image.

Compact artifact-derived evidence:

```text
results/evidence/msvc/detours/qualification-summary.json
```

## Collision methodology

### GCC/DWARF

`scripts/measure_collisions.py` follows the relevant pinned DecBench C++ model:
resolved unqualified `DW_AT_name`, `DW_AT_specification` /
`DW_AT_abstract_origin` resolution, and project ownership based on compiled
`.i`/`.ii` translation-unit stems matched against `DW_AT_decl_file`.

```text
collision_rate = collision_addresses / source_function_addresses
```

### MSVC/PDB

`scripts/validate_detours_msvc.ps1` extracts CodeView procedures from the linked
PDB, scopes them to selected Detours-owned compilands, and records raw-name and
leaf-name collision diagnostics. `FRAMEPROC opt speed` is diagnostic only; it is
not used as an optimization-mode oracle.

The PDB metric is deliberately not asserted to be equivalent to DecBench's current
DWARF `DW_AT_name` identity metric.

## Evidence inventory

```text
# Local aarch64 GCC evidence
results/evidence/environment.txt
results/evidence/compile_report.json
results/evidence/collision/snappy_O0.json
results/evidence/collision/snappy_O2.json
results/evidence/collision/snappy_O2-noinline.json
results/evidence/collision/double-conversion_O0.json
results/evidence/collision/double-conversion_O2.json
results/evidence/collision/double-conversion_O2-noinline.json
results/evidence/collision/ninja_O0.json
results/evidence/collision/ninja_O2.json
results/evidence/collision/ninja_O2-noinline.json

# Compact x86_64 GCC artifact summary
results/evidence/x86_64/qualification-summary.json

# Compact native MSVC/PDB Detours artifact summary
results/evidence/msvc/detours/qualification-summary.json
```

## Recommendation

Evidence-backed candidates suitable for discussion now:

- **double-conversion v3.3.1** — clean numerical GCC/DWARF baseline;
- **Ninja v1.13.1** — real executable with moderate identity pressure and observed
  architecture sensitivity;
- **Snappy 1.2.2** — compact collision-heavy GCC/DWARF stress/control target;
- **Detours v4.0.1** — native Windows/MSVC/PDB systems target with actual PE/PDB
  runtime qualification.

DirectXTex and WinSparkle should remain **PENDING** until equivalent native
MSVC/PDB execution evidence is collected.

## Remaining caveats

This is **target/oracle qualification**, not a full end-to-end DecBench scoring run
for GED, type matching, byte matching, and every decompiler.

The GCC C++ identity problem remains unresolved by this work; the measurements
quantify exposure to the current short-name model. The Detours PDB metric is a
separate diagnostic and should remain labelled as such.
