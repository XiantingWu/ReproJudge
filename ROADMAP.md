# ReproJudge roadmap

The roadmap distinguishes **release blockers** from later benchmark expansion.

## 0.3 mature public beta

Release-blocking engineering and benchmark content:

- versioned task/result contracts;
- bounded, fail-closed evaluator inputs;
- deterministic JSON/text/hash scorers;
- process failure taxonomy and timeout/post-exit cleanup;
- artifact hashes and task/source fingerprints;
- optional bounded agent/model/cost/token/intervention telemetry;
- summaries and leaderboard export;
- **15-case revision-pinned real-paper repository-discovery shard** with deterministic corpus identity;
- deterministic four-case evaluator reference suite;
- compatibility with the canonical v1 task contract published before 0.3;
- Repo1 compatibility evidence deferred to a future release;
- version-matched release evidence binding scientific shard, reference suite, release-source bytes and measurement provenance;
- fingerprint-preserving standalone extraction plus wheel/sdist/Twine/clean-install validation;
- security/contribution/conduct/citation docs;
- manual PyPI publication from tested evidence-bound distributions.

The scientific seed intentionally measures only paper-to-canonical-public-repository discovery. It is real benchmark content, but it is not a claim of environment construction, experiment execution, numerical reproduction, or scientific correctness.

Repo1 compatibility evidence is deferred to a future release and is not claimed in 0.3. The 0.3 release makes no pinned external compatibility attestation claim.

## Post-0.3

These are valuable extensions, not reasons to keep the first mature release private:

- broaden the curated discovery corpus with independent domain owners and explicit provenance review;
- add environment-construction and experiment-execution shards with domain-appropriate deterministic gold;
- add numerical-agreement shards with scientifically justified metrics/tolerances;
- container/remote-worker adapter protocol as a first-class plugin interface;
- richer tabular/image/domain-specific deterministic scorers;
- signed dataset/task registries;
- richer standardized agent telemetry adapters;
- leaderboard website/static export with published evaluation-policy metadata;
- benchmark shard scheduling and resumable distributed execution;
- cryptographic attestations for remote evaluation workers;
- independently maintained third-party agent adapters.

Every future benchmark expansion should preserve historical contracts, version new semantics explicitly, and keep evaluator authority separate from agent claims.
