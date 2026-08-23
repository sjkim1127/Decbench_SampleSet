# Release-pinned small C++ baselines

## tinyxml2

- Release: `v11.0.0`
- Resolved commit: `9148bdf719e997d1f474be6bcc7943881046dba1`
- Role: clean, low-noise C++ control target
- Build probe: MSVC x64 Release with `xmltest.exe`

## Microsoft Detours

- Release: `v4.0.1`
- Resolved commit: `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833`
- Role: compact Windows systems/instrumentation C++ target
- Build probe: MSVC x64 via upstream `nmake`, focused on the Detours library and `samples/simple` outputs

These release pins are intentionally preferred over current branch heads. The CI verifies that each tag still resolves to the expected commit before building.
