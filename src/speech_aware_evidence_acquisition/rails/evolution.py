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
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..analysis.paired import (
    PairedContrast,
    paired_contrast,
    per_sample_scores_from_score_file,
)
from .hashing import canonical_json_bytes, content_hash
from .proposer import (
    CandidateArtifact,
    ProposerError,
    candidate_bytes,
    parse_proposer_response,
    placebo_candidate,
    prompt_sha256,
    proposer_candidate,
    render_placebo_instruction,
    render_proposer_instruction,
)

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
    "EXEMPLARS_PER_TOOL",
    "CONTACT_FAMILIES",
    "PROPOSER_DRAW_SCHEMA",
    "PROPOSER_MATERIAL_SCHEMA",
    "HARVEST_SCHEMA",
    "ROUND_PLAN_SCHEMA",
    "ROUND_STEPS",
    "ProposerDraw",
    "draw_exemplar_ids",
    "plan_proposer_draws",
    "proposer_roster_receipt",
    "read_proposer_roster",
    "ProposerContact",
    "ProposerMaterial",
    "build_proposer_material",
    "CandidateHarvest",
    "harvest_proposer_responses",
    "assemble_round_portfolios",
    "RoundStep",
    "RoundPlan",
    "round_step_paths",
    "plan_round",
    "advance_round",
    "check_ledger_budget",
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


# ---------------------------------------------------------------------------
# The proposer flight (E3c): draws, the roster receipt, the rendered material
# ---------------------------------------------------------------------------
#
# ``rails.proposer`` knows how to RENDER one instruction and how to parse one
# answer; ``core.flight.FlightRuntime`` knows how to make one contact. What
# was missing is the thing in between: which contacts a round makes, what
# each one shows, and how a sealed response becomes a candidate. That is this
# section, and it is entirely model-free -- every function here is pure over
# committed receipts and carrier text, and none of them opens a socket.
#
# A proposer "roster" is a receipt whose ITEMS ARE THE DRAWS, one per
# (round, target, family, k). It is a real ``core.roster`` receipt with
# ``roster_role == "construction"`` so that ``contracts.gate_exposure
# ._require_construction_role_for_visible_targets`` accepts a plan bound to
# it; each item's ``sample_id`` is the draw's ANCHOR -- a real construction
# row of ``A2T-EVO-EXEMPLARS-V1``, which is what makes the payload's
# ``speech_ref``/``media_relpath``/``audio_seconds`` honest even though the
# contact is text-only and no audio part is ever sent.


#: Exemplars shown per tool in one proposer draw (preregistration section 4:
#: "M = 8 block-disjoint construction exemplars per tool").
EXEMPLARS_PER_TOOL = 8

#: The families a proposer FLIGHT can carry. ``deterministic`` is absent on
#: purpose: it is built with zero contacts (``rails.proposer
#: .deterministic_candidate``) and therefore never draws a roster item.
CONTACT_FAMILIES = ("proposer", "placebo")

PROPOSER_DRAW_SCHEMA = "saea-evolution-proposer-draw-v1"
PROPOSER_MATERIAL_SCHEMA = "saea-evolution-proposer-material-v1"


@dataclass(frozen=True)
class ProposerDraw:
    """One proposer contact, as a roster item: which target, which slot, and
    exactly which construction exemplars it shows, in the order it shows
    them."""

    round: int
    target_id: str
    family: str
    k: int
    exemplar_ids: tuple[str, ...]
    anchor_sample_id: str

    @property
    def draw_id(self) -> str:
        return f"r{self.round:02d}-{self.target_id}-{self.family}-k{self.k}"

    def validate(self) -> "ProposerDraw":
        if isinstance(self.round, bool) or not isinstance(self.round, int) or self.round < 1:
            raise EvolutionError("a proposer draw's round must be a positive integer")
        if not isinstance(self.target_id, str) or not self.target_id:
            raise EvolutionError("a proposer draw needs a non-empty target_id")
        if self.family not in CONTACT_FAMILIES:
            raise EvolutionError(
                f"a proposer draw's family must be one of {CONTACT_FAMILIES}; got "
                f"{self.family!r} (the deterministic control makes no contact)"
            )
        if isinstance(self.k, bool) or not isinstance(self.k, int) or self.k < 1:
            raise EvolutionError("a proposer draw's k must be a positive integer")
        ids = tuple(self.exemplar_ids)
        for item in ids:
            if not isinstance(item, str) or not item:
                raise EvolutionError("every exemplar id must be non-empty text")
        if len(set(ids)) != len(ids):
            raise EvolutionError(f"draw {self.draw_id} repeats an exemplar id")
        if self.family == "proposer" and not ids:
            raise EvolutionError(
                f"draw {self.draw_id} is a proposer draw with no exemplars; the "
                "instruction's whole grounding is the exemplar block"
            )
        if self.family == "placebo" and ids:
            raise EvolutionError(
                f"draw {self.draw_id} is a placebo draw carrying {len(ids)} exemplar "
                "id(s); a placebo is shown no exemplar at all, because an exemplar's "
                "gold call IS a distinguishing cue"
            )
        if not isinstance(self.anchor_sample_id, str) or not self.anchor_sample_id:
            raise EvolutionError(f"draw {self.draw_id} needs an anchor sample id")
        return self

    def as_item(self, media_facts: Mapping[str, object]) -> dict[str, object]:
        """This draw as one ``core.roster`` receipt item.

        ``media_facts`` are the anchor row's own measured media facts
        (``media_relpath``/``audio_sha256``/``audio_seconds``), the same
        three ``scripts/flights/run_calibration_cell.py`` re-measures before
        it builds a sample -- so a proposer flight hydrates through exactly
        the entry point every other Audio2Tool cell uses. They are recorded
        even though this arm sends no audio: the payload still names the
        anchor's ``speech_ref``, and the I-4 media-identity gate re-hashes
        precisely what the binding names.
        """

        self.validate()
        if not isinstance(media_facts, Mapping):
            raise EvolutionError(f"draw {self.draw_id} needs a media_facts mapping")
        required = {"media_relpath", "audio_sha256", "audio_seconds"}
        missing = sorted(required - set(media_facts))
        if missing:
            raise EvolutionError(
                f"draw {self.draw_id} media facts lack {missing} for anchor "
                f"{self.anchor_sample_id!r}"
            )
        return {
            "sample_id": self.anchor_sample_id,
            "stratum": self.target_id,
            "schema": PROPOSER_DRAW_SCHEMA,
            "draw_id": self.draw_id,
            "round": self.round,
            "target_id": self.target_id,
            "family": self.family,
            "k": self.k,
            "exemplar_ids": list(self.exemplar_ids),
            "media_relpath": str(media_facts["media_relpath"]),
            "audio_sha256": str(media_facts["audio_sha256"]),
            "audio_seconds": float(media_facts["audio_seconds"]),
        }

    @classmethod
    def from_item(cls, item: Mapping[str, object]) -> "ProposerDraw":
        if not isinstance(item, Mapping):
            raise EvolutionError("a proposer roster item must be an object")
        missing = sorted(
            {"sample_id", "round", "target_id", "family", "k", "exemplar_ids"} - set(item)
        )
        if missing:
            raise EvolutionError(f"proposer roster item lacks {missing}")
        raw_ids = item["exemplar_ids"]
        if isinstance(raw_ids, (str, bytes)) or not isinstance(raw_ids, Sequence):
            raise EvolutionError("proposer roster item exemplar_ids must be a list")
        return cls(
            round=int(item["round"]),
            target_id=str(item["target_id"]),
            family=str(item["family"]),
            k=int(item["k"]),
            exemplar_ids=tuple(str(value) for value in raw_ids),
            anchor_sample_id=str(item["sample_id"]),
        ).validate()


