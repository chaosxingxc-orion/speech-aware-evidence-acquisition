"""P-EMB-3M flight launcher (REGISTERED probe, exposure row
``SAEA-PROBE-pemb3m-388``). Four arms, 312 scored embedding contacts, plus 9
pre-flight/determinism gate contacts, across THREE sequential llama-server
sessions serving TWO different pinned embedder GGUFs and TWO in-process
transformers control models.

Structurally the archived P-EMB-3L launcher
(``docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3l-flight/
launcher/launch_pemb3l_flight.py``) -- its ``BudgetedCachingProxy``, its
zombie-safe ``_pid_alive``, its by-pid teardown and its arm-level idempotence
are reused in kind -- with the deltas this registration forces:

1. STAGED, not one-shot. The harness that drives this launcher reaps a command
   at 60 minutes, so the flight is a sequence of ``--stage`` invocations
   (``preflight`` / ``gate-b`` / ``m1`` / ``m23`` / ``m4`` / ``finalize``)
   sharing ONE ExecutionPlan, ONE durable attempt and ONE run directory. Arm-
   level idempotence (``rails.probes.pemb3m_flight.is_arm_complete``) is what
   makes that safe: a stage whose arm is already complete on the data root
   re-flies nothing and spends nothing, so a reaped or aborted stage is resumed
   by re-running it, never by re-spending.
2. THE FROZEN CORE IS NEVER LOADED. Two different embedder GGUFs are served
   through the SAME pinned llama.cpp binary via per-model runtime receipts
   (``flight_identity.embedder_runtime_receipt``). The gate checks that
   genuinely apply to a TOOL contact are run explicitly and individually --
   plan validation, exposure pre-registration, carrier scope, E0 closure +
   scoring freeze, llama.cpp runtime-library verification -- rather than
   through ``FrozenCoreGate.assert_model_touch_allowed``, whose remaining step
   (``_validate_runtime``) would re-hash and attest the 18 GB q4km GGUF set
   that THIS flight never loads. What replaces it is stronger for this flight,
   not weaker: every GGUF byte actually served is fully SHA-256'd in the
   preflight stage, cross-checked against the umbrella lock wherever the lock
   carries a per-file hash, and pinned into the config hash the plan's
   ``protocol_hash`` is computed from. The one deviation is recorded here,
   in the flight receipt, and in the archived README.
3. FOUR PRE-FLIGHT GATES (registration section 3), each fail-closed and
   receipt-logged, all run BEFORE any scored contact: (a) POOLING-DIFFER over
   two separate LCO boots, byte-compared; (b) GLAP/CLSP import feasibility,
   EXTENDED per the 2026-08-20 coordinator amendment to sanity-embed each
   control's AUDIO path on a synthetic non-corpus clip (a failure there marks
   that arm DROPPED-AUDIO-PATH, the same never-blocking semantics as
   DROPPED-DEPS, and nothing is ever installed); (c) the cascade source check
   against the CONSUMED pkey2-338 T0 transcripts; (d) the structural
   encode-only machine check.

THIS LAUNCHER NEVER READS A RESULT. Embedding VECTORS are the flight's own
product and are written to the data root, but nothing here ever compares two
of them for MEANING: no cosine, no argmax, no ranking, no accuracy, no per-arm
verdict, and scoring-side gold is never loaded. That is the separately
registered one-shot read mission's job (``analysis.pemb3m_read``). The two
byte-level comparisons this launcher DOES perform are instrument-health facts
the registration itself mandates, not results: the POOLING-DIFFER gate's
byte-compare (registration section 3 item 1, whose ``pooling_override_present``
outcome must be recorded honestly) and the repeat-call determinism samples
(registration section 6). Both are recorded as sha256-equality only; the cosine
tolerance evaluation belongs to the read suite. Health logging prints only the
contact index, kind, contact id, latency and dimension -- never a vector
component.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
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

import flight_identity as fid  # noqa: E402

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: E402
from speech_aware_evidence_acquisition.core.driver.smoke import fresh_attempt_id  # noqa: E402
from speech_aware_evidence_acquisition.core.session import load_runtime_receipt, start_session  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path  # noqa: E402
from speech_aware_evidence_acquisition.rails.embedding_client import (  # noqa: E402
    EmbeddingClient,
    EmbeddingVector,
    assert_no_conflicting_generation_server,
    resolve_expected_media_marker,
)
from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import (  # noqa: E402
    ARM_LABEL_N,
    ARM_M1_ID,
    ARM_M2_ID,
    ARM_M3_ID,
    ARM_M4_ID,
    ARM_QUERY_N,
    ARM_TOTAL_N,
    ARMS_BY_ID,
    CASCADE_SOURCE_STATUS_COMPLETE,
    PLANNED_TOTAL_EMBEDDING_CONTACTS,
    QWEN3_EMB_EMBEDDING_DIM,
    Pemb3mArmSummary,
    arm_run_id,
    assert_binding_config_sha256,
    assert_within_registered_ceilings,
    binding_config_sha256,
    is_arm_complete,
    run_cascade_source_check,
    run_control_import_feasibility_gates,
    run_encode_only_preflight_gate,
    run_local_encoder_arm_flight,
    run_m1_arm_flight,
    run_m4_arm_flight,
    run_m4_repeat_call_gate,
    run_pooling_differ_gate,
    write_pemb3m_arm_manifest,
)

STAGES = ("preflight", "gate-b", "m1", "m23", "m4", "finalize")


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)


# ---------------------------------------------------------------------------
# Process / port helpers (P-EMB-3L launcher, reused in kind).
# ---------------------------------------------------------------------------


def _port_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pid_alive(pid: int) -> bool:
    """Zombie-safe liveness for a server THIS process spawned.

    A spawned server is a CHILD, so the moment it exits it becomes a ZOMBIE
    until reaped -- and ``os.kill(pid, 0)`` SUCCEEDS on a zombie. Signal-probing
    alone therefore reports an already-exited server as alive forever, which is
    exactly what aborted P-EMB-3L's first attempt. Reap first, then treat a
    ``Z`` state as dead, and only then fall back to the signal probe."""

    try:
        reaped, _status = os.waitpid(pid, os.WNOHANG)
        if reaped == pid:
            return False
    except ChildProcessError:
        pass
    except OSError:
        pass
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
        if stat.rsplit(")", 1)[1].split()[0] == "Z":
            return False
    except (OSError, IndexError):
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def teardown_session(pid: int, host: str, port: int, *, timeout_seconds: float = 60.0) -> dict[str, object]:
    """Tear down the server THIS process spawned, by the exact pid
    ``start_session`` returned -- never a pattern-matched ``pkill``, so a
    sibling campaign's server can never be caught in the blast radius.
    Escalates SIGTERM -> SIGKILL and then proves the port is free."""

    record: dict[str, object] = {"pid": pid, "signal": "SIGTERM", "escalated": False}
    started = time.time()
    if not _pid_alive(pid):
        record["already_gone"] = True
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            record["already_gone"] = True
    while time.time() - started < timeout_seconds and _pid_alive(pid):
        time.sleep(0.5)
    if _pid_alive(pid):
        record["escalated"] = True
        record["signal"] = "SIGKILL"
        log(f"pid {pid} still resident after SIGTERM; escalating to SIGKILL")
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        deadline = time.time() + 20.0
        while time.time() < deadline and _pid_alive(pid):
            time.sleep(0.5)
    record["pid_alive_after"] = _pid_alive(pid)
    port_deadline = time.time() + 25.0
    while time.time() < port_deadline and _port_reachable(host, port, timeout=0.5):
        time.sleep(0.5)
    record["port_reachable_after"] = _port_reachable(host, port, timeout=0.5)
    record["teardown_seconds"] = time.time() - started
    if record["pid_alive_after"] or record["port_reachable_after"]:
        raise RuntimeError(
            f"teardown failed: pid {pid} alive={record['pid_alive_after']}, port {port} "
            f"reachable={record['port_reachable_after']} -- refusing to leave a resident "
            "server behind (fail-closed)"
        )
    return record


def _own_llama_server_children() -> list[int]:
    """Every live ``llama-server`` process whose PPid is THIS process.

    Scoped to our OWN children by construction, so it can never reach a sibling
    session's server or another repository's campaign -- the same blast-radius
    discipline the by-pid teardown above keeps. Used only to clean up an orphan
    that ``core.session.start_session`` left behind when it raised (it kills
    nothing itself and never hands back the Popen), which would otherwise sit on
    the GPU for the rest of the flight."""

    mine = os.getpid()
    found: list[int] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8", errors="replace")
            head, _, tail = stat.rpartition(")")
            comm = head.partition("(")[2]
            fields = tail.split()
            if comm == "llama-server" and fields[0] != "Z" and int(fields[1]) == mine:
                found.append(int(entry.name))
        except (OSError, IndexError, ValueError):
            continue
    return found


def sha256_file(path: Path, *, chunk_bytes: int = 8 << 20) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_bytes)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


# ---------------------------------------------------------------------------
# Durable, budget-enforcing, caching contact proxy (P-EMB-3L's own, generalized
# to also wrap a LocalEncoderClientProtocol, which carries no marker concept).
# ---------------------------------------------------------------------------


class BudgetedCachingProxy:
    """Wraps either an ``EmbeddingClientProtocol`` (M1/M4, wire) or a
    ``LocalEncoderClientProtocol`` (M2/M3, in-process) and (a) enforces the
    plan's own call/audio ceilings against the DURABLE store before every
    contact, (b) persists the spend BEFORE the request leaves the process, (c)
    caches every returned vector for resume, and (d) logs OPERATIONAL health
    only -- never a vector component.

    ONE proxy per ARM (its own contact index and vector cache), but the running
    spend counters are SEEDED from the durable attempt's own totals at
    construction, so a later arm never restarts its ceiling arithmetic from zero
    after an earlier one has already spent under the same attempt.

    A TEXT contact meters ZERO speech audio; it is charged
    ``TEXT_CONTACT_AUDIO_SECONDS`` (a documented, negligible positive sentinel)
    only because ``record_usage`` refuses a non-positive audio figure."""

    def __init__(
        self,
        inner,
        *,
        arm_id: str,
        store: AttemptStore,
        handle,
        plan: ExecutionPlan,
        vector_log: Path,
        cached: list[dict],
        audio_seconds_by_contact: Mapping[str, float],
        total_contacts: int,
        supports_prefix: bool = True,
        supports_marker: bool = True,
    ) -> None:
        self._inner = inner
        self._arm_id = arm_id
        self._store = store
        self._handle = handle
        self._plan = plan
        self._vector_log = vector_log
        self._cached = cached
        self._audio_seconds_by_contact = dict(audio_seconds_by_contact)
        self._total = total_contacts
        self._supports_prefix = supports_prefix
        self._supports_marker = supports_marker
        self._index = 0
        self._started_at = time.time()
        self.replayed = 0
        self.flown = 0
        self.failures: list[dict] = []
        self.latency_total = 0.0
        self.latency_by_kind: dict[str, float] = {}
        self.flown_by_kind: Counter = Counter()
        self.calls_used, self.audio_seconds_used = handle.actual_totals()

    # -- protocol ---------------------------------------------------------

    def verify_media_marker(self) -> Mapping[str, object]:
        if not self._supports_marker:
            return {}
        props = self._inner.verify_media_marker()
        log(
            f"[{self._arm_id}] media marker verified against the LIVE server's GET /props -- the "
            "env-pinned LLAMA_MEDIA_MARKER matches the server's own media_marker field "
            "(fail-closed; a missing field or a mismatched value would have refused)"
        )
        for key in ("n_ctx", "n_batch", "n_ubatch", "pooling_type", "model_path", "build_info"):
            if key in props:
                log(f"  /props {key}: {props[key]!r}")
        return props

    def embed_text(self, *, contact_id: str, text: str, prefix: str = "") -> EmbeddingVector:
        payload_sha256 = hashlib.sha256((prefix + text).encode("utf-8")).hexdigest()
        if self._supports_prefix:
            send = lambda: self._inner.embed_text(contact_id=contact_id, text=text, prefix=prefix)  # noqa: E731
        else:
            if prefix:
                raise RuntimeError(f"[{self._arm_id}] inner client accepts no prefix but one was given")
            send = lambda: self._inner.embed_text(contact_id=contact_id, text=text)  # noqa: E731
        return self._contact(
            kind="text",
            contact_id=contact_id,
            payload_sha256=payload_sha256,
            audio_seconds=fid.TEXT_CONTACT_AUDIO_SECONDS,
            send=send,
        )

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes, prompt_prefix: str = "") -> EmbeddingVector:
        digest = hashlib.sha256()
        digest.update(prompt_prefix.encode("utf-8"))
        digest.update(bytes(audio_bytes))
        payload_sha256 = digest.hexdigest()
        audio_seconds = self._audio_seconds_by_contact.get(contact_id)
        if audio_seconds is None:
            raise RuntimeError(
                f"audio contact {contact_id!r} has no metered audio_seconds in this flight's own "
                "sample table; refusing to meter a contact whose cost is unknown (fail-closed)"
            )
        if self._supports_prefix:
            send = lambda: self._inner.embed_audio(  # noqa: E731
                contact_id=contact_id, audio_bytes=audio_bytes, prompt_prefix=prompt_prefix
            )
        else:
            if prompt_prefix:
                raise RuntimeError(f"[{self._arm_id}] inner client accepts no prompt_prefix but one was given")
            send = lambda: self._inner.embed_audio(contact_id=contact_id, audio_bytes=audio_bytes)  # noqa: E731
        return self._contact(
            kind="audio",
            contact_id=contact_id,
            payload_sha256=payload_sha256,
            audio_seconds=float(audio_seconds),
            send=send,
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
                    f"[{self._arm_id}] resume divergence at contact {index}: cached "
                    f"({entry['kind']}, {entry['contact_id']!r}, {entry['payload_sha256'][:12]}...) "
                    f"!= rebuilt ({kind}, {contact_id!r}, {payload_sha256[:12]}...); refusing to "
                    "replay a vector that does not belong to this contact (fail-closed)"
                )
            self.replayed += 1
            if index % 25 == 0 or index == len(self._cached):
                log(f"[{self._arm_id}] replay {index}/{len(self._cached)} from cache")
            return EmbeddingVector(contact_id=contact_id, kind=kind, values=tuple(float(v) for v in entry["values"]))

        sibling_calls, sibling_audio = self._store.prior_actual_usage(
            self._plan.run_id, exclude_attempt_id=self._plan.attempt_id
        )
        if sibling_calls + self.calls_used + 1 > self._plan.planned_model_calls:
            raise RuntimeError(
                f"call ceiling: plan allows {self._plan.planned_model_calls}, {sibling_calls} already "
                f"spent by sibling attempts and {self.calls_used} by this attempt; refusing contact"
            )
        if sibling_audio + self.audio_seconds_used + audio_seconds > self._plan.planned_speech_audio_seconds:
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
                    "arm_id": self._arm_id,
                    "index": index,
                    "kind": kind,
                    "contact_id": contact_id,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            log(
                f"[{self._arm_id}] contact {index:04d} [{kind}] {contact_id} FAILED after "
                f"{elapsed:.1f}s :: {type(error).__name__}: {error}"
            )
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
                        "arm_id": self._arm_id,
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
            f"[{self._arm_id}] contact {index:04d} [{kind}] {contact_id} ok {elapsed:6.2f}s "
            f"dims={vector.dims} | flown={self.flown} {rate*60:.1f}/min "
            f"eta={remaining/max(rate,1e-9)/60:.1f} min"
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


# ---------------------------------------------------------------------------
# Shared inputs + flight state.
# ---------------------------------------------------------------------------


def load_inputs(lock, root):
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
        load_pslu_rosters,
        load_pslu_sample_manifest,
        select_pslu_samples,
    )
    from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import canonical_scenario_labels

    manifest = load_pslu_sample_manifest(REPO / fid.SAMPLE_MANIFEST_RELPATH)
    rosters = load_pslu_rosters(REPO / fid.ROSTER_TABLE_RELPATH)
    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    log("loading SLURP devel split (sha256 of every devel media file -- slow, model-free)")
    samples = select_pslu_samples(adapter.load_split("devel"), manifest)
    labels = canonical_scenario_labels(rosters)
    return list(samples), list(labels)


class FlightState:
    """The one JSON document every stage reads and extends, under the run
    directory on the DATA ROOT (never in Git). Written atomically."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.document: dict[str, object] = {}
        if self.path.is_file():
            self.document = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f"{self.path.name}.tmp-{os.getpid()}")
        tmp.write_text(
            json.dumps(self.document, indent=2, sort_keys=True, default=str), encoding="utf-8", newline="\n"
        )
        os.replace(tmp, self.path)

    def put(self, key: str, value: object) -> None:
        self.document[key] = value
        self.save()


