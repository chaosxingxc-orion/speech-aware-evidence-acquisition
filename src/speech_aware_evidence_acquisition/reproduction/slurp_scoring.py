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

#: Identity of the legal-label projection rule implemented by
#: :func:`project_slu_label` (preregistration
#: ``docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md``).
#: Bumped only when the RULE changes (candidate set, distance, tie-break
#: order, or which rows are eligible); the corpus the inventory and the prior
#: are mined from is pinned by the umbrella lock instead.
SLURP_LABEL_PROJECTION_ID = "slurp-legal-label-projection-v1"

#: Identity of the SUCCESSOR rule implemented by :func:`project_slu_label_v2`
#: (preregistration
#: ``docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md``).
#: A DIFFERENT rule, not a revision: v1 stays registered and resolvable, so a
#: verdict can pair against either one. Same bump policy.
SLURP_LABEL_PROJECTION_V2_ID = "slurp-legal-label-projection-v2"

#: The branch of a projection rule a row took, carried on
#: :class:`LabelProjection` so a receipt can count branches instead of
#: inferring them from a ``from -> to`` map.
PROJECTION_BRANCH_UNPARSED = "unparsed"
PROJECTION_BRANCH_NO_LABEL = "no-label"
PROJECTION_BRANCH_ALREADY_LEGAL = "already-legal"
PROJECTION_BRANCH_PROMOTE = "promote"
PROJECTION_BRANCH_EDIT_DISTANCE = "edit-distance"

#: Every branch name, in the order a receipt reports them.
PROJECTION_BRANCHES = (
    PROJECTION_BRANCH_UNPARSED,
    PROJECTION_BRANCH_NO_LABEL,
    PROJECTION_BRANCH_ALREADY_LEGAL,
    PROJECTION_BRANCH_PROMOTE,
    PROJECTION_BRANCH_EDIT_DISTANCE,
)

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


# ---------------------------------------------------------------------------
# Legal-label projection (2026-09-06 owner ruling: a model-usage LOCAL
# OPTIMIZATION, allowed before any mechanism, zero model contacts).
#
# The locked closed-list direct baseline still names a (scenario, action) pair
# that does not occur in ``train`` on 4.20 % of DEV-1000
# (docs/readiness/2026-09-05-slurp-closed-list-direct-baseline-v1-verdict.md
# section 4). Such a label is certainly wrong -- the gold vocabulary cannot
# contain it -- and MF-7 measured that legalising exactly this class is worth
# about +1.4 pp intent. The projection below maps an illegal pair onto the
# nearest legal one, deterministically, and NOTHING else: entities are never
# touched, an unparsed response stays unparsed, and a row that already names a
# legal pair is returned byte-identical.
#
# The rule lives HERE, in the pure per-sample scoring module, and takes its
# inventory and its prior as arguments: this module deliberately imports no
# loader (``data.slurp``), so the rule stays a pure function of its inputs and
# is unit-testable without a corpus. ``reproduction.slurp_official_eval``
# builds the real inventory from the pinned TRAIN corpus and passes it in.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LegalIntentInventory:
    """The closed ``(scenario, action)`` label space a projection may emit,
    plus the TRAIN prior that breaks its ties.

    ``actions_by_scenario`` is the SAME pairing
    ``data.slurp.SlurpOntology.actions_by_scenario`` carries -- 18 scenarios
    and the 60 pairs observed in ``train`` on the real corpus -- and
    ``intent_prior`` maps the ``f"{scenario}_{action}"`` spelling
    ``SlurpRecord.intent`` uses to that intent's TRAIN utterance count.

    Build one through :func:`legal_intent_inventory`, which validates and
    freezes both mappings; constructing this dataclass directly bypasses
    those checks.
    """

    actions_by_scenario: Mapping[str, tuple[str, ...]]
    intent_prior: Mapping[str, int]

    @property
    def scenarios(self) -> tuple[str, ...]:
        return tuple(sorted(self.actions_by_scenario))

    @property
    def pairs(self) -> frozenset[tuple[str, str]]:
        return frozenset(
            (scenario, action)
            for scenario, actions in self.actions_by_scenario.items()
            for action in actions
        )

    def prior(self, scenario: str, action: str) -> int:
        """This intent's TRAIN utterance count, 0 when TRAIN never carried it
        (an inventory pair with no prior entry is legal but unweighted -- it
        loses every tie to a pair TRAIN actually saw, which is the intended
        ordering, not a defect)."""

        return int(self.intent_prior.get(f"{scenario}_{action}", 0))

    def scenario_prior(self, scenario: str) -> int:
        """The scenario's total TRAIN utterance mass, summed over its own
        legal actions."""

        return sum(
            self.prior(scenario, action)
            for action in self.actions_by_scenario.get(scenario, ())
        )

    def owners_of(self, action: str) -> tuple[str, ...]:
        """Every legal scenario whose action list carries ``action``,
        alphabetically; empty when ``action`` is not a legal action name
        anywhere in the inventory.

        This is the whole extra structure ``slurp-legal-label-projection-v2``
        needs (:func:`project_slu_label_v2`): it is derived from the SAME 60
        pairs the v1 rule already reads, never from a second source.
        """

        return tuple(
            scenario
            for scenario in self.scenarios
            if action in self.actions_by_scenario[scenario]
        )


