# DecBench Windows C++ Target Validation

This is a compact research handoff workspace for evaluating candidate C++ targets for the multi-language phase of DecBench.

## Reproducibility policy

Candidate corpus versions are now pinned to **published stable source releases**, not arbitrary development commits. Each release tag is paired with the exact commit SHA it resolved to, and CI verifies that mapping before building.

The canonical manifest is [`research/release-pins.md`](../research/release-pins.md).

## Active candidate set

| Tier | Target | Stable release/tag | Intended role |
| --- | --- | --- | --- |
| Small | tinyxml2 | `11.0.0` | clean low-noise control |
| Small | Microsoft Detours | `v4.0.1` | Windows systems/instrumentation |
| Small | TrafficMonitor | `V1.86` | Win32/MFC application |
| Small | SpaceCadetPinball | `Release_2.1.0` | small MSVC/MinGW bridge |
| Medium | The Powder Toy | `v100.0.399` | algorithm/physics-heavy C++ |
| Medium | Explorer++ | `version-1.4.0` | native Win32 application |
| Large | OpenLoco | `v26.07.1` | large game/simulation codebase |
| Large | Notepad++ | `v8.9.6.1` | mature Windows app; compiler-pair target |
| Stress | x64dbg | `2026.05.27` | reversing/system-heavy C++ |
| Stress | Windows Terminal / OpenConsole | `v1.24.11321.0` | very-large component-level stress target |

Rainmeter `v4.5.26.3894` is a reserve candidate. Projects without a usable stable source release are kept out of the active set rather than pinned to a branch head.

## Current validation status

- tinyxml2 `11.0.0`: stable-tag MSVC x64 clean build **PASS**.
- Microsoft Detours `v4.0.1`: stable-tag MSVC x64 library + focused sample build **PASS**.
- The remaining active candidates are being revalidated from their stable tags. Previous commit-based successes remain useful feasibility evidence, but they are not treated as candidate corpus versions.

## DecBench compatibility note

Current DecBench C++ evaluation is primarily GCC/DWARF based:

- source CFG input is derived from GCC `-save-temps=obj` `.ii` files and parsed with Joern;
- type ground truth comes from DWARF via pyelftools.

For Windows projects with a MinGW/GCC path, the validation workflows preserve PE + DWARF + `.ii` so the existing evaluation architecture can potentially be reused. Native MSVC builds retain PE/PDB evidence as a separate feasibility path; PDB/CodeView support is not assumed to exist in DecBench today.

## Corpus shape

The working recommendation is intentionally tiered rather than selecting only large applications:

1. clean control — tinyxml2;
2. compact Windows systems — Detours;
3. small application/game — TrafficMonitor and SpaceCadetPinball;
4. medium — The Powder Toy and Explorer++;
5. large — OpenLoco and Notepad++;
6. stress later — x64dbg and an OpenConsole component subset.

This is a candidate pool, not a commitment to include every project in the final function sample set.

## Repository purpose

This private repository is a validation/staging workspace rather than a proposed DecBench patch. It records source-release pins, CI recipes, toolchain constraints, build results, and oracle feasibility so maintainers can choose the corpus before upstream integration work begins.
