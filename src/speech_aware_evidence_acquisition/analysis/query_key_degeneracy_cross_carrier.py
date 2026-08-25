"""THE CROSS-CARRIER QUERY-KEY DEGENERACY MEASUREMENT -- does the constant
retrieval key the Audio2Tool diagnosis found also occur on SLURP?

Row ``SAEA-SN-MF-QUERY-KEY-DEGENERACY-CROSS-CARRIER`` (model-free-check),
registered in ``docs/exposure-ledger.md`` BEFORE any number here was computed.

THE QUESTION, STATED FIRST. The A2T gold-absence diagnosis found that on the
dispatching subset the retrieval key is nearly a CONSTANT: 15 dead-direct
trajectories carry 5 distinct query vectors, 11 of them share ONE key -- the
embedding of an empty tool call -- and received ONE identical supply whatever
the utterance was about, while the 89 label-recovered trajectories carry 84
distinct keys of 89. The retrieval query IS the model's own contact-0 answer
text, so an empty answer is a key that carries no information about the
utterance, and the alpha veto selects exactly that subset. SLURP's dead-direct
retrieval deficit is only -4.0 to -7.9 pp against A2T's -45.24 pp, and SLURP's
dead-direct answers are BELIEVED to be wrong LABELS -- which carry utterance
content -- rather than empty calls, which do not. This module measures whether
that belief is true.

WHAT IT COMPUTES, in the order the registration fixed:

1. :func:`a2t_control` -- Q1. The A2T degeneracy statistics recomputed from the
   landed attempt-4 artifacts and compared against the landed diagnosis. This
   is a STOP CONDITION: if the control does not reproduce, :func:`run` raises
   and no SLURP number is read, because a control that cannot be reproduced
   cannot license a cross-carrier comparison.
2. :func:`group_profile` / :func:`carrier_groups` -- Q2. The same four
   statistics on both SLURP DEV-1000 halves, partitioned into dead-direct
   (``kb_policy.default_label_normalizer`` returns ``None`` on the flown
   direct-decode text) and label-recovered: distinct query vectors per
   trajectory, the largest identical-key cluster, distinct supplies per
   trajectory, and gold-in-top-5 plus median gold-facet cosine measured on the
   SAME records.
3. :func:`answer_content_profile` -- Q3. The evidence for the causal claim
   under test: "SLURP's dead-direct answer is a WRONG LABEL that still carries
   utterance content, so its query stays informative; A2T's is an EMPTY call
   that carries none." Measured as the structurally-empty-answer rate, the
   distinct-text count, and the number of tokens each answer carries OUTSIDE
   its own group's modal text. Reported whichever way it comes out.
4. :func:`tau_distance` -- Q4. The observed distance of each dead-direct gold
   facet from the frozen ``tau = 0.65`` percept gate, on both carriers. NO
   COUNTERFACTUAL QUERY IS MEASURED: that would need an embedding contact this
   row may not take.

REUSE, NEVER REIMPLEMENTATION. The A2T side is loaded, replayed and gated by
:mod:`.cross_carrier_ceiling_decomposition` and its geometry is
:func:`.a2t_gold_absence_diagnosis.compute_geometry`. The SLURP side is loaded
by :func:`.contrast_fewshot_preanalysis.load_cell_population`, replayed by
:func:`.contrast_fewshot_preanalysis.replay_population` -- and through them
recall, ranking, admission, fusion and the blend head all go through
``rails.kb_policy``'s own registered ranker, registered fuser,
``_fused_label_scores``, ``_blend_scores`` and ``_argmax_labels``. The DEV-1000
byte pins, the query-text identity proof and the v2 override deviation come
from :mod:`.k1_hybrid_ranking_gate`; the dead-direct partition comes from
:mod:`.dev100_next_experiment_projections`.

THE SLURP UNEXPOSED-500 IS A SECONDARY READING. It is the locked baseline's own
population; every statistic this module computes on it is descriptive and MUST
NOT be used to revise, re-tune or restate the lock. Every emitted block on that
half carries a ``reading_tier`` field saying so.

GOLD IS SCORING-SIDE ONLY. It is read from sealed records after the seal, never
on a runtime path; no gold value enters a prompt, a query vector or a policy
input.

WHAT IT DOES NOT DO. It changes no knob and writes nothing under ``configs/``,
``rails/`` or ``core/``. It opens no model session, no embedding sidecar and no
tokenizer: :func:`run` arms ``dev100_reviewer_audit.arm_offline_guard`` BEFORE
the first input is opened and writes the recorded outbound-attempt count into
the receipt. The resident llama-server on port 8090 is never contacted, probed,
reconfigured or stopped.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=<repo>/src \
      python -m speech_aware_evidence_acquisition.analysis.query_key_degeneracy_cross_carrier \
        --repo-root <repo> --data-root $SPEECHRL_DATA_DIR --out <receipt>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from . import a2t_gold_absence_diagnosis as agd
from . import a2t_read
from . import contrast_fewshot_preanalysis as cf
from . import cross_carrier_ceiling_decomposition as ccd
from . import dev100_next_experiment_projections as nx
from . import dev100_reviewer_audit as audit
from . import dev1000_lock_read as d1k
from . import k1_hybrid_ranking_gate as k1
from ..rails import kb_policy as kb

EXPOSURE_ROW_ID = "SAEA-SN-MF-QUERY-KEY-DEGENERACY-CROSS-CARRIER"
SCHEMA = "saea-query-key-degeneracy-cross-carrier-v1"

FROZEN_ALPHA = cf.FROZEN_ALPHA
FROZEN_WEIGHTS = cf.FROZEN_WEIGHTS
FROZEN_FUSE = cf.FROZEN_FUSE
FROZEN_TOP_K = cf.FROZEN_TOP_K

#: The landed A2T control, quoted from
#: ``docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md`` section 4.1 and
#: its receipt ``q3_dead_direct_contrast.query_key_degeneracy``. This module
#: must reproduce every one of these from the landed artifacts or STOP.
A2T_LANDED_CONTROL = {
    "source_document": "docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md",
    "source_receipt": (
        "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-gold-absence/"
        "diagnosis-report.json"
    ),
    "source_receipt_sha256": (
        "64327e98ff9f91a4affdf75f25e98eb5500aa4ab2eeab8befa6d3978799a3e14"
    ),
    "dead_direct_n": 15,
    "dead_direct_distinct_query_vectors": 5,
    "dead_direct_distinct_contact0_texts": 5,
    "dead_direct_largest_identical_query_cluster_size": 11,
    "label_recovered_n": 89,
    "label_recovered_distinct_query_vectors": 84,
    "label_recovered_distinct_contact0_texts": 84,
    "largest_cluster_distinct_flown_supplies": 1,
}

#: Tokenizer for the answer-content profile. The same registered tokenizer the
#: K1 gate's lexical channel uses, applied identically on both carriers.
TOKEN_RE = k1.TOKEN_RE

#: The DEV-1000 BLEND arm over ALL 1,000 scored ids. The k1 gate's own pin
#: restricts to the unexposed NEW500; this row needs both halves, so it takes
#: the same attempt with ``restrict_to=None`` and partitions afterwards from
#: the committed split receipts. Every other field is copied from
#: :data:`.k1_hybrid_ranking_gate.DEV1000_PIN` verbatim.
DEV1000_ALL_PIN = cf.CellPin(
    population_id="DEV-1000-ALL",
    run_id=d1k.RUN_ID,
    attempt_id=k1.DEV1000_PIN.attempt_id,
    outputs_basename=k1.DEV1000_PIN.outputs_basename,
    arm_key=k1.DEV1000_PIN.arm_key,
    report_relpath=k1.DEV1000_PIN.report_relpath,
    report_arm_key=None,
    restrict_to=None,
)

SECONDARY_READING_NOTE = (
    "SECONDARY READING. This is the locked baseline's own population "
    "(SAEA-DEV1000-BASELINE-LOCK, unexposed NEW500). Every statistic here is "
    "descriptive and MUST NOT be used to revise, re-tune or restate the LOCK."
)
EXPOSED_READING_NOTE = (
    "EXPOSED-TIER SECONDARY READING. This half was already read at the DEV-100 "
    "and DEV-500 tiers; reading it again is free and carries no lock authority."
)


class DegeneracyError(RuntimeError):
    """Raised when a pre-registered gate or the A2T control fails."""


# ---------------------------------------------------------------------------
# Shared primitives -- one definition, applied identically on both carriers
# ---------------------------------------------------------------------------


def vector_digest(vector: Sequence[float]) -> str:
    """The identity of one retrieval key.

    Byte-identical to :func:`.a2t_gold_absence_diagnosis.query_key_degeneracy`'s
    own inner ``digest``, so the A2T control this module recomputes is the same
    quantity the landed diagnosis published and not a look-alike."""

    return hashlib.sha256(
        ",".join(repr(float(value)) for value in vector).encode("utf-8")
    ).hexdigest()


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _cluster_block(
    ids: Sequence[str],
    *,
    label: str,
    query_vectors: Mapping[str, Sequence[float]],
    texts: Mapping[str, str],
    supplies: Mapping[str, tuple[str, ...]],
) -> dict[str, object]:
    """The degeneracy statistics for one group, on one carrier.

    Four quantities, fixed in the registration before this module ran:
    distinct query vectors per trajectory, the largest identical-key cluster,
    distinct supplies per trajectory, and -- inside the largest key cluster --
    how many distinct supplies that one key produced."""

    n = len(ids)
    digests = {sample_id: vector_digest(query_vectors[sample_id]) for sample_id in ids}
    key_counts = Counter(digests.values())
    text_counts = Counter(texts[sample_id] for sample_id in ids)
    supply_counts = Counter(tuple(sorted(supplies[sample_id])) for sample_id in ids)

    largest_key, largest_size = key_counts.most_common(1)[0] if key_counts else ("", 0)
    cluster = sorted(sample_id for sample_id in ids if digests[sample_id] == largest_key)
    cluster_supplies = Counter(tuple(sorted(supplies[sample_id])) for sample_id in cluster)
    largest_text, largest_text_size = (
        text_counts.most_common(1)[0] if text_counts else ("", 0)
    )

    return {
        "label": label,
        "n": n,
        "distinct_query_vectors": len(key_counts),
        "distinct_query_vectors_per_trajectory": (len(key_counts) / n) if n else None,
        "largest_identical_query_cluster_size": largest_size,
        "largest_identical_query_cluster_share": (largest_size / n) if n else None,
        "largest_identical_query_cluster_sample_ids": cluster[:20],
        "distinct_contact0_texts": len(text_counts),
        "distinct_contact0_texts_per_trajectory": (len(text_counts) / n) if n else None,
        "largest_identical_text_cluster_size": largest_text_size,
        "distinct_supplies": len(supply_counts),
        "distinct_supplies_per_trajectory": (len(supply_counts) / n) if n else None,
        "largest_identical_supply_size": (
            supply_counts.most_common(1)[0][1] if supply_counts else 0
        ),
        "distinct_supplies_inside_the_largest_key_cluster": len(cluster_supplies),
        "empty_supplies": supply_counts.get((), 0),
        # A landed measurement, not an assumption: if the embedding sidecar were
        # a pure function of its input text these two counts would be equal.
        # Where the vector count EXCEEDS the text count, identical texts were
        # embedded to different vectors and the distinct-TEXT count is the
        # conservative floor on key diversity.
        "distinct_query_vectors_minus_distinct_texts": len(key_counts) - len(text_counts),
        "embedding_is_a_pure_function_of_the_text": len(key_counts) == len(text_counts),
    }


def _retrieval_block(
    ids: Sequence[str],
    *,
    label: str,
    gold_positions: Mapping[str, int | None],
    gold_cosines: Mapping[str, float | None],
) -> dict[str, object]:
    """Gold-in-top-5 and the gold-facet cosine, on exactly the same records the
    degeneracy block counted -- which is the point of computing both here."""

    n = len(ids)
    in_kb = [s for s in ids if gold_positions[s] is not None]
    in_top5 = [s for s in in_kb if int(gold_positions[s]) <= FROZEN_TOP_K]
    cosines = [float(gold_cosines[s]) for s in in_kb if gold_cosines[s] is not None]
    positions = sorted(int(gold_positions[s]) for s in in_kb)
    return {
        "label": label,
        "n": n,
        "gold_present_in_kb": len(in_kb),
        "gold_in_top_5": len(in_top5),
        "gold_in_top_5_rate_over_all_members": (len(in_top5) / n) if n else None,
        "gold_facet_cosine_median": statistics.median(cosines) if cosines else None,
        "gold_facet_cosine_mean": statistics.fmean(cosines) if cosines else None,
        "gold_facet_position_median": (
            statistics.median(positions) if positions else None
        ),
    }


def answer_content_profile(
    ids: Sequence[str],
    *,
    label: str,
    texts: Mapping[str, str],
    structurally_empty: Mapping[str, bool],
) -> dict[str, object]:
    """Does the contact-0 answer carry utterance content at all?

    ``structurally empty`` is the carrier's own predicate for "this answer
    names no field content": on Audio2Tool it is
    :func:`.a2t_read.is_empty_tool_call`; on SLURP it is
    ``kb._parse_scenario_action`` returning no scenario/action pair -- the
    ``no-fields`` member of the landed dead-direct partition.

    ``tokens outside the group's modal text`` is the carrier-neutral measure of
    variation: if every member of a group emits the SAME string, this is 0 for
    all of them, and the embedding of that string is one constant key."""

    n = len(ids)
    counts = Counter(texts[sample_id] for sample_id in ids)
    modal_text = counts.most_common(1)[0][0] if counts else ""
    modal_tokens = set(tokenize(modal_text))
    novel = [len(set(tokenize(texts[s])) - modal_tokens) for s in ids]
    sizes = [len(set(tokenize(texts[s]))) for s in ids]
    lengths = [len(texts[s]) for s in ids]
    empty = [s for s in ids if structurally_empty[s]]
    return {
        "label": label,
        "n": n,
        "structurally_empty_answers": len(empty),
        "structurally_empty_answer_rate": (len(empty) / n) if n else None,
        "distinct_contact0_texts": len(counts),
        "modal_text_multiplicity": counts.most_common(1)[0][1] if counts else 0,
        "distinct_tokens_per_answer_median": statistics.median(sizes) if sizes else None,
        "tokens_outside_the_group_modal_text_median": (
            statistics.median(novel) if novel else None
        ),
        "tokens_outside_the_group_modal_text_mean": (
            statistics.fmean(novel) if novel else None
        ),
        "answers_with_zero_tokens_outside_the_modal_text": sum(
            1 for value in novel if value == 0
        ),
        "answer_length_chars_median": statistics.median(lengths) if lengths else None,
    }


def tau_distance(
    ids: Sequence[str],
    *,
    label: str,
    gold_cosines: Mapping[str, float | None],
) -> dict[str, object]:
    """How far the gold facet sits from the frozen percept gate.

    OBSERVED ONLY. Whether a differently-constructed query would clear tau is a
    COUNTERFACTUAL and cannot be established without an embedding contact,
    which this row may not take."""

    tau = FROZEN_FUSE.tau
    values = [float(gold_cosines[s]) for s in ids if gold_cosines[s] is not None]
    below = sorted(value for value in values if value < tau)
    above = sorted(value for value in values if value >= tau)
    gaps = sorted(tau - value for value in below)
    quantile = None
    if len(gaps) >= 4:
        quantile = [round(value, 6) for value in statistics.quantiles(gaps, n=4)]
    return {
        "label": label,
        "tau": tau,
        "n_with_gold_facet_in_kb": len(values),
        "gold_facet_below_tau": len(below),
        "gold_facet_at_or_above_tau": len(above),
        "gold_facet_below_tau_rate": (len(below) / len(values)) if values else None,
        "below_tau_cosine_min": below[0] if below else None,
        "below_tau_cosine_max": below[-1] if below else None,
        "below_tau_cosine_median": statistics.median(below) if below else None,
        "gap_to_tau_min": gaps[0] if gaps else None,
        "gap_to_tau_median": statistics.median(gaps) if gaps else None,
        "gap_to_tau_max": gaps[-1] if gaps else None,
        "gap_to_tau_quartiles": quantile,
        "gap_to_tau_within_0_05": sum(1 for value in gaps if value <= 0.05),
        "gap_to_tau_within_0_10": sum(1 for value in gaps if value <= 0.10),
        "counterfactual_disclosure": (
            "OBSERVED DISTRIBUTION ONLY. This row measures where the gold facet "
            "sits under the query the flight ACTUALLY embedded. It does not and "
            "cannot measure where it would sit under a differently-constructed "
            "query: that needs a new embedding contact, which this row may not "
            "take. No projection of clearing tau is made."
        ),
    }


# ---------------------------------------------------------------------------
# Q1 -- the A2T control, which is a STOP CONDITION
# ---------------------------------------------------------------------------


def a2t_control(*, data_root: Path, repo_root: Path) -> dict[str, object]:
    """Recompute the landed A2T degeneracy from the sealed attempt-4 artifacts.

    If any recomputed quantity disagrees with :data:`A2T_LANDED_CONTROL`, the
    caller must STOP: a control that cannot be reproduced cannot license a
    cross-carrier comparison."""

    carrier = ccd.load_a2t_attempt4(data_root=data_root, repo_root=repo_root)
    supplies, blends, direct_labels = ccd.replay_population(carrier)
    gate = ccd.fidelity_gate(carrier, supplies, blends, direct_labels)
    if not gate["gate_passed"]:
        raise DegeneracyError(
            "the A2T fidelity gate FAILED; no A2T number is read: " + json.dumps(gate)
        )

    geometry, probe_report, _kb_shape, _cosine_cache = agd.compute_geometry(carrier)

    dead = sorted(s for s in carrier.sample_ids if direct_labels[s] is None)
    live = sorted(s for s in carrier.sample_ids if direct_labels[s] is not None)
    flown_dispatched = sorted(
        s for s in carrier.sample_ids if carrier.flown_dispatched[s]
    )
    if dead != flown_dispatched:
        raise DegeneracyError(
            "on A2T the dead-direct set is not the flown dispatched set; the "
            "structural alpha-veto property this row relies on does not hold"
        )

    supplies_by_sample = {
        sample_id: tuple(sorted(carrier.flown_supply[sample_id]))
        for sample_id in carrier.sample_ids
    }
    dead_block = _cluster_block(
        dead,
        label="A2T dead-direct (dispatched)",
        query_vectors=carrier.inputs.query_vectors,
        texts=carrier.direct_texts,
        supplies=supplies_by_sample,
    )
    live_block = _cluster_block(
        live,
        label="A2T label-recovered (retained)",
        query_vectors=carrier.inputs.query_vectors,
        texts=carrier.direct_texts,
        supplies=supplies_by_sample,
    )

    recomputed = {
        "dead_direct_n": dead_block["n"],
        "dead_direct_distinct_query_vectors": dead_block["distinct_query_vectors"],
        "dead_direct_distinct_contact0_texts": dead_block["distinct_contact0_texts"],
        "dead_direct_largest_identical_query_cluster_size": dead_block[
            "largest_identical_query_cluster_size"
        ],
        "label_recovered_n": live_block["n"],
        "label_recovered_distinct_query_vectors": live_block["distinct_query_vectors"],
        "label_recovered_distinct_contact0_texts": live_block[
            "distinct_contact0_texts"
        ],
        "largest_cluster_distinct_flown_supplies": dead_block[
            "distinct_supplies_inside_the_largest_key_cluster"
        ],
    }
    disagreements = {
        key: {"landed": A2T_LANDED_CONTROL[key], "recomputed": value}
        for key, value in recomputed.items()
        if A2T_LANDED_CONTROL[key] != value
    }

    gold_positions = {s: geometry[s].gold_facet_position for s in carrier.sample_ids}
    gold_cosines = {s: geometry[s].gold_facet_cosine for s in carrier.sample_ids}
    structurally_empty = {
        s: bool(a2t_read.is_empty_tool_call(carrier.direct_texts[s]))
        for s in carrier.sample_ids
    }

    return {
        "carrier": "audio2tool",
        "population": "A2T-G1-104 (EXPOSED)",
        "reading_tier": EXPOSED_READING_NOTE,
        "artifact_hashes": dict(carrier.artifact_hashes),
        "fidelity_gate": gate,
        "recall_fidelity": probe_report,
        "dead_direct_is_the_flown_dispatched_set": True,
        "degeneracy": {"dead_direct": dead_block, "label_recovered": live_block},
        "supply_semantics": (
            "the A2T blocks count the FLOWN supply, which is what the landed "
            "diagnosis counted. The A2T flight records "
            "``fusion_selected_value_ids`` only for a trajectory it DISPATCHED, "
            "so all 89 label-recovered trajectories carry the empty tuple: the "
            "label-recovered supply columns are null BY CONSTRUCTION and must "
            "not be read as a degeneracy. Only the dead-direct supply columns "
            "are meaningful on this carrier. The SLURP blocks instead count the "
            "REPLAYED fusion decision, which the frozen fuser produces on every "
            "trajectory, and cross-check it against the flown supply on the "
            "dispatched dead-direct members."
        ),
        "retrieval": {
            "dead_direct": _retrieval_block(
                dead,
                label="A2T dead-direct",
                gold_positions=gold_positions,
                gold_cosines=gold_cosines,
            ),
            "label_recovered": _retrieval_block(
                live,
                label="A2T label-recovered",
                gold_positions=gold_positions,
                gold_cosines=gold_cosines,
            ),
        },
        "answer_content": {
            "dead_direct": answer_content_profile(
                dead,
                label="A2T dead-direct",
                texts=carrier.direct_texts,
                structurally_empty=structurally_empty,
            ),
            "label_recovered": answer_content_profile(
                live,
                label="A2T label-recovered",
                texts=carrier.direct_texts,
                structurally_empty=structurally_empty,
            ),
        },
        "tau_distance": {
            "dead_direct": tau_distance(
                dead, label="A2T dead-direct", gold_cosines=gold_cosines
            ),
            "label_recovered": tau_distance(
                live, label="A2T label-recovered", gold_cosines=gold_cosines
            ),
        },
        "landed_reference": dict(A2T_LANDED_CONTROL),
        "recomputed": recomputed,
        "control_reproduced": not disagreements,
        "disagreements": disagreements,
        "stop_condition": (
            "PRE-REGISTERED: if the control does not reproduce, this row reports "
            "the discrepancy and does NOT proceed to the SLURP measurement."
        ),
    }


# ---------------------------------------------------------------------------
# Q2 -- the same statistic on SLURP, on both DEV-1000 halves
# ---------------------------------------------------------------------------


def carrier_groups(
    *,
    ids: Sequence[str],
    label: str,
    reading_tier: str,
    population: cf.CellPopulation,
    replays: Mapping[str, cf.SampleReplay],
    annotated: Mapping[str, nx.AnnotatedSample],
) -> dict[str, object]:
    """One SLURP half, partitioned into dead-direct and label-recovered.

    ``dead-direct`` is ``replay.direct_label is None`` -- the SAME predicate the
    A2T side uses (``a2t_label_normalizer`` returning ``None``) and the same one
    :mod:`.dev100_next_experiment_projections` has used since the A3/A4
    projections."""

    dead = sorted(s for s in ids if replays[s].direct_label is None)
    live = sorted(s for s in ids if replays[s].direct_label is not None)

    supplies = {s: tuple(sorted(replays[s].selected_value_ids)) for s in ids}
    flown = {s: tuple(sorted(population.inputs.logged_supply.get(s, ()))) for s in ids}
    gold_positions = {s: replays[s].gold_facet_position for s in ids}
    gold_cosines = {s: replays[s].gold_facet_cosine for s in ids}
    structurally_empty = {
        s: annotated[s].joined_identity is None for s in ids
    }
    texts = {s: population.inputs.direct_texts[s] for s in ids}

    partition = Counter(
        annotated[s].dead_direct_partition() for s in dead
    )

    dispatched_dead = [s for s in dead if population.logged_contacts[s] == 2]
    flown_block = None
    if dispatched_dead:
        flown_block = _cluster_block(
            dispatched_dead,
            label=f"{label} dead-direct, FLOWN supply, dispatched only",
            query_vectors=population.inputs.query_vectors,
            texts=texts,
            supplies=flown,
        )

    return {
        "label": label,
        "reading_tier": reading_tier,
        "n": len(ids),
        "dead_direct_n": len(dead),
        "label_recovered_n": len(live),
        "dead_direct_rate": (len(dead) / len(ids)) if ids else None,
        "dead_direct_partition": {
            str(key): value for key, value in sorted(partition.items(), key=lambda kv: str(kv[0]))
        },
        "degeneracy": {
            "dead_direct": _cluster_block(
                dead,
                label=f"{label} dead-direct",
                query_vectors=population.inputs.query_vectors,
                texts=texts,
                supplies=supplies,
            ),
            "label_recovered": _cluster_block(
                live,
                label=f"{label} label-recovered",
                query_vectors=population.inputs.query_vectors,
                texts=texts,
                supplies=supplies,
            ),
        },
        "dead_direct_flown_supply_cross_check": flown_block,
        "retrieval": {
            "dead_direct": _retrieval_block(
                dead,
                label=f"{label} dead-direct",
                gold_positions=gold_positions,
                gold_cosines=gold_cosines,
            ),
            "label_recovered": _retrieval_block(
                live,
                label=f"{label} label-recovered",
                gold_positions=gold_positions,
                gold_cosines=gold_cosines,
            ),
        },
        "answer_content": {
            "dead_direct": answer_content_profile(
                dead,
                label=f"{label} dead-direct",
                texts=texts,
                structurally_empty=structurally_empty,
            ),
            "label_recovered": answer_content_profile(
                live,
                label=f"{label} label-recovered",
                texts=texts,
                structurally_empty=structurally_empty,
            ),
        },
        "tau_distance": {
            "dead_direct": tau_distance(
                dead, label=f"{label} dead-direct", gold_cosines=gold_cosines
            ),
            "label_recovered": tau_distance(
                live, label=f"{label} label-recovered", gold_cosines=gold_cosines
            ),
        },
        "supply_semantics": (
            "``distinct supplies`` counts the REPLAYED fusion decision, which "
            "the frozen fuser produces on every trajectory whether or not it "
            "dispatched, so the statistic is defined identically on both groups. "
            "``dead_direct_flown_supply_cross_check`` recounts it on the FLOWN "
            "supply over the dispatched dead-direct members, and the flight "
            "gate has already proved replayed == flown on every dispatched "
            "trajectory."
        ),
    }


# ---------------------------------------------------------------------------
# Q3 -- the cross-carrier verdict
# ---------------------------------------------------------------------------


def cross_carrier_verdict(
    a2t: Mapping[str, object], slurp_halves: Mapping[str, Mapping[str, object]]
) -> dict[str, object]:
    """The claim under test, decided by the numbers rather than by the story."""

    a2t_dead = a2t["degeneracy"]["dead_direct"]  # type: ignore[index]
    a2t_live = a2t["degeneracy"]["label_recovered"]  # type: ignore[index]
    a2t_content = a2t["answer_content"]["dead_direct"]  # type: ignore[index]

    rows: list[dict[str, object]] = [
        {
            "carrier": "audio2tool",
            "population": "A2T-G1-104 (EXPOSED)",
            "group": "dead-direct",
            "n": a2t_dead["n"],
            "distinct_query_vectors_per_trajectory": a2t_dead[
                "distinct_query_vectors_per_trajectory"
            ],
            "largest_identical_query_cluster_size": a2t_dead[
                "largest_identical_query_cluster_size"
            ],
            "structurally_empty_answer_rate": a2t_content[
                "structurally_empty_answer_rate"
            ],
        },
        {
            "carrier": "audio2tool",
            "population": "A2T-G1-104 (EXPOSED)",
            "group": "label-recovered",
            "n": a2t_live["n"],
            "distinct_query_vectors_per_trajectory": a2t_live[
                "distinct_query_vectors_per_trajectory"
            ],
            "largest_identical_query_cluster_size": a2t_live[
                "largest_identical_query_cluster_size"
            ],
            "structurally_empty_answer_rate": a2t["answer_content"][  # type: ignore[index]
                "label_recovered"
            ]["structurally_empty_answer_rate"],
        },
    ]
    degenerate_halves: list[str] = []
    for half_id, half in slurp_halves.items():
        for group in ("dead_direct", "label_recovered"):
            block = half["degeneracy"][group]  # type: ignore[index]
            content = half["answer_content"][group]  # type: ignore[index]
            rows.append(
                {
                    "carrier": "slurp",
                    "population": half["label"],
                    "group": group.replace("_", "-"),
                    "n": block["n"],
                    "distinct_query_vectors_per_trajectory": block[
                        "distinct_query_vectors_per_trajectory"
                    ],
                    "largest_identical_query_cluster_size": block[
                        "largest_identical_query_cluster_size"
                    ],
                    "structurally_empty_answer_rate": content[
                        "structurally_empty_answer_rate"
                    ],
                }
            )
        dead_ratio = half["degeneracy"]["dead_direct"][  # type: ignore[index]
            "distinct_query_vectors_per_trajectory"
        ]
        if dead_ratio is not None and float(dead_ratio) < 0.90:
            degenerate_halves.append(half_id)

    a2t_ratio = float(a2t_dead["distinct_query_vectors_per_trajectory"])

    def _discriminants(
        dead: Mapping[str, object],
        live: Mapping[str, object],
        dead_content: Mapping[str, object],
        live_content: Mapping[str, object],
        label: str,
    ) -> dict[str, object]:
        """The three quantities that separate 'the key is empty' from 'the
        label collided'. All three were fixed in the registration."""

        dead_ratio = float(dead["distinct_query_vectors_per_trajectory"])
        live_ratio = float(live["distinct_query_vectors_per_trajectory"])
        return {
            "population": label,
            # D-I: DIRECTION. On A2T the alpha veto selects the degenerate
            # subset, so dead/live is far below 1. A value at or above 1 means
            # the veto does NOT concentrate key collapse on the dispatching set.
            "dead_over_live_degeneracy_ratio": (
                dead_ratio / live_ratio if live_ratio else None
            ),
            "alpha_veto_concentrates_key_collapse_on_the_dispatching_subset": (
                dead_ratio < live_ratio
            ),
            # D-II: CONTENT. Is the shared key an answer that carries no field
            # content at all, or one that carries content and merely repeats?
            "dead_structurally_empty_answer_rate": dead_content[
                "structurally_empty_answer_rate"
            ],
            "live_structurally_empty_answer_rate": live_content[
                "structurally_empty_answer_rate"
            ],
            "dead_tokens_outside_the_group_modal_text_median": dead_content[
                "tokens_outside_the_group_modal_text_median"
            ],
            "dead_distinct_tokens_per_answer_median": dead_content[
                "distinct_tokens_per_answer_median"
            ],
            # D-III: EXTENT. How much of the group is inside ONE key.
            "dead_largest_identical_query_cluster_share": dead[
                "largest_identical_query_cluster_share"
            ],
            "dead_distinct_supplies_per_trajectory": dead[
                "distinct_supplies_per_trajectory"
            ],
        }

    discriminants = [
        _discriminants(
            a2t_dead,
            a2t_live,
            a2t["answer_content"]["dead_direct"],  # type: ignore[index]
            a2t["answer_content"]["label_recovered"],  # type: ignore[index]
            "audio2tool A2T-G1-104 (EXPOSED)",
        )
    ]
    for half in slurp_halves.values():
        discriminants.append(
            _discriminants(
                half["degeneracy"]["dead_direct"],  # type: ignore[index]
                half["degeneracy"]["label_recovered"],  # type: ignore[index]
                half["answer_content"]["dead_direct"],  # type: ignore[index]
                half["answer_content"]["label_recovered"],  # type: ignore[index]
                str(half["label"]),
            )
        )

    return {
        "claim_under_test": (
            "SLURP's dead-direct answer is a WRONG LABEL that still carries "
            "utterance content, so its query stays informative; A2T's is an "
            "EMPTY call that carries none."
        ),
        "decision_rule_fixed_in_the_registration": (
            "the degeneracy clause the A2T diagnosis introduced -- distinct "
            "query vectors per trajectory >= 0.90 -- is the threshold. A SLURP "
            "dead-direct group at or above 0.90 does NOT degenerate; a group "
            "below it DOES, and that is the headline finding either way."
        ),
        "threshold": 0.90,
        "table": rows,
        "a2t_dead_direct_degeneracy_ratio": a2t_ratio,
        "slurp_halves_below_the_pre_registered_threshold": degenerate_halves,
        "pre_registered_threshold_outcome": (
            "SLURP DEAD-DIRECT IS BELOW 0.90 ON: " + ", ".join(degenerate_halves)
            if degenerate_halves
            else "SLURP DEAD-DIRECT IS AT OR ABOVE 0.90 ON BOTH HALVES"
        ),
        "mechanism_discriminants": discriminants,
        "discriminant_semantics": (
            "the pre-registered 0.90 clause is a ONE-SIDED absolute threshold "
            "and, by construction, cannot tell 'the key is shared because the "
            "answer was empty' apart from 'the key is shared because two "
            "utterances genuinely carry the same short label'. The three "
            "discriminants above were fixed in the same registration and do "
            "separate them: DIRECTION (does the alpha veto concentrate key "
            "collapse on the dispatching subset?), CONTENT (does the shared "
            "answer name any field at all?) and EXTENT (what share of the "
            "group sits inside one key?). The threshold outcome and the "
            "discriminants are both reported; neither is suppressed."
        ),
        "reading_rule": (
            "PRE-REGISTERED: reported whichever way it comes out. A SLURP set "
            "that DOES degenerate is the headline finding, not a reason to "
            "re-partition the population or re-choose the statistic."
        ),
    }