def resolve_run_dir(root: Path, attempt_id: str) -> Path:
    return Path(root) / "runs" / fid.run_id() / attempt_id


def load_context(args):
    """Everything every stage needs: lock, root, values, config/protocol hash,
    plan, run dir, attempt handle."""

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    assert_binding_config_sha256(lock)

    attempt_id = args.attempt_id
    run_dir = resolve_run_dir(root, attempt_id)
    state = FlightState(run_dir / "flight-state.json")

    sha_by_relpath = state.document.get("model_file_sha256") or {}
    values = fid.build_values(REPO, lock, sha_by_relpath)
    cfg_hash = fid.config_hash_of(values)
    plan = ExecutionPlan(
        run_id=fid.run_id(),
        execution_profile=fid.EXECUTION_PROFILE,
        carrier_lock_key=fid.CARRIER_LOCK_KEY,
        split_role=fid.SPLIT_ROLE,
        split_identity_hash=fid.split_identity_hash(),
        planned_model_calls=int(fid.PLANNED_BUDGETS["model_calls"]),
        planned_gpu_hours=float(fid.PLANNED_BUDGETS["gpu_hours"]),
        planned_speech_audio_seconds=int(fid.PLANNED_BUDGETS["speech_audio_seconds"]),
        protocol_hash=cfg_hash,
        attempt_id=attempt_id,
    ).validate()
    assert_within_registered_ceilings(
        calls=plan.planned_model_calls,
        audio_seconds=plan.planned_speech_audio_seconds,
        gpu_hours=plan.planned_gpu_hours,
    )
    # Fail-closed across stages: a later stage must recompose the EXACT config
    # the preflight stage bound its plan to. Anything that drifted (a model
    # hash, the feature-cache directory, the arm table, the umbrella lock)
    # changes this digest and refuses here rather than flying under a protocol
    # hash the plan never carried.
    pinned = state.document.get("config_hash")
    if pinned is not None and pinned != cfg_hash:
        raise RuntimeError(
            f"config hash drifted since preflight: state pins {pinned}, recomposed {cfg_hash}; "
            "refusing (fail-closed)"
        )
    store = AttemptStore(attempts_root=root / "attempts")
    return lock, root, values, cfg_hash, plan, run_dir, state, store


