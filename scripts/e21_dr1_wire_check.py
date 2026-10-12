#!/usr/bin/env python3
"""Contact-free, socket-free wire check for the three DR-1 cells.

Exposure row ``SAEA-E21-MF-DR1-PREP-V1`` (``model-free-check``). **Zero model,
GPU, server, socket, tokenizer, tool, embedder, network and paid-API contacts.**
Nothing here constructs a transport, a gate, an attempt store or a
``core.model.FrozenCoreAdapter``; no audio file is opened and no MP3 is decoded,
so the pinned absence of ``ffmpeg`` is preserved.

Four halves, reported separately because they fail for different reasons.

``config``
    Real ``core.config.compose`` on all three cells and on the KC-E1f cell they
    derive their harness from. Reports each composed ``config_hash`` and
    ``protocol_hash`` against the same split identity, and the key-by-key diff
    that IS the one-factor claim: DR-1c against DR-1f must differ in exactly
    the delivery rule and its parameters, DR-1c against DR-1s in exactly the
    bound snapshot, and DR-1c against KC-E1f in exactly the keys a
    knowledge-free refresh is entitled to move.

``request``
    The real ``reproduction.repair_loop.RepairWindowHook`` over both real,
    hash-verified bindings, on a sample of calls. Four properties, on real
    sealed bytes:

    1. the rendered instruction EQUALS the fragment's own instruction plus the
       frozen frame filled with THAT window's draft -- an equality, so it pins
       the frame, the join and the window-to-draft mapping in one assertion;
    2. **each arm's floor is its own draft.** When every pass-2 answer is
       refused, the unit-draft cells deliver the sealed OBS-E1 hypothesis for
       the call byte for byte, and the self-draft twin delivers the sealed
       COMPARATOR's, byte for byte. DR-1's floor is therefore OBS-E1 and the
       twin's is the comparator, and that difference is measured here rather
       than argued;
    3. both delivery rules agree on every refusal -- an empty response and an
       empty draft deliver the same bytes under both -- so the DR-1c/DR-1f
       contrast is a contrast about EDITS;
    4. every window of the call is delivered exactly once.

``delivery``
    A model-free DIVERGENCE PROBE, clearly labelled as a probe. It feeds each
    window's hook the COMPARATOR's own sealed hypothesis as if it were the
    pass-2 response, and reports what each rule would then deliver: how often
    the bounded rule refuses and by which reason, how many substitutions it
    accepts, and how many whitespace tokens the free rule would move. It
    predicts nothing about the core; it measures how far the two rules are
    apart on real text of exactly the kind a refresh returns, which is the
    quantity the family's guards are set against.

``payload``
    The shared ``rails.core_client.payload_binding_stage`` over the cells' own
    44-row roster, through the real carrier root, so the family is reported
    wire-ready only if its payloads actually bind.

Usage (WSL2)::

    python scripts/e21_dr1_wire_check.py --out-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

RUN_ID = "SAEA-E21-MF-DR1-PREP-V1"
PREREGISTRATION = (
    "docs/readiness/2026-09-09-e21-draft-then-refresh-dr1-v1-preregistration.md"
)
EXPERIMENT = "e21-draft-then-refresh-dr1-v1"
KC_E1F_EXPERIMENT = "e21-kc-e1f-repair-44-v1"
SPLITS = REPO / "docs" / "receipts" / "splits.json"
FULL44_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)
COMPARATOR_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
COMPARATOR_ATTEMPT = "attempt-20260904T233816Z-bcd338"
UNIT_RUN = "SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1"
UNIT_ATTEMPT = "attempt-20260908T150858Z-c597a8"

#: How many calls the request and delivery halves drive through the real hook.
#: Their properties are per call and byte-exact, so a sample is a proof on
#: those calls and a spot check on the rest.
SAMPLE_CALLS = 4

DEFAULT_DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR",
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
)


def log(message: str) -> None:
    print(message, flush=True)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class _RosterAudioRef:
    path: str


@dataclass(frozen=True)
class _RosterSample:
    sample_id: str
    audio_ref: _RosterAudioRef
    audio_seconds: float


@dataclass(frozen=True)
class _Cut:
    start_seconds: float
    end_seconds: float


def _documentary(key: str) -> bool:
    """A key that exists to explain a fragment rather than to steer it."""

    return key.startswith("why_") or key in {
        "what_this_is",
        "composes_but_is_not_permission",
        "composes_since",
        "scorer_basis",
    }


def _baseline_fragment(name: str) -> dict:
    return json.loads(
        (REPO / "configs" / "baseline" / f"{name}.json").read_text(encoding="utf-8")
    )


def read_outputs_text(path: Path) -> dict[str, str]:
    return {
        str(row["sample_id"]): str(row["text"])
        for row in (
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.core.base import declared_derived_media_roots
    from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
    from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
        binding_from_values,
        load_predecessor_binding,
    )
    from speech_aware_evidence_acquisition.core.repair_alignment import (
        accept_entity_repair,
        accept_free_refresh,
        summarize_outcomes,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.rails.core_client import payload_binding_stage
    from speech_aware_evidence_acquisition.reproduction.repair_loop import (
        REPAIR_FRAMES,
        RepairWindowHook,
    )

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is dirty; a wire check certifies committed bytes:\n" + dirty
        )
    study_commit = git("rev-parse", "HEAD")
    log("%s tree at %s" % ("DIRTY (allowed)" if dirty else "clean", study_commit[:8]))

    failures: list[str] = []

    # ------------------------------------------------------------------
    # 1. config
    # ------------------------------------------------------------------
    experiment_doc = load_json(REPO / "configs" / "experiment" / f"{EXPERIMENT}.json")
    splits = load_json(SPLITS)
    composed: dict[str, Any] = {}
    for cell in experiment_doc["cells"]:
        composed[str(cell["cell_id"])] = (
            cell,
            compose(
                REPO,
                str(cell["model_fragment"]),
                str(cell["dataset_fragment"]),
                str(cell["baseline_fragment"]),
                EXPERIMENT,
            ),
        )
    kc_doc = load_json(REPO / "configs" / "experiment" / f"{KC_E1F_EXPERIMENT}.json")
    kc_cell = kc_doc["cells"][0]
    kc_composed = compose(
        REPO,
        str(kc_cell["model_fragment"]),
        str(kc_cell["dataset_fragment"]),
        str(kc_cell["baseline_fragment"]),
        KC_E1F_EXPERIMENT,
    )

    identities: dict[str, dict[str, str]] = {}
    for cell_id, (_cell, document) in composed.items():
        values = document.values
        split_block = splits["splits"][str(values["split_name"])]
        if str(split_block["carrier_lock_key"]) != str(values["carrier_lock_key"]):
            failures.append(f"{cell_id}: composed carrier is not the split's own")
        identities[cell_id] = {
            "config_hash": document.config_hash,
            "protocol_hash": protocol_hash(
                document.config_hash,
                str(values["arm"]),
                str(split_block["identity_hash"]),
            ),
            "split_identity_hash": str(split_block["identity_hash"]),
        }
        log(
            "composed %-36s config=%s protocol=%s"
            % (
                cell_id,
                document.config_hash[:16],
                identities[cell_id]["protocol_hash"][:16],
            )
        )

    constrained_id, free_id, twin_id = list(composed)

    def functional_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
        keys = sorted(set(left) | set(right))
        return [
            key
            for key in keys
            if not _documentary(key) and left.get(key) != right.get(key)
        ]

    fragments = {
        cell_id: _baseline_fragment(str(cell["baseline_fragment"]))
        for cell_id, (cell, _document) in composed.items()
    }
    kc_fragment = _baseline_fragment(str(kc_cell["baseline_fragment"]))

    c_vs_f = functional_diff(fragments[constrained_id], fragments[free_id])
    if c_vs_f != ["response_postprocessor", "response_postprocessor_params"]:
        failures.append(
            "DR-1c and DR-1f must differ in exactly the delivery rule and its "
            f"parameters; they differ in {c_vs_f}"
        )
    c_vs_s = functional_diff(fragments[constrained_id], fragments[twin_id])
    if c_vs_s != ["predecessor_snapshot"]:
        failures.append(
            f"DR-1c and DR-1s must differ in exactly predecessor_snapshot; they differ in {c_vs_s}"
        )
    c_vs_kc = functional_diff(fragments[constrained_id], kc_fragment)
    expected_vs_kc = {
        "arm",
        "brief_max_entries_per_class",
        "evidence_source",
        "predecessor_snapshot",
        "repair_frame",
        "task_instruction",
    }
    unexpected = [key for key in c_vs_kc if key not in expected_vs_kc]
    if unexpected:
        failures.append(
            "DR-1c's baseline fragment differs from KC-E1f's in unexpected keys: "
            f"{unexpected}"
        )
    # The serving geometry is a SEPARATE, named difference, never folded into
    # the one-factor claim: DR-1 projects np6 where KC-E1f flew np4, and a
    # prompt fit decides it before the first flight contact.
    geometry = {
        "dr1_model_fragment": str(composed[constrained_id][0]["model_fragment"]),
        "kc_e1f_model_fragment": str(kc_cell["model_fragment"]),
        "dr1_server_args": composed[constrained_id][1].values.get("server_args"),
        "kc_e1f_server_args": kc_composed.values.get("server_args"),
    }
    if len({str(cell["model_fragment"]) for cell, _d in composed.values()}) != 1:
        failures.append("the three cells do not share a serving geometry")
    log(f"functional diff DR-1c vs DR-1f: {c_vs_f}")
    log(f"functional diff DR-1c vs DR-1s: {c_vs_s}")
    log(f"functional diff DR-1c vs KC-E1f: {c_vs_kc}")

    # The instruction property the fragments claim in prose, asserted.
    comparator_instruction = _baseline_fragment("e21-buf90-zero-locked-scored4")[
        "task_instruction"
    ]
    dr1_instruction = str(fragments[constrained_id]["task_instruction"])
    if not dr1_instruction.endswith(comparator_instruction):
        failures.append(
            "the DR-1 instruction does not END with the comparator's own instruction "
            "byte for byte"
        )
    if len({str(f["task_instruction"]) for f in fragments.values()}) != 1:
        failures.append("the three cells do not share one task_instruction")

    # ------------------------------------------------------------------
    # 2. request: the real hook over both real bindings
    # ------------------------------------------------------------------
    roster = load_json(FULL44_ROSTER)
    roster_ids = [str(call["sample_id"]) for call in roster["calls"]]
    sealed_text = {
        "comparator": read_outputs_text(
            args.data_root
            / "runs"
            / COMPARATOR_RUN
            / COMPARATOR_ATTEMPT
            / f"{COMPARATOR_RUN}.outputs.jsonl"
        ),
        "unit": read_outputs_text(
            args.data_root / "runs" / UNIT_RUN / f"{UNIT_RUN}.outputs.jsonl"
        ),
    }

    snapshots: dict[str, Any] = {}
    for cell_id, (_cell, document) in composed.items():
        relpath, digest = binding_from_values(document.values)
        if relpath not in snapshots:
            snapshots[relpath] = load_predecessor_binding(
                REPO / "docs" / relpath, args.data_root, expected_receipt_sha256=digest
            )
        log(
            "  binding %-58s run=%s windows=%d"
            % (relpath, snapshots[relpath].run_id, snapshots[relpath].window_count)
        )

    def bounded(pass1: str, response: str):
        return accept_entity_repair(
            pass1,
            response,
            max_span_tokens=4,
            min_anchor_ratio=0.6,
            max_substituted_fraction=0.1,
        )

    RULES = {
        "e21-entity-repair-substitutions-v1": bounded,
        "e21-free-refresh-delivery-v1": accept_free_refresh,
    }

    request_rows: list[dict[str, Any]] = []
    for cell_id, (_cell, document) in composed.items():
        values = document.values
        relpath, _digest = binding_from_values(values)
        snapshot = snapshots[relpath]
        rule = RULES[str(values["response_postprocessor"])]
        frame = REPAIR_FRAMES[str(values["repair_frame"])]
        instruction_base = str(values["task_instruction"])
        floor_run = "unit" if snapshot.run_id == UNIT_RUN else "comparator"
        for sample_id in roster_ids[:SAMPLE_CALLS]:
            drafts = snapshot.for_sample(sample_id)
            hook = RepairWindowHook(
                sample_id=sample_id,
                predecessors=drafts,
                frame=frame,
                rule=rule,
                units=None,
            )
            instruction_ok = True
            delivered: list[str] = []
            for iteration, draft in enumerate(drafts):
                cut = _Cut(draft.start_seconds, draft.end_seconds)
                rendered = hook.instruction(
                    iteration=iteration, record=cut, default=instruction_base
                )
                expected = "%s\n\n%s" % (
                    instruction_base,
                    frame.format(predecessor=draft.text),
                )
                if rendered != expected:
                    instruction_ok = False
                span, _fields = hook.accept(
                    iteration=iteration,
                    record=cut,
                    transcript="",
                    saturated=False,
                    skipped=False,
                )
                delivered.append(span)
            rebuilt = " ".join(span for span in delivered if span)
            sealed = sealed_text[floor_run][sample_id]
            if not instruction_ok:
                failures.append(
                    f"{cell_id}/{sample_id}: a rendered instruction is not the "
                    "fragment's instruction plus the frozen frame"
                )
            if rebuilt != sealed:
                failures.append(
                    f"{cell_id}/{sample_id}: a fully refused pass 2 did not reproduce "
                    f"the sealed {floor_run} hypothesis ({len(rebuilt)} chars vs "
                    f"{len(sealed)})"
                )
            if len(delivered) != len(drafts):
                failures.append(
                    f"{cell_id}/{sample_id}: {len(delivered)} windows delivered for "
                    f"{len(drafts)} bound"
                )
            request_rows.append(
                {
                    "cell_id": cell_id,
                    "sample_id": sample_id,
                    "binding_relpath": relpath,
                    "floor_run": floor_run,
                    "windows": len(drafts),
                    "windows_delivered": len(delivered),
                    "uncontacted_windows": hook.uncontacted_windows,
                    "empty_drafts": sum(1 for draft in drafts if not draft.text),
                    "instruction_is_the_fragment_plus_the_frame": instruction_ok,
                    "refused_delivery_equals_the_sealed_floor": rebuilt == sealed,
                    "sealed_floor_sha256": hashlib.sha256(
                        sealed.encode("utf-8")
                    ).hexdigest(),
                    "refusal_ledger": summarize_outcomes(hook.outcomes),
                }
            )
            log(
                "  request %-36s %s: %d windows, floor=%s rebuild %s"
                % (
                    cell_id,
                    sample_id,
                    len(drafts),
                    floor_run,
                    "PASS" if rebuilt == sealed else "FAIL",
                )
            )

    # Both rules must agree on every refusal, or the DR-1c/DR-1f contrast is
    # not a contrast about edits.
    agree_rows: list[dict[str, Any]] = []
    unit_relpath, _ = binding_from_values(composed[constrained_id][1].values)
    unit_snapshot = snapshots[unit_relpath]
    for sample_id in roster_ids[:SAMPLE_CALLS]:
        agree = True
        for draft in unit_snapshot.for_sample(sample_id):
            for response in ("", "   \n "):
                if bounded(draft.text, response).text != accept_free_refresh(
                    draft.text, response
                ).text:
                    agree = False
        agree_rows.append({"sample_id": sample_id, "rules_agree_on_refusals": agree})
        if not agree:
            failures.append(
                f"{sample_id}: the two delivery rules disagree on a refusal, so the "
                "DR-1c/DR-1f contrast would not be a contrast about edits"
            )

    # ------------------------------------------------------------------
    # 3. delivery: the model-free divergence probe
    # ------------------------------------------------------------------
    comparator_relpath, _ = binding_from_values(composed[twin_id][1].values)
    comparator_snapshot = snapshots[comparator_relpath]
    probe_rows: list[dict[str, Any]] = []
    for sample_id in roster_ids[:SAMPLE_CALLS]:
        unit_drafts = unit_snapshot.for_sample(sample_id)
        comparator_drafts = comparator_snapshot.for_sample(sample_id)
        if len(unit_drafts) != len(comparator_drafts):
            failures.append(f"{sample_id}: the two bindings disagree on window count")
            continue
        bounded_outcomes = []
        free_outcomes = []
        free_moved_tokens = 0
        for unit_draft, comparator_draft in zip(unit_drafts, comparator_drafts):
            # The probe's "response" is the comparator's own sealed hypothesis
            # for the same window: real text of exactly the kind a refresh
            # returns, and the only such text this repository can produce
            # without a contact.
            bounded_outcomes.append(bounded(unit_draft.text, comparator_draft.text))
            free_outcomes.append(accept_free_refresh(unit_draft.text, comparator_draft.text))
            free_moved_tokens += abs(
                len(comparator_draft.text.split()) - len(unit_draft.text.split())
            )
        probe_rows.append(
            {
                "sample_id": sample_id,
                "windows": len(unit_drafts),
                "bounded": summarize_outcomes(bounded_outcomes),
                "free": summarize_outcomes(free_outcomes),
                "free_absolute_token_count_movement": free_moved_tokens,
                "unit_draft_tokens": sum(len(d.text.split()) for d in unit_drafts),
                "comparator_draft_tokens": sum(
                    len(d.text.split()) for d in comparator_drafts
                ),
            }
        )
        # The property that makes the probe worth running: the bounded rule
        # cannot move the token count and the free rule can.
        for outcome, draft in zip(bounded_outcomes, unit_drafts):
            if len(outcome.text.split()) != len(draft.text.split()):
                failures.append(
                    f"{sample_id}: the bounded rule moved a window's token count"
                )
                break
        log(
            "  probe %s: bounded refused %d/%d, changed %d; free would move %d tokens"
            % (
                sample_id,
                probe_rows[-1]["bounded"]["windows_refused"],
                len(unit_drafts),
                probe_rows[-1]["bounded"]["windows_changed"],
                free_moved_tokens,
            )
        )

    # ------------------------------------------------------------------
    # 4. payload-binding stage
    # ------------------------------------------------------------------
    values_a = composed[constrained_id][1].values
    lock = load_lock(umbrella_lock_path(REPO))
    by_id = {str(call["sample_id"]): call for call in roster["calls"]}
    binding_samples = tuple(
        _RosterSample(
            sample_id=sample_id,
            audio_ref=_RosterAudioRef(path=str(by_id[sample_id]["media_relpath"])),
            audio_seconds=float(by_id[sample_id]["audio_seconds"]),
        )
        for sample_id in roster_ids
    )
    binding_stage = payload_binding_stage(
        dataset_fragment=str(composed[constrained_id][0]["dataset_fragment"]),
        carrier_lock_key=str(values_a["carrier_lock_key"]),
        samples=binding_samples,
        data_root=args.data_root,
        carrier_root=asset_dir(lock, str(values_a["carrier_lock_key"]), args.data_root),
        derived_media_roots=declared_derived_media_roots(values_a, args.data_root),
    )
    if not binding_stage.bound:
        failures.append(f"payload-binding stage did not bind: {binding_stage.failures!r}")
    log(
        "  payload-binding stage: %s (%d/%d rows)"
        % (
            "PASS" if binding_stage.bound else "FAIL",
            len(binding_stage.rows_checked),
            binding_stage.rows_total,
        )
    )

    receipt = {
        "schema": "saea-e21-dr1-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "execution_profile": "model-free-check",
        "exposure_row": RUN_ID,
        "preregistration": PREREGISTRATION,
        "experiment_fragment": EXPERIMENT,
        "study_commit": study_commit,
        "study_repo_dirt": dirty,
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
        "zero_contact": (
            "No frozen core, server, socket, GPU, tokenizer, embedder, network or paid "
            "API. Nothing here constructs a transport, gate, attempt store or "
            "FrozenCoreAdapter; no audio file is opened and no MP3 is decoded, so the "
            "pinned absence of ffmpeg is preserved. The only bytes read are the "
            "committed fragments and receipts, the two sealed runs' own outputs.jsonl, "
            "and the two hash-verified snapshot artifacts."
        ),
        "identities": identities,
        "kc_e1f": {
            "config_hash": kc_composed.config_hash,
            "functional_diff_dr1c_vs_kc_e1f": c_vs_kc,
        },
        "one_factor": {
            "dr1c_vs_dr1f": c_vs_f,
            "dr1c_vs_dr1s": c_vs_s,
            "instruction_ends_with_the_comparators_own": dr1_instruction.endswith(
                comparator_instruction
            ),
            "one_task_instruction_across_the_three_cells": (
                len({str(f["task_instruction"]) for f in fragments.values()}) == 1
            ),
        },
        "serving_geometry": geometry,
        "bindings": {
            relpath: {
                "run_id": snapshot.run_id,
                "attempt_id": snapshot.attempt_id,
                "windows": snapshot.window_count,
                "calls": snapshot.call_count,
                "artifact_sha256": snapshot.artifact_sha256,
                "receipt_sha256": snapshot.receipt_sha256,
            }
            for relpath, snapshot in snapshots.items()
        },
        "request_half": request_rows,
        "refusal_agreement": agree_rows,
        "delivery_divergence_probe": {
            "what_it_is": (
                "a MODEL-FREE probe, never a prediction. It feeds each window's hook the "
                "COMPARATOR's own sealed hypothesis as if it were the pass-2 response, "
                "and reports what each rule would deliver. It says nothing about what "
                "the core will return; it measures how far the two rules are apart on "
                "real text of the kind a refresh returns"
            ),
            "rows": probe_rows,
        },
        "payload_binding": {
            "bound": binding_stage.bound,
            "rows_checked": list(binding_stage.rows_checked),
            "rows_total": binding_stage.rows_total,
            "failures": list(binding_stage.failures),
        },
        "authorizes": (
            "nothing. This receipt records a composition, a rendered request, a "
            "delivery probe and a payload binding. The three DR-1 cells still need the "
            "owner's GO to fly and do not have it."
        ),
    }
    if args.out_dir is not None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        out_path = args.out_dir / "wire-check.json"
        out_path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        log(f"wrote {out_path} ({_sha256(out_path)[:12]})")
    log(f"RESULT {receipt['result']} ({len(failures)} failure(s))")
    for failure in failures:
        log(f"  - {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
