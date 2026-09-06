"""The system-evolution loop's machinery (E3a).

``rails.proposer`` owns what a candidate IS and every gate it must clear.
This module owns what a ROUND is: the disjoint targets, the K portfolios a
round flies, the two-stage decision that either accepts one assembly or keeps
the incumbent, the stopping rule, the receipt, the model-free replay of that
receipt, and the budget arithmetic a ledger row needs before any of it runs.

The loop, preregistered in ``docs/readiness/2026-09-05-three-dimension-
experiment-program.md`` section 5:

1. State ``A_r`` is a mapping of description overrides for targeted tools
   only; ``A_0`` is empty, i.e. the released compact registry byte for byte.
2. Per target and round, K candidates are built (three proposer rewrites, one
   deterministic control, and in round 1 a length-matched placebo).
3. Candidate ``k`` of EVERY target is assembled into one portfolio registry,
   so a round flies the incumbent plus K portfolios -- never K x targets
   separate arms. :func:`assemble_portfolio`.
4. Stage one, on fold A, decides PER TARGET: admit a candidate iff it saves
   at least 4 rows, harms at most 1, and nets at least 3, all measured on
   that target's own rows; the winner is the largest net, ties broken by
   fewer harms, then fewer bytes, then the lowest ``k``.
   :func:`select_per_target`.
5. The winners are assembled into one candidate state and confirmed on fold
   B, as a whole and never partially: the targeted pooled CI90 lower bound
   must exceed 0 AND the background CI90 lower bound must stay at or above
   the tolerance. :func:`confirm_assembly`.
6. ``R_max`` = 4 rounds; stop after two consecutive rejects or an accepted
   gain under 0.5 pp. :func:`should_stop`.

Why the two stages are different statistics, deliberately. Stage one is a
COUNT rule on 20 units per targeted tool: at that n a bootstrap interval says
nothing, so the gate is saves/harms/net, which is exactly the quantity a
reviewer can recount by hand from the per-sample rows. Stage two is the
interval rule, on the pooled targeted rows plus a background sample that
exists to catch the failure mode a per-target rule cannot see -- a rewrite
that wins its own pair by stealing rows from the 150 tools nobody targeted.
Accepting the assembly as a whole is what makes the background bound
meaningful.

Everything here is model-free. :func:`replay_selection` recomputes a landed
round's every stage-one decision from the sealed per-sample score files
alone; if it disagrees with the receipt, the receipt is wrong.

No class in this module defines both ``initial_contact`` and ``advance``, and
nothing here subclasses ``rails.task_adapter.TaskAdapter``: the one
controller stays ``rails.controllers.EvidenceAgentController`` and the one
harness stays ``core.flight.FlightRuntime``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..analysis.paired import (
    PairedContrast,
    paired_contrast,
    per_sample_scores_from_score_file,
)
from .hashing import canonical_json_bytes, content_hash
from .proposer import CandidateArtifact, ProposerError, candidate_bytes

TARGET_SCHEMA = "saea-evolution-target-v1"
PORTFOLIO_SCHEMA = "saea-evolution-portfolio-v1"
SELECTION_SCHEMA = "saea-evolution-selection-v1"
CONFIRMATION_SCHEMA = "saea-evolution-confirmation-v1"
STATE_SCHEMA = "saea-evolution-state-v1"
ROUND_RECEIPT_SCHEMA = "saea-evolution-round-receipt-v1"
REPLAY_SCHEMA = "saea-evolution-replay-v1"

#: The registered fill name a written baseline fragment names. The fill
#: itself (reading the override artifact and rendering the compact registry
#: through it) is track E1/E3b's; this module only emits the keys.
EVOLVED_FILL_NAME = "evolved-artifact-v1"

#: File-name stems; the sha256 suffix is what makes them deterministic.
ARTIFACT_STEM = "evolved-registry"
FRAGMENT_STEM = "evolved-artifact"
SHA_PREFIX_LENGTH = 16

#: The key under which the incumbent arm's score file is looked up during a
#: replay; every other key is the portfolio's ``k`` rendered as text.
INCUMBENT_KEY = "incumbent"

#: Preregistered constants (program section 5).
MAX_ROUNDS = 4
MIN_ACCEPTED_GAIN_PP = 0.5
BACKGROUND_TOLERANCE_PP = -1.0
DEFAULT_SEED = 20260903

__all__ = [
    "TARGET_SCHEMA",
    "PORTFOLIO_SCHEMA",
    "SELECTION_SCHEMA",
    "CONFIRMATION_SCHEMA",
    "STATE_SCHEMA",
    "ROUND_RECEIPT_SCHEMA",
    "REPLAY_SCHEMA",
    "EVOLVED_FILL_NAME",
    "INCUMBENT_KEY",
    "MAX_ROUNDS",
    "MIN_ACCEPTED_GAIN_PP",
    "BACKGROUND_TOLERANCE_PP",
    "DEFAULT_SEED",
    "EvolutionError",
    "Target",
    "assert_disjoint_targets",
    "Portfolio",
    "assemble_portfolio",
    "write_candidate_fragments",
    "AdmissionGates",
    "CandidateOutcome",
    "StageOneDecision",
    "select_per_target",
    "selection_record",
    "ConfirmationDecision",
    "confirm_assembly",
    "RoundOutcome",
    "EvolutionState",
    "should_stop",
    "write_round_receipt",
    "ReplayResult",
    "replay_selection",
    "ledger_budget",
]


class EvolutionError(ValueError):
    """An evolution-loop input or decision record is malformed -- fail closed."""


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Target:
    """One MF-1 TARGET entry: a named, disjoint set of confusable tools."""

    target_id: str
    tools: tuple[str, ...]

    def validate(self) -> "Target":
        if not isinstance(self.target_id, str) or not self.target_id:
            raise EvolutionError("target_id must be non-empty text")
        if isinstance(self.tools, (str, bytes)) or len(self.tools) < 2:
            raise EvolutionError(
                f"target {self.target_id!r} must name at least two tools; a target "
                "of one tool has nothing to separate it from"
            )
        for tool in self.tools:
            if not isinstance(tool, str) or not tool:
                raise EvolutionError(f"target {self.target_id!r} has a non-text tool")
        if len(set(self.tools)) != len(self.tools):
            raise EvolutionError(f"target {self.target_id!r} repeats a tool")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "schema": TARGET_SCHEMA,
            "target_id": self.target_id,
            "tools": list(self.tools),
        }


def assert_disjoint_targets(targets: Sequence[Target]) -> tuple[Target, ...]:
    """Targets must be disjoint and uniquely named.

    Overlap would break the whole construction: two targets sharing a tool
    would write two different descriptions into one registry line, so
    "candidate k of every target" would no longer be a well-defined
    portfolio and a per-target save could not be attributed.
    """

    if isinstance(targets, (str, bytes)) or not targets:
        raise EvolutionError("targets must be a non-empty sequence")
    seen_ids: set[str] = set()
    owner: dict[str, str] = {}
    for target in targets:
        if not isinstance(target, Target):
            raise EvolutionError("every target must be a Target")
        target.validate()
        if target.target_id in seen_ids:
            raise EvolutionError(f"duplicate target_id {target.target_id!r}")
        seen_ids.add(target.target_id)
        for tool in target.tools:
            if tool in owner:
                raise EvolutionError(
                    f"tool {tool!r} appears in both target {owner[tool]!r} and "
                    f"target {target.target_id!r}; targets must be disjoint"
                )
            owner[tool] = target.target_id
    return tuple(targets)


# ---------------------------------------------------------------------------
# Portfolios
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Portfolio:
    """One flyable registry state: every target's chosen candidate, merged."""

    round: int
    k: int | None
    overrides: Mapping[str, str]
    candidate_ids: Mapping[str, str]
    portfolio_sha256: str

    def as_json(self) -> dict[str, object]:
        return {
            "schema": PORTFOLIO_SCHEMA,
            "round": self.round,
            "k": self.k,
            "overrides": {tool: self.overrides[tool] for tool in sorted(self.overrides)},
            "candidate_ids": {
                target: self.candidate_ids[target] for target in sorted(self.candidate_ids)
            },
            "portfolio_sha256": self.portfolio_sha256,
        }


