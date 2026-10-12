#!/usr/bin/env python3
"""Drive a REAL registered native cell through the REAL flight dispatch against a fake server.

Owner decision 159 (2026-09-27), the dispatcher slot-fill engineering-base item.
This harness is the model-free proof bench for the ``dispatch`` key:

* REAL: the composed fragments of a registered cell, the carrier adapter and
  its split, the prepared phase supply and the released knowledge stores, the
  promoted speech-feature packets (loaded and hash-verified on every render),
  ``FlightRuntime._dispatch_phase_program`` with ``model_free_check=True`` (the
  wire check's own dispatch mode: identity-only fit gates), the whole
  ``FrozenCoreClient`` / ``FrozenCoreAdapter`` stack with its attempt
  accounting and trace sink, and ``core.model.transport.LlamaServerTransport``
  -- the flight's own renderer, which produces the exact bytes a real
  llama-server would receive.
* FAKE: the gate (``WireCheckGate``) and the HTTP POST. The POST is a
  four-slot fake llama-server that records every request body it receives,
  holds the addressed slot for a deterministic service time drawn from the
  sealed ROLL-2 server timings of the same role (or zero), and answers with a
  canned, schema-valid role response keyed on (row, contact id) -- never on
  arrival order -- so the key-on and key-off runs walk the same trajectories.

Zero model, server, encoder, scorer and endpoint contacts. The scratch run id
carries ``WIRECHECK-`` exactly as ``FlightRuntime.wire_check`` does, and the
attempt it opens is aborted before return. The receipt holds digests, counts
and times only -- never utterance text, gold, knowledge bodies or model output.

Usage (WSL, speechrl venv, PYTHONPATH pinned to this tree):

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$TREE/src python3 \\
        scripts/analysis/slotfill_fake_server_harness.py --rows 60 \\
        --dispatch off --service measured --out /tmp/x.json
"""
from __future__ import annotations
import os

import argparse
import collections
import gc
import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
LOCK = Path(os.environ.get("SAEA_UMBRELLA_LOCK", "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"))
DEFAULT_EXPERIMENT = "slurp-native-default-plan-lock-v1"
ROLL2_TIMELINE = Path("/tmp/saea-slotfill/contacts-v1.json")
SLOT_ON_KEY = {"schema": "saea-dispatch-slot-fill-v1", "recall_prefetch": True, "role_input_offload": True, "gc_freeze": True}

_THREAD = threading.local()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _find_enum(node, key="intent_id"):
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict) and isinstance(props.get(key), dict) and isinstance(props[key].get("enum"), list):
            return list(props[key]["enum"])
        for value in node.values():
            found = _find_enum(value, key)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_enum(value, key)
            if found:
                return found
    return None


class ServiceModel:
    """Deterministic per-contact service seconds from ROLL-2's sealed server timings."""

    def __init__(self, mode: str, scale: float = 1.0):
        self.mode = mode
        self.scale = scale
        self.by_role: dict[str, list[float]] = {}
        if mode == "measured":
            doc = json.loads(ROLL2_TIMELINE.read_text(encoding="utf-8"))
            for c in doc["contacts"]:
                self.by_role.setdefault(c["role"], []).append(c["release"] - c["launch"])
            for values in self.by_role.values():
                values.sort()

    def seconds(self, role_class: str, key: str) -> float:
        if self.mode == "zero":
            return 0.0
        values = self.by_role[role_class]
        u = int(sha(key.encode())[:12], 16) / float(16 ** 12)
        return values[min(len(values) - 1, int(u * len(values)))] * self.scale


