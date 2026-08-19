"""P-FEW flight orchestration -- REGISTERED probe SAEA-PROBE-pfew-180
(``bounded-discovery-probe``): ``docs/readiness/2026-08-19-pfew-preregistration-
REGISTERED.md``. Arc: probe 1 of the routing-tier x filling-tier program
(2026-08-19 owner design order).

Question: does few-shot demonstration supply improve HIGH-ORDER routing
(closed-set scenario selection), and how bias-sensitive is it to demo label
skew? Three arms, single-phase, over the SAME frozen 60 SLURP devel samples
the consumed P-SLU/P-TRAP/P-KEY probes already used
(``configs/probes/g0-binding/pslu-sample-devel-n60.json``, whose own
``split_identity_hash`` is
``fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5`` --
:func:`assert_split_identity_hash` pins this VERBATIM):

- **FS-NONE**: zero demos -- the A1'r closed-set phase-1 construction
  (``rails.probes.pslu_s2_flight.closed_set_phase1_supply_packet``), reused
  UNMODIFIED, never re-derived.
- **FS-BAL**: K=4 demos, 4 DISTINCT canonical scenario labels, seeded
  (seed 20260807) per target sample, never the target's own recording.
- **FS-SKEW**: K=4 demos, all four carrying the SAME single seeded skew
  label (chosen ONCE, globally, for the whole arm -- never per-sample,
  since a per-sample "wrong for THIS sample" choice would require reading
  that sample's own gold scenario at binding time, which is prohibited;
  see :func:`build_demo_binding`'s own docstring for the full legal
  resolution).

Every arm's request is the SAME closed-set instruction
(:func:`~speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight.
closed_set_phase1_supply_packet`) over the 18 canonical SLURP scenario
labels (:func:`~speech_aware_evidence_acquisition.rails.probes.
pslu_s2_flight.canonical_scenario_labels`), reused verbatim, with an
OPTIONAL demo block prepended for FS-BAL/FS-SKEW -- single-phase routing
only (this probe measures the ROUTER, never phase-2 supply). Every
response is deterministically mapped to one of the 18 canonical labels
(``rails.probes.pslu_s2_flight.map_predicted_scenario_to_canonical``,
reused verbatim, the SAME never-gold-fallback discipline).

DEMO SOURCING (registration section 2 / section 5): demo content is
TRAIN-split transcript text plus its own gold scenario label -- LEGAL
supply, never devel gold (registration: "train gold transcripts are legal
supply per the program split philosophy per the program split philosophy;
they never touch devel gold"). :func:`load_train_demo_pool` reads the SAME
raw ``train.jsonl`` the legal roster table
(``configs/probes/g0-binding/pslu-rosters-train-only.json``) was itself
mined from (``data.slurp.load_slurp_ontology``'s own "roster/KB
construction only" split scope, that module's own docstring) -- but
``data.slurp.SlurpRecord`` deliberately excludes raw sentence text (its own
module docstring: "not needed by either the five TaskAdapter methods or by
scoring"), so this reads the RAW governed jsonl directly
(``data.slurp._governed_roots`` + ``data.slurp._read_jsonl``, private
cross-module reuse already precedented in this repository --
``analysis.pkey_read.load_gold_sentence_by_sample_id`` reads ``devel.jsonl``
the identical way for its own scoring-side WER descriptive). Text-only, no
audio file is ever opened here -- mirrors ``load_slurp_ontology``'s own
"text-only, no audio touched" discipline exactly.

Never calls the ceiling-tier ontology miner (``data.slurp.
load_slurp_ontology``): this module's own AST guard
(:func:`_assert_this_module_never_calls_ontology_miner`) reuses
``rails.probes.pslu_flight._source_references_ontology_miner`` verbatim,
checked at import time and again at the top of :func:`run_pfew_flight` --
this probe's closed-set scenario labels come ONLY from
``configs/probes/g0-binding/pslu-rosters-train-only.json`` via the SAME
frozen ``rails.probes.pslu_flight.load_pslu_rosters`` /
``rails.probes.pslu_s2_flight.canonical_scenario_labels``, and its demo
transcript text comes ONLY from the RAW ``train.jsonl`` (never
``train_synthetic``, never ``devel``, never ``test``).

Simple flight orchestration (mirrors ``rails.probes.ptrap_flight``'s own
"silence-swap-free" shape, never P-SLU-S2/P-KEY's phase-ordering or
silence-swap machinery -- this probe has neither): three independent,
single-phase arm blocks, 60 requests each, one session, 180 total.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ...reproduction.slurp_scoring import parse_slu_response
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace
from ..supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket
from .pslu_flight import (
    PsluRosters,
    _source_references_ontology_miner,
    assert_never_calls_ontology_miner,
)
from .pslu_s2_flight import (
    ClosedSetMapping,
    canonical_scenario_labels,
    closed_set_phase1_supply_packet,
    map_predicted_scenario_to_canonical,
)

FS_NONE_ARM = "FS-NONE"
FS_BAL_ARM = "FS-BAL"
FS_SKEW_ARM = "FS-SKEW"
PFEW_ARMS: tuple[str, ...] = (FS_NONE_ARM, FS_BAL_ARM, FS_SKEW_ARM)

# Registration section 2: "K=4 demos" on both FS-BAL and FS-SKEW.
FS_BAL_K = 4
FS_SKEW_K = 4

# Registration's own opening line / this study's SAME fixed seed reused
# throughout the probe family (``analysis.bootstrap.DEFAULT_SEED``,
# ``rails.probes.ptrap_flight.DEFAULT_TRAP_SEED``).
DEFAULT_DEMO_SEED = 20260807

# docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md's own opening
# line: "the SAME frozen 60 SLURP devel samples (seed 20260807)" --
# configs/probes/g0-binding/pslu-sample-devel-n60.json's own
# split_identity_hash, pinned VERBATIM (IDENTICAL to the consumed P-SLU/
# P-TRAP/P-KEY flights' own value).
EXPECTED_SPLIT_IDENTITY_HASH = "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"

TRAIN_SAMPLE_ID_PREFIX = "slurp:train:"


class PFewFlightError(RuntimeError):
    """A P-FEW flight/binding input is malformed, a hard invariant (split
    identity, demo legality, K-cap, label balance/skew) is violated, or the
    ontology-miner import guard tripped."""


# ---------------------------------------------------------------------------
# The ontology-miner call guard -- reuses the parent's own pure checker
# against THIS module's own source (mirrors rails.probes.ptrap_flight's own
# dual parent+self check).
# ---------------------------------------------------------------------------


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise PFewFlightError(
            "rails.probes.pfew_flight source references load_slurp_ontology; this flight is "
            "REGISTERED to consume its closed-set labels ONLY from configs/probes/g0-binding/"
            "pslu-rosters-train-only.json (rails.probes.pslu_flight.load_pslu_rosters) and its demo "
            "transcripts ONLY from the raw train.jsonl (load_train_demo_pool)"
        )


def assert_split_identity_hash(split_identity_hash: str) -> None:
    """Fail-closed (module docstring): ``split_identity_hash`` must equal
    :data:`EXPECTED_SPLIT_IDENTITY_HASH` VERBATIM -- this probe reuses the
    SAME frozen 60-sample manifest the consumed P-SLU/P-TRAP/P-KEY flights
    used, never a fresh draw."""

    if split_identity_hash != EXPECTED_SPLIT_IDENTITY_HASH:
        raise PFewFlightError(
            f"split_identity_hash {split_identity_hash!r} does not match the REGISTERED P-FEW "
            f"sample manifest's own hash {EXPECTED_SPLIT_IDENTITY_HASH!r} "
            "(configs/probes/g0-binding/pslu-sample-devel-n60.json, reused byte-identically for "
            "this probe) -- fail-closed"
        )


# ---------------------------------------------------------------------------
# TRAIN-split demo pool (module docstring).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DemoCandidate:
    """One TRAIN-split (utterance text -> scenario label) pair, legal
    few-shot supply content (module docstring). ``train_sample_id`` is
    namespaced ``"slurp:train:NNNNNN"`` -- structurally impossible to
    collide with a ``"slurp:devel:..."``/``"slurp:test:..."`` id, checked
    again explicitly by :func:`build_demo_binding`'s own binding-time
    fail-closed devel-overlap check (defense in depth, never relying on
    namespacing alone)."""

    train_sample_id: str
    utterance_text: str
    scenario_label: str

    def as_json(self) -> dict[str, object]:
        return {
            "train_sample_id": self.train_sample_id,
            "utterance_text": self.utterance_text,
            "scenario_label": self.scenario_label,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "DemoCandidate":
        return cls(
            train_sample_id=str(document["train_sample_id"]),
            utterance_text=str(document["utterance_text"]),
            scenario_label=str(document["scenario_label"]),
        )


def load_train_demo_pool(lock: Mapping[str, object], root: Path) -> dict[str, tuple[DemoCandidate, ...]]:
    """TRAIN-split (utterance text -> scenario label) pool, grouped by
    scenario label, sorted deterministically by ``train_sample_id`` (module
    docstring: the SAME raw ``train.jsonl`` the legal roster table was
    mined from, read directly because ``data.slurp.SlurpRecord`` deliberately
    excludes sentence text). One entry per distinct ``slurp_id`` (a
    (sentence, scenario) pair is per-sentence, not per-recording -- multiple
    ``recordings[]`` entries for the same ``slurp_id`` never produce
    duplicate demo candidates). Text-only: no audio file is opened, no
    ``recordings[]`` field is even read."""

    from ...data.slurp import _governed_roots, _read_jsonl

    _, _, metadata_dir = _governed_roots(lock, Path(root))
    path = metadata_dir / "train.jsonl"
    pool: dict[str, list[DemoCandidate]] = {}
    for raw in _read_jsonl(path):
        slurp_id = raw.get("slurp_id")
        sentence = raw.get("sentence")
        scenario = raw.get("scenario")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            continue
        if not isinstance(sentence, str) or not sentence:
            continue
        if not isinstance(scenario, str) or not scenario:
            continue
        train_sample_id = f"{TRAIN_SAMPLE_ID_PREFIX}{slurp_id:06d}"
        pool.setdefault(scenario, []).append(
            DemoCandidate(train_sample_id=train_sample_id, utterance_text=sentence, scenario_label=scenario)
        )
    return {label: tuple(sorted(items, key=lambda c: c.train_sample_id)) for label, items in pool.items()}


# ---------------------------------------------------------------------------
# Demo binding (module docstring: FS-BAL/FS-SKEW construction + the
# registered legal resolution of "wrong-for-most" skew).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SampleDemoSet:
    sample_id: str
    fs_bal_demos: tuple[DemoCandidate, ...]
    fs_skew_demos: tuple[DemoCandidate, ...]


@dataclass(frozen=True)
class DemoBinding:
    """The fully-resolved, hash-pinned demo assignment table
    :func:`run_pfew_flight` consumes without ever re-deriving it (mirrors
    ``rails.probes.ptrap_flight.SampleTrapSet``'s own binding-time-output
    convention). ``sha256`` hash-pins the ENTIRE per-sample assignment
    (module docstring / registration section 2: "demo assignments fixed per
    sample at binding, hash-pinned") -- deterministic given the SAME
    ``demo_pool``/``canonical_labels``/target sample set/``seed``, so a
    later flight launcher can cite this value as its own binding receipt."""

    skew_label: str
    canonical_labels: tuple[str, ...]
    per_sample: Mapping[str, SampleDemoSet]
    sha256: str


def _demo_binding_document(
    *, skew_label: str, canonical_labels: Sequence[str], per_sample: Mapping[str, SampleDemoSet]
) -> dict[str, object]:
    return {
        "skew_label": skew_label,
        "canonical_labels": list(canonical_labels),
        "per_sample": {
            sample_id: {
                "fs_bal_demos": [d.as_json() for d in demo_set.fs_bal_demos],
                "fs_skew_demos": [d.as_json() for d in demo_set.fs_skew_demos],
            }
            for sample_id, demo_set in sorted(per_sample.items())
        },
    }


def compute_demo_binding_sha256(document: Mapping[str, object]) -> str:
    return hashlib.sha256(json.dumps(document, sort_keys=True).encode("utf-8")).hexdigest()


def build_demo_binding(
    *,
    demo_pool: Mapping[str, tuple[DemoCandidate, ...]],
    canonical_labels: Sequence[str],
    target_samples: Sequence[SlurpSample],
    seed: int = DEFAULT_DEMO_SEED,
) -> DemoBinding:
    """Binding-time construction (module docstring / registration section 2),
    entirely offline and pure (no I/O, no model contact):

    - **FS-BAL**: per target sample, IN SORTED sample-id order, draw 4
      DISTINCT canonical labels (``random.sample`` over the labels the pool
      actually covers -- distinctness is structural, not merely checked),
      then one demo transcript per drawn label. "Never the target's own
      recording" is structural (demos are TRAIN-only, targets are DEVEL-
      only) and re-checked below by the devel-overlap scan.
    - **FS-SKEW**: the skew label is chosen EXACTLY ONCE, GLOBALLY, for the
      whole arm -- reading a per-SAMPLE "wrong for this sample" label would
      require that sample's own gold scenario at BINDING time, which this
      probe's own research boundary forbids (gold must never enter runtime
      construction). The REGISTERED legal resolution (registration section
      2's own "wrong-for-most-samples" reading, cross-referenced by the
      mission brief): draw ONE seeded label from the 18 canonical labels
      for the ENTIRE arm; for whichever samples that label happens to equal
      gold (a data fact, never consulted here), the read suite's OWN
      scoring-side capture-rate accounting excludes them from its
      denominator (disclosed, ``analysis.pfew_read.compute_skew_capture``) --
      this function never reads gold and never special-cases a sample by
      its own label. Per target sample, IN SORTED sample-id order, 4
      DISTINCT demo transcripts carrying that SAME skew label are drawn.

    Two independent ``random.Random(seed)`` streams (skew-label choice,
    FS-BAL draws) plus a third for FS-SKEW draws -- all seeded with the
    SAME ``seed`` but logically separate, so adding/removing a target
    sample never shifts an unrelated stream's own draw index (mirrors
    ``analysis.bootstrap.DEFAULT_SEED``'s "one seed value, many independent
    uses" convention, never one shared stream three different call sites
    race to consume from)."""

    canonical = tuple(canonical_labels)
    canonical_set = set(canonical)
    if not canonical:
        raise PFewFlightError("build_demo_binding requires at least one canonical label")
    if not target_samples:
        raise PFewFlightError("build_demo_binding requires at least one target sample")

    target_ids = [sample.sample_id for sample in target_samples]
    if len(target_ids) != len(set(target_ids)):
        raise PFewFlightError("build_demo_binding: duplicate sample_id in target_samples")
    target_ids_sorted = sorted(target_ids)
    devel_utterance_ids = {sample.utterance_id for sample in target_samples}

    # Binding-time fail-closed check: demo labels within the canonical 18 --
    # only pool entries under a canonical label are ever eligible to draw
    # from (a train scenario outside the 18 is simply never consulted).
    available_labels = sorted(label for label in canonical if demo_pool.get(label))
    if len(available_labels) < FS_BAL_K:
        raise PFewFlightError(
            f"train demo pool covers only {len(available_labels)} of the 18 canonical label(s) with "
            f">=1 example; FS-BAL needs >= {FS_BAL_K} distinct labels available"
        )

    label_rng = random.Random(seed)
    skew_label = label_rng.choice(canonical)
    skew_pool = demo_pool.get(skew_label, ())
    if len(skew_pool) < FS_SKEW_K:
        raise PFewFlightError(
            f"seeded skew label {skew_label!r} has only {len(skew_pool)} TRAIN candidate(s); "
            f"FS-SKEW needs >= {FS_SKEW_K}"
        )

    bal_rng = random.Random(seed)
    bal_demos_by_sample: dict[str, tuple[DemoCandidate, ...]] = {}
    for sample_id in target_ids_sorted:
        chosen_labels = sorted(bal_rng.sample(available_labels, FS_BAL_K))
        demos = tuple(bal_rng.choice(demo_pool[label]) for label in chosen_labels)
        bal_demos_by_sample[sample_id] = demos

    skew_rng = random.Random(seed)
    skew_demos_by_sample: dict[str, tuple[DemoCandidate, ...]] = {}
    for sample_id in target_ids_sorted:
        indices = sorted(skew_rng.sample(range(len(skew_pool)), FS_SKEW_K))
        skew_demos_by_sample[sample_id] = tuple(skew_pool[i] for i in indices)

    # Binding-time fail-closed checks (module docstring / registration
    # section 5): demo labels within the canonical 18 (structural, defended
    # here too); no demo recording id in devel; never the target's own
    # recording (structural given the split-disjoint id namespace, defended
    # here too).
    all_used: list[DemoCandidate] = []
    for demos in bal_demos_by_sample.values():
        all_used.extend(demos)
    for demos in skew_demos_by_sample.values():
        all_used.extend(demos)
    for candidate in all_used:
        if candidate.scenario_label not in canonical_set:
            raise PFewFlightError(
                f"demo candidate {candidate.train_sample_id!r} carries label "
                f"{candidate.scenario_label!r} outside the canonical 18 -- fail-closed"
            )
        if not candidate.train_sample_id.startswith(TRAIN_SAMPLE_ID_PREFIX):
            raise PFewFlightError(
                f"demo candidate {candidate.train_sample_id!r} is not a TRAIN-split id -- fail-closed "
                "(demo content must be TRAIN-split only, registration section 5)"
            )
        candidate_slurp_id = str(int(candidate.train_sample_id[len(TRAIN_SAMPLE_ID_PREFIX) :]))
        if candidate_slurp_id in devel_utterance_ids:
            raise PFewFlightError(
                f"demo candidate {candidate.train_sample_id!r} shares its slurp_id with a TARGET devel "
                "sample -- binding-time fail-closed devel-overlap check violated (registration section 5: "
                "\"no demo recording id in devel\")"
            )

    per_sample = {
        sample_id: SampleDemoSet(
            sample_id=sample_id,
            fs_bal_demos=bal_demos_by_sample[sample_id],
            fs_skew_demos=skew_demos_by_sample[sample_id],
        )
        for sample_id in target_ids_sorted
    }
    document = _demo_binding_document(skew_label=skew_label, canonical_labels=canonical, per_sample=per_sample)
    sha256 = compute_demo_binding_sha256(document)

    return DemoBinding(skew_label=skew_label, canonical_labels=canonical, per_sample=per_sample, sha256=sha256)


# ---------------------------------------------------------------------------
# Supply packet construction: the reused closed-set instruction plus an
# optional demo block.
# ---------------------------------------------------------------------------

DEMO_BLOCK_HEADER = (
    "Here are example (utterance -> scenario) pairs from OTHER recordings, for reference only "
    "-- never this sample's own transcript:"
)


def render_demo_block(demos: Sequence[DemoCandidate]) -> str:
    lines = [f'"{demo.utterance_text}" -> {demo.scenario_label}' for demo in demos]
    return DEMO_BLOCK_HEADER + "\n" + "\n".join(lines)


def pfew_supply_packet(arm: str, demos: Sequence[DemoCandidate], canonical_labels: Sequence[str]) -> SupplyPacket:
    """One arm's ``SupplyPacket`` -- FS-NONE reuses
    ``rails.probes.pslu_s2_flight.closed_set_phase1_supply_packet``
    UNMODIFIED (module docstring); FS-BAL/FS-SKEW prepend
    :func:`render_demo_block` ahead of that SAME reused instruction text,
    never re-typing it."""

    closed_set = closed_set_phase1_supply_packet(canonical_labels)
    if arm == FS_NONE_ARM:
        if demos:
            raise PFewFlightError(f"arm {FS_NONE_ARM} must carry zero demos")
        return closed_set
    if arm not in (FS_BAL_ARM, FS_SKEW_ARM):
        raise PFewFlightError(f"unknown P-FEW arm {arm!r}; known arms are {PFEW_ARMS}")
    if not demos:
        raise PFewFlightError(f"arm {arm} requires at least one demo")

    demo_block = render_demo_block(demos)
    prompt_block = f"{demo_block}\n\n{closed_set.prompt_block}"
    items = tuple(
        SupplyItem(item_id=f"{arm}-demo-{index:03d}", text=f"{demo.utterance_text} -> {demo.scenario_label}")
        for index, demo in enumerate(demos)
    )
    return SupplyPacket(
        form=SupplyForm.TEXT,
        dose=SupplyDose(n_items=len(items), token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id=f"pfew-{arm}-fewshot-v1",
        items=items,
    ).validate()


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PFewArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace
    closed_set_mapping: ClosedSetMapping
    # () on FS-NONE; K=4 DemoCandidate.as_json() entries on FS-BAL/FS-SKEW --
    # embedded so the read suite's capture-rate/label-balance checks never
    # need to re-derive the binding live (harness-defect-resistant design,
    # mirrors rails.probes.ptrap_flight.PTrapArmResult.trap_entries).
    demos: tuple[Mapping[str, object], ...] = ()


@dataclass(frozen=True)
class PFewFlightSummary:
    results: tuple[PFewArmResult, ...]
    canonical_labels: tuple[str, ...]
    skew_label: str
    demo_binding_sha256: str


def validate_pfew_flight_summary(
    summary: PFewFlightSummary, *, expected_sample_ids: Sequence[str]
) -> None:
    """Fail-closed structural checks (mission instruction: "60/60/60, no
    duplicates, split hash"): every arm in :data:`PFEW_ARMS` carries EXACTLY
    one row per id in ``expected_sample_ids``, no duplicate rows, exactly
    ``3 * len(expected_sample_ids)`` rows total, FS-NONE rows carry zero
    demos, FS-BAL rows carry exactly :data:`FS_BAL_K` demos with all-distinct
    labels, and FS-SKEW rows carry exactly :data:`FS_SKEW_K` demos all
    carrying ``summary.skew_label``. Called automatically at the end of
    :func:`run_pfew_flight`; independently callable against an
    already-assembled summary (e.g. by a test fixture)."""

    expected = tuple(expected_sample_ids)
    expected_set = set(expected)
    if len(expected) != len(expected_set):
        raise PFewFlightError("expected_sample_ids carries a duplicate")

    by_arm: dict[str, list[PFewArmResult]] = {arm: [] for arm in PFEW_ARMS}
    for row in summary.results:
        if row.arm not in PFEW_ARMS:
            raise PFewFlightError(f"unknown P-FEW arm {row.arm!r}")
        by_arm[row.arm].append(row)

    for arm in PFEW_ARMS:
        rows = by_arm[arm]
        ids = [row.sample_id for row in rows]
        if len(ids) != len(set(ids)):
            raise PFewFlightError(f"arm {arm}: duplicate sample_id row(s)")
        got = set(ids)
        if got != expected_set:
            missing = sorted(expected_set - got)
            extra = sorted(got - expected_set)
            raise PFewFlightError(
                f"arm {arm}: sample id set does not match the expected {len(expected_set)}-sample "
                f"manifest (missing={missing[:5]}, extra={extra[:5]})"
            )

    expected_total = len(expected) * len(PFEW_ARMS)
    if len(summary.results) != expected_total:
        raise PFewFlightError(
            f"expected exactly {expected_total} total rows ({len(expected)} samples x "
            f"{len(PFEW_ARMS)} arms), got {len(summary.results)}"
        )

    for row in by_arm[FS_NONE_ARM]:
        if row.demos:
            raise PFewFlightError(f"arm {FS_NONE_ARM} sample {row.sample_id!r}: must carry zero demos")

    for row in by_arm[FS_BAL_ARM]:
        if len(row.demos) != FS_BAL_K:
            raise PFewFlightError(
                f"arm {FS_BAL_ARM} sample {row.sample_id!r}: expected {FS_BAL_K} demos, got {len(row.demos)}"
            )
        labels = [str(d.get("scenario_label")) for d in row.demos]
        if len(set(labels)) != len(labels):
            raise PFewFlightError(
                f"arm {FS_BAL_ARM} sample {row.sample_id!r}: demo labels are not all distinct: {labels}"
            )

    for row in by_arm[FS_SKEW_ARM]:
        if len(row.demos) != FS_SKEW_K:
            raise PFewFlightError(
                f"arm {FS_SKEW_ARM} sample {row.sample_id!r}: expected {FS_SKEW_K} demos, got {len(row.demos)}"
            )
        labels = {str(d.get("scenario_label")) for d in row.demos}
        if labels != {summary.skew_label}:
            raise PFewFlightError(
                f"arm {FS_SKEW_ARM} sample {row.sample_id!r}: demo labels must all equal the skew label "
                f"{summary.skew_label!r}, got {sorted(labels)}"
            )


def run_pfew_flight(
    *,
    adapter: SlurpAdapter,
    core_client,
    samples: Sequence[SlurpSample],
    rosters: PsluRosters,
    demo_binding: DemoBinding,
    split_identity_hash: str,
    decoding_params: Mapping[str, object] | None = None,
) -> PFewFlightSummary:
    """Execute the full three-arm, single-phase P-FEW flight over
    ``samples`` (module docstring): ``3 * len(samples)`` requests, one arm
    block at a time (FS-NONE, then FS-BAL, then FS-SKEW), each block 60
    samples in the caller's own ``samples`` order -- ``180`` total for the
    registered 60-sample manifest. ``demo_binding`` is the ALREADY-BUILT
    :func:`build_demo_binding` output -- never re-derived here.

    ``core_client`` is duck-typed against ``rails.core_client.CoreClient``
    (the SAME "no forced import" discipline every sibling flight in this
    package uses)."""

    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_split_identity_hash(split_identity_hash)
    if not samples:
        raise PFewFlightError("run_pfew_flight requires at least one sample")
    sample_ids_list = [sample.sample_id for sample in samples]
    if len(sample_ids_list) != len(set(sample_ids_list)):
        raise PFewFlightError("duplicate sample_id in samples")

    canonical_labels = canonical_scenario_labels(rosters)
    if demo_binding.canonical_labels != canonical_labels:
        raise PFewFlightError(
            "demo_binding.canonical_labels does not match this flight's own roster table's canonical "
            "scenario labels -- stale demo binding"
        )
    missing_binding = [sid for sid in sample_ids_list if sid not in demo_binding.per_sample]
    if missing_binding:
        raise PFewFlightError(
            f"demo_binding carries no SampleDemoSet for {len(missing_binding)} sample id(s) this "
            f"flight's own samples name: {missing_binding[:5]}"
        )

    results: list[PFewArmResult] = []
    for arm in PFEW_ARMS:
        for sample in samples:
            if arm == FS_NONE_ARM:
                demos: tuple[DemoCandidate, ...] = ()
            else:
                demo_set = demo_binding.per_sample[sample.sample_id]
                demos = demo_set.fs_bal_demos if arm == FS_BAL_ARM else demo_set.fs_skew_demos
            supply = pfew_supply_packet(arm, demos, canonical_labels)
            messages = adapter.assemble_prompt(sample, supply)
            response_text = core_client.complete(messages, decoding_params=decoding_params)
            predicted_scenario, _predicted_action, _predicted_entities, parsed = parse_slu_response(response_text)
            mapping = map_predicted_scenario_to_canonical(
                predicted_scenario if parsed else None, canonical_labels
            )
            metrics = adapter.score(sample, response_text)
            consumption = adapter.extract_consumption(sample, supply, response_text)
            results.append(
                PFewArmResult(
                    arm=arm,
                    sample_id=sample.sample_id,
                    messages=tuple(messages),
                    response_text=response_text,
                    metrics=metrics,
                    consumption=consumption,
                    closed_set_mapping=mapping,
                    demos=tuple(demo.as_json() for demo in demos),
                )
            )

    summary = PFewFlightSummary(
        results=tuple(results),
        canonical_labels=canonical_labels,
        skew_label=demo_binding.skew_label,
        demo_binding_sha256=demo_binding.sha256,
    )
    validate_pfew_flight_summary(summary, expected_sample_ids=tuple(sample_ids_list))
    return summary


__all__ = [
    "DEFAULT_DEMO_SEED",
    "DEMO_BLOCK_HEADER",
    "EXPECTED_SPLIT_IDENTITY_HASH",
    "FS_BAL_ARM",
    "FS_BAL_K",
    "FS_NONE_ARM",
    "FS_SKEW_ARM",
    "FS_SKEW_K",
    "PFEW_ARMS",
    "TRAIN_SAMPLE_ID_PREFIX",
    "DemoBinding",
    "DemoCandidate",
    "PFewArmResult",
    "PFewFlightError",
    "PFewFlightSummary",
    "SampleDemoSet",
    "assert_split_identity_hash",
    "build_demo_binding",
    "compute_demo_binding_sha256",
    "load_train_demo_pool",
    "pfew_supply_packet",
    "render_demo_block",
    "run_pfew_flight",
    "validate_pfew_flight_summary",
]


# Executed at import time (mirrors rails.probes.pslu_flight's own
# module-bottom self-check, and rails.probes.ptrap_flight's own dual
# parent+self check): fails LOUD the moment this module is loaded if a
# future edit adds a live reference to the forbidden ontology miner.
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
