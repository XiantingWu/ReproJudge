# Telemetry contract

Agent telemetry is optional, bounded measurement data. It is never scientific authority.

The evaluator exposes `REPROJUDGE_TELEMETRY_PATH`. An agent or adapter may write one JSON object with:

- `agent_name`
- `agent_version`
- `model`
- `provider`
- `token_usage`
- `model_cost_usd`
- `interventions`

The file is limited to 64 KiB. Unknown keys, invalid types, negative/non-finite cost values, negative token counts, oversized intervention data, or control characters in bounded text produce `telemetry_error` rather than being silently ignored.

All fields are optional, but an optional field is represented by **omitting the key**. Explicit JSON `null` is not a valid value for an agent-authored telemetry key. Identity/model/provider/intervention text is trimmed, must contain a non-whitespace character, is capped at 256 characters, and must not contain C0/DEL control characters. Current evaluator-authored result telemetry uses the same canonical projection and omits absent scalar fields instead of serializing them as `null`.

Historical result schema v1 bundles may contain older additive telemetry representations. Result ingestion retains backward compatibility for those evaluator-authored records; the stricter rules above govern new agent telemetry and new evaluator output.

## Interpretation

Token and cost fields are self-reported by the integration unless an external system independently verifies them. Leaderboards may aggregate them for transparency, but they do not change deterministic scientific checks or convert a failed result into PASS.

`interventions` should record operator assistance that materially changes a run, such as repository/command overrides or other manual help supplied by an adapter. Recording intervention count allows comparisons to distinguish autonomous execution from assisted execution.

## Privacy and secrets

Do not place credentials, endpoints containing secrets, prompts containing private data, or raw provider responses in telemetry. The public schema intentionally contains only a narrow measurement surface.

Machine-readable schema: [`schemas/agent-telemetry-v1.schema.json`](../schemas/agent-telemetry-v1.schema.json).
