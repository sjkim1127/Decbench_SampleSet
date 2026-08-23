# DecBench C++ target validation result — Ninja

## Status

**VALIDATED WITH CAVEATS** on the GCC/DWARF track at DecBench revision
`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

Ninja is the largest and most application-like of the three validated GCC targets.
It has now been qualified both locally on aarch64 and independently on GitHub-hosted
x86_64. Unlike Snappy and double-conversion, its optimized project function counts
change materially across architectures.

## Target metadata

| Field | Value |
|---|---|
| Target | Ninja |
| Upstream | `ninja-build/ninja` |
| Release/tag | `v1.13.1` |
| Resolved commit | `79feac0f3e3bc9da9effc586cd5fea41e7550051` |
| Track | GCC / DWARF / `.ii` |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Compiler | GCC/G++ 13.3.0 |
| Local qualification | Ubuntu 24.04 aarch64 in `decbench-compile` Docker |
| CI requalification | GitHub Actions Ubuntu x86_64 |
| Intended role | Real system/tooling executable with parser, graph, filesystem, and subprocess logic |

## Build results

Both architectures pass all three build modes with exactly one intended `ninja`
executable and 33 preprocessed `.ii` units per mode.

### aarch64 project-source result

| Mode | Project addrs | Project collision |
|---|---:|---:|
| O0 | 412 | **110 / 412 = 26.70%** |
| O2 | 355 | **108 / 355 = 30.42%** |
| O2-noinline | 412 | **110 / 412 = 26.70%** |

### x86_64 project-source result

| Mode | Project addrs | Project collision |
|---|---:|---:|
| O0 | 412 | **110 / 412 = 26.70%** |
| O2 | 210 | **68 / 210 = 32.38%** |
| O2-noinline | 265 | **73 / 265 = 27.55%** |

The local aarch64 raw measurements were:

```text
O0          2674 / 4068 = 65.73%
O2           229 /  557 = 41.11%
O2-noinline 3145 / 4444 = 70.77%
```

## Optimization control

Ninja's upstream Release configuration can enable IPO/LTO. The qualification
configuration deliberately leaves `CMAKE_BUILD_TYPE` empty, injects DecBench's
flags, and builds only the `ninja` target.

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

The x86_64 artifact contains a producer audit for all three modes. Every final
binary is `EM_X86_64`, contains the expected optimization flags, and has an empty
LTO-marker set. In particular, the upstream CMake message that IPO/LTO is
**supported** does not mean LTO was applied to the qualified Ninja binary.

## CMake artifact contamination — resolved

An early local run exposed a CMake `_CMakeLTOTest-CXX` probe binary named `boo`.
It was not a benchmark output. The target config was tightened to build only the
real executable and remove CMake probe directories after the build.

Final qualification records exactly one linked `ninja` executable in every mode on
both architectures.

## Project source scope

Ninja contributes 33 compiled translation units covering parser logic, build graph,
logs/state, filesystem operations, subprocess control, scheduling, and CLI logic.

At low/no-inline optimization the raw executable contains thousands of concrete
standard-library/template/header functions. DecBench's project-source stem filter
excludes those emitted-library bodies from the project metric.

## Collision methodology

The collision key is resolved unqualified `DW_AT_name`; project ownership follows
the compiled `.i`/`.ii` translation-unit stem matching used by DecBench's C++
ground-truth path. Demangled linkage names remain diagnostic only.

```text
collision_rate = collision_addresses / source_function_addresses
```

## Architecture finding

The architecture comparison is now itself part of the qualification result:

```text
O0:          aarch64 412 / 26.70%  == x86_64 412 / 26.70%
O2:          aarch64 355 / 30.42%  != x86_64 210 / 32.38%
O2-noinline: aarch64 412 / 26.70%  != x86_64 265 / 27.55%
```

Because the x86_64 producer audit excludes LTO/WPA markers, the optimized count
difference is consistent with architecture/backend-dependent code generation,
inlining, and emitted-function selection rather than accidental upstream IPO.

Representative collision groups include repeated C++ method names such as
`LoadDyndeps`, `Dump`, `AddTarget`, `Parse`, `Load`, `OpenForWrite`, `Reset`, and
other class-local operations that collapse under an unqualified identity key.

## Evidence

```text
# local aarch64
results/evidence/compile_report.json
results/evidence/environment.txt
results/evidence/collision/ninja_O0.json
results/evidence/collision/ninja_O2.json
results/evidence/collision/ninja_O2-noinline.json

# GitHub Actions x86_64 artifact-derived summary
results/evidence/x86_64/qualification-summary.json
```

The x86_64 source artifact is workflow run `32632337105`, artifact `9491409143`,
SHA-256 `60fef5ba7bb9a252e0d8155cd7b775a54679ed2ff4b92b2d6152e7e54f01ccc2`.

## Qualification decision

Ninja remains **VALIDATED WITH CAVEATS** and recommended as the real executable /
moderate-identity-pressure target. The important caveat is no longer missing
x86_64 evidence; it is that optimized source-function counts are demonstrably
architecture-sensitive, so future publication builds should preserve the exact
architecture/toolchain in benchmark metadata.
