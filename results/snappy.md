# DecBench C++ target validation result — Google Snappy

## Status

**VALIDATED** on the GCC/DWARF track at DecBench revision
`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

This report is synchronized with the machine-readable evidence under
`results/evidence/` and the final source-stem collision methodology in
`scripts/measure_collisions.py`.

## Target metadata

| Field | Value |
|---|---|
| Target | Google Snappy |
| Upstream | `google/snappy` |
| Release/tag | `1.2.2` |
| Resolved commit | `6af9287fbdb913f0794d0148c6aa43b58e63c8e3` |
| Track | GCC / DWARF / `.ii` |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Validation date | 2026-08-23 |
| Host | macOS 26.5.1 arm64 |
| Build environment | `decbench-compile` Docker image, Ubuntu 24.04 aarch64 |
| Compiler | GCC/G++ 13.3.0 |
| Intended role | Small real-world compression/library baseline |

## Build and ground-truth results

| Mode | Build | Linked image | `.ii` | Project addrs | Raw addrs | Project collisions | Raw collisions |
|---|---|---|---:|---:|---:|---:|---:|
| O0 | PASS | `libsnappy.so.1.2.2` | 4 | 157 | 341 | **83 / 157 = 52.87%** | 167 / 341 = 48.97% |
| O2 | PASS | `libsnappy.so.1.2.2` | 4 | 79 | 84 | **42 / 79 = 53.16%** | 42 / 84 = 50.00% |
| O2-noinline | PASS | `libsnappy.so.1.2.2` | 4 | 152 | 332 | **79 / 152 = 51.97%** | 163 / 332 = 49.10% |

All three builds contain usable DWARF and exactly one intended linked ELF image.
The compile report records no build errors.

## Optimization control

The target configuration leaves `CMAKE_BUILD_TYPE` empty and injects DecBench's
flags through `CMAKE_CXX_FLAGS="$CFLAGS"`.

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

`DW_AT_producer` inspection did not show `-flto`, profile-guided optimization,
whole-program optimization, or an upstream Release IPO preset. On this aarch64
host, Snappy's normal CMake feature detection enabled the architecture-appropriate
SIMD path; this is part of the recorded aarch64 qualification and is one reason
x86-64 should be re-qualified before final corpus publication.

## Project source scope

The project ground-truth set follows DecBench's source-stem rule: compiled `.ii`
translation-unit stems are matched against each function's resolved
`DW_AT_decl_file` basename.

The four translation units are:

```text
snappy.cc
snappy-c.cc
snappy-sinksource.cc
snappy-stubs-internal.cc
```

Header-defined helpers and standard-library/template bodies that do not resolve to
one of these translation-unit stems remain visible in the raw metric but are not
counted as project-source functions.

## Collision methodology

Collision identity is the resolved unqualified `DW_AT_name`, following
`DW_AT_specification` and, for C++, `DW_AT_abstract_origin` exactly as DecBench's
DWARF ground-truth path does. Demangled `DW_AT_linkage_name` is retained only as
diagnostic metadata.

The metric is:

```text
collision_rate = addresses belonging to duplicated DW_AT_name groups
                 ----------------------------------------------------
                 all source-function addresses in the selected scope
```

This is intentionally a measure of how much DecBench's current unqualified C++
identity model is exposed to ambiguity; it is not a claim that the binary itself
is ambiguous.

## Main finding

Snappy is a useful **collision-heavy small target**. Its project collision rate is
stable at roughly 52–53% across all three optimization modes.

Representative causes observed in DWARF include:

- overloaded APIs such as `Compress`, `Uncompress`, `RawCompress`, and
  `CompressFromIOVec`;
- repeated virtual-interface names across `Source`/`Sink` implementations such as
  `Available`, `Peek`, `Skip`, and buffer methods;
- GCC ABI destructor variants that produce multiple concrete addresses with the
  same `DW_AT_name`, e.g. `~Source`, `~Sink`, and
  `~UncheckedByteArraySink`.

The high rate therefore reflects real pressure on the current short-name identity
model rather than a build failure or measurement parser artifact.

## Evidence

Canonical evidence:

```text
results/evidence/compile_report.json
results/evidence/environment.txt
results/evidence/collision/snappy_O0.json
results/evidence/collision/snappy_O2.json
results/evidence/collision/snappy_O2-noinline.json
```

The JSON collision reports preserve source stems, linked image paths, project/raw
address counts, collision groups, addresses, and representative demangled names.

## Qualification decision

Snappy remains **VALIDATED** and **recommended** for an initial C++ corpus because:

- all required optimization modes build through the real DecBench compile path;
- one linked shared object is produced per mode;
- four `.ii` units are preserved per mode;
- DWARF ground truth is usable;
- optimization control is clean;
- its collision behavior is measured and reproducible.

The collision rate is not a reason to discard the target. Instead, Snappy provides
a compact regression/stress case for the exact C++ function-identity problem that
DecBench is currently exposing.

## Remaining caveat

This qualification was performed on GCC 13.3.0 **aarch64**. Re-run the same
artifact checks on the architecture used for the final multi-language corpus,
especially if that corpus is produced on x86-64.
