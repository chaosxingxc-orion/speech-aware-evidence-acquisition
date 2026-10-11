"""The Stage-3 training-free RL algorithm registry (owner decision 101).

Owner decision 101 (2026-09-22, translated): *"in the Stage-3 experiment
set-up, different experiments must explicitly mark which training-free RL they
use; you may explore several groups of training-free RL algorithms."* Recorded
as row 101 of
``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``.

The ruling in this repository's own terms: every Stage-3 cell carries a
``stage3_algorithm`` label at the top level of its EXPERIMENT fragment, that
label's ``id`` resolves in
:data:`~speech_aware_evidence_acquisition.core.base.STAGE3_ALGORITHMS`, and
``scripts/checks/stage3_algorithm_label_check.py`` fails any Stage-3 cell
without one. This module is the canonical registration site for that registry,
exactly as ``core/policies.py`` is for ``POLICIES`` and
``rails/knowledge_index.py`` is for the three index registries -- one Registry
mechanism, no second table.

**Why a record and not a bare id.** A label that only said "GRPO" would not
tell a reader of a verdict table what moved. Each record therefore names the
LOOP OPERATORS the algorithm defines (:data:`STAGE3_OPERATORS`, the vocabulary
decision 101 itself lists: rollout / scoring / credit assignment / update /
selection, plus ``context_application`` for the operator that actually writes
the learned text into a row's context), and a cell's label declares the subset
it USES. A cell that claims an operator its algorithm does not define is a
mislabelled cell and the check refuses it.

**Label shape** (top level of a ``configs/experiment/*.json`` fragment)::

    "stage3_algorithm": {
      "id": "tfgrpo-semantic-advantage-v1",
      "operators_used": ["credit_assignment"],
      "note": "one sentence saying what this cell does with that operator"
    }

**Citations.** Two identifiers are recorded elsewhere in this repository and
are reused verbatim rather than restated from memory: Training-Free GRPO's
``arXiv:2510.08191``
(``docs/readiness/2026-09-11-system-selection-and-training-free-optimization.md``)
and GEPA's ``arXiv:2507.19457``
(``docs/readiness/2026-08-21-speech-native-agent-loop-training-free-rl-plan.md``).
No identifier is recorded anywhere in this repository for ACE, so its citation
is the design spec's own section 6 and nothing is invented here.

Model-free: importing this module contacts nothing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .base import STAGE3_ALGORITHMS, CoreError

#: The loop operators a training-free RL algorithm may define. The first five
#: are decision 101's own vocabulary; ``context_application`` is the sixth
#: because in a training-free loop the "policy update" and the moment that
#: update reaches a row's context are two separable acts -- S3-5 curates the
#: delta store (update) and S3-6's ``context_supply`` route puts deltas into a
#: row (context application) -- and a cell may be one factor on exactly one of
#: them.
STAGE3_OPERATORS: tuple[str, ...] = (
    "rollout",
    "scoring",
    "credit_assignment",
    "update",
    "selection",
    "context_application",
)

#: ``base-loop`` -- implemented for Stage-3 layer A and flown as a registered
#: cell family; ``planned`` -- registered so a fragment may name it, no cell
#: built yet; ``not-applicable`` -- the label a Stage-3 cell that carries NO
#: training-free RL operator wears (a control, contract or pruning cell on the
#: locked plan), which must state its ``reason``.
STAGE3_STATUSES: tuple[str, ...] = ("base-loop", "planned", "not-applicable")

#: The id every Stage-3 cell without a training-free RL operator carries.
NONE_ALGORITHM_ID = "none"

LABEL_KEY = "stage3_algorithm"
_REQUIRED_LABEL_KEYS = frozenset({"id", "note"})
_KNOWN_LABEL_KEYS = frozenset({"id", "operators_used", "note", "columns"})

#: Optional per-column map ``{arm_id: algorithm_id}`` (E-T5, decision 263-A).
#: A cell that flies several columns of different algorithms in one fragment
#: (lock / twin / parent / typed / ACE) labels each column here; the top-level
#: ``id`` stays the cell's own algorithm. Every value must resolve in
#: ``STAGE3_ALGORITHMS``.
COLUMNS_KEY = "columns"


class Stage3AlgorithmError(CoreError):
    """A Stage-3 algorithm record or cell label is malformed or unregistered."""


@dataclass(frozen=True)
class Stage3Algorithm:
    """One registered training-free RL algorithm.

    ``operators`` is what this algorithm DEFINES; a cell's label declares the
    subset it uses. ``reason`` is required of, and only of, the
    ``not-applicable`` record.
    """

    id: str
    family: str
    display_name: str
    citation: str
    operators: tuple[str, ...]
    status: str
    what_it_changes: str
    reason: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "id",
            "family",
            "display_name",
            "citation",
            "what_it_changes",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise Stage3AlgorithmError(
                    f"Stage-3 algorithm record {self.id!r}: {field_name} must be a "
                    "non-empty string"
                )
        if self.status not in STAGE3_STATUSES:
            raise Stage3AlgorithmError(
                f"Stage-3 algorithm record {self.id!r}: status {self.status!r} is not "
                f"one of {list(STAGE3_STATUSES)}"
            )
        if not isinstance(self.operators, tuple):
            raise Stage3AlgorithmError(
                f"Stage-3 algorithm record {self.id!r}: operators must be a tuple"
            )
        unknown = [op for op in self.operators if op not in STAGE3_OPERATORS]
        if unknown:
            raise Stage3AlgorithmError(
                f"Stage-3 algorithm record {self.id!r}: unknown operator(s) {unknown}; "
                f"the vocabulary is {list(STAGE3_OPERATORS)}"
            )
        if len(set(self.operators)) != len(self.operators):
            raise Stage3AlgorithmError(
                f"Stage-3 algorithm record {self.id!r}: operators repeats an entry"
            )
        if self.status == "not-applicable":
            if self.operators:
                raise Stage3AlgorithmError(
                    f"Stage-3 algorithm record {self.id!r}: a not-applicable record "
                    "defines no operator"
                )
            if not isinstance(self.reason, str) or not self.reason.strip():
                raise Stage3AlgorithmError(
                    f"Stage-3 algorithm record {self.id!r}: a not-applicable record "
                    "must state its reason"
                )
        elif self.reason is not None:
            raise Stage3AlgorithmError(
                f"Stage-3 algorithm record {self.id!r}: reason belongs to the "
                "not-applicable record only"
            )
        elif not self.operators:
            raise Stage3AlgorithmError(
                f"Stage-3 algorithm record {self.id!r}: an algorithm defines at least "
                "one operator"
            )


def _register(record: Stage3Algorithm) -> Stage3Algorithm:
    STAGE3_ALGORITHMS.register(record.id, record)
    return record


SYSTEM_TEXT_BLACK_BOX_V1 = _register(
    Stage3Algorithm(
        id="system-text-black-box-v1",
        family="black-box-text-policy-optimization",
        display_name="Whole-system reward-guided joint text-policy iteration",
        citation="docs/readiness/2026-10-01-slurp-system-text-search-v1/README.md",
        operators=("rollout", "scoring", "credit_assignment", "update", "selection", "context_application"),
        status="planned",
        what_it_changes=(
            "Joint English knowledge-construction, supplied knowledge and role-consumption policies. "
            "Complete-system official feedback guides bounded external text updates against a feedback-blind "
            "search. Relative returns describe whole trajectories, not node causal effects or policy gradients; "
            "no parameter training, invented action probabilities or PPO/GRPO claim."
        ),
    )
)

TFGRPO_SEMANTIC_ADVANTAGE_V1 = _register(
    Stage3Algorithm(
        id="tfgrpo-semantic-advantage-v1",
        family="training-free-grpo",
        display_name="Training-Free GRPO (group-relative semantic advantage)",
        citation="arXiv:2510.08191",
        operators=(
            "rollout",
            "scoring",
            "credit_assignment",
            "update",
            "context_application",
        ),
        status="base-loop",
        what_it_changes=(
            "Grouped rollouts are scored per row by the official scorer on copies, the "
            "frozen core states in words what distinguished the best sample from the "
            "worst, and those statements become provenance-tagged experiential deltas "
            "appended to a store and applied to a row by candidate-bound supply."
        ),
    )
)

TFGRPO_SYSTEM_MEMORY_DISJOINT_V1 = _register(
    Stage3Algorithm(
        id="tfgrpo-system-memory-disjoint-v1",
        family="training-free-grpo",
        display_name="Training-Free GRPO adapted to disjoint complete-system rounds",
        citation="docs/readiness/2026-09-26-slurp-system-round-configs.md",
        operators=("rollout", "scoring", "credit_assignment", "update", "context_application"),
        status="planned",
        what_it_changes=(
            "Frozen-core full-system trajectories and official terminal counts feed sealed "
            "summary, semantic comparison, group operations and model-synthesized atomic "
            "batch memory updates. Forward construction cohorts are disjoint; frozen "
            "source-attested guidance is made available through the Reviewer memory tool. "
            "Typed guidance, stable IDs, terminal feedback and disjoint rounds are explicit "
            "repository adaptations. No real update/reexecution cycle or RL benefit is "
            "established; the historical candidate-bound delta route remains closed."
        ),
    )
)


FINITE_ACTION_BANDIT_V1 = _register(
    Stage3Algorithm(
        id="finite-action-bandit-v1",
        family="contextual-bandit",
        display_name="Finite supply action bandit with complete-system returns",
        citation="docs/readiness/2026-09-25-slurp-stage3-finite-policy-design-v1.md",
        operators=("rollout", "scoring", "credit_assignment", "update", "selection"),
        status="planned",
        what_it_changes=(
            "A frozen per-round external value table selects one evidence-supply action "
            "after initial Perception and retains it throughout the ordinary complete "
            "episode. Values update from complete official-count feedback at round "
            "boundaries. This cumulative-mean baseline is MemRL-inspired, not full "
            "MemRL reproduction; no formal algorithm flight has executed yet."
        ),
    )
)

FINITE_SYSTEM_POLICY_BANDIT_V1 = _register(
    Stage3Algorithm(
        id="finite-system-policy-bandit-v1",
        family="finite-policy-bandit",
        display_name="Complete-episode policy bandit with terminal system returns",
        citation="docs/readiness/2026-09-25-system-episode-policy-integration.md",
        operators=("rollout", "scoring", "credit_assignment", "update", "selection"),
        status="planned",
        what_it_changes=(
            "Select a coherent complete native binding before its first role and "
            "retain the choice through final delivery. The initial version uses one "
            "episode-start state, actual logged allocation probabilities, and a frozen "
            "per-round cumulative-mean value table. This is an episode-level bandit "
            "comparator, not multistep RL, TF-GRPO or MemRL reproduction. Only offline "
            "graph and synthetic feedback integration is proven; no algorithm flight "
            "or efficacy claim is admitted."
        ),
    )
)

GEPA_REFLECTIVE_PARETO_V1 = _register(
    Stage3Algorithm(
        id="gepa-reflective-pareto-v1",
        family="gepa",
        display_name="GEPA (reflective Pareto evolution of the context)",
        citation="arXiv:2507.19457",
        operators=("credit_assignment", "update", "selection", "context_application"),
        status="base-loop",
        what_it_changes=(
            "The context/instruction text is mutated by reflecting on execution traces "
            "rather than by a per-row advantage statement, and survivors are chosen by "
            "the per-scenario Pareto frontier over per-row scores instead of by the "
            "best average."
        ),
    )
)

ACE_GROW_REFINE_V1 = _register(
    Stage3Algorithm(
        id="ace-grow-refine-v1",
        family="ace",
        display_name="ACE (agentic context engineering: generator / reflector / curator)",
        citation=(
            "arXiv:2510.04618 (Agentic Context Engineering: generator / reflector / "
            "curator over an evolving playbook); instantiation: docs/superpowers/specs/"
            "2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md section 4"
        ),
        operators=("update", "selection", "context_application"),
        status="planned",
        what_it_changes=(
            "A curator turns reflector output into incremental delta items over an "
            "evolving playbook, growing the store by appended items and refining it by "
            "de-duplication, never by rewriting a whole view."
        ),
    )
)

INFERENCE_TIME_VERIFICATION_V1 = _register(
    Stage3Algorithm(
        id="inference-time-verification-v1",
        family="test-time-scaling",
        display_name="Inference-time verification (self-selection over sampled answers)",
        citation=(
            "self-consistency / best-of-N with a verifier; see "
            "docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md"
        ),
        operators=("scoring", "selection"),
        status="base-loop",
        what_it_changes=(
            "The delivered answer is chosen from among the frozen core's OWN sampled "
            "answers by the frozen core itself rather than by a deterministic "
            "aggregation rule: the verifier reads a row's candidate answers and names "
            "one, so the scoring operator is a model judgement over sampled answers "
            "and the selection operator commits the named candidate. Nothing in the "
            "store, the plan's context or the sampling policy changes -- only which of "
            "the already-produced samples is delivered."
        ),
    )
)


SEALED_CREDIT_SYSTEM_POLICY_V1 = _register(
    Stage3Algorithm(
        id="sealed-credit-system-policy-v1",
        family="sealed-credit-system-policy",
        display_name=(
            "Sealed-credit system policy search (this repository's departure from the "
            "locked families)"
        ),
        citation=(
            "this repository: docs/readiness/"
            "2026-09-26-slurp-stage3-measurement-instrument-v1.md (the measured floors "
            "and the four failure modes it names) with "
            "docs/results/2026-09-24-slurp-plan-bad-case-bank.md (the typed classes and "
            "their headroom). No external identifier is recorded for it here because it "
            "is not an external algorithm."
        ),
        operators=(
            "rollout",
            "scoring",
            "credit_assignment",
            "update",
            "selection",
            "context_application",
        ),
        status="planned",
        what_it_changes=(
            "Four departures from the locked families, one per failure mode this "
            "repository measured. (i) The update is a TYPED, EXECUTABLE construction or "
            "consumption action -- which knowledge view a node consumes, which candidate "
            "set a proposal broadens to, which rule commits the answer -- not prose "
            "appended to a node's context, because injected prose paid a form cost and "
            "moved little (IDX -7.37 form loss; CELL-1 / CELL-2 within flight variance). "
            "(ii) Credit is assigned over DELIBERATE VARIANTS of the system policy "
            "carried in one campaign, not over decoding noise: two request-identical "
            "flights differ by 1.87 pp SLU at n=625 while 91.5 percent of delivered "
            "answers inside one flight are byte-identical, so the signal a between-flight "
            "group would score is mostly the instrument. (iii) SELECTION IS PART OF THE "
            "POLICY -- the episode commits the better of its own trajectories under a "
            "rule whose effect was read offline over sealed samples -- because the only "
            "two effects in the Stage-3 record that clear their design's floor are a "
            "deterministic support filter (+1.40) and the core's own self-selection "
            "(intent +0.544), both of which act on what the system already produced. "
            "(iv) An update is ADMITTED TO RE-EXECUTION only when its predicted effect "
            "exceeds the measured floor of the design that would read it, so the inner "
            "optimisation runs over sealed bytes at 0.67 pp and a flight is spent only on "
            "a composed policy large enough to be seen. The loop is therefore "
            "sealed-credit: rollout and scoring produce a custodied pool once, credit and "
            "the update are computed over that pool, and the GPU is re-entered for the "
            "composed policy and its in-chain replicate."
        ),
    )
)

SHARED_ROLLOUT = _register(
    Stage3Algorithm(
        id="shared-rollout",
        family="shared-substrate",
        display_name="Shared algorithm-neutral rollout (ROLL-t and its scoring)",
        citation=(
            "this repository: docs/superpowers/specs/"
            "2026-09-22-stage3-tfrl-base-loop-engineering.md sections S3-2 and S3-3"
        ),
        operators=("rollout", "scoring"),
        status="base-loop",
        what_it_changes=(
            "Nothing in the locked plan's context: it produces the custodied "
            "grouped-Solver samples and their official per-sample scores that every "
            "training-free RL family of layer A consumes, so the families are compared "
            "on one substrate."
        ),
    )
)

NONE = _register(
    Stage3Algorithm(
        id=NONE_ALGORITHM_ID,
        family="none",
        display_name="No training-free RL operator",
        citation="not applicable",
        operators=(),
        status="not-applicable",
        what_it_changes=(
            "Nothing: the cell is a control, a contract cell or a pruning cell on the "
            "locked plan and defines no training-free RL operator."
        ),
        reason=(
            "Stage-3 cells that carry no training-free RL operator -- R-PRIM's Reviewer "
            "verdict contract, the decision-85 pruning cells, and the model-free "
            "preparations of S3-1 -- are still Stage-3 cells and still carry a "
            "machine-checked label; theirs says so explicitly instead of leaving the "
            "field absent, which is the state decision 101 forbids."
        ),
    )
)


def registered_ids() -> list[str]:
    """Every registered Stage-3 algorithm id, sorted."""

    return STAGE3_ALGORITHMS.names()


def resolve_stage3_algorithm(algorithm_id: object) -> Stage3Algorithm:
    """The record ``algorithm_id`` names, or :class:`Stage3AlgorithmError`."""

    if not isinstance(algorithm_id, str) or not algorithm_id.strip():
        raise Stage3AlgorithmError(
            f"Stage-3 algorithm id must be a non-empty string, got {algorithm_id!r}"
        )
    try:
        record = STAGE3_ALGORITHMS.resolve(algorithm_id)
    except CoreError as error:
        raise Stage3AlgorithmError(str(error)) from None
    if not isinstance(record, Stage3Algorithm):  # pragma: no cover - registry is frozen here
        raise Stage3AlgorithmError(
            f"Stage-3 algorithm {algorithm_id!r} resolves to a {type(record).__name__}, "
            "not a Stage3Algorithm record"
        )
    return record


def validate_stage3_algorithm_label(
    label: object, *, cell: str = "<cell>"
) -> tuple[Stage3Algorithm, tuple[str, ...]]:
    """Validate one cell's ``stage3_algorithm`` label.

    Returns the resolved record and the declared ``operators_used`` tuple.
    Raises :class:`Stage3AlgorithmError` naming ``cell`` on any defect: a
    non-object label, a missing ``id`` or ``note``, an unknown key, an
    unregistered id, a repeated operator, or an operator the algorithm does
    not define.
    """

    if not isinstance(label, Mapping):
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY} must be an object with keys "
            f"{sorted(_KNOWN_LABEL_KEYS)}, got {type(label).__name__}"
        )
    keys = set(label)
    missing = sorted(_REQUIRED_LABEL_KEYS - keys)
    if missing:
        raise Stage3AlgorithmError(f"{cell}: {LABEL_KEY} is missing key(s) {missing}")
    unknown_keys = sorted(keys - _KNOWN_LABEL_KEYS)
    if unknown_keys:
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY} carries unknown key(s) {unknown_keys}; the shape is "
            f"{sorted(_KNOWN_LABEL_KEYS)}"
        )
    note = label.get("note")
    if not isinstance(note, str) or not note.strip():
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY}.note must be a non-empty sentence"
        )
    record = resolve_stage3_algorithm(label.get("id"))

    declared = label.get("operators_used", [])
    if not isinstance(declared, Sequence) or isinstance(declared, (str, bytes)):
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY}.operators_used must be a list of operator names"
        )
    used = tuple(declared)
    if any(not isinstance(op, str) for op in used):
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY}.operators_used must be a list of operator names"
        )
    if len(set(used)) != len(used):
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY}.operators_used repeats an operator"
        )
    outside = [op for op in used if op not in record.operators]
    if outside:
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY}.operators_used names {outside}, which algorithm "
            f"{record.id!r} does not define; it defines {list(record.operators)}"
        )
    if record.id != NONE_ALGORITHM_ID and not used:
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY}.operators_used is empty; a cell labelled "
            f"{record.id!r} states which of that algorithm's operators it exercises"
        )
    if COLUMNS_KEY in label:
        validate_stage3_algorithm_columns(label[COLUMNS_KEY], cell=cell)
    return record, used


def validate_stage3_algorithm_columns(
    columns: object, *, cell: str = "<cell>"
) -> dict[str, Stage3Algorithm]:
    """Validate a label's per-column map ``{arm_id: algorithm_id}``.

    Returns ``{arm_id: record}``. Raises :class:`Stage3AlgorithmError` naming
    ``cell`` when the map is not a non-empty object, an arm id is not a
    non-empty string, or an algorithm id does not resolve in the registry.
    """

    if not isinstance(columns, Mapping) or not columns:
        raise Stage3AlgorithmError(
            f"{cell}: {LABEL_KEY}.{COLUMNS_KEY} must be a non-empty object "
            "{arm_id: algorithm_id}"
        )
    resolved: dict[str, Stage3Algorithm] = {}
    for arm_id, algorithm_id in columns.items():
        if not isinstance(arm_id, str) or not arm_id.strip():
            raise Stage3AlgorithmError(
                f"{cell}: {LABEL_KEY}.{COLUMNS_KEY} keys must be non-empty arm ids, "
                f"got {arm_id!r}"
            )
        try:
            resolved[arm_id] = resolve_stage3_algorithm(algorithm_id)
        except Stage3AlgorithmError as error:
            raise Stage3AlgorithmError(
                f"{cell}: {LABEL_KEY}.{COLUMNS_KEY}[{arm_id!r}]: {error}"
            ) from None
    return resolved


def columns_of(label: object) -> dict[str, str]:
    """The label's ``{arm_id: algorithm_id}`` map, or ``{}``; no validation."""

    if isinstance(label, Mapping) and isinstance(label.get(COLUMNS_KEY), Mapping):
        return {str(arm): str(algo) for arm, algo in label[COLUMNS_KEY].items()}
    return {}