def assemble_portfolio(
    incumbent_overrides: Mapping[str, str],
    chosen: Mapping[str, CandidateArtifact],
) -> Portfolio:
    """Merge the incumbent state with one candidate per target.

    ``incumbent_overrides`` is ``A_r`` -- what the accepted rounds so far
    already changed, which for round 1 is the empty mapping (``A_0``, the
    released registry). ``chosen`` maps ``target_id`` to the candidate that
    target contributes. A candidate's overrides REPLACE the incumbent's for
    the tools it names and leave every other tool exactly as it was.

    ``k`` is the shared slot number when every chosen candidate came from the
    same slot -- the ordinary round-time case, "candidate k of every target
    assembled into one portfolio registry". It is ``None`` for the stage-two
    assembly, whose members are per-target WINNERS and therefore need not
    share a slot. The round must be shared either way; mixing rounds in one
    portfolio is refused.
    """

    if not isinstance(incumbent_overrides, Mapping):
        raise EvolutionError("incumbent_overrides must be a mapping")
    for tool, text in incumbent_overrides.items():
        if not isinstance(tool, str) or not tool:
            raise EvolutionError("incumbent_overrides has a non-text tool name")
        if not isinstance(text, str) or not text.strip():
            raise EvolutionError(f"incumbent override for {tool!r} must be non-empty text")
    if not isinstance(chosen, Mapping) or not chosen:
        raise EvolutionError("chosen must be a non-empty mapping of target_id to candidate")

    overrides = dict(incumbent_overrides)
    candidate_ids: dict[str, str] = {}
    rounds: set[int] = set()
    slots: set[int] = set()
    claimed: dict[str, str] = {}
    for target_id in sorted(chosen):
        candidate = chosen[target_id]
        if not isinstance(candidate, CandidateArtifact):
            raise EvolutionError(f"chosen[{target_id!r}] must be a CandidateArtifact")
        try:
            candidate.validate()
        except ProposerError as error:
            raise EvolutionError(
                f"chosen[{target_id!r}] is not a valid candidate: {error}"
            ) from error
        if candidate.target_id != target_id:
            raise EvolutionError(
                f"chosen[{target_id!r}] carries target_id {candidate.target_id!r}"
            )
        for tool in candidate.descriptions:
            if tool in claimed:
                raise EvolutionError(
                    f"tool {tool!r} is overridden by both target {claimed[tool]!r} and "
                    f"target {target_id!r}; targets must be disjoint"
                )
            claimed[tool] = target_id
        rounds.add(candidate.round)
        slots.add(candidate.k)
        overrides.update(candidate.descriptions)
        candidate_ids[target_id] = candidate.candidate_id

    if len(rounds) != 1:
        raise EvolutionError(
            f"a portfolio is one round's state; the chosen candidates span rounds "
            f"{sorted(rounds)}"
        )
    portfolio_round = rounds.pop()
    portfolio_k = slots.pop() if len(slots) == 1 else None
    body = {
        "round": portfolio_round,
        "k": portfolio_k,
        "overrides": {tool: overrides[tool] for tool in sorted(overrides)},
        "candidate_ids": {t: candidate_ids[t] for t in sorted(candidate_ids)},
    }
    return Portfolio(
        round=portfolio_round,
        k=portfolio_k,
        overrides=body["overrides"],
        candidate_ids=body["candidate_ids"],
        portfolio_sha256=content_hash(body),
    )


