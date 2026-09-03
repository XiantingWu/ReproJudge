# Changelog

Notable user-facing changes are recorded here.

## [Unreleased]

### 0.3.0 release candidate

- publish under the canonical public identity **XiantingWu/ReproJudge** with a fresh, clean Git history and the XiantingWu account as the sole release authority;
- keep the repository **workflow-free by design**: no GitHub Actions CI, CodeQL, dependency-review, canonical-drift, trusted-release-audit, or publish workflows exist; every quality gate runs locally under the maintainer's control;
- upgrade release evidence to **schema v4** with a `source_fingerprint` identity field;
- remove the previous persistent-runner era from the public surface: no persistent runners, no personal hosts, no draft runner labels appear anywhere in the repository;
- **The Repo1/VeriRepro 0.8 compatibility attestation is deferred to a future release** rather than relabeling stale provenance; the vendored attestation, compatibility lock, and canonical task bytes are removed from the public claim;
- add a fail-closed **public identity hygiene gate** (`scripts/check_public_identity_hygiene.py`) that rejects any occurrence of the former private identity, personal hosts/paths, draft runner names, or internal run identifiers in the public tree, plus a reachable-Git-history hygiene gate;
- add `scripts/validate_sdist.py` for sdist contents integrity, `scripts/check_scientific_canonical_drift.py` for canonical benchmark drift checks, and `scripts/verify_release_dependency_lock.py` with a committed `--require-hashes` transitive dependency lock for the release authority platform;
- adopt **PEP 639** license metadata (`license = "MIT"`, `license-files = ["LICENSE"]`) and remove the deprecated license classifier;
- require both wheel and sdist clean-install smoke gates locally;
- add `GOVERNANCE.md`, `SUPPORT.md`, and `docs/BENCHMARK_CORPUS_POLICY.md`, and refresh contributor/trust-model/source-identity documentation for the workflow-free architecture.

