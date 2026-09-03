from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def _linear_fit(x: list[float], y: list[float]) -> tuple[float, float]:
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("linear_fit requires equal x/y arrays with at least two points")
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        raise ValueError("linear_fit x values must not all be equal")
    slope = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x, y, strict=True)
    ) / denominator
    return slope, y_mean - slope * x_mean


def main() -> int:
    task_path = Path(os.environ["REPROJUDGE_TASK_MANIFEST"])
    output = Path(os.environ["REPROJUDGE_OUTPUT_DIR"])
    telemetry_path = Path(os.environ["REPROJUDGE_TELEMETRY_PATH"])
    task = json.loads(task_path.read_text(encoding="utf-8"))
    metadata = task.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("baseline task metadata must be an object")
    operation = metadata.get("operation")
    output.mkdir(parents=True, exist_ok=True)

    if operation == "mean":
        values = metadata.get("values")
        if not isinstance(values, list) or not values:
            raise ValueError("mean requires a non-empty values array")
        numeric = [float(value) for value in values]
        payload = {"result": sum(numeric) / len(numeric)}
    elif operation == "linear_fit":
        raw_x = metadata.get("x")
        raw_y = metadata.get("y")
        if not isinstance(raw_x, list) or not isinstance(raw_y, list):
            raise ValueError("linear_fit requires x/y arrays")
        slope, intercept = _linear_fit(
            [float(value) for value in raw_x],
            [float(value) for value in raw_y],
        )
        payload = {"intercept": intercept, "slope": slope}
    elif operation == "sha256":
        raw = metadata.get("payload")
        if not isinstance(raw, str):
            raise ValueError("sha256 requires a string payload")
        payload = {"sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()}
    else:
        raise ValueError(f"unsupported executable baseline operation: {operation!r}")

    (output / "baseline.json").write_text(
        json.dumps(payload, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    telemetry_path.write_text(
        json.dumps(
            {
                "agent_name": "reprojudge-executable-baseline",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
