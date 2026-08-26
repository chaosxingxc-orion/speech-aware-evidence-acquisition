"""SLURP intent-coverage check: does the pinned KB model every intent the
task is defined over, and can ``intent_coverage`` detect it if it does not?

Registered as exposure row ``SAEA-SN-MF-SLURP-INTENT-COVERAGE-CHECK``
(model-free-check) BEFORE any computation. ZERO model contacts, ZERO tool
contacts, ZERO embedding contacts, ZERO network:
:func:`analysis.dev100_reviewer_audit.arm_offline_guard` is armed before the
first input is opened and its attempt count is published in the receipt.

THE DISCREPANCY THIS MODULE MEASURES. ``rails/knowledge_build.py``'s module
docstring asserts "SLURP train: 91 intents, 55 entity types" as the very
justification for the two hard long-tail floors in
:func:`~..rails.knowledge_build.distribution_sample`. The landed KB-BUILD
receipt ``docs/receipts/knowledge/slurp-kb-size-full.json`` instead reports
``coverage_report.counts.train_intents`` = 60 and ``selected_intents`` = 60
over 11,514 TRAIN utterances. Both cannot be true of the same corpus. This
module answers, from the governed bytes and the landed artifacts only:

Q1  how many distinct intents the TRAIN material actually carries, and how
    large the SLURP label space is over train and devel (test is NEVER
    opened), counted BOTH as the corpus's own ``intent`` field and as the
    builder's synthesized ``f"{scenario}_{action}"``;
Q2  what the PINNED snapshot models, as three separately counted
    quantities -- ``facet:label:intent:`` facets, ``facet:prior:`` facets,
    and distinct ``ValueBundle.task_target`` values;
Q3  at which stage any intent is lost -- row loading, ``distribution_sample``
    or facet emission -- named by the count measured at each boundary;
Q4  the denominator ``coverage_report``'s ``intent_coverage`` divides by,
    read out of the source rather than inferred; and
Q5  the conservative consequence on the already-sealed DEV-1000 records.

DISCIPLINE. Nothing hash-pinned moves: the snapshot is opened read-only and
must re-hash to its pinned value or the check stops. No snapshot is rebuilt.
No knob is changed. The SLURP unexposed 500 is the LOCKED baseline's own
population, so every DEV-1000 number here is a SECONDARY READING that must
not be used to revise, re-tune or restate the lock, and the receipt says so
in its own ``secondary_reading_caveat`` field.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from . import dev1000_lock_read as lr
from . import dev500_confirmatory_read as d5

SCHEMA = "saea-slurp-intent-coverage-check-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-SLURP-INTENT-COVERAGE-CHECK"
LEDGER_REGISTRATION_COMMIT = "8c1aa59e"

KB_BUILD_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-kb-size-full.json"
CONTRACT_RELPATH = "docs/readiness/2026-08-08-unified-agent-abstraction.md"

#: Governed SLURP label-side files this check is allowed to open. ``test.jsonl``
#: is deliberately ABSENT and is never opened, loaded or enumerated.
LABEL_SPACE_SPLITS: tuple[str, ...] = ("train", "devel", "train_synthetic")

SECONDARY_READING_CAVEAT = (
    "The SLURP unexposed 500 inside DEV-1000 is the LOCKED baseline's own population. Every "
    "number this receipt reports over DEV-1000 or any subset of it is a SECONDARY READING, "
    "descriptive over already-sealed records; it must NOT be used to revise, re-tune or restate "
    "the 2026-08-25 baseline lock."
)


class CoverageCheckError(RuntimeError):
    """Fail-closed error for this check."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# Q1 -- the label space, straight out of the governed bytes
# ---------------------------------------------------------------------------