- add a **15-case revision-pinned real-paper repository-discovery benchmark shard** curated from the revision-pinned arXiv corpus, with exact manifest/filesystem validation, per-task hashes, a deterministic shard hash, and explicit discovery-only claim scope;
- refresh ALBERT and CLIP discovery golds to GitHub's current canonical owner/repository spellings, regression-lock those drift-sensitive targets alongside JAX-MD, and require a fresh release measurement whenever canonical oracle bytes change;
- add branch-aware release coverage with separately enforced **90% statement / 85% branch** thresholds over the complete `reprojudge` package, backed by a fail-closed coverage-JSON validator rather than one blended percentage;
- add pinned Hypothesis property tests for schema/scoring invariants, including JSON round trips, deterministic repeated scoring, serialization invariance, monotonic numeric tolerance, undeclared-evidence invariance, and deterministic leaderboard tie-breaking;
- add adversarial evaluator tests for invalid UTF-8 logs, bounded stderr, malformed/non-finite JSON artifacts, missing JSON paths, wrong hashes, duplicate declared artifacts, environment leakage, working-directory evidence confusion, and SIGTERM-resistant timeout escalation;
- reject non-UTF-8 programmatic task text (including lone Unicode surrogates) at schema-validation time instead of failing later while writing the agent request;
- add pinned Ruff and mypy quality gates to the local Python 3.11 quality lane;
- add a three-case, network-free **executable subprocess baseline** (mean, least-squares line fit, SHA-256) that runs through the real agent request/process/artifact/scoring boundary from both source and standalone export, while keeping it explicitly separate from the 15-case discovery-only scientific seed and making no arbitrary-paper/scientific-correctness claim;
- refresh the JAX-MD discovery gold to its current canonical `https://github.com/jax-md/jax-md` location after the historical `google/jax-md` URL began redirecting, and regression-pin that canonical target;
- make release-source identity fail closed over the standalone tree: covered files bind repository-relative path, normalized Git executable semantics, size, and exact bytes; only narrow generated/local state plus the strictly versioned promoted evidence record are excluded;
- make top-level `build/` and `dist/` exclusions location-aware so nested source directories with the same names remain fingerprinted and exported; add regressions for unknown root files, executable-mode changes, and nested build/dist source;
- normalize repository file modes so ordinary source/data/docs/tests use `100644`, with a repository-level hygiene regression that prevents executable-bit drift;
- bind reference-suite provenance to the exact measured PR/source head rather than GitHub's synthetic pull-request merge SHA;
- pin the direct release/test toolchain (`pip`, `hatchling`, `build`, `coverage`, `pytest-cov`, `hypothesis`, `jsonschema`, `pytest`, `ruff`, `mypy`, and `twine`) and use non-isolated package builds after those tools are installed, while explicitly not claiming a fully hermetic transitive/OS build environment;
- require both GitHub Release verification and OIDC publication jobs to prove the release tag resolves to the exact current `origin/main` commit, not merely any historical ancestor, and fail closed if `main` advances;
- add deterministic release-source and task fingerprints;
- retain task/result schema v1 compatibility with the canonical v1 task contract published before 0.3;
- add bounded agent identity/model/provider/token/cost/intervention telemetry that never grants scientific PASS authority;
- canonicalize new telemetry so optional scalar keys are omitted rather than serialized as null, reject control-character display metadata, and neutralize Markdown-table plus spreadsheet-formula injection in leaderboard exports without breaking historical v1 result ingestion;
- add text containment, regex, and SHA-256 scorers alongside JSON equality/numeric tolerance and artifact existence;
- bound scorer inputs, result loading, logs, telemetry, artifact hashing, aggregate argv, and check diagnostics so the evaluator cannot emit a current `result.json` that exceeds its own 4 MiB ingestion contract;
- refuse symlinked scored artifacts and harden POSIX timeout plus normal-exit descendant cleanup;
- record evaluator version, full-task/request fingerprints, telemetry, failure taxonomy, and log truncation state in result bundles without reinterpreting historical v1 core semantics;
- add leaderboard JSON/Markdown/CSV aggregation by agent/version with finite/status-consistent fail-closed historical result validation;
- add `python -m reprojudge`, `fingerprint`, `leaderboard`, strict readiness, and a non-destructive `reprojudge init` starter generator for one-command benchmark onboarding;
- add benchmark-authoring, external-agent integration and FAQ documentation that preserve the evaluator/private-check and non-sandbox boundaries;
- add a four-case deterministic release reference suite with source-bound manifest evidence;
- keep evaluator `checks` out of the generated agent-visible request and bind full task/request projections to separate SHA-256 fingerprints;
- make programmatic task construction obey the same finite canonical-JSON and size limits as file-loaded manifests, rejecting unknown task/check fields rather than silently dropping them;
- reject scorer-inapplicable check fields per check type instead of accepting and silently discarding known fields from another scorer;
- align the public task JSON Schema's artifact-path and bounded-string contracts with runtime rejection of unsafe paths, pure-whitespace required text, NUL-bearing strings, invalid metadata keys and multiline traversal tricks, with positive/negative schema regressions;
- tighten the public result schema around current command/artifact/check bounds, status/pass consistency and structured telemetry while retaining bounded historical v1 telemetry compatibility and top-level additive-field compatibility;
- evaluate regex scorers in an isolated child interpreter with a hard timeout and reject every symlink component in artifact paths;
- fail closed when a declared artifact exists but cannot receive bounded SHA-256 evidence;
- expand release-source identity to tests, all benchmark manifests/tasks, schemas, docs and public release files;
- exclude only strictly versioned `benchmarks/release-evidence-X.Y.Z.json` promotion records from the source fingerprint, while similarly prefixed benchmark files remain source-bound;
- make the independent release-source gate validate promoted evidence version, source fingerprint, exact standalone authority identity/platform and narrow public claim boundary;
- formal 0.3 measurement uses the standalone release process with regression tests rejecting wrong authorities, wrong platforms and unsupported Python versions;
- drop GitHub Actions artifact upload/download as release dependencies; candidate evidence is verified byte-exact by digest and promoted only after digest verification;
- publish manually from the tested evidence-bound distributions with Twine; the publisher does not rebuild;
- require both the semantic release-evidence gate and the independent source-evidence gate before PyPI publication;
- publish Draft 2020-12 task/result/telemetry JSON Schemas and regression-test runtime/schema round trips;
- add fingerprint-preserving symlink-free standalone export validation and build release wheels from the exported tree;
- require the 15-case scientific shard to validate in the local gates, the exported tree and the exact-source gate;
- strengthen public-surface validation for canonical URLs, private security advisory routing, CITATION identity, local Markdown links, workflow-free surface, adoption/onboarding docs, Dependabot, and release permissions;
- consolidate duplicate bug/feature issue forms into one security-aware bug report and one trust/compatibility-aware feature request, and strengthen the PR template around evaluator authority and release-evidence lifecycle;
- generate strict version-matched release evidence binding scientific-shard identity, deterministic reference evidence, exact standalone measurement provenance and exact narrow non-claims.

## 0.2.0 — functional public-beta core

- add versioned task schema and registry;
- add subprocess agent boundary, timeout, minimal environment, logs, artifacts, hashes, deterministic JSON scorers, summaries, CLI, and release artifact checks;
- add path/symlink/non-finite input hardening;
- align the canonical integer `schema_version: 1` contract with the canonical v1 task contract published before 0.3, including valid zero-artifact tasks.

## 0.1.0 — initial core

- initial task schema and validation CLI.
