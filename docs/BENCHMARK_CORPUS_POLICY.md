# Benchmark corpus policy

This document defines how benchmark corpora are accepted, pinned, and maintained in ReproJudge.

## Scope

ReproJudge currently ships two deterministic corpora:

- the **reference suite** (`benchmarks/reference-suite.json`, four cases) — deterministic evaluator mechanics only;
- the **executable baseline** (`benchmarks/executable-baseline/`, three cases) — network-free subprocess mechanics through the real agent boundary;
- the **scientific discovery seed** (`benchmarks/scientific-seed/`, 15 cases) — revision-pinned paper-to-canonical-repository discovery only.

## Corpus acceptance

A new corpus or a new case is accepted only when all of the following hold:

1. **Explicit scope**: the task states exactly which stage it measures and which stages it does not.
2. **Deterministic oracle**: every check is a deterministic scorer with bounded inputs; no model-as-oracle.
3. **Revision pinning**: papers are pinned to arXiv revisions; repositories to canonical owner/name spellings; any external byte input is pinned by SHA-256.
4. **Provenance**: the corpus records where the curation source came from and how gold values were constructed, without claiming provenance that does not exist.
5. **Licensing**: fixtures and vendored bytes are redistributable under terms compatible with this repository's license, and attribution is recorded.
6. **Failure paths**: positive and failure-path fixtures exist.
7. **Claim boundary**: non-claims are documented (e.g. "not a reproduction claim").

## Provenance and hidden gold

- Evaluator `checks` and gold values are never copied into the generated agent-visible request.
- A corpus must not depend on sibling repository code at runtime; cross-project inputs enter only as pinned, source-controlled bytes.
- Hostile-agent isolation (hidden gold) is an evaluation-environment concern, not a repository concern: see [TRUST_MODEL.md](TRUST_MODEL.md).

## Canonical repository pinning and drift

- Canonical GitHub repository spellings are curated release inputs.
- The maintainer runs `scripts/check_scientific_canonical_drift.py` to check each canonical repository for rename, transfer, 404, or archive drift.
- Drift detection **fails and reports**; it never silently rewrites gold.
- A gold refresh is a release-relevant change: the affected canonical bytes must be updated deliberately, and release evidence must be remeasured in a fresh cycle. Redirected historical URLs are not canonical merely because GitHub still resolves them.

## Semantic versioning and deprecation

- Corpus meaning follows the task/result schema version. Reinterpreting an existing task field requires a new schema version and migration documentation.
- Deprecating or replacing a corpus is a release-relevant decision: it must be announced in the changelog, and old evidence must not be relabeled against new corpus identity.
- Evidence from a different corpus identity is never relabeled or copied into a new release claim; it is either re-measured under the new identity or deferred.

## Release evidence binding

Formal release evidence binds the exact corpus bytes (manifest and task hashes), the deterministic reference-suite results, and the measurement provenance. Any corpus byte change invalidates previously promoted evidence and requires a fresh measurement cycle.