def draw_exemplar_ids(
    pool_by_tool: Mapping[str, Sequence[str]],
    *,
    round: int,
    target_id: str,
    k: int,
    exemplars_per_tool: int = EXEMPLARS_PER_TOOL,
    seed: int = DEFAULT_SEED,
) -> tuple[str, ...]:
    """The preregistered seeded ORDERED sample (preregistration section 4).

    ``A2T-EVO-EXEMPLARS-V1`` holds exactly ``M`` units for twelve of its
    twenty-three tools, so three draws over such a pool cannot differ in
    MEMBERSHIP; the frozen core decodes greedily, so three prompts differing
    only in a header would return three near-identical rewrites and ``K``
    would be decorative. The draw is therefore preregistered as: the seed
    ``(round, target_id, k)`` selects the ``M`` exemplars where more than
    ``M`` exist, and IN EVERY CASE fixes their order, which
    ``rails.proposer.render_proposer_instruction`` preserves within a tool's
    group.

    The rule, stated once so it cannot drift: tools are processed in
    ascending name order; within a tool the candidate ids are first sorted
    (so the draw never depends on input order) and then shuffled by ONE
    ``random.Random`` instance shared across the tools of this draw and
    seeded by the text ``"{seed}:{round}:{target_id}:{k}"``; the first
    ``exemplars_per_tool`` of the shuffled order are taken, in that order.
    This is the same single-shared-rng convention ``core.roster.freeze_roster``
    documents, and a different seed string per (round, target, k) is what
    makes the three slots genuinely different prompts.
    """

    if not isinstance(pool_by_tool, Mapping) or not pool_by_tool:
        raise EvolutionError("pool_by_tool must be a non-empty mapping of tool to ids")
    if isinstance(round, bool) or not isinstance(round, int) or round < 0:
        raise EvolutionError("round must be a nonnegative integer")
    if isinstance(k, bool) or not isinstance(k, int) or k < 0:
        raise EvolutionError("k must be a nonnegative integer")
    if not isinstance(target_id, str) or not target_id:
        raise EvolutionError("target_id must be non-empty text")
    if (
        isinstance(exemplars_per_tool, bool)
        or not isinstance(exemplars_per_tool, int)
        or exemplars_per_tool < 1
    ):
        raise EvolutionError("exemplars_per_tool must be a positive integer")

    rng = random.Random(f"{seed}:{round}:{target_id}:{k}")
    drawn: list[str] = []
    seen: set[str] = set()
    for tool in sorted(pool_by_tool):
        candidates = pool_by_tool[tool]
        if isinstance(candidates, (str, bytes)):
            raise EvolutionError(f"pool_by_tool[{tool!r}] must be a sequence of ids")
        pool = sorted(str(value) for value in candidates)
        if not pool:
            raise EvolutionError(
                f"tool {tool!r} has no construction exemplar left; a target whose tool "
                "cannot be exemplified must be dropped before the draw, not silently"
            )
        rng.shuffle(pool)
        for sample_id in pool[:exemplars_per_tool]:
            if sample_id in seen:
                raise EvolutionError(
                    f"exemplar {sample_id!r} is offered by two tools of target "
                    f"{target_id!r}; the pool must be disjoint per tool"
                )
            seen.add(sample_id)
            drawn.append(sample_id)
    return tuple(drawn)


