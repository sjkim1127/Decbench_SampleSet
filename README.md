# DecBench C++ Sample-Set Validation

Private CI workspace for validating candidate C++ / Windows C++ targets for a future DecBench multi-language corpus.

The repository does **not** vendor third-party source trees. Active candidates are pinned to published **stable release tags**. CI clones the tag, verifies the exact commit SHA it resolves to, builds it on a controlled Windows toolchain, and records build/oracle evidence.

Arbitrary branch heads and development commits are not candidate corpus versions. Older commit-based runs remain historical feasibility evidence only.

## Release-pinned candidate pool

| Tier | Target | Stable release/tag | Resolved commit | Primary path |
|---|---|---|---|---|
| Small | tinyxml2 | `11.0.0` | `9148bdf719e997d1f474be6bcc7943881046dba1` | MSVC clean control |
| Small | Microsoft Detours | `v4.0.1` | `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833` | MSVC Windows systems |
| Small | TrafficMonitor | `V1.86` | `02a817a069bac6bf4d263b5209d9c1b07fe2f950` | MSVC/MFC x64 |
| Small | SpaceCadetPinball | `Release_2.1.0` | `6a30ccbef12c7b7781ccf89788d77461fa20a90a` | MSVC + MinGW/DWARF/`.ii` |
| Medium | The Powder Toy | `v100.0.399` | `9c94feba3ed5eaa75a819ac000c0d29e4ce92570` | MSVC + MinGW/DWARF/`.ii` |
| Medium | Explorer++ | `version-1.4.0` | `384c2f687fd55c1e71e9fcb272f9113de009a248` | MSVC x64 |
| Large | OpenLoco | `v26.07.1` | `5c95820e2c022698f89908b8aade12423b1eef21` | MSVC x64 |
| Large | Notepad++ | `v8.9.6.1` | `41dd976310db0ba551bb8a2810b60331df3a77f5` | MSVC + MinGW/DWARF/`.ii` |
| Stress | x64dbg | `2026.05.27` | `9c8ca1cae0b6d56cc44f31fddcb10e3b02ffbb87` | MSVC x64 |
| Stress | Windows Terminal / OpenConsole | `v1.24.11321.0` | `b4e69c68620a822407d45bfbba6ee10feebc70a3` | release-era MSVC/OpenConsole |

Rainmeter `v4.5.26.3894` is retained as a medium-tier reserve. Projects without a usable stable source release are excluded rather than silently falling back to a development commit.

The canonical source of truth is [`research/release-pins.md`](research/release-pins.md).

## What CI records

- stable release/tag plus resolved upstream commit
- runner / Visual Studio / compiler / CMake or Meson versions
- clone size and submodule count
- clean build duration
- output PE size and SHA-256
- matching PDB when emitted
- PDB procedure-symbol evidence where applicable
- PE/DWARF evidence and preserved `.ii` files for MinGW/GCC compatibility probes
- build blockers and release-era environment requirements

PDB procedure counts are **not** treated as final source-function ground truth. Compiler/linker-emitted functions, PDB/CodeView procedures, source-attributable functions, and decompiler-discovered functions remain separate measurements.

## Workflows

- `.github/workflows/release-baseline-small-cpp.yml` — tinyxml2 + Detours release baselines
- `.github/workflows/windows-cpp-validation.yml` — TrafficMonitor, OpenLoco, x64dbg, OpenConsole release builds
- `.github/workflows/powder-toy-validation.yml` — Powder Toy release MSVC pass
- `.github/workflows/cpp-tier-validation.yml` — SpaceCadetPinball, Powder Toy MinGW, Explorer++, Notepad++ release-tier validation
