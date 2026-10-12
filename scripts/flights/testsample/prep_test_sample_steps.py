#!/usr/bin/env python3
"""Model-free helper steps for ``scripts/flights/testsample/prep_test_sample.sh``.

Owner decision 156 of 2026-09-27 (``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``,
row 156; the owner's words, translated: "The preparation work may run ahead."): the three label-free
preparations of the SLURP test SAMPLE ``SLURP-TEST-SAMPLE-3010-V1`` may run before the dev-admitted
composed arm, each registered, countersigned under that row, and run on CPU where the registered
path allows. The MILESTONE read ids keep row 151's gate and are refused here outright.

This file is the sample's sibling of ``scripts/flights/batch/prep_generic_steps.py`` and REUSES it
rather than forking it: the generic module is imported by path, this roster's ``PreparationSet`` is
added to its table in memory, and its own ``runtime-config`` / ``materialise`` / ``alias-receipt`` /
``report`` steps run unchanged. Exactly one generic function is wrapped: ``build_runtime_config``,
because a ``final-report`` plan must carry the pinned ``owner_allowance`` and the generic document has
no such field (the generic file lives under ``scripts/flights/batch/`` and is left byte-identical).

Subcommands, each pure Python over committed bytes and sealed outputs -- no model, encoder,
tokenizer, scorer, GPU or network contact, no media byte opened, and no gold, answer, transcript or
score read:

``guard``          the launch refusals: allowance bytes and status, the milestone refusal, and the
                   root countersignature of every exposure row the stage touches.
``check``          ``guard`` plus the per-preparation contract checks the runtime itself will run
                   (composed config, plan validation, exposure preregistration, final-report
                   isolation, protocol and inventory pins), printed verbatim; exit 1 on a refusal.
``inventory``      step 2a: write the byte-reproducible source inventory create-only and refuse
                   unless it hashes to the protocol's pin; cross-check it against the FULL
                   inventory when that file is present.
``runtime-config`` step 2b's minted runtime config (generic step + ``owner_allowance``), then the
                   final-report isolation re-proof of the minted plan.
``materialise`` / ``alias-receipt`` / ``report``   the generic steps, verbatim.
``summary``        the per-stage summary receipt under ``prepared/``.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

REPO_DEFAULT = Path(__file__).resolve().parents[3]
DATA_DEFAULT = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
UMBRELLA_LOCK = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
)

SET_NAME = "test-sample-3010"
ROSTER_KEY = "test-sample-3010"
PREPROCESS_RUN = "SAEA-SN-TEST-SAMPLE-3010-PREPROCESS"
ENCODING_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1"
EXPORT_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1"
ALIAS_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-ALIAS-V1"
PREPARATION_RUN_IDS = (PREPROCESS_RUN, ENCODING_RUN, EXPORT_RUN)
STAGE_RUN_IDS = {
    "packets": (PREPROCESS_RUN,),
    "queries": (ENCODING_RUN, EXPORT_RUN),
    "all": PREPARATION_RUN_IDS,
}
EXPECTED_ROWS = {
    PREPROCESS_RUN: ("bounded-discovery-probe", 3010, 8207, 1.0),
    ENCODING_RUN: ("bounded-discovery-probe", 3010, 8207, 2.0),
    EXPORT_RUN: ("model-free-check", 0, 0, 0.0),
}
ALLOWANCE = {
    "path": "docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json",
    "sha256": "c2ae2c4eb2142b5aef27d85c04c7dcd55952c105b469fd195592c71cb6bb331b",
}
SPLIT_IDENTITY = "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9"
ROWS = 3010
PLANNED_SPEECH_SECONDS = 8207
PROTOCOL_RELPATH = (
    "configs/preparation/slurp-test-sample-3010-speech-query-encoding-protocol-v1.json"
)
ALIAS_TEMPLATE_RELPATH = (
    "configs/preparation/slurp-test-sample-3010-query-alias-v1.json"
)
EXPERIMENT_RELPATH = "configs/experiment/slurp-test-sample-3010-preprocess.json"
DATASET_RELPATH = "configs/dataset/slurp-speech-native-test-sample-3010.json"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-test-sample-3010-v1.json"
INVENTORY_RELPATH = (
    "coordination/slurp-test-sample-3010-speech-query-source-inventory-v1.json"
)
INVENTORY_SHA256 = "77fce38e3825dff6f4bb409e2c4839c34a6bb41b55735feafab72ffc10e07a19"
FULL_INVENTORY_RELPATH = (
    "coordination/slurp-test-full-speech-query-source-inventory-v1.json"
)
FULL_INVENTORY_SHA256 = (
    "c16ede61a994ef5b2920ab0b9a446203574ee7c731e4c8cae7e5a31e1306ca5f"
)
PACKET_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = "TEST-SAMPLE-3010-promotion.json"
SUMMARY_DIR = "prepared/slurp-test-sample-3010-preparations-v1"
LEDGER_RELPATH = "docs/exposure-ledger.md"
DRAFT_TOKEN = re.compile(r"\bdraft\b", re.IGNORECASE)
COUNTERSIGNED_TOKEN = re.compile(r"root countersigned", re.IGNORECASE)
MILESTONE_TOKEN = "MILESTONE"


class SampleRunRefusal(RuntimeError):
    """A launch or check refusal, printed verbatim."""


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - unreadable checkout
        raise SampleRunRefusal("cannot import %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_generic(repo_root: Path):
    """``prep_generic_steps`` with this roster's set added and the plan carrying the allowance."""

    generic = _load(
        "prep_generic_steps_testsample",
        Path(repo_root) / "scripts" / "flights" / "batch" / "prep_generic_steps.py",
    )
    generic.PREPARATION_SETS[SET_NAME] = generic.PreparationSet(
        name=SET_NAME,
        run_id=ENCODING_RUN,
        attempt="encode-v1",
        alias_run_id=ALIAS_RUN,
        export_row=EXPORT_RUN,
        protocol_relpath=PROTOCOL_RELPATH,
        alias_template_relpath=ALIAS_TEMPLATE_RELPATH,
        roster_relpath=ROSTER_RELPATH,
        dataset_relpath=DATASET_RELPATH,
        inventory_relpath=INVENTORY_RELPATH,
        inventory_sha256=INVENTORY_SHA256,
        vector_dir="vectors/slurp-test-sample-3010-v1",
        coordination_dir="coordination/slurp-test-sample-3010-query-encoding-v1",
        session_id="local-nemotron-slurp-test-sample-3010-query-v1",
        rows=ROWS,
        vector_width=2048,
        split_identity_hash=SPLIT_IDENTITY,
        split_role="final-report",
        planned_speech_audio_seconds=PLANNED_SPEECH_SECONDS,
        planned_gpu_hours=EXPECTED_ROWS[ENCODING_RUN][3],
    )
    original = generic.build_runtime_config

    def build_runtime_config_with_allowance(preparation, **kwargs):
        document = original(preparation, **kwargs)
        if preparation.name == SET_NAME:
            document["plan"]["owner_allowance"] = dict(ALLOWANCE)
        return document

    generic.build_runtime_config = build_runtime_config_with_allowance
    return generic


