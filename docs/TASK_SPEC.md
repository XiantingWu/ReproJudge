# ReproJudge task contract v1

## Required core

```json
{
  "schema_version": 1,
  "task_id": "example",
  "domain": "scientific-ml",
  "paper": "arxiv-or-other-stable-reference",
  "expected_artifacts": ["metrics.json"]
}
```

The core fields intentionally remain compatible with the canonical v1 task contract published before 0.3. `schema_version` may be omitted and defaults to integer `1` for compatibility. String `"1"` is rejected.

`expected_artifacts` may be empty. A zero-artifact task can pass when the process exits successfully and no explicit checks fail.

## Bounds and fail-closed parsing

- task JSON: at most 1 MiB;
- task ID: at most 200 characters and filesystem-safe;
- expected artifacts: at most 128;
- checks: at most 256;
- tags: at most 64;
- metadata keys: at most 128 and metadata canonical JSON at most 128 KiB;
- `json_equals.expected`: finite canonical JSON at most 64 KiB;
- timeout: greater than zero and at most 86400 seconds;
- artifact paths: relative, no `..`, no empty/current-directory components;
- unknown top-level task fields and unknown check fields are rejected in 0.3 rather than silently discarded.

Programmatic callers are subject to the same JSON/finite-value requirements as file-loaded manifests. NaN, Infinity, Python-only objects, NUL-bearing strings, and oversized values fail validation.

Task manifests must be ordinary files and not symlinks.

## Optional fields

- `title`
- `instructions`
- `tags`
- `timeout_seconds`
- `metadata`
- `checks`

Agent-specific execution settings should generally live behind the process adapter/operator boundary instead of changing evaluator semantics.

## Evaluator-private checks

`checks` are evaluator authority, not agent instructions. ReproJudge writes a generated **agent-visible** `request.json` that omits the `checks` array. The full evaluator task remains fingerprinted as `task_sha256`; the projected request is independently fingerprinted as `request_sha256`.

This prevents the normal process protocol from directly disclosing expected JSON values, numeric targets, regexes, or expected file hashes. It is not a secrecy sandbox: process-mode agents still have the caller's filesystem permissions. For hidden-gold competitive evaluation, run the agent in an OS/container/VM boundary that does not mount evaluator manifests or gold files.

`expected_artifacts` remain agent-visible because they are part of the output contract.

## Check types

### `artifact_exists`

```json
{"type":"artifact_exists","artifact":"result.csv"}
```

### `json_equals`

```json
{
  "type":"json_equals",
  "artifact":"metrics.json",
  "json_path":"status",
  "expected":"ok"
}
```

### `json_numeric`

```json
{
  "type":"json_numeric",
  "artifact":"metrics.json",
  "json_path":"accuracy",
  "target":0.91,
  "abs_tol":0.01,
  "rel_tol":0.0
}
```

Observed and target values must be finite.

### `text_contains`

```json
{"type":"text_contains","artifact":"report.txt","contains":"completed"}
```

### `text_regex`

```json
{"type":"text_regex","artifact":"report.txt","pattern":"seed=[0-9]+"}
```

Regex uses Python `re` syntax, but evaluation occurs in a separate isolated Python child with a hard wall-clock timeout. A pathological regex therefore fails its check instead of hanging the evaluator indefinitely. Text scorer input is also byte-bounded.

### `file_sha256`

```json
{
  "type":"file_sha256",
  "artifact":"model.bin",
  "sha256":"<64 lowercase hex characters>"
}
```

This proves byte identity only.

## Implicit existence and evidence recording

Every declared expected artifact without an explicit check receives an implicit `artifact_exists` check. In addition, every present declared artifact must fit the evaluator's bounded evidence-hash policy so its size and SHA-256 can be recorded. A file that exists but cannot be safely hashed does **not** produce a passing run with missing provenance; it creates `artifact_evidence_unrecordable` failure evidence.

## Machine-readable schema

The normative public JSON Schema companion is [`schemas/task-v1.schema.json`](../schemas/task-v1.schema.json). Runtime validation remains implemented in the zero-dependency Python parser and is stricter about safe relative paths and finite serialized bounds than JSON Schema alone can conveniently express.

## Schema evolution

A package release may add result fields or additive tooling without changing the meaning of existing v1 task fields. A change that would reinterpret historical v1 tasks requires a new task schema version.
