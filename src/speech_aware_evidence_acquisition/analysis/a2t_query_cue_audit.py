"""MF-1: the Audio2Tool QUERY-CUE AUDIT (model-free, zero contacts).

Authority: ``docs/readiness/2026-09-05-a2t-query-cue-audit-v1-preregistration.md``
(sections 2 to 4) and ``docs/readiness/2026-09-05-three-dimension-experiment-
program.md`` section 3 (MF-1) and section 5 (the evolution loop's targets).
Exposure row: ``SAEA-A2T-MF-QUERY-CUE-AUDIT-V1``.

The question. A2T-ORG-1 landed HARMFUL: telling the frozen core which DOMAIN a
tool belongs to moved cross-domain twin misses (621 -> 521) into same-domain
ones (898 -> 1,118) and cost 3.23 points. A2T-ORG-2 would instead rewrite the
two twins' DESCRIPTIONS so that they contrast. A rewritten description can only
help if the spoken query itself carries a cue that separates the two tools.
This module measures that ceiling from construction-legal text alone, before
any rollout is spent, and names the pairs that are label noise from the
model's point of view.

Everything here is pure Python standard library. No model, tokenizer,
embedder, retriever, scorer, network, GPU or audio contact of any kind: the
inputs are construction-pool query strings with their gold tool names, the
pinned ``tools_registry.csv`` rows, and confusion counts a caller has already
read from SEALED per-row official scores.

The four measurements, one per preregistration section 3:

1. :func:`separability` -- the query separability CEILING. A bag-of-words
   MULTINOMIAL NAIVE BAYES classifier (a linear model in bag-of-words
   features, add-one smoothed, with UNIFORM class priors so the number
   answers "does the query carry a cue" rather than "can the prior be
   exploited"), 5-fold cross-validated with folds GROUPED BY ``query_idx`` so
   no block's re-renderings straddle a fold boundary. Reported as accuracy,
   with balanced accuracy and the majority-class rate beside it, plus the two
   per-token log-odds lists (top 15 each side).
2. :func:`description_cue` -- for each side, the share of its construction
   queries carrying at least one content token of its OWN registry
   description/signature, against the share carrying one of the TWIN's. The
   pair's gap is the mean of the two sides' differences, in points.
3. :func:`domain_cue` -- for a cross-domain pair, the share of each side's
   queries naming a device or context word of that side's gold domain, from
   the fixed, mutually disjoint word lists in :data:`DOMAIN_CUE_WORDS`.
4. The sealed-error cross-check is supplied by the caller as per-ordered-pair
   miss counts and is carried through :func:`audit_pair` unchanged, so every
   ceiling is stated against the actual error mass it could address.

:func:`decide` applies the preregistered rule in the order it was written
(TARGET, then DOMAIN-ONLY, then LABEL NOISE, then UNCERTAIN), with one
addition that is a refusal rather than a verdict: a pair whose either side has
fewer than :data:`MIN_SIDE_UNITS` construction units or
:data:`MIN_SIDE_BLOCKS` distinct blocks is INSUFFICIENT-DATA, because a
5-fold grouped classifier on three queries measures nothing. Those pairs are
reported with their error mass and are never counted as TARGET.
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

AUDIT_POLICY_ID = "saea-a2t-query-cue-audit-v1"

#: Decision labels, preregistration section 4 plus the data-sufficiency refusal.
TARGET = "TARGET"
DOMAIN_ONLY = "DOMAIN-ONLY"
LABEL_NOISE = "LABEL-NOISE"
UNCERTAIN = "UNCERTAIN"
INSUFFICIENT_DATA = "INSUFFICIENT-DATA"

#: Preregistered thresholds (section 4), fixed before the first read.
SEPARABILITY_TARGET = 0.80
SEPARABILITY_LABEL_NOISE = 0.65
DESCRIPTION_GAP_POINTS = 20.0
DOMAIN_COVERAGE_MIN = 0.60

#: Data-sufficiency floor for a 5-fold grouped measurement.
MIN_SIDE_UNITS = 5
MIN_SIDE_BLOCKS = 5

#: Fold count and seed. The seed is the program's statistics seed, so every
#: model-free draw in this campaign shares one constant.
FOLDS = 5
FOLD_SEED = 20260903

#: A token must appear at least this many times across the pair before it may
#: enter a published log-odds list, so a single stray word cannot top it.
LOG_ODDS_MIN_COUNT = 3
LOG_ODDS_TOP_N = 15

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_CAMEL_RE = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])")

#: Function words dropped when a DESCRIPTION or SIGNATURE is reduced to
#: content tokens. Deliberately short: "on", "off", "up" and "down" are task
#: content on this carrier and are NOT dropped. The classifier of
#: :func:`separability` uses every token and never consults this set.
STOPWORDS = frozenset(
    """
    a an the this that these those and or but if then else for of to in into with
    without from by at as is are was were be been being do does did done can could
    will would shall should may might must have has had it its their there here
    what which who whom whose when where why how all any both each few more most
    other some such no nor not only own same so than too very just now also
    please my your our his her me you we they them us
    """.split()
)

#: Type names and generic identifier fragments carry no discriminating
#: content, so they are dropped from a tool's description/signature tokens.
SIGNATURE_NOISE = frozenset(
    """
    string int integer float double bool boolean list map dict object none null
    optional value values param params arg args type types id ids device group
    target enum time date datetime number
    """.split()
)

#: Fixed, MUTUALLY DISJOINT domain cue lists (preregistration section 3.3).
#: A word a caller could plausibly say in two domains is not a domain cue, so
#: any term shared between two lists is refused by :func:`_assert_disjoint`
#: rather than silently counted for both. "garage", "camera", "fan", "lock",
#: "door", "window", "alarm", "battery" and "volume" are therefore absent from
#: every list: each names a real device in more than one domain of this
#: registry, and counting them would manufacture domain coverage.
DOMAIN_CUE_WORDS: Mapping[str, frozenset[str]] = {
    "smart_home": frozenset(
        """
        home house household apartment flat room rooms bedroom bedrooms living
        livingroom kitchen bathroom hallway hallways hall basement attic porch
        patio yard garden nursery upstairs downstairs thermostat lamp lamps bulb
        bulbs chandelier sconce dishwasher washer dryer oven microwave fridge
        refrigerator vacuum roomba doorbell router wifi blinds curtains shades
        sprinkler humidifier dehumidifier purifier kettle hub nightlight
        television tv soundbar den study lounge
        """.split()
    ),
    "smart_car": frozenset(
        """
        car cars vehicle vehicles cabin seat seats driver drivers driving drive
        trunk frunk windshield wiper wipers mirror mirrors steering wheel tesla
        gear odometer tire tires tyre tyres tpms sunroof moonroof valet dashboard
        hvac defrost defroster autopilot charging charger supercharger ev
        mileage parked parking road highway commute engine ignition horn
        """.split()
    ),
    "wearables": frozenset(
        """
        watch watches smartwatch wrist wearable band tracker workout workouts
        exercise treadmill jog jogging cycling steps stride heartrate hrv pulse
        bpm sleep sleeping calories hydration stress spo2 ecg mindfulness
        breathing recovery fitness
        """.split()
    ),
}

#: Head words that put a tool in the LIGHTING family. The family is DERIVED
#: from the registry rather than asserted: the campaign's "the lighting
#: cluster is one target" rule needs a membership test a reader can re-run.
LIGHTING_MARKERS = frozenset({"light", "lights", "lighting", "brightness", "dimmable", "kelvin"})


def _assert_disjoint(lists: Mapping[str, frozenset[str]]) -> None:
    seen: dict[str, str] = {}
    for domain, words in sorted(lists.items()):
        for word in sorted(words):
            if word in seen:
                raise ValueError(
                    f"domain cue word {word!r} appears in both {seen[word]!r} and {domain!r}"
                )
            seen[word] = domain


_assert_disjoint(DOMAIN_CUE_WORDS)


# ---------------------------------------------------------------------------
# Text reduction
# ---------------------------------------------------------------------------


def tokenize(text: str) -> tuple[str, ...]:
    """Lowercased alphanumeric tokens, in order. Used by the classifier, which
    sees EVERY token including function words."""

    return tuple(_TOKEN_RE.findall(text.lower()))


def content_tokens(text: str) -> frozenset[str]:
    """Tokens of ``text`` with function words and one-character tokens removed."""

    return frozenset(
        token for token in tokenize(text) if len(token) > 1 and token not in STOPWORDS
    )


def camel_split(identifier: str) -> tuple[str, ...]:
    """``setColorTemperature`` -> ``('set', 'color', 'temperature')``; a
    trailing ``_home`` / ``_diag`` suffix splits on the underscore first."""

    parts: list[str] = []
    for chunk in identifier.split("_"):
        parts.extend(piece.lower() for piece in _CAMEL_RE.findall(chunk))
    return tuple(part for part in parts if part)


def signature_argument_names(signature: str) -> tuple[str, ...]:
    """The ARGUMENT KEY names of a registry signature, types discarded.

    ``setLighting(deviceId: String, state: OnOff, level: Int?)`` ->
    ``('deviceId', 'state', 'level')``.
    """

    start = signature.find("(")
    end = signature.rfind(")")
    if start < 0 or end <= start:
        return ()
    inner = signature[start + 1 : end]
    names: list[str] = []
    depth = 0
    current: list[str] = []
    for character in inner:
        if character in "<([{":
            depth += 1
        elif character in ">)]}":
            depth -= 1
        if character == "," and depth == 0:
            names.append("".join(current))
            current = []
        else:
            current.append(character)
    names.append("".join(current))
    out: list[str] = []
    for name in names:
        head = name.split(":")[0].strip()
        if head:
            out.append(head)
    return tuple(out)


def tool_description_tokens(row: Mapping[str, str]) -> frozenset[str]:
    """A tool's content tokens: its description, its camel-split NAME and the
    camel-split ARGUMENT KEYS of its signature, minus type noise."""

    tokens = set(content_tokens(str(row.get("description", ""))))
    tokens.update(camel_split(str(row.get("tool_name", ""))))
    for argument in signature_argument_names(str(row.get("signature", ""))):
        tokens.update(camel_split(argument))
    return frozenset(
        token for token in tokens if len(token) > 1 and token not in SIGNATURE_NOISE
    )


def lighting_family(registry: Mapping[str, Mapping[str, str]]) -> frozenset[str]:
    """Every registry tool whose description, name or signature carries a
    lighting head word. Derived, so a reader can re-run the membership test."""

    family: set[str] = set()
    for name, row in registry.items():
        tokens = set(content_tokens(str(row.get("description", ""))))
        tokens.update(camel_split(name))
        for argument in signature_argument_names(str(row.get("signature", ""))):
            tokens.update(camel_split(argument))
        if tokens & LIGHTING_MARKERS:
            family.add(name)
    return frozenset(family)


# ---------------------------------------------------------------------------
# Population records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryRow:
    """One construction unit reduced to what this audit may read: the gold
    primary tool, the leakage-carrying ``query_idx`` block, and the invocation
    text. No sample id, no audio, no argument gold."""

    tool_name: str
    query_idx: int
    text: str


@dataclass(frozen=True)
class PairSpec:
    """One audited twin pair. ``left`` and ``right`` are tool-name tuples so a
    CLUSTER (the lighting family) can stand on one side."""

    pair_id: str
    left: tuple[str, ...]
    right: tuple[str, ...]
    origin: str

    @property
    def tools(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.left) | set(self.right)))


# ---------------------------------------------------------------------------
# 1. Separability ceiling
# ---------------------------------------------------------------------------


def fold_of_block(block: int, seed: int = FOLD_SEED, folds: int = FOLDS) -> int:
    """Deterministic fold for one ``query_idx`` block.

    A seeded per-block draw rather than ``block % folds``: block ids are
    corpus-assigned and adjacent ids share scenarios, so the modulus would
    correlate a fold with the corpus's own ordering.
    """

    return random.Random(f"{seed}:{block}").randrange(folds)


def _log_odds(left: Counter, right: Counter, vocabulary: Sequence[str]) -> dict[str, float]:
    """Add-one smoothed per-token log odds ``log P(t|left) - log P(t|right)``."""

    size = len(vocabulary)
    left_total = sum(left.values()) + size
    right_total = sum(right.values()) + size
    return {
        token: math.log((left[token] + 1) / left_total)
        - math.log((right[token] + 1) / right_total)
        for token in vocabulary
    }


@dataclass(frozen=True)
class Separability:
    accuracy: float
    balanced_accuracy: float
    majority_class_rate: float
    folds_used: int
    scored_left: int
    scored_right: int
    correct_left: int
    correct_right: int
    top_tokens_left: tuple[tuple[str, float], ...]
    top_tokens_right: tuple[tuple[str, float], ...]

    @property
    def imbalance_flag(self) -> bool:
        """True when accuracy does not beat the trivial majority-class rate.

        Accuracy is the preregistered decision statistic and is NOT overridden
        here, but on a pair whose two sides differ by an order of magnitude in
        row count it can clear 0.80 while the small side is never recovered
        (``setLighting`` 90 rows against ``setLightState`` 5: accuracy 0.926,
        balanced accuracy 0.489). Every flagged pair is reported so that a
        reader, and the evolution loop, can see which ceilings are real.
        """

        return self.accuracy <= self.majority_class_rate

    def as_json(self) -> dict[str, object]:
        return {
            "accuracy": round(self.accuracy, 4),
            "balanced_accuracy": round(self.balanced_accuracy, 4),
            "majority_class_rate": round(self.majority_class_rate, 4),
            "imbalance_flag": self.imbalance_flag,
            "folds_used": self.folds_used,
            "scored_left": self.scored_left,
            "scored_right": self.scored_right,
            "correct_left": self.correct_left,
            "correct_right": self.correct_right,
            "top_tokens_left": [
                {"token": token, "log_odds": round(value, 4)}
                for token, value in self.top_tokens_left
            ],
            "top_tokens_right": [
                {"token": token, "log_odds": round(value, 4)}
                for token, value in self.top_tokens_right
            ],
        }


def separability(
    left: Sequence[QueryRow],
    right: Sequence[QueryRow],
    *,
    seed: int = FOLD_SEED,
    folds: int = FOLDS,
) -> Separability:
    """The 5-fold block-grouped bag-of-words separability ceiling.

    Uniform class priors: a query is assigned to ``left`` when the summed
    per-token log odds is positive, and ties go to the side with more training
    rows (deterministic, and stated). Folds whose training half is missing a
    class are skipped and reported through ``folds_used``.
    """

    documents = [(row, 0) for row in left] + [(row, 1) for row in right]
    if not documents:
        raise ValueError("separability: no documents")
    assignments = {
        row.query_idx: fold_of_block(row.query_idx, seed=seed, folds=folds)
        for row, _ in documents
    }
    correct = [0, 0]
    scored = [0, 0]
    folds_used = 0
    for fold in range(folds):
        train = [(row, side) for row, side in documents if assignments[row.query_idx] != fold]
        test = [(row, side) for row, side in documents if assignments[row.query_idx] == fold]
        if not test:
            continue
        counts: list[Counter] = [Counter(), Counter()]
        rows_per_side = [0, 0]
        for row, side in train:
            counts[side].update(tokenize(row.text))
            rows_per_side[side] += 1
        if rows_per_side[0] == 0 or rows_per_side[1] == 0:
            continue
        folds_used += 1
        vocabulary = sorted(set(counts[0]) | set(counts[1]))
        weights = _log_odds(counts[0], counts[1], vocabulary)
        default = 0 if rows_per_side[0] >= rows_per_side[1] else 1
        for row, side in test:
            score = sum(weights.get(token, 0.0) for token in tokenize(row.text))
            if score > 0:
                predicted = 0
            elif score < 0:
                predicted = 1
            else:
                predicted = default
            scored[side] += 1
            if predicted == side:
                correct[side] += 1
    total = scored[0] + scored[1]
    accuracy = (correct[0] + correct[1]) / total if total else 0.0
    recalls = [correct[side] / scored[side] if scored[side] else 0.0 for side in (0, 1)]
    balanced = sum(recalls) / 2
    majority = max(scored) / total if total else 0.0

    whole: list[Counter] = [Counter(), Counter()]
    for row, side in documents:
        whole[side].update(tokenize(row.text))
    vocabulary = sorted(set(whole[0]) | set(whole[1]))
    weights = _log_odds(whole[0], whole[1], vocabulary)
    eligible = [
        token
        for token in vocabulary
        if whole[0][token] + whole[1][token] >= LOG_ODDS_MIN_COUNT
    ]
    ranked_left = sorted(eligible, key=lambda token: (-weights[token], token))
    ranked_right = sorted(eligible, key=lambda token: (weights[token], token))
    return Separability(
        accuracy=accuracy,
        balanced_accuracy=balanced,
        majority_class_rate=majority,
        folds_used=folds_used,
        scored_left=scored[0],
        scored_right=scored[1],
        correct_left=correct[0],
        correct_right=correct[1],
        top_tokens_left=tuple(
            (token, weights[token]) for token in ranked_left[:LOG_ODDS_TOP_N]
        ),
        top_tokens_right=tuple(
            (token, weights[token]) for token in ranked_right[:LOG_ODDS_TOP_N]
        ),
    )


# ---------------------------------------------------------------------------
# 2. Description-cue coverage
# ---------------------------------------------------------------------------


def _share(rows: Sequence[QueryRow], vocabulary: frozenset[str]) -> float:
    if not rows:
        return 0.0
    hits = sum(1 for row in rows if content_tokens(row.text) & vocabulary)
    return hits / len(rows)


def description_cue(
    left: Sequence[QueryRow],
    right: Sequence[QueryRow],
    left_tokens: frozenset[str],
    right_tokens: frozenset[str],
) -> dict[str, object]:
    """Own-description against twin-description coverage, per side and pooled.

    ``gap_points`` is the mean of the two sides' own-minus-twin differences in
    PERCENTAGE POINTS, which is the quantity the preregistered 20-point rule
    reads. The EXCLUSIVE variant repeats the measurement with each side's
    shared tokens removed and is reported as the sharper diagnostic.
    """

    left_only = left_tokens - right_tokens
    right_only = right_tokens - left_tokens
    own_left = _share(left, left_tokens)
    twin_left = _share(left, right_tokens)
    own_right = _share(right, right_tokens)
    twin_right = _share(right, left_tokens)
    gap_left = (own_left - twin_left) * 100.0
    gap_right = (own_right - twin_right) * 100.0
    excl_left = (_share(left, left_only) - _share(left, right_only)) * 100.0
    excl_right = (_share(right, right_only) - _share(right, left_only)) * 100.0
    return {
        "own_share_left": round(own_left, 4),
        "twin_share_left": round(twin_left, 4),
        "own_share_right": round(own_right, 4),
        "twin_share_right": round(twin_right, 4),
        "gap_points_left": round(gap_left, 2),
        "gap_points_right": round(gap_right, 2),
        "gap_points": round((gap_left + gap_right) / 2, 2),
        "gap_points_min_side": round(min(gap_left, gap_right), 2),
        "exclusive_gap_points": round((excl_left + excl_right) / 2, 2),
        "exclusive_tokens_left": sorted(left_only),
        "exclusive_tokens_right": sorted(right_only),
        "shared_tokens": sorted(left_tokens & right_tokens),
    }


# ---------------------------------------------------------------------------
# 3. Domain-cue coverage
# ---------------------------------------------------------------------------


def domain_cue(
    left: Sequence[QueryRow],
    right: Sequence[QueryRow],
    left_domain: str,
    right_domain: str,
) -> dict[str, object]:
    """Share of each side's queries naming a device or context word of that
    side's own gold domain. Not applicable to a same-domain pair, where the
    statistic has no meaning."""

    if left_domain == right_domain:
        return {"applicable": False, "reason": "same-domain pair"}
    left_words = DOMAIN_CUE_WORDS.get(left_domain, frozenset())
    right_words = DOMAIN_CUE_WORDS.get(right_domain, frozenset())
    coverage_left = _share(left, left_words)
    coverage_right = _share(right, right_words)
    return {
        "applicable": True,
        "left_domain": left_domain,
        "right_domain": right_domain,
        "coverage_left": round(coverage_left, 4),
        "coverage_right": round(coverage_right, 4),
        "coverage": round((coverage_left + coverage_right) / 2, 4),
        "coverage_min_side": round(min(coverage_left, coverage_right), 4),
    }


# ---------------------------------------------------------------------------
# 4. The preregistered decision
# ---------------------------------------------------------------------------


def decide(
    *,
    units_left: int,
    units_right: int,
    blocks_left: int,
    blocks_right: int,
    accuracy: float,
    description_gap_points: float,
    cross_domain: bool,
    domain_coverage: float | None,
) -> str:
    """Preregistration section 4, applied in the order it was written."""

    if (
        min(units_left, units_right) < MIN_SIDE_UNITS
        or min(blocks_left, blocks_right) < MIN_SIDE_BLOCKS
    ):
        return INSUFFICIENT_DATA
    if accuracy >= SEPARABILITY_TARGET and description_gap_points >= DESCRIPTION_GAP_POINTS:
        return TARGET
    if (
        cross_domain
        and accuracy >= SEPARABILITY_TARGET
        and domain_coverage is not None
        and domain_coverage >= DOMAIN_COVERAGE_MIN
    ):
        return DOMAIN_ONLY
    if accuracy < SEPARABILITY_LABEL_NOISE:
        return LABEL_NOISE
    return UNCERTAIN


# ---------------------------------------------------------------------------
# Per-pair assembly
# ---------------------------------------------------------------------------


def audit_pair(
    spec: PairSpec,
    rows_by_tool: Mapping[str, Sequence[QueryRow]],
    registry: Mapping[str, Mapping[str, str]],
    miss_counts: Mapping[tuple[str, str], int],
    *,
    seed: int = FOLD_SEED,
) -> dict[str, object]:
    """Every preregistered measurement for one pair, plus its decision."""

    for tool in spec.tools:
        if tool not in registry:
            raise ValueError(f"{spec.pair_id}: tool {tool!r} is not in tools_registry.csv")
    left = [row for tool in spec.left for row in rows_by_tool.get(tool, ())]
    right = [row for tool in spec.right for row in rows_by_tool.get(tool, ())]
    blocks_left = {row.query_idx for row in left}
    blocks_right = {row.query_idx for row in right}
    left_domains = sorted({str(registry[tool]["domain"]) for tool in spec.left})
    right_domains = sorted({str(registry[tool]["domain"]) for tool in spec.right})
    cross_domain = not (set(left_domains) & set(right_domains))

    left_tokens = frozenset().union(
        *(tool_description_tokens(registry[tool]) for tool in spec.left)
    )
    right_tokens = frozenset().union(
        *(tool_description_tokens(registry[tool]) for tool in spec.right)
    )

    left_to_right = sum(
        miss_counts.get((gold, predicted), 0) for gold in spec.left for predicted in spec.right
    )
    right_to_left = sum(
        miss_counts.get((gold, predicted), 0) for gold in spec.right for predicted in spec.left
    )

    enough = (
        min(len(left), len(right)) >= MIN_SIDE_UNITS
        and min(len(blocks_left), len(blocks_right)) >= MIN_SIDE_BLOCKS
    )
    separability_block: dict[str, object] | None = None
    accuracy = 0.0
    if enough:
        result = separability(left, right, seed=seed)
        separability_block = result.as_json()
        accuracy = result.accuracy

    description = description_cue(left, right, left_tokens, right_tokens)
    domain = domain_cue(
        left,
        right,
        left_domains[0] if len(left_domains) == 1 else "|".join(left_domains),
        right_domains[0] if len(right_domains) == 1 else "|".join(right_domains),
    )
    coverage = float(domain["coverage"]) if domain.get("applicable") else None
    decision = decide(
        units_left=len(left),
        units_right=len(right),
        blocks_left=len(blocks_left),
        blocks_right=len(blocks_right),
        accuracy=accuracy,
        description_gap_points=float(description["gap_points"]),
        cross_domain=cross_domain,
        domain_coverage=coverage,
    )
    return {
        "pair_id": spec.pair_id,
        "origin": spec.origin,
        "left_tools": list(spec.left),
        "right_tools": list(spec.right),
        "left_domains": left_domains,
        "right_domains": right_domains,
        "class": "cross_domain" if cross_domain else "same_domain",
        "construction_units_left": len(left),
        "construction_units_right": len(right),
        "construction_blocks_left": len(blocks_left),
        "construction_blocks_right": len(blocks_right),
        "separability": separability_block,
        "description_cue": description,
        "domain_cue": domain,
        "sealed_misses_left_to_right": left_to_right,
        "sealed_misses_right_to_left": right_to_left,
        "sealed_miss_mass": left_to_right + right_to_left,
        "decision": decision,
    }


# ---------------------------------------------------------------------------
# Pair discovery and target assembly
# ---------------------------------------------------------------------------


def discovered_pairs(
    miss_counts: Mapping[tuple[str, str], int],
    registry: Mapping[str, Mapping[str, str]],
    *,
    minimum: int = 5,
) -> tuple[tuple[str, str], ...]:
    """Unordered tool pairs reaching ``minimum`` sealed misses in at least one
    direction, both names registry-valid, ranked by summed mass."""

    unordered: Counter = Counter()
    for (gold, predicted), count in miss_counts.items():
        if gold not in registry or predicted not in registry or gold == predicted:
            continue
        if count < minimum:
            continue
        unordered[tuple(sorted((gold, predicted)))] += count
    return tuple(sorted(unordered, key=lambda pair: (-unordered[pair], pair)))


def build_targets(
    audited: Sequence[Mapping[str, object]],
    miss_counts: Mapping[tuple[str, str], int],
    lighting: frozenset[str],
    *,
    maximum: int = 12,
) -> dict[str, object]:
    """Disjoint target tool sets from the TARGET pairs.

    A tool belongs to at most one target: TARGET pairs are merged as an
    undirected graph, the whole LIGHTING family present among them is
    pre-merged into one node (the evolution loop's "the lighting cluster is
    one target" rule), and the resulting components are ranked by addressable
    error mass. ``strict_mass`` counts only the ordered directions the audited
    TARGET pairs actually name, each ONCE (so a cluster pair and the individual
    pairs inside it cannot double count); ``component_mass`` counts every
    sealed miss whose gold AND predicted tool both sit inside the target's tool
    set, including intra-set confusions no audited pair named.
    """

    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[max(a, b)] = min(a, b)

    target_pairs = [row for row in audited if row["decision"] == TARGET]
    tools: set[str] = set()
    for row in target_pairs:
        tools.update(str(tool) for tool in row["left_tools"])
        tools.update(str(tool) for tool in row["right_tools"])
    for tool in sorted(tools):
        find(tool)
    lighting_members = sorted(tools & lighting)
    for tool in lighting_members[1:]:
        union(lighting_members[0], tool)
    for row in target_pairs:
        members = [str(tool) for tool in row["left_tools"]] + [
            str(tool) for tool in row["right_tools"]
        ]
        for tool in members[1:]:
            union(members[0], tool)

    groups: dict[str, set[str]] = defaultdict(set)
    for tool in sorted(tools):
        groups[find(tool)].add(tool)

    directions_by_group: dict[str, set[tuple[str, str]]] = defaultdict(set)
    pairs_by_group: dict[str, list[str]] = defaultdict(list)
    for row in target_pairs:
        root = find(str(row["left_tools"][0]))
        directions_by_group[root] |= pair_directions(row)
        pairs_by_group[root].append(str(row["pair_id"]))

    out: list[dict[str, object]] = []
    for root, members in sorted(groups.items()):
        component = sum(
            count
            for (gold, predicted), count in miss_counts.items()
            if gold in members and predicted in members
        )
        strict = sum(
            miss_counts.get(direction, 0)
            for direction in sorted(directions_by_group[root])
        )
        out.append(
            {
                "target_id": ("lighting" if members & lighting else min(members)),
                "tools": sorted(members),
                "pairs": sorted(pairs_by_group[root]),
                "strict_mass": int(strict),
                "component_mass": int(component),
            }
        )
    out.sort(key=lambda row: (-int(row["strict_mass"]), str(row["target_id"])))
    kept = out[:maximum]
    dropped = out[maximum:]
    assignment: Counter = Counter()
    for row in kept:
        for tool in row["tools"]:
            assignment[str(tool)] += 1
    duplicated = sorted(tool for tool, count in assignment.items() if count > 1)
    if duplicated:
        raise ValueError(f"targets are not disjoint on {duplicated}")
    return {
        "targets": kept,
        "dropped_over_cap": dropped,
        "maximum": maximum,
        "strict_mass_total": sum(int(row["strict_mass"]) for row in kept),
        "component_mass_total": sum(int(row["component_mass"]) for row in kept),
        "tool_count": sum(len(row["tools"]) for row in kept),
    }


def pair_directions(row: Mapping[str, object]) -> frozenset[tuple[str, str]]:
    """Every ordered ``(gold, predicted)`` direction one audited pair covers.

    A CLUSTER pair (``setColor+setColorTemperature+setLighting`` against
    ``setAmbientLighting``) covers the same directions as the individual pairs
    beside it, so mass must be summed over the DIRECTION set rather than over
    the pair rows: adding both would count the same sealed miss twice.
    """

    left = [str(tool) for tool in row["left_tools"]]
    right = [str(tool) for tool in row["right_tools"]]
    return frozenset(
        [(gold, predicted) for gold in left for predicted in right]
        + [(gold, predicted) for gold in right for predicted in left]
    )


def class_mass(
    audited: Iterable[Mapping[str, object]],
    decision: str,
    miss_counts: Mapping[tuple[str, str], int],
) -> int:
    """Sealed miss mass of the pairs carrying ``decision``, each ordered
    direction counted ONCE."""

    directions: set[tuple[str, str]] = set()
    for row in audited:
        if row["decision"] == decision:
            directions |= pair_directions(row)
    return sum(miss_counts.get(direction, 0) for direction in sorted(directions))


# ---------------------------------------------------------------------------
# The audited pair set and the whole-population run
# ---------------------------------------------------------------------------

#: The pairs the three official-population verdicts and the A2T-ORG-1 verdict
#: named, plus the lighting CLUSTER the evolution loop treats as one target.
#: Every other audited pair is DISCOVERED from the sealed miss table by
#: :func:`discovered_pairs` and carries origin ``sealed-miss-table``.
NAMED_PAIRS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("rebootDevice",), ("restartDevice",)),
    (("setSecurityMode",), ("armSecuritySystem",)),
    (("activateScene",), ("activateRoutine",)),
    (("getApplianceState",), ("getApplianceStatus",)),
    (("setLighting",), ("setLightState",)),
    (("getAirQuality",), ("getAirQuality_diag",)),
    (("getNetworkHealth",), ("runNetworkSpeedTest",)),
    (("setColor", "setColorTemperature", "setLighting"), ("setAmbientLighting",)),
    (("setFanMode",), ("setFanSpeed",)),
    (("setGarageDoor",), ("setGarageOpener",)),
    (("setVolume",), ("adjustVolume",)),
    (("findMyDevice",), ("findPairedPhone",)),
    (("getLockState",), ("getLockStatus",)),
    (("controlPlayback_home",), ("controlPlayback",)),
)


def pair_id(left: Sequence[str], right: Sequence[str]) -> str:
    return f"{'+'.join(sorted(left))}|{'+'.join(sorted(right))}"


def group_rows(rows: Iterable[QueryRow]) -> dict[str, list[QueryRow]]:
    """Construction rows keyed by gold primary tool."""

    out: dict[str, list[QueryRow]] = defaultdict(list)
    for row in rows:
        out[row.tool_name].append(row)
    return dict(out)


def assemble_pairs(
    miss_counts: Mapping[tuple[str, str], int],
    registry: Mapping[str, Mapping[str, str]],
    *,
    minimum: int = 5,
) -> tuple[PairSpec, ...]:
    """The named pairs first, then every additional pair the sealed miss table
    shows at least ``minimum`` times, deduplicated on the unordered tool sets."""

    specs: list[PairSpec] = []
    seen: set[frozenset[frozenset[str]]] = set()
    for left, right in NAMED_PAIRS:
        key = frozenset({frozenset(left), frozenset(right)})
        seen.add(key)
        specs.append(
            PairSpec(
                pair_id=pair_id(left, right),
                left=tuple(sorted(left)),
                right=tuple(sorted(right)),
                origin="named",
            )
        )
    for left_tool, right_tool in discovered_pairs(miss_counts, registry, minimum=minimum):
        key = frozenset({frozenset({left_tool}), frozenset({right_tool})})
        if key in seen:
            continue
        seen.add(key)
        specs.append(
            PairSpec(
                pair_id=pair_id((left_tool,), (right_tool,)),
                left=(left_tool,),
                right=(right_tool,),
                origin="sealed-miss-table",
            )
        )
    return tuple(specs)


def audit_population(
    rows: Sequence[QueryRow],
    registry: Mapping[str, Mapping[str, str]],
    miss_counts: Mapping[tuple[str, str], int],
    specs: Sequence[PairSpec],
    *,
    seed: int = FOLD_SEED,
    maximum_targets: int = 12,
) -> dict[str, object]:
    """Audit every pair against one construction population and assemble the
    disjoint target list plus the KC-A1 gate arithmetic."""

    by_tool = group_rows(rows)
    lighting = lighting_family(registry)
    audited = [audit_pair(spec, by_tool, registry, miss_counts, seed=seed) for spec in specs]
    targets = build_targets(audited, miss_counts, lighting, maximum=maximum_targets)
    total_misses = sum(miss_counts.values())
    return {
        "policy_id": AUDIT_POLICY_ID,
        "fold_seed": seed,
        "folds": FOLDS,
        "thresholds": {
            "separability_target": SEPARABILITY_TARGET,
            "separability_label_noise": SEPARABILITY_LABEL_NOISE,
            "description_gap_points": DESCRIPTION_GAP_POINTS,
            "domain_coverage_min": DOMAIN_COVERAGE_MIN,
            "min_side_units": MIN_SIDE_UNITS,
            "min_side_blocks": MIN_SIDE_BLOCKS,
        },
        "construction_units": len(rows),
        "construction_blocks": len({row.query_idx for row in rows}),
        "pairs": audited,
        "pair_count": len(audited),
        "decision_counts": dict(
            sorted(Counter(str(row["decision"]) for row in audited).items())
        ),
        "mass_by_decision": {
            decision: class_mass(audited, decision, miss_counts)
            for decision in (TARGET, DOMAIN_ONLY, LABEL_NOISE, UNCERTAIN, INSUFFICIENT_DATA)
        },
        "lighting_family": sorted(lighting),
        "targets": targets,
        "sealed_miss_total": total_misses,
    }


# ---------------------------------------------------------------------------
# Receipt assembly (the CLI ``scripts/run_a2t_query_cue_audit.py`` is I/O only)
# ---------------------------------------------------------------------------

EXPOSURE_ROW = "SAEA-A2T-MF-QUERY-CUE-AUDIT-V1"

#: The sealed comparator this audit states its ceilings against: the three
#: 2026-09-04 official-population manifests that make up the 4,000 rows KC-A1
#: is paired on. Already-consumed rows; only their SEALED per-row official
#: scores and gold tool names are read, under the inherited exposure of their
#: own flight rows.
BASELINE_RUNS: tuple[tuple[str, str], ...] = (
    ("SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1", "attempt-20260904T172609Z-t1officialpop500"),
    ("SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1", "attempt-20260904T193726Z-t258officialpop1500"),
    ("SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1", "attempt-20260904T211040Z-t3467officialpop2000"),
)

#: The fourth sealed manifest, read as a CROSS-CHECK only: A2T-ORG-1's own
#: 4,000 outputs, so each pair's ceiling can be stated against both the
#: baseline error mass and the mass the domain-grouped registry left behind.
ORG1_RUN: tuple[str, str] = (
    "SAEA-A2T-ORG1-DOMAIN-GROUPED-V1",
    "attempt-20260905T171519Z-org1groupedraw",
)

KC_A1_GATE_ROWS = 100


def sealed_miss_counts(
    runs: Sequence[tuple[str, str]], lock: Mapping[str, object], root
) -> tuple[Counter, int, list[dict[str, object]]]:
    """``(gold, predicted)`` miss counts from SEALED outputs, through the
    registered ``a2t-toolcall-official`` scorer -- gold enters exactly as it
    does when a flight finalizes, never on a runtime path."""

    from ..core.base import SCORERS
    from ..core import scorers as _scorers  # noqa: F401  (registers the scorers)

    pairs: Counter = Counter()
    total = 0
    sources: list[dict[str, object]] = []
    for run_id, attempt in runs:
        outputs = root / "runs" / run_id / attempt / f"{run_id}.outputs.jsonl"
        per_sample = SCORERS.resolve("a2t-toolcall-official")(outputs, lock, root)["per_sample"]
        misses = 0
        for row in per_sample:
            if row["tool_correct"]:
                continue
            misses += 1
            pairs[(str(row["gold_tool"]), str(row["predicted_tool"] or ""))] += 1
        total += len(per_sample)
        sources.append(
            {"run_id": run_id, "attempt": attempt, "rows": len(per_sample), "misses": misses}
        )
    return pairs, total, sources


def to_query_rows(rows: Iterable[object]) -> list[QueryRow]:
    """``A2tKbRow`` units reduced to the three fields this audit may read."""

    return [QueryRow(row.tool_name, row.query_idx, row.text) for row in rows]


def build_receipts(
    *,
    lock: Mapping[str, object],
    root,
    registry: Mapping[str, Mapping[str, str]],
    pool: Sequence[object],
    inventory: Mapping[str, object],
    exposure: Mapping[str, object],
    exposed: frozenset[str],
    partition,
    outbound_attempts: int,
    outbound_targets: Sequence[str],
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    """``(summary, per-pair table, decontamination)``, fail-closed on overlap.

    PRIMARY population = every pool unit whose ``query_idx`` BLOCK is untouched
    by the exposure union. STRICT = ``propose_partition(...).construction``,
    which additionally removes the legacy 400-block PROPOSED evaluation tier
    (a proposal, never a registered split): under the union that now also
    reserves A2T-FRESH-800, that proposal costs a further 48 % of the
    remaining units and leaves single-digit row counts on most twins, so it is
    reported BESIDE the primary rather than as it.
    """

    exposed_blocks = frozenset(
        row.query_idx for row in pool if any(sid in exposed for sid in row.sample_ids)
    )
    free = tuple(row for row in pool if row.query_idx not in exposed_blocks)
    construction = tuple(partition.construction)

    baseline_pairs, baseline_rows, baseline_sources = sealed_miss_counts(
        BASELINE_RUNS, lock, root
    )
    org1_pairs, org1_rows, org1_sources = sealed_miss_counts((ORG1_RUN,), lock, root)
    specs = assemble_pairs(baseline_pairs, registry)
    primary = audit_population(to_query_rows(free), registry, baseline_pairs, specs)
    strict = audit_population(to_query_rows(construction), registry, baseline_pairs, specs)

    org1_view = {
        str(row["pair_id"]): {
            "left_to_right": sum(
                org1_pairs.get((str(gold), str(predicted)), 0)
                for gold in row["left_tools"]
                for predicted in row["right_tools"]
            ),
            "right_to_left": sum(
                org1_pairs.get((str(gold), str(predicted)), 0)
                for gold in row["right_tools"]
                for predicted in row["left_tools"]
            ),
        }
        for row in primary["pairs"]
    }

    free_ids = {sid for row in free for sid in row.sample_ids}
    strict_ids = {sid for row in construction for sid in row.sample_ids}
    decontamination = {
        "schema": "saea-a2t-query-cue-audit-decontamination-v1",
        "exposure_row": EXPOSURE_ROW,
        "exposure_union": dict(exposure),
        "population_rule": (
            "PRIMARY = every pool unit whose query_idx BLOCK is untouched by the exposure "
            "union; STRICT = propose_partition(...).construction, which additionally removes "
            "the legacy 400-block proposed evaluation tier."
        ),
        "primary_units": len(free),
        "primary_blocks": len({row.query_idx for row in free}),
        "primary_items": len(free_ids),
        "strict_units": len(construction),
        "strict_blocks": len({row.query_idx for row in construction}),
        "strict_items": len(strict_ids),
        "exposed_sample_ids": len(exposed),
        "exposed_blocks": len(exposed_blocks),
        "primary_overlap_with_exposure_union": len(free_ids & set(exposed)),
        "strict_overlap_with_exposure_union": len(strict_ids & set(exposed)),
        "primary_block_overlap_with_exposed_blocks": len(
            {row.query_idx for row in free} & exposed_blocks
        ),
        "partition_report": dict(partition.report),
    }
    if (
        decontamination["primary_overlap_with_exposure_union"]
        or decontamination["strict_overlap_with_exposure_union"]
        or decontamination["primary_block_overlap_with_exposed_blocks"]
    ):
        raise ValueError("decontamination failed: the construction pool touches the union")

    gate = int(primary["targets"]["strict_mass_total"])
    unflagged = [
        row
        for row in primary["pairs"]
        if row["decision"] == TARGET
        and not (row["separability"] or {}).get("imbalance_flag", False)
    ]
    unflagged_mass = class_mass(unflagged, TARGET, baseline_pairs)
    summary = {
        "schema": "saea-a2t-query-cue-audit-v1",
        "generator": "scripts/run_a2t_query_cue_audit.py",
        "authority": "docs/readiness/2026-09-05-a2t-query-cue-audit-v1-preregistration.md",
        "exposure_row": EXPOSURE_ROW,
        "offline_guard": {
            "outbound_connection_attempts": outbound_attempts,
            "attempted_targets": list(outbound_targets),
        },
        "carrier_inventory": dict(inventory),
        "sealed_sources": {
            "baseline": baseline_sources,
            "baseline_rows": baseline_rows,
            "baseline_misses": sum(baseline_pairs.values()),
            "org1_cross_check": org1_sources,
            "org1_rows": org1_rows,
            "org1_misses": sum(org1_pairs.values()),
        },
        "primary_population": {key: value for key, value in primary.items() if key != "pairs"},
        "strict_population": {key: value for key, value in strict.items() if key != "pairs"},
        "org1_cross_check_by_pair": org1_view,
        "kc_a1_gate": {
            "rule": (
                "KC-A1 is admitted only if the TARGET pairs carry at least "
                f"{KC_A1_GATE_ROWS} of the sealed 4,000-row misses"
            ),
            "threshold": KC_A1_GATE_ROWS,
            "target_strict_mass": gate,
            "target_component_mass": int(primary["targets"]["component_mass_total"]),
            "target_strict_mass_excluding_imbalanced": unflagged_mass,
            "imbalanced_target_pairs": sorted(
                str(row["pair_id"])
                for row in primary["pairs"]
                if row["decision"] == TARGET
                and (row["separability"] or {}).get("imbalance_flag", False)
            ),
            "verdict": "PASS" if gate >= KC_A1_GATE_ROWS else "FAIL",
            "verdict_excluding_imbalanced": (
                "PASS" if unflagged_mass >= KC_A1_GATE_ROWS else "FAIL"
            ),
            "strict_population_target_strict_mass": int(
                strict["targets"]["strict_mass_total"]
            ),
            "strict_population_pairs_unmeasurable": int(
                strict["decision_counts"].get(INSUFFICIENT_DATA, 0)
            ),
            "strict_population_pairs_total": int(strict["pair_count"]),
            "strict_population_note": (
                "The gate is read on the PRIMARY population. On the STRICT population the "
                "legacy 400-block proposed evaluation tier leaves fewer than 5 construction "
                "units or blocks on most twin sides, so the majority of pairs are "
                "INSUFFICIENT-DATA and the gate is UNMEASURABLE there rather than failed."
            ),
        },
    }
    table = {
        "schema": "saea-a2t-query-cue-audit-pairs-v1",
        "primary": primary["pairs"],
        "strict": strict["pairs"],
    }
    return summary, table, decontamination
