# ReproJudge architecture

## Boundary

ReproJudge owns **benchmark contracts, deterministic scoring, and evidence provenance**. It does not own the agent under test.

```text
scientific/reference task registries
  -> task parser / limits
  -> agent-visible request projection (evaluator checks withheld)
  -> process adapter
  -> isolated run directory
  -> bounded logs + optional telemetry
  -> residual process-group cleanup
  -> artifact collector / hashes
  -> deterministic evaluator-private scorers
  -> result bundle
  -> summary / leaderboard
  -> release evidence
```

The package runtime does not import sibling agent implementations. External agents and systems participate over process/artifact contracts.

## Components

1. **Task contract** (`schema.py`) — stable v1 core plus bounded optional metadata/checks and canonical serialization.
2. **Registry** (`registry.py`) — bounded recursive discovery, symlink refusal, duplicate-ID detection, per-task fingerprints.
3. **Runner** (`runner.py`) — projects an agent-visible request without evaluator checks, executes with `shell=False`, uses a minimal environment by default, captures bounded stdout/stderr, cleans residual same-group POSIX descendants before scoring, escalates timed-out process groups, and isolates run IDs.
4. **Telemetry** (`telemetry.py`) — optional bounded identity/model/cost/token/intervention data with no scoring authority.
5. **Scoring** (`scoring.py`) — artifact existence, JSON equality/numeric tolerance, text containment, time-bounded regex evaluation, and SHA-256.
6. **Evidence** (`evidence.py`) — canonical task/request hashing and deterministic release-source fingerprinting.
7. **Reporting** (`reporting.py`) — bounded, fail-closed result discovery and semantic validation before aggregate run statistics.
8. **Leaderboard** (`leaderboard.py`) — validated agent/version aggregate tables in JSON/Markdown/CSV.
9. **CLI** (`cli.py`) — validation, registry, run/suite, summary, leaderboard, fingerprint, readiness checks.
10. **Scientific shard** (`benchmarks/scientific-seed/`) — 15 revision-pinned real-paper repository-discovery tasks; manifest-level provenance remains evaluator-side, while agent-visible task metadata carries only shard/scope/evidence URL.
11. **Release gates** (`scripts/`) — public surface, scientific-shard identity, source identity, standalone export, reference suite, and version-matched release evidence.

## Benchmark layers

0.3 deliberately keeps three evidence layers separate:

- **scientific seed** — 15 real-paper tasks defining useful discovery benchmark content;
- **reference suite** — four deterministic fixture tasks proving evaluator mechanics;
- **external compatibility attestation** — deferred to a future release; 0.3 claims no pinned attestation against any external repository.

No layer is promoted into a stronger claim than it measures. In particular, the scientific seed validates paper-to-repository discovery, not environment setup, experiment execution, numerical agreement, or scientific correctness. External compatibility attestation is deferred to a future release and is not part of 0.3 claims.

## Result lifecycle

```text
full evaluator manifest
  -> bounded parse + task_sha256
  -> projected request.json (no checks) + request_sha256
  -> agent argv
       | stdout/stderr -> bounded logs
       | descendants   -> same-group cleanup before evidence read
       | artifacts     -> evaluator-private deterministic checks + required hashes
       | telemetry     -> bounded non-authoritative measurements
  -> result.json + failure taxonomy
  -> validated aggregation / release evidence
```

Run directories are never reused. A repeated task gets a fresh `run_id`; prior result bundles remain historical evidence and are revalidated when loaded for summaries or leaderboards.

## Evidence authority

Agent-authored values may be inputs to deterministic checks but never define whether those checks passed. Telemetry is descriptive only. A model-reported “success” or a zero process exit cannot override missing artifacts, unrecordable provenance, or failed checks.

Keeping `checks` out of `request.json` prevents the normal process protocol from directly handing gold values to the agent. Scientific task metadata also avoids exposing the curation-source file path. Process mode is still not a hidden-gold sandbox; a hostile same-host agent may inspect any benchmark files the OS lets it read. Competitive hidden-gold execution therefore needs an isolation boundary that does not mount evaluator manifests/gold.

Same-group descendant cleanup reduces post-exit artifact mutation on POSIX but is not a containment boundary: a hostile child can start a new session or otherwise rely on OS-granted capabilities. Untrusted code requires a sandbox/VM/container policy outside ReproJudge.

## Release-source identity

`source_fingerprint()` hashes release-relevant source, tests, scripts, schemas, docs, examples, all benchmark suite/task/lock bytes, and public metadata. Promoted `benchmarks/release-evidence-*.json` files are excluded so a release record can point at the exact source identity without creating a self-referential hash.

The standalone exporter copies a symlink-free tree and requires the exported source fingerprint to equal the canonical repository source fingerprint before packages are built from the export. The exported scientific shard is revalidated before package construction.

## Independence

`XiantingWu/ReproJudge` is the canonical standalone source. A source checkout or exported tree must build, test, validate benchmark inputs, and run the evaluator without importing implementation code from another project. Cross-project evidence would enter only through explicit, source-controlled contracts; no sibling repository is a runtime dependency.
