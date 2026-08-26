"""DATASTORE SCORING ALIGNMENT -- replace a self-invented coverage-ratio family
with the field's standard datastore metrics, at ZERO CONTACTS.

Row ``SAEA-SN-MF-DATASTORE-SCORING-ALIGNMENT`` (``model-free-check``),
registered in ``docs/exposure-ledger.md`` BEFORE any number here was computed.

WHY THIS EXISTS. Two landed audits established that this study invented a
metric family that cannot fail:

* ``docs/readiness/2026-08-25-slurp-intent-coverage-check.md`` section Q4 --
  ``rails.knowledge_build.coverage_report``'s ``intent_coverage`` is 1.0 with
  probability one at the landed configuration (``datastore_size=None`` makes
  ``selected == rows`` identically), and its denominator is TRAIN-derived
  while the contract clause it serves is about TASK targets.
* ``docs/readiness/2026-08-25-gate-audit-can-it-fail.md`` rows 1, 2, 5, 6, 7 --
  both KB-BUILD decontamination gates and all six A2T coverage metrics
  classify CANNOT FAIL, and ``tool_coverage``'s denominator is NARROWER THAN
  ITS CLAIM (registry 152, construction pool 151, ``getLockStatus`` modelled
  by nothing while the metric reads 1.0).

SAMPLING IS NOT THE PROBLEM and this module does not re-litigate it: SLURP
loads 60 intents, samples 60 and emits 60, and the landed build sampled
nothing at all; A2T's ``getLockStatus`` has no invocation anywhere in the
corpus, so there is nothing to sample.

WHAT THE FIELD DOES, and what this module implements instead of inventing a
fourth thing:

1. :func:`scaling_curve` -- DATASTORE SIZE AS A SWEPT AXIS with a scaling
   curve, not a coverage ratio (MassiveDS discipline; this repository's own
   plan already called for 1k / 5k / full and it was never run).
2. :func:`support_distribution` -- PER-TARGET SUPPORT: exemplars per intent /
   per tool, with the long-tail shape reported (min, quantiles, the count of
   targets at support 1 and at support 0), the way long-tail classification
   and K-shot cache work report support rather than a coverage flag.
3. :func:`gold_recall_curve` -- GOLD RECALL@k MEASURED AGAINST THE EVAL
   POPULATION'S GOLD. The denominator is the queries we care about, never the
   datastore's own contents. This already existed in this repository and has
   been doing the real work (the gold-absence diagnosis's reachability curve,
   K-WIDEN, K1); here it becomes a first-class reported metric rather than
   something each analysis re-derives.
4. :func:`decontamination_intersection` -- DECONTAMINATION AS THE MEASURED
   INTERSECTION COUNT plus the identities of any intersecting items, never an
   always-true boolean verdict.

THE ZERO-CONTACT ROUTE TO THE SCALING CURVE. A smaller datastore is a SUBSET
of the full one, and both builders emit content facets keyed
``facet:content:<row id>`` whose ``representation`` is the row's own text
(``rails.knowledge_build._build_facets_and_values`` /
``rails.knowledge_build_a2t._build_facets_and_values``). A reduced tier's
content-facet vectors are therefore ALREADY INSIDE the landed full NPZ, so the
candidate set is RESTRICTED rather than rebuilt and re-embedded. That is not
argued, it is PROVED at every swept size by :func:`prove_restriction_is_exact`,
which builds that size's snapshot IN MEMORY (a pure model-free function of the
pool rows; nothing is written to disk) and asserts content-facet-id subset plus
representation equality against the pinned full snapshot. A size where that is
not sound STOPS the sweep rather than buying an embedding contact.

WHAT IS OUT OF SCOPE, STATED SO IT IS NOT MISREAD. The restriction is exact for
the CONTENT dimension, which is the vector-recalled one. The label / prior /
speaker facets carry per-snapshot counts in their representation text and their
``prior_score`` is renormalised by the selection, so a full four-dimension
POLICY REPLAY at a reduced size is NOT reproducible by restriction and is not
attempted. Everything reported per size here is a retrieval-side quantity over
the content dimension, exactly as the field's recall@k is.

EVERY METRIC MUST BE SHOWN ABLE TO FAIL. :func:`mutation_battery` constructs,
for each of the four metrics, a concrete mutation that SHOULD break it, runs
it, and records the observed outcome. If a mutation does NOT move the metric,
:func:`mutation_battery` RAISES: landing another metric that cannot fail would
be worse than doing nothing, so the proof obligation is machine-enforced rather
than narrated.

WHAT IT DOES NOT DO. It changes no knob, rebuilds no snapshot on disk,
displaces nothing hash-pinned, and writes nothing under ``configs/``,
``rails/`` or ``core/``. The old metrics are left exactly where they are, in
``rails.knowledge_build.coverage_report`` /
``rails.knowledge_build_a2t.coverage_report_a2t`` and in the landed receipts
under ``docs/receipts/knowledge/``; :data:`SUPERSEDED_METRICS` records each of
them beside its replacement, marked superseded-and-uninformative with a pointer
to the audit that showed it. It opens no model session, no embedding sidecar
and no tokenizer: :func:`run` arms
``analysis.dev100_reviewer_audit.arm_offline_guard`` BEFORE the first input is
opened and writes the recorded outbound-attempt count into the receipt.

THE UNEXPOSED 500 INSIDE DEV-1000 IS THE LOCKED CELL'S OWN POPULATION. Every
number this module computes on it is a SECONDARY, DESCRIPTIVE READING, carries
:data:`SECONDARY_READING_CAVEAT`, and must NOT be used to revise, re-tune or
restate the 2026-08-25 baseline lock.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONPATH=<repo>/src \\
      python -m speech_aware_evidence_acquisition.analysis.datastore_scoring_alignment \\
        --repo-root <repo> --data-root $SPEECHRL_DATA_DIR --out <receipt>
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import random
import re
import time
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from . import a2t_admission_scale_sweep as sweep
from . import contrast_fewshot_preanalysis as cf
from . import cross_carrier_ceiling_decomposition as ccd
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as audit
from . import dev1000_lock_read as lr
from ..rails import kb_policy as kb

EXPOSURE_ROW_ID = "SAEA-SN-MF-DATASTORE-SCORING-ALIGNMENT"
SCHEMA = "saea-datastore-scoring-alignment-v1"

#: The swept datastore-size axis. ``None`` is the full tier. The two builders'
#: hard floors mean the ACTUAL size can exceed the requested one; the actual is
#: what every cell reports.
SIZE_GRID: tuple[int | None, ...] = (100, 500, 1000, 5000, None)

#: The recall@k grid. The lower half is the study's own operating region
#: (``FROZEN_TOP_K`` is 5) and the upper half is the reachability tail the
#: gold-absence diagnosis and K-WIDEN already read at.
K_GRID: tuple[int, ...] = (1, 5, 8, 16, 32, 64, 128, 256, 512)

#: Word n-gram width for the decontamination overlap test. An item with fewer
#: than this many tokens contributes its whole token sequence as a single gram
#: -- the standard short-document convention, stated so the number is readable.
DECONTAMINATION_NGRAM = 8

#: How many identities any intersection block prints before it truncates. The
#: COUNT is always exact; only the listing is capped.
IDENTITY_CAP = 50

#: How many samples per carrier are cross-checked against a REAL
#: ``kb.multidim_recall`` call before this module's vectorised ranking is
#: believed.
RECALL_FIDELITY_PROBES = cf.RECALL_FIDELITY_PROBES

FROZEN_TOP_K = cf.FROZEN_TOP_K

SECONDARY_READING_CAVEAT = (
    "SECONDARY READING. The SLURP unexposed 500 inside DEV-1000 is the LOCKED "
    "baseline's own population. Every number computed on it here is a "
    "secondary, descriptive retrieval-side reading over already-sealed records "
    "and must NOT be used to revise, re-tune or restate the 2026-08-25 "
    "baseline lock."
)

#: The old metrics, kept BESIDE the new ones rather than deleted. Each entry
#: names the metric, where its last landed value lives, what that value was,
#: which audit classified it, and which new metric replaces it.
SUPERSEDED_METRICS: tuple[Mapping[str, object], ...] = (
    {
        "metric": "intent_coverage",
        "carrier": "slurp",
        "implementation": "rails.knowledge_build.coverage_report",
        "last_landed_value": 1.0,
        "last_landed_receipt": "docs/receipts/knowledge/slurp-kb-size-full.json",
        "classified_by": "docs/readiness/2026-08-25-slurp-intent-coverage-check.md section Q4",
        "classification": "CANNOT FAIL",
        "why": (
            "1.0 with probability one at the landed configuration "
            "(datastore_size=None makes selected == rows identically), and the "
            "denominator is TRAIN-derived while the contract clause it serves is "
            "about TASK targets"
        ),
        "replaced_by": "support_distribution + gold_recall_curve, swept over datastore size",
    },
    {
        "metric": "scenario_coverage / action_coverage / entity_type_coverage / "
        "long_tail_coverage.* / cluster_coverage_proxy / "
        "kl_selected_given_train_over_intent",
        "carrier": "slurp",
        "implementation": "rails.knowledge_build.coverage_report",
        "last_landed_value": "1.0 / 1.0 / 1.0 / 1.0 / 1.0 / 0.0",
        "last_landed_receipt": "docs/receipts/knowledge/slurp-kb-size-full.json",
        "classified_by": "docs/readiness/2026-08-25-gate-audit-can-it-fail.md row 5",
        "classification": "CANNOT FAIL",
        "why": (
            "1.0 (and KL 0.0) in every one of the ten swept cells; at "
            "datastore_size=1 the stratified sampler still returns 90 utterances "
            "covering all 60 intents, so the size argument is a floor, not a cap"
        ),
        "replaced_by": "support_distribution + scaling_curve",
    },
    {
        "metric": "tool_coverage / tier_coverage / category_coverage / "
        "argument_key_coverage / argument_pattern_family_coverage / "
        "long_tail_coverage.*",
        "carrier": "audio2tool",
        "implementation": "rails.knowledge_build_a2t.coverage_report_a2t",
        "last_landed_value": 1.0,
        "last_landed_receipt": "docs/receipts/knowledge/a2t-kb-size-full.json",
        "classified_by": "docs/readiness/2026-08-25-gate-audit-can-it-fail.md rows 6 and 7",
        "classification": "CANNOT FAIL (row 6); NARROWER THAN ITS CLAIM (row 7)",
        "why": (
            "1.0 in every swept cell, and tool_coverage's denominator is the "
            "construction pool it was drawn from (151) rather than the frozen "
            "registry the core may call (152), so getLockStatus is modelled by "
            "nothing while the metric reads 1.0"
        ),
        "replaced_by": (
            "support_distribution denominated on the FROZEN TOOL REGISTRY, which "
            "reports getLockStatus at support 0"
        ),
    },
    {
        "metric": "decontamination.verdict",
        "carrier": "slurp and audio2tool",
        "implementation": (
            "scripts/build_knowledge_snapshot.py:153 and "
            "scripts/build_a2t_knowledge_snapshot.py:217"
        ),
        "last_landed_value": "clean",
        "last_landed_receipt": (
            "docs/receipts/knowledge/slurp-kb-size-full.json and "
            "docs/receipts/knowledge/a2t-kb-size-full.json"
        ),
        "classified_by": "docs/readiness/2026-08-25-gate-audit-can-it-fail.md rows 1, 2 and 4",
        "classification": "CANNOT FAIL",
        "why": (
            "the string 'clean' is a Python literal with no other reachable "
            "value, and the id intersection it reports is structurally empty "
            "(SLURP ids are split-namespaced; the A2T construction pool is "
            "literally pool minus eval minus exposed)"
        ),
        "replaced_by": (
            "decontamination_intersection, which reports the MEASURED count at "
            "three granularities with the identities of anything that intersects"
        ),
    },
)

#: What the field does, and the source this module took each item from. This
#: row took ZERO NETWORK CONTACTS, so nothing was fetched: every source below is
#: an ALREADY-LANDED, addressable entry in this repository's own commissioned
#: survey (``docs/readiness/2026-08-23-cross-modal-retrieval-survey.md``), which
#: is itself the record of the coordinator-directed web survey of 2026-08-23.
#: Carried in the receipt so the alignment claim is checkable without the
#: document.
SURVEY_RELPATH = "docs/readiness/2026-08-23-cross-modal-retrieval-survey.md"

FIELD_PRACTICE: tuple[Mapping[str, str], ...] = (
    {
        "practice": "datastore size as a swept axis with a scaling curve",
        "field_source": (
            "MassiveDS (Shao et al., NeurIPS 2024) -- trillion-token datastore scaling, "
            "'size is a reported axis'"
        ),
        "source_record": f"{SURVEY_RELPATH} lane 1 item 5",
        "source_mapping_line": (
            "'the template for the KB scaling curve and decontamination discipline' -- the "
            "survey's own mapping line, written on 2026-08-23"
        ),
        "our_own_prior_call": (
            "docs/readiness/2026-08-23-cross-modal-retrieval-survey.md section 'MassiveDS "
            "hygiene: KB scaling curve with decontamination and dev-only knob tuning' called "
            "for it, and the 1k / 5k / full snapshots were BUILT but never read as a curve"
        ),
        "implemented_by": "scaling_curve",
    },
    {
        "practice": "per-target support distribution with the long-tail shape",
        "field_source": (
            "Long-tail crisis in NN LMs (2025, arXiv 2503.22426) -- gains concentrate on a "
            "minority of targets and retrieval actively hurts elsewhere; Tip-Adapter (Zhang "
            "et al., ECCV 2022) -- a training-free K-shot key-value cache whose behaviour is "
            "read per class and per shot count"
        ),
        "source_record": f"{SURVEY_RELPATH} lane 1 item 3 and lane 2 item 15",
        "source_mapping_line": (
            "'report per-class and per-bucket deltas on dev, never aggregate only' -- the "
            "survey's own mapping line"
        ),
        "our_own_prior_call": (
            "the landed build receipts already carried a top-10 target histogram; the tail, "
            "the quantiles, the count at support 1 and the count at support 0 were never "
            "reported, and a coverage RATIO was reported instead"
        ),
        "implemented_by": "support_distribution",
    },
    {
        "practice": "gold recall@k against the eval population's gold",
        "field_source": (
            "retrieve-then-rerank evaluation -- ColBERTv2 (NAACL 2022), RankGPT (Sun et al., "
            "EMNLP 2023) and the listwise rerankers -- denominates recall on the QUERIES "
            "being served, never on the index's own contents"
        ),
        "source_record": f"{SURVEY_RELPATH} lane 1 item 12",
        "source_mapping_line": (
            "'cheap multi-dim recall, then one reranker fusing dimensions' -- recall depth is "
            "the reported axis, and it is reported over the query set"
        ),
        "our_own_prior_call": (
            "docs/readiness/2026-08-25-a2t-gold-absence-diagnosis.md's k = 5..1024 "
            "reachability curve, the K-WIDEN round and the K1 hybrid-ranking gate already did "
            "exactly this; it was RE-DERIVED per analysis instead of reported as a metric"
        ),
        "implemented_by": "gold_recall_curve",
    },
    {
        "practice": "decontamination as a measured intersection count",
        "field_source": (
            "MassiveDS (Shao et al., NeurIPS 2024) -- 'explicit decontamination vs eval "
            "sets'; RETRO (Borgeaud et al., ICML 2022) -- quantifies train/test leakage via "
            "n-gram overlap and stratifies results by it"
        ),
        "source_record": f"{SURVEY_RELPATH} lane 1 items 5 and 6",
        "source_mapping_line": (
            "'report accuracy stratified by train-eval near-duplicate overlap' -- which "
            "requires a MEASURED overlap, not a verdict string"
        ),
        "our_own_prior_call": (
            "the landed builders publish decontamination.verdict = 'clean', which is a Python "
            "literal with no other reachable value"
        ),
        "implemented_by": "decontamination_intersection",
    },
)


class AlignmentError(RuntimeError):
    """A pinned identity, a restriction proof or a mutation obligation failed."""


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path):
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


_PUNCTUATION = re.compile(r"[^0-9a-z]+")


def normalise_text(text: str) -> str:
    """Decontamination normalisation: case-folded, punctuation-stripped,
    whitespace-collapsed. Two items whose normalised forms are equal are the
    same item for overlap purposes."""

    return " ".join(_PUNCTUATION.sub(" ", str(text).lower()).split())


def _quantile(sorted_values: Sequence[int], q: float) -> int:
    """Nearest-rank quantile (inclusive): ``sorted[ceil(q*n) - 1]``.

    Chosen over interpolation because a support count is a count -- an
    interpolated 3.5 exemplars is not a thing that exists."""

    if not sorted_values:
        raise AlignmentError("_quantile: empty sequence")
    if not 0.0 < q <= 1.0:
        raise AlignmentError("_quantile: q must be in (0, 1]")
    n = len(sorted_values)
    return int(sorted_values[min(n - 1, max(0, math.ceil(q * n) - 1))])


# ---------------------------------------------------------------------------
# METRIC 2 -- per-target support distribution
# ---------------------------------------------------------------------------


def support_distribution(
    *,
    support_by_target: Mapping[str, int],
    task_target_space: Iterable[str],
    identity_cap: int = IDENTITY_CAP,
) -> dict[str, object]:
    """Exemplars per task target, with the long-tail shape.

    ``task_target_space`` is the denominator and it is the TASK's, never the
    datastore's: a target the task may require but the datastore does not
    contain appears here at support 0, which is precisely the failure the
    replaced coverage ratios could not express. A target the datastore holds
    that is OUTSIDE the declared task space is reported too
    (``targets_outside_task_space``) rather than silently dropped -- that shape
    means the declared space is itself too narrow.
    """

    space = sorted({str(target) for target in task_target_space})
    if not space:
        raise AlignmentError("support_distribution: the task target space is empty")
    supports = {str(target): int(count) for target, count in support_by_target.items()}
    for target, count in supports.items():
        if count < 0:
            raise AlignmentError(f"support_distribution: negative support for {target!r}")

    outside = sorted(set(supports) - set(space))
    per_target = {target: supports.get(target, 0) for target in space}
    values = sorted(per_target.values())

    zero = sorted(target for target, count in per_target.items() if count == 0)
    ones = sorted(target for target, count in per_target.items() if count == 1)
    below_5 = sorted(target for target, count in per_target.items() if 0 < count < 5)
    total = sum(values)

    return {
        "task_target_space_size": len(space),
        "total_exemplars": total,
        "targets_with_zero_support": len(zero),
        "zero_support_targets": zero[:identity_cap],
        "zero_support_targets_truncated": max(0, len(zero) - identity_cap),
        "targets_with_support_1": len(ones),
        "support_1_targets": ones[:identity_cap],
        "targets_with_support_below_5": len(below_5),
        "min": values[0],
        "p05": _quantile(values, 0.05),
        "p25": _quantile(values, 0.25),
        "p50": _quantile(values, 0.50),
        "p75": _quantile(values, 0.75),
        "p95": _quantile(values, 0.95),
        "max": values[-1],
        "mean": round(total / len(space), 4),
        "targets_outside_task_space": len(outside),
        "outside_task_space_targets": outside[:identity_cap],
        "quantile_convention": "nearest-rank inclusive: sorted[ceil(q*n) - 1]",
    }


# ---------------------------------------------------------------------------
# METRIC 3 -- gold recall@k against the EVAL population's gold
# ---------------------------------------------------------------------------


def gold_recall_curve(
    *,
    cosines,
    facet_target_index,
    facet_id_rank,
    candidate_mask,
    gold_target_index: Sequence[int],
    k_grid: Sequence[int] = K_GRID,
) -> dict[str, object]:
    """Recall@k of a gold-bearing content facet, denominated on the QUERIES.

    ``cosines`` is ``(n_queries, n_facets)``; ``facet_target_index`` maps each
    facet row to its value's ``task_target`` (as an int code);
    ``gold_target_index[i]`` is query ``i``'s gold target code, or ``-1`` when
    the gold target has no code at all. ``candidate_mask`` is the boolean
    restriction that makes a reduced datastore tier out of the full landed
    matrix.

    The ordering is ``kb.multidim_recall``'s own: cosine descending with
    ``facet_id`` ascending as the tie-break, and a facet is recalled only at a
    STRICTLY POSITIVE score. A query whose gold is absent from the restricted
    datastore, or present only at a non-positive cosine, is a MISS at every k
    -- it is never removed from the denominator. That is the whole point of the
    metric.
    """

    import numpy as np

    cosines = np.asarray(cosines, dtype=np.float64)
    facet_target_index = np.asarray(facet_target_index, dtype=np.int64)
    facet_id_rank = np.asarray(facet_id_rank, dtype=np.int64)
    candidate_mask = np.asarray(candidate_mask, dtype=bool)
    gold = np.asarray(gold_target_index, dtype=np.int64)

    n_queries, n_facets = cosines.shape
    if facet_target_index.shape != (n_facets,) or facet_id_rank.shape != (n_facets,):
        raise AlignmentError("gold_recall_curve: facet arrays do not match the cosine matrix")
    if candidate_mask.shape != (n_facets,):
        raise AlignmentError("gold_recall_curve: candidate mask does not match the cosine matrix")
    if gold.shape != (n_queries,):
        raise AlignmentError("gold_recall_curve: gold vector does not match the cosine matrix")
    if not n_queries:
        raise AlignmentError("gold_recall_curve: the eval population is empty")
    grid = tuple(int(k) for k in k_grid)
    if any(k <= 0 for k in grid):
        raise AlignmentError("gold_recall_curve: every k must be positive")

    candidate_count = int(candidate_mask.sum())
    if candidate_count == 0:
        raise AlignmentError("gold_recall_curve: the restricted datastore is empty")

    ranks: list[int | None] = []
    gold_absent = 0
    gold_non_positive = 0
    for i in range(n_queries):
        target = int(gold[i])
        if target < 0:
            gold_absent += 1
            ranks.append(None)
            continue
        gold_mask = candidate_mask & (facet_target_index == target)
        if not gold_mask.any():
            gold_absent += 1
            ranks.append(None)
            continue
        row = cosines[i]
        gold_scores = row[gold_mask]
        best = float(gold_scores.max())
        if best <= 0.0:
            gold_non_positive += 1
            ranks.append(None)
            continue
        best_rank_id = int(facet_id_rank[gold_mask][gold_scores == best].min())
        better = candidate_mask & (
            (row > best) | ((row == best) & (facet_id_rank < best_rank_id))
        )
        ranks.append(int(better.sum()) + 1)

    reachable = [rank for rank in ranks if rank is not None]
    curve = {
        f"recall_at_{k}": {
            "hits": sum(1 for rank in reachable if rank <= k),
            "n_queries": n_queries,
            "recall": round(sum(1 for rank in reachable if rank <= k) / n_queries, 6),
        }
        for k in grid
    }
    reachable_sorted = sorted(reachable)
    return {
        "n_queries": n_queries,
        "denominator": "the EVAL population's queries -- never the datastore's contents",
        "candidate_facets": candidate_count,
        "curve": curve,
        "recall_at_full_datastore": {
            "hits": len(reachable),
            "n_queries": n_queries,
            "recall": round(len(reachable) / n_queries, 6),
        },
        "queries_whose_gold_target_has_no_exemplar": gold_absent,
        "queries_whose_gold_exemplars_are_all_non_positive": gold_non_positive,
        "best_gold_rank": {
            "min": reachable_sorted[0] if reachable_sorted else None,
            "p25": _quantile(reachable_sorted, 0.25) if reachable_sorted else None,
            "p50": _quantile(reachable_sorted, 0.50) if reachable_sorted else None,
            "p75": _quantile(reachable_sorted, 0.75) if reachable_sorted else None,
            "p95": _quantile(reachable_sorted, 0.95) if reachable_sorted else None,
            "max": reachable_sorted[-1] if reachable_sorted else None,
        },
    }


# ---------------------------------------------------------------------------
# METRIC 4 -- decontamination as a measured intersection count
# ---------------------------------------------------------------------------


def decontamination_intersection(
    *,
    datastore_sample_ids: Iterable[str],
    datastore_texts: Iterable[str],
    eval_items: Mapping[str, str],
    ngram: int = DECONTAMINATION_NGRAM,
    identity_cap: int = IDENTITY_CAP,
) -> dict[str, object]:
    """How many EVAL items are actually inside the datastore, three ways.

    ``eval_items`` maps eval sample id -> that item's text. The denominator is
    the eval population, so a wider datastore cannot flatter the number. Every
    result is a COUNT with identities; there is no verdict string, because a
    verdict string is what this replaces.

    The three granularities are independent and are reported separately:

    * ``by_sample_id`` -- the exact check the landed builders make, reported as
      a count and a list rather than as ``"clean"``.
    * ``by_normalised_text`` -- case-folded, punctuation-stripped equality. An
      eval item whose text is verbatim in the datastore under a different id is
      a leak the id check cannot see.
    * ``by_ngram`` -- shared word ``ngram``-gram. An item shorter than ``ngram``
      tokens contributes its whole token sequence as one gram.
    """

    if ngram <= 0:
        raise AlignmentError("decontamination_intersection: ngram must be positive")
    store_ids = {str(sample_id) for sample_id in datastore_sample_ids}
    store_norm = {normalise_text(text) for text in datastore_texts}
    store_norm.discard("")

    store_grams: set[tuple[str, ...]] = set()
    for norm in store_norm:
        tokens = norm.split()
        if not tokens:
            continue
        if len(tokens) < ngram:
            store_grams.add(tuple(tokens))
        else:
            for start in range(len(tokens) - ngram + 1):
                store_grams.add(tuple(tokens[start : start + ngram]))

    id_hits: list[str] = []
    text_hits: list[str] = []
    gram_hits: list[str] = []
    short_items = 0
    for sample_id, text in sorted(eval_items.items()):
        sample_id = str(sample_id)
        if sample_id in store_ids:
            id_hits.append(sample_id)
        norm = normalise_text(text)
        if norm and norm in store_norm:
            text_hits.append(sample_id)
        tokens = norm.split()
        if not tokens:
            continue
        if len(tokens) < ngram:
            short_items += 1
            grams = {tuple(tokens)}
        else:
            grams = {
                tuple(tokens[start : start + ngram])
                for start in range(len(tokens) - ngram + 1)
            }
        if grams & store_grams:
            gram_hits.append(sample_id)

    def _block(hits: Sequence[str], label: str) -> dict[str, object]:
        return {
            "eval_items_found_in_the_datastore": len(hits),
            "eval_population": len(eval_items),
            "rate": round(len(hits) / len(eval_items), 6) if eval_items else 0.0,
            "identities": list(hits[:identity_cap]),
            "identities_truncated": max(0, len(hits) - identity_cap),
            "granularity": label,
        }

    return {
        "eval_population": len(eval_items),
        "datastore_sample_ids": len(store_ids),
        "datastore_distinct_normalised_texts": len(store_norm),
        "datastore_distinct_ngrams": len(store_grams),
        "ngram": ngram,
        "eval_items_shorter_than_ngram": short_items,
        "by_sample_id": _block(id_hits, "exact sample id"),
        "by_normalised_text": _block(
            text_hits, "case-folded, punctuation-stripped text equality"
        ),
        "by_ngram": _block(gram_hits, f"shared word {ngram}-gram"),
    }


# ---------------------------------------------------------------------------
# The restriction proof that buys the scaling curve at zero contacts
# ---------------------------------------------------------------------------


def prove_restriction_is_exact(
    *,
    reduced_snapshot,
    full_content: Mapping[str, str],
    require_equality: bool = False,
) -> dict[str, object]:
    """A reduced tier's content facets are a subset of the full tier's, with
    identical ids AND identical representations.

    This is what makes restricting the landed full NPZ equivalent to rebuilding
    and re-embedding at the smaller size. It RAISES rather than reports a
    failure, because a false restriction would silently corrupt every number in
    the scaling curve. ``require_equality`` is set at the full tier, where the
    rebuilt content plane must not merely be contained in the pinned snapshot's
    but must BE it -- otherwise the pinned NPZ is not the vector table for the
    corpus this sweep is restricting.
    """

    reduced_content = {
        facet.facet_id: facet.representation
        for facet in reduced_snapshot.facets
        if facet.dimension == "content"
    }
    if not reduced_content:
        raise AlignmentError("prove_restriction_is_exact: the reduced tier has no content facets")
    missing = sorted(set(reduced_content) - set(full_content))
    if missing:
        raise AlignmentError(
            f"restriction is NOT exact: {len(missing)} reduced content facet ids are absent "
            f"from the pinned full snapshot, e.g. {missing[:5]}"
        )
    drifted = sorted(
        facet_id
        for facet_id, representation in reduced_content.items()
        if full_content[facet_id] != representation
    )
    if drifted:
        raise AlignmentError(
            f"restriction is NOT exact: {len(drifted)} reduced content facet representations "
            f"differ from the pinned full snapshot, e.g. {drifted[:5]}"
        )
    unreached = sorted(set(full_content) - set(reduced_content))
    if require_equality and unreached:
        raise AlignmentError(
            f"the full tier rebuild covers only {len(reduced_content)} of "
            f"{len(full_content)} pinned content facets, e.g. missing {unreached[:5]}"
        )
    return {
        "reduced_content_facets": len(reduced_content),
        "full_content_facets": len(full_content),
        "ids_are_a_subset": True,
        "representations_are_identical": True,
        "pinned_content_facets_not_in_this_tier": len(unreached),
        "equality_required_and_held": bool(require_equality and not unreached),
    }


def _full_tier_identity(
    *, reduced, pinned_content_hash: str, content_facets_match: bool
) -> dict[str, object]:
    """What the full-tier rebuild does and does not reproduce, stated as a fact
    rather than asserted.

    The CONTENT plane is reproduced exactly -- identical facet ids, identical
    representations -- which is all the restriction argument needs, because the
    content dimension is the only vector-recalled one. The whole-snapshot
    content hash is a different question: the 2026-08-25 prior-score semantics
    repair (``docs/readiness/2026-08-25-prior-score-semantics-repair.md``)
    changed both builders' ``prior_score`` expression AFTER these snapshots were
    pinned, so a rebuild today legitimately differs from the pinned bytes on the
    prior plane. That divergence is REPORTED here, never papered over, and it
    does not touch a single number in this sweep.
    """

    measured = reduced.content_hash()
    return {
        "pinned_snapshot_content_hash": pinned_content_hash,
        "rebuilt_snapshot_content_hash": measured,
        "whole_snapshot_hash_reproduces": measured == pinned_content_hash,
        "content_plane_reproduces_exactly": bool(content_facets_match),
        "note": (
            "the content plane -- the only vector-recalled dimension, and the only one "
            "this sweep restricts -- is reproduced facet-for-facet with identical "
            "representations. A whole-snapshot hash difference, if any, is the "
            "2026-08-25 prior-score semantics repair landing in both builders after "
            "these snapshots were pinned; it changes the prior plane, not the content "
            "plane, and no number in this sweep reads the prior plane."
        ),
    }


# ---------------------------------------------------------------------------
# METRIC 1 -- the scaling curve
# ---------------------------------------------------------------------------


def scaling_curve(cells: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """The swept datastore-size axis, read as a curve.

    A curve whose reported quantity does not move across the swept axis is a
    curve that cannot fail, so the informativeness of the sweep is measured
    here and carried in the result rather than assumed.
    """

    if len(cells) < 2:
        raise AlignmentError("scaling_curve: a curve needs at least two swept sizes")
    rows = []
    for cell in cells:
        recall = cell["gold_recall"]  # type: ignore[index]
        primary = recall[str(cell["primary_population"])]  # type: ignore[index]
        rows.append(
            {
                "requested_datastore_size": cell["requested_datastore_size"],
                "datastore_size_actual": cell["datastore_size_actual"],
                "candidate_facets": primary["candidate_facets"],
                "recall_at_1": primary["curve"]["recall_at_1"]["recall"],
                "recall_at_5": primary["curve"]["recall_at_5"]["recall"],
                "recall_at_64": primary["curve"]["recall_at_64"]["recall"],
                "recall_at_full_datastore": primary["recall_at_full_datastore"]["recall"],
                "targets_with_zero_support": cell["support"]["targets_with_zero_support"],  # type: ignore[index]
                "median_support": cell["support"]["p50"],  # type: ignore[index]
            }
        )
    distinct_r5 = sorted({row["recall_at_5"] for row in rows})
    distinct_sizes = sorted({row["datastore_size_actual"] for row in rows})
    return {
        "axis": "datastore_size",
        "rows": rows,
        "distinct_datastore_sizes": len(distinct_sizes),
        "distinct_recall_at_5_values": len(distinct_r5),
        "curve_is_informative": len(distinct_r5) > 1 and len(distinct_sizes) > 1,
        "recall_at_5_span": (
            round(max(distinct_r5) - min(distinct_r5), 6) if distinct_r5 else 0.0
        ),
        "monotone_non_decreasing_in_size": all(
            rows[i]["recall_at_5"] <= rows[i + 1]["recall_at_5"] + 1e-12
            for i in range(len(rows) - 1)
        ),
    }


# ---------------------------------------------------------------------------
# Carrier assembly
# ---------------------------------------------------------------------------


def _target_codes(targets: Iterable[str]) -> dict[str, int]:
    return {target: code for code, target in enumerate(sorted({str(t) for t in targets}))}


def _facet_arrays(bundle, target_codes: Mapping[str, int]):
    """Per-NPZ-row target code and the lexicographic facet-id rank."""

    import numpy as np

    codes = np.full(len(bundle.facet_ids), -1, dtype=np.int64)
    unmapped: list[str] = []
    for position, facet_id in enumerate(bundle.facet_ids):
        target = bundle.content_facet_target.get(facet_id)
        if target is None:
            unmapped.append(facet_id)
            continue
        code = target_codes.get(str(target))
        if code is None:
            unmapped.append(facet_id)
            continue
        codes[position] = code
    if unmapped:
        raise AlignmentError(
            f"{len(unmapped)} landed content facets carry no task target code, "
            f"e.g. {unmapped[:5]}"
        )
    return codes, np.asarray(bundle.facet_id_rank, dtype=np.int64)


def _cosine_matrix(bundle, query_vectors: Mapping[str, Sequence[float]], order: Sequence[str]):
    import numpy as np

    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)
    queries = np.asarray([query_vectors[sample_id] for sample_id in order], dtype=np.float64)
    query_norms = np.linalg.norm(queries, axis=1)
    denominator = np.outer(query_norms, facet_norms)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(denominator > 0.0, (queries @ matrix.T) / denominator, 0.0)


def _recall_fidelity_probe(
    *, bundle, query_vectors: Mapping[str, Sequence[float]], order: Sequence[str], cosines
) -> dict[str, object]:
    """Verify -- never assume -- that this module's vectorised cosine row is the
    one ``kb.multidim_recall`` itself ranks with."""

    facet_vectors = cf._facet_vector_lookup(bundle)  # noqa: SLF001 -- the landed lookup
    probes = 0
    for position, sample_id in enumerate(order[:RECALL_FIDELITY_PROBES]):
        reference = kb.multidim_recall(
            bundle.snapshot,
            {"content": query_vectors[sample_id]},
            facet_vectors,
            FROZEN_TOP_K,
        )
        replayed = cf.vectorised_recall(bundle, cosines[position], top_k=FROZEN_TOP_K)
        if set(reference) != set(replayed):
            raise AlignmentError(
                f"{sample_id}: this module's cosine row admits a different facet set than "
                "kb.multidim_recall"
            )
        for facet_id, dim_scores in reference.items():
            for dimension, score in dim_scores.items():
                if abs(score - replayed[facet_id][dimension]) > 1e-9:
                    raise AlignmentError(
                        f"{sample_id}/{facet_id}/{dimension}: this module's cosine row "
                        "disagrees with kb.multidim_recall"
                    )
        probes += 1
    if probes == 0:
        raise AlignmentError("the recall fidelity probe ran zero samples")
    return {
        "probes": probes,
        "claim": (
            "kb.multidim_recall admits the same facet set with the same scores as this "
            "module's vectorised cosine row, so the recall@k ranking is the registered "
            "ranker's own ordering"
        ),
    }


# ---------------------------------------------------------------------------
# The mutation battery -- every metric must be shown able to FAIL
# ---------------------------------------------------------------------------


def mutation_battery(
    *,
    cells: Sequence[Mapping[str, object]],
    curve: Mapping[str, object],
    support_inputs: Mapping[str, object],
    recall_inputs: Mapping[str, object],
    decontamination_inputs: Mapping[str, object],
    carrier: str,
) -> list[dict[str, object]]:
    """For each of the four metrics: a mutation that SHOULD break it, run, and
    the observed outcome. A mutation that does not move its metric RAISES."""

    import numpy as np

    results: list[dict[str, object]] = []

    def _record(
        metric: str, mutation: str, expected: str, observed: str, moved: bool
    ) -> None:
        results.append(
            {
                "carrier": carrier,
                "metric": metric,
                "mutation": mutation,
                "expected": expected,
                "observed": observed,
                "metric_moved": bool(moved),
            }
        )
        if not moved:
            raise AlignmentError(
                f"{carrier}/{metric}: the mutation {mutation!r} did NOT move the metric. "
                "A metric that cannot fail is exactly what this row exists to replace, so "
                "it is REFUSED rather than landed."
            )

    # --- METRIC 1: the scaling curve -------------------------------------
    if not curve["curve_is_informative"]:
        raise AlignmentError(
            f"{carrier}: the unmutated scaling curve is CONSTANT across the swept axis. "
            "A flat curve cannot fail and is refused."
        )
    flat_cells = [
        {**cell, "gold_recall": cells[-1]["gold_recall"], "support": cells[-1]["support"]}
        for cell in cells
    ]
    flat = scaling_curve(flat_cells)
    _record(
        "scaling_curve",
        "ignore the datastore-size restriction and score every swept size against the FULL "
        "candidate set",
        "the curve collapses to a single recall@5 value and curve_is_informative goes False",
        f"unmutated distinct recall@5 values={curve['distinct_recall_at_5_values']} "
        f"(span {curve['recall_at_5_span']}); mutated="
        f"{flat['distinct_recall_at_5_values']} (informative={flat['curve_is_informative']})",
        int(flat["distinct_recall_at_5_values"]) == 1
        and not bool(flat["curve_is_informative"]),
    )

    # --- METRIC 2: the support distribution -------------------------------
    base_support = support_distribution(
        support_by_target=support_inputs["support_by_target"],  # type: ignore[index]
        task_target_space=support_inputs["task_target_space"],  # type: ignore[index]
    )
    phantom_space = list(support_inputs["task_target_space"]) + [  # type: ignore[index]
        "__mutation_phantom_target__"
    ]
    phantom = support_distribution(
        support_by_target=support_inputs["support_by_target"],  # type: ignore[index]
        task_target_space=phantom_space,
    )
    _record(
        "support_distribution",
        "add one target to the TASK target space that the datastore has no exemplar for",
        "targets_with_zero_support rises by exactly 1 and the new target is named",
        f"{base_support['targets_with_zero_support']} -> "
        f"{phantom['targets_with_zero_support']}; named="
        f"{'__mutation_phantom_target__' in phantom['zero_support_targets']}",
        int(phantom["targets_with_zero_support"])
        == int(base_support["targets_with_zero_support"]) + 1
        and "__mutation_phantom_target__" in phantom["zero_support_targets"],
    )

    busiest = max(
        support_inputs["support_by_target"].items(),  # type: ignore[union-attr]
        key=lambda item: (item[1], item[0]),
    )[0]
    stripped = {
        target: count
        for target, count in support_inputs["support_by_target"].items()  # type: ignore[union-attr]
        if target != busiest
    }
    stripped_report = support_distribution(
        support_by_target=stripped,
        task_target_space=support_inputs["task_target_space"],  # type: ignore[index]
    )
    _record(
        "support_distribution",
        f"delete every exemplar of the best-supported target ({busiest!r})",
        "that target drops to support 0, the zero count rises and the total falls",
        f"zero {base_support['targets_with_zero_support']} -> "
        f"{stripped_report['targets_with_zero_support']}; total "
        f"{base_support['total_exemplars']} -> {stripped_report['total_exemplars']}",
        int(stripped_report["targets_with_zero_support"])
        == int(base_support["targets_with_zero_support"]) + 1
        and busiest in stripped_report["zero_support_targets"]
        and int(stripped_report["total_exemplars"]) < int(base_support["total_exemplars"]),
    )

    # --- METRIC 3: gold recall@k -----------------------------------------
    base_recall = recall_inputs["baseline"]  # type: ignore[index]
    gold = np.asarray(recall_inputs["gold_target_index"], dtype=np.int64)  # type: ignore[index]
    rng = random.Random(20260825)
    permuted = list(range(len(gold)))
    rng.shuffle(permuted)
    shuffled = gold[np.asarray(permuted, dtype=np.int64)]
    shuffled_recall = gold_recall_curve(
        cosines=recall_inputs["cosines"],  # type: ignore[index]
        facet_target_index=recall_inputs["facet_target_index"],  # type: ignore[index]
        facet_id_rank=recall_inputs["facet_id_rank"],  # type: ignore[index]
        candidate_mask=recall_inputs["candidate_mask"],  # type: ignore[index]
        gold_target_index=shuffled,
    )
    base_r5 = float(base_recall["curve"]["recall_at_5"]["recall"])
    shuffled_r5 = float(shuffled_recall["curve"]["recall_at_5"]["recall"])
    _record(
        "gold_recall_curve",
        "deterministically permute the gold target assignment across the eval population "
        "(seed 20260825), leaving every query vector and the whole datastore untouched",
        "recall@5 collapses toward the label base rate",
        f"recall@5 {base_r5} -> {shuffled_r5}",
        shuffled_r5 < base_r5 - 1e-9,
    )

    absent_recall = gold_recall_curve(
        cosines=recall_inputs["cosines"],  # type: ignore[index]
        facet_target_index=recall_inputs["facet_target_index"],  # type: ignore[index]
        facet_id_rank=recall_inputs["facet_id_rank"],  # type: ignore[index]
        candidate_mask=recall_inputs["candidate_mask"],  # type: ignore[index]
        gold_target_index=np.full(len(gold), -1, dtype=np.int64),
    )
    _record(
        "gold_recall_curve",
        "declare every eval query's gold target absent from the datastore's target space",
        "recall goes to 0.0 at every k and every query is counted as a miss, never dropped "
        "from the denominator",
        f"recall@512 {base_recall['curve']['recall_at_512']['recall']} -> "
        f"{absent_recall['curve']['recall_at_512']['recall']}; denominator "
        f"{absent_recall['curve']['recall_at_512']['n_queries']} unchanged; "
        f"gold-absent {absent_recall['queries_whose_gold_target_has_no_exemplar']}",
        float(absent_recall["curve"]["recall_at_512"]["recall"]) == 0.0
        and int(absent_recall["curve"]["recall_at_512"]["n_queries"])
        == int(base_recall["curve"]["recall_at_512"]["n_queries"])
        and int(absent_recall["queries_whose_gold_target_has_no_exemplar"]) == len(gold),
    )

    # --- METRIC 4: the decontamination intersection ------------------------
    eval_items: Mapping[str, str] = decontamination_inputs["eval_items"]  # type: ignore[index]
    store_ids = list(decontamination_inputs["datastore_sample_ids"])  # type: ignore[index]
    store_texts = list(decontamination_inputs["datastore_texts"])  # type: ignore[index]
    base_decon = decontamination_inputs["baseline"]  # type: ignore[index]
    victim_id = sorted(eval_items)[0]
    injected_ids = decontamination_intersection(
        datastore_sample_ids=store_ids + [victim_id],
        datastore_texts=store_texts,
        eval_items=eval_items,
    )
    _record(
        "decontamination_intersection",
        f"inject one EVAL sample id ({victim_id!r}) into the datastore's id set",
        "by_sample_id rises by exactly 1 and the injected id is named",
        f"{base_decon['by_sample_id']['eval_items_found_in_the_datastore']} -> "
        f"{injected_ids['by_sample_id']['eval_items_found_in_the_datastore']}; named="
        f"{victim_id in injected_ids['by_sample_id']['identities']}",
        int(injected_ids["by_sample_id"]["eval_items_found_in_the_datastore"])
        == int(base_decon["by_sample_id"]["eval_items_found_in_the_datastore"]) + 1
        and victim_id in injected_ids["by_sample_id"]["identities"],
    )

    # Pick a victim whose normalised text is genuinely absent from the datastore
    # -- computed here rather than read off the baseline's IDENTITY LIST, which
    # is capped and would silently hand back a false negative on a wide hit set.
    store_norm = {normalise_text(text) for text in store_texts}
    store_norm.discard("")
    unseen = sorted(
        sample_id
        for sample_id in eval_items
        if normalise_text(eval_items[sample_id])
        and normalise_text(eval_items[sample_id]) not in store_norm
    )
    if not unseen:
        raise AlignmentError(
            "every eval item is already text-present in the datastore; the text mutation "
            "cannot be constructed"
        )
    victim_text_id = unseen[0]
    injected_text = decontamination_intersection(
        datastore_sample_ids=store_ids,
        datastore_texts=store_texts + [eval_items[victim_text_id]],
        eval_items=eval_items,
    )
    _record(
        "decontamination_intersection",
        f"inject one EVAL item's verbatim text ({victim_text_id!r}) into the datastore's "
        "text set, under NO shared id",
        "by_normalised_text rises by at least 1 and the id check stays where it was -- the "
        "id gate is exactly the leak this granularity exists to catch",
        f"text {base_decon['by_normalised_text']['eval_items_found_in_the_datastore']} -> "
        f"{injected_text['by_normalised_text']['eval_items_found_in_the_datastore']}; id "
        f"{base_decon['by_sample_id']['eval_items_found_in_the_datastore']} -> "
        f"{injected_text['by_sample_id']['eval_items_found_in_the_datastore']}",
        int(injected_text["by_normalised_text"]["eval_items_found_in_the_datastore"])
        > int(base_decon["by_normalised_text"]["eval_items_found_in_the_datastore"])
        and int(injected_text["by_sample_id"]["eval_items_found_in_the_datastore"])
        == int(base_decon["by_sample_id"]["eval_items_found_in_the_datastore"]),
    )

    return results


# ---------------------------------------------------------------------------
# SLURP carrier
# ---------------------------------------------------------------------------


def _slurp_query_vectors(*, data_root: Path, mechanical: Mapping[str, Mapping[str, object]]):
    """The sealed DEV-1000 BLEND arm's landed query vectors, cross-checked
    against the sealed per-sample records by text digest.

    A query vector whose ``text_sha256`` is not the sealed
    ``direct_response_sha256`` for its own sample would mean the vector table
    and the flight disagree about what was embedded, so it is refused."""

    pin = next(item for item in lr.ARM_PINS if item.arm_id == "BLEND")
    run_dir = Path(data_root) / "runs" / lr.RUN_ID / pin.attempt_id
    path = run_dir / "query-vectors.jsonl"
    vectors: dict[str, tuple[float, ...]] = {}
    digests: dict[str, str] = {}
    for record in _read_jsonl(path):
        contact_id = str(record["contact_id"])
        if not contact_id.startswith("query:"):
            continue
        sample_id = contact_id.split("query:", 1)[1]
        vectors[sample_id] = tuple(float(value) for value in record["values"])
        digests[sample_id] = str(record["text_sha256"])
    mismatched = sorted(
        sample_id
        for sample_id, digest in digests.items()
        if sample_id in mechanical
        and str(mechanical[sample_id]["direct_response_sha256"]) != digest
    )
    if mismatched:
        raise AlignmentError(
            f"{len(mismatched)} DEV-1000 query vectors do not carry the sealed contact-0 "
            f"response digest for their own sample, e.g. {mismatched[:5]}"
        )
    return vectors, _sha256_file(path), len(digests)


def _slurp_devel_sentences(*, lock, data_root: Path) -> dict[str, str]:
    """utterance_id -> reference sentence, read from the governed
    ``devel.jsonl``. Offline, scoring-side, for the decontamination
    measurement only; ``test.jsonl`` is never opened."""

    from ..data.slurp import _governed_roots  # noqa: SLF001 -- the registered resolver

    _audio_relpath, _audio_root, metadata_dir = _governed_roots(lock, Path(data_root))
    sentences: dict[str, str] = {}
    for raw in _read_jsonl(metadata_dir / "devel.jsonl"):
        slurp_id = raw.get("slurp_id")
        sentence = raw.get("sentence")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            continue
        if not isinstance(sentence, str):
            continue
        sentences[str(slurp_id)] = sentence
    if not sentences:
        raise AlignmentError("the governed devel.jsonl yielded no sentences")
    return sentences


def measure_slurp(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """The four metrics on the SLURP carrier, swept over datastore size."""

    import numpy as np

    from ..data.lock import load_lock, umbrella_lock_path
    from ..rails.knowledge_build import (
        KnowledgeBuildSpec,
        _default_forbidden_sample_ids,  # noqa: SLF001 -- the landed roster, not a new one
        _selected_rows_from_snapshot,  # noqa: SLF001 -- the landed selection reader
        build_knowledge_snapshot,
        coverage_report,
        slurp_kb_rows,
    )

    repo_root, data_root = Path(repo_root), Path(data_root)
    lock = load_lock(umbrella_lock_path(repo_root))

    bundle = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    rows = slurp_kb_rows(lock, data_root)
    forbidden = _default_forbidden_sample_ids(repo_root)

    full_content = {
        facet.facet_id: facet.representation
        for facet in bundle.snapshot.facets
        if facet.dimension == "content"
    }

    populations = lr.load_populations(repo_root)
    arms = {
        pin.arm_id: lr.load_arm(pin=pin, repo_root=repo_root, data_root=data_root)
        for pin in lr.ARM_PINS
    }
    blend_records = lr.load_per_sample_mechanical(arm=arms["BLEND"])
    query_vectors, query_sha256, query_count = _slurp_query_vectors(
        data_root=data_root, mechanical=blend_records
    )
    order = tuple(populations.dev1000)
    missing = [sample_id for sample_id in order if sample_id not in query_vectors]
    if missing:
        raise AlignmentError(f"{len(missing)} DEV-1000 samples have no landed query vector")

    gold_by_sample = dc._load_gold(  # noqa: SLF001 -- the registered gold path
        data_root=data_root, repo_root=repo_root, sample_ids=set(order)
    )
    gold_intent = {
        sample_id: f"{gold_by_sample[sample_id].scenario}_{gold_by_sample[sample_id].action}"
        for sample_id in order
    }

    train_targets = {row.intent for row in rows}
    eval_targets = set(gold_intent.values())
    task_target_space = sorted(train_targets | eval_targets)
    target_codes = _target_codes(task_target_space)
    facet_targets, facet_id_rank = _facet_arrays(bundle, target_codes)
    gold_codes = np.asarray(
        [target_codes.get(gold_intent[sample_id], -1) for sample_id in order], dtype=np.int64
    )

    cosines = _cosine_matrix(bundle, query_vectors, order)
    fidelity = _recall_fidelity_probe(
        bundle=bundle, query_vectors=query_vectors, order=order, cosines=cosines
    )

    index_of = {sample_id: position for position, sample_id in enumerate(order)}
    populations_by_name = {
        "DEV-1000 (pooled, descriptive)": tuple(populations.dev1000),
        "DEV-500 (prior-exposed)": tuple(populations.dev500),
        "DEV-1000 NEW500 (unexposed; SECONDARY READING)": tuple(populations.new500),
    }
    primary_population = "DEV-500 (prior-exposed)"

    devel_sentences = _slurp_devel_sentences(lock=lock, data_root=data_root)
    eval_items = {
        sample_id: devel_sentences[gold_by_sample[sample_id].utterance_id]
        for sample_id in order
        if gold_by_sample[sample_id].utterance_id in devel_sentences
    }
    if len(eval_items) != len(order):
        raise AlignmentError(
            f"{len(order) - len(eval_items)} DEV-1000 samples have no governed devel sentence"
        )

    facet_index = bundle.facet_index
    cells: list[dict[str, object]] = []
    selections: dict[object, tuple] = {}
    for size in SIZE_GRID:
        spec = KnowledgeBuildSpec(
            carrier_lock_key="slurp", datastore_size=size, seed=20260823
        )
        reduced = build_knowledge_snapshot(
            spec, lock=lock, root=data_root, rows=rows, forbidden_sample_ids=forbidden
        )
        # The builder's OWN selection, read back off the snapshot it emitted --
        # never a second, independently seeded call to ``distribution_sample``.
        selected = _selected_rows_from_snapshot(reduced, rows)
        selections[size] = selected
        proof = prove_restriction_is_exact(
            reduced_snapshot=reduced,
            full_content=full_content,
            require_equality=size is None,
        )
        reduced_content_ids = [
            facet.facet_id for facet in reduced.facets if facet.dimension == "content"
        ]
        mask = np.zeros(len(bundle.facet_ids), dtype=bool)
        for facet_id in reduced_content_ids:
            mask[facet_index[facet_id]] = True
        if int(mask.sum()) != len(reduced_content_ids):
            raise AlignmentError("a reduced content facet is absent from the landed NPZ")

        support = support_distribution(
            support_by_target=Counter(row.intent for row in selected),
            task_target_space=task_target_space,
        )
        recall = {
            name: gold_recall_curve(
                cosines=cosines[[index_of[sample_id] for sample_id in ids]],
                facet_target_index=facet_targets,
                facet_id_rank=facet_id_rank,
                candidate_mask=mask,
                gold_target_index=gold_codes[[index_of[sample_id] for sample_id in ids]],
            )
            for name, ids in populations_by_name.items()
        }
        selected_sample_ids = {sid for row in selected for sid in row.sample_ids}
        decon = decontamination_intersection(
            datastore_sample_ids=selected_sample_ids,
            datastore_texts=[row.content for row in selected],
            eval_items=eval_items,
        )
        cell = {
            "requested_datastore_size": size,
            "datastore_size_actual": len(selected),
            "snapshot_content_hash": reduced.content_hash(),
            "restriction_proof": proof,
            "support": support,
            "gold_recall": recall,
            "primary_population": primary_population,
            "decontamination": decon,
        }
        if size is None:
            cell["full_tier_identity"] = _full_tier_identity(
                reduced=reduced,
                pinned_content_hash=dc.SNAPSHOT_SHA256,
                content_facets_match=int(mask.sum()) == len(full_content),
            )
            cell["superseded_coverage_report"] = coverage_report(reduced, rows)
        cells.append(cell)

    curve = scaling_curve(cells)
    full_cell = cells[-1]
    full_selected = selections[None]
    mutations = mutation_battery(
        cells=cells,
        curve=curve,
        support_inputs={
            "support_by_target": Counter(row.intent for row in full_selected),
            "task_target_space": task_target_space,
        },
        recall_inputs={
            "baseline": full_cell["gold_recall"][primary_population],  # type: ignore[index]
            "cosines": cosines[
                [index_of[sample_id] for sample_id in populations_by_name[primary_population]]
            ],
            "facet_target_index": facet_targets,
            "facet_id_rank": facet_id_rank,
            "candidate_mask": np.ones(len(bundle.facet_ids), dtype=bool),
            "gold_target_index": gold_codes[
                [index_of[sample_id] for sample_id in populations_by_name[primary_population]]
            ],
        },
        decontamination_inputs={
            "baseline": full_cell["decontamination"],
            "datastore_sample_ids": sorted(
                {sid for row in full_selected for sid in row.sample_ids}
            ),
            "datastore_texts": [row.content for row in full_selected],
            "eval_items": eval_items,
        },
        carrier="slurp",
    )

    return {
        "carrier": "slurp",
        "secondary_reading_caveat": SECONDARY_READING_CAVEAT,
        "inputs": {
            "snapshot_relpath": dc.SNAPSHOT_RELPATH,
            "snapshot_pinned_sha256": dc.SNAPSHOT_SHA256,
            "snapshot_measured_content_hash": bundle.snapshot_sha256,
            "content_facet_npz_sha256": bundle.npz_sha256,
            "train_rows": len(rows),
            "decontamination_roster_ids": len(forbidden),
            "query_vectors_relpath": (
                f"runs/{lr.RUN_ID}/"
                f"{next(pin.attempt_id for pin in lr.ARM_PINS if pin.arm_id == 'BLEND')}/"
                "query-vectors.jsonl"
            ),
            "query_vectors_sha256": query_sha256,
            "query_vectors_count": query_count,
            "arm_pins": {
                pin.arm_id: {
                    "attempt_id": pin.attempt_id,
                    "outputs_sha256": pin.outputs_sha256,
                    "mechanical_sha256": pin.mechanical_sha256,
                }
                for pin in lr.ARM_PINS
            },
            "population_receipt_hashes": dict(populations.receipt_hashes),
        },
        "task_target_space": {
            "size": len(task_target_space),
            "definition": (
                "union of the TRAIN row intents and the EVAL population's gold intents -- "
                "the TASK's target vocabulary, never the datastore's contents"
            ),
            "train_targets": len(train_targets),
            "eval_gold_targets": len(eval_targets),
            "eval_gold_targets_absent_from_train": sorted(eval_targets - train_targets),
        },
        "recall_fidelity_probe": fidelity,
        "populations": {
            name: {"n": len(ids), "secondary_reading": "NEW500" in name}
            for name, ids in populations_by_name.items()
        },
        "primary_population": primary_population,
        "scaling_curve": curve,
        "cells": cells,
        "mutation_proofs": mutations,
    }


# ---------------------------------------------------------------------------
# Audio2Tool carrier
# ---------------------------------------------------------------------------


def measure_a2t(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """The four metrics on the Audio2Tool carrier, swept over datastore size."""

    import numpy as np

    from ..data.lock import load_lock, umbrella_lock_path
    from ..rails.knowledge_build_a2t import (
        A2tKnowledgeBuildSpec,
        _selected_rows_from_snapshot as _selected_rows_a2t,  # noqa: SLF001
        a2t_pool_rows,
        build_a2t_knowledge_snapshot,
        coverage_report_a2t,
        exposed_sample_ids,
        load_tool_registry_by_name,
        propose_partition,
    )

    repo_root, data_root = Path(repo_root), Path(data_root)
    lock = load_lock(umbrella_lock_path(repo_root))

    carrier = ccd.load_a2t_attempt4(data_root=data_root, repo_root=repo_root)
    bundle = carrier.bundle
    order = tuple(carrier.sample_ids)

    pool_rows, inventory = a2t_pool_rows(lock, data_root)
    registry = load_tool_registry_by_name(lock, data_root)
    exposed = exposed_sample_ids(repo_root)
    partition = propose_partition(pool_rows, exposed, seed=20260807)
    eval_ids = frozenset(partition.eval_sample_ids)
    forbidden = frozenset(exposed) | eval_ids
    governed_relpath_by_tier = {
        tier: f"datasets/audio2tool/public/{tier}_data/{tier}.json"
        for tier in {row.tier for row in partition.construction}
    }

    full_content = {
        facet.facet_id: facet.representation
        for facet in bundle.snapshot.facets
        if facet.dimension == "content"
    }

    task_target_space = sorted(registry)
    eval_targets = {carrier.gold_primary[sample_id] for sample_id in order}
    outside = sorted(eval_targets - set(task_target_space))
    if outside:
        raise AlignmentError(
            f"{len(outside)} eval gold tools are outside the frozen registry: {outside[:5]}"
        )
    target_codes = _target_codes(task_target_space)
    facet_targets, facet_id_rank = _facet_arrays(bundle, target_codes)
    gold_codes = np.asarray(
        [target_codes[carrier.gold_primary[sample_id]] for sample_id in order], dtype=np.int64
    )

    query_vectors = carrier.inputs.query_vectors
    cosines = _cosine_matrix(bundle, query_vectors, order)
    fidelity = _recall_fidelity_probe(
        bundle=bundle, query_vectors=query_vectors, order=order, cosines=cosines
    )

    rows_by_sample_id = {sid: row for row in pool_rows for sid in row.sample_ids}
    eval_items = {
        sample_id: rows_by_sample_id[sample_id].text
        for sample_id in sorted(eval_ids)
        if sample_id in rows_by_sample_id
    }
    if len(eval_items) != len(eval_ids):
        raise AlignmentError("an eval-tier sample id has no pool row")

    facet_index = bundle.facet_index
    cells: list[dict[str, object]] = []
    primary_population = "A2T-G1-104 (exposed)"
    selections: dict[object, tuple] = {}
    for size in SIZE_GRID:
        spec = A2tKnowledgeBuildSpec(datastore_size=size, seed=20260825)
        reduced = build_a2t_knowledge_snapshot(
            spec,
            rows=partition.construction,
            registry=registry,
            forbidden_sample_ids=forbidden,
            governed_relpath_by_tier=governed_relpath_by_tier,
        )
        # The builder's OWN selection, read back off the snapshot it emitted.
        selected = _selected_rows_a2t(reduced, partition.construction)
        selections[size] = selected
        proof = prove_restriction_is_exact(
            reduced_snapshot=reduced,
            full_content=full_content,
            require_equality=size is None,
        )
        reduced_content_ids = [
            facet.facet_id for facet in reduced.facets if facet.dimension == "content"
        ]
        mask = np.zeros(len(bundle.facet_ids), dtype=bool)
        for facet_id in reduced_content_ids:
            mask[facet_index[facet_id]] = True
        if int(mask.sum()) != len(reduced_content_ids):
            raise AlignmentError("a reduced content facet is absent from the landed NPZ")

        support = support_distribution(
            support_by_target=Counter(row.tool_name for row in selected),
            task_target_space=task_target_space,
        )
        recall = {
            primary_population: gold_recall_curve(
                cosines=cosines,
                facet_target_index=facet_targets,
                facet_id_rank=facet_id_rank,
                candidate_mask=mask,
                gold_target_index=gold_codes,
            )
        }
        selected_sample_ids = {sid for row in selected for sid in row.sample_ids}
        decon = decontamination_intersection(
            datastore_sample_ids=selected_sample_ids,
            datastore_texts=[row.text for row in selected],
            eval_items=eval_items,
        )
        cell = {
            "requested_datastore_size": size,
            "datastore_size_actual": len(selected),
            "snapshot_content_hash": reduced.content_hash(),
            "restriction_proof": proof,
            "support": support,
            "gold_recall": recall,
            "primary_population": primary_population,
            "decontamination": decon,
        }
        if size is None:
            cell["full_tier_identity"] = _full_tier_identity(
                reduced=reduced,
                pinned_content_hash=sweep.A2T_SNAPSHOT_SHA256,
                content_facets_match=int(mask.sum()) == len(full_content),
            )
            cell["superseded_coverage_report"] = coverage_report_a2t(
                reduced, partition.construction, registry_tool_count=len(registry)
            )
        cells.append(cell)

    curve = scaling_curve(cells)
    full_cell = cells[-1]
    full_selected = selections[None]
    mutations = mutation_battery(
        cells=cells,
        curve=curve,
        support_inputs={
            "support_by_target": Counter(row.tool_name for row in full_selected),
            "task_target_space": task_target_space,
        },
        recall_inputs={
            "baseline": full_cell["gold_recall"][primary_population],  # type: ignore[index]
            "cosines": cosines,
            "facet_target_index": facet_targets,
            "facet_id_rank": facet_id_rank,
            "candidate_mask": np.ones(len(bundle.facet_ids), dtype=bool),
            "gold_target_index": gold_codes,
        },
        decontamination_inputs={
            "baseline": full_cell["decontamination"],
            "datastore_sample_ids": sorted(
                {sid for row in full_selected for sid in row.sample_ids}
            ),
            "datastore_texts": [row.text for row in full_selected],
            "eval_items": eval_items,
        },
        carrier="audio2tool",
    )

    eval_gold_support = Counter(row.tool_name for row in full_selected)
    return {
        "carrier": "audio2tool",
        "inputs": {
            "snapshot_relpath": sweep.A2T_SNAPSHOT_RELPATH,
            "snapshot_pinned_sha256": sweep.A2T_SNAPSHOT_SHA256,
            "snapshot_measured_content_hash": bundle.snapshot_sha256,
            "content_facet_npz_sha256": bundle.npz_sha256,
            "pool_units": inventory["pool_units"],
            "construction_units": len(partition.construction),
            "eval_units": len(eval_ids),
            "exposed_ids": len(exposed),
            "decontamination_roster_ids": len(forbidden),
            "artifact_hashes": dict(carrier.artifact_hashes),
        },
        "task_target_space": {
            "size": len(task_target_space),
            "definition": (
                "the FROZEN TOOL REGISTRY -- every tool the core may call. This is the "
                "denominator the replaced tool_coverage should have had; it is what makes "
                "getLockStatus visible at support 0"
            ),
            "construction_pool_tools": len({row.tool_name for row in partition.construction}),
            "eval_gold_tools": len(eval_targets),
            "registry_tools_with_zero_construction_support": sorted(
                tool for tool in task_target_space if eval_gold_support.get(tool, 0) == 0
            ),
        },
        "recall_fidelity_probe": fidelity,
        "populations": {primary_population: {"n": len(order), "secondary_reading": False}},
        "primary_population": primary_population,
        "scaling_curve": curve,
        "cells": cells,
        "mutation_proofs": mutations,
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(*, repo_root: Path, data_root: Path, out_path: Path) -> dict[str, object]:
    attempts = audit.arm_offline_guard()
    started = time.perf_counter()

    repo_root, data_root = Path(repo_root), Path(data_root)
    policy_path = repo_root / cf.FROZEN_POLICY_CONFIG_RELPATH
    policy_sha256 = _sha256_file(policy_path)
    if policy_sha256 != sweep.FROZEN_POLICY_CONFIG_SHA256:
        raise AlignmentError(
            f"the locked v1 policy cell hashes to {policy_sha256}, not the pinned "
            f"{sweep.FROZEN_POLICY_CONFIG_SHA256}: this row must change no knob"
        )

    slurp = measure_slurp(repo_root=repo_root, data_root=data_root)
    a2t = measure_a2t(repo_root=repo_root, data_root=data_root)

    document = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "frame": (
            "ALIGNMENT AND REPORTING CHANGE. Owner ruling 2026-08-25: find out how the field "
            "does this, decide whether we created the implementation difficulty ourselves, and "
            "if so align to the field's implementation. We did create it. This row replaces a "
            "self-invented coverage-ratio family that cannot fail with the field's standard "
            "datastore metrics, changes WHAT IS REPORTED and never what is retrieved or "
            "decided, changes no knob, rebuilds no snapshot on disk, displaces nothing "
            "hash-pinned, revises no landed number, and authorises no flight."
        ),
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
            "mechanism": (
                "socket.socket.connect / connect_ex / socket.create_connection were replaced "
                "with counting refusals before the first input was opened"
            ),
        },
        "accounting": {
            "frozen_core_contacts": 0,
            "embedding_tool_contacts": 0,
            "tokenizer_contacts": 0,
            "http_requests": 0,
            "speech_audio_seconds": 0,
            "gpu_hours": 0.0,
        },
        "knob_invariance": {
            "frozen_policy_config_relpath": cf.FROZEN_POLICY_CONFIG_RELPATH,
            "frozen_policy_config_sha256": policy_sha256,
            "matches_the_locked_v1_cell": True,
        },
        "field_practice": list(FIELD_PRACTICE),
        "superseded_metrics": list(SUPERSEDED_METRICS),
        "metric_definitions": {
            "scaling_curve": (
                "datastore size swept as an axis; every reported quantity is a function of "
                "the swept size, and a curve that does not move is refused"
            ),
            "support_distribution": (
                "exemplars per TASK target, denominated on the task's target vocabulary, with "
                "min / p05 / p25 / p50 / p75 / p95 / max, the count at support 1 and the count "
                "at support 0 with identities"
            ),
            "gold_recall_curve": (
                "recall@k of a gold-bearing content facet, denominated on the EVAL "
                "population's queries; a query whose gold is absent from the datastore is a "
                "miss at every k and is never removed from the denominator"
            ),
            "decontamination_intersection": (
                "the MEASURED number of eval items found inside the datastore -- by exact "
                "sample id, by normalised text and by shared word n-gram -- with the "
                "identities of anything that intersects"
            ),
        },
        "k_grid": list(K_GRID),
        "size_grid": [size for size in SIZE_GRID],
        "slurp": slurp,
        "audio2tool": a2t,
        "mutation_proofs": list(slurp["mutation_proofs"]) + list(a2t["mutation_proofs"]),  # type: ignore[arg-type]
        "hard_stop": (
            "HARD STOP. This row reports; it does not act. No knob is changed, no snapshot is "
            "rebuilt on disk, no landed receipt or readiness document is rewritten, no flight "
            "or re-flight is authorised, and no number here revises, re-tunes or restates the "
            "2026-08-25 DEV-1000 baseline lock."
        ),
        "timing_seconds": round(time.perf_counter() - started, 3),
    }

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Datastore scoring alignment")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    document = run(
        repo_root=Path(args.repo_root),
        data_root=Path(args.data_root),
        out_path=Path(args.out),
    )
    for carrier in ("slurp", "audio2tool"):
        print(carrier, json.dumps(document[carrier]["scaling_curve"]["rows"], indent=1))  # type: ignore[index]
    print("outbound attempts", document["offline_guard"]["outbound_connection_attempts"])  # type: ignore[index]
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