def plan_proposer_draws(
    target_tools: Mapping[str, Sequence[str]],
    pool_by_tool: Mapping[str, Sequence[str]],
    *,
    round: int,
    proposer_slots: Sequence[int],
    placebo_slot: int | None = None,
    exemplars_per_tool: int = EXEMPLARS_PER_TOOL,
    seed: int = DEFAULT_SEED,
) -> tuple[ProposerDraw, ...]:
    """Every contact one round's PROPOSE step makes, in (target, k) order.

    ``proposer_slots`` are the F1 slots (``(1, 2, 3)`` in every round);
    ``placebo_slot`` is F3, which exists in round 1 only and is an EXTRA slot
    rather than a replaced proposer draw (preregistration section 4:
    ``K_1 = 5``, ``K_r = 4``). The F2 deterministic control is not here: it
    makes no contact at all.

    ANCHORS. Every draw needs a distinct sample id, because a flight's roster
    is a set of samples and the bundle contract seals exactly one outputs row
    per sample. The anchor is taken from the draw's OWN ordered exemplars --
    the first one no earlier draw of this round already claimed -- so a
    payload's ``speech_ref`` always names a construction row the same
    contact's prompt actually showed. A placebo shows no exemplar at all, so
    its anchor is drawn from its target's pool by the same seeded rule
    (``k`` = the placebo's own slot); its payload therefore DECLARES one
    construction target whose gold its prompt never rendered, which
    over-declares exposure by exactly one row -- the conservative direction,
    and recorded as such (``ProposerContact.rendered_exemplar_ids`` is empty
    for a placebo).
    """

    if not isinstance(target_tools, Mapping) or not target_tools:
        raise EvolutionError("target_tools must be a non-empty mapping")
    if isinstance(proposer_slots, (str, bytes)) or not proposer_slots:
        raise EvolutionError("proposer_slots must be a non-empty sequence of slots")
    slots = tuple(int(slot) for slot in proposer_slots)
    if len(set(slots)) != len(slots):
        raise EvolutionError("proposer_slots repeats a slot")
    if placebo_slot is not None:
        if isinstance(placebo_slot, bool) or not isinstance(placebo_slot, int):
            raise EvolutionError("placebo_slot must be an integer or None")
        if placebo_slot in slots:
            raise EvolutionError(
                f"placebo_slot {placebo_slot} collides with a proposer slot; the "
                "round-1 placebo is an EXTRA slot, never a replaced proposer draw"
            )

    draws: list[ProposerDraw] = []
    used_anchors: set[str] = set()

    def _anchor(candidates: Sequence[str], draw_id: str) -> str:
        for sample_id in candidates:
            if sample_id not in used_anchors:
                used_anchors.add(sample_id)
                return sample_id
        raise EvolutionError(
            f"draw {draw_id} cannot claim a distinct anchor: every candidate is "
            "already the anchor of an earlier draw in this round"
        )

    for target_id in sorted(target_tools):
        raw_tools = target_tools[target_id]
        tools = tuple(raw_tools)
        if isinstance(raw_tools, (str, bytes)) or len(tools) < 2:
            raise EvolutionError(f"target {target_id!r} must name at least two tools")
        missing = sorted(set(tools) - set(pool_by_tool))
        if missing:
            raise EvolutionError(
                f"target {target_id!r} names tool(s) with no exemplar pool: {missing}"
            )
        pool = {tool: pool_by_tool[tool] for tool in tools}
        for k in slots:
            exemplars = draw_exemplar_ids(
                pool,
                round=round,
                target_id=target_id,
                k=k,
                exemplars_per_tool=exemplars_per_tool,
                seed=seed,
            )
            draws.append(
                ProposerDraw(
                    round=round,
                    target_id=target_id,
                    family="proposer",
                    k=k,
                    exemplar_ids=exemplars,
                    anchor_sample_id=_anchor(
                        exemplars, f"r{round:02d}-{target_id}-proposer-k{k}"
                    ),
                ).validate()
            )
        if placebo_slot is not None:
            candidates = draw_exemplar_ids(
                pool,
                round=round,
                target_id=target_id,
                k=placebo_slot,
                exemplars_per_tool=exemplars_per_tool,
                seed=seed,
            )
            draws.append(
                ProposerDraw(
                    round=round,
                    target_id=target_id,
                    family="placebo",
                    k=placebo_slot,
                    exemplar_ids=(),
                    anchor_sample_id=_anchor(
                        candidates, f"r{round:02d}-{target_id}-placebo-k{placebo_slot}"
                    ),
                ).validate()
            )
    return tuple(draws)


