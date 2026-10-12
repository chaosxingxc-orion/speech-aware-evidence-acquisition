#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# One-shot continuation after the 2026-09-25 external process termination.
# The six-step queue retains completed steps. Skip only the already sealed smoke.
# Refuse any opened final arm, previous continuation, live flight, or changed checkout.
set -euo pipefail
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
PY=/home/chao/.venvs/speechrl/bin/python
SP=$MAIN/scripts/flights/batch
COMMIT=3ade29ffe2342ee65de47b6913990bd15fdcc24d
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
exec >> /home/chao/batch-continue-var1-unopened.out 2>&1
echo "continuation start $(date -u +%FT%TZ)"
test "$(git -C "$REPO" rev-parse HEAD)" = "$COMMIT"
test -z "$(git -C "$REPO" status --porcelain)"
test ! -e "$DATA/locks/flight.lock"
if pgrep -f '[c]ore.flight.cli|[b]atch_driver.sh' >/dev/null; then
  echo "a flight is alive; refuse"; exit 7
fi
$PY "$SP/batch_inspect.py" "$DATA" SAEA-SLURP-STAGE3-VAR1-SMOKE-4-V1 \
  attempt-slurp-native-stage3-var1-smoke-4-v1-generation smoke 4 11 1 "$COMMIT"
$PY - <<'PYCODE'
from pathlib import Path
import hashlib, json, os
home=Path('/home/chao')
data=Path(__import__('os').environ['SAEA_DATA_ROOT'])
queue=home/'batch-queue.json'
raw=queue.read_bytes()
steps=json.loads(raw)
assert len(steps)==6 and steps[-1]['short']=='var1perk16c5'
last=steps[-1]
assert not (data/'attempts'/last['run_id']).exists(), 'arm already opened'
assert not (data/'runs'/last['run_id']).exists(), 'arm outputs already exist'
assert not (data/'attempts'/last['fit_run_id']).exists(), 'arm fit already opened'
assert not (home/'batch-STOP').exists(), 'failure requires diagnosis'
events=[json.loads(line) for line in (home/'batch-status.jsonl').read_text().splitlines()]
done={event['detail']['short'] for event in events if event['event']=='step-done'}
assert done=={step['short'] for step in steps[:-1]}, 'completed steps differ'
assert any(event['event']=='smoke-inspect' and event['detail'].get('pass') is True
           and event['detail'].get('run_id')==last['smoke_run_id'] for event in events)
# Exclusive creation prevents replaying this orchestration correction.
backup=home/'batch-queue.pre-continuation-20260925.json'
with backup.open('xb') as fh: fh.write(raw)
for key in ('smoke_experiment','smoke_cell','smoke_run_id','smoke_attempt_id'):
    last[key]=None
new=(json.dumps(steps,indent=2)+'\n').encode()
temporary=queue.with_suffix('.continuation.tmp')
with temporary.open('xb') as fh: fh.write(new)
os.replace(temporary,queue)
receipt={'schema':'saea-unopened-arm-continuation-v1',
         'original_queue_sha256':hashlib.sha256(raw).hexdigest(),
         'continued_queue_sha256':hashlib.sha256(new).hexdigest(),
         'completed_steps_preserved':sorted(done),
         'unopened_arm':last['run_id'],
         'reason':'External process termination before attempt creation; sealed smoke reused.',
         'service_process_boundary':True,
         'automatic_recovery':False}
with (home/'var1-unopened-continuation-receipt.json').open('x') as fh:
    json.dump(receipt,fh,indent=2)
print(json.dumps(receipt))
PYCODE
test "$(cat /home/chao/batch-flight-commit.txt)" = "$COMMIT"
exec bash "$SP/batch_driver.sh"
