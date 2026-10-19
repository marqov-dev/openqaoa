# Restoring the local OpenQAOA core

Marqov uses OpenQAOA to explore QAOA experiments and is contributing a bounded
restoration so others can run and inspect those experiments. OpenQAOA was created
by Entropica Labs. This fork preserves its authorship, notices and MIT license.
It does not imply an agreed partnership or endorsement by Entropica Labs.

## Supported candidate

The first candidate, `openqaoa-core==0.2.6+marqov.1`, targets CPython 3.11 and
3.12 on Linux and macOS. CI builds a source distribution, builds a wheel from
that distribution, installs the wheel, checks imports outside the checkout,
and runs the core suite and the local MaxCut experiment.

Covered functionality includes built-in statevector simulation, the depth-one
analytical simulator, QAOA/RQAOA, parametrizations, optimizers, problem encodings
and result serialization. MaxCut zero edge weights are preserved, with an
exhaustive small weighted-graph energy check. Analytical and statevector energies
are compared independently for seeded, weighted instances.

The numerical compatibility window is intentionally bounded:

| Dependency | Candidate requirement | Reason |
| --- | --- | --- |
| NumPy | `>=1.26.4,<2` | Python 3.12 support; NumPy 2 migration is deferred. |
| SciPy | `>=1.11.2,<1.14` | Preserves the existing optimizer set and numerical regressions. SciPy 1.14 adds COBYQA to a private list used by this code; newer COBYLA changes also fail existing workflow regressions. |
| NetworkX | `>=3.2.1,<3.3` | Preserves seeded graph ordering used by the RQAOA regression fixture. A newer version produced a different bitstring for that fixture. |

These bounds are compatibility decisions, not a claim that all dependency versions
have been validated. Each CI artifact records the exact resolved environment.
Broad dependency modernization, including removal of private SciPy APIs and making
seeded graph fixtures independent of NetworkX ordering, is follow-up work.

## Install and reproduce

```bash
git clone https://github.com/marqov-dev/openqaoa.git
cd openqaoa
# For the review candidate, check out codex/core-restoration before installing.
git checkout codex/core-restoration
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip build
python -m build src/openqaoa-core --outdir dist
python -m pip install dist/*.whl pytest==8.4.2 plotly
python -m pip check
python -m pytest src/openqaoa-core/tests tests/test_core_restoration.py \
  -m 'not (cplex or qpu or sim or qvm or api or docker_aws or braket_api or notebook)' -q -rs
python examples/core_maxcut.py
```

The test selection excludes external services, hardware, proprietary CPLEX and
notebook execution. Plugin-specific cases also skip when their optional backend
is absent. This is core evidence, not evidence that the provider stack works.
The workflow requires no secrets and submits no quantum jobs. The inherited
provider, publishing and legacy CI jobs are guarded to run only in the upstream
repository. This fork's active workflow is `.github/workflows/core.yml`.

`examples/core_maxcut.py` runs six bounded, seeded trials on a six-vertex triangular
prism, compares depths one and two, and checks optimized energies against the
full statevector distribution and the classical MaxCut objective. It also reports
exhaustive, greedy and seeded random-search baselines. Expected QAOA cut and best
classical cut are different statistics, and budgets are not matched. This tiny
simulated experiment makes **no quantum-advantage claim**.

## Scope and maintenance

The root `openqaoa` metapackage and the Azure, Braket, PyQuil and Qiskit plugins
retain their upstream metadata and are **not supported by this candidate**.
Their presence in the repository is not evidence of compatibility. Do not use
the historical `make local-install` or root `pip install .` path for this core.
Windows, Python 3.13+, NumPy 2, provider API migrations, Mitiq ZNE, hardware runs,
and full notebook/documentation builds need separate validation.

ZNE dependencies now load only when constructing `ZNEWrapper`. Missing optional
dependencies give an actionable error instead of breaking core imports. This is
dependency isolation; it does not establish a working modern ZNE/provider combination.
The error-mitigation wrapper tests are not a substitute for that integration work.

The local version suffix distinguishes this source/wheel candidate from upstream
0.2.6. It is not a public PyPI release plan. Package publishing and release tags
remain separate review decisions; the inherited upstream publishing job is disabled
in this fork by its repository guard.

The initial maintenance commitment is the documented core restoration, its tests,
and reproducible evidence. New providers or additional Python/dependency targets
require a scoped proposal and tests. Issues should include the candidate commit,
Python and dependency versions, a small reproducer and whether a built-in backend
is used. Please open restoration issues and PRs on the Marqov fork rather than
directing support requests for these changes to Entropica Labs.

Keep patches small enough to offer upstream: core dependency isolation and the
MaxCut correctness fix can be reviewed independently of this fork's metadata and CI
policy. Any upstream PRs or coordination with Entropica Labs will be separate,
explicit actions. If upstream resumes maintenance, prefer contributing and moving
users back to its supported release over growing an independent provider ecosystem.

The Marqov orchestration demo, Capsule evidence and Loom spike live outside this
restoration. No Marqov runtime dependency is added to OpenQAOA.
