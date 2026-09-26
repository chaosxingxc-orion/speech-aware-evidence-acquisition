#!/usr/bin/env python3
"""How SLURP ``train_synthetic`` could be used efficiently -- a model-free measurement.

Owner decision row 132 (2026-09-26) admits SLURP's ``train_synthetic`` as a priority
analysis item with one boundary that is a rule and not a preference: **its audio is TTS
and is refused** under this study's "Human speech and its linguistic content only", so
only the TEXT and LABEL side enters. Nothing in this read reads, synthesises, encodes,
embeds or supplies a single synthetic audio file; ``slurp_synth`` is never opened.

ZERO CONTACTS. No model, server, tokenizer, encoder, embedder, scorer, ASR, network, GPU
or paid-API contact. Inputs are the governed SLURP label files, four released knowledge
snapshots, the sealed bad-case bank, the sealed per-sample official score files of the two
PLAN arms, and committed roster receipts. The script writes a JSON payload and a markdown
report and nothing else; it opens no config, no policy and no store-construction path.

COUNTS, TYPES AND IDS ONLY. No utterance text, sentence, transcript, delivered text, gold
filler value or knowledge body text is printed, cached or committed. Fillers and sentences
enter set arithmetic in memory and leave it only as integers; sentence patterns are counted
and never emitted, not even as a hash.

A DIAGNOSTIC, never a gate. It admits nothing, releases no store, registers no cell and
authorises no flight. Every number is a development number on a TRAIN construction fold or
a DEV roster (owner decisions 28 and 86) and is never a test claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.null_calibration_cli import (  # noqa: E402
    rows_for,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _SPLIT_FILES,
    _entity_filler,
    _entity_type,
    _read_jsonl,
    _tokens_by_id,
)

RECIPE_ID = "slurp-train-synthetic-efficient-use-v1"
SCHEMA = "saea-slurp-train-synthetic-efficient-use-v1"
RUN_ID = "SAEA-SLURP-TRAIN-SYNTHETIC-EFFICIENT-USE-V1"
DEFAULT_MARKDOWN = "docs/results/2026-09-26-slurp-train-synthetic-efficient-use-analysis.md"
METADATA_RELDIR = "datasets/slurp/metadata"
BANK_RELPATH = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
POOL_RELPATH = (
    "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
)
POOL_MINUS_R01_RELPATH = (
    "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json"
)
CONTRACT_RELPATH = "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
THIN_FILLER_CUT = 10
ENTITY_CLASSES = ("ENTITY-FN-ONLY", "ENTITY-FP-ONLY", "ENTITY-MIXED")
SCORE_FIELDS = (
    "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
    "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn",
    "slot_f1_exact_tp", "slot_f1_exact_fp", "slot_f1_exact_fn",
    "scenario_action_exact",
)
MICRO = {
    "slu_f1_micro": (
        ("slu_f1_word_tp", "slu_f1_char_tp"),
        ("slu_f1_word_fp", "slu_f1_char_fp"),
        ("slu_f1_word_fn", "slu_f1_char_fn"),
    ),
    "span_f1_micro": (("slot_f1_exact_tp",), ("slot_f1_exact_fp",), ("slot_f1_exact_fn",)),
}
ROSTERS = (
    {
        "key": "train-fold-a",
        "label": "TRAIN Fold A (construction roster, 1,080 rows)",
        "roster_relpath": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
        "scorer": "slurp-slu-official-train",
        "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
        "attempt": "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
    },
    {
        "key": "dev2000-added",
        "label": "DEV-2000-ADDED (fresh roster, 1,000 rows)",
        "roster_relpath": "docs/receipts/rosters/slurp-dev-2000-added-v1.json",
        "scorer": "slurp-slu-official",
        "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
        "attempt": "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
    },
)
#: Construction rosters and pools the retained slice must stay legal beside.
CONSTRUCTION_ROSTERS = (
    ("R01C", "docs/receipts/rosters/slurp-stage3-construction-r01c.json"),
    ("Fold A", "docs/receipts/rosters/slurp-evo-fold-a-v2.json"),
    ("Fold B", "docs/receipts/rosters/slurp-evo-fold-b-v2.json"),
    ("exemplar draw", "docs/receipts/rosters/slurp-evo-exemplars-v2.json"),
)

_WS = re.compile(r"\s+")
_KEEP = re.compile(r"[^a-z0-9' ]+")


class ReadError(SystemExit):
    """Refuse rather than report a number this read cannot bind to sealed bytes."""


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def norm_sentence(text: str) -> str:
    """NFKC, case-folded, punctuation-to-space, whitespace-collapsed. Never emitted."""
    folded = _KEEP.sub(" ", unicodedata.normalize("NFKC", text).lower())
    return _WS.sub(" ", folded).strip()


def read_split(metadata_dir: Path, split: str) -> dict[int, dict]:
    """One utterance per ``slurp_id``: labels, gold (type, filler) pairs, and two
    text-derived keys that never leave this process -- the normalised sentence and the
    entity-masked pattern. The (type, filler) join is the loader's own, which is the
    official SLURP eval script's own gold-side join."""
    path = metadata_dir / _SPLIT_FILES[split]
    if not path.is_file():
        raise ReadError(f"governed SLURP {split} file missing: {path}")
    out: dict[int, dict] = {}
    for line_no, raw in enumerate(_read_jsonl(path), start=1):
        context = f"SLURP {split}.jsonl line {line_no}"
        slurp_id = raw.get("slurp_id")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            raise ReadError(f"{context}: slurp_id must be an int")
        tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
        raw_entities = raw.get("entities")
        if not isinstance(raw_entities, list):
            raise ReadError(f"{context}: entities must be a list")
        entities = tuple(
            sorted(
                (
                    _entity_type(entity, context),
                    _entity_filler(tokens_by_id, entity.get("span"), context),
                )
                for entity in raw_entities
            )
        )
        masked: list[str] = []
        covered: dict[int, str] = {}
        for entity in raw_entities:
            etype = _entity_type(entity, context)
            for token_id in entity.get("span") or []:
                covered[int(token_id)] = etype
        previous = None
        for token_id in sorted(tokens_by_id):
            mask = covered.get(token_id)
            if mask is None:
                masked.append(tokens_by_id[token_id].lower())
                previous = None
            elif mask != previous:
                masked.append(f"<{mask}>")
                previous = mask
        record = {
            "slurp_id": slurp_id,
            "intent": f"{raw['scenario']}_{raw['action']}",
            "scenario": raw["scenario"],
            "entities": entities,
            "sentence_key": norm_sentence(str(raw.get("sentence") or "")),
            "pattern_key": " ".join(masked),
            "recordings": len(raw.get("recordings") or []),
        }
        if slurp_id in out:
            raise ReadError(f"{context}: repeats slurp_id {slurp_id}")
        out[slurp_id] = record
    return out


