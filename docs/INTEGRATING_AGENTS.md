# Integrating an agent with ReproJudge

ReproJudge does not require an agent SDK. The integration boundary is an external command plus a small environment contract.

## Smallest possible adapter

Run any executable after `--`:

```bash
reprojudge run tasks/my-task.json -- python3 my_agent.py
```

ReproJudge launches the command with `shell=False`. The agent receives a generated request and an output directory through environment variables.

The key variables are:

- `REPROJUDGE_TASK_MANIFEST` — path to the generated agent-visible request;
- `REPROJUDGE_OUTPUT_DIR` — directory where declared artifacts should be written;
- `REPROJUDGE_TELEMETRY_PATH` — optional telemetry JSON destination;
- run/task identifiers exposed by the documented runtime contract.

Read those paths from the environment rather than assuming a working-directory layout.

## Python example

```python
import json
import os
from pathlib import Path

request_path = Path(os.environ["REPROJUDGE_TASK_MANIFEST"])
output_dir = Path(os.environ["REPROJUDGE_OUTPUT_DIR"])
request = json.loads(request_path.read_text(encoding="utf-8"))

output_dir.mkdir(parents=True, exist_ok=True)
(output_dir / "answer.json").write_text(
    json.dumps({"status": "ok"}) + "\n",
    encoding="utf-8",
)
```

The request is not the full evaluator task: evaluator `checks` are deliberately omitted from the normal agent-visible projection.

## Wrapping an existing CLI agent

If your agent already has a command-line interface, write a thin adapter that:

1. reads the ReproJudge request;
2. converts it into the agent's native input;
3. invokes the agent using argv, not an interpolated shell string;
4. normalizes outputs into the declared ReproJudge artifacts;
5. optionally records bounded telemetry.

Keep adapter policy separate from benchmark truth. The adapter may transform formats, but it should not invent expected answers or convert its own confidence into an evaluator PASS.

## Environment inheritance

By default ReproJudge passes a minimal environment rather than inheriting the caller's full environment. This reduces accidental credential leakage into evaluated processes.

Use `--inherit-env` only for a trusted integration that genuinely requires the caller environment:

```bash
reprojudge run task.json --inherit-env -- my-agent ...
```

`--inherit-env` is an authority increase. Document why it is needed in reproducible benchmark runs.

## Telemetry

Telemetry is optional and never grants PASS authority. It can record bounded agent/model/provider identity, token usage, model cost and explicit interventions.

Typical telemetry:

```json
{
  "agent_name": "my-agent",
  "agent_version": "1.2.0",
  "provider": "local",
  "token_usage": 1200,
  "model_cost_usd": 0.02,
  "interventions": []
}
```

Use telemetry for reporting and comparison, not as a substitute for deterministic output checks.

## Failure behavior

Your adapter should fail loudly when it cannot produce the declared output. ReproJudge preserves launch errors, non-zero exits, timeouts, missing artifacts and check failures as distinct evidence.

Do not manufacture placeholder artifacts merely to keep a run green. If the underlying agent abstains or cannot complete the task, preserve that state in the agent output and let the evaluator contract decide the result.

## Security boundary

ReproJudge process mode is not a security sandbox. It bounds evaluator work, avoids a shell, minimizes inherited environment by default and confines evaluator-managed paths, but the external process still runs with the authority of its OS process.

For hostile agents, hidden gold, untrusted third-party experiment code or strong filesystem/network isolation requirements, place the whole agent command inside a suitable container/VM/worker boundary and treat that isolation layer as separate from ReproJudge's evaluator semantics.

## Integration acceptance checklist

A production adapter should demonstrate:

- deterministic parsing of the agent-visible request;
- outputs only under `REPROJUDGE_OUTPUT_DIR`;
- no dependency on evaluator-private `checks`;
- explicit timeout/abstention/error behavior;
- no implicit caller credential inheritance unless reviewed;
- bounded telemetry without secrets;
- a reproducible command line that can run under `reprojudge suite`;
- at least one fixture proving expected PASS and one proving expected failure.

Start with `reprojudge init`, then replace the generated `agent.py` with your adapter. See [AUTHORING.md](AUTHORING.md) for task design and [TRUST_MODEL.md](TRUST_MODEL.md) for authority boundaries.
