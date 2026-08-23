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
| Snappy 1.2.2 | GCC/DWARF | ✅ | ✅ | ✅ | `libsnappy.so.1.2.2` | DWARF ✅ | 45% / 66% (O0) · 53% / 53% (O2) · 45% / 70% (O2-noinline) | **VALIDATED** | Virtual destructor duals drive collisions |
| double-conversion v3.3.1 | GCC/DWARF | ✅ | ✅ | ✅ | `libdouble-conversion.so.3.3.0` | DWARF ✅ | 45% / 45% (O0) · 58% / 58% (O2) · 45% / 45% (O2-noinline) | **VALIDATED** | Clean: all project-owned constructor/overload collisions |
| Ninja v1.13.1 | GCC/DWARF | ✅ | ✅ | ✅ | `ninja` (exe) | DWARF ✅ | 45% / 85% (O0) · 42% / 48% (O2) · 44% / 85% (O2-noinline) | **VALIDATED WITH CAVEATS** | `boo` fixed; stdlib DWARF template presence at O0; LTO check PASSED |
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

### 1. Virtual destructor duals (all targets)

GCC emits two distinct destructor subprograms for virtual classes:
- D1 = complete-object destructor
- D2 = base-object destructor

Both share the same demangled short name (`~ClassName`). Under DecBench's current unqualified C++ identity model, these appear as collisions. **This affects every C++ project with virtual classes.**

### 2. Stdlib template presence (Ninja especially)

At O0 and O2-noinline, GCC emits concrete DWARF subprograms for non-inlined libstdc++ template instantiations (`std::vector<T>`, `std::_Rb_tree`, etc.). In Ninja, these account for over 75% of raw subprograms when inlining is disabled.
Using namespace filtering (`std::`, `__gnu_cxx::`, etc.), project-owned functions are isolated, yielding a consistent ~42–45% project collision rate across all three modes.

### 3. Constructor & method overloads (double-conversion, Ninja)

Legitimate C++ constructor and method overloads produce genuine collision groups under the unqualified name model (e.g. `double_conversion::Double::Double(double)` vs `double_conversion::Double::Double(unsigned long long)`).

### 4. boo artifact (Ninja) — Resolved

The Ninja build originally produced a pre-compiled CMake test binary `boo` (no DWARF, identical BuildID across modes). **Resolved:** `targets/ninja.toml` was updated with `&& rm -f build/boo` in `make_cmd` (commit `b9cf2c3`).

---

## Configuration & toolchain changes

| File | Change | Status |
|---|---|---|
| `targets/ninja.toml` | Added `&& rm -f build/boo` to `make_cmd` | Committed (`b9cf2c3`) |
| `scripts/measure_collisions.py` | Added namespace-based stdlib filtering & reproducible JSON output | Updated |
| `results/evidence/` | Raw JSON outputs, `compile_report.json`, `environment.txt` | Added |

---

## Recommendations for DecBench corpus

### Recommend for inclusion

| Target | Recommendation | Rationale |
|---|---|---|
| **Snappy 1.2.2** | ✅ RECOMMEND | Validated, small, clean build, reproducible collision profile. Good baseline. |
| **double-conversion v3.3.1** | ✅ RECOMMEND | Validated, zero stdlib contamination (all project-owned), numerical workload. |
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
2. **DecBench C++ Oracle namespace filtering**: DecBench's internal ground-truth pipeline should filter out system/stdlib template instantiations to prevent inflated collision numbers at lower optimization levels.
3. **Architecture qualification**: These results are qualified on GCC 13.3.0 `aarch64`. Final corpus creation on `x86_64` should re-verify symbol and collision counts.
