"""P-EMB flight launcher (REGISTERED probes, exposure rows SAEA-PROBE-pemb1-78
and SAEA-PROBE-pemb2-552). One invocation flies ONE run: ``--run A`` or
``--run B``.

Structurally the archived P-TRAP / P-A2T generation launchers, with the ONE
architectural difference the registration itself forces: the embedding tier
does NOT speak the generation wire protocol, so there is no
``rails.core_client.FrozenCoreClient`` on this path
(``rails.embedding_client`` module docstring: "deliberately a SIBLING of
rails.core_client ... never a variant of it"). Everything ``FrozenCoreClient``
would have done for a generation flight is therefore done explicitly here, in
the SAME order and with the SAME fail-closed semantics:

    contracts.FrozenCoreGate.for_study_repo(...).assert_model_touch_allowed(plan)
      -- plan/scope validation, exposure pre-registration match, carrier scope,
         E0 closure + scoring freeze, runtime receipt + binary + GGUF bytes.
    rails.embedding_client.assert_no_conflicting_generation_server(...)
      -- fail-closed refusal to start while anything still answers on the
         GENERATION port (GENERATION_COEXISTENCE_NOTE).
    core.attempts.AttemptStore.open_attempt(...)
      -- the durable, atomic, one-time (run_id, attempt_id) key; every contact's
         spend is persisted BEFORE the request leaves the process, and every
         sibling attempt's spend is charged against the SAME plan ceiling.
    core.session.start_session(...)
      -- spawns the receipt-pinned binary in EMBEDDING mode on its own port.
    rails.embedding_client.EmbeddingClient(...).verify_media_marker()
      -- the env-pinned LLAMA_MEDIA_MARKER re-verified against the LIVE
         server's own GET /props, fail-closed, before the first contact.
    rails.probes.pemb_flight.run_pemb1_flight / run_pemb2_flight
      -- the registered contact set, count-checked fail-closed.
    rails.probes.pemb_flight.write_embedding_manifest(...)
      -- fp32 .npy per contact + a hashed manifest.json under the DATA ROOT.

THIS LAUNCHER NEVER READS A RESULT. Embedding VECTORS are the flight's own
product and are written to the data root, but nothing here ever compares two
of them: no cosine, no argmax, no ranking, no accuracy. That is the
separately-registered one-shot read mission's job (``analysis.pemb_read``).
Health logging prints ONLY the contact index, kind, contact id, latency and
dimension -- never a vector component.

Resumability under one registration (``--attempt-id``): every returned vector
is appended to ``vectors.jsonl`` as it arrives, keyed by contact index and the
sha256 of that contact's own payload (raw audio bytes, or the exact text
string). A resumed attempt replays those cached vectors instead of
re-contacting the core, and fails closed the moment a replayed contact's
payload hash disagrees with the cached one -- so a mid-flight abort costs no
registered calls on the retry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_identity import (  # noqa: E402
    EMBEDDING_PORT,
    EXECUTION_PROFILE,
    GENERATION_PORT,
    PREREGISTRATION_RELPATH,
    ROSTER_TABLE_RELPATH,
    RUNS,
    SAMPLE_MANIFEST_RELPATH,
    SPLIT_ROLE,
    TEXT_CONTACT_AUDIO_SECONDS,
    build_values,
    config_hash_of,
    run_id_for,
    server_args,
    server_env,
    split_identity_hash_for,
)

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    model_lock_key,
    protocol_hash as compute_protocol_hash,
    resolve_runtime_receipt_path,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.core.driver.smoke import fresh_attempt_id  # noqa: E402
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.embedding_client import (  # noqa: E402
    EMBEDDING_DIM,
    EmbeddingClient,
    EmbeddingVector,
    assert_no_conflicting_generation_server,
    resolve_expected_media_marker,
)
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (  # noqa: E402
    RUN_A_AUDIO_N,
    RUN_A_LABEL_N,
    RUN_B_AUDIO_N,
    RUN_B_ROW_N,
    run_pemb1_flight,
    run_pemb2_flight,
    write_embedding_manifest,
)


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)


def _port_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class BudgetedCachingProxy:
    """``EmbeddingClientProtocol`` wrapper that (a) enforces the plan's own
    call/audio ceilings against the DURABLE store before every contact, (b)
    persists the spend before the request leaves the process, (c) caches every
    returned vector for resume, and (d) logs OPERATIONAL health only.

    The durable-spend discipline is ``core.model.adapter.FrozenCoreAdapter``'s
    own, reimplemented here because the embedding tier has no adapter: read
    sibling attempts' persisted usage, add this attempt's own, refuse if the
    next contact would cross the plan ceiling, then ``record_usage`` BEFORE the
    transport send.

    A TEXT contact meters ZERO speech audio; it is charged
    ``TEXT_CONTACT_AUDIO_SECONDS`` (a documented, negligible positive sentinel)
    only because the store's ``record_usage`` API refuses a non-positive audio
    figure. See ``flight_identity.TEXT_CONTACT_AUDIO_SECONDS``."""

    def __init__(
        self,
        inner: EmbeddingClient,
        *,
        store: AttemptStore,
        handle,
        plan: ExecutionPlan,
        vector_log: Path,
        cached: list[dict],
        audio_seconds_by_contact: Mapping[str, float],
        total_contacts: int,
    ) -> None:
        self._inner = inner
        self._store = store
        self._handle = handle
        self._plan = plan
        self._vector_log = vector_log
        self._cached = cached
        self._audio_seconds_by_contact = dict(audio_seconds_by_contact)
        self._total = total_contacts
        self._index = 0
        self._started_at = time.time()
        self.replayed = 0
        self.flown = 0
        self.failures: list[dict] = []
        self.latency_total = 0.0
        self.latency_by_kind: dict[str, float] = {}
        self.flown_by_kind: Counter = Counter()
        self.calls_used = 0
        self.audio_seconds_used = 0.0

    # -- protocol ---------------------------------------------------------

    def verify_media_marker(self) -> Mapping[str, object]:
        props = self._inner.verify_media_marker()
        log(
            "media marker verified against the LIVE server's GET /props -- the env-pinned "
            "LLAMA_MEDIA_MARKER matches the server's own media_marker field (fail-closed check "
            "passed; a missing field or a mismatched value would have refused here)"
        )
        # Operational only: the server's own self-reported knobs, so the receipt
        # records what embedding mode actually resolved to. Never a result.
        for key in ("n_ctx", "n_batch", "n_ubatch", "pooling_type", "model_path", "build_info"):
            if key in props:
                log(f"  /props {key}: {props[key]!r}")
        return props

    def embed_text(self, *, contact_id: str, text: str) -> EmbeddingVector:
        payload_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return self._contact(
            kind="text",
            contact_id=contact_id,
            payload_sha256=payload_sha256,
            audio_seconds=TEXT_CONTACT_AUDIO_SECONDS,
            send=lambda: self._inner.embed_text(contact_id=contact_id, text=text),
        )

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes) -> EmbeddingVector:
        payload_sha256 = hashlib.sha256(bytes(audio_bytes)).hexdigest()
        audio_seconds = self._audio_seconds_by_contact.get(contact_id)
        if audio_seconds is None:
            raise RuntimeError(
                f"audio contact {contact_id!r} has no metered audio_seconds in this flight's own "
                "sample table; refusing to meter a contact whose cost is unknown (fail-closed)"
            )
        return self._contact(
            kind="audio",
            contact_id=contact_id,
            payload_sha256=payload_sha256,
            audio_seconds=float(audio_seconds),
            send=lambda: self._inner.embed_audio(contact_id=contact_id, audio_bytes=audio_bytes),
        )

    # -- internals --------------------------------------------------------

    def _contact(self, *, kind: str, contact_id: str, payload_sha256: str, audio_seconds: float, send):
        self._index += 1
        index = self._index

        if index <= len(self._cached):
            entry = self._cached[index - 1]
            if (
                entry["index"] != index
                or entry["kind"] != kind
                or entry["contact_id"] != contact_id
                or entry["payload_sha256"] != payload_sha256
            ):
                raise RuntimeError(
                    f"resume divergence at contact {index}: cached "
                    f"({entry['kind']}, {entry['contact_id']!r}, {entry['payload_sha256'][:12]}...) "
                    f"!= rebuilt ({kind}, {contact_id!r}, {payload_sha256[:12]}...); refusing to "
                    "replay a vector that does not belong to this contact (fail-closed)"
                )
            self.replayed += 1
            if index % 50 == 0 or index == len(self._cached):
                log(f"replay {index}/{len(self._cached)} from cache")
            return EmbeddingVector(
                contact_id=contact_id, kind=kind, values=tuple(float(v) for v in entry["values"])
            )

        # Durable budget enforcement BEFORE the send (adapter discipline).
        sibling_calls, sibling_audio = self._store.prior_actual_usage(
            self._plan.run_id, exclude_attempt_id=self._plan.attempt_id
        )
        if sibling_calls + self.calls_used + 1 > self._plan.planned_model_calls:
            raise RuntimeError(
                f"call ceiling: plan allows {self._plan.planned_model_calls}, "
                f"{sibling_calls} already spent by sibling attempts and {self.calls_used} by this "
                "attempt; refusing contact"
            )
        if (
            sibling_audio + self.audio_seconds_used + audio_seconds
            > self._plan.planned_speech_audio_seconds
        ):
            raise RuntimeError(
                f"audio ceiling: plan allows {self._plan.planned_speech_audio_seconds}s, "
                f"{sibling_audio:.3f}s already spent by sibling attempts and "
                f"{self.audio_seconds_used:.3f}s by this attempt; refusing contact"
            )
        self.calls_used, self.audio_seconds_used = self._handle.record_usage(
            calls=1, audio_seconds=audio_seconds
        )

        started = time.time()
        try:
            vector = send()
        except Exception as error:  # noqa: BLE001 -- health accounting, then re-raise
            elapsed = time.time() - started
            self.failures.append(
                {
                    "index": index,
                    "kind": kind,
                    "contact_id": contact_id,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            log(f"contact {index:04d} [{kind}] {contact_id} FAILED after {elapsed:.1f}s :: {type(error).__name__}: {error}")
            raise
        elapsed = time.time() - started
        self.flown += 1
        self.flown_by_kind[kind] += 1
        self.latency_total += elapsed
        self.latency_by_kind[kind] = self.latency_by_kind.get(kind, 0.0) + elapsed
        with self._vector_log.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "index": index,
                        "kind": kind,
                        "contact_id": contact_id,
                        "payload_sha256": payload_sha256,
                        "audio_seconds": audio_seconds,
                        "latency_seconds": elapsed,
                        "dims": vector.dims,
                        "values": list(vector.values),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        rate = self.flown / max(time.time() - self._started_at, 1e-9)
        remaining = max(self._total - index, 0)
        log(
            f"contact {index:04d} [{kind}] {contact_id} ok {elapsed:6.2f}s dims={vector.dims} "
            f"| flown={self.flown} {rate*60:.1f}/min eta={remaining/max(rate,1e-9)/60:.1f} min"
        )
        return vector


def load_cached(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    entries = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    entries.sort(key=lambda entry: entry["index"])
    for position, entry in enumerate(entries, start=1):
        if entry["index"] != position:
            raise RuntimeError(f"vector cache {path} is not a contiguous 1..N sequence at {position}")
    return entries


def _load_run_a_inputs(lock, root):
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
        load_pslu_rosters,
        load_pslu_sample_manifest,
        select_pslu_samples,
    )
    from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import (
        canonical_scenario_labels,
    )

    manifest = load_pslu_sample_manifest(REPO / SAMPLE_MANIFEST_RELPATH)
    rosters = load_pslu_rosters(REPO / ROSTER_TABLE_RELPATH)
    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    log("loading SLURP devel split (sha256 of every devel media file -- slow, model-free)")
    samples = select_pslu_samples(adapter.load_split("devel"), manifest)
    labels = canonical_scenario_labels(rosters)
    return samples, labels


def _load_run_b_inputs(lock, root):
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry
    from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    log("loading Audio2Tool discovery split (model-free)")
    samples = list(adapter.load_split("discovery"))
    rows = list(load_tool_registry(lock, root))
    return samples, rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, choices=("A", "B"))
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--attempt-id", default=None, help="resume an existing attempt directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=EMBEDDING_PORT)
    parser.add_argument("--runtime-root", default="/home/chao")
    args = parser.parse_args()

    run_key = args.run
    block = RUNS[run_key]
    run_id = run_id_for(run_key)
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    values = build_values(REPO, run_key)
    cfg_hash = config_hash_of(values)
    split_hash = split_identity_hash_for(run_key)

    log(f"P-EMB Run {run_key} -- exposure row {run_id}")
    log(f"split_identity_hash (pinned, never re-derived): {split_hash}")

    # ---- inputs (model-free) ------------------------------------------------
    if run_key == "A":
        samples, text_inputs = _load_run_a_inputs(lock, root)
        expected_audio_n, expected_text_n = RUN_A_AUDIO_N, RUN_A_LABEL_N
        text_label = "canonical scenario labels"
    else:
        samples, text_inputs = _load_run_b_inputs(lock, root)
        expected_audio_n, expected_text_n = RUN_B_AUDIO_N, RUN_B_ROW_N
        text_label = "tool registry rows"
    total_contacts = len(samples) + len(text_inputs)
    one_pass_audio = sum(float(s.audio_seconds) for s in samples)
    log(
        f"inputs: {len(samples)} audio samples (expect {expected_audio_n}), "
        f"{len(text_inputs)} {text_label} (expect {expected_text_n}); total contacts {total_contacts}"
    )
    log(
        f"metered audio for this run: {one_pass_audio:.2f}s "
        f"(min {min((s.audio_seconds for s in samples), default=0):.2f}s, "
        f"max {max((s.audio_seconds for s in samples), default=0):.2f}s)"
    )

    planned_calls = int(block["planned_budgets"]["model_calls"])  # type: ignore[index]
    planned_audio = int(block["planned_budgets"]["speech_audio_seconds"])  # type: ignore[index]
    planned_gpu = float(block["planned_budgets"]["gpu_hours"])  # type: ignore[index]
    if total_contacts != planned_calls:
        raise RuntimeError(
            f"run yields {total_contacts} contacts, the launcher's PLANNED_BUDGETS declares "
            f"{planned_calls}"
        )
    if one_pass_audio > planned_audio:
        raise RuntimeError(
            f"one full run meters {one_pass_audio:.2f} audio seconds but the plan allows only "
            f"{planned_audio}"
        )

    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split_hash)
    attempt_id = args.attempt_id or fresh_attempt_id()
    plan = ExecutionPlan(
        run_id=run_id,
        execution_profile=EXECUTION_PROFILE,
        carrier_lock_key=str(block["carrier_lock_key"]),
        split_role=SPLIT_ROLE,
        split_identity_hash=split_hash,
        planned_model_calls=planned_calls,
        planned_gpu_hours=planned_gpu,
        planned_speech_audio_seconds=planned_audio,
        protocol_hash=phash,
        attempt_id=attempt_id,
    ).validate()

    run_dir = Path(args.run_dir) / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"attempt {attempt_id} -> {run_dir}")
    (run_dir / f"{run_id}.plan.json").write_text(
        json.dumps(asdict(plan), indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    (run_dir / f"{run_id}.config-values.json").write_text(
        json.dumps({"config_hash": cfg_hash, "protocol_hash": phash, "values": values}, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )

    # ---- gate ---------------------------------------------------------------
    runtime_receipt = load_runtime_receipt(resolve_runtime_receipt_path(REPO, values))
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path(args.runtime_root),
        runtime_receipt_relpath=runtime_receipt_relpath(values),
        expected_model_lock_key=model_lock_key(values),
    )
    log(f"gate constructed (receipt {runtime_receipt_relpath(values)}, model {model_lock_key(values)})")
    gate_diagnostics: dict[str, object] = {}
    lock_sha256 = gate.assert_model_touch_allowed(plan, diagnostics=gate_diagnostics)
    log(f"gate OPEN: umbrella lock sha256 {lock_sha256}")
    log(f"gate runtime diagnostics: {json.dumps(gate_diagnostics, sort_keys=True, default=str)}")

    # ---- no coexisting generation server ------------------------------------
    assert_no_conflicting_generation_server(
        generation_server_reachable=lambda: _port_reachable(args.host, GENERATION_PORT),
        generation_base_url=f"http://{args.host}:{GENERATION_PORT}",
    )
    log(f"coexistence guard: nothing answers on the generation port {GENERATION_PORT} -- PASS")

    # ---- durable attempt ----------------------------------------------------
    store = AttemptStore(attempts_root=root / "attempts")
    prior_calls, prior_audio = store.prior_actual_usage(run_id, exclude_attempt_id=None)
    log(f"prior durable spend on {run_id}: calls={prior_calls}, audio_seconds={prior_audio:.3f}")
    if args.attempt_id:
        handle = store.handle(run_id, attempt_id)
        log(f"resuming existing attempt {attempt_id} (state {handle.state()})")
    else:
        handle = store.open_attempt(
            run_id,
            attempt_id,
            carrier_lock_key=str(block["carrier_lock_key"]),
            reserved_calls=planned_calls,
            reserved_audio_seconds=float(planned_audio),
        )
        log(f"attempt opened durably: {attempt_id} (state {handle.state()})")

    vector_log = run_dir / "vectors.jsonl"
    cached = load_cached(vector_log)
    if cached:
        log(f"resume: {len(cached)} cached vectors will be replayed without core contact")

    session_receipt_path = run_dir / f"{run_id}.session-receipt.json"
    server_log_path = run_dir / f"{run_id}.server.log"

    log(f"spawning llama-server in EMBEDDING mode on port {args.port} (receipt-pinned binary)")
    gpu_started_at = time.time()
    session = None
    summary = None
    error: BaseException | None = None
    manifest_path: Path | None = None
    proxy: BudgetedCachingProxy | None = None
    try:
        session = start_session(
            runtime_root=Path(args.runtime_root),
            data_root=root,
            runtime_receipt=runtime_receipt,
            host=args.host,
            port=args.port,
            session_id=f"{run_id}-{attempt_id}",
            extra_argv=server_args(values),
            extra_env=server_env(values),
            receipt_path=session_receipt_path,
            server_log_path=server_log_path,
        )
        log(f"session up: pid={session.pid} port={session.port} (spawn+load {time.time()-gpu_started_at:.1f}s)")
        log(f"session argv: {' '.join(session.argv)}")
        for entry in session.model_files:
            log(f"  model file: {entry.path} sha256={entry.sha256}")

        client = EmbeddingClient(
            base_url=str(values["base_url"]),
            expected_media_marker=resolve_expected_media_marker(),
            timeout_seconds=float(values.get("timeout_seconds", 420.0)),
        )
        proxy = BudgetedCachingProxy(
            client,
            store=store,
            handle=handle,
            plan=plan,
            vector_log=vector_log,
            cached=cached,
            audio_seconds_by_contact={s.sample_id: float(s.audio_seconds) for s in samples},
            total_contacts=total_contacts,
        )

        flight_started_at = time.time()
        log(f"FLIGHT START: {total_contacts} embedding contacts, ZERO generation, ONE session")
        if run_key == "A":
            summary = run_pemb1_flight(
                client=proxy,
                samples=samples,
                canonical_labels=text_inputs,
                split_identity_hash=split_hash,
                data_root=root,
            )
        else:
            summary = run_pemb2_flight(
                client=proxy,
                samples=samples,
                registry_rows=text_inputs,
                split_identity_hash=split_hash,
                data_root=root,
            )
        wall = time.time() - flight_started_at
    except BaseException as exc:  # noqa: BLE001 -- always land evidence
        error = exc
        wall = time.time() - gpu_started_at
        log(f"FLIGHT ABORTED: {type(exc).__name__}: {exc}")
    gpu_wall = time.time() - gpu_started_at

    if summary is not None:
        manifest_path = write_embedding_manifest(root, summary)
        log(f"embedding manifest written: {manifest_path} (NOT read back by this launcher)")
        log(
            f"vectors: audio={len(summary.audio_vectors)} text={len(summary.text_vectors)} "
            f"dims={EMBEDDING_DIM}"
        )

    contact_records = [] if proxy is None else [
        {
            "contact_id": contact.contact_id,
            "kind": contact.kind,
            "started_at": contact.started_at,
            "latency_seconds": contact.latency_seconds,
            "dims": contact.dims,
        }
        for contact in proxy._inner.contacts  # noqa: SLF001 -- the client's own public record
    ]
    (run_dir / "contacts.json").write_text(
        json.dumps({"run_id": run_id, "attempt_id": attempt_id, "contacts": contact_records}, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )

    try:
        handle.record_gpu_seconds(gpu_wall)
    except Exception as exc:  # noqa: BLE001 -- never mask the flight's own outcome
        log(f"record_gpu_seconds failed (non-fatal): {type(exc).__name__}: {exc}")
    if error is None:
        handle.mark_finalized()
        log(f"attempt {attempt_id} FINALIZED")
    else:
        handle.mark_aborted(f"P-EMB Run {run_key} aborted: {type(error).__name__}: {error}")
        log(f"attempt {attempt_id} ABORTED")

    actual_calls, actual_audio = handle.actual_totals()
    log(f"durable spend this attempt: calls={actual_calls}, audio_seconds={actual_audio:.3f}")
    if proxy is not None:
        log(f"contacts: flown={proxy.flown} replayed={proxy.replayed} failures={len(proxy.failures)}")
        log(f"flown by kind: {json.dumps(dict(proxy.flown_by_kind), sort_keys=True)}")
        log(
            "mean latency by kind: "
            + json.dumps(
                {
                    kind: round(total / max(proxy.flown_by_kind[kind], 1), 3)
                    for kind, total in sorted(proxy.latency_by_kind.items())
                },
                sort_keys=True,
            )
        )
    log(f"wall: flight {wall/60:.1f} min; GPU-occupied {gpu_wall/60:.1f} min ({gpu_wall/3600:.3f} h)")

    flight_receipt = {
        "run_id": run_id,
        "run_key": run_key,
        "attempt_id": attempt_id,
        "status": "COMPLETED" if error is None else "ABORTED",
        "error": None if error is None else f"{type(error).__name__}: {error}",
        "config_hash": cfg_hash,
        "protocol_hash": phash,
        "split_identity_hash": split_hash,
        "umbrella_lock_sha256": lock_sha256,
        "preregistration": PREREGISTRATION_RELPATH,
        "tier": "embedding (encode+pool, ZERO generation, zero sampling seam)",
        "embedding_dim": EMBEDDING_DIM,
        "n_audio_contacts_expected": expected_audio_n,
        "n_text_contacts_expected": expected_text_n,
        "n_contacts_planned": total_contacts,
        "n_audio_vectors": 0 if summary is None else len(summary.audio_vectors),
        "n_text_vectors": 0 if summary is None else len(summary.text_vectors),
        "embedding_manifest_path": None if manifest_path is None else str(manifest_path),
        "metered_audio_seconds_expected": round(one_pass_audio, 3),
        "text_contact_audio_seconds_sentinel": TEXT_CONTACT_AUDIO_SECONDS,
        "planned_budgets": {
            "model_calls": planned_calls,
            "speech_audio_seconds": planned_audio,
            "gpu_hours": planned_gpu,
        },
        "registered_ceilings": dict(block["registered_ceilings"]),  # type: ignore[arg-type]
        "durable_actual": {"calls": actual_calls, "audio_seconds": actual_audio},
        "prior_durable_spend_before_this_attempt": {"calls": prior_calls, "audio_seconds": prior_audio},
        "wall_seconds": wall,
        "gpu_occupied_seconds_this_attempt": gpu_wall,
        "gpu_hours_this_attempt": gpu_wall / 3600.0,
        "contacts_flown_this_attempt": 0 if proxy is None else proxy.flown,
        "contacts_replayed_from_cache": 0 if proxy is None else proxy.replayed,
        "contact_latency_seconds_this_attempt": 0.0 if proxy is None else proxy.latency_total,
        "contacts_flown_by_kind": {} if proxy is None else dict(proxy.flown_by_kind),
        "latency_seconds_by_kind": {} if proxy is None else dict(proxy.latency_by_kind),
        "contact_failures": [] if proxy is None else proxy.failures,
        "gate_runtime_diagnostics": json.loads(json.dumps(gate_diagnostics, sort_keys=True, default=str)),
        "session": None
        if session is None
        else {
            "session_id": session.session_id,
            "pid": session.pid,
            "host": session.host,
            "port": session.port,
            "binary_path": session.binary_path,
            "binary_sha256": session.binary_sha256,
            "argv": list(session.argv),
            "model_files": [{"path": m.path, "sha256": m.sha256} for m in session.model_files],
            "started_at": session.started_at,
        },
    }
    (run_dir / "flight-receipt.json").write_text(
        json.dumps(flight_receipt, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    log(f"flight receipt: {run_dir / 'flight-receipt.json'}")
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
