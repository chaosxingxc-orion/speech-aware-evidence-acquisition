#!/usr/bin/env python3
"""Owner decision 160's CONDITION, proven model-free: may COMP-1 and G5 share one in-chain A/A?

Decision 160 (2026-09-27): COMP-1 and G5 fly in ONE campaign with ONE shared in-chain A/A --
COMP-1's ``SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`` -- on the condition, checked before the flip,
that the two registered A/A cells (COMP-1's and G5's ``SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1``) have
byte-identical prepared first-phase supply digests and byte-identical composed request bytes. If
they do not, the two families fly separately as registered.

Three proofs, each model-free (zero model, server, tokenizer, encoder or scorer contacts):

1. **Composed config.** Both A/A cells are composed from their committed fragments and every
   leaf is flattened (dicts by key, lists by index). Every differing leaf is classified by
   :func:`classify_leaf`: ``bookkeeping`` (identity, prose, budget -- read by the gate, the
   ledger and the receipts, never by the request composer), ``supply-recall-width`` (the
   first-phase supply's recall ``k``: read only by the prepared supply's recall and therefore
   output-neutral exactly when proof 2 finds equal output digests), or ``unclassified`` (treated
   as request-affecting: the verdict fails).
2. **Prepared supply.** ``core.flight.cli prepare-supply`` is run for each A/A into a scratch
   directory (never the data root's ``prepared/``), and the two artifacts' ``output_sha256`` --
   ``core.preparation.digest`` over the ``{facets, values}`` payload, the digest the flip's
   byte-identity check reads -- must be equal to each other and to the sealed PLAN lock's
   ``ba5e1faa...``.
3. **Request bytes.** Each A/A's REAL dispatch (``FlightRuntime._dispatch_phase_program`` with
   ``model_free_check=True``: the composed fragments, the adapter and split, the phase material,
   the live first-phase supply, the knowledge stores, the openJiuwen native role episode, the
   ``FrozenCoreClient`` and its payload allowlist) runs against the REAL ``llama-server``
   transport of the composed model fragment, whose POST is replaced by a fake server that records
   the exact body bytes and answers a canned, role-appropriate, deterministic completion. The
   session receipt is a fake bound to the fragment's own decoder identity; the transport's
   liveness probe is disabled for this process only, because no request is ever sent. Every
   contact is keyed by ``(sample_id, contact_id)`` (``<policy>:<role>:<visit>:<sample>``) and two
   byte strings are compared per key: the canonical request payload that crosses the client's
   transport seam, and the HTTP body the real transport would POST. The canned Planner answer is
   ``REVISE`` on its first visit for about half of the rows (a stable hash of the sample id), so
   the revision loop -- Solver, Reviewer and Planner second visits -- is exercised as well.

Nothing here writes to ``prepared/``, ``locks/`` or any run directory: the scratch supplies live
under ``--scratch``, and the dispatch's attempt is a ``WIRECHECK-`` scratch attempt under the data
root's ``wire-check/`` tree, aborted before this script returns (the same place and form every
``FlightRuntime.wire_check`` uses).

Exit 0 with verdict ``IDENTICAL`` when all three proofs hold; exit 3 with verdict ``DIFFERENT``
otherwise (the proof JSON names every difference). Usage, in WSL from the worktree::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=$DATA \\
    python -B scripts/flights/comp1/comp1_g5_shared_aa_proof.py \\
      --repo-root $REPO --data-root $DATA --lock-path $LOCK [--rows N] [--output PATH]
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

PROOF_SCHEMA = "saea-comp1-g5-shared-aa-proof-v1"
PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1"
DEFAULT_OUTPUT = PACKAGE + "/shared-aa-proof-v1.json"

#: The two registered A/A cells decision 160 compares (experiment id == cell id for both).
CELLS: dict[str, str] = {
    "comp1_aa": "slurp-native-stage3-comp1-aa-fold-a-v1",
    "g5_aa": "slurp-native-stage3-g5-aa-fold-a-v1",
}

#: The sealed PLAN lock's prepared first-phase supply output digest (both packages name it).
SEALED_PLAN_SUPPLY_OUTPUT_SHA256 = (
    "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
)

#: The first-phase supply's recall width -- the ONE non-bookkeeping leaf the two A/As are
#: registered to differ in (COMP-1's A/A carries the composed arm's k 60, G5's the lock's k 8).
SUPPLY_RECALL_WIDTH_LEAF = "knowledge_stores.intent-boundaries.phase_supply.perception.k"

#: Leaves (exact, or a prefix ending in ".") that no request composer reads. Each entry names
#: what the leaf is for, so a reader can check the claim against the code that reads it.
BOOKKEEPING_LEAVES: tuple[tuple[str, str], ...] = (
    ("cells.", "the experiment fragment's cell list: run, attempt and cell ids, the baseline "
               "fragment NAME, readiness state, reason and requirements -- read by the campaign "
               "loader, the readiness gate and the re-pin tool, never by request composition"),
    ("experiment_id", "the experiment's registered id (ledger and receipts)"),
    ("fragment_kind", "the fragment's self-description tag"),
    ("purpose", "prose"),
    ("what_this_is", "prose"),
    ("stage3_algorithm.", "the Stage-3 algorithm label and its prose (the label gate reads it)"),
    ("generation_budget.", "the run-cumulative generation budget prose and target (the ledger "
                           "and the batch inspector read it; the request composer never does)"),
    ("family_budget.", "the family caps (the decision receipt and the gate read them)"),
    ("native_contact_fit.run_id", "the cell's own FIT spend identity (a run id)"),
    ("native_contact_fit.attempt_id", "the cell's own FIT spend identity (an attempt id)"),
    ("date", "the registration date"),
    ("failure_policy", "prose"),
)


#: Three legal SLURP intents (members of the Perception schema's intent enum) the canned answers
#: name. Fixed, so both A/As receive the same completions byte for byte.
CANNED_INTENTS: tuple[str, ...] = ("weather_query", "alarm_set", "play_music")


# --------------------------------------------------------------------------------------------
# pure helpers (unit-tested)
# --------------------------------------------------------------------------------------------


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Every leaf of a JSON value, keyed by a dotted path (lists by ``[index]``)."""

    if isinstance(value, Mapping):
        if not value:
            return {prefix: {}}
        out: dict[str, Any] = {}
        for key in value:
            out.update(flatten(value[key], f"{prefix}.{key}" if prefix else str(key)))
        return out
    if isinstance(value, list):
        if not value:
            return {prefix: []}
        out = {}
        for index, item in enumerate(value):
            out.update(flatten(item, f"{prefix}[{index}]"))
        return out
    return {prefix: value}


