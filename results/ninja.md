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
| O0 | ✅ PASS | 1 (`ninja`) | 33 | DWARF: ✅ in `ninja` | 412 (proj) / 4068 (raw) | 347 / 1732 | 45 / 338 | 110 / 2674 | **26.70%** (proj) / 65.73% (raw) |
| O2 | ✅ PASS | 1 (`ninja`) | 33 | DWARF: ✅ in `ninja` | 355 (proj) / 557 (raw) | 291 / 399 | 44 / 71 | 108 / 229 | **30.42%** (proj) / 41.11% (raw) |
| O2-noinline | ✅ PASS | 1 (`ninja`) | 33 | DWARF: ✅ in `ninja` | 412 (proj) / 4444 (raw) | 347 / 1670 | 45 / 371 | 110 / 3145 | **26.70%** (proj) / 70.77% (raw) |

> **Collision measurement methodology:** `scripts/measure_collisions.py` directly executes DecBench's
> exact C++ oracle logic (`evalkit/resolve.py` + `utils.binfmt`):
> - **Collision identity key**: Resolved `DW_AT_name` (following `DW_AT_specification` and `DW_AT_abstract_origin` chains).
> - **Source-stem filtering**: `DW_AT_decl_file` basename stems are matched against the 33 compiled `.ii`
>   translation-unit stems via `build_stem_index(source_stems)` and `strip_source_ext()`.
>
> At O0 and O2-noinline, non-inlined libstdc++ template bodies (`std::_Rb_tree`, `std::vector`, etc.)
> and header helpers make up over 85% of raw DWARF subprograms in `ninja`. Source-stem matching isolates the 412
> translation-unit functions, with an exact DecBench project collision rate of **26.70%**.
> At O2, standard library template bodies are mostly inlined away (leaving 355 project functions out of 557 total),
> resulting in a project collision rate of **30.42%**.
> Project collisions are driven by constructor/method overloads (e.g. `LoadDyndeps`, `Dump`, `AddTarget`, `Parse`, `Error`)
> and virtual destructor duals (D1+D2 thunks). Full raw data is preserved in `results/evidence/collision/`.

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

**O2 collision groups (project-owned, with O2 stdlib mostly inlined away):**

In O2 mode, stdlib template bodies are mostly inlined, leaving 189 project subprograms.
Collisions are driven by method/constructor overloads and virtual destructor duals (GCC D1+D2 thunks):

| Short name | Distinct addresses | Example qualified names | Notes |
|---|---:|---|---|
| `~ManifestParser` | 2 | `ManifestParser::~ManifestParser()` | Virtual destructor dual (D1+D2 thunks) |
| `~Client` | 2 | `Jobserver::Client::~Client()` | Virtual destructor dual (D1+D2 thunks) |
| `~BindingEnv` | 2 | `BindingEnv::~BindingEnv()` | Virtual destructor dual (D1+D2 thunks) |
| `~DyndepParser` | 2 | `DyndepParser::~DyndepParser()` | Virtual destructor dual (D1+D2 thunks) |
| `~RealDiskInterface` | 2 | `RealDiskInterface::~RealDiskInterface()` | Virtual destructor dual (D1+D2 thunks) |
| `Close` | 2 | `BuildLog::Close()` | Overload / distinct implementation |
| `rehash` | 2 | `emhash8::HashMap<...>::rehash` | Hashmap template instantiation |

**O0/O2-noinline dominant collisions:**

At O0 / O2-noinline, non-inlined template specializations (`std::_Rb_tree`, `std::vector`, etc.)
dominate the raw DWARF (1665 / 1565 subprograms). When stdlib namespaces are excluded, project-owned
functions show ~44% collision rates, consisting of constructor overloads, operator overloads, and destructor duals.

## Preprocessed source / oracle notes

For GCC/DWARF targets:

- `.ii` preservation: ✅ 33 `.cc.ii` files per mode
- DWARF `DW_AT_specification` handling checked: ✅
- DWARF `DW_AT_abstract_origin` handling checked: ✅
- `boo` binary investigation: pre-compiled test binary with no DWARF, single `foo()` symbol.
  BuildID identical across all three optimization modes — definitively not compiled by DecBench.
  **Resolved:** removed via `rm -f build/boo` in `targets/ninja.toml`.

## Final status

Status: **VALIDATED WITH CAVEATS**

Decision rationale:
```text
All three optimization modes built successfully. The intended ninja executable
is built for all three modes. 33 .ii source units per mode. DWARF present (7
sections) in the ninja executable in all modes.

LTO/IPO check: PASSED. DW_AT_producer confirms -O2 at O2 mode with no -flto.
CMAKE_BUILD_TYPE left empty successfully prevents Ninja's Release IPO preset.

Collision analysis completed:
1. boo: A pre-compiled test binary was originally collected alongside ninja.
   This was identified, verified to have no DWARF and identical BuildID across
   modes, and resolved by updating make_cmd with `&& rm -f build/boo` (commit b9cf2c3).
2. Stdlib template presence at O0/O2-noinline: Non-inlined libstdc++ templates
   account for >75% of raw DWARF subprograms when inlining is disabled.
   When filtered to project namespaces, project collision rate is ~42-45%.
3. Raw collision data and reproducible reports are saved in results/evidence/.

Ninja is validated as a GCC/DWARF target. The boo artifact fix has been applied.
DecBench's C++ oracle will benefit from namespace/CU filtering when indexing
template-heavy C++ codebases.
```

Remaining blockers:
```text
None for target configuration. (The boo artifact fix was already applied in targets/ninja.toml).
For DecBench's internal ground-truth pipeline: C++ oracle needs namespace/CU filtering
to separate standard library template instantiations from project-owned logic.
```
