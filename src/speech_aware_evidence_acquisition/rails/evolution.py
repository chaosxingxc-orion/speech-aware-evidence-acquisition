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
   at least 4 rows, harms at most 1 per 30 rows, and nets at least 3, all
   measured on that target's own rows; the winner is the largest net, ties
   broken by fewer harms, then fewer bytes, then the lowest ``k``.
   :func:`select_per_target`.
5. The winners are assembled into one candidate state and confirmed on fold
   B, as a whole and never partially: the targeted pooled CI90 lower bound
   must exceed 0 AND the background CI90 lower bound must stay at or above
   the tolerance. :func:`confirm_assembly`.
6. ``R_max`` = 4 rounds; stop after two consecutive rejects or an accepted
   gain under 0.5 pp. :func:`should_stop`.

Why the two stages are different statistics, deliberately. Stage one is a
COUNT rule on 20 units per targeted tool (60 per targeted scenario on
EVO-S1, which is why the harm half of the gate is a rate and not a count):
at that n a bootstrap interval says nothing, so the gate is
saves/harms/net, which is exactly the quantity a
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
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..analysis.paired import (
    PairedContrast,
    paired_contrast,
    per_sample_scores_from_score_file,
)
from .hashing import canonical_json_bytes, content_hash
from .proposer import (
    A2T_DESCRIPTIONS_FAMILY,
    DECONTAMINATION_NGRAM,
    NULL_REWRITE_GATE,
    SLURP_SLOT_SCHEMA_FAMILY,
    CandidateArtifact,
    ProposerError,
    candidate_bytes,
    deterministic_candidate,
    null_rewrite_check,
    parse_proposer_response,
    parse_slurp_schema_response,
    placebo_candidate,
    prompt_sha256,
    proposer_candidate,
    proposer_instruction_version,
    render_placebo_instruction,
    render_proposer_instruction,
    render_slurp_proposer_instruction,
    slurp_block_texts,
    slurp_blocks_from_schema,
    slurp_candidate_schema,
    slurp_form_twin_candidate,
    slurp_proposer_candidate,
    slurp_shares_only_candidate,
)

TARGET_SCHEMA = "saea-evolution-target-v1"
PORTFOLIO_SCHEMA = "saea-evolution-portfolio-v1"
SELECTION_SCHEMA = "saea-evolution-selection-v1"
SENTINEL_SCHEMA = "saea-evolution-sentinel-harms-v1"
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

#: Per artifact family, ``(artifact file stem, baseline fragment stem)``.
#: EVO-S1's artifact is a slot SCHEMA, not a registry, and its fragment is a
#: state-fill arm rather than a task-instruction one, so calling either of
#: them ``evolved-registry`` would misname the bytes a reviewer opens.
ARTIFACT_FAMILY_STEMS: Mapping[str, tuple[str, str]] = {
    A2T_DESCRIPTIONS_FAMILY: (ARTIFACT_STEM, FRAGMENT_STEM),
    SLURP_SLOT_SCHEMA_FAMILY: ("evolved-schema", "evolved-slot-schema"),
}

#: The key under which the incumbent arm's score file is looked up during a
#: replay; every other key is the portfolio's ``k`` rendered as text.
INCUMBENT_KEY = "incumbent"

#: What EVO-A1's candidates step records about the decontamination gate. It is
#: a fact about THAT cell -- which registered row, which evaluation text, which
#: legal source of shared phrasing -- so a second cell states its own in its
#: loop config (``LoopConfig.decontamination``) rather than inheriting a
#: paragraph about a tool registry it does not have.
_A2T_DECONTAMINATION_INPUTS: Mapping[str, object] = {
    "row": "SAEA-A2T-MF-EVO-DECONTAMINATION-V1",
    "evaluation_query_texts": "the query text of all 4,000 union rows, opened inside "
    "rails.proposer.validate_candidate_artifact alone and never rendered",
    "registry_text": "the released compact registry, the legal source of shared "
    "phrasing",
    "exemplar_texts": "the construction rows each candidate's proposer was shown; "
    "overlap is measured and reported, never gated",
}

#: What a target IS. ``"contrast"`` is EVO-A1's confusable-tool set (two or
#: more members, by definition); ``"scenario"`` is EVO-S1's stratum (one
#: SLURP scenario, one member).
TARGET_KINDS = ("contrast", "scenario")

#: The two folds, and the fragment-variant label each one's fragments carry.
FOLD_KEYS: Mapping[str, str] = {"fold_a": "fold-a", "fold_b": "fold-b"}

#: Preregistered constants (program section 5).
MAX_ROUNDS = 4
MIN_ACCEPTED_GAIN_PP = 0.5
BACKGROUND_TOLERANCE_PP = -1.0
DEFAULT_SEED = 20260903

#: The rows one tolerated harm is measured against (owner, 2026-09-06). Both
#: harm rules in this module are RATES rather than counts: at most
#: ``harms`` per ``HARMS_PER_ROWS`` rows, floored at the base count so that a
#: small fold is never held to a bound looser than the base. At EVO-A1's
#: 20-row quota the rate reproduces the old absolute rule exactly (20 // 30 =
#: 0, floored to 1); at EVO-S1's 60 rows per scenario it reads 2.
HARMS_PER_ROWS = 30


