# Evidence model

ReproJudge distinguishes **run evidence**, **scientific-shard identity**, **reference-suite evidence**, and **release evidence**.

## Run evidence

Each run records:

- an agent-visible request projection in `request.json` with evaluator `checks` omitted;
- deterministic SHA-256 fingerprints for both the full evaluator task and the projected request;
- exact agent argv;
- start time and duration;
- exit/timeout/launch status and evaluator-derived failure taxonomy;
- bounded stdout/stderr with truncation flags;
- declared artifact sizes and SHA-256 hashes, with PASS refused when required bounded provenance cannot be recorded;
- deterministic evaluator check outcomes;
- evaluator version/platform;
- optional bounded telemetry.

The full evaluator task remains the authority for scoring even though the generated agent request does not expose its `checks` array.

## Scientific-shard identity

`benchmarks/scientific-seed/` contains 15 real-paper repository-discovery tasks curated from the revision-pinned arXiv real-paper corpus used for 0.3. This is benchmark content rather than release-fixture output.

`scripts/validate_scientific_seed.py` fails closed unless:

- the manifest lists exactly the 15 task files actually present;
- all task/paper/repository identities are unique;
- every arXiv identifier includes an explicit revision;
- every evidence URL points to that exact revision;
- every task emits only `discovery.json` and has exactly one `json_equals` check on `repository_url`;
- repository gold values are canonical HTTPS GitHub repository URLs;
- shard/scope/provenance metadata remains fixed.

It emits the manifest SHA-256, the pinned curation-source blob SHA, every task fingerprint/paper/repository target, and a deterministic aggregate shard SHA-256. These bytes are part of the ReproJudge release-source fingerprint; final release evidence repeats their identity so a reviewer can inspect exactly which real benchmark content belongs to 0.3.

This shard measures **paper-to-canonical-public-repository discovery only**. Its 15 cases must never be described as 15 full paper reproductions.

## Reference-suite evidence

`benchmarks/reference-suite.json` contains four deterministic evaluator cases. `scripts/run_reference_suite.py` runs them on the exact candidate source and emits a manifest containing:

- suite hash;
- reference-agent hash;
- release-source fingerprint;
- each task/result hash;
- case status;
- aggregate summary;
- measurement provenance when available.

This measures evaluator mechanics and packaging behavior, not broad scientific-agent quality.

## External compatibility attestation (deferred)

0.3 makes no pinned external compatibility attestation claim. Repo1/VeriRepro compatibility evidence is deferred to a future release: no external repository's recorded runs, task bytes, run IDs, or result hashes are vendored into the 0.3 source or repeated in its release evidence. Reintroducing such an attestation requires explicit source-controlled evidence and a complete fresh ReproJudge measurement cycle.

## Release measurement and provenance

ReproJudge 0.3 uses no GitHub Actions workflows. All gates run locally; release evidence is produced by the standalone measurement process.

Formal release measurement:

- repository: `XiantingWu/ReproJudge`;
- runner environment: `github-hosted` (when measured on hosted compute);
- mode: `github-actions-hosted` (recorded provenance from the hosted measurement lane);
- platform: macOS ARM64;
- evidence Python: 3.11.9.

## Release evidence promotion

After the standalone audit passes, `scripts/build_release_evidence.py` constructs a sanitized version-matched record from:

- the exact current ReproJudge release-source fingerprint;
- the validated 15-case scientific shard;
- fresh four-case reference evidence from the same source;
- the current measurement provenance;
- explicit narrow non-claims.

Release-evidence schema **v4** records the measurement provenance — repository, platform and Python — and binds the release to the measured source identity through the **release source authority identity** (`source_tree_sha256`) and the **portable byte identity** (`source_fingerprint`) fields, rather than accepting caller-supplied authority labels. The two names are fixed public terminology defined in [SOURCE_IDENTITY.md](SOURCE_IDENTITY.md); the authority identity is the formal release fingerprint, the portable byte identity is the exec-normalized cross-platform byte-equivalence fingerprint.

The measurement process writes a candidate evidence record and proves both:

```bash
python3 scripts/release_check.py --require-release-evidence
python3 scripts/release_source_check.py --require-release-evidence
```

accept that candidate before promotion. A maintainer verifies the SHA-256 digest of the candidate bytes before committing them.

The promoted record contains:

- exact ReproJudge release-source fingerprint;
- scientific-seed manifest/shard hashes, pinned curation-source blob and all 15 task identities;
- four reference task/result hashes plus suite/reference-agent/manifest hashes;
- exact ReproJudge repository/platform/Python provenance and the measured candidate-head identity;
- exact narrow claim scope, including explicit false flags for arbitrary-paper reproducibility and scientific-correctness proof.

The promoted file is stored as `benchmarks/release-evidence-<version>.json`. Only that strictly versioned promotion record is excluded from source fingerprint input to avoid self-reference. All scientific tasks, tests, schemas, scripts, examples and public documentation remain source-bound.

After promotion, the exact final head must run the complete audit again. Because the evidence file is then present from checkout, the evidence-required gates validate committed evidence through both semantic and independent source/provenance gates before generating a fresh diagnostic candidate. Any covered source change after measurement invalidates the promoted evidence and requires remeasurement.

## Non-claims

Release material must not turn:

- 15 real discovery tasks into “15 reproduced papers”;
- four deterministic evaluator cases into “four reproduced papers”;
- a deferred external compatibility claim into current 0.3 attestation;
- exact hashes into semantic scientific equivalence;
- maintainer-operated release evidence into independent third-party certification;
- operator overrides into autonomous agent success.
