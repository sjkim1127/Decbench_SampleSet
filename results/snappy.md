# DecBench C++ target validation result — Google Snappy

## Target metadata

| Field | Value |
|---|---|
| Target | Google Snappy |
| Upstream | `google/snappy` |
| Release/tag | `1.2.2` |
| Resolved commit | `6af9287fbdb913f0794d0148c6aa43b58e63c8e3` |
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
| O0 | ✅ PASS | 1 (`libsnappy.so.1.2.2`) | 4 | DWARF: ✅ present (7 sections) | 38 (proj) / 70 (raw) | 24 / 43 | 11 / 18 | 17 / 46 | **44.74%** (proj) / 65.71% (raw) |
| O2 | ✅ PASS | 1 (`libsnappy.so.1.2.2`) | 4 | DWARF: ✅ present (7 sections) | 19 (proj) / 19 (raw) | 14 / 14 | 5 / 5 | 10 / 10 | **52.63%** (proj) / 52.63% (raw) |
| O2-noinline | ✅ PASS | 1 (`libsnappy.so.1.2.2`) | 4 | DWARF: ✅ present (7 sections) | 33 (proj) / 63 (raw) | 20 / 39 | 10 / 17 | 15 / 44 | **45.45%** (proj) / 69.84% (raw) |

> **Collision measurement methodology:** `scripts/measure_collisions.py` runs against the ELF and
> produces two rates per image:
> - **raw**: all concrete DWARF subprograms excluding CMake probe CUs
> - **project**: subprograms whose fully-qualified demangled name does NOT start with a stdlib/system
>   namespace prefix (`std::`, `__gnu_cxx::`, `__cxxabiv::`, `__detail::`, `__gnu_pbds::`)
>
> Because DecBench builds in `/tmp/tmp*/` sandboxes, source-path–based CU filtering cannot
> distinguish stdlib template instantiations from project code. Namespace-prefix filtering is the
> authoritative project-owned rate. Both values are recorded in `results/evidence/collision/`.
>
> The O0/O2-noinline `raw ≠ project` delta is from libstdc++ template bodies emitted into the
> shared library when inlining is disabled. At O2 all 19 concrete subprograms are project-owned
> (no stdlib template bodies survive inlining), so raw == project.
>
> The project collision rate (44–53%) is driven primarily by **virtual destructor duals**: GCC emits
> both a D1 (complete-object) and D2 (base-object) destructor for every virtual class, giving two
> distinct addresses with the same demangled short name.


Collision rate formula: `collision_addresses / source_function_addresses`

## Optimization control

DW_AT_producer from O2 build:
```
GNU C++17 13.3.0 -mlittle-endian -mabi=lp64 -g -O2 -fno-builtin ...
```

### O0
```text
compile: g++ -O0 -g -fno-builtin -save-temps=obj [from CFLAGS] + CMake project flags
         cmake -S . -B build -DCMAKE_BUILD_TYPE= -DCMAKE_CXX_COMPILER=g++ -DCMAKE_CXX_FLAGS="$CFLAGS"
                -DBUILD_SHARED_LIBS=ON -DSNAPPY_BUILD_TESTS=OFF -DSNAPPY_BUILD_BENCHMARKS=OFF
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
None. No -flto, -fprofile, or IPO flags detected in DW_AT_producer.
DecBench correctly controls optimization through CFLAGS injection.
CMAKE_BUILD_TYPE intentionally left empty — no upstream Release preset triggered.
NEON SIMD was detected/enabled by Snappy's CMake checks (aarch64 host).
```

## Linked images

### O0
```text
results/cpp_local/O0/snappy/compiled/libsnappy.so.1.2.2
  ELF 64-bit LSB shared object, ARM aarch64, dynamically linked
  BuildID: b53a58ae4070a435d058d1619290996a80aec828
  Size: 850720 bytes
  DWARF: present (7 sections)
  Not stripped
```

### O2
```text
results/cpp_local/O2/snappy/compiled/libsnappy.so.1.2.2
  ELF 64-bit LSB shared object, ARM aarch64, dynamically linked
  BuildID: 5bfa092d685f5a5729c70a77bfba79c0038d2d52
  Size: 817064 bytes
  DWARF: present (7 sections)
```