# ---------------------------------------------------------------------------
# The two-sided falsifier for the candidate fix
# ---------------------------------------------------------------------------


def separated_query_falsifier(
    a2t: Mapping[str, object], slurp_halves: Mapping[str, Mapping[str, object]]
) -> dict[str, object]:
    """The two-sided falsifier for SQ (SEPARATED QUERY), pre-registered here.

    The candidate fix is: contact-0 emits a retrieval query SEPARATELY from its
    answer attempt, so the query stays informative when the answer is empty.

    TRAP CATEGORY. K3 (field-role-constrained contact-0) was REFUSED for
    Audio2Tool because it improves the QUERY by making the ANSWER better, and a
    better-formed answer recovers a direct label, whereupon the alpha veto
    suppresses dispatch: projected dispatch 15/104 -> 3/104, -80 % relative,
    worse than the already-rejected E-C variant. SQ is in the OTHER category:
    it leaves the answer channel untouched and adds a second, separately
    emitted field, so the label normalizer sees exactly what it saw before and
    the alpha veto's retain/dispatch decision is -- by construction -- expected
    to be invariant. D1 below is what turns that expectation into a refutable
    claim rather than a design argument.

    The degeneracy clause is ANCHORED ON EACH CARRIER'S OWN MEASURED
    label-recovered reference rather than on A2T's number applied everywhere:
    this row measures 0.944 on A2T and 0.685 / 0.716 on the two SLURP halves,
    so a single absolute 0.90 bar is A2T-calibrated and mis-anchored on SLURP.
    """

    anchors = {
        "audio2tool_A2T_G1_104": {
            "dead_direct_distinct_query_vectors_per_trajectory": a2t["degeneracy"][  # type: ignore[index]
                "dead_direct"
            ]["distinct_query_vectors_per_trajectory"],
            "label_recovered_distinct_query_vectors_per_trajectory": a2t[  # type: ignore[index]
                "degeneracy"
            ]["label_recovered"]["distinct_query_vectors_per_trajectory"],
        }
    }
    for half_id, half in slurp_halves.items():
        anchors[f"slurp_{half_id}"] = {
            "dead_direct_distinct_query_vectors_per_trajectory": half["degeneracy"][  # type: ignore[index]
                "dead_direct"
            ]["distinct_query_vectors_per_trajectory"],
            "label_recovered_distinct_query_vectors_per_trajectory": half[  # type: ignore[index]
                "degeneracy"
            ]["label_recovered"]["distinct_query_vectors_per_trajectory"],
        }

    return {
        "measured_anchors": anchors,
        "item_id": "SQ",
        "name": "separated retrieval query at contact 0",
        "change": (
            "contact-0 emits a retrieval query SEPARATELY from its answer "
            "attempt -- a distinct field whose text is embedded as the content "
            "dimension's key -- so the query stays informative when the answer "
            "itself is empty or malformed."
        ),
        "trap_category": {
            "category": "SEPARATES the query from the answer",
            "contrast": (
                "K3 (field-role-constrained contact-0) improves the query by "
                "making the ANSWER better. On Audio2Tool that was measured to "
                "project dispatch 15/104 -> 3/104, -80 % relative -- worse than "
                "the rejected E-C variant -- because a better-formed contact-0 "
                "recovers a direct label and the alpha veto then suppresses "
                "dispatch. Any fix in K3's category inherits that trap."
            ),
            "why_SQ_may_not_inherit_it": (
                "SQ does not touch the answer field, so "
                "``default_label_normalizer`` / ``a2t_label_normalizer`` sees "
                "the same string it saw before and the retain/dispatch decision "
                "is expected to be invariant. That expectation is a DESIGN "
                "ARGUMENT, not a measurement, which is exactly why D1 is stated "
                "as a hard bound and not as a prediction."
            ),
            "residual_risk_named": (
                "asking for a second field changes the decode and can perturb "
                "the answer field as a side effect; D1 and D3 are the clauses "
                "that catch that, and they must be measured on the SAME flight, "
                "not argued away."
            ),
        },
        "must_improve": {
            "I1": (
                "Gold-facet recall@1 on the dead-direct subgroup rises by "
                ">= +5.0 pp under the separated query, measured on the carrier "
                "whose dead-direct subgroup is large enough to see an effect "
                "that size. Recall@1, not recall@5: this is the K1 correction, "
                "and it is stated first because K1's own falsifier omitted it "
                "(recall@5 rose while recall@1 fell 23/500)."
            ),
            "I2": (
                "Median gold-facet cosine on the dead-direct subgroup rises by "
                ">= +0.03 toward the label-recovered subgroup's value on the "
                "same flight."
            ),
            "I3": (
                "DEGENERACY CLAUSE, carried from the A2T gold-absence "
                "diagnosis and RE-ANCHORED here. It APPLIES ON AUDIO2TOOL as "
                "the diagnosis wrote it: distinct query vectors per dead-direct "
                "trajectory >= 0.90, against a measured 0.333 dead-direct and "
                "0.944 label-recovered on that carrier. A separated query that "
                "emits the same skeleton on every empty answer changes the text "
                "and not the key, and would pass I1/I2 by accident on a small "
                "sample while fixing nothing. IT DOES NOT APPLY VERBATIM ON "
                "SLURP: this row measures SLURP's dead-direct subgroup at 0.850 "
                "(unexposed NEW500) and 0.735 (exposed DEV-500) against a "
                "LABEL-RECOVERED reference of 0.685 and 0.716 on the same "
                "halves -- i.e. SLURP's dead-direct keys are already MORE "
                "diverse than that carrier's own healthy reference, and an "
                "absolute 0.90 bar would demand of the dead-direct subgroup "
                "something the label-recovered subgroup does not meet either. "
                "On SLURP the clause binds as the non-degradation bound D5, "
                "measured against that carrier's own label-recovered reference."
            ),
            "I4": (
                "At SUPPLY level, after the tau / top-m / top_l stages: newly "
                "gold-supplied among currently-WRONG dispatched > gold-supply "
                "LOST among currently-CORRECT. Rank-level improvement does not "
                "substitute; this is the account K1 failed (12 gained against "
                "29-40 lost)."
            ),
        },
        "must_not_degrade": {
            "D1": (
                "DISPATCH-PRESERVATION CLAUSE, mandatory. Projected dispatch "
                "count falls by no more than 10 % relative on the gated "
                "population, measured from the flight's own landed answers "
                "through the SAME label normalizer. This is the clause that "
                "refused K3 on Audio2Tool (-13.3 % on the most conservative "
                "arm, -80.0 % on the arm that measures actual form repair). SQ "
                "expects invariance here; if the measurement says otherwise, SQ "
                "is an off-switch in disguise and is refused exactly as K3 and "
                "E-C were."
            ),
            "D2": (
                "Gold-facet recall@1 on the label-recovered (retained) subgroup "
                "does not fall. SQ rewrites the query on EVERY trajectory, not "
                "only the dead-direct ones."
            ),
            "D3": (
                "No currently-CORRECT retained trajectory moves into dispatch. "
                "The alpha veto's structural guarantee (retain == "
                "direct-label-recovered) is what keeps evidence away from "
                "correct answers; a change that breaks a label recovery "
                "converts a correct retain into a dispatch, which the measured "
                "anchors price at a loss."
            ),
            "D4": (
                "The conversion-weighted product reach share x within-reach "
                "conversion, projected with the measured rank anchors (98.2 % "
                "at fused top-1, 69.6 % at rank 2-3, 0 % absent -- cited to "
                "``analysis.k1_hybrid_ranking_gate.ANCHOR_TOP1 / ANCHOR_RANK23 "
                "/ ANCHOR_ABSENT``), does not fall."
            ),
            "D5": (
                "DEGENERACY NON-DEGRADATION, the SLURP-binding form of I3. "
                "Distinct query vectors per trajectory does not FALL on either "
                "subgroup of either carrier, measured against that carrier's "
                "OWN landed values in ``measured_anchors``, and the dead-direct "
                "subgroup does not fall below its own carrier's label-recovered "
                "reference. On SLURP this is the operative clause: the keys "
                "there repeat because short labels COLLIDE, not because answers "
                "are empty (structurally-empty dead-direct answers are 2/160 "
                "and 3/166), so the only way a separated query can hurt SLURP "
                "is by collapsing its keys toward a shared query skeleton -- "
                "which is exactly the failure mode a role-schema-shaped "
                "separated query is most likely to produce."
            ),
        },
        "reporting_rule": (
            "A negative outcome is the finding and is reported as such. The "
            "query construction, the separated-field schema and the prompt text "
            "are fixed in the gating module before it runs, and none may be "
            "re-tried after the answer is seen. Any SQ flight is NEW400-tier or "
            "larger, read once, per the key-construction plan's "
            "statistical-honesty clause."
        ),
        "authority": (
            "PRE-REGISTERED ONLY. This falsifier opens no gate, authorizes no "
            "flight and is not an agenda item; SQ needs its own registration "
            "and its own owner decision."
        ),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(*, repo_root: Path, data_root: Path, out_path: Path) -> dict[str, object]:
    attempts = audit.arm_offline_guard()
    started = time.perf_counter()

    package_file = Path(kb.__file__).resolve()
    if not package_file.as_posix().startswith("/mnt/d/"):
        raise DegeneracyError(
            f"imported rails.kb_policy from {package_file}, not the /mnt/d/ checkout"
        )
    if "speech-aware-evidence-acquisition" not in package_file.as_posix():
        raise DegeneracyError(
            f"imported rails.kb_policy from {package_file}, not this study checkout"
        )

    repo_root = Path(repo_root)
    data_root = Path(data_root)

    # --- Q1: the control, which is a stop condition -----------------------
    control = a2t_control(data_root=data_root, repo_root=repo_root)
    if not control["control_reproduced"]:
        raise DegeneracyError(
            "the A2T control did NOT reproduce; the cross-carrier comparison is "
            "refused: " + json.dumps(control["disagreements"])
        )

    # --- Q2: SLURP, both halves -------------------------------------------
    bundle = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    populations = k1.load_populations(repo_root)
    byte_pins = k1.assert_dev1000_byte_pins(repo_root=repo_root, data_root=data_root)
    override_fires = k1.load_override_fires(data_root=data_root)

    population = cf.load_cell_population(
        pin=DEV1000_ALL_PIN,
        bundle=bundle,
        populations=populations,
        data_root=data_root,
        repo_root=repo_root,
    )
    if len(population.sample_ids) != 1000:
        raise DegeneracyError(
            f"the DEV-1000 BLEND arm carries {len(population.sample_ids)} ids, not 1,000"
        )
    text_identity = k1.assert_query_text_identity(population=population)
    if not text_identity["passed"]:
        raise DegeneracyError(
            "the flown direct-decode texts do not re-hash to the digests the "
            "flight's own embedding contacts recorded"
        )

    replays, flight_gate = cf.replay_population(population, bundle)
    mismatches = {
        str(item["sample_id"])
        for item in flight_gate["retain_dispatch_decision_mismatches"]
    }
    unexplained = mismatches - override_fires
    flight_gate["v2_override_deviation"] = {
        "explanation": (
            "the DEV-1000 BLEND arm flew the v2 delta>=0.14 retain-override, "
            "which the lock read FALSIFIED out of sample and which the locked v1 "
            "cell does not carry; the v1 replay therefore disagrees with the "
            "flown contact count on exactly the override fires. The override "
            "requires a RECOVERED direct label to disagree with, so it never "
            "fires on a dead-direct trajectory and cannot move this row's "
            "partition."
        ),
        "override_fires_in_population": len(
            override_fires & set(population.sample_ids)
        ),
        "mismatch_count": len(mismatches),
        "mismatches_all_explained_by_the_override": not unexplained,
        "unexplained_mismatch_sample_ids": sorted(unexplained)[:10],
    }
    if unexplained:
        raise DegeneracyError(
            f"{len(unexplained)} DEV-1000 dispatch mismatches are NOT override "
            "fires -- the replay does not reproduce the flight"
        )
    if not flight_gate["supply_gate_passed"]:
        raise DegeneracyError("the flown DEV-1000 SUPPLY was not reproduced exactly")

    override_dead = sorted(
        s
        for s in population.sample_ids
        if s in override_fires and replays[s].direct_label is None
    )
    if override_dead:
        raise DegeneracyError(
            "a v2 override fired on a dead-direct trajectory, which the "
            "override's own disagreement precondition forbids"
        )

    annotated = nx.annotate_population(population, replays, bundle)

    halves = {
        "UNEXPOSED-NEW500": carrier_groups(
            ids=sorted(populations.new500),
            label="SLURP DEV-1000 unexposed NEW500",
            reading_tier=SECONDARY_READING_NOTE,
            population=population,
            replays=replays,
            annotated=annotated,
        ),
        "EXPOSED-DEV500": carrier_groups(
            ids=sorted(populations.dev500),
            label="SLURP DEV-1000 prior-exposed nested DEV-500",
            reading_tier=EXPOSED_READING_NOTE,
            population=population,
            replays=replays,
            annotated=annotated,
        ),
    }

    verdict = cross_carrier_verdict(control, halves)

    report: dict[str, object] = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "contacts": {
            "frozen_core": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "audio_seconds": 0.0,
            "gpu_hours": 0.0,
            "outbound_connection_attempts": attempts.count,
            "outbound_targets": list(attempts.targets),
            "gold_opened": (
                "SCORING-SIDE ONLY, over populations whose seal the landed "
                "DEV-1000 lock read and the landed A2T G1 read already broke; "
                "never on a runtime path"
            ),
        },
        "frozen_cell": {
            "alpha": FROZEN_ALPHA,
            "tau": FROZEN_FUSE.tau,
            "m": FROZEN_FUSE.m,
            "c": FROZEN_FUSE.c,
            "top_l": FROZEN_FUSE.top_l,
            "top_k": FROZEN_TOP_K,
            "weights": {
                "w_cos": FROZEN_WEIGHTS.w_cos,
                "w_prior": FROZEN_WEIGHTS.w_prior,
                "w_agree": FROZEN_WEIGHTS.w_agree,
            },
        },
        "a2t_control": control,
        "slurp": {
            "run_id": d1k.RUN_ID,
            "blend_attempt_id": DEV1000_ALL_PIN.attempt_id,
            "m0_attempt_id": next(
                pin.attempt_id for pin in d1k.ARM_PINS if pin.arm_id == "M0"
            ),
            "run_dir": str(population.run_dir),
            "artifact_hashes": dict(population.artifact_hashes),
            "committed_byte_pins": byte_pins,
            "snapshot_sha256": bundle.snapshot_sha256,
            "content_facet_npz_sha256": bundle.npz_sha256,
            "query_vector_source": str(population.run_dir / "query-vectors.jsonl"),
            "query_text_identity": text_identity,
            "flight_gate": flight_gate,
            "halves": halves,
            "m0_arm_role": (
                "the M0 attempt is the baseline arm and carries no retrieval "
                "query: it takes one direct contact per sample and never embeds "
                "an answer. Every query vector in this row is the BLEND arm's, "
                "which is the only arm that has one."
            ),
        },
        "q3_cross_carrier_verdict": verdict,
        "separated_query_falsifier": separated_query_falsifier(control, halves),
        "hard_stop": (
            "MEASUREMENT ONLY. No knob is changed, no flight is authorized, no "
            "gate is opened, no test contact is taken, and no generality or "
            "superiority claim follows from this artifact. The SLURP unexposed "
            "NEW500 statistics are a SECONDARY READING and may not revise, "
            "re-tune or restate the lock."
        ),
    }
    report["wall_seconds"] = round(time.perf_counter() - started, 3)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="cross-carrier query-key degeneracy")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    report = run(
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
        out_path=Path(args.out),
    )
    print(json.dumps(report["q3_cross_carrier_verdict"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