def proposer_roster_receipt(
    draws: Sequence[ProposerDraw],
    *,
    carrier_lock_key: str,
    roster_id: str,
    media_facts: Mapping[str, Mapping[str, object]],
    split_role: str = "discovery",
    seed: int = DEFAULT_SEED,
    design: str = "",
) -> dict[str, object]:
    """The committed roster receipt one round's proposer flight flies.

    Shape and identity are ``core.roster``'s, not a second convention: the
    same ``saea-roster-receipt-v1`` schema, the same
    ``split_identity_hash`` over the LF-joined sorted carrier-prefixed sample
    ids, and ``roster_role = "construction"``, which is exactly what
    ``contracts.gate_exposure._require_construction_role_for_visible_targets``
    scans ``docs/receipts/rosters/`` for. It is not produced by
    :func:`core.roster.freeze_roster` because nothing here is a stratified
    DRAW over a candidate pool -- the pool draw already happened, per target,
    in :func:`plan_proposer_draws`; this only freezes it.

    The returned document is verified through ``core.roster.verify_roster``
    before it is returned, so a caller can never write an unverifiable one.
    """

    from ..core.roster import (  # noqa: PLC0415 -- function-local, breaks the core/rails cycle
        CONSTRUCTION_ROSTER_ROLE,
        RECEIPT_SCHEMA,
        verify_roster,
    )
    from ..data.splits import prefixed, split_identity_hash  # noqa: PLC0415

    if isinstance(draws, (str, bytes)) or not draws:
        raise EvolutionError("draws must be a non-empty sequence of ProposerDraw")
    if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
        raise EvolutionError("carrier_lock_key must be non-empty text")
    if not isinstance(roster_id, str) or not roster_id:
        raise EvolutionError("roster_id must be non-empty text")
    if not isinstance(media_facts, Mapping):
        raise EvolutionError("media_facts must be a mapping of sample id to media facts")

    rounds = {draw.round for draw in draws}
    if len(rounds) != 1:
        raise EvolutionError(
            f"a proposer roster is ONE round's contacts; these span rounds {sorted(rounds)}"
        )
    items: list[dict[str, object]] = []
    for draw in draws:
        if not isinstance(draw, ProposerDraw):
            raise EvolutionError("every draw must be a ProposerDraw")
        facts = media_facts.get(draw.anchor_sample_id)
        if facts is None:
            raise EvolutionError(
                f"no media facts for anchor {draw.anchor_sample_id!r} of draw "
                f"{draw.draw_id}"
            )
        items.append(draw.as_item(facts))
    items.sort(key=lambda item: str(item["sample_id"]))
    ids = [str(item["sample_id"]) for item in items]
    if len(set(ids)) != len(ids):
        raise EvolutionError("two draws claim the same anchor sample id")

    strata_counts: dict[str, int] = {}
    for item in items:
        strata_counts[str(item["stratum"])] = strata_counts.get(str(item["stratum"]), 0) + 1
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "roster_id": roster_id,
        "carrier_lock_key": carrier_lock_key,
        "split_role": split_role,
        "roster_role": CONSTRUCTION_ROSTER_ROLE,
        "seed": seed,
        "round": rounds.pop(),
        "design": design
        or (
            "EVO-A1 proposer draws: one item per (round, target, family, k) contact on "
            "the text-only 'construction-proposer-text' arm. sample_id is the draw's "
            "anchor construction row; exemplar_ids are the rows whose gold that "
            "contact's rendered instruction shows, in the order it shows them."
        ),
        "per_stratum": dict(sorted(strata_counts.items())),
        "strata_counts": dict(sorted(strata_counts.items())),
        "items": items,
        "excluded_count": 0,
        "split_identity_hash": split_identity_hash(prefixed(carrier_lock_key, ids)),
    }
    verify_roster(receipt)
    return receipt


def read_proposer_roster(
    document: Mapping[str, object], *, carrier_lock_key: str | None = None
) -> tuple[ProposerDraw, ...]:
    """The draws a committed proposer roster receipt carries -- verified.

    Fail-closed on anything that would let a flight show gold it was not
    licensed for: a receipt whose recomputed identity hash disagrees with its
    own items (``core.roster.verify_roster``), a receipt whose
    ``roster_role`` is not ``"construction"`` (the one role whose gold may
    cross to the frozen core at all), a carrier mismatch, or an item that is
    not a well-formed draw.
    """

    from ..core.roster import (  # noqa: PLC0415
        CONSTRUCTION_ROSTER_ROLE,
        RosterError,
        verify_roster,
    )

    if not isinstance(document, Mapping) or not document:
        raise EvolutionError("proposer roster receipt must be a non-empty mapping")
    try:
        verify_roster(document)
    except RosterError as error:
        raise EvolutionError(f"proposer roster receipt is not verifiable: {error}") from error
    if document.get("roster_role") != CONSTRUCTION_ROSTER_ROLE:
        raise EvolutionError(
            f"proposer roster receipt roster_role is "
            f"{document.get('roster_role')!r}, not {CONSTRUCTION_ROSTER_ROLE!r}; only a "
            "construction roster's gold may reach the frozen core"
        )
    if carrier_lock_key is not None and document.get("carrier_lock_key") != carrier_lock_key:
        raise EvolutionError(
            f"proposer roster receipt names carrier "
            f"{document.get('carrier_lock_key')!r}, not {carrier_lock_key!r}"
        )
    draws = tuple(ProposerDraw.from_item(item) for item in document["items"])
    rounds = {draw.round for draw in draws}
    if len(rounds) != 1:
        raise EvolutionError(
            f"proposer roster receipt spans rounds {sorted(rounds)}; a proposer flight "
            "is one round's contacts"
        )
    return draws


@dataclass(frozen=True)
class ProposerContact:
    """One rendered, flyable proposer contact.

    ``instruction`` is the whole system message
    (``rails.proposer.render_proposer_instruction`` for F1,
    ``render_placebo_instruction`` for F3) and is the ONLY place a
    construction row's query text or gold call is ever rendered -- it is
    built at flight time from the carrier and is never written to a receipt.
    ``construction_target_ids`` is what the audited payload declares, in the
    order the prompt showed; ``rendered_exemplar_ids`` is what the prompt
    ACTUALLY showed, which for a placebo is nothing at all.
    """

    draw: ProposerDraw
    instruction: str
    prompt_sha256: str
    construction_target_ids: tuple[str, ...]
    rendered_exemplar_ids: tuple[str, ...]

    @property
    def sample_id(self) -> str:
        return self.draw.anchor_sample_id

    def as_json(self) -> dict[str, object]:
        """Everything a receipt may record about this contact -- identity,
        counts and digests, never the rendered text."""

        return {
            "draw_id": self.draw.draw_id,
            "sample_id": self.sample_id,
            "round": self.draw.round,
            "target_id": self.draw.target_id,
            "family": self.draw.family,
            "k": self.draw.k,
            "prompt_sha256": self.prompt_sha256,
            "prompt_characters": len(self.instruction),
            "declared_construction_targets": len(self.construction_target_ids),
            "rendered_exemplars": len(self.rendered_exemplar_ids),
            "exemplar_ids": list(self.draw.exemplar_ids),
        }


