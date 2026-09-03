# Public release checklist

## Source-controlled public/release surface

- [x] package/CLI/import identity documented (`reprojudge` / `reprojudge`)
- [x] canonical repository URLs point to `XiantingWu/ReproJudge`
- [x] MIT license
- [x] README states capabilities and deliberate non-claims
- [x] architecture, task/result, trust, evidence, release documentation
- [x] machine-readable task/result/telemetry JSON Schemas
- [x] 15-case revision-pinned real-paper repository-discovery shard with manifest/validator
- [x] known upstream canonical repository spellings are regression-locked and oracle drift requires remeasurement
- [x] Repo1 compatibility evidence is documented as deferred to a future release; no external attestation, task bytes or lock are vendored
- [x] security, contribution, conduct, citation, roadmap, changelog
- [x] issue forms and PR template
- [x] no Dependabot configuration by design; no automatic dependency-update PR mechanism exists
- [x] no GitHub Actions workflows exist by design; all quality gates are runnable locally
- [x] `launch_surface_check.py` fails closed on workflow presence regressions, Python-matrix regressions, and broken local Markdown links

## Evaluator integrity

- [x] task manifests bounded and symlink/path traversal rejected
- [x] unknown task/check fields fail closed rather than being silently discarded
- [x] programmatic and file-loaded JSON obey the same finite/serialized-size policy
- [x] task/check/artifact/tag/metadata counts bounded
- [x] evaluator checks omitted from the generated agent-visible request
- [x] full evaluator task and agent request have separate SHA-256 fingerprints
- [x] `shell=False` and bounded argv
- [x] minimal environment default
- [x] timeout and post-exit POSIX process-group cleanup with TERM/KILL escalation
- [x] stdout/stderr capture bounded
- [x] regex scoring isolated behind a hard child-process timeout
- [x] scorer inputs and artifact hashing bounded
- [x] every artifact symlink component rejected
- [x] declared artifacts that cannot receive bounded hash evidence prevent PASS
- [x] telemetry bounded, typed, finite, and non-authoritative
- [x] result aggregation bounded and malformed/unsafe results fail closed
- [x] leaderboard inputs are finite/status-consistent and fail closed on malformed evidence
- [x] task and release-source deterministic fingerprints cover tests, schemas and all benchmark bytes except strictly versioned promoted self-referential evidence
- [x] successful process exit remains distinct from failed scientific/evidence checks
- [x] machine-readable failure taxonomy is evaluator-derived

## Scientific benchmark integrity

- [x] scientific shard contains exactly 15 task files and the manifest must match the on-disk set exactly
- [x] every paper identifier is pinned to an explicit arXiv revision
- [x] every evidence URL matches the exact paper revision
- [x] every task has a unique task ID, paper revision and canonical GitHub repository gold
- [x] current canonical spellings for known drift-sensitive ALBERT, CLIP and JAX-MD golds are regression-tested
- [x] every task emits only `discovery.json` and has one `json_equals` evaluator check on `repository_url`
- [x] validator emits per-task fingerprints plus manifest/shard hashes
- [x] curation provenance is pinned to the exact revision-pinned arXiv real-paper corpus blob used for 0.3
- [x] docs state that 15 discovery tasks are not 15 complete paper reproductions
- [x] competitive hidden-gold users are told to isolate evaluator files from agent filesystem access

## External compatibility integrity

- [x] Repo1/VeriRepro compatibility evidence is deferred to a future release and is not claimed in 0.3
- [x] no external repository's recorded runs, task bytes, run IDs or result hashes are vendored into the 0.3 source
- [x] no compatibility lock or attestation file is part of 0.3 release evidence
- [x] documentation never describes deferred compatibility work as current attestation

## 0.3 release-evidence invariants

These conditions are machine-enforced. **Do not edit this checklist after measurement merely to record PASS/FAIL**; doing so correctly changes the release-source fingerprint. Release status belongs in the version-matched evidence record and repository control plane.

A releasable 0.3 head must satisfy all of the following without source drift:

1. the complete regression suite, launch-surface check, 15-case scientific-seed validation, source check, four-case reference suite, standalone export, package/Twine/clean-install gates all pass;
2. the standalone export revalidates the same 15-case shard before package construction;
3. the standalone release-authority lane passes on the exact source head without cross-repository credentials;
4. no pinned external compatibility attestation is part of 0.3 release evidence; such evidence is deferred to a future release;
5. candidate `benchmarks/release-evidence-0.3.0.json` is generated from that exact ReproJudge source using release-evidence schema v4, binding current ReproJudge repository/platform/Python provenance;
6. before promotion, the candidate evidence is temporarily injected and both `release_check.py --require-release-evidence` and `release_source_check.py --require-release-evidence` pass;
7. the exact candidate bytes are hash-verified before promotion, and no artifact service is used;
8. committed evidence explicitly keeps `arbitrary_paper_reproducibility_proven` and `scientific_correctness_proven` false and makes no external compatibility attestation claim;
9. after committing only the excluded evidence record, the exact final standalone head passes both evidence-required gates plus the full repository-local engineering/package gate again;
10. no release-relevant source or benchmark byte is changed after that final evidence-required run. Any such change requires fresh ReproJudge measurement and evidence;
11. after normal-merge promotion into `main`, exact-`main` validation passes, and `main` remains frozen until any release publication completes.

