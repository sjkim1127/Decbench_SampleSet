# Corpus release pinning policy

DecBench candidate validation should prefer published stable releases over moving branch heads or arbitrary latest commits.

For each validated target, record:

- stable release/tag name,
- exact commit SHA resolved from that tag at validation time,
- compiler/toolchain version,
- architecture and optimization profile,
- build and oracle artifacts used for measurement.

Prereleases should be avoided unless a specific experiment requires them. If no suitable stable release exists, pin an exact commit and document the exception.

Historical exploratory CI results may remain attached to commit pins, but final corpus proposals should be migrated to stable release pins where practical.