def label_space_of_split(metadata_dir: Path, split_id: str) -> dict[str, object]:
    """Distinct scenario / action / intent inventory of one governed jsonl.

    Counted two ways on purpose. ``intent_field`` is SLURP's OWN ``intent``
    label; ``scenario_action`` is the string
    :func:`~..rails.knowledge_build.slurp_kb_rows` synthesizes and keys the
    whole KB by. If those two disagree the builder is modelling a different
    vocabulary from the one the corpus ships, and the disagreement is
    reported per row rather than assumed away.
    """

    from ..data.slurp import _SPLIT_FILES  # noqa: SLF001 -- reused, not reimplemented

    if split_id not in _SPLIT_FILES:
        raise CoverageCheckError(f"unknown SLURP split {split_id!r}")
    if split_id == "test":
        raise CoverageCheckError(
            "test.jsonl is HELD OUT and this check never opens it (study CLAUDE.md research "
            "boundary)"
        )
    path = Path(metadata_dir) / _SPLIT_FILES[split_id]
    if not path.is_file():
        raise CoverageCheckError(f"governed SLURP metadata file missing: {path}")

    intent_field: Counter[str] = Counter()
    scenario_action: Counter[str] = Counter()
    scenarios: set[str] = set()
    actions: set[str] = set()
    mismatches: list[dict[str, object]] = []
    rows = 0
    form_counts: Counter[str] = Counter()
    intents_per_pair: dict[str, set[str]] = {}
    pairs_per_intent: dict[str, set[str]] = {}
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            rows += 1
            scenario = record.get("scenario")
            action = record.get("action")
            declared = record.get("intent")
            if not isinstance(scenario, str) or not isinstance(action, str):
                raise CoverageCheckError(f"{path.name} line {line_no}: scenario/action not strings")
            synthesized = f"{scenario}_{action}"
            scenarios.add(scenario)
            actions.add(action)
            scenario_action[synthesized] += 1
            if isinstance(declared, str) and declared:
                intent_field[declared] += 1
                intents_per_pair.setdefault(synthesized, set()).add(declared)
                pairs_per_intent.setdefault(declared, set()).add(synthesized)
                if declared == synthesized:
                    form_counts["equals_scenario_action"] += 1
                elif declared == action:
                    form_counts["equals_action_only"] += 1
                else:
                    form_counts["neither_form"] += 1
                if declared != synthesized and len(mismatches) < 20:
                    mismatches.append(
                        {
                            "line": line_no,
                            "slurp_id": record.get("slurp_id"),
                            "intent_field": declared,
                            "scenario_action": synthesized,
                        }
                    )
            else:
                form_counts["intent_field_absent"] += 1
    ambiguous_pairs = {
        pair: sorted(values) for pair, values in intents_per_pair.items() if len(values) > 1
    }
    ambiguous_intents = {
        intent: sorted(pairs) for intent, pairs in pairs_per_intent.items() if len(pairs) > 1
    }
    return {
        "file": path.name,
        "file_sha256": _sha256_file(path),
        "rows": rows,
        "distinct_scenarios": len(scenarios),
        "distinct_actions": len(actions),
        "distinct_intent_field": len(intent_field),
        "distinct_scenario_action": len(scenario_action),
        "intent_field_equals_scenario_action_on_every_row": not mismatches,
        "mismatch_examples": mismatches,
        "intent_field_structure": {
            "row_form_histogram": dict(sorted(form_counts.items())),
            "scenario_action_pairs_with_more_than_one_intent_field_value": len(ambiguous_pairs),
            "ambiguous_pairs": dict(sorted(ambiguous_pairs.items())),
            "intent_field_values_spanning_more_than_one_scenario_action": len(ambiguous_intents),
            "ambiguous_intent_values": dict(sorted(ambiguous_intents.items())),
            "intent_field_is_a_function_of_scenario_action": not ambiguous_pairs,
            "scenario_action_is_a_function_of_intent_field": not ambiguous_intents,
        },
        "intent_field_inventory": sorted(intent_field),
        "scenario_action_inventory": sorted(scenario_action),
        "scenario_inventory": sorted(scenarios),
        "action_inventory": sorted(actions),
    }


def official_ontology_probe(data_root: Path) -> dict[str, object]:
    """Is an OFFICIAL SLURP intent ontology resolvable offline?

    Reported as a fact, never guessed at: the governed label side and the
    pinned upstream checkout are enumerated, and if neither ships a file that
    enumerates the intent vocabulary the check says the official count is
    UNVERIFIABLE offline instead of quoting a number from memory.
    """

    checkout = Path(data_root) / "repos/slurp"
    governed = Path(data_root) / "datasets/slurp/metadata"
    candidates: list[str] = []
    for root in (checkout, governed):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            name = path.name.lower()
            if any(token in name for token in ("ontolog", "intent", "label", "taxonom")):
                candidates.append(str(path.relative_to(Path(data_root))))
            if len(candidates) > 50:
                break
    return {
        "searched_roots": [
            str(checkout.relative_to(Path(data_root))) if checkout.is_dir() else None,
            str(governed.relative_to(Path(data_root))) if governed.is_dir() else None,
        ],
        "ontology_files_found": candidates,
        "available_offline": bool(candidates),
        "note": (
            "No file in the governed label side or the pinned upstream checkout enumerates the "
            "SLURP intent vocabulary; the corpus ships the label only per utterance. The official "
            "published intent count is therefore UNVERIFIABLE from the governed bytes and is not "
            "quoted here."
            if not candidates
            else "See ontology_files_found."
        ),
    }