def legal_intent_inventory(
    actions_by_scenario: Mapping[str, Sequence[str]],
    intent_prior: Mapping[str, int] | None = None,
) -> LegalIntentInventory:
    """Validate and freeze a :class:`LegalIntentInventory`.

    Fails closed on an empty pairing, on a scenario with no actions, and on a
    non-text label: a projection whose target space is empty or malformed
    would silently emit garbage into a scored prediction file, which is
    exactly what this module exists to prevent.
    """

    if not actions_by_scenario:
        raise ValueError(
            "legal_intent_inventory requires a non-empty (scenario -> actions) pairing; "
            "a projection with no legal target space can only invent labels"
        )
    frozen: dict[str, tuple[str, ...]] = {}
    for scenario, actions in actions_by_scenario.items():
        if not isinstance(scenario, str) or not scenario:
            raise ValueError(f"legal inventory scenario must be non-empty text, got {scenario!r}")
        if isinstance(actions, (str, bytes)) or not actions:
            raise ValueError(
                f"legal inventory scenario {scenario!r} must carry a non-empty action sequence"
            )
        for action in actions:
            if not isinstance(action, str) or not action:
                raise ValueError(
                    f"legal inventory scenario {scenario!r} carries a non-text action {action!r}"
                )
        frozen[scenario] = tuple(sorted(set(actions)))
    prior: dict[str, int] = {}
    for intent, count in (intent_prior or {}).items():
        if not isinstance(intent, str) or not intent:
            raise ValueError(f"TRAIN prior key must be non-empty text, got {intent!r}")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(
                f"TRAIN prior for {intent!r} must be a non-negative int, got {count!r}"
            )
        prior[intent] = count
    return LegalIntentInventory(
        actions_by_scenario=dict(sorted(frozen.items())),
        intent_prior=dict(sorted(prior.items())),
    )


@dataclass(frozen=True)
class LabelProjection:
    """One row's projection outcome. ``changed`` is ``True`` only when the
    emitted pair differs from the parsed one; ``eligible`` says whether the
    row was a candidate at all (a parsed row naming BOTH a scenario and an
    action); ``branch`` names the rule branch the row took, one of
    :data:`PROJECTION_BRANCHES`.

    ``branch`` is descriptive bookkeeping, never an input to a metric: it
    exists so a receipt can count how many rows each branch of a rule carried
    instead of reverse-engineering that from a ``from -> to`` map.
    """

    scenario: str | None
    action: str | None
    changed: bool
    eligible: bool
    source_scenario: str | None
    source_action: str | None
    branch: str = PROJECTION_BRANCH_EDIT_DISTANCE

    @property
    def source_intent(self) -> str | None:
        if self.source_scenario is None or self.source_action is None:
            return None
        return f"{self.source_scenario}_{self.source_action}"

    @property
    def projected_intent(self) -> str | None:
        if self.scenario is None or self.action is None:
            return None
        return f"{self.scenario}_{self.action}"


def project_slu_label(
    scenario: str | None,
    action: str | None,
    inventory: LegalIntentInventory,
    *,
    parsed: bool = True,
) -> LabelProjection:
    """Map an illegal ``(scenario, action)`` onto the nearest legal intent.

    The rule, exactly as preregistered
    (``docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md``
    section 1):

    1. an unparsed response stays unparsed -- no label is invented;
    2. a row missing either half (the ``{"entities": [...]}`` shape a
       slot-only arm answers with) is untouched: there is no
       ``scenario_action`` to project;
    3. a row already naming one of the legal pairs is untouched;
    4. otherwise, with ``lev`` the Levenshtein distance the char-distance
       metric already uses:

       * **the scenario is legal** -- keep it, and choose the action of that
         scenario minimizing ``(lev(action, candidate), -prior, candidate)``:
         smallest edit distance, then the LARGER TRAIN prior, then the
         alphabetically first name;
       * **the scenario is illegal** -- choose the legal scenario minimizing
         ``(lev(scenario, candidate), -scenario_prior, candidate)`` under the
         same three-level key, then its nearest action by the rule above.

    Entities are not an argument and are never touched, so every entity-side
    metric (entities strict, Word-F1, Char-F1, SLU-F1) is structurally
    unchanged by this function.
    """

    if not parsed or scenario is None or action is None:
        return LabelProjection(
            scenario=scenario,
            action=action,
            changed=False,
            eligible=False,
            source_scenario=scenario,
            source_action=action,
            branch=(
                PROJECTION_BRANCH_UNPARSED if not parsed else PROJECTION_BRANCH_NO_LABEL
            ),
        )
    if (scenario, action) in inventory.pairs:
        return LabelProjection(
            scenario=scenario,
            action=action,
            changed=False,
            eligible=True,
            source_scenario=scenario,
            source_action=action,
            branch=PROJECTION_BRANCH_ALREADY_LEGAL,
        )
    target_scenario = scenario
    if scenario not in inventory.actions_by_scenario:
        target_scenario = min(
            inventory.scenarios,
            key=lambda candidate: (
                _levenshtein(scenario, candidate),
                -inventory.scenario_prior(candidate),
                candidate,
            ),
        )
    target_action = min(
        inventory.actions_by_scenario[target_scenario],
        key=lambda candidate: (
            _levenshtein(action, candidate),
            -inventory.prior(target_scenario, candidate),
            candidate,
        ),
    )
    return LabelProjection(
        scenario=target_scenario,
        action=target_action,
        changed=(target_scenario, target_action) != (scenario, action),
        eligible=True,
        source_scenario=scenario,
        source_action=action,
        branch=PROJECTION_BRANCH_EDIT_DISTANCE,
    )


