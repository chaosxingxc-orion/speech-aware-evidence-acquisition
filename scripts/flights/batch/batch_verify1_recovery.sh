#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Only the diagnosed zero-contact fit-count recovery. No network or assistant.
set -euo pipefail
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
PY=/home/chao/.venvs/speechrl/bin/python
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
exec >> /home/chao/batch-verify1-recovery.out 2>&1
COMMIT=$(cat /home/chao/verify1-recovery-flight-commit.txt)
test ! -e "$DATA/locks/flight.lock"
test -z "$(git -C "$REPO" status --porcelain)"
if pgrep -f '[c]ore.flight.cli|[l]ease_cli|[b]ash .*/batch_driver.sh' >/dev/null; then
  echo "Another flight is alive; refuse"; exit 9
fi
$PY - <<'PYCODE'
import hashlib,json,shutil
from pathlib import Path
h=Path('/home/chao')
r=Path('/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition')
d=Path(__import__('os').environ['SAEA_DATA_ROOT'])
proof=json.loads((r/'docs/receipts/continuation/2026-09-25-verify1-fit-count-recovery.json').read_text())
for name,item in proof['evidence'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==item['sha256'],name
assert proof['generation_contacts']==proof['tokenizer_contacts']==0
archive=h/'verify1-before-fit-count-recovery'
archive.mkdir()
for name in ['batch-queue.json','batch-status.jsonl','batch-STOP','batch-flight-commit.txt',
             'batch-smoke-1-worker.log','batch-smoke-1-lease.out']:
    shutil.copy2(h/name,archive/name)
c='slurp-native-stage3-verify-1-recovery-v1'
s='slurp-native-stage3-verify-1-recovery-smoke-4-v1'
run='SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-V1'
smoke_run='SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-SMOKE-4-V1'
assert not (d/'attempts'/run).exists()
assert not (d/'attempts'/smoke_run).exists()
step=dict(order=1,short='verify1recovery',kind='cell',experiment=c,cell=c,
 smoke_experiment=s,smoke_cell=s,campaign_plan='configs/campaign/'+c+'.json',
 run_id=run,fit_run_id='SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-FIT-V1',
 gen_attempt_id='attempt-'+c+'-generation',smoke_run_id=smoke_run,
 smoke_attempt_id='attempt-'+s+'-generation',
 expected_rows=625,contacts_per_row=1,ceiling_per_row=2,notool=True,owner='root-'+c)
(h/'batch-queue.json').write_text(json.dumps([step],indent=2)+'\n')
(h/'batch-status.jsonl').write_text('')
(h/'batch-STOP').unlink()
PYCODE
git -C "$REPO" checkout -q --detach "$COMMIT"
test "$(git -C "$REPO" rev-parse HEAD)" = "$COMMIT"
printf '%s\n' "$COMMIT" > /home/chao/batch-flight-commit.txt
bash "$MAIN/scripts/flights/batch/batch_driver.sh"
VERIFY1_RUN_ID=SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-V1 \
VERIFY1_ATTEMPT_ID=attempt-slurp-native-stage3-verify-1-recovery-v1-generation \
VERIFY1_READ_ID=SAEA-SLURP-STAGE3-VERIFY-1-RECOVERY-READ-V1 \
bash "$MAIN/scripts/flights/batch/verify1_read.sh"
echo "VERIFY-1 recovery complete $(date -u +%FT%TZ)"