### O2-noinline
```text
results/cpp_local/O2-noinline/snappy/compiled/libsnappy.so.1.2.2
  ELF 64-bit LSB shared object, ARM aarch64, dynamically linked
  BuildID: f1553870bc2174b7ec149c3b225da31e481c6344
  Size: 880568 bytes   (larger than O2 — inlining disabled, more function instances)
  DWARF: present (7 sections)
```

## Source ownership filter

Included project-owned paths/compilands:
```text
snappy.cc, snappy-c.cc, snappy-sinksource.cc, snappy-stubs-internal.cc
(.ii files for each: verified present)
```

Excluded tests/vendor/compiler-probe/generated paths:
```text
snappy_unittest.cc, snappy_test_utils.cc (BUILD_TESTING=OFF)
Benchmarks excluded (BUILD_BENCHMARKS=OFF)
CMakeFiles/[0-9]* compiler-probe directories removed by make_cmd
```

Any uncertain ownership cases:
```text
stdlib/libstdc++ template instantiations appear in DWARF when O0/-fno-inline
causes them to be emitted as non-inlined subprograms in the shared object.
These are filtered by namespace prefix for project-owned collision rate.
```

## Short-name collision details

All collisions are measured from compiled DWARF, not inferred from source.

| Short name | Distinct addresses | Example qualified names | Notes |
|---|---:|---|---|
| `~UncheckedByteArraySink` | 2 | `snappy::UncheckedByteArraySink::~UncheckedByteArraySink()` (×2) | Virtual destructor dual (D1+D2 thunks) |
| `~ByteArraySource` | 2 | `snappy::ByteArraySource::~ByteArraySource()` (×2) | Virtual destructor dual |
| `~Sink` | 2 | `snappy::Sink::~Sink()` (×2) | Virtual destructor dual |
| `~Source` | 2 | `snappy::Source::~Source()` (×2) | Virtual destructor dual |
| `~SnappyIOVecReader` | 2 | `snappy::SnappyIOVecReader::~SnappyIOVecReader()` (×2) | Virtual destructor dual |
| `__normal_iterator` | 4 | `__gnu_cxx::__normal_iterator<SnappySinkAllocator::Datablock*,...>` | stdlib template — not project-owned |
| `pair` | 3 | `std::pair<unsigned long, bool>::pair<...>` | stdlib — not project-owned |
| `_Vector_impl` | 3 | `std::_Vector_base<...>::_Vector_impl::_Vector_impl()` | stdlib — not project-owned |

Key finding: The main source of project-owned collisions in Snappy is GCC's virtual destructor
dual emission. Each virtual destructor generates two distinct addresses (D1 complete-object
destructor, D2 base-object destructor) with identical short names. Under DecBench's current
unqualified identity model, these appear as collisions. This affects all 5+ virtual classes
in Snappy.

## Preprocessed source / oracle notes

For GCC/DWARF targets:

- `.ii` preservation: ✅ 4 `.cc.ii` files per mode (snappy.cc.ii, snappy-c.cc.ii, snappy-sinksource.cc.ii, snappy-stubs-internal.cc.ii)
- DWARF `DW_AT_specification` handling checked: ✅ (used in collision script)
- DWARF `DW_AT_abstract_origin` handling checked: ✅ (used in collision script)

## Final status

Status: **VALIDATED**

Decision rationale:
```text
All three optimization modes built successfully. One linked ELF image per mode.
Four .ii source units per mode. DWARF present (7 sections) in all modes.
Collision analysis completed from measured DWARF.

The collision rate is real and significant (52-65% raw, 19-52% project-owned).
The primary driver is virtual destructor dual emission — a known GCC/ABI behavior.
This does NOT make Snappy unsuitable as a benchmark target; it documents a real
constraint on DecBench's current unqualified C++ identity model.

Snappy is confirmed as the first validated GCC/DWARF target. It correctly
represents a small real C++ library with a specific, measurable identity challenge.
```

Remaining blockers:
```text
None for this target. The DecBench C++ identity model's handling of virtual
destructor duals (D1/D2 thunks) is a separate open issue in DecBench itself.
```