# ---------------------------------------------------------------------------
# Q2 / Q3 -- stage-boundary intent counts
# ---------------------------------------------------------------------------


def snapshot_modeling(snapshot) -> dict[str, object]:
    """What the PINNED snapshot models, counted three separate ways."""

    intent_label_facets = [
        facet.facet_id
        for facet in snapshot.facets
        if facet.facet_id.startswith("facet:label:intent:")
    ]
    prior_facets = [
        facet.facet_id for facet in snapshot.facets if facet.facet_id.startswith("facet:prior:")
    ]
    scenario_facets = [
        facet.facet_id
        for facet in snapshot.facets
        if facet.facet_id.startswith("facet:label:scenario:")
    ]
    action_facets = [
        facet.facet_id
        for facet in snapshot.facets
        if facet.facet_id.startswith("facet:label:action:")
    ]
    task_targets = sorted(
        {str(value.task_target) for value in snapshot.values if value.task_target is not None}
    )
    intents_from_label_facets = sorted(
        fid[len("facet:label:intent:") :] for fid in intent_label_facets
    )
    intents_from_prior_facets = sorted(fid[len("facet:prior:") :] for fid in prior_facets)
    return {
        "facet_count_total": len(snapshot.facets),
        "value_count_total": len(snapshot.values),
        "label_intent_facets": len(intent_label_facets),
        "prior_facets": len(prior_facets),
        "distinct_task_targets": len(task_targets),
        "label_scenario_facets": len(scenario_facets),
        "label_action_facets": len(action_facets),
        "values_without_task_target": sum(
            1 for value in snapshot.values if value.task_target is None
        ),
        "three_counts_agree": (
            len(intent_label_facets) == len(prior_facets) == len(task_targets)
            and set(intents_from_label_facets) == set(intents_from_prior_facets) == set(task_targets)
        ),
        "modeled_intent_inventory": task_targets,
    }


def stage_boundaries(rows: Sequence[object], selected: Sequence[object], modeled: Mapping[str, object]) -> dict[str, object]:
    """The intent count at each of the three candidate loss stages."""

    row_intents = sorted({row.intent for row in rows})
    selected_intents = sorted({row.intent for row in selected})
    emitted = list(modeled["modeled_intent_inventory"])  # type: ignore[index]
    lost_at_sampling = sorted(set(row_intents) - set(selected_intents))
    lost_at_emission = sorted(set(selected_intents) - set(emitted))
    return {
        "stage_1_row_loading": {
            "utterances": len(rows),
            "distinct_intents": len(row_intents),
            "function": "data.slurp.load_slurp_train_material -> rails.knowledge_build.slurp_kb_rows",
        },
        "stage_2_distribution_sample": {
            "utterances": len(selected),
            "distinct_intents": len(selected_intents),
            "function": "rails.knowledge_build.distribution_sample(rows, size=None, seed=20260823)",
            "intents_lost_here": lost_at_sampling,
        },
        "stage_3_facet_emission": {
            "distinct_intents": len(emitted),
            "function": "rails.knowledge_build._build_facets_and_values (pinned snapshot, read from disk)",
            "intents_lost_here": lost_at_emission,
        },
        "any_intent_lost_inside_the_builder": bool(lost_at_sampling or lost_at_emission),
    }


# ---------------------------------------------------------------------------
# Q4 -- the coverage denominator, read out of the source
# ---------------------------------------------------------------------------


