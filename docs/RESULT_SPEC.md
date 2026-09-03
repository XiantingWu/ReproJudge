# ReproJudge result contract

`result.json` is evaluator-authored evidence. Result schema version remains integer `1`; 0.3 adds backward-compatible fields without reinterpreting the original core.

## Core and 0.3 evidence fields

The result includes process identity/status, exact argv, timing, artifacts, deterministic check outcomes, log paths, Python/platform identity and derived `passed`. 0.3 additionally records:

- `evaluator_version`;
- `task_sha256` — fingerprint of the full evaluator task including private checks;
- `request_sha256` — fingerprint of the agent-visible request projection;
- `stdout_truncated` / `stderr_truncated`;
- `failure_taxonomy`;
- optional bounded `telemetry`.

## Status semantics

- `passed` — agent exited zero, telemetry (if present) was valid, every deterministic check passed, and required artifact evidence could be recorded;
- `failed` — process exited zero but one or more evaluator/evidence checks failed;
- `agent_error` — process returned non-zero;
- `timeout` — evaluator timeout expired and process-group termination was attempted;
- `launch_error` — process could not be started;
- `telemetry_error` — optional telemetry violated its bounded contract.

A process exit of zero is necessary but not sufficient for `passed`.

The machine schema enforces `passed == (status == "passed")`; when `timed_out` is present, it must agree with the `timeout` status.

## Bounded result invariant

A current evaluator must never emit a `result.json` that its own bounded result loader will reject for size.

To keep that invariant:

- command argv is limited to 256 arguments, 16 KiB per argument, and 256 KiB total characters;
- deterministic check diagnostics are capped at 4096 characters;
- JSON mismatch diagnostics use bounded structural representations instead of embedding arbitrarily large observed values;
- current results contain at most 128 artifact evidence records and at most 512 check/evidence records under the v1 task bounds;
- `result.json` is serialized and checked against the same 4 MiB maximum accepted by result ingestion before it is written.

If that final internal size assertion is ever violated, it is treated as an evaluator bug rather than producing evidence that cannot be reloaded.

## Failure taxonomy

`failure_taxonomy` is an additive machine-readable classification derived by evaluator code. Current categories include:

- `launch_error`;
- `timeout`;
- `agent_nonzero_exit`;
- `invalid_telemetry`;
- `artifact_path_violation`;
- `expected_artifact_missing`;
- `artifact_evidence_unrecordable`;
- `evaluator_check_mismatch`;
- `unclassified_evaluation_failure`.

The human-readable check details remain available for diagnosis; taxonomy is intended for aggregation and leaderboard analysis.

## Artifact records

Every present declared artifact that remains inside the output root, contains no symlink path component, and fits the bounded hash policy is recorded with relative path, byte size and SHA-256. If a declared file exists but cannot receive bounded evidence, the run fails closed rather than silently omitting provenance.

## Telemetry

Telemetry is optional and non-authoritative. Supported fields are agent identity/version, model/provider, token usage, model cost and explicit interventions. Cost/token values are agent/adapter-reported unless a higher-level integration independently verifies them. They never override scientific checks.

New evaluator output uses the canonical telemetry projection documented in [`TELEMETRY.md`](TELEMETRY.md), which omits absent optional scalar fields. The result schema deliberately keeps bounded `null` compatibility for older additive v1 telemetry fields so historical evaluator-authored bundles remain machine-readable.

## Machine-readable schema

See [`schemas/result-v1.schema.json`](../schemas/result-v1.schema.json) and [`schemas/agent-telemetry-v1.schema.json`](../schemas/agent-telemetry-v1.schema.json).

The result schema bounds known v1 fields and nested artifact/check/telemetry records while retaining `additionalProperties` at the result top level so future additive v1 evidence fields remain forward-compatible.

## Historical compatibility

Consumers should ignore unknown result fields and rely on explicit schema versions rather than package-version guesses. New additive fields do not change the meaning of historical result schema v1 fields.
