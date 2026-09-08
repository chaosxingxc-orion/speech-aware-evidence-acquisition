#!/usr/bin/env python3
"""MF-8 -- the speech-to-knowledge audit (model-free).

Prices the owner's 2026-09-08 three-dimension direction: how (multi-speaker)
speech maps onto already-constructed knowledge in text-domain, speech-domain
and state-knowledge form. Readiness note and boundary:
``docs/readiness/2026-09-08-mf8-speech-to-knowledge-audit-v1.md``.
Exposure row ``SAEA-SLURP-MF8-SPEECH-TO-KNOWLEDGE-AUDIT-V1``.

**Zero model, GPU, tool, embedding, network and audio-decode contacts.** The
script starts no server, loads no model and decodes no waveform; flac
*headers* are the only audio bytes it touches, through the loaders' own
``soundfile.info`` path.

Subcommands
-----------
``speakers``
    Question 1: SLURP speaker structure in TRAIN and in the DEV-1000 roster,
    the speaker overlap, and the per-row same-speaker same-intent TRAIN
    exemplar distribution against other speakers'.
``comparator``
    Question 2: where the RE-LOCKED closed-list comparator fails, and whether
    the gold intent is reachable in a candidate set built WITHOUT the gold --
    which is what prices an "oracle-candidate" design that isolates matching
    from retrieval.

Boundary enforced in code, not only in prose: no devel ``sentence`` string is
ever read (``data.slurp.load_slurp_split`` does not carry one), the held-out
``test`` split is never named, and every read is a committed or governed byte
some earlier registered row already opened.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

ROW_ID = "SAEA-SLURP-MF8-SPEECH-TO-KNOWLEDGE-AUDIT-V1"
RECEIPT_DIRNAME = "2026-09-08-mf8-speech-to-knowledge-audit"
DEV1000_CONFIG = "configs/dataset/slurp-speech-native-dev1000.json"
UMBRELLA_LOCK_FALLBACK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"

# The DEV-1000 roster's own sample ids name a devel recording; this is the
# inverse of ``data.slurp._parse_record``'s sample-id construction.
_SAMPLE_ID_PARTS = 4


def recording_filename(sample_id: str) -> str:
    """``slurp:devel:000011:audio-1497266596`` to ``audio-1497266596.flac``."""

    parts = sample_id.split(":")
    if len(parts) != _SAMPLE_ID_PARTS or not parts[3]:
        raise ValueError(f"not a SLURP sample id: {sample_id!r}")
    return f"{parts[3]}.flac"


def roster_sample_ids(config_path: Path) -> tuple[str, ...]:
    """The roster's sample ids in committed file order."""

    document = json.loads(Path(config_path).read_text(encoding="utf-8"))
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError(f"{config_path} carries no items")
    ids: list[str] = []
    for item in items:
        sample_id = item.get("sample_id") if isinstance(item, Mapping) else None
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(f"{config_path} carries an item without a sample id")
        ids.append(sample_id)
    if len(set(ids)) != len(ids):
        raise ValueError(f"{config_path} repeats a sample id")
    return tuple(ids)


def histogram(values: Iterable[int]) -> dict[str, int]:
    """A stable count histogram keyed by the string of the integer."""

    return {str(key): int(count) for key, count in sorted(Counter(values).items())}


def quantiles(values: Sequence[float]) -> dict[str, float]:
    """min / p25 / median / p75 / p90 / max / mean, nearest-rank quantiles."""

    if not values:
        return {}
    ordered = sorted(float(value) for value in values)
    size = len(ordered)

    def rank(fraction: float) -> float:
        index = max(0, min(size - 1, int(round(fraction * (size - 1)))))
        return ordered[index]

    return {
        "min": ordered[0],
        "p25": rank(0.25),
        "median": rank(0.50),
        "p75": rank(0.75),
        "p90": rank(0.90),
        "max": ordered[-1],
        "mean": sum(ordered) / size,
    }


def at_least_counts(values: Sequence[int], thresholds: Sequence[int]) -> dict[str, int]:
    """How many entries reach each threshold."""

    return {
        f">={threshold}": sum(1 for value in values if value >= threshold)
        for threshold in thresholds
    }


def resolve_lock_and_root() -> tuple[Mapping[str, object], Path, Path]:
    """The umbrella lock, the controlled data root, and the lock path used."""

    from speech_aware_evidence_acquisition.data.lock import data_root, load_lock

    lock_path = REPO_ROOT.parent.parent / "docs" / "datasets.lock.json"
    if not lock_path.is_file():
        # A git worktree sits outside the registered adjacent-checkout layout;
        # the umbrella lock is still the single live authority, so it is named
        # explicitly rather than copied.
        lock_path = Path(UMBRELLA_LOCK_FALLBACK)
    if not lock_path.is_file():
        raise SystemExit(f"umbrella datasets lock not found (tried {lock_path})")
    return load_lock(lock_path), data_root(), lock_path


