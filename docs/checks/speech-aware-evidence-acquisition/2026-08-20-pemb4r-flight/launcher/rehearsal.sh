#!/usr/bin/env bash
# Launcher REHEARSAL against a TEMP data root and MOCK clients. ZERO model
# contact, zero server, zero GPU, and nothing is written under
# $SPEECHRL_DATA_DIR. It exercises exactly the launcher-owned glue the pinned
# unit suite does not cover: the BudgetedCachingProxy, the bank/arm sweep
# wiring, resume replay, the retrieval-plan stage's own construction stats, and
# the C-DECODE call path.
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"
python - <<'PY'
import json, shutil, struct, sys, tempfile, wave
from pathlib import Path

sys.path.insert(0, ".")
import flight_identity as fid
import launch_pemb4r_flight as L

from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.rails.adapters.slurp import AudioRef, SlurpSample
from speech_aware_evidence_acquisition.rails.core_client import MockCoreClient
from speech_aware_evidence_acquisition.rails.embedding_client import MockEmbeddingClient
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F
from speech_aware_evidence_acquisition.rails.probes.pkey_flight import build_transcript_record

tmp = Path(tempfile.mkdtemp(prefix="pemb4r-rehearsal-"))
print("temp root:", tmp)

# ---- synthetic, NON-CORPUS audio + samples --------------------------------
def tiny_wav() -> bytes:
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as h:
        h.setnchannels(1); h.setsampwidth(2); h.setframerate(16000)
        h.writeframes(b"".join(struct.pack("<h", 0) for _ in range(1600)))
    return buf.getvalue()

media_dir = tmp / "datasets" / "rehearsal"
media_dir.mkdir(parents=True, exist_ok=True)
samples = []
transcripts = {}
for i in range(F.QUERY_N):
    rel = f"datasets/rehearsal/clip-{i:03d}.wav"
    (tmp / rel).write_bytes(tiny_wav())
    sid = f"rehearsal-{i:03d}"
    samples.append(
        SlurpSample(
            sample_id=sid, audio_ref=AudioRef(path=str(tmp / rel), sha256="0" * 64), audio_seconds=0.1,
            utterance_id=sid, media_relpath=rel, scenario="", action="", intent="", entities=(),
        )
    )
    transcripts[sid] = build_transcript_record(sid, f"rehearsal transcript {i}")

# ---- small synthetic bank -------------------------------------------------
entries = []
import hashlib
for label in ("alarm", "calendar", "email"):
    for j in range(4):
        text = f"{label} utterance {j}"
        entries.append(
            F.BankEntry(
                bank_id=f"bank-{label}-{j:03d}", gold_scenario=label, text=text,
                text_sha256=hashlib.sha256(text.encode()).hexdigest(), train_sample_id=f"train-{label}-{j}",
            )
        )
bank = F.BankTable(entries=tuple(entries), seed=1, per_scenario_n=4)
bank_labels = {e.bank_id: e.gold_scenario for e in bank.entries}

# ---- durable attempt + plan ----------------------------------------------
store = AttemptStore(attempts_root=tmp / "attempts")
attempt_id = "attempt-rehearsal-000000"
plan = ExecutionPlan(
    run_id=F.PROBE_ID, execution_profile="bounded-discovery-probe", carrier_lock_key="slurp",
    split_role="discovery", split_identity_hash=F.EXPECTED_SPLIT_IDENTITY_HASH,
    planned_model_calls=4100, planned_gpu_hours=0.5, planned_speech_audio_seconds=700,
    protocol_hash=F.BINDING_CONFIG_SHA256, attempt_id=attempt_id,
).validate()
handle = store.open_attempt(F.PROBE_ID, attempt_id, carrier_lock_key="slurp", reserved_calls=4100, reserved_audio_seconds=700.0)

run_dir = tmp / "runs" / F.PROBE_ID / attempt_id
run_dir.mkdir(parents=True, exist_ok=True)
state = L.FlightState(run_dir / "flight-state.json")

# ---- exercise the sweep for TWO models ------------------------------------
for model, dim in (("lco3", 2048), ("qw", 1024)):
    client = MockEmbeddingClient(expected_dim=dim)
    client.verify_media_marker()

    def factory(sweep_id, total, audio_map, _client=client):
        vector_log = run_dir / f"vectors-{sweep_id.replace(':', '-')}.jsonl"
        cached = L.load_cached(vector_log)
        return L.BudgetedCachingProxy(
            _client, sweep_id=sweep_id, store=store, handle=handle, plan=plan, vector_log=vector_log,
            cached=cached, audio_seconds_by_contact=audio_map, total_contacts=total, log_every=1000,
        )

    flown, latency = L._run_bank_and_queries(
        model=model, client=client, proxy_factory=factory, state=state, root=tmp, bank=bank,
        samples=samples, transcripts=transcripts, supports_prefix=True, supports_marker=True,
        server_key=f"{model}-rehearsal",
    )
    print(f"  {model}: flown={flown} latency={latency:.3f}s")

    # idempotence: a second pass must fly NOTHING
    flown2, _ = L._run_bank_and_queries(
        model=model, client=client, proxy_factory=factory, state=state, root=tmp, bank=bank,
        samples=samples, transcripts=transcripts, supports_prefix=True, supports_marker=True,
        server_key=f"{model}-rehearsal",
    )
    assert flown2 == 0, f"idempotence broken for {model}: re-flew {flown2}"
    print(f"  {model}: idempotence PASS (second pass flew 0)")

