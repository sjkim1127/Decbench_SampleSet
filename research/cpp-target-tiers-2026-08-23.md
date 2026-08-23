# DecBench multi-lang C++ target tiers — 2026-08-23

This note refreshes the Windows/C++ target search around **small / medium / large** tiers.

The tier is **not** based only on GitHub repository size. It is a provisional benchmark-cost classification based on expected build cost, dependency graph, linked binary size/function population, and source/third-party contamination. CI measurements should override these provisional labels.

## Recommended initial balance

| Tier | Primary | Secondary | Why |
| --- | --- | --- | --- |
| Small | TrafficMonitor Lite | SpaceCadetPinball | cheap baseline + a dual MSVC/MinGW game target |
| Medium | The Powder Toy | Explorer++ | algorithm/physics-heavy + native Win32 application |
| Large | OpenLoco | Notepad++ | large real-world C++ + a Windows target with both MSVC and MinGW build paths |
| Stress / expansion | x64dbg | OpenConsole component subset | system/reversing and very heavy Windows-system code; not first-line corpus targets |

This gives a six-target initial pool before function-level sampling, while keeping the heaviest projects out of the first pass.

## Small tier

### 1. TrafficMonitor Lite — validated
- Repo: https://github.com/zhongyang219/TrafficMonitor
- Probe pin: `5efd2159af8117301a2b6a755897aaa995887678`
- Profile: Windows desktop utility / MFC / Win32 C++.
- Existing clean CI result: MSVC x64 Release PASS.
- Existing measured output: ~1.94 MB EXE, ~19.85 MB PDB, raw `PROC32` 5,297.
- Role: **small native-Windows baseline**.

### 2. SpaceCadetPinball — new high-priority candidate
- Repo: https://github.com/k4zmu2a/SpaceCadetPinball
- Probe pin: `cb9b7b886244a27773f66b0b19fdc2998392565e`
- Profile: C++11 game / reverse-engineered Windows title / SDL2 + SDL2_mixer.
- Windows build: Visual Studio supported.
- Compatibility-first path: upstream explicitly documents MinGW cross-compilation for Windows.
- Strength: unusually clean A/B bridge — the same project can plausibly be evaluated as native MSVC/PDB and MinGW/PE+DWARF.
- Caveat: original game resources are not included; compilation itself does not require shipping those resources.
- Role: **small dual-toolchain C++ target**.

### 3. Nilesoft Shell — reserve
- Repo: https://github.com/moudey/Shell
- Probe pin: `81ec1a410d1277efa58aff52be912a254f66e5a3`
- Profile: Windows File Explorer context-menu extension.
- License: MIT.
- Upstream CI builds `src/Shell.sln` in Release for x64, x86 and ARM64 with MSBuild.
- Strength: small repository footprint, native Windows APIs, reproducible upstream Windows CI.
- Caveat: currently treated as MSVC-native; MinGW compatibility is not established.
- Role: **small native-Windows reserve target**.

## Medium tier

### 1. The Powder Toy — high-priority
- Repo: https://github.com/The-Powder-Toy/The-Powder-Toy
- Probe pin used in our CI: `b31f4462bc7d217159b83859a35405db9b640455`
- Profile: C++20 physics/simulation sandbox.
- Build system: Meson.
- Upstream build logic explicitly distinguishes `msvc`, `clang-cl`, Windows GCC/MinGW and Windows Clang/MinGW-style environments.
- Prebuilt dependency variants include both `x86_64-windows-mingw-*` and `x86_64-windows-msvc-*`.
- Strength: algorithm/physics-heavy code instead of another GUI-only target; good MSVC vs MinGW comparison candidate.
- Caveat: several third-party libraries; project-owned function attribution will matter, especially for static builds.
- Role: **medium algorithm-heavy dual-toolchain target**.

### 2. Explorer++ — new high-priority candidate
- Repo: https://github.com/derceg/explorerplusplus
- Probe pin: `4d3f5320b9c307bef325fc78801d1dd7c6deb09d`
- Profile: lightweight native Windows file manager.
- Build requirements: Visual Studio 2019/2022, Desktop C++, Windows 10 SDK; vcpkg manages dependencies.
- Has active upstream build CI and x86/x64/ARM64 release builds.
- Strength: representative Win32 GUI/file-system code without Windows Terminal-scale infrastructure.
- Caveat: vcpkg dependency restore cost must be measured; no MinGW path is currently assumed.
- Role: **medium native-Windows application**.

