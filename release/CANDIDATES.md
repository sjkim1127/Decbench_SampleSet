# Candidate Summary — DecBench Fit

This list is ordered around the **current DecBench implementation**, not just whether a project can build on Windows.

Reference DecBench revision inspected: `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

| Target | Stable release | Role | Current DecBench fit | Recommendation |
| --- | --- | --- | --- | --- |
| tinyxml2 | `11.0.0` | low-noise C++ control | GCC/DWARF path directly | Best first control target |
| Notepad++ | `v8.9.6.1` | real Windows desktop C++ | MinGW PE + DWARF + `.ii`; needs `g++-mingw-w64` in compile image and a small release-build patch | Best first Windows target after MinGW C++ enablement |
| SpaceCadetPinball | `Release_2.1.0` | small game / OO C++ | MinGW-capable but needs SDL cross dependencies | Good second Windows tier |
| The Powder Toy | `v100.0.399` | algorithm / physics-heavy C++ | MinGW-capable with larger dependency surface | Strong complementary target after basic path works |
| OpenLoco | `v26.07.1` | large game / simulation C++ | GCC-compatible family, but dependency/build surface is heavier | Large real-world tier |
| TrafficMonitor | `V1.86` | Win32/MFC desktop utility | Native MSVC/MFC; not a drop-in fit for current DWARF ground truth | Keep as native-Windows follow-up |
| x64dbg | `2026.05.27` | reversing / Windows systems | Native MSVC/PDB | Stress target if PDB/CodeView support is chosen |
| Windows Terminal / OpenConsole | `v1.24.11321.0` | large Windows systems C++ | Native MSVC/PDB; very heavy | Component-level stress target only |

The broader release-pinned pool still contains Microsoft Detours and Explorer++ as reserve/alternative Windows candidates. Rainmeter remains a reserve. Nilesoft Shell and nCine stay out of the active pool because the stable-source-release policy does not fall back to branch heads or arbitrary commits.

## Why this ordering

DecBench already has experimental C++ support via its disabled LevelDB target, including `.ii` collection and Joern C++ parsing. Its make-based compiler path remains GCC-family based, and linked PE files from MinGW are already recognized. The smallest extension therefore is to prove the existing C++ path with release-pinned targets before designing a new native-MSVC ground-truth backend.

For that reason, this handoff separates candidates into three practical groups:

- **Direct/current path:** tinyxml2 and other GCC/DWARF C++ controls.
- **Compatibility-first Windows path:** MinGW-built PE + DWARF + `.ii` targets such as Notepad++.
- **Native-Windows follow-up:** MSVC/PDB targets such as TrafficMonitor, x64dbg, and OpenConsole.

## Existing DecBench C++ caveats

Target selection should not hide the current experimental limitations:

- C++ functions are still vulnerable to unqualified same-name method collapse in scoring.
- some publish/dataset paths remain `.i`-only and can skip `.ii`.
- Joern's C++ frontend is less exercised than the C path.

Those issues should be treated as scoring/publication correctness work, separate from whether a candidate source tree builds reproducibly.

## Selection criteria

A useful candidate should have source available, a stable release pin, reproducible builds, a clear license, meaningful project-owned C++ code, manageable dependency contamination, preserved ground truth, and controlled optimization levels that are not silently replaced by an upstream `Release` preset.

See `DECBENCH_HANDOFF.md` and `../decbench-drafts/` for the concrete mapping to DecBench's current project/TOML model.