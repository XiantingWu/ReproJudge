# Testing and evaluator trust gates

ReproJudge treats evaluator correctness as a release property, not only as a collection of example tests.

## Test layers

The release test surface has four complementary layers:

1. **Unit and regression tests** cover task parsing, runner behavior, scoring, reporting, telemetry, evidence, CLI behavior, and release-policy failure paths.
2. **Property tests** use Hypothesis to exercise invariants across generated inputs rather than a fixed set of examples. Current invariants include task JSON round trips, deterministic scoring for identical evidence, serialization invariance, monotonic numeric tolerance, and immunity to undeclared extra evidence.
3. **Adversarial-output tests** exercise malformed or hostile-but-unprivileged agent behavior, including invalid UTF-8 logs, bounded stdout/stderr, malformed and non-finite JSON artifacts, missing values, wrong hashes, duplicate declarations, environment leakage, working-directory confusion, timeout escalation, symlink handling, and process cleanup.
4. **Executable baselines** run a real subprocess agent through the public evaluator boundary. They are separate from the scientific discovery seed and from ordinary unit tests.

## Supported Python matrix

The 0.3 package declares Python 3.11+. The supported patch versions **3.11.9, 3.12.10, 3.13.15, and 3.14.7** are validated locally on the platforms where they are exercised. There is no hosted CI matrix: this repository uses **no GitHub Actions workflows** by design, and Python-version authority is established by local runs on the platform actually used for release measurement.

The runtime remains standard-library-only and portable by design, but operating-system-specific authority must be established by a real run on the target platform before it is described as release-validated.

## Coverage gate

The release measurement collects branch-aware coverage over the complete `reprojudge` package. `scripts/check_coverage_thresholds.py` evaluates statement and branch coverage separately and fails closed unless both release thresholds are met:

- statement coverage: **at least 90%**;
- branch coverage: **at least 85%**.

The thresholds are not a substitute for meaningful assertions. New tests should target observable contracts and failure modes; do not exclude production modules or mark lines as unmeasured merely to satisfy the percentage.

## Static analysis

The same Python 3.11 quality lane runs pinned versions of:

```bash
python3 -m ruff check src/reprojudge
python3 -m mypy src/reprojudge
```

Ruff catches selected correctness and bug-risk classes in addition to syntax/import failures. Mypy checks the package's typed execution paths with untyped function bodies checked as well.

## Executable baseline versus scientific seed

These surfaces answer different questions and must not be conflated.

`benchmarks/scientific-seed/` contains 15 revision-pinned real-paper **repository-discovery** tasks. Its scope is paper-to-canonical-public-repository discovery only. It does not execute the referenced research repositories and does not establish scientific reproducibility. Repository URL golds are exact evaluator inputs; known canonical spellings have regression tests so upstream casing/rename drift cannot be silently normalized into a false oracle.

`benchmarks/executable-baseline/` contains three fixed, local, network-free tasks executed by `examples/executable_baseline_agent.py` through the real ReproJudge subprocess boundary. The baseline checks deterministic mean calculation, least-squares line fitting, and SHA-256 computation. It runs once from the source tree and again from the standalone export.

Passing the executable baseline demonstrates that the evaluator can deliver an agent-visible request, isolate the process environment as configured, collect artifacts, score private checks, record evidence, and produce passing result bundles for those fixed tasks. It **does not** prove arbitrary-paper reproducibility or scientific correctness.

Run the baseline directly with:

```bash
python3 scripts/run_executable_baseline.py --output .reprojudge/executable-baseline
```

## Workflow-free trust surface

This repository uses **no GitHub Actions workflows** by design. There is no hosted CI trigger, no scheduled drift job, and no hosted release audit. The local gates are the complete trust surface; tests lock that no workflow directory exists and that the public tree carries no stale workflow references.

## Local quality check

After installing the development dependencies, the authoritative local sequence is:

```bash
python3 -m pytest -q \
  --cov=reprojudge --cov-branch \
  --cov-report=term-missing \
  --cov-report=json:coverage.json
python3 scripts/check_coverage_thresholds.py coverage.json --statements 90 --branches 85
python3 -m ruff check src/reprojudge
python3 -m mypy src/reprojudge
python3 scripts/run_executable_baseline.py --output .reprojudge/executable-baseline
```

Formal release authority still comes from the standalone release measurement and source-bound release evidence, not from a local convenience run.
