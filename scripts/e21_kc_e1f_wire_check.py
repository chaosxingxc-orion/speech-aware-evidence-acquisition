#!/usr/bin/env python3
"""Contact-free wire check for the Earnings-21 entity-repair cells (KC-E1f).

A 4-row dry run through the committed launcher path, on CONSTRUCTION calls
only, before either cell is registered to fly -- the same shape
``scripts/e21_kc_e1_wire_check.py`` runs for KC-E1, plus the five properties
the repair pass adds and KC-E1 had no way to have.

**Zero model contacts.** The only fakes are the two the committed
``saea-driver smoke --dry-run`` path substitutes and documents at their own
construction sites (``core.driver.smoke._dry_run_transport`` and
``_NoOpGate``). Everything between them is real: the real ``core.config.
compose``, the real split verification, the real ``contracts.ExecutionPlan``
validation, the real evidence source, the real
``core.evidence_derivation.DerivedEvidenceRegistry``, the real predecessor
binding, the real ``obs-repair-loop`` policy with the real 90-second tiling and
real cut slices, the real arm allowlist, the real bundle seal, the real
``core.scoring_batch`` over all five declared scorers and the real finalize.

HOW ZERO CONTACTS IS PROVED, NOW THAT A SERVER IS ALWAYS RESIDENT
------------------------------------------------------------------
KC-E1's wire check REFUSED to run beside a resident ``llama-server``. That
guard predates the owner's 2026-09-07 always-on serving ruling, under which the
core stays resident per geometry and agents attach rather than spawn -- so
"no server anywhere on the host" is no longer a property a model-free check can
demand, and refusing on it would just make the check unrunnable. It is replaced
by two DIRECT proofs, both read out of the sealed artifacts rather than out of
the process table:

1. the sealed session receipt is the dry-run placeholder -- binary
   ``dry-run/no-real-binary``, pid 1, port 1 -- which ``core.driver.smoke``
   writes only on the ``--dry-run`` path;
2. every one of the sealed per-slice ``MODEL_RESPONSE`` texts is exactly
   ``core.driver.smoke._dry_run_transport``'s canned string.

The resident server's pid and argv are recorded in the receipt as context, so a
reader can see what was running and that nothing spoke to it.

THE FIVE REPAIR PROPERTIES
---------------------------
1. **The predecessor is on the wire, verbatim and by equality.** Each contact's
   rendered ``task_instruction`` EQUALS the fragment's own instruction plus the
   frozen frame filled with THAT window's sealed pass-1 hypothesis. An equality
   pins the frame, the join and the window-to-predecessor mapping in one
   assertion instead of three substring searches.
2. **Every window's OBS record carries the delivery and the ledger.**
   ``obs_delivered_text`` plus the full refusal/rejection block, all classes
   present even at zero.
3. **The delivered token count equals the predecessor's, on every window.**
   The property the whole cell rests on, checked on real sealed bytes rather
   than in a unit test's synthetic pair.
4. **A canned response cannot make the transcript worse.** The dry-run
   transport answers every window with the same eleven words, which the
   delivery rule refuses by the anchor floor -- so every delivered span is its
   sealed predecessor BYTE FOR BYTE, and every stitched outputs row equals the
   comparator's own sealed hypothesis for that call. That is the guarantee
   stated as a measurement: on this rail, a useless pass-2 answer costs
   nothing.
5. **The one factor survives to the wire.** The two cells' sealed requests are
   identical except for the evidence transform names, the evidence ids and the
   rendered brief content.

Usage::

    python scripts/e21_kc_e1f_wire_check.py --out-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, NamedTuple, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e21-kc-e1f-repair-44-v1"
)
ROSTER_RECEIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)

EXPERIMENT = "e21-kc-e1f-repair-44-v1"
#: KC-E1's own committed wire-check fragment, reused unchanged: the four
#: shortest kb-construction calls, 61 fixed 90-second windows, 5,322.108 s,
#: carrying the SAME carrier and D1 evidence supplement as the flight fragment.
#: Reusing it is the point -- the two cells rehearse the same four calls, so
#: their wire checks are comparable, and no new roster is minted for a check.
WIRE_DATASET = "e21-kc-e1-wire-check-4"
RUN_ID = "SAEA-E21-KC-E1F-WIRE-CHECK-V1"
FLIGHT_RUN_ID = "SAEA-E21-KC-E1F-REPAIR-44-V1"

PLAN_CALLS = 400
PLAN_AUDIO_SECONDS = 30000
PLAN_GPU_HOURS = 0.5

ROSTER_SUFFIX = "/contexts/participant_names/%s.names.txt"
DOCUMENT_SUFFIX = "/contexts/%s.txt"

DRY_RUN_TEXT = "dry-run smoke: no real model was touched"
DRY_RUN_BINARY = "dry-run/no-real-binary"

#: Every rejection class and refusal reason a repair ledger must report, so a
#: receipt shows the complete table rather than whatever happened to fire.
from speech_aware_evidence_acquisition.core.repair_alignment import (  # noqa: E402
    REFUSAL_REASONS,
    REJECTION_CLASSES,
)


class _RosterAudioRef(NamedTuple):
    """The one field ``rails.core_client.build_payload_binding`` reads off a
    sample's ``audio_ref`` (``.path``). A ``NamedTuple`` and not a
    ``@dataclass`` for the reason ``scripts/e21_kc_e1_wire_check.py`` states
    at its own copy: this module is loadable via bare ``importlib.util.
    exec_module`` without a prior ``sys.modules`` registration, and
    ``dataclasses._process_class`` reads ``sys.modules[cls.__module__]``
    unconditionally under ``from __future__ import annotations``."""

    path: str


class _RosterSample(NamedTuple):
    """The minimal ``rails.task_adapter.TaskSample`` duck type (sample_id /
    audio_ref.path / audio_seconds) built directly from this cell's own
    flight-roster-receipt row -- never a second load, so the payload-binding
    stage checks exactly the media identity the roster itself re-hashed."""

    sample_id: str
    audio_ref: _RosterAudioRef
    audio_seconds: float


def roster_binding_samples(
    roster: Mapping[str, Any], sample_ids: Sequence[str]
) -> tuple[_RosterSample, ...]:
    by_id = {str(call["sample_id"]): call for call in roster["calls"]}
    missing = [sample_id for sample_id in sample_ids if sample_id not in by_id]
    if missing:
        raise SystemExit("flight roster receipt lacks sample id(s) %r" % (missing,))
    return tuple(
        _RosterSample(
            sample_id=sample_id,
            audio_ref=_RosterAudioRef(path=str(by_id[sample_id]["media_relpath"])),
            audio_seconds=float(by_id[sample_id]["audio_seconds"]),
        )
        for sample_id in sample_ids
    )


def log(message: str) -> None:
    print(
        "[%s] %s" % (datetime.now(tz=timezone.utc).strftime("%H:%M:%SZ"), message),
        flush=True,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git(*argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=CHECK / "wire-check")
    parser.add_argument("--experiment", default=EXPERIMENT)
    parser.add_argument("--dataset", default=WIRE_DATASET)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--driver-run-id-suffix", default="a")
    # ``./mlruns`` and not ``./mlruns-wire-check``: the driver refuses to run
    # against a dirty study repo (a manifest must bind the exact commit that
    # produced it), and ``.gitignore`` ignores ``mlruns/`` but not a sibling
    # name -- so a store under any other name makes the FIRST cell's own
    # tracking directory dirty the tree and abort the SECOND cell.
    parser.add_argument("--tracking-uri", default="file:./mlruns")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
        raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

    import speech_aware_evidence_acquisition as _pkg

    if (
        Path(_pkg.__file__ or "").resolve()
        != (REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py").resolve()
    ):
        raise SystemExit("package resolves to %s, not this checkout" % (_pkg.__file__,))

    from speech_aware_evidence_acquisition.core.base import (
        EVIDENCE_SOURCES,
        declared_derived_media_roots,
    )
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
        binding_from_values,
        load_predecessor_binding,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
    from speech_aware_evidence_acquisition.rails.core_client import payload_binding_stage
    from speech_aware_evidence_acquisition.reproduction.repair_loop import REPAIR_FRAMES

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is dirty; a wire check certifies committed bytes:\n" + dirty
        )
    study_commit = git("rev-parse", "HEAD")
    log("clean tree at %s" % study_commit[:8])

    # Context, not a gate (module docstring): the always-on serving ruling
    # makes a resident server expected, and zero contacts is proved from the
    # sealed artifacts instead.
    resident = subprocess.run(
        ["pgrep", "-ax", "llama-server"], capture_output=True, text=True
    )
    resident_lines = [
        line.strip() for line in resident.stdout.splitlines() if line.strip()
    ]
    for line in resident_lines:
        log("  resident (not contacted): %s" % line[:120])

    experiment_doc = load_json(REPO / "configs" / "experiment" / f"{args.experiment}.json")
    cells = list(experiment_doc["cells"])
    model = str(cells[0]["model_fragment"])
    roster = load_json(ROSTER_RECEIPT)
    windows_by_call = {
        str(call["sample_id"]): int(call["fixed_90s_windows"]) for call in roster["calls"]
    }

    dataset_doc = load_json(REPO / "configs" / "dataset" / f"{args.dataset}.json")
    wire_split = load_json(
        REPO / "docs/receipts/probe-samples" / f"{dataset_doc['split_name']}.json"
    )
    wire_sample_ids = [str(item["id"]) for item in wire_split["items"]]
    flight_dataset_doc = load_json(
        REPO / "configs" / "dataset" / f"{cells[0]['dataset_fragment']}.json"
    )
    for key in (
        "carrier_lock_key",
        "d1_evidence_supplement",
        "d1_evidence_supplement_sha256",
    ):
        if dataset_doc.get(key) != flight_dataset_doc.get(key):
            raise SystemExit(
                "the wire-check dataset fragment must carry the flight fragment's own "
                "carrier and D1 evidence supplement, or it rehearses a different run"
            )

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    scratch = root / "runs" / args.run_id
    scratch.mkdir(parents=True, exist_ok=True)

    per_cell: dict[str, Any] = {}
    failures: list[str] = []
    for cell in cells:
        cell_id = str(cell["cell_id"])
        baseline = str(cell["baseline_fragment"])
        composed = compose(REPO, model, args.dataset, baseline, args.experiment)
        values = composed.values
        arm = str(values["arm"])
        cap = int(values["brief_max_entries_per_class"])
        instruction_base = str(values["task_instruction"])
        frame = REPAIR_FRAMES[str(values["repair_frame"])]
        relpath, digest = binding_from_values(values)
        snapshot = load_predecessor_binding(
            REPO / "docs" / relpath, root, expected_receipt_sha256=digest
        )
        log(
            "cell %s: baseline %s, evidence_source %s, cap %d, policy %s"
            % (cell_id, baseline, values["evidence_source"], cap, values["policy"])
        )

        driver_run_id = "%s-%s-%s" % (args.run_id, baseline, args.driver_run_id_suffix)
        cells_path = scratch / f"{baseline}.ledger-cells.json"
        cells_path.write_text(
            json.dumps(
                {
                    "experiment_id": (
                        "%s (%s; CONTACT-FREE WIRE CHECK, never a measurement)"
                        % (args.run_id, cell_id)
                    ),
                    "speech task/carrier": (
                        "dataset fragment %r, the four shortest kb-construction calls"
                        % args.dataset
                    ),
                    "changed axes": (
                        "baseline fragment %r; the one factor against its twin is "
                        "evidence_source" % baseline
                    ),
                    "shared code revision": "none (study repo only)",
                    "model rev": (
                        "model fragment %r; NO MODEL WAS TOUCHED -- the transport is "
                        "core.driver.smoke._dry_run_transport" % model
                    ),
                    "dataset rev": "umbrella lock; sha256 at cost.umbrella_lock_sha256",
                    "effectiveness": (
                        "NOT MEASURED. Every score in this bundle is computed over a "
                        "canned fake response and means nothing"
                    ),
                    "reasonableness": "NOT MEASURED (see effectiveness)",
                    "efficiency": "NOT MEASURED (see effectiveness)",
                    "deviations": "none",
                    "decision": (
                        "no decision. A wire check gates a flight; it never "
                        "contributes to one"
                    ),
                },
                indent=1,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        argv = [
            sys.executable, "-m", "speech_aware_evidence_acquisition.core.driver",
            "smoke", "--dry-run",
            "--model", model,
            "--dataset", args.dataset,
            "--baseline", baseline,
            "--experiment", args.experiment,
            "--run-id", driver_run_id,
            "--execution-profile", str(values["execution_profile"]),
            "--planned-model-calls", str(PLAN_CALLS),
            "--planned-gpu-hours", str(PLAN_GPU_HOURS),
            "--planned-speech-audio-seconds", str(PLAN_AUDIO_SECONDS),
            "--run-dir", str(scratch / baseline),
            "--tracking-uri", args.tracking_uri,
            "--ledger-cells", str(cells_path),
        ]
        log("  smoke --dry-run: %s" % " ".join(argv[3:8]))
        # MLFLOW_ALLOW_FILE_STORE: the installed mlflow refuses a filesystem
        # tracking backend by default (maintenance mode), and this study's
        # local ``mlruns`` store is exactly that. The opt-out is an environment
        # compatibility flag, not a protocol choice -- it changes no request,
        # no seal and no score, and the exposure ledger already records it as
        # the same non-semantic deviation two flights hit at finalize. Set here
        # so the check is self-contained rather than depending on whoever runs
        # it having exported it.
        env = dict(os.environ)
        env.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
        completed = subprocess.run(
            argv, cwd=REPO, capture_output=True, text=True, env=env
        )
        if completed.returncode != 0:
            sys.stderr.write(completed.stdout[-6000:])
            sys.stderr.write(completed.stderr[-6000:])
            raise SystemExit(
                "smoke --dry-run exited %d for cell %s" % (completed.returncode, cell_id)
            )
        brace = completed.stdout.rindex("{")
        smoke_out = json.loads(completed.stdout[brace:])
        manifest_path = Path(smoke_out["manifest"])
        attempt_dir = manifest_path.parent
        smoke_run_id = str(smoke_out["run_id"])
        trace_path = attempt_dir / f"{smoke_run_id}.trace.jsonl"
        outputs_path = attempt_dir / f"{smoke_run_id}.outputs.jsonl"
        scores_path = Path(smoke_out["scores"])
        session_receipt_path = attempt_dir / f"{smoke_run_id}.session-receipt.json"
        log("  smoke OK: attempt %s, state %s"
            % (smoke_out["attempt_id"], smoke_out["attempt_state"]))
        for line in sorted(
            {
                line.strip()
                for line in (completed.stdout + completed.stderr).splitlines()
                if line.startswith("WARNING:")
            }
        ):
            log("  %s" % line)

        # ---------------- zero-contact half ----------------
        session_receipt = load_json(session_receipt_path)
        zero_contact = {
            "session_receipt_is_the_dry_run_placeholder": (
                str(session_receipt.get("binary_path")) == DRY_RUN_BINARY
                and int(session_receipt.get("pid", -1)) == 1
                and int(session_receipt.get("port", -1)) == 1
            ),
        }

        # ---------------- request half ----------------
        allowlist = set(ARM_VISIBLE_FIELDS[arm])
        source = EVIDENCE_SOURCES.resolve(str(values["evidence_source"]))
        expected_by_sample = {
            sample_id: source(
                lock, root, sample_id, str(values["carrier_lock_key"]), values
            )
            for sample_id in wire_sample_ids
        }
        requests: list[Mapping[str, Any]] = []
        stitches: list[Mapping[str, Any]] = []
        obs_by_request: dict[str, Mapping[str, Any]] = {}
        response_texts: list[str] = []
        cost_records = 0
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            channel = record.get("channel")
            payload = record.get("payload", {})
            base = str(record.get("record_id", "")).split("/", 1)[0]
            if channel == "MODEL_REQUEST":
                (stitches if payload.get("stitch") else requests).append(
                    payload if payload.get("stitch") else payload["payload"]
                )
            elif channel == "MODEL_RESPONSE" and not payload.get("stitch"):
                response_texts.append(str(payload["text"]))
            elif channel == "OBS" and "obs_iteration" in payload:
                # Keyed by the record id's own base, exactly the way
                # analysis.e21_window_pairing binds an OBS record to its slice
                # -- never by guessing an iteration suffix.
                obs_by_request[base] = payload
            elif channel == "COST":
                cost_records += 1
        zero_contact["every_sealed_response_is_the_canned_dry_run_text"] = (
            bool(response_texts) and set(response_texts) == {DRY_RUN_TEXT}
        )

        windows_seen: dict[str, set[int]] = {}
        for payload in requests:
            sample_id = str(payload["sample_id"])
            items = expected_by_sample[sample_id]
            if set(payload) != allowlist:
                failures.append(
                    "%s/%s: payload key set differs from the %s allowlist by %r"
                    % (cell_id, sample_id, arm, sorted(set(payload) ^ allowlist))
                )
            evidence = payload["supplied_evidence"]
            provenance = payload["evidence_provenance"]
            if len(evidence) != 2 or len(provenance) != 2:
                failures.append(
                    "%s/%s: %d evidence item(s), %d provenance entr(ies)"
                    % (cell_id, sample_id, len(evidence), len(provenance))
                )
                continue
            if [entry["brief_part"] for entry in provenance] != ["roster", "document"]:
                failures.append("%s/%s: evidence is not roster-then-document"
                                % (cell_id, sample_id))
            relpaths = [str(entry["relpath"]) for entry in provenance]
            if not relpaths[0].endswith(ROSTER_SUFFIX % sample_id):
                failures.append("%s/%s: roster relpath %r"
                                % (cell_id, sample_id, relpaths[0]))
            if (
                not relpaths[1].endswith(DOCUMENT_SUFFIX % sample_id)
                or "participant_names" in relpaths[1]
            ):
                failures.append("%s/%s: document relpath %r"
                                % (cell_id, sample_id, relpaths[1]))
            for index, item in enumerate(evidence):
                if item["evidence_id"] != items[index].evidence_id:
                    failures.append("%s/%s: evidence id %r"
                                    % (cell_id, sample_id, item["evidence_id"]))
                if sha256_text(item["content"]) != items[index].derivation.derived_sha256:
                    failures.append(
                        "%s/%s: half %d does not re-hash to the transform's output at "
                        "cap %d" % (cell_id, sample_id, index, cap)
                    )
                if int(provenance[index]["max_entries_per_class"]) != cap:
                    failures.append("%s/%s: provenance cap disagrees"
                                    % (cell_id, sample_id))
            media = str(payload["media_relpath"])
            prefix = "derived/obs-slices/%s/%s/" % (smoke_run_id, sample_id)
            if not media.startswith(prefix):
                failures.append("%s/%s: media_relpath %r is not this run's own slice"
                                % (cell_id, sample_id, media))
            else:
                windows_seen.setdefault(sample_id, set()).add(
                    int(media[len(prefix) + 1 : -len(".wav")])
                )

        window_counts = {sid: len(seen) for sid, seen in windows_seen.items()}
        expected_windows = {sid: windows_by_call[sid] for sid in expected_by_sample}
        if window_counts != expected_windows:
            failures.append("%s: OBS tiling cut %r windows, the roster says %r"
                            % (cell_id, window_counts, expected_windows))
        stitched_ids = sorted(
            rid for record in stitches for rid in record["stitched_request_ids"]
        )
        contacted_ids = sorted(str(payload["request_id"]) for payload in requests)
        if stitched_ids != contacted_ids:
            failures.append("%s: stitch chains and contacted request ids disagree" % cell_id)
        if cost_records != len(requests):
            failures.append("%s: %d COST record(s) for %d contacts"
                            % (cell_id, cost_records, len(requests)))

        # ---------------- payload-binding stage ----------------
        # docs/readiness/2026-09-07-derived-media-confinement-v1.md section 5,
        # and section 7.3 of this cell's own preregistration, which named this
        # stage as PENDING the wt/wirepay merge rather than skipping it. The
        # shared rails.core_client.payload_binding_stage runs over this cell's
        # own real roster rows, through the REAL carrier root (never a
        # per-script carrier_root_resolver swap) plus whatever derived media
        # roots the dataset fragment declares -- so a cell is reported
        # wire-ready only if its payloads actually BIND. Zero sockets, zero
        # servers, zero model contacts.
        binding_stage = payload_binding_stage(
            dataset_fragment=args.dataset,
            carrier_lock_key=str(values["carrier_lock_key"]),
            samples=roster_binding_samples(roster, sorted(expected_by_sample)),
            data_root=root,
            carrier_root=asset_dir(lock, str(values["carrier_lock_key"]), root),
            derived_media_roots=declared_derived_media_roots(values, root),
        )
        if not binding_stage.bound:
            failures.append(
                "%s: payload-binding stage did not bind: %r"
                % (cell_id, binding_stage.failures)
            )
        log(
            "  payload-binding stage: %s (%d/%d row(s) checked)"
            % (
                "PASS" if binding_stage.bound else "FAIL",
                len(binding_stage.rows_checked),
                binding_stage.rows_total,
            )
        )

        # ---------------- repair half ----------------
        by_request = {str(payload["request_id"]): payload for payload in requests}
        repair_props = {
            name: True
            for name in (
                "instruction_equals_the_base_plus_the_framed_predecessor",
                "every_window_records_a_delivery_and_a_complete_ledger",
                "delivered_token_count_equals_the_predecessors",
                "a_canned_response_delivers_the_predecessor_byte_for_byte",
            )
        }
        ledger = {
            "windows": 0,
            "refusal_reasons": {name: 0 for name in REFUSAL_REASONS},
            "rejected_opcodes": {name: 0 for name in REJECTION_CLASSES},
            "windows_changed": 0,
        }
        for request_id, record in sorted(obs_by_request.items()):
            window_id = str(record.get("obs_repair_predecessor_window_id", ""))
            predecessor = snapshot.windows.get(window_id)
            if predecessor is None or request_id not in by_request:
                repair_props["instruction_equals_the_base_plus_the_framed_predecessor"] = False
                continue
            expected_instruction = "%s\n\n%s" % (
                instruction_base, frame.format(predecessor=predecessor.text)
            )
            if str(by_request[request_id]["task_instruction"]) != expected_instruction:
                repair_props["instruction_equals_the_base_plus_the_framed_predecessor"] = False
            for key in ("obs_delivered_text", "obs_repair_refused", "obs_repair_rejected"):
                if key not in record:
                    repair_props["every_window_records_a_delivery_and_a_complete_ledger"] = False
            if set(record.get("obs_repair_rejected", {})) != set(REJECTION_CLASSES):
                repair_props["every_window_records_a_delivery_and_a_complete_ledger"] = False
            delivered = str(record.get("obs_delivered_text", ""))
            if len(delivered.split()) != len(predecessor.text.split()):
                repair_props["delivered_token_count_equals_the_predecessors"] = False
            if delivered != predecessor.text:
                repair_props["a_canned_response_delivers_the_predecessor_byte_for_byte"] = False
            ledger["windows"] += 1
            reason = record.get("obs_repair_refusal_reason")
            if reason in ledger["refusal_reasons"]:
                ledger["refusal_reasons"][reason] += 1
            for name, count in dict(record.get("obs_repair_rejected", {})).items():
                if name in ledger["rejected_opcodes"]:
                    ledger["rejected_opcodes"][name] += int(count)
            if int(record.get("obs_repair_substitutions", 0)):
                ledger["windows_changed"] += 1
        if ledger["windows"] != len(requests):
            failures.append("%s: %d repair OBS record(s) for %d contacts"
                            % (cell_id, ledger["windows"], len(requests)))

        # The strongest single statement this check can make: the stitched
        # outputs row equals the comparator's OWN sealed hypothesis for that
        # call, byte for byte, because every window refused.
        outputs_match = True
        for line in outputs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            sealed = " ".join(
                window.text
                for window in snapshot.for_sample(str(row["sample_id"]))
                if window.text
            )
            if str(row["text"]) != sealed:
                outputs_match = False
        repair_props["stitched_row_equals_the_sealed_comparator_hypothesis"] = outputs_match

        # ---------------- seal half ----------------
        bundle = verify_bundle(manifest_path)
        scores = load_json(scores_path)
        declared = list(values["scorers"])
        scored = sorted(
            name
            for name in declared
            if isinstance(scores.get(name), Mapping) and "aggregate" in scores[name]
        )
        if scored != sorted(declared):
            failures.append("%s: scored %r, the fragment declares %r"
                            % (cell_id, scored, sorted(declared)))

        per_cell[cell_id] = {
            "cell_id": cell_id,
            "baseline_fragment": baseline,
            "evidence_source": str(values["evidence_source"]),
            "policy": str(values["policy"]),
            "config_hash": composed.config_hash,
            "task_instruction_sha256": sha256_text(instruction_base),
            "repair_frame_sha256": sha256_text(frame),
            "predecessor_binding": {"relpath": relpath, "sha256": digest},
            "driver_run_id": smoke_run_id,
            "attempt_id": str(smoke_out["attempt_id"]),
            "attempt_state": str(smoke_out["attempt_state"]),
            "contacts": len(requests),
            "calls": len(expected_by_sample),
            "windows_per_call": window_counts,
            "cost_records": cost_records,
            "zero_contact": zero_contact,
            "payload_binding_stage": binding_stage.as_receipt(),
            "repair_properties": repair_props,
            "repair_ledger": ledger,
            "scorers_with_aggregates": scored,
            "manifest_sha256": sha256_file(manifest_path),
            "trace_sha256": sha256_file(trace_path),
            "outputs_sha256": sha256_file(outputs_path),
            "bundle_attempt_state": bundle.attempt_state,
        }
        log(
            "  request half OK: %d contacts, %d calls; repair properties %s; "
            "refusals %r"
            % (
                len(requests),
                len(expected_by_sample),
                "ALL HOLD" if all(repair_props.values()) else "FAILED",
                {k: v for k, v in ledger["refusal_reasons"].items() if v},
            )
        )
        if not all(zero_contact.values()):
            failures.append("%s: the zero-contact proof does not hold: %r"
                            % (cell_id, zero_contact))
        if not all(repair_props.values()):
            failures.append("%s: a repair property failed: %r" % (cell_id, repair_props))

    # ---------------- the one factor, across the two cells ----------------
    cell_ids = list(per_cell)
    a, b = per_cell[cell_ids[0]], per_cell[cell_ids[1]]
    one_factor = {
        "same_policy": a["policy"] == b["policy"],
        "same_task_instruction": a["task_instruction_sha256"] == b["task_instruction_sha256"],
        "same_repair_frame": a["repair_frame_sha256"] == b["repair_frame_sha256"],
        "same_predecessor_binding": a["predecessor_binding"] == b["predecessor_binding"],
        "same_contact_count": a["contacts"] == b["contacts"],
        "same_windows_per_call": a["windows_per_call"] == b["windows_per_call"],
        "different_evidence_source": a["evidence_source"] != b["evidence_source"],
        "different_config_hash": a["config_hash"] != b["config_hash"],
    }
    if not all(one_factor.values()):
        failures.append("the one-factor comparison failed: %r" % one_factor)

    document = {
        "schema": "saea-e21-kc-e1f-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "flight_run_id": FLIGHT_RUN_ID,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": study_commit,
        "experiment_fragment": args.experiment,
        "wire_dataset_fragment": args.dataset,
        "wire_sample_ids": wire_sample_ids,
        "zero_contact": (
            "no model, server, socket, GPU or network contact. Audio IS decoded and "
            "sliced (that is the point of a dry run through the real OBS tiling) and "
            "the five declared scorers DO run over canned responses. Proved from the "
            "sealed artifacts: the session receipt is the dry-run placeholder and "
            "every sealed per-slice MODEL_RESPONSE is the canned string"
        ),
        "resident_processes_not_contacted": resident_lines,
        "why_a_resident_server_is_no_longer_a_refusal": (
            "the owner's 2026-09-07 always-on serving ruling keeps the core resident "
            "per geometry and has agents attach rather than spawn, so 'no server on "
            "the host' is not a property a model-free check can demand. The two "
            "direct proofs above replace it"
        ),
        "cells": per_cell,
        "one_factor": one_factor,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "what_this_does_not_certify": (
            "it certifies that the harness assembles, seals and scores the right "
            "request, that the payloads BIND through the real carrier root, and that "
            "a useless pass-2 answer cannot move the transcript. It does NOT certify "
            "the geometry -- that is the prompt fit in SERVER mode, run on the "
            "geometry the cells name -- and it says nothing about what the frozen "
            "core does with a real request"
        ),
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "wire-check.json"
    out_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%s)" % (out_path, document["result"]))
    for failure in failures:
        log("  FAILURE: %s" % failure)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
