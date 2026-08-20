"""P-EMB-4R flight launcher (REGISTERED probe, exposure row
``SAEA-PROBE-pemb4r-4100``).

Seven embedding arms over FOUR embedding models (each model's own 900-row key
bank embedded exactly ONCE and shared by that model's arms), a flight-side
gold-free retrieval plan, and C-DECODE: 60 closed-set generation calls on the
pinned q4km frozen core over the retrieval-shrunk label space.

Structurally the archived P-EMB-3M launcher
(``docs/checks/speech-aware-evidence-acquisition/2026-08-20-pemb3m-flight/
launcher/launch_pemb3m_flight.py``) -- its ``BudgetedCachingProxy``, its
zombie-safe ``_pid_alive``, its by-pid teardown, its staged
``--stage``/``--attempt-id`` shape and its arm-level idempotence are reused in
kind -- crossed with the archived P-CORR-F launcher's own frozen-core path
(``FrozenCoreGate`` -> ``start_session`` -> ``TRANSPORTS.resolve`` ->
``FrozenCoreClient``) for the single C-DECODE stage, with the deltas this
registration forces:

1. STAGED, not one-shot. The harness that drives this launcher reaps a command
   at 60 minutes, so the flight is a sequence of ``--stage`` invocations
   (``preflight`` / ``lco3`` / ``lco7`` / ``qw`` / ``glap`` / ``retrieval`` /
   ``cdecode`` / ``finalize``) sharing ONE ExecutionPlan, ONE durable attempt
   and ONE run directory. Bank-level and arm-level idempotence
   (``rails.probes.pemb4r_flight.is_bank_vectors_complete`` /
   ``is_query_vectors_complete``) is what makes that safe: a stage whose bank
   or arm is already complete on the data root re-flies nothing and spends
   nothing, so a reaped or aborted stage is resumed by re-running it, never by
   re-spending.
2. THE FROZEN CORE IS LOADED EXACTLY ONCE, AT THE END. Every kNN arm is a
   TOOL contact against a pinned embedder (the P-EMB-3M gate discipline:
   plan validation, exposure pre-registration, carrier scope, E0 closure +
   scoring freeze, llama.cpp runtime-library verification run explicitly, and
   every served embedder GGUF byte fully SHA-256'd in preflight). C-DECODE is a
   genuine frozen-core contact and therefore runs the FULL
   ``FrozenCoreGate.assert_model_touch_allowed`` -- including the q4km GGUF
   attestation -- BEFORE it spawns anything. That ordering is the P-CORR-F
   section-8 ruling's own FORWARD RULE, carried verbatim: build the transport
   and every payload binding before spawning any server, so model-identity
   hashing never runs while a server session holds VRAM idle.
3. THE POOLING-DIFFER GATE RUNS SEQUENTIALLY, NOT CONCURRENTLY. The machinery's
   ``run_pooling_differ_gate`` takes a LIVE ``last_client`` and a LIVE
   ``mean_client`` at the same instant, i.e. two resident llama-server sessions
   over the same weights. For LCO-7B that is 2 x ~12.6 GB against 23.1 GB of
   free VRAM on this host -- an OOM, not a gate. So this launcher carries the
   ARCHIVED P-EMB-3M PRECEDENT instead (``stage_m1``: boot ``--pooling last``,
   embed the synthetic gate clip, tear down, boot ``--pooling mean``, embed the
   SAME clip, tear down, byte-compare the persisted vectors). The COMPUTATION
   is identical -- ``last_vector.values == mean_vector.values``, the machinery's
   own one-line verdict -- and the machinery is not modified; only the
   concurrency is. Documented deviation, recorded here, in the flight receipt
   and in the archived README.

KNOWN DEFECTS IN THE ``cdecode`` STAGE, recorded honestly rather than silently
repaired. This is the instrument AS FLOWN on 2026-08-20; the seven embedding
arms and the retrieval plan flew on it end to end, but the C-DECODE path was
exercised only as far as the frozen-core gate and the server spawn before it
refused (registered metered-audio ceiling -- see the flight receipt's
``c_decode_blocked``). Everything past that point in this file is therefore
UNEXERCISED against a real core, and carries two defects a follow-on must fix
deliberately:

1. **The plan's ``attempt_id`` collides.** ``core.model.FrozenCoreAdapter``
   opens its OWN durable attempt for ``plan.attempt_id`` (invariant I6, a
   one-time ``(run_id, attempt_id)`` key), and this launcher's preflight has
   already opened that id for the embedding arms. A follow-on must build the
   C-DECODE ``ExecutionPlan`` with a FRESH SIBLING attempt id; sibling spend is
   summed into the same ceiling by ``AttemptStore.prior_actual_usage``, so the
   accounting stays correct.
2. **``GenerationHealthProxy`` would double-charge.** It charges the durable
   attempt and re-checks the ceilings itself, but ``FrozenCoreAdapter`` already
   does both (``core.model.adapter``, under its own metering lock) for every
   frozen-core request. The proxy's charging and ceiling arithmetic must be
   removed and its role reduced to response caching and health logging; the
   adapter's accounting is authoritative. The same applies to the manual
   ``handle.record_usage`` in front of the determinism resend.

A third, factual defect WAS repaired, because it had already written a false
number into the landed evidence: the teardown block recorded the q4km session's
contact count from a hardcoded ``QUERY_N + 1`` instead of the measured count,
so a session that issued nothing was recorded as 61 contacts. It now records
the measured ``session_contacts``, and the landed receipt carries the
correction under its own ``corrections`` key.

THIS LAUNCHER NEVER READS A RESULT. Embedding VECTORS, the retrieval PLAN and
C-DECODE's raw RESPONSES are the flight's own product and are written to the
data root, but nothing here ever scores any of them: no accuracy, no recall, no
vote evaluation, no gold-vs-prediction comparison anywhere, and the frozen 60's
own devel gold is never loaded (machine-checked by
``rails.probes.pemb4r_flight.assert_never_accesses_frozen_60_gold``, an AST
guard this launcher re-runs explicitly). That is the separately registered
one-shot read mission's job (``analysis.pemb4r_read``).

The retrieval plan IS built here, on purpose and by design: retrieval is a PURE
function of already-flown vectors plus the bank's own TRAIN-split VALUE
metadata (the module docstring of ``rails.probes.pemb4r_flight``, registration
section 3 item 8). It involves no scoring-side gold whatsoever, and C-DECODE
cannot be constructed without it. ``analysis.pemb4r_read`` independently
RE-DERIVES the same retrieval from the same vectors and compares it
byte-for-byte rather than trusting this artifact.

The byte-level comparisons this launcher DOES perform are instrument-health
facts the registration itself mandates, not results: the two POOLING-DIFFER
byte-compares, the three embedding repeat-call determinism samples, and the one
C-DECODE identical-prompt resend. All are recorded as sha256 equality only;
tolerance evaluation belongs to the read suite. Health logging prints only the
contact index, kind, contact id, latency, dimension and response LENGTH --
never a vector component, never a response body.
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
from typing import Mapping, Sequence

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import flight_identity as fid  # noqa: E402

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: E402
from speech_aware_evidence_acquisition.core.driver.smoke import fresh_attempt_id  # noqa: E402
from speech_aware_evidence_acquisition.core.session import load_runtime_receipt, start_session  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.embedding_client import (  # noqa: E402
    EmbeddingClient,
    EmbeddingVector,
    assert_no_conflicting_generation_server,
    resolve_expected_media_marker,
)
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F  # noqa: E402

STAGES = ("preflight", "lco3", "lco7", "qw", "glap", "retrieval", "cdecode", "finalize")

MODEL_STAGE_ORDER = ("lco3", "lco7", "qw", "glap")


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)


# ---------------------------------------------------------------------------
# Process / port helpers (P-EMB-3L/3M launchers, reused in kind).
# ---------------------------------------------------------------------------


def _port_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pid_alive(pid: int) -> bool:
    """Zombie-safe liveness for a server THIS process spawned: reap first
    (``waitpid(WNOHANG)``), then treat a ``Z`` state as dead, and only then
    fall back to the signal probe -- ``os.kill(pid, 0)`` SUCCEEDS on a zombie
    and would report an already-exited server as alive forever."""

    try:
        reaped, _status = os.waitpid(pid, os.WNOHANG)
        if reaped == pid:
            return False
    except (ChildProcessError, OSError):
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
    ``start_session`` returned -- never a pattern-matched ``pkill``."""

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
    """Every live ``llama-server`` whose PPid is THIS process -- scoped to our
    OWN children by construction, so it can never reach a sibling campaign."""

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


