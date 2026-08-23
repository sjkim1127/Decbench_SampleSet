# DecBench C++ Target Validation — Summary

**Validation date:** 2026-08-23  
**DecBench revision:** `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`  
**Host:** macOS 26.5.1 arm64  
**Build environment:** Docker `decbench-compile` image, Ubuntu 24.04 aarch64  
**Compiler:** GCC/G++ 13.3.0  
**MSVC/Wine environment:** not available on this host  
**Raw evidence:** `results/evidence/`

## Target status

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Project collision rate | Status |
|---|---|---|---|---|---|---|---|---|
| Snappy 1.2.2 | GCC/DWARF | PASS | PASS | PASS | `libsnappy.so.1.2.2` | DWARF + `.ii` | 52.87% / 53.16% / 51.97% | **VALIDATED** |
| double-conversion v3.3.1 | GCC/DWARF | PASS | PASS | PASS | `libdouble-conversion.so.3.3.0` | DWARF + `.ii` | 7.87% / 15.58% / 8.06% | **VALIDATED** |
| Ninja v1.13.1 | GCC/DWARF | PASS | PASS | PASS | `ninja` | DWARF + `.ii` | 26.70% / 30.42% / 26.70% | **VALIDATED WITH CAVEATS** |
| Detours v4.0.1 | MSVC/PDB | — | — | — | — | — | not measured | **BLOCKED** |
| DirectXTex may2026 | MSVC/PDB | — | — | — | — | — | not measured | **BLOCKED** |
| WinSparkle v0.9.4 | MSVC/PDB | — | — | — | — | — | not measured | **BLOCKED** |

Collision-rate order is `O0 / O2 / O2-noinline`.

## GCC/DWARF execution gates

All three GCC/DWARF targets completed the required qualification gates:

| Gate | Snappy | double-conversion | Ninja |
|---|---|---|---|
| All 3 modes built | PASS | PASS | PASS |
| Intended linked ELF per mode | 1 | 1 | 1 |
| Preprocessed `.ii` units per mode | 4 | 8 | 33 |
| Usable DWARF | yes | yes | yes |
| Collision analysis | complete | complete | complete |
| Unexpected LTO/IPO | none observed | none observed | none observed |

The machine-readable compile record is `results/evidence/compile_report.json`; it
contains all 9 target/mode entries with `ok: true`, one linked binary per entry,
and no recorded errors.

## Compiler-mode control

The validated modes are:

```text
O0:          g++ -O0 -g -fno-builtin -save-temps=obj + platform flags
O2:          g++ -O2 -g -fno-builtin -save-temps=obj + platform flags
O2-noinline: g++ -O2 -fno-inline -g -fno-builtin -save-temps=obj + platform flags
```

`DW_AT_producer` inspection found no `-flto`, profile-guided optimization, or
whole-program optimization flags in the validated binaries. Ninja's upstream
Release IPO path was avoided by leaving `CMAKE_BUILD_TYPE` empty.

## Collision methodology

`scripts/measure_collisions.py` uses the same relevant identity and source-scope
model as the pinned DecBench C++ ground-truth path for the current targets:

- identity key: resolved unqualified `DW_AT_name`;
- C++ resolution: follow `DW_AT_specification` / `DW_AT_abstract_origin` chains;
- project scope: derive translation-unit stems from compiled `.i` / `.ii` files;
- resolve `DW_AT_decl_file` and compare its basename stem through
  `strip_source_ext()` / source-stem matching;
- preserve demangled `DW_AT_linkage_name` only for diagnostics.

The metric is:

```text
collision_rate = collision_addresses / source_function_addresses
```

The raw JSON reports preserve both the project-source measurement and a broader raw
measurement over concrete emitted subprograms.

## Target findings

### double-conversion

The cleanest of the validated targets. Project collision exposure is **7.87% at
O0, 15.58% at O2, and 8.06% at O2-noinline**. Source-stem filtering removes
header-defined/multi-TU helper bodies that are outside DecBench's project
translation-unit scope. Remaining project collisions represent genuine C++
short-name identity cases in source-owned units.

### Ninja

A valuable real executable target with **26.70% / 30.42% / 26.70%** project
collision exposure. O0 and O2-noinline contain thousands of concretely emitted
standard-library/template/header functions, so the raw collision rate is much
higher than the DecBench project-source rate. The earlier CMake `_CMakeLTOTest-CXX`
`boo` artifact was removed from the final build output; recompilation confirms one
linked `ninja` executable per mode.

### Snappy

A compact but collision-heavy target at **52.87% / 53.16% / 51.97%** project
collision exposure. Overloaded compression APIs, repeated source/sink interface
method names, and GCC destructor variants create sustained ambiguity under the
current unqualified C++ identity model. It remains useful as a small stress/control
case rather than the clean baseline.

## Windows/MSVC status

The three Windows targets were statically reviewed, but runtime qualification was
not attempted because this host lacks the required environment:

```text
wine:        not available
cl.exe:      not available
link.exe:    not available
msbuild:     not available
Windows SDK: not installed
```

Therefore they remain **BLOCKED**, not FAIL and not PASS.

- **Detours v4.0.1:** requires real MSVC/NMAKE build, linked PE selection, PDB
  pairing, optimization override verification, and PDB collision measurement.
- **DirectXTex may2026:** requires MSVC/CMake runtime validation and overload-heavy
  PDB collision measurement.
- **WinSparkle v0.9.4:** requires MSBuild, LTCG/WholeProgramOptimization override
  verification, third-party compiland filtering, and PDB collision measurement.

## Evidence inventory

```text
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
```

## Recommendation

Recommend the three runtime-validated GCC/DWARF targets for discussion as an
initial C++ slice:

- **double-conversion v3.3.1** — clean numerical baseline;
- **Ninja v1.13.1** — real executable with moderate, quantified identity pressure;
- **Snappy 1.2.2** — compact collision-heavy baseline/stress case.

Keep Detours, DirectXTex, and WinSparkle as the Windows/MSVC shortlist until real
PE/PDB runtime evidence exists.

## Remaining caveat

All runtime evidence here is **aarch64**. Final corpus creation on x86-64 should
repeat the same build, DWARF, source-stem, and collision checks because emitted
functions and collision rates can change with architecture and toolchain behavior.