class FakeLlamaServer:
    """Four slots, request recording, canned role answers keyed on (row, contact)."""

    def __init__(self, service: ServiceModel, *, revise_share: float, slots: int):
        self.service = service
        self.revise_share = revise_share
        self.slots = slots
        self.lock = threading.Lock()
        self.records: list[dict] = []
        self.busy: dict[int, int] = collections.Counter()
        self.max_concurrency = 0
        self.slot_conflicts = 0
        self.legal: list[str] | None = None
        self.last_role: dict[str, str] = {}

    def _answer(self, sample_id: str, contact_id: str, role: str, body: dict) -> str:
        h = int(sha(f"{sample_id}|{contact_id}".encode())[:8], 16)
        if role == "perception":
            if self.legal is None:
                self.legal = _find_enum(body.get("response_format") or body) or []
                if not self.legal:
                    raise RuntimeError("fake server found no legal intent enum in the Perception body")
            picks = []
            for k in range(3):
                intent = self.legal[(h + 7919 * k) % len(self.legal)]
                if intent not in picks:
                    picks.append(intent)
            return json.dumps({"candidates": [
                {"intent_id": i, "distinction": "Harness canned alternative.", "evidence_refs": [], "unresolved_fields": []}
                for i in picks]}, separators=(",", ":"))
        if role == "solver":
            # keyed on the ROW only: grouped Solver samples agree, so a
            # plurality commit has its support
            hr = int(sha(sample_id.encode())[:8], 16)
            scenario, _, action = (self.legal[hr % len(self.legal)] if self.legal else "x_y").partition("_")
            return json.dumps({"scenario": scenario, "action": action, "entities": []}, separators=(",", ":"))
        if role == "reviewer":
            return "The draft names one legal intent and no unsupported entity."
        if role == "planner":
            row = int(sha(sample_id.encode())[:8], 16) / float(16 ** 8)
            first_visit = contact_id.split(":")[2] == "0"
            return "REVISE" if (row < self.revise_share and first_visit) else "ACCEPT"
        raise RuntimeError(f"unexpected role {role!r}")

    def post(self, _url: str, body_bytes: bytes) -> bytes:
        ctx = getattr(_THREAD, "ctx", None)
        if ctx is None:
            raise RuntimeError("fake server received a request outside the transport wrapper")
        sample_id, contact_id = ctx
        body = json.loads(body_bytes)
        slot = body.get("id_slot")
        role = contact_id.split(":")[1]
        masked = dict(body)
        masked.pop("id_slot", None)
        masked_bytes = json.dumps(masked, sort_keys=True).encode()
        with self.lock:
            prev = self.last_role.get(sample_id)
            role_class = role
            if role == "solver":
                role_class = "solver#2-5(full hit)" if prev == "solver" else "solver#1"
            self.last_role[sample_id] = role
            self.busy[slot] += 1
            if self.busy[slot] > 1:
                self.slot_conflicts += 1
            self.max_concurrency = max(self.max_concurrency, sum(1 for v in self.busy.values() if v))
            arrival = time.monotonic()
        try:
            time.sleep(self.service.seconds(role_class if role_class in self.service.by_role or self.service.mode == "zero" else "solver#1", f"{sample_id}|{contact_id}"))
            text = self._answer(sample_id, contact_id, role, body)
        finally:
            with self.lock:
                self.busy[slot] -= 1
                departure = time.monotonic()
                self.records.append({
                    "sample_id": sample_id, "contact_id": contact_id, "role": role, "role_class": role_class,
                    "slot": slot, "arrival": arrival, "departure": departure,
                    "body_sha256": sha(body_bytes), "body_sha256_id_slot_masked": sha(masked_bytes),
                    "response_sha256": sha(text.encode()),
                })
        return json.dumps({
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": max(1, len(body_bytes) // 4), "completion_tokens": max(1, len(text) // 4)},
        }).encode()


