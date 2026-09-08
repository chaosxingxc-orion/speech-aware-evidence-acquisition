#!/usr/bin/env python3
"""Contact-free wire check for the Earnings-21 pre-meeting-brief cells.

Section 8 item 3 of ``docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-
preregistration.md``: a 4-row dry run through the committed launcher path, on
CONSTRUCTION calls only, before either cell is registered to fly.

**Zero contacts of every kind**: no model, no server, no socket, no GPU, no
tokenizer, no network. The only fakes are the two the committed
``saea-driver smoke --dry-run`` path substitutes and documents at their own
construction sites -- ``core.driver.smoke._dry_run_transport`` and
``core.driver.smoke._NoOpGate``. Everything between them is the real thing:
the real ``core.config.compose``, the real split verification, the real
``contracts.ExecutionPlan`` validation, the real evidence source, the real
``core.evidence_derivation.DerivedEvidenceRegistry``, the real 90-second OBS
tiling with its real cut slices, the real arm allowlist, the real bundle seal,
the real ``core.scoring_batch`` over all five declared scorers and the real
finalize.

THE TWO HALVES
--------------
**Request half.** Read out of the SEALED trace, per contact, never from a
second in-memory copy:

1. the payload's key set is exactly ``fixed-legal-context``'s D2-frozen field
   set -- no more, no less;
2. ``supplied_evidence`` carries exactly TWO items, roster first then document.
   This is the property precondition 1's driver fix made observable: before it,
   ``core.driver.run_experiment`` ASSIGNED rather than accumulated the per-sample
   evidence relpath and the ROSTER half was the one silently dropped;
3. ``evidence_provenance`` carries both relpaths, each naming this call's own
   sample id, one under ``contexts/participant_names/`` and one directly under
   ``contexts/``;
4. every rendered brief half re-hashes to the derived sha256 the transform
   produces at the COMMITTED cap -- so the wire check and the prompt fit are
   pinned to the same bytes, and a fragment edited between them would be caught;
5. the OBS tiling cut exactly the roster receipt's own window count for each
   call, every window naming a slice under this run's own slice directory.

**Evidence-rail half.** ``smoke --dry-run`` runs under ``_NoOpGate``, so the D1
evidence-identity rail is NOT exercised by it. That rail is therefore driven
here directly, with a REAL ``contracts.FrozenCoreGate`` built from the cell's own
composed config, over the four calls' own two relpaths each: both must resolve,
and they must route to ``e21_participant_names`` and ``e21_contexts``
respectively. A gate is a file-and-hash check; it opens nothing and contacts
nothing.

**Seal half.** The sealed manifest verifies through ``core.bundle.verify_bundle``,
carries one canonical row per call, and every one of the five declared scorers
produced an aggregate over the complete manifest. A four-scorer manifest that
does not actually score is the defect the full-44 preregistration existed to
fix; this is the same proof for a five-scorer one.

Finally the two cells are compared: identical everywhere except the evidence
transform names, the evidence ids and the rendered content -- which is the one
factor the experiment claims, asserted on the wire rather than in prose.

Usage::

    python scripts/e21_kc_e1_wire_check.py --out-dir <dir>
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

#: Resolved from the script's own location, exactly as every ``scripts/
#: flights/*.py`` entry point already does, so this check runs against
#: WHICHEVER checkout (or git worktree) it is invoked from rather than always
#: the one main checkout path this constant used to hard-code -- a worktree
#: doing model-free repair work must be able to run its own copy of this
#: check without ever touching the main checkout's tree.
REPO = Path(__file__).resolve().parents[1]

CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-kc-e1-brief-44-v1"
)
ROSTER_RECEIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)

EXPERIMENT = "e21-kc-e1-brief-44-v1"
WIRE_DATASET = "e21-kc-e1-wire-check-4"
RUN_ID = "SAEA-E21-KC-E1-WIRE-CHECK-V1"
FLIGHT_RUN_ID = "SAEA-E21-KC-E1-BRIEF-44-V1"

#: The dry run's ExecutionPlan budget. NOT a spend registration: the transport
#: is ``core.driver.smoke._dry_run_transport`` and zero real contacts are made,
#: but the REAL metering rail still runs, and it is cumulative across every
#: attempt of a run id. One attempt costs 61 windows and 5,322.108 audio
#: seconds -- the four calls' whole duration, tiled -- so a budget sized for a
#: single attempt makes the SECOND invocation of the check fail with an
#: exhausted budget rather than a result. Sized for five attempts, which is
#: what a check that may need iterating actually needs.
PLAN_CALLS = 400
PLAN_AUDIO_SECONDS = 30000
PLAN_GPU_HOURS = 0.5

#: An evidence provenance relpath is relative to the ``conec`` lock key's own
#: asset root, so it reads ``earnings21/contexts/...`` rather than
#: ``contexts/...``. These anchor on the TAIL, which is what distinguishes the
#: two halves: ``contexts/`` is a prefix of ``contexts/participant_names/``, so
#: a prefix test alone would classify the roster as a document.
ROSTER_SUFFIX = "/contexts/participant_names/%s.names.txt"
DOCUMENT_SUFFIX = "/contexts/%s.txt"


class _RosterAudioRef(NamedTuple):
    """The one field ``rails.core_client.build_payload_binding`` reads off a
    sample's ``audio_ref`` (``.path``); a placeholder, unvalidated sha256 is
    fine here because nothing calls ``.validate()`` on it. A ``NamedTuple``
    rather than a ``@dataclass``: this script is loaded via bare
    ``importlib.util.exec_module`` by at least one sibling test convention
    (``tests/unit/test_a2t_input_rate_16k_fragments.py``'s own ``_module()``
    helper, applied to a sibling wire-check script), which does not register
    the loaded module in ``sys.modules`` first -- and ``dataclasses.
    _process_class`` unconditionally reads ``sys.modules[cls.__module__]``
    under ``from __future__ import annotations``, so any ``@dataclass``
    defined directly in such a module raises at import time."""

    path: str


class _RosterSample(NamedTuple):
    """The minimal ``rails.task_adapter.TaskSample`` duck type (sample_id /
    audio_ref.path / audio_seconds) built directly from this cell's own
    flight-roster-receipt row -- never a second load, so the payload-binding
    stage checks exactly the media identity the roster itself already
    re-hashed."""

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
    parser.add_argument(
        "--driver-run-id-suffix",
        default=datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        help=(
            "per-invocation suffix for the run id handed to the driver. The "
            "attempt store meters CUMULATIVELY across every attempt of a run id, "
            "and each invocation of this check tiles the four calls' whole "
            "5,322.108 seconds through the FAKE transport -- so a stable driver "
            "run id makes the check die of an exhausted audio budget after a "
            "handful of invocations, for a reason that has nothing to do with "
            "the cell. A fresh suffix per invocation is correct here and ONLY "
            "here: zero real contacts are made, so there is no real spend for "
            "the rail to bound. The stable --run-id is what the receipt and the "
            "exposure ledger name; the suffixed ids are recorded beside it"
        ),
    )
    parser.add_argument(
        "--tracking-uri",
        default="sqlite:///%s" % (Path.home() / "mlruns.db"),
        help=(
            "explicit local MLflow tracking URI. Defaults to the SAME ext4 sqlite "
            "backend scripts/run_arm_sequence.sh uses; the file store this "
            "repository once used is refused outright by the installed MLflow"
        ),
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "TEST-ONLY. A wire check certifies a COMMITTED tree; without this the "
            "run refuses a dirty one rather than recording a study_commit that "
            "describes different bytes than the ones it exercised"
        ),
    )
    args = parser.parse_args()

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
        raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

    import speech_aware_evidence_acquisition as _pkg

    if (
        Path(_pkg.__file__ or "")
        != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
    ):
        raise SystemExit(
            "package resolves to %s, not this checkout" % (_pkg.__file__,)
        )

    from speech_aware_evidence_acquisition.contracts import FrozenCoreGate
    from speech_aware_evidence_acquisition.contracts.gate_evidence_identity import (
        _route_evidence_layer_key,
    )
    from speech_aware_evidence_acquisition.core.base import (
        EVIDENCE_SOURCES,
        declared_derived_media_roots,
    )
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.core.config import (
        compose,
        d1_evidence_supplement_relpath,
        d1_evidence_supplement_sha256,
        d1_media_supplement_relpath,
        d1_media_supplement_sha256,
        model_materialization_root,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
    from speech_aware_evidence_acquisition.rails.core_client import payload_binding_stage

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is dirty; a wire check certifies committed bytes:\n"
            + dirty
        )
    study_commit = git("rev-parse", "HEAD")
    log("clean tree at %s" % study_commit[:8])

    # ``pgrep -x`` matches the process NAME, not the command line. ``-f`` was
    # tried first and is wrong here: it matches any shell, editor or pipeline
    # whose arguments merely mention llama-server, which made this check refuse
    # to run because of a transient sibling that was never a server. The
    # matched command lines are printed when it does fire, so a future refusal
    # is diagnosable instead of a bare pid.
    resident = subprocess.run(
        ["pgrep", "-ax", "llama-server"], capture_output=True, text=True
    )
    if resident.returncode == 0 and resident.stdout.strip():
        raise SystemExit(
            "a llama-server is resident; a zero-socket wire check refuses to run "
            "beside one:\n" + resident.stdout
        )

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
    supplement_keys = (
        "carrier_lock_key",
        "d1_evidence_supplement",
        "d1_evidence_supplement_sha256",
    )
    supplement_matches_flight = all(
        dataset_doc.get(key) == flight_dataset_doc.get(key) for key in supplement_keys
    )
    if not supplement_matches_flight:
        raise SystemExit(
            "the wire-check dataset fragment must carry the flight fragment's own "
            "carrier and D1 evidence supplement, or it rehearses a different run"
        )

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    scratch = root / "runs" / args.run_id
    scratch.mkdir(parents=True, exist_ok=True)

    per_cell: dict[str, Any] = {}
    for cell in cells:
        cell_id = str(cell["cell_id"])
        baseline = str(cell["baseline_fragment"])
        composed = compose(REPO, model, args.dataset, baseline, args.experiment)
        values = composed.values
        arm = str(values["arm"])
        cap = int(values["brief_max_entries_per_class"])
        log(
            "cell %s: baseline %s, evidence_source %s, cap %d"
            % (cell_id, baseline, values["evidence_source"], cap)
        )

        # finalize_bundle renders a DRAFT wiki-ledger row and core.tracking.
        # ledger_row refuses a missing column outright, so the launcher must
        # supply the judgment columns the driver has no basis to invent --
        # exactly what scripts/run_arm_sequence.sh does for a real arm. A wire
        # check has no science, so its cells say so rather than borrowing the
        # launcher's PENDING-ANALYSIS placeholders, which would imply an
        # analysis is coming.
        driver_run_id = "%s-%s-%s" % (
            args.run_id,
            baseline,
            args.driver_run_id_suffix,
        )
        cells_path = scratch / f"{baseline}.ledger-cells.json"
        cells_path.parent.mkdir(parents=True, exist_ok=True)
        cells_path.write_text(
            json.dumps(
                {
                    "experiment_id": (
                        "%s (%s; CONTACT-FREE WIRE CHECK, never a measurement)"
                        % (args.run_id, cell_id)
                    ),
                    "speech task/carrier": (
                        "dataset fragment %r, the four shortest kb-construction calls; "
                        "identity: exposure-ledger row SAEA-E21-KC-E1-PROMPT-FIT-V1"
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
                    "dataset rev": (
                        "umbrella lock; sha256 recorded at manifest "
                        "cost.umbrella_lock_sha256"
                    ),
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
            sys.executable,
            "-m",
            "speech_aware_evidence_acquisition.core.driver",
            "smoke",
            "--dry-run",
            "--model",
            model,
            "--dataset",
            args.dataset,
            "--baseline",
            baseline,
            "--experiment",
            args.experiment,
            "--run-id",
            driver_run_id,
            "--execution-profile",
            str(values["execution_profile"]),
            "--planned-model-calls",
            str(PLAN_CALLS),
            "--planned-gpu-hours",
            str(PLAN_GPU_HOURS),
            "--planned-speech-audio-seconds",
            str(PLAN_AUDIO_SECONDS),
            "--run-dir",
            str(scratch / baseline),
            "--tracking-uri",
            args.tracking_uri,
            "--ledger-cells",
            str(cells_path),
        ]
        log("  smoke --dry-run: %s" % " ".join(argv[3:8]))
        completed = subprocess.run(
            argv, cwd=REPO, capture_output=True, text=True, env=dict(os.environ)
        )
        if completed.returncode != 0:
            sys.stderr.write(completed.stdout[-4000:])
            sys.stderr.write(completed.stderr[-4000:])
            raise SystemExit(
                "smoke --dry-run exited %d for cell %s" % (completed.returncode, cell_id)
            )
        # The CLI prints its artifact locations as the LAST JSON object it
        # writes; everything before it is progress output.
        brace = completed.stdout.rindex("{")
        smoke_out = json.loads(completed.stdout[brace:])
        manifest_path = Path(smoke_out["manifest"])
        attempt_dir = manifest_path.parent
        smoke_run_id = str(smoke_out["run_id"])
        trace_path = attempt_dir / f"{smoke_run_id}.trace.jsonl"
        outputs_path = attempt_dir / f"{smoke_run_id}.outputs.jsonl"
        scores_path = Path(smoke_out["scores"])
        log(
            "  smoke OK: attempt %s, state %s"
            % (smoke_out["attempt_id"], smoke_out["attempt_state"])
        )
        # Surfaced rather than swallowed: the arm predates the 2026-08-15
        # legality doctrine's either-field rule, so every run of it -- this
        # dry run and the flight alike -- records provenance tier UNVERIFIED.
        # The flight agent should know that before reading the manifest's
        # legality block, not after.
        warnings = sorted(
            {
                line.strip()
                for line in (completed.stdout + completed.stderr).splitlines()
                if line.startswith("WARNING:")
            }
        )
        for line in warnings:
            log("  %s" % line)

        # ---------------- request half ----------------
        allowlist = set(ARM_VISIBLE_FIELDS[arm])
        source = EVIDENCE_SOURCES.resolve(str(values["evidence_source"]))
        expected_by_sample = {
            sample_id: source(
                lock, root, sample_id, str(values["carrier_lock_key"]), values
            )
            for sample_id in wire_sample_ids
        }
        # The obs-agent-loop emits TWO shapes on MODEL_REQUEST: one per
        # contact carrying the payload, and one per SAMPLE carrying
        # ``stitch: true`` and the ids it stitched. Both are read: the first
        # is the request half's subject, the second is an independent check
        # that every window this sample cut actually reached the wire and was
        # stitched back, with no id invented and none lost.
        requests: list[Mapping[str, Any]] = []
        stitches: list[Mapping[str, Any]] = []
        organized: list[Mapping[str, Any]] = []
        supplied: list[Mapping[str, Any]] = []
        cost_records = 0
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            channel = record.get("channel")
            payload = record.get("payload", {})
            if channel == "MODEL_REQUEST":
                if payload.get("stitch"):
                    stitches.append(payload)
                else:
                    requests.append(payload["payload"])
            elif channel == "ORG":
                organized.append(payload)
            elif channel == "SUPPLY":
                supplied.append(payload)
            elif channel == "COST":
                cost_records += 1

        failures: list[str] = []
        windows_seen: dict[str, set[int]] = {}
        for payload in requests:
            sample_id = str(payload["sample_id"])
            items = expected_by_sample[sample_id]
            if set(payload) != allowlist:
                failures.append(
                    "payload key set for %s is %r, not the %s allowlist"
                    % (sample_id, sorted(set(payload) ^ allowlist), arm)
                )
            evidence = payload["supplied_evidence"]
            provenance = payload["evidence_provenance"]
            if len(evidence) != 2 or len(provenance) != 2:
                failures.append(
                    "%s carries %d evidence item(s) and %d provenance entr(ies), "
                    "expected 2 and 2" % (sample_id, len(evidence), len(provenance))
                )
                continue
            if [entry["brief_part"] for entry in provenance] != ["roster", "document"]:
                failures.append("%s: evidence is not roster-then-document" % sample_id)
            relpaths = [str(entry["relpath"]) for entry in provenance]
            # Shape, not prefix: a provenance relpath is relative to the conec
            # lock key's own asset root, so it opens with the carrier subdir
            # (``earnings21/``) and only THEN reaches the layer directories.
            # Anchoring on the tail is what makes the two halves distinguishable
            # -- ``contexts/`` is a prefix of ``contexts/participant_names/``,
            # so a prefix test alone would call the roster a document.
            if not relpaths[0].endswith(ROSTER_SUFFIX % sample_id):
                failures.append("%s: roster relpath %r" % (sample_id, relpaths[0]))
            if (
                not relpaths[1].endswith(DOCUMENT_SUFFIX % sample_id)
                or "participant_names" in relpaths[1]
            ):
                failures.append("%s: document relpath %r" % (sample_id, relpaths[1]))
            for index, item in enumerate(evidence):
                if item["evidence_id"] != items[index].evidence_id:
                    failures.append(
                        "%s: evidence id %r, expected %r"
                        % (sample_id, item["evidence_id"], items[index].evidence_id)
                    )
                if (
                    hashlib.sha256(item["content"].encode("utf-8")).hexdigest()
                    != items[index].derivation.derived_sha256
                ):
                    failures.append(
                        "%s: half %d does not re-hash to the transform's own output at "
                        "cap %d" % (sample_id, index, cap)
                    )
                if int(entry_cap := provenance[index]["max_entries_per_class"]) != cap:
                    failures.append(
                        "%s: provenance records cap %d, the fragment carries %d"
                        % (sample_id, entry_cap, cap)
                    )
            media = str(payload["media_relpath"])
            prefix = "derived/obs-slices/%s/%s/" % (smoke_run_id, sample_id)
            if not media.startswith(prefix):
                failures.append("%s: media_relpath %r is not this run's own slice"
                                % (sample_id, media))
            else:
                windows_seen.setdefault(sample_id, set()).add(
                    int(media[len(prefix) + 1 : -len(".wav")])
                )

        window_counts = {sid: len(seen) for sid, seen in windows_seen.items()}
        expected_windows = {sid: windows_by_call[sid] for sid in expected_by_sample}
        if window_counts != expected_windows:
            failures.append(
                "OBS tiling cut %r windows, the roster receipt says %r"
                % (window_counts, expected_windows)
            )
        if len(stitches) != len(expected_by_sample):
            failures.append(
                "%d stitch record(s) for %d calls"
                % (len(stitches), len(expected_by_sample))
            )
        stitched_ids = sorted(
            request_id
            for record in stitches
            for request_id in record["stitched_request_ids"]
        )
        contacted_ids = sorted(str(payload["request_id"]) for payload in requests)
        if stitched_ids != contacted_ids:
            failures.append(
                "the stitch chains and the contacted request ids disagree "
                "(%d stitched, %d contacted)"
                % (len(stitched_ids), len(contacted_ids))
            )
        if cost_records != len(requests):
            failures.append(
                "%d COST record(s) for %d contacts" % (cost_records, len(requests))
            )
        # ORG and SUPPLY are the driver's own per-sample view of what was
        # organized and supplied. They are checked independently of the
        # payloads above, because two views agreeing is evidence and one view
        # asserting is not.
        if len(organized) != len(expected_by_sample):
            failures.append("%d ORG record(s) for %d calls"
                            % (len(organized), len(expected_by_sample)))
        if any(int(record["org_evidence_count"]) != 2 for record in organized):
            failures.append(
                "an ORG record reports an evidence count other than 2: %r"
                % ([record["org_evidence_count"] for record in organized],)
            )
        expected_ids = {
            tuple(item.evidence_id for item in items)
            for items in expected_by_sample.values()
        }
        supplied_ids = {tuple(record["supply_evidence_ids"]) for record in supplied}
        if supplied_ids != expected_ids:
            failures.append(
                "SUPPLY evidence ids %r do not match the source's own %r"
                % (sorted(supplied_ids), sorted(expected_ids))
            )

        # ---------------- payload-binding stage ----------------
        # docs/readiness/2026-09-07-derived-media-confinement-v1.md section 5:
        # no model-free gate in this repository had ever built a payload. This
        # drives the shared rails.core_client.payload_binding_stage over this
        # cell's own real roster rows, through the REAL carrier root (never a
        # per-script carrier_root_resolver swap) plus whatever derived media
        # roots this dataset fragment declares (empty for earnings21-original,
        # which declares none -- the carrier-rooted comparator case) -- so a
        # cell is reported wire-ready only if its payloads actually BIND.
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
                "payload-binding stage did not bind: %r" % (binding_stage.failures,)
            )
        log(
            "  payload-binding stage: %s (%d/%d row(s) checked)"
            % (
                "PASS" if binding_stage.bound else "FAIL",
                len(binding_stage.rows_checked),
                binding_stage.rows_total,
            )
        )

        # ---------------- evidence-rail half ----------------
        configured_model_root = model_materialization_root(values)
        gate = FrozenCoreGate.for_study_repo(
            REPO,
            root,
            Path("/home/chao"),
            runtime_receipt_relpath=str(values["runtime_receipt"]),
            expected_model_lock_key=str(values["model_lock_key"]),
            model_root=(Path(configured_model_root) if configured_model_root else None),
            d1_media_supplement_relpath=d1_media_supplement_relpath(values),
            d1_media_supplement_sha256=d1_media_supplement_sha256(values),
            d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(values),
            d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(values),
        )
        evidence_facts = {
            sample_id: tuple(
                item.derivation.source_relpath for item in items
            )
            for sample_id, items in expected_by_sample.items()
        }
        evidence_contents = {
            sample_id: tuple(item.derivation_source_bytes for item in items)
            for sample_id, items in expected_by_sample.items()
        }
        layout = gate._evidence_layout(str(values["carrier_lock_key"]))
        routing = {
            sample_id: [
                _route_evidence_layer_key(layout, relpath) for relpath in relpaths
            ]
            for sample_id, relpaths in evidence_facts.items()
        }
        expected_routing = ["e21_participant_names", "e21_contexts"]
        rail_failures = [
            sample_id
            for sample_id, keys in routing.items()
            if keys != expected_routing
        ]
        gate.verify_evidence_identity(str(values["carrier_lock_key"]), evidence_facts)
        gate.verify_evidence_content_identity(
            str(values["carrier_lock_key"]), evidence_contents, evidence_facts
        )
        if rail_failures:
            failures.append("evidence rail routing failed for %r" % (rail_failures,))
        log("  evidence rail: both relpaths of all %d calls resolve and route"
            % len(evidence_facts))

        # ---------------- seal half ----------------
        declared = list(values["scorers"])
        manifest = load_json(manifest_path)
        verify_bundle(manifest_path)
        if manifest.get("study_commit") != study_commit or manifest.get(
            "study_repo_dirt"
        ):
            failures.append(
                "the sealed manifest records study_commit %r with dirt %r; this "
                "check ran at %r on a clean tree"
                % (
                    manifest.get("study_commit"),
                    manifest.get("study_repo_dirt"),
                    study_commit,
                )
            )
        if manifest.get("status") != "COMPLETED":
            failures.append("manifest status %r" % (manifest.get("status"),))
        if list(manifest.get("scorers") or []) != declared:
            failures.append(
                "the sealed manifest declares scorers %r, the fragment %r"
                % (manifest.get("scorers"), declared)
            )
        scores = load_json(scores_path)
        aggregates = {
            name: sorted(block.get("aggregate", {}))
            for name, block in scores.items()
            if isinstance(block, Mapping)
        }
        missing = [name for name in declared if name not in aggregates]
        if missing:
            failures.append("declared scorers with no aggregate: %r" % (missing,))
        outputs_rows = sum(
            1 for line in outputs_path.read_text(encoding="utf-8").splitlines() if line
        )
        if outputs_rows != len(expected_by_sample):
            failures.append(
                "sealed outputs carry %d rows for %d calls"
                % (outputs_rows, len(expected_by_sample))
            )

        if failures:
            # Deduplicated: one broken property repeats once per contact, and a
            # 61-line wall of the same sentence hides how many DISTINCT things
            # are wrong.
            for entry, count in sorted(
                {entry: failures.count(entry) for entry in failures}.items()
            ):
                log("  FAIL (x%d) %s" % (count, entry))
            raise SystemExit("wire check failed for cell %s" % cell_id)
        log("  request half OK: %d contacts, %d calls, %d windows"
            % (len(requests), len(expected_by_sample), sum(window_counts.values())))
        log("  seal half OK: %d sealed rows, %d scorers with aggregates"
            % (outputs_rows, len(declared)))

        per_cell[cell_id] = {
            "cell_id": cell_id,
            "baseline_fragment": baseline,
            "evidence_source": str(values["evidence_source"]),
            "brief_max_entries_per_class": cap,
            "arm": arm,
            "config_hash": composed.config_hash,
            "protocol_hash": manifest.get("protocol_hash"),
            "launcher_warnings": warnings,
            "legality_block": manifest.get("legality"),
            "smoke_run_id": smoke_run_id,
            "driver_run_id": driver_run_id,
            "attempt_id": str(smoke_out["attempt_id"]),
            "attempt_state": str(smoke_out["attempt_state"]),
            "artifact_dir": str(attempt_dir),
            "artifact_sha256": {
                "outputs.jsonl": sha256_file(outputs_path),
                "run-manifest.json": sha256_file(manifest_path),
                "scores.json": sha256_file(scores_path),
                "trace.jsonl": sha256_file(trace_path),
            },
            "request_half": {
                "contacts": len(requests),
                "cost_records": cost_records,
                "stitch_records": len(stitches),
                "stitch_chains_cover_every_contact_exactly_once": True,
                "org_records_report_two_evidence_items": True,
                "supply_records_name_the_sources_own_evidence_ids": True,
                "calls": len(expected_by_sample),
                "windows_per_call": window_counts,
                "windows_per_call_matches_the_roster_receipt": True,
                "payload_key_set_equals_the_arm_allowlist": True,
                "arm_allowlist": sorted(allowlist),
                "two_evidence_items_roster_then_document": True,
                "both_relpaths_in_evidence_provenance": True,
                "every_half_rehashes_to_its_transform_output": True,
                "provenance_records_the_committed_cap": True,
                "every_window_names_this_runs_own_slice": True,
                "evidence_ids": [
                    item.evidence_id
                    for item in next(iter(expected_by_sample.values()))
                ],
            },
            "payload_binding_stage": binding_stage.as_receipt(),
            "evidence_rail_half": {
                "calls": len(evidence_facts),
                "relpaths_per_call": 2,
                "routing": routing,
                "expected_routing": expected_routing,
                "verify_evidence_identity": "PASS",
                "verify_evidence_content_identity": "PASS",
                "why_this_is_here": (
                    "smoke --dry-run runs under core.driver.smoke._NoOpGate, which "
                    "accepts any plan and never touches the D1 evidence rail, so "
                    "the rail is driven here with a REAL FrozenCoreGate built from "
                    "this cell's own composed config. This is the property "
                    "precondition 1 of the preregistration created and the "
                    "accumulate-not-assign driver fix made observable: BOTH halves "
                    "are checked, against two different D1 layers"
                ),
            },
            "seal_half": {
                "manifest_status": manifest.get("status"),
                "manifest_study_commit": manifest.get("study_commit"),
                "manifest_study_repo_dirt": manifest.get("study_repo_dirt"),
                "manifest_split": manifest.get("split", {}).get("name"),
                "manifest_split_count": manifest.get("split", {}).get("count"),
                "manifest_scorers": manifest.get("scorers"),
                "verify_bundle": "PASS",
                "sealed_output_rows": outputs_rows,
                "declared_scorers": declared,
                "scorer_aggregate_keys": aggregates,
                "all_declared_scorers_produced_an_aggregate": True,
            },
        }

    arm_cell, twin_cell = (per_cell[str(cell["cell_id"])] for cell in cells)
    one_factor = {
        "same_arm": arm_cell["arm"] == twin_cell["arm"],
        "same_cap": (
            arm_cell["brief_max_entries_per_class"]
            == twin_cell["brief_max_entries_per_class"]
        ),
        "same_contact_count": (
            arm_cell["request_half"]["contacts"] == twin_cell["request_half"]["contacts"]
        ),
        "same_windows_per_call": (
            arm_cell["request_half"]["windows_per_call"]
            == twin_cell["request_half"]["windows_per_call"]
        ),
        "same_declared_scorers": (
            arm_cell["seal_half"]["declared_scorers"]
            == twin_cell["seal_half"]["declared_scorers"]
        ),
        "different_evidence_source": (
            arm_cell["evidence_source"] != twin_cell["evidence_source"]
        ),
        "different_evidence_ids": (
            arm_cell["request_half"]["evidence_ids"]
            != twin_cell["request_half"]["evidence_ids"]
        ),
    }
    if not all(one_factor.values()):
        raise SystemExit("the one-factor comparison failed: %r" % (one_factor,))

    document = {
        "schema": "saea-e21-kc-e1-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "for_flight_run_id": FLIGHT_RUN_ID,
        "study_commit": study_commit,
        "working_tree_clean": not dirty,
        "what_this_is": (
            "saea-driver smoke --dry-run for BOTH cells on a clean committed tree: "
            "the real compose, split verification, ExecutionPlan validation, "
            "evidence resolution, derivation registry, 90-second OBS slicing, "
            "request assembly under the arm's D2-frozen allowlist, bundle sealing, "
            "all five manifest scorers through core.scoring_batch and finalize -- "
            "against a fake transport and a no-op gate, plus the D1 evidence rail "
            "driven separately with a REAL gate because the no-op one skips it"
        ),
        "driver_run_id_suffix": args.driver_run_id_suffix,
        "why_the_driver_run_id_is_suffixed": (
            "the attempt store meters cumulatively across every attempt of a run "
            "id, and each invocation of this check tiles 5,322.108 audio seconds "
            "through core.driver.smoke._dry_run_transport. A stable driver run id "
            "therefore exhausts its own budget after a handful of invocations and "
            "the check fails for a reason unrelated to the cell. A per-invocation "
            "suffix is correct HERE and only here, because zero real contacts are "
            "made and there is no real spend for the rail to bound. The stable "
            "run_id above is what this receipt and the exposure ledger name"
        ),
        "plan_budget": {
            "planned_model_calls": PLAN_CALLS,
            "planned_speech_audio_seconds": PLAN_AUDIO_SECONDS,
            "planned_gpu_hours": PLAN_GPU_HOURS,
            "what_it_is_not": (
                "a spend registration. Zero real contacts are made: the transport "
                "is core.driver.smoke._dry_run_transport. The REAL metering rail "
                "still runs and is cumulative across every attempt of a run id, so "
                "the plan has to cover one attempt's 61 windows and 5,322.108 tiled "
                "audio seconds several times over or a second invocation of this "
                "check fails on an exhausted budget instead of returning a result"
            ),
        },
        "zero_contact": {
            "model_contacts": 0,
            "generated_tokens": 0,
            "servers_started": 0,
            "sockets_opened": 0,
            "llama_server_processes": 0,
            "gpu_seconds": 0,
            "fakes": [
                "core.driver.smoke._dry_run_transport",
                "core.driver.smoke._NoOpGate",
            ],
        },
        "population": {
            "dataset_fragment": args.dataset,
            "split_name": str(dataset_doc["split_name"]),
            "carrier_lock_key": str(dataset_doc["carrier_lock_key"]),
            "calls": sorted(arm_cell["request_half"]["windows_per_call"]),
            "windows": sum(arm_cell["request_half"]["windows_per_call"].values()),
            "construction_only": True,
            "why_construction_only": (
                "section 8 item 3 of the preregistration: an evaluation call's "
                "brief is the thing under test, and a dry run must not rehearse it"
            ),
            "carries_the_flight_fragments_d1_evidence_supplement": (
                supplement_matches_flight
            ),
        },
        "cells": per_cell,
        "one_factor_on_the_wire": one_factor,
        "not_certified_here": (
            "nothing about the model. A wire check proves the harness assembles, "
            "seals and scores the right request; what the frozen core does with "
            "that request is the flight's question, and the flight is not "
            "authorized by this receipt"
        ),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "wire-check.json"
    out_path.write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    log("WIRE CHECK PASS for both cells at study commit %s" % study_commit[:8])
    return 0


if __name__ == "__main__":
    sys.exit(main())
