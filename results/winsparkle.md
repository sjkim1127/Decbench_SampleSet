# DecBench C++ target validation result — WinSparkle

## Status

**PENDING** on the native MSVC/PDB track.

WinSparkle remains a selected Windows C++ candidate, but it has not yet received
the runtime qualification now completed for Detours. The repository now has a
working GitHub-hosted Windows/Visual Studio path, so the remaining work is
WinSparkle-specific MSBuild/LTCG/PDB qualification rather than lack of access to an
MSVC environment.

## Target metadata

| Field | Value |
|---|---|
| Target | WinSparkle |
| Upstream | `vslavik/winsparkle` |
| Release/tag | `v0.9.4` |
| Resolved commit | `a8986caf620262f7d4581b241436ceaa0cc9370f` |
| Track | native MSVC / PE / PDB / CodeView |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Intended output | `WinSparkle.dll` + matching PDB |
| Build system | Visual Studio / MSBuild x64 |
| Intended role | Windows updater / networking / threading / UI-oriented C++ |

## Static config result

The TOML at `targets/windows/winsparkle.toml` passed static review:

- the pinned commit matches upstream `v0.9.4`;
- the project is correctly treated as Visual Studio/MSBuild rather than a GCC-like
  build;
- expected x64 DLL/PDB output paths are identified;
- source ownership is restricted to WinSparkle project code and excludes third-party
  dependencies, examples, and tests;
- the intended mode mapping is:

```text
O0:          /Od /Ob0 /Zi
O2:          /O2 /Zi
O2-noinline: /O2 /Ob0 /Zi
link:        /DEBUG with LTCG disabled
```

A key risk is upstream Release `WholeProgramOptimization`. The runtime harness must
explicitly disable WPO/LTCG rather than assume command-line optimization flags are
sufficient.

## Runtime qualification still required

The Detours workflow proves that native Visual Studio/MSVC/PDB qualification is
viable on GitHub-hosted Windows. WinSparkle still needs target-specific checks for:

1. exact `v0.9.4` checkout;
2. x64 MSBuild for O0/O2/O2-noinline;
3. explicit `WholeProgramOptimization=false` / LTCG-off verification;
4. exact DLL/PDB pairing;
5. `IMAGE_FILE_MACHINE_AMD64` validation;
6. PDB source/compiland filtering that excludes `3rdparty/**`;
7. procedure extraction and repeated-name diagnostics from the actual PDB;
8. compact machine-readable evidence retained in Git.

Repeated class-local names around thread/update-check behavior are a known source
review risk, but no collision percentage is claimed until the PDB is measured.

## Current decision

WinSparkle is **not failed** and is no longer blocked by absence of Windows tooling.
It is **PENDING runtime qualification** and should remain a second-stage candidate
until the MSBuild/WPO/PDB gates above have actual execution evidence.