@dataclass(frozen=True)
class ProposerMaterial:
    """Every contact one proposer flight makes, plus the gold it may show.

    ``bound_targets`` is what ``rails.core_client.FrozenCoreClient`` is
    constructed with: the union, sorted by sample id, of every contact's own
    declared targets. Binding the union ONCE and selecting a subset per
    request is what keeps the module's invariant intact -- a request can
    narrow what the core sees, never widen it.
    """

    contacts: tuple[ProposerContact, ...]
    bound_targets: tuple[Mapping[str, str], ...]

    def by_sample(self) -> dict[str, ProposerContact]:
        return {contact.sample_id: contact for contact in self.contacts}

    def as_json(self) -> dict[str, object]:
        return {
            "schema": PROPOSER_MATERIAL_SCHEMA,
            "contacts": [contact.as_json() for contact in self.contacts],
            "bound_target_count": len(self.bound_targets),
            "bound_target_sample_ids": [
                str(entry["sample_id"]) for entry in self.bound_targets
            ],
        }


def _incumbent_descriptions(
    rows_by_name: Mapping[str, Mapping[str, str]],
    tools: Sequence[str],
    incumbent_overrides: Mapping[str, str],
) -> dict[str, str]:
    out: dict[str, str] = {}
    for tool in tools:
        row = rows_by_name.get(tool)
        if row is None:
            raise EvolutionError(f"tool {tool!r} is not in the supplied registry rows")
        text = incumbent_overrides.get(tool, row["description"])
        if not isinstance(text, str) or not text.strip():
            raise EvolutionError(f"incumbent description for {tool!r} is empty")
        out[tool] = text
    return out


def build_proposer_material(
    roster_document: Mapping[str, object],
    *,
    registry_rows: Sequence[Mapping[str, str]],
    target_tools: Mapping[str, Sequence[str]],
    incumbent_overrides: Mapping[str, str],
    exemplar_rows: Mapping[str, Mapping[str, str]],
    carrier_lock_key: str | None = None,
) -> ProposerMaterial:
    """Render every contact of one committed proposer roster. Pure.

    ``exemplar_rows`` maps a construction sample id to
    ``{"query": ..., "gold_call": ..., "tool_name": ...}`` -- exactly what
    ``data.audio2tool.load_query_rows`` returns. It must cover every id the
    roster's draws name (every exemplar AND every anchor), and this function
    refuses an exemplar whose gold call does not open with its own declared
    tool name: the instruction groups exemplars by the tool their GOLD CALL
    names, so a silent disagreement there would put a row under the wrong
    heading.

    The placebo's ``target_lengths`` are the INCUMBENT description lengths,
    not a later winner's: the placebo prompt is rendered in the same PROPOSE
    step as the proposer prompts, before any fold has flown, and "length
    matched" at that point can only mean matched to the description the
    rewrite replaces. The refusal for a length above
    ``rails.proposer.MAX_DESCRIPTION_CHARS`` is
    ``render_placebo_instruction``'s own and is left where it is.
    """

    draws = read_proposer_roster(roster_document, carrier_lock_key=carrier_lock_key)
    if not isinstance(registry_rows, Sequence) or isinstance(registry_rows, (str, bytes)):
        raise EvolutionError("registry_rows must be a sequence of registry rows")
    rows_by_name = {str(row["tool_name"]): row for row in registry_rows}
    if not isinstance(target_tools, Mapping) or not target_tools:
        raise EvolutionError("target_tools must be a non-empty mapping")
    if not isinstance(incumbent_overrides, Mapping):
        raise EvolutionError("incumbent_overrides must be a mapping")
    if not isinstance(exemplar_rows, Mapping):
        raise EvolutionError("exemplar_rows must be a mapping")

    contacts: list[ProposerContact] = []
    bound: dict[str, str] = {}

    def _row(sample_id: str) -> Mapping[str, str]:
        row = exemplar_rows.get(sample_id)
        if not isinstance(row, Mapping):
            raise EvolutionError(
                f"no construction row supplied for {sample_id!r}; every exemplar and "
                "every anchor the roster names must be resolvable"
            )
        for column in ("query", "gold_call", "tool_name"):
            value = row.get(column)
            if not isinstance(value, str) or not value.strip():
                raise EvolutionError(f"construction row {sample_id!r} has no {column}")
        return row

    for draw in draws:
        tools = tuple(target_tools.get(draw.target_id, ()))
        if len(tools) < 2:
            raise EvolutionError(
                f"draw {draw.draw_id} names target {draw.target_id!r}, which the "
                "supplied target set does not describe as two or more tools"
            )
        target_rows = []
        for tool in sorted(tools):
            row = rows_by_name.get(tool)
            if row is None:
                raise EvolutionError(
                    f"target {draw.target_id!r} names tool {tool!r}, absent from the "
                    "supplied registry rows"
                )
            target_rows.append(row)
        incumbent = _incumbent_descriptions(rows_by_name, sorted(tools), incumbent_overrides)

        if draw.family == "proposer":
            exemplars: list[tuple[str, str, str]] = []
            for sample_id in draw.exemplar_ids:
                row = _row(sample_id)
                gold_call = row["gold_call"]
                head = gold_call.split("(", 1)[0].strip()
                if head != row["tool_name"]:
                    raise EvolutionError(
                        f"construction row {sample_id!r} declares tool "
                        f"{row['tool_name']!r} but its gold call opens with {head!r}; "
                        "the exemplar block groups by the gold call's own tool"
                    )
                exemplars.append((sample_id, row["query"], gold_call))
            instruction = render_proposer_instruction(
                target_rows,
                incumbent,
                exemplars,
                target_id=draw.target_id,
                round=draw.round,
                k=draw.k,
            )
            declared = tuple(draw.exemplar_ids)
            rendered = tuple(draw.exemplar_ids)
        else:
            instruction = render_placebo_instruction(
                target_rows,
                incumbent,
                target_id=draw.target_id,
                round=draw.round,
                k=draw.k,
                target_lengths={tool: len(incumbent[tool]) for tool in incumbent},
            )
            declared = (draw.anchor_sample_id,)
            rendered = ()

        for sample_id in declared:
            row = _row(sample_id)
            existing = bound.get(sample_id)
            if existing is not None and existing != row["gold_call"]:
                raise EvolutionError(
                    f"construction row {sample_id!r} resolves to two different gold "
                    "calls within one flight"
                )
            bound[sample_id] = row["gold_call"]

        contacts.append(
            ProposerContact(
                draw=draw,
                instruction=instruction,
                prompt_sha256=prompt_sha256(instruction),
                construction_target_ids=declared,
                rendered_exemplar_ids=rendered,
            )
        )

    return ProposerMaterial(
        contacts=tuple(contacts),
        bound_targets=tuple(
            {"sample_id": sample_id, "target": bound[sample_id]}
            for sample_id in sorted(bound)
        ),
    )


