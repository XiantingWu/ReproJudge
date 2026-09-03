# ReproJudge

[![Python 3.11–3.14](https://img.shields.io/badge/python-3.11%E2%80%933.14-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Evidence-first evaluation infrastructure for autonomous scientific reproducibility agents.**

ReproJudge evaluates **any external agent command** without trusting the agent's own claim that it succeeded. A versioned task contract defines the job, deterministic evaluator checks decide the verdict, and every run leaves an auditable bundle of artifacts, hashes, logs, timing, and provenance.

> **Status:** 0.3 public-beta release candidate. This repository is the canonical standalone source. The core runtime has zero third-party Python dependencies. The first scientific shard contains 15 revision-pinned real-paper **repository-discovery** tasks. Those tasks are not 15 paper reproductions, and ReproJudge process mode is **not a security sandbox**.

## Why ReproJudge

| Need | ReproJudge surface |
| --- | --- |
| Evaluate different agent frameworks fairly | any executable after `--`; no agent SDK required |
| Keep benchmark truth outside the agent | evaluator `checks` are omitted from the normal agent-visible request |
| Make PASS auditable | deterministic checks + artifact SHA-256 + bounded logs + provenance |
| Compare repeated runs | `summarize` and agent-identity `leaderboard` outputs |
| Keep the evaluator lightweight | Python 3.11+ standard-library core, zero runtime dependencies |
| Preserve claim boundaries | versioned task/result contracts, explicit failure taxonomy, release evidence |

ReproJudge is the **evaluation layer**, not the scientific agent itself. It is intended for agent benchmarks, reproducibility-agent regression suites, deterministic challenge sets, and evidence-preserving research evaluations.

## 60-second start

Install the current source and generate a complete starter benchmark:

```bash
git clone https://github.com/XiantingWu/ReproJudge.git
cd ReproJudge
python3 -m pip install .

reprojudge init my-benchmark
cd my-benchmark
reprojudge run tasks/hello-reprojudge.json --output runs -- python3 agent.py
reprojudge summarize runs
```

On Windows, use `py -3 -m pip install .` and `py -3 agent.py` in place of the `python3` commands above.

`reprojudge init` creates a minimal valid task, a deterministic agent adapter, and a short local README. It **refuses to overwrite a non-empty directory**.

The distribution, Python package, and CLI intentionally share the single public namespace **`reprojudge`**, so install, import, and command identity stay consistent.

Prefer to inspect the repository demo directly?

```bash
reprojudge validate examples/tasks/demo-task.json
reprojudge run \
  examples/tasks/demo-task.json \
  --output .reprojudge/runs \
  -- python3 examples/demo_agent.py
reprojudge leaderboard .reprojudge/runs
```

A run preserves evidence instead of only printing a verdict:

```text
request.json
result.json
stdout.log
stderr.log
agent-telemetry.json       # only when emitted by the agent
artifacts/
  ...
```

`result.json` records evaluator/task and agent-visible request fingerprints, exact argv, timing/platform/version, bounded-log truncation state, deterministic check outcomes, failure taxonomy, artifact sizes/hashes, and optional bounded telemetry.

## Mental model

Scientific-agent demos often blur four roles:

```text
task author -> agent under test -> evaluator -> public claim
```

ReproJudge keeps them explicit:

```text
versioned evaluator task
        |
        +--> agent-visible request (private checks omitted)
        |
        v
 external agent process
        |
        +--> bounded stdout/stderr
        +--> declared artifacts
        +--> optional telemetry
        |
        v
 deterministic scorers
        |
        v
 result.json + hashes + provenance
        |
        +--> summary / leaderboard
        +--> release evidence
```

A process exit code of zero does not automatically become scientific success. Only declared evaluator checks determine the ReproJudge `passed` result.

## Author your own benchmark

Start from the generated scaffold, then replace the synthetic task with a bounded claim you can justify:

```bash
reprojudge init my-benchmark
reprojudge validate my-benchmark/tasks/hello-reprojudge.json
reprojudge fingerprint my-benchmark/tasks/hello-reprojudge.json
```

The v1 task contract remains compatible with the canonical v1 seed contract published before 0.3:

```json
{
  "schema_version": 1,
  "task_id": "governed-individuation-mechanism-v1",
  "domain": "agent-governance",
  "paper": "2607.04613v1",
  "expected_artifacts": []
}
```

0.3 optionally adds bounded `title`, `instructions`, `tags`, `timeout_seconds`, `metadata`, and deterministic `checks`.

Supported scorers:

- `artifact_exists`
- `json_equals`
- `json_numeric` with absolute/relative tolerances
- `text_contains`
- `text_regex`
- `file_sha256`

Evaluator `checks` are **not copied into the generated agent-visible `request.json`**. This prevents the normal request contract from handing expected numeric values, JSON values, or hashes directly to the agent. The full evaluator task is still fingerprinted in `result.json`.

See the [benchmark authoring guide](docs/AUTHORING.md), [task specification](docs/TASK_SPEC.md), and machine-readable contracts in [`schemas/`](schemas/).

## Bring your own agent

ReproJudge integrates at the process boundary, so an agent can be local, closed-source, a research prototype, or a thin adapter around a remote service.

```bash
reprojudge run task.json -- python3 my_agent_adapter.py
```

The adapter reads the generated request from `REPROJUDGE_TASK_MANIFEST`, writes declared outputs under `REPROJUDGE_OUTPUT_DIR`, and may write bounded telemetry to `REPROJUDGE_TELEMETRY_PATH`.

By default ReproJudge passes a minimal environment rather than inheriting the caller's full environment. `--inherit-env` is an explicit authority increase for trusted integrations.

See [Integrating agents](docs/INTEGRATING_AGENTS.md) for the complete adapter contract and acceptance checklist.

## Real scientific shard

[`benchmarks/scientific-seed/`](benchmarks/scientific-seed/) contains 15 revision-pinned papers across vision, NLP, generative modeling, scientific ML, dynamical systems, differentiable physics, and quantum computing.

The 0.3 shard measures one bounded stage only:

> **paper -> canonical public repository discovery**

Each task asks an agent to emit:

```json
{"repository_url":"https://github.com/owner/repository"}
```

Validate the complete shard:

```bash
python3 scripts/validate_scientific_seed.py
```

The validator requires exactly 15 unique task/paper/repository identities, explicit paper revisions, revision-matched evidence URLs, exact manifest/filesystem equality, deterministic task hashes, and a deterministic aggregate shard hash. Canonical GitHub repository spellings are curated release inputs; if an upstream repository is renamed or its canonical owner/name casing changes, the affected gold must be refreshed and the release evidence remeasured rather than silently accepting a stale oracle.

**This is not a 15-paper reproduction claim.** The shard does not test environment reconstruction, experiment execution, numerical agreement, or scientific correctness. Those are separate benchmark stages.

## Reference and compatibility evidence

The four-case deterministic reference suite tests evaluator mechanics including JSON equality/numeric tolerance, text/regex checks, exact SHA-256, and the zero-artifact compatibility contract:

```bash
python3 scripts/run_reference_suite.py --output .reprojudge/reference
```

External cross-repository compatibility attestation (the Repo1/VeriRepro 0.8 compatibility layer of earlier releases) is **deferred to a future release**: it is not re-issued under the current repository identity without a fresh, formally re-established measurement. No stale provenance is relabeled.

See [Compatibility](docs/COMPATIBILITY.md) and the [evidence model](docs/EVIDENCE.md).

## Safety model

ReproJudge is **not a security sandbox**.

The evaluator uses argv execution rather than a shell, refuses escaping/symlinked evaluator paths, bounds manifests/results/telemetry/logs/scorer/hash work, evaluates regex checks in a time-bounded child interpreter, cleans ordinary same-process-group descendants on POSIX, keeps private checks out of the normal agent request, and avoids inheriting caller credentials by default.

An evaluated agent is still arbitrary code with the authority of its OS process. A hostile process may inspect other readable host files or deliberately escape application-level process-group assumptions. Hidden-gold or hostile-agent evaluation belongs in an appropriate VM/container/worker boundary.

See [SECURITY.md](SECURITY.md) and the [trust model](docs/TRUST_MODEL.md).

## CLI

```text
reprojudge init [DIRECTORY]
reprojudge validate TASK.json
reprojudge registry TASK_DIRECTORY
reprojudge run TASK.json [--output DIR] [--cwd DIR] [--inherit-env] -- AGENT ...
reprojudge suite TASK_DIRECTORY [--output DIR] [--cwd DIR] [--inherit-env] -- AGENT ...
reprojudge summarize RUN_DIRECTORY [--format markdown|json]
reprojudge leaderboard RUN_DIRECTORY [--format markdown|json|csv]
reprojudge fingerprint TASK.json
reprojudge fingerprint PROJECT_ROOT --source-tree
reprojudge doctor [--strict] [--require-docker]
```

`doctor --strict` verifies the core process boundary and writable temporary storage. `doctor --strict --require-docker` additionally requires a usable Docker daemon for trusted container-backed integration work. Ordinary ReproJudge process-mode evaluation does not require Docker.

## Development

```bash
python3 -m pip install -e '.[dev]'
pytest -q
python3 scripts/check_public_identity_hygiene.py
python3 scripts/launch_surface_check.py
python3 scripts/validate_scientific_seed.py
python3 scripts/release_check.py
python3 scripts/release_source_check.py
```

All quality gates are runnable locally: the full test suite, public identity hygiene, launch-surface, scientific-seed, release, reference-suite, standalone-export, sdist-validation, ruff, mypy, and coverage gates. No GitHub Actions workflows are used in this repository.

## Release evidence

0.3 release evidence keeps three statements separate:

1. **15 real-paper discovery tasks** define the first scientific benchmark shard;
2. **4 deterministic reference cases** test evaluator mechanics on the exact candidate source;
3. the **release audit** proves the exact current standalone source, package, and evidence binding.

Formal ReproJudge source measurement uses:

```text
repository: XiantingWu/ReproJudge
runner_environment: github-hosted
platform: macOS ARM64 (GitHub-hosted)
python: 3.11.9
```

Candidate evidence is generated on the exact source head, verified by digest, promoted byte-exact as `benchmarks/release-evidence-0.3.0.json`, then revalidated on the exact committed-evidence head. Only that strictly versioned promotion file is excluded from the release-source fingerprint to avoid self-reference; tests, schemas, scripts, examples, benchmark inputs, and public documentation remain fingerprinted.

See the [evidence model](docs/EVIDENCE.md), [release process](docs/RELEASING.md), and [public release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md).

## Deliberate non-claims

A ReproJudge 0.3 PASS does **not** mean:

- the 15 discovery papers were fully reproduced;
- an arbitrary scientific paper is reproducible;
- scientific correctness has been established;
- four reference tasks provide broad scientific benchmark coverage;
- external cross-repository compatibility was freshly re-established in this release;
- process success is scientific equivalence;
- regex/JSON/hash checks replace domain-expert metrics;
- process mode safely sandboxes hostile code;
- hosted-runner evidence is independent third-party certification.

## Design principles

1. **Agent-neutral** — the runtime imports no sibling project.
2. **Evidence-first** — verdicts point to concrete artifacts, checks, and hashes.
3. **Fail closed** — malformed input, unsafe paths, invalid telemetry, missing artifacts, launch failures, non-zero exits, and timeouts remain explicit.
4. **Bounded host work** — untrusted manifests, telemetry, results, logs, scorer inputs, and artifact hashing have explicit limits.
5. **Versioned contracts** — historical task/result meaning does not silently change.
6. **Honest claims** — evidence says exactly what was measured and what was not.
7. **Portable core** — the evaluator runtime uses the Python standard library only.

## Governance and support

- [Governance](GOVERNANCE.md) — maintainer model, release authority, and decision process.
- [Support](SUPPORT.md) — how to route bugs, features, benchmark proposals, usage, security, and conduct questions.
- [Benchmark corpus policy](docs/BENCHMARK_CORPUS_POLICY.md) — corpus acceptance, provenance, pinning, drift, and claim boundaries.

## Documentation

**Start here**

- [Getting started](docs/GETTING_STARTED.md)
- [Authoring benchmarks](docs/AUTHORING.md)
- [Integrating agents](docs/INTEGRATING_AGENTS.md)
- [FAQ](docs/FAQ.md)

**Contracts and evidence**

- [Task specification](docs/TASK_SPEC.md)
- [Result specification](docs/RESULT_SPEC.md)
- [Evidence model](docs/EVIDENCE.md)
- [Telemetry](docs/TELEMETRY.md)
- [Leaderboard semantics](docs/LEADERBOARD.md)
- [Compatibility](docs/COMPATIBILITY.md)

**Architecture and operations**

- [Architecture](docs/ARCHITECTURE.md)
- [Trust model](docs/TRUST_MODEL.md)
- [0.3 launch readiness](docs/LAUNCH_READINESS_0.3.0.md)
- [Release process](docs/RELEASING.md)
- [Public release checklist](docs/PUBLIC_RELEASE_CHECKLIST.md)
- [Benchmark corpus policy](docs/BENCHMARK_CORPUS_POLICY.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Citation](CITATION.cff)
- [Changelog](CHANGELOG.md)

## License

MIT. See [LICENSE](LICENSE). For academic use, see [CITATION.cff](CITATION.cff).
