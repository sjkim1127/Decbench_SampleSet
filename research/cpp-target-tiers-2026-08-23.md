# DecBench multi-lang C++ target tiers — 2026-08-23

This note organizes the Windows/C++ target search around **small / medium / large** tiers. Tiering is based on expected benchmark cost: build time, dependency graph, linked function population, source/third-party contamination, and oracle complexity.

## Pinning policy

The candidate pool is now **release-only**.

- Use a published stable release/tag as the corpus version.
- Record the exact commit SHA that the tag resolves to.
- CI clones the tag and verifies that SHA before building.
- Do not use branch heads, arbitrary latest commits, prereleases, or snapshots as final corpus pins.
- If a project has no usable stable source release, keep it out of the active pool instead of falling back to a development commit.

The canonical list is maintained in [`research/release-pins.md`](./release-pins.md).

## Recommended balance

| Tier | Primary | Secondary | Additional | Role |
| --- | --- | --- | --- | --- |
| Small | TrafficMonitor `V1.86` | SpaceCadetPinball `Release_2.1.0` | tinyxml2 `11.0.0`, Detours `v4.0.1` | GUI/game + clean-control + Windows systems |
| Medium | The Powder Toy `v100.0.399` | Explorer++ `version-1.4.0` | Rainmeter `v4.5.26.3894` reserve | algorithm-heavy + native Win32 application |
| Large | OpenLoco `v26.07.1` | Notepad++ `v8.9.6.1` | — | large real-world C++ + dual-toolchain Windows app |
| Stress / expansion | x64dbg `2026.05.27` | Windows Terminal `v1.24.11321.0` OpenConsole subset | — | reversing/system-heavy stress targets |

Target discovery is effectively saturated. The useful work now is release build/oracle validation rather than collecting more names.

## Small tier

### tinyxml2 — clean control
- Repo: https://github.com/leethomason/tinyxml2
- Stable tag: `11.0.0`
- Resolved SHA: `9148bdf719e997d1f474be6bcc7943881046dba1`
- Role: low-noise C++ baseline with minimal dependency/build-system contamination.
- Release CI: MSVC x64 build validated.
- Oracle caveat: the default Release configuration did not emit a PDB; native MSVC type/oracle experiments would need explicit debug-info flags.

### Microsoft Detours — Windows systems baseline
- Repo: https://github.com/microsoft/Detours
- Stable tag: `v4.0.1`
- Resolved SHA: `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833`
- Role: compact Windows API instrumentation/binary-rewriting C++.
- Release CI: MSVC x64 library + focused sample build validated.
- Build note: upstream samples require `syelog` before the `simple` sample.

### TrafficMonitor Lite — native Windows GUI
- Repo: https://github.com/zhongyang219/TrafficMonitor
- Stable tag: `V1.86`
- Resolved SHA: `02a817a069bac6bf4d263b5209d9c1b07fe2f950`
- Role: MFC/Win32 application baseline.
- CI requirement: use a VS2022 image with the required MFC components rather than relying on `windows-latest`.

### SpaceCadetPinball — dual-toolchain small target
- Repo: https://github.com/k4zmu2a/SpaceCadetPinball
- Stable tag: `Release_2.1.0`
- Resolved SHA: `6a30ccbef12c7b7781ccf89788d77461fa20a90a`
- Profile: C++11, SDL2/SDL2_mixer, game/OO code.
- Role: same source can be probed under MSVC/PDB and MinGW/PE+DWARF+`.ii`.
- Caveat: original game resources are not part of the source release; compilation itself remains usable for corpus validation.

## Medium tier

### The Powder Toy — algorithm/simulation target
- Repo: https://github.com/The-Powder-Toy/The-Powder-Toy
- Stable tag: `v100.0.399`
- Resolved SHA: `9c94feba3ed5eaa75a819ac000c0d29e4ce92570`
- Profile: C++20 physics/simulation sandbox.
- Role: algorithm-heavy C++ and a strong MSVC vs MinGW comparison candidate.
- Caveat: static/prebuilt dependencies require project-owned function attribution.