def label_of(document: Mapping[str, object]) -> object | None:
    """The fragment's ``stage3_algorithm`` label, or ``None``."""

    if not isinstance(document, Mapping):
        return None
    return document.get(LABEL_KEY)


def summary_of(
    record: Stage3Algorithm, operators_used: Sequence[str] = ()
) -> dict[str, object]:
    """The JSON block a read driver echoes into its summary / verdict table."""

    return {
        "id": record.id,
        "family": record.family,
        "display_name": record.display_name,
        "citation": record.citation,
        "status": record.status,
        "operators_used": list(operators_used),
    }


EXPERIMENT_DIR = "configs/experiment"


def label_for_run_id(
    repo_root: Path, run_id: str
) -> tuple[Stage3Algorithm, tuple[str, ...], str] | None:
    """``(record, operators_used, fragment stem)`` for the Stage-3 cell that
    owns ``run_id``, or ``None``.

    Read-only and model-free: it scans ``configs/experiment/*.json`` for the
    fragment whose ``experiment_id`` or whose cell ``run_id`` is ``run_id``
    and validates that fragment's label. A fragment with no label, or a run id
    no fragment claims, is simply ``None`` -- a read driver labels what it can
    and never fails on what it cannot.
    """

    directory = Path(repo_root) / EXPERIMENT_DIR
    if not directory.is_dir():
        return None
    for path in sorted(directory.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(document, Mapping):
            continue
        claimed = document.get("experiment_id") == run_id or any(
            isinstance(cell, Mapping) and cell.get("run_id") == run_id
            for cell in document.get("cells", [])
            if isinstance(document.get("cells"), list)
        )
        if not claimed:
            continue
        label = label_of(document)
        if label is None:
            return None
        record, used = validate_stage3_algorithm_label(label, cell=path.name)
        return record, used, path.stem
    return None


def summary_for_run_id(
    repo_root: Path, run_id: str, override_id: str | None = None
) -> dict[str, object] | None:
    """The ``stage3_algorithm`` block a read driver echoes into its summary.

    ``override_id`` (the drivers' ``--stage3-algorithm`` flag) wins and names
    a registered id directly, for a read whose run id predates its fragment or
    whose fragment this driver cannot see; otherwise the label is resolved
    from the experiment fragment that owns ``run_id``. ``None`` means the run
    is not a labelled Stage-3 cell and the driver writes no block.
    """

    if override_id is not None:
        record = resolve_stage3_algorithm(override_id)
        return {**summary_of(record, record.operators), "source": "cli"}
    found = label_for_run_id(repo_root, run_id)
    if found is None:
        return None
    record, used, stem = found
    return {
        **summary_of(record, used),
        "source": f"{EXPERIMENT_DIR}/{stem}.json",
    }