def load_derive(repo_root: Path):
    return _load(
        "derive_test_sample_preparations_steps",
        Path(repo_root)
        / "scripts"
        / "flights"
        / "testsample"
        / "derive_test_sample_preparations.py",
    )


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------- guard


def check_allowance(repo_root: Path) -> dict:
    path = Path(repo_root) / ALLOWANCE["path"]
    measured = sha256_of(path)
    if measured != ALLOWANCE["sha256"]:
        raise SampleRunRefusal(
            "allowance %s hashes to %s, not the pinned %s"
            % (ALLOWANCE["path"], measured, ALLOWANCE["sha256"])
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("status") != "authorised":
        raise SampleRunRefusal(
            "allowance status is %r, not 'authorised'" % document.get("status")
        )
    if (document.get("split") or {}).get("split_identity_hash") != SPLIT_IDENTITY:
        raise SampleRunRefusal("allowance binds a different split identity")
    preparations = set(document.get("preparation_run_ids") or ())
    reads = set(document.get("read_run_ids") or ())
    for run_id in PREPARATION_RUN_IDS:
        if run_id not in preparations:
            raise SampleRunRefusal(
                "%s is not a preparation run id of the allowance" % run_id
            )
        if run_id in reads:
            raise SampleRunRefusal(
                "%s is a READ run id; row 151's gate holds it" % run_id
            )
    return document


def refuse_milestones(
    repo_root: Path, run_ids: Sequence[str], allowance: Mapping
) -> None:
    """No milestone read id may appear in anything this runner launches or binds."""

    reads = set(allowance.get("read_run_ids") or ())
    for run_id in run_ids:
        if MILESTONE_TOKEN in run_id or run_id in reads:
            raise SampleRunRefusal(
                "milestone read id %s refused: owner decision 156 lifts row 151's gate for the three "
                "preparations only" % run_id
            )
    for relpath in (
        EXPERIMENT_RELPATH,
        PROTOCOL_RELPATH,
        ALIAS_TEMPLATE_RELPATH,
        DATASET_RELPATH,
    ):
        text = (Path(repo_root) / relpath).read_text(encoding="utf-8")
        if MILESTONE_TOKEN in text or any(read_id in text for read_id in reads):
            raise SampleRunRefusal("%s names a milestone read id; refused" % relpath)


def ledger_rows(repo_root: Path, ledger: Path | None = None) -> list[Mapping[str, str]]:
    from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables

    path = Path(ledger) if ledger is not None else Path(repo_root) / LEDGER_RELPATH
    return _parse_ledger_tables(path.read_text(encoding="utf-8"))


def row_refusals(
    rows: Sequence[Mapping[str, str]], run_ids: Sequence[str]
) -> list[str]:
    """Every reason a row may not launch yet, in the order a reader fixes them."""

    refusals = []
    for run_id in run_ids:
        matched = [row for row in rows if row.get("run/experiment id") == run_id]
        if len(matched) != 1:
            refusals.append(
                "%s: %d exposure rows, need exactly one" % (run_id, len(matched))
            )
            continue
        row = matched[0]
        profile, calls, seconds, gpu_hours = EXPECTED_ROWS[run_id]
        if row.get("execution profile") != profile:
            refusals.append(
                "%s: execution profile %r, registered %r"
                % (run_id, row.get("execution profile"), profile)
            )
        if (
            row.get("split role") != "final-report"
            or row.get("split identity hash") != SPLIT_IDENTITY
        ):
            refusals.append(
                "%s: split role / identity differ from the sample's" % run_id
            )
        if str(row.get("consumed", "")).strip().lower() != "no":
            refusals.append(
                "%s: row is consumed; a sealed preparation is never re-run" % run_id
            )
        try:
            numbers = (
                int(row["calls"]),
                int(row["speech audio seconds"]),
                float(row["gpu hours"]),
            )
        except (KeyError, ValueError):
            numbers = None
        if numbers != (calls, seconds, gpu_hours):
            refusals.append(
                "%s: budgets %r, registered %r"
                % (run_id, numbers, (calls, seconds, gpu_hours))
            )
        text = " ".join(str(value) for value in row.values())
        if DRAFT_TOKEN.search(text):
            refusals.append(
                "%s: the exposure row is marked draft (root countersignature pending); owner decision "
                "156 requires it countersigned before the step runs" % run_id
            )
        elif not COUNTERSIGNED_TOKEN.search(text):
            refusals.append(
                "%s: the exposure row carries no root countersignature" % run_id
            )
    return refusals


def guard(repo_root: Path, stage: str, ledger: Path | None = None) -> list[str]:
    allowance = check_allowance(repo_root)
    run_ids = STAGE_RUN_IDS[stage]
    refuse_milestones(repo_root, run_ids, allowance)
    return row_refusals(ledger_rows(repo_root, ledger), run_ids)


def step_guard(args) -> int:
    refusals = guard(Path(args.repo_root), args.stage, args.ledger)
    for message in refusals:
        print("REFUSED: %s" % message)
    if refusals:
        return 1
    print(
        "GUARD PASS: stage %s; rows %s countersigned; allowance authorised; no milestone id"
        % (args.stage, ", ".join(STAGE_RUN_IDS[args.stage]))
    )
    return 0


# ---------------------------------------------------------------------------------------- check


def _exposure_checks(repo_root: Path, data_root: Path):
    from speech_aware_evidence_acquisition.contracts.tool_plan import (
        _ToolPlanExposureChecks,
    )

    checks = _ToolPlanExposureChecks(
        source_root=Path(repo_root), exposure_ledger=Path(repo_root) / LEDGER_RELPATH
    )
    checks.data_root = Path(data_root)
    return checks


def check_preprocess(repo_root: Path, data_root: Path) -> list[str]:
    """What ``scripts/slurp_evo_fold_preprocess.py --run`` validates before its first contact,
    minus everything that opens a media file or a model receipt."""

    from speech_aware_evidence_acquisition.contracts import (
        ExecutionPlan,
        require_owner_split_allowance,
    )

    driver = _load(
        "slurp_evo_fold_preprocess_testsample",
        Path(repo_root) / "scripts" / "slurp_evo_fold_preprocess.py",
    )
    spec = driver.PREPROCESS_ROSTERS[ROSTER_KEY]
    composed = driver.compose(
        Path(repo_root),
        spec.sidecar_fragment,
        spec.dataset_fragment,
        driver.BASELINE_FRAGMENT,
        spec.experiment_fragment,
    )
    values = composed.values
    lines = [
        "composed config %s (%s)"
        % (composed.config_hash, ", ".join(composed.fragments.values()))
    ]
    if values["experiment_id"] != spec.run_id or spec.run_id != PREPROCESS_RUN:
        raise SampleRunRefusal("experiment fragment names %r" % values["experiment_id"])
    if (
        values["split_role"] != "final-report"
        or values["split_identity_hash"] != SPLIT_IDENTITY
    ):
        raise SampleRunRefusal(
            "the dataset fragment is not the sample's final-report view"
        )
    slots = driver._server_slots(values, spec.sidecar_fragment)
    if slots > 8:
        raise SampleRunRefusal(
            "the sidecar serves -np %d, above the 8-worker cap" % slots
        )
    if "8080" in json.dumps(values.get("server_args")) or ":8080" in str(
        values.get("base_url")
    ):
        raise SampleRunRefusal("the sidecar fragment names port 8080")
    require_owner_split_allowance(
        run_id=spec.run_id,
        execution_profile=str(values["execution_profile"]),
        carrier_lock_key="slurp",
        split_identity_hash=SPLIT_IDENTITY,
        owner_allowance=values.get("owner_allowance"),
        source_root=Path(repo_root),
    )
    lines.append("owner allowance PASS (%s, authorised)" % ALLOWANCE["sha256"][:12])
    plan = ExecutionPlan(
        run_id=spec.run_id,
        execution_profile=str(values["execution_profile"]),
        carrier_lock_key="slurp",
        split_role=spec.split_role,
        split_identity_hash=SPLIT_IDENTITY,
        planned_model_calls=spec.plan_calls,
        planned_gpu_hours=spec.plan_gpu_hours,
        planned_speech_audio_seconds=spec.plan_speech_seconds,
        protocol_hash=composed.config_hash,
        attempt_id=spec.default_attempt_id,
        owner_allowance=values.get("owner_allowance"),
    ).validate(source_root=Path(repo_root))
    lines.append(
        "ExecutionPlan PASS (%d calls / %d speech s / %.1f GPU h, sidecar -np %d, base_url %s)"
        % (
            plan.planned_model_calls,
            plan.planned_speech_audio_seconds,
            plan.planned_gpu_hours,
            slots,
            values.get("base_url"),
        )
    )
    checks = _exposure_checks(repo_root, data_root)
    from speech_aware_evidence_acquisition.data.lock import load_lock

    checks._require_exposure_preregistration(plan, load_lock(UMBRELLA_LOCK))
    lines.append(
        "exposure preregistration PASS (profile, split, identity, carrier, consumed=no, budgets)"
    )
    checks._require_final_report_isolation(plan, None)
    lines.append(
        "final-report isolation PASS (partition-aware disjointness, attempt budget)"
    )
    return lines


def runtime_plan_document(repo_root: Path, generic) -> dict:
    preparation = generic.PREPARATION_SETS[SET_NAME]
    head = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return generic.build_runtime_config(
        preparation,
        study_head=head,
        protocol_sha256=sha256_of(Path(repo_root) / PROTOCOL_RELPATH),
        umbrella_lock=str(UMBRELLA_LOCK),
        umbrella_lock_sha256=sha256_of(UMBRELLA_LOCK),
    )


def check_encoding(repo_root: Path, data_root: Path) -> list[str]:
    """What ``core.speech_preparation_runtime.run_preparation`` validates before its first contact,
    minus the media re-hash and the encoder-directory re-hash, which belong to the run."""

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.contracts.tool_plan import (
        assert_registered_tool_plan,
    )
    from speech_aware_evidence_acquisition.core.preparation_speech_queries import (
        segment_plan,
    )

    generic = load_generic(repo_root)
    derive = load_derive(repo_root)
    document = runtime_plan_document(repo_root, generic)
    plan = ExecutionPlan(**document["plan"]).validate()
    lines = [
        "ExecutionPlan PASS (%d calls / %d speech s / %.1f GPU h, owner_allowance pinned)"
        % (
            plan.planned_model_calls,
            plan.planned_speech_audio_seconds,
            plan.planned_gpu_hours,
        )
    ]
    assert_registered_tool_plan(
        plan=plan,
        source_root=Path(repo_root),
        exposure_ledger=Path(repo_root) / LEDGER_RELPATH,
        umbrella_lock=UMBRELLA_LOCK,
        umbrella_lock_sha256=document["umbrella_lock"]["sha256"],
        protocol_path=Path(repo_root) / PROTOCOL_RELPATH,
        protocol_sha256=document["protocol"]["sha256"],
    )
    lines.append(
        "tool-plan admission PASS (WSL, lock, protocol %s, exposure preregistration)"
        % document["protocol"]["sha256"][:12]
    )
    _exposure_checks(repo_root, data_root)._require_final_report_isolation(plan, None)
    lines.append(
        "final-report isolation PASS (the tool-plan admission does not run it; this runner does)"
    )
    protocol = json.loads(
        (Path(repo_root) / PROTOCOL_RELPATH).read_text(encoding="utf-8")
    )
    raw = derive.derive_inventory_bytes(Path(repo_root))
    digest = hashlib.sha256(raw).hexdigest()
    if not digest == protocol["sources"]["sha256"] == INVENTORY_SHA256:
        raise SampleRunRefusal(
            "the derived inventory hashes to %s, not the protocol's pin" % digest
        )
    if protocol["roster_sha256"] != sha256_of(Path(repo_root) / ROSTER_RELPATH):
        raise SampleRunRefusal(
            "the protocol's roster_sha256 is not the committed roster receipt"
        )
    rows = json.loads(raw)["rows"]
    spans = {
        (
            row["audio_sha256"],
            row["source_frames"],
            row["source_sample_rate_hz"],
            span["start_frame"],
            span["end_frame"],
        )
        for row in rows
        for span in segment_plan(
            row["source_frames"],
            row["source_sample_rate_hz"],
            max_seconds=protocol["max_seconds"],
            overlap_seconds=protocol["overlap_seconds"],
        )
    }
    seconds = sum((end - start) / rate for _sha, _frames, rate, start, end in spans)
    if (
        len(spans) != protocol["expected_unique_spans"]
        or len(spans) > plan.planned_model_calls
    ):
        raise SampleRunRefusal(
            "the inventory plans %d spans, not %d"
            % (len(spans), protocol["expected_unique_spans"])
        )
    if seconds > plan.planned_speech_audio_seconds:
        raise SampleRunRefusal(
            "the inventory plans %.3f s, above %d"
            % (seconds, plan.planned_speech_audio_seconds)
        )
    lines.append(
        "inventory pin PASS (%s, %d rows, %d spans, %.6f s <= %d)"
        % (
            digest[:12],
            len(rows),
            len(spans),
            seconds,
            plan.planned_speech_audio_seconds,
        )
    )
    template = json.loads(
        (Path(repo_root) / ALIAS_TEMPLATE_RELPATH).read_text(encoding="utf-8")
    )
    generic.materialise_alias_config(
        template, queries_sha256="a" * 64, receipt_sha256="b" * 64
    )
    lines.append(
        "alias template materialisable through prep_generic_steps.materialise_alias_config"
    )
    return lines


def check_export(repo_root: Path) -> list[str]:
    script = Path(repo_root) / "scripts" / "build_slurp_query_content_derivative.py"
    if not script.is_file():
        raise SampleRunRefusal(
            "scripts/build_slurp_query_content_derivative.py is missing"
        )
    return [
        "zero-contact CLI present; it constructs no ExecutionPlan (model-free-check)"
    ]


def step_check(args) -> int:
    repo_root, data_root = Path(args.repo_root).resolve(), Path(args.data_root)
    refused = False
    try:
        allowance = check_allowance(repo_root)
        refuse_milestones(repo_root, PREPARATION_RUN_IDS, allowance)
        print(
            "allowance %s authorised; milestone ids absent from every stage and config"
            % ALLOWANCE["path"]
        )
    except SampleRunRefusal as error:
        print("REFUSED: %s" % error)
        return 1
    rows = ledger_rows(repo_root)
    for run_id, checker in (
        (PREPROCESS_RUN, lambda: check_preprocess(repo_root, data_root)),
        (ENCODING_RUN, lambda: check_encoding(repo_root, data_root)),
        (EXPORT_RUN, lambda: check_export(repo_root)),
    ):
        print("== %s" % run_id)
        try:
            for line in checker():
                print("   %s" % line)
        except Exception as error:  # noqa: BLE001 -- every refusal is printed verbatim
            refused = True
            print("   REFUSED (%s): %s" % (type(error).__name__, error))
        for message in row_refusals(rows, (run_id,)):
            refused = True
            print("   REFUSED: %s" % message)
    return 1 if refused else 0


# ------------------------------------------------------------------------------ run-time steps


def step_inventory(args) -> int:
    repo_root, data_root = Path(args.repo_root).resolve(), Path(args.data_root)
    derive = load_derive(repo_root)
    protocol = json.loads((repo_root / PROTOCOL_RELPATH).read_text(encoding="utf-8"))
    raw = derive.derive_inventory_bytes(repo_root)
    digest = hashlib.sha256(raw).hexdigest()
    if not digest == protocol["sources"]["sha256"] == INVENTORY_SHA256:
        raise SampleRunRefusal(
            "derived inventory %s differs from the protocol's pin" % digest
        )
    target = data_root / INVENTORY_RELPATH
    if Path(protocol["sources"]["path"]) != target:
        raise SampleRunRefusal(
            "protocol sources path %s is not %s" % (protocol["sources"]["path"], target)
        )
    state = derive.write_create_only(target, raw)
    print("2a inventory %s %s sha256 %s" % (state, target, digest))
    full = data_root / FULL_INVENTORY_RELPATH
    if full.is_file() and sha256_of(full) == FULL_INVENTORY_SHA256:
        by_id = {
            row["id"]: row
            for row in json.loads(full.read_text(encoding="utf-8"))["rows"]
        }
        derived = json.loads(raw)["rows"]
        differing = [row["id"] for row in derived if by_id.get(row["id"]) != row]
        if differing:
            raise SampleRunRefusal(
                "%d derived rows differ from the media-measured FULL inventory (first %s)"
                % (len(differing), differing[:3])
            )
        print(
            "2a cross-check PASS: all %d rows equal the media-measured FULL inventory %s"
            % (len(derived), FULL_INVENTORY_SHA256[:12])
        )
    else:
        print(
            "2a cross-check skipped: the FULL inventory is absent or drifted; the runtime's own "
            "per-file re-hash and header check still run before the first forward"
        )
    return 0


def step_runtime_config(args) -> int:
    repo_root = Path(args.repo_root).resolve()
    generic = load_generic(repo_root)
    rc = generic.main(
        [
            "runtime-config",
            "--set",
            SET_NAME,
            "--repo-root",
            str(repo_root),
            "--data-root",
            str(args.data_root),
            "--umbrella-lock",
            str(UMBRELLA_LOCK),
        ]
    )
    if rc != 0:
        return rc
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan

    minted = (
        Path(args.data_root) / generic.PREPARATION_SETS[SET_NAME].runtime_config_relpath
    )
    plan = ExecutionPlan(
        **json.loads(minted.read_text(encoding="utf-8"))["plan"]
    ).validate()
    _exposure_checks(repo_root, Path(args.data_root))._require_final_report_isolation(
        plan, None
    )
    print(
        "# final-report isolation PASS for the minted plan (attempt %s)"
        % plan.attempt_id
    )
    return 0


def step_generic(args) -> int:
    generic = load_generic(Path(args.repo_root).resolve())
    argv = [args.step, "--set", SET_NAME, "--data-root", str(args.data_root)]
    if args.step == "materialise":
        argv += ["--repo-root", str(Path(args.repo_root).resolve())]
    if args.step == "report":
        argv += ["--roster-sha256", sha256_of(Path(args.repo_root) / ROSTER_RELPATH)]
    return generic.main(argv)


def _entry(path: Path) -> dict:
    return {"path": str(path), "sha256": sha256_of(path) if path.is_file() else None}


def step_summary(args) -> int:
    repo_root, data_root = Path(args.repo_root).resolve(), Path(args.data_root)
    head = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    document: dict = {
        "schema": "saea-slurp-test-sample-preparation-summary-v1",
        "stage": args.stage,
        "study_head": head,
        "owner_decision": "156 (2026-09-27): the three label-free preparations run ahead; milestone reads keep row 151's gate",
        "allowance": dict(ALLOWANCE),
        "split_identity_hash": SPLIT_IDENTITY,
        "rows": ROWS,
        "run_ids": list(STAGE_RUN_IDS[args.stage]),
        "reads_labels": False,
    }
    if args.stage == "packets":
        receipt = PACKET_ROOT / PROMOTION_RECEIPT
        entry = _entry(receipt)
        if entry["sha256"] is None:
            raise SampleRunRefusal("no promotion receipt at %s" % receipt)
        promoted = json.loads(receipt.read_text(encoding="utf-8"))
        entry["count"] = promoted.get("count")
        if entry["count"] != ROWS:
            raise SampleRunRefusal(
                "promotion receipt count %r, expected %d" % (entry["count"], ROWS)
            )
        document["promotion_receipt"] = entry
    else:
        generic = load_generic(repo_root)
        preparation = generic.PREPARATION_SETS[SET_NAME]
        encode = json.loads(
            (data_root / preparation.encode_receipt_relpath).read_text(encoding="utf-8")
        )
        if encode.get("logical_encoder_contacts") != ROWS:
            raise SampleRunRefusal(
                "step-2b receipt records %r contacts"
                % encode.get("logical_encoder_contacts")
            )
        document["encoder_contacts"] = encode.get("logical_encoder_contacts")
        document["outputs"] = {
            label: _entry(data_root / relpath)
            for label, relpath in (
                ("source_inventory", INVENTORY_RELPATH),
                ("encode_receipt", preparation.encode_receipt_relpath),
                ("queries", preparation.queries_relpath),
                ("alias_receipt", preparation.alias_receipt_relpath),
                ("segments", preparation.segments_relpath),
                ("content", preparation.content_relpath),
                ("content_provenance", preparation.provenance_relpath),
            )
        }
    raw = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target = data_root / SUMMARY_DIR / ("summary-%s.json" % args.stage)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() != raw:
        raise SampleRunRefusal("%s exists with different bytes" % target)
    if not target.exists():
        with io.open(target, "xb") as handle:
            handle.write(raw)
    print(raw.decode("utf-8"), end="")
    print("SUMMARY %s sha256 %s" % (target, hashlib.sha256(raw).hexdigest()))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo-root", default=str(REPO_DEFAULT))
    parser.add_argument("--data-root", default=str(DATA_DEFAULT))
    sub = parser.add_subparsers(dest="step", required=True)
    guard_parser = sub.add_parser("guard")
    guard_parser.add_argument("--stage", choices=sorted(STAGE_RUN_IDS), required=True)
    guard_parser.add_argument("--ledger", type=Path, default=None)
    guard_parser.set_defaults(handler=step_guard)
    sub.add_parser("check").set_defaults(handler=step_check)
    sub.add_parser("inventory").set_defaults(handler=step_inventory)
    sub.add_parser("runtime-config").set_defaults(handler=step_runtime_config)
    for name in ("materialise", "alias-receipt", "report"):
        sub.add_parser(name).set_defaults(handler=step_generic)
    summary = sub.add_parser("summary")
    summary.add_argument("--stage", choices=("packets", "queries"), required=True)
    summary.set_defaults(handler=step_summary)
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except SampleRunRefusal as error:
        print("REFUSED: %s" % error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
