#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Thin registered VAR-2 queue: shared WSL driver, then complete derived scoring.
set -euo pipefail
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=$DATA
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
PROFILE=initial
if [ "$#" -gt 0 ]; then PROFILE=$1; fi
case "$PROFILE" in
  initial)
    export VAR2_PROTOCOL=docs/readiness/2026-09-25-slurp-stage3-var2-v1/protocol-registered-v1.json
    export VAR2_ARCHIVE=var2-before-launch VAR2_SHORT=var2
    export VAR2_READ_ID=SAEA-SLURP-STAGE3-VAR2-SUPPLY-READ-V1
    PIN=/home/chao/var2-flight-commit.txt
    CHAIN_LOG=/home/chao/batch-chain-var2.out
    ;;
  recovery)
    export VAR2_PROTOCOL=docs/readiness/2026-09-25-slurp-stage3-var2-recovery-v1/protocol-registered-v1.json
    export VAR2_ARCHIVE=var2-recovery-before-launch VAR2_SHORT=var2-recovery
    export VAR2_READ_ID=SAEA-SLURP-STAGE3-VAR2-RECOVERY-SUPPLY-READ-V1
    PIN=/home/chao/var2-recovery-flight-commit.txt
    CHAIN_LOG=/home/chao/batch-chain-var2-recovery.out
    ;;
  *) echo "Unknown VAR-2 launch profile" >&2; exit 2 ;;
esac
exec >> "$CHAIN_LOG" 2>&1
trap 'echo "VAR-2 chain failed at $(date -u +%FT%TZ); preserve attempts; no replay" >&2' ERR
COMMIT=$(cat "$PIN")
test ! -e "$DATA/locks/flight.lock"
test ! -e /home/chao/batch-STOP
test -z "$(git -C "$REPO" status --porcelain)"
if pgrep -f '[c]ore.flight.cli|[l]ease_cli|[b]ash .*/batch_driver.sh' >/dev/null; then
  echo "Another flight is alive; refuse"; exit 9
fi
git -C "$REPO" checkout -q --detach "$COMMIT"
test "$(git -C "$REPO" rev-parse HEAD)" = "$COMMIT"
$PY - <<'PYCODE'
import json, os, shutil
from pathlib import Path
h=Path('/home/chao')
r=Path('/home/chao/saea-worktrees/fable-batch-flight')
d=Path(__import__('os').environ['SAEA_DATA_ROOT'])
p=json.loads((r/os.environ['VAR2_PROTOCOL']).read_text())
a,s=p['cells'].get('arm',p['cells'].get('full')),p['cells']['smoke']
for cell in (a,s):
    assert not (d/'attempts'/cell['run_id']).exists(), 'Attempt already exists; refuse replay'
    assert not (d/'attempts'/cell['fit_run_id']).exists(), 'Fit attempt already exists; refuse replay'
closed=json.loads((d/'analysis/SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-READ-V1/report.json').read_text())
assert closed['rows']==625 and closed['primary']['no_admission_claim'] is True
archive=h/os.environ['VAR2_ARCHIVE']
archive.mkdir()
for name in ['batch-queue.json','batch-status.jsonl','batch-done','batch-flight-commit.txt',
             'batch-smoke-1-worker.log','batch-smoke-1-lease.out']:
    if (h/name).exists():
        shutil.copy2(h/name,archive/name)
step=dict(order=1,short=os.environ['VAR2_SHORT'],kind='cell',experiment=a['experiment'],cell=a['cell_id'],
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
$PY - <<'PYCODE'
import json, os, subprocess
from pathlib import Path
r=Path('/home/chao/saea-worktrees/fable-batch-flight')
d=Path(__import__('os').environ['SAEA_DATA_ROOT'])
p=json.loads((r/os.environ['VAR2_PROTOCOL']).read_text())
a=p['cells'].get('arm',p['cells'].get('full'))
subprocess.run([
 '/home/chao/.venvs/speechrl/bin/python','-B','scripts/analysis/stage3_rollout_score.py',
 '--mode','supply-variants','--stage','all','--repo-root',str(r),'--data-root',str(d),
 '--run',a['run_id'],'--attempt',a['attempt_id'],
 '--roster','docs/receipts/rosters/slurp-stage3-construction-r01c.json',
 '--scorer-id','slurp-slu-official-train',
 '--analysis-root',str(d/'analysis'/os.environ['VAR2_READ_ID']),
],cwd=r,check=True)
PYCODE
echo "VAR-2 generation and scoring complete $(date -u +%FT%TZ)"
