# DecBench C++ Target Validation

Focused validation workspace for a future DecBench multi-language C++ corpus.

The shortlist is split into two tracks:

- **GCC / DWARF / `.ii`** targets that fit DecBench's existing experimental C++ path;
- **MSVC / PE / PDB** targets intended for the experimental Windows path described by DecBench PR #36.

The goal is not to maximize project count, but to keep a small set of source-available C++ projects with meaningfully different workloads and controllable build configurations.

## Confirmed target

### Google Snappy 1.2.2

**Status: confirmed for the C++ target shortlist.**

- upstream: `google/snappy`
- stable release: `1.2.2`
- resolved commit: `6af9287fbdb913f0794d0148c6aa43b58e63c8e3`
- language: C++11
- build: CMake + GCC
- DecBench modes: `O0`, `O2`, `O2-noinline`
- ground-truth path: DWARF + preprocessed `.ii`
- output: shared `libsnappy` linked image
- intended role: small compression/library baseline

Snappy is retained as the first confirmed target because it is a small real C++ library with a straightforward build, no mandatory third-party runtime dependency for the core library, and a relatively limited object-oriented hierarchy compared with larger C++ applications.

## Selected GCC / DWARF candidates

### Google double-conversion v3.3.1

**Status: selected candidate; source/build shape reviewed.**

- upstream: `google/double-conversion`
- stable release: `v3.3.1`
- resolved commit: `ae0dbfeb9744efd216c95b30555049d75d47116a`
- language: C++
- build: CMake + GCC
- expected modes: `O0`, `O2`, `O2-noinline`
- ground-truth path: DWARF + preprocessed `.ii`
- intended role: numeric / algorithm-heavy baseline

Reason for selection:

- compact but real C++ implementation;
- floating-point conversion, arithmetic, parsing, and bit-level code;
- limited inheritance/virtual hierarchy compared with larger C++ applications;
- low dependency burden;
- complements Snappy with a more numerical workload.

Runtime CI validation is still pending; the previous Actions run did not complete because the private-repository Actions allowance was exhausted.

### Ninja v1.13.1

**Status: selected candidate.**

- upstream: `ninja-build/ninja`
- stable release: `v1.13.1`
- resolved commit: `79feac0f3e3bc9da9effc586cd5fea41e7550051`
- language: C++11
- build: CMake / bootstrap build
- expected modes: `O0`, `O2`, `O2-noinline`
- ground-truth path: DWARF + preprocessed `.ii`
- intended role: system / tooling executable

Reason for selection:

- real-world executable rather than only a library;
- parser, dependency graph, filesystem, process, and build-scheduling code;
- low external dependency burden;
- substantially different workload from Snappy and double-conversion;
- suitable intermediate-size target before larger application-style corpora.

For DecBench configuration, tests should be disabled and the build type should remain unset so DecBench retains control over optimization rather than inheriting Ninja's Release IPO/LTO behavior.

## Selected Windows / MSVC candidates

These candidates are intended for DecBench's experimental native Windows path using real `cl.exe` under Wine, PE binaries, and PDB/CodeView ground truth. They should not be presented as already supported by the current DWARF pipeline.

### Microsoft Detours v4.0.1

**Status: selected Windows/MSVC system target.**

- upstream: `microsoft/Detours`
- stable release: `v4.0.1`
- resolved commit: `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833`
- language: C++ / Win32
- build: MSVC + NMAKE
- ground-truth path: PDB / CodeView
- primary output: static `detours.lib`, with upstream linked PE samples/tools available
- intended role: Windows instrumentation / PE manipulation / systems code

Reason for selection:

- native Windows code with direct Win32 and PE-manipulation behavior;
- API names are relatively distinctive (`DetourAttach`, `DetourFindFunction`, `DetourEnumerateExports`, etc.), making it a cleaner first Windows C++ candidate than broad GUI class hierarchies;
- naturally uses MSVC debug information and fits the direction already explored by DecBench's MSVC prototype;
- upstream sample executables such as `withdll`, `dumpe`, `disas`, and `findfunc` provide linked PE images that include/use Detours functionality.

Caveat: the upstream build defaults sample compilation to `/Od`; DecBench integration must explicitly control `/Od` versus `/O2` rather than treating the upstream defaults as benchmark modes.

### Microsoft DirectXTex may2026

**Status: selected Windows/MSVC rich C++ stress target.**

