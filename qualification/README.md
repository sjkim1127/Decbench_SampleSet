# DecBench C++ corpus qualification farm

This directory documents the CI layer used to turn a source-available C++ candidate into evidence that is useful to DecBench rather than only proving that the upstream project builds.

## Current scope

The first qualification lane deliberately targets the compatibility-first path already present in DecBench at revision `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`:

- stable release tags only;
- the real DecBench `compile_project` / `scripts/compile_all.py` path;
- `O0`, `O2`, and `O2-noinline`;
- linked ELF or MinGW PE outputs;
- `.ii` preservation;
- DWARF procedure/name evidence;
- short-name collision pressure for experimental C++ scoring;
- pyjoern parse coverage over the captured `.ii` translation units;
- three independent clean builds for binary-hash reproducibility;
- a non-blocking real DecBench/angr O2 smoke on the smallest control target.

The initial executable qualification targets are:

1. `tinyxml2 11.0.0` — low-noise native GCC C++ control;
2. `Notepad++ v8.9.6.1` — real Windows x86-64 C++ target through MinGW PE + DWARF + `.ii`.

The rest of the stable-release candidate pool remains in the build-validation workflows. Targets should only be promoted into this DecBench-shaped lane when their build recipe can preserve DecBench-controlled optimization flags and source ground truth without silently substituting the upstream project's own Release policy.

## Why three clean builds?

A benchmark target should not only compile. Rebuilding the same release/toolchain/configuration three times gives an immediate signal about whether the emitted binary is deterministic enough for long-lived corpus use. Nondeterminism is recorded as evidence rather than treated as a CI infrastructure failure.

## Qualification outputs

Each matrix cell uploads the full compiled DecBench result tree plus:

- `compile_report.json`
- `dwarf-audit.json`
- `joern-audit.json`
- `QUALIFICATION.md`

A second job compares binary SHA-256 values across the three clean-build replicates. A final non-blocking lane attempts an actual O2 `angr` decompile/evaluate pass for tinyxml2.

## Promotion rule

A candidate should not be described as DecBench-compatible merely because its upstream CI is green. Promotion requires, at minimum:

1. all three optimization levels build through DecBench;
2. at least one linked benchmark image is collected per level;
3. `.ii` files are captured per level;
4. usable DWARF subprogram evidence exists;
5. Joern parse coverage is measured;
6. name-collision pressure is reported;
7. dependency/project-owned-source contamination is understood.

Native MSVC/PDB targets remain a separate research track. They are useful Windows feasibility evidence, but they are not silently treated as compatible with DecBench's current GCC/DWARF ground-truth path.
