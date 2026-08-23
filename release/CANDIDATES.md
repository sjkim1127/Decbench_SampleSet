# Candidate Summary

The active candidate pool is **stable-release-only**. Each tag is paired with the exact SHA it resolved to during validation setup.

| Tier | Target | Stable release/tag | Role in a C++ corpus |
| --- | --- | --- | --- |
| Small | tinyxml2 | `11.0.0` | clean low-noise C++ control |
| Small | Microsoft Detours | `v4.0.1` | Windows systems/instrumentation |
| Small | TrafficMonitor | `V1.86` | Win32/MFC desktop target |
| Small | SpaceCadetPinball | `Release_2.1.0` | compact game/OO target; MSVC + MinGW bridge |
| Medium | The Powder Toy | `v100.0.399` | algorithm/physics-heavy C++ |
| Medium | Explorer++ | `version-1.4.0` | native Win32 application |
| Large | OpenLoco | `v26.07.1` | large real-world game/simulation C++ |
| Large | Notepad++ | `v8.9.6.1` | mature Windows app; MSVC/MinGW comparison |
| Stress | x64dbg | `2026.05.27` | Windows systems/reversing C++ |
| Stress | Windows Terminal / OpenConsole | `v1.24.11321.0` | very-large Windows systems component |

Rainmeter `v4.5.26.3894` is retained as a reserve. Nilesoft Shell and nCine are not active candidates because this pass did not identify a usable stable GitHub source release; the policy does not fall back to a moving branch or arbitrary commit.

## Selection criteria

A useful DecBench candidate should have source available, a reproducible stable release, a clear license, a meaningful amount of project-owned C++ code, manageable dependency contamination, and a binary set that can be mapped back to source ground truth.

For every active candidate the CI must verify `release tag -> expected SHA` before compiling. Old commit-probe results are historical feasibility evidence only and are not corpus versions.