def pool_slurp_ids(snapshot: dict) -> set[int]:
    """Every TRAIN utterance the released pool draws on, from its own source ids."""
    ids: set[int] = set()
    for value in snapshot["values"]:
        for sample_id in value.get("source_sample_ids") or []:
            parts = str(sample_id).split(":")
            if len(parts) < 3 or parts[0] != "slurp" or not parts[2].isdigit():
                raise ReadError(f"pool source id {sample_id!r} is not a SLURP sample id")
            ids.add(int(parts[2]))
    return ids


def roster_ids(repo: Path, relpath: str) -> list[str]:
    document = json.loads((repo / relpath).read_text(encoding="utf-8"))
    ids = [item.get("sample_id") or item.get("id") for item in document.get("items") or []]
    if not ids or any(not isinstance(value, str) for value in ids):
        raise ReadError(f"{relpath}: carries no sample_id list")
    return ids


def utterance_ids_of(sample_ids) -> set[int]:
    out: set[int] = set()
    for sample_id in sample_ids:
        parts = str(sample_id).split(":")
        if len(parts) < 3 or not parts[2].isdigit():
            raise ReadError(f"{sample_id!r} is not a SLURP sample id")
        out.add(int(parts[2]))
    return out


def f1(tp: float, fp: float, fn: float) -> float:
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0


def headroom(rows: dict, ids: list[str], members: set[str]) -> dict:
    """EXACT pooled upper bound if every row of ``members`` delivered gold: tp -> tp + fn,
    fp -> 0, fn -> 0, every other row untouched. The bad-case bank's own identity."""
    out = {}
    for metric, (tps, fps, fns) in MICRO.items():
        base = [0.0, 0.0, 0.0]
        fixed = [0.0, 0.0, 0.0]
        for sample_id in ids:
            row = rows[sample_id]
            tp = sum(row[name] for name in tps)
            fp = sum(row[name] for name in fps)
            fn = sum(row[name] for name in fns)
            base[0] += tp
            base[1] += fp
            base[2] += fn
            if sample_id in members:
                fixed[0] += tp + fn
            else:
                fixed[0] += tp
                fixed[1] += fp
                fixed[2] += fn
        now = 100.0 * f1(*base)
        repaired = 100.0 * f1(*fixed)
        out[metric] = {"now": now, "repaired": repaired, "recoverable_pp": repaired - now}
    return out


def load_arm_rows(data_root: Path, spec: dict, ids: list[str]) -> dict:
    path = data_root / "runs" / spec["run_id"] / spec["attempt"] / f"{spec['run_id']}.scores.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = rows_for({"verified": True, "scores": raw}, spec["scorer"], SCORE_FIELDS)
    missing = sorted(set(ids) - set(rows))
    if missing:
        raise ReadError(f"{spec['run_id']}: per_sample is missing {len(missing)} roster rows")
    official = ((raw.get(spec["scorer"]) or {}).get("aggregate") or {}).get("official") or {}
    for metric, groups in MICRO.items():
        published = official.get({"slu_f1_micro": "slu_f1", "span_f1_micro": "span_f1"}[metric])
        totals = [0.0, 0.0, 0.0]
        for sample_id in ids:
            for index, names in enumerate(groups):
                totals[index] += sum(rows[sample_id][name] for name in names)
        scale = 100.0 if float(published) > 1.5 else 1.0
        if abs(scale * f1(*totals) - float(published)) > 1e-6:
            raise ReadError(f"{spec['run_id']}: recomputed {metric} does not reproduce {published}")
    # Only the four numeric official fields are carried forward: the sealed aggregate also holds
    # the evaluator's own rendered report string, and a payload should carry numbers, not reports.
    return {
        "path": str(path),
        "sha256": digest(path),
        "rows": rows,
        "official": {
            name: float(official[name])
            for name in ("slu_f1", "span_f1", "intent_accuracy", "action_accuracy")
            if isinstance(official.get(name), (int, float)) and not isinstance(official.get(name), bool)
        },
    }


