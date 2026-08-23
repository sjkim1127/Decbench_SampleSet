# DecBench-specific C++ target handoff

This note maps the candidate work in this repository to the current DecBench implementation rather than presenting it as a generic Windows C++ survey.

Reference DecBench revision inspected: `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`.

## What DecBench supports today

The current C++ path already runs end-to-end, but is intentionally experimental and disabled by default. `projects/cpp/disabled/leveldb.toml` is the reference shape.

The important implementation constraints are:

- project configs are TOML files under `projects/<group>/*.toml`;
- the compile pipeline is GCC-family based (`GCCCompiler`);
- make-based builds receive `CC` and `CFLAGS` from DecBench;
- C++ projects therefore need to wire their C++ compiler/flags explicitly, as LevelDB already does with `-DCMAKE_CXX_COMPILER=g++` and `-DCMAKE_CXX_FLAGS="$CFLAGS"`;
- linked PE files are already accepted by the collector, so MinGW-produced Windows binaries do not require a new binary collector;
- the compile image already contains `gcc-mingw-w64`, but does not currently install `g++-mingw-w64`;
- source-CFG evaluation expects preprocessed C++ `.ii` files;
- current C++ scoring still has the known unqualified-name collision issue and some publish/export paths remain `.i`-only.

That makes a compatibility-first Windows C++ path relatively small: add the MinGW C++ frontend to the compile image, then use release-pinned projects that can emit **PE + DWARF + `.ii`** while preserving DecBench's existing `O0`, `O2`, and `O2-noinline` regimes.

## Recommended DecBench-first target order

| Priority | Target | Stable release | DecBench fit | Why |
| --- | --- | --- | --- | --- |
| 1 | tinyxml2 | `11.0.0` | Direct GCC/DWARF baseline | Very low dependency noise; useful C++ control target before larger applications |
| 2 | Notepad++ | `v8.9.6.1` | Small infra delta: MinGW C++ | Real Windows C++ application; upstream ships a GCC/MinGW makefile; can preserve PE + DWARF + `.ii` |
| 3 | SpaceCadetPinball | `Release_2.1.0` | MinGW + SDL packages | Small Windows/game/OO target with manageable complexity |
| 4 | The Powder Toy | `v100.0.399` | MinGW + larger dependency surface | Algorithm/simulation-heavy complement to GUI/system applications |
| 5 | OpenLoco | `v26.07.1` | GCC-compatible path possible, but dependencies are heavier | Large real-world C++ application |
| 6 | TrafficMonitor | `V1.86` | Native MSVC/MFC path | Strong Windows-native target, but not a drop-in fit for current GCC/DWARF ground truth |
| 7 | x64dbg | `2026.05.27` | Native MSVC/PDB path | Excellent stress target; would require PDB/CodeView ground-truth work |
| 8 | Windows Terminal / OpenConsole | `v1.24.11321.0` | Native MSVC/PDB, component-level | Very large systems target; better after the basic Windows C++ path is stable |

## Minimal compatibility-first delta

The narrowest change to DecBench itself is:

1. install `g++-mingw-w64` in `docker/compile.Dockerfile`;
2. keep the current GCC-family compilation model rather than adding an MSVC backend;
3. for each C++ target, explicitly route C++ flags from DecBench's `$CFLAGS` into the project's C++ build system;
4. require `-save-temps=obj` so `.ii` files survive;
5. keep debug information (`-g`) and do not strip the PE so DWARF remains available;
6. keep `O0`, `O2`, and `O2-noinline` controlled by DecBench, not by a project's Release preset.

No new PE collector is needed: current `GCCCompiler` already recognizes linked PE executables/DLLs.

## Draft project configs

`decbench-drafts/` contains TOML drafts shaped for the existing DecBench project model:

- `tinyxml2.toml` — low-noise C++ baseline using the current GCC/DWARF path.
- `notepadplusplus.toml` — Windows x86-64 PE candidate using MinGW-w64, DWARF, and `.ii` preservation.

These are handoff drafts, not upstream patches. They should only be moved into DecBench after the corresponding release CI result is green and the maintainers decide they want the compatibility-first path.

## DecBench-native qualification lane

The repository now also contains `.github/workflows/decbench-cpp-qualification.yml`. This is deliberately different from the upstream-build validation workflows: it checks whether a target behaves like a usable **DecBench corpus target**.

The first lane runs the real pinned DecBench compile path for tinyxml2 and Notepad++ across `O0`, `O2`, and `O2-noinline`, three independent clean times each. It then records:

- linked ELF/PE images and captured `.ii` files;
- DWARF `DW_TAG_subprogram` and linkage-name evidence;
- short-name collision pressure relevant to the current experimental C++ name keying;
- project-owned functions by matching DWARF `decl_file` against captured translation units using DecBench's own binary/DWARF helpers;
- identity survival from O0 to O2-noinline and O2;
- pyjoern parse and non-empty parse rates over every captured `.ii`;
- SHA-256 reproducibility across the three clean builds;
- a non-blocking actual O2 DecBench/angr decompile/evaluate smoke for the tinyxml2 control target.

The intent is to make the handoff answer a stronger question than “does this project compile?” A candidate can build successfully and still be a poor benchmark target because its source CFG cannot be parsed, its project-owned code is swamped by bundled dependencies, its debug/oracle data is incomplete, or current C++ short-name keying produces excessive collisions.

`qualification/README.md` describes the promotion rule and the generated artifacts.

## What should stay separate for now

Native MSVC validation in this repository is useful feasibility evidence, but it should not be mixed into the first DecBench corpus change. MSVC produces PE + PDB/CodeView, while the current type-ground-truth path is DWARF-based. If native MSVC becomes a research goal later, PDB/CodeView should be treated as a separate ground-truth backend rather than silently substituting it for the current model.

Likewise, the existing C++ qualified-name collision and `.ii` publication gaps should be fixed before C++ numbers are presented as publication-quality results. They do not prevent target discovery/build validation, but they do affect interpretation of scores.

## Suggested decision for maintainers

The first decision is intentionally small:

> Should `multi-lang.decbench.com` start with release-pinned C++ targets that fit the existing GCC/DWARF pipeline, including Windows PE through MinGW, and leave native MSVC/PDB as a later extension?

If yes, tinyxml2 + Notepad++ are the cleanest first pair: one low-noise C++ control and one real Windows C++ application. The qualification lane is intended to produce the evidence needed to decide whether each one should actually be promoted.