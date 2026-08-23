# DecBench Windows C++ Target Validation — Release-Pinned Refresh

This is a research handoff for candidate selection, not a DecBench integration release.

## Main change

The candidate workspace has moved from development-commit probes to a **stable-release-only** corpus policy.

- Every active target has a published stable release/tag.
- The exact SHA resolved by that tag is recorded in `research/release-pins.md`.
- CI clones the release tag and rejects it if it does not resolve to the expected SHA.
- Arbitrary latest commits, branch heads, prereleases, and snapshots are not final corpus pins.
- Historical commit-based CI remains available only as feasibility evidence.

## Release-pinned candidates

- tinyxml2 `11.0.0`
- Microsoft Detours `v4.0.1`
- TrafficMonitor `V1.86`
- SpaceCadetPinball `Release_2.1.0`
- The Powder Toy `v100.0.399`
- Explorer++ `version-1.4.0`
- OpenLoco `v26.07.1`
- Notepad++ `v8.9.6.1`
- x64dbg `2026.05.27`
- Windows Terminal / OpenConsole `v1.24.11321.0`

Rainmeter `v4.5.26.3894` is retained as a reserve.

## Validation status

Stable-tag validation is already green for:

- **tinyxml2 `11.0.0`** — MSVC x64 clean build.
- **Microsoft Detours `v4.0.1`** — MSVC x64 library plus focused sample build.

The other targets are being rerun from their release tags. Older build metrics are not promoted to the release-pinned corpus until the corresponding tag build succeeds.

## Fit with current DecBench

Current DecBench C++ evaluation is primarily GCC/DWARF based. The compatibility-first jobs therefore preserve `.ii` preprocessing output and DWARF for MinGW-capable projects, while MSVC/PDB builds remain a separate native-Windows feasibility path.

Function counts from compiler/linker output, PDB procedure records, source-attributable functions, and decompiler-discovered functions remain separate measurements.

## Suggested tier order

1. Small controls/systems: tinyxml2, Detours
2. Small application/game: TrafficMonitor, SpaceCadetPinball
3. Medium: The Powder Toy, Explorer++
4. Large: OpenLoco, Notepad++
5. Stress: x64dbg, OpenConsole component subset

This refresh deliberately removes the stale OpenLoco measurements that were present in Preview 1. Fresh metrics should be published only from the release-tag validation runs.
