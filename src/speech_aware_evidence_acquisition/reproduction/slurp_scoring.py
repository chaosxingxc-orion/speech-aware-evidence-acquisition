"""Deterministic SLU scoring for the SLURP carrier (B0 rails).

Reimplements the SLURP repository's own official evaluation metrics (pinned
commit 8eb16545762be97ace75334109d73824217311f1,
``scripts/evaluation/metrics/metrics.py`` / ``distance.py`` / ``util.py``,
read directly from the umbrella-governed local clone under
``SPEECHRL_DATA_DIR/repos/slurp`` -- no network fetch, that repo's own git
history is the verification) at PER-SAMPLE granularity: this study's
``TaskAdapter.score(sample, response)`` scores one response at a time
(``rails.task_adapter`` module docstring), while the official
``evaluate.py`` accumulates TP/FP/FN across an entire corpus before ever
computing precision/recall/F1. :func:`score_slu` below reproduces exactly
ONE iteration of that corpus loop's TP/FP/FN contribution for one
gold/predicted example pair; summing a split's ``SluScore.slu_f1_tp`` /
``_fp`` / ``_fn`` (and the ``slot_f1_exact`` / ``slu_f1_word`` /
``slu_f1_char`` analogs) across every sample reproduces the official
corpus-level counts exactly -- MICRO averaging only (the official script's
own default ``--average micro``; macro (per-entity-type) averaging would
need per-type TP/FP/FN, not carried at this per-sample granularity, and is
out of scope for this rails-freeze mission).

Two metric families, named so neither is ever mistaken for the other (this
mission's own never-mislabel-a-metric instruction):

- ``slot_f1_exact``: mirrors the official ``SpanFMeasure`` class exactly --
  an entity is a true positive only on an EXACT ``{type, filler}`` match.
  This is NOT the paper's headline "SLU-F1" metric (the official script
  reports it under the plain "entities" label, distinct from its own
  "SLU F1" row) -- named ``slot_f1_exact`` throughout this module, i.e. the
  "slot-F1-exact (not official SLU-F1)" variant this mission names.
- ``slu_f1``: the official headline metric -- word-distance (WER, via
  ``jiwer.wer``; deferred import, this study's own client guide already
  names ``jiwer`` as an expected shared-venv library) and char-distance
  (normalized Levenshtein, hand-rolled in :func:`_char_distance` -- no
  dependency this study does not already carry: the official script uses
  ``textdistance``, which this shared venv does not have) span-distance F1s,
  combined exactly as the official ``SLUF1`` class combines them (TP/FP/FN
  summed across both distances).

Intent: the task brief's "intent accuracy (scenario_action exact)" is a
per-sample 0/1 match indicator (mean over samples = accuracy) -- simpler
than the official script's own per-label ``intent_f1`` (a multi-class
Precision/Recall/F1 over the raw ``"{scenario}_{action}"`` string), which
this module does not reproduce (out of the brief's scope).

Gold/predicted asymmetry (byte-for-byte fidelity to the official script,
NOT a bug): the official ``release2prediction`` lowercases gold filler text
at load time (``" ".join([tokens[i]["surface"].lower() for i in
entity["span"]])`` -- reproduced in ``data.slurp._entity_filler``) but never
lowercases predicted filler text (a prediction file's own entities are
compared as-is). :func:`parse_slu_response` below deliberately does NOT
lowercase predicted fillers either, matching the official protocol exactly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

SLURP_SCORER_VERSION = "slurp-scorer-v1"

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class SlotEntity:
    """One SLU entity slot: ``type`` is the governed jsonl's own entity-type
    vocabulary term (e.g. ``"currency_name"``); ``filler`` is its value
    text. Shared by gold (``data.slurp.SlurpRecord.entities``) and predicted
    (:func:`parse_slu_response`'s return) so both sides compare through the
    exact same shape."""

    type: str
    filler: str


def _prf(true_positives: float, false_positives: float, false_negatives: float) -> tuple[float, float, float]:
    """Exactly ``metrics.compute_metrics`` from the official SLURP eval
    script (module docstring)."""

    if true_positives == 0.0 and false_positives == 0.0:
        precision = 0.0
    else:
        precision = true_positives / (true_positives + false_positives)
    if true_positives == 0.0 and false_negatives == 0.0:
        recall = 0.0
    else:
        recall = true_positives / (true_positives + false_negatives)
    if precision == 0.0 and recall == 0.0:
        f1_measure = 0.0
    else:
        f1_measure = 2.0 * precision * recall / (precision + recall)
    return precision, recall, f1_measure


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i] + [0] * len(b)
        for j, char_b in enumerate(b, start=1):
            cost = 0 if char_a == char_b else 1
            current_row[j] = min(
                previous_row[j] + 1,  # deletion
                current_row[j - 1] + 1,  # insertion
                previous_row[j - 1] + cost,  # substitution
            )
        previous_row = current_row
    return previous_row[-1]


def _char_distance(truth: str, hypothesis: str) -> float:
    """Normalized Levenshtein distance in [0, 1] -- the official script's
    ``CharDistance`` (``textdistance.algorithms.edit_based.levenshtein.
    normalized_distance``), hand-rolled here (module docstring):
    ``edit_distance / max(len(truth), len(hypothesis))``, 0.0 when both
    strings are empty."""

    if not truth and not hypothesis:
        return 0.0
    return _levenshtein(truth, hypothesis) / max(len(truth), len(hypothesis))


def _word_distance(truth: str, hypothesis: str) -> float:
    """Word Error Rate -- the official script's ``WordDistance``
    (``jiwer.wer``, deferred import: repo convention, module docstring).
    Unclipped (can exceed 1.0 on heavy insertion), matching the official
    script exactly -- it is never clipped there either."""

    import jiwer  # deferred: heavy import stays function-local (repo convention)

    return float(jiwer.wer(truth, hypothesis))


def _lowest_distance(
    entity: SlotEntity,
    gold_types: Sequence[str],
    gold_fillers: Sequence[str],
    distance_fn: Callable[[str, str], float],
) -> tuple[int, float]:
    """Exactly the official ``SpanDistanceFMeasure._get_lowest_distance``:
    the index (within the CURRENT, not-yet-matched gold list) and distance
    of the closest same-type gold candidate."""

    index = 0
    lowest = float("inf")
    for candidate_index, gold_type in enumerate(gold_types):
        if gold_type == entity.type:
            distance = distance_fn(gold_fillers[candidate_index], entity.filler)
            if distance < lowest:
                index = candidate_index
                lowest = distance
    return index, lowest


def _distance_based_counts(
    gold: Sequence[SlotEntity],
    predicted: Sequence[SlotEntity],
    distance_fn: Callable[[str, str], float],
) -> tuple[float, float, float]:
    """One example's (TP, FP, FN) contribution to the official
    ``SpanDistanceFMeasure``'s micro totals (module docstring) --
    ``distance_fn`` is :func:`_word_distance` or :func:`_char_distance`."""

    remaining_types = [entity.type for entity in gold]
    remaining_fillers = [entity.filler for entity in gold]
    true_positives = false_positives = false_negatives = 0.0
    for entity in predicted:
        if entity.type in remaining_types:
            index, distance = _lowest_distance(entity, remaining_types, remaining_fillers, distance_fn)
            true_positives += 1.0
            false_positives += distance
            false_negatives += distance
            del remaining_types[index]
            del remaining_fillers[index]
        else:
            false_positives += 1.0
    false_negatives += float(len(remaining_types))
    return true_positives, false_positives, false_negatives


def _exact_counts(gold: Sequence[SlotEntity], predicted: Sequence[SlotEntity]) -> tuple[float, float, float]:
    """One example's (TP, FP, FN) contribution to the official
    ``SpanFMeasure``'s micro totals -- exact ``{type, filler}`` match
    (module docstring's ``slot_f1_exact``)."""

    remaining = list(gold)
    true_positives = false_positives = 0.0
    for entity in predicted:
        if entity in remaining:
            true_positives += 1.0
            remaining.remove(entity)
        else:
            false_positives += 1.0
    false_negatives = float(len(remaining))
    return true_positives, false_positives, false_negatives


@dataclass(frozen=True)
class SluScore:
    """One sample's SLU scoring ingredients -- summable across a split to
    reproduce the official corpus-level micro metrics exactly (module
    docstring)."""

    scenario_action_exact: float
    scenario_exact: float
    action_exact: float
    slot_f1_exact_tp: float
    slot_f1_exact_fp: float
    slot_f1_exact_fn: float
    slu_f1_word_tp: float
    slu_f1_word_fp: float
    slu_f1_word_fn: float
    slu_f1_char_tp: float
    slu_f1_char_fp: float
    slu_f1_char_fn: float

    @property
    def slot_f1_exact(self) -> tuple[float, float, float]:
        return _prf(self.slot_f1_exact_tp, self.slot_f1_exact_fp, self.slot_f1_exact_fn)

    @property
    def slu_f1_word(self) -> tuple[float, float, float]:
        return _prf(self.slu_f1_word_tp, self.slu_f1_word_fp, self.slu_f1_word_fn)

    @property
    def slu_f1_char(self) -> tuple[float, float, float]:
        return _prf(self.slu_f1_char_tp, self.slu_f1_char_fp, self.slu_f1_char_fn)

    @property
    def slu_f1(self) -> tuple[float, float, float]:
        """The official combined metric -- ``SLUF1.__call__`` summing the
        word- and char-distance TP/FP/FN before computing P/R/F1."""

        return _prf(
            self.slu_f1_word_tp + self.slu_f1_char_tp,
            self.slu_f1_word_fp + self.slu_f1_char_fp,
            self.slu_f1_word_fn + self.slu_f1_char_fn,
        )

    def as_metrics_dict(self) -> dict[str, object]:
        slot_p, slot_r, slot_f1_measure = self.slot_f1_exact
        word_p, word_r, word_f1_measure = self.slu_f1_word
        char_p, char_r, char_f1_measure = self.slu_f1_char
        slu_p, slu_r, slu_f1_measure = self.slu_f1
        return {
            "scenario_action_exact": self.scenario_action_exact,
            "scenario_exact": self.scenario_exact,
            "action_exact": self.action_exact,
            # "slot-F1-exact (not official SLU-F1)" (module docstring):
            # exact {type, filler} dict match, mirrors the official script's
            # own plain "entities" row (SpanFMeasure), never the paper's
            # headline SLU-F1.
            "slot_f1_exact_tp": self.slot_f1_exact_tp,
            "slot_f1_exact_fp": self.slot_f1_exact_fp,
            "slot_f1_exact_fn": self.slot_f1_exact_fn,
            "slot_f1_exact_precision": slot_p,
            "slot_f1_exact_recall": slot_r,
            "slot_f1_exact_f1": slot_f1_measure,
            # official SLU-F1 ingredients (word-distance + char-distance,
            # micro-averaged) -- module docstring.
            "slu_f1_word_tp": self.slu_f1_word_tp,
            "slu_f1_word_fp": self.slu_f1_word_fp,
            "slu_f1_word_fn": self.slu_f1_word_fn,
            "slu_f1_word_f1": word_f1_measure,
            "slu_f1_char_tp": self.slu_f1_char_tp,
            "slu_f1_char_fp": self.slu_f1_char_fp,
            "slu_f1_char_fn": self.slu_f1_char_fn,
            "slu_f1_char_f1": char_f1_measure,
            "slu_f1_precision": slu_p,
            "slu_f1_recall": slu_r,
            "slu_f1_f1": slu_f1_measure,
        }


def score_slu(
    *,
    gold_scenario: str,
    gold_action: str,
    gold_entities: Sequence[SlotEntity],
    predicted_scenario: str | None,
    predicted_action: str | None,
    predicted_entities: Sequence[SlotEntity],
) -> SluScore:
    """One sample's full SLU scoring ingredients (module docstring)."""

    scenario_exact = 1.0 if predicted_scenario == gold_scenario else 0.0
    action_exact = 1.0 if predicted_action == gold_action else 0.0
    scenario_action_exact = 1.0 if (scenario_exact == 1.0 and action_exact == 1.0) else 0.0
    exact_tp, exact_fp, exact_fn = _exact_counts(gold_entities, predicted_entities)
    word_tp, word_fp, word_fn = _distance_based_counts(gold_entities, predicted_entities, _word_distance)
    char_tp, char_fp, char_fn = _distance_based_counts(gold_entities, predicted_entities, _char_distance)
    return SluScore(
        scenario_action_exact=scenario_action_exact,
        scenario_exact=scenario_exact,
        action_exact=action_exact,
        slot_f1_exact_tp=exact_tp,
        slot_f1_exact_fp=exact_fp,
        slot_f1_exact_fn=exact_fn,
        slu_f1_word_tp=word_tp,
        slu_f1_word_fp=word_fp,
        slu_f1_word_fn=word_fn,
        slu_f1_char_tp=char_tp,
        slu_f1_char_fp=char_fp,
        slu_f1_char_fn=char_fn,
    )


def parse_slu_response(text: str) -> tuple[str | None, str | None, list[SlotEntity], bool]:
    """Parse the model's response into ``(scenario, action, entities,
    parsed)`` -- fails closed to ``(None, None, [], False)``, mirroring
    ``reproduction.toolcall_scoring.parse_tool_calls_text``'s own
    fail-closed discipline. Expected shape mirrors the official SLURP
    prediction-file format exactly (``scripts/evaluation/util.py``'s own
    ``release2prediction`` output shape): a JSON object ``{"scenario": ...,
    "action": ..., "entities": [{"type": ..., "filler": ...}, ...]}``."""

    candidates = [match.strip() for match in _FENCE_RE.findall(text)]
    candidates.append(text.strip())
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        parsed = _as_slu_prediction(payload)
        if parsed is not None:
            return parsed[0], parsed[1], parsed[2], True
    return None, None, [], False


def _as_slu_prediction(payload: object) -> tuple[str | None, str | None, list[SlotEntity]] | None:
    if not isinstance(payload, Mapping):
        return None
    scenario = payload.get("scenario")
    action = payload.get("action")
    if scenario is not None and not isinstance(scenario, str):
        return None
    if action is not None and not isinstance(action, str):
        return None
    raw_entities = payload.get("entities", [])
    if not isinstance(raw_entities, list):
        return None
    entities: list[SlotEntity] = []
    for raw in raw_entities:
        if not isinstance(raw, Mapping):
            return None
        entity_type = raw.get("type")
        filler = raw.get("filler")
        if not isinstance(entity_type, str) or not isinstance(filler, str):
            return None
        entities.append(SlotEntity(type=entity_type, filler=filler))
    return scenario, action, entities


__all__ = [
    "SLURP_SCORER_VERSION",
    "SlotEntity",
    "SluScore",
    "parse_slu_response",
    "score_slu",
]