The release lane is maintainer-operated evidence, not independent third-party certification.

## Live control-plane requirements

The canonical repository is already public. The items in this section describe live, externally mutable GitHub state; they are not source-controlled proof and intentionally are not represented as stale unchecked checkboxes. Read them back through the repository control plane under the maintainer identity whenever this checklist is used.

| Surface | Required live state | Authority |
|---|---|---|
| Repository | public visibility, default branch `main`, bounded description/topics, Issues/Discussions disabled, Wiki disabled | GitHub repository settings/API |
| Merge policy | merge commits enabled; squash and rebase disabled for the evidence-preserving path | GitHub repository settings/API |
| `main` ruleset | active; pull request required; conversation resolution required; zero required approvals is intentional for the single-maintainer model | GitHub ruleset API |
| Release tag rulesets | active creation-only rule for `refs/tags/v*` with the minimum maintainer actor, plus an independent update/deletion block with no bypass actors | GitHub ruleset API |
| Security | private vulnerability reporting, secret scanning, push protection, Dependabot alerts enabled, Dependabot security updates disabled (no dependabot.yml by design) | GitHub security/settings APIs |
| Actions | no workflows exist; GitHub Actions remains enabled for future maintainer decisions only | GitHub Actions settings/API |
| Public smoke | unauthenticated clone/install/demo/scientific-seed validation succeeds | independent public client |
| Projects | disable only when the control plane proves there are zero Projects; otherwise preserve and document the real Project | GitHub Projects control plane |

The source-controlled guards for standalone history, hosted execution, and public claim boundaries are recorded in the sections above. Live GitHub settings must be verified through the control plane; this document defines required state and is not itself proof of current state.

## Future PyPI/release control-plane actions

This task is not a release. The following actions remain intentionally unperformed and belong to a separate release task:

- confirm ownership/availability of `reprojudge`;
- tag the exact validated current `main` as `v0.3.0` while `main` is frozen;
- create the GitHub Release from that exact tag;
- publish the tested wheel/sdist manually (no GitHub Actions publishing workflow exists by design);
- install and verify the actually published wheel/sdist in fresh environments;
- verify the PyPI README/project links after publication.

## Evidence claims

- [x] 15 scientific cases are described as repository-discovery benchmark tasks, not full reproductions
- [x] deterministic reference suite is described as evaluator-mechanics evidence only
- [x] external compatibility evidence is documented as deferred to a future release rather than presented as current attestation
- [x] process success is not presented as scientific equivalence
- [x] public/hidden-gold fairness limitation of process mode is explicit
- [x] release evidence requires exact narrow claim text plus false flags for arbitrary-paper and scientific-correctness proof

## Main ruleset design

The active `main` ruleset is the required control-plane contract:

- blocks force push and blocks deletion of `main`;
- requires a pull request for ordinary future contributions and resolved conversations;
- requires zero approving reviews because this is a single-maintainer repository; external contributions still require maintainer review and merge authority;
- allows a maintainer bypass only where the ruleset explicitly configures it and the live configuration is externally verified;
- keeps squash/rebase disabled so the evidence-preserving merge-commit path stays the only merge method.

## Release tag protection design

Use two active `refs/tags/v*` rulesets. The creation-only ruleset restricts tag creation to the minimum supported maintainer actor. The independent immutability ruleset blocks tag update and deletion and has no bypass actors. A published release tag must never move or be deleted.

## Public security requirements

The public repository must keep the following live controls enabled and read back from GitHub:

- `main` and the two `v*` tag rulesets described above;
- private vulnerability reporting, secret scanning, push protection, Dependabot alerts enabled, Dependabot security updates disabled (no dependabot.yml by design);
- no GitHub Actions workflows and no repository runner registrations;
- anonymous clone / install / demo / scientific-shard validation from an unauthenticated environment.

## Optional launch polish

The following can improve presentation but is not allowed to weaken or block the reproducibility/evidence gates above:

- demo GIF/video
- social preview image
- benchmark comparison announcement after public package smoke
- SBOM (SPDX/CycloneDX) and ecosystem artifact attestation as additive provenance layers, introduced post-0.3 with their own verification gates