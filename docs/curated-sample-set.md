# DecBench C++ Curated Sample-Set Specification

## Motivation & Design Principles

Following feedback from the DecBench team:
1. **Platform Balance:** An even spread between Linux (GCC/DWARF) and Windows (MSVC/CodeView PDB).
2. **Domain Diversity:** Balanced representation across systems/kernel-interface, server/network, CLI/developer tools, GUI/graphics, and modern user-space abstractions.
3. **Quality & Feature Coverage over Volume:** A focused, high-signal collection of programs highlighting diverse C++ paradigms (templates, inheritance hierarchies, SIMD, asynchronous I/O, Win32/POSIX system boundaries).

---

## Target Matrix

| Category | Target | Platform | Toolchain & Format | Key C++ Features & Paradigms |
|---|---|---|---|---|
| **System / Low-Level** | **Microsoft Detours** (v4.0.1) | Windows x64 | MSVC (`/Zi`, PE + PDB) | Machine-code hooking, instruction decoding, raw PE traversal, Win32 system boundary |
| **System / Storage** | **Google Snappy** (1.2.2) | Linux aarch64 | GCC 13.3 (`-g`, ELF + DWARF) | Bitwise compression algorithms, endianness abstractions, buffer iterators |
| **Network / Updater** | **WinSparkle** (v0.9.4) | Windows x64 | MSVC (`/Zi`, PE + PDB) | Worker thread pools, XML/RSS parsing, asynchronous HTTP, UI notification hooks |
| **Graphics / SIMD** | **Microsoft DirectXTex** (may2026) | Windows x64 | MSVC (`/Zi`, PE + PDB) | SIMD/DirectX math, pixel format conversions, deep class hierarchies |
| **Graphics / Software**| **tinyrenderer** | Linux aarch64 | GCC 13.3 (`-g`, ELF + DWARF) | Software 3D rendering pipeline, barycentric coordinates, geometry algebra |
| **Server / Async** | **Oat++** (1.3.0) / **Asio** | Linux aarch64 | GCC 13.3 (`-g`, ELF + DWARF) | Zero-copy DTO serialization, async coroutine networking, memory pools |
| **CLI / Build Tool** | **Ninja** (v1.13.1) | Linux / Windows | GCC & MSVC (Cross-platform) | Dependency graph DAG traversal, string hashing, lexer/parser, POSIX/Win32 subprocesses |
| **Modern C++ / Templates** | **fmt** (10.x) / **Catch2** (v3) | Linux aarch64 | GCC 13.3 (`-g`, ELF + DWARF) | Deep compile-time template metaprogramming, concepts, custom type formatters |

---

## Ground Truth Guarantees

- **Compilation Modes:** Evaluated across `O0`, `O2`, and `O2-noinline` for each target.
- **DWARF / PDB:** Unstripped debug artifacts preserved alongside every binary.
- **Source Units:** Preprocessed compilation units (`.ii` for GCC, `/P` for MSVC) stored to decouple raw AST/type ground truth from decompiler-specific scoring heuristics.
