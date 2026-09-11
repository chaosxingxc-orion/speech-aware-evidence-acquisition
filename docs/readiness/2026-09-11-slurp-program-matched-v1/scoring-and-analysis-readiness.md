# Program-matched SLURP scoring and analysis readiness

**Status: HELD before launch, scoring, and result reading.** This folder prepares the unchanged G6 analysis for the owner-approved program-matched pair. It does not authorize a model, tokenizer, scorer, reference, or result contact. The historical G6 system remains not admitted after its NEW500 scenario guard changed by minus 0.2 percentage points.

## Fixed identities and accounting

The control generation is `SAEA-SLURP-LIVE-PROGRAM-MATCHED-CONTROL-V1`, attempt `attempt-live-program-matched-control-generation-v1`, with derivative `live-program-matched-control-delivery-v1`. The speech generation is `SAEA-SLURP-LIVE-PROGRAM-MATCHED-SPEECH-V1`, attempt `attempt-live-program-matched-speech-generation-v1`, with derivative `live-program-matched-speech-delivery-v1`.

Both arms use the same program identity and generate independent complete first-stage answers. No historical answer and no answer shared across arms may be used. The pair plans 4,000 generation contacts with a 4,200 ceiling, 12,004 live-fit endpoints, a 1.0 utilization-GPU-hour family ceiling with 0.5 per arm, and 6,000 speech seconds per arm.

The analysis plan is `analysis-plan.json`, SHA-256 `471e0d7ab6f900b5f2f31a6a7c74dd4d0d7bda22471f1db82da53141e20c5893`. It retains every numerical, population, estimand, bootstrap, seed, interval, weighting, guard, stopping, cost-reporting, and attribution definition from the original G6 plan. Only the comparison identity and purpose change.

## Deterministic deliveries

After both ordinary parents seal and verify, build each predeclared derivative through the shared public function:

```python
build_delivery_bundle(
    parent_manifest=Path(PARENT_MANIFEST),
    repo_root=Path(SOURCE),
    experiment_path=Path(EXPERIMENT_FRAGMENT),
    data_root=Path(DATA),
    derivative_cell_id=DELIVERY_CELL_ID,
    output_dir=Path(NEW_DERIVATIVE_DIRECTORY),
)
```

Use `live-program-matched-control-delivery-v1` and `live-program-matched-speech-delivery-v1` as the derivative cell identifiers. Verify both derivative bundles and record their exact manifest hashes. Keep both raw parents immutable.

## Complete scoring

`complete-score-jobs.template.jsonl`, SHA-256 `dd82931697eeec4f3c9ef4a492fc0bba5284134bbe5930b5753ab46f5d1518d6`, carries the two exact prospective derived-manifest paths. It is a held template until those manifests exist and root records the scoring release.

Run exactly one complete job at a time, with per-sample retention and without finalization or sharding:

The `score-batch` CLI does not accept explicit repository, data-root, or umbrella-lock arguments. Use the public batch API, matching the successful G6 score invocation, so every isolated scorer process receives the intended frozen checkout and pinned scoring environment:

```bash
export SOURCE=<root-frozen-program-matched-source>
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$SOURCE/src
export SPEECHRL_DATA_DIR=$DATA
/home/chao/.venvs/speechrl/bin/python -B - <<'PY'
import os
from pathlib import Path

from speech_aware_evidence_acquisition.core.scoring_batch import (
    ScoringContext,
    load_score_jobs,
    run_score_batch,
)

source = Path(os.environ["SOURCE"])
data = Path(os.environ["DATA"])
lock = Path(os.environ["LOCK"])
jobs = load_score_jobs(
    source
    / "docs/readiness/2026-09-11-slurp-program-matched-v1/complete-score-jobs.template.jsonl"
)
result = run_score_batch(
    jobs,
    output_dir=(
        data
        / "analysis/SAEA-SLURP-LIVE-PROGRAM-MATCHED-PAIRED-ANALYSIS-V1/complete-score-batch"
    ),
    max_workers=1,
    operation="score",
    include_per_sample=True,
    context=ScoringContext(
        repo_root=source,
        data_root=data,
        lock_path=lock,
    ),
)
if result["job_count"] != 2 or result["succeeded"] != 2 or result["failed"] != 0:
    raise SystemExit("the two complete official score jobs did not both succeed exactly once")
PY
```

The job file contains two jobs, so this invocation processes them sequentially. Do not use `--finalize`. Before starting, require both complete derivative manifests, a new output directory, and a root-recorded score release. If either job fails or is incomplete, stop without rerunning.

## Saved-score comparison

`paired-score-analysis.template.json`, SHA-256 `7a6fee6619f1b7f15f7de434ea55dc91d8a1833dee9ba2e6e209c57d989667fc`, preserves the existing comparator schema and frozen definitions. Its `AWAITING_*` values deliberately make it non-executable. After scoring completes, create an immutable bound successor that replaces each pending manifest, score, and complete-score-receipt hash with the measured value. Do not alter any other analysis field.

Then, only after root records the result-read release, run the existing saved-score comparator:

```bash
SOURCE=<same-root-frozen-program-matched-source>
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$SOURCE/src SPEECHRL_DATA_DIR=$DATA \
/home/chao/.venvs/speechrl/bin/python -B \
  -m speech_aware_evidence_acquisition.analysis.score_compare_cli \
  --config $SOURCE/docs/readiness/2026-09-11-slurp-program-matched-v1/paired-score-analysis.bound.json \
  --output $DATA/analysis/SAEA-SLURP-LIVE-PROGRAM-MATCHED-PAIRED-ANALYSIS-V1/paired-contrasts.json
```

The bound filename is prospective and must be created only after the two first complete score receipts exist. The comparator verifies pinned bundles and saved scores and invokes no scorer. Preserve NEW500 as primary, OLD500 and DEV1000 as reporting populations, speaker-cluster 10,000-resample CI90 with seed 20260903, inherited row sensitivity, pooled micro SLU-F1, equal-scenario reporting, all protection guards, and the no-adaptive-rerun stopping rule.

## Closure conditions

Keep generation, scoring, and result-read gates held until their preceding evidence exists. Record all fit, generation, service, preparation, barrier, delivery, score-tail, retry, saturation, malformed-output, and utilization costs. If the inherited guards fail, retain the result and stop this comparison. The new comparison cannot erase or reinterpret the prior failed G6 decision.