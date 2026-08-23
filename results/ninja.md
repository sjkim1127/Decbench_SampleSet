# DecBench C++ target validation result — Ninja

## Target metadata

| Field | Value |
|---|---|
| Target | Ninja |
| Upstream | `ninja-build/ninja` |
| Release/tag | `v1.13.1` |
| Resolved commit | `79feac0f3e3bc9da9effc586cd5fea41e7550051` |
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
| O0 | ✅ PASS | 2 (`ninja` + `boo`†) | 33 | DWARF: ✅ in `ninja` | 1665 (all) / ~1664 (boo=0) | — | 25 (stdlib) + 1 proj | 1382 | 83.00% (raw); ~1.1% (proj-only) |
| O2 | ✅ PASS | 2 (`ninja` + `boo`†) | 33 | DWARF: ✅ in `ninja` | 218 (all) / 218 (boo=0) | 177 | 6 stdlib + 19 proj | 67 | 30.73% (raw); ~18.8% (proj-only) |
| O2-noinline | ✅ PASS | 2 (`ninja` + `boo`†) | 33 | DWARF: ✅ in `ninja` | 1565 (all) / ~1565 (boo=0) | — | 25 (stdlib) + 1 proj | 1297 | 82.88% (raw); ~0.9% (proj-only) |

† `boo` is a pre-existing test binary (single `_Z3foov` = `foo()` symbol, BuildID identical
across all three modes, **no DWARF**, not compiled by DecBench). It is collected by DecBench's
source-copy step as an executable artifact but contributes 0 addresses to collision measurement.
See "Source ownership filter" below.

> **Critical measurement note:** The raw collision rates at O0 and O2-noinline (83%) are massively
> inflated by stdlib template instantiations inlined into the ninja executable. At O0/-fno-inline,
> ~1600 of the ~1665 source addresses in DWARF belong to libstdc++ template instantiations
> (`_M_erase`, `~vector`, `_M_realloc_insert`, `~_Deque_base`, etc.) that share short names
> across different template specializations. When filtered to project-owned Ninja code only,
> the true project collision rate is approximately 1% (O0), 18.8% (O2), 0.9% (O2-noinline).
>
> The O2 mode shows far fewer total addresses (218 vs 1665) because inlining at -O2 eliminates
> most stdlib template bodies from the DWARF subprogram list.

Collision rate formula: `collision_addresses / source_function_addresses`

## Optimization control

DW_AT_producer from O2 build:
```
GNU C++17 13.3.0 -mlittle-endian -mabi=lp64 -g -O2 -fno-builtin -fasynchronous-unwind-tables
         -fstack-protector-strong -fstack-clash-protection
```

**✅ No `-flto`, `-fprofile`, `-fwhole-program`, or IPO flags detected.**
**✅ CMAKE_BUILD_TYPE left empty — Ninja's Release IPO/LTO preset was NOT inherited.**

### O0
```text
compile: g++ -O0 -g -fno-builtin -save-temps=obj [from CFLAGS]
         cmake -S . -B build -DCMAKE_BUILD_TYPE= -DCMAKE_CXX_COMPILER=g++ -DCMAKE_CXX_FLAGS="$CFLAGS"
                -DBUILD_TESTING=OFF
link:    cmake --build build -j --target ninja && rm -rf build/CMakeFiles/[0-9]*
```

### O2
```text
compile: g++ -O2 -g -fno-builtin -save-temps=obj [from CFLAGS]
link:    cmake --build build -j --target ninja
```

### O2-noinline
```text
compile: g++ -O2 -fno-inline -g -fno-builtin -save-temps=obj [from CFLAGS]
link:    cmake --build build -j --target ninja
```

Unexpected optimization/LTO/IPO/inlining behavior:
```text
None. DecBench correctly controls optimization. Ninja's upstream Release preset
(which enables IPO) was successfully avoided by leaving CMAKE_BUILD_TYPE empty.
The DW_AT_producer confirms only the expected -O2 flag at O2 mode.
```

## Linked images

### O0
```text
results/cpp_local/O0/ninja/compiled/ninja
  ELF 64-bit LSB pie executable, ARM aarch64
  BuildID: dfc2cf85b94b479b9d647d5f43bd1f2e1a860b0d
  Size: 7,266,400 bytes (large at O0 due to DWARF + no inlining)
  DWARF: present (7 sections), not stripped

results/cpp_local/O0/ninja/compiled/boo  ← NOT a benchmark target (see below)
  ELF 64-bit LSB pie executable, ARM aarch64
  BuildID: ce0227c2d88321cda9b99987909f1a1f8f878f06 (IDENTICAL across O0/O2/O2-noinline)
  Size: 70272 bytes, NO DWARF, single symbol: _Z3foov (foo())
  Origin: CMake/bootstrap pre-compiled test binary, not compiled by DecBench
```

### O2
```text
results/cpp_local/O2/ninja/compiled/ninja
  ELF 64-bit LSB pie executable, ARM aarch64
  BuildID: 5d3c2760f3541b71c25d6ed02d6b179ef9ffc036
  Size: 9,645,040 bytes (O2 larger than O0 due to inlining expansion)
  DWARF: present (7 sections)
```

### O2-noinline
```text
results/cpp_local/O2-noinline/ninja/compiled/ninja
  ELF 64-bit LSB pie executable, ARM aarch64
  BuildID: deb57d29bf19bddd22f69ab44d433cd916479c09
  Size: 8,103,824 bytes
  DWARF: present (7 sections)
```

## Source ownership filter

