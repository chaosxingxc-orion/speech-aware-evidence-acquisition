#!/usr/bin/env python3
"""Contact-free, socket-free wire check for E21-LOOP-1 and its form twin.

Exposure row ``SAEA-E21-MF-LOOP-1-PREP-V1`` (``model-free-check``). **Zero
model, GPU, server, socket, tokenizer, tool, embedder, network and paid-API
contacts.** Nothing here constructs a transport, a gate, an attempt store or a
``core.model.FrozenCoreAdapter``.

Four halves, reported separately because they fail for different reasons.

``config``
    Real ``core.config.compose`` on the arm, on the twin and on the KC-E1f arm
    they derive from. Reports each composed ``config_hash``, each
    ``protocol_hash`` against the SAME split identity, and the key-by-key diff
    against KC-E1f. The expected functional diff is exactly the two plan keys
    plus the two declaration blocks; everything else that differs must be a
    documentary key.

``plan``
    The real ``reproduction.obs_loop`` plan loader on both pinned plans, so
    each is re-proved on the bytes actually loaded: every unit inside its named
    parent window, over the refusal-to-shrink floor, naming a non-empty word
    range inside that window's own pass-1 text, one unit per flagged window in
    ascending order. Then the two agreements that make the twin a FORM control
    rather than a different cell: identical unit count per call, and an
    identical multiset of re-cut durations per call. And the agreement that
    makes the fragments honest: every value of ``window_review`` /
    ``window_observe`` equals the plan document's own.

``request``
    The real ``reproduction.repair_loop.RepairWindowHook`` over the real,
    hash-verified predecessor binding, on the plan's own units for a sample of
    calls. Three properties, on real sealed bytes:

    1. the rendered instruction carries EXACTLY the plan's word range of that
       window's own pass-1 text, and no word outside it;
    2. a useless pass-2 answer costs nothing -- when every response is refused,
       the hook's deliveries concatenate to the sealed comparator's own
       hypothesis for that call, byte for byte;
    3. every window of the call is delivered exactly once, so the selective
       plan loses no window.

``payload``
    The shared ``rails.core_client.payload_binding_stage`` over the cell's own
    44-row roster, through the real carrier root, so the cell is reported
    wire-ready only if its payloads actually bind.

Usage (WSL2)::

    python scripts/e21_loop_1_wire_check.py --out-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

RUN_ID = "SAEA-E21-MF-LOOP-1-PREP-V1"
PREREGISTRATION = "docs/readiness/2026-09-08-e21-loop-1-v1-preregistration.md"
EXPERIMENT = "e21-loop-1-v1"
KC_E1F_EXPERIMENT = "e21-kc-e1f-repair-44-v1"
SPLITS = REPO / "docs" / "receipts" / "splits.json"
FULL44_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)
SEALED_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
SEALED_ATTEMPT = "attempt-20260904T233816Z-bcd338"

#: How many calls the request half drives through the real hook. The property
#: it checks is per call and byte-exact, so a sample is a proof on those calls
#: and a spot check on the rest; the plan half already covers all 44.
REQUEST_HALF_CALLS = 4

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
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class _RosterAudioRef:
    path: str


@dataclass(frozen=True)
class _RosterSample:
    sample_id: str
    audio_ref: _RosterAudioRef
    audio_seconds: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _documentary(key: str) -> bool:
    """A key that exists to explain a fragment rather than to steer it.

    Every one of these is prose. A fragment that carries a paragraph saying
    what it is must not thereby read as a factor, and a fragment that does NOT
    carry one must not read as a factor either.
    """

    return key.startswith("why_") or key in {
        "what_this_is",
        "on_flag_vocabulary_note",
        "plan_pin_basis",
        "composes_but_is_not_permission",
        "composes_since",
        "baseline_re_pinned_to_v2",
        "scorer_basis",
        "tail_basis",
    }


def _baseline_fragment(repo, name: str) -> dict:
    """One baseline fragment's own keys, read from its own file.

    The FUNCTIONAL comparison is between baseline fragments, not between whole
    composed documents: a composed document also carries the experiment
    fragment's identity block and the model fragment's serving geometry, and
    two different cells necessarily differ in both. Those two are compared
    separately and by name (the geometry below, the identity block never).
    """

    return json.loads(
        (repo / "configs" / "baseline" / f"{name}.json").read_text(encoding="utf-8")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
    from speech_aware_evidence_acquisition.core.base import (
        declared_derived_media_roots,
    )
    from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
        binding_from_values,
        load_predecessor_binding,
    )
    from speech_aware_evidence_acquisition.core.repair_alignment import (
        accept_entity_repair,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.rails.core_client import (
        payload_binding_stage,
    )
    from speech_aware_evidence_acquisition.reproduction.obs_loop import (
        OBS_RELISTEN_PLAN_SCHEMA,
        ObsLoopConfig,
    )
    from speech_aware_evidence_acquisition.reproduction.repair_loop import (
        REPAIR_FRAMES,
        RepairWindowHook,
    )

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is dirty; a wire check certifies committed bytes:\n"
            + dirty
        )
    study_commit = git("rev-parse", "HEAD")
    log("%s tree at %s" % ("DIRTY (allowed)" if dirty else "clean", study_commit[:8]))

    failures: list[str] = []

    # ------------------------------------------------------------------
    # 1. config
    # ------------------------------------------------------------------
    experiment_doc = load_json(REPO / "configs" / "experiment" / f"{EXPERIMENT}.json")
    splits = load_json(SPLITS)
    composed_cells: dict[str, Any] = {}
    for cell in experiment_doc["cells"]:
        composed_cells[str(cell["cell_id"])] = (
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
    for cell_id, (_cell, composed) in composed_cells.items():
        values = composed.values
        split_block = splits["splits"][str(values["split_name"])]
        if str(split_block["carrier_lock_key"]) != str(values["carrier_lock_key"]):
            failures.append(f"{cell_id}: composed carrier is not the split's own")
        identities[cell_id] = {
            "config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(
                composed.config_hash,
                str(values["arm"]),
                str(split_block["identity_hash"]),
            ),
            "split_identity_hash": str(split_block["identity_hash"]),
        }
        log(
            "composed %s config_hash=%s protocol_hash=%s"
            % (cell_id, composed.config_hash[:16], identities[cell_id]["protocol_hash"][:16])
        )

    arm_id, twin_id = list(composed_cells)
    arm_values = composed_cells[arm_id][1].values
    kc_values = kc_composed.values

    def functional_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
        keys = sorted(set(left) | set(right))
        return [
            key
            for key in keys
            if not _documentary(key) and left.get(key) != right.get(key)
        ]

    arm_fragment = _baseline_fragment(REPO, str(composed_cells[arm_id][0]["baseline_fragment"]))
    twin_fragment = _baseline_fragment(
        REPO, str(composed_cells[twin_id][0]["baseline_fragment"])
    )
    kc_fragment = _baseline_fragment(REPO, str(kc_cell["baseline_fragment"]))

    arm_vs_kc = functional_diff(arm_fragment, kc_fragment)
    expected_vs_kc = {
        "obs_unit_plan",
        "obs_unit_plan_sha256",
        "window_review",
        "window_observe",
    }
    unexpected = [key for key in arm_vs_kc if key not in expected_vs_kc]
    if unexpected:
        failures.append(
            f"the arm's baseline fragment differs from KC-E1f's in unexpected keys: "
            f"{unexpected}"
        )
    arm_vs_twin = functional_diff(arm_fragment, twin_fragment)
    expected_vs_twin = {
        "obs_unit_plan",
        "obs_unit_plan_sha256",
        "window_observe",
        "window_review",
    }
    if set(arm_vs_twin) - expected_vs_twin:
        failures.append(
            f"the arm and its twin differ in unexpected keys: "
            f"{sorted(set(arm_vs_twin) - expected_vs_twin)}"
        )
    # The serving geometry is a SEPARATE, named difference: this cell projects
    # np6 where KC-E1f flew np4, and a prompt fit decides it before the first
    # flight contact. Reported, never folded into the one-factor claim.
    geometry = {
        "arm_model_fragment": str(composed_cells[arm_id][0]["model_fragment"]),
        "twin_model_fragment": str(composed_cells[twin_id][0]["model_fragment"]),
        "kc_e1f_model_fragment": str(kc_cell["model_fragment"]),
        "arm_server_args": arm_values.get("server_args"),
        "kc_e1f_server_args": kc_values.get("server_args"),
    }
    if geometry["arm_model_fragment"] != geometry["twin_model_fragment"]:
        failures.append("the arm and its twin do not share a serving geometry")
    log(f"functional diff vs KC-E1f: {arm_vs_kc}")
    log(f"functional diff vs the twin: {arm_vs_twin}")
    log(
        "serving geometry: arm %s, KC-E1f %s (projected; the prompt fit decides)"
        % (geometry["arm_model_fragment"], geometry["kc_e1f_model_fragment"])
    )

    # ------------------------------------------------------------------
    # 2. plan
    # ------------------------------------------------------------------
    plans: dict[str, Any] = {}
    plan_stats: dict[str, dict[str, Any]] = {}
    for cell_id, (_cell, composed) in composed_cells.items():
        cfg = ObsLoopConfig.from_values(composed.values, REPO)
        if cfg.unit_plan is None:
            failures.append(f"{cell_id}: the composed config carries no unit plan")
            continue
        if cfg.unit_plan.schema != OBS_RELISTEN_PLAN_SCHEMA:
            failures.append(
                f"{cell_id}: the plan declares schema {cfg.unit_plan.schema!r}"
            )
        plans[cell_id] = cfg.unit_plan
        document = load_json(REPO / cfg.unit_plan.relpath)
        declared_review = composed.values.get("window_review") or {}
        declared_observe = composed.values.get("window_observe") or {}
        for key, plan_key in (
            ("context_margin_seconds", "context_margin_seconds"),
            ("min_relisten_seconds", "min_relisten_seconds"),
            ("flag_source", "flag_source"),
        ):
            if declared_observe.get(key) != document.get(plan_key):
                failures.append(
                    f"{cell_id}: window_observe.{key} = "
                    f"{declared_observe.get(key)!r} but the pinned plan says "
                    f"{document.get(plan_key)!r}"
                )
        plan_judges = [
            str(entry["id"]) for entry in document["provenance"].get("judges", [])
        ]
        if list(declared_review.get("judges") or []) != plan_judges:
            failures.append(
                f"{cell_id}: window_review.judges = "
                f"{declared_review.get('judges')!r} but the pinned plan was built "
                f"from {plan_judges!r}"
            )
        units = sum(len(block) for block in cfg.unit_plan.units_by_sample.values())
        seconds = sum(
            unit.duration_seconds
            for block in cfg.unit_plan.units_by_sample.values()
            for unit in block
        )
        plan_stats[cell_id] = {
            "relpath": cfg.unit_plan.relpath,
            "sha256": cfg.unit_plan.sha256,
            "calls": len(cfg.unit_plan.units_by_sample),
            "units": units,
            "recut_seconds": round(seconds, 6),
            "mean_recut_seconds": round(seconds / max(units, 1), 6),
            "min_recut_seconds": round(
                min(
                    (
                        unit.duration_seconds
                        for block in cfg.unit_plan.units_by_sample.values()
                        for unit in block
                    ),
                    default=0.0,
                ),
                6,
            ),
            "judges": plan_judges,
            "flag_source": document.get("flag_source"),
        }
        log(
            "plan %s: %d units over %d calls, %.1f s re-cut (%s)"
            % (cell_id, units, len(cfg.unit_plan.units_by_sample), seconds,
               cfg.unit_plan.sha256[:12])
        )

    roster = load_json(FULL44_ROSTER)
    roster_ids = [str(call["sample_id"]) for call in roster["calls"]]
    for cell_id, plan in plans.items():
        uncovered = [
            sample_id
            for sample_id in roster_ids
            if sample_id not in plan.units_by_sample
        ]
        if uncovered:
            failures.append(f"{cell_id}: the plan covers no units for {uncovered}")

    if len(plans) == 2:
        arm_plan, twin_plan = plans[arm_id], plans[twin_id]
        count_mismatch = [
            sample_id
            for sample_id in roster_ids
            if len(arm_plan.units_by_sample.get(sample_id, ()))
            != len(twin_plan.units_by_sample.get(sample_id, ()))
        ]
        if count_mismatch:
            failures.append(
                f"the twin's contact count differs from the arm's on "
                f"{len(count_mismatch)} call(s): {count_mismatch[:5]}"
            )
        duration_mismatch = []
        for sample_id in roster_ids:
            left = Counter(
                round(unit.duration_seconds, 6)
                for unit in arm_plan.units_by_sample.get(sample_id, ())
            )
            right = Counter(
                round(unit.duration_seconds, 6)
                for unit in twin_plan.units_by_sample.get(sample_id, ())
            )
            if left != right:
                duration_mismatch.append(sample_id)
        if duration_mismatch:
            failures.append(
                f"the twin's re-cut durations differ from the arm's on "
                f"{len(duration_mismatch)} call(s): {duration_mismatch[:5]}"
            )
        overlap = sum(
            1
            for sample_id in roster_ids
            for unit in twin_plan.units_by_sample.get(sample_id, ())
            if unit.parent_window_index
            in {
                other.parent_window_index
                for other in arm_plan.units_by_sample.get(sample_id, ())
            }
        )
        log(
            "twin: contact count and duration multiset match on %d/%d calls; "
            "%d of its %d windows coincide with a judge-flagged one"
            % (
                len(roster_ids) - len(count_mismatch),
                len(roster_ids),
                overlap,
                plan_stats[twin_id]["units"],
            )
        )
        plan_stats[twin_id]["windows_coinciding_with_a_flagged_one"] = overlap

    # ------------------------------------------------------------------
    # 3. request: the real hook over the real predecessor binding
    # ------------------------------------------------------------------
    attempt_dir = args.data_root / "runs" / SEALED_RUN / SEALED_ATTEMPT
    outputs_text = {
        str(row["sample_id"]): str(row["text"])
        for row in (
            json.loads(line)
            for line in (attempt_dir / f"{SEALED_RUN}.outputs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
    }
    relpath, digest = binding_from_values(composed_cells[arm_id][1].values)
    snapshot = load_predecessor_binding(
        REPO / "docs" / relpath, args.data_root, expected_receipt_sha256=digest
    )
    rule = lambda pass1, response: accept_entity_repair(  # noqa: E731
        pass1,
        response,
        max_span_tokens=4,
        min_anchor_ratio=0.6,
        max_substituted_fraction=0.1,
    )

    @dataclass(frozen=True)
    class _Cut:
        start_seconds: float
        end_seconds: float

    request_rows: list[dict[str, Any]] = []
    for sample_id in roster_ids[:REQUEST_HALF_CALLS]:
        predecessors = snapshot.for_sample(sample_id)
        units = plans[arm_id].units_by_sample[sample_id]
        hook = RepairWindowHook(
            sample_id=sample_id,
            predecessors=predecessors,
            frame=REPAIR_FRAMES["e21-entity-repair-frame-v1"],
            rule=rule,
            units=units,
        )
        instruction_ok = True
        delivered: list[str] = []
        for iteration, unit in enumerate(units):
            cut = _Cut(unit.start_seconds, unit.end_seconds)
            rendered = hook.instruction(
                iteration=iteration, record=cut, default="BASE"
            )
            window = predecessors[int(unit.parent_window_index) - 1]
            words = window.text.split()
            shown = " ".join(
                words[int(unit.predecessor_word_start) : int(unit.predecessor_word_end)]
            )
            # An EQUALITY on the frame's own tail, not a substring search: the
            # frame ends with the quoted predecessor, so this pins the frame,
            # the join and the plan's word range in one assertion -- and it
            # cannot be satisfied by a longer span that merely contains the
            # right one.
            if not rendered.endswith(f'"{shown}"'):
                instruction_ok = False
            # The empty response is the refusal every window takes here, so
            # the delivery is the predecessor and the concatenation is the
            # comparator's own hypothesis.
            span, _fields = hook.accept(
                iteration=iteration,
                record=cut,
                transcript="",
                saturated=False,
                skipped=False,
            )
            delivered.append(span)
        rebuilt = " ".join(span for span in delivered if span)
        sealed = outputs_text[sample_id]
        if not instruction_ok:
            failures.append(f"{sample_id}: an instruction did not carry its own span")
        if rebuilt != sealed:
            failures.append(
                f"{sample_id}: a fully refused pass 2 did not reproduce the sealed "
                f"hypothesis ({len(rebuilt)} chars vs {len(sealed)})"
            )
        request_rows.append(
            {
                "sample_id": sample_id,
                "windows": len(predecessors),
                "units": len(units),
                "uncontacted_windows": hook.uncontacted_windows,
                "instruction_carries_its_own_span": instruction_ok,
                "refused_delivery_equals_the_sealed_hypothesis": rebuilt == sealed,
                "sealed_hypothesis_sha256": hashlib.sha256(
                    sealed.encode("utf-8")
                ).hexdigest(),
            }
        )
        if hook.uncontacted_windows + len(units) != len(predecessors):
            failures.append(
                f"{sample_id}: {len(units)} contacted + "
                f"{hook.uncontacted_windows} back-filled != {len(predecessors)} windows"
            )
        log(
            "  request %s: %d units, %d windows back-filled, refusal rebuild %s"
            % (
                sample_id,
                len(units),
                hook.uncontacted_windows,
                "PASS" if rebuilt == sealed else "FAIL",
            )
        )

    # ------------------------------------------------------------------
    # 4. payload-binding stage
    # ------------------------------------------------------------------
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
        dataset_fragment=str(composed_cells[arm_id][0]["dataset_fragment"]),
        carrier_lock_key=str(arm_values["carrier_lock_key"]),
        samples=binding_samples,
        data_root=args.data_root,
        carrier_root=asset_dir(lock, str(arm_values["carrier_lock_key"]), args.data_root),
        derived_media_roots=declared_derived_media_roots(arm_values, args.data_root),
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
        "schema": "saea-e21-loop-1-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "execution_profile": "model-free-check",
        "exposure_row": RUN_ID,
        "preregistration": PREREGISTRATION,
        "study_commit": study_commit,
        "study_repo_dirt": dirty,
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
        "zero_contact": (
            "No frozen core, server, socket, GPU, tokenizer, embedder, network or "
            "paid API. Nothing here constructs a transport, gate, attempt store or "
            "FrozenCoreAdapter; no audio file is opened and no MP3 is decoded, so "
            "the pinned absence of ffmpeg is preserved. The only bytes read are the "
            "committed fragments and plans, the sealed comparator's own "
            "outputs.jsonl, and the hash-verified predecessor artifact."
        ),
        "identities": identities,
        "kc_e1f": {
            "config_hash": kc_composed.config_hash,
            "functional_diff_arm_vs_kc_e1f": arm_vs_kc,
        },
        "functional_diff_arm_vs_twin": arm_vs_twin,
        "serving_geometry": geometry,
        "plans": plan_stats,
        "request_half": request_rows,
        "payload_binding": {
            "bound": binding_stage.bound,
            "rows_checked": list(binding_stage.rows_checked),
            "rows_total": binding_stage.rows_total,
            "failures": list(binding_stage.failures),
        },
        "authorizes": (
            "nothing. This receipt records a composition, a plan proof, a rendered "
            "request and a payload binding. E21-LOOP-1 still needs the owner's GO to "
            "fly and does not have it."
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
