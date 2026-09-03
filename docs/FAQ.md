# ReproJudge FAQ

## What problem does ReproJudge solve?

It gives scientific-agent evaluations a neutral, deterministic boundary. An external agent runs against a versioned task contract; evaluator-owned checks decide the result; ReproJudge preserves logs, artifacts, hashes, timing and provenance so a benchmark claim can be audited later.

## Is ReproJudge an agent framework?

No. ReproJudge does not require an agent SDK and does not implement an autonomous agent. It evaluates an external command. This keeps the benchmark runner agent-neutral.

## Is it a scientific reproduction agent?

No. A system such as VeriRepro can be evaluated by ReproJudge, but ReproJudge itself is the evaluator/contract layer.

## Does a PASS mean a paper was reproduced?

Only if the task contract actually measures the relevant reproduction claim. A PASS means the declared evaluator checks passed for that task. The current 0.3 scientific shard is a **repository-discovery** benchmark: it measures paper-to-canonical-public-repository discovery only; it does not establish full experiment reproduction or scientific correctness.

## Why are evaluator checks omitted from the agent-visible request?

Expected values and hashes can become gold leakage if they are handed directly to the system being evaluated. ReproJudge therefore fingerprints the full evaluator task while generating a normal agent-visible request without `checks`.

This is an evaluation-contract separation, not a hostile-code secrecy guarantee. Process mode is not a security sandbox.

## Can I evaluate a closed-source or remote agent?

Yes, if you can expose it through a local command or adapter that reads the ReproJudge request and writes declared artifacts. The runner does not require importing the agent's code.

## Does the core require Docker?

No. Ordinary process-mode evaluation uses the Python standard library and does not require Docker. `reprojudge doctor --strict --require-docker` exists for trusted container-backed integration work.

## Why do the distribution, Python package, and CLI all use `reprojudge`?

They intentionally share one public namespace so `pip install reprojudge`, `import reprojudge`, and the `reprojudge` command describe the same project. This avoids a split identity between installation, imports, and CLI usage.

## Why is there optional telemetry if telemetry cannot decide PASS?

Token usage, cost, model identity and intervention counts are useful comparison dimensions. They are reporting evidence, not scientific truth. Deterministic evaluator checks remain the verdict authority.

## How do I create my first benchmark?

```bash
reprojudge init my-benchmark
cd my-benchmark
reprojudge run tasks/hello-reprojudge.json --output runs -- python3 agent.py
```

Then edit the task and replace the deterministic starter agent. See [AUTHORING.md](AUTHORING.md).

## How do I compare several agents?

Run the same task directory for each agent and preserve their telemetry identity, then use:

```bash
reprojudge summarize runs/
reprojudge leaderboard runs/ --format markdown
```

A leaderboard is only meaningful when the underlying tasks, source identities and evaluator semantics are held fixed.

## Can benchmark tasks execute shell snippets?

The agent command is supplied by the operator after `--`; ReproJudge launches argv with `shell=False`. Evaluator task JSON is data, not a shell program.

## What happens on timeout or missing output?

The result remains explicit. Timeouts, launch failures, non-zero exits, missing artifacts and deterministic check failures are preserved in the result/failure taxonomy instead of being collapsed into an ambiguous success flag.

## Can I use hidden tests against a hostile agent?

Not safely with process mode alone. ReproJudge limits what it places in the normal agent-visible request, but a hostile process may have the OS authority to inspect other readable host files. Use a suitable isolation boundary for hidden-gold evaluation.

## How is release evidence different from benchmark results?

Benchmark results describe evaluated task runs. Release evidence additionally binds the public ReproJudge release source to its scientific shard identity, deterministic reference suite and measurement provenance using the v4 evidence schema (source fingerprint). External compatibility attestation is deferred to a future release and is not part of 0.3 evidence.

## Why does the release source fingerprint include docs?

Public claims, task semantics, release authority and user instructions are part of the meaning of a benchmark release. ReproJudge therefore treats them as release-source identity rather than unrelated decoration. No GitHub Actions workflows exist in this repository by design.

## Where should security issues be reported?

Follow [SECURITY.md](../SECURITY.md). Do not disclose exploitable security reports in a public issue.