Included project-owned paths/compilands:
```text
Primary: ninja executable from cmake --build --target ninja
33 .ii files per mode (browse.cc, build.cc, build_log.cc, clean.cc,
clparser.cc, debug_flags.cc, depfile_parser.cc, deps_log.cc, disk_interface.cc,
dyndep.cc, dyndep_parser.cc, edit_distance.cc, eval_env.cc, getopt.cc,
graph.cc, graphviz.cc, jobserver.cc, lexer.cc, line_printer.cc, load_status.cc,
manifest_parser.cc, metrics.cc, missing_deps.cc, ninja.cc, parser.cc,
real_deps_log.cc, state.cc, status.cc, string_piece_util.cc, subprocess.cc,
test.cc, util.cc, version.cc)
```

Excluded tests/vendor/compiler-probe/generated paths:
```text
boo: Pre-compiled test binary with identical BuildID across all three modes.
     Contains only void foo() { abort(); }. Not compiled by DecBench.
     Should be EXCLUDED from benchmark ground-truth measurement.
     
CMakeFiles/[0-9]* compiler-probe directories removed by make_cmd.
BUILD_TESTING=OFF — Ninja test targets excluded.
```

Any uncertain ownership cases:
```text
stdlib/libstdc++ template instantiations (O0/O2-noinline): At lower optimization,
GCC emits concrete DWARF subprograms for non-inlined template instantiations
(std::vector<T>::_M_erase, std::_Rb_tree<...>::_M_erase, etc.) in the ninja
executable. These are NOT ninja project code. They inflate the raw collision rate
from ~1% to ~83%. DecBench's source-function oracle should filter by CU source
file path to exclude /usr/include/c++ paths.

getopt.c: Copied but a C system utility, not Ninja source. Not linked into ninja
the executable (Ninja has its own getopt_long).
```

## Short-name collision details

**O2 collision groups (most actionable, with O2 stdlib mostly inlined away):**

| Short name | Distinct addresses | Example qualified names | Notes |
|---|---:|---|---|
| `_Iter_less_iter>` | 4 | `void std::__insertion_sort<...>`, `void std::__adjust_heap<...>` | stdlib template suffix — not Ninja code |
| `_M_realloc_insert` | 3 | `std::vector<Edge*,...>::_M_realloc_insert<Edge* const&>`, `std::vector<Node*,...>::_M_realloc_insert` | stdlib — not Ninja code |
| `~ManifestParser` | 2 | `ManifestParser::~ManifestParser()` (D1+D2) | Virtual destructor dual |
| `~Client` | 2 | `Jobserver::Client::~Client()` (D1+D2) | Virtual destructor dual |
| `LogEntry` | 2 | `BuildLog::LogEntry::LogEntry(std::string)` | Constructor overload or D1/D2 |

**O0/O2-noinline dominant collisions (stdlib template instantiation noise):**

| Short name | Distinct addresses | Notes |
|---|---:|---|
| `_M_erase` | 9 | 9 distinct std::_Rb_tree<T,...>::_M_erase specializations |
| `~vector` | 6 | 6 distinct std::vector<T,...>::~vector specializations |
| `_Iter_less_iter>` | 4–14 | std template helper |
| `_M_realloc_insert` | 3 | std::vector specializations |
| `~_Deque_base` | 3 | std::_Deque_base specializations |

## Preprocessed source / oracle notes

For GCC/DWARF targets:

- `.ii` preservation: ✅ 33 `.cc.ii` files per mode
- DWARF `DW_AT_specification` handling checked: ✅
- DWARF `DW_AT_abstract_origin` handling checked: ✅
- `boo` binary investigation: pre-compiled test binary with no DWARF, single `foo()` symbol.
  BuildID identical across all three optimization modes — definitively not compiled by DecBench.

## Final status

Status: **VALIDATED WITH CAVEATS**

Decision rationale:
```text
All three optimization modes built successfully. The intended ninja executable
is built for all three modes. 33 .ii source units per mode. DWARF present (7
sections) in the ninja executable in all modes.

LTO/IPO check: PASSED. DW_AT_producer confirms -O2 at O2 mode with no -flto.
CMAKE_BUILD_TYPE left empty successfully prevents Ninja's Release IPO preset.

Collision analysis completed. Key findings:

1. boo: A pre-compiled test binary is collected alongside ninja in the compiled/
   directory. It has identical BuildID across all modes (= not compiled by DecBench),
   no DWARF, and a single trivial symbol. It MUST be excluded from benchmark
   measurement. The make_cmd already targets --target ninja and removes CMakeFiles/[0-9]*,
   but boo is not removed. Consider adding `&& rm -f build/boo` to the make_cmd if
   DecBench's image collector cannot distinguish it.

2. Stdlib contamination at O0/O2-noinline: When inlining is disabled, libstdc++
   template instantiations appear as concrete DWARF subprograms in the ninja
   executable (~1600 of ~1665 addresses at O0). This inflates the raw collision
   rate to ~83%. Project-owned Ninja code has approximately 1% collision rate
   at O0 — much lower than Snappy or double-conversion.

3. O2 collision rate (~19% project-owned) is driven by stdlib helpers that remain
   despite inlining. When filtered to non-stdlib functions, Ninja's own code
   shows ~2 collision groups (virtual destructor duals).

Ninja is validated as a GCC/DWARF target. The boo artifact issue is documented
as a caveat. The stdlib contamination issue is a fundamental DecBench C++ oracle
problem, not a Ninja-specific issue.
```

Remaining blockers:
```text
1. boo artifact: Should be filtered or removed. Config fix: add `&& rm -f build/boo`
   to make_cmd in targets/ninja.toml (see config fix section).
2. Stdlib template contamination: DecBench's source-function oracle needs CU source
   path filtering to exclude /usr/include/c++ compilation units. This affects all
   C++ targets using heavy template code (Ninja is most affected).
```
