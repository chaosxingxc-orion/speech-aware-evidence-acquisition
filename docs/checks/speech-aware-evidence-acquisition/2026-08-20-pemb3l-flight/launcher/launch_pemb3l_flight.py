"""P-EMB-3L flight launcher (REGISTERED probe, exposure row
``SAEA-PROBE-pemb3l-234``). ONE invocation flies the WHOLE registered sweep:
three arms, 234 embedding contacts, across TWO sequential llama-server
sessions (one per pooling mode).

Structurally the archived P-EMB launcher
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-pemb1-flight/
launcher/launch_pemb_flight.py``), with the ONE architectural difference this
registration forces: a resident llama-server's pooling mode is a STARTUP FLAG,
never a per-request parameter, so L1+L2 (``--pooling last``) and L3
(``--pooling mean``) cannot share a session. This launcher therefore owns TWO
sequential sessions under ONE ExecutionPlan and ONE durable attempt --
``rails.probes.pemb3l_flight`` itself never touches a socket ("tagged not
managed", its own module docstring), so the per-arm entry point
:func:`~rails.probes.pemb3l_flight.run_pemb3l_arm_flight` is the sanctioned
seam and this launcher re-asserts the sweep total
(:data:`~rails.probes.pemb3l_flight.EXPECTED_TOTAL_CONTACTS`) itself, exactly
as ``run_pemb3l_sweep_flight`` would have.

Order of operations, identical in kind and fail-closed semantics to the P-EMB
precedent:

    contracts.FrozenCoreGate.for_study_repo(...).assert_model_touch_allowed(plan)
      -- plan/scope validation, exposure pre-registration match, carrier scope,
         E0 closure + scoring freeze, runtime receipt + binary + GGUF bytes.
    rails.embedding_client.assert_no_conflicting_generation_server(...)
      -- fail-closed refusal to start while anything still answers on the
         GENERATION port (GENERATION_COEXISTENCE_NOTE). Re-checked before EACH
         session's spawn, not only once.
    core.attempts.AttemptStore.open_attempt(...)
      -- the durable, atomic, one-time (run_id, attempt_id) key; every contact's
         spend is persisted BEFORE the request leaves the process, and every
         sibling attempt's spend is charged against the SAME plan ceiling.
    core.session.start_session(...)   [per session]
      -- spawns the receipt-pinned binary in EMBEDDING mode, on its own port,
         with that session's own --pooling value.
    rails.embedding_client.EmbeddingClient(...).verify_media_marker()
      -- run by the machinery at the head of EVERY arm: the env-pinned
         LLAMA_MEDIA_MARKER re-verified against the LIVE server's own
         GET /props, fail-closed, before that arm's first contact.
    rails.probes.pemb3l_flight.run_pemb3l_arm_flight(...)   [per arm]
      -- the registered 78-contact arm, count/identity/legality-checked
         fail-closed, with THAT arm's own pooling tag and instruct prefixes.
    rails.probes.pemb3l_flight.write_pemb3l_arm_manifest(...)   [per arm]
      -- fp32 .npy per contact + a hashed manifest.json under the DATA ROOT, at
         derived/embeddings/SAEA-PROBE-pemb3l-234/<arm>/.
    teardown  [per session]
      -- SIGTERM the pid this launcher itself spawned, wait, escalate, and
         prove the port is free before the next session binds it.

THIS LAUNCHER NEVER READS A RESULT. Embedding VECTORS are the flight's own
product and are written to the data root, but nothing here ever compares two
of them: no cosine, no argmax, no ranking, no accuracy, no per-arm verdict.
That is the separately-registered one-shot read mission's job
(``analysis.pemb3l_read``). Health logging prints ONLY the contact index,
kind, contact id, latency and dimension -- never a vector component.

Resumability under one registration (``--attempt-id``): every returned vector
is appended to that ARM's own ``vectors-<arm>.jsonl`` as it arrives, keyed by
contact index and the sha256 of that contact's own payload (the raw audio
bytes or exact text string, PREFIXED exactly as sent -- so an L1 cache entry
can never be replayed for an L2 contact). A resumed attempt replays those
cached vectors instead of re-contacting the core, and fails closed the moment
a replayed contact's payload hash disagrees with the cached one.
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

from flight_identity import (  # noqa: E402
    CARRIER_LOCK_KEY,
    EMBEDDING_PORT,
    EXECUTION_PROFILE,
    GENERATION_PORT,
    PLANNED_BUDGETS,
    PREREGISTRATION_RELPATH,
    REGISTERED_CEILINGS,
    ROSTER_TABLE_RELPATH,
    SAMPLE_MANIFEST_RELPATH,
    SPLIT_ROLE,
    TEXT_CONTACT_AUDIO_SECONDS,
    build_values,
    config_hash_of,
    run_id as resolve_run_id,
    server_env,
    session_argv,
    session_plan,
    split_identity_hash as resolve_split_identity_hash,
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
from speech_aware_evidence_acquisition.rails.probes.pemb3l_flight import (  # noqa: E402
    ARM_AUDIO_N,
    ARM_LABEL_N,
    ARM_TOTAL_N,
    ARMS_BY_ID,
    EXPECTED_TOTAL_CONTACTS,
    arm_run_id,
    assert_binding_config_sha256,
    binding_config_sha256,
    run_pemb3l_arm_flight,
    write_pemb3l_arm_manifest,
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


def _pid_alive(pid: int) -> bool:
    """Zombie-safe liveness for a server THIS launcher spawned.

    A spawned server is a CHILD of this process, so the moment it exits it
    becomes a ZOMBIE until someone reaps it -- and ``os.kill(pid, 0)``
    SUCCEEDS on a zombie, because the pid still occupies a slot in the
    process table. Signal-probing alone therefore reports an already-exited
    server as alive forever. That is exactly what aborted this probe's first
    attempt (2026-08-20 ``attempt-20260820T062543Z-e91099``): llama-server
    took SIGTERM and died -- its port was already unreachable -- but the
    unreaped zombie kept answering signal 0, so the teardown guard escalated
    to SIGKILL and then refused the whole sweep.

    Reap first (the repository's own ``tests/unit/test_session.py`` spawn
    probe uses the same ``os.waitpid`` discipline after killing), then treat a
    ``Z`` state as dead, and only then fall back to the signal probe for a
    process that is genuinely not ours."""

    try:
        reaped, _status = os.waitpid(pid, os.WNOHANG)
        if reaped == pid:
            return False
    except ChildProcessError:
        pass  # not (or no longer) our child -- fall through to the probes below
    except OSError:
        pass
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
        # The comm field is parenthesised and may itself contain spaces, so
        # split on the LAST ')' before reading the state character.
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


def arm_manifest_status(root: Path, arm_id: str) -> tuple[bool, dict[str, object]]:
    """Is this arm's registered product ALREADY on the data root, complete?

    STRUCTURAL ONLY -- entry count, kind split, declared dims and ``.npy``
    presence, read out of the arm's own ``manifest.json``. No vector VALUE is
    ever read and no two vectors are compared; this is the same "did the bytes
    land" shape the post-flight check uses, never a result.

    A complete arm is SKIPPED rather than re-flown. That makes the sweep
    idempotent at the arm level, which is what lets a second attempt finish a
    partially-flown registered sweep without re-spending registered calls on
    contacts an earlier attempt already durably paid for."""

    manifest_path = Path(root) / "derived" / "embeddings" / arm_run_id(arm_id) / "manifest.json"
    info: dict[str, object] = {"manifest_path": str(manifest_path), "manifest_present": manifest_path.is_file()}
    if not manifest_path.is_file():
        return False, info
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        info["error"] = f"{type(error).__name__}: {error}"
        return False, info
    entries = document.get("entries", [])
    audio_n = sum(1 for e in entries if e.get("kind") == "audio")
    text_n = sum(1 for e in entries if e.get("kind") == "text")
    npy_present = sum(1 for e in entries if (Path(root) / str(e.get("relpath", ""))).is_file())
    dims_ok = all(e.get("dims") == EMBEDDING_DIM for e in entries)
    info.update(
        {
            "manifest_run_id": document.get("run_id"),
            "entry_count": len(entries),
            "audio_entries": audio_n,
            "text_entries": text_n,
            "npy_present": npy_present,
            "distinct_vector_sha256": len({e.get("sha256") for e in entries}),
            "all_entries_declare_pinned_dim": dims_ok,
        }
    )
    complete = (
        len(entries) == ARM_TOTAL_N
        and audio_n == ARM_AUDIO_N
        and text_n == ARM_LABEL_N
        and npy_present == len(entries)
        and dims_ok
    )
    info["complete"] = complete
    return complete, info


def teardown_session(pid: int, host: str, port: int, *, timeout_seconds: float = 45.0) -> dict[str, object]:
    """Tear down the server THIS launcher spawned, by the exact pid it got
    back from ``start_session`` -- never a pattern-matched ``pkill``, so a
    sibling session's server (or another repo's campaign) can never be caught
    in the blast radius. Escalates SIGTERM -> SIGKILL and then proves the port
    is actually free before returning, because the next session is about to
    bind it."""

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
        deadline = time.time() + 15.0
        while time.time() < deadline and _pid_alive(pid):
            time.sleep(0.5)
    record["pid_alive_after"] = _pid_alive(pid)
    port_deadline = time.time() + 20.0
    while time.time() < port_deadline and _port_reachable(host, port, timeout=0.5):
        time.sleep(0.5)
    record["port_reachable_after"] = _port_reachable(host, port, timeout=0.5)
    record["teardown_seconds"] = time.time() - started
    if record["pid_alive_after"] or record["port_reachable_after"]:
        raise RuntimeError(
            f"teardown failed: pid {pid} alive={record['pid_alive_after']}, port {port} "
            f"reachable={record['port_reachable_after']} -- refusing to spawn the next session "
            "on top of a resident server (fail-closed)"
        )
    return record


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

    ONE proxy per ARM (its own contact index and its own vector cache), but the
    running spend counters are SEEDED from the durable attempt's own totals at
    construction, so arm 2 and arm 3 never start their ceiling arithmetic from
    zero after arm 1 has already spent 78 calls under the same attempt.

    A TEXT contact meters ZERO speech audio; it is charged
    ``TEXT_CONTACT_AUDIO_SECONDS`` (a documented, negligible positive sentinel)
    only because the store's ``record_usage`` API refuses a non-positive audio
    figure. See ``flight_identity.TEXT_CONTACT_AUDIO_SECONDS``.

    The ``prefix``/``prompt_prefix`` keywords the machinery passes for L2/L3
    are forwarded VERBATIM to the client and folded into the cached payload
    hash, so an arm's cache can never be replayed for a different arm's
    construction."""

    def __init__(
        self,
        inner: EmbeddingClient,
        *,
        arm_id: str,
        store: AttemptStore,
        handle,
        plan: ExecutionPlan,
        vector_log: Path,
        cached: list[dict],
        audio_seconds_by_contact: Mapping[str, float],
        total_contacts: int,
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
        self._index = 0
        self._started_at = time.time()
        self.replayed = 0
        self.flown = 0
        self.failures: list[dict] = []
        self.latency_total = 0.0
        self.latency_by_kind: dict[str, float] = {}
        self.flown_by_kind: Counter = Counter()
        # Seeded from the durable attempt, not from zero (class docstring).
        self.calls_used, self.audio_seconds_used = handle.actual_totals()

    # -- protocol ---------------------------------------------------------

    def verify_media_marker(self) -> Mapping[str, object]:
        props = self._inner.verify_media_marker()
        log(
            f"[{self._arm_id}] media marker verified against the LIVE server's GET /props -- the "
            "env-pinned LLAMA_MEDIA_MARKER matches the server's own media_marker field "
            "(fail-closed check passed; a missing field or a mismatched value would have refused)"
        )
        # Operational only: the server's own self-reported knobs, so the receipt
        # records what embedding mode actually resolved to. Never a result.
        for key in ("n_ctx", "n_batch", "n_ubatch", "pooling_type", "model_path", "build_info"):
            if key in props:
                log(f"  /props {key}: {props[key]!r}")
        return props

    def embed_text(self, *, contact_id: str, text: str, prefix: str = "") -> EmbeddingVector:
        payload_sha256 = hashlib.sha256((prefix + text).encode("utf-8")).hexdigest()
        return self._contact(
            kind="text",
            contact_id=contact_id,
            payload_sha256=payload_sha256,
            audio_seconds=TEXT_CONTACT_AUDIO_SECONDS,
            send=lambda: self._inner.embed_text(contact_id=contact_id, text=text, prefix=prefix),
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
        return self._contact(
            kind="audio",
            contact_id=contact_id,
            payload_sha256=payload_sha256,
            audio_seconds=float(audio_seconds),
            send=lambda: self._inner.embed_audio(
                contact_id=contact_id, audio_bytes=audio_bytes, prompt_prefix=prompt_prefix
            ),
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
            if index % 50 == 0 or index == len(self._cached):
                log(f"[{self._arm_id}] replay {index}/{len(self._cached)} from cache")
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


def _load_inputs(lock, root):
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
    return list(samples), list(labels)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--attempt-id", default=None, help="resume an existing attempt directory")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=EMBEDDING_PORT)
    parser.add_argument("--runtime-root", default="/home/chao")
    args = parser.parse_args()

    run_id = resolve_run_id()
    lock = load_lock(umbrella_lock_path())
    root = data_root()

    # Fail-closed before anything else: the live arm table's own digest.
    assert_binding_config_sha256()
    log(f"binding config sha256 verified against the pinned value: {binding_config_sha256()}")

    values = build_values(REPO)
    cfg_hash = config_hash_of(values)
    split_hash = resolve_split_identity_hash()

    log(f"P-EMB-3L sweep -- exposure row {run_id}")
    log(f"split_identity_hash (pinned, never re-derived): {split_hash}")

    # ---- inputs (model-free) ------------------------------------------------
    samples, labels = _load_inputs(lock, root)
    routing = session_plan()
    arm_order = [arm_id for block in routing for arm_id in block["arm_ids"]]  # type: ignore[union-attr]
    per_arm_contacts = len(samples) + len(labels)
    total_contacts = per_arm_contacts * len(arm_order)
    one_pass_audio = sum(float(s.audio_seconds) for s in samples)
    sweep_audio = one_pass_audio * len(arm_order)
    log(
        f"inputs: {len(samples)} audio samples (expect {ARM_AUDIO_N}), {len(labels)} canonical "
        f"labels (expect {ARM_LABEL_N}); {per_arm_contacts} contacts per arm (expect {ARM_TOTAL_N})"
    )
    log(f"arms in flight order: {arm_order}; sweep total {total_contacts} (expect {EXPECTED_TOTAL_CONTACTS})")
    log(
        f"metered audio: one pass {one_pass_audio:.3f}s x {len(arm_order)} arms = {sweep_audio:.3f}s "
        f"(min {min((s.audio_seconds for s in samples), default=0):.2f}s, "
        f"max {max((s.audio_seconds for s in samples), default=0):.2f}s)"
    )

    planned_calls = int(PLANNED_BUDGETS["model_calls"])  # type: ignore[arg-type]
    planned_audio = int(PLANNED_BUDGETS["speech_audio_seconds"])  # type: ignore[arg-type]
    planned_gpu = float(PLANNED_BUDGETS["gpu_hours"])  # type: ignore[arg-type]
    if total_contacts != EXPECTED_TOTAL_CONTACTS:
        raise RuntimeError(
            f"sweep yields {total_contacts} contacts, the machinery pins {EXPECTED_TOTAL_CONTACTS}"
        )
    if total_contacts != planned_calls:
        raise RuntimeError(
            f"sweep yields {total_contacts} contacts, the launcher's PLANNED_BUDGETS declares "
            f"{planned_calls}"
        )
    if sweep_audio > planned_audio:
        raise RuntimeError(
            f"the sweep meters {sweep_audio:.3f} audio seconds but the plan allows only {planned_audio}"
        )

    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split_hash)
    attempt_id = args.attempt_id or fresh_attempt_id()
    plan = ExecutionPlan(
        run_id=run_id,
        execution_profile=EXECUTION_PROFILE,
        carrier_lock_key=CARRIER_LOCK_KEY,
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
            carrier_lock_key=CARRIER_LOCK_KEY,
            reserved_calls=planned_calls,
            reserved_audio_seconds=float(planned_audio),
        )
        log(f"attempt opened durably: {attempt_id} (state {handle.state()})")

    audio_seconds_by_contact = {s.sample_id: float(s.audio_seconds) for s in samples}
    expected_marker = resolve_expected_media_marker()

    arm_results: dict[str, dict[str, object]] = {}
    session_records: list[dict[str, object]] = []
    contact_records: list[dict[str, object]] = []
    proxies: dict[str, BudgetedCachingProxy] = {}
    summaries: dict[str, object] = {}
    gpu_seconds_total = 0.0
    error: BaseException | None = None
    flight_started_at = time.time()

    try:
        for block in routing:
            session_key = str(block["session_key"])
            argv = session_argv(values, session_key)
            arm_ids = [str(a) for a in block["arm_ids"]]  # type: ignore[union-attr]

            # Arm-level idempotence (see arm_manifest_status): an arm whose
            # registered product is already complete on the data root is
            # CARRIED, never re-flown -- its contacts were durably paid for by
            # an earlier attempt on this same run_id and re-flying them would
            # re-spend registered calls for no new evidence.
            pending_arms = []
            for arm_id in arm_ids:
                complete, info = arm_manifest_status(root, arm_id)
                if complete:
                    log(
                        f"[{arm_id}] CARRIED from an earlier attempt: manifest already complete on "
                        f"the data root ({info['entry_count']} entries, {info['audio_entries']} audio "
                        f"+ {info['text_entries']} text, {info['npy_present']} .npy present) -- "
                        "skipping, zero contacts, zero spend"
                    )
                    arm = ARMS_BY_ID[arm_id]
                    arm_results[arm_id] = {
                        "arm_id": arm_id,
                        "manifest_run_id": arm_run_id(arm_id),
                        "pooling_mode": arm.pooling_mode,
                        "audio_prefix": arm.audio_prefix,
                        "text_prefix": arm.text_prefix,
                        "session_key": session_key,
                        "carried_from_earlier_attempt": True,
                        "n_audio_vectors": info["audio_entries"],
                        "n_text_vectors": info["text_entries"],
                        "n_contacts": info["entry_count"],
                        "embedding_manifest_path": info["manifest_path"],
                        "contacts_flown": 0,
                        "contacts_replayed": 0,
                        "contact_failures": [],
                        "manifest_status": info,
                    }
                else:
                    pending_arms.append(arm_id)

            if not pending_arms:
                log(
                    f"session {session_key!r}: every arm ({arm_ids}) is already complete on the "
                    "data root -- NOT spawning a server for it (no GPU, no contacts)"
                )
                session_records.append(
                    {
                        "session_key": session_key,
                        "pooling_mode": session_key,
                        "arm_ids": arm_ids,
                        "skipped_all_arms_already_complete": True,
                        "spawned": False,
                    }
                )
                continue
            arm_ids = pending_arms

            # Re-checked before EACH spawn, not only once (module docstring).
            assert_no_conflicting_generation_server(
                generation_server_reachable=lambda: _port_reachable(args.host, GENERATION_PORT),
                generation_base_url=f"http://{args.host}:{GENERATION_PORT}",
            )
            log(
                f"coexistence guard: nothing answers on the generation port {GENERATION_PORT} "
                f"-- PASS (before session {session_key!r})"
            )
            if _port_reachable(args.host, args.port):
                raise RuntimeError(
                    f"something is already listening on the embedding port {args.port} before "
                    f"session {session_key!r} -- refusing (fail-closed)"
                )

            session_receipt_path = run_dir / f"{run_id}.session-{session_key}.receipt.json"
            server_log_path = run_dir / f"{run_id}.session-{session_key}.server.log"
            log(
                f"spawning llama-server in EMBEDDING mode (--pooling {session_key}) on port "
                f"{args.port} for arms {arm_ids} (receipt-pinned binary)"
            )
            session_started_at = time.time()
            session = start_session(
                runtime_root=Path(args.runtime_root),
                data_root=root,
                runtime_receipt=runtime_receipt,
                host=args.host,
                port=args.port,
                session_id=f"{run_id}-{attempt_id}-{session_key}",
                extra_argv=argv,
                extra_env=server_env(values),
                receipt_path=session_receipt_path,
                server_log_path=server_log_path,
            )
            spawn_seconds = time.time() - session_started_at
            log(f"session {session_key!r} up: pid={session.pid} port={session.port} (spawn+load {spawn_seconds:.1f}s)")
            log(f"session argv: {' '.join(session.argv)}")
            for entry in session.model_files:
                log(f"  model file: {entry.path} sha256={entry.sha256}")

            client = EmbeddingClient(
                base_url=str(values["base_url"]),
                expected_media_marker=expected_marker,
                timeout_seconds=float(values.get("timeout_seconds", 420.0)),
            )

            session_flown = 0
            session_replayed = 0
            try:
                for arm_id in arm_ids:
                    arm = ARMS_BY_ID[arm_id]
                    vector_log = run_dir / f"vectors-{arm_id}.jsonl"
                    cached = load_cached(vector_log)
                    if cached:
                        log(f"[{arm_id}] resume: {len(cached)} cached vectors will be replayed without core contact")
                    proxy = BudgetedCachingProxy(
                        client,
                        arm_id=arm_id,
                        store=store,
                        handle=handle,
                        plan=plan,
                        vector_log=vector_log,
                        cached=cached,
                        audio_seconds_by_contact=audio_seconds_by_contact,
                        total_contacts=per_arm_contacts,
                    )
                    proxies[arm_id] = proxy
                    arm_started = time.time()
                    log(
                        f"ARM START {arm_id}: pooling={arm.pooling_mode} "
                        f"audio_prefix={arm.audio_prefix!r} text_prefix={arm.text_prefix!r} "
                        f"-> {per_arm_contacts} contacts, ZERO generation"
                    )
                    summary = run_pemb3l_arm_flight(
                        client=proxy,
                        arm=arm,
                        samples=samples,
                        canonical_labels=labels,
                        split_identity_hash=split_hash,
                        data_root=root,
                    )
                    arm_wall = time.time() - arm_started
                    summaries[arm_id] = summary
                    manifest_path = write_pemb3l_arm_manifest(root, summary)
                    log(f"[{arm_id}] embedding manifest written: {manifest_path} (NOT read back by this launcher)")
                    log(
                        f"[{arm_id}] vectors: audio={len(summary.audio_vectors)} "
                        f"text={len(summary.text_vectors)} dims={EMBEDDING_DIM}"
                    )
                    log(f"ARM DONE {arm_id}: {arm_wall:.1f}s, flown={proxy.flown} replayed={proxy.replayed}")
                    session_flown += proxy.flown
                    session_replayed += proxy.replayed
                    arm_results[arm_id] = {
                        "arm_id": arm_id,
                        "manifest_run_id": arm_run_id(arm_id),
                        "pooling_mode": arm.pooling_mode,
                        "audio_prefix": arm.audio_prefix,
                        "text_prefix": arm.text_prefix,
                        "session_key": session_key,
                        "carried_from_earlier_attempt": False,
                        "n_audio_vectors": len(summary.audio_vectors),
                        "n_text_vectors": len(summary.text_vectors),
                        "n_contacts": len(summary.audio_vectors) + len(summary.text_vectors),
                        "embedding_manifest_path": str(manifest_path),
                        "contacts_flown": proxy.flown,
                        "contacts_replayed": proxy.replayed,
                        "contact_failures": list(proxy.failures),
                        "flown_by_kind": dict(proxy.flown_by_kind),
                        "latency_seconds_by_kind": dict(proxy.latency_by_kind),
                        "wall_seconds": arm_wall,
                    }
            finally:
                contact_records.extend(
                    {
                        "session_key": session_key,
                        "contact_id": contact.contact_id,
                        "kind": contact.kind,
                        "started_at": contact.started_at,
                        "latency_seconds": contact.latency_seconds,
                        "dims": contact.dims,
                    }
                    for contact in client.contacts
                )
                session_wall = time.time() - session_started_at
                log(f"tearing down session {session_key!r} (pid {session.pid})")
                teardown = teardown_session(session.pid, args.host, args.port)
                gpu_seconds_total += session_wall
                session_records.append(
                    {
                        "session_key": session_key,
                        "pooling_mode": session_key,
                        "arm_ids": arm_ids,
                        "spawned": True,
                        "session_id": session.session_id,
                        "pid": session.pid,
                        "host": session.host,
                        "port": session.port,
                        "binary_path": session.binary_path,
                        "binary_sha256": session.binary_sha256,
                        "argv": list(session.argv),
                        "model_files": [{"path": m.path, "sha256": m.sha256} for m in session.model_files],
                        "started_at": session.started_at,
                        "spawn_seconds": spawn_seconds,
                        "resident_seconds": session_wall,
                        "contacts_flown": session_flown,
                        "contacts_replayed": session_replayed,
                        "teardown": teardown,
                    }
                )
                log(
                    f"session {session_key!r} torn down: resident {session_wall:.1f}s, "
                    f"{json.dumps(teardown, sort_keys=True, default=str)}"
                )
    except BaseException as exc:  # noqa: BLE001 -- always land evidence
        error = exc
        log(f"FLIGHT ABORTED: {type(exc).__name__}: {exc}")
    wall = time.time() - flight_started_at

    # ---- sweep-total invariant (what run_pemb3l_sweep_flight would assert) ---
    # Counted over the registered PRODUCT on the data root, across every arm,
    # rather than over this attempt's own summaries: the sweep is complete when
    # all three arms' manifests are complete, whether a given arm was flown in
    # THIS attempt or carried from an earlier one on the same run_id.
    sweep_contacts = 0
    arm_status_final: dict[str, object] = {}
    for arm_id in arm_order:
        complete, info = arm_manifest_status(root, arm_id)
        arm_status_final[arm_id] = info
        if complete:
            sweep_contacts += int(info["entry_count"])  # type: ignore[arg-type]
    sweep_total_ok = sweep_contacts == EXPECTED_TOTAL_CONTACTS
    log(
        f"sweep-total invariant (on-disk product across all arms): {sweep_contacts} contacts, "
        f"expected {EXPECTED_TOTAL_CONTACTS} -- {'PASS' if sweep_total_ok else 'FAIL'}"
    )
    for arm_id in arm_order:
        info = arm_status_final[arm_id]  # type: ignore[assignment]
        log(
            f"  {arm_id}: complete={info.get('complete', False)} "  # type: ignore[union-attr]
            f"entries={info.get('entry_count')} npy={info.get('npy_present')}"  # type: ignore[union-attr]
        )
    if error is None and not sweep_total_ok:
        error = RuntimeError(
            f"sweep produced {sweep_contacts} total contacts, expected exactly "
            f"{EXPECTED_TOTAL_CONTACTS} (3 arms x {ARM_TOTAL_N})"
        )

    (run_dir / "contacts.json").write_text(
        json.dumps(
            {"run_id": run_id, "attempt_id": attempt_id, "contacts": contact_records},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
        newline="\n",
    )

    try:
        handle.record_gpu_seconds(gpu_seconds_total)
    except Exception as exc:  # noqa: BLE001 -- never mask the flight's own outcome
        log(f"record_gpu_seconds failed (non-fatal): {type(exc).__name__}: {exc}")
    if error is None:
        handle.mark_finalized()
        log(f"attempt {attempt_id} FINALIZED")
    else:
        handle.mark_aborted(f"P-EMB-3L sweep aborted: {type(error).__name__}: {error}")
        log(f"attempt {attempt_id} ABORTED")

    actual_calls, actual_audio = handle.actual_totals()
    log(f"durable spend this attempt: calls={actual_calls}, audio_seconds={actual_audio:.3f}")
    flown = sum(p.flown for p in proxies.values())
    replayed = sum(p.replayed for p in proxies.values())
    failures = [f for p in proxies.values() for f in p.failures]
    by_kind: Counter = Counter()
    latency_by_kind: dict[str, float] = {}
    for proxy in proxies.values():
        by_kind.update(proxy.flown_by_kind)
        for kind, total in proxy.latency_by_kind.items():
            latency_by_kind[kind] = latency_by_kind.get(kind, 0.0) + total
    log(f"contacts: flown={flown} replayed={replayed} failures={len(failures)}")
    log(f"flown by kind: {json.dumps(dict(by_kind), sort_keys=True)}")
    log(
        "mean latency by kind: "
        + json.dumps(
            {kind: round(total / max(by_kind[kind], 1), 3) for kind, total in sorted(latency_by_kind.items())},
            sort_keys=True,
        )
    )
    log(
        f"wall: flight {wall/60:.1f} min; GPU-occupied (sum of both sessions) "
        f"{gpu_seconds_total/60:.1f} min ({gpu_seconds_total/3600:.3f} h) vs plan ceiling {planned_gpu} h"
    )

    flight_receipt = {
        "run_id": run_id,
        "probe": "P-EMB-3L",
        "attempt_id": attempt_id,
        "status": "COMPLETED" if error is None else "ABORTED",
        "error": None if error is None else f"{type(error).__name__}: {error}",
        "config_hash": cfg_hash,
        "protocol_hash": phash,
        "split_identity_hash": split_hash,
        "binding_config_sha256": binding_config_sha256(),
        "umbrella_lock_sha256": lock_sha256,
        "preregistration": PREREGISTRATION_RELPATH,
        "tier": "embedding (encode+pool, ZERO generation, zero sampling seam)",
        "embedding_dim": EMBEDDING_DIM,
        "arm_order": arm_order,
        "arms": arm_results,
        "sessions": session_records,
        "n_audio_contacts_expected_per_arm": ARM_AUDIO_N,
        "n_text_contacts_expected_per_arm": ARM_LABEL_N,
        "n_contacts_expected_per_arm": ARM_TOTAL_N,
        "n_contacts_planned": total_contacts,
        "n_contacts_produced": sweep_contacts,
        "sweep_total_invariant_pass": sweep_total_ok,
        "arm_manifest_status_final": arm_status_final,
        "arms_flown_this_attempt": sorted(summaries),
        "arms_carried_from_earlier_attempts": sorted(
            arm_id for arm_id, a in arm_results.items() if a.get("carried_from_earlier_attempt")
        ),
        "metered_audio_seconds_expected_one_pass": round(one_pass_audio, 3),
        "metered_audio_seconds_expected_sweep": round(sweep_audio, 3),
        "text_contact_audio_seconds_sentinel": TEXT_CONTACT_AUDIO_SECONDS,
        "planned_budgets": {
            "model_calls": planned_calls,
            "speech_audio_seconds": planned_audio,
            "gpu_hours": planned_gpu,
        },
        "registered_ceilings": dict(REGISTERED_CEILINGS),
        "durable_actual": {"calls": actual_calls, "audio_seconds": actual_audio},
        "prior_durable_spend_before_this_attempt": {"calls": prior_calls, "audio_seconds": prior_audio},
        "wall_seconds": wall,
        "gpu_occupied_seconds_this_attempt": gpu_seconds_total,
        "gpu_hours_this_attempt": gpu_seconds_total / 3600.0,
        "contacts_flown_this_attempt": flown,
        "contacts_replayed_from_cache": replayed,
        "contacts_flown_by_kind": dict(by_kind),
        "latency_seconds_by_kind": latency_by_kind,
        "contact_failures": failures,
        "gate_runtime_diagnostics": json.loads(json.dumps(gate_diagnostics, sort_keys=True, default=str)),
    }
    (run_dir / "flight-receipt.json").write_text(
        json.dumps(flight_receipt, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    log(f"flight receipt: {run_dir / 'flight-receipt.json'}")
    return 0 if error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