- upstream: `microsoft/DirectXTex`
- stable release: `may2026`
- resolved commit: `4feb3e11a020f35b796fc769a74216a555d4f5ef`
- language: C++17
- build: CMake + MSVC
- ground-truth path: PDB / CodeView
- outputs: DirectXTex library plus Windows tools such as `texconv`, `texassemble`, and `texdiag`
- intended role: graphics / image processing / richer C++ stress target

Reason for selection:

- Windows-oriented image and texture processing workload;
- BC compression, DDS/WIC handling, mipmap generation, resize/convert operations, and vector-heavy code provide a distinct decompilation workload;
- build can produce linked PE executables as well as the library;
- complements Detours with computation-heavy C++ rather than another systems/instrumentation target.

Caveat: DirectXTex contains many overloads (`Compress`, `CompressEx`, `SaveToDDS*`, `EvaluateImage`, `TransformImage`, etc.). Under DecBench's current unqualified C++ function-identity model, it should be treated as a richer/stress target until qualified-name handling is fixed or collision rates are explicitly measured.

### WinSparkle v0.9.4

**Status: selected Windows/MSVC application-library target.**

- upstream: `vslavik/winsparkle`
- stable release: `v0.9.4`
- resolved commit: `a8986caf620262f7d4581b241436ceaa0cc9370f`
- language: C++ / Win32
- build: Visual Studio / MSBuild
- ground-truth path: PDB / CodeView
- output: `WinSparkle.dll` + import library + PDB for Win32/x64/ARM64 configurations
- intended role: Windows updater / networking / threading / UI-oriented C++

Reason for selection:

- native Windows DLL rather than another cross-platform library;
- project-owned C++ covers appcast parsing, WinInet-based download/update behavior, signature verification, registry/settings handling, Win32 UI, and worker-thread coordination;
- provides object-oriented and asynchronous/threaded C++ behavior that is distinct from Detours and DirectXTex;
- stable release produces linked PE DLL and PDB artifacts directly.

Caveats:

- the `Thread` hierarchy intentionally repeats virtual names such as `Run` and `IsJoinable`, and `UpdateChecker` subclasses also repeat virtual methods. This gives WinSparkle a moderate short-name collision risk under DecBench's current C++ identity model;
- the Visual Studio Release configuration enables size optimization and whole-program/LTCG behavior, so benchmark integration must explicitly override optimization and LTO settings for controlled `/Od` and `/O2` variants;
- the project includes/vends third-party components such as Expat, OpenSSL-related material, wxWidgets headers, and Ed25519 code, so source/compiland filtering should restrict benchmark ground truth to WinSparkle-owned sources.

## Initial C++ target shortlist

1. **Snappy 1.2.2** — small compression/library baseline — GCC/DWARF
2. **double-conversion v3.3.1** — numeric / algorithm-heavy baseline — GCC/DWARF
3. **Ninja v1.13.1** — system / tooling executable — GCC/DWARF
4. **Microsoft Detours v4.0.1** — Windows instrumentation / PE systems target — MSVC/PDB
5. **Microsoft DirectXTex may2026** — Windows graphics / image-processing stress target — MSVC/PDB
6. **WinSparkle v0.9.4** — Windows updater / networking / threading / UI-oriented target — MSVC/PDB

The Powder Toy was removed from the initial shortlist. Its application diversity is useful, but its dependency footprint, GUI-style inheritance, repeated method names, and optimization/build behavior make it less suitable than the selected Windows targets for this first corpus.

## DecBench integration shape

`targets/snappy.toml` is shaped for the current DecBench project model. It keeps DecBench in control of optimization flags, enables a shared library so the linked-image collector has a benchmark target, disables Snappy tests and benchmarks, and preserves `-g -save-temps=obj` for DWARF and `.ii` collection.

`targets/double-conversion.toml` is also present as the next GCC/DWARF candidate configuration.

The validation workflow pins DecBench to:

`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`

For the GCC/DWARF track, the first integration gate remains:

- all three optimization modes are attempted;
- at least one linked image is collected for each mode;
- at least one preprocessed `.ii` unit is collected for each mode;
- C++ short-name collision rates should be measured before treating a target as fully benchmark-ready.

For the Windows/MSVC track, DecBench PR #36 already demonstrates a working `cl.exe` + Wine compile environment and PDB extraction path, but full benchmark integration remains experimental. The Windows candidates therefore remain **selected MSVC/PDB targets**, not current-pipeline validated targets.
