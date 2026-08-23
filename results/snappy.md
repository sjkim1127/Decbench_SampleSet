# DecBench C++ target validation result — Google Snappy

## Status

**VALIDATED** on the GCC/DWARF track at DecBench revision
`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

Snappy has now been qualified on both the original local aarch64 environment and a
GitHub-hosted x86_64 environment. The x86_64 project function counts and collision
rates reproduce the aarch64 results exactly for all three modes.

## Target metadata

| Field | Value |
|---|---|
| Target | Google Snappy |
| Upstream | `google/snappy` |
| Release/tag | `1.2.2` |
| Resolved commit | `6af9287fbdb913f0794d0148c6aa43b58e63c8e3` |
| Track | GCC / DWARF / `.ii` |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Compiler | GCC/G++ 13.3.0 |
| Local qualification | Ubuntu 24.04 aarch64 in `decbench-compile` Docker |
| CI requalification | GitHub Actions Ubuntu x86_64 |
| Intended role | Small real-world compression/library stress baseline |

## Build and ground-truth results

The project-source results are identical on aarch64 and x86_64:

| Mode | Build | Linked image | `.ii` | Project addrs | Project collisions |
|---|---|---|---:|---:|---:|
| O0 | PASS | `libsnappy.so.1.2.2` | 4 | 157 | **83 / 157 = 52.87%** |
| O2 | PASS | `libsnappy.so.1.2.2` | 4 | 79 | **42 / 79 = 53.16%** |
| O2-noinline | PASS | `libsnappy.so.1.2.2` | 4 | 152 | **79 / 152 = 51.97%** |

The original aarch64 raw measurements are:

```text
O0          167 / 341 = 48.97%
O2           42 /  84 = 50.00%
O2-noinline 163 / 332 = 49.10%
```

All three modes produce exactly one intended linked ELF image and four preprocessed
`.ii` units.

## Optimization control

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

The x86_64 `DW_AT_producer` audit identifies `EM_X86_64`, the requested mode flags,
and no LTO/WPA markers. Snappy's producer metadata also records its project-specific
`-fno-exceptions` and `-fno-rtti` settings.

## Project source scope

The DecBench-aligned project set is restricted to the four compiled translation
units:

```text
snappy.cc
snappy-c.cc
snappy-sinksource.cc
snappy-stubs-internal.cc
```

Header/template functions that do not resolve to these source stems remain visible
in raw binary diagnostics but are outside the benchmark's project-source set.

## Collision methodology

Collision identity is resolved unqualified `DW_AT_name`, following
`DW_AT_specification` and C++ `DW_AT_abstract_origin`. Demangled linkage names are
diagnostic only.

```text
collision_rate = collision_addresses / source_function_addresses
```

## Main finding

Snappy remains a useful **collision-heavy compact target**. The 52–53% rate is
stable across optimization modes and across the aarch64/x86_64 requalification.
Representative causes include overloaded compression APIs, repeated Source/Sink
interface method names, and GCC ABI destructor variants.

This makes Snappy more useful as an identity stress/control case than as the clean
baseline.

## Evidence

```text
# local aarch64
results/evidence/compile_report.json
results/evidence/environment.txt
results/evidence/collision/snappy_O0.json
results/evidence/collision/snappy_O2.json
results/evidence/collision/snappy_O2-noinline.json

# GitHub Actions x86_64 artifact-derived summary
results/evidence/x86_64/qualification-summary.json
```

The x86_64 source artifact is workflow run `32632337105`, artifact `9491409143`,
SHA-256 `60fef5ba7bb9a252e0d8155cd7b775a54679ed2ff4b92b2d6152e7e54f01ccc2`.

## Qualification decision

Snappy remains **VALIDATED** and recommended as a compact collision-stress target.
The prior aarch64-only caveat is resolved by the independent x86_64 qualification;
future corpus builds should still rerun the same checks if compiler version or
benchmark build policy changes.
