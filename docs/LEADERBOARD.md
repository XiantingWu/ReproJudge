# Leaderboard semantics

`reprojudge leaderboard` aggregates evaluator-authored result bundles by the reported agent identity/version.

Supported output formats:

```bash
reprojudge leaderboard RUN_DIRECTORY --format markdown
reprojudge leaderboard RUN_DIRECTORY --format json
reprojudge leaderboard RUN_DIRECTORY --format csv
```

## What ranking means

The leaderboard reports only measurements contained in validated ReproJudge result bundles: run count, pass/fail outcomes, pass rate, runtime, reported token/cost telemetry, and recorded interventions where available.

A leaderboard is meaningful only when compared systems ran the same task set under comparable execution policy. ReproJudge does not claim that a higher pass rate across different tasks, hardware, network permissions, operator assistance, or hidden-gold access represents a stronger scientific agent.

## Untrusted display metadata

Agent identity/version are agent-authored telemetry, not trusted markup. ReproJudge therefore treats them as data when exporting a leaderboard:

- bounded identity text containing control characters is rejected before grouping;
- Markdown output escapes table/markup metacharacters so an agent label cannot create rows, links, or formatting syntax;
- CSV output prefixes spreadsheet-formula-leading identity cells (`=`, `+`, `-`, `@`) so opening a leaderboard in common spreadsheet software does not reinterpret an agent label as a formula;
- JSON output preserves the validated identity values as data.

These rendering controls protect the report surface only. They do not make telemetry authoritative and do not affect PASS/FAIL.

## Fairness requirements

For publishable comparisons, record and hold constant where applicable:

- exact task fingerprints and suite identity;
- evaluator version/source identity;
- hardware/runtime policy;
- network and credential policy;
- artifact/gold visibility;
- timeout/resource budgets;
- operator interventions.

The normal agent request omits evaluator checks, but process mode alone cannot keep repository-local gold secret from a hostile agent. Competitive hidden-gold leaderboards require OS/container/worker isolation that excludes evaluator manifests and gold data from the agent filesystem.

## Cost and token telemetry

Cost/token numbers are adapter-reported unless independently verified. They are displayed for transparency and must not be presented as audited billing data without an independent measurement source.