class RecordingTransport:
    """The REAL configured transport, with its POST replaced by the fake server."""

    def __init__(self, real, server: FakeLlamaServer):
        self._real = real
        self._server = server
        real._post = server.post
        self.payloads: list[dict] = []
        self.payload_digests: dict[tuple[str, str], str] = {}

    def render_request(self, request_bytes: bytes):
        return self._real.render_request(request_bytes)

    def __getattr__(self, name):
        return getattr(self._real, name)

    def __call__(self, request_bytes: bytes) -> bytes:
        payload = json.loads(request_bytes)
        sample_id = payload["sample_id"]
        contact_id = payload["history"][-1]["contact_id"]
        masked = json.loads(request_bytes)
        (masked.get("decoding_params") or {}).pop("id_slot", None)
        self.payload_digests[(sample_id, contact_id)] = json.dumps(masked, sort_keys=True)
        _THREAD.ctx = (sample_id, contact_id)
        try:
            return self._real(request_bytes)
        finally:
            _THREAD.ctx = None


def slot_accounting(records, slots: int):
    if not records:
        return {}
    t0 = min(r["arrival"] for r in records)
    t1 = max(r["departure"] for r in records)
    wall = t1 - t0
    busy = sum(r["departure"] - r["arrival"] for r in records)
    events = sorted([(r["arrival"], 1) for r in records] + [(r["departure"], -1) for r in records])
    level = 0
    last = t0
    all_idle = 0.0
    for t, d in events:
        if level == 0:
            all_idle += t - last
        level += d
        last = t
    return {
        "contact_window_s": round(wall, 3), "contacts": len(records),
        "slot_seconds_total": round(slots * wall, 3), "busy_slot_s": round(busy, 3),
        "empty_slot_s": round(slots * wall - busy, 3),
        "empty_slot_share": round(1 - busy / (slots * wall), 4),
        "all_slots_empty_s": round(all_idle, 3),
        "mean_busy_slots": round(busy / wall, 3),
        "contacts_per_hour_of_window": round(len(records) / wall * 3600, 1),
    }


_FLIGHT_RE = re.compile(r"flight-\d+")
_SLOT_RE = re.compile(r'"id_slot": ?\d+')
#: Fields assigned by ARRIVAL, not by content (see ``Normaliser``).
_ARRIVAL_KEYS = frozenset({"id_slot", "slot_id", "slot_ids"})
_WALL_CLOCK_KEYS = frozenset({"latency_seconds"})


class Normaliser:
    """Order-free, arrival-free view of sealed records.

    Exactly two facts in a sealed record are assigned by ARRIVAL rather than
    by content, and both already differ between two runs of today's
    dispatcher: the request-id counter (``flight-<n>``, numbered in dispatch
    order) and the llama.cpp slot number (``id_slot`` on the wire,
    ``slot_id`` / ``slot_ids`` in the sealed waves: whichever pinned slot the
    row drew). Two DIGESTS inherit them: a request's own sha256 (its bytes
    carry both fields) and a row's runtime-trace sha256 (its records carry
    the slot ids). Everything else is compared byte for byte.

    The normaliser therefore (1) renames every ``flight-<n>`` to its own
    (row, contact) identity, (2) renames every request sha256 to the same
    identity, (3) masks the three slot keys, (4) masks the runtime-trace
    digest -- whose preimage records are themselves compared -- and (5) drops
    the wall-clock ``latency_seconds``.
    """

    def __init__(self, trace_lines):
        self.flight: dict[str, str] = {}
        self.request_sha: dict[str, str] = {}
        for line in trace_lines:
            rec = json.loads(line)
            fid = rec["record_id"].split("/")[0]
            if rec["channel"] == "MODEL_REQUEST":
                payload = rec["payload"]["payload"]
                contact = payload["history"][-1].get("contact_id") if payload.get("history") else None
                if contact is None and payload.get("history"):
                    contact = json.loads(payload["history"][-1]["content"]).get("contact_id")
                label = "REQ[" + sha(f"{payload['sample_id']}|{contact}".encode())[:16] + "]"
                self.flight[fid] = label
                digest = rec["payload"].get("payload_sha256")
                if isinstance(digest, str):
                    self.request_sha[digest] = "REQSHA" + label
        for line in trace_lines:
            rec = json.loads(line)
            if rec["channel"] == "USE" and rec["record_id"].endswith("/native-role-contact"):
                fid = rec["record_id"].split("/")[0]
                digest = rec["payload"].get("use_request_sha256")
                if isinstance(digest, str) and fid in self.flight:
                    self.request_sha.setdefault(digest, "REQSHA" + self.flight[fid])

    def _walk(self, obj):
        if isinstance(obj, dict):
            out = {}
            for key, value in obj.items():
                if key in _WALL_CLOCK_KEYS:
                    continue
                if key in _ARRIVAL_KEYS:
                    out[key] = "ARRIVAL"
                elif key == "use_runtime_trace_sha256":
                    out[key] = "RUNTIME-TRACE-DIGEST"
                else:
                    out[key] = self._walk(value)
            return out
        if isinstance(obj, list):
            return [self._walk(v) for v in obj]
        if isinstance(obj, str):
            if obj in self.request_sha:
                return self.request_sha[obj]
            text = _FLIGHT_RE.sub(lambda m: self.flight.get(m.group(0), "REQ[?]"), obj)
            if text.startswith("{") and '"id_slot"' in text:
                try:
                    return json.dumps(self._walk(json.loads(text)), sort_keys=True)
                except ValueError:
                    pass
            return _SLOT_RE.sub('"id_slot": "ARRIVAL"', text)
        return obj

    def text(self, obj) -> str:
        return json.dumps(self._walk(obj), sort_keys=True, ensure_ascii=False)


