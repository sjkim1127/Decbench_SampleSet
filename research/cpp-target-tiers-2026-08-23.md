# DecBench multi-lang C++ target tiers — 2026-08-23

This note refreshes the Windows/C++ target search around **small / medium / large** tiers.

The tier is **not** based only on GitHub repository size. It is a provisional benchmark-cost classification based on expected build cost, dependency graph, linked binary size/function population, and source/third-party contamination. CI measurements should override these provisional labels.

## Pinning policy

For benchmark candidates, prefer a **published stable release** over a moving branch head or an arbitrary latest commit.

For reproducibility, record both:

1. the release/tag name used as the human-facing corpus version, and
2. the exact commit SHA to which that tag resolved when the corpus was validated.

Avoid prereleases unless the benchmark explicitly needs them. If a project has no usable stable release, pin an exact commit and document why. Existing commit-only pins below are historical validation pins; before final upstream integration they should be migrated to stable release pins where practical.

## Recommended initial balance

| Tier | Primary | Secondary | Additional gap-filler | Why |
| --- | --- | --- | --- | --- |
| Small | TrafficMonitor Lite | SpaceCadetPinball | tinyxml2 + Microsoft Detours | GUI/game plus clean-control and Windows-systems coverage |
| Medium | The Powder Toy | Explorer++ | — | algorithm/physics-heavy + native Win32 application |
| Large | OpenLoco | Notepad++ | — | large real-world C++ + a Windows target with both MSVC and MinGW build paths |
| Stress / expansion | x64dbg | OpenConsole component subset | — | system/reversing and very heavy Windows-system code; not first-line corpus targets |

The target-discovery phase can be considered effectively saturated after adding the two small-tier gap-fillers. The next useful work is build/oracle validation rather than collecting more names.

## Small tier

### 0. tinyxml2 — release-pinned clean control
- Repo: https://github.com/leethomason/tinyxml2
- Stable release: `v11.0.0`
- Release-resolved commit: `9148bdf719e997d1f474be6bcc7943881046dba1`
- Profile: compact C++ XML parser; the core library is essentially `tinyxml2.cpp` + `tinyxml2.h`, with `xmltest.cpp` available as a test executable.
- Build system: CMake; no large dependency graph is required for the baseline.
- Strength: extremely low build/vendor noise, useful as a clean compiler/optimization control target.
- Role: **small clean-control C++ baseline**.

### 1. Microsoft Detours — release-pinned Windows systems baseline
- Repo: https://github.com/microsoft/Detours
- Stable release: `v4.0.1`
- Release-resolved commit: `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833`
- Profile: Microsoft Research Windows API instrumentation / binary-rewriting library.
- License: MIT.
- Build: Visual Studio developer environment + `nmake`; the upstream tree contains focused C++ library sources and small sample executables/DLLs.
- Important caveat: `v4.0.1` is old relative to current `main`, but it is still the latest published stable release. For benchmark reproducibility we intentionally prefer the release first; current-main experiments can remain a separate comparison if needed.
- Strength: fills the missing Windows systems/instrumentation niche without x64dbg/OpenConsole-scale build cost.
- Role: **small Windows-systems C++ baseline**.

### 2. TrafficMonitor Lite — validated historical probe
- Repo: https://github.com/zhongyang219/TrafficMonitor
- Historical probe pin: `5efd2159af8117301a2b6a755897aaa995887678`
- Profile: Windows desktop utility / MFC / Win32 C++.
- Existing clean CI result: MSVC x64 Release PASS.
- Existing measured output: 1,942,016 B EXE, 19,845,120 B PDB, raw `PROC32` 5,297.
- Role: **small native-Windows GUI baseline**.
- Before final corpus integration: choose and validate a stable release tag if available.

### 3. SpaceCadetPinball — high-priority dual-toolchain candidate
- Repo: https://github.com/k4zmu2a/SpaceCadetPinball
- Historical probe pin: `cb9b7b886244a27773f66b0b19fdc2998392565e`
- Profile: C++11 game / reverse-engineered Windows title / SDL2 + SDL2_mixer.
- Windows build: Visual Studio supported.
- Compatibility-first path: upstream supports MinGW Windows builds.
- Strength: unusually clean A/B bridge — the same project can plausibly be evaluated as native MSVC/PDB and MinGW/PE+DWARF.
- Caveat: original game resources are not included; compilation itself does not require shipping those resources.
- Role: **small dual-toolchain C++ target**.
- Before final corpus integration: choose and validate a stable release tag if available.

### 4. Nilesoft Shell — reserve
- Repo: https://github.com/moudey/Shell
- Historical probe pin: `81ec1a410d1277efa58aff52be912a254f66e5a3`
- Profile: Windows File Explorer context-menu extension.
- License: MIT.
- Upstream CI builds `src/Shell.sln` in Release for x64, x86 and ARM64 with MSBuild.
- Caveat: currently treated as MSVC-native; MinGW compatibility is not established.
- Role: **small native-Windows reserve target**.

## Medium tier

### 1. The Powder Toy — high-priority
- Repo: https://github.com/The-Powder-Toy/The-Powder-Toy
- Historical probe pin used in our CI: `b31f4462bc7d217159b83859a35405db9b640455`
- Profile: C++20 physics/simulation sandbox.
- Build system: Meson.
- Upstream build logic distinguishes MSVC, clang-cl, Windows GCC/MinGW and Windows Clang/MinGW-style environments.
- Prebuilt dependency variants include both Windows MinGW and Windows MSVC configurations.
- Strength: algorithm/physics-heavy code instead of another GUI-only target; good MSVC vs MinGW comparison candidate.
- Caveat: several third-party libraries; project-owned function attribution will matter, especially for static builds.
- Role: **medium algorithm-heavy dual-toolchain target**.
- Before final corpus integration: choose and validate a stable release tag if available.

