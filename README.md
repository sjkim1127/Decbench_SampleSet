# DecBench C++ Sample-Set Validation

Private CI workspace for validating candidate C++ / Windows C++ targets for a future DecBench multi-language corpus.

The repository does **not** vendor third-party source trees. GitHub Actions clones exact upstream commits at runtime, builds them on a Windows runner, and records build/toolchain/function-count evidence.

## Initial targets

| Target | Pinned commit | First-pass configuration |
|---|---|---|
| TrafficMonitor Lite | `5efd2159af8117301a2b6a755897aaa995887678` | MSVC, x64, `Release (lite)` |
| The Powder Toy | `b31f4462bc7d217159b83859a35405db9b640455` | Meson/MSVC, x64 `debugoptimized` (O2 + debug info), prebuilt static deps, LTO |
| OpenLoco | `96de081155f326a7af83f925185c1a934ba536b4` | CMake, Windows x64 Release |
| x64dbg | `17233957ea0a7e70d188187380bd74f80c2a4b93` | CMake/MSVC, x64 Release |
| Windows Terminal | `20588130d8ef2ba40eb56bdae88e04cce7fc5b5d` | OpenConsole component build attempt |

## Measured results

### TrafficMonitor Lite x64 Release — validated

GitHub Actions `windows-2022` with Visual Studio 2022 successfully produced the optimized Windows target after explicitly installing the MFC component required by the upstream project.

| Metric | Value |
|---|---:|
| MSBuild | `17.14.51.32402` |
| MSVC toolset | `14.44.35207` |
| Build | `/O2 /Oi /GL /EHsc /MD /Gy /std:c++20`, x64 |
| Link | `/OPT:REF /OPT:ICF /LTCG:incremental /DEBUG:FULL /MACHINE:X64` |
| Clean build time | `105.554 s` |
| Checkout size | `7,742,420 B` |
| Submodules | `0` |
| `TrafficMonitor.exe` | `1,942,016 B` |
| `TrafficMonitor.pdb` | `19,845,120 B` |
| raw PDB PROC32 symbols | `5,297` |
| PE SHA-256 | `9800EFF50B021AD3EB64CF58D0958C3C0ECBEA0EF88E903074DADCD861523C76` |

The linker also reported `12670 functions were compiled` during LTCG. This is deliberately **not** equated with the PDB procedure count: the two numbers describe different compiler/linker layers and are useful evidence that DecBench should keep source-attributable functions, compiler/linker-emitted procedures, and recovered function boundaries as separate concepts.

**Current verdict:** strong Windows/MSVC corpus candidate. It is reproducible, dependency-light enough for CI, emits a full PDB oracle, and exercises optimized PE/COFF C++ with MFC/Win32 code.

### x64dbg x64 Release — build validated, oracle pass still needed

The complete x64dbg CMake build succeeds on the current `windows-latest` VS 2026 runner.

| Metric | Value |
|---|---:|
| MSVC | `19.51.36256.0` |
| Build time | `645.505 s` |
| Checkout size | `65,402,540 B` |
| Submodules | `4` |
| `x64gui.dll` | `4,444,672 B` |
| `x64dbg.dll` | `2,230,272 B` |
| `x64bridge.dll` | `83,456 B` |

Matching linker PDBs were produced, but the current raw procedure-symbol counts (`90`, `129`, `61`) are much too small to represent source-level function ground truth for DLLs of this size. The next oracle pass must preserve Release optimization while forcing private compile debug information (for example `/Zi` plus a full linker PDB), then extract procedure records and boundaries from that PDB.

The broad `x64*.dll` measurement pattern also catches copied dependency shims (`x64_bridge.dll`, `x64_dbg.dll`). Final corpus selection should explicitly target only `x64gui.dll`, `x64dbg.dll`, and `x64bridge.dll`.

## Pending validation

- **The Powder Toy:** added as a dedicated MSVC/Meson CI target pinned to `b31f4462bc7d217159b83859a35405db9b640455`. The first pass intentionally uses Meson `debugoptimized` so optimization and useful debug information coexist, with `-Dstatic=prebuilt` for reproducibility and `-Dlto=true` to exercise the project's explicit MSVC `/GL` + `/LTCG` path. The initial binary target is `powder.exe`; source-attributable PDB filtering will be needed to exclude statically linked third-party code from later ground truth.
- **OpenLoco:** clean Windows/VS2022 build is currently running. Upstream itself tests both VS2022 and VS2026 presets and publishes Release PDB artifacts; first uncached vcpkg population is the main CI cost.
- **Windows Terminal / OpenConsole:** full `OpenConsole.slnx` Release build is currently running and is substantially heavier than the other candidates. If full-solution cost remains excessive, the next pass will target the `Host.EXE` / conhost project and only its required dependencies.

## Why The Powder Toy is useful

The Powder Toy fills a different part of the corpus than the existing Windows-heavy targets: it is a modern C++20 physics/simulation application with large update loops, numeric code, arrays and pointer-heavy state, many branch-rich particle interactions, and real application architecture rather than a synthetic microbenchmark. Upstream explicitly supports MSVC/clang-cl, disables C++ RTTI by default, and has an explicit LTO implementation for MSVC. That combination makes it particularly interesting for structure recovery and type-recovery evaluation.

The first build uses prebuilt static dependencies because it is the most reproducible CI path. This does mean third-party library code can enter the PE. The benchmark oracle therefore must distinguish project-source functions from vendor/library functions using PDB/source attribution before this target is admitted to the final sample set.

## What CI records

- exact upstream commit
- runner / Visual Studio / MSVC / CMake/Meson versions
- clone size and submodule count
- clean build duration
- output PE size and SHA-256
- matching PDB, when emitted
- approximate PDB procedure-symbol count using `llvm-pdbutil`
- build blockers and logs through the GitHub Actions job output

The PDB count is **not** treated as a final source-function ground truth. The intended oracle pipeline will separate:

1. source-attributable functions,
2. compiler/linker-emitted procedures and aliases/thunks,
3. function boundaries recovered by each decompiler.

## Workflow

`.github/workflows/windows-cpp-validation.yml` performs the main build-validation pass. `.github/workflows/powder-toy-validation.yml` performs the dedicated The Powder Toy MSVC/Meson pass. Reports are uploaded as GitHub Actions artifacts for each target.
