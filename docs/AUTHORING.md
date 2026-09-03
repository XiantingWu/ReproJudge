# Authoring ReproJudge tasks

ReproJudge tasks are evaluator-owned contracts. They describe what an external agent must produce and which deterministic checks decide the benchmark result.

The fastest way to start is:

```bash
reprojudge init my-benchmark
cd my-benchmark
reprojudge validate tasks/hello-reprojudge.json
reprojudge run tasks/hello-reprojudge.json --output runs -- python3 agent.py
```

The generated starter is deliberately synthetic. Replace it with a task whose evidence authority you can defend.

## The benchmark-author rule

A useful ReproJudge task answers four questions explicitly:

1. **What is the bounded task?** Keep the stage narrower than the claim you intend to measure.
2. **What may the agent see?** Instructions, input identity and required artifact names belong in the agent-visible request.
3. **What decides PASS?** Deterministic evaluator `checks` belong to the evaluator task and are omitted from the normal agent-visible request.
4. **What evidence remains after the run?** ReproJudge preserves result metadata, logs, artifacts, hashes and optional telemetry.

Do not make a broad scientific claim from a narrow task. A repository-discovery benchmark does not establish experiment reproduction, and an exit code of zero does not establish scientific equivalence.

## Minimal task

```json
{
  "schema_version": 1,
  "task_id": "my-task-v1",
  "domain": "scientific-reproducibility",
  "paper": "2308.04073v1",
  "expected_artifacts": ["answer.json"],
  "checks": [
    {
      "type": "json_equals",
      "artifact": "answer.json",
      "json_path": "status",
      "expected": "ok"
    }
  ],
  "timeout_seconds": 120
}
```

Validate before running:

```bash
reprojudge validate tasks/my-task-v1.json
reprojudge fingerprint tasks/my-task-v1.json
```

Task IDs should be stable and versioned when meaning changes. Pin paper revisions, repository commits, datasets or other external identities whenever the benchmark claim depends on them.

## Available deterministic checks

| Check | Use it for | Key fields |
| --- | --- | --- |
| `artifact_exists` | required file existence | `artifact` |
| `json_equals` | exact JSON value equality | `artifact`, `json_path`, `expected` |
| `json_numeric` | numeric comparison with tolerance | `artifact`, `json_path`, `target`, `abs_tol` / `rel_tol` |
| `text_contains` | bounded literal text evidence | `artifact`, `text` |
| `text_regex` | bounded regular-expression evidence | `artifact`, `pattern` |
| `file_sha256` | exact file identity | `artifact`, `sha256` |

Use the narrowest check that expresses the evidence requirement. Avoid regex when an exact structured check is available.

## Hidden evaluator checks

The full evaluator task is fingerprinted, but normal agent execution receives a generated agent-visible request in which evaluator `checks` are omitted. This prevents a standard task request from directly handing expected values or hashes to the agent.

That separation is not a hostile-code secret boundary. ReproJudge process mode is not a security sandbox; an untrusted process with host filesystem access may be able to inspect files outside the documented request contract. Use an appropriate VM/container/worker boundary for hidden-gold or hostile-agent evaluation.

## Artifact design

Prefer small, structured, reviewable artifacts:

- JSON for scalar or structured outputs;
- text for bounded explanations or extracted identities;
- files with SHA-256 checks when exact bytes are the contract.

Declare every artifact whose absence should matter in `expected_artifacts`. Keep paths relative and confined; traversal and symlink escape attempts are rejected.

## Task suites

Put one JSON task per file in a directory, then validate and run the whole registry:

```bash
reprojudge registry tasks/
reprojudge suite tasks/ --output runs -- python3 agent.py
reprojudge summarize runs/
reprojudge leaderboard runs/ --format markdown
```

A suite should have a written scope statement. If the suite mixes stages, domains or evidence authorities, report those strata separately rather than hiding them behind one aggregate percentage.

## Scientific benchmark contribution checklist

Before proposing a benchmark shard, record:

- exact task scope and non-claims;
- source-paper identifiers with explicit revisions where available;
- public evidence used to define expected values;
- deterministic oracle/check construction;
- licensing and redistribution constraints for included fixtures;
- task hashes or other pinned identities;
- expected failure modes and abstention semantics;
- whether hostile code or hidden gold requires isolation stronger than ReproJudge process mode.

The current 0.3 scientific shard is intentionally limited to paper-to-canonical-public-repository discovery. New stages should be added as distinct evidence scopes rather than silently widening the meaning of existing results.

## Versioning policy

Schema version and task meaning are separate concerns. `schema_version: 1` identifies the task contract format; `task_id` should carry a new semantic version/suffix when a change would alter what an old result means.

Changes that alter expected artifacts, evaluator checks, source identities or scientific claim scope should be treated as benchmark-meaning changes and reviewed accordingly.

See also [TASK_SPEC.md](TASK_SPEC.md), [RESULT_SPEC.md](RESULT_SPEC.md), [EVIDENCE.md](EVIDENCE.md), and [TRUST_MODEL.md](TRUST_MODEL.md).