def normalised_trace(trace_path: Path):
    lines = trace_path.read_text(encoding="utf-8").splitlines()
    normaliser = Normaliser(lines)
    return [normaliser.text(json.loads(line)) for line in lines], normaliser


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    ap.add_argument("--rows", type=int, default=60)
    ap.add_argument("--dispatch", choices=("off", "on"), default="off")
    ap.add_argument("--dispatch-json", default=None, help="override the ON dispatch block (JSON)")
    ap.add_argument("--service", choices=("zero", "measured"), default="zero")
    ap.add_argument("--service-scale", type=float, default=1.0)
    ap.add_argument("--revise-share", type=float, default=0.25)
    ap.add_argument("--label", default="run")
    ap.add_argument("--pair", default=None, help="shared scratch run-id suffix of a comparison pair")
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile-role", default=None, help="cProfile the role-input builder of this role")
    ap.add_argument("--roster-mode", choices=("resume", "split"), default="resume",
                    help="narrow through the resume seam, or truncate the adapter split (required by --seal)")
    ap.add_argument("--seal", action="store_true",
                    help="build the COMPLETED manifest and run verify_bundle (clean tree; no scoring)")
    ap.add_argument("--keep-dir", default=None, help="copy trace/outputs here for comparison")
    args = ap.parse_args(argv)
    _forbid_sockets()

    import speech_aware_evidence_acquisition as pkg
    tree = os.environ.get("SAEA_TREE_UNDER_TEST")
    if tree and not pkg.__file__.startswith(tree):
        raise SystemExit(f"package resolves to {pkg.__file__}, not the tree under test {tree}")

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.flight import runtime as rt
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
    from speech_aware_evidence_acquisition.core.configured_transport import build_configured_transport
    from speech_aware_evidence_acquisition.core.config import protocol_hash as compute_protocol_hash
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.reproduction.ojw import native_episode as ne

    fragment = json.loads((REPO / "configs" / "experiment" / f"{args.experiment}.json").read_text(encoding="utf-8"))
    cell = fragment["cells"][0]
    runtime = build_flight_runtime(
        REPO, DATA, model=cell["model_fragment"], dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"], experiment=args.experiment,
        run_id=cell["run_id"], attempt_id=cell["attempt_id"], runtime_root=Path("/tmp/saea-slotfill/runtime-root"),
        lock_path=LOCK, campaign_active=False,
    )
    # Config overrides ride core.config.compose itself, because the runtime
    # re-composes from the fragment files at every identity computation
    # (``_prepare``): the ON arm's ``dispatch`` block exactly as a baseline
    # fragment declaring it would compose, and the scratch supply pin.
    overrides: dict[str, object] = {}
    drop: set[str] = {"prepared_phase_supply"}
    if args.dispatch == "on":
        overrides["dispatch"] = json.loads(args.dispatch_json) if args.dispatch_json else SLOT_ON_KEY
    original_compose = rt.compose

    def compose_with_overrides(*a, **k):
        import dataclasses
        composed = original_compose(*a, **k)
        if "dispatch" in composed.values and args.dispatch == "off":
            raise SystemExit("the OFF arm must not declare a dispatch key")
        new_values = {key: v for key, v in composed.values.items() if key not in drop}
        new_values.update(overrides)
        return dataclasses.replace(composed, values=new_values)

    rt.compose = compose_with_overrides
    if args.roster_mode == "split":
        # A genuinely smaller roster: the adapter's own split, truncated. The
        # split identity, the minted supply and the sealed manifest's verified
        # split then all describe the same N rows, which is what a seal needs.
        adapter = runtime._adapter_factory(None, DATA)
        original_load_split = adapter.load_split
        adapter.load_split = lambda split_id: tuple(original_load_split(split_id))[: args.rows]
    values, carrier_lock_key, _split_id, identity_hash = runtime._prepare()
    arm = runtime._arm()
    policy = values["policy"]
    program = default_phase_program(policy)
    stamp = int(time.time() * 1000)
    # One scratch RUN id per comparison (``--pair``): the run id enters every
    # row's QueryState id, so the two arms of a byte-identity comparison must
    # share it; each arm opens its own attempt under it.
    run_id = f"{rt.WIRE_CHECK_RUN_ID_PREFIX}SLOTFILL-{args.pair or (args.label + '-' + str(stamp))}"
    attempt_id = f"attempt-wire-check-slotfill-{args.label}-{stamp}"
    # The committed pin was minted at its cell's flip commit; its identity
    # binds that commit's implementation files (item E16), so this tree mints
    # its OWN first-phase supply exactly as a flip does -- model-free, from
    # the sealed vectors -- under the scratch run id, and pins it. The key-on
    # and key-off runs mint separately (the composed config is part of the
    # identity) and must agree on the OUTPUT bytes.
    supply_rel = f"wire-check/{run_id}/phase-supply-{args.label}-{stamp}.json"
    (DATA / supply_rel).parent.mkdir(parents=True, exist_ok=True)
    supply_receipt = runtime.prepare_phase_supply(DATA / supply_rel, max_workers=4)
    supply_doc = json.loads((DATA / supply_rel).read_text(encoding="utf-8"))
    supply_output_sha256 = sha(json.dumps(supply_doc.get("output"), sort_keys=True).encode())
    drop.discard("prepared_phase_supply")
    overrides["prepared_phase_supply"] = {"relpath": supply_rel, "sha256": supply_receipt["sha256"]}
    values, carrier_lock_key, _split_id, identity_hash = runtime._prepare()
    # Restrict the flight to the first N roster rows through the production
    # resume seam (E10/E10c): the runner, the packet map and the ceiling all
    # follow one narrowed roster, exactly as a resume-recovery narrows them.
    roster = tuple(s.sample_id for s in runtime._samples)[: args.rows]
    if args.roster_mode == "resume":
        runtime._resume = object()
        runtime._resume_flown_sample_ids = roster

    declared = values["execution_plan"]
    plan = ExecutionPlan(
        run_id=run_id, execution_profile=declared["execution_profile"], carrier_lock_key=carrier_lock_key,
        split_role=declared["split_role"], split_identity_hash=identity_hash,
        # run-cumulative across the pair's attempts (and a resume), so sized for four
        planned_model_calls=4 * len(roster) * int(program.max_contacts),
        planned_gpu_hours=declared["planned_gpu_hours"],
        planned_speech_audio_seconds=declared["planned_speech_audio_seconds"],
        protocol_hash=compute_protocol_hash(runtime._composed.config_hash, arm, identity_hash),
        attempt_id=attempt_id,
    ).validate()
    run_dir = DATA / "wire-check" / run_id / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)

    service = ServiceModel(args.service, args.service_scale)
    slots = int(runtime._adapter.serving_geometry()["slots"])
    server = FakeLlamaServer(service, revise_share=args.revise_share, slots=slots)
    runtime_receipt = runtime._runtime_receipt_loader(rt.resolve_runtime_receipt_path(REPO, values))
    fake_session = _fake_session(values, runtime_receipt)
    from speech_aware_evidence_acquisition.core.model import transport as transport_module
    transport_module.assert_session_alive = lambda *_a, **_k: None
    real = build_configured_transport(
        values, DATA, repo_root=REPO, session=fake_session, runtime_receipt=runtime_receipt,
        runtime_root=Path("/tmp/saea-slotfill/runtime-root"),
    )
    transport = RecordingTransport(real, server)
    runtime._transport = transport
    runtime._plan = plan
    runtime._prepare_native_phase_runtime(policy)
    gate = rt.WireCheckGate()
    client_kwargs = runtime.frozen_core_client_kwargs(plan=plan, gate=gate, transport=transport, run_dir=run_dir)
    client = runtime._client_factory(**client_kwargs)
    runtime._client = client

    # --- instrumentation: time spent in the role-input builder (the part of a
    # hand-over the episode graph runs synchronously), and GC pauses
    builder_seconds: dict[str, list[float]] = collections.defaultdict(list)
    original_invoke = ne._RoleQuery.invoke

    profiler = None
    if args.profile_role:
        import cProfile
        profiler = cProfile.Profile()

    async def timed_invoke(self, inputs, session, context):
        t = time.perf_counter()
        prof = profiler is not None and self._role_id == args.profile_role
        if prof:
            profiler.enable()
        try:
            return await original_invoke(self, inputs, session, context)
        finally:
            if prof:
                profiler.disable()
            builder_seconds[self._role_id].append(time.perf_counter() - t)

    ne._RoleQuery.invoke = timed_invoke
    gc_pauses: list[float] = []
    gc_start = {}

    def gc_cb(phase, info):
        if phase == "start":
            gc_start["t"] = time.perf_counter()
        elif "t" in gc_start:
            gc_pauses.append(time.perf_counter() - gc_start.pop("t"))

    gc.callbacks.append(gc_cb)
    cpu0 = time.process_time()
    wall0 = time.perf_counter()
    rt._WIRE_CHECK_ACTIVE = True
    runtime._wire_check_active = True
    try:
        rows, contact_count, _kind, dispatch, _phases = runtime._dispatch_phase_program(
            client, plan, policy, model_free_check=True
        )
    finally:
        runtime._wire_check_active = False
        gc.callbacks.remove(gc_cb)
        ne._RoleQuery.invoke = original_invoke
    wall = time.perf_counter() - wall0
    cpu = time.process_time() - cpu0
    runtime._output_rows = rows
    close_receipt = client.close()
    canonical = runtime._canonical_output_rows(client)
    seal = {"status": "NOT-REQUESTED"}
    if args.seal:
        seal = _seal_and_verify(runtime, plan=plan, run_dir=run_dir, close_receipt=close_receipt, canonical=canonical)
    aborted = runtime._abort_attempt(DATA, run_id, attempt_id, reason="slot-fill harness: contact-free, no model was ever reached")

    trace_path = run_dir / f"{run_id}.trace.jsonl"
    norm_trace, normaliser = normalised_trace(trace_path)

    per_row_outputs = {r["sample_id"]: sha(normaliser.text(r).encode()) for r in canonical}
    per_row_states = {r["sample_id"]: sha(normaliser.text(r).encode()) for r in rows}
    body_digests = {f"{r['sample_id']}|{r['contact_id']}": r["body_sha256_id_slot_masked"] for r in server.records}
    payload_digests = {
        f"{s}|{c}": sha(normaliser.text(json.loads(text)).encode())
        for (s, c), text in transport.payload_digests.items()
    }
    receipt = {
        "schema": "saea-slotfill-fake-server-harness-v1",
        "label": args.label, "experiment": args.experiment, "dispatch": args.dispatch,
        "dispatch_block": values.get("dispatch"), "service": args.service, "service_scale": args.service_scale,
        "rows": len(roster), "contacts": contact_count, "server_requests": len(server.records),
        "slots": slots, "max_concurrency": server.max_concurrency, "slot_conflicts": server.slot_conflicts,
        "wall_s": round(wall, 3), "process_cpu_s": round(cpu, 3), "cpu_per_contact_s": round(cpu / max(1, contact_count), 4),
        "slot_accounting": slot_accounting(server.records, slots),
        "role_input_seconds": {k: {"n": len(v), "sum": round(sum(v), 3), "mean": round(sum(v) / len(v), 4), "max": round(max(v), 4)} for k, v in builder_seconds.items()},
        "gc": {"collections": len(gc_pauses), "pause_s_sum": round(sum(gc_pauses), 3), "pause_s_max": round(max(gc_pauses or [0]), 4)},
        "attempt_aborted": bool(aborted),
        "seal": seal,
        "phase_supply": {"relpath": supply_rel, "artifact_sha256": supply_receipt["sha256"], "output_sha256": supply_output_sha256, "artifact_recorded_output_sha256": supply_doc.get("output_sha256")}, "trace_manifest_hash": close_receipt["trace_manifest_hash"],
        "digests": {
            "request_bodies_id_slot_masked": body_digests,
            "request_payloads_id_slot_masked": payload_digests,
            "per_row_outputs": per_row_outputs,
            "per_row_dispatch_rows": per_row_states,
            "trace_records_normalised_multiset_sha256": sha("\n".join(sorted(norm_trace)).encode()),
            "trace_records": len(norm_trace),
        },
        "dispatch_receipt_keys": sorted(dispatch),
        "run_dir": str(run_dir), "model_contacts": 0,
    }
    Path(args.out).write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if profiler is not None:
        import io
        import pstats
        buf = io.StringIO()
        pstats.Stats(profiler, stream=buf).sort_stats("cumulative").print_stats(50)
        Path(args.out + ".profile.txt").write_text(buf.getvalue(), encoding="utf-8")
    if args.keep_dir:
        keep = Path(args.keep_dir)
        keep.mkdir(parents=True, exist_ok=True)
        (keep / "trace.normalised.jsonl").write_text("\n".join(sorted(norm_trace)) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ("label", "dispatch", "rows", "contacts", "wall_s", "process_cpu_s",
                                              "cpu_per_contact_s", "slot_accounting", "role_input_seconds", "gc",
                                              "max_concurrency", "slot_conflicts")}, indent=1))
    return 0