def command_speakers(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.data.slurp import (
        _governed_roots,
        _slurp_speaker_index,
        load_slurp_split,
        load_slurp_train_material,
    )

    lock, root, lock_path = resolve_lock_and_root()
    _, _, metadata_dir = _governed_roots(lock, root)
    speakers_by_file = _slurp_speaker_index(metadata_dir)

    train = load_slurp_train_material(lock, root)
    # TRAIN side: one row per (utterance, recording) -- the recording is the
    # unit an audio exemplar would actually carry.
    train_recordings_by_speaker_intent: dict[tuple[str, str], int] = defaultdict(int)
    train_sentences_by_speaker_intent: dict[tuple[str, str], set[str]] = defaultdict(set)
    train_recordings_by_intent: dict[str, int] = defaultdict(int)
    train_recordings_by_speaker: dict[str, int] = defaultdict(int)
    train_utterances_by_speaker: dict[str, set[str]] = defaultdict(set)
    train_intents_by_speaker: dict[str, set[str]] = defaultdict(set)
    train_recording_total = 0
    for utterance in train:
        intent = f"{utterance.scenario}_{utterance.action}"
        for recording in utterance.recordings:
            train_recording_total += 1
            key = (recording.speaker_id, intent)
            train_recordings_by_speaker_intent[key] += 1
            train_sentences_by_speaker_intent[key].add(utterance.utterance_id)
            train_recordings_by_intent[intent] += 1
            train_recordings_by_speaker[recording.speaker_id] += 1
            train_utterances_by_speaker[recording.speaker_id].add(utterance.utterance_id)
            train_intents_by_speaker[recording.speaker_id].add(intent)

    # DEV side: gold LABELS only. ``SlurpRecord`` deliberately carries no
    # reference sentence, so no devel text can reach this pass.
    devel = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)

    rows: list[dict[str, object]] = []
    for sample_id in roster:
        record = devel.get(sample_id)
        if record is None:
            raise SystemExit(f"DEV-1000 sample {sample_id!r} is absent from devel.jsonl")
        filename = recording_filename(sample_id)
        speaker = speakers_by_file.get(filename)
        if speaker is None:
            raise SystemExit(f"DEV-1000 recording {filename!r} lacks a governed speaker")
        key = (speaker, record.intent)
        same_speaker_recordings = train_recordings_by_speaker_intent.get(key, 0)
        same_speaker_sentences = len(train_sentences_by_speaker_intent.get(key, ()))
        total_recordings = train_recordings_by_intent.get(record.intent, 0)
        rows.append(
            {
                "sample_id": sample_id,
                "speaker_id": speaker,
                "gold_intent": record.intent,
                "gold_scenario": record.scenario,
                "audio_seconds": record.audio_seconds,
                "speaker_in_train": speaker in train_recordings_by_speaker,
                "train_recordings_this_speaker": train_recordings_by_speaker.get(speaker, 0),
                "same_speaker_same_intent_recordings": same_speaker_recordings,
                "same_speaker_same_intent_sentences": same_speaker_sentences,
                "other_speaker_same_intent_recordings": total_recordings - same_speaker_recordings,
                "any_speaker_same_intent_recordings": total_recordings,
            }
        )

    dev_speakers = {row["speaker_id"] for row in rows}
    train_speakers = set(train_recordings_by_speaker)
    same_speaker_values = [int(row["same_speaker_same_intent_recordings"]) for row in rows]
    same_sentence_values = [int(row["same_speaker_same_intent_sentences"]) for row in rows]
    other_speaker_values = [int(row["other_speaker_same_intent_recordings"]) for row in rows]
    thresholds = (1, 2, 3, 5, 8, 10)

    devel_speakers_all = {
        speakers_by_file[recording_filename(sample_id)]
        for sample_id in devel
        if recording_filename(sample_id) in speakers_by_file
    }

    result: dict[str, object] = {
        "schema": "saea-mf8-speaker-structure-v1",
        "row_id": ROW_ID,
        "lock_path": str(lock_path),
        "boundary": (
            "zero model, GPU, tool, embedding, network and audio-decode contacts. DEV gold "
            "INTENT LABELS only; no devel sentence text is read and the test split is never "
            "named."
        ),
        "train": {
            "utterances": len(train),
            "recordings": train_recording_total,
            "distinct_speakers": len(train_speakers),
            "recordings_per_speaker": quantiles(sorted(train_recordings_by_speaker.values())),
            "utterances_per_speaker": quantiles(
                sorted(len(value) for value in train_utterances_by_speaker.values())
            ),
            "distinct_intents_per_speaker": quantiles(
                sorted(len(value) for value in train_intents_by_speaker.values())
            ),
            "distinct_intents": len(train_recordings_by_intent),
        },
        "devel": {
            "recordings_total": len(devel),
            "distinct_speakers": len(devel_speakers_all),
            "speakers_shared_with_train": len(devel_speakers_all & train_speakers),
        },
        "dev1000": {
            "rows": len(rows),
            "distinct_speakers": len(dev_speakers),
            "speakers_also_in_train": len(dev_speakers & train_speakers),
            "rows_whose_speaker_is_in_train": sum(1 for row in rows if row["speaker_in_train"]),
            "train_recordings_per_shared_speaker": quantiles(
                sorted(
                    train_recordings_by_speaker[speaker]
                    for speaker in sorted(dev_speakers & train_speakers)
                )
            ),
            "rows_per_dev_speaker": quantiles(
                sorted(Counter(row["speaker_id"] for row in rows).values())
            ),
        },
        "same_speaker_same_intent_recordings": {
            "quantiles": quantiles(same_speaker_values),
            "histogram": histogram(same_speaker_values),
            "at_least": at_least_counts(same_speaker_values, thresholds),
        },
        "same_speaker_same_intent_sentences": {
            "quantiles": quantiles(same_sentence_values),
            "histogram": histogram(same_sentence_values),
            "at_least": at_least_counts(same_sentence_values, thresholds),
        },
        "other_speaker_same_intent_recordings": {
            "quantiles": quantiles(other_speaker_values),
            "at_least": at_least_counts(other_speaker_values, thresholds),
        },
        "rows": rows,
    }

    by_scenario: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        by_scenario[str(row["gold_scenario"])].append(
            int(row["same_speaker_same_intent_recordings"])
        )
    result["per_scenario"] = {
        scenario: {
            "n": len(values),
            "median_same_speaker_exemplars": quantiles(values).get("median"),
            "rows_with_at_least_5": sum(1 for value in values if value >= 5),
            "rows_with_zero": sum(1 for value in values if value == 0),
        }
        for scenario, values in sorted(by_scenario.items())
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "speaker-structure.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = dict(result)
    summary.pop("rows")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# Question 2 -- where the comparator fails, and what a candidate set can reach.
# ---------------------------------------------------------------------------

#: The re-locked comparator (`slurp-legal-label-projection-v2` verdict, 2026-09-06),
#: hard-coded so this read FAILS CLOSED if the same sealed bytes stop reproducing it.
COMPARATOR_INTENT_ANCHORS = {"pooled_1000": 73.10, "old500": 71.00, "new500": 75.20}
#: MF-7b's own published `intent_recall_at_k` at k = 5 on NEW500, same purpose.
NEIGHBOUR_RECALL_ANCHORS = {"speech": 83.20, "speech-state": 87.40}

SEALED_COMPARATOR_OUTPUTS = (
    "runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/attempt-20260905T060424Z-2c5596/"
    "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.outputs.jsonl"
)
SEALED_VECTOR_DIR = "vectors/slurp-kus3"
NEW500_RECEIPT = "docs/receipts/probe-samples/DEV-1000-NEW500.json"


def read_sealed_outputs(path: Path) -> dict[str, str]:
    """``sample_id -> response text`` from a sealed outputs JSONL."""

    texts: dict[str, str] = {}
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        record = json.loads(stripped)
        sample_id = record.get("sample_id")
        text = record.get("text")
        if not isinstance(sample_id, str) or not isinstance(text, str):
            raise ValueError(f"{path} line {line_no}: malformed sealed output row")
        if sample_id in texts:
            raise ValueError(f"{path} line {line_no}: duplicate sample id {sample_id!r}")
        texts[sample_id] = text
    if not texts:
        raise ValueError(f"{path} carries no sealed rows")
    return texts


def sealed_outputs_carry_logprobs(path: Path) -> bool:
    """Whether ANY sealed row carries a logprobs object.

    Candidate source (a) of the audit -- "the comparator's own top-k" -- only
    exists if the flight asked for and stored them. A substring test over the
    whole file is deliberately the weakest possible claim: a False here means
    the string never occurs, which is the strongest evidence of absence a
    sealed byte file can give.
    """

    return "logprob" in Path(path).read_text(encoding="utf-8")


def ordered_candidates(pairs: Sequence[tuple[str, float]]) -> tuple[str, ...]:
    """Distinct candidate labels in rank order, best first."""

    seen: dict[str, None] = {}
    for label, _score in pairs:
        seen.setdefault(label, None)
    return tuple(seen)


def recall_at(candidates: Sequence[str], gold: str, k: int) -> bool:
    """Is ``gold`` among the first ``k`` candidates?"""

    return gold in tuple(candidates)[:k]


def _load_vectors(path: Path, dimension: str = "content"):
    import numpy as np

    ids: list[str] = []
    rows: list[list[float]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            vectors = record.get("vectors")
            identity = record.get("id")
            if not isinstance(identity, str) or not isinstance(vectors, Mapping):
                raise ValueError(f"{path} line {line_no}: malformed sealed vector row")
            vector = vectors.get(dimension)
            if not isinstance(vector, list) or not vector:
                raise ValueError(f"{path} line {line_no}: no {dimension!r} vector")
            ids.append(identity)
            rows.append(vector)
    matrix = np.asarray(rows, dtype=np.float32)
    return tuple(ids), matrix


def command_comparator(args: argparse.Namespace) -> int:
    import numpy as np

    from speech_aware_evidence_acquisition.data.slurp import (
        _governed_roots,
        _slurp_speaker_index,
        load_slurp_split,
        load_slurp_train_material,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
        load_legal_intent_inventory,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        parse_slu_response,
        project_slu_label_v2,
    )

    lock, root, lock_path = resolve_lock_and_root()
    _, _, metadata_dir = _governed_roots(lock, root)
    speakers_by_file = _slurp_speaker_index(metadata_dir)
    inventory = load_legal_intent_inventory(lock, root)

    train = load_slurp_train_material(lock, root)
    intent_by_utterance = {
        utterance.utterance_id: f"{utterance.scenario}_{utterance.action}" for utterance in train
    }
    train_recordings_by_speaker_intent: dict[tuple[str, str], int] = defaultdict(int)
    for utterance in train:
        intent = f"{utterance.scenario}_{utterance.action}"
        for recording in utterance.recordings:
            train_recordings_by_speaker_intent[(recording.speaker_id, intent)] += 1

    devel = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)
    new500_receipt = json.loads((REPO_ROOT / NEW500_RECEIPT).read_text(encoding="utf-8"))
    new500 = {str(item["id"]) for item in new500_receipt["items"]}
    if len(new500) != int(new500_receipt["n_items"]):
        raise SystemExit("DEV-1000-NEW500 receipt item count disagrees with its own n_items")

    outputs_path = root / SEALED_COMPARATOR_OUTPUTS
    texts = read_sealed_outputs(outputs_path)
    logprobs_present = sealed_outputs_carry_logprobs(outputs_path)

    # --- the comparator's own per-row prediction, through the LOCKED rule ---
    rows: list[dict[str, object]] = []
    for sample_id in roster:
        record = devel[sample_id]
        text = texts.get(sample_id)
        if text is None:
            raise SystemExit(f"sealed outputs miss DEV-1000 row {sample_id!r}")
        scenario, action, _entities, parsed = parse_slu_response(text)
        projection = project_slu_label_v2(scenario, action, inventory, parsed=parsed)
        predicted_intent = projection.projected_intent
        speaker = speakers_by_file[recording_filename(sample_id)]
        rows.append(
            {
                "sample_id": sample_id,
                "speaker_id": speaker,
                "gold_intent": record.intent,
                "gold_scenario": record.scenario,
                "gold_action": record.action,
                "predicted_intent": predicted_intent,
                "predicted_scenario": projection.scenario,
                "predicted_action": projection.action,
                "parsed": parsed,
                "projection_branch": projection.branch,
                "correct": predicted_intent == record.intent,
                "in_new500": sample_id in new500,
                "same_speaker_same_intent_recordings": train_recordings_by_speaker_intent.get(
                    (speaker, record.intent), 0
                ),
            }
        )

    def accuracy(subset: Sequence[Mapping[str, object]]) -> float:
        return round(100.0 * sum(1 for row in subset if row["correct"]) / len(subset), 2)

    measured = {
        "pooled_1000": accuracy(rows),
        "new500": accuracy([row for row in rows if row["in_new500"]]),
        "old500": accuracy([row for row in rows if not row["in_new500"]]),
    }
    for population, expected in COMPARATOR_INTENT_ANCHORS.items():
        if abs(measured[population] - expected) > 1e-9:
            raise SystemExit(
                f"IDENTITY ANCHOR FAILED: comparator intent on {population} is "
                f"{measured[population]} against the published {expected}"
            )

    errors = [row for row in rows if not row["correct"]]

    # --- error structure -------------------------------------------------
    by_scenario: dict[str, dict[str, int]] = {}
    for row in rows:
        bucket = by_scenario.setdefault(
            str(row["gold_scenario"]), {"n": 0, "errors": 0}
        )
        bucket["n"] += 1
        if not row["correct"]:
            bucket["errors"] += 1
    for bucket in by_scenario.values():
        bucket["error_rate_pct"] = round(100.0 * bucket["errors"] / bucket["n"], 2)
        bucket["share_of_error_mass_pct"] = round(100.0 * bucket["errors"] / len(errors), 2)

    confusion = Counter(
        (str(row["gold_intent"]), str(row["predicted_intent"])) for row in errors
    )
    within_scenario = sum(
        1 for row in errors if row["predicted_scenario"] == row["gold_scenario"]
    )
    no_label = sum(1 for row in errors if row["predicted_intent"] is None)
    unparsed = sum(1 for row in errors if not row["parsed"])

    # --- candidate sources, all built WITHOUT the gold --------------------
    # (b) the PREDICTED scenario's legal intents, TRAIN prior first.
    scenario_candidates: dict[str, tuple[str, ...]] = {}
    for scenario in inventory.scenarios:
        ranked = sorted(
            inventory.actions_by_scenario[scenario],
            key=lambda candidate: (-inventory.prior(scenario, candidate), candidate),
        )
        scenario_candidates[scenario] = tuple(f"{scenario}_{action}" for action in ranked)

    # (c) the pinned Nemotron speech-vector neighbours.
    vector_dir = root / SEALED_VECTOR_DIR
    key_ids, key_matrix = _load_vectors(vector_dir / "facet-vectors.jsonl")
    key_intents = []
    for key_id in key_ids:
        utterance_id = key_id.rsplit(":", 1)[-1]
        intent = intent_by_utterance.get(utterance_id)
        if intent is None:
            raise SystemExit(f"sealed key {key_id!r} has no TRAIN intent")
        key_intents.append(intent)

    neighbour_intents: dict[str, dict[str, list[str]]] = {}
    for query_name, filename in (
        ("speech", "query-vectors-speech.jsonl"),
        ("speech-state", "query-vectors-speech-state.jsonl"),
    ):
        query_ids, query_matrix = _load_vectors(vector_dir / filename)
        index = {identity: position for position, identity in enumerate(query_ids)}
        similarity = query_matrix @ key_matrix.T
        top = np.argsort(-similarity, axis=1)[:, : args.neighbour_depth]
        table: dict[str, list[str]] = {}
        for sample_id in roster:
            position = index.get(sample_id)
            if position is None:
                raise SystemExit(f"{filename} has no vector for {sample_id!r}")
            table[sample_id] = [key_intents[int(column)] for column in top[position]]
        neighbour_intents[query_name] = table

    # MF-7b's own anchor: gold intent among the intents of the top-5 NEIGHBOURS
    # (not the top-5 distinct intents), NEW500.
    for query_name, expected in NEIGHBOUR_RECALL_ANCHORS.items():
        hits = sum(
            1
            for row in rows
            if row["in_new500"]
            and row["gold_intent"] in neighbour_intents[query_name][str(row["sample_id"])][:5]
        )
        got = round(100.0 * hits / sum(1 for row in rows if row["in_new500"]), 2)
        if abs(got - expected) > 1e-9:
            raise SystemExit(
                f"IDENTITY ANCHOR FAILED: MF-7b neighbour recall@5 for {query_name!r} on "
                f"NEW500 is {got} against the published {expected}"
            )

    ks = (3, 5, 8)

    def candidate_table(subset: Sequence[Mapping[str, object]]) -> dict[str, object]:
        table: dict[str, object] = {"n": len(subset)}
        if not subset:
            return table
        # (a) does not exist -- reported, never computed.
        table["comparator_top_k_logprobs"] = None
        sizes = []
        source_b: dict[str, int] = {f"recall_at_{k}": 0 for k in ks}
        source_b["recall_at_full_list"] = 0
        for row in subset:
            scenario = row["predicted_scenario"]
            candidates = scenario_candidates.get(str(scenario), ())
            sizes.append(len(candidates))
            for k in ks:
                if recall_at(candidates, str(row["gold_intent"]), k):
                    source_b[f"recall_at_{k}"] += 1
            if str(row["gold_intent"]) in candidates:
                source_b["recall_at_full_list"] += 1
        table["predicted_scenario_legal_intents"] = {
            key: round(100.0 * value / len(subset), 2) for key, value in source_b.items()
        } | {"mean_candidate_list_size": round(sum(sizes) / len(sizes), 2)}

        for query_name, per_row in neighbour_intents.items():
            distinct: dict[str, int] = {f"recall_at_{k}": 0 for k in ks}
            raw: dict[str, int] = {f"neighbours_at_{k}": 0 for k in ks}
            union: dict[str, int] = {"recall_at_8_union_with_scenario_top_3": 0}
            for row in subset:
                ranked = per_row[str(row["sample_id"])]
                gold = str(row["gold_intent"])
                candidates = ordered_candidates([(intent, 0.0) for intent in ranked])
                for k in ks:
                    if recall_at(candidates, gold, k):
                        distinct[f"recall_at_{k}"] += 1
                    if gold in ranked[:k]:
                        raw[f"neighbours_at_{k}"] += 1
                merged = list(scenario_candidates.get(str(row["predicted_scenario"]), ())[:3])
                for intent in candidates:
                    if intent not in merged:
                        merged.append(intent)
                    if len(merged) >= 8:
                        break
                if gold in merged[:8]:
                    union["recall_at_8_union_with_scenario_top_3"] += 1
            table[f"nemotron_{query_name}_neighbours"] = {
                key: round(100.0 * value / len(subset), 2)
                for key, value in (distinct | raw | union).items()
            }
        return table

    result: dict[str, object] = {
        "schema": "saea-mf8-comparator-failure-v1",
        "row_id": ROW_ID,
        "lock_path": str(lock_path),
        "comparator": {
            "run_id": "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1",
            "attempt_id": "attempt-20260905T060424Z-2c5596",
            "scorer_id": "slurp-slu-official-projected-v2",
            "outputs": str(outputs_path),
            "intent_pct_measured": measured,
            "intent_pct_published": COMPARATOR_INTENT_ANCHORS,
            "identity_anchors_passed": True,
        },
        "candidate_source_a_comparator_top_k": {
            "available": logprobs_present,
            "evidence": (
                "the sealed outputs JSONL carries text and three sha256 fields per row and no "
                "logprobs object; the trace carries the request payload only. The flight never "
                "set decoding_params.logprobs, so no top-k distribution was ever stored."
            ),
        },
        "errors": {
            "n": len(errors),
            "within_scenario_action_confusion": within_scenario,
            "within_scenario_share_pct": round(100.0 * within_scenario / len(errors), 2),
            "cross_scenario": len(errors) - within_scenario,
            "cross_scenario_share_pct": round(
                100.0 * (len(errors) - within_scenario) / len(errors), 2
            ),
            "no_label_rows": no_label,
            "unparsed_rows": unparsed,
        },
        "error_mass_by_gold_scenario": dict(sorted(by_scenario.items())),
        "top_confusions": [
            {"gold": gold, "predicted": predicted, "rows": count}
            for (gold, predicted), count in confusion.most_common(30)
        ],
        "distinct_confusion_pairs": len(confusion),
        "exemplar_reach_on_errors": {
            "at_least": at_least_counts(
                [int(row["same_speaker_same_intent_recordings"]) for row in errors],
                (1, 3, 5, 8, 10),
            ),
            "quantiles": quantiles(
                [int(row["same_speaker_same_intent_recordings"]) for row in errors]
            ),
            "note": (
                "availability of the GOLD intent's same-speaker TRAIN exemplars on rows the "
                "comparator gets wrong -- the reachable share for dimension 2. Counted on DEV "
                "gold, an audit statistic only."
            ),
        },
        "candidate_recall": {
            "all_rows": candidate_table(rows),
            "error_rows": candidate_table(errors),
            "error_rows_new500": candidate_table(
                [row for row in errors if row["in_new500"]]
            ),
        },
        "neighbour_depth": args.neighbour_depth,
        "rows": rows,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "comparator-failure.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = dict(result)
    summary.pop("rows")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# Question 3 -- multi-audio prompt feasibility and its token cost.
# ---------------------------------------------------------------------------

#: Qwen3-Omni audio encoder rate, from the pinned llama.cpp source itself:
#: ``tools/mtmd/clip.cpp`` PROJECTOR_TYPE_QWEN3A -- "chunk_size=100 frames ->
#: 3x stride-2 conv2d -> 13 tokens per chunk", i.e. 13 tokens per 100 mel
#: frames = 13 tokens per second, allocated in whole one-second blocks.
AUDIO_TOKENS_PER_CHUNK = 13
AUDIO_CHUNK_SECONDS = 1.0

#: `configs/model/q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64.json`
SLURP_PACKET_CONTEXT = 65536
SLURP_PACKET_SLOTS = 8


def audio_prompt_tokens(seconds: float) -> int:
    """Prompt tokens one clip costs through the Qwen3-Omni audio encoder.

    The encoder emits :data:`AUDIO_TOKENS_PER_CHUNK` tokens per whole
    100-mel-frame chunk and the mel is padded up to a whole chunk, so a clip
    is charged by the CEILING of its second count -- the same arithmetic the
    Earnings-21 tail probe measured on the wire (2.0 s of appended silence
    cost exactly 26 tokens per window, 1,593 windows, no residue).
    """

    if seconds < 0:
        raise ValueError("audio seconds must be non-negative")
    import math

    chunks = math.ceil(seconds / AUDIO_CHUNK_SECONDS)
    return int(chunks * AUDIO_TOKENS_PER_CHUNK)


def _measure_seconds(paths: Sequence[Path], workers: int = 16) -> tuple[float, ...]:
    """Container-header durations only -- no audio sample is decoded."""

    import soundfile
    from concurrent.futures import ThreadPoolExecutor

    def probe(path: Path) -> float:
        info = soundfile.info(str(path))
        return float(info.frames) / float(info.samplerate)

    if not paths:
        return ()
    with ThreadPoolExecutor(max_workers=min(workers, len(paths))) as pool:
        return tuple(pool.map(probe, paths))


def command_feasibility(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.data.slurp import (
        _governed_roots,
        _slurp_speaker_index,
        load_slurp_split,
        load_slurp_train_material,
    )

    lock, root, lock_path = resolve_lock_and_root()
    audio_root_relpath, _audio_root, metadata_dir = _governed_roots(lock, root)
    speakers_by_file = _slurp_speaker_index(metadata_dir)
    train = load_slurp_train_material(lock, root)
    devel = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)

    # The exemplar pool that a same-speaker cell would actually draw from:
    # every TRAIN recording whose (speaker, intent) matches some DEV-1000 row's
    # (speaker, gold intent).
    wanted = {
        (speakers_by_file[recording_filename(sample_id)], devel[sample_id].intent)
        for sample_id in roster
    }
    pool_paths: list[Path] = []
    pool_sentence_chars: list[int] = []
    for utterance in train:
        intent = f"{utterance.scenario}_{utterance.action}"
        for recording in utterance.recordings:
            if (recording.speaker_id, intent) in wanted:
                pool_paths.append(root / recording.media_relpath)
                pool_sentence_chars.append(len(utterance.sentence))
    pool_seconds = _measure_seconds(pool_paths, workers=args.workers)

    query_seconds = [devel[sample_id].audio_seconds for sample_id in roster]
    query_tokens = [audio_prompt_tokens(value) for value in query_seconds]
    exemplar_tokens = [audio_prompt_tokens(value) for value in pool_seconds]
    mean_exemplar_tokens = sum(exemplar_tokens) / len(exemplar_tokens)

    # The sealed comparator's own realized prompt volume, from its run manifest.
    comparator_prompt_tokens_total = 2190161
    comparator_calls = 1000
    comparator_prompt_mean = comparator_prompt_tokens_total / comparator_calls
    fixed_text_tokens = comparator_prompt_mean - (sum(query_tokens) / len(query_tokens))

    slot_tokens = SLURP_PACKET_CONTEXT // SLURP_PACKET_SLOTS
    budget: dict[str, object] = {}
    for k in (3, 5, 8):
        added_audio = k * mean_exemplar_tokens
        worst_added_audio = k * max(exemplar_tokens)
        budget[f"k={k}"] = {
            "added_audio_tokens_mean": round(added_audio, 1),
            "added_audio_tokens_worst_case": worst_added_audio,
            "prompt_tokens_mean": round(comparator_prompt_mean + added_audio, 1),
            "prompt_tokens_worst_case": round(
                fixed_text_tokens + max(query_tokens) + worst_added_audio, 1
            ),
            "slot_headroom_factor_mean": round(
                slot_tokens / (comparator_prompt_mean + added_audio), 2
            ),
            "fits_slot_at_np8": bool(
                fixed_text_tokens + max(query_tokens) + worst_added_audio < slot_tokens
            ),
        }

    result: dict[str, object] = {
        "schema": "saea-mf8-multi-audio-feasibility-v1",
        "row_id": ROW_ID,
        "lock_path": str(lock_path),
        "audio_root_relpath": audio_root_relpath,
        "boundary": (
            "container headers only; no audio sample is decoded, no server is started and no "
            "tokenizer is loaded. Text volume is reported in CHARACTERS, never estimated tokens."
        ),
        "encoder_rate": {
            "tokens_per_chunk": AUDIO_TOKENS_PER_CHUNK,
            "chunk_seconds": AUDIO_CHUNK_SECONDS,
            "source": "tools/mtmd/clip.cpp PROJECTOR_TYPE_QWEN3A (llama.cpp-featcache 04ccc72a)",
        },
        "geometry": {
            "context": SLURP_PACKET_CONTEXT,
            "slots": SLURP_PACKET_SLOTS,
            "tokens_per_slot": slot_tokens,
            "config": (
                "configs/model/"
                "q4km-mmproj-free-speech-native-np8-base-speech-query-prefix-max64.json"
            ),
        },
        "dev1000_query": {
            "rows": len(query_seconds),
            "seconds": quantiles(query_seconds),
            "seconds_total": round(sum(query_seconds), 4),
            "audio_tokens": quantiles(query_tokens),
            "audio_tokens_total": sum(query_tokens),
        },
        "same_speaker_exemplar_pool": {
            "recordings": len(pool_seconds),
            "distinct_speaker_intent_pairs": len(wanted),
            "seconds": quantiles(pool_seconds),
            "seconds_total": round(sum(pool_seconds), 4),
            "audio_tokens": quantiles(exemplar_tokens),
            "sentence_characters": quantiles(pool_sentence_chars),
        },
        "comparator_realized": {
            "run_id": "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1",
            "calls": comparator_calls,
            "prompt_tokens_total": comparator_prompt_tokens_total,
            "prompt_tokens_mean": round(comparator_prompt_mean, 2),
            "completion_tokens_total": 26495,
            "fixed_text_tokens_mean": round(fixed_text_tokens, 1),
            "wall_seconds": 225.5,
            "contacts_per_second": 4.43,
            "gpu_hours": 0.105,
            "source": "the sealed run manifest and its exposure-ledger row",
        },
        "budget": budget,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "multi-audio-feasibility.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# The deterministic legality judge -- an agent-SYSTEM component, not a prompt.
# ---------------------------------------------------------------------------


def judge_verdict(
    scenario: str | None,
    action: str | None,
    parsed: bool,
    legal_scenarios: frozenset[str],
    legal_pairs: frozenset[tuple[str, str]],
) -> str | None:
    """Which deterministic legality tier flags this RAW response, if any.

    ``None`` means the judge passes the row through untouched. The judge reads
    the model's own output and the TRAIN-mined closed list, and nothing else --
    no gold, no score, no second model.
    """

    if not parsed:
        return "unparsed"
    if scenario is None or action is None:
        return "no-label"
    if (scenario, action) in legal_pairs:
        return None
    if scenario not in legal_scenarios:
        return "scenario-not-legal"
    return "action-illegal-for-scenario"


def command_judge(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
        load_legal_intent_inventory,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        parse_slu_response,
        project_slu_label_v2,
    )

    lock, root, lock_path = resolve_lock_and_root()
    inventory = load_legal_intent_inventory(lock, root)
    legal_scenarios = frozenset(inventory.scenarios)
    legal_pairs = inventory.pairs

    devel = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)
    texts = read_sealed_outputs(root / SEALED_COMPARATOR_OUTPUTS)

    gold_outside_closed_list = sorted(
        {devel[sample_id].intent for sample_id in roster}
        - {f"{scenario}_{action}" for scenario, action in legal_pairs}
    )

    tiers: Counter[str] = Counter()
    flagged_and_raw_wrong = 0
    flagged_and_raw_right = 0
    raw_wrong = 0
    projected_wrong = 0
    flagged_still_wrong_after_projection = 0
    for sample_id in roster:
        record = devel[sample_id]
        scenario, action, _entities, parsed = parse_slu_response(texts[sample_id])
        raw_intent = (
            f"{scenario}_{action}" if parsed and scenario and action else None
        )
        projected = project_slu_label_v2(scenario, action, inventory, parsed=parsed)
        verdict = judge_verdict(scenario, action, parsed, legal_scenarios, legal_pairs)
        raw_is_wrong = raw_intent != record.intent
        raw_wrong += int(raw_is_wrong)
        projected_wrong += int(projected.projected_intent != record.intent)
        if verdict is not None:
            tiers[verdict] += 1
            flagged_and_raw_wrong += int(raw_is_wrong)
            flagged_and_raw_right += int(not raw_is_wrong)
            flagged_still_wrong_after_projection += int(
                projected.projected_intent != record.intent
            )

    flagged = sum(tiers.values())
    result = {
        "schema": "saea-mf8-legality-judge-v1",
        "row_id": ROW_ID,
        "lock_path": str(lock_path),
        "judge": (
            "deterministic: parse the response, then compare its (scenario, action) against the "
            "60 TRAIN-mined legal pairs. Reads no gold, calls no model, and is the cheapest "
            "component an agent SYSTEM can put in front of a core revise."
        ),
        "rows": len(roster),
        "gold_intents_outside_the_closed_list": gold_outside_closed_list,
        "flagged": flagged,
        "flagged_share_of_rows_pct": round(100.0 * flagged / len(roster), 2),
        "tiers": dict(sorted(tiers.items())),
        "raw_errors": raw_wrong,
        "projected_errors": projected_wrong,
        "recall_over_raw_errors_pct": round(100.0 * flagged_and_raw_wrong / raw_wrong, 2),
        "precision_pct": round(100.0 * flagged_and_raw_wrong / flagged, 2),
        "false_flags_on_correct_rows": flagged_and_raw_right,
        "flagged_rows_still_wrong_after_projection_v2": flagged_still_wrong_after_projection,
        "reading": (
            "every SLURP gold intent is one of the 60 legal pairs, so a row the judge flags "
            "CANNOT be correct: precision is 100 % by construction and the false-flag count is "
            "structurally zero. Its recall is the ceiling of what deterministic legality can "
            "intercept before any core contact is spent."
        ),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "legality-judge.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# Question 4 -- what "state" a home assistant legitimately holds beforehand.
# ---------------------------------------------------------------------------

#: Entity types that name a THING the assistant would already have on record --
#: a device, a place, a medium, an app, a person, a list. Chosen by what the
#: type NAMES, before any count was looked at, and reported as a partition of
#: the 55 TRAIN types rather than as a selection.
STATE_BEARING_TYPE_HINTS = (
    "device_type",
    "house_place",
    "player_setting",
    "media_type",
    "app_name",
    "playlist_name",
    "list_name",
    "person",
    "personal_info",
    "email_address",
    "podcast_name",
    "artist_name",
    "song_name",
    "radio_name",
    "audiobook_name",
    "game_name",
    "business_name",
    "business_type",
    "transport_type",
    "transport_name",
    "transport_agency",
    "news_topic",
    "food_type",
    "drink_type",
    "coffee_type",
    "music_genre",
    "joke_type",
    "movie_name",
    "movie_type",
    "sport_type",
    "currency_name",
    "place_name",
    "house_type",
    "cooking_type",
    "alarm_type",
    "weather_descriptor",
)


def jsonl_field_names(path: Path, limit: int | None = None) -> dict[str, int]:
    """Top-level KEY NAMES and their row counts -- never a value.

    This is how the audit establishes that SLURP has no prior-turn/session/
    dialogue field without reading one word of any utterance.
    """

    counts: Counter[str] = Counter()
    rows = 0
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows += 1
            record = json.loads(stripped)
            if not isinstance(record, Mapping):
                raise ValueError(f"{path}: a row is not a JSON object")
            counts.update(record.keys())
            if limit is not None and rows >= limit:
                break
    return {"__rows__": rows} | dict(sorted(counts.items()))


def command_state(args: argparse.Namespace) -> int:
    from speech_aware_evidence_acquisition.data.slurp import (
        _governed_roots,
        load_slurp_intent_slot_schema,
        load_slurp_ontology,
        load_slurp_train_material,
    )

    lock, root, lock_path = resolve_lock_and_root()
    _, _, metadata_dir = _governed_roots(lock, root)

    field_names = {
        split: jsonl_field_names(metadata_dir / f"{split}.jsonl")
        for split in ("train", "devel")
    }
    speaker_metadata = json.loads(
        (metadata_dir / "metadata.json").read_text(encoding="utf-8")
    )
    speaker_entry_fields: Counter[str] = Counter()
    recording_fields: Counter[str] = Counter()
    for entry in speaker_metadata.values():
        if not isinstance(entry, Mapping):
            continue
        speaker_entry_fields.update(entry.keys())
        recordings = entry.get("recordings")
        if isinstance(recordings, Mapping):
            for recording in recordings.values():
                if isinstance(recording, Mapping):
                    recording_fields.update(recording.keys())

    ontology = load_slurp_ontology(lock, root)
    schema = load_slurp_intent_slot_schema(lock, root)
    train = load_slurp_train_material(lock, root)

    per_scenario: dict[str, dict[str, object]] = {}
    fillers_by_type: dict[str, set[str]] = defaultdict(set)
    for utterance in train:
        bucket = per_scenario.setdefault(
            utterance.scenario,
            {"utterances": 0, "types": defaultdict(set)},
        )
        bucket["utterances"] = int(bucket["utterances"]) + 1
        for entity in utterance.entities:
            bucket["types"][entity.type].add(entity.filler)  # type: ignore[index]
            fillers_by_type[entity.type].add(entity.filler)

    scenario_inventory = {
        scenario: {
            "train_utterances": data["utterances"],
            "legal_actions": len(ontology.actions_by_scenario.get(scenario, ())),
            "entity_types": len(data["types"]),  # type: ignore[arg-type]
            "distinct_fillers": sum(
                len(values) for values in data["types"].values()  # type: ignore[union-attr]
            ),
            "largest_types": [
                {"entity_type": name, "distinct_fillers": len(values)}
                for name, values in sorted(
                    data["types"].items(),  # type: ignore[union-attr]
                    key=lambda item: (-len(item[1]), item[0]),
                )[:5]
            ],
        }
        for scenario, data in sorted(per_scenario.items())
    }

    state_bearing = {
        name: len(values)
        for name, values in sorted(fillers_by_type.items())
        if name in STATE_BEARING_TYPE_HINTS
    }
    non_state = {
        name: len(values)
        for name, values in sorted(fillers_by_type.items())
        if name not in STATE_BEARING_TYPE_HINTS
    }

    result = {
        "schema": "saea-mf8-state-inventory-v1",
        "row_id": ROW_ID,
        "lock_path": str(lock_path),
        "boundary": (
            "field NAMES and TRAIN gold entity values only. No devel sentence text is read; the "
            "devel column is a key-name census, never a value."
        ),
        "prior_turn_context": {
            "record_field_names": field_names,
            "speaker_metadata_entry_fields": dict(sorted(speaker_entry_fields.items())),
            "speaker_metadata_recording_fields": dict(sorted(recording_fields.items())),
            "verdict": (
                "SLURP carries NO dialogue, session, turn-index, history or prior-turn field on "
                "either split, and no timestamp beyond the recording id. Every utterance is a "
                "cold single turn. 'Prior-turn context' as state DOES NOT EXIST on this carrier "
                "and cannot be manufactured without inventing it."
            ),
        },
        "closed_label_space": {
            "scenarios": len(ontology.actions_by_scenario),
            "legal_pairs": len(schema.intents),
            "entity_types": len(fillers_by_type),
            "already_rendered_by": [
                "data.slurp.render_slurp_closed_label_inventory",
                "data.slurp.render_slurp_label_inventory",
            ],
            "already_in_the_comparator_prompt": True,
        },
        "device_and_entity_inventory": {
            "distinct_fillers_total": sum(len(values) for values in fillers_by_type.values()),
            "state_bearing_types": state_bearing,
            "state_bearing_type_count": len(state_bearing),
            "state_bearing_filler_count": sum(state_bearing.values()),
            "other_types": non_state,
            "other_type_count": len(non_state),
            "note": (
                "the type partition is by what the type NAMES (a device, a place, a medium, a "
                "person, a named work), fixed before any count was read; it is reported as a "
                "partition, not a selection."
            ),
        },
        "per_scenario": scenario_inventory,
        "existing_knowledge_receipts": {
            "docs/receipts/knowledge/slurp-intent-slot-schema-v1.json": (
                "per-intent entity types with counts, shares and 5 example fillers -- the state "
                "fill KC-S1b already flies (slurp-intent-slot-schema-for-state)"
            ),
            "docs/receipts/knowledge/slurp-kb-size-full.json": (
                "the full 11,514-utterance content datastore and its coverage report"
            ),
            "docs/receipts/knowledge/slurp-kb-size-full-content-slot-fillers.json": (
                "the slot-fillers KB view KU-S3 consumes"
            ),
            "docs/receipts/knowledge/slurp-kb-size-full-label-prior-speaker.json": (
                "label prior plus the SPEAKER histogram -- the only speaker-aware knowledge "
                "artifact this study already holds"
            ),
            "docs/receipts/knowledge/slurp-kb-size-full-embeddings.json": (
                "the embedded content facets"
            ),
            "docs/receipts/knowledge/slurp-evo-decontamination-v1.json": (
                "the DEV-1000 6-gram digest gate every candidate filler is validated against"
            ),
            "$SPEECHRL_DATA_DIR/vectors/slurp-kus3/": (
                "sealed Nemotron key and query vectors (receipt "
                "docs/checks/.../2026-09-07-slurp-kus3-vectors/)"
            ),
        },
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "state-inventory.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# Question 5 -- the priced (NOT preregistered) KU-S4 family.
# ---------------------------------------------------------------------------


def compose_candidates(
    scenario_candidates: Sequence[str],
    neighbour_candidates: Sequence[str],
    k: int,
    *,
    scenario_lead: int,
) -> tuple[str, ...]:
    """The gold-free candidate set an arm would actually offer.

    ``scenario_lead`` entries come from the PREDICTED scenario's legal list
    (TRAIN prior first); the rest are filled from the speech-vector neighbours
    in cosine rank order, skipping repeats. Both halves are built without the
    gold label, which is the whole point of the design.
    """

    if k <= 0:
        raise ValueError("candidate count must be positive")
    if scenario_lead < 0:
        raise ValueError("scenario lead must be non-negative")
    chosen: list[str] = []
    for intent in scenario_candidates[: min(scenario_lead, k)]:
        if intent not in chosen:
            chosen.append(intent)
    for intent in neighbour_candidates:
        if len(chosen) >= k:
            break
        if intent not in chosen:
            chosen.append(intent)
    return tuple(chosen[:k])


def command_family(args: argparse.Namespace) -> int:
    import numpy as np

    from speech_aware_evidence_acquisition.data.slurp import (
        _governed_roots,
        _slurp_speaker_index,
        load_slurp_split,
        load_slurp_train_material,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
        load_legal_intent_inventory,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        parse_slu_response,
        project_slu_label_v2,
    )

    lock, root, lock_path = resolve_lock_and_root()
    _, _, metadata_dir = _governed_roots(lock, root)
    speakers_by_file = _slurp_speaker_index(metadata_dir)
    inventory = load_legal_intent_inventory(lock, root)
    train = load_slurp_train_material(lock, root)

    intent_by_utterance: dict[str, str] = {}
    speaker_intent_recordings: dict[tuple[str, str], int] = defaultdict(int)
    intent_recordings: dict[str, int] = defaultdict(int)
    for utterance in train:
        intent = f"{utterance.scenario}_{utterance.action}"
        intent_by_utterance[utterance.utterance_id] = intent
        for recording in utterance.recordings:
            speaker_intent_recordings[(recording.speaker_id, intent)] += 1
            intent_recordings[intent] += 1

    devel = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    roster = roster_sample_ids(REPO_ROOT / DEV1000_CONFIG)
    texts = read_sealed_outputs(root / SEALED_COMPARATOR_OUTPUTS)
    new500_receipt = json.loads((REPO_ROOT / NEW500_RECEIPT).read_text(encoding="utf-8"))
    new500 = {str(item["id"]) for item in new500_receipt["items"]}

    scenario_candidates: dict[str, tuple[str, ...]] = {}
    for scenario in inventory.scenarios:
        ranked = sorted(
            inventory.actions_by_scenario[scenario],
            key=lambda candidate: (-inventory.prior(scenario, candidate), candidate),
        )
        scenario_candidates[scenario] = tuple(f"{scenario}_{action}" for action in ranked)

    vector_dir = root / SEALED_VECTOR_DIR
    key_ids, key_matrix = _load_vectors(vector_dir / "facet-vectors.jsonl")
    key_intents = [intent_by_utterance[key_id.rsplit(":", 1)[-1]] for key_id in key_ids]
    query_ids, query_matrix = _load_vectors(vector_dir / "query-vectors-speech.jsonl")
    position_of = {identity: index for index, identity in enumerate(query_ids)}
    top = np.argsort(-(query_matrix @ key_matrix.T), axis=1)[:, :50]

    designs = {
        "k3-neighbours-only": {"k": 3, "scenario_lead": 0},
        "k5-neighbours-only": {"k": 5, "scenario_lead": 0},
        "k8-scenario3-plus-neighbours": {"k": 8, "scenario_lead": 3},
    }
    measured: dict[str, dict[str, object]] = {}
    for name, spec in designs.items():
        k = int(spec["k"])
        lead = int(spec["scenario_lead"])
        gold_in_set = 0
        gold_in_set_errors = 0
        covered_fractions: list[float] = []
        fully_covered = 0
        fully_covered_new500 = 0
        gold_candidate_has_same_speaker_exemplar = 0
        gold_candidate_has_any_exemplar = 0
        errors = 0
        for sample_id in roster:
            record = devel[sample_id]
            scenario, action, _entities, parsed = parse_slu_response(texts[sample_id])
            projection = project_slu_label_v2(scenario, action, inventory, parsed=parsed)
            is_error = projection.projected_intent != record.intent
            errors += int(is_error)
            neighbours = ordered_candidates(
                [
                    (key_intents[int(column)], 0.0)
                    for column in top[position_of[sample_id]]
                ]
            )
            candidates = compose_candidates(
                scenario_candidates.get(str(projection.scenario), ()),
                neighbours,
                k,
                scenario_lead=lead,
            )
            speaker = speakers_by_file[recording_filename(sample_id)]
            covered = sum(
                1
                for intent in candidates
                if speaker_intent_recordings.get((speaker, intent), 0) > 0
            )
            covered_fractions.append(covered / len(candidates))
            is_fully_covered = covered == len(candidates)
            fully_covered += int(is_fully_covered)
            fully_covered_new500 += int(is_fully_covered and sample_id in new500)
            if record.intent in candidates:
                gold_in_set += 1
                gold_in_set_errors += int(is_error)
                gold_candidate_has_same_speaker_exemplar += int(
                    speaker_intent_recordings.get((speaker, record.intent), 0) > 0
                )
                gold_candidate_has_any_exemplar += int(
                    intent_recordings.get(record.intent, 0) > 0
                )
        measured[name] = {
            "k": k,
            "scenario_lead": lead,
            "narrowing_ratio_pct": round(100.0 * k / 60, 2),
            "gold_in_candidate_set_pct": round(100.0 * gold_in_set / len(roster), 2),
            "gold_in_candidate_set_on_errors_pct": round(
                100.0 * gold_in_set_errors / errors, 2
            ),
            "same_speaker_exemplar_coverage_of_candidates_pct": round(
                100.0 * sum(covered_fractions) / len(covered_fractions), 2
            ),
            "rows_with_every_candidate_covered_by_own_speaker": fully_covered,
            "rows_with_every_candidate_covered_by_own_speaker_new500": fully_covered_new500,
            "gold_candidate_covered_by_own_speaker": gold_candidate_has_same_speaker_exemplar,
            "gold_candidate_covered_by_any_speaker": gold_candidate_has_any_exemplar,
        }

    result = {
        "schema": "saea-mf8-cell-family-price-v1",
        "row_id": ROW_ID,
        "lock_path": str(lock_path),
        "status": "PRICED, NOT PREREGISTERED. No cell is admitted, promoted or registered here.",
        "rarest_intent_train_recordings": min(intent_recordings.values()),
        "designs": measured,
        "boundary": (
            "candidate sets are built from the arm's OWN sealed prediction and the pinned speech "
            "vectors; no gold label enters their construction. Gold is used only to report "
            "whether the set contains it."
        ),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cell-family-price.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MF-8 speech-to-knowledge audit (model-free)")
    parser.add_argument(
        "--out-dir",
        default=str(
            REPO_ROOT / "docs" / "checks" / "speech-aware-evidence-acquisition" / RECEIPT_DIRNAME
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("speakers", help="question 1: SLURP speaker structure")
    comparator = subparsers.add_parser(
        "comparator", help="question 2: comparator failure and candidate reach"
    )
    comparator.add_argument("--neighbour-depth", type=int, default=50)
    feasibility = subparsers.add_parser(
        "feasibility", help="question 3: multi-audio prompt cost and geometry fit"
    )
    feasibility.add_argument("--workers", type=int, default=16)
    subparsers.add_parser(
        "judge", help="the deterministic legality judge's reach and precision"
    )
    subparsers.add_parser("state", help="question 4: the state-knowledge inventory")
    subparsers.add_parser("family", help="question 5: price the KU-S4 family (never registers it)")
    args = parser.parse_args(argv)
    if args.command == "speakers":
        return command_speakers(args)
    if args.command == "comparator":
        return command_comparator(args)
    if args.command == "feasibility":
        return command_feasibility(args)
    if args.command == "judge":
        return command_judge(args)
    if args.command == "state":
        return command_state(args)
    if args.command == "family":
        return command_family(args)
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
