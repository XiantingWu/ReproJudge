# Contributing to ReproJudge

ReproJudge is evaluator infrastructure. Changes must preserve deterministic evidence semantics and must not give the evaluated agent authority over its own score.

## Development setup

The commands below use `python3` on macOS/Linux. On Windows, use `py -3` instead.

```bash
python3 -m pip install -e '.[dev]'
pytest -q
python3 scripts/check_public_identity_hygiene.py
python3 scripts/launch_surface_check.py
python3 scripts/release_check.py
python3 scripts/run_reference_suite.py --output .reprojudge/reference
```

For a user-facing smoke path:

```bash
reprojudge init /tmp/reprojudge-starter
reprojudge run /tmp/reprojudge-starter/tasks/hello-reprojudge.json \
  --output /tmp/reprojudge-runs -- python3 /tmp/reprojudge-starter/agent.py
```

## Required properties

A change to task/result/scoring/runtime behavior should include:

1. a regression test for the intended path;
2. at least one failure-path test;
3. bounded input/work semantics where untrusted data is introduced;
4. documentation for contract changes;
5. an explicit schema-version decision when historical interpretation would change.

Do not:

- import implementation code from another evaluated agent project;
- use model output as evaluator PASS/FAIL authority;
- use `shell=True` execution;
- silently inherit the caller environment;
- add an unbounded parser/log/artifact traversal;
- weaken release evidence checks to make CI green;
- introduce the former private identity, personal host/path names, or internal runner identifiers anywhere in the public tree.

## Pull requests

Before requesting review:

```bash
pytest -q
reprojudge doctor
python3 scripts/check_public_identity_hygiene.py
python3 scripts/launch_surface_check.py
python3 scripts/validate_scientific_seed.py
python3 scripts/release_check.py
python3 scripts/release_source_check.py
python3 -m build
python3 -m twine check dist/*
```

This repository uses **no GitHub Actions workflows** by design. All quality gates run locally under the maintainer's control, including the full test suite, coverage/ruff/mypy gates, and clean-wheel/sdist installs.

### Untrusted PR and automation policy

No CI or release workflow exists in this repository, so no pull request or automation path can execute hosted jobs. Do not ask contributors to add secrets, grant runner access, or configure any workflow infrastructure. The repository does not register or permit persistent or personal runners.

## Benchmark additions

A benchmark task should state exactly what its deterministic checks establish. Prefer immutable external references/checksums for release-gated cases. If an operator must provide a repository, command, network permission, or other override, record that as an intervention rather than presenting it as autonomous success.

For a new benchmark shard, include:

- an explicit scope statement and non-claims;
- revision-pinned paper/source identities where possible;
- the public evidence used to construct expected values;
- deterministic oracle/check semantics;
- licensing/redistribution notes for fixtures;
- positive and failure-path fixtures;
- a versioning decision when task meaning changes.

Repository-discovery gold values must be checked for current canonical ownership/location before a release measurement. Redirected historical GitHub URLs are not treated as canonical merely because GitHub still resolves them.

See [docs/AUTHORING.md](docs/AUTHORING.md) for the complete authoring guide and [docs/BENCHMARK_CORPUS_POLICY.md](docs/BENCHMARK_CORPUS_POLICY.md) for corpus governance.

## Agent adapters

Adapters should consume the generated agent-visible request and write only the declared outputs. They must not depend on evaluator-private `checks` or reinterpret their own confidence/telemetry as PASS authority.

See [docs/INTEGRATING_AGENTS.md](docs/INTEGRATING_AGENTS.md).

## Release-source identity

Release identity is fail-closed over the standalone tree. Covered regular files contribute their relative path, normalized Git executable mode (`100644` or `100755`), size, and exact bytes. Future root configuration files therefore become release-relevant automatically rather than requiring an allowlist update.

Only narrow generated/local paths and the exact versioned promoted evidence record are excluded. Top-level generated `build/` and `dist/` are excluded, but nested source directories with those names remain covered. See [docs/SOURCE_IDENTITY.md](docs/SOURCE_IDENTITY.md) for the complete policy.

If a covered byte or executable mode changes after release evidence has been promoted, the old evidence is stale by design. Direct release/test tool pins are also source-bound.

The correct lifecycle is:

1. make the source change and remove stale promoted evidence;
2. obtain a successful exact-source trusted candidate measurement;
3. verify the emitted candidate bytes and SHA-256;
4. promote those exact bytes;
5. re-run the complete trusted audit on the committed-evidence head.

Never edit a promoted evidence record to make a new source fingerprint appear valid.

## Compatibility

The v1 core fields intentionally remain compatible with the canonical v1 task contract published before 0.3. Breaking that compatibility requires a new task schema rather than silent reinterpretation. External cross-repository compatibility attestation is deferred to a future release until it can be formally re-established under the current public identity.