# ---------------------------------------------------------------------------
# Harvesting a sealed proposer flight
# ---------------------------------------------------------------------------


HARVEST_SCHEMA = "saea-evolution-candidate-harvest-v1"
ROUND_PLAN_SCHEMA = "saea-evolution-round-plan-v1"

#: The four steps one round runs, in order. Each reads its predecessor's
#: sealed receipt and refuses to redo it, which is the whole of the driver's
#: resumability: a round interrupted anywhere is resumed by re-running the
#: same command.
ROUND_STEPS = ("propose", "candidates", "select", "confirm")


@dataclass(frozen=True)
class CandidateHarvest:
    """What one sealed proposer flight yielded: the candidates that parsed
    and validated, and the refusals, which are RECORDED and never repaired.

    A refused slot is not retried and not patched: preregistration section 5
    step 1 -- "a candidate that fails a form or decontamination gate is
    dropped and its slot flies the incumbent's descriptions for that
    target". Repairing a proposer answer here would be a second, unlogged
    policy deciding what the frozen core meant.
    """

    round: int
    candidates: tuple[CandidateArtifact, ...]
    refusals: tuple[Mapping[str, object], ...]

    def by_target_and_slot(self) -> dict[str, dict[int, CandidateArtifact]]:
        out: dict[str, dict[int, CandidateArtifact]] = {}
        for candidate in self.candidates:
            out.setdefault(candidate.target_id, {})[candidate.k] = candidate
        return out

    def as_json(self) -> dict[str, object]:
        return {
            "schema": HARVEST_SCHEMA,
            "round": self.round,
            "candidates": [candidate.as_json() for candidate in self.candidates],
            "refusals": [dict(refusal) for refusal in self.refusals],
            "candidate_count": len(self.candidates),
            "refusal_count": len(self.refusals),
        }


def harvest_proposer_responses(
    contact_records: Sequence[Mapping[str, object]],
    responses: Mapping[str, str],
    *,
    target_tools: Mapping[str, Sequence[str]],
) -> CandidateHarvest:
    """Turn one sealed proposer manifest into candidates. Pure, model-free.

    ``contact_records`` are the PROPOSE step receipt's own contact records
    (``ProposerContact.as_json``): identity, the prompt digest and the
    exemplar ids, never the rendered text. ``responses`` maps a sealed
    outputs row's ``sample_id`` to its ``text`` -- so this reads the bundle
    the flight actually sealed, and nothing else.

    Parsing is ``rails.proposer.parse_proposer_response`` (strict JSON, exact
    keys, exact tool set) followed by the family's own constructor, both
    fail-closed; a failure becomes a refusal record naming the draw, the
    reason and the response's sha256, and costs exactly one candidate slot.
    A placebo's answer is parsed by the same strict parser and its ``cue`` is
    DISCARDED rather than stored -- ``placebo_candidate`` refuses to carry
    one by construction, because a placebo that recorded a cue would be a
    second proposer candidate wearing the control's label.
    """

    if isinstance(contact_records, (str, bytes)) or not contact_records:
        raise EvolutionError("contact_records must be a non-empty sequence")
    if not isinstance(responses, Mapping):
        raise EvolutionError("responses must be a mapping of sample id to text")
    if not isinstance(target_tools, Mapping) or not target_tools:
        raise EvolutionError("target_tools must be a non-empty mapping")

    candidates: list[CandidateArtifact] = []
    refusals: list[Mapping[str, object]] = []
    rounds: set[int] = set()
    for record in contact_records:
        if not isinstance(record, Mapping):
            raise EvolutionError("every contact record must be a mapping")
        missing = sorted(
            {"draw_id", "sample_id", "round", "target_id", "family", "k", "prompt_sha256"}
            - set(record)
        )
        if missing:
            raise EvolutionError(f"contact record lacks {missing}")
        draw_id = str(record["draw_id"])
        sample_id = str(record["sample_id"])
        target_id = str(record["target_id"])
        family = str(record["family"])
        rounds.add(int(record["round"]))
        tools = tuple(target_tools.get(target_id, ()))
        if len(tools) < 2:
            raise EvolutionError(
                f"contact {draw_id} names target {target_id!r}, which the supplied "
                "target set does not describe"
            )
        text = responses.get(sample_id)
        if not isinstance(text, str) or not text.strip():
            refusals.append(
                {
                    "draw_id": draw_id,
                    "sample_id": sample_id,
                    "target_id": target_id,
                    "family": family,
                    "k": int(record["k"]),
                    "reason": "the sealed manifest carries no response text for this draw",
                    "response_sha256": None,
                }
            )
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        try:
            cue, descriptions = parse_proposer_response(text, expected_tools=sorted(tools))
            if family == "proposer":
                candidate = proposer_candidate(
                    cue,
                    descriptions,
                    target_id=target_id,
                    round=int(record["round"]),
                    k=int(record["k"]),
                    proposer_prompt_sha256=str(record["prompt_sha256"]),
                    exemplar_ids=tuple(
                        str(value) for value in record.get("exemplar_ids", ())
                    ),
                )
            elif family == "placebo":
                candidate = placebo_candidate(
                    descriptions,
                    target_id=target_id,
                    round=int(record["round"]),
                    k=int(record["k"]),
                    proposer_prompt_sha256=str(record["prompt_sha256"]),
                )
            else:
                raise ProposerError(
                    f"family {family!r} makes no contact and cannot be harvested"
                )
        except ProposerError as error:
            refusals.append(
                {
                    "draw_id": draw_id,
                    "sample_id": sample_id,
                    "target_id": target_id,
                    "family": family,
                    "k": int(record["k"]),
                    "reason": str(error),
                    "response_sha256": digest,
                }
            )
            continue
        candidates.append(candidate)
    if len(rounds) != 1:
        raise EvolutionError(
            f"contact records span rounds {sorted(rounds)}; a harvest is one round's"
        )
    return CandidateHarvest(
        round=rounds.pop(), candidates=tuple(candidates), refusals=tuple(refusals)
    )