def coverage_denominator_evidence() -> dict[str, object]:
    """Quote, do not paraphrase, the code that computes ``intent_coverage``."""

    from ..rails import knowledge_build as kb_build

    source_path = Path(kb_build.__file__).resolve()
    source_text = source_path.read_text(encoding="utf-8")
    report_source = inspect.getsource(kb_build.coverage_report)
    # ``_coverage_pct`` is a closure inside ``coverage_report``; extract it by
    # name from the enclosing source rather than by a line number that would
    # rot on the next edit.
    marker = "    def _coverage_pct("
    start = report_source.index(marker)
    end = report_source.index("\n\n", start)
    pct_source = report_source[start:end]
    return {
        "source_file": "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
        "source_file_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "coverage_pct_source": pct_source,
        "intent_coverage_expression": (
            '"intent_coverage": _coverage_pct(train_intent_counts, selected_intent_counts)'
        ),
        "train_intent_counts_definition": (
            "train_intent_counts = Counter(row.intent for row in rows) -- ``rows`` is the TRAIN "
            "row population the CALLER passes in, i.e. exactly what "
            "rails.knowledge_build.slurp_kb_rows returned"
        ),
        "denominator": (
            "len(train_intent_counts) -- the number of DISTINCT INTENTS PRESENT IN THE TRAIN ROWS "
            "the builder loaded. It is NOT the task's intent vocabulary, and no devel, test or "
            "ontology inventory is ever consulted by coverage_report."
        ),
    }


# ---------------------------------------------------------------------------
# Q5 -- the conservative consequence on the sealed DEV-1000 records
# ---------------------------------------------------------------------------


