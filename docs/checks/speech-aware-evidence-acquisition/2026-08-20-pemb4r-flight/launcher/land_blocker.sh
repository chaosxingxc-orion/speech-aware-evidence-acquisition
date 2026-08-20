#!/usr/bin/env bash
# Land the C-DECODE ceiling blocker into this attempt's flight state, and
# SUPERSEDE the modality-decision block's own affordability claim, which was
# computed under a wrong assumption about how a frozen-core TEXT-ONLY request
# meters speech audio. Model-free, zero contact.
# Usage: land_blocker.sh <attempt_id>
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

if pgrep -f "python .*launch_pemb4r" >/dev/null; then
  echo "REFUSING: a launcher stage is in flight"; exit 2
fi

python - "$1" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, ".")
import flight_identity as fid
import launch_pemb4r_flight as L
from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.data.lock import data_root
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F

attempt = sys.argv[1]
root = data_root()
run_dir = root / "runs" / F.PROBE_ID / attempt
state = L.FlightState(run_dir / "flight-state.json")
if "c_decode" in state.document:
    raise SystemExit("REFUSING: C-DECODE completed; there is no blocker to record")

store = AttemptStore(attempts_root=root / "attempts")
total_calls, total_audio = store.prior_actual_usage(F.PROBE_ID, exclude_attempt_id=None)
one_pass = float(state.document["one_pass_metered_audio_seconds"])
per_call = one_pass / F.QUERY_N
needed = one_pass + per_call
would_total = total_audio + needed

blocker = {
    "status": "NOT-FLOWN-CEILING-BLOCKED",
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "contacts_made": 0,
    "evidence_of_zero_contacts": [
        "c-decode-responses.jsonl absent from the run dir",
        "c-decode-outputs.jsonl absent from the run dir",
        "no 'c_decode' block in this flight state",
        "the refusal came from FrozenCoreClient.__init__ (core.model.lifecycle."
        "_open_gate_and_attempt), strictly BEFORE any request could be built",
    ],
    "first_refusal": (
        "FrozenCoreError: attempt accounting refused -- core.model.FrozenCoreAdapter opens its OWN "
        "durable attempt for plan.attempt_id (invariant I6, a one-time (run_id, attempt_id) key), "
        "and this attempt_id was already opened by the embedding preflight. Resolvable by minting a "
        "sibling attempt id for the C-DECODE plan; that is NOT the blocker below."
    ),
    "blocker": "registered metered-audio ceiling",
    "why": (
        "rails.core_client.FrozenCoreClient.complete() resolves audio_seconds from the payload "
        "BINDING for the named sample, including on the text-only branch "
        "('audio_seconds, sample_rate_hz = self._binding.sample_facts[sample_id]'), and "
        "core.model.adapter charges exactly that per request before the request leaves the process. "
        "A C-DECODE pass over the frozen 60 therefore meters a FULL corpus audio pass on EITHER "
        "modality -- the transcript modality does not reduce metered speech audio, because the "
        "request is still, honestly, about that bound sample's speech_ref. The budget-forced "
        "text-modality fallback the coordinator ratified cannot save the pass, and neither can the "
        "winner arm happening to be a text arm (it is: t-glap)."
    ),
    "arithmetic": {
        "already_spent_audio_seconds": total_audio,
        "one_metered_pass_seconds": one_pass,
        "c_decode_60_requests_seconds": one_pass,
        "c_decode_determinism_resend_seconds": per_call,
        "total_if_c_decode_flies": would_total,
        "registered_ceiling_seconds": F.CEILING_AUDIO_SECONDS,
        "over_by_seconds": would_total - F.CEILING_AUDIO_SECONDS,
        "headroom_remaining_seconds": F.CEILING_AUDIO_SECONDS - total_audio,
        "requests_affordable_of_60": int((F.CEILING_AUDIO_SECONDS - total_audio) / per_call),
    },
    "registration_gap": (
        "Registration section 5 reads 'Ceilings: <=4,500 calls; <=700 metered audio-seconds "
        "(3x182.26 planned); <=0.5 GPU-h.' 3x182.26 = 546.78 s is exactly the THREE audio embedding "
        "arms. The cost line never budgeted a metered pass for C-DECODE's own 60 frozen-core "
        "requests, which the machinery's accounting charges as a fourth pass. The ceiling and the "
        "arm set are therefore jointly unsatisfiable once all three audio arms fly -- a registration "
        "defect that can only surface at contact time."
    ),
    "action_taken": (
        "REFUSED to fly, fail-closed. No partial C-DECODE was attempted: 45 of 60 requests would fit "
        "the headroom, but a truncated closed-set decode is a different experiment than the one "
        "registered and would poison the paired comparison. Everything else this flight owes -- all "
        "seven embedding arms, all four banks, and the gold-free retrieval plan -- is complete and "
        "landed."
    ),
    "what_would_unblock": (
        "An owner/coordinator amendment raising the registered metered-audio ceiling to >= 747 s "
        "(4 x 182.259 + 14 s of synthetic non-corpus gate clips = 746.08 s), or an explicit "
        "re-registration of how a frozen-core text-only request meters speech audio. On the calls "
        "and GPU axes there is ample room: 4031/4500 calls and well under 0.5 GPU-h. C-DECODE would "
        "then fly as a follow-on against a FRESH sibling attempt id (which the FrozenCoreAdapter "
        "requires in any case), reusing this attempt's own retrieval plan by hash."
    ),
    "retrieval_plan_sha256_for_followon": state.document["retrieval_plan"]["sha256"],
    "winner_arm_id_for_followon": state.document["retrieval_plan"]["winner_arm_id"],
    "coordinator_pre_contact_ruling": fid.COORDINATOR_PRE_CONTACT_RULING,
}
state.put("c_decode_blocked", blocker)

decision = dict(state.document.get("c_decode_modality_decision") or {})
decision["superseded_by"] = "c_decode_blocked"
decision["superseded_note"] = (
    "The 'metered_audio_needed_for_audio_modality' figure in this block assumed a text-modality "
    "C-DECODE request meters a negligible sentinel, as an EMBEDDING text contact does. That is "
    "wrong for a FROZEN-CORE request: core_client resolves audio_seconds from the sample binding on "
    "the text-only branch too. The corrected arithmetic is in c_decode_blocked, and no contact was "
    "made under the wrong figure -- the stage refused before building a single request."
)
state.put("c_decode_modality_decision", decision)

print(json.dumps(blocker, indent=2, sort_keys=True))
PY
