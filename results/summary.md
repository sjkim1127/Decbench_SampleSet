# DecBench C++ Target Validation — Summary

**Validation date:** 2026-08-23  
**DecBench revision:** `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`  
**Host:** macOS 26.5.1 arm64  
**Build environment:** Docker `decbench-compile` image (Ubuntu 24.04, GCC/G++ 13.3.0 aarch64)  
**MSVC/Wine environment:** Not available on this host  
**Raw evidence:** Preserved in `results/evidence/` (`compile_report.json`, per-target collision JSONs, `environment.txt`)

---

## Target status table

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Collision rate (proj / raw) | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Snappy 1.2.2 | GCC/DWARF | ✅ | ✅ | ✅ | `libsnappy.so.1.2.2` | DWARF ✅ | 53% / 49% (O0) · 53% / 50% (O2) · 52% / 49% (O2-noinline) | **VALIDATED** | Virtual destructor duals & overloads |
| double-conversion v3.3.1 | GCC/DWARF | ✅ | ✅ | ✅ | `libdouble-conversion.so.3.3.0` | DWARF ✅ | 8% / 31% (O0) · 16% / 21% (O2) · 8% / 42% (O2-noinline) | **VALIDATED** | Cleanest: 8–16% genuine constructor/method overloads |
| Ninja v1.13.1 | GCC/DWARF | ✅ | ✅ | ✅ | `ninja` (exe) | DWARF ✅ | 27% / 66% (O0) · 30% / 41% (O2) · 27% / 71% (O2-noinline) | **VALIDATED WITH CAVEATS** | `boo` fixed; source-stem matched; LTO check PASSED |
| Detours v4.0.1 | MSVC/PDB | — | — | — | — | — | — | **BLOCKED** | No Wine/cl.exe on this host |
| DirectXTex may2026 | MSVC/PDB | — | — | — | — | — | — | **BLOCKED** | No Wine/cl.exe on this host |
| WinSparkle v0.9.4 | MSVC/PDB | — | — | — | — | — | — | **BLOCKED** | No Wine/cl.exe on this host |

---

## Phase 1 — GCC/DWARF results

All three GCC/DWARF targets completed all required gates:

| Gate | Snappy | double-conversion | Ninja |
|---|---|---|---|
| All 3 modes built | ✅ | ✅ | ✅ |
| ≥1 linked ELF per mode | ✅ (1) | ✅ (1) | ✅ (1) |
| ≥1 `.ii` per mode | ✅ (4) | ✅ (8) | ✅ (33) |
| DWARF present | ✅ | ✅ | ✅ |
| Collision analysis completed | ✅ | ✅ | ✅ |
| LTO/IPO absent | ✅ | ✅ | ✅ |

### Compiler flags (verified from DW_AT_producer)

```text
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

### 1. Exact DecBench Source-Stem Alignment

`scripts/measure_collisions.py` directly executes DecBench's ground-truth resolution pipeline (`evalkit/resolve.py` + `utils.binfmt`):
- **Collision Identity Key**: Resolved `DW_AT_name` across `DW_AT_specification` / `DW_AT_abstract_origin` DIE chains.
- **Source-Stem Scope**: Collects translation-unit stems from compiled `.ii` / `.i` files and matches `DW_AT_decl_file` basename stems using `build_stem_index()` and `strip_source_ext()`.
- Excludes header-defined helpers (e.g. `utils.h`) and standard library instantiations from project scope, reflecting exact DecBench ground-truth behavior.

### 2. Target Collision Profiles

- **double-conversion (8%–16% project collision)**: Extremely clean numerical codebase. Zero stdlib contamination. Collisions consist only of genuine constructor/method overloads (e.g. `Double`, `Vector`, `DiyFp`, `operator[]`).
- **Ninja (27%–30% project collision)**: Large real-world CLI tool. When inlining is disabled, stdlib template bodies account for over 85% of raw DWARF functions, but DecBench source-stem filtering cleanly isolates project functions, giving a stable 27–30% project collision rate.
- **Snappy (52%–53% project collision)**: Small compression library where virtual destructor duals (GCC D1+D2 thunks) and overloaded APIs (`Compress`, `GetAppendBuffer`) drive collision rates.

### 3. boo artifact (Ninja) — Resolved

The Ninja CMake bootstrap originally placed `_CMakeLTOTest-CXX/bin/boo` in the build directory. **Resolved:** `targets/ninja.toml` was updated to `cmake --build build -j --target ninja && rm -rf build/CMakeFiles/[0-9]* build/CMakeFiles/_*`. Recompilation confirmed 1 linked binary (`ninja`) and 33 `.ii` preprocessed source units.

---

## Configuration & toolchain changes

| File | Change | Status |
|---|---|---|
| `targets/ninja.toml` | Added `&& rm -rf build/CMakeFiles/[0-9]* build/CMakeFiles/_*` to `make_cmd` | Verified clean 1-binary output & 33 .ii preserved |
| `scripts/measure_collisions.py` | Exact DecBench `evalkit/resolve.py` source-stem matching & `die_attr_owner` resolution | Standalone & reproducible |
| `results/evidence/` | Raw JSON outputs, `compile_report.json`, `environment.txt` | Complete & synchronized |

---

## Recommendations for DecBench corpus

### Recommend for inclusion

| Target | Recommendation | Rationale |
|---|---|---|
| **Snappy 1.2.2** | ✅ RECOMMEND | Validated, small, clean build, predictable collision profile. Good baseline. |
| **double-conversion v3.3.1** | ✅ RECOMMEND | Validated, cleanest collision profile (8–16%), genuine overloads, numerical workload. |
| **Ninja v1.13.1** | ✅ RECOMMEND WITH CAVEATS | Validated, no LTO contamination, valuable executable target. boo artifact fixed. |

### BLOCKED — Cannot recommend until environment is available

| Target | Recommendation | Key requirement |
|---|---|---|
| **Detours v4.0.1** | ⏸ BLOCKED | cl.exe + link.exe + NMAKE + Windows SDK under Wine or native Windows |
| **DirectXTex may2026** | ⏸ BLOCKED | Same + CMake for Windows; overload collision measurement critical before confirming |
| **WinSparkle v0.9.4** | ⏸ BLOCKED | Same + MSBuild; Thread hierarchy collision measurement required; LTCG override verification |

---

## Remaining blockers / future work

1. **MSVC/Wine environment**: All three Windows targets require a working `cl.exe` environment before runtime validation can proceed.
2. **Architecture qualification**: These results are qualified on GCC 13.3.0 `aarch64`. Final corpus creation on `x86_64` should re-verify symbol and collision counts.
