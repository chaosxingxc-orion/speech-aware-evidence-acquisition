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
    args = parser.parse_args(argv)
    if args.command == "speakers":
        return command_speakers(args)
    if args.command == "comparator":
        return command_comparator(args)
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
