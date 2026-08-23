# Candidate Summary

| Target | Role in a C++ corpus | Native Windows CI | Current recommendation |
| --- | --- | --- | --- |
| TrafficMonitor Lite | Compact Win32/MFC desktop target | PASS | Strong first target |
| OpenLoco | Medium/large real-world C++ application | PASS | Strong first target |
| The Powder Toy | Algorithm/physics-heavy C++ | Validation workflow added | Strong complementary target |
| x64dbg | Windows systems/reversing C++ | PASS | Stress/complexity tier |
| OpenConsole | Large Windows systems C++ | Heavy build in progress/under validation | Prefer component subset |

## Selection criteria

A useful DecBench candidate should have source available, a reproducible pinned build, a clear license, a meaningful amount of project-owned C++ code, manageable dependency contamination, and a binary set that can be mapped back to source ground truth.

The Windows candidates are intentionally diverse rather than five variations of the same application style: desktop/MFC, game/simulation, physics-heavy algorithms, debugger/system code, and a large Windows platform component.
