# DecBench C++ target validation result — Google double-conversion

## Status

**VALIDATED** on the GCC/DWARF track at DecBench revision
`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

This is the cleanest currently validated C++ target in this workspace under
DecBench's existing unqualified `DW_AT_name` identity model.

## Target metadata

| Field | Value |
|---|---|
| Target | Google double-conversion |
| Upstream | `google/double-conversion` |
| Release/tag | `v3.3.1` |
| Resolved commit | `ae0dbfeb9744efd216c95b30555049d75d47116a` |
| Track | GCC / DWARF / `.ii` |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Validation date | 2026-08-23 |
| Host | macOS 26.5.1 arm64 |
| Build environment | `decbench-compile` Docker image, Ubuntu 24.04 aarch64 |
| Compiler | GCC/G++ 13.3.0 |
| Intended role | Numeric / floating-point / algorithmic library baseline |

## Build and ground-truth results

| Mode | Build | Linked image | `.ii` | Project addrs | Raw addrs | Project collisions | Raw collisions |
|---|---|---|---:|---:|---:|---:|---:|
| O0 | PASS | `libdouble-conversion.so.3.3.0` | 8 | 127 | 237 | **10 / 127 = 7.87%** | 74 / 237 = 31.22% |
| O2 | PASS | `libdouble-conversion.so.3.3.0` | 8 | 77 | 89 | **12 / 77 = 15.58%** | 19 / 89 = 21.35% |
| O2-noinline | PASS | `libdouble-conversion.so.3.3.0` | 8 | 124 | 267 | **10 / 124 = 8.06%** | 113 / 267 = 42.32% |

All three modes produced one intended linked ELF image, eight preprocessed `.ii`
translation units, and usable DWARF. The compile report records no errors.

## Optimization control

The CMake build is configured with an empty `CMAKE_BUILD_TYPE`, shared-library
output, tests disabled, and DecBench's flags injected through
`CMAKE_CXX_FLAGS="$CFLAGS"`.

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

No LTO/IPO/profile flags were observed in the final compiler producer metadata.

## Project source scope

The project metric uses the same source-stem model as DecBench. The eight compiled
translation units are:

```text
bignum-dtoa.cc
bignum.cc
cached-powers.cc
double-to-string.cc
fast-dtoa.cc
fixed-dtoa.cc
string-to-double.cc
strtod.cc
```

This distinction matters substantially for double-conversion. Header-defined helper
functions can be emitted into several translation units and therefore produce many
raw duplicate names, but DecBench's project-source oracle intentionally retains only
functions whose `DW_AT_decl_file` stem matches an actual compiled translation unit.
That is why the final project collision rate is much lower than the raw rate.

## Collision methodology

The identity key is resolved `DW_AT_name`, following the same
`DW_AT_specification` / C++ `DW_AT_abstract_origin` chain used by DecBench. The
project scope is then restricted with DecBench-style `.i`/`.ii` source-stem
matching. Demangled linkage names are diagnostic only.

```text
collision_rate = collision_addresses / source_function_addresses
```

The committed reports preserve both project and raw measurements so the effect of
source filtering is auditable.

## Main finding

double-conversion has the best current collision profile of the three validated
GCC/DWARF targets:

```text
O0          7.87%
O2         15.58%
O2-noinline 8.06%
```

The remaining project collisions are genuine C++ identity cases in source-owned
translation units: overloaded methods, constructors, const/non-const variants, and
similar functions that share an unqualified `DW_AT_name`. They are not caused by
the earlier short-name parser bug and are not dominated by standard-library
instantiations.

The raw metric is intentionally higher at O0 and O2-noinline because non-inlined
header/template bodies remain concretely emitted in DWARF. Those functions are not
part of DecBench's project translation-unit ground-truth set.

## Evidence

Canonical evidence:

```text
results/evidence/compile_report.json
results/evidence/environment.txt
results/evidence/collision/double-conversion_O0.json
results/evidence/collision/double-conversion_O2.json
results/evidence/collision/double-conversion_O2-noinline.json
```

Each JSON report records the exact source stems, linked image, address totals,
collision groups, and representative diagnostic names.

## Qualification decision

double-conversion is **VALIDATED** and **recommended** for the initial C++ corpus.
It provides:

- a small dependency-light real C++ library;
- a substantially different workload from compression/tooling targets;
- controlled O0/O2/O2-noinline builds;
- clean `.ii` and DWARF ground truth;
- the lowest measured current short-name collision exposure in this target set.

Its 8–16% project collision rate should still be treated as a known property of
the present DecBench C++ identity model rather than ignored.

## Remaining caveat

The current evidence is from GCC 13.3.0 on **aarch64**. The final corpus should
re-run the same checks on its production architecture, particularly x86-64 if that
becomes the publication target.
