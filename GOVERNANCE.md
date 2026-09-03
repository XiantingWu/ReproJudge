# Governance

## Maintainer model

ReproJudge is a **single-maintainer** open-source project. The maintainer (XiantingWu) owns the repository, the release authority, and the benchmark truth surface.

This is stated explicitly: there is no fictional maintainer team. Additional maintainers may be added over time through documented review of sustained, high-quality contributions and explicit agreement.

## Decision areas

| Area | Decision maker | Policy |
|---|---|---|
| evaluator/schema semantics | maintainer | breaking semantics require a new schema version and migration notes |
| release evidence promotion | maintainer | only the standalone release measurement may produce candidate evidence; promotion is byte-exact and evidence-only |
| benchmark corpus content | maintainer | see [BENCHMARK_CORPUS_POLICY.md](docs/BENCHMARK_CORPUS_POLICY.md) |
| quality gates | maintainer | all gates run locally; no GitHub Actions workflows exist by design |
| public identity hygiene | enforce by gate | any occurrence of former private identity or internal identifiers fails the local gates |

## Release authority

Formal release evidence is produced by the standalone release measurement at an exact `main` head:

- repository: `XiantingWu/ReproJudge`
- runner environment: `github-hosted` (when measured on hosted compute)
- platform: macOS ARM64, Python 3.11.9
- evidence schema: v4 with release source authority identity (`source_tree_sha256`) and portable byte identity (`source_fingerprint`)

Candidate evidence is verified independently by digest and promoted as the single evidence-only commit. No maintainer edits evidence by hand; stale or hand-edited evidence fails the release gates.

## Contributions

Contributions are welcome under [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md). Decision-making for non-maintainer contributions follows the decision areas above; contract or corpus changes are reviewed against the documented evidence and claim-boundary requirements before merge.

## Merge authority

The maintainer is the sole merge authority. Ordinary maintainer changes use pull requests and the required review; ordinary external contributions are reviewed and, when needed, replayed from a maintainer-controlled branch. An emergency bypass exists only where a repository ruleset explicitly configures it and the configuration has been externally verified; this document does not assume a bypass that is not configured.

## Review ownership

The repository does not use `CODEOWNERS` by design. As a single-maintainer repository, review ownership of all surfaces — including release authority, benchmark truth, and identity hygiene — rests with the maintainer. Review ownership is advisory for direct maintainer changes and mandatory for ordinary contribution reviews.

## Maintainer succession

If the maintainer becomes unable to act, the project may be archived or handed over through an explicit public handover: a successor is named in a repository announcement, the successor must accept this governance and the release/evidence discipline, and evidence history is preserved as-is (never rewritten). Until such a handover is announced, the current maintainer remains the sole authority.

## Security

Security-sensitive findings go through the private advisory channel in [SECURITY.md](SECURITY.md). The maintainer is the security contact. Secrets, tokens, and private evidence must never appear in issues, PRs, commits, or logs.
