# DecBench C++ Target Validation — Summary

**Validation date:** 2026-08-23  
**DecBench revision:** `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`  
**Host:** macOS 26.5.1 arm64  
**Build environment:** Docker `decbench-compile` image (Ubuntu 24.04, GCC/G++ 13.3.0 aarch64)  
**MSVC/Wine environment:** Not available on this host

---

## Target status table

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Collision rate (raw / proj-only) | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Snappy 1.2.2 | GCC/DWARF | ✅ | ✅ | ✅ | `libsnappy.so.1.2.2` | DWARF ✅ | 61% / 20% (O0) · 53% / 53% (O2) · 65% / 19% (O2-noinline) | **VALIDATED** | Virtual destructor duals drive collisions |
| double-conversion v3.3.1 | GCC/DWARF | ✅ | ✅ | ✅ | `libdouble-conversion.so.3.3.0` | DWARF ✅ | 22% / 22% (O0) · 15% / 15% (O2) · 22% / 22% (O2-noinline) | **VALIDATED** | Clean: only project-owned overload collisions |
| Ninja v1.13.1 | GCC/DWARF | ✅ | ✅ | ✅ | `ninja` (exe) | DWARF ✅ | 83% / 1% (O0) · 31% / 19% (O2) · 83% / 1% (O2-noinline) | **VALIDATED WITH CAVEATS** | `boo` artifact; stdlib DWARF contamination; LTO check PASSED |
| Detours v4.0.1 | MSVC/PDB | — | — | — | — | — | — | **BLOCKED** | No Wine/cl.exe on this host |
| DirectXTex may2026 | MSVC/PDB | — | — | — | — | — | — | **BLOCKED** | No Wine/cl.exe on this host |
| WinSparkle v0.9.4 | MSVC/PDB | — | — | — | — | — | — | **BLOCKED** | No Wine/cl.exe on this host |

---

## Phase 1 — GCC/DWARF results

All three GCC/DWARF targets completed all required gates:

| Gate | Snappy | double-conversion | Ninja |
|---|---|---|---|
| All 3 modes built | ✅ | ✅ | ✅ |
| ≥1 linked ELF per mode | ✅ | ✅ | ✅ |
| ≥1 `.ii` per mode | ✅ (4) | ✅ (8) | ✅ (33) |
| DWARF present | ✅ | ✅ | ✅ |
| Collision analysis completed | ✅ | ✅ | ✅ |
| LTO/IPO absent | ✅ | ✅ | ✅ |

### Compiler flags (verified from DW_AT_producer)

```
O0:          g++ -O0 -g -fno-builtin -save-temps=obj + platform flags
O2:          g++ -O2 -g -fno-builtin -save-temps=obj + platform flags
O2-noinline: g++ -O2 -fno-inline -g -fno-builtin -save-temps=obj + platform flags
```

No `-flto`, `-fprofile`, `-fwhole-program`, or IPO flags in any mode.

---

## Phase 2 — Windows/MSVC: Environment check

| Requirement | Status |
|---|---|
| `wine` | ❌ not found |
| `cl.exe` / MSVC Build Tools | ❌ not found |
| `link.exe` | ❌ not found |
| `msbuild` | ❌ not found |
| Windows SDK | ❌ not installed |

**All three Windows/MSVC targets are BLOCKED.** Static TOML config validation was performed for all three and found no errors. Runtime validation requires a Wine+MSVC environment or a native Windows machine with MSVC Build Tools installed.

---

## Key findings from collision measurement

### 1. Virtual destructor duals (all targets)

GCC emits two distinct destructor addresses for virtual classes:
- D1 = complete-object destructor
- D2 = base-object destructor

Both share the same demangled short name (`~ClassName`). Under DecBench's current unqualified C++ identity model, these appear as collisions. **This affects every C++ project with virtual classes.** Snappy is most visibly affected.

### 2. Stdlib template contamination (Ninja especially)

