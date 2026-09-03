# Security policy

## Supported versions

Security fixes are applied to the latest public beta line.

## Reporting

Do not publish credentials, sandbox escapes, command-injection findings, or other sensitive exploit details in a public issue. For the standalone repository, use GitHub's **private security advisory** form at <https://github.com/XiantingWu/ReproJudge/security/advisories/new>. If that control is not enabled yet, do not fall back to a public issue containing exploit details.

## Threat model

ReproJudge parses benchmark-controlled JSON, creates run directories, launches external commands, reads agent-authored artifacts/telemetry, and produces result bundles. These are trust boundaries.

The evaluator therefore:

- executes argv with `shell=False`;
- rejects task/output paths that escape the evaluator-owned root;
- rejects symlinked task manifests and every symlink component in scored artifact paths;
- caps task, telemetry, result, scorer-input, log, and artifact-hash work;
- rejects JSON NaN/Infinity where evaluator semantics depend on numeric values;
- uses a minimal inherited environment by default;
- records exact argv but warns users never to put secrets in argv;
- evaluates regex scorers in an isolated child interpreter with a hard timeout;
- terminates residual same-group POSIX descendants after normal agent exit, and escalates timed-out process groups from TERM to KILL;
- treats malformed telemetry as an explicit evaluator failure;
- separates optional cost/token/intervention telemetry from scientific authority;
- keeps evaluator `checks` out of the generated agent-visible request and fingerprints full task/request separately;
- fails a run when declared artifact evidence cannot be bounded and SHA-256 recorded instead of silently dropping provenance;
- rejects malformed, non-finite, inconsistent or unsafe historical result data before summary/leaderboard aggregation.

## Execution warning

ReproJudge is **not an OS sandbox**. An agent process can access whatever the host OS grants it. The controls above protect evaluator integrity; they do not make hostile code safe.

For untrusted agents use a dedicated VM, container, sandbox worker, or equivalent isolation boundary.

This repository uses **no GitHub Actions workflows** by design: no CI, release, or publish job executes on hosted runners. All quality gates run locally under the maintainer's control. Never place API keys, passwords, access tokens, signed URLs, or other secrets in repository files, issues, or pull requests.

## Credentials

Never place API keys, passwords, access tokens, signed URLs, or other secrets in agent command-line arguments because `result.json` records argv.

`--inherit-env` is an explicit trust decision. Use narrowly scoped credentials and isolated runners for integrations that need network/API access.

## Residual risks

- a hostile local process can consume resources outside ReproJudge's application-level limits unless the OS/container also constrains it;
- a child that deliberately starts a new process session can escape ReproJudge's same-process-group cleanup;
- process-mode evaluation does not provide network or filesystem secrecy/isolation;
- hiding checks from `request.json` does not prevent a hostile same-host agent from searching readable benchmark/gold files;
- artifact semantic correctness depends on the chosen deterministic scorer;
- a hash proves byte identity, not scientific validity;
- regex/text checks are syntactic evidence only;
- external repositories/datasets remain supply-chain inputs and need their own pinning/checksum policies.
