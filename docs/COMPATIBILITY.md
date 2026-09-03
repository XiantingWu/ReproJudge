# Compatibility policy

## Stable v1 task core

ReproJudge 0.3 preserves the integer `schema_version: 1` core published before 0.3:

- `task_id`
- `domain`
- `paper`
- `expected_artifacts`

`expected_artifacts: []` remains valid, and the release audit exercises the zero-artifact contract through the deterministic reference suite.

## External cross-repository compatibility (deferred)

Earlier development releases carried a pinned Repo1/VeriRepro 0.8 compatibility attestation: vendored canonical v1 task bytes, a compatibility lock, and a recorded two-case integration result set. That evidence was bound to a former private repository identity and its internal provenance.

Under the current public identity, that compatibility claim is **deferred to a future release**. It is deliberately not re-issued by relabeling the old attestation bytes, renaming the source repository, or copying historical run provenance into the new repository. Re-establishing the claim requires a fresh, formally measured compatibility cycle under the public repository identity — new canonical source authority, re-verified task bytes, and newly recorded evidence.

The public release therefore makes **no cross-repository compatibility claim** for 0.3.0. The v1 task contract itself remains source-compatible with tasks written against the canonical v1 seed contract, as verified by the reference suite and schema tests; that is a statement about the parser, not an attestation of an external project's results.

## Additive 0.3 task features

ReproJudge adds optional bounded fields such as `title`, `instructions`, `tags`, `timeout_seconds`, `metadata`, and evaluator `checks`. Unknown task/check fields fail closed so typos do not silently change benchmark meaning.

## Result compatibility

Result schema version remains integer `1`. 0.3 adds fields such as evaluator/request fingerprints, failure taxonomy, telemetry and log truncation flags. Existing v1 fields retain their prior meaning. Consumers should ignore unknown additive result fields.

## Agent process contract

The environment-variable boundary is stable for 0.x. `REPROJUDGE_TASK_MANIFEST` points to an agent-visible projection of the task; evaluator `checks` are deliberately omitted. This is a fairness hardening and does not alter the required v1 core fields the agent sees.

## Evidence compatibility

The task/result schemas are long-lived interoperability contracts. Release evidence is intentionally stricter: 0.3 evidence is accepted only when its exact field shape, source fingerprint, reference-suite identity, measurement provenance, and narrow claim scope all match the release checker. Extra fields are rejected so a promoted evidence document cannot quietly add stronger claims.

## Breaking changes

A future change that reinterprets an existing v1 task field, scorer meaning, or result core field requires an explicit new schema version and migration documentation. Package-version changes alone must not silently reinterpret old evidence.