At O0 and O2-noinline, GCC emits concrete DWARF subprograms for libstdc++ template instantiations (`std::vector<T>::_M_erase`, `std::_Rb_tree<...>::_M_erase`, etc.) that are linked into the executable. These massively inflate the raw collision rate for Ninja from ~1% (project-owned) to ~83% (raw). **DecBench's source-function oracle must filter by CU source path to exclude `/usr/include/c++` compilation units.**

### 3. Constructor overloads (double-conversion, Ninja)

Legitimate C++ constructor and method overloads produce genuine collision groups under the unqualified name model. `double_conversion::Double::Double(double)` vs `double_conversion::Double::Double(unsigned long long)` both shorten to `Double`. This is a real benchmark identity challenge that must be documented in the corpus.

### 4. boo artifact (Ninja)

The Ninja build produces a tiny pre-compiled `boo` test binary (single `foo()` function, no DWARF, identical BuildID across all optimization modes). It is collected alongside `ninja` by DecBench's file-collection step. **It must be excluded from benchmark measurement.** Config fix: add `&& rm -f build/boo` to the `make_cmd` in `targets/ninja.toml`.

---

## Configuration changes made during validation

| File | Change | Reason |
|---|---|---|
| `decbench/projects/cpp/snappy.toml` | Copied from `targets/snappy.toml` | Temporary integration for compile run |
| `decbench/projects/cpp/double-conversion.toml` | Copied from `targets/double-conversion.toml` | Temporary integration |
| `decbench/projects/cpp/ninja.toml` | Copied from `targets/ninja.toml` | Temporary integration |
| `scripts/measure_collisions.py` | NEW: DWARF collision measurement helper | Required for collision analysis |

> **Upstream DecBench not modified.** The TOML copies are temporary; the upstream
> `decbench/` repository is not permanently modified.

### Recommended fix for ninja.toml

The `boo` artifact should be cleaned up:

```toml
# Current:
make_cmd = 'cmake --build build -j --target ninja && rm -rf build/CMakeFiles/[0-9]*'

# Recommended:
make_cmd = 'cmake --build build -j --target ninja && rm -rf build/CMakeFiles/[0-9]* && rm -f build/boo'
```

---

## Recommendations for DecBench corpus

### Recommend for inclusion

| Target | Recommendation | Rationale |
|---|---|---|
| **Snappy 1.2.2** | ✅ RECOMMEND | Validated, small, clean build, predictable collision profile (virtual dtor duals). Good baseline. |
| **double-conversion v3.3.1** | ✅ RECOMMEND | Validated, cleanest collision profile (all project-owned, 15-22%), no stdlib contamination. Numerical workload. |
| **Ninja v1.13.1** | ✅ RECOMMEND WITH CAVEATS | Validated, no LTO contamination, but boo artifact fix needed and stdlib CU filtering required for honest ground truth. Valuable as a real executable target. |

### BLOCKED — Cannot recommend until environment is available

| Target | Recommendation | Key requirement |
|---|---|---|
| **Detours v4.0.1** | ⏸ BLOCKED | cl.exe + link.exe + NMAKE + Windows SDK under Wine or native Windows |
| **DirectXTex may2026** | ⏸ BLOCKED | Same + CMake for Windows; overload collision measurement critical before confirming |
| **WinSparkle v0.9.4** | ⏸ BLOCKED | Same + MSBuild; Thread hierarchy collision measurement required; LTCG override verification |

---

## Remaining blockers

1. **MSVC/Wine environment**: All three Windows targets require a working `cl.exe` environment. This must be set up on a Windows machine or via Wine+msvc-wine before runtime validation can proceed.

2. **boo artifact**: Fix `targets/ninja.toml` `make_cmd` to remove `build/boo` after build.

3. **Stdlib CU filtering**: DecBench's C++ source-function oracle should filter DWARF CUs by source path to exclude `/usr/include/c++` and other system headers. Without this, collision rates at O0/O2-noinline are not representative of project-owned code.

4. **Virtual destructor dual handling**: DecBench's unqualified name model should document or handle D1/D2 destructor duals. Options: (a) deduplicate by treating same-named destructors as identical, (b) use address-range overlap detection, (c) keep as known collision and document.