calls, audio = handle.actual_totals()
print("durable after sweeps:", calls, "calls,", round(audio, 6), "audio-seconds")
expected_calls = 2 * len(bank.entries) + 3 * F.QUERY_N  # lco3 has 2 arms, qw has 1
assert calls == expected_calls, (calls, expected_calls)
print("call accounting PASS:", expected_calls)

# ---- retrieval ------------------------------------------------------------
bank_vectors = {m: F.load_bank_vectors(tmp, m, expected_count=len(bank.entries)).vectors for m in ("lco3", "qw")}
arm_retrievals = {}
for arm_id in ("a-lco3", "t-lco3", "t-qw"):
    q = F.load_query_vectors(tmp, arm_id)
    arm_retrievals[arm_id] = F.build_arm_retrieval(arm_id, q.vectors, bank_vectors[F.ARMS_BY_ID[arm_id].model], bank_labels)
winner = F.select_retrieval_winner(arm_retrievals)
document = F.build_retrieval_plan_document(arm_retrievals, winner)
path, sha = F.write_retrieval_plan(tmp, document)
reloaded = F.load_retrieval_plan(tmp)
assert F.retrieval_plan_document_sha256(reloaded) == sha
print("retrieval plan:", path.name, "sha256", sha[:16], "winner", winner, F.ARMS_BY_ID[winner].query_kind)
from collections import Counter
for arm_id, r in sorted(arm_retrievals.items()):
    sizes = Counter(len(row.dedup_labels_k5) for row in r.per_sample.values())
    print(f"   [{arm_id}] mean_top1={r.mean_top1_cosine:.6f} k5 sizes={dict(sorted(sizes.items()))}")

# ---- C-DECODE (mock core, TEXT modality) ---------------------------------
core = MockCoreClient(responder=lambda m: '{"scenario": "alarm", "action": "set", "entities": []}')
results = F.run_c_decode_flight(
    core_client=core, samples=samples, retrieval_plan_document=document, winner_arm_id=winner,
    winner_query_kind="text", transcript_registry=transcripts, decoding_params={"temperature": 0},
)
print("c-decode rows:", len(results), "| candidate-set sizes:",
      dict(sorted(Counter(len(r.candidate_labels) for r in results).items())))
print("c-decode mapping sample:", results[0].closed_set_mapping.as_json())

# ---- GenerationHealthProxy over the same path ----------------------------
resp_log = run_dir / "c-decode-responses.jsonl"
proxy = L.GenerationHealthProxy(
    core, response_log=resp_log, cached=[], store=store, handle=handle, plan=plan,
    audio_seconds=fid.TEXT_CONTACT_AUDIO_SECONDS, total=F.QUERY_N,
)
results2 = F.run_c_decode_flight(
    core_client=proxy, samples=samples, retrieval_plan_document=document, winner_arm_id=winner,
    winner_query_kind="text", transcript_registry=transcripts, decoding_params={"temperature": 0},
)
print("proxy flown:", proxy.flown, "replayed:", proxy.replayed, "rows:", len(results2))
cached = L.load_cached(resp_log)
proxy2 = L.GenerationHealthProxy(
    core, response_log=resp_log, cached=cached, store=store, handle=handle, plan=plan,
    audio_seconds=fid.TEXT_CONTACT_AUDIO_SECONDS, total=F.QUERY_N,
)
F.run_c_decode_flight(
    core_client=proxy2, samples=samples, retrieval_plan_document=document, winner_arm_id=winner,
    winner_query_kind="text", transcript_registry=transcripts, decoding_params={"temperature": 0},
)
assert proxy2.flown == 0 and proxy2.replayed == F.QUERY_N, (proxy2.flown, proxy2.replayed)
print("c-decode resume replay PASS: flown=0 replayed=", proxy2.replayed)

# ---- GPU accounting roll-up ----------------------------------------------
L._gpu_add(state, wall=1000.0, load=100.0, contact=50.0)
acc = L._gpu_accounting(state)
print(f"gpu accounting: wall={acc.wall_hours:.4f}h active={acc.gpu_active_hours:.4f}h measured-eq={acc.measured_equivalent_hours:.4f}h")
F.assert_gpu_hours_within_ceiling(acc)

shutil.rmtree(tmp, ignore_errors=True)
print("REHEARSAL DONE -- temp root removed; nothing touched the real data root")
PY
