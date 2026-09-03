# Support

ReproJudge is a small single-maintainer project. Please route questions to the right channel so they reach the maintainer efficiently.

## Channels

| Topic | Where | Notes |
|---|---|---|
| Bug reports | [Issues](https://github.com/XiantingWu/ReproJudge/issues) — bug template | include the exact command, task, agent command, OS/Python versions, and the resulting `result.json` if available |
| Feature requests | [Issues](https://github.com/XiantingWu/ReproJudge/issues) — feature template | describe the claim boundary and evidence impact |
| Benchmark proposals | [Issues](https://github.com/XiantingWu/ReproJudge/issues) — benchmark proposal template | see [BENCHMARK_CORPUS_POLICY.md](docs/BENCHMARK_CORPUS_POLICY.md) before proposing |
| Usage questions | [Discussions](https://github.com/XiantingWu/ReproJudge/discussions) | start with [GETTING_STARTED.md](docs/GETTING_STARTED.md) and [FAQ.md](docs/FAQ.md) |
| Security findings | private security advisory (see [SECURITY.md](SECURITY.md)) | never post exploit details in public issues |
| Code of conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | report violations privately to the maintainer |

## Before asking

- [ ] read [GETTING_STARTED.md](docs/GETTING_STARTED.md) and the [FAQ](docs/FAQ.md);
- [ ] run `reprojudge doctor --strict` and include its output;
- [ ] confirm you are on a supported Python (3.11, 3.12, 3.13, 3.14);
- [ ] check that the task file passes `reprojudge validate`.

## Support lifecycle

- **Before the first tagged/package release**: the supported public-beta surface is the canonical public source at its exact commit.
- **After the first published release**: support follows the newest published 0.x line; older 0.x lines are fixed only when the fix cannot be backported cleanly, at the maintainer's discretion.
- **Supported Python minors**: 3.11, 3.12, 3.13, 3.14 — the versions continuously tested by the hosted CI matrix. Unsupported Python versions may still install but receive no compatibility guarantee.
- **Schema compatibility**: task/result/telemetry schema version stays integer `1` across 0.x; 0.x additions are additive. Deprecated fields are not silently reinterpreted; a deprecated form is removed only with a documented migration in the changelog.
- **Breaking semantics**: any change that reinterprets an existing v1 task field, scorer meaning, or result core field requires a new schema version and migration documentation (see [COMPATIBILITY.md](docs/COMPATIBILITY.md)).
- **Security fixes**: security-sensitive findings go through the private route in [SECURITY.md](SECURITY.md); fixes are released as a patch of the current line and, if the released artifact is unsafe, accompanied by a yank/advisory decision per [RELEASING.md](docs/RELEASING.md).
- **No SLA**: this is a single-maintainer project; triage happens as time allows.

## Expectations

- Issues and PRs are triaged as the maintainer's time allows; there is no guaranteed SLA.
- Release evidence and benchmark gold changes follow the evidence lifecycle in [RELEASING.md](docs/RELEASING.md) — they are not quick edits.
- Do not share private benchmark gold, credentials, or internal evidence in public channels.
