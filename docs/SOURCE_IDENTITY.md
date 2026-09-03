# Release source identity

ReproJudge treats release identity as a property of the complete standalone source tree, not only of the Python package directory.

## Two public identity names

ReproJudge publishes exactly two fingerprints with fixed, non-interchangeable names:

| Public name | Field | Semantics |
| --- | --- | --- |
| **release source authority identity** | `source_tree_sha256` | the formal release/publication authority fingerprint; exec-bit-aware and enforced on the release authority platform (macOS ARM64) |
| **portable byte identity** | `source_fingerprint` | the exec-normalized byte identity used for cross-platform byte equivalence (Windows cannot represent POSIX execute bits) |

Formal release evidence, wheel/sdist metadata binding, and any release-claim statement quote the **release source authority identity** (`source_tree_sha256`). The **portable byte identity** (`source_fingerprint`) exists so Windows lanes can verify byte-for-byte source equality without pretending to represent execute bits; it is never presented as the formal authority.

## What the fingerprint covers

`source_fingerprint()` is fail-closed. Every regular file in the standalone checkout is release-relevant by default, including source, tests, benchmark inputs, schemas, scripts, examples, documentation, root configuration files, and future files that have not yet been assigned to a known category.

For every covered file the fingerprint binds:

- its repository-relative POSIX path;
- normalized Git executable semantics (`100644` or `100755`);
- byte size;
- exact file bytes.

A chmod that changes whether a covered file is executable therefore changes the release source identity even when its bytes do not change.

## Cross-platform byte identity

Windows filesystems cannot represent POSIX execute bits. On Windows lanes the source-identity gates therefore compare the **portable byte identity** (executable semantics normalized away); the release authority platform (macOS ARM64) always enforces the full exec-bit-aware **release source authority identity**. An executable-bit change that is invisible on Windows is still caught on the authority lane and by the repository-level executable-mode hygiene regression.

## Narrow exclusions

Only deliberately local or generated state is excluded:

- top-level `.git/`, `.venv/`, `.reprojudge/`, `build/`, and `dist/`;
- `__pycache__/` and `.pytest_cache/` cache directories;
- `.DS_Store`;
- the exact versioned promoted record `benchmarks/release-evidence-X.Y.Z.json`.

The top-level rule is intentional. A legitimate nested source path such as `src/reprojudge/build/helper.py` or `src/reprojudge/dist/runtime.py` remains covered. Similarly named benchmark/source files are not hidden by prefix matching.

The versioned release-evidence record is excluded only to avoid a self-reference: it records the fingerprint to which it is attached. All inputs that generate or validate that record remain covered.

## Standalone export

`scripts/standalone_export.py` shares the same exclusion policy and copies files with metadata-preserving `copy2`. After export, ReproJudge recomputes the source fingerprint and requires it to match the source checkout. This verifies both bytes and executable semantics across the exported source used for package construction.

## Toolchain boundary

The 0.3 release process pins the exact Python standalone assets and their SHA-256 digests. It also pins the direct release/test tools used by the repository (`pip`, `hatchling`, `build`, `jsonschema`, `pytest`, and `twine`) and builds with `--no-isolation` after those tools are installed.

This is a direct-toolchain pin, not a claim that every transitive package or host operating-system component is a hermetic build input. Release evidence records the measurement platform and Python version so that boundary remains explicit.

## Exact-main publication

PyPI publication is performed manually by the maintainer from the tested wheel/sdist at the exact evidence-bound `main` commit. The release tag must resolve to the **exact current `main` commit**, not merely any historical ancestor, before proceeding.

This prevents an otherwise evidence-bound but stale source state from being published: if `main` advances after a candidate was validated, publication fails closed and the release must be revalidated at the new authority head.

Any change to a covered byte, covered executable mode, benchmark gold, source-identity rule, or direct release-tool pin invalidates previously promoted evidence and requires a fresh candidate measurement and promotion cycle.