def _vector_sha256(values: Sequence[float]) -> str:
    return hashlib.sha256(json.dumps(list(values)).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Durable, budget-enforcing, caching EMBEDDING contact proxy (P-EMB-3M's own).
# ---------------------------------------------------------------------------


class BudgetedCachingProxy:
    """Wraps either an ``EmbeddingClientProtocol`` (wire) or a
    ``LocalEncoderClientProtocol`` (in-process) and (a) enforces the plan's own
    call/audio ceilings against the DURABLE store before every contact,
    (b) persists the spend BEFORE the request leaves the process, (c) caches
    every returned vector for resume, and (d) logs OPERATIONAL health only --
    never a vector component.

    ONE proxy per SWEEP (its own contact index and vector cache), but the
    running spend counters are SEEDED from the durable attempt's own totals at
    construction, so a later sweep never restarts its ceiling arithmetic from
    zero after an earlier one has already spent under the same attempt."""

    def __init__(
        self,
        inner,
        *,
        sweep_id: str,
        store: AttemptStore,
        handle,
        plan: ExecutionPlan,
        vector_log: Path,
        cached: list[dict],
        audio_seconds_by_contact: Mapping[str, float],
        total_contacts: int,
        supports_prefix: bool = True,
        supports_marker: bool = True,
        log_every: int = 100,
    ) -> None:
        self._inner = inner
        self._sweep_id = sweep_id
        self._store = store
        self._handle = handle
        self._plan = plan
        self._vector_log = vector_log
        self._cached = cached
        self._audio_seconds_by_contact = dict(audio_seconds_by_contact)
        self._total = total_contacts
        self._supports_prefix = supports_prefix
        self._supports_marker = supports_marker
        self._log_every = max(int(log_every), 1)
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
            f"[{self._sweep_id}] media marker verified against the LIVE server's GET /props -- the "
            "env-pinned LLAMA_MEDIA_MARKER matches the server's own media_marker field (fail-closed)"
        )
        return props

    def embed_text(self, *, contact_id: str, text: str, prefix: str = "") -> EmbeddingVector:
        payload_sha256 = hashlib.sha256((prefix + text).encode("utf-8")).hexdigest()
        if self._supports_prefix:
            send = lambda: self._inner.embed_text(contact_id=contact_id, text=text, prefix=prefix)  # noqa: E731
        else:
            if prefix:
                raise RuntimeError(f"[{self._sweep_id}] inner client accepts no prefix but one was given")
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
                raise RuntimeError(f"[{self._sweep_id}] inner client accepts no prompt_prefix but one was given")
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
                    f"[{self._sweep_id}] resume divergence at contact {index}: cached "
                    f"({entry['kind']}, {entry['contact_id']!r}, {entry['payload_sha256'][:12]}...) "
                    f"!= rebuilt ({kind}, {contact_id!r}, {payload_sha256[:12]}...); refusing to "
                    "replay a vector that does not belong to this contact (fail-closed)"
                )
            self.replayed += 1
            if index % self._log_every == 0 or index == len(self._cached):
                log(f"[{self._sweep_id}] replay {index}/{len(self._cached)} from cache")
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
        self.calls_used, self.audio_seconds_used = self._handle.record_usage(calls=1, audio_seconds=audio_seconds)

        started = time.time()
        try:
            vector = send()
        except Exception as error:  # noqa: BLE001 -- health accounting, then re-raise
            elapsed = time.time() - started
            self.failures.append(
                {
                    "sweep_id": self._sweep_id,
                    "index": index,
                    "kind": kind,
                    "contact_id": contact_id,
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            log(
                f"[{self._sweep_id}] contact {index:04d} [{kind}] {contact_id} FAILED after "
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
                        "sweep_id": self._sweep_id,
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
        if index % self._log_every == 0 or index == self._total or index <= 3:
            rate = self.flown / max(time.time() - self._started_at, 1e-9)
            remaining = max(self._total - index, 0)
            log(
                f"[{self._sweep_id}] contact {index:04d}/{self._total} [{kind}] {contact_id} ok "
                f"{elapsed:6.2f}s dims={vector.dims} | flown={self.flown} {rate*60:.1f}/min "
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


class ChargingGateClient:
    """A gate contact charges the durable attempt EXACTLY ONCE PER CONTACT
    ACTUALLY ISSUED, immediately before the request leaves the process (the
    P-EMB-3M ``ChargingControlClient`` lesson: pre-charging a batch over-charges
    when a later contact is never reached). A contact that raises AFTER being
    charged stays spent -- exactly the one-shot semantics this study requires."""

    def __init__(self, inner, *, handle, audio_seconds: float) -> None:
        self._inner = inner
        self._handle = handle
        self._audio_seconds = audio_seconds
        self.charged = 0

    def verify_media_marker(self):
        return self._inner.verify_media_marker()

    def embed_text(self, *, contact_id: str, text: str):
        self._handle.record_usage(calls=1, audio_seconds=fid.TEXT_CONTACT_AUDIO_SECONDS)
        self.charged += 1
        return self._inner.embed_text(contact_id=contact_id, text=text)

    def embed_audio(self, *, contact_id: str, audio_bytes: bytes):
        self._handle.record_usage(calls=1, audio_seconds=self._audio_seconds)
        self.charged += 1
        return self._inner.embed_audio(contact_id=contact_id, audio_bytes=audio_bytes)


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
    F.assert_split_identity_hash(manifest.split_identity_hash)
    return adapter, list(samples), list(labels), manifest


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
        tmp.write_text(json.dumps(self.document, indent=2, sort_keys=True, default=str), encoding="utf-8", newline="\n")
        os.replace(tmp, self.path)

    def put(self, key: str, value: object) -> None:
        self.document[key] = value
        self.save()


def resolve_run_dir(root: Path, attempt_id: str) -> Path:
    return Path(root) / "runs" / fid.run_id() / attempt_id


def _refuse_stray_feat_cache_env() -> None:
    if os.environ.get("SAEA_FEAT_CACHE_DIR"):
        raise RuntimeError(
            "SAEA_FEAT_CACHE_DIR is set in this environment. P-EMB-4R serves TWO different audio "
            "encoders plus the frozen core and pins one feature-cache directory PER MODEL "
            "(docs/featcache-directories.md); a process-wide override could silently repoint a "
            "session at another encoder's cache. Refusing (fail-closed)."
        )


def load_context(args):
    """Everything every stage needs: lock, root, values, config/protocol hash,
    plan, run dir, attempt handle."""

    _refuse_stray_feat_cache_env()
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    F.assert_binding_config_sha256(lock)

    attempt_id = args.attempt_id
    run_dir = resolve_run_dir(root, attempt_id)
    state = FlightState(run_dir / "flight-state.json")

    sha_by_relpath = state.document.get("model_file_sha256") or {}
    declared_dims = state.document.get("declared_embedding_length_by_model") or {}
    values = fid.build_values(REPO, lock, sha_by_relpath, declared_dims)
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
    F.assert_within_registered_ceilings(
        calls=plan.planned_model_calls,
        audio_seconds=plan.planned_speech_audio_seconds,
        gpu_hours=plan.planned_gpu_hours,
    )
    pinned = state.document.get("config_hash")
    if pinned is not None and pinned != cfg_hash:
        raise RuntimeError(
            f"config hash drifted since preflight: state pins {pinned}, recomposed {cfg_hash}; "
            "refusing (fail-closed)"
        )
    store = AttemptStore(attempts_root=root / "attempts")
    return lock, root, values, cfg_hash, plan, run_dir, state, store


def _gpu_add(state: FlightState, *, wall: float = 0.0, load: float = 0.0, contact: float = 0.0) -> dict[str, float]:
    """The P-CORR-F section-8 three-measure GPU accounting, accumulated across
    stages. ``wall`` is server-alive/in-process wall (recorded, NEVER gates);
    ``load`` is model load/spawn occupancy; ``contact`` is the summed per-call
    MEASURED latency. ``gpu_active = load + contact``; ``measured_equivalent =
    contact``. Both gating bases exclude every idle gap by construction."""

    acc = dict(state.document.get("gpu_accounting_seconds") or {"wall": 0.0, "load": 0.0, "contact": 0.0})
    acc["wall"] = float(acc.get("wall", 0.0)) + float(wall)
    acc["load"] = float(acc.get("load", 0.0)) + float(load)
    acc["contact"] = float(acc.get("contact", 0.0)) + float(contact)
    state.put("gpu_accounting_seconds", acc)
    return acc


def _gpu_accounting(state: FlightState) -> F.GpuHoursAccounting:
    acc = dict(state.document.get("gpu_accounting_seconds") or {"wall": 0.0, "load": 0.0, "contact": 0.0})
    return F.GpuHoursAccounting(
        wall_hours=float(acc.get("wall", 0.0)) / 3600.0,
        gpu_active_hours=(float(acc.get("load", 0.0)) + float(acc.get("contact", 0.0))) / 3600.0,
        measured_equivalent_hours=float(acc.get("contact", 0.0)) / 3600.0,
    )


# ---------------------------------------------------------------------------
# Stage: preflight (ZERO contacts).
# ---------------------------------------------------------------------------


def stage_preflight(args) -> int:
    _refuse_stray_feat_cache_env()
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    attempt_id = args.attempt_id
    run_dir = resolve_run_dir(root, attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    state = FlightState(run_dir / "flight-state.json")
    log(f"P-EMB-4R preflight -- exposure row {fid.run_id()}, attempt {attempt_id} -> {run_dir}")

    # -- legality guards, re-run explicitly ---------------------------------
    F.assert_never_accesses_frozen_60_gold()
    F.assert_never_calls_ontology_miner()
    log("guards: frozen-60-gold AST guard PASS; ontology-miner ban PASS")

    # -- binding-config hash stability --------------------------------------
    F.assert_binding_config_sha256(lock)
    digest_a = F.binding_config_sha256(lock)
    digest_b = F.binding_config_sha256(lock)
    if digest_a != digest_b:
        raise RuntimeError("binding config sha256 is not stable across two computations")
    log(f"binding config sha256 verified + stable across recomputation: {digest_a}")
    state.put("binding_config_sha256", digest_a)

    # -- bank: DOUBLE DERIVATION, bit-identity vs the pinned sha256 ----------
    from speech_aware_evidence_acquisition.rails.probes.pfew_flight import load_train_demo_pool
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters
    from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import canonical_scenario_labels

    rosters = load_pslu_rosters(REPO / fid.ROSTER_TABLE_RELPATH)
    canonical_labels = canonical_scenario_labels(rosters)
    pool = load_train_demo_pool(lock, root)
    bank_a = F.build_bank_table(pool, canonical_labels)
    bank_b = F.build_bank_table(pool, canonical_labels)
    F.validate_bank_table(bank_a)
    F.validate_bank_table(bank_b)
    sha_a = F.bank_manifest_sha256(bank_a)
    sha_b = F.bank_manifest_sha256(bank_b)
    if sha_a != sha_b:
        raise RuntimeError(f"bank double derivation is NOT bit-identical: {sha_a} != {sha_b}")
    F.assert_bank_manifest_sha256(bank_a)
    bank_path = F.write_bank_manifest(root, bank_a)
    log(
        f"bank: {len(bank_a.entries)} rows, seed {bank_a.seed}, {bank_a.per_scenario_n}/scenario; "
        f"double derivation BIT-IDENTICAL sha256={sha_a} (matches the pinned pin); manifest -> {bank_path}"
    )
    state.put(
        "bank",
        {
            "manifest_path": str(bank_path),
            "sha256": sha_a,
            "double_derivation_bit_identical": True,
            "rows": len(bank_a.entries),
            "seed": bank_a.seed,
            "per_scenario_n": bank_a.per_scenario_n,
            "min_train_candidates_per_label": min(len(pool.get(label, ())) for label in canonical_labels),
        },
    )

    # -- every embedder byte this flight will actually serve -----------------
    relpaths = list(fid.all_hashed_relpaths())
    measured: dict[str, dict[str, object]] = {}
    sha_by_relpath: dict[str, str] = {}
    for relpath in relpaths:
        path = root / relpath
        if not path.is_file():
            raise RuntimeError(f"pinned embedder file missing: {path}")
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
        log(f"file {relpath}: {size} bytes sha256={digest} ({elapsed:.1f}s, {measured[relpath]['read_MB_per_s']} MB/s)")
    state.put("model_file_sha256", sha_by_relpath)
    state.put("model_file_measurements", measured)

    # -- LCO-7B's own declared embedding length (OFFLINE, model-free) --------
    declared: dict[str, int] = {}
    for model in ("lco3", "lco7", "qw"):
        primary = root / fid.gguf_relpaths(model)[0]
        declared[model] = fid.gguf_declared_embedding_length(primary)
        log(f"gguf declared embedding_length[{model}] = {declared[model]} (header read, no server)")
    from speech_aware_evidence_acquisition.rails.local_encoder_client import GLAP_EMBEDDING_DIM

    declared["glap"] = int(GLAP_EMBEDDING_DIM)
    for model, known in F.KNOWN_MODEL_DIM.items():
        if declared.get(model) != int(known):
            raise RuntimeError(
                f"model {model!r}: the machinery pins dim {known} but the GGUF/module declares "
                f"{declared.get(model)}; refusing (fail-closed)"
            )
    if "lco7" in F.KNOWN_MODEL_DIM:
        raise RuntimeError("lco7 must NOT be statically pinned in KNOWN_MODEL_DIM -- its dim is gate-measured")
    state.put("declared_embedding_length_by_model", declared)

    # -- cross-check against the umbrella lock wherever it carries a hash ----
    lock_crosscheck: dict[str, object] = {}
    for model in F.MODELS:
        lock_key = F.MODEL_LOCK_KEY[model]
        binding = F.resolve_model_binding(lock, lock_key)
        file_hashes = {entry["filename"]: entry["sha256"] for entry in binding["file_hashes"] if entry.get("filename")}
        verdicts = []
        for relpath, digest in sha_by_relpath.items():
            filename = Path(relpath).name
            if filename in file_hashes:
                agree = file_hashes[filename] == digest
                verdicts.append(
                    {"filename": filename, "lock_sha256": file_hashes[filename], "measured": digest, "agree": agree}
                )
                if not agree:
                    raise RuntimeError(
                        f"{lock_key}: umbrella lock pins {filename} at {file_hashes[filename]} but the "
                        f"real bytes hash to {digest}; refusing (fail-closed)"
                    )
        lock_crosscheck[lock_key] = {
            "model": model,
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
            f"lock binding {lock_key}: lifecycle={binding['lifecycle']!r} per-file-sha256="
            + ("yes" if file_hashes else "NO (LOCAL_CANDIDATE -- this flight self-pins)")
            + (f" -> {len(verdicts)} file(s) cross-checked AGREE" if verdicts else "")
        )
    state.put("umbrella_lock_crosscheck", lock_crosscheck)

    # -- the full config/plan, with the measured hashes bound in ------------
    values = fid.build_values(REPO, lock, sha_by_relpath, declared)
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
    F.assert_within_registered_ceilings(
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

    # -- machinery's own registered plan constructor, cross-checked ---------
    machinery_plan = F.build_execution_plan(lock=lock, attempt_id=attempt_id)
    if machinery_plan.protocol_hash != F.BINDING_CONFIG_SHA256:
        raise RuntimeError("machinery build_execution_plan protocol_hash != pinned binding config sha256")
    if machinery_plan.split_identity_hash != plan.split_identity_hash:
        raise RuntimeError("machinery plan split identity disagrees with the launcher plan")
    log(
        "machinery build_execution_plan cross-check PASS "
        f"(profile={machinery_plan.execution_profile!r}, protocol_hash={machinery_plan.protocol_hash})"
    )
    state.put("machinery_execution_plan", asdict(machinery_plan))

    # -- registered ceilings: three independent sources must agree ----------
    ledger_text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    ledger_row = [line for line in ledger_text.splitlines() if f"| {fid.run_id()} |" in line]
    if len(ledger_row) != 1:
        raise RuntimeError(f"expected exactly one exposure-ledger row for {fid.run_id()}, found {len(ledger_row)}")
    cells = [cell.strip() for cell in ledger_row[0].strip().strip("|").split("|")]
    ledger_ceilings = {"model_calls": int(cells[9]), "speech_audio_seconds": int(cells[10]), "gpu_hours": float(cells[11])}
    machinery_ceilings = {
        "model_calls": F.CEILING_CALLS,
        "speech_audio_seconds": F.CEILING_AUDIO_SECONDS,
        "gpu_hours": F.CEILING_GPU_HOURS,
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

    # -- the tool-contact gate checks (the P-EMB-3M scope) ------------------
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path(args.runtime_root),
        runtime_receipt_relpath=fid.RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=str(values["model_lock_key"]),
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
        "The SEVEN embedding arms are TOOL contacts: FrozenCoreGate._validate_runtime (q4km GGUF "
        "attestation) is deliberately NOT run for them -- the frozen core is not loaded by any of "
        "them. Every embedder byte actually served is fully SHA-256'd in preflight instead, and the "
        "llama.cpp binary is re-hashed fail-closed by core.session.start_session at every spawn. "
        "C-DECODE IS a frozen-core contact and runs the FULL assert_model_touch_allowed, including "
        "the q4km GGUF attestation, BEFORE it spawns anything (the P-CORR-F section-8 forward rule).",
    )

    # -- gate (d): structural encode-only machine check ---------------------
    report = F.run_encode_only_preflight_gate()
    log(f"GATE (d) ENCODE-ONLY: PASS over {list(report.checked_modules)}")
    if "speech_aware_evidence_acquisition.rails.probes.pemb4r_flight" not in report.checked_modules:
        raise RuntimeError("encode-only check does not cover rails.probes.pemb4r_flight")
    state.put("gate_d_encode_only", {"status": "PASS", "checked_modules": list(report.checked_modules)})

    # -- inputs + gate (e): cascade/T0 source check -------------------------
    _adapter, samples, labels, manifest = load_inputs(lock, root)
    if len(samples) != F.QUERY_N or len(labels) != F.BANK_N_SCENARIOS:
        raise RuntimeError(f"inputs: {len(samples)} samples / {len(labels)} labels, expected {F.QUERY_N}/{F.BANK_N_SCENARIOS}")
    one_pass_audio = sum(float(sample.audio_seconds) for sample in samples)
    log(
        f"inputs: {len(samples)} audio samples, {len(labels)} canonical labels; one metered audio "
        f"pass = {one_pass_audio:.3f}s (3 audio arms -> {3*one_pass_audio:.3f}s vs plan "
        f"{plan.planned_speech_audio_seconds}s / ceiling {F.CEILING_AUDIO_SECONDS}s)"
    )
    if 3 * one_pass_audio > plan.planned_speech_audio_seconds:
        raise RuntimeError("three audio passes would exceed the plan's metered-audio ceiling")
    expected_ids = frozenset(sample.sample_id for sample in samples)
    cascade = F.run_pemb4r_cascade_source_check(data_root=root, ledger_text=ledger_text, expected_sample_ids=expected_ids)
    log(
        f"GATE (e) CASCADE/T0 SOURCE: {cascade.status} -- {len(cascade.transcripts)}/{F.QUERY_N} T0 "
        f"transcripts, registry sha256 {cascade.registry_sha256}, supplement_required={cascade.supplement_required}"
    )
    from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import CASCADE_SOURCE_STATUS_COMPLETE

    if cascade.status != CASCADE_SOURCE_STATUS_COMPLETE:
        raise RuntimeError(
            f"cascade source check reports {cascade.status}, not COMPLETE. P-EMB-4R has no registered "
            "T0 supplement; refusing (fail-closed)."
        )
    state.put(
        "gate_e_cascade_source",
        {
            "status": cascade.status,
            "registry_path": str(cascade.registry_path),
            "registry_sha256": cascade.registry_sha256,
            "transcript_count": len(cascade.transcripts),
            "supplement_required": cascade.supplement_required,
        },
    )
    state.put("one_pass_metered_audio_seconds", round(one_pass_audio, 6))
    state.put("sample_ids", sorted(expected_ids))
    state.put("canonical_labels", list(labels))

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
# Server-session helper.
# ---------------------------------------------------------------------------


def spawn_embedder_session(
    *, args, root: Path, run_dir: Path, server_key: str, gguf_relpaths_, sha_by_relpath, server_args, server_env, port: int
):
    committed_runtime = load_runtime_receipt(REPO / "docs" / fid.RUNTIME_RECEIPT_RELPATH)
    receipt_doc = fid.embedder_runtime_receipt(
        committed_runtime, gguf_relpaths_=gguf_relpaths_, sha256_by_relpath=sha_by_relpath
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


def _append_session(state: FlightState, record: dict) -> None:
    sessions = list(state.document.get("sessions", []))
    sessions.append(record)
    state.put("sessions", sessions)


def _props_subset(props: Mapping[str, object]) -> dict[str, object]:
    keys = ("media_marker", "pooling_type", "n_ctx", "n_batch", "n_ubatch", "model_path", "build_info")
    return {k: props[k] for k in sorted(props) if k in keys}


def _record_sweep(state: FlightState, key: str, payload: dict) -> None:
    sweeps = dict(state.document.get("sweeps", {}))
    sweeps[key] = payload
    state.put("sweeps", sweeps)


def _run_bank_and_queries(
    *,
    model: str,
    client,
    proxy_factory,
    state: FlightState,
    root: Path,
    bank,
    samples,
    transcripts,
    supports_prefix: bool,
    supports_marker: bool,
    server_key: str,
) -> tuple[int, float]:
    """Bank once per model, then that model's own arms. Returns
    ``(contacts_flown, contact_latency_seconds)``. Bank-level and arm-level
    idempotence come from the machinery's own ``run_pemb4r_bank_sweep`` /
    ``run_pemb4r_query_sweep`` completeness checks."""

    flown = 0
    latency = 0.0
    audio_seconds_by_contact = {s.sample_id: float(s.audio_seconds) for s in samples}
    sample_ids = sorted(s.sample_id for s in samples)

    # ---- bank (shared by every arm of this model) -------------------------
    if F.is_bank_vectors_complete(root, model):
        log(f"[bank:{model}] CARRIED: bank vectors already complete on the data root -- zero contacts")
    else:
        proxy = proxy_factory(f"bank:{model}", F.BANK_TOTAL_N, audio_seconds_by_contact)
        log(f"BANK START {model}: {F.BANK_TOTAL_N} TEXT contacts (bank row texts only; labels never embedded)")
        started = time.time()
        if supports_marker:
            runner = lambda: F.run_server_bank_embedding(client=proxy, bank=bank)  # noqa: E731
        else:
            runner = lambda: F.run_local_bank_embedding(client=proxy, bank=bank)  # noqa: E731
        F.run_pemb4r_bank_sweep(root=root, bank=bank, model_runners={model: runner})
        wall = time.time() - started
        flown += proxy.flown
        latency += proxy.latency_total
        log(f"BANK DONE {model}: {wall:.1f}s, flown={proxy.flown} replayed={proxy.replayed}")
        _record_sweep(
            state,
            f"bank:{model}",
            {
                "model": model,
                "server_key": server_key,
                "contacts_flown": proxy.flown,
                "contacts_replayed": proxy.replayed,
                "contact_failures": list(proxy.failures),
                "latency_seconds": round(proxy.latency_total, 3),
                "wall_seconds": round(wall, 2),
                "flown_by_kind": dict(proxy.flown_by_kind),
            },
        )

    # ---- this model's own arms -------------------------------------------
    for arm_id in F.ARM_IDS_BY_MODEL[model]:
        arm = F.ARMS_BY_ID[arm_id]
        if F.is_query_vectors_complete(root, arm_id):
            log(f"[{arm_id}] CARRIED: query vectors already complete on the data root -- zero contacts")
            continue
        proxy = proxy_factory(arm_id, F.QUERY_N, audio_seconds_by_contact)
        log(f"ARM START {arm_id}: {F.QUERY_N} {arm.query_kind.upper()} query contacts")
        started = time.time()
        if arm.query_kind == "audio":
            if supports_marker:
                runner = lambda: F.run_server_audio_query(client=proxy, samples=samples, data_root=root)  # noqa: E731
            else:
                runner = lambda: F.run_local_audio_query(client=proxy, samples=samples, data_root=root)  # noqa: E731
        else:
            if supports_marker:
                runner = lambda: F.run_server_text_query(  # noqa: E731
                    client=proxy, transcript_registry=transcripts, sample_ids=sample_ids
                )
            else:
                runner = lambda: F.run_local_text_query(  # noqa: E731
                    client=proxy, transcript_registry=transcripts, sample_ids=sample_ids
                )
        F.run_pemb4r_query_sweep(root=root, arm_runners={arm_id: runner})
        wall = time.time() - started
        flown += proxy.flown
        latency += proxy.latency_total
        log(f"ARM DONE {arm_id}: {wall:.1f}s, flown={proxy.flown} replayed={proxy.replayed}")
        _record_sweep(
            state,
            arm_id,
            {
                "arm_id": arm_id,
                "model": model,
                "query_kind": arm.query_kind,
                "server_key": server_key,
                "contacts_flown": proxy.flown,
                "contacts_replayed": proxy.replayed,
                "contact_failures": list(proxy.failures),
                "latency_seconds": round(proxy.latency_total, 3),
                "mean_latency_seconds": round(proxy.latency_total / max(proxy.flown, 1), 4),
                "wall_seconds": round(wall, 2),
                "flown_by_kind": dict(proxy.flown_by_kind),
            },
        )
    return flown, latency


def _cascade(root: Path, sample_ids: Sequence[str]):
    ledger_text = (REPO / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import CASCADE_SOURCE_STATUS_COMPLETE

    cascade = F.run_pemb4r_cascade_source_check(
        data_root=root, ledger_text=ledger_text, expected_sample_ids=frozenset(sample_ids)
    )
    if cascade.status != CASCADE_SOURCE_STATUS_COMPLETE:
        raise RuntimeError(f"cascade source re-check reports {cascade.status}; refusing")
    return cascade


# ---------------------------------------------------------------------------
# LCO stages (gate (c) POOLING-DIFFER + determinism + bank + arms).
# ---------------------------------------------------------------------------


def _rebuild_bank(lock, root):
    from speech_aware_evidence_acquisition.rails.probes.pfew_flight import load_train_demo_pool
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters
    from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import canonical_scenario_labels

    rosters = load_pslu_rosters(REPO / fid.ROSTER_TABLE_RELPATH)
    labels = canonical_scenario_labels(rosters)
    pool = load_train_demo_pool(lock, root)
    bank = F.build_bank_table(pool, labels)
    F.validate_bank_table(bank)
    F.assert_bank_manifest_sha256(bank)
    return bank


def _lco_stage(args, model: str) -> int:
    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    sha_by_relpath = state.document["model_file_sha256"]
    declared = state.document["declared_embedding_length_by_model"]
    gate_wav = Path(state.document["gate_wav_path"]).read_bytes()
    expected_marker = resolve_expected_media_marker()
    port = fid.SERVER_PORT_BY_MODEL[model]
    timeout_seconds = float(values["timeout_seconds"])
    server_env = {
        "LLAMA_MTMD_FEAT_CACHE_DIR": fid.FEAT_CACHE_BY_MODEL[model],
        "LLAMA_MEDIA_MARKER": expected_marker,
    }

    arms = F.ARM_IDS_BY_MODEL[model]
    dropped = dict(state.document.get("dropped_arms", {}))
    if all(arm_id in dropped for arm_id in arms):
        log(f"[{model}] every arm already DROPPED ({sorted(arms)}) -- nothing to do")
        return 0
    all_complete = F.is_bank_vectors_complete(root, model) and all(F.is_query_vectors_complete(root, a) for a in arms)
    gate_key = f"gate_c_pooling_differ_{model}"
    if all_complete and gate_key in state.document:
        log(f"[{model}] CARRIED: bank + both arms complete and gate (c) already recorded -- zero contacts")
        return 0

    # Inputs BEFORE any spawn: load_inputs re-hashes every SLURP devel media
    # file (model-free, but minutes of cold 9p I/O), and doing it inside a
    # resident session would charge all of that CPU-bound time to GPU
    # accounting (the P-CORR-F section-8 forward rule).
    inputs_started = time.time()
    _adapter, samples, _labels, _manifest = load_inputs(lock, root)
    bank = _rebuild_bank(lock, root)
    cascade = _cascade(root, [s.sample_id for s in samples])
    log(f"inputs + bank ready in {time.time()-inputs_started:.1f}s (BEFORE any spawn -- not charged to GPU time)")

    expected_dim = int(declared[model])
    log(f"[{model}] EmbeddingClient expected_dim = {expected_dim} (GGUF-declared, gate-confirmed live)")

    # ---- session A: --pooling last -- gate (a) for lco7, gate (c) half, ----
    # ---- determinism pair, bank, both arms --------------------------------
    session, spawn_seconds, started = spawn_embedder_session(
        args=args, root=root, run_dir=run_dir, server_key=f"{model}-last",
        gguf_relpaths_=fid.gguf_relpaths(model), sha_by_relpath=sha_by_relpath,
        server_args=fid.lco_session_args("last"), server_env=server_env, port=port,
    )
    session_contacts = 0
    contact_latency = 0.0
    dropped_here = False
    try:
        client = EmbeddingClient(
            base_url=f"http://{args.host}:{port}",
            expected_media_marker=expected_marker,
            timeout_seconds=timeout_seconds,
            expected_dim=expected_dim,
        )
        gate_client = ChargingGateClient(client, handle=handle, audio_seconds=float(fid.GATE_WAV_SECONDS))

        # ---- gate (a): LCO-7B server sanity (lco7 only) -------------------
        if model == "lco7" and "gate_a_lco7_sanity" not in state.document:
            t0 = time.time()
            sanity = F.run_lco7_server_sanity_gate(client=gate_client)
            contact_latency += time.time() - t0
            session_contacts += gate_client.charged
            log(f"GATE (a) LCO-7B SERVER SANITY: {sanity.status} -- {sanity.detail}")
            state.put(
                "gate_a_lco7_sanity",
                {
                    "status": sanity.status,
                    "detail": sanity.detail,
                    "measured_dim": sanity.measured_dim,
                    "declared_dim": expected_dim,
                    "declared_matches_measured": sanity.measured_dim == expected_dim,
                    "contacts": gate_client.charged,
                },
            )
            if sanity.status != F.STATUS_OK:
                for arm_id in arms:
                    dropped[arm_id] = f"{F.STATUS_DROPPED_LCO7}: {sanity.detail}"
                state.put("dropped_arms", dropped)
                dropped_here = True
                log(
                    f"GATE (a) FAILED -> {F.STATUS_DROPPED_LCO7} for {sorted(arms)}; disclosed and "
                    "NON-BLOCKING to every other arm"
                )
                return 0

        props = client.verify_media_marker()
        log(f"/props verified for {model}-last: media_marker={props.get('media_marker')!r} pooling_type={props.get('pooling_type')!r}")
        state.put(f"props_{model}_last", _props_subset(props))

        # ---- gate (c) first half + repeat-call determinism ----------------
        if gate_key not in state.document:
            t0 = time.time()
            last_vector = gate_client.embed_audio(contact_id="pooling-differ-gate", audio_bytes=gate_wav)
            repeat_vector = gate_client.embed_audio(contact_id=f"{model}-jitter-b", audio_bytes=gate_wav)
            contact_latency += time.time() - t0
            session_contacts += 2
            a_sha = _vector_sha256(last_vector.values)
            b_sha = _vector_sha256(repeat_vector.values)
            log(f"[{model}] repeat-call determinism sample: dims={last_vector.dims} byte_identical={a_sha == b_sha}")
            (run_dir / f"{model}-jitter-vectors.json").write_text(
                json.dumps({"a": list(last_vector.values), "b": list(repeat_vector.values)}),
                encoding="utf-8",
                newline="\n",
            )
            (run_dir / f"gate-c-{model}-last-vector.json").write_text(
                json.dumps(list(last_vector.values)), encoding="utf-8", newline="\n"
            )
            state.put(
                f"repeat_call_determinism_{model}",
                {
                    "server_session": f"{model}-last",
                    "kind": "audio",
                    "dims": last_vector.dims,
                    "vector_a_sha256": a_sha,
                    "vector_b_sha256": b_sha,
                    "byte_identical": a_sha == b_sha,
                    "contacts": 1,
                    "note": (
                        "vector_a is the pooling-differ gate contact itself, reused as the first half "
                        "of the pair; only one additional contact was spent. Both vectors are persisted "
                        "on the data root so analysis.pemb4r_read can derive the measured repeat-delta "
                        "the registration's own argmax-stability statement needs; this flight records "
                        "sha256 equality only and evaluates no tolerance."
                    ),
                },
            )

        # ---- bank + arms --------------------------------------------------
        def proxy_factory(sweep_id: str, total: int, audio_map):
            vector_log = run_dir / f"vectors-{sweep_id.replace(':', '-')}.jsonl"
            cached = load_cached(vector_log)
            if cached:
                log(f"[{sweep_id}] resume: {len(cached)} cached vectors will be replayed without a tool contact")
            return BudgetedCachingProxy(
                client, sweep_id=sweep_id, store=store, handle=handle, plan=plan,
                vector_log=vector_log, cached=cached, audio_seconds_by_contact=audio_map, total_contacts=total,
            )

        flown, latency = _run_bank_and_queries(
            model=model, client=client, proxy_factory=proxy_factory, state=state, root=root, bank=bank,
            samples=samples, transcripts=cascade.transcripts, supports_prefix=True, supports_marker=True,
            server_key=f"{model}-last",
        )
        session_contacts += flown
        contact_latency += latency
    finally:
        resident = time.time() - started
        teardown = teardown_session(session.pid, args.host, port)
        _append_session(
            state,
            session_record(
                session, server_key=f"{model}-last", spawn_seconds=spawn_seconds, resident_seconds=resident,
                teardown=teardown, extra={"pooling_mode": "last", "contacts": session_contacts},
            ),
        )
        acc = _gpu_add(state, wall=resident, load=spawn_seconds, contact=contact_latency)
        log(
            f"session {model}-last torn down after {resident:.1f}s resident; cumulative GPU-active "
            f"{(acc['load']+acc['contact'])/3600:.4f} h (wall {acc['wall']/3600:.4f} h, never gates)"
        )
    if dropped_here:
        return 0

    # ---- session B: --pooling mean -- ONE gate contact, then byte-compare --
    if gate_key not in state.document:
        session, spawn_seconds, started = spawn_embedder_session(
            args=args, root=root, run_dir=run_dir, server_key=f"{model}-mean",
            gguf_relpaths_=fid.gguf_relpaths(model), sha_by_relpath=sha_by_relpath,
            server_args=fid.lco_session_args("mean"), server_env=server_env, port=port,
        )
        contact_latency = 0.0
        try:
            mean_client = EmbeddingClient(
                base_url=f"http://{args.host}:{port}",
                expected_media_marker=expected_marker,
                timeout_seconds=timeout_seconds,
                expected_dim=expected_dim,
            )
            props = mean_client.verify_media_marker()
            log(f"/props verified for {model}-mean: pooling_type={props.get('pooling_type')!r}")
            state.put(f"props_{model}_mean", _props_subset(props))
            gate_client = ChargingGateClient(mean_client, handle=handle, audio_seconds=float(fid.GATE_WAV_SECONDS))
            t0 = time.time()
            mean_vector = gate_client.embed_audio(contact_id="pooling-differ-gate", audio_bytes=gate_wav)
            contact_latency += time.time() - t0
            (run_dir / f"gate-c-{model}-mean-vector.json").write_text(
                json.dumps(list(mean_vector.values)), encoding="utf-8", newline="\n"
            )
            last_values = json.loads((run_dir / f"gate-c-{model}-last-vector.json").read_text(encoding="utf-8"))
            if mean_vector.dims != len(last_values):
                raise RuntimeError(
                    f"gate (c) {model}: mean-pooled dim {mean_vector.dims} != last-pooled dim {len(last_values)}"
                )
            pooling_override_present = list(mean_vector.values) == list(last_values)
            log(
                f"GATE (c) POOLING-DIFFER [{model}]: "
                + (
                    "BYTE-IDENTICAL -> POOLING-OVERRIDE-PRESENT (this model's own arm verdicts stay stack-scoped)"
                    if pooling_override_present
                    else "vectors DIFFER -> gate passes clean (model-level verdicts stay in scope)"
                )
            )
            scope = F.pooling_override_scope_for_model(model, pooling_override_present)
            state.put(
                gate_key,
                {
                    "model": model,
                    "pooling_override_present": pooling_override_present,
                    "dims": mean_vector.dims,
                    "last_vector_sha256": _vector_sha256(last_values),
                    "mean_vector_sha256": _vector_sha256(mean_vector.values),
                    "boots": 2,
                    "contacts": 2,
                    "gate_clip": "synthetic 2s 440Hz sine, non-corpus",
                    "scope": scope,
                    "sequential_boot_deviation": (
                        "run_pooling_differ_gate takes two LIVE clients at once (two resident sessions "
                        "over the same weights); for LCO-7B that is ~2x12.6 GB against 23.1 GB free VRAM "
                        "on this host. The archived P-EMB-3M precedent is carried instead: boot last, "
                        "embed, tear down, boot mean, embed the SAME clip, tear down, byte-compare the "
                        "persisted vectors. Identical computation, no concurrent VRAM."
                    ),
                },
            )
        finally:
            resident = time.time() - started
            teardown = teardown_session(session.pid, args.host, port)
            _append_session(
                state,
                session_record(
                    session, server_key=f"{model}-mean", spawn_seconds=spawn_seconds, resident_seconds=resident,
                    teardown=teardown, extra={"pooling_mode": "mean", "contacts": 1},
                ),
            )
            acc = _gpu_add(state, wall=resident, load=spawn_seconds, contact=contact_latency)
            log(f"session {model}-mean torn down after {resident:.1f}s resident; cumulative GPU-active {(acc['load']+acc['contact'])/3600:.4f} h")

    calls, audio = handle.actual_totals()
    log(f"durable spend after stage {model}: calls={calls}, audio_seconds={audio:.3f}")
    return 0


def stage_lco3(args) -> int:
    return _lco_stage(args, "lco3")


def stage_lco7(args) -> int:
    return _lco_stage(args, "lco7")


# ---------------------------------------------------------------------------
# Stage: qw (text-only server; determinism pair + bank + T-QW).
# ---------------------------------------------------------------------------


def stage_qw(args) -> int:
    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    sha_by_relpath = state.document["model_file_sha256"]
    model = "qw"
    port = fid.QW_PORT
    arms = F.ARM_IDS_BY_MODEL[model]
    if F.is_bank_vectors_complete(root, model) and all(F.is_query_vectors_complete(root, a) for a in arms):
        if "repeat_call_determinism_qw" in state.document:
            log("[qw] CARRIED: bank + arms complete and determinism pair recorded -- zero contacts")
            return 0

    inputs_started = time.time()
    _adapter, samples, _labels, _manifest = load_inputs(lock, root)
    bank = _rebuild_bank(lock, root)
    cascade = _cascade(root, [s.sample_id for s in samples])
    log(f"inputs + bank ready in {time.time()-inputs_started:.1f}s (BEFORE any spawn)")

    session, spawn_seconds, started = spawn_embedder_session(
        args=args, root=root, run_dir=run_dir, server_key="qw",
        gguf_relpaths_=fid.gguf_relpaths(model), sha_by_relpath=sha_by_relpath,
        server_args=fid.QW_SERVER_ARGS, server_env={}, port=port,
    )
    session_contacts = 0
    contact_latency = 0.0
    try:
        # A text-only embedding server has no mmproj and no media-marker
        # concept: rails.embedding_client's own EXTENSION seam for exactly this
        # caller (require_marker_verification=False, expected_dim=1024).
        client = EmbeddingClient(
            base_url=f"http://{args.host}:{port}",
            timeout_seconds=float(values["timeout_seconds"]),
            expected_dim=F.QWEN3_EMB_EMBEDDING_DIM,
            require_marker_verification=False,
        )
        client.verify_media_marker()
        import urllib.request

        with urllib.request.urlopen(f"http://{args.host}:{port}/props", timeout=30) as response:
            props = json.loads(response.read().decode("utf-8"))
        log(f"/props for qw (text-only, no media marker to verify): pooling_type={props.get('pooling_type')!r}")
        state.put("props_qw", _props_subset(props))

        if "repeat_call_determinism_qw" not in state.document:
            gate_client = ChargingGateClient(client, handle=handle, audio_seconds=float(fid.GATE_WAV_SECONDS))
            t0 = time.time()
            jitter_a = gate_client.embed_text(contact_id="qw-jitter-a", text="repeat call determinism sample")
            jitter_b = gate_client.embed_text(contact_id="qw-jitter-b", text="repeat call determinism sample")
            contact_latency += time.time() - t0
            session_contacts += gate_client.charged
            a_sha = _vector_sha256(jitter_a.values)
            b_sha = _vector_sha256(jitter_b.values)
            log(f"[qw] repeat-call determinism sample: dims={jitter_a.dims} byte_identical={a_sha == b_sha}")
            (run_dir / "qw-jitter-vectors.json").write_text(
                json.dumps({"a": list(jitter_a.values), "b": list(jitter_b.values)}), encoding="utf-8", newline="\n"
            )
            state.put(
                "repeat_call_determinism_qw",
                {
                    "server_session": "qw",
                    "kind": "text",
                    "dims": jitter_a.dims,
                    "vector_a_sha256": a_sha,
                    "vector_b_sha256": b_sha,
                    "byte_identical": a_sha == b_sha,
                    "contacts": 2,
                    "note": (
                        "E-1 Mission C established that qwen3-emb is NOT bit-exact across identical GPU "
                        "calls; both vectors are persisted on the data root so the read can derive the "
                        "measured repeat-delta. This flight records sha256 equality only."
                    ),
                },
            )

        def proxy_factory(sweep_id: str, total: int, audio_map):
            vector_log = run_dir / f"vectors-{sweep_id.replace(':', '-')}.jsonl"
            cached = load_cached(vector_log)
            if cached:
                log(f"[{sweep_id}] resume: {len(cached)} cached vectors will be replayed without a tool contact")
            return BudgetedCachingProxy(
                client, sweep_id=sweep_id, store=store, handle=handle, plan=plan,
                vector_log=vector_log, cached=cached, audio_seconds_by_contact=audio_map, total_contacts=total,
                supports_marker=False,
            )

        flown, latency = _run_bank_and_queries(
            model=model, client=client, proxy_factory=proxy_factory, state=state, root=root, bank=bank,
            samples=samples, transcripts=cascade.transcripts, supports_prefix=True, supports_marker=True,
            server_key="qw",
        )
        session_contacts += flown
        contact_latency += latency
    finally:
        resident = time.time() - started
        teardown = teardown_session(session.pid, args.host, port)
        _append_session(
            state,
            session_record(
                session, server_key="qw", spawn_seconds=spawn_seconds, resident_seconds=resident,
                teardown=teardown, extra={"pooling_mode": "last", "contacts": session_contacts},
            ),
        )
        acc = _gpu_add(state, wall=resident, load=spawn_seconds, contact=contact_latency)
        log(f"session qw torn down after {resident:.1f}s resident; cumulative GPU-active {(acc['load']+acc['contact'])/3600:.4f} h")
    calls, audio = handle.actual_totals()
    log(f"durable spend after stage qw: calls={calls}, audio_seconds={audio:.3f}")
    return 0


# ---------------------------------------------------------------------------
# Stage: glap (gate (b) import + audio-path sanity, then bank + both arms).
# ---------------------------------------------------------------------------


def stage_glap(args) -> int:
    import glap_loader

    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    gate_wav = Path(state.document["gate_wav_path"]).read_bytes()
    model = "glap"
    arms = F.ARM_IDS_BY_MODEL[model]
    dropped = dict(state.document.get("dropped_arms", {}))
    if all(arm_id in dropped for arm_id in arms):
        log(f"[glap] every arm already DROPPED -- nothing to do")
        return 0
    if F.is_bank_vectors_complete(root, model) and all(F.is_query_vectors_complete(root, a) for a in arms) and "gate_b_glap" in state.document:
        log("[glap] CARRIED: bank + both arms complete and gate (b) recorded -- zero contacts")
        return 0

    inputs_started = time.time()
    _adapter, samples, _labels, _manifest = load_inputs(lock, root)
    bank = _rebuild_bank(lock, root)
    cascade = _cascade(root, [s.sample_id for s in samples])
    log(f"inputs + bank ready in {time.time()-inputs_started:.1f}s")

    # An in-process control runs its encoder on the SAME GPU a server session
    # would occupy, so its whole load+encode wall time is charged to the
    # flight's GPU accounting exactly like a session's resident time.
    gpu_started = time.time()
    cached_client: dict[str, object] = {}
    charged = {"n": 0}

    def loader():
        """Memoized: run_glap_import_and_audio_sanity_gate calls its loader
        TWICE (text sanity, then audio sanity). Loading 3.4 GB of weights twice
        would double the GPU occupancy for zero evidence, so the client is
        built once and handed back. The gate's own semantics are unchanged."""

        if "client" not in cached_client:
            load_started = time.time()
            inner = glap_loader.build_glap_client(root)
            log(f"[glap] model loaded in {time.time()-load_started:.1f}s")
            cached_client["inner"] = inner
            cached_client["client"] = ChargingGateClient(inner, handle=handle, audio_seconds=float(fid.GATE_WAV_SECONDS))
        return cached_client["client"]

    load_seconds = 0.0
    contact_latency = 0.0
    try:
        if "gate_b_glap" not in state.document:
            t0 = time.time()
            # The machinery's own gate deliberately lets a non-ImportError
            # surface loud ("a real bug in a present dependency must surface
            # loud, never be misreported as a missing one") -- that is what
            # caught the GLAP device-placement bug during P-EMB-3M. It is
            # caught HERE instead of inside the machinery, under its own
            # distinct, loudly-named status, so the fact is disclosed rather
            # than swallowed AND "a dropped model never blocks another arm"
            # still holds.
            try:
                result_status = None
                result = F.run_glap_import_and_audio_sanity_gate(
                    model_id=glap_loader.GLAP_MODEL_ID, loader=loader, sanity_audio_bytes=gate_wav
                )
                result_status = result.status
                result_detail = result.detail
                result_dims = None if result.sanity_vector is None else result.sanity_vector.dims
            except Exception as error:  # noqa: BLE001 -- disclosed, never silent
                result_status = "DROPPED-RUNTIME-ERROR"
                result_detail = f"{type(error).__name__}: {error}"
                result_dims = None
                log(f"GATE (b) GLAP: DROPPED-RUNTIME-ERROR -- {result_detail}")
            contact_latency += time.time() - t0
            charged["n"] = getattr(cached_client.get("client"), "charged", 0)
            log(f"GATE (b) GLAP IMPORT + AUDIO-PATH SANITY: {result_status} -- {result_detail}")
            state.put(
                "gate_b_glap",
                {
                    "model_id": glap_loader.GLAP_MODEL_ID,
                    "status": result_status,
                    "detail": result_detail,
                    "sanity_dims": result_dims,
                    "contacts": charged["n"],
                },
            )
            if result_status != F.STATUS_OK:
                for arm_id in arms:
                    dropped[arm_id] = f"{result_status}: {result_detail}"
                state.put("dropped_arms", dropped)
                log(f"GATE (b) FAILED -> {sorted(arms)} DROPPED; disclosed and NON-BLOCKING to every other arm")
                return 0
        if "inner" not in cached_client:
            load_started = time.time()
            cached_client["inner"] = glap_loader.build_glap_client(root)
            load_seconds += time.time() - load_started
            log(f"[glap] model loaded in {load_seconds:.1f}s")
        client = cached_client["inner"]

        def proxy_factory(sweep_id: str, total: int, audio_map):
            vector_log = run_dir / f"vectors-{sweep_id.replace(':', '-')}.jsonl"
            cached = load_cached(vector_log)
            if cached:
                log(f"[{sweep_id}] resume: {len(cached)} cached vectors will be replayed without a tool contact")
            return BudgetedCachingProxy(
                client, sweep_id=sweep_id, store=store, handle=handle, plan=plan,
                vector_log=vector_log, cached=cached, audio_seconds_by_contact=audio_map, total_contacts=total,
                supports_prefix=False, supports_marker=False,
            )

        flown, latency = _run_bank_and_queries(
            model=model, client=client, proxy_factory=proxy_factory, state=state, root=root, bank=bank,
            samples=samples, transcripts=cascade.transcripts, supports_prefix=False, supports_marker=False,
            server_key="in-process",
        )
        contact_latency += latency
    finally:
        wall = time.time() - gpu_started
        acc = _gpu_add(state, wall=wall, load=max(wall - contact_latency, 0.0), contact=contact_latency)
        log(
            f"[glap] in-process arm wall {wall:.1f}s (contact latency {contact_latency:.1f}s); cumulative "
            f"GPU-active {(acc['load']+acc['contact'])/3600:.4f} h"
        )
        for key in list(cached_client):
            cached_client.pop(key, None)
        try:
            import gc

            import torch

            gc.collect()
            torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001 -- best-effort VRAM release
            pass
    calls, audio = handle.actual_totals()
    log(f"durable spend after stage glap: calls={calls}, audio_seconds={audio:.3f}")
    return 0


# ---------------------------------------------------------------------------
# Stage: retrieval (FLIGHT-SIDE, gold-free, ZERO contacts).
# ---------------------------------------------------------------------------


def stage_retrieval(args) -> int:
    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    F.assert_never_accesses_frozen_60_gold()
    bank = _rebuild_bank(lock, root)
    bank_labels = {entry.bank_id: entry.gold_scenario for entry in bank.entries}
    dropped = dict(state.document.get("dropped_arms", {}))

    flyable = [a for a in F.ARM_IDS if a not in dropped]
    log(f"retrieval: flyable arms {flyable}; dropped {sorted(dropped)}")

    bank_vectors: dict[str, Mapping[str, object]] = {}
    for model in F.MODELS:
        if any(a in flyable for a in F.ARM_IDS_BY_MODEL[model]) and F.is_bank_vectors_complete(root, model):
            loaded = F.load_bank_vectors(root, model)
            bank_vectors[model] = loaded.vectors
            log(f"  bank vectors [{model}]: {len(loaded.vectors)} rows, dim {loaded.dims}")

    arm_retrievals: dict[str, F.ArmRetrieval] = {}
    for arm_id in flyable:
        arm = F.ARMS_BY_ID[arm_id]
        if arm.model not in bank_vectors:
            raise RuntimeError(f"arm {arm_id!r} is flyable but its model's bank vectors are missing")
        if not F.is_query_vectors_complete(root, arm_id):
            raise RuntimeError(f"arm {arm_id!r} is flyable but its query vectors are incomplete")
        queries = F.load_query_vectors(root, arm_id)
        started = time.time()
        retrieval = F.build_arm_retrieval(arm_id, queries.vectors, bank_vectors[arm.model], bank_labels)
        arm_retrievals[arm_id] = retrieval
        log(
            f"  retrieval [{arm_id}]: {len(retrieval.per_sample)} samples ranked against "
            f"{len(bank_vectors[arm.model])} bank rows in {time.time()-started:.1f}s"
        )

    if not arm_retrievals:
        raise RuntimeError("retrieval: no arm produced a retrieval; refusing to write an empty plan")
    winner = F.select_retrieval_winner(arm_retrievals)
    document = F.build_retrieval_plan_document(arm_retrievals, winner)
    path, plan_sha256 = F.write_retrieval_plan(root, document)
    log(f"retrieval plan written: {path}")
    log(f"retrieval plan sha256: {plan_sha256}")
    log(f"winner arm (GOLD-FREE proxy, {F.WINNER_SELECTION_RULE}): {winner}")

    # CONSTRUCTION METADATA ONLY -- candidate-set SIZES, never their contents'
    # correctness. No gold is involved anywhere in this block.
    per_arm_stats: dict[str, object] = {}
    for arm_id, retrieval in sorted(arm_retrievals.items()):
        sizes = Counter(len(row.dedup_labels_k5) for row in retrieval.per_sample.values())
        sizes3 = Counter(len(row.dedup_labels_k3) for row in retrieval.per_sample.values())
        per_arm_stats[arm_id] = {
            "mean_top1_cosine": retrieval.mean_top1_cosine,
            "candidate_set_size_distribution_k5": {str(k): v for k, v in sorted(sizes.items())},
            "candidate_set_size_distribution_k3": {str(k): v for k, v in sorted(sizes3.items())},
            "mean_candidate_set_size_k5": sum(k * v for k, v in sizes.items()) / max(sum(sizes.values()), 1),
            "n_samples": len(retrieval.per_sample),
        }
        log(
            f"  [{arm_id}] mean_top1_cosine={retrieval.mean_top1_cosine:.6f} "
            f"k5 candidate-set sizes={json.dumps({str(k): v for k, v in sorted(sizes.items())})}"
        )
    state.put(
        "retrieval_plan",
        {
            "path": str(path),
            "sha256": plan_sha256,
            "schema": document["schema"],
            "k_primary": document["k_primary"],
            "winner_arm_id": winner,
            "winner_query_kind": F.ARMS_BY_ID[winner].query_kind,
            "winner_selection_rule": document["winner_selection_rule"],
            "arms_in_plan": sorted(arm_retrievals),
            "per_arm_construction_stats": per_arm_stats,
            "gold_free_note": (
                "retrieval is a PURE function of already-flown vectors plus the bank's own TRAIN-split "
                "VALUE metadata; no devel gold is loaded anywhere in this stage, and nothing here is "
                "scored. analysis.pemb4r_read re-derives the SAME plan independently and compares it "
                "field-by-field rather than trusting this artifact."
            ),
        },
    )
    log("RETRIEVAL PLAN COMPLETE -- zero contacts spent, zero gold loaded")
    return 0


# ---------------------------------------------------------------------------
# Stage: cdecode (the ONE frozen-core contact block).
# ---------------------------------------------------------------------------


class GenerationHealthProxy:
    """Charges the durable attempt before every generation request, persists
    every response for resume, and logs OPERATIONAL health only -- request
    index, sample id, latency, response LENGTH. Never inspects a response body,
    never scores anything."""

    def __init__(self, inner, *, response_log: Path, cached: list[dict], store, handle, plan, audio_seconds: float, total: int) -> None:
        self._inner = inner
        self._response_log = response_log
        self._cached = cached
        self._store = store
        self._handle = handle
        self._plan = plan
        self._audio_seconds = float(audio_seconds)
        self._total = total
        self._index = 0
        self._started_at = time.time()
        self.replayed = 0
        self.flown = 0
        self.failures: list[dict] = []
        self.latency_total = 0.0
        self.calls_used, self.audio_seconds_used = handle.actual_totals()

    @staticmethod
    def messages_hash(messages: Sequence[Mapping[str, object]]) -> str:
        blob = json.dumps(list(messages), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def complete(self, messages, *, decoding_params=None, text_only_sample_id=None):
        self._index += 1
        index = self._index
        mhash = self.messages_hash(messages)

        if index <= len(self._cached):
            entry = self._cached[index - 1]
            if entry["index"] != index or entry["messages_sha256"] != mhash:
                raise RuntimeError(
                    f"resume divergence at request {index}: cached messages_sha256 "
                    f"{entry['messages_sha256']!r} != rebuilt {mhash!r}; refusing to replay a response "
                    "that does not belong to this request (fail-closed)"
                )
            self.replayed += 1
            if index % 10 == 0 or index == len(self._cached):
                log(f"replay {index}/{len(self._cached)} from cache")
            return entry["response_text"]

        sibling_calls, sibling_audio = self._store.prior_actual_usage(
            self._plan.run_id, exclude_attempt_id=self._plan.attempt_id
        )
        if sibling_calls + self.calls_used + 1 > self._plan.planned_model_calls:
            raise RuntimeError(
                f"call ceiling: plan allows {self._plan.planned_model_calls}; refusing generation contact"
            )
        if sibling_audio + self.audio_seconds_used + self._audio_seconds > self._plan.planned_speech_audio_seconds:
            raise RuntimeError(
                f"audio ceiling: plan allows {self._plan.planned_speech_audio_seconds}s, "
                f"{self.audio_seconds_used:.3f}s spent by this attempt; refusing generation contact"
            )
        self.calls_used, self.audio_seconds_used = self._handle.record_usage(
            calls=1, audio_seconds=self._audio_seconds
        )

        started = time.time()
        try:
            text = self._inner.complete(messages, decoding_params=decoding_params, text_only_sample_id=text_only_sample_id)
        except Exception as error:  # noqa: BLE001
            elapsed = time.time() - started
            self.failures.append({"index": index, "error": f"{type(error).__name__}: {error}"})
            log(f"c-decode req {index:03d} FAILED after {elapsed:.1f}s :: {type(error).__name__}: {error}")
            raise
        elapsed = time.time() - started
        self.flown += 1
        self.latency_total += elapsed
        with self._response_log.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "index": index,
                        "messages_sha256": mhash,
                        "text_only_sample_id": text_only_sample_id,
                        "latency_seconds": elapsed,
                        "response_text": text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        rate = self.flown / max(time.time() - self._started_at, 1e-9)
        remaining = max(self._total - index, 0)
        log(
            f"c-decode req {index:03d}/{self._total} ok {elapsed:6.2f}s chars={len(text)} | "
            f"flown={self.flown} {rate*60:.1f} req/min eta={remaining/max(rate,1e-9)/60:.1f} min"
        )
        return text


def stage_cdecode(args) -> int:
    from speech_aware_evidence_acquisition.core.base import TRANSPORTS
    from speech_aware_evidence_acquisition.data.lock import asset_dir
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SLURP_LOCK_KEY
    from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient, build_payload_binding

    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    F.assert_never_accesses_frozen_60_gold()

    if state.document.get("c_decode", {}).get("status") == "COMPLETE":
        log("[c-decode] CARRIED: already complete for this attempt -- zero contacts")
        return 0

    plan_block = state.document.get("retrieval_plan")
    if not plan_block:
        raise RuntimeError("stage cdecode requires the retrieval stage to have run first")
    retrieval_plan_document = F.load_retrieval_plan(root)
    if F.retrieval_plan_document_sha256(retrieval_plan_document) != plan_block["sha256"]:
        raise RuntimeError("the retrieval plan on the data root no longer hashes to the value recorded at build time")
    winner = str(plan_block["winner_arm_id"])
    winner_kind = F.ARMS_BY_ID[winner].query_kind
    log(f"winner arm {winner} (query kind {winner_kind}); retrieval plan sha256 {plan_block['sha256']}")

    # ---- the coordinator's own pre-contact ruling, fail-closed ------------
    # It must already be recorded in the flight state, with its own timestamp,
    # BEFORE this stage issues a single generation contact -- that recording is
    # the flight-side proof that the ruling preceded the contacts. Refusing
    # here rather than recording it here is deliberate: a note this stage wrote
    # for itself would prove nothing about ordering.
    ruling = state.document.get(fid.COORDINATOR_PRE_CONTACT_RULING_KEY)
    if not ruling or ruling.get("text") != fid.COORDINATOR_PRE_CONTACT_RULING:
        raise RuntimeError(
            "the coordinator's pre-contact ruling is not recorded in this attempt's flight state "
            "(or does not match verbatim); it MUST be landed before any C-DECODE contact. Refusing "
            "(fail-closed)."
        )
    log(f"coordinator pre-contact ruling recorded at {ruling.get('recorded_at')} (before any generation contact):")
    log(f"  {ruling['text']}")

    # ---- inputs and payload binding BEFORE any spawn (forward rule) -------
    inputs_started = time.time()
    adapter, samples, _labels, manifest = load_inputs(lock, root)
    cascade = _cascade(root, [s.sample_id for s in samples])
    one_pass = sum(float(s.audio_seconds) for s in samples)
    log(f"inputs ready in {time.time()-inputs_started:.1f}s (BEFORE any spawn)")

    # ---- budget-aware modality decision -----------------------------------
    calls_used, audio_used = handle.actual_totals()
    remaining_audio = float(plan.planned_speech_audio_seconds) - float(audio_used)
    per_call_audio = one_pass / len(samples)
    needed_audio = one_pass + per_call_audio  # 60 calls + the 1 determinism resend
    if winner_kind == "audio" and remaining_audio < needed_audio:
        decision_kind = "text"
        decision_reason = (
            f"BUDGET-FORCED TEXT MODALITY: the winner arm {winner!r} is an AUDIO arm, but only "
            f"{remaining_audio:.2f} metered audio-seconds remain of the registered {F.CEILING_AUDIO_SECONDS}s "
            f"ceiling and a fourth full corpus pass needs {needed_audio:.2f}s. The registration's own "
            "C-DECODE requirement is the WINNER'S TOP-K DEDUP LABELS feeding a closed-set decode "
            "(section 3 row 8); presenting the winner's own modality is the machinery docstring's "
            "additional preference, and rails.probes.pemb4r_flight.assemble_c_decode_messages supports "
            "both modalities as a first-class parameter. So the candidate label sets stay EXACTLY the "
            "winner arm's own, and the observation is the CONSUMED pkey2-338 T0 self-transcript. "
            "The read must carry this: the paired FS-NONE baseline is audio-modality, so this pairing "
            "confounds retrieval-shrunk supply with a transcript-vs-audio observation change."
        )
    else:
        decision_kind = winner_kind
        decision_reason = (
            f"winner arm {winner!r} is a {winner_kind.upper()} arm and the modality it queried with is "
            f"affordable ({remaining_audio:.2f}s metered audio remaining, {needed_audio:.2f}s needed); "
            "C-DECODE presents the SAME modality the winner's own query side used, per the machinery."
        )
    log(decision_reason)
    state.put(
        "c_decode_modality_decision",
        {
            "winner_arm_id": winner,
            "winner_query_kind": winner_kind,
            "c_decode_query_kind": decision_kind,
            "budget_forced": decision_kind != winner_kind,
            "metered_audio_used_before_c_decode": audio_used,
            "metered_audio_remaining": remaining_audio,
            "metered_audio_needed_for_audio_modality": needed_audio,
            "reason": decision_reason,
            "coordinator_pre_contact_ruling": fid.COORDINATOR_PRE_CONTACT_RULING,
            "coordinator_pre_contact_ruling_recorded_at": ruling.get("recorded_at"),
            # Disclosed unconditionally, because it is true whenever C-DECODE
            # ends up on the transcript modality -- whether that came from the
            # budget-forced fallback OR from the winner arm simply being a text
            # arm, which is the machinery's own intended behaviour. The
            # coordinator's ruling keys "not evaluable" to budget_forced; this
            # field records the underlying comparator fact separately so the
            # read never has to infer it.
            "fs_none_comparator_modality": "audio",
            "modality_matches_fs_none_comparator": decision_kind == "audio",
            "modality_confound_note": (
                "The CONSUMED P-FEW FS-NONE rows this probe's C-DECODE is paired against were "
                "produced on the AUDIO modality (rails.probes.pfew_flight uses "
                "SlurpAdapter.assemble_prompt for FS-NONE). Whenever C-DECODE runs on the "
                "transcript modality the pairing therefore mixes the retrieval-shrunk label space "
                "with a transcript-vs-audio observation change, independently of whether the "
                "budget-forced fallback fired. Recorded flight-side, before the contacts, as a fact "
                "for the read to carry; this flight evaluates nothing."
            ),
            "read_consequence": (
                "budget_forced fired -> per the coordinator's pre-contact ruling above, the "
                "registration's C-DECODE HELPS/HURTS clauses are NOT evaluable at the read; "
                "C-DECODE reports descriptively only"
                if decision_kind != winner_kind
                else "budget_forced did NOT fire -> the registration's C-DECODE clauses evaluate as registered"
            ),
        },
    )
    audio_per_call = per_call_audio if decision_kind == "audio" else fid.TEXT_CONTACT_AUDIO_SECONDS

    # ---- the FULL frozen-core gate, BEFORE the spawn ----------------------
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path(args.runtime_root),
        runtime_receipt_relpath=fid.RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=str(values["model_lock_key"]),
    )
    log(
        "FORWARD RULE (P-CORR-F section 8): running the FULL frozen-core gate -- including the q4km "
        "GGUF attestation -- BEFORE any server is spawned, so model-identity hashing never runs while "
        "a session holds VRAM idle. This is minutes of cold 9p I/O and costs ZERO GPU time."
    )
    gate_started = time.time()
    diagnostics: dict[str, object] = {}
    lock_sha256 = gate.assert_model_touch_allowed(plan, full_hash=True, diagnostics=diagnostics)
    gate_seconds = time.time() - gate_started
    log(f"frozen-core gate PASS in {gate_seconds:.1f}s (umbrella lock sha256 {lock_sha256})")
    state.put(
        "c_decode_gate",
        {
            "seconds": round(gate_seconds, 1),
            "full_hash": True,
            "diagnostics": {k: str(v) for k, v in diagnostics.items()},
            "umbrella_lock_sha256": lock_sha256,
            "ran_before_spawn": True,
        },
    )

    payload_binding = build_payload_binding(
        carrier_lock_key=SLURP_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root),
    )
    log("payload binding built (still pre-spawn)")

    runtime_receipt = load_runtime_receipt(REPO / "docs" / fid.RUNTIME_RECEIPT_RELPATH)
    if _port_reachable(args.host, fid.GENERATION_PORT):
        raise RuntimeError(f"something is already listening on the generation port {fid.GENERATION_PORT}; refusing")
    log("spawning llama-server (receipt-pinned q4km binary, CHILD of this process)")
    session, spawn_seconds, started = None, 0.0, time.time()
    contact_latency = 0.0
    session_receipt_path = run_dir / f"{fid.run_id()}.session-q4km-core.receipt.json"
    server_log_path = run_dir / f"{fid.run_id()}.session-q4km-core.server.log"
    # The session's own contact count, MEASURED. It starts at zero and is only
    # ever advanced by what actually flew -- never by a hardcoded expectation of
    # the full pass. The teardown below runs in a `finally`, so a stage that
    # refuses before issuing a single request must record 0, not QUERY_N + 1.
    # (This is the corrected form of a real defect in this launcher's first
    # cdecode run: it wrote 61 for a session that issued nothing. The landed
    # receipt carries the correction under its own `corrections` key.)
    session_contacts = 0
    try:
        session = start_session(
            runtime_root=Path(args.runtime_root),
            data_root=root,
            runtime_receipt=runtime_receipt,
            host=args.host,
            port=fid.GENERATION_PORT,
            session_id=f"{fid.run_id()}-{args.attempt_id}-q4km-core",
            extra_argv=fid.core_server_args(values),
            extra_env=fid.core_server_env(values),
            receipt_path=session_receipt_path,
            server_log_path=server_log_path,
            ready_timeout_seconds=900.0,
        )
        spawn_seconds = time.time() - started
        log(f"session up: pid={session.pid} port={session.port} (spawn+load {spawn_seconds:.1f}s)")
        log(f"session argv: {' '.join(session.argv)}")
        log(f"generation parallelism: -np {values['generation_session']['parallelism_np']} (carried UNCHANGED from the committed fragment)")
        for entry in session.model_files:
            log(f"  model file: {entry.path} sha256={entry.sha256}")

        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=Path(args.runtime_root)
        )
        client = FrozenCoreClient(
            plan=plan, gate=gate, transport=transport, run_dir=run_dir, binding=payload_binding,
            arm=fid.D2_ARM, request_id_prefix="pemb4r",
        )
        log(f"FrozenCoreClient constructed (D2 arm {client.arm}); flight lock {client.flight_lock}")

        response_log = run_dir / "c-decode-responses.jsonl"
        cached = load_cached(response_log)
        if cached:
            log(f"resume: {len(cached)} cached C-DECODE responses will be replayed without a core contact")
        proxy = GenerationHealthProxy(
            client, response_log=response_log, cached=cached, store=store, handle=handle, plan=plan,
            audio_seconds=audio_per_call, total=F.QUERY_N,
        )
        flight_started = time.time()
        log(f"C-DECODE START: {F.QUERY_N} closed-set generation calls over the winner arm's own top-5 dedup labels")
        results = F.run_c_decode_flight(
            core_client=proxy,
            samples=samples,
            retrieval_plan_document=retrieval_plan_document,
            winner_arm_id=winner,
            winner_query_kind=decision_kind,
            transcript_registry=cascade.transcripts,
            adapter=adapter,
            decoding_params=fid.decoding_params(values),
        )
        flight_wall = time.time() - flight_started
        contact_latency += proxy.latency_total
        session_contacts += proxy.flown
        log(f"C-DECODE DONE: {flight_wall:.1f}s, flown={proxy.flown} replayed={proxy.replayed}")

        # ---- outputs, WRITTEN, NEVER READ by this launcher ---------------
        outputs_path = run_dir / "c-decode-outputs.jsonl"
        with outputs_path.open("w", encoding="utf-8") as sink:
            for result in results:
                sink.write(
                    json.dumps(
                        {
                            "sample_id": result.sample_id,
                            "winner_arm_id": winner,
                            "c_decode_query_kind": decision_kind,
                            "candidate_labels": list(result.candidate_labels),
                            "messages": list(result.messages),
                            "response_text": result.response_text,
                            "closed_set_mapping": result.closed_set_mapping.as_json(),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        log(f"c-decode-outputs.jsonl written: {len(results)} rows -- NOT read by this launcher")

        # ---- the ONE identical-prompt determinism resend -----------------
        resend = state.document.get("c_decode_determinism")
        if resend is None:
            first = results[0]
            base_sha = hashlib.sha256(first.response_text.encode("utf-8")).hexdigest()
            gate_audio = audio_per_call
            handle.record_usage(calls=1, audio_seconds=gate_audio)
            t0 = time.time()
            resend_text = client.complete(
                list(first.messages),
                decoding_params=fid.decoding_params(values),
                text_only_sample_id=(first.sample_id if decision_kind == "text" else None),
            )
            contact_latency += time.time() - t0
            session_contacts += 1
            resend_sha = hashlib.sha256(resend_text.encode("utf-8")).hexdigest()
            log(
                f"C-DECODE determinism resend (sample {first.sample_id}, IDENTICAL prompt): "
                f"byte_identical={base_sha == resend_sha} (chars {len(first.response_text)} vs {len(resend_text)})"
            )
            (run_dir / "c-decode-determinism-resend.json").write_text(
                json.dumps(
                    {
                        "sample_id": first.sample_id,
                        "messages_sha256": GenerationHealthProxy.messages_hash(first.messages),
                        "response_a_sha256": base_sha,
                        "response_b_sha256": resend_sha,
                        "response_a_chars": len(first.response_text),
                        "response_b_chars": len(resend_text),
                        "byte_identical": base_sha == resend_sha,
                        "response_b_text": resend_text,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
                newline="\n",
            )
            state.put(
                "c_decode_determinism",
                {
                    "sample_id": first.sample_id,
                    "parallelism_np": values["generation_session"]["parallelism_np"],
                    "response_a_sha256": base_sha,
                    "response_b_sha256": resend_sha,
                    "byte_identical": base_sha == resend_sha,
                    "contacts": 1,
                    "note": (
                        "one IDENTICAL-prompt resend against the SAME live session, recorded because the "
                        "P-CORR-F pre-read resend finding (6/20 identical-prompt pairs diverged at -np 4) "
                        "makes the generation server's own parallelism setting load-bearing. sha256 "
                        "equality only; the flight evaluates no tolerance and reads no response body."
                    ),
                },
            )

        receipt = client.close()
        log(f"client.close(): trace_manifest_hash={receipt['trace_manifest_hash']}")
        log(f"cost: {json.dumps(receipt['cost'], sort_keys=True)}")
        state.put(
            "c_decode",
            {
                "status": "COMPLETE",
                "winner_arm_id": winner,
                "winner_query_kind": winner_kind,
                "c_decode_query_kind": decision_kind,
                "n_rows": len(results),
                "outputs_path": str(outputs_path),
                "contacts_flown": proxy.flown,
                "contacts_replayed": proxy.replayed,
                "contact_failures": list(proxy.failures),
                "latency_seconds": round(proxy.latency_total, 3),
                "mean_latency_seconds": round(proxy.latency_total / max(proxy.flown, 1), 3),
                "wall_seconds": round(flight_wall, 2),
                "trace_manifest_hash": receipt["trace_manifest_hash"],
                "core_client_cost": receipt["cost"],
                "candidate_set_sizes": {
                    str(size): count
                    for size, count in sorted(Counter(len(r.candidate_labels) for r in results).items())
                },
            },
        )
    finally:
        if session is not None:
            resident = time.time() - started
            teardown = teardown_session(session.pid, args.host, fid.GENERATION_PORT)
            _append_session(
                state,
                session_record(
                    session, server_key="q4km-core", spawn_seconds=spawn_seconds, resident_seconds=resident,
                    teardown=teardown, extra={"contacts": session_contacts, "kind": "generation"},
                ),
            )
            acc = _gpu_add(state, wall=resident, load=spawn_seconds, contact=contact_latency)
            log(
                f"session q4km-core torn down after {resident:.1f}s resident; cumulative GPU-active "
                f"{(acc['load']+acc['contact'])/3600:.4f} h"
            )
    calls, audio = handle.actual_totals()
    log(f"durable spend after C-DECODE: calls={calls}, audio_seconds={audio:.3f}")
    return 0


# ---------------------------------------------------------------------------
# Stage: finalize.
# ---------------------------------------------------------------------------


def stage_finalize(args) -> int:
    lock, root, values, cfg_hash, plan, run_dir, state, store = load_context(args)
    handle = store.handle(fid.run_id(), args.attempt_id)
    dropped = dict(state.document.get("dropped_arms", {}))

    bank_status: dict[str, object] = {}
    produced = 0
    for model in F.MODELS:
        complete = F.is_bank_vectors_complete(root, model)
        info: dict[str, object] = {"complete": complete}
        if complete:
            loaded = F.load_bank_vectors(root, model)
            info.update({"count": len(loaded.vectors), "dims": loaded.dims})
            produced += len(loaded.vectors)
        bank_status[model] = info
        log(f"  bank[{model}]: complete={complete} " + (f"count={info.get('count')} dims={info.get('dims')}" if complete else ""))

    arm_status: dict[str, object] = {}
    for arm_id in F.ARM_IDS:
        complete = F.is_query_vectors_complete(root, arm_id)
        info = {"complete": complete, "dropped_reason": dropped.get(arm_id)}
        if complete:
            loaded = F.load_query_vectors(root, arm_id)
            info.update({"count": len(loaded.vectors), "dims": loaded.dims})
            produced += len(loaded.vectors)
        arm_status[arm_id] = info
        log(f"  {arm_id}: complete={complete} " + (f"count={info.get('count')} dims={info.get('dims')}" if complete else f"(dropped: {dropped.get(arm_id)})"))

    expected_arms = [a for a in F.ARM_IDS if a not in dropped]
    missing = [a for a in expected_arms if not arm_status[a]["complete"]]
    if missing:
        raise RuntimeError(f"finalize refused: expected arms {missing} are not complete on the data root")
    expected_models = sorted({F.ARMS_BY_ID[a].model for a in expected_arms})
    missing_banks = [m for m in expected_models if not bank_status[m]["complete"]]
    if missing_banks:
        raise RuntimeError(f"finalize refused: expected banks {missing_banks} are not complete")

    expected_produced = len(expected_models) * F.BANK_TOTAL_N + len(expected_arms) * F.QUERY_N
    log(f"sweep-total invariant: {produced} vectors on disk, expected {expected_produced} -- {'PASS' if produced == expected_produced else 'FAIL'}")
    if produced != expected_produced:
        raise RuntimeError(f"sweep produced {produced} vectors, expected {expected_produced}")

    accounting = _gpu_accounting(state)
    F.assert_gpu_hours_within_ceiling(accounting)
    log(
        f"GPU accounting (P-CORR-F section-8 basis): measured-equivalent {accounting.measured_equivalent_hours:.4f} h, "
        f"GPU-active {accounting.gpu_active_hours:.4f} h, server-alive wall {accounting.wall_hours:.4f} h "
        f"(wall recorded, NEVER gates) -- ceiling {F.CEILING_GPU_HOURS} h"
    )
    try:
        handle.record_gpu_seconds(accounting.gpu_active_hours * 3600.0)
    except Exception as exc:  # noqa: BLE001 -- never mask the flight's own outcome
        log(f"record_gpu_seconds failed (non-fatal): {type(exc).__name__}: {exc}")
    actual_calls, actual_audio = handle.actual_totals()
    F.assert_within_registered_ceilings(
        calls=actual_calls, audio_seconds=actual_audio, gpu_hours=accounting.gpu_active_hours
    )
    handle.mark_finalized()
    log(f"attempt {args.attempt_id} FINALIZED")

    receipt = {
        "run_id": fid.run_id(),
        "probe": fid.PROBE_LABEL,
        "attempt_id": args.attempt_id,
        "status": "COMPLETED" if state.document.get("c_decode") else "COMPLETED-EMBEDDING-ARMS-C-DECODE-CEILING-BLOCKED",
        "preregistration": fid.PREREGISTRATION_RELPATH,
        "study_commit_at_takeoff": state.document.get("study_commit"),
        "config_hash": cfg_hash,
        "protocol_hash": plan.protocol_hash,
        "split_identity_hash": plan.split_identity_hash,
        "binding_config_sha256": state.document.get("binding_config_sha256"),
        "umbrella_lock_sha256": state.document.get("umbrella_lock_sha256"),
        "gate_scope_note": state.document.get("gate_scope_note"),
        "bank": state.document.get("bank"),
        "gates": {
            "a_lco7_server_sanity": state.document.get("gate_a_lco7_sanity"),
            "b_glap_import_and_audio_sanity": state.document.get("gate_b_glap"),
            "c_pooling_differ_lco3": state.document.get("gate_c_pooling_differ_lco3"),
            "c_pooling_differ_lco7": state.document.get("gate_c_pooling_differ_lco7"),
            "d_encode_only": state.document.get("gate_d_encode_only"),
            "e_cascade_source": state.document.get("gate_e_cascade_source"),
        },
        "determinism_samples": {
            "lco3": state.document.get("repeat_call_determinism_lco3"),
            "lco7": state.document.get("repeat_call_determinism_lco7"),
            "qw": state.document.get("repeat_call_determinism_qw"),
            "c_decode": state.document.get("c_decode_determinism"),
            "note": (
                "recorded as sha256 equality only; every jitter vector pair and the resend response are "
                "persisted on the data root so analysis.pemb4r_read can derive the measured repeat-delta "
                "the registration's own argmax-stability statement needs. GLAP is in-process with no "
                "server session at all, so section 6's per-server-session rule does not reach it."
            ),
        },
        "model_file_sha256": state.document.get("model_file_sha256"),
        "model_file_measurements": state.document.get("model_file_measurements"),
        "declared_embedding_length_by_model": state.document.get("declared_embedding_length_by_model"),
        "umbrella_lock_crosscheck": state.document.get("umbrella_lock_crosscheck"),
        "props": {k: v for k, v in state.document.items() if k.startswith("props_")},
        "gate_wav_sha256": state.document.get("gate_wav_sha256"),
        "sweeps": state.document.get("sweeps"),
        "bank_status_final": bank_status,
        "arm_status_final": arm_status,
        "arms_flown": sorted(expected_arms),
        "arms_dropped": dropped,
        "retrieval_plan": state.document.get("retrieval_plan"),
        "c_decode": state.document.get("c_decode"),
        "c_decode_blocked": state.document.get("c_decode_blocked"),
        "c_decode_modality_decision": state.document.get("c_decode_modality_decision"),
        "c_decode_gate": state.document.get("c_decode_gate"),
        # Recorded VERBATIM at the coordinator's instruction, with the UTC
        # instant it was landed in this attempt's own flight state. The
        # cdecode stage refuses fail-closed unless this block is already
        # present and matches verbatim, so its presence here IS the flight-side
        # record that the ruling preceded every generation contact.
        "coordinator_pre_contact_ruling": state.document.get(fid.COORDINATOR_PRE_CONTACT_RULING_KEY),
        "sessions": state.document.get("sessions", []),
        "n_vectors_produced": produced,
        "n_vectors_expected": expected_produced,
        "planned_budgets": dict(fid.PLANNED_BUDGETS),
        "planned_gate_contacts": fid.PLANNED_GATE_CONTACTS,
        "gate_contact_plan": dict(fid.GATE_CONTACT_PLAN),
        "registered_ceilings": state.document.get("registered_ceilings"),
        "one_pass_metered_audio_seconds": state.document.get("one_pass_metered_audio_seconds"),
        "gpu_accounting": {
            "basis": (
                "P-CORR-F section-8 ruling: the ceiling's accounting basis is PER-CALL "
                "MEASURED-EQUIVALENT and GPU-ACTIVE OCCUPANCY. Server-alive wall is recorded and "
                "NEVER gates."
            ),
            "measured_equivalent_hours": accounting.measured_equivalent_hours,
            "gpu_active_hours": accounting.gpu_active_hours,
            "server_alive_wall_hours": accounting.wall_hours,
            "seconds": state.document.get("gpu_accounting_seconds"),
            "ceiling_gpu_hours": F.CEILING_GPU_HOURS,
            "forward_rule_applied": (
                "the frozen-core gate's full q4km GGUF attestation and every payload binding ran BEFORE "
                "the generation session was spawned, so no model-identity hashing happened while a "
                "server held VRAM idle"
            ),
        },
        "durable_actual": {
            "calls": actual_calls,
            "audio_seconds": actual_audio,
            "gpu_seconds": handle.actual_gpu_seconds(),
            "gpu_hours": handle.actual_gpu_seconds() / 3600.0,
        },
        "prior_durable_spend_before_this_attempt": state.document.get("prior_durable_spend"),
        "result_read": False,
        "result_read_note": (
            "THIS FLIGHT READ NO RESULT: no accuracy, no recall, no vote evaluation, no "
            "gold-vs-prediction comparison anywhere; the frozen 60's own devel gold was never loaded "
            "(machine-checked by rails.probes.pemb4r_flight.assert_never_accesses_frozen_60_gold). The "
            "retrieval plan is a PURE function of flown vectors plus the bank's own TRAIN-split VALUE "
            "metadata and is flight-side by the machinery's own design; the read re-derives it "
            "independently. The byte-level comparisons recorded above (two POOLING-DIFFER gates, three "
            "embedding repeat-call determinism samples, one C-DECODE identical-prompt resend) are "
            "instrument-health facts the registration itself mandates."
        ),
    }
    receipt_path = run_dir / "flight-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str), encoding="utf-8", newline="\n")
    log(f"flight receipt: {receipt_path}")
    log(
        f"durable spend this attempt: calls={actual_calls}, audio_seconds={actual_audio:.3f}, "
        f"gpu_hours(active)={accounting.gpu_active_hours:.4f}"
    )
    log(
        f"vs registered ceilings: {actual_calls}/{fid.REGISTERED_CEILINGS['model_calls']} calls, "
        f"{actual_audio:.1f}/{fid.REGISTERED_CEILINGS['speech_audio_seconds']}s audio, "
        f"{accounting.gpu_active_hours:.4f}/{fid.REGISTERED_CEILINGS['gpu_hours']} GPU-h (active), "
        f"{accounting.measured_equivalent_hours:.4f} measured-equivalent, {accounting.wall_hours:.4f} wall"
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
        "lco3": stage_lco3,
        "lco7": stage_lco7,
        "qw": stage_qw,
        "glap": stage_glap,
        "retrieval": stage_retrieval,
        "cdecode": stage_cdecode,
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
