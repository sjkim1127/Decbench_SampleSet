# DecBench Windows C++ Target Validation — Preview 1

This is a research handoff release for candidate selection, not a DecBench integration release.

## What was validated

Three real-world Windows C++ targets have completed clean CI builds with MSVC x64:

- **TrafficMonitor Lite** — Win32/MFC utility; compact and practical first-tier target.
- **OpenLoco** — larger game/simulation codebase; useful medium/large C++ application target.
- **x64dbg** — Windows debugger/reverse-engineering codebase; useful system-level stress target.

Additional candidates under validation:

- **The Powder Toy** — physics/simulation-heavy C++.
- **Windows Terminal / OpenConsole** — large Windows system component; build cost is substantially higher and may be better used as a subset target.

## Reproducibility evidence

### TrafficMonitor Lite
- MSVC x64 Release: **PASS**
- `/O2 /GL` + LTCG
- Clean CI build: ~105.6 s
- EXE: ~1.94 MB
- PDB: ~19.85 MB
- Raw `PROC32`: 5,297
- Linker: 12,670 functions compiled

### OpenLoco
- MSVC x64 Release: **PASS**
- Clean CI build: ~1,656 s
- EXE: 9,673,216 bytes
- PDB: 26,484,736 bytes
- Raw `PROC32`: 10,777

### x64dbg
- MSVC x64 Release: **PASS**
- Clean CI build: ~645.5 s
- `x64gui.dll`: ~4.44 MB
- `x64dbg.dll`: ~2.23 MB
- `x64bridge.dll`: ~83 KB
- Current Release PDBs are not sufficient as a source-level oracle; `/Zi` + full PDB should be tested separately.

## Fit with current DecBench

Current DecBench C++ evaluation is primarily GCC/DWARF based. Source CFG ground truth is produced from `.ii` files and type ground truth comes from DWARF. Therefore there are two plausible integration paths:

1. **Compatibility-first** — use MinGW/GCC for Windows projects that support it, keeping PE + DWARF + `.ii` close to the existing pipeline.
2. **Native-Windows** — retain MSVC/PE/PDB builds and add PDB/CodeView ground-truth support.

This release intentionally does **not** choose between those directions. Its purpose is to provide validated targets and enough build evidence for that scope decision to be made by the DecBench maintainers.

## Suggested target order

1. TrafficMonitor Lite
2. OpenLoco
3. The Powder Toy
4. x64dbg
5. OpenConsole/component subset

## Notes

- Native MSVC build validation is treated as feasibility evidence, not as a proposal to redesign DecBench.
- Function counts from compiler/linker output, PDB procedure records, and decompiler-discovered functions should remain separate measurements.
- Before corpus integration, each target should be pinned to an exact upstream commit/tag and checked for license, dependency/vendor contamination, and project-owned function attribution.