def _relative_posix(path: Path, base: Path) -> str:
    try:
        relative = path.resolve().relative_to(base.resolve())
    except ValueError as error:
        raise EvolutionError(
            f"{path} is not under the artifact relpath base {base}"
        ) from error
    text = relative.as_posix()
    if not text or text.startswith("/") or ".." in text.split("/"):
        raise EvolutionError(f"{path} does not yield a plain relative path under {base}")
    return text


def write_candidate_fragments(
    portfolios: Sequence[Portfolio],
    *,
    base_fragment: Mapping[str, object],
    out_dir: Path | str,
    artifact_dir: Path | str,
    artifact_relpath_base: Path | str | None = None,
) -> list[Path]:
    """Write each portfolio's override artifact and its baseline fragment.

    Per portfolio, two files with names determined entirely by
    ``portfolio_sha256`` (so re-running the assembly rewrites the same bytes
    at the same paths and never accumulates near-duplicates):

    * ``<artifact_dir>/evolved-registry-<sha16>.json`` -- the override
      mapping ``{tool: description}`` alone, canonical JSON. This IS the
      evolved artifact; the registry it modifies stays the released one.
    * ``<out_dir>/evolved-artifact-<sha16>.json`` -- a copy of
      ``base_fragment`` with ``task_instruction_fill`` set to
      ``"evolved-artifact-v1"`` and ``task_instruction_fill_params`` set to
      ``{"artifact_relpath": ..., "artifact_sha256": ...}``.

    Only the KEYS are this module's business: reading them, resolving the
    relpath and rendering the fill belongs to track E1/E3b, and this function
    deliberately does not import ``core.instructions``. The sha256 is over
    the artifact file's bytes as written, so a fragment can never be flown
    against an artifact that was edited after the fragment was emitted.

    ``base_fragment`` must already name a template that carries the tool
    placeholder, and must NOT itself set the two keys this writer owns --
    silently overwriting a caller's fill would hide which arm actually flew.
    ``artifact_relpath`` is relative to ``artifact_relpath_base`` when given
    (a repository root, say), else to ``artifact_dir`` -- i.e. the bare file
    name.
    """

    if isinstance(portfolios, (str, bytes)) or not portfolios:
        raise EvolutionError("portfolios must be a non-empty sequence")
    if not isinstance(base_fragment, Mapping) or not base_fragment:
        raise EvolutionError("base_fragment must be a non-empty mapping")
    for owned in ("task_instruction_fill", "task_instruction_fill_params"):
        if owned in base_fragment:
            raise EvolutionError(
                f"base_fragment already sets {owned!r}; this writer owns that key and "
                "will not silently replace it"
            )
    out_path = Path(out_dir)
    artifact_path = Path(artifact_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    artifact_path.mkdir(parents=True, exist_ok=True)
    base = Path(artifact_relpath_base) if artifact_relpath_base is not None else artifact_path

    written: list[Path] = []
    seen: set[str] = set()
    for portfolio in portfolios:
        if not isinstance(portfolio, Portfolio):
            raise EvolutionError("every portfolio must be a Portfolio")
        if portfolio.portfolio_sha256 in seen:
            raise EvolutionError(
                f"portfolios repeat {portfolio.portfolio_sha256}; two identical states "
                "would write one file twice"
            )
        seen.add(portfolio.portfolio_sha256)
        stem = portfolio.portfolio_sha256[:SHA_PREFIX_LENGTH]

        overrides = {tool: portfolio.overrides[tool] for tool in sorted(portfolio.overrides)}
        artifact_file = artifact_path / f"{ARTIFACT_STEM}-{stem}.json"
        artifact_bytes = canonical_json_bytes(overrides)
        artifact_file.write_bytes(artifact_bytes)

        fragment = dict(base_fragment)
        fragment["task_instruction_fill"] = EVOLVED_FILL_NAME
        fragment["task_instruction_fill_params"] = {
            "artifact_relpath": _relative_posix(artifact_file, base),
            "artifact_sha256": content_hash(overrides),
            "portfolio_sha256": portfolio.portfolio_sha256,
            "round": portfolio.round,
            "k": portfolio.k,
        }
        fragment_file = out_path / f"{FRAGMENT_STEM}-{stem}.json"
        fragment_file.write_text(
            json.dumps(fragment, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        written.append(fragment_file)
    return written


# ---------------------------------------------------------------------------
# Stage one: per-target admission on fold A
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdmissionGates:
    """The preregistered stage-one counts (section 5)."""

    saves: int = 4
    harms: int = 1
    net: int = 3

    def as_json(self) -> dict[str, object]:
        return {"saves": self.saves, "harms": self.harms, "net": self.net}

    def admits(self, *, saves: int, harms: int) -> bool:
        return saves >= self.saves and harms <= self.harms and (saves - harms) >= self.net


@dataclass(frozen=True)
class CandidateOutcome:
    """One candidate's fold-A counts on its own target's rows."""

    k: int
    candidate_id: str | None
    n: int
    saves: int
    harms: int
    ties: int
    net: int
    delta: float
    bytes: int | None
    admitted: bool

    def as_json(self) -> dict[str, object]:
        return {
            "k": self.k,
            "candidate_id": self.candidate_id,
            "n": self.n,
            "saves": self.saves,
            "harms": self.harms,
            "ties": self.ties,
            "net": self.net,
            "delta": self.delta,
            "bytes": self.bytes,
            "admitted": self.admitted,
        }


@dataclass(frozen=True)
class StageOneDecision:
    """One target's fold-A result: every candidate's counts and the winner."""

    target_id: str
    metric: str
    n_rows: int
    outcomes: tuple[CandidateOutcome, ...]
    winner_k: int | None
    winner_candidate_id: str | None
    winner: CandidateArtifact | None = field(default=None, repr=False, compare=False)

    def as_json(self) -> dict[str, object]:
        return {
            "target_id": self.target_id,
            "metric": self.metric,
            "n_rows": self.n_rows,
            "outcomes": [outcome.as_json() for outcome in self.outcomes],
            "winner_k": self.winner_k,
            "winner_candidate_id": self.winner_candidate_id,
        }


def _rows_lookup(
    rows_of_target: Mapping[str, Sequence[str]] | Callable[[str], Sequence[str]],
) -> Callable[[str], tuple[str, ...]]:
    if callable(rows_of_target) and not isinstance(rows_of_target, Mapping):
        resolver = rows_of_target
    elif isinstance(rows_of_target, Mapping):
        def resolver(target_id: str, table=rows_of_target):  # type: ignore[misc]
            if target_id not in table:
                raise EvolutionError(f"rows_of_target has no entry for {target_id!r}")
            return table[target_id]
    else:
        raise EvolutionError("rows_of_target must be a mapping or a callable")

    def lookup(target_id: str) -> tuple[str, ...]:
        rows = resolver(target_id)
        if isinstance(rows, (str, bytes)) or not rows:
            raise EvolutionError(f"target {target_id!r} has no fold-A rows")
        ids = tuple(rows)
        for row in ids:
            if not isinstance(row, str) or not row:
                raise EvolutionError(f"target {target_id!r} has a non-text row id")
        if len(set(ids)) != len(ids):
            raise EvolutionError(f"target {target_id!r} repeats a row id")
        return ids

    return lookup


def select_per_target(
    incumbent_scores: Mapping[str, Mapping[str, float]],
    portfolio_scores: Mapping[int, Mapping[str, Mapping[str, float]]],
    *,
    targets: Sequence[Target],
    rows_of_target: Mapping[str, Sequence[str]] | Callable[[str], Sequence[str]],
    metric: str,
    gates: AdmissionGates = AdmissionGates(saves=4, harms=1, net=3),
    candidates: Mapping[str, Mapping[int, CandidateArtifact]] | None = None,
    seed: int = DEFAULT_SEED,
    n_replicates: int = 1,
) -> dict[str, StageOneDecision]:
    """Stage one, per target, on fold A.

    ``portfolio_scores`` maps a portfolio's slot ``k`` to that whole arm's
    per-sample scores (the shape ``analysis.paired
    .per_sample_scores_from_score_file`` returns). One arm was flown per
    ``k``, over the whole fold-A roster; this function slices each arm down to
    one target's own rows and counts there, which is why a portfolio is
    admissible for one target and not another.

    Counts come from ``analysis.paired.paired_contrast`` -- the same saves /
    harms / ties definition every other paired reading in this repository
    uses, never a local re-implementation. Its bootstrap is NOT read here:
    stage one is a count rule at n = 20 per targeted tool, where an interval
    would be noise, so ``n_replicates`` defaults to 1 and exists only to
    satisfy the shared API at negligible cost. The interval rule is stage
    two, :func:`confirm_assembly`.

    Winner: largest net, ties broken by fewer harms, then fewer override
    bytes, then the lowest ``k`` -- section 5's rule in that order.
    ``candidates`` (target_id -> k -> artifact) supplies the byte count and
    lets the decision carry the winning artifact itself; a real round always
    passes it, and omitting it drops only the byte tie-break.
    ``winner_k`` is ``None`` when the gates admitted nothing, which is the
    "keep the incumbent for this target" outcome.
    """

    if not isinstance(metric, str) or not metric:
        raise EvolutionError("metric must be non-empty text")
    if not isinstance(portfolio_scores, Mapping) or not portfolio_scores:
        raise EvolutionError("portfolio_scores must be a non-empty mapping of k to scores")
    for slot in portfolio_scores:
        if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
            raise EvolutionError("every portfolio_scores key must be a nonnegative int k")
    if not isinstance(gates, AdmissionGates):
        raise EvolutionError("gates must be an AdmissionGates")
    checked_targets = assert_disjoint_targets(targets)
    lookup = _rows_lookup(rows_of_target)

    decisions: dict[str, StageOneDecision] = {}
    for target in checked_targets:
        rows = lookup(target.target_id)
        outcomes: list[CandidateOutcome] = []
        for slot in sorted(portfolio_scores):
            arm = portfolio_scores[slot]
            contrast = paired_contrast(
                incumbent_scores,
                arm,
                metrics=[metric],
                sample_ids=rows,
                seed=seed,
                n_replicates=n_replicates,
            )[metric]
            artifact = None
            if candidates is not None:
                artifact = candidates.get(target.target_id, {}).get(slot)
                if artifact is not None and not isinstance(artifact, CandidateArtifact):
                    raise EvolutionError(
                        f"candidates[{target.target_id!r}][{slot}] is not a CandidateArtifact"
                    )
            net = contrast.saves - contrast.harms
            outcomes.append(
                CandidateOutcome(
                    k=slot,
                    candidate_id=None if artifact is None else artifact.candidate_id,
                    n=contrast.n,
                    saves=contrast.saves,
                    harms=contrast.harms,
                    ties=contrast.ties,
                    net=net,
                    delta=contrast.delta,
                    bytes=None if artifact is None else candidate_bytes(artifact),
                    admitted=gates.admits(saves=contrast.saves, harms=contrast.harms),
                )
            )

        admitted = [outcome for outcome in outcomes if outcome.admitted]
        winner_outcome = None
        if admitted:
            winner_outcome = min(
                admitted,
                key=lambda outcome: (
                    -outcome.net,
                    outcome.harms,
                    # An absent byte count must not silently win the tie-break:
                    # rank unknown-size candidates after every known one.
                    float("inf") if outcome.bytes is None else outcome.bytes,
                    outcome.k,
                ),
            )
        winner_artifact = None
        if winner_outcome is not None and candidates is not None:
            winner_artifact = candidates.get(target.target_id, {}).get(winner_outcome.k)
        decisions[target.target_id] = StageOneDecision(
            target_id=target.target_id,
            metric=metric,
            n_rows=len(rows),
            outcomes=tuple(outcomes),
            winner_k=None if winner_outcome is None else winner_outcome.k,
            winner_candidate_id=(
                None if winner_outcome is None else winner_outcome.candidate_id
            ),
            winner=winner_artifact,
        )
    return decisions


def selection_record(
    decisions: Mapping[str, StageOneDecision],
    *,
    metric: str,
    scorer_id: str,
    gates: AdmissionGates,
    rows_of_target: Mapping[str, Sequence[str]],
    targets: Sequence[Target],
    seed: int = DEFAULT_SEED,
    n_replicates: int = 1,
) -> dict[str, object]:
    """The replayable JSON block a round receipt carries for stage one.

    It records not only WHAT was decided but every input the decision read --
    the metric, the scorer whose per-sample rows were used, the gates, the
    targets, and each target's fold-A row ids -- so :func:`replay_selection`
    can recompute the whole thing from the sealed score files with no other
    context.
    """

    if not isinstance(decisions, Mapping) or not decisions:
        raise EvolutionError("decisions must be a non-empty mapping")
    if not isinstance(scorer_id, str) or not scorer_id:
        raise EvolutionError("scorer_id must be non-empty text")
    checked_targets = assert_disjoint_targets(targets)
    if {target.target_id for target in checked_targets} != set(decisions):
        raise EvolutionError("targets and decisions must name the same target ids")
    if not isinstance(rows_of_target, Mapping):
        raise EvolutionError("selection_record needs an explicit rows_of_target mapping")
    return {
        "schema": SELECTION_SCHEMA,
        "metric": metric,
        "scorer_id": scorer_id,
        "seed": seed,
        "n_replicates": n_replicates,
        "gates": gates.as_json(),
        "targets": [target.as_json() for target in checked_targets],
        "rows_of_target": {
            target_id: list(rows_of_target[target_id])
            for target_id in sorted(decisions)
        },
        "decisions": {
            target_id: decisions[target_id].as_json() for target_id in sorted(decisions)
        },
    }


# ---------------------------------------------------------------------------
# Stage two: whole-assembly confirmation on fold B
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfirmationDecision:
    """The fold-B verdict on one assembled state, as a whole."""

    accepted: bool
    reason: str
    metric: str
    targeted: PairedContrast
    background: PairedContrast
    background_tolerance_pp: float
    targeted_gain_pp: float
    background_gain_pp: float

    def as_json(self) -> dict[str, object]:
        return {
            "schema": CONFIRMATION_SCHEMA,
            "accepted": self.accepted,
            "reason": self.reason,
            "metric": self.metric,
            "background_tolerance_pp": self.background_tolerance_pp,
            "targeted_gain_pp": self.targeted_gain_pp,
            "background_gain_pp": self.background_gain_pp,
            "targeted": self.targeted.as_dict(),
            "background": self.background.as_dict(),
        }


def confirm_assembly(
    incumbent_scores: Mapping[str, Mapping[str, float]],
    assembly_scores: Mapping[str, Mapping[str, float]],
    *,
    targeted_rows: Sequence[str],
    background_rows: Sequence[str],
    metric: str,
    strata_of: Callable[[str], str] | None = None,
    seed: int = DEFAULT_SEED,
    background_tolerance: float = BACKGROUND_TOLERANCE_PP,
    n_replicates: int = 10_000,
    metric_is_fraction: bool = True,
) -> ConfirmationDecision:
    """Accept the whole assembly, or keep the incumbent -- never partially.

    Two CI90 bounds, both required:

    * targeted pooled lower bound strictly ABOVE 0 -- the rewrite helped the
      rows it was written for;
    * background lower bound at or above ``background_tolerance`` -- the
      rewrite did not pay for that by breaking the 150 tools nobody targeted.

    ``background_tolerance`` is in PERCENTAGE POINTS, exactly as section 5
    states it (-1.0 pp), because that is the unit the program, the receipts
    and the owner rules all speak. The scores themselves are 0/1 accuracies,
    so with ``metric_is_fraction`` (the default) the bound is compared after
    dividing by 100; pass ``metric_is_fraction=False`` for a metric already
    expressed on a 0-100 scale. Getting this wrong in the other direction --
    comparing a fraction against -1.0 -- would silently disable the
    background gate entirely, which is why the unit is in the parameter's
    name and in this docstring rather than left to the caller.

    Both contrasts are recorded whole, accepted or not: a rejected round's
    numbers are the evidence for the "two consecutive rejects" stop.
    """

    if not isinstance(metric, str) or not metric:
        raise EvolutionError("metric must be non-empty text")
    if isinstance(targeted_rows, (str, bytes)) or not targeted_rows:
        raise EvolutionError("targeted_rows must be a non-empty sequence of ids")
    if isinstance(background_rows, (str, bytes)) or not background_rows:
        raise EvolutionError("background_rows must be a non-empty sequence of ids")
    targeted_ids = tuple(targeted_rows)
    background_ids = tuple(background_rows)
    overlap = set(targeted_ids) & set(background_ids)
    if overlap:
        raise EvolutionError(
            f"{len(overlap)} row(s) are in both the targeted and the background "
            "population; the background bound would then be partly the targeted one"
        )
    if not isinstance(background_tolerance, (int, float)) or isinstance(
        background_tolerance, bool
    ):
        raise EvolutionError("background_tolerance must be a number in percentage points")

    targeted = paired_contrast(
        incumbent_scores,
        assembly_scores,
        metrics=[metric],
        sample_ids=targeted_ids,
        strata_of=strata_of,
        seed=seed,
        n_replicates=n_replicates,
    )[metric]
    background = paired_contrast(
        incumbent_scores,
        assembly_scores,
        metrics=[metric],
        sample_ids=background_ids,
        strata_of=strata_of,
        seed=seed,
        n_replicates=n_replicates,
    )[metric]
    if targeted.bootstrap is None or background.bootstrap is None:
        raise EvolutionError("confirmation requires both bootstrap intervals")

    scale = 100.0 if metric_is_fraction else 1.0
    tolerance = background_tolerance / scale
    targeted_ok = targeted.bootstrap.ci_low > 0.0
    background_ok = background.bootstrap.ci_low >= tolerance
    if targeted_ok and background_ok:
        reason = (
            f"targeted CI90 lower bound {targeted.bootstrap.ci_low * scale:.3f} pp > 0 "
            f"and background lower bound {background.bootstrap.ci_low * scale:.3f} pp "
            f">= {background_tolerance:.3f} pp"
        )
    elif not targeted_ok:
        reason = (
            f"targeted CI90 lower bound {targeted.bootstrap.ci_low * scale:.3f} pp is "
            "not above 0"
        )
    else:
        reason = (
            f"background CI90 lower bound {background.bootstrap.ci_low * scale:.3f} pp "
            f"is below the {background_tolerance:.3f} pp tolerance"
        )
    return ConfirmationDecision(
        accepted=bool(targeted_ok and background_ok),
        reason=reason,
        metric=metric,
        targeted=targeted,
        background=background,
        background_tolerance_pp=float(background_tolerance),
        targeted_gain_pp=targeted.delta * scale,
        background_gain_pp=background.delta * scale,
    )


# ---------------------------------------------------------------------------
# Rounds, state, stopping
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoundOutcome:
    """What one completed round decided, in the units the stop rule reads."""

    round: int
    accepted: bool
    gain_pp: float
    reason: str
    portfolio_sha256: str | None = None

    def validate(self) -> "RoundOutcome":
        if isinstance(self.round, bool) or not isinstance(self.round, int) or self.round < 1:
            raise EvolutionError("a round outcome's round must be a positive integer")
        if not isinstance(self.accepted, bool):
            raise EvolutionError("accepted must be a bool")
        if isinstance(self.gain_pp, bool) or not isinstance(self.gain_pp, (int, float)):
            raise EvolutionError("gain_pp must be a number in percentage points")
        if not isinstance(self.reason, str) or not self.reason:
            raise EvolutionError("a round outcome must carry its reason")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "round": self.round,
            "accepted": self.accepted,
            "gain_pp": float(self.gain_pp),
            "reason": self.reason,
            "portfolio_sha256": self.portfolio_sha256,
        }


@dataclass(frozen=True)
class EvolutionState:
    """``A_r`` plus the history that produced it."""

    round: int
    incumbent_overrides: Mapping[str, str]
    history: tuple[RoundOutcome, ...] = ()

    def validate(self) -> "EvolutionState":
        if isinstance(self.round, bool) or not isinstance(self.round, int) or self.round < 0:
            raise EvolutionError("round must be a nonnegative integer")
        if not isinstance(self.incumbent_overrides, Mapping):
            raise EvolutionError("incumbent_overrides must be a mapping")
        for tool, text in self.incumbent_overrides.items():
            if not isinstance(tool, str) or not tool:
                raise EvolutionError("incumbent_overrides has a non-text tool name")
            if not isinstance(text, str) or not text.strip():
                raise EvolutionError(f"override for {tool!r} must be non-empty text")
        for outcome in self.history:
            if not isinstance(outcome, RoundOutcome):
                raise EvolutionError("history must hold RoundOutcome entries")
            outcome.validate()
        rounds = [outcome.round for outcome in self.history]
        if rounds != sorted(set(rounds)):
            raise EvolutionError("history must be strictly increasing in round")
        return self

    def with_outcome(
        self, outcome: RoundOutcome, *, overrides: Mapping[str, str] | None = None
    ) -> "EvolutionState":
        """The next state. Named ``with_outcome``, never ``advance``: the
        engineering-base rule reserves the controller shape (a class defining
        both ``initial_contact`` and ``advance``) to
        ``rails.controllers.EvidenceAgentController``, and a state object that
        half-matched it would be exactly the regrowth that rule forbids.

        ``overrides`` is the accepted assembly's state; omitting it keeps the
        incumbent, which is what a rejected round does.
        """

        outcome.validate()
        return EvolutionState(
            round=outcome.round,
            incumbent_overrides=(
                dict(self.incumbent_overrides) if overrides is None else dict(overrides)
            ),
            history=(*self.history, outcome),
        ).validate()

    def as_json(self) -> dict[str, object]:
        return {
            "schema": STATE_SCHEMA,
            "round": self.round,
            "incumbent_overrides": {
                tool: self.incumbent_overrides[tool]
                for tool in sorted(self.incumbent_overrides)
            },
            "history": [outcome.as_json() for outcome in self.history],
        }

    def state_sha256(self) -> str:
        return content_hash(self.as_json())


def should_stop(
    history: Sequence[RoundOutcome],
    *,
    max_rounds: int = MAX_ROUNDS,
    min_accepted_gain_pp: float = MIN_ACCEPTED_GAIN_PP,
) -> tuple[bool, str]:
    """``(stop, reason)`` under section 5's three stopping conditions.

    Checked most-specific first, so the reason names what actually happened
    rather than the cap that would also have applied:

    1. two consecutive rejects -- the loop is not finding anything;
    2. an ACCEPTED round whose gain is under ``min_accepted_gain_pp`` (0.5 pp)
       -- it is finding something too small to be worth another round's
       contacts;
    3. ``max_rounds`` (4) completed rounds.

    ``gain_pp`` is percentage points, the same unit
    :class:`ConfirmationDecision` reports and the program document states.
    """

    if isinstance(history, (str, bytes)):
        raise EvolutionError("history must be a sequence of RoundOutcome")
    entries = tuple(history)
    for outcome in entries:
        if not isinstance(outcome, RoundOutcome):
            raise EvolutionError("history must hold RoundOutcome entries")
        outcome.validate()
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 1:
        raise EvolutionError("max_rounds must be a positive integer")
    if not entries:
        return False, "no round has completed yet"
    if len(entries) >= 2 and not entries[-1].accepted and not entries[-2].accepted:
        return True, (
            f"two consecutive rejects (rounds {entries[-2].round} and {entries[-1].round})"
        )
    last = entries[-1]
    if last.accepted and last.gain_pp < min_accepted_gain_pp:
        return True, (
            f"round {last.round} was accepted at {last.gain_pp:.3f} pp, below the "
            f"{min_accepted_gain_pp:.3f} pp minimum"
        )
    if len(entries) >= max_rounds:
        return True, f"round cap reached ({len(entries)} of {max_rounds})"
    return False, "continue"


def write_round_receipt(
    state: EvolutionState,
    *,
    out_dir: Path | str,
    extra: Mapping[str, object],
) -> tuple[Path, str]:
    """Write one round's receipt; return ``(path, sha256_of_the_written_bytes)``.

    ``extra`` is the round's evidence, and by convention carries at least
    ``"selection"`` (a :func:`selection_record` block) and ``"confirmation"``
    (a :meth:`ConfirmationDecision.as_json` block). It must be JSON-safe: the
    receipt is the artifact a replay reads, so a value that only survives
    ``repr`` would make the round unreplayable -- ``canonical_json_bytes`` is
    called first purely as that check.

    The file is written key-sorted with ``indent=2`` and a trailing newline
    (the shape every other receipt in this repository carries, so a reviewer
    can read it), and the digest returned is over EXACTLY those bytes -- so
    ``sha256sum`` on the file reproduces it, which a digest over a separate
    canonical serialization would not.
    """

    state.validate()
    if not isinstance(extra, Mapping):
        raise EvolutionError("extra must be a mapping")
    document = {
        "schema": ROUND_RECEIPT_SCHEMA,
        "state": state.as_json(),
        "extra": {key: extra[key] for key in sorted(extra)},
    }
    try:
        canonical_json_bytes(document)
    except (TypeError, ValueError) as error:
        raise EvolutionError(f"round receipt is not JSON-safe: {error}") from error
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"evolution-round-{state.round:02d}.json"
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return path, hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Model-free replay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayResult:
    """Whether a landed round's stage-one decisions recompute exactly."""

    matches: bool
    mismatches: tuple[str, ...]
    recomputed: Mapping[str, StageOneDecision]

    def as_json(self) -> dict[str, object]:
        return {
            "schema": REPLAY_SCHEMA,
            "matches": self.matches,
            "mismatches": list(self.mismatches),
            "recomputed": {
                target_id: self.recomputed[target_id].as_json()
                for target_id in sorted(self.recomputed)
            },
        }


def replay_selection(
    round_receipt: Mapping[str, object],
    score_files: Mapping[str, Path | str],
) -> ReplayResult:
    """Recompute every stage-one decision from the sealed per-sample scores.

    This is the model-free check section 5 requires: a reviewer with the
    round receipt and the ``<job_id>.score.json`` files, and nothing else,
    reproduces every save, harm, net and winner the round recorded. Nothing
    is re-flown, no model is contacted, and no number is taken from the
    receipt except as the thing being checked.

    ``round_receipt`` is either a whole receipt (as
    :func:`write_round_receipt` wrote it) or the ``selection`` block alone.
    ``score_files`` maps ``"incumbent"`` and each portfolio's ``k`` rendered
    as text (``"0"``, ``"1"``, ...) to that arm's score file.

    Returns rather than raises on a DISAGREEMENT -- the disagreement is the
    finding, and every mismatched field is named. It still raises
    :class:`EvolutionError` when the receipt or the files cannot be read at
    all, which is a different failure.
    """

    record = _selection_block(round_receipt)
    metric = record["metric"]
    scorer_id = record["scorer_id"]
    if not isinstance(metric, str) or not isinstance(scorer_id, str):
        raise EvolutionError("selection record needs text metric and scorer_id")
    gates_raw = record.get("gates")
    if not isinstance(gates_raw, Mapping):
        raise EvolutionError("selection record carries no gates")
    gates = AdmissionGates(
        saves=int(gates_raw["saves"]), harms=int(gates_raw["harms"]), net=int(gates_raw["net"])
    )
    targets_raw = record.get("targets")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise EvolutionError("selection record carries no targets")
    targets = tuple(
        Target(target_id=str(item["target_id"]), tools=tuple(item["tools"]))
        for item in targets_raw
    )
    rows_raw = record.get("rows_of_target")
    if not isinstance(rows_raw, Mapping) or not rows_raw:
        raise EvolutionError("selection record carries no rows_of_target")
    rows_of_target = {str(key): tuple(value) for key, value in rows_raw.items()}
    decisions_raw = record.get("decisions")
    if not isinstance(decisions_raw, Mapping) or not decisions_raw:
        raise EvolutionError("selection record carries no decisions")

    if not isinstance(score_files, Mapping) or INCUMBENT_KEY not in score_files:
        raise EvolutionError(
            f"score_files must map {INCUMBENT_KEY!r} and each portfolio k to a score file"
        )
    slots: set[int] = set()
    for decision in decisions_raw.values():
        for outcome in decision["outcomes"]:  # type: ignore[index]
            slots.add(int(outcome["k"]))
    incumbent_scores = per_sample_scores_from_score_file(
        Path(score_files[INCUMBENT_KEY]), scorer_id, [metric]
    )
    portfolio_scores: dict[int, Mapping[str, Mapping[str, float]]] = {}
    for slot in sorted(slots):
        key = str(slot)
        if key not in score_files:
            raise EvolutionError(f"score_files has no entry for portfolio k={slot}")
        portfolio_scores[slot] = per_sample_scores_from_score_file(
            Path(score_files[key]), scorer_id, [metric]
        )

    recomputed = select_per_target(
        incumbent_scores,
        portfolio_scores,
        targets=targets,
        rows_of_target=rows_of_target,
        metric=metric,
        gates=gates,
        seed=int(record.get("seed", DEFAULT_SEED)),
        n_replicates=int(record.get("n_replicates", 1)),
    )

    mismatches: list[str] = []
    if set(recomputed) != set(decisions_raw):
        mismatches.append(
            f"target set: receipt {sorted(decisions_raw)} vs recomputed {sorted(recomputed)}"
        )
    for target_id in sorted(set(recomputed) & set(decisions_raw)):
        recorded = decisions_raw[target_id]
        fresh = recomputed[target_id]
        if int(recorded["n_rows"]) != fresh.n_rows:  # type: ignore[index]
            mismatches.append(
                f"{target_id}.n_rows: receipt {recorded['n_rows']} vs {fresh.n_rows}"  # type: ignore[index]
            )
        recorded_outcomes = {
            int(item["k"]): item for item in recorded["outcomes"]  # type: ignore[index]
        }
        fresh_outcomes = {outcome.k: outcome for outcome in fresh.outcomes}
        if set(recorded_outcomes) != set(fresh_outcomes):
            mismatches.append(
                f"{target_id}.slots: receipt {sorted(recorded_outcomes)} vs "
                f"{sorted(fresh_outcomes)}"
            )
        for slot in sorted(set(recorded_outcomes) & set(fresh_outcomes)):
            for name in ("saves", "harms", "ties", "net", "admitted"):
                recorded_value = recorded_outcomes[slot][name]
                fresh_value = getattr(fresh_outcomes[slot], name)
                if recorded_value != fresh_value:
                    mismatches.append(
                        f"{target_id}.k{slot}.{name}: receipt {recorded_value!r} vs "
                        f"{fresh_value!r}"
                    )
        if recorded["winner_k"] != fresh.winner_k:  # type: ignore[index]
            mismatches.append(
                f"{target_id}.winner_k: receipt {recorded['winner_k']!r} vs "  # type: ignore[index]
                f"{fresh.winner_k!r}"
            )
    return ReplayResult(
        matches=not mismatches, mismatches=tuple(mismatches), recomputed=recomputed
    )


def _selection_block(round_receipt: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(round_receipt, Mapping) or not round_receipt:
        raise EvolutionError("round_receipt must be a non-empty mapping")
    if round_receipt.get("schema") == SELECTION_SCHEMA:
        return round_receipt
    extra = round_receipt.get("extra")
    if isinstance(extra, Mapping):
        candidate = extra.get("selection")
        if isinstance(candidate, Mapping) and candidate.get("schema") == SELECTION_SCHEMA:
            return candidate
    raise EvolutionError(
        "round_receipt carries no selection record; expected either the record itself "
        f"(schema {SELECTION_SCHEMA}) or it under extra.selection"
    )


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


def ledger_budget(
    rounds: int,
    *,
    roster_rows: int,
    k: int,
    proposer_calls_per_round: int,
    speech_seconds_per_pass: float,
    seconds_per_call: float,
) -> dict[str, float]:
    """The exposure-ledger pre-registration arithmetic for a whole loop.

    Formula, stated once so a ledger row and this function cannot drift::

        calls          = R * (K + 1) * rows  +  R * proposer_calls_per_round
        speech_seconds = R * (K + 1) * speech_seconds_per_pass
        gpu_hours      = calls * seconds_per_call / 3600

    Read term by term:

    * ``(K + 1)`` is the K portfolio arms PLUS the incumbent, which every
      round re-flies on the same fold so the pairing is against that round's
      own sealed rows rather than an older bundle.
    * ``rows`` is one fold's roster, so ``R * (K + 1) * rows`` is every
      speech-bearing contact the loop makes.
    * the proposer term is ADDED, not multiplied by rows: the proposer arm is
      text-only (registry rows, exemplar transcripts, gold calls), one call
      per target per proposer slot, so it consumes no audio at all -- which is
      why it appears in ``calls`` and never in ``speech_seconds``.
    * ``speech_seconds_per_pass`` is the fold's total audio duration, counted
      once per whole-roster pass.

    Plan budgets are run-cumulative, so this is the WORST case for the whole
    loop: a successor plan covers the durable spend of every prior attempt
    plus its own.
    """

    def _positive_int(value: object, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise EvolutionError(f"{name} must be a positive integer")
        return value

    def _nonnegative_int(value: object, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise EvolutionError(f"{name} must be a nonnegative integer")
        return value

    def _nonnegative_number(value: object, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise EvolutionError(f"{name} must be a nonnegative number")
        return float(value)

    r = _positive_int(rounds, "rounds")
    rows = _positive_int(roster_rows, "roster_rows")
    slots = _positive_int(k, "k")
    proposer_calls = _nonnegative_int(proposer_calls_per_round, "proposer_calls_per_round")
    audio = _nonnegative_number(speech_seconds_per_pass, "speech_seconds_per_pass")
    per_call = _nonnegative_number(seconds_per_call, "seconds_per_call")

    passes = r * (slots + 1)
    calls = passes * rows + r * proposer_calls
    return {
        "calls": float(calls),
        "speech_seconds": passes * audio,
        "gpu_hours": calls * per_call / 3600.0,
    }