### 3. Rainmeter — reserve
- Repo: https://github.com/rainmeter/rainmeter
- Probe pin: `e7403adda22d2b2d254c5c2efcc74e615d4846ff`
- Profile: mature Windows desktop customization application.
- License: GPLv2.
- Upstream build docs use Visual Studio 2026 with Desktop C++ and `Rainmeter.sln`.
- Strength: mature Win32/event/timer/plugin-oriented application code.
- Caveat: full solution/install tooling may add noise; benchmark should target core runtime binaries rather than packaging projects.
- Role: **medium native-Windows reserve target**.

### 4. nCine — compatibility reserve
- Repo: https://github.com/nCine/nCine
- Profile: C++11 cross-platform 2D game engine, MIT.
- Upstream advertises separate Windows and MinGW CI and supports Windows with both MSVC and MinGW-w64/MSYS2.
- Strength: direct compiler-pair comparison is feasible.
- Caveat: broad dependency set (graphics/audio/Lua/UI libraries) may increase build and attribution cost.
- Role: **medium dual-toolchain reserve target**.

## Large tier

### 1. OpenLoco — validated
- Repo: https://github.com/OpenLoco/OpenLoco
- Probe pin: `96de081155f326a7af83f925185c1a934ba536b4`
- Profile: substantial game/simulation C++ codebase.
- Existing clean CI result: MSVC x64 Release PASS.
- Existing measured output: ~9.67 MB EXE, ~26.48 MB PDB, raw `PROC32` 10,777.
- Clean build cost observed: ~1,656 s on Windows CI.
- Role: **large real-world C++ target**.

### 2. Notepad++ — new high-priority large candidate
- Repo: https://github.com/notepad-plus-plus/notepad-plus-plus
- Probe pin: `a6c46fd4cb0fa115ced3b3bfb1ff53fbdb8989f3`
- Profile: mature Windows-native text editor.
- License: GPLv3 with project clarifications/exceptions.
- MSVC path: Visual Studio 2022, x86/x64/ARM64.
- Compatibility-first path: upstream explicitly documents and regularly tests MinGW-w64/GCC builds; Clang can also be selected.
- Strength: one of the strongest candidates for comparing the same Windows C++ application across MSVC and MinGW.
- Caveat: `notepad++.exe` links static Scintilla/Lexilla code and vendored Boost regex support, so project-owned vs bundled-library attribution needs an explicit policy.
- Role: **large dual-toolchain Windows application**.

### 3. x64dbg — validated stress candidate
- Repo: https://github.com/x64dbg/x64dbg
- Probe pin: `17233957ea0a7e70d188187380bd74f80c2a4b93`
- Profile: Windows debugger / reverse-engineering system code.
- Existing clean CI result: MSVC x64 Release PASS.
- Core outputs validated: `x64gui.dll`, `x64dbg.dll`, `x64bridge.dll`.
- Caveat: dependency/submodule graph is heavy and current Release PDBs are not yet a complete source-level oracle.
- Role: **large system/reversing stress target**, preferably after the initial corpus works.

### 4. Windows Terminal / OpenConsole — stress only
- Repo: https://github.com/microsoft/terminal
- Probe pin: `20588130d8ef2ba40eb56bdae88e04cce7fc5b5d`
- Profile: very large Windows console/terminal system codebase.
- Recommendation: do **not** use the full solution as an initial corpus target. Select a component such as `Host.EXE` / conhost with its required dependencies.
- Role: **very-large component-level stress target**.

## Why this is safer than the original flat shortlist

The previous shortlist mixed tiny utilities and very large system applications as if they had equal integration cost. For DecBench, the sample-set itself may select only a limited number of functions, but the project still has to be downloaded, built at multiple optimization levels, preprocessed, ground-truthed and source-CFG parsed. Corpus construction cost therefore matters independently of sample-set size.

A better first pass is:

1. **Small:** TrafficMonitor Lite + SpaceCadetPinball
2. **Medium:** The Powder Toy + Explorer++
3. **Large:** OpenLoco + Notepad++
4. **Stress later:** x64dbg + OpenConsole subset

## Next validation pass

- [ ] Add SpaceCadetPinball MSVC x64 Release CI.
- [ ] Add SpaceCadetPinball MinGW-w64 build with DWARF + `.ii` preservation.
- [ ] Finish The Powder Toy MSVC validation, then add a MinGW counterpart.
- [ ] Add Explorer++ MSVC x64 Release CI and measure dependency/build cost.
- [ ] Add Notepad++ both MSVC and MinGW builds; separate Notepad++ / Scintilla / Lexilla attribution.
- [ ] Measure actual linked function populations before fixing final small/medium/large labels.
- [ ] Keep x64dbg/OpenConsole out of the initial corpus until the smaller pipeline is stable.