def project_slu_label_v2(
    scenario: str | None,
    action: str | None,
    inventory: LegalIntentInventory,
    *,
    parsed: bool = True,
) -> LabelProjection:
    """``slurp-legal-label-projection-v2``: promote an action-named scenario
    back to the scenario that owns it, and otherwise fall through to v1.

    The rule, exactly as preregistered
    (``docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md``
    section 1). Rows 1-3 are v1's and are reached through v1's own code, not a
    copy of it: an unparsed response stays unparsed, a row missing either half
    is untouched, a row already naming one of the legal pairs is untouched.
    For an ILLEGAL pair:

    * **4-PROMOTE** -- if ``scenario`` is NOT a legal scenario but IS a legal
      ACTION name, emit ``(owner, scenario)``: the model wrote the action in
      the scenario slot (``locations/query`` for ``recommendation_locations``)
      and put a generic action beside it, so the action name is the signal and
      ``action`` is discarded. The owner is chosen by ``(-prior, scenario)`` --
      the larger TRAIN prior, then alphabetically -- ONE expression whether the
      action name has a single owner or several, so the two cases cannot drift
      apart.
    * **4-FALLBACK** -- otherwise :func:`project_slu_label`, unchanged.

    Why this exists: v1 repairs LEGALITY by spelling, which sends ``locations``
    to ``lists`` because that is what ``locations`` is spelled like. The
    label's legality was never the problem; which legal label the repair picks
    is. v1's own verdict named and priced this class and refused to lock it,
    because it was found by reading v1's output
    (``docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-verdict.md``
    section 5).

    Entities are not an argument and are never touched, so every entity-side
    metric is structurally unchanged, exactly as under v1.
    """

    base = project_slu_label(scenario, action, inventory, parsed=parsed)
    if not base.eligible or not base.changed:
        # Unparsed, label-free or already legal: v1 and v2 agree by
        # construction, and the branch v1 recorded is the branch v2 took.
        return base
    # ``base.eligible and base.changed`` implies both halves are text and the
    # pair is illegal -- 4-PROMOTE's precondition, checked from the SOURCE
    # label rather than from v1's chosen target.
    if scenario is None or scenario in inventory.actions_by_scenario:
        # A legal scenario slot may well be right; the promotion only repairs
        # a scenario slot that CANNOT be right.
        return base
    owners = inventory.owners_of(scenario)
    if not owners:
        return base
    owner = min(owners, key=lambda candidate: (-inventory.prior(candidate, scenario), candidate))
    return LabelProjection(
        scenario=owner,
        action=scenario,
        # ``owner`` is a legal scenario and ``scenario`` is not, so the emitted
        # pair can never equal the parsed one.
        changed=True,
        eligible=True,
        source_scenario=scenario,
        source_action=action,
        branch=PROJECTION_BRANCH_PROMOTE,
    )


__all__ = [
    "PROJECTION_BRANCHES",
    "PROJECTION_BRANCH_ALREADY_LEGAL",
    "PROJECTION_BRANCH_EDIT_DISTANCE",
    "PROJECTION_BRANCH_NO_LABEL",
    "PROJECTION_BRANCH_PROMOTE",
    "PROJECTION_BRANCH_UNPARSED",
    "SLURP_LABEL_PROJECTION_ID",
    "SLURP_LABEL_PROJECTION_V2_ID",
    "SLURP_SCORER_VERSION",
    "LabelProjection",
    "LegalIntentInventory",
    "SlotEntity",
    "SluScore",
    "legal_intent_inventory",
    "parse_slu_response",
    "project_slu_label",
    "project_slu_label_v2",
    "score_slu",
]
