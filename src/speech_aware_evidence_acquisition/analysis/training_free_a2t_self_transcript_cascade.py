"""Training-free control for the Audio2Tool self-transcript cascade.

Runtime functions in this module accept only a same-core English transcript,
the frozen TRAIN knowledge snapshot, and the frozen M0 response. Gold enters
only through scorer-side ``SelfTranscriptOutcome`` objects after all model
responses and complete prediction manifests have sealed.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from ..rails.knowledge import KnowledgeSnapshot
from ..reproduction.toolcall_scoring import ItemScore, parse_tool_calls_text
from .a2t_lexical_ceiling import Bm25Index
from .bootstrap import paired_cluster_bootstrap

EXPERIMENT_ID = "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1"
RETRIEVER_POLICY_ID = "saea-a2t-self-transcript-content-bm25-top5-v1"
SELF_TRANSCRIPT_INSTRUCTION = (
    "Transcribe the English speech verbatim. Output only the spoken English "
    "words. Do not answer the request, infer missing content, emit JSON, or "
    "name a tool. If a word is unclear, write the most likely English word "
    "without commentary."
)

STOP_M0 = "STOP_M0"
USE_MATCHED = "USE_MATCHED"
Action = Literal["STOP_M0", "USE_MATCHED"]

EXPECTED_ROWS = 104
MIN_RESPONSES = 102
MIN_VALID_TRANSCRIPTS = 99
MIN_POSITIVE_ROUTES = 94
MIN_DISTINCT_TRANSCRIPTS = 83
MAX_IDENTICAL_TRANSCRIPTS = 5
MAX_FACETS = 5
MAX_VALUES = 6
MAX_TARGETS = 5
N_FOLDS = 5
FOLD_SEED = 20260901
MIN_CELL_SUPPORT = 4
MIN_CELL_SAVES = 2
MAX_CELL_HARMS = 0
MIN_USED = 5
MAX_USED = 52
MIN_POLICY_SAVES = 3
MAX_POLICY_HARMS = 0
MIN_POLICY_NET_GAIN = 3
MIN_INFORMATION_GAIN = 3
MIN_POSITIVE_FOLDS = 2
MIN_NON_DOMINANT_STATE_SAMPLES = 10

_ALNUM_TOKEN = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
_ROLE_PREFIX = re.compile(r"\s*(?:assistant|user|system|model|transcript)\s*:", re.I)
_TOOL_STRUCTURE = re.compile(r"(?:tool_calls?|function_call|<tool_call)", re.I)
_REFUSAL_PREFIXES = (
    "i cannot transcribe",
    "i can't transcribe",
    "i am unable to transcribe",
    "sorry, i cannot",
    "sorry, i can't",
)


class SelfTranscriptCascadeError(RuntimeError):
    """The registered observation, retrieval, policy, or gate failed."""


@dataclass(frozen=True)
class TranscriptParse:
    valid: bool
    reason: str
    text: str
    word_count: int
    prohibited_structure: bool = False


def validate_self_transcript(response_text: object) -> TranscriptParse:
    """Apply the frozen English-only structural gate without reading gold."""

    def invalid(reason: str, *, prohibited: bool = False) -> TranscriptParse:
        return TranscriptParse(False, reason, "", 0, prohibited)

    if not isinstance(response_text, str):
        return invalid("transcript response must be text")
    stripped = response_text.strip()
    if not stripped:
        return invalid("transcript is empty")
    if "```" in stripped:
        return invalid("transcript contains a code fence", prohibited=True)
    if any(ord(character) < 32 or ord(character) > 126 for character in stripped):
        return invalid("transcript must contain printable ASCII only")
    if "\n" in stripped or "\r" in stripped:
        return invalid("transcript must contain exactly one line")
    if _ROLE_PREFIX.match(stripped):
        return invalid("transcript contains a role prefix", prohibited=True)
    if _TOOL_STRUCTURE.search(stripped):
        return invalid("transcript contains a tool-call structure", prohibited=True)
    try:
        json.loads(stripped)
    except json.JSONDecodeError:
        pass
    else:
        return invalid("transcript is JSON", prohibited=True)

    canonical = " ".join(stripped.split())
    folded = canonical.casefold()
    if folded.startswith(_REFUSAL_PREFIXES):
        return invalid("transcript contains a refusal marker", prohibited=True)
    words = canonical.split()
    if len(words) > 160:
        return invalid("transcript exceeds 160 tokens")
    tokens = _ALNUM_TOKEN.findall(canonical)
    if not tokens or not any(any(character.isalpha() for character in token) for token in tokens):
        return invalid("transcript must contain an ASCII letter")
    letter_tokens = sum(
        any("A" <= character <= "Z" or "a" <= character <= "z" for character in token)
        for token in tokens
    )
    if letter_tokens / len(tokens) < 0.80:
        return invalid("fewer than 0.80 of alphanumeric tokens contain an ASCII letter")
    return TranscriptParse(True, "accepted", canonical, len(words), False)


@dataclass(frozen=True)
class EvidenceRoute:
    available: bool
    facet_ids: tuple[str, ...]
    value_ids: tuple[str, ...]
    task_targets: tuple[str, ...]
    scores: tuple[float, ...]
    positive_facet_count: int
    top1_margin: float
    prompt_block: str


def _content_documents(
    snapshot: KnowledgeSnapshot,
) -> tuple[tuple[str, str], ...]:
    values_by_facet: dict[str, list[object]] = defaultdict(list)
    for value in snapshot.values:
        if value.task_target is None:
            continue
        for facet_id in value.associated_facet_ids:
            values_by_facet[facet_id].append(value)
    documents = tuple(
        sorted(
            (
                (facet.facet_id, facet.representation)
                for facet in snapshot.facets
                if facet.dimension == "content" and facet.facet_id in values_by_facet
            ),
            key=lambda item: item[0],
        )
    )
    if not documents:
        raise SelfTranscriptCascadeError(
            "knowledge snapshot has no task-target-bearing content facets"
        )
    return documents


class EvidenceRetriever:
    """One immutable BM25 index reused across the complete observation batch."""

    def __init__(self, snapshot: KnowledgeSnapshot) -> None:
        self._snapshot = snapshot.validate()
        self._documents = _content_documents(snapshot)
        self._index = Bm25Index.build(self._documents)
        self.snapshot_sha256 = snapshot.content_hash()

    def route(self, transcript: str) -> EvidenceRoute:
        if not isinstance(transcript, str) or not transcript.strip():
            raise SelfTranscriptCascadeError(
                "retrieval requires a non-empty transcript"
            )
        scored = [
            (document_index, float(score))
            for document_index, score in self._index.scores(transcript).items()
            if math.isfinite(score) and score > 0.0
        ]
        if not scored:
            return EvidenceRoute(False, (), (), (), (), 0, 0.0, "")
        ranked = sorted(
            scored,
            key=lambda item: (-item[1], self._index.doc_ids[item[0]]),
        )
        selected = ranked[:MAX_FACETS]
        facet_ids = tuple(
            self._index.doc_ids[index_] for index_, _score in selected
        )
        scores = tuple(score for _index, score in selected)
        top_score = scores[0]
        second_score = scores[1] if len(scores) > 1 else 0.0
        top1_margin = (top_score - second_score) / max(top_score, 1e-12)

        selected_score = dict(zip(facet_ids, scores, strict=True))
        value_candidates: list[tuple[float, str, object]] = []
        for value in self._snapshot.values:
            supporting = set(value.associated_facet_ids) & set(facet_ids)
            if not supporting or value.task_target is None:
                continue
            best = max(selected_score[facet_id] for facet_id in supporting)
            value_candidates.append((-best, value.value_id, value))
        value_candidates.sort(key=lambda item: (item[0], item[1]))

        chosen: list[object] = []
        targets: list[str] = []
        for _negative_score, _value_id, value in value_candidates:
            target = value.task_target
            if target not in targets and len(targets) >= MAX_TARGETS:
                continue
            chosen.append(value)
            if target not in targets:
                targets.append(target)
            if len(chosen) == MAX_VALUES:
                break
        if not chosen:
            return EvidenceRoute(
                False, (), (), (), (), len(scored), top1_margin, ""
            )
        prompt_block = "\n".join(
            f"[value {value.value_id}] {value.content}" for value in chosen
        )
        return EvidenceRoute(
            True,
            facet_ids,
            tuple(value.value_id for value in chosen),
            tuple(targets),
            scores,
            len(scored),
            top1_margin,
            prompt_block,
        )


def retrieve_evidence(
    transcript: str,
    snapshot: KnowledgeSnapshot,
    *,
    max_facets: int = MAX_FACETS,
    max_values: int = MAX_VALUES,
    max_targets: int = MAX_TARGETS,
) -> EvidenceRoute:
    """Reference one-query entry point with frozen 5/6/5 budgets."""

    if (max_facets, max_values, max_targets) != (
        MAX_FACETS,
        MAX_VALUES,
        MAX_TARGETS,
    ):
        raise SelfTranscriptCascadeError("retrieval budgets are frozen at 5/6/5")
    return EvidenceRetriever(snapshot).route(transcript)


@dataclass(frozen=True)
class ObservationRecord:
    sample_id: str
    tier: str
    response_received: bool
    transcript: TranscriptParse
    positive_route: bool


@dataclass(frozen=True)
class LivenessReport:
    row_count: int
    response_count: int
    valid_transcript_count: int
    positive_route_count: int
    distinct_transcript_count: int
    largest_identical_transcript_count: int
    prohibited_structure_count: int
    gates: Mapping[str, bool]
    passed: bool


@dataclass(frozen=True)
class LivenessReceipt:
    passed: bool
    row_count: int
    report_sha256: str
    gates: Mapping[str, bool]


def _derangement_possible(rows: Sequence[ObservationRecord]) -> bool:
    by_tier: Counter[str] = Counter(
        row.tier for row in rows if row.transcript.valid and row.positive_route
    )
    return all(count >= 2 for count in by_tier.values()) and bool(by_tier)


def evaluate_liveness(rows: Sequence[ObservationRecord]) -> LivenessReport:
    frozen = tuple(rows)
    if len(frozen) != EXPECTED_ROWS:
        raise SelfTranscriptCascadeError(
            f"liveness requires exactly {EXPECTED_ROWS} observation rows"
        )
    ids = [row.sample_id for row in frozen]
    if any(not sample_id for sample_id in ids) or len(set(ids)) != len(ids):
        raise SelfTranscriptCascadeError(
            "liveness observation sample identities must be non-empty and unique"
        )
    if any(not row.tier for row in frozen):
        raise SelfTranscriptCascadeError("liveness rows require tier identities")
    valid_texts = [row.transcript.text for row in frozen if row.transcript.valid]
    transcript_counts = Counter(valid_texts)
    response_count = sum(row.response_received for row in frozen)
    valid_count = len(valid_texts)
    route_count = sum(
        row.transcript.valid and row.positive_route for row in frozen
    )
    prohibited_count = sum(row.transcript.prohibited_structure for row in frozen)
    distinct_count = len(transcript_counts)
    largest_count = max(transcript_counts.values(), default=0)
    gates = {
        "response_count": response_count >= MIN_RESPONSES,
        "valid_transcript_count": valid_count >= MIN_VALID_TRANSCRIPTS,
        "positive_route_count": route_count >= MIN_POSITIVE_ROUTES,
        "transcript_diversity": distinct_count >= MIN_DISTINCT_TRANSCRIPTS,
        "mode_count": largest_count <= MAX_IDENTICAL_TRANSCRIPTS,
        "prohibited_structure": prohibited_count == 0,
        "same_tier_derangement": _derangement_possible(frozen),
    }
    return LivenessReport(
        row_count=len(frozen),
        response_count=response_count,
        valid_transcript_count=valid_count,
        positive_route_count=route_count,
        distinct_transcript_count=distinct_count,
        largest_identical_transcript_count=largest_count,
        prohibited_structure_count=prohibited_count,
        gates=gates,
        passed=all(gates.values()),
    )


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def authorize_use_phase(rows: Sequence[ObservationRecord]) -> LivenessReceipt:
    report = evaluate_liveness(rows)
    if not report.passed:
        failed = sorted(key for key, passed in report.gates.items() if not passed)
        raise SelfTranscriptCascadeError(
            f"label-free liveness gate failed: {failed}"
        )
    payload = {
        "row_count": report.row_count,
        "response_count": report.response_count,
        "valid_transcript_count": report.valid_transcript_count,
        "positive_route_count": report.positive_route_count,
        "distinct_transcript_count": report.distinct_transcript_count,
        "largest_identical_transcript_count": report.largest_identical_transcript_count,
        "prohibited_structure_count": report.prohibited_structure_count,
        "gates": dict(report.gates),
        "passed": report.passed,
    }
    return LivenessReceipt(
        passed=True,
        row_count=report.row_count,
        report_sha256=hashlib.sha256(_canonical_json(payload)).hexdigest(),
        gates=dict(report.gates),
    )


def build_same_tier_derangement(
    sample_tiers: Mapping[str, str],
) -> dict[str, str]:
    if not sample_tiers:
        raise SelfTranscriptCascadeError("derangement requires routed samples")
    if any(not sample_id or not tier for sample_id, tier in sample_tiers.items()):
        raise SelfTranscriptCascadeError("derangement identities must be non-empty")
    by_tier: dict[str, list[str]] = defaultdict(list)
    for sample_id, tier in sample_tiers.items():
        by_tier[tier].append(sample_id)
    result: dict[str, str] = {}
    for tier, sample_ids in sorted(by_tier.items()):
        if len(sample_ids) < 2:
            raise SelfTranscriptCascadeError(
                f"tier {tier!r} needs at least two routed samples for derangement"
            )
        ordered = sorted(
            sample_ids,
            key=lambda sample_id: (
                hashlib.sha256(
                    f"shuffled-evidence-v1\n{sample_id}".encode("utf-8")
                ).hexdigest(),
                sample_id,
            ),
        )
        for index, sample_id in enumerate(ordered):
            result[sample_id] = ordered[(index + 1) % len(ordered)]
    return dict(sorted(result.items()))


def _count_bucket(count: int) -> str:
    if count <= 0:
        return "unavailable"
    if count == 1:
        return "one"
    if count <= 5:
        return "two-to-five"
    return "six-or-more"


def _word_bucket(count: int) -> str:
    if count <= 0:
        return "unavailable"
    if count <= 4:
        return "one-to-four"
    if count <= 8:
        return "five-to-eight"
    return "nine-or-more"


def _target_bucket(count: int) -> str:
    if count <= 0:
        return "unavailable"
    if count == 1:
        return "one"
    if count <= 3:
        return "two-to-three"
    return "four-to-five"


@dataclass(frozen=True)
class SelfTranscriptState:
    m0_relation: str
    top1_margin: str
    positive_facet_count: str
    transcript_word_count: str
    supplied_target_count: str

    @property
    def coarse_key(self) -> tuple[str, ...]:
        return (
            self.m0_relation,
            self.top1_margin,
            self.positive_facet_count,
        )

    @property
    def detailed_key(self) -> tuple[str, ...]:
        return (
            *self.coarse_key,
            self.transcript_word_count,
            self.supplied_target_count,
        )


def extract_runtime_state(
    *,
    transcript: TranscriptParse,
    route: EvidenceRoute,
    m0_response: str,
) -> SelfTranscriptState:
    if not transcript.valid or not route.available:
        return SelfTranscriptState(
            "unresolved", "unavailable", "unavailable", "unavailable", "unavailable"
        )
    calls, parsed = parse_tool_calls_text(m0_response)
    names = {call.name for call in calls}
    if not parsed or not names:
        relation = "unresolved"
    elif names & set(route.task_targets):
        relation = "intersects"
    else:
        relation = "known-disjoint"
    return SelfTranscriptState(
        m0_relation=relation,
        top1_margin=(
            "at-least-0.15" if route.top1_margin >= 0.15 else "below-0.15"
        ),
        positive_facet_count=_count_bucket(route.positive_facet_count),
        transcript_word_count=_word_bucket(transcript.word_count),
        supplied_target_count=_target_bucket(len(route.task_targets)),
    )


@dataclass(frozen=True)
class SelfTranscriptOutcome:
    sample_id: str
    group_id: str
    state: SelfTranscriptState
    route_available: bool
    top5_gold_tool_correct: bool
    stop_score: ItemScore
    matched_score: ItemScore
    shuffled_score: ItemScore

    def __post_init__(self) -> None:
        if not self.sample_id or not self.group_id:
            raise ValueError("sample_id and group_id must be non-empty")
        for label, score in (
            ("STOP", self.stop_score),
            ("matched", self.matched_score),
            ("shuffled", self.shuffled_score),
        ):
            if score.exact_match not in (0.0, 1.0):
                raise ValueError(f"{label} exact match must be binary")
        if not self.route_available and self.top5_gold_tool_correct:
            raise ValueError("an unavailable route cannot contain the gold tool")

    @property
    def delta(self) -> int:
        return int(self.matched_score.exact_match - self.stop_score.exact_match)


@dataclass(frozen=True)
class MemoryDecision:
    action: Action
    level: str
    support: int
    saves: int
    harms: int
    reason: str


def _cell_counts(
    key: tuple[str, ...],
    memory: Sequence[SelfTranscriptOutcome],
    *,
    detailed: bool,
) -> tuple[int, int, int]:
    cell = tuple(
        item
        for item in memory
        if item.route_available
        and (item.state.detailed_key if detailed else item.state.coarse_key) == key
    )
    return (
        len(cell),
        sum(item.delta > 0 for item in cell),
        sum(item.delta < 0 for item in cell),
    )


def _decide_counts(
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
        USE_MATCHED,
        level,
        support,
        saves,
        harms,
        "supported-positive-zero-harm-cell",
    )


def decide(
    state: SelfTranscriptState,
    memory: Sequence[SelfTranscriptOutcome],
    *,
    route_available: bool,
) -> MemoryDecision:
    if not route_available:
        return MemoryDecision(STOP_M0, "availability", 0, 0, 0, "route-unavailable")
    detailed_counts = _cell_counts(
        state.detailed_key, memory, detailed=True
    )
    detailed = _decide_counts(*detailed_counts, level="detailed")
    if detailed.support >= MIN_CELL_SUPPORT:
        return detailed
    return _decide_counts(
        *_cell_counts(state.coarse_key, memory, detailed=False),
        level="coarse",
    )


def _stable_rank(seed: int, group_id: str) -> str:
    return hashlib.sha256(f"{seed}\0{group_id}".encode("utf-8")).hexdigest()


def assign_folds(
    outcomes: Sequence[SelfTranscriptOutcome],
    *,
    seed: int,
    n_folds: int = N_FOLDS,
) -> tuple[tuple[SelfTranscriptOutcome, ...], ...]:
    if n_folds < 2:
        raise SelfTranscriptCascadeError("cross-fitting requires at least two folds")
    by_group: dict[str, list[SelfTranscriptOutcome]] = defaultdict(list)
    seen: set[str] = set()
    for item in outcomes:
        if item.sample_id in seen:
            raise SelfTranscriptCascadeError(
                f"duplicate sample_id {item.sample_id!r}"
            )
        seen.add(item.sample_id)
        by_group[item.group_id].append(item)
    if len(by_group) < n_folds:
        raise SelfTranscriptCascadeError("fewer independent groups than folds")
    ordered = sorted(
        by_group.items(),
        key=lambda pair: (-len(pair[1]), _stable_rank(seed, pair[0]), pair[0]),
    )
    folds: list[list[SelfTranscriptOutcome]] = [[] for _ in range(n_folds)]
    for _group_id, items in ordered:
        target = min(range(n_folds), key=lambda index: (len(folds[index]), index))
        folds[target].extend(items)
    return tuple(
        tuple(sorted(fold, key=lambda item: item.sample_id)) for fold in folds
    )


@dataclass(frozen=True)
class DecisionOutcome:
    outcome: SelfTranscriptOutcome
    action: Action

    @property
    def selected_score(self) -> ItemScore:
        return (
            self.outcome.matched_score
            if self.action == USE_MATCHED
            else self.outcome.stop_score
        )

    @property
    def net_gain(self) -> int:
        return int(
            self.selected_score.exact_match - self.outcome.stop_score.exact_match
        )


def _slot_f1(scores: Sequence[ItemScore]) -> float:
    true_positives = sum(score.slot_true_positives for score in scores)
    expected = sum(score.slot_expected_total for score in scores)
    predicted = sum(score.slot_predicted_total for score in scores)
    denominator = expected + predicted
    return 2.0 * true_positives / denominator if denominator else 1.0


def _grouped_bootstrap(
    outcomes: Sequence[SelfTranscriptOutcome],
    values: Sequence[int],
    *,
    seed: int,
    n_replicates: int,
):
    by_group: dict[str, list[int]] = defaultdict(list)
    for outcome, value in zip(outcomes, values, strict=True):
        by_group[outcome.group_id].append(value)
    groups = tuple(sorted(by_group))

    def statistic(sampled_groups: Sequence[str]) -> float:
        flattened = [value for group in sampled_groups for value in by_group[group]]
        return sum(flattened) / len(flattened)

    return paired_cluster_bootstrap(
        sample_ids=groups,
        statistic=statistic,
        n_replicates=n_replicates,
        seed=seed,
        ci_level=0.90,
    )


@dataclass(frozen=True)
class PolicyMetrics:
    n_samples: int
    used: int
    stopped: int
    saved: int
    harmed: int
    net_gain: int
    tool_accuracy_net_gain: int
    slot_micro_f1_net_gain: float
    observation_contacts: int
    final_contacts: int
    new_contacts_per_sample: float
    fold_net_gains: tuple[int, ...]
    policy_ci_low: float
    policy_ci_high: float
    matched_shuffled_ci_low: float
    matched_shuffled_ci_high: float
    always_use_net_gain: int
    matched_m0_exact_gain: int
    matched_m0_tool_gain: int
    matched_shuffled_exact_gain: int
    matched_shuffled_tool_gain: int
    m0_tool_correct_count: int
    top5_gold_tool_correct_count: int


@dataclass(frozen=True)
class PolicyReport:
    state_class_counts: Mapping[str, int]
    metrics: PolicyMetrics
    gates: Mapping[str, bool]
    promotion_passed: bool
    decisions: tuple[DecisionOutcome, ...]


def evaluate_policy(
    outcomes: Sequence[SelfTranscriptOutcome],
    *,
    liveness_passed: bool,
    resend_absolute_exact_count_difference: int,
    seed: int = FOLD_SEED,
    n_folds: int = N_FOLDS,
    n_replicates: int = 10_000,
) -> PolicyReport:
    ordered = tuple(sorted(outcomes, key=lambda item: item.sample_id))
    if not ordered:
        raise SelfTranscriptCascadeError("policy evaluation requires outcomes")
    if (
        isinstance(resend_absolute_exact_count_difference, bool)
        or not isinstance(resend_absolute_exact_count_difference, int)
        or resend_absolute_exact_count_difference < 0
    ):
        raise SelfTranscriptCascadeError(
            "resend exact-count difference must be a non-negative integer"
        )
    folds = assign_folds(ordered, seed=seed, n_folds=n_folds)
    decisions: list[DecisionOutcome] = []
    fold_net: list[int] = []
    for fold_index, evaluation in enumerate(folds):
        memory = tuple(
            item
            for index, fold in enumerate(folds)
            if index != fold_index
            for item in fold
        )
        current = tuple(
            DecisionOutcome(
                item,
                decide(item.state, memory, route_available=item.route_available).action,
            )
            for item in evaluation
        )
        decisions.extend(current)
        fold_net.append(sum(item.net_gain for item in current))
    selected = tuple(sorted(decisions, key=lambda item: item.outcome.sample_id))

    used = sum(item.action == USE_MATCHED for item in selected)
    saved = sum(
        item.action == USE_MATCHED and item.outcome.delta > 0 for item in selected
    )
    harmed = sum(
        item.action == USE_MATCHED and item.outcome.delta < 0 for item in selected
    )
    net_gain = sum(item.net_gain for item in selected)
    tool_gain = sum(
        int(item.selected_score.tool_accuracy - item.outcome.stop_score.tool_accuracy)
        for item in selected
    )
    selected_scores = tuple(item.selected_score for item in selected)
    stop_scores = tuple(item.outcome.stop_score for item in selected)
    slot_gain = _slot_f1(selected_scores) - _slot_f1(stop_scores)

    policy_bootstrap = _grouped_bootstrap(
        tuple(item.outcome for item in selected),
        tuple(item.net_gain for item in selected),
        seed=seed,
        n_replicates=n_replicates,
    )
    matched_shuffled_values = tuple(
        int(item.matched_score.exact_match - item.shuffled_score.exact_match)
        for item in ordered
    )
    matched_shuffled_bootstrap = _grouped_bootstrap(
        ordered,
        matched_shuffled_values,
        seed=seed + 1,
        n_replicates=n_replicates,
    )
    matched_m0_exact = sum(item.delta for item in ordered if item.route_available)
    matched_m0_tool = sum(
        int(item.matched_score.tool_accuracy - item.stop_score.tool_accuracy)
        for item in ordered
        if item.route_available
    )
    matched_shuffled_exact = sum(matched_shuffled_values)
    matched_shuffled_tool = sum(
        int(item.matched_score.tool_accuracy - item.shuffled_score.tool_accuracy)
        for item in ordered
    )
    always_net = matched_m0_exact
    m0_tool_correct = sum(int(item.stop_score.tool_accuracy) for item in ordered)
    top5_correct = sum(item.top5_gold_tool_correct for item in ordered)
    state_counts = Counter(
        json.dumps(item.state.detailed_key, separators=(",", ":"))
        for item in ordered
    )
    non_dominant = len(ordered) - max(state_counts.values())

    gates = {
        "liveness": liveness_passed,
        "top5_information_gain": (
            top5_correct >= m0_tool_correct + MIN_INFORMATION_GAIN
        ),
        "matched_vs_m0_exact": matched_m0_exact >= MIN_INFORMATION_GAIN,
        "matched_vs_m0_tool": matched_m0_tool >= MIN_INFORMATION_GAIN,
        "matched_vs_shuffled_exact": (
            matched_shuffled_exact >= MIN_INFORMATION_GAIN
        ),
        "matched_vs_shuffled_tool": (
            matched_shuffled_tool >= MIN_INFORMATION_GAIN
        ),
        "matched_vs_shuffled_positive_ci90_lower": (
            matched_shuffled_bootstrap.ci_low > 0.0
        ),
        "both_actions": 0 < used < len(ordered),
        "use_range": MIN_USED <= used <= MAX_USED,
        "policy_saved_minimum": saved >= MIN_POLICY_SAVES,
        "policy_harm_maximum": harmed <= MAX_POLICY_HARMS,
        "policy_net_gain": net_gain >= MIN_POLICY_NET_GAIN,
        "policy_gain_exceeds_resend_floor": (
            net_gain > resend_absolute_exact_count_difference
        ),
        "policy_positive_ci90_lower": policy_bootstrap.ci_low > 0.0,
        "policy_tool_accuracy_nonnegative": tool_gain >= 0,
        "policy_slot_micro_f1_nonnegative": slot_gain >= 0.0,
        "every_fold_nonnegative": all(value >= 0 for value in fold_net),
        "positive_fold_count": (
            sum(value > 0 for value in fold_net) >= MIN_POSITIVE_FOLDS
        ),
        "policy_at_least_always_use_gain": net_gain >= always_net,
        "policy_fewer_final_contacts": used < sum(
            item.route_available for item in ordered
        ),
        "state_liveness": len(state_counts) >= 2
        and non_dominant >= MIN_NON_DOMINANT_STATE_SAMPLES,
    }
    metrics = PolicyMetrics(
        n_samples=len(ordered),
        used=used,
        stopped=len(ordered) - used,
        saved=saved,
        harmed=harmed,
        net_gain=net_gain,
        tool_accuracy_net_gain=tool_gain,
        slot_micro_f1_net_gain=slot_gain,
        observation_contacts=len(ordered),
        final_contacts=used,
        new_contacts_per_sample=1.0 + used / len(ordered),
        fold_net_gains=tuple(fold_net),
        policy_ci_low=policy_bootstrap.ci_low,
        policy_ci_high=policy_bootstrap.ci_high,
        matched_shuffled_ci_low=matched_shuffled_bootstrap.ci_low,
        matched_shuffled_ci_high=matched_shuffled_bootstrap.ci_high,
        always_use_net_gain=always_net,
        matched_m0_exact_gain=matched_m0_exact,
        matched_m0_tool_gain=matched_m0_tool,
        matched_shuffled_exact_gain=matched_shuffled_exact,
        matched_shuffled_tool_gain=matched_shuffled_tool,
        m0_tool_correct_count=m0_tool_correct,
        top5_gold_tool_correct_count=top5_correct,
    )
    return PolicyReport(
        state_class_counts=dict(sorted(state_counts.items())),
        metrics=metrics,
        gates=gates,
        promotion_passed=all(gates.values()),
        decisions=selected,
    )


__all__ = [
    "EXPERIMENT_ID",
    "RETRIEVER_POLICY_ID",
    "SELF_TRANSCRIPT_INSTRUCTION",
    "STOP_M0",
    "USE_MATCHED",
    "DecisionOutcome",
    "EvidenceRetriever",
    "EvidenceRoute",
    "LivenessReceipt",
    "LivenessReport",
    "MemoryDecision",
    "ObservationRecord",
    "PolicyMetrics",
    "PolicyReport",
    "SelfTranscriptCascadeError",
    "SelfTranscriptOutcome",
    "SelfTranscriptState",
    "TranscriptParse",
    "assign_folds",
    "authorize_use_phase",
    "build_same_tier_derangement",
    "decide",
    "evaluate_liveness",
    "evaluate_policy",
    "extract_runtime_state",
    "retrieve_evidence",
    "validate_self_transcript",
]
