#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Independent local continuation. Wait for VAR-1 sealing, then smoke and VERIFY-1.
# The owner approved these cells. No assistant, network, or credit-based scheduler.
set -euo pipefail
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
PY=/home/chao/.venvs/speechrl/bin/python
SP=$MAIN/scripts/flights/batch
export PYTHONPATH=$MAIN/src PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
exec >> /home/chao/batch-chain-verify1.out 2>&1
COMMIT=$(cat /home/chao/verify1-flight-commit.txt)
echo "waiting for VAR-1 $(date -u +%FT%TZ), next commit $COMMIT"
while [ ! -f /home/chao/batch-done ]; do
  test ! -f /home/chao/batch-STOP
  if ! pgrep -f '[b]ash .*/batch_driver.sh' >/dev/null; then
    echo "predecessor driver absent without completion; stop"; exit 9
  fi
  sleep 10
done
# The marker is necessary but insufficient: bind it to the actual predecessor queue.
$PY - <<'PYCODE'
import json
from pathlib import Path
home=Path('/home/chao')
queue=json.loads((home/'batch-queue.json').read_text())
assert len(queue)==6 and queue[-1]['short']=='var1perk16c5'
events=[json.loads(line) for line in (home/'batch-status.jsonl').read_text().splitlines()]
assert not any(e['event']=='STOP' for e in events)
done={e['detail']['short'] for e in events if e['event']=='step-done'}
assert done=={s['short'] for s in queue}
assert events[-1]['event']=='driver-done'
data=Path(__import__('os').environ['SAEA_DATA_ROOT'])
for s in queue:
    attempt=json.loads((data/'attempts'/s['run_id']/(s['gen_attempt_id']+'.json')).read_text())
    assert attempt['state']=='FINALIZED'
PYCODE
while pgrep -f '[c]ore.flight.cli|[b]ash .*/batch_driver.sh' >/dev/null; do sleep 2; done
test ! -e "$DATA/locks/flight.lock"
test -z "$(git -C "$REPO" status --porcelain)"
git -C "$REPO" checkout -q --detach "$COMMIT"
test "$(git -C "$REPO" rev-parse HEAD)" = "$COMMIT"
# Preserve the entire predecessor queue and all local status events.
ARCHIVE=/home/chao/var1-before-verify1
mkdir "$ARCHIVE"
for name in batch-queue.json batch-status.jsonl batch-done batch-flight-commit.txt; do
  cp "/home/chao/$name" "$ARCHIVE/$name"
done
$PY - <<'PYCODE'
import json
from pathlib import Path
h=Path('/home/chao')
c='slurp-native-stage3-verify-1-v1'
smoke='slurp-native-stage3-verify-1-smoke-4-v1'
step=dict(order=1,short='verify1',kind='cell',experiment=c,cell=c,
 smoke_experiment=smoke,smoke_cell=smoke,
 campaign_plan='configs/campaign/'+c+'.json',
 run_id='SAEA-SLURP-STAGE3-VERIFY-1-V1',
 fit_run_id='SAEA-SLURP-STAGE3-VERIFY-1-FIT-V1',
 gen_attempt_id='attempt-'+c+'-generation',
 smoke_run_id='SAEA-SLURP-STAGE3-VERIFY-1-SMOKE-4-V1',
 smoke_attempt_id='attempt-'+smoke+'-generation',
 expected_rows=625,contacts_per_row=1,ceiling_per_row=2,notool=True,owner='root-'+c)
(h/'batch-queue.json').write_text(json.dumps([step],indent=2)+'\n')
(h/'batch-status.jsonl').write_text('')
(h/'batch-done').unlink()
PYCODE
printf '%s\n' "$COMMIT" > /home/chao/batch-flight-commit.txt
# Registered, model-free VAR-1 analysis can overlap independent VERIFY-1 generation.
(SAEA_ANALYSIS_SUFFIX=-CORRECTED-V2 bash "$SP/var1_read.sh" variant \
  > /home/chao/var1-variant-read-corrected-v2.log 2>&1) &
ANALYSIS_PID=$!
echo "VERIFY-1 driver start $(date -u +%FT%TZ)"
set +e
bash "$SP/batch_driver.sh"
RC=$?
wait "$ANALYSIS_PID"
ANALYSIS_RC=$?
set -e
echo "generation exit $RC; VAR-1 read exit $ANALYSIS_RC"
test "$RC" -eq 0
# The selector read consumes sealed counts only; no scorer or model is called.
bash "$SP/verify1_read.sh"
echo "continuation completed $(date -u +%FT%TZ)"