def _seal_and_verify(runtime, *, plan, run_dir, close_receipt, canonical):
    """The seal half of ``FlightRuntime._wire_check_seal_and_score`` without the
    scorers: write the canonical outputs, build the COMPLETED manifest over the
    trace as written (arrival order) and run the bundle verifier on it."""

    from speech_aware_evidence_acquisition.core.base import RunResult
    from speech_aware_evidence_acquisition.core.flight import runtime as rt
    from speech_aware_evidence_acquisition.core.split_receipt import VerifiedSplit
    from speech_aware_evidence_acquisition.data.splits import prefixed

    outputs_path = run_dir / f"{plan.run_id}.outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as handle:
        for row in canonical:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    result = RunResult(
        run_id=plan.run_id, arm=close_receipt["arm"], outputs_path=outputs_path,
        trace_manifest_hash=close_receipt["trace_manifest_hash"], cost=close_receipt["cost"],
    )
    sample_ids = tuple(sample.sample_id for sample in runtime._samples)
    verified_split = VerifiedSplit(
        name=runtime._split_id, carrier_lock_key=plan.carrier_lock_key, split_role=plan.split_role,
        ids=tuple(sorted(sample_ids)), prefixed_ids=tuple(prefixed(plan.carrier_lock_key, sample_ids)),
        identity_hash=plan.split_identity_hash,
    )
    try:
        manifest_path = runtime._manifest_builder(
            repo_root=runtime._repo_root, data_root=runtime._data_root, composed=runtime._composed,
            plan=plan, verified_split=verified_split, session_receipt_path=None, run_dir=run_dir,
            status="COMPLETED", result=result,
        )
        verified = runtime._bundle_verifier(manifest_path)
    except Exception as error:  # noqa: BLE001 -- recorded, the caller decides
        return {"status": "REFUSED", "reason": f"{type(error).__name__}: {error}"}
    return {
        "status": "VERIFIED",
        "manifest_sha256": rt._sha256_file(manifest_path),
        "verified_attempt_state": getattr(verified, "attempt_state", None),
        "outputs_rows": len(canonical),
        "outputs_sha256_as_written": rt._sha256_file(outputs_path),
        "trace_manifest_hash": close_receipt["trace_manifest_hash"],
    }


