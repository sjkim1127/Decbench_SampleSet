# Canonical stable release pins

This file is the source-of-truth candidate pin manifest for the DecBench multi-language C++ target study.

## Policy

- Benchmark candidates are pinned to a **published stable release tag**, not to a moving branch head or an arbitrary development commit.
- Each entry records both the human-facing release/tag and the exact commit SHA that tag resolved to when validated.
- CI must clone the release tag and verify the resolved SHA before building.
- Prereleases and snapshots are excluded unless there is a benchmark-specific reason to use one.
- A project without a usable stable source release is not part of the release-pinned candidate pool.

## Current release-pinned pool

| Tier | Project | Stable release/tag | Resolved commit | Intended role |
| --- | --- | --- | --- | --- |
| Small | tinyxml2 | `11.0.0` | `9148bdf719e997d1f474be6bcc7943881046dba1` | clean low-noise C++ control |
| Small | Microsoft Detours | `v4.0.1` | `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833` | Windows systems / instrumentation |
| Small | TrafficMonitor | `V1.86` | `02a817a069bac6bf4d263b5209d9c1b07fe2f950` | native Windows/MFC GUI |
| Small | SpaceCadetPinball | `Release_2.1.0` | `6a30ccbef12c7b7781ccf89788d77461fa20a90a` | small dual-toolchain game / OO C++ |
| Medium | The Powder Toy | `v100.0.399` | `9c94feba3ed5eaa75a819ac000c0d29e4ce92570` | algorithm / simulation-heavy C++ |
| Medium | Explorer++ | `version-1.4.0` | `384c2f687fd55c1e71e9fcb272f9113de009a248` | native Win32 application |
| Medium reserve | Rainmeter | `v4.5.26.3894` | `5a124b6a09e2f7f67f8be9232718c489100e6173` | mature Windows application reserve |
| Large | OpenLoco | `v26.07.1` | `5c95820e2c022698f89908b8aade12423b1eef21` | large real-world game / simulation C++ |
| Large | Notepad++ | `v8.9.6.1` | `41dd976310db0ba551bb8a2810b60331df3a77f5` | mature Windows app; MSVC/MinGW comparison |
| Stress | x64dbg | `2026.05.27` | `9c8ca1cae0b6d56cc44f31fddcb10e3b02ffbb87` | reversing / Windows systems stress target |
| Stress | Windows Terminal / OpenConsole | `v1.24.11321.0` | `b4e69c68620a822407d45bfbba6ee10feebc70a3` | very large component-level Windows systems target |

## Not in the release-pinned pool

- **Nilesoft Shell:** no usable GitHub stable source release was identified for this policy. Keep it out of the active pool rather than falling back to a development commit.
- **nCine:** no usable current GitHub stable release was identified in this pass. Keep it as an external reserve idea only; do not use a branch-head pin.

## Validation status semantics

A release pin is not considered validated merely because the tag exists. Validation requires:

1. tag -> expected SHA verification,
2. clean build in the intended CI environment,
3. output binary identification,
4. compiler/toolchain metadata,
5. PE/PDB or PE/DWARF evidence as appropriate, and
6. `.ii` preservation for the GCC/MinGW compatibility-first path.

Older commit-based CI results remain useful as feasibility history, but they are not candidate versions and must not be used as final corpus pins.