def dev1000_consequence(
    *, repo_root: Path, data_root: Path, modeled_intents: Sequence[str]
) -> dict[str, object]:
    """How many sealed DEV-1000 samples carry an intent the KB does not model,
    and what happened to them. DESCRIPTIVE ONLY -- see the caveat field."""

    modeled = set(modeled_intents)
    populations = lr.load_populations(repo_root)
    arms = {
        pin.arm_id: lr.load_arm(pin=pin, repo_root=repo_root, data_root=data_root)
        for pin in lr.ARM_PINS
    }
    records = {
        arm_id: lr.load_per_sample_mechanical(arm=arm) for arm_id, arm in arms.items()
    }
    gold_by_sample = dc._load_gold(  # noqa: SLF001 -- the registered gold path, not a new one
        data_root=data_root, repo_root=repo_root, sample_ids=set(populations.dev1000)
    )
    scored = {arm_id: d5.score_arm(arm=arm, gold_by_sample=gold_by_sample) for arm_id, arm in arms.items()}

    gold_intent = {
        sid: f"{gold_by_sample[sid].scenario}_{gold_by_sample[sid].action}"
        for sid in populations.dev1000
    }
    unmodeled_ids = sorted(sid for sid in populations.dev1000 if gold_intent[sid] not in modeled)
    intent_hist = Counter(gold_intent[sid] for sid in unmodeled_ids)

    def _slice(sample_ids: Sequence[str]) -> dict[str, object]:
        ids = list(sample_ids)
        blend_records = records["BLEND"]
        dispatched = [sid for sid in ids if int(blend_records[sid]["contacts"]) == 2]
        return {
            "n": len(ids),
            "blend_dispatched": len(dispatched),
            "m0_correct": sum(scored["M0"].correct[sid] for sid in ids),
            "blend_correct": sum(scored["BLEND"].correct[sid] for sid in ids),
        }

    # Fidelity: this read must reproduce the sealed lock read's own pooled
    # accuracies exactly, or its slices mean nothing.
    verdict_path = (
        Path(repo_root)
        / "docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/read-verdict.json"
    )
    verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    landed_pooled = verdict["arm_accuracies"]["DEV-1000 (pooled, descriptive)"]
    fidelity = {
        "landed_read_verdict_sha256": _sha256_file(verdict_path),
        "landed_pooled_m0_correct": int(landed_pooled["M0"]["correct"]),
        "landed_pooled_blend_correct": int(landed_pooled["BLEND"]["correct"]),
        "recomputed_pooled_m0_correct": sum(scored["M0"].correct.values()),
        "recomputed_pooled_blend_correct": sum(scored["BLEND"].correct.values()),
    }
    fidelity["reproduces_the_sealed_lock_read"] = (
        fidelity["landed_pooled_m0_correct"] == fidelity["recomputed_pooled_m0_correct"]
        and fidelity["landed_pooled_blend_correct"] == fidelity["recomputed_pooled_blend_correct"]
    )
    if not fidelity["reproduces_the_sealed_lock_read"]:
        raise CoverageCheckError(
            "this read does not reproduce the sealed DEV-1000 lock read's own pooled accuracies; "
            "its slices are therefore meaningless and the check STOPS: "
            + json.dumps(fidelity, sort_keys=True)
        )

    return {
        "secondary_reading_caveat": SECONDARY_READING_CAVEAT,
        "fidelity_gate": fidelity,
        "dev1000_distinct_gold_intents": len(set(gold_intent.values())),
        "dev1000_gold_intents_not_modeled_by_the_kb": sorted(intent_hist),
        "dev1000_samples_carrying_an_unmodeled_intent": len(unmodeled_ids),
        "unmodeled_intent_histogram": dict(sorted(intent_hist.items())),
        "unmodeled_slice": _slice(unmodeled_ids),
        "modeled_slice": _slice(
            [sid for sid in populations.dev1000 if sid not in set(unmodeled_ids)]
        ),
        "whole_dev1000": _slice(list(populations.dev1000)),
        "unexposed_500_unmodeled_samples": sum(
            1 for sid in populations.new500 if gold_intent[sid] not in modeled
        ),
        "arm_pins": {
            pin.arm_id: {
                "attempt_id": pin.attempt_id,
                "outputs_sha256": pin.outputs_sha256,
                "mechanical_sha256": pin.mechanical_sha256,
            }
            for pin in lr.ARM_PINS
        },
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(*, repo_root: Path, data_root: Path, out_path: Path) -> dict[str, object]:
    attempts = ra.arm_offline_guard()
    started = time.perf_counter()

    repo_root, data_root = Path(repo_root), Path(data_root)

    from ..data.lock import load_lock, umbrella_lock_path
    from ..data.slurp import _governed_roots  # noqa: SLF001 -- reused, not reimplemented
    from ..rails.knowledge import KnowledgeSnapshot
    from ..rails.knowledge_build import (
        KnowledgeBuildSpec,
        coverage_report,
        distribution_sample,
        slurp_kb_rows,
    )

    package_file = Path(__file__).resolve()
    if "speech-aware-evidence-acquisition" not in package_file.as_posix():
        raise CoverageCheckError(f"imported this module from {package_file}, not this checkout")

    lock = load_lock(umbrella_lock_path(repo_root))
    _audio_relpath, _audio_root, metadata_dir = _governed_roots(lock, data_root)

    # ---- Q1: the label space --------------------------------------------
    label_space = {
        split_id: label_space_of_split(metadata_dir, split_id) for split_id in LABEL_SPACE_SPLITS
    }
    train_sa = set(label_space["train"]["scenario_action_inventory"])  # type: ignore[index]
    devel_sa = set(label_space["devel"]["scenario_action_inventory"])  # type: ignore[index]
    synth_sa = set(label_space["train_synthetic"]["scenario_action_inventory"])  # type: ignore[index]
    train_if = set(label_space["train"]["intent_field_inventory"])  # type: ignore[index]
    devel_if = set(label_space["devel"]["intent_field_inventory"])  # type: ignore[index]
    label_space_union = {
        "train_union_devel_scenario_action": len(train_sa | devel_sa),
        "train_union_devel_intent_field": len(train_if | devel_if),
        "devel_scenario_action_absent_from_train": sorted(devel_sa - train_sa),
        "devel_intent_field_absent_from_train": sorted(devel_if - train_if),
        "train_synthetic_scenario_action_absent_from_train": sorted(synth_sa - train_sa),
        "train_synthetic_union_train_scenario_action": len(train_sa | synth_sa),
        "test_split": "NOT OPENED, NOT LOADED, NOT ENUMERATED (held out)",
    }
    official = official_ontology_probe(data_root)

    # ---- Q2/Q3: stage boundaries against the PINNED snapshot -------------
    snapshot_path = data_root / dc.SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    measured_snapshot_hash = snapshot.content_hash()
    if measured_snapshot_hash != dc.SNAPSHOT_SHA256:
        raise CoverageCheckError(
            f"pinned snapshot hashes to {measured_snapshot_hash}, not {dc.SNAPSHOT_SHA256}"
        )
    modeled = snapshot_modeling(snapshot)

    spec = KnowledgeBuildSpec(carrier_lock_key="slurp", datastore_size=None, seed=20260823)
    rows = slurp_kb_rows(lock, data_root)
    selected = distribution_sample(rows, spec.datastore_size, spec.seed)
    stages = stage_boundaries(rows, selected, modeled)

    # ---- Q4: the denominator, and what the receipt's 1.0 means -----------
    denominator = coverage_denominator_evidence()
    recomputed = coverage_report(snapshot, rows)
    kb_receipt_path = repo_root / KB_BUILD_RECEIPT_RELPATH
    kb_receipt = json.loads(kb_receipt_path.read_text(encoding="utf-8"))
    landed = kb_receipt["coverage_report"]
    reproduces = (
        float(recomputed["intent_coverage"]) == float(landed["intent_coverage"])
        and recomputed["counts"] == landed["counts"]
    )
    task_vocabulary = len(train_sa | devel_sa)
    denominator["measured_denominator"] = int(recomputed["counts"]["train_intents"])
    denominator["task_intent_vocabulary_train_union_devel"] = task_vocabulary
    denominator["denominator_equals_task_vocabulary"] = (
        int(recomputed["counts"]["train_intents"]) == task_vocabulary
    )
    denominator["full_tier_selected_equals_train_rows"] = bool(
        int(recomputed["counts"]["selected_utterances"])
        == int(recomputed["counts"]["train_utterances"])
    )
    denominator["reproduces_the_landed_receipt"] = bool(reproduces)
    denominator["landed_intent_coverage"] = landed["intent_coverage"]
    denominator["recomputed_intent_coverage"] = recomputed["intent_coverage"]

    # ---- Q5: the sealed DEV-1000 consequence -----------------------------
    consequence = dev1000_consequence(
        repo_root=repo_root,
        data_root=data_root,
        modeled_intents=list(modeled["modeled_intent_inventory"]),  # type: ignore[arg-type]
    )

    document = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "ledger_registration_commit": LEDGER_REGISTRATION_COMMIT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "secondary_reading_caveat": SECONDARY_READING_CAVEAT,
        "zero_contact_proof": {
            "offline_guard": {
                "armed_before_first_input": True,
                "outbound_connection_attempts": attempts.count,
                "targets": list(attempts.targets),
            },
            "resident_service_untouched": (
                "llama-server pid 38623 on port 8090 was not contacted, probed, reconfigured or "
                "stopped"
            ),
        },
        "inputs": {
            "snapshot_relpath": dc.SNAPSHOT_RELPATH,
            "snapshot_pinned_sha256": dc.SNAPSHOT_SHA256,
            "snapshot_measured_content_hash": measured_snapshot_hash,
            "snapshot_file_sha256": _sha256_file(snapshot_path),
            "kb_build_receipt_relpath": KB_BUILD_RECEIPT_RELPATH,
            "kb_build_receipt_sha256": _sha256_file(kb_receipt_path),
            "contract_relpath": CONTRACT_RELPATH,
            "contract_sha256": _sha256_file(repo_root / CONTRACT_RELPATH),
            "governed_metadata_dir": str(metadata_dir),
        },
        "q1_label_space": {
            "per_split": label_space,
            "union": label_space_union,
            "official_ontology": official,
        },
        "q2_snapshot_models": modeled,
        "q3_stage_boundaries": stages,
        "q4_coverage_denominator": denominator,
        "q5_consequence": consequence,
        "docstring_claim_under_test": {
            "file": "src/speech_aware_evidence_acquisition/rails/knowledge_build.py",
            "claim": "SLURP train: 91 intents, 55 entity types",
            "measured_train_intents_scenario_action": int(
                label_space["train"]["distinct_scenario_action"]  # type: ignore[index]
            ),
            "measured_train_intents_intent_field": int(
                label_space["train"]["distinct_intent_field"]  # type: ignore[index]
            ),
            "measured_train_entity_types": int(recomputed["counts"]["train_entity_types"]),
        },
        "timing_seconds": round(time.perf_counter() - started, 3),
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    document = run(
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
        out_path=Path(args.out),
    )
    print(json.dumps(document["q3_stage_boundaries"], indent=1, sort_keys=True))
    print(json.dumps(document["q2_snapshot_models"]["three_counts_agree"], indent=1))
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
