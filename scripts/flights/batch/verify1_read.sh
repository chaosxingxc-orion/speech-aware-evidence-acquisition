#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Read the completed selector using pinned source counts, no new official scoring.
set -euo pipefail
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=$SAEA_DATA_ROOT
PY=/home/chao/.venvs/speechrl/bin/python
RUN=${VERIFY1_RUN_ID:-SAEA-SLURP-STAGE3-VERIFY-1-V1}
ATTEMPT=${VERIFY1_ATTEMPT_ID:-attempt-slurp-native-stage3-verify-1-v1-generation}
OUT=${VERIFY1_READ_ID:-SAEA-SLURP-STAGE3-VERIFY-1-READ-V1}
export PYTHONPATH=$MAIN/src PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2
exec "$PY" "$MAIN/scripts/analysis/slurp_verifier_selection_read.py" \
 --repo-root "$MAIN" --data-root "$DATA" --expected-run-id "$RUN" \
 --manifest "runs/$RUN/$ATTEMPT/$RUN.run-manifest.json" \
 --source-manifest runs/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1/attempt-slurp-native-stage3-rollout-r01-generation-v1/SAEA-SLURP-STAGE3-ROLLOUT-R01-V1.run-manifest.json \
 --receipt docs/receipts/verify1/slurp-stage3-verify-1-material-v1.json \
 --expected-receipt-sha256 e8154290564f6adb653c8200e2fc97ee676a5a1433c6bc79fa9516bf4743f5f5 \
 --roster docs/receipts/rosters/slurp-stage3-construction-r01c.json \
 --source-score-root analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1 \
 --out-root "analysis/$OUT" \
 --intent-ni-margin-pp 1.44 --draws 10000 --seed 20260915