def assemble_round_portfolios(
    harvest: CandidateHarvest,
    *,
    incumbent_overrides: Mapping[str, str],
    extra_candidates: Sequence[CandidateArtifact] = (),
) -> dict[int, Portfolio]:
    """The round's portfolios, one per surviving slot ``k``.

    ``extra_candidates`` carries the families that make no contact -- today
    exactly F2, ``rails.proposer.deterministic_candidate``, which the caller
    builds from the registry with zero contacts.

    A target whose slot-``k`` candidate was refused simply does not appear in
    that portfolio's ``chosen`` mapping, so the incumbent's descriptions
    stand for it: preregistration section 5 step 1, stated as code rather
    than as a comment. A slot whose every target was refused would be
    byte-identical to the incumbent arm and is DROPPED rather than flown --
    two arms that are identical on the wire must never look like two
    mechanisms in the ledger.
    """

    if not isinstance(harvest, CandidateHarvest):
        raise EvolutionError("harvest must be a CandidateHarvest")
    if isinstance(extra_candidates, (str, bytes)):
        raise EvolutionError("extra_candidates must be a sequence of CandidateArtifact")
    by_slot: dict[int, dict[str, CandidateArtifact]] = {}
    for candidate in (*harvest.candidates, *extra_candidates):
        if not isinstance(candidate, CandidateArtifact):
            raise EvolutionError("every candidate must be a CandidateArtifact")
        if candidate.round != harvest.round:
            raise EvolutionError(
                f"candidate {candidate.candidate_id} is from round {candidate.round}, "
                f"not this harvest's round {harvest.round}"
            )
        slot = by_slot.setdefault(candidate.k, {})
        if candidate.target_id in slot:
            raise EvolutionError(
                f"two candidates claim target {candidate.target_id!r} in slot "
                f"{candidate.k}"
            )
        slot[candidate.target_id] = candidate
    return {
        k: assemble_portfolio(incumbent_overrides, by_slot[k])
        for k in sorted(by_slot)
        if by_slot[k]
    }


# ---------------------------------------------------------------------------
# The round driver: plan_round / advance_round
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoundStep:
    """One step of a round: what it reads, what it writes, and whether the
    sealed receipts on disk say it has already run."""

    name: str
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    done: bool
    ready: bool
    missing: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "reads": list(self.reads),
            "writes": list(self.writes),
            "done": self.done,
            "ready": self.ready,
            "missing": list(self.missing),
        }


@dataclass(frozen=True)
class RoundPlan:
    """Which step of round ``r`` runs next, and why the others do not."""

    round: int
    steps: tuple[RoundStep, ...]
    next_step: str | None
    blocked_on: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "schema": ROUND_PLAN_SCHEMA,
            "round": self.round,
            "next_step": self.next_step,
            "blocked_on": list(self.blocked_on),
            "steps": [step.as_json() for step in self.steps],
        }


def round_step_paths(round_index: int) -> dict[str, dict[str, tuple[str, ...]]]:
    """The relative artefact names each step of round ``r`` reads and writes.

    Names only, no I/O: :func:`plan_round` takes an ``exists`` predicate so
    the whole plan is a pure function of which receipts are present, and a
    test can drive a full round with no filesystem at all.

    ``<sealed>`` entries are produced by a FLIGHT, not by the driver: the
    driver never contacts the model, so a step that needs a flight's output
    simply waits for it (``blocked_on``).
    """

    if isinstance(round_index, bool) or not isinstance(round_index, int) or round_index < 1:
        raise EvolutionError("round_index must be a positive integer")
    stem = f"round-{round_index:02d}"
    return {
        "propose": {
            "reads": (),
            "writes": (
                f"{stem}/proposer-roster.json",
                f"{stem}/proposer-experiment.json",
                f"{stem}/propose.json",
            ),
        },
        "candidates": {
            "reads": (f"{stem}/propose.json", f"{stem}/proposer-outputs.jsonl"),
            "writes": (
                f"{stem}/candidates.json",
                f"{stem}/fold-a-experiment.json",
            ),
        },
        "select": {
            "reads": (f"{stem}/candidates.json", f"{stem}/fold-a-scores.json"),
            "writes": (
                f"{stem}/selection.json",
                f"{stem}/fold-b-experiment.json",
            ),
        },
        "confirm": {
            "reads": (f"{stem}/selection.json", f"{stem}/fold-b-scores.json"),
            "writes": (
                f"{stem}/confirmation.json",
                f"evolution-round-{round_index:02d}.json",
            ),
        },
    }


