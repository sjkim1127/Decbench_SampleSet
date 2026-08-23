# DecBench C++ Sample-Set Validation

Private CI workspace for validating candidate C++ / Windows C++ targets for a future DecBench multi-language corpus.

The repository does **not** vendor third-party source trees. GitHub Actions clones exact upstream commits at runtime, builds them on a Windows runner, and records build/toolchain/function-count evidence.

## Initial targets

| Target | Pinned commit | First-pass configuration |
|---|---|---|
| TrafficMonitor Lite | `5efd2159af8117301a2b6a755897aaa995887678` | MSVC, x64, `Release (lite)` |
| The Powder Toy | `b31f4462bc7d217159b83859a35405db9b640455` | Meson/MSVC, x64 `debugoptimized`, prebuilt static deps, LTO |
| OpenLoco | `96de081155f326a7af83f925185c1a934ba536b4` | CMake, Windows x64 Release |
| x64dbg | `17233957ea0a7e70d188187380bd74f80c2a4b93` | CMake/MSVC, x64 Release |
| Windows Terminal | `20588130d8ef2ba40eb56bdae88e04cce7fc5b5d` | environment + component build attempt |

The Powder Toy is included as an algorithm/physics-heavy real-world C++20 target. Its upstream Meson configuration disables RTTI by default, supports MSVC/clang-cl, and has an explicit MSVC LTO path (`/GL` + `/LTCG`). The first CI pass uses `debugoptimized` so optimized code and useful PDB information can coexist. Because the first build uses prebuilt static dependencies, later oracle generation must use PDB/source attribution to exclude vendor/library functions from the project-source ground truth.

## What CI records

- exact upstream commit
- runner / Visual Studio / MSVC / CMake/Meson versions
- clone size and submodule count
- clean build duration
- output PE size and SHA-256
- matching PDB, when emitted
- approximate PDB procedure-symbol count using `llvm-pdbutil` (`S_GPROC32` / `S_LPROC32`)
- build blockers and logs through the GitHub Actions job output

The PDB count is **not** treated as a final source-function ground truth. It is a first measurement that will later be split into source-attributable functions, compiler/linker-emitted functions, and decompiler-discovered functions.

## Workflow

`.github/workflows/windows-cpp-validation.yml` runs the main candidate matrix. `.github/workflows/powder-toy-validation.yml` runs the dedicated The Powder Toy MSVC/Meson validation pass. Both can be dispatched manually from the Actions tab.
