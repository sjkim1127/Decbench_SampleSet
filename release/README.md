# DecBench Windows C++ Target Validation — Preview 1

This release is a compact handoff package for evaluating candidate C++ targets for the next multi-language phase of DecBench.

## Goal

Identify real-world C++ projects with source code, with an emphasis on Windows targets, and validate that they can be built reproducibly before proposing them for corpus integration.

## Current validated targets

| Target | Domain | Native Windows build | Status | Notes |
| --- | --- | --- | --- | --- |
| TrafficMonitor Lite | Win32/MFC desktop utility | MSVC x64 Release | ✅ Validated | Small/medium Windows-native target; clean CI build; PDB preserved |
| OpenLoco | Game/simulation | MSVC x64 Release | ✅ Validated | Larger real-world C++ target; clean CI build; PDB preserved |
| x64dbg | Debugger / reverse engineering | MSVC x64 Release | ✅ Validated | System-heavy C++; core DLLs build successfully; PDB oracle needs a `/Zi` follow-up |
| Windows Terminal / OpenConsole | Windows system / console | MSVC x64 Release | ⏳ Heavy validation target | Build is substantially heavier; better considered as a component/subset target |
| The Powder Toy | Physics / simulation | MSVC x64 | 🧪 Added for validation | Useful algorithm/physics-heavy C++ target; intended for O0/O2/LTO comparison |

## Measured CI results

### TrafficMonitor Lite

- Toolchain: Visual Studio 2022 / MSVC x64
- Optimization: `/O2 /GL` with LTCG
- Clean CI build: successful
- Build time: ~105.6 s
- `TrafficMonitor.exe`: ~1.94 MB
- PDB: ~19.85 MB
- Raw PDB `PROC32` records: 5,297
- Linker reported: 12,670 functions compiled

The difference between linker-emitted function counts and PDB procedure records is intentional evidence that a Windows ground-truth pipeline should not treat a single function count as authoritative.

### OpenLoco

- Toolchain: Visual Studio 2022 / MSVC x64
- Clean CI build: successful
- Build time: ~1,656 s (~27m 36s)
- `OpenLoco.exe`: 9,673,216 bytes
- `OpenLoco.pdb`: 26,484,736 bytes
- Raw PDB `PROC32` records: 10,777

### x64dbg

- Toolchain: MSVC x64 Release
- Clean CI build: successful
- Build time: ~645.5 s
- Main benchmarkable outputs:
  - `x64gui.dll`: ~4.44 MB
  - `x64dbg.dll`: ~2.23 MB
  - `x64bridge.dll`: ~83 KB
- Current Release PDB procedure counts are too sparse to use as a source-level oracle; a follow-up build should preserve optimization while forcing `/Zi` and a full linker PDB.

## DecBench compatibility note

The current DecBench C++ path is primarily GCC/DWARF based:

- C++ source CFG input is generated from GCC `-save-temps=obj` `.ii` files and parsed with Joern.
- Type ground truth comes from DWARF via pyelftools.
- Existing C++ support is experimental; LevelDB is currently disabled by default.

For Windows projects that also build under MinGW/GCC, a PE + DWARF + `.ii` route may allow substantial reuse of the current pipeline.

Native MSVC builds instead produce PE + PDB/CodeView. Supporting those directly would require additional ground-truth work, so this preview treats MSVC/PDB as a feasibility result rather than assuming that DecBench should adopt that path.

## Suggested first corpus tier

1. TrafficMonitor Lite — compact Windows-native target
2. OpenLoco — larger real-world C++ application
3. The Powder Toy — algorithm/physics-heavy C++
4. x64dbg — system/reversing stress target
5. OpenConsole — large/complex component target

## Decision point

The practical next step depends on the intended scope of `multi-lang.decbench.com`:

- **Compatibility-first:** prefer targets that can be built through the existing GCC/DWARF C++ pipeline (including MinGW where appropriate).
- **Native-Windows:** retain MSVC builds and add PDB/CodeView ground-truth support.

This package deliberately does not choose between those directions. The target/build validation is meant to make that decision easier.

## Repository purpose

This repository is a validation workspace, not a proposed DecBench patch. It records pinned upstream builds, CI recipes, and measurements so candidate selection can be reviewed before any integration work is started.
