#!/usr/bin/env bash
# Model-free arithmetic: exactly what C-DECODE would meter under the machinery's
# own accounting, against the registered audio ceiling. Zero contact.
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"
python - "$1" <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
import flight_identity as fid
from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.data.lock import data_root
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F

attempt = sys.argv[1]
root = data_root()
store = AttemptStore(attempts_root=root / "attempts")
handle = store.handle(F.PROBE_ID, attempt)
calls, audio = handle.actual_totals()
total_calls, total_audio = store.prior_actual_usage(F.PROBE_ID, exclude_attempt_id=None)

one_pass = 182.259
per_call = one_pass / F.QUERY_N
print("=== durable spend so far (7 embedding arms + 12 gate contacts) ===")
print(f"  this attempt : {calls} calls, {audio:.6f} audio-seconds")
print(f"  all attempts : {total_calls} calls, {total_audio:.6f} audio-seconds")
print()
print("=== registered ceilings ===")
print(f"  calls {F.CEILING_CALLS} | audio {F.CEILING_AUDIO_SECONDS} | gpu {F.CEILING_GPU_HOURS}")
print()
print("=== what C-DECODE would meter ===")
print("  rails.core_client.FrozenCoreClient.complete() resolves audio_seconds from the payload")
print("  BINDING for the named sample -- for a TEXT-ONLY request too (text_only_sample_id branch:")
print("  'audio_seconds, sample_rate_hz = self._binding.sample_facts[sample_id]'), and")
print("  core.model.adapter charges exactly that per request. A C-DECODE pass over the frozen 60")
print("  therefore meters a FULL corpus pass on EITHER modality.")
print()
print(f"  60 C-DECODE requests      : {one_pass:.3f} s")
print(f"  1 determinism resend      : {per_call:.3f} s")
print(f"  already spent             : {total_audio:.3f} s")
need = total_audio + one_pass + per_call
print(f"  TOTAL if C-DECODE flies   : {need:.3f} s")
print(f"  registered ceiling        : {F.CEILING_AUDIO_SECONDS} s")
print(f"  OVER BY                   : {need - F.CEILING_AUDIO_SECONDS:.3f} s")
print(f"  headroom remaining        : {F.CEILING_AUDIO_SECONDS - total_audio:.3f} s")
print(f"  requests affordable       : {int((F.CEILING_AUDIO_SECONDS - total_audio) / per_call)} of 60")
print()
print("=== registration cost line ===")
print("  'Ceilings: <=4,500 calls; <=700 metered audio-seconds (3x182.26 planned); <=0.5 GPU-h.'")
print(f"  3 x 182.26 = {3*one_pass:.2f} s  -> the registration budgeted exactly THREE metered audio")
print("  passes (the three audio embedding arms) and never budgeted a C-DECODE pass at all.")
print(f"  A ceiling of {int(-(-(need)//1))} s (i.e. >= 4 x 182.26 + gate clips) would admit it.")
print()
print("=== C-DECODE contacts made so far ===")
run_dir = root / "runs" / F.PROBE_ID / attempt
for name in ("c-decode-responses.jsonl", "c-decode-outputs.jsonl"):
    p = run_dir / name
    n = len([l for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]) if p.is_file() else 0
    print(f"  {name}: {'ABSENT' if not p.is_file() else f'{n} rows'}")
state = json.loads((run_dir / "flight-state.json").read_text(encoding="utf-8"))
print("  flight-state c_decode key present:", "c_decode" in state)
print("  flight-state c_decode_modality_decision present:", "c_decode_modality_decision" in state)
PY