def _set_values(runtime, new_values):
    """Replace the composed values in place (the ON key, the scratch supply pin)."""
    composed = runtime._composed
    try:
        object.__setattr__(composed, "values", new_values)
    except (AttributeError, TypeError):
        import dataclasses
        runtime._composed = dataclasses.replace(composed, values=new_values)


def _fake_session(values, runtime_receipt):
    """A real ``SessionReceipt`` for an endpoint that is never dialled.

    Host and port are the composed ``base_url``'s (the transport refuses a
    receipt for any other endpoint); binary and model identities are the
    runtime receipt's own pins. The POST is replaced before any send and the
    per-send liveness check is replaced by a no-op (there is no process to
    re-verify), and ``_forbid_sockets`` refuses any TCP connect, so nothing
    can reach the resident session on this host.
    """
    import hashlib as _h
    from urllib.parse import urlparse

    from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
    from speech_aware_evidence_acquisition.core.session.receipt import (
        SESSION_RECEIPT_SCHEMA_V2, SessionReceipt,
    )

    from speech_aware_evidence_acquisition.core.session.receipt import _pinned_binary, _pinned_model_files

    url = urlparse(str(values.get("base_url", "http://127.0.0.1:8080")))
    binary_path, binary_sha256 = _pinned_binary(runtime_receipt)
    files = tuple(_pinned_model_files(runtime_receipt))
    return SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA_V2, study=STUDY_SLUG, session_id="slotfill-harness-fake-session",
        binary_path=binary_path,
        binary_sha256=binary_sha256,
        argv=(binary_path, "--host", url.hostname, "--port", str(url.port or 8080)),
        pid=0, host=url.hostname, port=int(url.port or 8080), model_files=files,
        started_at="2026-09-27T00:00:00+00:00", startup_stdout_sha256=_h.sha256(b"").hexdigest(),
        role="inference", server_env_keys=(),
    )


def _forbid_sockets():
    """Refuse every INET connect in this process: the harness is contact-free."""
    import socket

    real_connect = socket.socket.connect

    def refuse(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError(f"slot-fill harness refused a network connect to {address!r}")
        return real_connect(self, address)

    socket.socket.connect = refuse
    socket.socket.connect_ex = refuse


if __name__ == "__main__":
    raise SystemExit(main())
