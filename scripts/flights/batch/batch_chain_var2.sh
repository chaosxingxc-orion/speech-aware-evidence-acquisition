#!/bin/bash
# Thin registered VAR-2 queue: shared WSL driver, then complete derived scoring.
set -euo pipefail
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=$DATA
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
exec >> /home/chao/batch-chain-var2.out 2>&1
trap 'echo "VAR-2 chain failed at $(date -u +%FT%TZ); preserve attempts; no replay" >&2' ERR
COMMIT=$(cat /home/chao/var2-flight-commit.txt)
test ! -e "$DATA/locks/flight.lock"
test ! -e /home/chao/batch-STOP
test -z "$(git -C "$REPO" status --porcelain)"
if pgrep -f '[c]ore.flight.cli|[l]ease_cli|[b]ash .*/batch_driver.sh' >/dev/null; then
  echo "Another flight is alive; refuse"; exit 9
fi
git -C "$REPO" checkout -q --detach "$COMMIT"
test "$(git -C "$REPO" rev-parse HEAD)" = "$COMMIT"
$PY - <<'PYCODE'
import json, shutil
from pathlib import Path
h=Path('/home/chao')
r=Path('/home/chao/saea-worktrees/fable-batch-flight')
d=Path('/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data')
p=json.loads((r/'docs/readiness/2026-09-25-slurp-stage3-var2-v1/protocol-registered-v1.json').read_text())
a,s=p['cells']['arm'],p['cells']['smoke']
for cell in (a,s):
    assert not (d/'attempts'/cell['run_id']).exists(), 'Attempt already exists; refuse replay'
    assert not (d/'attempts'/cell['fit_run_id']).exists(), 'Fit attempt already exists; refuse replay'
closed=json.loads((d/'analysis/SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-READ-V1/report.json').read_text())
assert closed['rows']==625 and closed['primary']['no_admission_claim'] is True
archive=h/'var2-before-launch'
archive.mkdir()
for name in ['batch-queue.json','batch-status.jsonl','batch-done','batch-flight-commit.txt',
             'batch-smoke-1-worker.log','batch-smoke-1-lease.out']:
    if (h/name).exists():
        shutil.copy2(h/name,archive/name)
step=dict(order=1,short='var2',kind='cell',experiment=a['experiment'],cell=a['cell_id'],
 smoke_experiment=s['experiment'],smoke_cell=s['cell_id'],
 campaign_plan='configs/campaign/'+a['experiment']+'.json',
 run_id=a['run_id'],fit_run_id=a['fit_run_id'],gen_attempt_id=a['attempt_id'],
 smoke_run_id=s['run_id'],smoke_attempt_id=s['attempt_id'],
 expected_rows=625,contacts_per_row=7,ceiling_per_row=17,notool=True,
 owner='root-'+a['cell_id'])
(h/'batch-queue.json').write_text(json.dumps([step],indent=2)+'\n')
(h/'batch-status.jsonl').write_text('')
if (h/'batch-done').exists():
    (h/'batch-done').unlink()
PYCODE
printf '%s\n' "$COMMIT" > /home/chao/batch-flight-commit.txt
bash "$REPO/scripts/flights/batch/batch_driver.sh"
echo "VAR-2 derived complete scoring start $(date -u +%FT%TZ)"
cd "$REPO"
$PY -B scripts/analysis/stage3_rollout_score.py \
  --mode supply-variants --stage all --repo-root "$REPO" --data-root "$DATA" \
  --run SAEA-SLURP-STAGE3-VAR2-SUPPLY-VARIANTS-R01C-V1 \
  --attempt attempt-slurp-native-stage3-var2-supply-variants-r01c-v1-generation \
  --roster docs/receipts/rosters/slurp-stage3-construction-r01c.json \
  --scorer-id slurp-slu-official-train \
  --analysis-root "$DATA/analysis/SAEA-SLURP-STAGE3-VAR2-SUPPLY-READ-V1"
echo "VAR-2 generation and scoring complete $(date -u +%FT%TZ)"
