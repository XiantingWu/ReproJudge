# ReproJudge 0.3 release-candidate readiness

The public repository launch is complete. This document defines the source and release-candidate requirements for the public 0.3 beta surface. It is deliberately stricter than “tests pass” and separates benchmark content, evaluator mechanics, compatibility attestation, packaging, repository controls, and publication state. Live GitHub settings are external mutable state and must be verified through the repository control plane; this document defines the required state but is not proof of the current state.

## Engineering and benchmark gates

A final candidate must demonstrate on the exact source identity:

- complete deterministic unit/regression suite green;
- task/result/telemetry public JSON Schemas valid and round-trip tested;
- launch-surface/source checks green;
- **15-case revision-pinned real-paper repository-discovery shard validates exactly**, including manifest/filesystem equality, unique task/paper/repository identities, pinned evidence URLs, task hashes and deterministic shard hash;
- drift-sensitive canonical repository golds are regression-locked so upstream rename/casing changes cannot silently leave a stale exact-string oracle;
- four-case deterministic evaluator reference suite green on the same source;
- symlink/path, finite-JSON, log/scorer/hash, regex-timeout, hidden-gold, historical-result and descendant-cleanup regressions green;
- fingerprint-verified standalone export contains and validates the same scientific inputs;
- wheel and sdist built from that export, Twine-clean and installable in a fresh venv;
- CLI and module entry points green;
- Repo1/VeriRepro compatibility evidence is documented as deferred to a future release and no pinned external attestation is claimed.

The 15 scientific cases are real benchmark content but measure repository discovery only. They are not counted as complete paper reproductions.

## Trusted execution model

ReproJudge 0.3 uses **no GitHub Actions workflows**. All engineering and release gates run locally under the maintainer's control; there is no hosted CI, no scheduled drift, and no hosted release audit by design.

Formal release measurement:

```text
repository: XiantingWu/ReproJudge
runner environment: github-hosted (when measured on hosted compute)
mode: github-actions-hosted (recorded provenance from the hosted measurement lane)
platform: macOS ARM64
evidence Python: 3.11.9
```

The core release-authority lane uses only `reprojudge doctor --strict`. `reprojudge doctor --strict --require-docker` is validated separately when a Docker daemon is available.

The 0.3 authority chain has no dependency on GitHub Actions artifact upload/download storage.

Repo1/VeriRepro compatibility evidence is deferred to a future release. 0.3 makes no pinned external compatibility attestation claim and vendors no external repository evidence, so no credentialed dependency on another repository exists.

Changing the release-authority measurement lane or reintroducing a pinned external compatibility attestation is release-relevant and requires review plus fresh ReproJudge measurement.

## Release-evidence gates

The standalone measurement must produce candidate `benchmarks/release-evidence-0.3.0.json` bytes using release-evidence schema v4 and containing:

- exact ReproJudge source fingerprint;
- scientific-seed manifest/shard hashes, pinned curation-source blob and all 15 task/paper/repository identities;
- fresh reference task/result/suite/reference-agent hashes from the same candidate source;
- exact ReproJudge repository/platform/Python provenance;
- exact measured standalone candidate-head SHA;
- exact narrow claim scope with arbitrary-paper reproducibility and scientific correctness explicitly false.

Before promotion, the candidate is temporarily injected and both:

```bash
python3 scripts/release_check.py --require-release-evidence
python3 scripts/release_source_check.py --require-release-evidence
```

must pass. Promotion verifies the candidate digest before committing. After promotion, the exact committed-evidence head must pass those two gates plus the complete standalone engineering/package gate again. Any covered source or benchmark change invalidates evidence and requires remeasurement.

After a normal merge into `main`, exact-`main` validation must pass. The release tag is not allowed to name an older validated ancestor: the release tag must equal current `main`. `main` must remain frozen from final exact-main validation through publication; otherwise publishing fails closed and a new exact-main release decision is required.

## Live GitHub control-plane requirements

The canonical repository `XiantingWu/ReproJudge` is public. The following requirements describe live control-plane state and must be read back from GitHub, not inferred from this file:

- repository metadata/topics describe the actual bounded benchmark scope;
- normal merge commits are the only enabled merge method for the evidence-preserving launch path;
- `main` protection requires appropriate review for future changes;
- private vulnerability reporting is enabled;
- no GitHub Actions workflows exist; no runner infrastructure is used;
- unauthenticated clone/install/demo/scientific-shard smoke succeeds while the repository is public;
- no private Papers ancestry or internal-only files are present.

These are repository/account controls. They must not be marked complete merely because source files describe them or because this checklist contains a completed-looking entry.

## PyPI control-plane gates

Before announcing a package release:

- confirm the `reprojudge` project ownership/availability;
- create `v0.3.0` only from the exact validated current `main` commit while `main` is frozen;
- build the wheel/sdist from the fingerprint-checked standalone export, record their SHA-256 digests, and publish those exact files manually with Twine;
- install the actually published wheel in a fresh environment and run `pip check`, CLI/module version smoke and `doctor --strict`.

No long-lived PyPI password/token is stored as a repository secret. No GitHub Actions publishing workflow exists by design; publication is a maintainer manual step.

## Claim boundary

Passing these gates supports the claim that ReproJudge 0.3 is a mature, evidence-bound benchmark/evaluator release candidate with a first real 15-case scientific repository-discovery shard. It does **not** prove those 15 papers were reproduced, arbitrary papers are reproducible, deferred external compatibility evidence is current attestation, the two discovery cases generalize to all agents, scientific correctness, or independent third-party certification.
