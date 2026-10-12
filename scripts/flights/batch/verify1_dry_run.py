#!/usr/bin/env python
"""The VERIFY-1 OFFLINE dry run: what one selection contact actually carries.

Model-free by construction: zero model, tokenizer, tool, network, GPU, gate,
transport, client, attempt and serving-session contacts. Nothing is written into
any run directory and no candidate text, utterance, transcript or gold is
printed or persisted -- the table below is characters, counts, permutations and
hashes only.

What it proves, in the order the registration needs it:

1. COMPOSITION. Both registered cells compose from their own committed
   fragments; the composed config hash and protocol hash are printed and are
   the ones the readiness package registers.
2. THE FORM. For each of the four smoke rows, the phase renders FIVE numbered
   candidates and the recorded permutation says which sealed sample index sat
   in which position. Two of the four rows render one distinct answer (the
   position-bias control shape) and two render four and five (the informative
   shape).
3. DETERMINISM. The rendered block for a row is a function of (manifest bytes,
   permutation seed) and nothing else: two independent loads agree on every
   byte of every block and on every permutation.
4. PROMPT FIT. The widest of all 625 rows is measured against the live slot
   with the registered one-eighth operational reserve, at a pessimistic
   2.5 characters per token.
5. THE LEAKAGE RULE. Not one of the bound MINUS-R01 exemplar snapshot's
   protected payloads is contained in any of the 625 rendered candidate blocks
   or in either probe template, so
   ``rails.runner._assert_agent_control_excludes_knowledge_payloads`` -- which
   this cell's instruction is subject to because its instruction carries
   model-produced text -- passes rather than killing the flight mid-roster.
6. AGREEMENT WITH THE COMMITTED RECORD. Every per-row permutation, block hash
   and distinct-answer count equals the one
   ``scripts/build_slurp_verify1_material.py`` committed, so the read's
   resolution table and the wire cannot disagree.

Usage (from a worktree, in WSL)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src \\
    SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT \\
    python -B scripts/flights/batch/verify1_dry_run.py \\
      --repo-root $REPO --data-root $DATA --lock-path $LOCK [--json out.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

CELLS = {
    "arm": {
        "experiment": "slurp-native-stage3-verify-1-v1",
        "cell": "slurp-native-stage3-verify-1-v1",
        "baseline": "slurp-native-stage3-verify-1-baseline-v1",
        "split_identity_hash": (
            "f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515"
        ),
    },
    "smoke": {
        "experiment": "slurp-native-stage3-verify-1-smoke-4-v1",
        "cell": "slurp-native-stage3-verify-1-smoke-4-v1",
        "baseline": "slurp-native-stage3-verify-1-smoke-4-baseline-v1",
        "split_identity_hash": (
            "2657110d135195dafbf1ebd12850470b0ae8dc28ffa1d61494266d047e349efd"
        ),
    },
}
MODEL = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
DATASET = "slurp-speech-native-stage3-construction-r01c"
MATERIAL_RECORD = "docs/receipts/verify1/slurp-stage3-verify-1-material-v1.json"

#: The pessimistic characters-per-token rate the VAR-1 package argued prompt fit
#: at, reused unchanged so the two estimates are comparable.
CHARS_PER_TOKEN = 2.5
#: An upper bound on the audio tokens one R01C packet contributes: the roster's
#: longest recording (14.5899375 s) at 25 tokens per second, which is above the
#: Qwen3-Omni audio rate rather than at it.
AUDIO_TOKENS_PER_SECOND = 25
MAX_AUDIO_SECONDS = 14.5899375
#: The live slot and the registered operational reserve (one eighth), item
#: "fit gate live-slot reserve".
SLOT_TOKENS = 24576
RESERVE_TOKENS = 3072
COMPLETION_CEILING = 512
#: A generous allowance for everything the chat envelope adds around the two
#: message bodies (role markers, the control-turn framing, the packet
#: descriptor's own JSON). Deliberately larger than measured.
ENVELOPE_OVERHEAD_TOKENS = 512


class _Ctx:
    def __init__(self, sample_id: str) -> None:
        self.sample_id = sample_id


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    parser.add_argument("--lock-path", default=None)
    parser.add_argument("--json", default=None)
    args = parser.parse_args(argv)
    if not args.data_root:
        parser.error("--data-root or SPEECHRL_DATA_DIR is required")
    repo_root = Path(args.repo_root).resolve()
    data_root = Path(args.data_root)

    from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
    from speech_aware_evidence_acquisition.core.instructions import (
        render_template_with_fill,
    )
    from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
    from speech_aware_evidence_acquisition.rails.phase_material import (
        build_material_for_phase,
        load_phase_material_specs,
        load_sealed_sample_groups,
        phase_material_receipt,
        render_static_instruction,
        resolve_response_formats,
    )

    lock = load_lock(
        Path(args.lock_path) if args.lock_path else umbrella_lock_path(repo_root)
    )
    report: dict[str, object] = {"cells": {}, "zero_contacts": True}

    for label, spec in CELLS.items():
        composed = compose(
            repo_root,
            model=MODEL,
            dataset=DATASET,
            baseline=spec["baseline"],
            experiment=spec["experiment"],
        )
        values = composed.values
        program = default_phase_program(str(values["policy"]))
        specs = load_phase_material_specs(values, program)
        static = {
            phase: render_static_instruction(item, repo_root, lock, data_root)
            for phase, item in specs.items()
        }
        formats = resolve_response_formats(specs, lock, data_root)
        system_text = render_template_with_fill(
            str(values["task_instruction_template"]),
            str(values["task_instruction_fill"]),
            repo_root,
            lock,
            data_root,
            {},
        )
        report["cells"][label] = {
            "cell_id": spec["cell"],
            "experiment": spec["experiment"],
            "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(
                composed.config_hash, str(values["arm"]), spec["split_identity_hash"]
            ),
            "split_identity_hash": spec["split_identity_hash"],
            "program_id": program.program_id,
            "phases": list(program.phase_names()),
            "per_row_ceiling": program.max_contacts,
            "response_format_ids": {
                phase: item.response_format_id for phase, item in specs.items()
            },
            "response_formats_resolved": sorted(formats),
            "system_text_chars": len(system_text),
            "system_text_sha256": _sha256(system_text),
            "static_instruction_chars": {
                phase: len(text) for phase, text in static.items()
            },
            "phase_material_receipt_sha256": _sha256(
                json.dumps(
                    phase_material_receipt(specs, static, formats),
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            ),
        }
        if label == "arm":
            arm_values, arm_specs, arm_static, arm_system = values, specs, static, system_text

    # ---- the sealed candidate material -------------------------------------
    source = arm_specs["choose"].predecessor_source
    manifest = data_root / str(source["manifest_relpath"])
    smoke_ids = tuple(
        json.loads(
            (repo_root / "configs" / "experiment" / CELLS["smoke"]["experiment"]).with_suffix(
                ".json"
            ).read_text(encoding="utf-8")
        )["populations"][0]["ids"]
    )
    record = json.loads((repo_root / MATERIAL_RECORD).read_text(encoding="utf-8"))
    all_ids = tuple(row["sample_id"] for row in record["rows"])

    groups = load_sealed_sample_groups(
        manifest,
        expected_sha256=str(source["manifest_sha256"]),
        phase_name="choose",
        producer_policy_id=str(source["producer_policy_id"]),
        sample_ids=all_ids,
        expected_sample_count=int(source["expected_sample_count"]),
        permutation_seed=int(source["permutation_seed"]),
        permutation_rule=str(source.get("permutation_rule", "row-hash-v1")),
    )
    again = load_sealed_sample_groups(
        manifest,
        expected_sha256=str(source["manifest_sha256"]),
        phase_name="choose",
        producer_policy_id=str(source["producer_policy_id"]),
        sample_ids=all_ids,
        expected_sample_count=int(source["expected_sample_count"]),
        permutation_seed=int(source["permutation_seed"]),
        permutation_rule=str(source.get("permutation_rule", "row-hash-v1")),
    )
    deterministic = all(
        groups[key].state.content == again[key].state.content
        and groups[key].permutation == again[key].permutation
        for key in all_ids
    )

    material = build_material_for_phase(
        arm_specs,
        program_id="phase-slurp-verify-select-v1",
        static_text_by_phase=arm_static,
        response_format_by_phase=resolve_response_formats(arm_specs, lock, data_root),
        per_sample_states={"choose": {key: groups[key].state for key in all_ids}},
    )

    rows = []
    for sample_id in smoke_ids:
        group = groups[sample_id]
        built = material("choose", _Ctx(sample_id), {})
        lines = group.state.content.splitlines()
        rows.append(
            {
                "sample_id": sample_id,
                "candidates_rendered": len(group.rendered),
                "numbered_lines": sum(
                    1 for line in lines if line[:1].isdigit() and ". " in line[:4]
                ),
                "permutation_position_to_sample_index": list(group.permutation),
                "distinct_answers": group.distinct_answers,
                "parse_ok": group.parse_ok,
                "parse_failed": group.parse_failed,
                "block_chars": len(group.state.content),
                "instruction_chars": len(built.instruction),
                "instruction_sha256": _sha256(built.instruction),
                "contact_id": built.contact_id,
                "response_format": built.response_format is not None,
            }
        )

    # ---- prompt fit on the WIDEST of all 625 -------------------------------
    widest_id = max(all_ids, key=lambda key: len(groups[key].state.content))
    widest = material("choose", _Ctx(widest_id), {})
    audio_tokens = int(MAX_AUDIO_SECONDS * AUDIO_TOKENS_PER_SECOND) + 1
    text_tokens = int(
        (len(arm_system) + len(widest.instruction)) / CHARS_PER_TOKEN
    ) + 1
    required = text_tokens + audio_tokens + ENVELOPE_OVERHEAD_TOKENS + COMPLETION_CEILING
    budget = SLOT_TOKENS - RESERVE_TOKENS
    fit = {
        "widest_sample_id": widest_id,
        "widest_block_chars": len(groups[widest_id].state.content),
        "widest_instruction_chars": len(widest.instruction),
        "system_text_chars": len(arm_system),
        "chars_per_token_pessimistic": CHARS_PER_TOKEN,
        "estimated_text_prompt_tokens": text_tokens,
        "audio_tokens_upper_bound": audio_tokens,
        "envelope_overhead_tokens": ENVELOPE_OVERHEAD_TOKENS,
        "completion_ceiling_tokens": COMPLETION_CEILING,
        "estimated_required_window_tokens": required,
        "live_slot_tokens": SLOT_TOKENS,
        "operational_reserve_tokens": RESERVE_TOKENS,
        "budget_tokens": budget,
        "headroom_tokens": budget - required,
        "decision": "ALLOW" if required <= budget else "REFUSE",
    }

    # ---- the leakage rule --------------------------------------------------
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(
            (data_root / str(arm_values["knowledge_snapshot_relpath"])).read_text(
                encoding="utf-8"
            )
        )
    )
    protected = tuple(
        item.strip().casefold()
        for item in (
            *(facet.representation for facet in snapshot.facets),
            *(value.content for value in snapshot.values),
        )
        if len(item.strip()) >= 8
    )
    haystacks = [groups[key].state.content.casefold() for key in all_ids]
    haystacks.append(arm_static["choose"].casefold())
    haystacks.append(arm_system.casefold())
    hits = sum(1 for item in protected if any(item in hay for hay in haystacks))
    leakage = {
        "snapshot_content_hash": snapshot.content_hash(),
        "protected_payloads": len(protected),
        "haystacks": len(haystacks),
        "containment_hits": hits,
        "decision": "PASS" if hits == 0 else "REFUSE",
    }

    # ---- agreement with the committed record --------------------------------
    mismatches = []
    by_id = {row["sample_id"]: row for row in record["rows"]}
    for sample_id in all_ids:
        group = groups[sample_id]
        row = by_id[sample_id]
        if (
            list(group.permutation) != row["permutation"]
            or group.distinct_answers != row["distinct_answers"]
            or group.parse_failed != row["parse_failed"]
            or _sha256(group.state.content) != row["block_sha256"]
        ):
            mismatches.append(sample_id)

    report["material"] = {
        "manifest_relpath": str(source["manifest_relpath"]),
        "manifest_sha256": str(source["manifest_sha256"]),
        "permutation_seed": int(source["permutation_seed"]),
        "expected_sample_count": int(source["expected_sample_count"]),
        "rows_loaded": len(all_ids),
        "deterministic_two_loads": deterministic,
        "committed_record": MATERIAL_RECORD,
        "committed_record_sha256": hashlib.sha256(
            (repo_root / MATERIAL_RECORD).read_bytes()
        ).hexdigest(),
        "record_mismatches": mismatches,
        "populations": record["populations"],
    }
    report["four_row_table"] = rows
    report["prompt_fit"] = fit
    report["leakage_rule"] = leakage
    report["verdict"] = (
        "PASS"
        if deterministic
        and not mismatches
        and hits == 0
        and fit["decision"] == "ALLOW"
        and all(row["candidates_rendered"] == 5 for row in rows)
        and all(row["numbered_lines"] == 5 for row in rows)
        else "FAIL"
    )
    text = json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False)
    print(text)
    if args.json:
        Path(args.json).write_text(text + "\n", encoding="utf-8", newline="\n")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