def measure(repo: Path, data_root: Path) -> dict:
    metadata_dir = data_root / METADATA_RELDIR
    splits = {name: read_split(metadata_dir, name) for name in ("train", "devel", "test", "train_synthetic")}
    train, devel, test, synth = (splits[k] for k in ("train", "devel", "test", "train_synthetic"))

    # ---- 1. the decontamination filter, re-run here -------------------------------
    held_ids = set(devel) | set(test)
    held_sentences = {r["sentence_key"] for r in devel.values()} | {r["sentence_key"] for r in test.values()}
    retained = {
        sid: row
        for sid, row in synth.items()
        if sid not in held_ids and row["sentence_key"] not in held_sentences
    }
    recurrence = {
        "devel_ids_recurring": sum(1 for sid in devel if sid in synth),
        "devel_rows": len(devel),
        "test_ids_recurring": sum(1 for sid in test if sid in synth),
        "test_rows": len(test),
        "dropped_by_id": sum(1 for sid in synth if sid in held_ids),
        "dropped_by_sentence_only": sum(
            1 for sid, row in synth.items()
            if sid not in held_ids and row["sentence_key"] in held_sentences
        ),
    }

    train_sentences = {r["sentence_key"] for r in train.values()}
    train_patterns = {r["pattern_key"] for r in train.values()}
    train_fillers: dict[str, set[str]] = defaultdict(set)
    for row in train.values():
        for etype, filler in row["entities"]:
            train_fillers[etype].add(filler)

    pool_snapshot = json.loads((data_root / POOL_RELPATH).read_text(encoding="utf-8"))
    minus_snapshot = json.loads((data_root / POOL_MINUS_R01_RELPATH).read_text(encoding="utf-8"))
    contract_snapshot = json.loads((data_root / CONTRACT_RELPATH).read_text(encoding="utf-8"))
    pool_ids = pool_slurp_ids(pool_snapshot)
    store_fillers: set[tuple[str, str]] = set()
    store_by_type: dict[str, set[str]] = defaultdict(set)
    for sid in pool_ids:
        for pair in train[sid]["entities"]:
            store_fillers.add(pair)
            store_by_type[pair[0]].add(pair[1])
    contract_types = sorted(
        facet["facet_id"].split(":", 1)[1] for facet in contract_snapshot["facets"]
    )

    synth_fillers_by_type: dict[str, set[str]] = defaultdict(set)
    rows_by_type: Counter = Counter()
    for row in retained.values():
        for etype, filler in row["entities"]:
            synth_fillers_by_type[etype].add(filler)
        for etype in {pair[0] for pair in row["entities"]}:
            rows_by_type[etype] += 1

    new_sentences = {r["sentence_key"] for r in retained.values()} - train_sentences
    new_patterns = {r["pattern_key"] for r in retained.values()} - train_patterns
    retained_sentence_in_train = sum(
        1 for r in retained.values() if r["sentence_key"] in train_sentences
    )

    per_type = []
    for etype in sorted(set(train_fillers) | set(synth_fillers_by_type) | set(contract_types)):
        new_vs_train = sorted(synth_fillers_by_type.get(etype, set()) - train_fillers.get(etype, set()))
        new_vs_store = sorted(synth_fillers_by_type.get(etype, set()) - store_by_type.get(etype, set()))
        per_type.append({
            "type": etype,
            "train_fillers": len(train_fillers.get(etype, set())),
            "store_fillers": len(store_by_type.get(etype, set())),
            "synth_fillers": len(synth_fillers_by_type.get(etype, set())),
            "new_vs_train": len(new_vs_train),
            "new_vs_store": len(new_vs_store),
            "retained_rows": rows_by_type.get(etype, 0),
            "has_contract": etype in set(contract_types),
        })
    thin_types = sorted(
        (entry for entry in per_type if entry["train_fillers"] < THIN_FILLER_CUT and entry["train_fillers"]),
        key=lambda entry: (entry["train_fillers"], entry["type"]),
    )

    per_intent = []
    intents = sorted({r["intent"] for r in train.values()} | {r["intent"] for r in retained.values()})
    train_intents = {r["intent"] for r in train.values()}
    for intent in intents:
        members = [r for r in retained.values() if r["intent"] == intent]
        sentences = {r["sentence_key"] for r in members} - train_sentences
        patterns = {r["pattern_key"] for r in members} - train_patterns
        fillers = {pair for r in members for pair in r["entities"]} - store_fillers
        per_intent.append({
            "intent": intent,
            "retained_rows": len(members),
            "new_sentences": len(sentences),
            "new_patterns": len(patterns),
            "new_fillers_vs_store": len(fillers),
            "in_train_label_space": intent in train_intents,
        })

    # ---- 2. where it lands against the measured error mass ------------------------
    bank: dict[str, list[dict]] = defaultdict(list)
    with (data_root / BANK_RELPATH).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            bank[row["roster"]].append(row)
    thickened = {entry["type"] for entry in per_type if entry["new_vs_store"] > 0}
    #: Every retained row that contributes a (type, filler) pair, kept as its identity pair
    #: so a contribution can be told apart from the evaluated row's OWN re-synthesis.
    contributors: dict[tuple[str, str], set[tuple[int, str]]] = defaultdict(set)
    for row in retained.values():
        for pair in row["entities"]:
            contributors[pair].add((row["slurp_id"], row["sentence_key"]))
    synth_pairs = set(contributors)
    landing = []
    for spec in ROSTERS:
        ids = sorted(roster_ids(repo, spec["roster_relpath"]))
        arm = load_arm_rows(data_root, spec, ids)
        split = devel if spec["key"] == "dev2000-added" else train
        per_class = []
        members_b: set[str] = set()
        members_b_clean: set[str] = set()
        members_b_clean_stable: set[str] = set()
        for name in ENTITY_CLASSES:
            rows = [r for r in bank[spec["key"]] if r["plan_class"] == name]
            counts = {
                "class": name, "rows": len(rows), "missed_items": 0,
                "rows_type_thickened": 0, "items_type_thickened": 0,
                "rows_value_absent": 0, "items_value_absent": 0,
                "rows_value_absent_and_in_synth": 0, "items_value_absent_and_in_synth": 0,
                "items_absent_and_not_in_synth": 0,
                "items_self_resynthesis_only": 0, "rows_self_resynthesis_only": 0,
                "items_clean": 0, "rows_clean": 0, "rows_clean_stable_wrong": 0,
            }
            for row in rows:
                utt = split[int(row["sample_id"].split(":")[2])]
                if tuple(sorted({p[0] for p in utt["entities"]})) != tuple(row["gold_entity_types"]):
                    raise ReadError(f"{row['sample_id']}: gold types disagree with the sealed bank")
                missed = [p for p in utt["entities"] if p[0] in set(row["fn_types"])]
                counts["missed_items"] += len(missed)
                hit_type = [p for p in missed if p[0] in thickened]
                absent = [p for p in missed if p not in store_fillers]
                both = [p for p in absent if p in synth_pairs]
                # A pair only counts as genuinely NEW material when some retained row that
                # carries it is neither the evaluated utterance itself (same slurp_id) nor a
                # re-synthesis of its sentence. Otherwise the slice is handing the scored row
                # its own gold back, which is contamination and not knowledge.
                clean = [
                    pair for pair in both
                    if any(
                        sid != utt["slurp_id"] and key != utt["sentence_key"]
                        for sid, key in contributors[pair]
                    )
                ]
                counts["items_type_thickened"] += len(hit_type)
                counts["items_value_absent"] += len(absent)
                counts["items_value_absent_and_in_synth"] += len(both)
                counts["items_absent_and_not_in_synth"] += len(absent) - len(both)
                counts["items_self_resynthesis_only"] += len(both) - len(clean)
                counts["items_clean"] += len(clean)
                counts["rows_type_thickened"] += 1 if hit_type else 0
                counts["rows_value_absent"] += 1 if absent else 0
                if both:
                    counts["rows_value_absent_and_in_synth"] += 1
                    members_b.add(row["sample_id"])
                if both and not clean:
                    counts["rows_self_resynthesis_only"] += 1
                if clean:
                    counts["rows_clean"] += 1
                    members_b_clean.add(row["sample_id"])
                    if row["stability_joint"] == "STABLE-WRONG":
                        counts["rows_clean_stable_wrong"] += 1
                        members_b_clean_stable.add(row["sample_id"])
            per_class.append(counts)
        landing.append({
            "roster": spec["key"], "label": spec["label"], "rows": len(ids),
            "scores_sha256": arm["sha256"], "official": arm["official"],
            "classes": per_class,
            "ceiling_all": headroom(arm["rows"], ids, members_b),
            "ceiling_clean": headroom(arm["rows"], ids, members_b_clean),
            "ceiling_clean_stable_wrong": headroom(arm["rows"], ids, members_b_clean_stable),
            "condition_b_rows": len(members_b),
            "condition_b_rows_clean": len(members_b_clean),
            "condition_b_rows_clean_stable_wrong": len(members_b_clean_stable),
        })

    # ---- 4. disjointness and hygiene ---------------------------------------------
    hygiene = {
        "retained_rows": len(retained),
        "synth_rows": len(synth),
        "retained_share": len(retained) / len(synth),
        "retained_ids_in_devel": sum(1 for sid in retained if sid in devel),
        "retained_ids_in_test": sum(1 for sid in retained if sid in test),
        "retained_sentences_in_devel_or_test": sum(
            1 for r in retained.values() if r["sentence_key"] in held_sentences
        ),
        "retained_ids_in_train": sum(1 for sid in retained if sid in train),
        "retained_sentence_in_train": retained_sentence_in_train,
        "rosters": [],
    }
    for label, relpath in CONSTRUCTION_ROSTERS:
        utt_ids = utterance_ids_of(roster_ids(repo, relpath))
        keys = {train[sid]["sentence_key"] for sid in utt_ids if sid in train}
        hygiene["rosters"].append({
            "roster": label, "relpath": relpath, "utterances": len(utt_ids),
            "retained_sharing_slurp_id": sum(1 for sid in retained if sid in utt_ids),
            "retained_sharing_sentence": sum(
                1 for r in retained.values() if r["sentence_key"] in keys
            ),
        })

    return {
        "schema": SCHEMA, "recipe": RECIPE_ID, "run_id": RUN_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {
            "model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
            "scorer": 0, "asr": 0, "network": 0, "gpu_hours": 0.0, "audio_seconds": 0.0,
            "synthetic_audio_files_opened": 0,
        },
        "inputs": [
            {"relpath": f"{METADATA_RELDIR}/{_SPLIT_FILES[name]}",
             "sha256": digest(metadata_dir / _SPLIT_FILES[name]), "rows": len(splits[name])}
            for name in ("train", "devel", "test", "train_synthetic")
        ] + [
            {"relpath": relpath, "sha256": digest(data_root / relpath)}
            for relpath in (POOL_RELPATH, POOL_MINUS_R01_RELPATH, CONTRACT_RELPATH, BANK_RELPATH)
        ],
        "pool": {
            "values": len(pool_snapshot["values"]),
            "minus_r01_values": len(minus_snapshot["values"]),
            "source_recordings": len(pool_snapshot["source_sample_ids"]),
            "utterances_joined": len(pool_ids),
            "distinct_type_filler_pairs": len(store_fillers),
            "contract_entries": len(contract_types),
        },
        "filter": {
            "synth_rows": len(synth), "retained": len(retained),
            "retained_share": len(retained) / len(synth), **recurrence,
            "new_sentences_vs_train": len(new_sentences),
            "new_patterns_vs_train": len(new_patterns),
            "retained_sentence_already_in_train": retained_sentence_in_train,
            "new_fillers_vs_train": sum(entry["new_vs_train"] for entry in per_type),
            "new_fillers_vs_store": sum(entry["new_vs_store"] for entry in per_type),
            "thin_types": len(thin_types),
            "thin_types_with_rows": sum(1 for entry in thin_types if entry["retained_rows"] > 0),
            "thin_types_gaining": sum(1 for entry in thin_types if entry["new_vs_train"] > 0),
            "thin_types_gaining_vs_store": sum(
                1 for entry in thin_types if entry["new_vs_store"] > 0
            ),
            "thin_types_new_fillers": sum(entry["new_vs_train"] for entry in thin_types),
            "out_of_label_space_intents": sorted(
                entry["intent"] for entry in per_intent
                if not entry["in_train_label_space"] and entry["retained_rows"]
            ),
        },
        "per_type": per_type, "thin_types": thin_types, "per_intent": per_intent,
        "landing": landing, "hygiene": hygiene,
    }


