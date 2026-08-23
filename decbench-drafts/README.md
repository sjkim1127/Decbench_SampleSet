# DecBench-shaped target drafts

These files are deliberately shaped around the current DecBench project model instead of being standalone CI recipes.

They are **handoff drafts**, not upstream-ready patches. The goal is to make the remaining integration work concrete and reviewable before anything is proposed to `Noelo-Lab/decbench`.

## Reference implementation assumptions

Reference DecBench revision: `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

Current DecBench behavior relevant to C++:

- `ProjectConfig` consumes project TOMLs with `source_remote`, `version`, `source_dir`, build commands, labels, and `[compilation]` settings.
- `GCCCompiler` controls `O0` / `O2` / `O2-noinline` and exports `CC` + `CFLAGS` to make-based projects.
- linked PE files are already accepted by the collector.
- `.ii` files are recognized as C++ preprocessed input.
- `projects/cpp/disabled/leveldb.toml` explicitly routes `$CFLAGS` into CMake's C++ flags because the generic pipeline does not export CXX/CXXFLAGS.

## Drafts

### `tinyxml2.toml`

Low-noise control target. It should fit the existing GCC/DWARF path with no compiler-infrastructure change. It builds the shared library intentionally because DecBench ignores static archives.

Status: **structurally DecBench-compatible draft; release CI evidence should be attached before upstreaming.**

### `notepadplusplus.toml`

Windows x86-64 PE target through MinGW-w64. The upstream release includes a GCC/MinGW makefile, but three DecBench-specific details matter:

1. the current compile image has `gcc-mingw-w64` but needs `g++-mingw-w64` for C++;
2. upstream Release hard-codes `-O3` and `-s`, which would invalidate DecBench's controlled optimization/debug setup;
3. the upstream Linux cross-build path invokes a Windows `.bat` pre-build generator, so the target patch supplies the pinned generated header and makes that pre-build step a no-op.

`notepadplusplus-decbench.patch` addresses (2) and (3). The compile-image package addition is intentionally left out of this repository because that change belongs in DecBench itself.

The bundled Scintilla/Lexilla code should be checked during final corpus integration for source-attribution/ground-truth coverage; the target should not silently treat third-party linked code as project-owned benchmark ground truth.

Status: **DecBench-shaped Windows C++ draft; requires green MinGW release validation and the one-package compile-image change before upstreaming.**

## Not represented as DecBench TOMLs yet

TrafficMonitor, x64dbg, and Windows Terminal/OpenConsole remain native-MSVC feasibility targets. Turning those into DecBench project files today would be misleading because the current ground-truth stack is GCC/DWARF-oriented while those native builds produce PDB/CodeView.

SpaceCadetPinball and The Powder Toy are plausible MinGW candidates, but they require additional cross-compiled dependencies in the DecBench compile image. They should follow after the smallest GCC/MinGW path is proven.

## Upstream order if maintainers choose compatibility-first

1. prove/fix the generic C++ correctness issues already documented in DecBench (qualified identity and `.ii` publication paths);
2. add tinyxml2 as a low-noise control;
3. add `g++-mingw-w64` to the compile image;
4. validate and add Notepad++ as the first real Windows C++ PE target;
5. only then expand into dependency-heavy Windows C++ targets.
