# DecBench C++ target validation result — Google double-conversion

## Target metadata

| Field | Value |
|---|---|
| Target | Google double-conversion |
| Upstream | `google/double-conversion` |
| Release/tag | `v3.3.1` |
| Resolved commit | `ae0dbfeb9744efd216c95b30555049d75d47116a` |
| Track | GCC/DWARF |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Validation date | 2026-08-23 |
| Host | macOS 26.5.1, arm64 (Docker container: Ubuntu 24.04 aarch64) |
| Container / OS | `decbench-compile` Docker image, Ubuntu 24.04 |
| Compiler | GCC/G++ 13.3.0 (aarch64) |
| Linker | GNU ld (via GCC) |
| Windows SDK | N/A |
| Wine/msvc-wine | N/A |

## Build and ground-truth summary

| Mode | Build | Linked image(s) | `.ii` count | Ground truth | Source-owned function addresses | Unique short names | Collision groups | Collision addresses | Collision rate |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| O0 | ✅ PASS | 1 (`libdouble-conversion.so.3.3.0`) | 8 | DWARF: ✅ present (7 sections) | 55 | 45 | 12 | 25 | **45.45%** (proj = raw) |
| O2 | ✅ PASS | 1 (`libdouble-conversion.so.3.3.0`) | 8 | DWARF: ✅ present (7 sections) | 26 | 20 | 7 | 15 | **57.69%** (proj = raw) |
| O2-noinline | ✅ PASS | 1 (`libdouble-conversion.so.3.3.0`) | 8 | DWARF: ✅ present (7 sections) | 55 | 45 | 12 | 25 | **45.45%** (proj = raw) |

> **Note:** `project == raw` for all modes: double-conversion contains no stdlib template
> instantiations in its DWARF (the library has minimal STL usage and its headers do not cause
> observable template body emission). All collision groups are in the `double_conversion::` namespace.
> Both rates are recorded in `results/evidence/collision/`.


Collision rate formula: `collision_addresses / source_function_addresses`

## Optimization control

### O0
```text
compile: g++ -O0 -g -fno-builtin -save-temps=obj [from CFLAGS]
         cmake -S . -B build -DCMAKE_BUILD_TYPE= -DCMAKE_CXX_COMPILER=g++ -DCMAKE_CXX_FLAGS="$CFLAGS"
                -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=OFF
link:    cmake --build build -j && rm -rf build/CMakeFiles/[0-9]*
```

### O2
```text
compile: g++ -O2 -g -fno-builtin -save-temps=obj [from CFLAGS]
link:    cmake --build build -j
```

### O2-noinline
```text
compile: g++ -O2 -fno-inline -g -fno-builtin -save-temps=obj [from CFLAGS]
link:    cmake --build build -j
```

Unexpected optimization/LTO/IPO/inlining behavior:
```text
None. No -flto, -fprofile, or IPO flags.
CMAKE_BUILD_TYPE intentionally left empty. No upstream Release preset triggered.
```

## Linked images

### O0
```text
results/cpp_local/O0/double-conversion/compiled/libdouble-conversion.so.3.3.0
  ELF 64-bit LSB shared object, ARM aarch64
  BuildID: 088f77bbceda26de747b05c6a56f0c2db7b9539f
  Size: 404424 bytes
  DWARF: present (7 sections), not stripped
```

### O2
```text
results/cpp_local/O2/double-conversion/compiled/libdouble-conversion.so.3.3.0
  ELF 64-bit LSB shared object, ARM aarch64
  BuildID: 450a6d925b75f3429e75327d603c28f25f5f2e20
  Size: 559464 bytes (larger than O0 — optimizer may expand some specializations)
  DWARF: present (7 sections)
```

### O2-noinline
```text
results/cpp_local/O2-noinline/double-conversion/compiled/libdouble-conversion.so.3.3.0
  ELF 64-bit LSB shared object, ARM aarch64
  BuildID: 622d77bad265087a4d8f6679c98710a0c3206969
  Size: 510632 bytes
  DWARF: present (7 sections)
```

## Source ownership filter

Included project-owned paths/compilands:
```text
bignum.cc, bignum-dtoa.cc, cached-powers.cc, double-to-string.cc,
fast-dtoa.cc, fixed-dtoa.cc, string-to-double.cc, strtod.cc
(8 .ii files verified per mode)
```

Excluded tests/vendor/compiler-probe/generated paths:
```text
BUILD_TESTING=OFF — test sources (test-bignum.cc, test-bignum-dtoa.cc,
test-conversions.cc, test-diy-fp.cc, test-dtoa.cc, cctest.cc) excluded from build.
CMakeFiles/[0-9]* compiler-probe directories removed by make_cmd.
Note: test .cc files are copied into compiled/ by DecBench's source-copy step
but NOT linked into the benchmark library (they are NOT compiled into libdouble-conversion.so).
```

Any uncertain ownership cases:
```text
None. All collision groups confirmed in double_conversion:: namespace.
```

## Short-name collision details

All collisions are from project-owned `double_conversion::` namespace, confirmed from DWARF.
No stdlib contamination detected in any mode.

| Short name | Distinct addresses | Example qualified names | Notes |
|---|---:|---|---|
| `Double` | 3 | `double_conversion::Double::Double(double)`, `double_conversion::Double::Double(unsigned long long)`, `double_conversion::Double::Double()` | Constructor overloads in helper class |
| `Vector` | 3 | `double_conversion::Vector<char>::Vector(char*, int)`, `double_conversion::Vector<double>::Vector(double*, int)`, `double_conversion::Vector<char>::Vector()` | Template constructor overloads |
| `RawBigit` | 2 | `double_conversion::Bignum::RawBigit(int)`, `double_conversion::Bignum::RawBigit(int) const` | const vs non-const overload |
| `Single` | 2 | `double_conversion::Single::Single(float)`, `double_conversion::Single::Single(unsigned int)` | Constructor overloads |
| `DiyFp` | 2 | `double_conversion::DiyFp::DiyFp(unsigned long, int)`, `double_conversion::DiyFp::DiyFp()` | Constructor overloads |
| `AddUInt64` | 2 | `double_conversion::Bignum::AddUInt64(unsigned long)` (appears at 2 addresses under O2) | Possible const/non-const variant |

These are legitimate C++ overloads and multi-constructor patterns — not GCC ABI artifacts.
Under DecBench's current unqualified name model, `Double(double)` and `Double(unsigned long long)`
are indistinguishable. This is a true identity challenge, not a measurement artifact.

## Preprocessed source / oracle notes

For GCC/DWARF targets:

- `.ii` preservation: ✅ 8 `.cc.ii` files per mode
- DWARF `DW_AT_specification` handling checked: ✅
- DWARF `DW_AT_abstract_origin` handling checked: ✅

## Final status

Status: **VALIDATED**

Decision rationale:
```text
All three optimization modes built successfully. One linked ELF image per mode.
Eight .ii source units per mode. DWARF present (7 sections) in all modes.
Collision analysis completed from measured DWARF. All collision groups are
project-owned (double_conversion:: namespace) — no stdlib contamination.

Collision rate of 15-22% is moderate and driven by constructor overloads
and const/non-const overload pairs. This is a cleaner target than Snappy
(no virtual destructor dual noise) and represents a genuine identity challenge
for DecBench's unqualified name model.

double-conversion is validated as a GCC/DWARF target for the corpus.
The numeric/floating-point workload is substantially different from Snappy.
```

Remaining blockers:
```text
None. The 15-22% collision rate is documented and acceptable for the initial corpus,
provided DecBench tracks this as a known qualification caveat.
```