### Explorer++ — native Win32 application
- Repo: https://github.com/derceg/explorerplusplus
- Stable tag: `version-1.4.0`
- Resolved SHA: `384c2f687fd55c1e71e9fcb272f9113de009a248`
- Role: Windows file-manager code without Windows Terminal-scale build cost.
- Caveat: release-era vcpkg/submodule layout must be validated independently from current-main CI assumptions.

### Rainmeter — reserve
- Repo: https://github.com/rainmeter/rainmeter
- Stable tag: `v4.5.26.3894`
- Resolved SHA: `5a124b6a09e2f7f67f8be9232718c489100e6173`
- Role: mature Windows event/timer/plugin-oriented application reserve.
- Recommendation: target core runtime binaries, not installer/packaging projects.

## Large tier

### OpenLoco — large real-world target
- Repo: https://github.com/OpenLoco/OpenLoco
- Stable tag: `v26.07.1`
- Resolved SHA: `5c95820e2c022698f89908b8aade12423b1eef21`
- Role: substantial game/simulation C++.
- CI requirement: use VS2022 because the Windows preset explicitly targets the Visual Studio 17 2022 generator.

### Notepad++ — large dual-toolchain Windows target
- Repo: https://github.com/notepad-plus-plus/notepad-plus-plus
- Stable tag: `v8.9.6.1`
- Resolved SHA: `41dd976310db0ba551bb8a2810b60331df3a77f5`
- Role: mature Windows-native application with both MSVC and MinGW/GCC paths.
- Caveat: Scintilla/Lexilla and bundled/vendor code must be separated from Notepad++-owned function attribution.

## Stress / expansion

### x64dbg
- Repo: https://github.com/x64dbg/x64dbg
- Stable tag: `2026.05.27`
- Resolved SHA: `9c8ca1cae0b6d56cc44f31fddcb10e3b02ffbb87`
- Role: reversing/system-heavy Windows C++ stress target.
- Keep after the initial corpus because dependency/submodule and oracle cost are materially higher.

### Windows Terminal / OpenConsole
- Repo: https://github.com/microsoft/terminal
- Stable tag: `v1.24.11321.0`
- Resolved SHA: `b4e69c68620a822407d45bfbba6ee10feebc70a3`
- Role: very-large Windows systems stress target.
- Use an OpenConsole/conhost component subset rather than treating the entire solution as one initial corpus target.

## Excluded under release-only policy

- **Nilesoft Shell:** no usable GitHub stable source release was identified in this pass; do not fall back to a branch-head pin.
- **nCine:** no usable current GitHub stable release was identified in this pass; keep as an external reserve idea only.

## Proposed initial corpus shape

1. Small clean control: tinyxml2 `11.0.0`
2. Small Windows systems: Detours `v4.0.1`
3. Small application/game: TrafficMonitor `V1.86`, SpaceCadetPinball `Release_2.1.0`
4. Medium: The Powder Toy `v100.0.399`, Explorer++ `version-1.4.0`
5. Large: OpenLoco `v26.07.1`, Notepad++ `v8.9.6.1`
6. Stress later: x64dbg `2026.05.27`, OpenConsole from Windows Terminal `v1.24.11321.0`

This remains a candidate pool, not a commitment to include every project in the final function sample set.

## Validation checklist

- [x] tinyxml2 release pin + MSVC clean build
- [x] Detours release pin + MSVC focused sample build
- [ ] TrafficMonitor `V1.86` release build on VS2022/MFC
- [ ] SpaceCadetPinball `Release_2.1.0` MSVC + MinGW/DWARF/`.ii`
- [ ] The Powder Toy `v100.0.399` MSVC + MinGW/DWARF/`.ii`
- [ ] Explorer++ `version-1.4.0` release build
- [ ] OpenLoco `v26.07.1` release build on VS2022
- [ ] Notepad++ `v8.9.6.1` MSVC + MinGW/DWARF/`.ii`
- [ ] x64dbg `2026.05.27` release build
- [ ] Windows Terminal `v1.24.11321.0` OpenConsole component build
- [ ] Measure linked function populations and source/vendor attribution before final tier lock-in