# --------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------

def thousands(value: int) -> str:
    return f"{value:,}"


def render(payload: dict) -> str:
    out: list[str] = []
    add = out.append
    f = payload["filter"]
    pool = payload["pool"]
    h = payload["hygiene"]
    total_missed = sum(c["missed_items"] for e in payload["landing"] for c in e["classes"])
    total_b = sum(c["items_value_absent_and_in_synth"] for e in payload["landing"] for c in e["classes"])
    total_self = sum(c["items_self_resynthesis_only"] for e in payload["landing"] for c in e["classes"])
    total_clean = sum(c["items_clean"] for e in payload["landing"] for c in e["classes"])
    clean_ceilings = ", ".join(
        f"{e['roster']} {e['ceiling_clean']['slu_f1_micro']['recoverable_pp']:+.2f} pp"
        for e in payload["landing"]
    )
    add("# Using SLURP `train_synthetic` efficiently: construction only, on cost, and the ceiling is 18 items")
    add("")
    add(
        f"Date: 2026-09-26. Read id `{payload['run_id']}`, recipe `{payload['recipe']}`, schema "
        f"`{payload['schema']}`. Script `scripts/analysis/slurp_train_synthetic_efficient_use.py` "
        "renders every number below from the artefacts in section 0; two runs differ only in the "
        "payload timestamp."
    )
    add("")
    add(
        "**Zero contacts.** No model, server, tokenizer, encoder, embedder, scorer, ASR, network, "
        "GPU or paid-API contact; 0 audio seconds. Tools: `python` reads of the governed SLURP label "
        "files, three released snapshots, the sealed bad-case bank, two sealed per-sample official "
        "score files and committed roster receipts, plus `git`. **No synthetic audio file was "
        "opened.** `train_synthetic`'s audio is TTS and is refused by this study's research boundary "
        "(\"Human speech and its linguistic content only\"), so only the text and label side enters "
        "here; nothing below proposes synthesising, encoding, embedding or supplying that audio, and "
        "a reader who expects an OBS-side use of the 69,253 synthetic recordings will not find one."
    )
    add("")
    add(
        "**Counts, types and ids only.** No utterance text, sentence, transcript, delivered text, "
        "gold filler value or knowledge body text is printed or persisted. Fillers and sentences "
        "enter set arithmetic in memory and leave it as integers; the entity-masked sentence "
        "patterns are counted and never emitted, not even as a hash. Gold is used offline as a "
        "scoring key exactly as `core.scoring_batch` uses it."
    )
    add("")
    add(
        "**A DIAGNOSTIC, never a gate.** It admits nothing, releases no store, registers no cell, "
        "expands no source and authorises no flight. Fold A and DEV-2000-ADDED numbers are "
        "development numbers (owner decisions 28 and 86) and are never a test claim."
    )
    add("")
    add("## The answer, first")
    add("")
    add(
        "**1. The route question, with my own opening premise corrected.** A text-only row cannot be "
        "a QUERY -- `rails.phase_supply.QUERY_SIGNAL_MODALITIES` is `(\"speech\", \"speech+state\")` "
        "and `assert_query_signal_declares_speech` refuses a non-speech `query_source` before the "
        "file is opened -- but a knowledge row does not need to be a query. It needs to be a KEY, and "
        "**the key side of every SLURP store is already text**, by design: `kb_policy.multidim_recall` "
        "scores the row's own speech embedding against the store facet's TEXT embedding in the same "
        "2048-d space, and the comment at `phase_supply.py:167` says so outright -- \"the KEY (facet) "
        "side is deliberately UNCONSTRAINED: a key is knowledge text and always has been\". So the "
        "speech key is **not** an impossibility for this material, and a reader told otherwise would "
        "be misled. The obstacle is a price, and it is this: a facet with no row in the sealed, "
        "hash-pinned facet-vector file is silently skipped (`.get(...)` then `continue`, no error, no "
        "fallback, no receipt field), so admitting these rows means a fresh TEXT-EMBEDDING PASS over "
        "15,703 of them -- a real encoder contact -- a re-cut sealed facet-vector file, and a re-pin "
        "of the 55 baselines that pin the exemplar vectors. The new entries would then compete on "
        "PURE COSINE (`w_cos 1.0`, the other two weights zeroed) against 9,354 incumbents, with no "
        "mechanism that prefers them. Against section 3's ceiling that price is not worth paying. The "
        "one channel that needs no vector at all is `slot-contracts-v2`, selected by "
        "`intent_bindings[].intent_id` through a static per-intent index with no embedding anywhere on "
        "the path -- and it is almost empty (section 4). **Recommendation: construction-side only, on "
        "cost rather than on impossibility.**"
    )
    add("")
    add(
        f"**2. The honest upper bound is {total_clean} gold items, and most of the apparent bound is "
        f"contamination.** Of {thousands(total_missed)} missed (false-negative) gold entity items on "
        f"the entity-error rows of the two sealed PLAN rosters, {total_b} carry a (type, filler) pair "
        f"that is absent from the released exemplar pool **and** present in the retained "
        f"`train_synthetic` slice. But {total_self} of those {total_b} are supplied only by a "
        f"retained row that is the evaluated utterance itself -- same `slurp_id`, or the same "
        f"normalised sentence re-synthesised. Handing a scored row its own gold back is leakage, not "
        f"knowledge. Excluding it leaves **{total_clean} items**, whose exact pooled SLU-F1 ceiling "
        f"is {clean_ceilings}. That is the ceiling to quote for any admission -- not ENTITY-MIXED's "
        f"+17.43 / +16.47, which is the ceiling of repairing that whole class by any means."
    )
    add("")
    add(
        f"**3. What it buys is difference, not volume -- and one published figure needs correcting.** "
        f"The 2026-09-26 coverage read proved volume is not the lever (count-versus-error-rate R^2 "
        f"0.07-0.14, the sign flipping between class families, quartile curves with no knee), so this "
        f"material is only worth anything as *different* material. It supplies "
        f"{thousands(f['new_patterns_vs_train'])} entity-masked sentence patterns and "
        f"{f['new_fillers_vs_train']} (type, filler) pairs TRAIN does not hold. But the survey figure "
        f"\"fillers for 11 of the 12 thinnest entity types\" reads as more than it is: measured here, "
        f"{f['thin_types_with_rows']} of the {f['thin_types']} thinnest types receive retained ROWS, "
        f"while only **{f['thin_types_gaining']}** gains a filler value TRAIN does not already have "
        f"({f['thin_types_new_fillers']} new pair(s) in total across all twelve). The thin types get "
        f"support, not vocabulary."
    )
    add("")
    add("## 0. Inputs and identity")
    add("")
    add("| Artefact | Relpath under `SPEECHRL_DATA_DIR` | sha256 | Rows |")
    add("| --- | --- | --- | ---: |")
    for entry in payload["inputs"]:
        rows = thousands(entry["rows"]) if entry.get("rows") else "--"
        add(f"| | `{entry['relpath']}` | `{entry['sha256'][:16]}` | {rows} |")
    for entry in payload["landing"]:
        add(
            f"| {entry['roster']} PLAN `scores.json` | `runs/<run id>/<attempt>/` | "
            f"`{entry['scores_sha256'][:16]}` | {thousands(entry['rows'])} |"
        )
    add("")
    add(
        f"Each arm's sealed per-sample rows were re-pooled and had to reproduce that arm's own sealed "
        f"official SLU-F1 and span-F1 to 1e-6 before any table was built, and every bank row's "
        f"`gold_entity_types` had to agree with the governed gold read here, or the read refuses. "
        f"Released pool: {thousands(pool['values'])} exemplar values over "
        f"{thousands(pool['source_recordings'])} source recordings, joining to "
        f"{thousands(pool['utterances_joined'])} TRAIN utterances and "
        f"{thousands(pool['distinct_type_filler_pairs'])} distinct (type, filler) pairs; the "
        f"minus-R01 sibling holds {thousands(pool['minus_r01_values'])}. `slot-contracts-v2` holds "
        f"{pool['contract_entries']} entries, one per slot type. The pool already excludes Fold A, "
        f"Fold B and DEV-1000 utterances, which is why the two PLAN rosters may pin the full pool."
    )
    add("")
    add("## 1. What the filter admits (table 1)")
    add("")
    add(
        f"Re-run here rather than cited: drop every `train_synthetic` row whose `slurp_id` **or** "
        f"whose normalised sentence occurs in devel or test. {thousands(f['retained'])} of "
        f"{thousands(f['synth_rows'])} rows survive ({100 * f['retained_share']:.1f} %); "
        f"{thousands(f['dropped_by_id'])} go on the `slurp_id` and a further "
        f"{f['dropped_by_sentence_only']} on the sentence key alone. Devel recurrence is "
        f"{thousands(f['devel_ids_recurring'])} of {thousands(f['devel_rows'])} "
        f"({100 * f['devel_ids_recurring'] / f['devel_rows']:.1f} %) and the test side "
        f"{thousands(f['test_ids_recurring'])} of {thousands(f['test_rows'])} "
        f"({100 * f['test_ids_recurring'] / f['test_rows']:.1f} %). The 2026-09-26 source survey "
        f"reported 15,705 retained and 6,382 new sentences against this read's "
        f"{thousands(f['retained'])} and {thousands(f['new_sentences_vs_train'])}; the gap is two "
        f"rows and {6382 - f['new_sentences_vs_train']} sentences and it is the sentence normaliser, "
        f"not the filter -- this read's is NFKC, case-folded, punctuation-to-space, "
        f"whitespace-collapsed, stated in the script so the number is reproducible."
    )
    add("")
    add(
        f"Against TRAIN: {thousands(f['new_sentences_vs_train'])} normalised sentences and "
        f"{thousands(f['new_patterns_vs_train'])} entity-masked patterns are new, while "
        f"{thousands(f['retained_sentence_already_in_train'])} retained rows "
        f"({100 * f['retained_sentence_already_in_train'] / f['retained']:.1f} %) carry a sentence "
        f"TRAIN already holds -- those are re-synthesised prompts and add nothing but a duplicate. "
        f"{f['new_fillers_vs_train']} (type, filler) pairs are absent from TRAIN and "
        f"{f['new_fillers_vs_store']} from the released pool (the pool is smaller than TRAIN because "
        f"it excludes the fold rosters, so the second number is the larger one). The "
        f"{len(f['out_of_label_space_intents'])} intent keys outside TRAIN's label space are "
        f"{', '.join('`' + key + '`' for key in f['out_of_label_space_intents'])}; the survey "
        f"measured 0 devel and 0 test `scenario_action` keys absent from TRAIN, so they buy nothing "
        f"the task is scored on and they are not a fix for INTENT-UNCOVERED."
    )
    add("")
    add(
        "Per entity type, the 18 leading types by new-vs-store fillers; the full table and the full per-intent "
        "table (60 scored keys plus the 9 unscored) are in the payload. `store` counts distinct "
        "fillers the released pool holds for the type."
    )
    add("")
    add("| Slot type | TRAIN fillers | store fillers | retained rows | synth fillers | new vs TRAIN | new vs store |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    ordered = sorted(payload["per_type"], key=lambda e: (-e["new_vs_store"], e["type"]))
    for entry in ordered[:18]:
        add(
            f"| `{entry['type']}` | {entry['train_fillers']} | {entry['store_fillers']} | "
            f"{thousands(entry['retained_rows'])} | {entry['synth_fillers']} | "
            f"{entry['new_vs_train']} | {entry['new_vs_store']} |"
        )
    rest = ordered[18:]
    add(
        f"| *{len(rest)} remaining types, summed* | {sum(e['train_fillers'] for e in rest)} | "
        f"{sum(e['store_fillers'] for e in rest)} | {thousands(sum(e['retained_rows'] for e in rest))} | "
        f"{sum(e['synth_fillers'] for e in rest)} | {sum(e['new_vs_train'] for e in rest)} | "
        f"{sum(e['new_vs_store'] for e in rest)} |"
    )
    add("")
    add(f"## 2. The {f['thin_types']} thinnest entity types, before and after (table 2)")
    add("")
    add(
        f"\"Thinnest\" is the source survey's own definition: a TRAIN entity type holding fewer than "
        f"{THIN_FILLER_CUT} distinct fillers. This is the table the value claim was resting on, and "
        f"it does not carry it: {f['thin_types_with_rows']} of {f['thin_types']} types receive "
        f"retained rows but only {f['thin_types_gaining']} gains a filler TRAIN does not have, and "
        f"{f['thin_types_gaining_vs_store']} gain one the released pool does not have. Read it "
        f"beside the 2026-09-26 coverage read, which found the 12 types the pool shows at most ten "
        f"times carry 13 gold mentions (0.7 %), 10 FN (1.2 %) and 22 FP (2.3 %) of the two rosters' "
        f"mass -- no zero-coverage class carries any error mass to recover."
    )
    add("")
    add("| Slot type | TRAIN fillers (before) | store fillers | + new from synth | after (TRAIN + new) | retained rows | has contract |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for entry in payload["thin_types"]:
        add(
            f"| `{entry['type']}` | {entry['train_fillers']} | {entry['store_fillers']} | "
            f"{entry['new_vs_train']} | {entry['train_fillers'] + entry['new_vs_train']} | "
            f"{thousands(entry['retained_rows'])} | {'yes' if entry['has_contract'] else 'no'} |"
        )
    add("")
    add("## 3. Where it lands against the measured error mass (table 3)")
    add("")
    add(
        "One row per sealed entity-error class per roster. `missed items` are the row's gold entities "
        "whose TYPE the sealed bank records as a false negative -- the only items a new filler VALUE "
        "could repair, which is why ENTITY-FP-ONLY contributes none. `absent AND in synth` is the "
        "naive upper bound; `self re-synthesis` is the part of it supplied only by a retained row "
        "that IS the evaluated utterance (same `slurp_id`, or its sentence re-synthesised), which is "
        "leakage; **`clean` is the honest upper bound.**"
    )
    add("")
    add("| Roster | Class | Rows | Missed items | Items, type thickened | Items, value absent | Items, absent AND in synth | Items, self re-synthesis | **Items, clean** | Rows, clean | Of those, STABLE-WRONG |")
    add("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for entry in payload["landing"]:
        for cls in entry["classes"]:
            add(
                f"| {entry['roster']} | `{cls['class']}` | {thousands(cls['rows'])} | "
                f"{thousands(cls['missed_items'])} | {thousands(cls['items_type_thickened'])} | "
                f"{thousands(cls['items_value_absent'])} | {cls['items_value_absent_and_in_synth']} | "
                f"{cls['items_self_resynthesis_only']} | **{cls['items_clean']}** | "
                f"{cls['rows_clean']} | {cls['rows_clean_stable_wrong']} |"
            )
    add("")
    add(
        "The exact pooled ceiling of repairing every row that carries at least one such item, by the "
        "bad-case bank's own identity (a repaired row delivers gold: `tp -> tp + fn`, `fp -> 0`, "
        "`fn -> 0`, every other row of the roster untouched):"
    )
    add("")
    add("| Roster | SLU-F1 now | Naive rows | Naive ceiling, SLU pp | **Clean rows** | **Clean ceiling, SLU pp** | Clean span-F1 pp | Clean STABLE-WRONG rows | Ceiling, SLU pp |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for entry in payload["landing"]:
        naive = entry["ceiling_all"]["slu_f1_micro"]
        clean = entry["ceiling_clean"]["slu_f1_micro"]
        span = entry["ceiling_clean"]["span_f1_micro"]
        stable = entry["ceiling_clean_stable_wrong"]["slu_f1_micro"]
        add(
            f"| {entry['roster']} | {clean['now']:.2f} | {entry['condition_b_rows']} | "
            f"{naive['recoverable_pp']:+.2f} | **{entry['condition_b_rows_clean']}** | "
            f"**{clean['recoverable_pp']:+.2f}** | {span['recoverable_pp']:+.2f} | "
            f"{entry['condition_b_rows_clean_stable_wrong']} | {stable['recoverable_pp']:+.2f} |"
        )
    add("")
    add(
        "**Read this as a disappointment, because it is one, and note where the two rosters diverge.** "
        "Fold A's naive column is by far the larger, and that is an artefact of what Fold A is: a "
        "TRAIN roster, whose utterances the exemplar pool deliberately excludes, so its gold fillers "
        "are 'absent from the store' by design -- and whose prompts `train_synthetic` re-synthesises, "
        "so the slice can hand a Fold A row its own gold. DEV-2000-ADDED cannot have that defect, "
        "because the filter removes every devel row from the slice first. The clean column is the "
        "comparable one and it is small on both. Three prior measurements say the same thing from "
        "three directions: the 2026-09-26 coverage read puts mode (i) *absent knowledge* at 2 items "
        "in 2,705 rows at TYPE level, leaves 92-100 % of entity items in the "
        "delivered-but-ignored-or-misused residual, and shows mode (iii) *budget-excluded* is 0 rows "
        "and 0 values. This read asks the same question one grain finer, at VALUE level, and gets the "
        "same shape of answer. **The entity half of the SLURP loss is a USE failure, and no source "
        "expansion reaches a use failure.**"
    )
    add("")
    add("## 4. How it could enter, and what each route costs (table 4)")
    add("")
    add(
        "Token costs are quoted from two committed measurements made on the pinned tokenizer at "
        "registered contacts -- the 2026-09-19 M1 exemplar-compression analysis and the 2026-09-26 "
        "supply-dedup measurement -- and this read makes no tokenizer contact of its own. The "
        "per-item figures are **~37 tokens for one supplied exemplar** (737 tokens for a 20-line "
        "block at a measured 3.63 chars/token) and **~395 tokens for one slot-contract card** (mean "
        "2,028.6 chars at 5.13 chars/token), inside a 7,240-token supply block and a ~9,906-token "
        "Solver row. The dedup note's k-sweep agrees at the margin: 10 / 20 / 30 exemplars render "
        "6,898.6 / 7,271.3 / 7,520.0 Solver-block tokens, about 31 tokens per additional exemplar "
        "once the block's fixed scaffolding is already paid."
    )
    add("")
    add("| Route | What it populates | How retrieval reaches it | Token cost at supply time | What goes wrong |")
    add("| --- | --- | --- | --- | --- |")
    add(
        "| A. Extra exemplar-store entries -- the B1/M1 route, this programme's largest admitted "
        "supply gain (+12.61 SLU); the locked plan supplies **k=20** per row, not the top-5 a "
        "diagnostic figure suggests | the 9,354-entry `size-pool-annotated-exemplars` pool, one "
        "`KeyFacet` and one `ValueBundle` per utterance, 1:1 | **Possible, at a price.** The facet is "
        "a TEXT embedding, so these rows can be keyed -- but only after a fresh text-embedding pass "
        "over 15,703 rows -- over their TEXT, never over their refused TTS audio -- a re-cut sealed "
        "facet-vector file and a re-pin of the "
        "55 baselines. Until then each is silently skipped, and a value whose `task_target` is unset "
        "is skipped by the fuser too | **~37 tokens per supplied exemplar** (committed: 737 tokens for "
        "a 20-line block at 3.63 chars/token, the densest text in the request) on a 9,906-token row | "
        "The pass is the cheap part. The entries then compete on pure cosine (`w_cos 1.0`) against "
        "9,354 incumbents with nothing preferring them, and the k-sweep already showed that 20 "
        "genuinely new exemplar bodies per row moved +0.07 / +0.09 pp -- nothing. Plus the snapshot "
        "hash changes and re-pins every downstream readiness package |"
    )
    add(
        "| B. Slot-contract filler inventories -- typed values per slot, not examples | the 54 "
        "`slot-contracts-v2` entries, one per slot type, `facet_id == value_id == "
        "\"slot-contract:<slot_id>\"` | **Yes, and with no vector at all.** "
        "`_released_candidate_index` builds a static `{intent_id: value_ids}` map from the authored "
        "rows and `select_candidate_semantic_values` visits the row's at most 3 Perception candidates "
        "round-robin. No embedding, no cosine, no `query_source` on this path | **~395 tokens per "
        "card** (committed: mean 2,028.6 chars at 5.13 chars/token), about 12 cards per row = ~4,855 "
        "tokens, **49 % of the row** -- by far the most expensive route | 54 of 55 types already have "
        "a contract and the one gap (`music_album`) carries 1 gold mention and 1 FN of 1,881 and 824. "
        "90.6 % of the card characters already describe slot types neither the core nor the "
        "annotation used, so lengthening bodies feeds the wrong end. And re-authoring a card is a "
        "MODEL contact: `candidate_semantic_supply` rebuilds the snapshot from the authored source "
        "and demands byte equality |"
    )
    add(
        "| C. Negative / contrastive material for the confusable pairs | `intent-boundaries-v1`, 60 "
        "cards, one per intent, top-8 retrieved | **Possible, same price as A** -- its facets come "
        "from a text-facet encoding protocol (`saea-text-facet-encoding-protocol-v1`, 60 facets, "
        "passage prompt), so a new card needs that pass re-run and re-pinned | ~800 tokens for the "
        "8-card block at 7.53 chars/token, so ~100 tokens per card on a 1,091-token Perception block | "
        "This is the route the error mass argues for -- retrieval owns 55-64 % of the intent errors "
        "and INTENT-UNCOVERED carries +5.4 / +6.8 SLU and +12.0 / +16.9 intent -- but it needs the "
        "confusable PAIR, not a corpus, and the leading confusions (`general_quirky`, "
        "`calendar_query`, `play_music`) already sit on the most exemplar-rich intents. This read "
        "measures no contrastive gain and claims none |"
    )
    add(
        "| D. Construction-side material only, never supplied at runtime | an offline text/label pool "
        "a card author, a contract author or a rollout proposer reads | n/a -- it never enters a "
        "retrieval path, so no vector, no pass and no re-pin | **0 tokens at supply time, 0 encoder "
        "contacts, 0 re-pins** | Bounded by what construction can do with it, which section 3 caps at "
        "18 items; and it must stay disjoint from every roster it is used beside (section 5) |"
    )
    add("")
    add(
        "**Recommended route: D, construction-side only -- on cost, not on impossibility.** A and C "
        "are reachable: their keys are text and a text-embedding pass would key these rows. They are "
        "refused here because the price (an encoder pass over 15,703 rows, a new sealed vector file, "
        "a re-pin of 55 baselines) is paid against an 18-item ceiling, and because the one time this "
        "programme bought 20 genuinely new exemplar bodies per row the result was +0.07 / +0.09 pp. B "
        "needs no vector at all and is the cheapest to reach and the most expensive to carry -- ~395 "
        "tokens a card, 49 % of the row already -- and its gap is one slot type with one gold mention. "
        "D is the only route whose cost is zero on every axis, and its value is bounded by the use "
        "failure it cannot fix."
    )
    add("")
    add("## 5. Disjointness and hygiene")
    add("")
    add(
        f"The filter's own proof: of the {thousands(h['retained_rows'])} retained rows, "
        f"{h['retained_ids_in_devel']} share a `slurp_id` with devel, {h['retained_ids_in_test']} "
        f"with test and {h['retained_sentences_in_devel_or_test']} share a normalised sentence with "
        f"either -- zero on all three by construction, which is what makes the filter a proof rather "
        f"than a hope. {thousands(h['retained_ids_in_train'])} retained rows share a `slurp_id` with "
        f"TRAIN and {thousands(h['retained_sentence_in_train'])} share a sentence with it: the slice "
        f"is mostly TRAIN prompts re-synthesised, which is exactly why section 3's self-re-synthesis "
        f"column exists."
    )
    add("")
    add("| Construction roster / pool | Utterances | Retained rows sharing a `slurp_id` | Retained rows sharing a normalised sentence |")
    add("| --- | ---: | ---: | ---: |")
    for entry in h["rosters"]:
        add(
            f"| {entry['roster']} (`{entry['relpath'].split('/')[-1]}`) | "
            f"{thousands(entry['utterances'])} | "
            f"{thousands(entry['retained_sharing_slurp_id'])} | "
            f"{thousands(entry['retained_sharing_sentence'])} |"
        )
    add("")
    add(
        "**What must be true for the slice to stay legal beside those rosters.** The "
        "construction-versus-knowledge guard is `rails.runner.run_speech_native_agent_loop`, which "
        "refuses when a flown roster's sample ids intersect the bound snapshot's own "
        "`source_sample_ids`, and again when BUILD and USE share a `split_identity_hash`. It bit once "
        "(2026-09-23: 175 R01 utterances were sources of the composed stores, which is why R01C and "
        "`size-pool-annotated-exemplars-minus-r01` exist). Four conditions follow, and the devel/test "
        "filter satisfies none of them."
    )
    add("")
    add(
        "1. **The guard compares ids, not sentences, so it would not see this hazard at all.** The "
        "table above is the number that must be carried into any registration, per roster: a slice "
        "used beside Fold A must have that roster's sentence column at zero, not merely its id "
        "column. Identity-level disjointness passing while a sentence is shared is precisely the "
        "leakage section 3 measures."
    )
    add(
        "2. **The committed receipt cannot prove the sentence half.** "
        "`docs/receipts/knowledge/slurp-split-identity.json` pins devel and test at recording "
        "identity only -- its own note says scenario, action, entities, tokens and sentence \"are "
        "never read\" -- so the 79.7 % retention is not reproducible from it. A frozen "
        "normalised-sentence receipt would have to be minted, and none exists."
    )
    add(
        "3. **TRAIN exclusions propagate.** A retained row shares its `slurp_id` with a TRAIN "
        "utterance, so the fold builders' standing exclusion of every TRAIN utterance this study has "
        "already touched (739 named by the committed probe-sample receipts) carries over to the "
        "synthetic twin of that utterance."
    )
    add(
        "4. **The legality row must change first.** "
        "`analysis/information_audit_specs.py` still reads `\"train_synthetic split\": \"forbidden\"` "
        "in `_SLURP_CORPUS_STRUCTURE_LEGALITY` -- correct for the undecontaminated split, wrong for "
        "this slice. Nothing may read the split until a successor value says "
        "`construction-only-knowledge for the decontaminated slice`, and because that table is "
        "descriptive rather than executable the loader path in `slurp_spec` has to change with it or "
        "the two will disagree silently."
    )
    add("")
    add("## 6. Recommendation, and the no-harm gate it would need")
    add("")
    add(
        f"**Do not admit it as runtime supply and do not open a store for it.** Admit it, if at all, "
        f"as an offline construction-side text/label pool, under owner decision 127's terms for an "
        f"engineering-base item: sound logic, a stated ceiling, a no-harm reading, "
        f"`claims_benefit: false`, and a preregistered harm margin equal to the measured floor of its "
        f"own design. The ceiling to state is this read's own question-2 number and not the headroom "
        f"table's: **{clean_ceilings}** from {total_clean} clean gold items across both rosters, "
        f"against ENTITY-MIXED's +17.43 / +16.47 which belongs to any repair of that class by any "
        f"means. A construction-side pool touches no arm, so its no-harm design is the offline "
        f"sealed-pool floor of 0.67 pp rather than the 1.2485 / 1.2525 cross-flight floors; note that "
        f"`scripts/checks/stage3_effect_floor_check.py` has no no-harm design and no harm-margin "
        f"field yet, so today `claims_benefit: false` only relaxes the gate and a declared margin "
        f"would be trusted rather than checked -- decision 127's instruction to teach that check is "
        f"still open, and a base item should not be flown under it before it is."
    )
    add("")
    add(
        "**The smallest first step, and it costs no flight and no contact:** amend the one legality "
        "row and mint the one receipt it needs. Concretely -- change "
        "`_SLURP_CORPUS_STRUCTURE_LEGALITY`'s `train_synthetic` entry to name the decontaminated "
        "slice as `construction-only-knowledge`, with this read's filter as its receipt; freeze a "
        "normalised-sentence identity receipt for devel and test beside "
        "`slurp-split-identity.json` so the filter is reproducible from committed bytes; and record "
        "the per-roster sentence-overlap column above as the hygiene condition any consumer must "
        "meet. That is a legality edit plus a receipt plus a check. It unblocks every offline use, it "
        "commits no store, no cell and no flight, and it can be undone. Only if a construction step "
        "then NAMES a specific thin type or a specific confusable pair it wants material for does the "
        "question of a store arise -- and on section 3's measurement it should not, because the items "
        "are single digits."
    )
    add("")
    add("## 7. What this read does not say")
    add("")
    add(
        "It states no effectiveness, superiority or generalisation claim, admits nothing, releases no "
        "store, expands no source and authorises no flight. The ceilings are exact upper bounds on a "
        "PERFECT repair of the rows they name, by any means, and are not a forecast: a filler value "
        "appearing in a supplied exemplar is not the same as the Solver using it. It does not measure "
        "whether a value the store already holds reached the failing row -- that is mode (ii), and it "
        "belongs to the 2026-09-26 coverage read, which owns the finding that retrieval rather than "
        "absence is the binding constraint. It says nothing about `train_synthetic`'s audio except "
        "that the boundary refuses it, and proposes no use for it. The per-item token costs are "
        "quoted from a committed measurement, not measured here. Every roster is a discovery or dev "
        "roster and every number is a development number."
    )
    add("")
    add(
        f"Machine-readable payload: `$SPEECHRL_DATA_DIR/analysis/{RUN_ID}/payload.json` (schema "
        f"`{SCHEMA}`, recipe `{payload['recipe']}`) -- the full per-type and per-intent tables, ids, "
        f"counts and hashes only, no text and no filler value."
    )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--markdown", default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    data_root = Path(args.data_root or os.environ.get("SPEECHRL_DATA_DIR", ""))
    if not data_root.is_dir():
        raise ReadError("--data-root (or SPEECHRL_DATA_DIR) does not resolve to a directory")
    payload = measure(REPO, data_root)
    out_dir = data_root / "analysis" / RUN_ID
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "payload.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    target = REPO / args.markdown
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(payload), encoding="utf-8", newline="\n")
    print(f"wrote {target}")
    print(f"wrote {out_dir / 'payload.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