# ---------------------------------------------------------------------------
# Stage: preflight.
# ---------------------------------------------------------------------------


def stage_preflight(args) -> int:
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    attempt_id = args.attempt_id
    run_dir = resolve_run_dir(root, attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    state = FlightState(run_dir / "flight-state.json")
    log(f"P-EMB-3M preflight -- exposure row {fid.run_id()}, attempt {attempt_id} -> {run_dir}")

    # -- binding-config hash stability -------------------------------------
    assert_binding_config_sha256(lock)
    digest_a = binding_config_sha256(lock)
    digest_b = binding_config_sha256(lock)
    if digest_a != digest_b:
        raise RuntimeError("binding config sha256 is not stable across two computations")
    log(f"binding config sha256 verified + stable across recomputation: {digest_a}")
    state.put("binding_config_sha256", digest_a)

    # -- every GGUF byte this flight will actually serve --------------------
    relpaths = list(fid.lco_gguf_relpaths()) + list(fid.qwen3_emb_gguf_relpaths())
    measured: dict[str, dict[str, object]] = {}
    sha_by_relpath: dict[str, str] = {}
    for relpath in relpaths:
        path = root / relpath
        if not path.is_file():
            raise RuntimeError(f"pinned embedder GGUF missing: {path}")
        started = time.time()
        digest, size = sha256_file(path)
        elapsed = time.time() - started
        sha_by_relpath[relpath] = digest
        measured[relpath] = {
            "sha256": digest,
            "bytes": size,
            "hash_seconds": round(elapsed, 2),
            "read_MB_per_s": round(size / max(elapsed, 1e-9) / 1e6, 1),
        }
        log(f"gguf {relpath}: {size} bytes sha256={digest} ({elapsed:.1f}s, {measured[relpath]['read_MB_per_s']} MB/s)")
    state.put("model_file_sha256", sha_by_relpath)
    state.put("model_file_measurements", measured)

    # -- cross-check against the umbrella lock wherever it carries a hash ---
    from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import resolve_model_binding

    lock_crosscheck: dict[str, object] = {}
    for lock_key in ("lco-embedding-omni-3b-gguf", "qwen3-embedding-0.6b-gguf", "glap", "clsp"):
        binding = resolve_model_binding(lock, lock_key)
        file_hashes = {entry["filename"]: entry["sha256"] for entry in binding["file_hashes"] if entry.get("filename")}
        verdicts = []
        for relpath, digest in sha_by_relpath.items():
            filename = Path(relpath).name
            if filename in file_hashes:
                agree = file_hashes[filename] == digest
                verdicts.append({"filename": filename, "lock_sha256": file_hashes[filename], "measured": digest, "agree": agree})
                if not agree:
                    raise RuntimeError(
                        f"{lock_key}: umbrella lock pins {filename} at {file_hashes[filename]} but the "
                        f"real bytes hash to {digest}; refusing (fail-closed)"
                    )
        lock_crosscheck[lock_key] = {
            "lifecycle": binding["lifecycle"],
            "source_kind": binding["source_kind"],
            "source_id": binding["source_id"],
            "revision": binding["revision"],
            "size_bytes": binding["size_bytes"],
            "files_count": binding["files_count"],
            "lock_carries_per_file_sha256": bool(file_hashes),
            "verified_against_lock": verdicts,
        }
        log(
            f"lock binding {lock_key}: lifecycle={binding['lifecycle']!r} "
            f"per-file-sha256={'yes' if file_hashes else 'NO (LOCAL_CANDIDATE -- this flight self-pins)'}"
            + (f" -> {len(verdicts)} file(s) cross-checked AGREE" if verdicts else "")
        )
    state.put("umbrella_lock_crosscheck", lock_crosscheck)

    # -- now the full config/plan, with the measured hashes bound in --------
    values = fid.build_values(REPO, lock, sha_by_relpath)
    cfg_hash = fid.config_hash_of(values)
    plan = ExecutionPlan(
        run_id=fid.run_id(),
        execution_profile=fid.EXECUTION_PROFILE,
        carrier_lock_key=fid.CARRIER_LOCK_KEY,
        split_role=fid.SPLIT_ROLE,
        split_identity_hash=fid.split_identity_hash(),
        planned_model_calls=int(fid.PLANNED_BUDGETS["model_calls"]),
        planned_gpu_hours=float(fid.PLANNED_BUDGETS["gpu_hours"]),
        planned_speech_audio_seconds=int(fid.PLANNED_BUDGETS["speech_audio_seconds"]),
        protocol_hash=cfg_hash,
        attempt_id=attempt_id,
    ).validate()
    assert_within_registered_ceilings(
        calls=plan.planned_model_calls,
        audio_seconds=plan.planned_speech_audio_seconds,
        gpu_hours=plan.planned_gpu_hours,
    )
    log(f"config hash (= protocol hash): {cfg_hash}")
    (run_dir / f"{fid.run_id()}.plan.json").write_text(
        json.dumps(asdict(plan), indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    (run_dir / f"{fid.run_id()}.config-values.json").write_text(
        json.dumps({"config_hash": cfg_hash, "values": values}, indent=2, sort_keys=True),
        encoding="utf-8",
        newline="\n",
    )

    # -- registered ceilings: three independent sources must agree ----------
    from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import (
        CEILING_AUDIO_SECONDS,
        CEILING_CALLS,
        CEILING_GPU_HOURS,
    )

    ledger_text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    ledger_row = [line for line in ledger_text.splitlines() if f"| {fid.run_id()} |" in line]
    if len(ledger_row) != 1:
        raise RuntimeError(f"expected exactly one exposure-ledger row for {fid.run_id()}, found {len(ledger_row)}")
    cells = [cell.strip() for cell in ledger_row[0].strip().strip("|").split("|")]
    ledger_ceilings = {"model_calls": int(cells[9]), "speech_audio_seconds": int(cells[10]), "gpu_hours": float(cells[11])}
    machinery_ceilings = {
        "model_calls": CEILING_CALLS,
        "speech_audio_seconds": CEILING_AUDIO_SECONDS,
        "gpu_hours": CEILING_GPU_HOURS,
    }
    if ledger_ceilings != machinery_ceilings or ledger_ceilings != fid.REGISTERED_CEILINGS:
        raise RuntimeError(
            f"registered ceilings disagree: ledger {ledger_ceilings}, machinery {machinery_ceilings}, "
            f"launcher {fid.REGISTERED_CEILINGS} -- refusing (fail-closed)"
        )
    log(f"registered ceilings agree across ledger / machinery / launcher: {ledger_ceilings}")
    state.put("registered_ceilings", ledger_ceilings)
    state.put("ledger_consumed_cell_at_takeoff", cells[8])
    if cells[8] != "no":
        raise RuntimeError(f"exposure row consumed cell reads {cells[8]!r}, expected 'no'")

    # -- the gate checks that genuinely apply to a TOOL contact -------------
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path(args.runtime_root),
        runtime_receipt_relpath=fid.RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key="qwen3-omni-30b-a3b-instruct-gguf-q4km",
    )
    lock_doc, lock_sha256 = gate._load_lock_with_hash()
    gate._require_exposure_preregistration(plan, lock_doc)
    log("gate: exposure pre-registration cross-check PASS (profile/split/identity/carrier/consumed/budgets)")
    gate._resolve_carrier_dataset_entry(plan.carrier_lock_key, lock_doc)
    log(f"gate: carrier scope PASS ({plan.carrier_lock_key} resolves to a speech-aware dataset entry)")
    gate._validate_e0()
    log("gate: E0 closure + scoring freeze PASS (D1-D4 artifacts + frozen scoring-source hashes + no relocated bytecode)")
    committed_runtime = load_runtime_receipt(REPO / "docs" / fid.RUNTIME_RECEIPT_RELPATH)
    gate._validate_runtime_libraries(committed_runtime, str(committed_runtime["llama_cpp"]["binary_path"]))
    log("gate: llama.cpp runtime libraries PASS (exact set, every file re-hashed)")
    log(f"umbrella lock sha256: {lock_sha256}")
    state.put("umbrella_lock_sha256", lock_sha256)
    state.put(
        "gate_scope_note",
        "TOOL-contact flight: FrozenCoreGate._validate_runtime (q4km GGUF attestation) is "
        "deliberately NOT run -- the frozen core is never loaded. Every GGUF byte actually "
        "served is fully SHA-256'd above instead, and the llama.cpp binary is re-hashed "
        "fail-closed by core.session.start_session at every spawn.",
    )

    # -- pre-flight gate (d): structural encode-only machine check ----------
    report = run_encode_only_preflight_gate()
    log(f"GATE (d) ENCODE-ONLY: PASS over {list(report.checked_modules)}")
    state.put(
        "gate_d_encode_only",
        {"status": "PASS", "checked_modules": list(report.checked_modules)},
    )

    # -- pre-flight gate (c): cascade source check --------------------------
    samples, labels = load_inputs(lock, root)
    if len(samples) != ARM_QUERY_N or len(labels) != ARM_LABEL_N:
        raise RuntimeError(f"inputs: {len(samples)} samples / {len(labels)} labels, expected {ARM_QUERY_N}/{ARM_LABEL_N}")
    one_pass_audio = sum(float(sample.audio_seconds) for sample in samples)
    log(
        f"inputs: {len(samples)} audio samples, {len(labels)} canonical labels; one metered audio "
        f"pass = {one_pass_audio:.3f}s (3 audio arms -> {3*one_pass_audio:.3f}s vs ceiling "
        f"{plan.planned_speech_audio_seconds}s)"
    )
    if 3 * one_pass_audio > plan.planned_speech_audio_seconds:
        raise RuntimeError("three audio passes would exceed the plan's metered-audio ceiling")
    expected_ids = frozenset(sample.sample_id for sample in samples)
    cascade = run_cascade_source_check(data_root=root, ledger_text=ledger_text, expected_sample_ids=expected_ids)
    log(
        f"GATE (c) CASCADE SOURCE: {cascade.status} -- {len(cascade.transcripts)}/{ARM_QUERY_N} T0 "
        f"transcripts, registry sha256 {cascade.registry_sha256}, supplement_required="
        f"{cascade.supplement_required}"
    )
    if cascade.status != CASCADE_SOURCE_STATUS_COMPLETE:
        raise RuntimeError(
            f"cascade source check reports {cascade.status}, not COMPLETE. The CASCADE-T0 supplement "
            "is NOT authorized to fly in this attempt (coordinator instruction: STOP and report). "
            "Refusing (fail-closed)."
        )
    state.put(
        "gate_c_cascade_source",
        {
            "status": cascade.status,
            "registry_path": str(cascade.registry_path),
            "registry_sha256": cascade.registry_sha256,
            "transcript_count": len(cascade.transcripts),
            "supplement_required": cascade.supplement_required,
            "supplement_flown": False,
        },
    )
    state.put(
        "one_pass_metered_audio_seconds",
        round(one_pass_audio, 6),
    )

    # -- the synthetic, non-corpus gate clip --------------------------------
    gate_wav = fid.build_gate_wav_bytes()
    gate_wav_path = run_dir / "gate-clip.wav"
    gate_wav_path.write_bytes(gate_wav)
    log(
        f"synthetic gate clip written ({len(gate_wav)} bytes, sha256 "
        f"{hashlib.sha256(gate_wav).hexdigest()}) -- NON-CORPUS: no SLURP audio, no gold"
    )
    state.put("gate_wav_sha256", hashlib.sha256(gate_wav).hexdigest())
    state.put("gate_wav_path", str(gate_wav_path))

    # -- durable attempt ----------------------------------------------------
    store = AttemptStore(attempts_root=root / "attempts")
    prior_calls, prior_audio = store.prior_actual_usage(fid.run_id(), exclude_attempt_id=None)
    log(f"prior durable spend on {fid.run_id()}: calls={prior_calls}, audio_seconds={prior_audio:.6f}")
    if prior_calls or prior_audio:
        log("NOTE: a prior attempt on this run_id has durable spend; this attempt charges against the SAME plan ceiling")
    handle = store.open_attempt(
        fid.run_id(),
        attempt_id,
        carrier_lock_key=fid.CARRIER_LOCK_KEY,
        reserved_calls=plan.planned_model_calls,
        reserved_audio_seconds=float(plan.planned_speech_audio_seconds),
    )
    log(f"attempt opened durably: {attempt_id} (state {handle.state()})")
    state.put("attempt_id", attempt_id)
    state.put("config_hash", cfg_hash)
    state.put("study_commit", args.study_commit)
    state.put("prior_durable_spend", {"calls": prior_calls, "audio_seconds": prior_audio})
    state.put("preflight_completed_at", datetime.now(timezone.utc).isoformat())
    log("PREFLIGHT COMPLETE -- zero contacts spent")
    return 0


# ---------------------------------------------------------------------------
# Stage: gate-b (control import feasibility + audio-path sanity).
# ---------------------------------------------------------------------------


class ChargingControlClient:
    """Minimal ``LocalEncoderClientProtocol`` wrapper that charges the durable
    attempt EXACTLY ONCE PER CONTACT ACTUALLY ISSUED, immediately before the
    encode runs.

    The gate-b stage originally pre-charged one call per control up front, which
    over-charged by one when the first control raised and the second was never
    reached (2026-08-20 11:06:15Z: 2 calls charged, 1 contact issued). Charging
    inside the call path makes the durable spend equal the contacts actually
    attempted -- and a contact that raises AFTER being charged stays spent,
    which is exactly the one-shot semantics this study requires."""

    def __init__(self, inner, *, handle, audio_seconds: float) -> None:
        self._inner = inner
        self._handle = handle
        self._audio_seconds = audio_seconds
        self.charged = 0

    def embed_text(self, *, contact_id: str, text: str):
        self._handle.record_usage(calls=1, audio_seconds=fid.TEXT_CONTACT_AUDIO_SECONDS)
        self.charged += 1
        return self._inner.embed_text(contact_id=contact_id, text=text)

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes):
        self._handle.record_usage(calls=1, audio_seconds=self._audio_seconds)
        self.charged += 1
        return self._inner.embed_audio(contact_id=contact_id, audio_bytes=audio_bytes)


def stage_gate_b(args) -> int:
    import control_loaders

    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    gate_wav = Path(state.document["gate_wav_path"]).read_bytes()
    log(f"GATE (b): control import feasibility + AUDIO-path sanity (attempt state {handle.state()})")

    from speech_aware_evidence_acquisition.rails.local_encoder_client import (
        STATUS_DROPPED_DEPS,
        STATUS_OK,
    )

    clients: dict[str, object] = {}

    def loader_for(arm_id: str):
        def load():
            inner = control_loaders.CONTROL_BUILDERS[arm_id](root)
            client = ChargingControlClient(
                inner, handle=handle, audio_seconds=float(fid.GATE_WAV_SECONDS)
            )
            clients[arm_id] = client
            return client

        return load

    loaders = {
        arm_id: (control_loaders.CONTROL_MODEL_IDS[arm_id], loader_for(arm_id))
        for arm_id in (ARM_M2_ID, ARM_M3_ID)
    }

    # One control at a time, so a runtime failure in one can never prevent the
    # other from being evaluated. The machinery's own gate deliberately lets a
    # non-ImportError surface loud ("a real bug in a present dependency must
    # surface loud, never be misreported as a missing one") -- that is what
    # caught the GLAP device-placement bug. It is caught HERE instead of inside
    # the machinery, under its own distinct, loudly-named status, so the fact is
    # disclosed rather than swallowed AND "a dropped control never blocks
    # M1/M4" still holds.
    results: dict[str, object] = {}
    runtime_failures: dict[str, str] = {}
    for arm_id, entry in loaders.items():
        try:
            results.update(run_control_import_feasibility_gates(loaders={arm_id: entry}))
        except Exception as error:  # noqa: BLE001 -- disclosed, never silent
            runtime_failures[arm_id] = f"{type(error).__name__}: {error}"
            log(f"GATE (b) TEXT [{arm_id}]: DROPPED-RUNTIME-ERROR -- {type(error).__name__}: {error}")

    outcomes: dict[str, object] = {}
    for arm_id, detail in runtime_failures.items():
        outcomes[arm_id] = {
            "model_id": control_loaders.CONTROL_MODEL_IDS[arm_id],
            "text_status": "DROPPED-RUNTIME-ERROR",
            "text_detail": detail,
            "text_sanity_dims": None,
        }
    for arm_id, result in results.items():
        log(f"GATE (b) TEXT [{arm_id}] {result.model_id}: {result.status} -- {result.detail}")
        outcomes[arm_id] = {
            "model_id": result.model_id,
            "text_status": result.status,
            "text_detail": result.detail,
            "text_sanity_dims": None if result.sanity_vector is None else result.sanity_vector.dims,
        }

    # -- the 2026-08-20 coordinator amendment: AUDIO-path sanity ------------
    # Gate (b) as shipped only sanity-embeds the TEXT side, which would leave
    # 156 scored M2/M3 contacts exposed to an audio-path failure discovered
    # mid-arm. One synthetic, NON-CORPUS clip through each control's audio path
    # closes that. A failure -> DROPPED-AUDIO-PATH, the same never-blocking
    # semantics as DROPPED-DEPS; nothing is ever installed.
    for arm_id in loaders:
        entry = outcomes[arm_id]
        if entry["text_status"] != STATUS_OK:
            entry["audio_status"] = "SKIPPED-TEXT-SIDE-ALREADY-DROPPED"
            entry["audio_detail"] = (
                f"the text side already reported {entry['text_status']}; no audio contact issued"
            )
            entry["arm_flyable"] = False
            log(f"GATE (b) AUDIO [{arm_id}]: skipped -- text side already {entry['text_status']}")
            continue
        client = clients.get(arm_id)
        if client is None:
            entry["audio_status"] = "DROPPED-AUDIO-PATH"
            entry["audio_detail"] = "loader did not yield a client instance"
            entry["arm_flyable"] = False
            continue
        try:
            vector = client.embed_audio(contact_id=f"{arm_id}-audio-sanity", audio_bytes=gate_wav)
        except Exception as error:  # noqa: BLE001 -- amendment: ANY audio-path failure drops the arm
            entry["audio_status"] = "DROPPED-AUDIO-PATH"
            entry["audio_detail"] = f"{type(error).__name__}: {error}"
            entry["arm_flyable"] = False
            log(f"GATE (b) AUDIO [{arm_id}]: DROPPED-AUDIO-PATH -- {type(error).__name__}: {error}")
            continue
        entry["audio_status"] = STATUS_OK
        entry["audio_detail"] = f"one synthetic non-corpus audio embed succeeded (dim {vector.dims})"
        entry["audio_sanity_dims"] = vector.dims
        entry["arm_flyable"] = True
        log(f"GATE (b) AUDIO [{arm_id}]: OK -- dim {vector.dims}")

    entries = int(state.document.get("gate_b_entries", 0)) + 1
    state.put("gate_b_entries", entries)
    state.put("gate_b_controls", outcomes)
    flyable = sorted(a for a, o in outcomes.items() if o.get("arm_flyable"))
    log(f"GATE (b) COMPLETE: flyable control arms = {flyable or 'NONE'} (a dropped control never blocks M1/M4)")
    calls, audio = handle.actual_totals()
    log(f"durable spend after gate (b): calls={calls}, audio_seconds={audio:.6f}")
    return 0


# ---------------------------------------------------------------------------
# Server-session helper.
# ---------------------------------------------------------------------------


def spawn_embedder_session(
    *,
    args,
    root: Path,
    run_dir: Path,
    server_key: str,
    gguf_relpaths,
    sha_by_relpath: Mapping[str, str],
    server_args,
    server_env: Mapping[str, str],
    port: int,
):
    committed_runtime = load_runtime_receipt(REPO / "docs" / fid.RUNTIME_RECEIPT_RELPATH)
    receipt_doc = fid.embedder_runtime_receipt(
        committed_runtime, gguf_relpaths=gguf_relpaths, sha256_by_relpath=sha_by_relpath
    )
    assert_no_conflicting_generation_server(
        generation_server_reachable=lambda: _port_reachable(args.host, fid.GENERATION_PORT),
        generation_base_url=f"http://{args.host}:{fid.GENERATION_PORT}",
    )
    log(f"coexistence guard: nothing answers on the generation port {fid.GENERATION_PORT} -- PASS")
    if _port_reachable(args.host, port):
        raise RuntimeError(f"something is already listening on port {port} before session {server_key!r}; refusing")
    session_id = f"{fid.run_id()}-{args.attempt_id}-{server_key}"
    log(f"spawning llama-server in EMBEDDING mode for {server_key!r} on port {port}: {list(server_args)}")
    started = time.time()
    try:
        session = start_session(
            runtime_root=Path(args.runtime_root),
            data_root=root,
            runtime_receipt=receipt_doc,
            host=args.host,
            port=port,
            session_id=session_id,
            extra_argv=list(server_args),
            extra_env=dict(server_env),
            receipt_path=run_dir / f"{fid.run_id()}.session-{server_key}.receipt.json",
            server_log_path=run_dir / f"{fid.run_id()}.session-{server_key}.server.log",
            ready_timeout_seconds=900.0,
        )
    except BaseException:
        # start_session kills nothing and never hands back the Popen, so a
        # readiness TIMEOUT (as opposed to an exit) leaves a live server holding
        # the GPU. Reap our own children only -- never a pattern-matched pkill.
        for pid in _own_llama_server_children():
            log(f"spawn failed: killing orphaned own-child llama-server pid {pid}")
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except OSError:
                pass
        raise
    spawn_seconds = time.time() - started
    log(f"session {server_key!r} up: pid={session.pid} port={session.port} (spawn+load {spawn_seconds:.1f}s)")
    log(f"session argv: {' '.join(session.argv)}")
    for entry in session.model_files:
        log(f"  model file: {entry.path} sha256={entry.sha256}")
    return session, spawn_seconds, started


def session_record(session, *, server_key: str, spawn_seconds: float, resident_seconds: float, teardown, extra=None):
    record = {
        "server_key": server_key,
        "session_id": session.session_id,
        "pid": session.pid,
        "host": session.host,
        "port": session.port,
        "binary_path": session.binary_path,
        "binary_sha256": session.binary_sha256,
        "argv": list(session.argv),
        "model_files": [{"path": m.path, "sha256": m.sha256} for m in session.model_files],
        "started_at": session.started_at,
        "spawn_seconds": round(spawn_seconds, 2),
        "resident_seconds": round(resident_seconds, 2),
        "teardown": teardown,
    }
    if extra:
        record.update(extra)
    return record


# ---------------------------------------------------------------------------
# Stage: m1 (pre-flight gate (a) + the M1 PRIMARY arm).
# ---------------------------------------------------------------------------


def stage_m1(args) -> int:
    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    sha_by_relpath = state.document["model_file_sha256"]
    gate_wav = Path(state.document["gate_wav_path"]).read_bytes()
    expected_marker = resolve_expected_media_marker()
    sessions: list[dict] = list(state.document.get("sessions", []))
    gpu_seconds = float(state.document.get("gpu_occupied_seconds", 0.0))

    already = is_arm_complete(root, ARM_M1_ID)
    gate_a_done = "gate_a_pooling_differ" in state.document
    if already and gate_a_done:
        log(f"[{ARM_M1_ID}] CARRIED: manifest already complete on the data root and gate (a) already recorded -- zero contacts")
        return 0

    lco_env = {
        "LLAMA_MTMD_FEAT_CACHE_DIR": fid.resolve_feat_cache_dir(),
        "LLAMA_MEDIA_MARKER": expected_marker,
    }
    timeout_seconds = float(values["timeout_seconds"])

    # Load the inputs BEFORE any server is spawned. ``load_inputs`` re-hashes
    # every SLURP devel media file (model-free, but minutes of cold 9p I/O after
    # the preflight GGUF sweep evicts the page cache), and doing it inside a
    # resident session would charge all of that CPU-bound time to this flight's
    # GPU accounting against a 0.5 GPU-h ceiling.
    samples: list = []
    labels: list = []
    if not is_arm_complete(root, ARM_M1_ID):
        inputs_started = time.time()
        samples, labels = load_inputs(lock, root)
        log(f"inputs ready in {time.time()-inputs_started:.1f}s (BEFORE any spawn -- not charged to GPU time)")

    # ---- session 1: --pooling mean, ONE gate contact ----------------------
    if not gate_a_done:
        mean_vector_values = None
        session, spawn_seconds, started = spawn_embedder_session(
            args=args, root=root, run_dir=run_dir, server_key="lco-mean",
            gguf_relpaths=fid.lco_gguf_relpaths(), sha_by_relpath=sha_by_relpath,
            server_args=fid.lco_session_args("mean"), server_env=lco_env, port=fid.LCO_PORT,
        )
        try:
            mean_client = EmbeddingClient(
                base_url=f"http://{args.host}:{fid.LCO_PORT}",
                expected_media_marker=expected_marker,
                timeout_seconds=timeout_seconds,
            )
            props = mean_client.verify_media_marker()
            log(f"/props media_marker verified for lco-mean: {props.get('media_marker')!r}; pooling_type={props.get('pooling_type')!r}")
            state.put("props_lco_mean", {k: props[k] for k in sorted(props) if k in ("media_marker", "pooling_type", "n_ctx", "n_batch", "n_ubatch", "model_path", "build_info")})
            handle.record_usage(calls=1, audio_seconds=float(fid.GATE_WAV_SECONDS))
            vector = mean_client.embed_audio(contact_id="pooling-differ-gate", audio_bytes=gate_wav)
            mean_vector_values = vector.values
            log(f"GATE (a) mean-pooled gate vector: dim {vector.dims}")
        finally:
            resident = time.time() - started
            teardown = teardown_session(session.pid, args.host, fid.LCO_PORT)
            gpu_seconds += resident
            sessions.append(session_record(session, server_key="lco-mean", spawn_seconds=spawn_seconds, resident_seconds=resident, teardown=teardown, extra={"pooling_mode": "mean", "contacts": 1}))
            state.put("sessions", sessions)
            state.put("gpu_occupied_seconds", gpu_seconds)
            log(f"session 'lco-mean' torn down after {resident:.1f}s resident")
        if mean_vector_values is None:
            raise RuntimeError("gate (a): the mean-pooled gate contact produced no vector")
        state.put("gate_a_mean_vector_sha256", hashlib.sha256(json.dumps(list(mean_vector_values)).encode()).hexdigest())
        (run_dir / "gate-a-mean-vector.json").write_text(json.dumps(list(mean_vector_values)), encoding="utf-8", newline="\n")

    # ---- session 2: --pooling last -- gate contact + determinism + M1 -----
    session, spawn_seconds, started = spawn_embedder_session(
        args=args, root=root, run_dir=run_dir, server_key="lco-last",
        gguf_relpaths=fid.lco_gguf_relpaths(), sha_by_relpath=sha_by_relpath,
        server_args=fid.lco_session_args("last"), server_env=lco_env, port=fid.LCO_PORT,
    )
    session_contacts = 0
    try:
        client = EmbeddingClient(
            base_url=f"http://{args.host}:{fid.LCO_PORT}",
            expected_media_marker=expected_marker,
            timeout_seconds=timeout_seconds,
        )
        props = client.verify_media_marker()
        log(f"/props media_marker verified for lco-last: {props.get('media_marker')!r}; pooling_type={props.get('pooling_type')!r}")
        state.put("props_lco_last", {k: props[k] for k in sorted(props) if k in ("media_marker", "pooling_type", "n_ctx", "n_batch", "n_ubatch", "model_path", "build_info")})

        if not gate_a_done:
            mean_values = json.loads((run_dir / "gate-a-mean-vector.json").read_text(encoding="utf-8"))
            handle.record_usage(calls=1, audio_seconds=float(fid.GATE_WAV_SECONDS))
            last_vector = client.embed_audio(contact_id="pooling-differ-gate", audio_bytes=gate_wav)
            session_contacts += 1
            if last_vector.dims != len(mean_values):
                raise RuntimeError(
                    f"gate (a): last-pooled dim {last_vector.dims} != mean-pooled dim {len(mean_values)}"
                )
            pooling_override_present = list(last_vector.values) == list(mean_values)
            log(
                "GATE (a) POOLING-DIFFER: "
                + (
                    "BYTE-IDENTICAL -> POOLING-OVERRIDE-PRESENT (section 4 substitutes the scoped verdict names)"
                    if pooling_override_present
                    else "vectors DIFFER -> gate passes clean (model-level verdicts stay in scope)"
                )
            )
            (run_dir / "gate-a-last-vector.json").write_text(json.dumps(list(last_vector.values)), encoding="utf-8", newline="\n")

            # Registration section 6: repeat-call determinism sample for THIS
            # server session -- the SAME synthetic non-corpus clip, again, on
            # the AUDIO path M1 actually scores. sha256-equality only; the
            # cosine tolerance evaluation is the read suite's job.
            handle.record_usage(calls=1, audio_seconds=float(fid.GATE_WAV_SECONDS))
            repeat_vector = client.embed_audio(contact_id="lco-jitter-b", audio_bytes=gate_wav)
            session_contacts += 1
            a_sha = hashlib.sha256(json.dumps(list(last_vector.values)).encode()).hexdigest()
            b_sha = hashlib.sha256(json.dumps(list(repeat_vector.values)).encode()).hexdigest()
            log(f"LCO repeat-call determinism sample: byte_identical={a_sha == b_sha}")
            (run_dir / "lco-jitter-vectors.json").write_text(
                json.dumps({"a": list(last_vector.values), "b": list(repeat_vector.values)}), encoding="utf-8", newline="\n"
            )
            state.put(
                "gate_a_pooling_differ",
                {
                    "pooling_override_present": pooling_override_present,
                    "dims": last_vector.dims,
                    "mean_vector_sha256": hashlib.sha256(json.dumps(mean_values).encode()).hexdigest(),
                    "last_vector_sha256": a_sha,
                    "boots": 2,
                    "contacts": 2,
                    "gate_clip": "synthetic 2s 440Hz sine, non-corpus",
                },
            )
            state.put(
                "lco_repeat_call_determinism",
                {
                    "server_session": "lco-last",
                    "kind": "audio",
                    "vector_a_sha256": a_sha,
                    "vector_b_sha256": b_sha,
                    "byte_identical": a_sha == b_sha,
                    "contacts": 1,
                    "note": (
                        "vector_a is the pooling-differ gate contact itself, reused as the first half "
                        "of the pair; only one additional contact was spent. Cosine tolerance is "
                        "analysis.pemb3m_read's job -- this flight records sha256 equality only."
                    ),
                },
            )

        if not is_arm_complete(root, ARM_M1_ID):
            audio_seconds_by_contact = {s.sample_id: float(s.audio_seconds) for s in samples}
            vector_log = run_dir / f"vectors-{ARM_M1_ID}.jsonl"
            cached = load_cached(vector_log)
            if cached:
                log(f"[{ARM_M1_ID}] resume: {len(cached)} cached vectors will be replayed without a tool contact")
            proxy = BudgetedCachingProxy(
                client, arm_id=ARM_M1_ID, store=store, handle=handle, plan=plan,
                vector_log=vector_log, cached=cached,
                audio_seconds_by_contact=audio_seconds_by_contact, total_contacts=ARM_TOTAL_N,
            )
            arm_started = time.time()
            log(f"ARM START {ARM_M1_ID}: LCO-3B --pooling last, bare content both sides -> {ARM_TOTAL_N} contacts, ZERO generation")
            summary = run_m1_arm_flight(
                client=proxy, samples=samples, canonical_labels=labels,
                split_identity_hash=fid.split_identity_hash(), data_root=root,
            )
            arm_wall = time.time() - arm_started
            manifest_path = write_pemb3m_arm_manifest(root, summary)
            session_contacts += proxy.flown
            log(f"[{ARM_M1_ID}] manifest written: {manifest_path} (NOT read back by this launcher)")
            log(f"ARM DONE {ARM_M1_ID}: {arm_wall:.1f}s, flown={proxy.flown} replayed={proxy.replayed}")
            record_arm(state, ARM_M1_ID, proxy, summary, manifest_path, arm_wall, server_key="lco-last")
    finally:
        resident = time.time() - started
        teardown = teardown_session(session.pid, args.host, fid.LCO_PORT)
        gpu_seconds += resident
        sessions.append(session_record(session, server_key="lco-last", spawn_seconds=spawn_seconds, resident_seconds=resident, teardown=teardown, extra={"pooling_mode": "last", "contacts": session_contacts}))
        state.put("sessions", sessions)
        state.put("gpu_occupied_seconds", gpu_seconds)
        log(f"session 'lco-last' torn down after {resident:.1f}s resident; cumulative GPU-occupied {gpu_seconds/3600:.4f} h")
    return 0


def record_arm(state: FlightState, arm_id: str, proxy, summary, manifest_path, wall_seconds, *, server_key: str) -> None:
    arms = dict(state.document.get("arms", {}))
    arms[arm_id] = {
        "arm_id": arm_id,
        "manifest_run_id": arm_run_id(arm_id),
        "model_lock_key": ARMS_BY_ID[arm_id].model_lock_key,
        "embedding_dim": summary.embedding_dim,
        "server_key": server_key,
        "n_query_vectors": len(summary.query_vectors),
        "n_label_vectors": len(summary.label_vectors),
        "n_jitter_vectors": len(summary.jitter_vectors),
        "n_contacts": len(summary.query_vectors) + len(summary.label_vectors) + len(summary.jitter_vectors),
        "embedding_manifest_path": str(manifest_path),
        "contacts_flown": proxy.flown,
        "contacts_replayed": proxy.replayed,
        "contact_failures": list(proxy.failures),
        "flown_by_kind": dict(proxy.flown_by_kind),
        "latency_seconds_by_kind": {k: round(v, 3) for k, v in proxy.latency_by_kind.items()},
        "mean_latency_seconds_by_kind": {
            k: round(v / max(proxy.flown_by_kind[k], 1), 3) for k, v in proxy.latency_by_kind.items()
        },
        "wall_seconds": round(wall_seconds, 2),
    }
    state.put("arms", arms)


# ---------------------------------------------------------------------------
# Stage: m23 (the two in-process control arms).
# ---------------------------------------------------------------------------


def stage_m23(args) -> int:
    import control_loaders

    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    gate_b = state.document.get("gate_b_controls") or {}
    if not gate_b:
        raise RuntimeError("stage m23 requires gate (b) to have run first (no gate_b_controls in the flight state)")

    samples, labels = load_inputs(lock, root)
    audio_seconds_by_contact = {s.sample_id: float(s.audio_seconds) for s in samples}
    gpu_seconds = float(state.document.get("gpu_occupied_seconds", 0.0))

    for arm_id in (ARM_M2_ID, ARM_M3_ID):
        outcome = gate_b.get(arm_id, {})
        if not outcome.get("arm_flyable"):
            log(
                f"[{arm_id}] NOT FLOWN: gate (b) reported text={outcome.get('text_status')!r} "
                f"audio={outcome.get('audio_status')!r} -- a dropped control never blocks M1/M4"
            )
            continue
        if is_arm_complete(root, arm_id):
            log(f"[{arm_id}] CARRIED: manifest already complete on the data root -- zero contacts, zero spend")
            continue
        log(f"[{arm_id}] loading the control model in-process (transformers, shared venv AS-IS)")
        # An in-process control runs its encoder on the SAME GPU a server
        # session would occupy, so its whole load+encode wall time is charged to
        # the flight's GPU accounting exactly like a session's resident time.
        gpu_started = time.time()
        load_started = time.time()
        client = control_loaders.CONTROL_BUILDERS[arm_id](root)
        log(f"[{arm_id}] model loaded in {time.time()-load_started:.1f}s")
        vector_log = run_dir / f"vectors-{arm_id}.jsonl"
        cached = load_cached(vector_log)
        if cached:
            log(f"[{arm_id}] resume: {len(cached)} cached vectors will be replayed without a tool contact")
        proxy = BudgetedCachingProxy(
            client, arm_id=arm_id, store=store, handle=handle, plan=plan,
            vector_log=vector_log, cached=cached,
            audio_seconds_by_contact=audio_seconds_by_contact, total_contacts=ARM_TOTAL_N,
            supports_prefix=False, supports_marker=False,
        )
        arm_started = time.time()
        log(f"ARM START {arm_id}: in-process control, bare content both sides -> {ARM_TOTAL_N} contacts")
        summary = run_local_encoder_arm_flight(
            arm_id=arm_id, client=proxy, samples=samples, canonical_labels=labels,
            split_identity_hash=fid.split_identity_hash(), data_root=root,
        )
        arm_wall = time.time() - arm_started
        manifest_path = write_pemb3m_arm_manifest(root, summary)
        log(f"[{arm_id}] manifest written: {manifest_path} (NOT read back by this launcher)")
        log(f"ARM DONE {arm_id}: {arm_wall:.1f}s, flown={proxy.flown} replayed={proxy.replayed}")
        record_arm(state, arm_id, proxy, summary, manifest_path, arm_wall, server_key="in-process")
        gpu_seconds += time.time() - gpu_started
        state.put("gpu_occupied_seconds", gpu_seconds)
        log(f"[{arm_id}] GPU-occupied this arm {time.time()-gpu_started:.1f}s; cumulative {gpu_seconds/3600:.4f} h")
        del client, proxy
        try:
            import gc

            import torch

            gc.collect()
            torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001 -- best-effort VRAM release between controls
            pass
    return 0


# ---------------------------------------------------------------------------
# Stage: m4 (the cascade arm).
# ---------------------------------------------------------------------------


def stage_m4(args) -> int:
    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    sha_by_relpath = state.document["model_file_sha256"]
    sessions: list[dict] = list(state.document.get("sessions", []))
    gpu_seconds = float(state.document.get("gpu_occupied_seconds", 0.0))

    if is_arm_complete(root, ARM_M4_ID):
        log(f"[{ARM_M4_ID}] CARRIED: manifest already complete on the data root -- zero contacts, zero spend")
        return 0

    ledger_text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    samples, labels = load_inputs(lock, root)
    expected_ids = frozenset(sample.sample_id for sample in samples)
    cascade = run_cascade_source_check(data_root=root, ledger_text=ledger_text, expected_sample_ids=expected_ids)
    if cascade.status != CASCADE_SOURCE_STATUS_COMPLETE:
        raise RuntimeError(f"cascade source re-check reports {cascade.status}; refusing to fly M4")
    log(f"cascade source re-verified at M4 entry: {cascade.status}, registry sha256 {cascade.registry_sha256}")

    session, spawn_seconds, started = spawn_embedder_session(
        args=args, root=root, run_dir=run_dir, server_key="qwen3-emb",
        gguf_relpaths=fid.qwen3_emb_gguf_relpaths(), sha_by_relpath=sha_by_relpath,
        server_args=fid.QWEN3_EMB_SERVER_ARGS, server_env={}, port=fid.QWEN3_EMB_PORT,
    )
    session_contacts = 0
    try:
        # A text-only embedding server has no mmproj and no media-marker
        # concept: rails.embedding_client's own EXTENSION seam for exactly this
        # caller (require_marker_verification=False, expected_dim=1024).
        client = EmbeddingClient(
            base_url=f"http://{args.host}:{fid.QWEN3_EMB_PORT}",
            timeout_seconds=float(values["timeout_seconds"]),
            expected_dim=QWEN3_EMB_EMBEDDING_DIM,
            require_marker_verification=False,
        )
        client.verify_media_marker()
        import urllib.request

        with urllib.request.urlopen(f"http://{args.host}:{fid.QWEN3_EMB_PORT}/props", timeout=30) as response:
            props = json.loads(response.read().decode("utf-8"))
        log(
            f"/props for qwen3-emb (text-only, no media marker to verify): pooling_type="
            f"{props.get('pooling_type')!r} media_marker={props.get('media_marker')!r}"
        )
        state.put("props_qwen3_emb", {k: props[k] for k in sorted(props) if k in ("media_marker", "pooling_type", "n_ctx", "n_batch", "n_ubatch", "model_path", "build_info")})

        # Registration section 6: repeat-call determinism sample for THIS
        # server session (E-1 Mission C: qwen3-emb is NOT bit-exact across
        # identical GPU calls). Two contacts, persisted into M4's own manifest
        # so the read suite can evaluate the declared >= 0.9999 tolerance.
        for _ in range(2):
            handle.record_usage(calls=1, audio_seconds=fid.TEXT_CONTACT_AUDIO_SECONDS)
        jitter_a, jitter_b = run_m4_repeat_call_gate(client=client, text="repeat call determinism sample")
        session_contacts += 2
        a_sha = hashlib.sha256(json.dumps(list(jitter_a.values)).encode()).hexdigest()
        b_sha = hashlib.sha256(json.dumps(list(jitter_b.values)).encode()).hexdigest()
        log(f"M4 repeat-call determinism sample: dims={jitter_a.dims}, byte_identical={a_sha == b_sha}")
        state.put(
            "m4_repeat_call_determinism",
            {
                "server_session": "qwen3-emb",
                "kind": "text",
                "dims": jitter_a.dims,
                "vector_a_sha256": a_sha,
                "vector_b_sha256": b_sha,
                "byte_identical": a_sha == b_sha,
                "contacts": 2,
                "note": (
                    "persisted into M4's own manifest jitter side; the declared cosine >= 0.9999 "
                    "tolerance (E-1 Mission C) is analysis.pemb3m_read's job, not this flight's"
                ),
            },
        )

        vector_log = run_dir / f"vectors-{ARM_M4_ID}.jsonl"
        cached = load_cached(vector_log)
        if cached:
            log(f"[{ARM_M4_ID}] resume: {len(cached)} cached vectors will be replayed without a tool contact")
        proxy = BudgetedCachingProxy(
            client, arm_id=ARM_M4_ID, store=store, handle=handle, plan=plan,
            vector_log=vector_log, cached=cached, audio_seconds_by_contact={}, total_contacts=ARM_TOTAL_N,
        )
        arm_started = time.time()
        log(f"ARM START {ARM_M4_ID}: qwen3-emb text-text over the CONSUMED pkey2-338 T0 transcripts -> {ARM_TOTAL_N} contacts")
        summary = run_m4_arm_flight(
            client=proxy, transcript_registry=cascade.transcripts, canonical_labels=labels,
            split_identity_hash=fid.split_identity_hash(), jitter_vectors=(jitter_a, jitter_b),
        )
        arm_wall = time.time() - arm_started
        manifest_path = write_pemb3m_arm_manifest(root, summary)
        session_contacts += proxy.flown
        log(f"[{ARM_M4_ID}] manifest written: {manifest_path} (NOT read back by this launcher)")
        log(f"ARM DONE {ARM_M4_ID}: {arm_wall:.1f}s, flown={proxy.flown} replayed={proxy.replayed}")
        record_arm(state, ARM_M4_ID, proxy, summary, manifest_path, arm_wall, server_key="qwen3-emb")
    finally:
        resident = time.time() - started
        teardown = teardown_session(session.pid, args.host, fid.QWEN3_EMB_PORT)
        gpu_seconds += resident
        sessions.append(session_record(session, server_key="qwen3-emb", spawn_seconds=spawn_seconds, resident_seconds=resident, teardown=teardown, extra={"pooling_mode": "last", "contacts": session_contacts}))
        state.put("sessions", sessions)
        state.put("gpu_occupied_seconds", gpu_seconds)
        log(f"session 'qwen3-emb' torn down after {resident:.1f}s resident; cumulative GPU-occupied {gpu_seconds/3600:.4f} h")
    return 0


# ---------------------------------------------------------------------------
# Stage: finalize.
# ---------------------------------------------------------------------------


def stage_finalize(args) -> int:
    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    gate_b = state.document.get("gate_b_controls") or {}
    arms = state.document.get("arms") or {}

    expected_arms = [ARM_M1_ID, ARM_M4_ID] + [
        arm_id for arm_id in (ARM_M2_ID, ARM_M3_ID) if gate_b.get(arm_id, {}).get("arm_flyable")
    ]
    dropped_arms = [arm_id for arm_id in (ARM_M2_ID, ARM_M3_ID) if not gate_b.get(arm_id, {}).get("arm_flyable")]

    arm_status: dict[str, object] = {}
    produced = 0
    for arm_id in (ARM_M1_ID, ARM_M2_ID, ARM_M3_ID, ARM_M4_ID):
        complete = is_arm_complete(root, arm_id)
        manifest_path = root / "derived" / "embeddings" / arm_run_id(arm_id) / "manifest.json"
        info: dict[str, object] = {"complete": complete, "manifest_path": str(manifest_path)}
        if complete:
            document = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = document.get("entries", [])
            npy_present = sum(1 for e in entries if (root / str(e.get("relpath", ""))).is_file())
            info.update(
                {
                    "dims": document.get("dims"),
                    "query_count": document.get("query_count"),
                    "label_count": document.get("label_count"),
                    "jitter_count": document.get("jitter_count"),
                    "entry_count": len(entries),
                    "npy_present": npy_present,
                    "distinct_vector_sha256": len({e.get("sha256") for e in entries}),
                }
            )
            produced += int(document.get("query_count", 0)) + int(document.get("label_count", 0))
        arm_status[arm_id] = info
        log(f"  {arm_id}: complete={complete} " + (f"entries={info.get('entry_count')} npy={info.get('npy_present')} dims={info.get('dims')}" if complete else "(not flown)"))

    missing = [arm_id for arm_id in expected_arms if not arm_status[arm_id]["complete"]]
    if missing:
        raise RuntimeError(f"finalize refused: expected arms {missing} are not complete on the data root")
    expected_scored = len(expected_arms) * ARM_TOTAL_N
    log(
        f"sweep-total invariant (scored product on disk across flyable arms): {produced} contacts, "
        f"expected {expected_scored} -- {'PASS' if produced == expected_scored else 'FAIL'}"
    )
    if produced != expected_scored:
        raise RuntimeError(f"sweep produced {produced} scored contacts, expected {expected_scored}")

    gpu_seconds = float(state.document.get("gpu_occupied_seconds", 0.0))
    try:
        handle.record_gpu_seconds(gpu_seconds)
    except Exception as exc:  # noqa: BLE001 -- never mask the flight's own outcome
        log(f"record_gpu_seconds failed (non-fatal): {type(exc).__name__}: {exc}")
    actual_calls, actual_audio = handle.actual_totals()
    handle.mark_finalized()
    log(f"attempt {args.attempt_id} FINALIZED")

    receipt = {
        "run_id": fid.run_id(),
        "probe": fid.PROBE_LABEL,
        "attempt_id": args.attempt_id,
        "status": "COMPLETED",
        "preregistration": fid.PREREGISTRATION_RELPATH,
        "e1_identity_record": fid.E1_IDENTITY_RELPATH,
        "study_commit_at_takeoff": state.document.get("study_commit"),
        "config_hash": cfg_hash,
        "protocol_hash": plan.protocol_hash,
        "split_identity_hash": plan.split_identity_hash,
        "binding_config_sha256": state.document.get("binding_config_sha256"),
        "umbrella_lock_sha256": state.document.get("umbrella_lock_sha256"),
        "gate_scope_note": state.document.get("gate_scope_note"),
        "tier": "embedding (encode+pool, ZERO generation, zero sampling seam)",
        "frozen_core_loaded": False,
        "gates": {
            "a_pooling_differ": state.document.get("gate_a_pooling_differ"),
            "b_controls": gate_b,
            "c_cascade_source": state.document.get("gate_c_cascade_source"),
            "d_encode_only": state.document.get("gate_d_encode_only"),
        },
        "determinism_samples": {
            "lco_last": state.document.get("lco_repeat_call_determinism"),
            "qwen3_emb": state.document.get("m4_repeat_call_determinism"),
            "note": (
                "recorded as sha256 equality only -- registration section 6's cosine >= 0.9999 "
                "tolerance evaluation belongs to analysis.pemb3m_read, never to the flight. "
                "The lco-mean gate boot carries no pair of its own (it exists only to produce the "
                "one vector the byte-compare needs, and the 10-contact gate allowance is fully "
                "committed); M2/M3 are in-process with no server session at all."
            ),
        },
        "model_file_sha256": state.document.get("model_file_sha256"),
        "model_file_measurements": state.document.get("model_file_measurements"),
        "umbrella_lock_crosscheck": state.document.get("umbrella_lock_crosscheck"),
        "props": {
            "lco_mean": state.document.get("props_lco_mean"),
            "lco_last": state.document.get("props_lco_last"),
            "qwen3_emb": state.document.get("props_qwen3_emb"),
        },
        "gate_wav_sha256": state.document.get("gate_wav_sha256"),
        "arms": arms,
        "arm_manifest_status_final": arm_status,
        "arms_flown": sorted(expected_arms),
        "arms_dropped": sorted(dropped_arms),
        "sessions": state.document.get("sessions", []),
        "n_contacts_expected_per_arm": ARM_TOTAL_N,
        "n_query_contacts_expected_per_arm": ARM_QUERY_N,
        "n_label_contacts_expected_per_arm": ARM_LABEL_N,
        "n_scored_contacts_registered": PLANNED_TOTAL_EMBEDDING_CONTACTS,
        "n_scored_contacts_produced": produced,
        "planned_gate_contacts": fid.PLANNED_GATE_CONTACTS,
        "gate_contact_plan": dict(fid.GATE_CONTACT_PLAN),
        "planned_budgets": dict(fid.PLANNED_BUDGETS),
        "registered_ceilings": state.document.get("registered_ceilings"),
        "one_pass_metered_audio_seconds": state.document.get("one_pass_metered_audio_seconds"),
        "durable_actual": {
            "calls": actual_calls,
            "audio_seconds": actual_audio,
            "gpu_seconds": handle.actual_gpu_seconds(),
            "gpu_hours": handle.actual_gpu_seconds() / 3600.0,
        },
        "prior_durable_spend_before_this_attempt": state.document.get("prior_durable_spend"),
        "cascade_t0_supplement_flown": False,
        "result_read": False,
        "result_read_note": (
            "THIS FLIGHT READ NO RESULT: no cosine, no argmax, no ranking, no accuracy, no per-arm "
            "verdict; scoring-side gold was never loaded. The two byte-level comparisons recorded "
            "above (POOLING-DIFFER, repeat-call determinism) are instrument-health facts the "
            "registration itself mandates."
        ),
    }
    receipt_path = run_dir / "flight-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str), encoding="utf-8", newline="\n")
    log(f"flight receipt: {receipt_path}")
    log(
        f"durable spend this attempt: calls={actual_calls}, audio_seconds={actual_audio:.3f}, "
        f"gpu_hours={handle.actual_gpu_seconds()/3600.0:.4f}"
    )
    log(
        f"vs registered ceilings: {actual_calls}/{fid.REGISTERED_CEILINGS['model_calls']} calls, "
        f"{actual_audio:.1f}/{fid.REGISTERED_CEILINGS['speech_audio_seconds']}s audio, "
        f"{handle.actual_gpu_seconds()/3600.0:.4f}/{fid.REGISTERED_CEILINGS['gpu_hours']} GPU-h"
    )
    return 0


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=STAGES)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--runtime-root", default="/home/chao")
    parser.add_argument("--study-commit", default=None)
    args = parser.parse_args()
    if args.attempt_id is None:
        if args.stage != "preflight":
            raise SystemExit("--attempt-id is required for every stage after preflight")
        args.attempt_id = fresh_attempt_id()
        print(f"ATTEMPT_ID={args.attempt_id}", flush=True)

    handlers = {
        "preflight": stage_preflight,
        "gate-b": stage_gate_b,
        "m1": stage_m1,
        "m23": stage_m23,
        "m4": stage_m4,
        "finalize": stage_finalize,
    }
    started = time.time()
    try:
        code = handlers[args.stage](args)
    except BaseException as error:  # noqa: BLE001 -- always land evidence
        log(f"STAGE {args.stage} FAILED: {type(error).__name__}: {error}")
        raise
    log(f"STAGE {args.stage} OK in {time.time()-started:.1f}s")
    print(f"ATTEMPT_ID={args.attempt_id}", flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
