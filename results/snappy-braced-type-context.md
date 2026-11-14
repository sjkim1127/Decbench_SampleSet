# Snappy braced temporary type context

This sidecar supplies the visible type name for 13 entries where an isolated
Snappy definition uses `CompressionOptions{}`. The preprocessed translation
unit declares the type, but the function slice leaves that declaration behind.
The entries cover Linux ARM64 O0 (6), macOS ARM64 O0 (6), and macOS ARM64 O2 (1).

Use the [frozen qualification-v2 revision](https://huggingface.co/datasets/sjkim1127/decbench-cpp-qualification/tree/07dd95dbe6214b8a78fc1e4a55961ab515986489/qualification-v2).
Its manifest SHA-256 is
`0744ffeea002d3e9a5ce0ee26cd24bfbe5c648ca216655c5af6189f146b9ae7e`.
The sidecar keys each entry by the unstripped binary hash and exact address.
Apply it only after the TU member, TU hash, qualified definition name and
definition hash also match. Give this metadata to the source evaluator only.

## Reproduce the evidence

1. Verify the archived binary and source archive against the frozen manifest.
   Linux members are in `sources/snappy/preprocessed-all-modes.tar.gz`; macOS
   members are in the corresponding binary directory's `preprocessed.tar.gz`.
2. Check the selected definition against its native debug location and TU.
   On Linux, GCC 13.3.0's `-fdump-lang-raw` identifies the
   `snappy::CompressionOptions` record and typed operands in the selected
   definition. On macOS, Apple Clang 17.0.0's AST JSON
   (`-Xclang -ast-dump=json`) identifies the constructed type. The Clang
   declaration must match the function's presumed file and line and its exact
   definition bytes. Both builds use C++11.
3. Parse the selected definition in strict C++ mode with Rust-Joern. With the
   verified `cpp_type_names` it yields a CFG for the complete selected function.
   Without those names the isolated parse reports an unexpected `{`.
   The six distinct definitions in this sidecar match the directed CFG
   topology and entry/exit roles of Joern 4.0.150 / PyJoern 4.0.150.4.

The sidecar contains compiler-verified source hints. The CFG comparison covers
topology and function boundaries. Windows entries require separate compiler
evidence and are outside this sidecar.
