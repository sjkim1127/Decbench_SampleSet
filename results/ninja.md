# DecBench C++ target validation result — Ninja

## Status

**VALIDATED WITH CAVEATS** on the GCC/DWARF track at DecBench revision
`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

Ninja is the largest and most application-like of the three validated GCC targets.
Its build path is now clean, but its project-level short-name collision exposure is
materially higher than double-conversion.

## Target metadata

| Field | Value |
|---|---|
| Target | Ninja |
| Upstream | `ninja-build/ninja` |
| Release/tag | `v1.13.1` |
| Resolved commit | `79feac0f3e3bc9da9effc586cd5fea41e7550051` |
| Track | GCC / DWARF / `.ii` |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Validation date | 2026-08-23 |
| Host | macOS 26.5.1 arm64 |
| Build environment | `decbench-compile` Docker image, Ubuntu 24.04 aarch64 |
| Compiler | GCC/G++ 13.3.0 |
| Intended role | Real system/tooling executable with parser, graph, filesystem, and subprocess logic |

## Build and ground-truth results

| Mode | Build | Linked image | `.ii` | Project addrs | Raw addrs | Project collisions | Raw collisions |
|---|---|---|---:|---:|---:|---:|---:|
| O0 | PASS | `ninja` | 33 | 412 | 4068 | **110 / 412 = 26.70%** | 2674 / 4068 = 65.73% |
| O2 | PASS | `ninja` | 33 | 355 | 557 | **108 / 355 = 30.42%** | 229 / 557 = 41.11% |
| O2-noinline | PASS | `ninja` | 33 | 412 | 4444 | **110 / 412 = 26.70%** | 3145 / 4444 = 70.77% |

The final compile report shows exactly **one intended linked binary per mode** and
no compile errors. All 33 `.ii` units are preserved.

## Optimization control

Ninja's upstream Release configuration can enable IPO/LTO, so the validation
configuration deliberately leaves `CMAKE_BUILD_TYPE` empty and builds only the
`ninja` target.

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

`DW_AT_producer` inspection confirms the intended optimization mode and no
`-flto`, profile-guided optimization, or whole-program optimization flags.

## CMake artifact contamination — resolved

The first local run exposed a non-target executable named `boo` under CMake's
internal `_CMakeLTOTest-CXX` area. It was not a Ninja benchmark image: it had no
usable target DWARF and originated from CMake's own probe/test machinery.

The target config was tightened to build only the real executable and remove CMake
probe directories after the build:

```text
cmake --build build -j --target ninja &&
rm -rf build/CMakeFiles/[0-9]* build/CMakeFiles/_*
```

After recompilation, `results/evidence/compile_report.json` records
`linked_binaries: 1` for Ninja in O0, O2, and O2-noinline.

## Project source scope

The project metric follows DecBench's `.ii` source-stem matching. Ninja contributes
33 compiled translation units, including its parser, build graph, logs, filesystem,
subprocess, scheduling, and CLI implementation.

At O0 and O2-noinline, the executable contains thousands of concrete standard
library/template subprograms. They remain visible in the **raw** measurement, but
DecBench's project-source stem filter excludes them from the benchmark's own-source
function set.

This is why the raw collision rate reaches 66–71% while the project rate remains
27–30%.

## Collision methodology

The collision key is resolved unqualified `DW_AT_name`; project ownership is based
on the same compiled `.i`/`.ii` translation-unit stem matching used by DecBench's
`project_source_functions()` / eval-kit resolver. Demangled linkage names are kept
for diagnosis only.

```text
collision_rate = collision_addresses / source_function_addresses
```

## Main finding

Ninja's project collision profile is stable but non-trivial:

```text
O0          26.70%
O2         30.42%
O2-noinline 26.70%
```

Representative source-owned collision groups in the final evidence include common
C++ method names such as:

- `LoadDyndeps`
- `Dump`
- `AddTarget`
- `Parse`
- `Load`
- `OpenForWrite`
- `Reset`
- `Start` / `Finish`
- destructor names for virtual/interface classes

These collisions are exactly the kind of ambiguity created when class/namespace and
signature information are discarded and only `DW_AT_name` is used as function
identity.

## Evidence

Canonical evidence:

```text
results/evidence/compile_report.json
results/evidence/environment.txt
results/evidence/collision/ninja_O0.json
results/evidence/collision/ninja_O2.json
results/evidence/collision/ninja_O2-noinline.json
```

The JSON reports retain both raw and project-scoped counts so the effect of
standard-library/template emission is directly inspectable.

## Qualification decision

Ninja remains **VALIDATED WITH CAVEATS** and **recommended** for the initial corpus.
It is valuable precisely because it differs from the two library targets:

- it is a complete executable;
- it exercises parsing, graphs, filesystem operations, process execution, and build
  scheduling;
- the benchmark controls its optimization modes without upstream LTO contamination;
- its current identity-collision pressure is substantial but quantified.

The target configuration itself has no remaining known build blocker.

## Remaining caveat

The current qualification is GCC 13.3.0 **aarch64**. A final x86-64 corpus should
re-run function-count and collision measurements because architecture-specific
codepaths, optimization decisions, and emitted template bodies can change the
numbers.
