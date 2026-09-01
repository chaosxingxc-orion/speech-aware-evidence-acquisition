"""Training-free control for semantic-factor top-1 Audio2Tool supply.

The module contains only deterministic parsing, retrieval, state extraction,
cross-fitted reward memory, and result-artifact logic. Model contact belongs
to the separately gated AgentLoop flight boundary. Gold is accepted only in
``FactorTop1Outcome`` scorer-side returns; it never enters factor parsing,
retrieval, rendering, or runtime state.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Literal, Mapping, Sequence

from ..data.audio2tool import render_registry_row
from ..reproduction.toolcall_scoring import ItemScore, parse_tool_calls_text
from .a2t_lexical_ceiling import BM25_B, BM25_K1, Bm25Index, tokenize
from .bootstrap import paired_cluster_bootstrap

EXPERIMENT_ID = "SAEA-A2T-TFRL-FACTOR-TOP1-104-V1"
POLICY_SCHEMA = "saea-a2t-training-free-factor-top1-policy-v1"
RETRIEVER_POLICY_ID = "saea-a2t-factor-registry-bm25-top1-v1"

STOP_M0 = "STOP_M0"
USE_FACTOR_TOP1 = "USE_FACTOR_TOP1"
Action = Literal["STOP_M0", "USE_FACTOR_TOP1"]

COARSE_CANDIDATE = "factor-top1-coarse-v1"
DETAILED_CANDIDATE = "factor-top1-detailed-v1"
CANDIDATE_IDS = (COARSE_CANDIDATE, DETAILED_CANDIDATE)

FOLD_SEED = 20260901
N_FOLDS = 5
MIN_CELL_SUPPORT = 4
MIN_CELL_SAVES = 2
MAX_CELL_HARMS = 0
MIN_USED = 5
MAX_USED = 52
MIN_SAVED = 3
MAX_HARMED = 1
MIN_NET_GAIN = 2
MIN_POSITIVE_FOLDS = 2
MIN_HARM_AVOIDANCE = 0.80
MIN_SAVE_RETENTION = 0.50
MIN_NON_DOMINANT_STATE_SAMPLES = 10
MIN_FACTOR_PARSE_RATE = 0.95
MIN_TOP1_AVAILABLE_FRACTION = 0.90
MIN_TOP1_TOOL_GAIN = 3
RESEND_COUNT = 16

_FACTOR_FIELDS = {
    "task_action",
    "task_object",
    "qualifiers",
    "argument_hints",
    "uncertainty",
}
_HINT_FIELDS = {"role", "value_hint"}
_UNCERTAINTIES = {"low", "medium", "high"}
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SIGNATURE_PARAMETER = re.compile(r"([A-Za-z][A-Za-z0-9_]*)\s*:")


class FactorTop1Error(RuntimeError):
    """The registered factor, retrieval, reward, or artifact contract failed."""


def _clean_ascii(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise FactorTop1Error(f"{field} must be ASCII text")
    if any(ord(character) < 32 or ord(character) > 126 for character in value):
        raise FactorTop1Error(f"{field} must contain printable ASCII text")
    cleaned = " ".join(value.split())
    if len(cleaned) > 80:
        raise FactorTop1Error(f"{field} exceeds 80 ASCII characters")
    return cleaned


def _contains_tool_name(value: str, tool_names: Sequence[str]) -> bool:
    folded = value.casefold()
    return any(name.casefold() in folded for name in tool_names if name)


@dataclass(frozen=True, order=True)
class ArgumentHint:
    role: str
    value_hint: str

    def as_json(self) -> dict[str, str]:
        return {"role": self.role, "value_hint": self.value_hint}


@dataclass(frozen=True)
class SemanticFactors:
    task_action: str
    task_object: str
    qualifiers: tuple[str, ...]
    argument_hints: tuple[ArgumentHint, ...]
    uncertainty: str

    def as_json(self) -> dict[str, object]:
        return {
            "task_action": self.task_action,
            "task_object": self.task_object,
            "qualifiers": list(self.qualifiers),
            "argument_hints": [hint.as_json() for hint in self.argument_hints],
            "uncertainty": self.uncertainty,
        }

    def query_text(self) -> str:
        parts = [self.task_action, self.task_object, *self.qualifiers]
        for hint in self.argument_hints:
            parts.extend((hint.role, hint.value_hint))
        return " ".join(part for part in parts if part)

    def nonempty_field_count(self) -> int:
        return sum(
            (
                bool(self.task_action),
                bool(self.task_object),
                bool(self.qualifiers),
                bool(self.argument_hints),
            )
        )


@dataclass(frozen=True)
class FactorParse:
    status: str
    reason: str
    factors: SemanticFactors | None
    canonical_json: str


def parse_semantic_factors(
    response_text: str, *, registry_tool_names: Sequence[str]
) -> FactorParse:
    """Parse and canonicalize the exact registered factor object."""

    def invalid(reason: str) -> FactorParse:
        return FactorParse("invalid", reason, None, "")

    if not isinstance(response_text, str):
        return invalid("factor response must be text")
    try:
        document = json.loads(response_text)
    except json.JSONDecodeError as error:
        return invalid(f"factor response is not exact JSON: {error}")
    if not isinstance(document, Mapping) or set(document) != _FACTOR_FIELDS:
        return invalid("factor object must carry the exact fields")
    try:
        action = _clean_ascii(document["task_action"], field="task_action")
        task_object = _clean_ascii(document["task_object"], field="task_object")
        uncertainty = document["uncertainty"]
        if uncertainty not in _UNCERTAINTIES:
            raise FactorTop1Error("uncertainty must be low, medium, or high")

        raw_qualifiers = document["qualifiers"]
        if not isinstance(raw_qualifiers, list) or len(raw_qualifiers) > 4:
            raise FactorTop1Error("qualifiers must be a list of at most four values")
        qualifiers = tuple(
            sorted(
                {
                    _clean_ascii(value, field="qualifier")
                    for value in raw_qualifiers
                    if _clean_ascii(value, field="qualifier")
                }
            )
        )

        raw_hints = document["argument_hints"]
        if not isinstance(raw_hints, list) or len(raw_hints) > 4:
            raise FactorTop1Error(
                "argument_hints must be a list of at most four values"
            )
        hints: set[ArgumentHint] = set()
        for index, raw_hint in enumerate(raw_hints):
            if not isinstance(raw_hint, Mapping) or set(raw_hint) != _HINT_FIELDS:
                raise FactorTop1Error(
                    f"argument_hints[{index}] must carry the exact fields"
                )
            role = _clean_ascii(raw_hint["role"], field=f"argument_hints[{index}].role")
            value_hint = _clean_ascii(
                raw_hint["value_hint"],
                field=f"argument_hints[{index}].value_hint",
            )
            if role or value_hint:
                hints.add(ArgumentHint(role, value_hint))

        factors = SemanticFactors(
            task_action=action,
            task_object=task_object,
            qualifiers=qualifiers,
            argument_hints=tuple(sorted(hints)),
            uncertainty=str(uncertainty),
        )
    except FactorTop1Error as error:
        return invalid(str(error))

    canonical = json.dumps(
        factors.as_json(), ensure_ascii=True, separators=(",", ":")
    )
    if _contains_tool_name(canonical, registry_tool_names):
        return invalid("factor object leaked a registry tool name")
    status = "valid-nonempty" if factors.query_text() else "valid-empty"
    return FactorParse(status, "accepted", factors, canonical)


def split_camel_case(value: str) -> str:
    return _CAMEL_BOUNDARY.sub(" ", value).replace("_", " ")


def _registry_rows(
    registry_rows: Sequence[Mapping[str, str]],
) -> tuple[tuple[int, Mapping[str, str]], ...]:
    parsed: list[tuple[int, Mapping[str, str]]] = []
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    for row in registry_rows:
        name = row.get("tool_name")
        if not isinstance(name, str) or not name:
            raise FactorTop1Error("registry row lacks a non-empty tool_name")
        try:
            tool_id = int(row.get("tool_id", ""))
        except (TypeError, ValueError):
            raise FactorTop1Error(f"registry tool {name!r} lacks numeric tool_id") from None
        if tool_id in seen_ids or name in seen_names:
            raise FactorTop1Error("registry tool ids and names must be unique")
        seen_ids.add(tool_id)
        seen_names.add(name)
        parsed.append((tool_id, row))
    if not parsed:
        raise FactorTop1Error("registry must contain at least one row")
    return tuple(sorted(parsed, key=lambda item: (item[0], item[1]["tool_name"])))


def registry_document_text(row: Mapping[str, str]) -> str:
    signature = row.get("signature", "")
    parameters = " ".join(
        split_camel_case(value) for value in _SIGNATURE_PARAMETER.findall(signature)
    )
    return " ".join(
        part
        for part in (
            split_camel_case(row.get("tool_name", "")),
            split_camel_case(row.get("domain", "")),
            split_camel_case(row.get("category", "")),
            row.get("description", ""),
            parameters,
        )
        if part
    )


@dataclass(frozen=True)
class Top1Retrieval:
    available: bool
    tool_id: int | None
    tool_name: str | None
    score: float
    second_score: float
    ranking_relation: str
    positive_document_count: int
    matched_token_fraction: float
    prompt_block: str


def retrieve_registry_top1(
    factors: SemanticFactors,
    registry_rows: Sequence[Mapping[str, str]],
) -> Top1Retrieval:
    """Rank the frozen registry and render at most one values-stripped row."""

    ordered = _registry_rows(registry_rows)
    documents = tuple(
        (str(tool_id), registry_document_text(row)) for tool_id, row in ordered
    )
    index = Bm25Index.build(documents)
    scores_by_index = index.scores(factors.query_text())
    positive = [
        (index_, score)
        for index_, score in scores_by_index.items()
        if math.isfinite(score) and score > 0.0
    ]
    if not positive:
        return Top1Retrieval(False, None, None, 0.0, 0.0, "no-positive", 0, 0.0, "")
    ranked = sorted(
        positive,
        key=lambda item: (-item[1], ordered[item[0]][0], ordered[item[0]][1]["tool_name"]),
    )
    top_index, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    tied = len(ranked) > 1 and top_score == second_score
    tool_id, row = ordered[top_index]
    query_tokens = set(tokenize(factors.query_text()))
    document_tokens = set(tokenize(documents[top_index][1]))
    matched_fraction = (
        len(query_tokens & document_tokens) / len(query_tokens)
        if query_tokens
        else 0.0
    )
    return Top1Retrieval(
        available=True,
        tool_id=tool_id,
        tool_name=row["tool_name"],
        score=float(top_score),
        second_score=float(second_score),
        ranking_relation="tied-top" if tied else "unique-top",
        positive_document_count=len(positive),
        matched_token_fraction=matched_fraction,
        prompt_block=render_registry_row(row, strip_defaults=True),
    )


def _positive_document_bucket(count: int) -> str:
    if count <= 0:
        return "unavailable"
    if count == 1:
        return "one"
    if count <= 5:
        return "two-to-five"
    return "six-or-more"


def _matched_fraction_bucket(value: float) -> str:
    if value <= 0.0:
        return "none"
    if value < 0.5:
        return "minority-below-one-half"
    return "majority-at-least-one-half"


def _field_count_bucket(count: int) -> str:
    if count <= 0:
        return "zero"
    if count == 1:
        return "one"
    if count == 2:
        return "two"
    return "three-or-more"


@dataclass(frozen=True)
class FactorTop1State:
    factor_status: str
    uncertainty: str
    m0_relation: str
    ranking_relation: str
    positive_document_count: str
    matched_token_fraction: str
    nonempty_field_count: str

    def key(self, candidate_id: str) -> tuple[str, ...]:
        if candidate_id == COARSE_CANDIDATE:
            return (
                self.factor_status,
                self.uncertainty,
                self.m0_relation,
                self.ranking_relation,
            )
        if candidate_id == DETAILED_CANDIDATE:
            return (
                *self.key(COARSE_CANDIDATE),
                self.positive_document_count,
                self.matched_token_fraction,
                self.nonempty_field_count,
            )
        raise FactorTop1Error(f"unknown candidate_id {candidate_id!r}")

    @property
    def coarse_key(self) -> tuple[str, ...]:
        return self.key(COARSE_CANDIDATE)

    @property
    def detailed_key(self) -> tuple[str, ...]:
        return self.key(DETAILED_CANDIDATE)


def extract_runtime_state(
    factor_parse: FactorParse,
    retrieval: Top1Retrieval,
    m0_response: str,
) -> FactorTop1State:
    factors = factor_parse.factors
    if not retrieval.available or retrieval.tool_name is None:
        m0_relation = "unavailable"
    else:
        calls, parsed = parse_tool_calls_text(m0_response)
        names = {call.name for call in calls}
        if not parsed or not names:
            m0_relation = "m0-unresolved"
        elif retrieval.tool_name in names:
            m0_relation = "m0-contains-top1"
        else:
            m0_relation = "m0-known-disagrees"
    return FactorTop1State(
        factor_status=factor_parse.status,
        uncertainty=(factors.uncertainty if factors is not None else "unavailable"),
        m0_relation=m0_relation,
        ranking_relation=retrieval.ranking_relation,
        positive_document_count=_positive_document_bucket(
            retrieval.positive_document_count
        ),
        matched_token_fraction=_matched_fraction_bucket(
            retrieval.matched_token_fraction
        ),
        nonempty_field_count=_field_count_bucket(
            factors.nonempty_field_count() if factors is not None else 0
        ),
    )


@dataclass(frozen=True)
class FactorTop1Outcome:
    sample_id: str
    group_id: str
    state: FactorTop1State
    supply_available: bool
    top1_gold_tool_correct: bool
    stop_score: ItemScore
    supply_score: ItemScore

    def __post_init__(self) -> None:
        if not self.sample_id or not self.group_id:
            raise ValueError("sample_id and group_id must be non-empty")
        if self.stop_score.exact_match not in (0.0, 1.0):
            raise ValueError("STOP exact match must be binary")
        if self.supply_score.exact_match not in (0.0, 1.0):
            raise ValueError("USE exact match must be binary")
        if not self.supply_available and self.top1_gold_tool_correct:
            raise ValueError("unavailable top-1 cannot be gold-tool correct")

    @property
    def delta(self) -> int:
        return int(self.supply_score.exact_match - self.stop_score.exact_match)

    @property
    def tool_accuracy_delta(self) -> int:
        return int(
            self.supply_score.tool_accuracy - self.stop_score.tool_accuracy
        )


@dataclass(frozen=True)
class MemoryDecision:
    action: Action
    level: str
    support: int
    saves: int
    harms: int
    reason: str


def _cell_counts(
    state_key: tuple[str, ...],
    memory: Sequence[FactorTop1Outcome],
    *,
    candidate_id: str,
) -> tuple[int, int, int]:
    cell = tuple(
        item
        for item in memory
        if item.supply_available and item.state.key(candidate_id) == state_key
    )
    return (
        len(cell),
        sum(item.delta > 0 for item in cell),
        sum(item.delta < 0 for item in cell),
    )


def _decide_cell(
    support: int, saves: int, harms: int, *, level: str
) -> MemoryDecision:
    if support < MIN_CELL_SUPPORT:
        return MemoryDecision(
            STOP_M0, level, support, saves, harms, "insufficient-support"
        )
    if harms > MAX_CELL_HARMS:
        return MemoryDecision(STOP_M0, level, support, saves, harms, "observed-harm")
    if saves < MIN_CELL_SAVES:
        return MemoryDecision(
            STOP_M0, level, support, saves, harms, "insufficient-saves"
        )
    return MemoryDecision(
        USE_FACTOR_TOP1,
        level,
        support,
        saves,
        harms,
        "supported-positive-zero-harm-cell",
    )


def decide(
    state: FactorTop1State,
    memory: Sequence[FactorTop1Outcome],
    *,
    supply_available: bool,
    candidate_id: str,
) -> MemoryDecision:
    if not supply_available:
        return MemoryDecision(STOP_M0, "availability", 0, 0, 0, "supply-unavailable")
    if candidate_id == COARSE_CANDIDATE:
        return _decide_cell(
            *_cell_counts(
                state.coarse_key, memory, candidate_id=COARSE_CANDIDATE
            ),
            level="coarse",
        )
    if candidate_id != DETAILED_CANDIDATE:
        raise FactorTop1Error(f"unknown candidate_id {candidate_id!r}")
    detailed_counts = _cell_counts(
        state.detailed_key, memory, candidate_id=DETAILED_CANDIDATE
    )
    detailed = _decide_cell(*detailed_counts, level="detailed")
    if detailed.support >= MIN_CELL_SUPPORT:
        return detailed
    return _decide_cell(
        *_cell_counts(state.coarse_key, memory, candidate_id=COARSE_CANDIDATE),
        level="coarse",
    )


def _stable_rank(seed: int, group_id: str) -> str:
    return hashlib.sha256(f"{seed}\0{group_id}".encode()).hexdigest()


def assign_folds(
    outcomes: Sequence[FactorTop1Outcome], *, seed: int, n_folds: int = N_FOLDS
) -> tuple[tuple[FactorTop1Outcome, ...], ...]:
    if n_folds < 2:
        raise FactorTop1Error("cross-fitting requires at least two folds")
    by_group: dict[str, list[FactorTop1Outcome]] = {}
    seen: set[str] = set()
    for item in outcomes:
        if item.sample_id in seen:
            raise FactorTop1Error(f"duplicate sample_id {item.sample_id!r}")
        seen.add(item.sample_id)
        by_group.setdefault(item.group_id, []).append(item)
    if len(by_group) < n_folds:
        raise FactorTop1Error("fewer independent groups than folds")
    ordered = sorted(
        by_group.items(),
        key=lambda pair: (-len(pair[1]), _stable_rank(seed, pair[0]), pair[0]),
    )
    folds: list[list[FactorTop1Outcome]] = [[] for _ in range(n_folds)]
    for _group_id, items in ordered:
        index = min(range(n_folds), key=lambda value: (len(folds[value]), value))
        folds[index].extend(items)
    return tuple(
        tuple(sorted(fold, key=lambda item: item.sample_id)) for fold in folds
    )


@dataclass(frozen=True)
class DecisionOutcome:
    outcome: FactorTop1Outcome
    action: Action

    @property
    def selected_score(self) -> ItemScore:
        return (
            self.outcome.supply_score
            if self.action == USE_FACTOR_TOP1
            else self.outcome.stop_score
        )

    @property
    def net_gain(self) -> int:
        return int(self.selected_score.exact_match - self.outcome.stop_score.exact_match)

    @property
    def tool_accuracy_net_gain(self) -> int:
        return int(
            self.selected_score.tool_accuracy
            - self.outcome.stop_score.tool_accuracy
        )


def _slot_f1(scores: Sequence[ItemScore]) -> float:
    true_positives = sum(score.slot_true_positives for score in scores)
    expected = sum(score.slot_expected_total for score in scores)
    predicted = sum(score.slot_predicted_total for score in scores)
    denominator = expected + predicted
    return (2.0 * true_positives / denominator) if denominator else 1.0


@dataclass(frozen=True)
class CandidateMetrics:
    n_samples: int
    used: int
    stopped: int
    saved: int
    harmed: int
    net_gain: int
    tool_accuracy_net_gain: int
    slot_micro_f1_net_gain: float
    final_contact_rate: float
    new_contacts_per_sample: float
    fold_net_gains: tuple[int, ...]
    ci_low: float
    ci_high: float
    sigma_hat: float
    harm_avoidance: float
    save_retention: float
    always_use_net_gain: int
    always_use_saves: int
    always_use_harms: int
    factor_parse_rate: float
    top1_available_fraction: float
    m0_tool_correct_count: int
    top1_gold_tool_correct_count: int


@dataclass(frozen=True)
class CandidateReport:
    candidate_id: str
    state_class_counts: Mapping[str, int]
    metrics: CandidateMetrics
    gates: Mapping[str, bool]
    promotion_passed: bool
    decisions: tuple[DecisionOutcome, ...]


@dataclass(frozen=True)
class ScreenResult:
    reports: Mapping[str, CandidateReport]
    selected_candidate: str | None
    promotion_passed: bool


def _state_label(state: FactorTop1State, candidate_id: str) -> str:
    return json.dumps(state.key(candidate_id), separators=(",", ":"))


def _bootstrap(
    decisions: Sequence[DecisionOutcome], *, seed: int, n_replicates: int
):
    by_group: dict[str, list[int]] = defaultdict(list)
    for decision in decisions:
        by_group[decision.outcome.group_id].append(decision.net_gain)
    group_ids = tuple(sorted(by_group))

    def statistic(groups: Sequence[str]) -> float:
        values = [value for group in groups for value in by_group[group]]
        return sum(values) / len(values)

    return paired_cluster_bootstrap(
        sample_ids=group_ids,
        statistic=statistic,
        n_replicates=n_replicates,
        seed=seed,
        ci_level=0.90,
    )


def evaluate_candidate(
    outcomes: Sequence[FactorTop1Outcome],
    *,
    candidate_id: str,
    resend_absolute_exact_count_difference: int,
    seed: int = FOLD_SEED,
    n_folds: int = N_FOLDS,
    n_replicates: int = 10_000,
) -> CandidateReport:
    ordered = tuple(sorted(outcomes, key=lambda item: item.sample_id))
    if not ordered:
        raise FactorTop1Error("candidate evaluation requires outcomes")
    if (
        isinstance(resend_absolute_exact_count_difference, bool)
        or not isinstance(resend_absolute_exact_count_difference, int)
        or resend_absolute_exact_count_difference < 0
    ):
        raise FactorTop1Error("resend exact-count difference must be non-negative")
    folds = assign_folds(ordered, seed=seed, n_folds=n_folds)
    decisions: list[DecisionOutcome] = []
    fold_net_gains: list[int] = []
    for fold_index, evaluation in enumerate(folds):
        memory = tuple(
            item
            for index, fold in enumerate(folds)
            if index != fold_index
            for item in fold
        )
        fold_decisions = tuple(
            DecisionOutcome(
                item,
                decide(
                    item.state,
                    memory,
                    supply_available=item.supply_available,
                    candidate_id=candidate_id,
                ).action,
            )
            for item in evaluation
        )
        decisions.extend(fold_decisions)
        fold_net_gains.append(sum(item.net_gain for item in fold_decisions))
    selected = tuple(sorted(decisions, key=lambda item: item.outcome.sample_id))

    used = sum(item.action == USE_FACTOR_TOP1 for item in selected)
    saved = sum(
        item.action == USE_FACTOR_TOP1 and item.outcome.delta > 0
        for item in selected
    )
    harmed = sum(
        item.action == USE_FACTOR_TOP1 and item.outcome.delta < 0
        for item in selected
    )
    always_use = tuple(item for item in ordered if item.supply_available)
    always_saves = sum(item.delta > 0 for item in always_use)
    always_harms = sum(item.delta < 0 for item in always_use)
    always_net = sum(item.delta for item in always_use)
    harm_avoidance = (
        (always_harms - harmed) / always_harms if always_harms else 1.0
    )
    save_retention = saved / always_saves if always_saves else 1.0
    net_gain = sum(item.net_gain for item in selected)
    tool_gain = sum(item.tool_accuracy_net_gain for item in selected)
    selected_scores = tuple(item.selected_score for item in selected)
    stop_scores = tuple(item.outcome.stop_score for item in selected)
    slot_gain = _slot_f1(selected_scores) - _slot_f1(stop_scores)
    bootstrap = _bootstrap(selected, seed=seed, n_replicates=n_replicates)
    class_counts = Counter(
        _state_label(item.state, candidate_id) for item in ordered
    )
    factor_parse_rate = sum(
        item.state.factor_status != "invalid" for item in ordered
    ) / len(ordered)
    available_fraction = sum(item.supply_available for item in ordered) / len(ordered)
    m0_tool_correct = sum(int(item.stop_score.tool_accuracy) for item in ordered)
    top1_correct = sum(item.top1_gold_tool_correct for item in ordered)
    non_dominant = len(ordered) - max(class_counts.values())

    gates = {
        "factor_parse_rate": factor_parse_rate >= MIN_FACTOR_PARSE_RATE,
        "top1_available": available_fraction >= MIN_TOP1_AVAILABLE_FRACTION,
        "top1_information_gain": top1_correct >= m0_tool_correct + MIN_TOP1_TOOL_GAIN,
        "both_actions": 0 < used < len(ordered),
        "use_range": MIN_USED <= used <= MAX_USED,
        "saved_minimum": saved >= MIN_SAVED,
        "harm_maximum": harmed <= MAX_HARMED,
        "net_gain": net_gain >= MIN_NET_GAIN,
        "gain_exceeds_resend_floor": net_gain
        > resend_absolute_exact_count_difference,
        "positive_ci90_lower": bootstrap.ci_low > 0.0,
        "tool_accuracy_nonnegative": tool_gain >= 0,
        "slot_micro_f1_nonnegative": slot_gain >= 0.0,
        "every_fold_nonnegative": all(value >= 0 for value in fold_net_gains),
        "positive_fold_count": sum(value > 0 for value in fold_net_gains)
        >= MIN_POSITIVE_FOLDS,
        "harm_avoidance": harm_avoidance >= MIN_HARM_AVOIDANCE,
        "save_retention": save_retention >= MIN_SAVE_RETENTION,
        "control_vs_always_use": net_gain >= always_net,
        "avoids_one_always_use_harm": always_harms - harmed >= 1,
        "state_liveness": len(class_counts) >= 2
        and non_dominant >= MIN_NON_DOMINANT_STATE_SAMPLES,
    }
    metrics = CandidateMetrics(
        n_samples=len(ordered),
        used=used,
        stopped=len(ordered) - used,
        saved=saved,
        harmed=harmed,
        net_gain=net_gain,
        tool_accuracy_net_gain=tool_gain,
        slot_micro_f1_net_gain=slot_gain,
        final_contact_rate=used / len(ordered),
        new_contacts_per_sample=1.0 + used / len(ordered),
        fold_net_gains=tuple(fold_net_gains),
        ci_low=bootstrap.ci_low,
        ci_high=bootstrap.ci_high,
        sigma_hat=bootstrap.sigma_hat,
        harm_avoidance=harm_avoidance,
        save_retention=save_retention,
        always_use_net_gain=always_net,
        always_use_saves=always_saves,
        always_use_harms=always_harms,
        factor_parse_rate=factor_parse_rate,
        top1_available_fraction=available_fraction,
        m0_tool_correct_count=m0_tool_correct,
        top1_gold_tool_correct_count=top1_correct,
    )
    return CandidateReport(
        candidate_id=candidate_id,
        state_class_counts=dict(sorted(class_counts.items())),
        metrics=metrics,
        gates=gates,
        promotion_passed=all(gates.values()),
        decisions=selected,
    )


def screen_candidates(
    outcomes: Sequence[FactorTop1Outcome],
    *,
    resend_absolute_exact_count_difference: int,
    seed: int = FOLD_SEED,
    n_folds: int = N_FOLDS,
    n_replicates: int = 10_000,
) -> ScreenResult:
    reports = {
        candidate_id: evaluate_candidate(
            outcomes,
            candidate_id=candidate_id,
            resend_absolute_exact_count_difference=(
                resend_absolute_exact_count_difference
            ),
            seed=seed,
            n_folds=n_folds,
            n_replicates=n_replicates,
        )
        for candidate_id in CANDIDATE_IDS
    }
    eligible = [report for report in reports.values() if report.promotion_passed]
    if not eligible:
        return ScreenResult(reports, None, False)
    winner = sorted(
        eligible,
        key=lambda report: (
            -report.metrics.net_gain,
            -report.metrics.saved,
            report.metrics.used,
            report.candidate_id,
        ),
    )[0]
    return ScreenResult(reports, winner.candidate_id, True)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()


def with_self_hash(document: Mapping[str, object]) -> dict[str, object]:
    payload = dict(document)
    payload.pop("self_sha256", None)
    payload["self_sha256"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
    return payload


def assert_self_hash(document: Mapping[str, object]) -> None:
    expected = document.get("self_sha256")
    payload = dict(document)
    payload.pop("self_sha256", None)
    actual = hashlib.sha256(_canonical_json(payload)).hexdigest()
    if expected != actual:
        raise FactorTop1Error(
            f"policy self hash mismatch: recorded={expected!r}, recomputed={actual!r}"
        )


def _decision_hash(report: CandidateReport) -> str:
    payload = "\n".join(
        f"{item.outcome.sample_id}\t{item.action}" for item in report.decisions
    ) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def _report_payload(report: CandidateReport) -> dict[str, object]:
    return {
        "candidate_id": report.candidate_id,
        "decision_identity_sha256": _decision_hash(report),
        "gates": dict(report.gates),
        "metrics": asdict(report.metrics),
        "promotion_passed": report.promotion_passed,
        "state_class_counts": dict(report.state_class_counts),
    }


def build_policy_artifact(
    outcomes: Sequence[FactorTop1Outcome],
    screen: ScreenResult,
    *,
    source_hashes: Mapping[str, str],
    resend_absolute_exact_count_difference: int,
    offline_attempts: int,
) -> dict[str, object]:
    if offline_attempts != 0:
        raise FactorTop1Error("offline guard recorded an outbound attempt")
    expected_sources = {"m0", "factors", "main", "resend", "registry"}
    if set(source_hashes) != expected_sources or any(
        len(value) != 64 for value in source_hashes.values()
    ):
        raise FactorTop1Error(
            "source hashes must bind full m0/factors/main/resend/registry SHA-256 values"
        )
    reports = {
        key: _report_payload(report)
        for key, report in sorted(screen.reports.items())
    }
    selected = reports.get(screen.selected_candidate) if screen.selected_candidate else None
    state_identity = hashlib.sha256(
        _canonical_json(
            [
                {
                    "sample_id": item.sample_id,
                    "group_id": item.group_id,
                    "state": asdict(item.state),
                    "supply_available": item.supply_available,
                }
                for item in sorted(outcomes, key=lambda row: row.sample_id)
            ]
        )
    ).hexdigest()
    return with_self_hash(
        {
            "schema": POLICY_SCHEMA,
            "experiment_id": EXPERIMENT_ID,
            "execution_profile": "bounded-discovery-probe",
            "claim_status": "exposed-cohort secondary discovery only",
            "policy": {
                "default_action": STOP_M0,
                "minimum_cell_support": MIN_CELL_SUPPORT,
                "minimum_cell_saves": MIN_CELL_SAVES,
                "maximum_cell_harms": MAX_CELL_HARMS,
                "mandatory_factor_contacts_per_sample": 1,
                "parameter_training": "none",
            },
            "candidate_reports": reports,
            "selected_candidate": screen.selected_candidate,
            "selected": selected,
            "promotion_passed": screen.promotion_passed,
            "state_identity_sha256": state_identity,
            "resend_absolute_exact_count_difference": (
                resend_absolute_exact_count_difference
            ),
            "source_hashes": dict(sorted(source_hashes.items())),
            "offline_guard": {
                "outbound_connection_attempts": offline_attempts,
                "targets": [],
            },
            "next_scale": (
                "separately preregister a fresh approximately-104 support flight"
                if screen.promotion_passed
                else "close semantic-factor BM25 top-1 single-row supply"
            ),
        }
    )


def assert_policy_admits_support(document: Mapping[str, object]) -> None:
    assert_self_hash(document)
    if document.get("schema") != POLICY_SCHEMA:
        raise FactorTop1Error("policy schema mismatch")
    if document.get("promotion_passed") is not True:
        raise FactorTop1Error("discovery promotion screen did not pass")
    selected = document.get("selected")
    if not isinstance(selected, Mapping):
        raise FactorTop1Error("policy lacks a selected candidate")
    metrics = selected.get("metrics")
    if not isinstance(metrics, Mapping):
        raise FactorTop1Error("policy lacks selected metrics")
    if int(metrics.get("used", 0)) <= 0 or int(metrics.get("stopped", 0)) <= 0:
        raise FactorTop1Error("selected policy must exercise both final actions")
    counts = selected.get("state_class_counts")
    if not isinstance(counts, Mapping) or len(counts) < 2:
        raise FactorTop1Error("selected policy state is not live")


__all__ = [
    "BM25_B",
    "BM25_K1",
    "CANDIDATE_IDS",
    "COARSE_CANDIDATE",
    "DETAILED_CANDIDATE",
    "EXPERIMENT_ID",
    "MIN_SAVED",
    "MAX_HARMED",
    "N_FOLDS",
    "POLICY_SCHEMA",
    "RESEND_COUNT",
    "RETRIEVER_POLICY_ID",
    "STOP_M0",
    "USE_FACTOR_TOP1",
    "ArgumentHint",
    "CandidateMetrics",
    "CandidateReport",
    "DecisionOutcome",
    "FactorParse",
    "FactorTop1Error",
    "FactorTop1Outcome",
    "FactorTop1State",
    "MemoryDecision",
    "ScreenResult",
    "SemanticFactors",
    "Top1Retrieval",
    "assert_policy_admits_support",
    "assert_self_hash",
    "assign_folds",
    "build_policy_artifact",
    "decide",
    "evaluate_candidate",
    "extract_runtime_state",
    "parse_semantic_factors",
    "registry_document_text",
    "retrieve_registry_top1",
    "screen_candidates",
    "split_camel_case",
    "with_self_hash",
]