def harm_allowance(base: int, *, n_rows: int | None, per_rows: int) -> int:
    """How many harms ``base`` per ``per_rows`` rows allows over ``n_rows``.

    ``n_rows is None`` means "the rows are not known here", and the answer is
    the unscaled base -- the strictest reading, so a caller that forgets to
    pass the denominator can only be too harsh, never too lenient.
    """

    if isinstance(base, bool) or not isinstance(base, int) or base < 0:
        raise EvolutionError("a harm base must be a nonnegative integer")
    if isinstance(per_rows, bool) or not isinstance(per_rows, int) or per_rows <= 0:
        raise EvolutionError("harms_per_rows must be a positive integer")
    if n_rows is None:
        return base
    if isinstance(n_rows, bool) or not isinstance(n_rows, int) or n_rows < 0:
        raise EvolutionError("n_rows must be a nonnegative integer or None")
    return max(base, base * (n_rows // per_rows))

__all__ = [
    "TARGET_SCHEMA",
    "PORTFOLIO_SCHEMA",
    "SELECTION_SCHEMA",
    "SENTINEL_SCHEMA",
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
    "HARMS_PER_ROWS",
    "harm_allowance",
    "EvolutionError",
    "Target",
    "TARGET_KINDS",
    "FOLD_KEYS",
    "ARTIFACT_FAMILY_STEMS",
    "assert_disjoint_targets",
    "Portfolio",
    "assemble_portfolio",
    "fragment_stem",
    "write_candidate_fragments",
    "AdmissionGates",
    "CandidateOutcome",
    "StageOneDecision",
    "select_per_target",
    "selection_record",
    "sentinel_harms",
    "ConfirmationDecision",
    "PerTargetHarmBound",
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
    "LoopConfig",
    "plan_round",
    "advance_round",
    "CarrierMaterial",
    "RoundStepResult",
    "STEP_RESULT_SCHEMA",
    "run_propose_step",
    "run_candidates_step",
    "NOISE_FLOOR_SCHEMA",
    "question_sha256",
    "sealed_question_digests",
    "prompt_noise_floor",
    "run_select_step",
    "run_confirm_step",
    "ROUND_STEP_RUNNERS",
    "check_ledger_budget",
]


class EvolutionError(ValueError):
    """An evolution-loop input or decision record is malformed -- fail closed."""


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Target:
    """One TARGET entry: a named, disjoint set of reward-bearing members.

    Two KINDS, and the difference is not cosmetic.

    ``"contrast"`` (EVO-A1's, and the default) is a hand-picked set of
    CONFUSABLE tools. Its whole reason to exist is the separation between its
    members, so a contrast target of one tool is a contradiction and is
    refused.

    ``"scenario"`` (EVO-S1's) is a STRATUM: one SLURP scenario, whose rows are
    the fold rows carrying that gold scenario. There is nothing to separate --
    the eighteen scenarios are disjoint by construction, since every utterance
    has exactly one gold scenario and every intent belongs to exactly one
    scenario -- so a single member is the normal case, not a degenerate one.
    Keying such a target on intents instead would not rescue the two-member
    rule either: ``news`` and ``weather`` own one intent each.
    """

    target_id: str
    tools: tuple[str, ...]
    kind: str = "contrast"

    def validate(self) -> "Target":
        if not isinstance(self.target_id, str) or not self.target_id:
            raise EvolutionError("target_id must be non-empty text")
        if self.kind not in TARGET_KINDS:
            raise EvolutionError(
                f"target {self.target_id!r} kind must be one of {list(TARGET_KINDS)}"
            )
        minimum = 1 if self.kind == "scenario" else 2
        if isinstance(self.tools, (str, bytes)) or len(self.tools) < minimum:
            if minimum == 2:
                raise EvolutionError(
                    f"target {self.target_id!r} must name at least two tools; a target "
                    "of one tool has nothing to separate it from"
                )
            raise EvolutionError(
                f"target {self.target_id!r} must name at least one stratum member"
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
            "kind": self.kind,
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


def _checked_override_value(key: str, value: object, *, label: str) -> object:
    """One artifact override value, WITHOUT deciding which family wrote it.

    EVO-A1's override is one tool DESCRIPTION -- a line of text. EVO-S1's is
    one intent BLOCK (``{"types": [...]}``), because a slot block is a
    structure the renderer turns into text rather than text a candidate
    writes. The incumbent state of an ACCEPTED SLURP round therefore carries
    mappings, and a state object that insisted on text would refuse ``A_1``
    the moment round 1 was accepted -- a failure that would land after the
    fold-B flight had already been paid for.

    What a block MEANS is checked where the family is known
    (``rails.proposer._checked_slurp_blocks``, reached through
    ``slurp_candidate_schema`` on every render), so this refuses only what no
    family can mean: an empty value.
    """

    if isinstance(value, str):
        if not value.strip():
            raise EvolutionError(f"{label} for {key!r} must be non-empty text")
        return value
    if isinstance(value, Mapping) and value:
        return value
    raise EvolutionError(
        f"{label} for {key!r} must be non-empty text (a description) or a non-empty "
        "object (an artifact block)"
    )


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
        _checked_override_value(tool, text, label="incumbent override")
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


def fragment_stem(
    portfolio_sha256: str,
    *,
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY,
    fold: str | None = None,
) -> str:
    """The baseline-fragment name one portfolio gets, as a pure function.

    Deterministic in the portfolio's own content hash, so re-running an
    assembly rewrites the same bytes at the same path and a step that needs to
    NAME a fragment (a cell's ``baseline_fragment``) never has to guess which
    file the writer produced. ``fold`` is EVO-S1's second dimension: a slot
    cell's sealed-intent predecessor differs per fold, so one portfolio has one
    artifact and two fragment variants.

    FLAT names with no path separator, because ``core.config
    ._FRAGMENT_NAME_PATTERN`` refuses one.
    """

    if not isinstance(portfolio_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", portfolio_sha256
    ):
        raise EvolutionError("portfolio_sha256 must be a sha256 hex digest")
    if artifact_family not in ARTIFACT_FAMILY_STEMS:
        raise EvolutionError(f"unknown artifact family {artifact_family!r}")
    stem = f"{ARTIFACT_FAMILY_STEMS[artifact_family][1]}-{portfolio_sha256[:SHA_PREFIX_LENGTH]}"
    if fold is None:
        return stem
    if not isinstance(fold, str) or not re.fullmatch(r"[a-z0-9-]+", fold):
        raise EvolutionError(f"fold {fold!r} is not a plain lower-case name")
    return f"{stem}-{fold}"


def write_candidate_fragments(
    portfolios: Sequence[Portfolio],
    *,
    base_fragment: Mapping[str, object],
    out_dir: Path | str,
    artifact_dir: Path | str,
    artifact_relpath_base: Path | str | None = None,
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY,
    state_fill: str | None = None,
    state_fill_phase: str | None = None,
    fold_variants: Mapping[str, Mapping[str, object]] | None = None,
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

    ``slurp-slot-schema`` (EVO-S1) takes the OTHER consumption path, and the
    difference is a fact about the cell rather than a preference: SLURP reads
    its artifact through ``rails.phase_material``'s per-sample
    ``phase_material.<phase>.state_fill``, not through
    ``task_instruction_fill``, because the block a row is shown depends on
    that row's sealed intent. So the writer sets ``state_fill`` (normally
    ``"slurp-evolved-slot-schema-for-state"``) and that phase's
    ``fill_params`` on a base fragment that must already BE a state-fill arm
    -- ``configs/baseline/slurp-phase-slots-given-intent-schema-v1.json``,
    KC-S1b's own -- so an evolved arm differs from the admitted incumbent by
    the artifact and by nothing else.

    ``fold_variants`` maps a fold name to that fold's
    ``predecessor_source`` object. EVO-S1 needs it because each fold's slot
    cells bind THAT fold's one-time closed-list intent manifest as their
    sealed predecessor: two folds, two manifests, two fragment variants per
    portfolio, and the binding never changes across rounds or candidates.
    """

    if isinstance(portfolios, (str, bytes)) or not portfolios:
        raise EvolutionError("portfolios must be a non-empty sequence")
    if not isinstance(base_fragment, Mapping) or not base_fragment:
        raise EvolutionError("base_fragment must be a non-empty mapping")
    if artifact_family not in ARTIFACT_FAMILY_STEMS:
        raise EvolutionError(f"unknown artifact family {artifact_family!r}")
    artifact_stem, _fragment_stem = ARTIFACT_FAMILY_STEMS[artifact_family]
    state_fill_family = artifact_family != A2T_DESCRIPTIONS_FAMILY
    if state_fill_family:
        if not isinstance(state_fill, str) or not state_fill:
            raise EvolutionError(
                f"a {artifact_family!r} fragment is consumed through a per-sample state "
                "fill; name it"
            )
        if not isinstance(state_fill_phase, str) or not state_fill_phase:
            raise EvolutionError("a state-fill fragment must name the phase it fills")
    elif state_fill is not None or state_fill_phase is not None:
        raise EvolutionError(
            f"a {artifact_family!r} fragment is consumed through task_instruction_fill; "
            "it declares no state fill"
        )
    folds: tuple[tuple[str, Mapping[str, object] | None], ...] = ((("", None)),)
    if fold_variants is not None:
        if not state_fill_family:
            raise EvolutionError("fold variants are a state-fill fragment's shape")
        if not isinstance(fold_variants, Mapping) or not fold_variants:
            raise EvolutionError("fold_variants must be a non-empty mapping")
        folds = tuple(
            (name, fold_variants[name]) for name in sorted(fold_variants)
        )
    for owned in ("task_instruction_fill", "task_instruction_fill_params"):
        if owned in base_fragment and not state_fill_family:
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
        artifact_file = artifact_path / f"{artifact_stem}-{stem}.json"
        artifact_bytes = canonical_json_bytes(overrides)
        artifact_file.write_bytes(artifact_bytes)

        params = {
            "artifact_relpath": _relative_posix(artifact_file, base),
            "artifact_sha256": content_hash(overrides),
            "portfolio_sha256": portfolio.portfolio_sha256,
            "round": portfolio.round,
            "k": portfolio.k,
        }
        for fold_name, predecessor in folds:
            fragment = dict(base_fragment)
            if state_fill_family:
                fragment["phase_material"] = _with_state_fill(
                    base_fragment,
                    phase=str(state_fill_phase),
                    state_fill=str(state_fill),
                    fill_params=params,
                    predecessor_source=predecessor,
                )
            else:
                fragment["task_instruction_fill"] = EVOLVED_FILL_NAME
                fragment["task_instruction_fill_params"] = params
            fragment_file = out_path / (
                fragment_stem(
                    portfolio.portfolio_sha256,
                    artifact_family=artifact_family,
                    fold=fold_name or None,
                )
                + ".json"
            )
            fragment_file.write_text(
                json.dumps(fragment, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            written.append(fragment_file)
    return written


def _with_state_fill(
    base_fragment: Mapping[str, object],
    *,
    phase: str,
    state_fill: str,
    fill_params: Mapping[str, object],
    predecessor_source: Mapping[str, object] | None,
) -> dict[str, object]:
    """``base_fragment``'s ``phase_material`` with ONE phase re-pointed at the
    evolved artifact, and everything else left exactly as the base has it.

    Fail-closed on a base that is not already a state-fill arm of that phase:
    the evolved fragment has to differ from the admitted incumbent by the
    artifact alone, so a base without the phase, without a ``state_fill``, or
    without the ``sealed-manifest`` predecessor a state fill reads is a
    different arm and is refused rather than repaired.
    """

    material = base_fragment.get("phase_material")
    if not isinstance(material, Mapping) or phase not in material:
        raise EvolutionError(
            f"base_fragment declares no phase_material[{phase!r}]; a state-fill "
            "fragment is written from the arm that already carries that phase"
        )
    entry = material[phase]
    if not isinstance(entry, Mapping):
        raise EvolutionError(f"phase_material[{phase!r}] must be an object")
    if not entry.get("state_fill"):
        raise EvolutionError(
            f"base_fragment phase_material[{phase!r}] declares no state_fill; the "
            "evolved arm must differ from the incumbent by the artifact alone"
        )
    # The base MAY carry fill_params, and EVO-S1's does: the projection its
    # fold arms select their block through is declared once, on the base, so
    # the incumbent arm and every candidate arm of that fold read the same
    # sealed label. What the base may not do is set a key this writer owns --
    # silently replacing the artifact binding would hide which arm flew.
    inherited = entry.get("fill_params") or {}
    if not isinstance(inherited, Mapping):
        raise EvolutionError(
            f"base_fragment phase_material[{phase!r}] fill_params must be an object"
        )
    collisions = sorted(set(inherited) & set(fill_params))
    if collisions:
        raise EvolutionError(
            f"base_fragment phase_material[{phase!r}] fill_params already set "
            f"{collisions}; this writer owns those keys and will not silently replace a "
            "caller's binding"
        )
    if predecessor_source is not None and entry.get("predecessor_binding") != (
        "sealed-manifest"
    ):
        raise EvolutionError(
            f"phase_material[{phase!r}] binds "
            f"{entry.get('predecessor_binding')!r}, not 'sealed-manifest'; a per-fold "
            "predecessor variant has nothing to replace"
        )
    updated = {key: dict(value) if isinstance(value, Mapping) else value
               for key, value in material.items()}
    phase_entry = dict(entry)
    phase_entry["state_fill"] = state_fill
    phase_entry["fill_params"] = {**dict(inherited), **dict(fill_params)}
    if predecessor_source is not None:
        phase_entry["predecessor_source"] = dict(predecessor_source)
    updated[phase] = phase_entry
    return updated


# ---------------------------------------------------------------------------
# Stage one: per-target admission on fold A
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdmissionGates:
    """The preregistered stage-one counts (section 5).

    ``saves`` and ``net`` are absolute counts. ``harms`` is a RATE (owner,
    2026-09-06): at most ``harms`` per ``harms_per_rows`` rows of the fold the
    candidate was counted on, never below ``harms`` itself. EVO-A1 counts 20
    rows per target and so still admits at most one harm; EVO-S1 counts 60
    rows per scenario and admits two. The gate that a reviewer recounts by
    hand is therefore (saves, harms allowed at this n, net), and every
    receipt records ``n`` and ``harms_allowed`` beside the raw counts.
    """

    saves: int = 4
    harms: int = 1
    net: int = 3
    harms_per_rows: int = HARMS_PER_ROWS

    def as_json(self) -> dict[str, object]:
        return {
            "saves": self.saves,
            "harms": self.harms,
            "net": self.net,
            "harms_per_rows": self.harms_per_rows,
        }

    def allowed_harms(self, n_rows: int | None) -> int:
        """The harm allowance over ``n_rows`` rows."""

        return harm_allowance(self.harms, n_rows=n_rows, per_rows=self.harms_per_rows)

    def admits(self, *, saves: int, harms: int, n_rows: int | None = None) -> bool:
        return (
            saves >= self.saves
            and harms <= self.allowed_harms(n_rows)
            and (saves - harms) >= self.net
        )


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
    #: The harm rate's answer at this outcome's own ``n``, recorded so the
    #: admission can be recounted from the receipt without the config.
    harms_allowed: int | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "k": self.k,
            "candidate_id": self.candidate_id,
            "n": self.n,
            "saves": self.saves,
            "harms": self.harms,
            "harms_allowed": self.harms_allowed,
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

    The harm half of the gate is scaled to each outcome's own paired ``n``
    (``AdmissionGates.harms_per_rows``), so the one gate object reads "at
    most 1 harm" on a 20-row tool fold and "at most 2" on a 60-row scenario
    fold, and two targets of different sizes in the SAME round are read
    differently. The denominator is that contrast's own ``n`` and nothing
    wider; a row named by the target but missing from a score file is
    refused outright by ``paired_contrast``, so the allowance can never be
    widened by a hole in the evidence.

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
                    admitted=gates.admits(
                        saves=contrast.saves,
                        harms=contrast.harms,
                        n_rows=contrast.n,
                    ),
                    harms_allowed=gates.allowed_harms(contrast.n),
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


def sentinel_harms(
    incumbent_scores: Mapping[str, Mapping[str, float]],
    portfolio_scores: Mapping[int, Mapping[str, Mapping[str, float]]],
    *,
    sentinel_rows: Mapping[str, Mapping[str, Sequence[str]]],
    metric: str,
) -> dict[str, object]:
    """The per-target SENTINEL-HARMS line (owner decision, 2026-09-06).

    A sentinel row's gold tool is one the corpus cannot give the loop enough
    rows of to reward on, so it never enters stage one's count. It is still
    flown, and it is the cheapest early warning the loop has: a rewrite that
    wins its own pair by breaking the thin tool it was rewritten AGAINST shows
    up here, by tool name and by sample id, one round before the 4,000 would
    show it.

    This REPORTS and never decides. The stage-one gates, the assembly and the
    fold-B confirmation are exactly the preregistered ones; the 4,000 stays
    the harm detector at scale. Counts use the same save / harm / tie sense
    every paired reading in this repository uses, recomputed row by row here
    because the report has to NAME the harmed rows and a bootstrap contrast
    only counts them.
    """

    if not isinstance(metric, str) or not metric:
        raise EvolutionError("metric must be non-empty text")
    if not isinstance(sentinel_rows, Mapping):
        raise EvolutionError("sentinel_rows must be a mapping of target id to tool rows")

    def _score(scores: Mapping[str, Mapping[str, float]], row: str, arm: str) -> float:
        entry = scores.get(row)
        if not isinstance(entry, Mapping) or metric not in entry:
            raise EvolutionError(f"{arm} carries no {metric!r} score for sentinel row {row!r}")
        return float(entry[metric])

    by_target: dict[str, object] = {}
    for target_id in sorted(sentinel_rows):
        tool_of = {
            str(row): str(tool)
            for tool, rows in sentinel_rows[target_id].items()
            for row in rows
        }
        by_k: dict[str, object] = {}
        for slot in sorted(portfolio_scores):
            arm = portfolio_scores[slot]
            harmed: list[dict[str, str]] = []
            saved: list[dict[str, str]] = []
            ties = 0
            for row in sorted(tool_of):
                before = _score(incumbent_scores, row, "the incumbent")
                after = _score(arm, row, f"portfolio k={slot}")
                if after < before:
                    harmed.append({"sample_id": row, "tool": tool_of[row]})
                elif after > before:
                    saved.append({"sample_id": row, "tool": tool_of[row]})
                else:
                    ties += 1
            by_k[str(slot)] = {
                "n": len(tool_of),
                "saves": len(saved),
                "harms": len(harmed),
                "ties": ties,
                "net": len(saved) - len(harmed),
                "harmed": harmed,
                "saved": saved,
            }
        by_target[target_id] = {
            "n": len(tool_of),
            "tools": sorted(sentinel_rows[target_id]),
            "by_k": by_k,
        }
    return {
        "schema": SENTINEL_SCHEMA,
        "metric": metric,
        "rule": (
            "a sentinel row is never a reward row: it is counted in the confirmation's "
            "background bound and reported here by name. This line decides nothing"
        ),
        "rows_of_sentinel_tool": {
            target_id: {
                tool: list(sentinel_rows[target_id][tool])
                for tool in sorted(sentinel_rows[target_id])
            }
            for target_id in sorted(sentinel_rows)
        },
        "by_target": by_target,
    }


# ---------------------------------------------------------------------------
# Stage two: whole-assembly confirmation on fold B
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerTargetHarmBound:
    """EVO-S1's replacement for the background population.

    On SLURP every scenario is a target, so the "150 tools nobody targeted"
    that EVO-A1's background bound watches simply do not exist, and the
    program's -1.0 pp background tolerance has to be transposed. The
    coordinator's transposition, encoded here exactly:

    * ``max_net_harm_rows`` -- for every scenario whose candidate was ADMITTED
      at stage one, on fold B, ``harms - saves <= 1 per harms_per_rows rows``
      on that scenario's own rows (owner, 2026-09-06): 1 at 30 rows, 2 at the
      V2 draw's 60, and never below ``max_net_harm_rows`` itself, so a small
      fold is not held to a looser bound than a large one. A count rule and
      not an interval, because a CI90 over 30 rows of a sparse metric accepts
      everything and a reviewer can recount a count by hand;
    * ``unadmitted_tolerance_pp`` -- for the scenarios NOT admitted, whose
      blocks the assembly leaves at the incumbent, the POOLED paired point
      estimate stays at or above -1.0 pp. Those rows are the nearest thing
      this cell has to a background population, and a rewrite that broke them
      would be breaking rows it did not even claim to change;
    * and, unchanged from EVO-A1, the pooled TARGETED CI90 lower bound above
      zero -- here pooled over the admitted scenarios' rows.
    """

    max_net_harm_rows: int = 1
    unadmitted_tolerance_pp: float = BACKGROUND_TOLERANCE_PP
    harms_per_rows: int = HARMS_PER_ROWS

    def validate(self) -> "PerTargetHarmBound":
        if (
            isinstance(self.max_net_harm_rows, bool)
            or not isinstance(self.max_net_harm_rows, int)
            or self.max_net_harm_rows < 0
        ):
            raise EvolutionError("max_net_harm_rows must be a nonnegative integer")
        if (
            isinstance(self.harms_per_rows, bool)
            or not isinstance(self.harms_per_rows, int)
            or self.harms_per_rows <= 0
        ):
            raise EvolutionError("harms_per_rows must be a positive integer")
        if isinstance(self.unadmitted_tolerance_pp, bool) or not isinstance(
            self.unadmitted_tolerance_pp, (int, float)
        ):
            raise EvolutionError(
                "unadmitted_tolerance_pp must be a number in percentage points"
            )
        return self

    def allowed_net_harm_rows(self, n_rows: int | None) -> int:
        """The net-harm allowance over ``n_rows`` fold-B rows."""

        return harm_allowance(
            self.max_net_harm_rows, n_rows=n_rows, per_rows=self.harms_per_rows
        )

    def as_json(self) -> dict[str, object]:
        return {
            "max_net_harm_rows": self.max_net_harm_rows,
            "unadmitted_tolerance_pp": float(self.unadmitted_tolerance_pp),
            "harms_per_rows": self.harms_per_rows,
        }


@dataclass(frozen=True)
class ConfirmationDecision:
    """The fold-B verdict on one assembled state, as a whole."""

    accepted: bool
    reason: str
    metric: str
    targeted: PairedContrast
    background: PairedContrast | None
    background_tolerance_pp: float
    targeted_gain_pp: float
    background_gain_pp: float
    harm_bound: PerTargetHarmBound | None = None
    per_target: tuple[Mapping[str, object], ...] = ()

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
            "background": None if self.background is None else self.background.as_dict(),
            "harm_bound": None if self.harm_bound is None else self.harm_bound.as_json(),
            "per_target": [dict(record) for record in self.per_target],
        }


def confirm_assembly(
    incumbent_scores: Mapping[str, Mapping[str, float]],
    assembly_scores: Mapping[str, Mapping[str, float]],
    *,
    targeted_rows: Sequence[str],
    background_rows: Sequence[str] = (),
    metric: str,
    strata_of: Callable[[str], str] | None = None,
    seed: int = DEFAULT_SEED,
    background_tolerance: float = BACKGROUND_TOLERANCE_PP,
    n_replicates: int = 10_000,
    metric_is_fraction: bool = True,
    harm_bound: PerTargetHarmBound | None = None,
    rows_of_target: Mapping[str, Sequence[str]] | None = None,
    admitted_targets: Sequence[str] = (),
) -> ConfirmationDecision:
    """Accept the whole assembly, or keep the incumbent -- never partially.

    Two regimes, and which one runs is a fact about the cell rather than a
    knob. Without ``harm_bound`` this is EVO-A1's rule, unchanged. With one it
    is EVO-S1's, where every scenario is a target and there is therefore no
    background population to bound; see :class:`PerTargetHarmBound`, whose
    three parts this function evaluates and reports one by one.

    EVO-A1's rule, two CI90 bounds, both required:

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
    if harm_bound is None:
        if isinstance(background_rows, (str, bytes)) or not background_rows:
            raise EvolutionError("background_rows must be a non-empty sequence of ids")
    else:
        harm_bound.validate()
        if isinstance(background_rows, (str, bytes)):
            raise EvolutionError("background_rows must be a sequence of ids")
        if not isinstance(rows_of_target, Mapping) or not rows_of_target:
            raise EvolutionError(
                "a per-target harm bound needs each target's own fold-B rows"
            )
        if isinstance(admitted_targets, (str, bytes)):
            raise EvolutionError("admitted_targets must be a sequence of target ids")
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
    background = None
    if background_ids:
        background = paired_contrast(
            incumbent_scores,
            assembly_scores,
            metrics=[metric],
            sample_ids=background_ids,
            strata_of=strata_of,
            seed=seed,
            n_replicates=n_replicates,
        )[metric]
    if targeted.bootstrap is None:
        raise EvolutionError("confirmation requires the targeted bootstrap interval")
    scale = 100.0 if metric_is_fraction else 1.0
    targeted_ok = targeted.bootstrap.ci_low > 0.0

    if harm_bound is not None:
        return _confirm_with_harm_bound(
            incumbent_scores,
            assembly_scores,
            targeted=targeted,
            background=background,
            targeted_ok=targeted_ok,
            metric=metric,
            harm_bound=harm_bound,
            rows_of_target=rows_of_target or {},
            admitted_targets=tuple(admitted_targets),
            strata_of=strata_of,
            seed=seed,
            n_replicates=n_replicates,
            scale=scale,
        )

    if background is None or background.bootstrap is None:
        raise EvolutionError("confirmation requires both bootstrap intervals")
    tolerance = background_tolerance / scale
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


def _confirm_with_harm_bound(
    incumbent_scores: Mapping[str, Mapping[str, float]],
    assembly_scores: Mapping[str, Mapping[str, float]],
    *,
    targeted: PairedContrast,
    background: PairedContrast | None,
    targeted_ok: bool,
    metric: str,
    harm_bound: PerTargetHarmBound,
    rows_of_target: Mapping[str, Sequence[str]],
    admitted_targets: Sequence[str],
    strata_of: Callable[[str], str] | None,
    seed: int,
    n_replicates: int,
    scale: float,
) -> ConfirmationDecision:
    """EVO-S1's stage two: the pooled targeted interval plus the three-part
    per-scenario harm bound, each part measured and each part reported.

    Every admitted scenario's own fold-B rows are counted (saves, harms, net,
    delta, and its CI90 -- recorded even though the count rule is what
    decides, so a reviewer can see how uninformative the interval is at 30
    rows). The unadmitted scenarios are pooled into one contrast and read on
    the POINT ESTIMATE.
    """

    per_target: list[dict[str, object]] = []
    admitted = tuple(sorted(set(admitted_targets)))
    unknown = sorted(set(admitted) - set(rows_of_target))
    if unknown:
        raise EvolutionError(f"no fold-B rows supplied for admitted target(s) {unknown}")
    breaches: list[str] = []
    for target_id in admitted:
        rows = tuple(rows_of_target[target_id])
        if not rows:
            raise EvolutionError(f"admitted target {target_id!r} has no fold-B row")
        contrast = paired_contrast(
            incumbent_scores,
            assembly_scores,
            metrics=[metric],
            sample_ids=rows,
            seed=seed,
            n_replicates=n_replicates,
        )[metric]
        net_harm = contrast.harms - contrast.saves
        allowed = harm_bound.allowed_net_harm_rows(contrast.n)
        within = net_harm <= allowed
        per_target.append(
            {
                "target_id": target_id,
                "admitted": True,
                "n": contrast.n,
                "saves": contrast.saves,
                "harms": contrast.harms,
                "ties": contrast.ties,
                "net_harm_rows": net_harm,
                "net_harm_rows_allowed": allowed,
                "delta_pp": contrast.delta * scale,
                "ci90_low_pp": (
                    None if contrast.bootstrap is None else contrast.bootstrap.ci_low * scale
                ),
                "ci90_high_pp": (
                    None if contrast.bootstrap is None else contrast.bootstrap.ci_high * scale
                ),
                "within_harm_bound": within,
            }
        )
        if not within:
            breaches.append(
                f"{target_id} (harms - saves = {net_harm} over {allowed} "
                f"allowed at n = {contrast.n})"
            )

    unadmitted_pp = None if background is None else background.delta * scale
    unadmitted_ok = (
        True
        if background is None
        else unadmitted_pp >= harm_bound.unadmitted_tolerance_pp
    )
    if background is not None:
        per_target.append(
            {
                "target_id": "(unadmitted, pooled)",
                "admitted": False,
                "n": background.n,
                "saves": background.saves,
                "harms": background.harms,
                "ties": background.ties,
                "net_harm_rows": background.harms - background.saves,
                # The unadmitted pool is read on the point estimate, not on a
                # count, so it has no allowance to report.
                "net_harm_rows_allowed": None,
                "delta_pp": unadmitted_pp,
                "ci90_low_pp": (
                    None
                    if background.bootstrap is None
                    else background.bootstrap.ci_low * scale
                ),
                "ci90_high_pp": (
                    None
                    if background.bootstrap is None
                    else background.bootstrap.ci_high * scale
                ),
                "within_harm_bound": unadmitted_ok,
            }
        )

    parts = [
        f"pooled targeted CI90 lower bound {targeted.bootstrap.ci_low * scale:.3f} pp "
        f"{'>' if targeted_ok else 'is not >'} 0",
        (
            f"every admitted scenario within harms - saves <= "
            f"{harm_bound.max_net_harm_rows} per {harm_bound.harms_per_rows} rows"
            if not breaches
            else f"scenario(s) over the harm bound: {', '.join(breaches)}"
        ),
        (
            "no unadmitted scenario flew"
            if background is None
            else (
                f"unadmitted pooled delta {unadmitted_pp:.3f} pp "
                f"{'>=' if unadmitted_ok else '<'} "
                f"{harm_bound.unadmitted_tolerance_pp:.3f} pp"
            )
        ),
    ]
    accepted = bool(targeted_ok and not breaches and unadmitted_ok)
    return ConfirmationDecision(
        accepted=accepted,
        reason="; ".join(parts),
        metric=metric,
        targeted=targeted,
        background=background,
        background_tolerance_pp=float(harm_bound.unadmitted_tolerance_pp),
        targeted_gain_pp=targeted.delta * scale,
        background_gain_pp=0.0 if unadmitted_pp is None else unadmitted_pp,
        harm_bound=harm_bound,
        per_target=tuple(per_target),
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
            _checked_override_value(tool, text, label="override")
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
        saves=int(gates_raw["saves"]),
        harms=int(gates_raw["harms"]),
        net=int(gates_raw["net"]),
        # The harm rate is part of the gate a receipt replays under; defaulted
        # for any record written before the rate existed, where every fold was
        # 20 rows and the rate and the count agree anyway.
        harms_per_rows=int(gates_raw.get("harms_per_rows", HARMS_PER_ROWS)),
    )
    targets_raw = record.get("targets")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise EvolutionError("selection record carries no targets")
    targets = tuple(
        Target(
            target_id=str(item["target_id"]),
            tools=tuple(item["tools"]),
            # A scenario target has ONE member, so a replay that rebuilt it as
            # a contrast would refuse the very receipt it is checking.
            # Defaulted for the landed EVO-A1 records that predate the key.
            kind=str(item.get("kind", "contrast")),
        )
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
    min_members: int = 2,
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

    if isinstance(min_members, bool) or not isinstance(min_members, int) or min_members < 1:
        raise EvolutionError("min_members must be a positive integer")
    for target_id in sorted(target_tools):
        raw_tools = target_tools[target_id]
        tools = tuple(raw_tools)
        if isinstance(raw_tools, (str, bytes)) or len(tools) < min_members:
            raise EvolutionError(
                f"target {target_id!r} must name at least "
                f"{'two tools' if min_members == 2 else 'one stratum member'}"
            )
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
    #: The artifact keys THIS contact asked to be rewritten, in the order the
    #: instruction gave them. EVO-A1: the target's tools. EVO-S1: only the
    #: intents the drawn exemplars actually covered -- a candidate never
    #: rewrites a block it saw no evidence for, so a nine-intent scenario
    #: under M = 8 leaves the uncovered blocks at the incumbent. The harvest
    #: parses a response against exactly this list.
    artifact_keys: tuple[str, ...] = ()

    @property
    def sample_id(self) -> str:
        return self.draw.anchor_sample_id

    @property
    def draw_id(self) -> str:
        """This contact's own stable id. Named on the CONTACT (rather than
        reached through ``contact.draw``) so every construction-visible
        material -- this one and ``rails.stage3_advantage_material
        .AdvantageContact``, which has no ``ProposerDraw`` at all -- answers
        the same accessor for the wire check's own messages."""

        return self.draw.draw_id

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
            "artifact_keys": list(self.artifact_keys),
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
    registry_rows: Sequence[Mapping[str, str]] = (),
    target_tools: Mapping[str, Sequence[str]],
    incumbent_overrides: Mapping[str, object],
    exemplar_rows: Mapping[str, Mapping[str, object]],
    carrier_lock_key: str | None = None,
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY,
    artifact_keys: Mapping[str, Sequence[str]] | None = None,
    slot_schema: object = None,
    unfloored_schema: object = None,
    entity_type_names: Sequence[str] = (),
    min_members: int = 2,
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
    if artifact_family == SLURP_SLOT_SCHEMA_FAMILY:
        return _slurp_proposer_material(
            draws,
            target_tools=target_tools,
            artifact_keys=artifact_keys or target_tools,
            incumbent_overrides=incumbent_overrides,
            exemplar_rows=exemplar_rows,
            slot_schema=slot_schema,
            unfloored_schema=unfloored_schema,
            entity_type_names=entity_type_names,
        )
    if artifact_family != A2T_DESCRIPTIONS_FAMILY:
        raise EvolutionError(f"unknown artifact family {artifact_family!r}")

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
        if len(tools) < min_members:
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
                # A released ``expected_tool_call`` is occasionally NAMESPACED
                # ("smart_home.setApplianceMode(...)") while the row's own
                # ``tool_name`` column is the bare name -- 1 of the 274 V2
                # exemplar rows and 3 of fold A's 424. The manifest's
                # ``tool_name`` is the authority the official scorer itself
                # compares against (``reproduction.a2t_scorer`` scores
                # ``compute_tool_accuracy(predicted, gold.tool_name)``), so the
                # namespace is cosmetic and refusing it would drop a legal
                # exemplar over a released-data quirk. The bare name must still
                # AGREE: a row whose call string names a genuinely different
                # tool (the released tier3_multi_intent:002505 pairs
                # ``updateFirmware`` with a ``setTargetTemperature`` call) is
                # still refused, because the exemplar block groups by tool and
                # such a row would teach the wrong grouping.
                if head.rsplit(".", 1)[-1] != row["tool_name"]:
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
                artifact_keys=tuple(sorted(tools)),
            )
        )

    return ProposerMaterial(
        contacts=tuple(contacts),
        bound_targets=tuple(
            {"sample_id": sample_id, "target": bound[sample_id]}
            for sample_id in sorted(bound)
        ),
    )


def _slurp_proposer_material(
    draws: Sequence[ProposerDraw],
    *,
    target_tools: Mapping[str, Sequence[str]],
    artifact_keys: Mapping[str, Sequence[str]],
    incumbent_overrides: Mapping[str, object],
    exemplar_rows: Mapping[str, Mapping[str, object]],
    slot_schema: object,
    unfloored_schema: object,
    entity_type_names: Sequence[str],
) -> ProposerMaterial:
    """EVO-S1's half of :func:`build_proposer_material`. Pure.

    Three things differ from EVO-A1 and all three are preregistered.

    The exemplars are ``(sample_id, intent, sentence, [(entity type, filler),
    ...])`` rows grouped by INTENT rather than gold calls grouped by tool.

    A contact asks only for the intents its own draw COVERED: section 5's
    "any intent the draw did not cover keeps its incumbent block unchanged",
    which for ``iot`` (nine intents against ``M = 8``) is the difference
    between a candidate grounded in evidence and one inventing a block. The
    covered intents are ordered by the config's own preregistered intent order
    (descending TRAIN mention mass), which is the order the blocks are given
    in and therefore the order they must come back in.

    Every contact declares its own exemplars as its construction targets --
    unlike EVO-A1's placebo, which declares an anchor whose gold it never
    renders -- because EVO-S1's controls make no contact at all.
    """

    if slot_schema is None or unfloored_schema is None:
        raise EvolutionError(
            "the slurp-slot-schema proposer needs A_0 and the unfloored TRAIN table; "
            "every count and share in a rendered block comes from them"
        )
    types = tuple(str(name) for name in entity_type_names)
    if not types:
        raise EvolutionError(
            "the slurp-slot-schema proposer needs the closed entity-type name list"
        )
    incumbent = _checked_slurp_incumbent(incumbent_overrides, slot_schema)

    contacts: list[ProposerContact] = []
    bound: dict[str, str] = {}
    for draw in draws:
        members = tuple(target_tools.get(draw.target_id, ()))
        if not members:
            raise EvolutionError(
                f"draw {draw.draw_id} names target {draw.target_id!r}, which the "
                "supplied target set does not describe"
            )
        if draw.family != "proposer":
            raise EvolutionError(
                f"draw {draw.draw_id} is a {draw.family!r} draw, but every EVO-S1 "
                "control is deterministic and makes no contact"
            )
        declared_intents = tuple(str(key) for key in artifact_keys.get(draw.target_id, ()))
        if not declared_intents:
            raise EvolutionError(
                f"target {draw.target_id!r} declares no intent to rewrite"
            )
        rows: list[tuple[str, str, str, tuple[tuple[str, str], ...]]] = []
        covered: set[str] = set()
        for sample_id in draw.exemplar_ids:
            row = exemplar_rows.get(sample_id)
            if not isinstance(row, Mapping):
                raise EvolutionError(
                    f"no construction row supplied for {sample_id!r}; every exemplar the "
                    "roster names must be resolvable"
                )
            intent = str(row.get("intent", ""))
            sentence = str(row.get("sentence", ""))
            if not intent or not sentence.strip():
                raise EvolutionError(
                    f"construction row {sample_id!r} carries no intent or sentence"
                )
            if intent not in declared_intents:
                raise EvolutionError(
                    f"construction row {sample_id!r} carries intent {intent!r}, which is "
                    f"not one of target {draw.target_id!r}'s intents"
                )
            entities = tuple(
                (str(pair[0]), str(pair[1])) for pair in row.get("entities", ())
            )
            covered.add(intent)
            rows.append((sample_id, intent, sentence, entities))
            bound[sample_id] = intent
        order = tuple(intent for intent in declared_intents if intent in covered)
        if not order:
            raise EvolutionError(
                f"draw {draw.draw_id} covered no intent of target {draw.target_id!r}"
            )
        blocks = slurp_block_texts(slot_schema_for(incumbent, slot_schema, unfloored_schema),
                                   intents=order)
        instruction = render_slurp_proposer_instruction(
            blocks,
            intent_order=order,
            entity_type_names=types,
            exemplars=[row for intent in order for row in rows if row[1] == intent],
            line_caps={
                intent: len(unfloored_schema.intents[intent].types) for intent in order
            },
            scenario=draw.target_id,
            round=draw.round,
            k=draw.k,
        )
        contacts.append(
            ProposerContact(
                draw=draw,
                instruction=instruction,
                prompt_sha256=prompt_sha256(instruction),
                construction_target_ids=tuple(draw.exemplar_ids),
                rendered_exemplar_ids=tuple(draw.exemplar_ids),
                artifact_keys=order,
            )
        )
    return ProposerMaterial(
        contacts=tuple(contacts),
        bound_targets=tuple(
            {"sample_id": sample_id, "target": bound[sample_id]}
            for sample_id in sorted(bound)
        ),
    )


def _checked_slurp_incumbent(
    incumbent_overrides: Mapping[str, object], slot_schema: object
) -> dict[str, object]:
    """``A_r`` as a full block mapping: every intent A_0 carries, overridden
    where an accepted round changed it."""

    blocks = dict(slurp_blocks_from_schema(slot_schema))
    for intent, block in incumbent_overrides.items():
        if intent not in blocks:
            raise EvolutionError(
                f"the incumbent state carries intent {intent!r}, which A_0 does not"
            )
        blocks[intent] = block
    return blocks


def slot_schema_for(blocks: Mapping[str, object], base: object, unfloored: object):
    """The renderable schema of one block mapping -- ``rails.proposer``'s
    builder, re-exported here so the material step reads one name."""

    return slurp_candidate_schema(blocks, unfloored=unfloored, base=base)


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
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY,
    allowed_entity_types: Sequence[str] = (),
    refuse_ngrams: Sequence[str] = (),
    min_members: int = 2,
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
        if len(tools) < min_members:
            raise EvolutionError(
                f"contact {draw_id} names target {target_id!r}, which the supplied "
                "target set does not describe"
            )
        # What this contact ASKED for, which for EVO-S1 is only the intents
        # its own draw covered. Falling back to the target's members keeps a
        # landed EVO-A1 receipt readable, since those records predate the key.
        keys = tuple(str(value) for value in record.get("artifact_keys", ())) or tuple(
            sorted(tools)
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
            if artifact_family == SLURP_SLOT_SCHEMA_FAMILY:
                if family != "proposer":
                    raise ProposerError(
                        f"family {family!r} makes no contact on this carrier and cannot "
                        "be harvested; both EVO-S1 controls are deterministic"
                    )
                candidate = slurp_proposer_candidate(
                    parse_slurp_schema_response(
                        text,
                        expected_intents=keys,
                        allowed_entity_types=allowed_entity_types,
                        refuse_ngrams=refuse_ngrams,
                    ),
                    target_id=target_id,
                    round=int(record["round"]),
                    k=int(record["k"]),
                    proposer_prompt_sha256=str(record["prompt_sha256"]),
                    exemplar_ids=tuple(str(value) for value in record.get("exemplar_ids", ())),
                )
                candidates.append(candidate)
                continue
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


#: EVO-A1's measured V2 fold sizes, which are also
#: :class:`LoopConfig`'s defaults, so that cell's committed config keeps
#: declaring exactly the plan it declared before the fields existed.
A2T_FOLD_ROWS = 404
A2T_FOLD_A_SPEECH_SECONDS = 1913.527
A2T_FOLD_B_SPEECH_SECONDS = 1877.630


@dataclass(frozen=True)
class LoopConfig:
    """Everything one EVO-A1 loop is, as data.

    Read from a committed JSON file (``LoopConfig.from_json``) so the driver
    carries no cell knowledge of its own: the targets, the rosters, the run
    ids, the fragment names and the loop constants are all preregistered
    values, and a driver invocation that wanted different ones would have to
    change a committed file.
    """

    carrier_lock_key: str
    targets: Mapping[str, tuple[str, ...]]
    proposer_run_id: str
    fold_a_run_id: str
    fold_b_run_id: str
    base_fragment: str
    model_fragment: str
    fold_a_dataset_fragment: str
    fold_b_dataset_fragment: str
    metric: str
    scorer_id: str
    # Owner decision 2026-09-06 ("RELAXED with sentinels"): target_id -> the
    # tools of that target whose fold rows are HARM SENTINELS rather than
    # reward rows. The loop still rewrites their descriptions -- they are the
    # tools the model wrongly reaches for -- but the corpus cannot supply
    # enough of their own gold rows to count saves on, so they are excluded
    # from stage one's slice and reported by name in the sentinel-harms line.
    sentinel_tools: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    proposer_slots: tuple[int, ...] = (1, 2, 3)
    placebo_slot: int | None = 5
    deterministic_slot: int = 4
    exemplars_per_tool: int = EXEMPLARS_PER_TOOL
    seed: int = DEFAULT_SEED
    max_rounds: int = MAX_ROUNDS
    gates: AdmissionGates = AdmissionGates()
    #: The rows one tolerated harm is measured against, for BOTH harm rules
    #: (owner, 2026-09-06). One field rather than two, because a cell whose
    #: stage-one and stage-three harm rates disagreed would be reporting two
    #: different definitions of the same word. Stamped onto ``gates`` and
    #: ``harm_bound`` at load, so both objects carry it into their receipts.
    harms_per_rows: int = HARMS_PER_ROWS
    background_tolerance_pp: float = BACKGROUND_TOLERANCE_PP
    n_replicates: int = 10_000
    # -- what a target IS, and what a candidate WRITES ---------------------
    #: ``"contrast"`` (EVO-A1) or ``"scenario"`` (EVO-S1). The kind decides
    #: whether a one-member target is legal and how ``confirm_assembly`` is
    #: bounded; it is config rather than code because both cells fly the same
    #: loop.
    target_kind: str = "contrast"
    artifact_family: str = A2T_DESCRIPTIONS_FAMILY
    #: ``target_id -> the artifact keys that target's candidate rewrites``.
    #: For EVO-A1 that IS ``targets`` (a target's own tools). For EVO-S1 a
    #: target is one SCENARIO -- the stratum its reward rows carry -- while
    #: the artifact is keyed by INTENT, so the two mappings differ and both
    #: are preregistered. Absent means "the same as ``targets``".
    artifact_keys: Mapping[str, tuple[str, ...]] | None = None
    #: EVO-S1's controls are DETERMINISTIC, so the round-1 form twin costs no
    #: contact and must not be planned as a proposer draw.
    deterministic_placebo: bool = False
    #: The SIZE of each fold: rows per pass and speech seconds per pass. They
    #: are what every emitted fragment's ``execution_plan`` is written from
    #: and what :func:`check_ledger_budget` charges against the registered
    #: ceiling, so a cell whose folds are larger than the default would
    #: otherwise declare a plan its own flight exceeds. The defaults ARE
    #: EVO-A1's measured V2 folds, so its committed config stays byte for byte
    #: what it is; EVO-S1 declares 1,080 rows per fold and its own measured
    #: pass durations.
    fold_a_rows: int = A2T_FOLD_ROWS
    fold_a_speech_seconds: float = A2T_FOLD_A_SPEECH_SECONDS
    fold_b_rows: int = A2T_FOLD_ROWS
    fold_b_speech_seconds: float = A2T_FOLD_B_SPEECH_SECONDS
    #: The per-sample state fill an evolved fragment declares, and the phase
    #: that declares it (``rails.phase_material.PHASE_STATE_FILLS``). Only a
    #: state-fill artifact family sets these.
    state_fill: str | None = None
    state_fill_phase: str | None = None
    #: ``fold name -> that fold's sealed predecessor_source object``. EVO-S1's
    #: slot cells bind their fold's one-time closed-list intent manifest, so
    #: one portfolio has two fragment variants and the binding never changes
    #: across rounds or candidates.
    fold_predecessors: Mapping[str, Mapping[str, object]] | None = None
    #: The harm bound that replaces the background population when every
    #: stratum is a target.
    harm_bound: PerTargetHarmBound | None = None
    #: ``A_0``'s pins: the committed receipt's relpath and file sha256, the
    #: floored schema's content hash (the bytes KC-S1b flew), the UNFLOORED
    #: table's content hash, and the TRAIN source identity both were mined
    #: from. Config rather than code, and verified at carrier load
    #: (:meth:`assert_a_0`) rather than merely recorded: round 0 of the curve
    #: is the admitted mechanism only if the loop starts from exactly those
    #: bytes, and the unfloored table -- the sole authority for every count,
    #: every share and every intent's line cap -- was pinned nowhere at all
    #: before the closure row. A mismatch stops the cell.
    a_0: Mapping[str, object] | None = None
    #: What this cell's candidates step records about the decontamination
    #: gate: the registered model-free row and what each of its inputs IS.
    #: Config rather than code because the answer is cell knowledge -- EVO-A1
    #: guards tool-query text against a released registry, EVO-S1 guards
    #: fillers against SLURP devel sentences with A_0's own 1,008 fillers
    #: exempt -- and a receipt that inherited the other cell's paragraph would
    #: describe a gate that never ran. ``ngram`` is added by the code.
    decontamination: Mapping[str, object] | None = None
    #: The reward arm every cell of this loop flies. EVO-A1 flies Audio2Tool's
    #: ``bare-core``; EVO-S1 flies the ``speech-feature-query`` arm KC-S1b
    #: flew, unchanged, because the evolved cell must differ from the admitted
    #: incumbent by the artifact alone.
    arm: str = "bare-core"
    #: The model fragment the PROPOSER cells declare, when it is not the one
    #: the reward cells fly. EVO-A1 leaves it absent and both halves fly
    #: ``model_fragment``, so its committed config and every fragment it emits
    #: are byte for byte unchanged. EVO-S1 cannot: its reward cells are
    #: KC-S1b's arm at ``max_tokens`` 64, while a proposer contact returns a
    #: scenario's whole block set and the preregistration fixes its ceiling at
    #: 1,536 (section 5, "max_tokens 1536"). ``decoding_params`` lives in the
    #: model fragment and ``core.config.compose`` refuses the same key from
    #: two fragments, so the two halves need two fragments and the propose
    #: step has to name the right one.
    proposer_model_fragment: str | None = None
    #: ``{"fold_a"|"fold_b"|"proposer": split id}``. ``core.flight.FlightRuntime.
    #: _prepare`` reads ``values["split_id"]`` off the composed config and no
    #: emitted fragment carried one, so every EVO fragment this module writes was
    #: unflyable -- a defect the model-free steps could not see, because they never
    #: compose. The ids are the rosters' own ``split_name`` values and are config
    #: rather than code because the driver holds no cell knowledge. Absent means the
    #: emitted fragment declares none, which is EVO-A1's committed state today.
    split_ids: Mapping[str, str] | None = None
    receipts_reldir: str = (
        "docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-a1"
    )
    rosters_reldir: str = "docs/receipts/rosters"
    #: The three committed rosters a round resolves: the proposer's exemplar
    #: pool and the two reward folds. Config rather than a loader default, so
    #: a fresh draw (EVO-A1's and EVO-S1's V2 folds, say) is a one-line change
    #: to a committed file and not an edit to a function signature, and a
    #: re-freeze is a config change rather than a code change.
    exemplar_roster_relpath: str = "docs/receipts/rosters/a2t-evo-exemplars-v2.json"
    fold_a_roster_relpath: str = "docs/receipts/rosters/a2t-evo-fold-a-v2.json"
    fold_b_roster_relpath: str = "docs/receipts/rosters/a2t-evo-fold-b-v2.json"
    experiments_reldir: str = "configs/experiment"
    # FLAT, and this is a harness constraint rather than a taste: a config
    # fragment name may carry no path separator (``core.config
    # ._FRAGMENT_NAME_PATTERN``), so a fragment written into a
    # ``configs/baseline/<subdir>/`` tree could never be composed.
    fragment_reldir: str = "configs/baseline"
    artifact_reldir: str = "configs/knowledge/a2t-evo-a1"
    slug: str = "a2t-evo-a1"
    #: What a receipt and a fragment call this cell, and which preregistration
    #: they cite. Config, not code, so the one driver serves both cells.
    cell_label: str = "EVO-A1"
    preregistration: str = (
        "docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md"
    )

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "LoopConfig":
        if not isinstance(document, Mapping) or not document:
            raise EvolutionError("loop config must be a non-empty mapping")
        known = {f.name for f in fields(cls)}
        raw_document = dict(document)
        # EVO-S1 preregisters its draw size as ``exemplars_per_scenario``,
        # because its targets are scenarios and calling it "per tool" there
        # would name a thing that cell does not have. One field, two legal
        # spellings, and never both at once.
        if "exemplars_per_scenario" in raw_document:
            if "exemplars_per_tool" in raw_document:
                raise EvolutionError(
                    "loop config sets both exemplars_per_tool and "
                    "exemplars_per_scenario; they are one field"
                )
            raw_document["exemplars_per_tool"] = raw_document.pop("exemplars_per_scenario")
        unknown = sorted(set(raw_document) - known - {"schema", "note"})
        if unknown:
            raise EvolutionError(f"loop config carries unknown key(s): {unknown}")
        values = {key: raw_document[key] for key in known if key in raw_document}
        for key in ("targets", "artifact_keys"):
            if key in values and values[key] is not None:
                raw = values[key]
                if not isinstance(raw, Mapping) or not raw:
                    raise EvolutionError(
                        f"loop config {key} must be a non-empty mapping"
                    )
                values[key] = {
                    str(name): tuple(str(item) for item in items)
                    for name, items in raw.items()
                }
        # A sentinel mapping MAY be empty -- that is the V1 reading, and the
        # loop it describes has no sentinel at all -- so it is parsed apart
        # from the non-empty targets/artifact_keys above.
        if "sentinel_tools" in values:
            raw = values["sentinel_tools"]
            if not isinstance(raw, Mapping):
                raise EvolutionError("loop config sentinel_tools must be a mapping")
            values["sentinel_tools"] = {
                str(name): tuple(str(tool) for tool in tools)
                for name, tools in raw.items()
            }
        for key in ("proposer_slots",):
            if key in values:
                values[key] = tuple(int(slot) for slot in values[key])
        # The harm rate is declared ONCE, at the top level, and stamped onto
        # both harm rules below. A config that hid a second spelling of it
        # inside ``gates`` or ``harm_bound`` would silently be ignored, so
        # refuse it instead.
        per_rows = values.get("harms_per_rows", HARMS_PER_ROWS)
        if isinstance(per_rows, bool) or not isinstance(per_rows, int) or per_rows <= 0:
            raise EvolutionError("loop config harms_per_rows must be a positive integer")
        values["harms_per_rows"] = per_rows
        if "gates" in values:
            raw = values["gates"]
            unknown_gate_keys = sorted(set(raw) - {"saves", "harms", "net"})
            if unknown_gate_keys:
                raise EvolutionError(
                    f"loop config gates carries unknown key(s): {unknown_gate_keys}; "
                    "the harm rate is the top-level harms_per_rows"
                )
            values["gates"] = AdmissionGates(
                saves=int(raw["saves"]),
                harms=int(raw["harms"]),
                net=int(raw["net"]),
                harms_per_rows=per_rows,
            )
        else:
            values["gates"] = AdmissionGates(harms_per_rows=per_rows)
        if values.get("harm_bound") is not None:
            raw = values["harm_bound"]
            if not isinstance(raw, Mapping):
                raise EvolutionError("loop config harm_bound must be an object")
            unknown_bound_keys = sorted(
                set(raw) - {"max_net_harm_rows", "unadmitted_tolerance_pp"}
            )
            if unknown_bound_keys:
                raise EvolutionError(
                    f"loop config harm_bound carries unknown key(s): "
                    f"{unknown_bound_keys}; the harm rate is the top-level "
                    "harms_per_rows"
                )
            values["harm_bound"] = PerTargetHarmBound(
                max_net_harm_rows=int(raw.get("max_net_harm_rows", 1)),
                unadmitted_tolerance_pp=float(
                    raw.get("unadmitted_tolerance_pp", BACKGROUND_TOLERANCE_PP)
                ),
                harms_per_rows=per_rows,
            ).validate()
        config = cls(**values)
        if config.target_kind not in TARGET_KINDS:
            raise EvolutionError(
                f"loop config target_kind must be one of {list(TARGET_KINDS)}"
            )
        if config.artifact_family not in ARTIFACT_FAMILY_STEMS:
            raise EvolutionError(
                f"loop config artifact_family must be one of "
                f"{sorted(ARTIFACT_FAMILY_STEMS)}"
            )
        if config.artifact_keys is not None and set(config.artifact_keys) != set(
            config.targets
        ):
            raise EvolutionError(
                "loop config artifact_keys must name exactly the same targets as "
                "targets"
            )
        if (config.artifact_family != A2T_DESCRIPTIONS_FAMILY) != bool(config.state_fill):
            raise EvolutionError(
                "a state-fill artifact family declares a state_fill and no other family "
                "may; this config disagrees with itself"
            )
        if config.fold_predecessors is not None and set(config.fold_predecessors) != set(
            FOLD_KEYS.values()
        ):
            raise EvolutionError(
                f"loop config fold_predecessors must name exactly "
                f"{sorted(FOLD_KEYS.values())}"
            )
        # ``target_objects`` is the disjointness check for tool targets; a
        # scenario target is a single-member stratum and is disjoint by
        # construction.
        config.target_objects()
        config.assert_sentinels_are_target_tools()
        return config

    def assert_a_0(
        self, *, floored, unfloored, receipt_sha256: str | None = None
    ) -> "LoopConfig":
        """Refuse a round whose ``A_0`` is not the artifact the config pins.

        No-op when the config declares no ``a_0`` block (EVO-A1, whose state
        is the released registry and whose identity the lock already pins).
        For EVO-S1 every declared key is checked against the freshly mined
        schemas, and a disagreement raises: preregistration section 16 open
        point 1 makes this an engineering step that must actually run, not a
        number transcribed into a document.
        """

        if not self.a_0:
            return self
        pins = dict(self.a_0)
        measured = {
            "content_hash": floored.content_hash(),
            "unfloored_content_hash": unfloored.content_hash(),
            "source_identity_hash": floored.source_identity_hash,
            "utterance_count": floored.utterance_count,
        }
        if receipt_sha256 is not None:
            measured["receipt_sha256"] = receipt_sha256
        if unfloored.source_identity_hash != floored.source_identity_hash:
            raise EvolutionError(
                "the floored and unfloored TRAIN minings read different corpora; "
                "A_0 cannot be closed"
            )
        wrong = sorted(
            key
            for key, value in pins.items()
            if key in measured and measured[key] != value
        )
        if wrong:
            raise EvolutionError(
                "A_0 does not reproduce the pinned artifact: "
                + "; ".join(f"{key} is {measured[key]!r}, pinned {pins[key]!r}" for key in wrong)
                + ". Round 0 of the curve is the admitted mechanism only if the loop "
                "starts from exactly those bytes; the cell stops here"
            )
        return self

    def assert_sentinels_are_target_tools(self) -> "LoopConfig":
        """A sentinel is a MEMBER of the target it guards, never a stranger.

        The loop rewrites a sentinel tool's description because the model
        wrongly reaches for it, so it has to be inside the target's tool list;
        naming one that is not would silently score rows no candidate could
        ever move.
        """

        for target_id, sentinels in self.sentinel_tools.items():
            if target_id not in self.targets:
                raise EvolutionError(
                    f"sentinel_tools names target {target_id!r}, which is not a target"
                )
            stray = sorted(set(sentinels) - set(self.targets[target_id]))
            if stray:
                raise EvolutionError(
                    f"target {target_id!r} declares sentinel tool(s) {stray} it does not "
                    "itself carry"
                )
            if set(sentinels) == set(self.targets[target_id]):
                raise EvolutionError(
                    f"target {target_id!r} is all sentinels; it has no reward row and "
                    "must be dropped before the round, not silently"
                )
        return self

    def reward_tools(self, target_id: str) -> tuple[str, ...]:
        """One target's tools MINUS its sentinels: the rows stage one counts."""

        sentinels = set(self.sentinel_tools.get(target_id, ()))
        return tuple(tool for tool in self.targets[target_id] if tool not in sentinels)

    def target_objects(self) -> tuple[Target, ...]:
        return assert_disjoint_targets(
            [
                Target(target_id=key, tools=tools, kind=self.target_kind)
                for key, tools in sorted(self.targets.items())
            ]
        )

    def split_id_for(self, which: str) -> str | None:
        """The split id one emitted fragment declares, or ``None``.

        ``which`` is ``"fold_a"``, ``"fold_b"`` or ``"proposer"``. A config that
        declares the mapping must name every one it uses: a silently missing id
        would produce a fragment that composes and then dies at preflight, which is
        exactly the failure this field exists to remove.
        """

        if self.split_ids is None:
            return None
        if which not in self.split_ids:
            raise EvolutionError(
                f"loop config split_ids declares no {which!r}; it must name every "
                "population this loop emits a fragment for"
            )
        value = self.split_ids[which]
        if not isinstance(value, str) or not value:
            raise EvolutionError(f"loop config split_ids[{which!r}] must be non-empty text")
        return value

    def fold_name(self, which: str) -> str | None:
        """The fragment-variant label of ``"fold_a"`` / ``"fold_b"``, or
        ``None`` when this loop writes one fragment per portfolio.

        A cell whose arm binds a SEALED predecessor per fold (EVO-S1's slot
        cells, each bound to that fold's one-time closed-list intent manifest)
        needs one fragment per fold; a cell whose arm is fold-independent
        (EVO-A1's) needs one, and naming a fold in its fragment would suggest
        a difference that is not there.
        """

        if which not in FOLD_KEYS:
            raise EvolutionError(f"fold key must be one of {list(FOLD_KEYS)}")
        if self.fold_predecessors is None:
            return None
        name = FOLD_KEYS[which]
        if name not in self.fold_predecessors:
            raise EvolutionError(
                f"loop config fold_predecessors carries no {name!r} entry"
            )
        return name

    def incumbent_fragment(self, which: str) -> str:
        """The baseline fragment the INCUMBENT arm flies on one fold.

        A cell whose arm binds a SEALED predecessor per fold needs one
        incumbent fragment per fold for exactly the reason its candidates need
        one per fold: the fold-B incumbent bound to fold A's intent manifest
        would be flying against another population's sealed rows. So when
        ``fold_predecessors`` is declared, the incumbent's fragment is
        ``<base_fragment>-<fold>`` and both variants are committed beside the
        base; the base itself is the template ``write_candidate_fragments``
        copies and is never flown directly.

        EVO-A1's arm is fold-independent, so it declares no fold predecessors
        and the incumbent flies the base fragment on both folds, unchanged.
        """

        fold = self.fold_name(which)
        return self.base_fragment if fold is None else f"{self.base_fragment}-{fold}"

    def keys_of_target(self, target_id: str) -> tuple[str, ...]:
        """The ARTIFACT keys ``target_id``'s candidate rewrites, in the order
        the proposer instruction shows them.

        EVO-A1: that target's tools. EVO-S1: that scenario's intents, in the
        preregistered descending-TRAIN-mention-mass order the config records,
        which is the order the blocks are given in and the order a response's
        blocks must come back in.
        """

        table = self.artifact_keys if self.artifact_keys is not None else self.targets
        if target_id not in table:
            raise EvolutionError(f"loop config describes no target {target_id!r}")
        return tuple(table[target_id])

    def slots_for_round(self, round_index: int) -> tuple[int, ...]:
        """The proposer slots plus, in round 1 only, the placebo slot.

        Preregistration section 4: ``K_1 = 5`` and ``K_r = 4`` for ``r >= 2``
        -- the round-1 placebo is an EXTRA slot, never a replaced proposer
        draw.
        """

        if round_index == 1 and self.placebo_slot is not None:
            return (*self.proposer_slots, self.placebo_slot)
        return tuple(self.proposer_slots)

    def round_paths(self, round_index: int) -> dict[str, dict[str, tuple[str, ...]]]:
        """The repository-relative artefacts each step of round ``r`` reads
        and writes.

        Names only, no I/O: :func:`plan_round` takes an ``exists`` predicate,
        so the whole plan is a pure function of which artefacts are present
        and a test can drive a full round with no filesystem at all.

        Three of the reads are produced by a FLIGHT, not by the driver -- the
        sealed proposer outputs and the two score indexes. The driver never
        contacts the model, so a step that needs one simply waits for it
        (``RoundPlan.blocked_on``).
        """

        if (
            isinstance(round_index, bool)
            or not isinstance(round_index, int)
            or round_index < 1
        ):
            raise EvolutionError("round_index must be a positive integer")
        stem = f"{self.receipts_reldir}/round-{round_index:02d}"
        experiments = self.experiments_reldir
        return {
            "propose": {
                "reads": (),
                "writes": (
                    f"{self.rosters_reldir}/{self.slug}-proposer-r{round_index:02d}.json",
                    f"{experiments}/{self.slug}-proposer-r{round_index:02d}.json",
                    f"{stem}/propose.json",
                ),
            },
            "candidates": {
                "reads": (f"{stem}/propose.json", f"{stem}/proposer-outputs.jsonl"),
                "writes": (
                    f"{stem}/candidates.json",
                    f"{experiments}/{self.slug}-fold-a-r{round_index:02d}.json",
                ),
            },
            "select": {
                "reads": (f"{stem}/candidates.json", f"{stem}/fold-a-scores.json"),
                "writes": (
                    f"{stem}/selection.json",
                    f"{experiments}/{self.slug}-fold-b-r{round_index:02d}.json",
                ),
            },
            "confirm": {
                "reads": (f"{stem}/selection.json", f"{stem}/fold-b-scores.json"),
                "writes": (
                    f"{stem}/confirmation.json",
                    f"{self.receipts_reldir}/evolution-round-{round_index:02d}.json",
                ),
            },
        }


def plan_round(
    state: EvolutionState,
    round_index: int,
    *,
    paths: Mapping[str, Mapping[str, Sequence[str]]],
    exists: Callable[[str], bool],
) -> RoundPlan:
    """The resumable step list for round ``round_index``. Pure.

    Every step is DONE when all of its own outputs are present, READY when
    every input it reads is present and its predecessor is done, and blocked
    otherwise -- so re-running the driver after an interruption re-enters at
    exactly the first step that has not landed, and a step whose outputs are
    already sealed is never redone.

    ``state`` supplies the round the loop has actually reached, checked
    against ``round_index``: a driver invoked for round 3 while the state's
    history ends at round 1 would otherwise silently skip a round's evidence.
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
    if not isinstance(paths, Mapping) or set(paths) != set(ROUND_STEPS):
        raise EvolutionError(f"paths must name exactly the steps {list(ROUND_STEPS)}")

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
    confirmation: ConfirmationDecision | None,
    assembly: Portfolio | None,
    max_rounds: int = MAX_ROUNDS,
    min_accepted_gain_pp: float = MIN_ACCEPTED_GAIN_PP,
    no_confirmation_reason: str | None = None,
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
    if confirmation is None:
        # A round in which stage one admitted no target never reaches fold B,
        # so there is no interval to read. It is still a completed ROUND with
        # an outcome the stop rule counts -- "two consecutive rejects" must
        # include this one -- so the reason is required rather than invented.
        if not isinstance(no_confirmation_reason, str) or not no_confirmation_reason:
            raise EvolutionError(
                "a round with no confirmation must state why it never flew one"
            )
        if assembly is not None:
            raise EvolutionError(
                "an assembly was built but no confirmation was read; a flown assembly "
                "must be confirmed or the round is not a round"
            )
        accepted, gain_pp, reason = False, 0.0, no_confirmation_reason
    else:
        if not isinstance(confirmation, ConfirmationDecision):
            raise EvolutionError("confirmation must be a ConfirmationDecision")
        if no_confirmation_reason is not None:
            raise EvolutionError(
                "no_confirmation_reason is only for a round that read no confirmation"
            )
        if confirmation.accepted and assembly is None:
            raise EvolutionError(
                "an accepted round must carry the assembly whose overrides become the "
                "next incumbent"
            )
        accepted = confirmation.accepted
        gain_pp = float(confirmation.targeted_gain_pp)
        reason = confirmation.reason
    if assembly is not None and not isinstance(assembly, Portfolio):
        raise EvolutionError("assembly must be a Portfolio or None")
    outcome = RoundOutcome(
        round=round_index,
        accepted=accepted,
        gain_pp=gain_pp,
        reason=reason,
        portfolio_sha256=None if assembly is None else assembly.portfolio_sha256,
    ).validate()
    next_state = state.with_outcome(
        outcome,
        overrides=dict(assembly.overrides) if (accepted and assembly) else None,
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


# ---------------------------------------------------------------------------
# The four steps, as pure functions over sealed receipts
# ---------------------------------------------------------------------------


STEP_RESULT_SCHEMA = "saea-evolution-round-step-v1"


@dataclass(frozen=True)
class CarrierMaterial:
    """Everything a round's steps need from the carrier and the committed
    rosters, resolved ONCE by the driver and handed in.

    Keeping it a plain value object is what makes every step function pure
    and testable with synthetic data: the offline dry run builds one of these
    by hand and drives a whole round with no carrier, no lock and no wav.
    """

    registry_rows: tuple[Mapping[str, str], ...]
    exemplar_pool: Mapping[str, tuple[str, ...]]
    media_facts: Mapping[str, Mapping[str, object]]
    exemplar_rows: Mapping[str, Mapping[str, object]]
    fold_a_rows_of_target: Mapping[str, tuple[str, ...]]
    fold_b_targeted_rows: tuple[str, ...]
    fold_b_background_rows: tuple[str, ...]
    fold_a_strata_of: Callable[[str], str] | None = None
    fold_b_strata_of: Callable[[str], str] | None = None
    #: EVO-S1's own material. ``slot_schema`` is ``A_0`` (the floored TRAIN
    #: schema KC-S1b flew) and ``unfloored_schema`` is the same mining at
    #: ``min_share = 0.0`` -- the only authority for a type's count, its share
    #: and its intent's line cap. ``entity_type_names`` is the closed list the
    #: proposer instruction shows. EVO-A1 leaves all three empty.
    slot_schema: object = None
    unfloored_schema: object = None
    entity_type_names: tuple[str, ...] = ()
    #: Each target's own fold-B rows, which the per-scenario harm bound counts
    #: on. EVO-A1's stage two reads a background population instead and leaves
    #: this empty.
    fold_b_rows_of_target: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    #: EVO-A1's own material: ``target_id -> sentinel tool -> that tool's
    #: fold-A rows``. Empty when the loop declares no sentinel, which is the
    #: V1 reading and EVO-S1's.
    fold_a_sentinel_rows: Mapping[str, Mapping[str, tuple[str, ...]]] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class RoundStepResult:
    """One step's output: documents to write, the state it produced, and the
    summary the driver prints. Nothing here is written by the step itself
    except the two artefact writers the preregistration names
    (:func:`write_candidate_fragments`, :func:`write_round_receipt`), whose
    paths are reported in ``summary``."""

    step: str
    round: int
    documents: Mapping[str, object]
    state: EvolutionState | None
    summary: Mapping[str, object]

    def as_json(self) -> dict[str, object]:
        return {
            "schema": STEP_RESULT_SCHEMA,
            "step": self.step,
            "round": self.round,
            "documents": sorted(self.documents),
            "summary": dict(self.summary),
        }


def _experiment_fragment(
    *,
    config: LoopConfig,
    round_index: int,
    run_id: str,
    profile: str,
    dataset_fragment: str,
    arm: str,
    cells: Sequence[Mapping[str, object]],
    planned_model_calls: int,
    planned_speech_audio_seconds: int,
    planned_gpu_hours: float,
    purpose: str,
    split_id: str | None = None,
) -> dict[str, object]:
    """One composable experiment fragment.

    A fragment declares EXACTLY ONE ``execution_plan``, and that object
    carries the single ``execution_profile`` ``contracts.assert_execution_scope``
    validates (``FlightRuntime._build_execution_plan`` reads
    ``values["execution_plan"]``). That is why the reward flights
    (``baseline-reproduction``) and the proposer contacts
    (``bounded-discovery-probe``) get one fragment each per round rather
    than sharing one: it is a finding about the harness, not a preference.
    """

    document: dict[str, object] = {
        "experiment_id": run_id,
        # ``fragment_kind``, not ``schema``: ``core.config.compose`` refuses the
        # same key from two fragments, and a SLURP dataset fragment is a
        # ``saea-speech-native-runtime-view-v1`` document that declares ``schema``
        # itself. Every hand-written SLURP experiment fragment already spells it
        # this way; the VALUE is unchanged, so provenance reads the same.
        "fragment_kind": "saea-a2t-direct-calibration-experiment-v1",
        "generated_by": "scripts/run_evolution_round.py",
        "round": round_index,
        "purpose": purpose,
        "execution_profile": profile,
        "preregistration": config.preregistration,
        "cells": [dict(cell) for cell in cells],
        "populations": [{"dataset_fragment": dataset_fragment, "arm": arm}],
        "execution_plan": {
            "execution_profile": profile,
            "split_role": "discovery",
            "planned_model_calls": int(planned_model_calls),
            "planned_gpu_hours": float(planned_gpu_hours),
            "planned_speech_audio_seconds": int(planned_speech_audio_seconds),
        },
    }
    # ``FlightRuntime._prepare`` reads this off the COMPOSED config and refuses a
    # fragment set that declares none. It belongs to the experiment fragment
    # because a candidate's baseline fragment is fold-independent by construction
    # (one artifact, two fold variants) while a split id is not.
    if split_id is not None:
        document["split_id"] = split_id
    return document


def run_propose_step(
    state: EvolutionState,
    round_index: int,
    *,
    config: LoopConfig,
    carrier: CarrierMaterial,
    ledger_rows: Sequence[Mapping[str, str]] = (),
    seconds_per_call: float = 0.80,
) -> RoundStepResult:
    """Step (a): the proposer roster receipt and its experiment fragment.

    The draws are planned, the roster is frozen, and every contact is
    RENDERED here so the step receipt can pin each prompt's sha256 -- the
    same digest a candidate id carries, and the same one the flight's own
    wire check recomputes. The rendered text itself never leaves this
    process: ``ProposerContact.as_json`` records identity, counts and
    digests only.
    """

    state.validate()
    paths = config.round_paths(round_index)["propose"]["writes"]
    slots = config.slots_for_round(round_index)
    proposer_slots = tuple(slot for slot in slots if slot != config.placebo_slot)
    # EVO-S1's form twin is a string transformation, not a contact, so it is
    # built in the CANDIDATES step and never planned as a draw here.
    placebo_slot = (
        config.placebo_slot
        if config.placebo_slot in slots and not config.deterministic_placebo
        else None
    )
    min_members = 1 if config.target_kind == "scenario" else 2
    draws = plan_proposer_draws(
        config.targets,
        carrier.exemplar_pool,
        round=round_index,
        proposer_slots=proposer_slots,
        placebo_slot=placebo_slot,
        exemplars_per_tool=config.exemplars_per_tool,
        seed=config.seed,
        min_members=min_members,
    )
    roster = proposer_roster_receipt(
        draws,
        carrier_lock_key=config.carrier_lock_key,
        roster_id=f"{config.slug.upper()}-PROPOSER-R{round_index:02d}",
        media_facts=carrier.media_facts,
        seed=config.seed,
        # Byte-identical to the function's own default for EVO-A1, and it has
        # to be: a receipt that called itself "EVO-A1 proposer draws" on the
        # SLURP cell would name the wrong preregistration to every reviewer
        # who opened it.
        design=(
            f"{config.cell_label} proposer draws: one item per (round, target, family, "
            "k) contact on the text-only 'construction-proposer-text' arm. sample_id is "
            "the draw's anchor construction row; exemplar_ids are the rows whose gold "
            "that contact's rendered instruction shows, in the order it shows them."
        ),
    )
    material = build_proposer_material(
        roster,
        registry_rows=carrier.registry_rows,
        target_tools=config.targets,
        incumbent_overrides=state.incumbent_overrides,
        exemplar_rows=carrier.exemplar_rows,
        carrier_lock_key=config.carrier_lock_key,
        artifact_family=config.artifact_family,
        artifact_keys={
            target_id: config.keys_of_target(target_id) for target_id in config.targets
        },
        slot_schema=carrier.slot_schema,
        unfloored_schema=carrier.unfloored_schema,
        entity_type_names=carrier.entity_type_names,
        min_members=min_members,
    )
    speech_seconds = sum(
        float(carrier.media_facts[draw.anchor_sample_id]["audio_seconds"]) for draw in draws
    )
    budget = check_ledger_budget(
        ledger_rows,
        run_id=config.proposer_run_id,
        calls=len(draws) * config.max_rounds,
        speech_seconds=speech_seconds * config.max_rounds,
    ) if ledger_rows else {"checked": False, "reason": "no ledger rows supplied"}

    fragment = _experiment_fragment(
        config=config,
        round_index=round_index,
        run_id=config.proposer_run_id,
        profile="bounded-discovery-probe",
        dataset_fragment=f"{config.slug}-proposer-r{round_index:02d}",
        arm="construction-proposer-text",
        cells=[
            {
                "cell_id": f"{config.slug}-r{round_index}-{contact.draw.draw_id}",
                "run_id": config.proposer_run_id,
                "attempt_id": f"attempt-r{round_index}-p{contact.draw.target_id}"
                f"-k{contact.draw.k}",
                "arm": "construction-proposer-text",
                "baseline_fragment": f"{config.slug}-proposer",
                "model_fragment": config.proposer_model_fragment or config.model_fragment,
                "factor": (
                    f"{contact.draw.family} draw k={contact.draw.k} for target "
                    f"{contact.draw.target_id}"
                ),
            }
            for contact in material.contacts
        ],
        planned_model_calls=len(draws),
        # NOT zero, and this is a harness fact rather than a claim about
        # audio: ``core.model.FrozenCoreAdapter`` charges the payload's own
        # ``audio_seconds`` against the plan even for a text-only request
        # that sends no audio part, and ``contracts.ExecutionPlan`` refuses a
        # non-positive value outright. The arm still sends no audio; the plan
        # must nevertheless cover the anchors' durations.
        planned_speech_audio_seconds=max(1, int(speech_seconds) + 1),
        planned_gpu_hours=max(len(draws) * seconds_per_call / 3600.0, 0.01),
        purpose=(
            f"{config.cell_label} round {round_index} PROPOSE: one text-only contact per "
            "draw on the "
            "construction-proposer-text arm. Zero audio parts are sent."
        ),
        split_id=config.split_id_for("proposer"),
    )
    # The three keys ``core.flight.runtime._default_construction_material``
    # resolves. They live in the EXPERIMENT fragment, not in the proposer's
    # baseline fragment, because the roster is per ROUND and ``core.config
    # .compose`` refuses the same key from two fragments.
    fragment["construction_proposer_roster_receipt"] = paths[0]
    fragment["construction_proposer_roster_split_identity_hash"] = roster[
        "split_identity_hash"
    ]
    fragment["construction_target_tools"] = {
        key: list(value) for key, value in sorted(config.targets.items())
    }
    # From round 2 the proposer is shown ``A_r`` rather than the released
    # descriptions, and the artifact that IS ``A_r`` is the one the last
    # ACCEPTED round's assembly wrote -- named, like every artifact this
    # module emits, by its portfolio sha256.
    for outcome in reversed(state.history):
        if outcome.accepted and outcome.portfolio_sha256:
            fragment["evolution_incumbent_artifact_relpath"] = (
                f"{config.artifact_reldir}/"
                f"{ARTIFACT_FAMILY_STEMS[config.artifact_family][0]}-"
                f"{outcome.portfolio_sha256[:SHA_PREFIX_LENGTH]}.json"
            )
            break
    receipt = {
        "schema": "saea-evolution-propose-step-v1",
        "round": round_index,
        # Which revision of the rendered instruction produced the prompt
        # digests below. The bytes are inside every candidate id, so a round
        # whose proposer text changed must say so rather than leave two rounds
        # incomparable with nothing in the record to explain it.
        "proposer_instruction_version": proposer_instruction_version(
            config.artifact_family
        ),
        "roster_id": roster["roster_id"],
        "roster_split_identity_hash": roster["split_identity_hash"],
        "incumbent_state_sha256": state.state_sha256(),
        "slots": list(slots),
        "proposer_slots": list(proposer_slots),
        "placebo_slot": placebo_slot,
        "targets": {key: list(value) for key, value in sorted(config.targets.items())},
        "contacts": [contact.as_json() for contact in material.contacts],
        "budget": budget,
    }
    return RoundStepResult(
        step="propose",
        round=round_index,
        documents={paths[0]: roster, paths[1]: fragment, paths[2]: receipt},
        state=None,
        summary={
            "draws": len(draws),
            "roster": paths[0],
            "experiment_fragment": paths[1],
            "next": "fly the proposer cells, then copy the sealed outputs to "
            f"{config.receipts_reldir}/round-{round_index:02d}/proposer-outputs.jsonl",
        },
    )


def _incumbent_artifact(
    state: EvolutionState, *, config: LoopConfig, carrier: CarrierMaterial
) -> dict[str, object]:
    """``A_r`` as a whole artifact mapping in the loop's own family --
    ``{tool: description}`` for ``a2t-descriptions``, ``{intent: block}`` for
    ``slurp-slot-schema``.

    This is the thing the null-rewrite gate compares a candidate against, and
    it is built from the SAME two inputs the round already trusts: the
    committed incumbent state and the carrier's own material. A tool or intent
    no accepted round has touched contributes its released content, which is
    what makes the round-1 case ("the proposer returned A_0's block verbatim")
    a refusal rather than an admission.
    """

    if config.artifact_family == SLURP_SLOT_SCHEMA_FAMILY:
        if carrier.slot_schema is None:
            raise EvolutionError(
                "the null-rewrite gate needs A_0 to render the incumbent's blocks"
            )
        return _checked_slurp_incumbent(state.incumbent_overrides, carrier.slot_schema)
    rows_by_name = {str(row["tool_name"]): row for row in carrier.registry_rows}
    if not rows_by_name:
        raise EvolutionError(
            "the null-rewrite gate needs the registry rows to render the incumbent"
        )
    return dict(
        _incumbent_descriptions(
            rows_by_name, sorted(rows_by_name), state.incumbent_overrides
        )
    )


def run_candidates_step(
    state: EvolutionState,
    round_index: int,
    *,
    config: LoopConfig,
    carrier: CarrierMaterial,
    propose_receipt: Mapping[str, object],
    responses: Mapping[str, str],
    repo_root: Path,
    validator: Callable[[CandidateArtifact], Mapping[str, object]] | None = None,
    ledger_rows: Sequence[Mapping[str, str]] = (),
    fold_a_rows: int | None = None,
    fold_a_speech_seconds: float | None = None,
    seconds_per_call: float = 0.80,
    token_counter: Callable[[str], int] | None = None,
) -> RoundStepResult:
    """Step (b): candidates, portfolios, their committed fragments, and the
    fold-A reward fragment.

    ``validator`` is the decontamination/form gate seam and is deliberately
    OPTIONAL and deliberately not supplied by the driver: the authority on a
    candidate's token count is the serving geometry's own tokenizer
    (preregistration section 3 -- "never price a candidate with an
    estimator"), which is a model-adjacent contact and belongs to the
    prompt-fit row, not to a driver that must make none. When it is supplied
    (the offline dry run does), a candidate it refuses is dropped into the
    refusal record exactly like a parse failure.
    """

    state.validate()
    # The fold's own size, from the committed loop config unless a caller
    # (the offline dry run) overrides it. Config rather than a function
    # default, because these numbers are what the emitted fragment's
    # execution_plan is written from: a SLURP round costed at EVO-A1's 404
    # rows would declare a plan its own 1,080-row flight exceeds.
    fold_a_rows = config.fold_a_rows if fold_a_rows is None else fold_a_rows
    fold_a_speech_seconds = (
        config.fold_a_speech_seconds
        if fold_a_speech_seconds is None
        else fold_a_speech_seconds
    )
    paths = config.round_paths(round_index)["candidates"]["writes"]
    contacts = propose_receipt.get("contacts")
    if not isinstance(contacts, list) or not contacts:
        raise EvolutionError("the propose receipt carries no contact records")
    slurp = config.artifact_family == SLURP_SLOT_SCHEMA_FAMILY
    harvest = harvest_proposer_responses(
        contacts,
        responses,
        target_tools=config.targets,
        artifact_family=config.artifact_family,
        allowed_entity_types=carrier.entity_type_names,
        min_members=1 if config.target_kind == "scenario" else 2,
    )

    # The null-rewrite form gate (track E3e). It runs BEFORE the injected
    # validator and independently of it, because whether a candidate is a
    # rewrite at all is not a question about tokens: it needs no tokenizer, so
    # it must not be reachable only on the flights that supply one.
    incumbent_artifact = _incumbent_artifact(state, config=config, carrier=carrier)
    null_rewrites: list[Mapping[str, object]] = []
    validations: list[Mapping[str, object]] = []
    kept: list[CandidateArtifact] = []
    refusals = list(harvest.refusals)
    for candidate in harvest.candidates:
        stub: dict[str, object] = {
            "draw_id": None,
            "sample_id": None,
            "target_id": candidate.target_id,
            "family": candidate.family,
            "k": candidate.k,
            "response_sha256": None,
        }
        try:
            check = null_rewrite_check(
                candidate,
                incumbent_artifact,
                registry_rows=carrier.registry_rows,
                base=carrier.slot_schema,
                unfloored=carrier.unfloored_schema,
            )
        except (ProposerError, EvolutionError) as error:
            refusals.append({**stub, "reason": f"unrenderable candidate: {error}"})
            continue
        null_rewrites.append(check.as_json())
        if check.null_rewrite:
            refusals.append(
                {**stub, "reason": check.reason, "gate": NULL_REWRITE_GATE}
            )
            continue
        if validator is None:
            kept.append(candidate)
            continue
        try:
            validations.append(dict(validator(candidate)))
        except (ProposerError, EvolutionError) as error:
            refusals.append({**stub, "reason": f"validation refused: {error}"})
            continue
        kept.append(candidate)
    harvest = CandidateHarvest(
        round=harvest.round, candidates=tuple(kept), refusals=tuple(refusals)
    )

    if slurp:
        deterministic = _slurp_control_candidates(
            state,
            round_index,
            config=config,
            carrier=carrier,
            token_counter=token_counter,
        )
    else:
        deterministic = tuple(
            deterministic_candidate(
                carrier.registry_rows,
                config.targets[target_id],
                round=round_index,
                k=config.deterministic_slot,
                target_id=target_id,
            )
            for target_id in sorted(config.targets)
        )
    portfolios = assemble_round_portfolios(
        harvest,
        incumbent_overrides=state.incumbent_overrides,
        extra_candidates=deterministic,
    )
    if not portfolios:
        raise EvolutionError(
            "no portfolio survived: every proposer slot was refused and the "
            "deterministic control produced none either; the round cannot fly"
        )
    base = json.loads(
        (Path(repo_root) / "configs" / "baseline" / f"{config.base_fragment}.json").read_text(
            encoding="utf-8"
        )
    )
    written = write_candidate_fragments(
        [portfolios[k] for k in sorted(portfolios)],
        base_fragment=base,
        out_dir=Path(repo_root) / config.fragment_reldir,
        artifact_dir=Path(repo_root) / config.artifact_reldir,
        artifact_relpath_base=Path(repo_root),
        artifact_family=config.artifact_family,
        state_fill=config.state_fill,
        state_fill_phase=config.state_fill_phase,
        fold_variants=config.fold_predecessors,
    )
    arms = 1 + len(portfolios)
    budget = check_ledger_budget(
        ledger_rows,
        run_id=config.fold_a_run_id,
        calls=arms * fold_a_rows * config.max_rounds,
        speech_seconds=arms * fold_a_speech_seconds * config.max_rounds,
    ) if ledger_rows else {"checked": False, "reason": "no ledger rows supplied"}

    cells = [
        {
            "cell_id": f"{config.slug}-r{round_index}-foldA-incumbent",
            "run_id": config.fold_a_run_id,
            "attempt_id": f"attempt-r{round_index}-i",
            "dataset_fragment": config.fold_a_dataset_fragment,
            "arm": config.arm,
            "baseline_fragment": config.incumbent_fragment("fold_a"),
            "model_fragment": config.model_fragment,
            "factor": "the incumbent A_r, re-flown so this round's pairing is against "
            "its own sealed rows",
        }
    ]
    fold_a = config.fold_name("fold_a")
    fragment_by_slot: dict[str, str] = {}
    for k in sorted(portfolios):
        stem = fragment_stem(
            portfolios[k].portfolio_sha256,
            artifact_family=config.artifact_family,
            fold=fold_a,
        )
        fragment_by_slot[str(k)] = stem
        cells.append(
            {
                "cell_id": f"{config.slug}-r{round_index}-foldA-c{k}",
                "run_id": config.fold_a_run_id,
                "attempt_id": f"attempt-r{round_index}-c{k}",
                "dataset_fragment": config.fold_a_dataset_fragment,
                "arm": config.arm,
                "baseline_fragment": stem,
                "model_fragment": config.model_fragment,
                "factor": f"portfolio k={k}, sha256 {portfolios[k].portfolio_sha256}",
            }
        )
    fragment = _experiment_fragment(
        config=config,
        round_index=round_index,
        run_id=config.fold_a_run_id,
        profile="baseline-reproduction",
        dataset_fragment=config.fold_a_dataset_fragment,
        arm=config.arm,
        cells=cells,
        planned_model_calls=arms * fold_a_rows,
        planned_speech_audio_seconds=int(arms * fold_a_speech_seconds) + 1,
        planned_gpu_hours=max(arms * fold_a_rows * seconds_per_call / 3600.0, 0.01),
        purpose=(
            f"{config.cell_label} round {round_index} FOLD A: the incumbent plus "
            f"{len(portfolios)} "
            "portfolios over the whole fold, one contact per row."
        ),
        split_id=config.split_id_for("fold_a"),
    )
    receipt = {
        "schema": "saea-evolution-candidates-step-v1",
        "round": round_index,
        "incumbent_state_sha256": state.state_sha256(),
        "harvest": harvest.as_json(),
        "null_rewrite_checks": null_rewrites,
        "validations": validations,
        "validation_authority": (
            "the serving geometry's own tokenizer at prompt fit (preregistration "
            "section 12 item 7); this driver makes no contact and prices no candidate"
            if validator is None
            else "an injected token counter supplied by the caller"
        ),
        "decontamination_inputs": {
            **(config.decontamination or _A2T_DECONTAMINATION_INPUTS),
            "ngram": DECONTAMINATION_NGRAM,
        },
        "portfolios": {str(k): portfolios[k].as_json() for k in sorted(portfolios)},
        "fragments": {slot: name for slot, name in sorted(fragment_by_slot.items())},
        "budget": budget,
    }
    return RoundStepResult(
        step="candidates",
        round=round_index,
        documents={paths[0]: receipt, paths[1]: fragment},
        state=None,
        summary={
            "candidates": len(harvest.candidates),
            "refusals": len(harvest.refusals),
            "null_rewrites_refused": sum(
                1 for record in null_rewrites if record["null_rewrite"]
            ),
            "portfolios": sorted(portfolios),
            "fragments": [str(path) for path in written],
            "experiment_fragment": paths[1],
        },
    )


def _slurp_control_candidates(
    state: EvolutionState,
    round_index: int,
    *,
    config: LoopConfig,
    carrier: CarrierMaterial,
    token_counter: Callable[[str], int] | None,
) -> tuple[CandidateArtifact, ...]:
    """EVO-S1's two zero-contact controls, per target.

    F2, the shares-only content floor, in every round. F3, the token-matched
    form twin, in round 1 only and as an EXTRA slot rather than a replaced
    proposer draw -- ``K_1 = 5``, ``K_r = 4``.

    F3 needs a tokenizer, and this module refuses to invent one: the
    preregistration is explicit that the authority is the serving geometry's
    own ``/tokenize`` and that "a candidate that only an estimator admits is
    refused". A round-1 step invoked without one therefore stops and names the
    prompt-fit row rather than pricing a control with a ratio.
    """

    if carrier.slot_schema is None or carrier.unfloored_schema is None:
        raise EvolutionError(
            "the slurp-slot-schema controls need A_0 and the unfloored TRAIN table"
        )
    incumbent = _checked_slurp_incumbent(state.incumbent_overrides, carrier.slot_schema)
    controls: list[CandidateArtifact] = []
    for target_id in sorted(config.targets):
        keys = config.keys_of_target(target_id)
        blocks = {intent: incumbent[intent] for intent in keys}
        controls.append(
            slurp_shares_only_candidate(
                blocks,
                target_id=target_id,
                round=round_index,
                k=config.deterministic_slot,
            )
        )
        if round_index != 1 or config.placebo_slot is None:
            continue
        if token_counter is None:
            raise EvolutionError(
                "round 1's token-matched form twin must be priced on the serving "
                "geometry's own tokenizer (preregistration section 5); supply "
                "token_counter= from the prompt-fit row rather than an estimator"
            )
        controls.append(
            slurp_form_twin_candidate(
                blocks,
                unfloored=carrier.unfloored_schema,
                base=carrier.slot_schema,
                token_counter=token_counter,
                target_id=target_id,
                round=round_index,
                k=config.placebo_slot,
            )
        )
    return tuple(controls)


def run_select_step(
    state: EvolutionState,
    round_index: int,
    *,
    config: LoopConfig,
    carrier: CarrierMaterial,
    candidates_receipt: Mapping[str, object],
    score_files: Mapping[str, Path | str],
    repo_root: Path,
    ledger_rows: Sequence[Mapping[str, str]] = (),
    fold_b_rows: int | None = None,
    fold_b_speech_seconds: float | None = None,
    seconds_per_call: float = 0.80,
) -> RoundStepResult:
    """Step (c): stage one on fold A, the assembly, and the fold-B fragment.

    ``score_files`` maps ``"incumbent"`` and each portfolio's ``k`` rendered
    as text to that arm's sealed ``<job_id>.score.json`` -- the SAME index
    :func:`replay_selection` reads, so a reviewer replays this decision from
    the receipt and those files alone.
    """

    state.validate()
    fold_b_rows = config.fold_b_rows if fold_b_rows is None else fold_b_rows
    fold_b_speech_seconds = (
        config.fold_b_speech_seconds
        if fold_b_speech_seconds is None
        else fold_b_speech_seconds
    )
    paths = config.round_paths(round_index)["select"]["writes"]
    portfolios_raw = candidates_receipt.get("portfolios")
    if not isinstance(portfolios_raw, Mapping) or not portfolios_raw:
        raise EvolutionError("the candidates receipt carries no portfolios")
    harvest_raw = candidates_receipt.get("harvest")
    if not isinstance(harvest_raw, Mapping):
        raise EvolutionError("the candidates receipt carries no harvest")
    candidates_by_target: dict[str, dict[int, CandidateArtifact]] = {}
    for record in harvest_raw.get("candidates", ()):
        artifact = CandidateArtifact(
            candidate_id=str(record["candidate_id"]),
            family=str(record["family"]),
            target_id=str(record["target_id"]),
            round=int(record["round"]),
            k=int(record["k"]),
            descriptions=dict(record["descriptions"]),
            cue=record["cue"],
            proposer_prompt_sha256=record["proposer_prompt_sha256"],
            exemplar_ids=tuple(record["exemplar_ids"]),
            # The family says how to READ ``descriptions`` -- text per tool,
            # or a block object per intent -- so a candidate rebuilt without
            # it is rebuilt as the wrong artifact and refuses its own id.
            # Defaulted for the landed EVO-A1 receipts that predate the key.
            artifact_family=str(
                record.get("artifact_family", A2T_DESCRIPTIONS_FAMILY)
            ),
        ).validate()
        candidates_by_target.setdefault(artifact.target_id, {})[artifact.k] = artifact

    if INCUMBENT_KEY not in score_files:
        raise EvolutionError(f"score_files must map {INCUMBENT_KEY!r} to a score file")
    incumbent_scores = per_sample_scores_from_score_file(
        Path(score_files[INCUMBENT_KEY]), config.scorer_id, [config.metric]
    )
    portfolio_scores: dict[int, Mapping[str, Mapping[str, float]]] = {}
    for key in sorted(portfolios_raw):
        if key not in score_files:
            raise EvolutionError(f"score_files has no entry for portfolio k={key}")
        portfolio_scores[int(key)] = per_sample_scores_from_score_file(
            Path(score_files[key]), config.scorer_id, [config.metric]
        )
    targets = config.target_objects()
    decisions = select_per_target(
        incumbent_scores,
        portfolio_scores,
        targets=targets,
        rows_of_target=carrier.fold_a_rows_of_target,
        metric=config.metric,
        gates=config.gates,
        candidates=candidates_by_target,
        seed=config.seed,
    )
    record = selection_record(
        decisions,
        metric=config.metric,
        scorer_id=config.scorer_id,
        gates=config.gates,
        rows_of_target=carrier.fold_a_rows_of_target,
        targets=targets,
        seed=config.seed,
    )
    sentinels = (
        sentinel_harms(
            incumbent_scores,
            portfolio_scores,
            sentinel_rows=carrier.fold_a_sentinel_rows,
            metric=config.metric,
        )
        if carrier.fold_a_sentinel_rows
        else None
    )
    winners = {
        target_id: decision.winner
        for target_id, decision in decisions.items()
        if decision.winner is not None
    }
    assembly = (
        assemble_portfolio(state.incumbent_overrides, winners) if winners else None
    )
    if assembly is not None:
        base = json.loads(
            (
                Path(repo_root) / "configs" / "baseline" / f"{config.base_fragment}.json"
            ).read_text(encoding="utf-8")
        )
        write_candidate_fragments(
            [assembly],
            base_fragment=base,
            out_dir=Path(repo_root) / config.fragment_reldir,
            artifact_dir=Path(repo_root) / config.artifact_reldir,
            artifact_relpath_base=Path(repo_root),
            artifact_family=config.artifact_family,
            state_fill=config.state_fill,
            state_fill_phase=config.state_fill_phase,
            fold_variants=config.fold_predecessors,
        )
    budget = check_ledger_budget(
        ledger_rows,
        run_id=config.fold_b_run_id,
        calls=2 * fold_b_rows * config.max_rounds,
        speech_seconds=2 * fold_b_speech_seconds * config.max_rounds,
    ) if (ledger_rows and assembly is not None) else {
        "checked": False,
        "reason": "no fold-B flight" if assembly is None else "no ledger rows supplied",
    }

    assembly_fragment = (
        None
        if assembly is None
        else fragment_stem(
            assembly.portfolio_sha256,
            artifact_family=config.artifact_family,
            fold=config.fold_name("fold_b"),
        )
    )
    cells: list[Mapping[str, object]] = []
    if assembly is not None:
        cells = [
            {
                "cell_id": f"{config.slug}-r{round_index}-foldB-incumbent",
                "run_id": config.fold_b_run_id,
                "attempt_id": f"attempt-r{round_index}-i",
                "dataset_fragment": config.fold_b_dataset_fragment,
                "arm": config.arm,
                "baseline_fragment": config.incumbent_fragment("fold_b"),
                "model_fragment": config.model_fragment,
                "factor": "the incumbent on fold B, the confirmation's comparator",
            },
            {
                "cell_id": f"{config.slug}-r{round_index}-foldB-assembly",
                "run_id": config.fold_b_run_id,
                "attempt_id": f"attempt-r{round_index}-a",
                "dataset_fragment": config.fold_b_dataset_fragment,
                "arm": config.arm,
                "baseline_fragment": assembly_fragment,
                "model_fragment": config.model_fragment,
                "factor": "the assembled winners of every admitted target, confirmed as "
                "a WHOLE and never partially",
            },
        ]
    fragment = _experiment_fragment(
        config=config,
        round_index=round_index,
        run_id=config.fold_b_run_id,
        profile="baseline-reproduction",
        dataset_fragment=config.fold_b_dataset_fragment,
        arm=config.arm,
        cells=cells,
        planned_model_calls=max(2 * fold_b_rows, 1),
        planned_speech_audio_seconds=int(2 * fold_b_speech_seconds) + 1,
        planned_gpu_hours=max(2 * fold_b_rows * seconds_per_call / 3600.0, 0.01),
        purpose=(
            f"{config.cell_label} round {round_index} FOLD B: the incumbent and the assembly, "
            "confirmed as a whole."
            if assembly is not None
            else f"{config.cell_label} round {round_index} FOLD B does not fly: stage one admitted no "
            "target, so the round is a reject and the incumbent stands."
        ),
        split_id=config.split_id_for("fold_b"),
    )
    receipt = {
        "schema": "saea-evolution-selection-step-v1",
        "round": round_index,
        "incumbent_state_sha256": state.state_sha256(),
        "selection": record,
        "sentinel_harms": sentinels,
        "assembly": None if assembly is None else assembly.as_json(),
        "assembly_fragment": assembly_fragment,
        "admitted_targets": sorted(winners),
        "winners": {target: winners[target].candidate_id for target in sorted(winners)},
        "flies_fold_b": assembly is not None,
        "budget": budget,
    }
    return RoundStepResult(
        step="select",
        round=round_index,
        documents={paths[0]: receipt, paths[1]: fragment},
        state=None,
        summary={
            "admitted_targets": sorted(winners),
            "flies_fold_b": assembly is not None,
            "experiment_fragment": paths[1],
            "sentinel_harms": (
                {}
                if sentinels is None
                else {
                    target_id: {
                        k: block["harms"]  # type: ignore[index]
                        for k, block in row["by_k"].items()  # type: ignore[index,union-attr]
                    }
                    for target_id, row in sentinels["by_target"].items()  # type: ignore[union-attr]
                }
            ),
        },
    )


#: The round receipt's decoder-noise instrumentation. It is a REPORT and never
#: a rule: no admission, no confirmation and no stop decision reads it. Round 1
#: measured why it has to exist -- of 1,019 fold-B rows whose prompt was
#: byte-identical across the two arms, 286 (28.1 %) came back with different
#: text anyway, and 31 of the 35 rows whose reward moved were of that kind. A
#: round that cannot see that number cannot tell its mechanism from its
#: decoder. Whether the admission rule should change is the OWNER's call and is
#: open; this only makes the quantity visible.
NOISE_FLOOR_SCHEMA = "saea-evolution-prompt-noise-floor-v1"


#: Payload fields that are TRANSPORT and not QUESTION. ``request_id`` is the
#: request's ordinal in its own run and ``decoding_params.id_slot`` is which
#: server slot the scheduler happened to hand it; two arms that asked exactly
#: the same thing differ in both whenever their batches packed differently.
#: Round 1 is the demonstration: of its 1,080 fold-B rows, 820 differ in
#: ``id_slot`` alone and 62 in ``request_id``, while only 61 differ in
#: ``history`` -- the rendered prompt. Comparing whole request digests would
#: therefore have reported 842 "different questions" against the 61 there are.
QUESTION_TRANSPORT_FIELDS = ("request_id",)
QUESTION_TRANSPORT_DECODING_FIELDS = ("id_slot",)


def question_sha256(payload: Mapping[str, object]) -> str:
    """The digest of WHAT one request asked, with the transport envelope
    removed: the whole sealed payload minus :data:`QUESTION_TRANSPORT_FIELDS`
    and minus :data:`QUESTION_TRANSPORT_DECODING_FIELDS` inside
    ``decoding_params``.

    A denylist rather than an allowlist, and deliberately: a field this module
    has never heard of is CONTENT until someone proves it is scheduling, so a
    future addition to the payload widens the "different question" set rather
    than being silently ignored by it.
    """

    if not isinstance(payload, Mapping):
        raise EvolutionError("payload must be a mapping")
    question = {
        key: value
        for key, value in payload.items()
        if key not in QUESTION_TRANSPORT_FIELDS
    }
    decoding = question.get("decoding_params")
    if isinstance(decoding, Mapping):
        question["decoding_params"] = {
            key: value
            for key, value in decoding.items()
            if key not in QUESTION_TRANSPORT_DECODING_FIELDS
        }
    return hashlib.sha256(canonical_json_bytes(question)).hexdigest()


def _sealed_file(
    manifest: Mapping[str, object], manifest_file: Path, key: str
) -> bytes:
    """One file a run manifest names, read and hash-checked against what the
    manifest says it is."""

    named = manifest.get(key)
    if not isinstance(named, Mapping) or not isinstance(named.get("path"), str):
        raise EvolutionError(f"{manifest_file} names no {key} file")
    path = Path(str(named["path"]))
    if not path.is_absolute():
        path = manifest_file.parent / str(named["path"])
    raw = path.read_bytes()
    expected = named.get("sha256")
    measured = hashlib.sha256(raw).hexdigest()
    if isinstance(expected, str) and expected and expected != measured:
        raise EvolutionError(
            f"sealed {key} {path} hashes to {measured}, not the manifest's {expected}"
        )
    return raw


def sealed_question_digests(score_file: Path | str) -> dict[str, tuple[str, str]]:
    """``{sample_id: (question_sha256, response_text_sha256)}`` for one arm.

    Resolved from the SAME file the confirm step already reads: a
    ``<job_id>.score.json`` names its own run manifest, the manifest names its
    ``raw_trace`` and its ``outputs``, and both are hash-checked against the
    manifest before a line is parsed. Nothing is opened that the round did not
    already have to trust.

    The trace is where the QUESTION lives (the ``MODEL_REQUEST`` payload, whose
    ``history`` is the rendered prompt) and the outputs file is where the
    answer's digest lives. Neither the prompt nor the response text leaves this
    function: only two sha256s per row do, which is what keeps a diagnostic off
    the evidence surface.
    """

    score = json.loads(Path(score_file).read_text(encoding="utf-8"))
    if not isinstance(score, Mapping):
        raise EvolutionError(f"{score_file} is not a score document")
    manifest_path = score.get("manifest")
    if not isinstance(manifest_path, str) or not manifest_path:
        raise EvolutionError(f"{score_file} names no run manifest")
    manifest_file = Path(manifest_path)
    if not manifest_file.is_absolute():
        manifest_file = Path(score_file).parent / manifest_path
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise EvolutionError(f"{manifest_file} is not a run manifest")

    questions: dict[str, str] = {}
    for line in _sealed_file(manifest, manifest_file, "raw_trace").decode(
        "utf-8"
    ).splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not str(record.get("record_id", "")).endswith("/request"):
            continue
        payload = record.get("payload", {}).get("payload")
        if not isinstance(payload, Mapping):
            raise EvolutionError(f"{manifest_file} traces a request with no payload")
        sample_id = str(payload.get("sample_id", ""))
        if not sample_id:
            raise EvolutionError(f"{manifest_file} traces a request with no sample id")
        questions[sample_id] = question_sha256(payload)

    digests: dict[str, tuple[str, str]] = {}
    for line in _sealed_file(manifest, manifest_file, "outputs").decode(
        "utf-8"
    ).splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        sample_id = str(row.get("sample_id", ""))
        response = row.get("response_text_sha256")
        if not sample_id or not isinstance(response, str):
            raise EvolutionError(
                f"{manifest_file} seals an output row without a sample id and a "
                "response digest"
            )
        question = questions.get(sample_id)
        if question is None:
            raise EvolutionError(
                f"{manifest_file} seals an output for {sample_id!r} that its own trace "
                "never requested"
            )
        digests[sample_id] = (question, response)
    if not digests:
        raise EvolutionError(f"{manifest_file} seals no output row")
    return digests


def _noise_floor_counts(
    rows: Sequence[str],
    incumbent_digests: Mapping[str, tuple[str, str]],
    arm_digests: Mapping[str, tuple[str, str]],
    incumbent_scores: Mapping[str, Mapping[str, float]],
    arm_scores: Mapping[str, Mapping[str, float]],
    metric: str,
) -> dict[str, object]:
    counts = {
        "rows": 0,
        "changed_prompt_rows": 0,
        "unchanged_prompt_rows": 0,
        "unchanged_prompt_flips": 0,
        "changed_prompt": {"saves": 0, "harms": 0},
        "unchanged_prompt": {"saves": 0, "harms": 0},
    }
    for sample_id in rows:
        left = incumbent_digests.get(sample_id)
        right = arm_digests.get(sample_id)
        if left is None or right is None:
            continue
        counts["rows"] += 1
        unchanged = left[0] == right[0]
        side = "unchanged_prompt" if unchanged else "changed_prompt"
        counts[f"{side}_rows"] += 1
        if unchanged and left[1] != right[1]:
            counts["unchanged_prompt_flips"] += 1
        before = incumbent_scores.get(sample_id, {}).get(metric)
        after = arm_scores.get(sample_id, {}).get(metric)
        if before is None or after is None:
            continue
        if after > before:
            counts[side]["saves"] += 1
        elif after < before:
            counts[side]["harms"] += 1
    return counts


def prompt_noise_floor(
    incumbent_digests: Mapping[str, tuple[str, str]],
    arm_digests: Mapping[str, tuple[str, str]],
    incumbent_scores: Mapping[str, Mapping[str, float]],
    arm_scores: Mapping[str, Mapping[str, float]],
    *,
    metric: str,
    rows: Sequence[str],
    rows_of_target: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, object]:
    """How much of a fold's movement the DECODER can account for.

    Both digest mappings are :func:`sealed_question_digests` output --
    ``{sample_id: (question_sha256, response_text_sha256)}`` -- so "the same
    question" is the sealed payload minus its transport envelope and not the
    whole request digest. A row the two arms asked identically asked the frozen
    core the same thing; greedy decoding at temperature 0 is nevertheless not
    bitwise reproducible across batch compositions, so such a row can still come
    back different, and its reward can still move. Splitting both counts by that
    test is the whole of this function:

    * ``unchanged_prompt_flips`` -- rows the two arms asked identically and
      that answered differently anyway. This is the noise floor;
    * ``changed_prompt`` / ``unchanged_prompt`` saves and harms -- where the
      round's movement actually came from.

    Per target as well as pooled, because a scenario the assembly never touched
    is ALL noise floor by construction and reading it beside a scenario the
    assembly rewrote is the point. Reported, never gated: nothing in
    :func:`confirm_assembly` or :func:`advance_round` reads any of it.
    """

    if not isinstance(metric, str) or not metric:
        raise EvolutionError("metric must be non-empty text")
    report: dict[str, object] = {
        "schema": NOISE_FLOOR_SCHEMA,
        "measured": True,
        "metric": metric,
        "rule": (
            "reported, never gated: no admission, confirmation or stop decision "
            "reads these counts"
        ),
        **_noise_floor_counts(
            tuple(rows),
            incumbent_digests,
            arm_digests,
            incumbent_scores,
            arm_scores,
            metric,
        ),
    }
    report["by_target"] = {
        target_id: _noise_floor_counts(
            tuple(target_rows),
            incumbent_digests,
            arm_digests,
            incumbent_scores,
            arm_scores,
            metric,
        )
        for target_id, target_rows in sorted((rows_of_target or {}).items())
    }
    return report


def run_confirm_step(
    state: EvolutionState,
    round_index: int,
    *,
    config: LoopConfig,
    carrier: CarrierMaterial,
    selection_receipt: Mapping[str, object],
    score_files: Mapping[str, Path | str],
    receipts_dir: Path,
) -> RoundStepResult:
    """Step (d): fold-B confirmation, the next incumbent, the stop rule and
    the round receipt.

    When stage one admitted no target there is no fold-B flight and no
    interval to read: the round is a REJECT on that ground, recorded with
    that reason, and the incumbent stands. That is not a special case bolted
    on -- it is what "accept the assembly as a whole, or keep the incumbent"
    means when there is no assembly.
    """

    state.validate()
    paths = config.round_paths(round_index)["confirm"]["writes"]
    assembly_raw = selection_receipt.get("assembly")
    selection = selection_receipt.get("selection")
    if not isinstance(selection, Mapping):
        raise EvolutionError("the selection receipt carries no selection record")

    assembly = None
    confirmation = None
    noise_floor: dict[str, object] = {
        "schema": NOISE_FLOOR_SCHEMA,
        "measured": False,
        "reason": "stage one admitted no target, so no fold-B pair was flown",
    }
    if isinstance(assembly_raw, Mapping):
        assembly = Portfolio(
            round=int(assembly_raw["round"]),
            k=assembly_raw["k"],
            overrides=dict(assembly_raw["overrides"]),
            candidate_ids=dict(assembly_raw["candidate_ids"]),
            portfolio_sha256=str(assembly_raw["portfolio_sha256"]),
        )
        for key in (INCUMBENT_KEY, "assembly"):
            if key not in score_files:
                raise EvolutionError(f"score_files must map {key!r} to a score file")
        admitted = tuple(
            str(value) for value in selection_receipt.get("admitted_targets", ())
        )
        targeted_rows = carrier.fold_b_targeted_rows
        background_rows = carrier.fold_b_background_rows
        if config.harm_bound is not None:
            # With every stratum a target there is no background population:
            # the targeted rows are the ADMITTED scenarios' own fold-B rows
            # and the "background" is what the assembly left at the incumbent.
            if not carrier.fold_b_rows_of_target:
                raise EvolutionError(
                    "a per-scenario harm bound needs each target's own fold-B rows"
                )
            targeted_rows = tuple(
                sorted(
                    row
                    for target_id in admitted
                    for row in carrier.fold_b_rows_of_target.get(target_id, ())
                )
            )
            background_rows = tuple(
                sorted(
                    row
                    for target_id, rows in carrier.fold_b_rows_of_target.items()
                    if target_id not in admitted
                    for row in rows
                )
            )
        incumbent_rows = per_sample_scores_from_score_file(
            Path(score_files[INCUMBENT_KEY]), config.scorer_id, [config.metric]
        )
        assembly_rows = per_sample_scores_from_score_file(
            Path(score_files["assembly"]), config.scorer_id, [config.metric]
        )
        # The decoder-noise report, from the SAME two score files: each names
        # its run manifest, which names its sealed outputs. It changes no rule
        # and must never stop a round, so a trace this driver cannot resolve is
        # recorded as unmeasured rather than raised.
        try:
            noise_floor = prompt_noise_floor(
                sealed_question_digests(Path(score_files[INCUMBENT_KEY])),
                sealed_question_digests(Path(score_files["assembly"])),
                incumbent_rows,
                assembly_rows,
                metric=config.metric,
                rows=tuple(sorted({*targeted_rows, *background_rows})),
                rows_of_target=carrier.fold_b_rows_of_target or None,
            )
        except (EvolutionError, OSError, ValueError) as error:
            noise_floor = {
                "schema": NOISE_FLOOR_SCHEMA,
                "measured": False,
                "reason": f"the sealed traces could not be read: {error}",
            }
        confirmation = confirm_assembly(
            incumbent_rows,
            assembly_rows,
            targeted_rows=targeted_rows,
            background_rows=background_rows,
            metric=config.metric,
            strata_of=carrier.fold_b_strata_of,
            seed=config.seed,
            background_tolerance=config.background_tolerance_pp,
            n_replicates=config.n_replicates,
            harm_bound=config.harm_bound,
            rows_of_target=carrier.fold_b_rows_of_target or None,
            admitted_targets=admitted,
        )

    next_state, outcome, (stop, stop_reason) = advance_round(
        state,
        round_index=round_index,
        confirmation=confirmation,
        assembly=assembly,
        max_rounds=config.max_rounds,
        no_confirmation_reason=(
            "stage one admitted no target, so no assembly was flown on fold B"
            if confirmation is None
            else None
        ),
    )
    extra = {
        "selection": selection,
        "noise_floor": noise_floor,
        "sentinel_harms": selection_receipt.get("sentinel_harms"),
        "confirmation": None if confirmation is None else confirmation.as_json(),
        "decontamination": selection_receipt.get("decontamination_inputs"),
        "stop": {"stop": stop, "reason": stop_reason},
    }
    receipt_path, receipt_sha256 = write_round_receipt(
        next_state, out_dir=Path(receipts_dir), extra=extra
    )
    document = {
        "schema": "saea-evolution-confirmation-step-v1",
        "round": round_index,
        "accepted": outcome.accepted,
        "gain_pp": outcome.gain_pp,
        "reason": outcome.reason,
        "stop": stop,
        "stop_reason": stop_reason,
        "next_incumbent_state_sha256": next_state.state_sha256(),
        "round_receipt": str(Path(receipt_path).name),
        "round_receipt_sha256": receipt_sha256,
        "confirmation": None if confirmation is None else confirmation.as_json(),
    }
    return RoundStepResult(
        step="confirm",
        round=round_index,
        documents={paths[0]: document},
        state=next_state,
        summary={
            "accepted": outcome.accepted,
            "gain_pp": outcome.gain_pp,
            "unchanged_prompt_flips": noise_floor.get("unchanged_prompt_flips"),
            "stop": stop,
            "stop_reason": stop_reason,
            "round_receipt": str(receipt_path),
            "round_receipt_sha256": receipt_sha256,
        },
    )


#: The four step executors, keyed by step name -- the driver script resolves
#: one of these and nothing else, which is what keeps it under 150 lines and
#: keeps every decision in this module.
ROUND_STEP_RUNNERS: Mapping[str, Callable[..., RoundStepResult]] = {
    "propose": run_propose_step,
    "candidates": run_candidates_step,
    "select": run_select_step,
    "confirm": run_confirm_step,
}
