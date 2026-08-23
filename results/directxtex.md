# DecBench C++ target validation result — Microsoft DirectXTex

## Status

**PENDING** on the native MSVC/PDB track.

DirectXTex remains a selected Windows C++ candidate, but it has not yet received
the runtime qualification now completed for Detours. The earlier local-host
constraint is no longer the relevant blocker: the repository now has a proven
GitHub-hosted Windows/Visual Studio path. What remains is target-specific build and
PDB qualification.

## Target metadata

| Field | Value |
|---|---|
| Target | Microsoft DirectXTex |
| Upstream | `microsoft/DirectXTex` |
| Release/tag | `may2026` |
| Resolved commit | `4feb3e11a020f35b796fc769a74216a555d4f5ef` |
| Track | native MSVC / PE / PDB / CodeView |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Intended output | `DirectXTex.dll` + matching PDB |
| Intended role | Windows graphics / image-processing / rich-C++ stress target |

## Static config result

The TOML at `targets/windows/directxtex.toml` passed static review:

- the pinned commit matches the intended `may2026` release;
- the preferred output is `DirectXTex.dll` with shared-library configuration;
- sample builds and DX11 are disabled to reduce scope;
- the source filter is restricted to the DirectXTex library rather than optional
  tools/tests;
- the intended mode mapping is:

```text
O0:          /Od /Ob0 /Zi
O2:          /O2 /Zi
O2-noinline: /O2 /Ob0 /Zi
link:        /DEBUG with LTCG disabled
```

DirectXTex is intentionally expected to be a higher-pressure C++ identity target
because of its overload-rich public API and large set of image-processing helpers.
No collision number is claimed until an actual PDB is measured.

## Runtime qualification still required

A DirectXTex workflow should reuse the now-proven native Windows/MSVC infrastructure
but add target-specific checks for:

1. exact `may2026` checkout;
2. CMake/Visual Studio x64 build for all three modes;
3. explicit suppression of accidental Release IPO/LTCG;
4. exact `DirectXTex.dll` / `DirectXTex.pdb` pairing;
5. `IMAGE_FILE_MACHINE_AMD64` validation;
6. PDB source/compiland ownership restricted to DirectXTex project code;
7. procedure extraction and PDB name-collision measurement;
8. compact machine-readable evidence retained in Git.

## Current decision

DirectXTex is **not failed** and is no longer blocked by the absence of a usable
Windows CI environment. It is **PENDING runtime qualification** and should remain a
second-stage Windows candidate until equivalent PE/PDB evidence exists.
