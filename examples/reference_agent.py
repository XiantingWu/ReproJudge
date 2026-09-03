from __future__ import annotations

import json
import os
from pathlib import Path

task_path = Path(os.environ["REPROJUDGE_TASK_MANIFEST"])
output = Path(os.environ["REPROJUDGE_OUTPUT_DIR"])
telemetry_path = Path(os.environ["REPROJUDGE_TELEMETRY_PATH"])
task = json.loads(task_path.read_text(encoding="utf-8"))
output.mkdir(parents=True, exist_ok=True)

task_id = task["task_id"]
if task_id == "reference-json":
    (output / "metrics.json").write_text(
        json.dumps({"accuracy": 0.91, "status": "ok"}, sort_keys=True) + "\n",
        encoding="utf-8",
    )
elif task_id == "reference-text":
    (output / "report.txt").write_text(
        "Reproduced successfully\nseed=7\n", encoding="utf-8"
    )
elif task_id == "reference-hash":
    (output / "artifact.bin").write_bytes(b"reprojudge-reference-v1\n")
elif task_id == "reference-zero-artifact":
    pass
else:
    raise SystemExit(f"unknown reference task: {task_id}")

telemetry_path.write_text(
    json.dumps(
        {
            "agent_name": "reprojudge-reference-agent",
            "agent_version": "1",
            "provider": "deterministic-local",
            "token_usage": 0,
            "model_cost_usd": 0.0,
            "interventions": [],
        },
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)
