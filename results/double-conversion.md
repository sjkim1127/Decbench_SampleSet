# DecBench C++ target validation result — Google double-conversion

## Status

**VALIDATED** on the GCC/DWARF track at DecBench revision
`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

double-conversion remains the cleanest current GCC/DWARF target in this workspace
under DecBench's existing unqualified `DW_AT_name` identity model. Its project
function counts and collision rates reproduce exactly between the original aarch64
qualification and the GitHub-hosted x86_64 requalification.

## Target metadata

| Field | Value |
|---|---|
| Target | Google double-conversion |
| Upstream | `google/double-conversion` |
| Release/tag | `v3.3.1` |
| Resolved commit | `ae0dbfeb9744efd216c95b30555049d75d47116a` |
| Track | GCC / DWARF / `.ii` |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Compiler | GCC/G++ 13.3.0 |
| Local qualification | Ubuntu 24.04 aarch64 in `decbench-compile` Docker |
| CI requalification | GitHub Actions Ubuntu x86_64 |
| Intended role | Numeric / floating-point / algorithmic library baseline |

## Build and ground-truth results

The project-source results are identical on aarch64 and x86_64:

| Mode | Build | Linked image | `.ii` | Project addrs | Project collisions |
|---|---|---|---:|---:|---:|
| O0 | PASS | `libdouble-conversion.so.3.3.0` | 8 | 127 | **10 / 127 = 7.87%** |
| O2 | PASS | `libdouble-conversion.so.3.3.0` | 8 | 77 | **12 / 77 = 15.58%** |
| O2-noinline | PASS | `libdouble-conversion.so.3.3.0` | 8 | 124 | **10 / 124 = 8.06%** |

The original aarch64 raw measurements are:

```text
O0           74 / 237 = 31.22%
O2           19 /  89 = 21.35%
O2-noinline 113 / 267 = 42.32%
```

All three modes produce one intended linked ELF image, eight `.ii` units, and
usable DWARF.

## Optimization control

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

The x86_64 producer audit reports `EM_X86_64`, the expected mode flags, and no
LTO/WPA markers.

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

Header-defined helpers can be emitted into several translation units and therefore
create many raw duplicate names. DecBench's project-source oracle retains only
functions whose `DW_AT_decl_file` stem matches an actual compiled translation unit,
which is why the project metric is much cleaner than the raw emitted-binary metric.

## Collision methodology

The identity key is resolved `DW_AT_name`, following the same
`DW_AT_specification` / C++ `DW_AT_abstract_origin` chain used by DecBench. The
project set is then restricted using compiled `.i`/`.ii` source-stem matching.
Demangled linkage names are diagnostic only.

```text
collision_rate = collision_addresses / source_function_addresses
```

## Main finding

double-conversion has the lowest measured project collision exposure in the current
GCC/DWARF shortlist:

```text
O0           7.87%
O2          15.58%
O2-noinline  8.06%
```

The remaining collisions are genuine C++ short-name identity cases in source-owned
translation units rather than standard-library/template domination.

## Evidence

```text
# local aarch64
results/evidence/compile_report.json
results/evidence/environment.txt
results/evidence/collision/double-conversion_O0.json
results/evidence/collision/double-conversion_O2.json
results/evidence/collision/double-conversion_O2-noinline.json

# GitHub Actions x86_64 artifact-derived summary
results/evidence/x86_64/qualification-summary.json
```

The x86_64 source artifact is workflow run `32632337105`, artifact `9491409143`,
SHA-256 `60fef5ba7bb9a252e0d8155cd7b775a54679ed2ff4b92b2d6152e7e54f01ccc2`.

## Qualification decision

double-conversion remains **VALIDATED** and recommended as the clean baseline for
an initial C++ corpus slice. The prior aarch64-only caveat is resolved by the
x86_64 qualification; future compiler/toolchain changes should still trigger the
same reproducibility checks.