def classify_leaf(leaf: str) -> tuple[str, str]:
    """``(class, reason)`` for one differing composed-config leaf."""

    if leaf == SUPPLY_RECALL_WIDTH_LEAF:
        return (
            "supply-recall-width",
            "the first-phase supply's recall width: read only by the prepared supply's recall "
            "(rails.phase_supply); it reaches a request only through the supply's OUTPUT, so it "
            "is output-neutral exactly when the two prepared supply output digests are equal",
        )
    normalized = leaf.replace("[", ".[")
    for prefix, reason in BOOKKEEPING_LEAVES:
        if prefix.endswith("."):
            if normalized.startswith(prefix) or leaf.startswith(prefix.rstrip(".") + "["):
                return "bookkeeping", reason
        elif leaf == prefix:
            return "bookkeeping", reason
    return "unclassified", "no rule names this leaf: treated as request-affecting"


def config_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every differing leaf of two composed configs, classified."""

    flat_left, flat_right = flatten(left), flatten(right)
    rows: list[dict[str, Any]] = []
    for leaf in sorted(set(flat_left) | set(flat_right)):
        a = flat_left.get(leaf, "<absent>")
        b = flat_right.get(leaf, "<absent>")
        if a == b:
            continue
        klass, reason = classify_leaf(leaf)
        rows.append(
            {
                "leaf": leaf,
                "comp1_aa": a,
                "g5_aa": b,
                "class": klass,
                "request_affecting": klass == "unclassified",
                "reason": reason,
            }
        )
    return rows


def classify_supply_input(leaf: str) -> str:
    """The class of one differing prepared-supply artifact INPUT (identity, not output)."""

    if leaf == "sources.supply_spec.k":
        return "supply-recall-width"
    if leaf == "config_sha256":
        return "supply-config-identity-hash (covers the recall width k)"
    return "unclassified"


def contact_key(payload: Mapping[str, Any]) -> str:
    """``<sample_id>|<contact_id>`` of one request payload (the last history turn's contact)."""

    history = payload.get("history")
    contact = history[-1].get("contact_id") if isinstance(history, list) and history else None
    if not isinstance(contact, str) or not contact:
        raise ValueError("request payload carries no contact_id on its last history turn")
    return f"{payload.get('sample_id')}|{contact}"


def role_of(contact_id: str) -> tuple[str, int]:
    """``(role, visit)`` from ``<policy>:<role>:<visit>:<sample>``."""

    parts = contact_id.split(":")
    if len(parts) < 4:
        raise ValueError(f"contact id {contact_id!r} is not <policy>:<role>:<visit>:<sample>")
    return parts[1], int(parts[2])


def revises_first(sample_id: str) -> bool:
    """The canned Planner answers REVISE on its first visit for about half of the rows."""

    return hashlib.sha256(sample_id.encode("utf-8")).digest()[-1] % 2 == 1


def canned_answer(role: str, visit: int, sample_id: str, intents: Iterable[str]) -> str:
    """One deterministic, schema-valid completion per role (identical for both A/As)."""

    intents = list(intents)
    if role == "perception":
        return json.dumps(
            {
                "candidates": [
                    {
                        "intent_id": intent,
                        "distinction": "Proof canned alternative.",
                        "evidence_refs": [],
                        "unresolved_fields": [],
                    }
                    for intent in intents[:3]
                ]
            },
            separators=(",", ":"),
        )
    if role == "solver":
        scenario, _, action = intents[0].partition("_")
        return json.dumps(
            {"scenario": scenario, "action": action, "entities": []}, separators=(",", ":")
        )
    if role == "reviewer":
        return "The draft names one legal intent and no unsupported entity."
    if role == "planner":
        return "REVISE" if visit == 0 and revises_first(sample_id) else "ACCEPT"
    raise ValueError(f"unexpected role {role!r}")


#: The one payload field whose value is derived from the RUN ID: every history turn's
#: ``source_query_state_sha256`` is ``rails.knowledge.QueryState.content_hash()``, and the
#: QueryState's ``query_id`` is ``<plan run id>:<sample id>:step<n>``. It is custody (which
#: sealed state a turn came from), it never reaches the POST body, and it differs between ANY
#: two runs -- including two runs of the same cell.
RUN_ID_DERIVED_PAYLOAD_FIELD = "source_query_state_sha256"


def run_id_normalized_payload(payload: Any) -> Any:
    """The payload with every :data:`RUN_ID_DERIVED_PAYLOAD_FIELD` value blanked."""

    if isinstance(payload, Mapping):
        return {
            key: ("<run-id-derived>" if key == RUN_ID_DERIVED_PAYLOAD_FIELD else
                  run_id_normalized_payload(value))
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [run_id_normalized_payload(item) for item in payload]
    return payload


def compare_captures(
    left: Mapping[str, Mapping[str, str]], right: Mapping[str, Mapping[str, str]]
) -> dict[str, Any]:
    """Compare two ``{key: {"payload_sha256", "normalized_payload_sha256", "body_sha256"}}``
    captures key by key."""

    only_left = sorted(set(left) - set(right))
    only_right = sorted(set(right) - set(left))
    keys_equal = not only_left and not only_right
    diffs: dict[str, list[str]] = {
        "payload_sha256": [], "normalized_payload_sha256": [], "body_sha256": [],
    }
    for key in sorted(set(left) & set(right)):
        for field in diffs:
            if left[key][field] != right[key][field]:
                diffs[field].append(key)
    return {
        "contacts_comp1_aa": len(left),
        "contacts_g5_aa": len(right),
        "keys_equal": keys_equal,
        "only_in_comp1_aa": only_left[:20],
        "only_in_g5_aa": only_right[:20],
        "payload_bytes_identical": keys_equal and not diffs["payload_sha256"],
        "run_id_normalized_payload_bytes_identical": keys_equal
        and not diffs["normalized_payload_sha256"],
        "post_body_bytes_identical": keys_equal and not diffs["body_sha256"],
        "payload_mismatches": len(diffs["payload_sha256"]),
        "run_id_normalized_payload_mismatches": len(diffs["normalized_payload_sha256"]),
        "post_body_mismatches": len(diffs["body_sha256"]),
        "first_mismatches": (
            diffs["normalized_payload_sha256"] + diffs["body_sha256"] + diffs["payload_sha256"]
        )[:20],
    }


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


# --------------------------------------------------------------------------------------------
# the three proofs (need the data root; run in WSL)
# --------------------------------------------------------------------------------------------


def _cell(repo: Path, experiment: str):
    from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells

    (cell,) = load_campaign_cells(repo, experiment)
    return cell


def _composed(repo: Path, experiment: str):
    from speech_aware_evidence_acquisition.core.config import compose, protocol_hash

    cell = _cell(repo, experiment)
    document = cell.document
    composed = compose(
        repo, document["model_fragment"], document["dataset_fragment"],
        document["baseline_fragment"], experiment,
    )
    fragment = json.loads(
        (repo / "configs" / "experiment" / f"{experiment}.json").read_text(encoding="utf-8")
    )
    split = fragment["population"]["split_identity_hash"]
    return cell, composed, {
        "experiment": experiment,
        "run_id": cell.run_id,
        "baseline_fragment": document["baseline_fragment"],
        "composed_config_hash": composed.config_hash,
        "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
    }


def prove_supply(repo: Path, data: Path, lock: Path, scratch: Path) -> dict[str, Any]:
    """``core.flight.cli prepare-supply`` for both A/As into ``scratch``; compare digests."""

    out: dict[str, Any] = {}
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    artifacts = {}
    for name, experiment in CELLS.items():
        path = scratch / name / "phase-supply-v1.json"
        if path.exists():
            raise SystemExit(f"scratch supply {path} already exists; use a fresh --scratch")
        started = time.time()
        subprocess.run(
            [
                sys.executable, "-B", "-m", "speech_aware_evidence_acquisition.core.flight.cli",
                "prepare-supply", "--repo-root", str(repo), "--data-root", str(data),
                "--runtime-root", str(Path.home()), "--lock-path", str(lock),
                "--experiment", experiment, "--cell", experiment, "--output", str(path),
                "--workers", "4",
            ],
            check=True, env=env, cwd=str(repo), stdout=subprocess.DEVNULL,
        )
        raw = path.read_bytes()
        artifact = json.loads(raw)
        values = {
            sample: ids
            for per_phase in artifact["output"]["values"].values()
            for sample, ids in per_phase.items()
        }
        artifacts[name] = artifact
        out[name] = {
            "command": f"core.flight.cli prepare-supply --experiment {experiment} --cell {experiment} --output <scratch>/{name}/phase-supply-v1.json",
            "output_sha256": artifact["output_sha256"],
            "file_sha256": _sha(raw),
            "rows_seeded": sum(1 for ids in values.values() if ids),
            "selected_value_ids": sum(len(ids) for ids in values.values()),
            "seconds": round(time.time() - started, 1),
        }
    inputs_diff = [
        {"leaf": leaf, "comp1_aa": a, "g5_aa": b, "class": classify_supply_input(leaf)}
        for leaf, a, b in _diff_pairs(artifacts["comp1_aa"]["inputs"], artifacts["g5_aa"]["inputs"])
    ]
    equal = out["comp1_aa"]["output_sha256"] == out["g5_aa"]["output_sha256"]
    out.update(
        {
            "sealed_plan_output_sha256": SEALED_PLAN_SUPPLY_OUTPUT_SHA256,
            "output_digests_equal": equal,
            "both_equal_sealed_plan": equal
            and out["comp1_aa"]["output_sha256"] == SEALED_PLAN_SUPPLY_OUTPUT_SHA256,
            "artifact_input_differences": inputs_diff,
            "note": (
                "file_sha256 differs whenever an artifact INPUT differs (the recall width k is an "
                "input); output_sha256 is core.preparation.digest over the {facets, values} "
                "payload -- the same value ids in the same order on every row -- and is what the "
                "flip's byte-identity check and the request composer consume"
            ),
        }
    )
    return out


def _diff_pairs(left: Any, right: Any):
    flat_left, flat_right = flatten(left), flatten(right)
    for leaf in sorted(set(flat_left) | set(flat_right)):
        a, b = flat_left.get(leaf, "<absent>"), flat_right.get(leaf, "<absent>")
        if a != b:
            yield leaf, (a if len(json.dumps(a, default=str)) < 300 else "<long>"), (
                b if len(json.dumps(b, default=str)) < 300 else "<long>"
            )


def capture_requests(
    repo: Path, data: Path, lock: Path, experiment: str, rows: int | None, *,
    keep_raw: bool = False, serial: bool = True, common_run: tuple[str, int] | None = None,
):
    """Drive one A/A's real dispatch against the real transport with a fake POST.

    ``common_run`` -- ``(label, stamp)`` -- flies the dispatch under ONE scratch run id shared by
    both cells (``WIRECHECK-<label>-<stamp>``, each cell under its own attempt id), so the only
    run-id-derived payload field coincides; ``None`` uses the cell's own run id, as a flight does.
    """

    from speech_aware_evidence_acquisition.core.flight import runtime as flight_runtime
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
    from speech_aware_evidence_acquisition.core.model import transport as transport_module
    from speech_aware_evidence_acquisition.core.session.receipt import (
        SESSION_RECEIPT_SCHEMA_V2,
        ModelFileRef,
        SessionReceipt,
    )

    cell = _cell(repo, experiment)
    document = cell.document
    runtime = build_flight_runtime(
        repo, data, model=document["model_fragment"], dataset=document["dataset_fragment"],
        baseline=document["baseline_fragment"], experiment=experiment, run_id=cell.run_id,
        attempt_id=cell.attempt_id, runtime_root=Path.home(), lock_path=lock,
    )
    values, carrier, _split, identity = runtime._prepare()
    intents = CANNED_INTENTS
    if rows is not None:
        # The E10 resume seam narrows what is DISPATCHED to the first ``rows`` samples while the
        # first-phase supply keeps its identity roster (runtime._resume_filtered_binding).
        runtime._resume = object()
        runtime._resume_flown_sample_ids = tuple(s.sample_id for s in runtime._samples[:rows])
    flown = rows if rows is not None else len(runtime._samples)
    if serial:
        # One slot, one row in flight: the per-process request counter (request_id and the
        # rails-message/<request_id>/ provenance relpaths) and the slot id are then assigned in
        # roster order in BOTH runs. Under the production np4 geometry they are assigned by
        # arrival order, which differs between two dispatches of the SAME cell.
        runtime._continuous_phase_runner = functools.partial(
            runtime._continuous_phase_runner, slot_count=1, queue_depth=1
        )

    # A fake session bound to the fragment's own decoder identity; no process, no socket.
    transport_module.assert_session_alive = lambda *_args, **_kwargs: None
    session = SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA_V2, study="speech-aware-evidence-acquisition",
        session_id="comp1-g5-shared-aa-proof-fake-session", binary_path="/nonexistent/llama-server",
        binary_sha256="0" * 64, argv=("/nonexistent/llama-server",), pid=0, host="127.0.0.1",
        port=8080,
        model_files=(ModelFileRef(
            path="models/decoder.gguf",
            sha256=str(values["server_env"]["LLAMA_SPEECH_DECODER_SHA256"]),
        ),),
        started_at="2026-09-27T00:00:00+00:00", startup_stdout_sha256="0" * 64, role="inference",
    )
    local = threading.local()
    guard = threading.Lock()
    captured: dict[str, dict[str, str]] = {}

    def fake_post(_url: str, body: bytes) -> bytes:
        key = local.key
        with guard:
            if "body_sha256" in captured[key]:
                raise RuntimeError(f"contact {key} posted twice")
            captured[key]["body_sha256"] = _sha(body)
            if keep_raw:
                captured[key]["body"] = body.decode("utf-8")
        return json.dumps(
            {
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": local.answer}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        ).encode("utf-8")

    real = transport_module.TRANSPORTS.resolve(str(values["transport"]))(
        values, data, session=session, runtime_receipt={}, runtime_root=Path.home(),
    )
    real._post = fake_post
    runtime._transport = real

    def recorder(request_bytes: bytes) -> bytes:
        payload = json.loads(request_bytes)
        key = contact_key(payload)
        role, visit = role_of(key.split("|", 1)[1])
        with guard:
            if key in captured:
                raise RuntimeError(f"contact {key} requested twice")
            captured[key] = {
                "payload_sha256": _sha(request_bytes),
                "normalized_payload_sha256": _sha(json.dumps(
                    run_id_normalized_payload(payload), sort_keys=True, separators=(",", ":"),
                ).encode("utf-8")),
                "role": role,
            }
            if keep_raw:
                captured[key]["payload"] = request_bytes.decode("utf-8")
        local.key = key
        local.answer = canned_answer(role, visit, str(payload.get("sample_id")), intents)
        return real(request_bytes)

    arm = runtime._arm()
    policy = str(values["policy"])
    declared = runtime._composed.values["execution_plan"]
    if common_run is None:
        stamp = int(time.time() * 1000)
        wire_run_id = f"{flight_runtime.WIRE_CHECK_RUN_ID_PREFIX}{runtime._run_id}-{stamp:d}"
        wire_attempt_id = f"attempt-wire-check-{stamp:d}"
    else:
        label, stamp = common_run
        wire_run_id = f"{flight_runtime.WIRE_CHECK_RUN_ID_PREFIX}{label}-{stamp:d}"
        wire_attempt_id = f"attempt-wire-check-{stamp:d}-{runtime._run_id}"
    plan = flight_runtime.ExecutionPlan(
        run_id=wire_run_id, execution_profile=declared["execution_profile"],
        carrier_lock_key=carrier, split_role=declared["split_role"],
        split_identity_hash=identity, planned_model_calls=flown * 11 * 2,
        planned_gpu_hours=declared["planned_gpu_hours"],
        planned_speech_audio_seconds=declared["planned_speech_audio_seconds"],
        protocol_hash=flight_runtime.compute_protocol_hash(
            runtime._composed.config_hash, arm, identity
        ),
        attempt_id=wire_attempt_id,
    ).validate()
    run_dir = data / "wire-check" / wire_run_id / wire_attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    runtime._plan = plan
    runtime._prepare_native_phase_runtime(policy)
    client = runtime._client_factory(
        **runtime.frozen_core_client_kwargs(
            plan=plan, gate=flight_runtime.WireCheckGate(), transport=recorder, run_dir=run_dir,
        )
    )
    runtime._client = client
    runtime._wire_check_active = True
    started = time.time()
    try:
        _rows, contact_count, _kind, _dispatch, _phases = runtime._dispatch_phase_program(
            client, plan, policy, model_free_check=True
        )
    finally:
        runtime._wire_check_active = False
        try:
            client.close()
        finally:
            runtime._abort_attempt(
                data, wire_run_id, wire_attempt_id,
                reason="comp1-g5 shared A/A proof: fake server, no model was ever reached",
            )
    missing_body = sorted(key for key, row in captured.items() if "body_sha256" not in row)
    if missing_body:
        raise RuntimeError(f"{len(missing_body)} contact(s) never reached the fake POST")
    roles: dict[str, int] = {}
    for row in captured.values():
        roles[row["role"]] = roles.get(row["role"], 0) + 1
    return captured, {
        "rows_dispatched": flown,
        "contacts": contact_count,
        "contacts_by_role": dict(sorted(roles.items())),
        "rows_revised_by_canned_planner": sum(
            1 for s in runtime._samples[:flown] if revises_first(s.sample_id)
        ),
        "wire_check_run_id": wire_run_id,
        "seconds": round(time.time() - started, 1),
    }


def _leaf_classes(left: str, right: str) -> list[str]:
    import re

    a, b = flatten(json.loads(left)), flatten(json.loads(right))
    return sorted({re.sub(r"\[\d+\]", "[]", leaf) for leaf in set(a) | set(b)
                   if a.get(leaf) != b.get(leaf)})


def self_control_reading(first: Mapping[str, Any], second: Mapping[str, Any], rows: int) -> dict:
    """Which request fields differ between two concurrent dispatches of the SAME cell."""

    payload_fields: dict[str, int] = {}
    body_fields: dict[str, int] = {}
    for key in sorted(set(first) & set(second)):
        for field in _leaf_classes(first[key]["payload"], second[key]["payload"]):
            payload_fields[field] = payload_fields.get(field, 0) + 1
        for field in _leaf_classes(first[key]["body"], second[key]["body"]):
            body_fields[field] = body_fields.get(field, 0) + 1
    return {
        "what": (
            "cell COMP-1's A/A dispatched twice, both at the production concurrency (np4 "
            "geometry: four slots, queue depth 16), each under its own scratch run id; the "
            "number of contacts on which each field differs between the two dispatches of the "
            "SAME cell. These fields are assigned by arrival order (request_id, the "
            "rails-message/<request_id>/ provenance relpaths, the slot id) or derived from the "
            "run id (source_query_state_sha256), which is why the A/A comparison dispatches "
            "serially and reads the run-id-derived field separately"
        ),
        "rows": rows,
        "contacts": len(set(first) & set(second)),
        "keys_equal": set(first) == set(second),
        "payload_fields_differing": dict(sorted(payload_fields.items())),
        "post_body_fields_differing": dict(sorted(body_fields.items())),
    }


#: 64-hex values the proof may quote IN FULL: the prepared-supply OUTPUT digests (the claim
#: itself; core.flight.repin never maps an output digest) and the study commit. Every other
#: 64-hex value -- a composed config hash, a protocol hash, an artifact pin -- is quoted by a
#: 16-hex prefix, because core.flight.repin rewrites every JSON file of a readiness package from
#: its old identity hashes to its new ones at the flip and then refuses any old hash left under
#: docs/: quoted in full, a record of what was computed at ``study_commit`` would be silently
#: rewritten or would block the flip.
FULL_HASH_KEYS = frozenset({"output_sha256", "sealed_plan_output_sha256", "study_commit"})


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str) and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def quote_hashes_by_prefix(node: Any, key: str | None = None) -> Any:
    """Every 64-hex string outside :data:`FULL_HASH_KEYS` as ``sha256-prefix16:<16 hex>``."""

    if isinstance(node, Mapping):
        return {name: quote_hashes_by_prefix(value, name) for name, value in node.items()}
    if isinstance(node, list):
        return [quote_hashes_by_prefix(item, key) for item in node]
    if _is_sha256(node) and key not in FULL_HASH_KEYS:
        return "sha256-prefix16:" + node[:16]
    return node


def _launch_worker(repo: Path, args, *, cell: str, out: Path, rows: int | None,
                   common: tuple[str, int] | None, serial: bool, raw: bool):
    command = [
        sys.executable, "-B", str(Path(__file__).resolve()),
        "--repo-root", str(repo), "--data-root", str(args.data_root),
        "--lock-path", str(args.lock_path), "--worker-cell", cell, "--worker-out", str(out),
    ]
    if rows is not None:
        command += ["--rows", str(rows)]
    if common is not None:
        command += ["--worker-common", f"{common[0]}:{common[1]}"]
    if not serial:
        command.append("--worker-concurrent")
    if raw:
        command.append("--worker-raw")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    log = out.with_suffix(".log").open("w", encoding="utf-8")
    return subprocess.Popen(command, env=env, cwd=str(repo), stdout=log, stderr=subprocess.STDOUT)


def _run_workers(jobs: list[tuple[str, Any]], parallel: int) -> None:
    """Run ``(label, launcher)`` jobs at most ``parallel`` at a time; refuse on any failure."""

    pending, running = list(jobs), []
    while pending or running:
        while pending and len(running) < parallel:
            label, launch = pending.pop(0)
            running.append((label, launch()))
        time.sleep(5)
        still, failed = [], None
        for label, process in running:
            code = process.poll()
            if code is None:
                still.append((label, process))
            elif code != 0 and failed is None:
                failed = (label, code)
        if failed is not None:
            for _label, process in still:
                process.send_signal(2)  # SIGINT: each worker aborts its own scratch attempt
            for _label, process in still:
                process.wait()
            raise SystemExit(f"capture worker {failed[0]} exited {failed[1]}; see its .log")
        running = still


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--lock-path", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=None,
                        help="dispatch only the first N rows (default: the whole roster)")
    parser.add_argument("--self-control-rows", type=int, default=12,
                        help="rows of the concurrent self-control (0 skips it)")
    parser.add_argument("--parallel", type=int, default=4,
                        help="capture worker processes at once (the owner's campaign-time CPU "
                             "budget is 8 workers)")
    parser.add_argument("--scratch", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--worker-cell", help=argparse.SUPPRESS)
    parser.add_argument("--worker-out", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-common", help=argparse.SUPPRESS)
    parser.add_argument("--worker-concurrent", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-raw", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    import speech_aware_evidence_acquisition as package

    if not str(Path(package.__file__).resolve()).startswith(str(repo)):
        raise SystemExit(f"imported package {package.__file__} is not under {repo}")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if args.worker_cell:
        common = None
        if args.worker_common:
            label, _, stamp = args.worker_common.rpartition(":")
            common = (label, int(stamp))
        captured, receipt = capture_requests(
            repo, args.data_root, args.lock_path, CELLS[args.worker_cell], args.rows,
            keep_raw=args.worker_raw, serial=not args.worker_concurrent, common_run=common,
        )
        args.worker_out.write_text(
            json.dumps({"captured": captured, "receipt": receipt}), encoding="utf-8"
        )
        return 0
    scratch = args.scratch or Path(f"/tmp/comp1g5-shared-aa-proof-{int(time.time())}")
    scratch.mkdir(parents=True, exist_ok=True)

    cells, composed = {}, {}
    for name, experiment in CELLS.items():
        _cell_obj, composed[name], cells[name] = _composed(repo, experiment)
    diff = config_diff(composed["comp1_aa"].values, composed["g5_aa"].values)
    unclassified = [row["leaf"] for row in diff if row["class"] == "unclassified"]

    supply = prove_supply(repo, args.data_root, args.lock_path, scratch)

    # Mode A (decisive): both cells under ONE scratch run id -- every payload byte must match.
    # Mode B (flight-shaped): each cell under its own run id -- the POST bodies must match and the
    # payloads may differ ONLY in the run-id-derived custody field. Each capture is its own
    # process (the dispatch is CPU-bound); the self-control dispatches COMP-1's A/A twice at the
    # production concurrency.
    common_run = ("COMP1-G5-SHARED-AA-PROOF", int(time.time() * 1000))
    jobs, outputs = [], {}
    for mode, common in (("common_run_id", common_run), ("own_run_ids", None)):
        for name in CELLS:
            out = scratch / f"capture-{mode}-{name}.json"
            outputs[(mode, name)] = out
            jobs.append((f"{mode}/{name}", functools.partial(
                _launch_worker, repo, args, cell=name, out=out, rows=args.rows, common=common,
                serial=True, raw=False,
            )))
    if args.self_control_rows:
        for index in (1, 2):
            out = scratch / f"capture-self-control-{index}.json"
            outputs[("self_control", index)] = out
            jobs.append((f"self-control/{index}", functools.partial(
                _launch_worker, repo, args, cell="comp1_aa", out=out,
                rows=args.self_control_rows, common=None, serial=False, raw=True,
            )))
    _run_workers(jobs, args.parallel)

    def _load(key):
        return json.loads(outputs[key].read_text(encoding="utf-8"))

    modes: dict[str, dict[str, Any]] = {}
    for mode in ("common_run_id", "own_run_ids"):
        loaded = {name: _load((mode, name)) for name in CELLS}
        modes[mode] = {
            "comp1_aa": loaded["comp1_aa"]["receipt"],
            "g5_aa": loaded["g5_aa"]["receipt"],
            "comparison": compare_captures(
                loaded["comp1_aa"]["captured"], loaded["g5_aa"]["captured"]
            ),
        }
    self_control = (
        self_control_reading(
            _load(("self_control", 1))["captured"], _load(("self_control", 2))["captured"],
            args.self_control_rows,
        )
        if args.self_control_rows else None
    )
    common_cmp = modes["common_run_id"]["comparison"]
    own_cmp = modes["own_run_ids"]["comparison"]
    requests_identical = (
        common_cmp["payload_bytes_identical"]
        and common_cmp["post_body_bytes_identical"]
        and own_cmp["post_body_bytes_identical"]
        and own_cmp["run_id_normalized_payload_bytes_identical"]
    )

    recall_rows = [row for row in diff if row["class"] == "supply-recall-width"]
    identical = (
        not unclassified
        and supply["output_digests_equal"]
        and supply["both_equal_sealed_plan"]
        and requests_identical
    )
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    proof = {
        "schema": PROOF_SCHEMA,
        "owner_decision": 160,
        "question": (
            "Do COMP-1's in-chain A/A (SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1) and G5's "
            "(SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1) have byte-identical prepared first-phase supply "
            "digests and byte-identical composed request bytes? If so, one shared A/A serves both "
            "arms (decision 160); if not, the two families fly separately as registered."
        ),
        "verdict": "IDENTICAL" if identical else "DIFFERENT",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_commit": head,
        "tool": "scripts/flights/comp1/comp1_g5_shared_aa_proof.py",
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "cells": cells,
        "composed_config_diff": {
            "differing_leaves": diff,
            "by_class": {
                klass: sum(1 for row in diff if row["class"] == klass)
                for klass in sorted({row["class"] for row in diff})
            },
            "request_affecting_leaves": unclassified,
            "supply_recall_width": [
                {"leaf": row["leaf"], "comp1_aa": row["comp1_aa"], "g5_aa": row["g5_aa"]}
                for row in recall_rows
            ],
            "reading": (
                "every differing leaf is bookkeeping except the first-phase supply's recall width "
                "k (COMP-1's A/A 60, G5's 8), which reaches a request only through the supply's "
                "output; proof 2 finds the two outputs byte-identical, and proof 3 finds every "
                "request byte identical, so the width is output-neutral on this roster"
            ) if identical else "see request_affecting_leaves, prepared_supply and request_bytes",
        },
        "prepared_supply": supply,
        "request_bytes": {
            "method": (
                "FlightRuntime._dispatch_phase_program(model_free_check=True) on each A/A's own "
                "composed fragments, against the composed model fragment's REAL llama-server "
                "transport (render, allowlist, speech-feature packet binding) with its POST "
                "replaced by a fake server that records the body bytes and answers a canned, "
                "role-appropriate completion; a fake session receipt bound to the fragment's "
                "decoder identity; keyed by (sample_id, contact_id); dispatched serially (one "
                "slot, one row in flight) so the per-process request counter and the slot id are "
                "assigned in roster order in both runs"
            ),
            "modes": {
                "common_run_id": (
                    "both cells under ONE scratch run id (each under its own attempt id): the "
                    "decisive mode -- every canonical payload byte and every POST body byte must "
                    "match"
                ),
                "own_run_ids": (
                    "each cell under its own run id, as a flight is: every POST body byte must "
                    "match; the canonical payloads differ ONLY in history[]."
                    + RUN_ID_DERIVED_PAYLOAD_FIELD
                    + " (rails.knowledge.QueryState.content_hash, whose query_id is "
                    "<run id>:<sample id>:step<n> -- custody, never sent to the model, different "
                    "between any two runs of the same cell)"
                ),
            },
            "canned_answers": {
                "perception": "candidates weather_query, alarm_set, play_music (schema-valid)",
                "solver": "scenario weather, action query, no entities",
                "reviewer": "one fixed sentence",
                "planner": "REVISE on the first visit for rows whose sha256(sample_id) ends odd, else ACCEPT",
            },
            "common_run_id": modes["common_run_id"],
            "own_run_ids": modes["own_run_ids"],
            "scheduling_self_control": self_control,
        },
        "scratch": str(scratch),
        "hash_quoting": (
            "64-hex identities other than the prepared-supply output digests and the study "
            "commit are quoted as sha256-prefix16:<first 16 hex>: core.flight.repin rewrites every "
            "JSON file of a readiness package from a cell's old identity hashes to its new ones at "
            "the flip and refuses any old hash left under docs/, so a full quote would either be "
            "rewritten -- falsifying this record of what was computed at study_commit -- or block "
            "the flip; the full values are recomputable from study_commit"
        ),
    }
    proof = quote_hashes_by_prefix(proof)
    output = args.output or (repo / DEFAULT_OUTPUT)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": proof["verdict"], "output": str(output),
                      "config_classes": proof["composed_config_diff"]["by_class"],
                      "supply": {k: supply[k]["output_sha256"] for k in CELLS},
                      "common_run_id": common_cmp, "own_run_ids": own_cmp}, indent=1))
    return 0 if identical else 3


if __name__ == "__main__":
    raise SystemExit(main())