def plan_round(
    state: EvolutionState,
    round_index: int,
    *,
    exists: Callable[[str], bool],
) -> RoundPlan:
    """The resumable step list for round ``round_index``. Pure.

    Every step is DONE when all of its own outputs are present, READY when
    every input it reads is present and its predecessor is done, and blocked
    otherwise -- so re-running the driver after an interruption re-enters at
    exactly the first step that has not landed, and a step whose outputs are
    already sealed is never redone.

    ``state`` supplies the round number the loop has actually reached, which
    is checked against ``round_index``: a driver invoked for round 3 while
    the state's history ends at round 1 would otherwise silently skip a
    round's evidence.
    """

    state.validate()
    if not callable(exists):
        raise EvolutionError("exists must be a callable over relative artefact names")
    if (
        isinstance(round_index, bool)
        or not isinstance(round_index, int)
        or round_index != state.round + 1
    ):
        raise EvolutionError(
            f"round_index must be the state's next round ({state.round + 1}); got "
            f"{round_index!r}"
        )

    paths = round_step_paths(round_index)
    steps: list[RoundStep] = []
    predecessor_done = True
    next_step: str | None = None
    blocked_on: tuple[str, ...] = ()
    for name in ROUND_STEPS:
        reads = tuple(paths[name]["reads"])
        writes = tuple(paths[name]["writes"])
        done = bool(writes) and all(exists(path) for path in writes)
        missing = tuple(path for path in reads if not exists(path))
        ready = predecessor_done and not done and not missing
        steps.append(
            RoundStep(
                name=name,
                reads=reads,
                writes=writes,
                done=done,
                ready=ready,
                missing=missing,
            )
        )
        if next_step is None and not done and predecessor_done:
            if ready:
                next_step = name
            else:
                blocked_on = missing
        predecessor_done = predecessor_done and done
    return RoundPlan(
        round=round_index,
        steps=tuple(steps),
        next_step=next_step,
        blocked_on=blocked_on,
    )


def advance_round(
    state: EvolutionState,
    *,
    round_index: int,
    confirmation: ConfirmationDecision,
    assembly: Portfolio | None,
    max_rounds: int = MAX_ROUNDS,
    min_accepted_gain_pp: float = MIN_ACCEPTED_GAIN_PP,
) -> tuple[EvolutionState, RoundOutcome, tuple[bool, str]]:
    """The round's tail, as one pure step: the next incumbent, the outcome
    the stop rule reads, and the stop verdict.

    An ACCEPTED round adopts the assembly's overrides WHOLE (fold B accepts
    the assembly as a whole and never partially, preregistration section 5
    step 6); a rejected round keeps the incumbent unchanged. The gain the
    stop rule reads is the fold-B TARGETED gain in percentage points --
    the same number :class:`ConfirmationDecision` reports -- because that is
    the quantity the round actually confirmed, not the fold-A counts that
    only selected among candidates.
    """

    state.validate()
    if not isinstance(confirmation, ConfirmationDecision):
        raise EvolutionError("confirmation must be a ConfirmationDecision")
    if confirmation.accepted and assembly is None:
        raise EvolutionError(
            "an accepted round must carry the assembly whose overrides become the "
            "next incumbent"
        )
    if assembly is not None and not isinstance(assembly, Portfolio):
        raise EvolutionError("assembly must be a Portfolio or None")
    outcome = RoundOutcome(
        round=round_index,
        accepted=confirmation.accepted,
        gain_pp=float(confirmation.targeted_gain_pp),
        reason=confirmation.reason,
        portfolio_sha256=None if assembly is None else assembly.portfolio_sha256,
    ).validate()
    next_state = state.with_outcome(
        outcome,
        overrides=dict(assembly.overrides) if (confirmation.accepted and assembly) else None,
    )
    stop = should_stop(
        next_state.history,
        max_rounds=max_rounds,
        min_accepted_gain_pp=min_accepted_gain_pp,
    )
    return next_state, outcome, stop


def check_ledger_budget(
    ledger_rows: Sequence[Mapping[str, str]],
    *,
    run_id: str,
    calls: float,
    speech_seconds: float,
) -> dict[str, object]:
    """Refuse to emit a fragment whose flight would exceed its registered row.

    Plan budgets are RUN-CUMULATIVE across every attempt of a run id, so the
    number checked here is the loop's worst case for the whole run id
    (:func:`ledger_budget`), not one round's. ``ledger_rows`` are the parsed
    exposure-ledger rows (``contracts._parse_ledger_tables``); the row must
    exist exactly once, must still read ``consumed = no``, and its ``calls``
    and ``speech audio seconds`` cells are the ceilings.
    """

    if isinstance(ledger_rows, (str, bytes)):
        raise EvolutionError("ledger_rows must be a sequence of parsed ledger rows")
    if not isinstance(run_id, str) or not run_id:
        raise EvolutionError("run_id must be non-empty text")
    matched = [
        row
        for row in ledger_rows
        if isinstance(row, Mapping) and str(row.get("run/experiment id", "")).strip() == run_id
    ]
    if len(matched) != 1:
        raise EvolutionError(
            f"exposure ledger carries {len(matched)} row(s) for run {run_id!r}; exactly "
            "one pre-registered row is required before a fragment is emitted"
        )
    row = matched[0]
    if str(row.get("consumed", "")).strip().lower() != "no":
        raise EvolutionError(
            f"exposure row for run {run_id!r} is not consumed=no; refusing to emit a "
            "fragment for it"
        )

    def _ceiling(column: str) -> float:
        raw = str(row.get(column, "")).strip().replace(",", "")
        try:
            return float(raw)
        except ValueError as error:
            raise EvolutionError(
                f"exposure row for run {run_id!r} has a non-numeric {column!r} cell "
                f"{raw!r}"
            ) from error

    ceilings = {
        "calls": _ceiling("calls"),
        "speech_seconds": _ceiling("speech audio seconds"),
    }
    planned = {"calls": float(calls), "speech_seconds": float(speech_seconds)}
    over = sorted(name for name in ceilings if planned[name] > ceilings[name])
    if over:
        raise EvolutionError(
            f"run {run_id!r} would spend "
            + ", ".join(f"{name}={planned[name]:g} over {ceilings[name]:g}" for name in over)
            + "; the registered ceiling is run-cumulative and is not raised by a driver"
        )
    return {"run_id": run_id, "planned": planned, "ceilings": ceilings, "within": True}