### 2. Explorer++ — high-priority
- Repo: https://github.com/derceg/explorerplusplus
- Historical probe pin: `4d3f5320b9c307bef325fc78801d1dd7c6deb09d`
- Profile: lightweight native Windows file manager.
- Build requirements: Visual Studio, Desktop C++, Windows SDK; vcpkg manages dependencies.
- Has active upstream build CI and x86/x64/ARM64 release builds.
- Strength: representative Win32 GUI/file-system code without Windows Terminal-scale infrastructure.
- Caveat: vcpkg dependency restore cost must be measured; no MinGW path is currently assumed.
- Role: **medium native-Windows application**.
- Before final corpus integration: choose and validate a stable release tag if available.

### 3. Rainmeter — reserve
- Repo: https://github.com/rainmeter/rainmeter
- Historical probe pin: `e7403adda22d2b2d254c5c2efcc74e615d4846ff`
- Profile: mature Windows desktop customization application.
- License: GPLv2.
- Strength: mature Win32/event/timer/plugin-oriented application code.
- Caveat: full solution/install tooling may add noise; benchmark should target core runtime binaries rather than packaging projects.
- Role: **medium native-Windows reserve target**.

### 4. nCine — compatibility reserve
- Repo: https://github.com/nCine/nCine
- Profile: C++11 cross-platform 2D game engine, MIT.
- Upstream advertises separate Windows and MinGW CI and supports Windows with both MSVC and MinGW-w64/MSYS2.
- Strength: direct compiler-pair comparison is feasible.
- Caveat: broad dependency set may increase build and attribution cost.
- Role: **medium dual-toolchain reserve target**.

## Large tier

### 1. OpenLoco — validated historical probe
- Repo: https://github.com/OpenLoco/OpenLoco
- Historical probe pin: `96de081155f326a7af83f925185c1a934ba536b4`
- Profile: substantial game/simulation C++ codebase.
- Existing clean CI result: MSVC x64 Release PASS.
- Existing measured output: 7,745,536 B EXE, 61,722,624 B PDB, raw `PROC32` 21,257.
- Clean build cost observed: 1,699.576 s on Windows CI.
- Role: **large real-world C++ target**.
- Before final corpus integration: choose and validate a stable release tag if available.

### 2. Notepad++ — high-priority large candidate
- Repo: https://github.com/notepad-plus-plus/notepad-plus-plus
- Historical probe pin: `a6c46fd4cb0fa115ced3b3bfb1ff53fbdb8989f3`
- Profile: mature Windows-native text editor.
- License: GPLv3 with project clarifications/exceptions.
- MSVC path: Visual Studio x86/x64/ARM64.
- Compatibility-first path: upstream regularly tests MinGW-w64/GCC builds; Clang can also be selected.
- Strength: one of the strongest candidates for comparing the same Windows C++ application across MSVC and MinGW.
- Caveat: `notepad++.exe` links static Scintilla/Lexilla code and vendored Boost regex support, so project-owned vs bundled-library attribution needs an explicit policy.
- Role: **large dual-toolchain Windows application**.
- Before final corpus integration: choose and validate a stable release tag if available.

### 3. x64dbg — validated stress candidate
- Repo: https://github.com/x64dbg/x64dbg
- Historical probe pin: `17233957ea0a7e70d188187380bd74f80c2a4b93`
- Profile: Windows debugger / reverse-engineering system code.
- Existing clean CI result: MSVC x64 Release PASS.
- Core outputs validated: `x64gui.dll`, `x64dbg.dll`, `x64bridge.dll`.
- Caveat: dependency/submodule graph is heavy and current Release PDBs are not yet a complete source-level oracle.
- Role: **large system/reversing stress target**, preferably after the initial corpus works.

### 4. Windows Terminal / OpenConsole — stress only
- Repo: https://github.com/microsoft/terminal
- Historical probe pin: `20588130d8ef2ba40eb56bdae88e04cce7fc5b5d`
- Profile: very large Windows console/terminal system codebase.
- Recommendation: do **not** use the full solution as an initial corpus target. Select a component such as `Host.EXE` / conhost with its required dependencies.
- Role: **very-large component-level stress target**.

## Proposed initial C++ corpus shape

1. **Small clean control:** tinyxml2 `v11.0.0`
2. **Small Windows systems:** Microsoft Detours `v4.0.1`
3. **Small Windows GUI/game:** TrafficMonitor Lite + SpaceCadetPinball
4. **Medium:** The Powder Toy + Explorer++
5. **Large:** OpenLoco + Notepad++
6. **Stress later:** x64dbg + OpenConsole subset

This is intentionally a candidate pool, not a commitment to include every project in the final function sample set.

## Next validation pass

- [ ] Validate tinyxml2 `v11.0.0` MSVC x64 and record build/binary/PDB metrics.
- [ ] Validate Microsoft Detours `v4.0.1` MSVC x64 and a focused sample executable/DLL.
- [ ] Convert the remaining high-priority historical commit pins to stable release pins where practical.
- [ ] Validate SpaceCadetPinball with MSVC and MinGW-w64, preserving DWARF + `.ii` on the GCC path.
- [ ] Validate The Powder Toy MinGW counterpart.
- [ ] Validate Explorer++ MSVC x64 Release and measure dependency/build cost.
- [ ] Validate Notepad++ both MSVC and MinGW builds; separate Notepad++ / Scintilla / Lexilla attribution.
- [ ] Measure actual linked function populations before fixing final small/medium/large labels.
- [ ] Keep x64dbg/OpenConsole out of the initial corpus until the smaller pipeline is stable.
