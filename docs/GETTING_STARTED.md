# Getting started

## Requirements

- Python 3.11 or newer
- no runtime third-party Python dependencies
- an external command that can read the ReproJudge request and write declared artifacts

The commands below use `python3` on macOS/Linux. On Windows, use `py -3` instead.

Install from a checkout:

```bash
python3 -m pip install -e .
reprojudge --version
reprojudge doctor --strict
```

For development and release checks:

```bash
python3 -m pip install -e '.[dev]'
pytest -q
python3 scripts/release_check.py
```

## Run the deterministic demo

```bash
reprojudge validate examples/tasks/demo-task.json
reprojudge run examples/tasks/demo-task.json \
  --output .reprojudge/runs \
  -- python3 examples/demo_agent.py
reprojudge summarize .reprojudge/runs
reprojudge leaderboard .reprojudge/runs
```

The agent receives paths through `REPROJUDGE_*` environment variables. It does not receive evaluator `checks` in the generated request. The result records separate SHA-256 identities for the full evaluator task and the projected agent request.

## Integrating another agent

Use the process boundary rather than importing ReproJudge internals into the agent. The agent should:

1. read `REPROJUDGE_TASK_MANIFEST`;
2. write outputs only beneath `REPROJUDGE_OUTPUT_DIR`;
3. optionally write bounded telemetry to `REPROJUDGE_TELEMETRY_PATH`;
4. exit zero only when its own execution completed normally.

ReproJudge, not the agent, decides benchmark PASS/FAIL by applying evaluator-owned checks.

## Safety

Process mode is not a sandbox. Use a container, VM, or isolated worker for untrusted agents. Hidden-gold evaluations must also keep evaluator manifests/gold data outside the agent-visible filesystem.
