"""K1 -- the offline gate on activating a GENUINE SECOND key dimension.

Exposure row ``SAEA-SN-MF-K1-HYBRID-RANKING-GATE`` (registered before any
computation): zero frozen-core contacts, zero embedding-tool contacts, zero
tokenizer contacts, zero HTTP or socket requests, no new dependency, no
package installation. Everything this module reads is already landed and
sealed.

The established defect this gate acts on
----------------------------------------
Every facet in the pinned TRAIN snapshot carries exactly ONE dimension.
``agreement = dims_hit / dims_total`` is therefore a CONSTANT 1/3 for every
candidate (the three recalling dimensions are ``content``, ``label`` and
``prior``; ``speaker`` has no query vector and never recalls), and content
facets carry ``max_prior = 0.0`` because they are not a prior-mass
dimension. The ranker's score collapses to the affine map
``0.5 * cos + 0.2 * (1/3) = 0.5 * cos + 0.0667`` and the ranking IS the
cosine ranking for any positive ``w_cos``. That is why the rank-weight
family measured inert. This module VERIFIES that once and moves on; it does
not re-derive it.

The question K1 asks
--------------------
Does a genuine second dimension -- a deterministic LEXICAL dimension over
the SAME content-facet texts, matched against the SAME query texts the
flights embedded (the direct decode's own response text) -- move the
gold-bearing content facet into the top-5 for a meaningful number of the
currently recall-limited errors?

Two parts, deliberately kept apart
----------------------------------
**Part A -- the RANKING question, and the falsifier.** A pure retrieval
computation: under each registered fusion rule, where does the gold-bearing
content facet sit in the FULL ordering of the 11,514 content facets? No
admission threshold, no target budget -- just the ordering. This is the
quantity the agenda plan's pre-registered falsifier names.

**Part B -- the SUPPLY question, and the decision quantity.** The frozen
cell replayed end to end with the second dimension actually ACTIVATED
inside the registered policy code: ``recall_scores`` carries a
``content_lex`` dimension beside ``content``, and the REAL
``kb_policy`` ranker and fuser run on it, so ``dims_total`` becomes 4,
``agreement`` becomes a real signal, percept admission and the
``(c, top_l)`` budget apply as frozen, and the alpha-blend head re-decides
retain-versus-dispatch. This is the change item K1 actually describes.

What is registered in advance, and may not be re-tried after the answer
----------------------------------------------------------------------
The tokenizer, the BM25 parameters, the lexical similarity's bounding
transform, the fusion grid, the two query normalizations, the populations,
and the recall grid are all module constants fixed before the module was
first executed. A negative result is reported as the finding.

Deliberate reuse
----------------
:mod:`.contrast_fewshot_preanalysis` owns the snapshot bundle, the
population loader, the vectorised recall and the flight-gated replay;
through it :mod:`.dev100_damage_channel_analysis` owns ``replay_supply`` /
``replay_blend`` (which call the registered ``kb_policy`` stages, not a
second implementation) and :mod:`.dev500_confirmatory_read` owns the
population receipts and the hash pins; :mod:`.dev100_reviewer_audit` owns
the offline guard. All are IMPORTED. What is new here and only here is the
lexical channel, the fusion grid, the hybrid gold-position arithmetic, the
native two-dimension recall construction, and the conversion projection.

Scope
-----
Dev-tier, iteration-tier DESIGN INPUT. This gates a flight and is not one.
No knob is changed, no arm is re-flown, no new sample is touched, no new
gold surface is opened, and no test or FINAL60 surface is opened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from . import contrast_fewshot_preanalysis as cf
from . import dev100_damage_channel_analysis as dc
from . import dev100_reviewer_audit as ra
from . import dev1000_lock_read as d1k
from . import dev500_confirmatory_read as d5
from ..rails import kb_policy as kb

SCHEMA = "saea-k1-hybrid-ranking-gate-v1"
EXPOSURE_ROW_ID = "SAEA-SN-MF-K1-HYBRID-RANKING-GATE"
PLAN_RELPATH = "docs/readiness/2026-08-25-key-construction-agenda-plan.md"
VERDICT_RELPATH = "docs/readiness/2026-08-25-baseline-lock-verdict.md"

FALSIFIER = (
    "if hybrid ranking does not raise recall@5, key representation is not the lever either, "
    "and the residual is task-intrinsic"
)


class GateError(RuntimeError):
    """A pinned input does not match, or a gated replay contradicts a sealed
    record. Never raised for a legitimate data shape."""


# ---------------------------------------------------------------------------
# REGISTERED CONSTANTS -- fixed before first execution, never re-tried after
# ---------------------------------------------------------------------------

#: The tokenizer. Lowercase, then every maximal run of ASCII letters and
#: digits is one token. Nothing is stemmed, nothing is stopped, no language
#: resource is consulted, and the same function tokenizes both sides.
TOKEN_RE = re.compile(r"[a-z0-9]+")

#: The five CONSTANT JSON schema key tokens the SLU answer format emits on
#: every single query. They carry no per-sample information, so the second
#: registered query normalization removes them. Removal is a literal token
#: filter, not a JSON parse, so it behaves identically on unparsed answers.
SCHEMA_KEY_TOKENS = frozenset({"scenario", "action", "entities", "type", "filler"})

QUERY_NORMALIZATIONS = ("Q-RAW", "Q-VAL")

#: Okapi BM25, Robertson/Lucene non-negative IDF, standard parameters.
BM25_K1 = 1.2
BM25_B = 0.75

#: Reciprocal-rank fusion constant.
RRF_K = 60

#: Lexical weight for the score-level linear rule.
LINEAR_W_GRID = (0.25, 0.50, 0.75)

FUSION_RULES = ("DENSE-ONLY", "LIN-0.25", "LIN-0.50", "LIN-0.75", "RRF-60", "TIEBREAK")

#: The grid the sealed reads publish, reproduced as the fidelity gate.
FIDELITY_K_GRID = d5.RECALL_AT_K_GRID
#: The grid this gate reports per fusion rule.
REPORT_K_GRID = (1, 3, 5, 8)

#: The frozen cell, imported rather than restated.
FROZEN_ALPHA = cf.FROZEN_ALPHA
FROZEN_TOP_K = cf.FROZEN_TOP_K
FROZEN_WEIGHTS = cf.FROZEN_WEIGHTS
FROZEN_FUSE = cf.FROZEN_FUSE

#: The name the second dimension takes inside ``recall_scores``. It is NOT
#: in :data:`kb_policy.PRIOR_MASS_DIMENSIONS`, so the registered ranker
#: treats it as a cosine-family dimension: it enters ``max_cosine`` and it
#: enters percept admission -- which is exactly the intended semantics of an
#: independently matchable second key dimension.
LEX_DIMENSION = "content_lex"

#: The MEASURED conversion anchors, pooled over the three sealed populations
#: (docs/readiness/2026-08-25-ec-and-retain-override-projections.md section 3,
#: recomputed identically in the supply-budget projection section 6).
ANCHOR_TOP1 = 108 / 110
ANCHOR_RANK23 = 16 / 23
ANCHOR_ABSENT = 0.0
#: NOT measured -- the frozen ``top_l = 3`` means no flown trajectory ever
#: supplied a fourth target. Carried one further step down the same measured
#: slope and LABELLED AS AN EXTRAPOLATION wherever it is used.
ANCHOR_RANK4PLUS_EXTRAPOLATED = ANCHOR_RANK23 * (ANCHOR_RANK23 / ANCHOR_TOP1)

#: The registered variance channel every DEV-tier band is read against.
VARIANCE_PRIOR = "DEV-100 round-5 replication: plus-minus 2 per 100 at 8-slot decode"

#: The measured control-plane cost the plan carries into both agendas.
MULTIDIM_RECALL_SECONDS_PER_CALL = 1.147
MULTIDIM_RECALL_CALLS_PER_TRAJECTORY = 2


# ---------------------------------------------------------------------------
# Pinned sources
# ---------------------------------------------------------------------------

#: The two committed one-shot read verdicts whose published recall@k this
#: gate must reproduce before any hybrid number is believed.
FIDELITY_PINS = {
    "DEV-1000-NEW500": (
        "docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-lock-read/read-verdict.json",
        "2f8e295852e1c09d737467a62123586f097f938ec353dcbe58d258dadc1ea581",
        500,
    ),
    "DEV-500-NEW400": (
        "docs/checks/speech-aware-evidence-acquisition/2026-08-24-dev500-confirmatory-read/read-verdict.json",
        "b3187fea6f23f637dfa8ac43718667b0286a5c034ea9304bfb03e7029bfc90a3",
        400,
    ),
}

#: The DEV-1000 BLEND arm, restricted to the UNEXPOSED NEW500 -- the exact
#: population the lock statistic used. ``report_arm_key`` is None because the
#: DEV-1000 committed report is a mechanical-only landing whose shape has no
#: ``arms`` block; its byte pins are asserted separately against
#: :data:`.dev1000_lock_read.ARM_PINS`.
DEV1000_PIN = cf.CellPin(
    population_id="DEV-1000-NEW500",
    run_id=d1k.RUN_ID,
    attempt_id="attempt-20260825T054707Z-dev1000blend",
    outputs_basename="arm2-blend-outputs.jsonl",
    arm_key="BLEND",
    report_relpath=(
        "docs/checks/speech-aware-evidence-acquisition/2026-08-25-dev1000-baseline-lock/"
        "arm2-blend-mechanical-report.json"
    ),
    report_arm_key=None,
    restrict_to="new500",
)

#: Populations, primary first.
CELL_PINS = (DEV1000_PIN,) + tuple(
    pin for pin in cf.CELL_PINS if pin.population_id != "DEV-1000-NEW500"
)

#: The DEV-1000 BLEND arm flew the v2 candidate (the delta >= 0.14
#: retain-override), which the lock read FALSIFIED out of sample and which
#: the locked cell does not carry. The v1 replay this gate runs therefore
#: disagrees with the flown contact count on EXACTLY the override fires --
#: a proved, attributable deviation rather than a gate failure. The gate
#: refuses any mismatch that is not an override fire.
V2_OVERRIDE_POPULATIONS = frozenset({"DEV-1000-NEW500"})


@dataclass(frozen=True)
class _Shim:
    """A ``restrict_to`` target for the DEV-1000 population, which
    :class:`.dev500_confirmatory_read.Populations` does not carry."""

    dev100: tuple[str, ...]
    dev500: tuple[str, ...]
    new400: tuple[str, ...]
    new500: tuple[str, ...]


# ---------------------------------------------------------------------------
# The lexical channel
# ---------------------------------------------------------------------------


def tokenize(text: str) -> list[str]:
    """The registered tokenizer, applied identically to both sides."""

    return TOKEN_RE.findall(text.lower())


def query_tokens(text: str, normalization: str) -> list[str]:
    """``Q-RAW`` is the direct-decode text verbatim. ``Q-VAL`` drops the five
    constant JSON schema key tokens, which every query emits and which
    therefore carry no per-sample information."""

    tokens = tokenize(text)
    if normalization == "Q-RAW":
        return tokens
    if normalization == "Q-VAL":
        return [token for token in tokens if token not in SCHEMA_KEY_TOKENS]
    raise GateError(f"unknown query normalization {normalization!r}")


@dataclass(frozen=True)
class Bm25Index:
    """A term-major BM25 index over the content-facet texts.

    Every BM25 weight is query-independent under the registered scoring form
    (each DISTINCT query term contributes once; no query-term-frequency
    saturation), so the whole ``idf * tf(k1+1) / (tf + k1(1-b+b*dl/avgdl))``
    product is precomputed once and a query is a gather-and-bincount. That
    is what makes the channel cheap enough to matter -- see the cost note.
    """

    vocabulary: Mapping[str, int]
    term_ptr: object  # numpy int64[n_terms + 1]
    term_docs: object  # numpy int32[nnz]
    term_weights: object  # numpy float64[nnz]
    n_docs: int
    avg_doc_length: float
    corpus_sha256: str

    def score(self, tokens: Sequence[str]):
        """BM25 over the whole corpus for one query. Returns float64[n_docs]."""

        import numpy as np

        seen: set[int] = set()
        chunks_docs = []
        chunks_weights = []
        for token in tokens:
            term = self.vocabulary.get(token)
            if term is None or term in seen:
                continue
            seen.add(term)
            start, end = int(self.term_ptr[term]), int(self.term_ptr[term + 1])
            chunks_docs.append(self.term_docs[start:end])
            chunks_weights.append(self.term_weights[start:end])
        if not chunks_docs:
            return np.zeros(self.n_docs, dtype=np.float64)
        docs = np.concatenate(chunks_docs)
        weights = np.concatenate(chunks_weights)
        return np.bincount(docs, weights=weights, minlength=self.n_docs).astype(
            np.float64, copy=False
        )


def build_bm25_index(texts: Sequence[str]) -> Bm25Index:
    """Build the registered BM25 index over the content-facet texts.

    IDF is the Robertson/Lucene non-negative form
    ``ln(1 + (N - df + 0.5) / (df + 0.5))``; the length normalization is the
    standard ``k1``/``b`` form at :data:`BM25_K1` / :data:`BM25_B`. The
    corpus is hashed so the index is addressable in the receipt.
    """

    import numpy as np

    digest = hashlib.sha256()
    for text in texts:
        digest.update(text.encode("utf-8"))
        digest.update(b"\x00")
    corpus_sha256 = digest.hexdigest()

    n_docs = len(texts)
    vocabulary: dict[str, int] = {}
    postings: list[list[tuple[int, int]]] = []
    doc_lengths = np.zeros(n_docs, dtype=np.float64)
    for doc_index, text in enumerate(texts):
        tokens = tokenize(text)
        doc_lengths[doc_index] = float(len(tokens))
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        for token, frequency in counts.items():
            term = vocabulary.get(token)
            if term is None:
                term = len(vocabulary)
                vocabulary[token] = term
                postings.append([])
            postings[term].append((doc_index, frequency))

    avg_doc_length = float(doc_lengths.mean()) if n_docs else 0.0
    denominator_length = BM25_K1 * (
        1.0 - BM25_B + BM25_B * (doc_lengths / avg_doc_length if avg_doc_length else doc_lengths)
    )

    term_ptr = np.zeros(len(vocabulary) + 1, dtype=np.int64)
    for term, entries in enumerate(postings):
        term_ptr[term + 1] = term_ptr[term] + len(entries)
    nnz = int(term_ptr[-1])
    term_docs = np.zeros(nnz, dtype=np.int32)
    term_weights = np.zeros(nnz, dtype=np.float64)
    for term, entries in enumerate(postings):
        document_frequency = len(entries)
        idf = float(np.log(1.0 + (n_docs - document_frequency + 0.5) / (document_frequency + 0.5)))
        start = int(term_ptr[term])
        for offset, (doc_index, frequency) in enumerate(entries):
            term_docs[start + offset] = doc_index
            term_weights[start + offset] = idf * (
                frequency * (BM25_K1 + 1.0) / (frequency + denominator_length[doc_index])
            )

    return Bm25Index(
        vocabulary=vocabulary,
        term_ptr=term_ptr,
        term_docs=term_docs,
        term_weights=term_weights,
        n_docs=n_docs,
        avg_doc_length=avg_doc_length,
        corpus_sha256=corpus_sha256,
    )


def lexical_similarity(bm25_scores):
    """Bound the BM25 scores into ``[0, 1]`` by the query's own maximum.

    Percept admission and the ranker's ``max_cosine`` both compare against a
    cosine-scaled threshold, so a second dimension that is to be
    INDEPENDENTLY MATCHABLE inside the registered policy must present on the
    same bounded scale. The transform is per query and order-preserving, so
    it changes no lexical ordering; an all-zero query maps to all zeros.
    """

    import numpy as np

    peak = float(bm25_scores.max()) if bm25_scores.size else 0.0
    if peak <= 0.0:
        return np.zeros_like(bm25_scores)
    return bm25_scores / peak


# ---------------------------------------------------------------------------
# The fusion grid
# ---------------------------------------------------------------------------


def _zscore(values):
    import numpy as np

    mean = float(values.mean())
    deviation = float(values.std())
    if deviation <= 0.0:
        return np.zeros_like(values)
    return (values - mean) / deviation


def _ranks_from_scores(scores):
    """1-based dense-position ranks under the sealed reads' own ordering
    convention: score descending, ties broken by facet INDEX ascending
    (``np.argsort(-scores, kind="stable")``), which is what
    ``reachability_ceiling`` and ``replay_population`` both use."""

    import numpy as np

    order = np.argsort(-scores, kind="stable")
    ranks = np.empty(scores.shape[0], dtype=np.int64)
    ranks[order] = np.arange(1, scores.shape[0] + 1, dtype=np.int64)
    return ranks


def fused_ranks(rule: str, *, cosines, lexical, dense_ranks, lexical_ranks):
    """1-based ranks of every content facet under one registered fusion rule.

    ``DENSE-ONLY``   the flown ranking, reproduced.
    ``LIN-w``        ``(1 - w) * z(cos) + w * z(lex)``, each channel
                     z-normalized per query over the FULL facet population.
    ``RRF-60``       ``1/(60 + rank_dense) + 1/(60 + rank_lex)``.
    ``TIEBREAK``     order by cosine, break exact float ties by lexical
                     score, then by facet index.
    """

    import numpy as np

    if rule == "DENSE-ONLY":
        return dense_ranks
    if rule.startswith("LIN-"):
        weight = float(rule.split("-", 1)[1])
        fused = (1.0 - weight) * _zscore(cosines) + weight * _zscore(lexical)
        return _ranks_from_scores(fused)
    if rule == "RRF-60":
        fused = 1.0 / (RRF_K + dense_ranks) + 1.0 / (RRF_K + lexical_ranks)
        return _ranks_from_scores(fused)
    if rule == "TIEBREAK":
        index = np.arange(cosines.shape[0], dtype=np.int64)
        order = np.lexsort((index, -lexical, -cosines))
        ranks = np.empty(cosines.shape[0], dtype=np.int64)
        ranks[order] = np.arange(1, cosines.shape[0] + 1, dtype=np.int64)
        return ranks
    raise GateError(f"unknown fusion rule {rule!r}")


# ---------------------------------------------------------------------------
# Populations
# ---------------------------------------------------------------------------


def load_populations(repo_root: Path) -> _Shim:
    """The four id sets, each proved against its own committed receipt."""

    dev500 = d5.load_populations(Path(repo_root))
    dev1000 = d1k.load_populations(Path(repo_root))
    if set(dev500.dev500) != set(dev1000.dev500):
        raise GateError("the two receipt loaders disagree on the DEV-500 id set")
    return _Shim(
        dev100=dev500.dev100,
        dev500=dev500.dev500,
        new400=dev500.new400,
        new500=dev1000.new500,
    )


def assert_dev1000_byte_pins(*, repo_root: Path, data_root: Path) -> dict[str, str]:
    """Hash-verify the DEV-1000 BLEND arm's committed report and sealed
    attempt-store bytes against :data:`.dev1000_lock_read.ARM_PINS`, which
    :func:`.contrast_fewshot_preanalysis.load_cell_population` cannot do for
    a pin it does not know."""

    pin = next(item for item in d1k.ARM_PINS if item.arm_id == "BLEND")
    if pin.attempt_id != DEV1000_PIN.attempt_id:
        raise GateError("the DEV-1000 arm pin names another attempt")
    run_dir = Path(data_root) / "runs" / d1k.RUN_ID / pin.attempt_id
    return {
        pin.report_basename: d5._require_hash(
            Path(repo_root) / d1k.CHECK_DIR_RELPATH / pin.report_basename,
            pin.report_sha256,
            "DEV-1000 BLEND committed mechanical report",
        ),
        pin.outputs_basename: d5._require_hash(
            run_dir / pin.outputs_basename, pin.outputs_sha256, "DEV-1000 BLEND sealed outputs"
        ),
        pin.mechanical_basename: d5._require_hash(
            run_dir / pin.mechanical_basename,
            pin.mechanical_sha256,
            "DEV-1000 BLEND sealed per-sample mechanical records",
        ),
    }


def load_override_fires(*, data_root: Path) -> frozenset[str]:
    """The v2 retain-override fires, from the already hash-verified sealed
    per-sample mechanical record."""

    pin = next(item for item in d1k.ARM_PINS if item.arm_id == "BLEND")
    path = Path(data_root) / "runs" / d1k.RUN_ID / pin.attempt_id / pin.mechanical_basename
    records = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(sid for sid, record in records.items() if bool(record["override_fires"]))


def assert_query_text_identity(*, population: cf.CellPopulation) -> dict[str, object]:
    """Prove that the direct-decode texts this gate tokenizes are EXACTLY the
    texts the flight embedded.

    The landed ``query-vectors.jsonl`` carries, per sample, the sha256 of the
    text the embedding sidecar was handed. Re-hashing each recovered
    direct-decode text and matching it to that digest makes text substitution
    impossible and binds the lexical channel's query side to the dense
    channel's query side, byte for byte.
    """

    digests: dict[str, str] = {}
    with (population.run_dir / "query-vectors.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            contact_id = str(record["contact_id"])
            if contact_id.startswith("query:"):
                digests[contact_id.split("query:", 1)[1]] = str(record["text_sha256"])
    matched = 0
    for sample_id in population.sample_ids:
        text = population.inputs.direct_texts.get(sample_id)
        expected = digests.get(sample_id)
        if text is None or expected is None:
            raise GateError(f"{sample_id}: no direct-decode text or no landed query digest")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != expected:
            raise GateError(
                f"{sample_id}: the recovered direct-decode text does not re-hash to the digest "
                "the flight's own embedding contact recorded"
            )
        matched += 1
    return {
        "samples": len(population.sample_ids),
        "direct_text_matches_flown_query_digest": matched,
        "passed": matched == len(population.sample_ids),
    }


# ---------------------------------------------------------------------------
# Part A -- the ranking question
# ---------------------------------------------------------------------------


@dataclass
class SampleHybrid:
    """One sample's gold-facet position under every registered rule."""

    sample_id: str
    gold_target: str
    correct: bool
    dispatched_flown: bool
    dense_position: int | None
    positions: dict[str, int | None]
    lexical_top1_is_gold: bool
    query_token_count: int
    #: How many of the 11,514 dense cosines are EXACT float duplicates. The
    #: lexical-as-tiebreak rule can only act where this is non-zero, so the
    #: number is reported rather than left implicit.
    cosine_exact_ties: int
    lexical_nonzero_facets: int


def part_a(
    *,
    population: cf.CellPopulation,
    replays: Mapping[str, cf.SampleReplay],
    bundle: cf.SnapshotBundle,
    index: Bm25Index,
    normalization: str,
) -> tuple[dict[str, SampleHybrid], dict[str, object]]:
    """Gold-facet position under every fusion rule, for one population and
    one query normalization."""

    import numpy as np

    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)
    out: dict[str, SampleHybrid] = {}
    lexical_seconds = 0.0
    dense_seconds = 0.0
    dense_agreement_checked = 0

    for sample_id in population.sample_ids:
        replay = replays[sample_id]
        started = time.perf_counter()
        query = np.asarray(population.inputs.query_vectors[sample_id], dtype=np.float64)
        denominator = facet_norms * float(np.linalg.norm(query))
        with np.errstate(divide="ignore", invalid="ignore"):
            cosines = np.where(denominator > 0.0, matrix @ query / denominator, 0.0)
        dense_seconds += time.perf_counter() - started

        tokens = query_tokens(population.inputs.direct_texts[sample_id], normalization)
        started = time.perf_counter()
        lexical = lexical_similarity(index.score(tokens))
        lexical_seconds += time.perf_counter() - started

        dense_ranks = _ranks_from_scores(cosines)
        lexical_ranks = _ranks_from_scores(lexical)
        gold_indices = bundle.facet_indices_by_target.get(replay.gold_target)

        def position(ranks) -> int | None:
            if gold_indices is None or len(gold_indices) == 0:
                return None
            return int(np.asarray(ranks)[gold_indices].min())

        dense_position = position(dense_ranks)
        # The imported replay computed the same quantity through the sealed
        # reads' own code path; they must agree exactly or nothing below is
        # believable.
        if dense_position != replay.gold_facet_position:
            raise GateError(
                f"{sample_id}: recomputed dense gold position {dense_position} disagrees with "
                f"the imported replay's {replay.gold_facet_position}"
            )
        dense_agreement_checked += 1

        positions = {
            rule: position(
                fused_ranks(
                    rule,
                    cosines=cosines,
                    lexical=lexical,
                    dense_ranks=dense_ranks,
                    lexical_ranks=lexical_ranks,
                )
            )
            for rule in FUSION_RULES
        }
        lexical_top1 = int(np.argmax(lexical_ranks == 1))
        out[sample_id] = SampleHybrid(
            sample_id=sample_id,
            gold_target=replay.gold_target,
            correct=replay.correct,
            dispatched_flown=population.logged_contacts[sample_id] == 2,
            dense_position=dense_position,
            positions=positions,
            lexical_top1_is_gold=(
                bundle.content_facet_target.get(bundle.facet_ids[lexical_top1])
                == replay.gold_target
                and float(lexical[lexical_top1]) > 0.0
            ),
            query_token_count=len(tokens),
            cosine_exact_ties=int(cosines.shape[0] - np.unique(cosines).shape[0]),
            lexical_nonzero_facets=int((lexical > 0.0).sum()),
        )

    timing = {
        "dense_cosine_seconds_total": dense_seconds,
        "dense_cosine_seconds_per_sample": dense_seconds / max(1, len(out)),
        "lexical_scoring_seconds_total": lexical_seconds,
        "lexical_scoring_seconds_per_sample": lexical_seconds / max(1, len(out)),
        "dense_position_agreement_with_imported_replay": dense_agreement_checked,
    }
    return out, timing


def recall_table(
    hybrids: Mapping[str, SampleHybrid], *, k_grid: Sequence[int]
) -> dict[str, dict[str, object]]:
    total = len(hybrids)
    table: dict[str, dict[str, object]] = {}
    for rule in FUSION_RULES:
        row: dict[str, object] = {}
        for k in k_grid:
            count = sum(
                1
                for hybrid in hybrids.values()
                if hybrid.positions[rule] is not None and hybrid.positions[rule] <= k
            )
            row[f"recall_at_{k}"] = {"count": count, "rate": count / total if total else 0.0}
        positions = sorted(
            hybrid.positions[rule]
            for hybrid in hybrids.values()
            if hybrid.positions[rule] is not None
        )
        row["median_position"] = positions[len(positions) // 2] if positions else None
        table[rule] = row
    return table


def newly_reachable(
    hybrids: Mapping[str, SampleHybrid], *, window: int = FROZEN_TOP_K
) -> dict[str, object]:
    """The decision quantity at RANK level: currently-WRONG DISPATCHED
    trajectories whose gold facet is outside the top-``window`` under the
    flown dense ranking and inside it under the rule.

    The loss side is reported beside it, because a rule that promotes five
    errors and demotes five correct answers has changed nothing.
    """

    eligible = [
        hybrid
        for hybrid in hybrids.values()
        if hybrid.dispatched_flown
        and not hybrid.correct
        and (hybrid.dense_position is None or hybrid.dense_position > window)
    ]
    at_risk = [
        hybrid
        for hybrid in hybrids.values()
        if hybrid.dispatched_flown
        and hybrid.correct
        and hybrid.dense_position is not None
        and hybrid.dense_position <= window
    ]
    out: dict[str, object] = {
        "window": window,
        "dispatched_flown": sum(1 for h in hybrids.values() if h.dispatched_flown),
        "wrong_dispatched_with_gold_outside_window": len(eligible),
        "correct_dispatched_with_gold_inside_window": len(at_risk),
        "per_rule": {},
    }
    for rule in FUSION_RULES:
        gained = [
            hybrid.sample_id
            for hybrid in eligible
            if hybrid.positions[rule] is not None and hybrid.positions[rule] <= window
        ]
        lost = [
            hybrid.sample_id
            for hybrid in at_risk
            if hybrid.positions[rule] is None or hybrid.positions[rule] > window
        ]
        out["per_rule"][rule] = {
            "newly_reachable_wrong_dispatched": len(gained),
            "newly_reachable_sample_ids": gained[:20],
            "correct_dispatched_pushed_out": len(lost),
            "pushed_out_sample_ids": lost[:20],
            "net_rank_level": len(gained) - len(lost),
        }
    return out


# ---------------------------------------------------------------------------
# Part B -- the second dimension activated inside the registered policy
# ---------------------------------------------------------------------------


@dataclass
class NativeReplay:
    """One sample's frozen-cell replay with the second dimension active."""

    sample_id: str
    dims_total: int
    candidates: int
    candidates_dims_hit_2: int
    top_m_dims_hit_2: int
    admitted_count: int
    admitted_lex_only: int
    supplied_targets: tuple[str, ...]
    gold_supplied: bool
    gold_target_rank: int | None
    selected_value_ids: tuple[str, ...]
    retain_primary: bool
    dispatched: bool
    #: The direct decode's OWN score against gold. A trajectory that retains
    #: under the hybrid answers with this text, so its outcome is arithmetic
    #: rather than projected -- the dispatch anchors do not apply to it.
    direct_correct: bool
    baseline_dispatched: bool
    supply_identical_to_baseline: bool


def _native_recall_scores(
    *,
    bundle: cf.SnapshotBundle,
    cosines,
    lexical,
    top_k: int = FROZEN_TOP_K,
) -> dict[str, dict[str, float]]:
    """``multidim_recall``'s exact contract, extended by ONE dimension.

    Each dimension truncates to its OWN top ``top_k`` (score descending,
    facet_id ascending tie-break) BEFORE the union and admits only strictly
    positive scores -- ``content`` by dense cosine and :data:`LEX_DIMENSION`
    by the bounded lexical similarity, over the SAME facet population. The
    prior-mass dimensions are carried unchanged from the bundle's own
    ``kb.multidim_recall`` call. A facet recalled by both content channels
    therefore carries TWO dimensions, which is the whole point of K1.
    """

    import numpy as np

    recalled: dict[str, dict[str, float]] = {}
    for dimension, scores in ((("content"), cosines), (LEX_DIMENSION, lexical)):
        order = np.lexsort((bundle.facet_id_rank, -np.asarray(scores)))
        for index in order[:top_k]:
            value = float(scores[int(index)])
            if value <= 0.0:
                break
            recalled.setdefault(bundle.facet_ids[int(index)], {})[dimension] = value
    for facet_id, dim_scores in bundle.prior_dimension_recall.items():
        recalled.setdefault(facet_id, {}).update(dim_scores)
    return recalled


def part_b(
    *,
    population: cf.CellPopulation,
    replays: Mapping[str, cf.SampleReplay],
    bundle: cf.SnapshotBundle,
    index: Bm25Index,
    normalization: str,
) -> tuple[dict[str, NativeReplay], dict[str, object]]:
    """Replay the frozen cell with :data:`LEX_DIMENSION` ACTIVE, through the
    registered ``kb_policy`` ranker and fuser -- not a second implementation.

    Gated twice: the BASELINE arm of the same code path must reproduce the
    imported replay's ``selected_value_ids`` exactly on every sample, and the
    single-dimension ``agreement`` degeneracy must measure as the constant
    the plan asserts.
    """

    import numpy as np

    matrix = np.asarray(bundle.matrix, dtype=np.float64)
    facet_norms = np.linalg.norm(matrix, axis=1)
    out: dict[str, NativeReplay] = {}
    baseline_supply_matches = 0
    degeneracy_checked = 0
    degeneracy_violations: list[str] = []
    fuse_seconds = 0.0

    for sample_id in population.sample_ids:
        replay = replays[sample_id]
        query = np.asarray(population.inputs.query_vectors[sample_id], dtype=np.float64)
        denominator = facet_norms * float(np.linalg.norm(query))
        with np.errstate(divide="ignore", invalid="ignore"):
            cosines = np.where(denominator > 0.0, matrix @ query / denominator, 0.0)
        tokens = query_tokens(population.inputs.direct_texts[sample_id], normalization)
        lexical = lexical_similarity(index.score(tokens))

        # --- the baseline arm of the SAME code path, as a fidelity gate ---
        baseline_scores = cf.vectorised_recall(bundle, cosines, top_k=FROZEN_TOP_K)
        baseline_supply = dc.replay_supply(
            population.inputs,
            sample_id,
            weights=FROZEN_WEIGHTS,
            knobs=FROZEN_FUSE,
            top_k=FROZEN_TOP_K,
            recall_scores=baseline_scores,
        )
        if tuple(sorted(baseline_supply.selected_value_ids)) != tuple(
            sorted(replay.selected_value_ids)
        ):
            raise GateError(
                f"{sample_id}: the baseline arm of this module's own code path does not reproduce "
                "the imported replay's supply"
            )
        baseline_supply_matches += 1
        if baseline_supply.dims_total != 3:
            degeneracy_violations.append(f"{sample_id}: dims_total {baseline_supply.dims_total}")
        elif any(len(dims) != 1 for dims in baseline_scores.values()):
            degeneracy_violations.append(f"{sample_id}: a facet carries more than one dimension")
        degeneracy_checked += 1

        # --- the hybrid arm: the second dimension is live ---
        hybrid_scores = _native_recall_scores(bundle=bundle, cosines=cosines, lexical=lexical)
        started = time.perf_counter()
        hybrid_supply = dc.replay_supply(
            population.inputs,
            sample_id,
            weights=FROZEN_WEIGHTS,
            knobs=FROZEN_FUSE,
            top_k=FROZEN_TOP_K,
            recall_scores=hybrid_scores,
        )
        fuse_seconds += time.perf_counter() - started
        direct_label = kb.default_label_normalizer(
            population.inputs.direct_texts[sample_id], population.inputs.label_targets
        )
        blend = dc.replay_blend(
            population.inputs, hybrid_supply, direct_label=direct_label, alpha=FROZEN_ALPHA
        )
        supply_empty = not hybrid_supply.selected_value_ids
        retain = blend.retain_primary and not supply_empty

        supplied_targets: list[str] = []
        for value_id in hybrid_supply.selected_value_ids:
            target = population.inputs.values_by_id[value_id].task_target
            if target is not None and target not in supplied_targets:
                supplied_targets.append(target)
        # Target order as the fuser itself ranks them: by the score of the
        # best admitted supporting facet.
        facet_score = {
            candidate.facet_id: candidate.score for candidate in hybrid_supply.rank_result.candidates
        }
        best_by_target: dict[str, float] = {}
        for value_id in hybrid_supply.selected_value_ids:
            value = population.inputs.values_by_id[value_id]
            if value.task_target is None:
                continue
            supporting = set(value.associated_facet_ids) & set(hybrid_supply.admitted_facet_ids)
            if not supporting:
                continue
            best = max(facet_score.get(facet_id, 0.0) for facet_id in supporting)
            best_by_target[value.task_target] = max(
                best_by_target.get(value.task_target, 0.0), best
            )
        ordered_targets = tuple(
            target for target, _ in sorted(best_by_target.items(), key=lambda kv: (-kv[1], kv[0]))
        )
        gold_rank = (
            ordered_targets.index(replay.gold_target) + 1
            if replay.gold_target in ordered_targets
            else None
        )

        candidates = hybrid_scores
        dims_hit_2 = sum(1 for dims in candidates.values() if len(dims) >= 2)
        top_m_hit_2 = sum(
            1
            for facet_id in hybrid_supply.top_m_facet_ids
            if len(candidates.get(facet_id, {})) >= 2
        )
        admitted_lex_only = sum(
            1
            for facet_id in hybrid_supply.admitted_facet_ids
            if candidates.get(facet_id, {}).get("content", 0.0) < FROZEN_FUSE.tau
        )

        out[sample_id] = NativeReplay(
            sample_id=sample_id,
            dims_total=hybrid_supply.dims_total,
            candidates=len(candidates),
            candidates_dims_hit_2=dims_hit_2,
            top_m_dims_hit_2=top_m_hit_2,
            admitted_count=len(hybrid_supply.admitted_facet_ids),
            admitted_lex_only=admitted_lex_only,
            supplied_targets=ordered_targets,
            gold_supplied=replay.gold_target in ordered_targets,
            gold_target_rank=gold_rank,
            selected_value_ids=tuple(sorted(hybrid_supply.selected_value_ids)),
            retain_primary=retain,
            dispatched=not (retain or supply_empty),
            direct_correct=bool(
                dc.score_response(
                    population.inputs.gold_by_sample[sample_id],
                    population.inputs.direct_texts[sample_id],
                )["correct"]
            ),
            baseline_dispatched=population.logged_contacts[sample_id] == 2,
            supply_identical_to_baseline=(
                tuple(sorted(hybrid_supply.selected_value_ids))
                == tuple(sorted(replay.selected_value_ids))
            ),
        )

    gate = {
        "baseline_arm_supply_reproduces_imported_replay": baseline_supply_matches,
        "baseline_arm_gate_passed": baseline_supply_matches == len(population.sample_ids),
        "single_dimension_degeneracy_checked": degeneracy_checked,
        "single_dimension_degeneracy_violations": degeneracy_violations[:10],
        "single_dimension_degeneracy_confirmed": not degeneracy_violations,
        "hybrid_fuse_seconds_total": fuse_seconds,
        "hybrid_fuse_seconds_per_sample": fuse_seconds / max(1, len(out)),
    }
    return out, gate


def supply_delta(
    *,
    replays: Mapping[str, cf.SampleReplay],
    natives: Mapping[str, NativeReplay],
    population: cf.CellPopulation,
) -> dict[str, object]:
    """What the activated second dimension does to the SUPPLY, which is the
    only channel through which it can change an answer."""

    baseline_targets: dict[str, tuple[str, ...]] = {}
    for sample_id, replay in replays.items():
        ordered = tuple(
            target for target, _ in sorted(replay.supplied_per_target.items(), key=lambda kv: kv[0])
        )
        baseline_targets[sample_id] = ordered

    unchanged = changed = 0
    newly_supplied_wrong: list[str] = []
    lost_supply_correct: list[str] = []
    dispatch_flips: list[str] = []
    for sample_id, native in natives.items():
        replay = replays[sample_id]
        same = tuple(sorted(native.selected_value_ids)) == tuple(sorted(replay.selected_value_ids))
        if same:
            unchanged += 1
        else:
            changed += 1
        gold_was_supplied = replay.gold_target in set(baseline_targets[sample_id])
        if not replay.correct and native.gold_supplied and not gold_was_supplied:
            newly_supplied_wrong.append(sample_id)
        if replay.correct and gold_was_supplied and not native.gold_supplied:
            lost_supply_correct.append(sample_id)
        if native.dispatched != (population.logged_contacts[sample_id] == 2):
            dispatch_flips.append(sample_id)

    return {
        "supply_unchanged": unchanged,
        "supply_changed": changed,
        "newly_gold_supplied_currently_wrong": len(newly_supplied_wrong),
        "newly_gold_supplied_sample_ids": newly_supplied_wrong[:20],
        "lost_gold_supply_currently_correct": len(lost_supply_correct),
        "lost_gold_supply_sample_ids": lost_supply_correct[:20],
        "dispatch_decision_flips_vs_flown": len(dispatch_flips),
        "dispatch_flip_sample_ids": dispatch_flips[:20],
    }


# ---------------------------------------------------------------------------
# Conversion projection
# ---------------------------------------------------------------------------


def _anchor_rate(rank: int | None) -> tuple[float, str]:
    if rank is None:
        return ANCHOR_ABSENT, "absent (measured 0/67)"
    if rank == 1:
        return ANCHOR_TOP1, "fused top-1 (measured 108/110)"
    if rank in (2, 3):
        return ANCHOR_RANK23, "fused rank 2-3 (measured 16/23)"
    return ANCHOR_RANK4PLUS_EXTRAPOLATED, "fused rank 4+ (EXTRAPOLATED, not measured)"


def conversion_projection(
    *,
    replays: Mapping[str, cf.SampleReplay],
    natives: Mapping[str, NativeReplay],
) -> dict[str, object]:
    """Project accuracy over the hybrid supply using ONLY measured anchors.

    Construction, identical to the supply-budget projection section 7: a
    trajectory whose supplied set is UNCHANGED receives a byte-identical
    evidence prompt and its outcome is carried over EXACTLY (arithmetic, not
    projection); a trajectory whose supplied set CHANGES is priced at the
    measured rate for wherever gold sits under the variant, whether it is
    right or wrong today -- the symmetric reading. The PESSIMISTIC edge
    prices every changed trajectory one rank-band worse; the OPTIMISTIC edge
    assumes no currently-correct trajectory is disturbed and every
    gold-supplied error converts at the top-1 rate.
    """

    baseline_correct = sum(1 for replay in replays.values() if replay.correct)
    central = pessimistic = optimistic = 0.0
    exact_carried = exact_retained = 0
    changed = 0
    priced_at_extrapolation = 0
    for sample_id, native in natives.items():
        replay = replays[sample_id]
        if not native.dispatched:
            # The trajectory answers with its OWN direct decode. Arithmetic,
            # not projection -- and the DISPATCH anchors, which are measured
            # only on dispatched trajectories, must not be applied to it.
            outcome = 1.0 if native.direct_correct else 0.0
            central += outcome
            pessimistic += outcome
            optimistic += outcome
            exact_retained += 1
            continue
        if native.baseline_dispatched and native.supply_identical_to_baseline:
            # A byte-identical evidence prompt: carry the sealed outcome.
            outcome = 1.0 if replay.correct else 0.0
            central += outcome
            pessimistic += outcome
            optimistic += outcome
            exact_carried += 1
            continue
        changed += 1
        rank = native.gold_target_rank if native.gold_supplied else None
        rate, label = _anchor_rate(rank)
        if label.startswith("fused rank 4+"):
            priced_at_extrapolation += 1
        central += rate
        worse_rank = None if rank is None else (rank + 2 if rank == 1 else rank + 1)
        pessimistic += _anchor_rate(worse_rank)[0]
        if replay.correct:
            optimistic += 1.0
        else:
            optimistic += ANCHOR_TOP1 if native.gold_supplied else 0.0

    total = len(natives)
    return {
        "exact_outcomes_retained_trajectories": exact_retained,
        "exact_outcomes_identical_supply": exact_carried,
        "construction": (
            "a trajectory that RETAINS under the hybrid carries its own direct decode's score "
            "EXACTLY; a dispatched trajectory whose supplied set is byte-identical to the flown "
            "one carries its sealed outcome EXACTLY; only a dispatched trajectory whose supply "
            "CHANGED is priced, at the measured anchor for wherever gold sits under the hybrid, "
            "symmetrically for currently-correct and currently-wrong trajectories"
        ),
        "anchors": {
            "fused_top1": ANCHOR_TOP1,
            "fused_rank_2_or_3": ANCHOR_RANK23,
            "absent": ANCHOR_ABSENT,
            "fused_rank_4_plus_EXTRAPOLATED": ANCHOR_RANK4PLUS_EXTRAPOLATED,
        },
        "n": total,
        "sealed_baseline_correct": baseline_correct,
        "sealed_baseline_rate": baseline_correct / total if total else 0.0,
        "changed_trajectories": changed,
        "changed_priced_at_the_unanchored_rank": priced_at_extrapolation,
        "projected_pessimistic": pessimistic,
        "projected_central": central,
        "projected_optimistic": optimistic,
        "delta_pp_pessimistic": 100.0 * (pessimistic - baseline_correct) / total if total else 0.0,
        "delta_pp_central": 100.0 * (central - baseline_correct) / total if total else 0.0,
        "delta_pp_optimistic": 100.0 * (optimistic - baseline_correct) / total if total else 0.0,
        "variance_prior": VARIANCE_PRIOR,
    }


def agreement_finding(natives: Mapping[str, NativeReplay]) -> dict[str, object]:
    """The STRUCTURAL claim, independent of the accuracy projection."""

    total_candidates = sum(native.candidates for native in natives.values())
    total_hit2 = sum(native.candidates_dims_hit_2 for native in natives.values())
    top_m_total = sum(min(FROZEN_FUSE.m, native.candidates) for native in natives.values())
    top_m_hit2 = sum(native.top_m_dims_hit_2 for native in natives.values())
    samples_with_hit2 = sum(1 for native in natives.values() if native.candidates_dims_hit_2 > 0)
    dims_totals = sorted({native.dims_total for native in natives.values()})
    return {
        "before": (
            "every facet carries exactly ONE dimension, dims_total is 3, agreement is a constant "
            "1/3 for every candidate, and the ranker's score is the affine map 0.5*cos + 0.0667"
        ),
        "after_dims_total_observed": dims_totals,
        "candidate_facets_total": total_candidates,
        "candidate_facets_dims_hit_2": total_hit2,
        "candidate_facets_dims_hit_2_rate": total_hit2 / total_candidates if total_candidates else 0.0,
        "top_m_candidates_total": top_m_total,
        "top_m_candidates_dims_hit_2": top_m_hit2,
        "top_m_candidates_dims_hit_2_rate": top_m_hit2 / top_m_total if top_m_total else 0.0,
        "samples_with_at_least_one_two_dimension_candidate": samples_with_hit2,
        "samples": len(natives),
        "agreement_values_now_reachable": [1 / 4, 2 / 4],
        "score_separation_at_equal_max_signal": FROZEN_WEIGHTS.w_agree * (2 / 4 - 1 / 4),
        "reading": (
            "with two content dimensions live, agreement takes two distinct values instead of one, "
            "so w_agree is no longer multiplying a constant and the rank-weight family is "
            "structurally non-degenerate; whether that BUYS anything is the separate accuracy "
            "question this gate also answers"
        ),
    }


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def fidelity_gate(
    *, repo_root: Path, population_id: str, hybrids: Mapping[str, SampleHybrid]
) -> dict[str, object]:
    """Reproduce the sealed one-shot read's published gold-facet recall@k
    from this module's own recomputation, before any hybrid number counts."""

    relpath, sha256, expected_n = FIDELITY_PINS[population_id]
    path = Path(repo_root) / relpath
    measured = d5._require_hash(path, sha256, f"{population_id} committed read verdict")
    published = json.loads(path.read_text(encoding="utf-8"))["reachability_ceiling"]
    if int(published["n"]) != expected_n or len(hybrids) != expected_n:
        raise GateError(f"{population_id}: population size disagrees with the sealed verdict")

    rows: dict[str, object] = {}
    all_match = True
    for k in FIDELITY_K_GRID:
        count = sum(
            1
            for hybrid in hybrids.values()
            if hybrid.dense_position is not None and hybrid.dense_position <= k
        )
        expected = int(published["recall_at_k"][f"recall_at_{k}"]["count"])
        match = count == expected
        all_match = all_match and match
        rows[f"recall_at_{k}"] = {
            "recomputed_count": count,
            "published_count": expected,
            "rate": count / expected_n,
            "match": match,
        }
    absent = sum(1 for hybrid in hybrids.values() if hybrid.dense_position is None)
    absent_match = absent == int(published["gold_bearing_facet_absent_from_kb"])
    return {
        "source": relpath,
        "source_sha256": measured,
        "n": expected_n,
        "rows": rows,
        "gold_absent_recomputed": absent,
        "gold_absent_published": int(published["gold_bearing_facet_absent_from_kb"]),
        "passed": all_match and absent_match,
    }


def cost_note(*, timings: Mapping[str, object], index: Bm25Index) -> dict[str, object]:
    """What the second channel costs, against the plan's measured reference."""

    per_sample = float(timings["lexical_scoring_seconds_per_sample"])
    reference = MULTIDIM_RECALL_SECONDS_PER_CALL * MULTIDIM_RECALL_CALLS_PER_TRAJECTORY
    return {
        "reference_measured": (
            f"multidim_recall costs {MULTIDIM_RECALL_SECONDS_PER_CALL} s per call over 11,514 "
            f"facets and runs {MULTIDIM_RECALL_CALLS_PER_TRAJECTORY}x per trajectory = "
            f"{reference:.3f} s per trajectory of pure control-plane CPU"
        ),
        "lexical_index_build_terms": len(index.vocabulary),
        "lexical_index_postings": int(index.term_ptr[-1]),
        "lexical_index_corpus_sha256": index.corpus_sha256,
        "lexical_seconds_per_query_measured": per_sample,
        "lexical_seconds_per_1000_trajectories": per_sample * 1000.0,
        "reference_seconds_per_1000_trajectories": reference * 1000.0,
        "lexical_cost_as_fraction_of_the_reference": per_sample / reference if reference else None,
        "dense_cosine_seconds_per_sample_measured": float(
            timings["dense_cosine_seconds_per_sample"]
        ),
        "reading": (
            "the lexical channel is an inverted index whose per-document BM25 weights are entirely "
            "query-independent under the registered scoring form, so a query is a gather and a "
            "bincount; the index is built ONCE per snapshot and the per-query cost is measured "
            "here, not modelled"
        ),
        "vectorization_prerequisite": (
            "the plan's engineering note stands and is UNCHANGED by this gate: the 1.147 s/call "
            "cost belongs to the EXISTING scalar content dimension, not to the new channel, and "
            "it is what must be vectorised before a 1,000-sample flight"
        ),
    }


def run(*, repo_root: Path, data_root: Path) -> dict[str, object]:
    """Execute the gate. Offline guard armed before any input is opened."""

    attempts = ra.arm_offline_guard()

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    started = time.perf_counter()

    bundle = cf.load_snapshot_bundle(data_root=data_root, repo_root=repo_root)
    populations = load_populations(repo_root)
    dev1000_hashes = assert_dev1000_byte_pins(repo_root=repo_root, data_root=data_root)
    override_fires = load_override_fires(data_root=data_root)

    content_texts = {
        facet.facet_id: facet.representation
        for facet in bundle.snapshot.facets
        if facet.dimension == "content"
    }
    missing = set(bundle.facet_ids) - set(content_texts)
    if missing:
        raise GateError(f"{len(missing)} landed content-facet vectors have no facet text")
    index_started = time.perf_counter()
    index = build_bm25_index([content_texts[facet_id] for facet_id in bundle.facet_ids])
    index_build_seconds = time.perf_counter() - index_started

    results: dict[str, object] = {}
    all_timings: dict[str, object] = {}
    for pin in CELL_PINS:
        population = cf.load_cell_population(
            pin=pin,
            bundle=bundle,
            populations=populations,
            data_root=data_root,
            repo_root=repo_root,
        )
        replays, flight_gate = cf.replay_population(population, bundle)

        # The v2 override deviation, proved rather than tolerated.
        mismatches = {
            str(item["sample_id"]) for item in flight_gate["retain_dispatch_decision_mismatches"]
        }
        if pin.population_id in V2_OVERRIDE_POPULATIONS:
            unexplained = mismatches - override_fires
            flight_gate["v2_override_deviation"] = {
                "explanation": (
                    "the DEV-1000 BLEND arm flew the v2 delta>=0.14 retain-override, which the "
                    "lock read FALSIFIED out of sample and which the locked v1 cell does not "
                    "carry; the v1 replay therefore disagrees with the flown contact count on "
                    "exactly the override fires"
                ),
                "override_fires_in_population": len(
                    override_fires & set(population.sample_ids)
                ),
                "mismatches_all_explained_by_the_override": not unexplained,
                "unexplained_mismatch_sample_ids": sorted(unexplained)[:10],
            }
            if unexplained:
                raise GateError(
                    f"{pin.population_id}: {len(unexplained)} dispatch mismatches are NOT override "
                    "fires -- the replay does not reproduce the flight"
                )
        elif not flight_gate["retain_dispatch_gate_passed"]:
            raise GateError(f"{pin.population_id}: the flight replay gate did not pass")
        if not flight_gate["supply_gate_passed"]:
            raise GateError(f"{pin.population_id}: the flown SUPPLY was not reproduced exactly")
        if "committed_anchor_gate_passed" in flight_gate and not flight_gate[
            "committed_anchor_gate_passed"
        ]:
            raise GateError(
                f"{pin.population_id}: the replay does not reproduce the committed report's own "
                "retain-primary and correct counts"
            )

        query_identity = assert_query_text_identity(population=population)

        per_normalization: dict[str, object] = {}
        for normalization in QUERY_NORMALIZATIONS:
            hybrids, timing = part_a(
                population=population,
                replays=replays,
                bundle=bundle,
                index=index,
                normalization=normalization,
            )
            all_timings[f"{pin.population_id}/{normalization}"] = timing
            entry: dict[str, object] = {
                "recall_table": recall_table(hybrids, k_grid=REPORT_K_GRID),
                "newly_reachable": newly_reachable(hybrids),
                "lexical_channel_alone_top1_is_gold": sum(
                    1 for hybrid in hybrids.values() if hybrid.lexical_top1_is_gold
                ),
                "mean_query_tokens": sum(h.query_token_count for h in hybrids.values())
                / max(1, len(hybrids)),
                "samples_with_any_exact_cosine_tie": sum(
                    1 for h in hybrids.values() if h.cosine_exact_ties > 0
                ),
                "mean_lexically_touched_facets": sum(
                    h.lexical_nonzero_facets for h in hybrids.values()
                )
                / max(1, len(hybrids)),
                "samples_with_empty_lexical_channel": sum(
                    1 for h in hybrids.values() if h.lexical_nonzero_facets == 0
                ),
                "timing": timing,
            }
            if pin.population_id in FIDELITY_PINS and normalization == QUERY_NORMALIZATIONS[0]:
                entry["fidelity_gate"] = fidelity_gate(
                    repo_root=repo_root, population_id=pin.population_id, hybrids=hybrids
                )
                if not entry["fidelity_gate"]["passed"]:
                    raise GateError(
                        f"{pin.population_id}: the recomputed dense recall@k does not reproduce "
                        "the sealed one-shot read"
                    )
            natives, native_gate = part_b(
                population=population,
                replays=replays,
                bundle=bundle,
                index=index,
                normalization=normalization,
            )
            entry["native_second_dimension"] = {
                "gate": native_gate,
                "supply_delta": supply_delta(
                    replays=replays, natives=natives, population=population
                ),
                "agreement": agreement_finding(natives),
                "conversion_projection": conversion_projection(
                    replays=replays, natives=natives
                ),
                "admitted_by_the_lexical_dimension_alone": sum(
                    native.admitted_lex_only for native in natives.values()
                ),
            }
            per_normalization[normalization] = entry

        results[pin.population_id] = {
            "pin": {
                "run_id": pin.run_id,
                "attempt_id": pin.attempt_id,
                "outputs": pin.outputs_basename,
                "restrict_to": pin.restrict_to,
                "n": len(population.sample_ids),
            },
            "artifact_hashes": dict(population.artifact_hashes),
            "flight_replay_gate": flight_gate,
            "query_text_identity": query_identity,
            "by_query_normalization": per_normalization,
        }

    primary = results["DEV-1000-NEW500"]["by_query_normalization"]
    verdict = {}
    for normalization in QUERY_NORMALIZATIONS:
        table = primary[normalization]["recall_table"]
        baseline = table["DENSE-ONLY"]["recall_at_5"]["rate"]
        best_rule = max(
            (rule for rule in FUSION_RULES if rule != "DENSE-ONLY"),
            key=lambda rule: table[rule]["recall_at_5"]["rate"],
        )
        best = table[best_rule]["recall_at_5"]["rate"]
        verdict[normalization] = {
            "baseline_recall_at_5": baseline,
            "best_rule": best_rule,
            "best_recall_at_5": best,
            "delta_pp": 100.0 * (best - baseline),
            "raised": best > baseline,
        }
    raised = any(entry["raised"] for entry in verdict.values())

    return {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row_id": EXPOSURE_ROW_ID,
        "authority": {"plan": PLAN_RELPATH, "lock_verdict": VERDICT_RELPATH},
        "registered_constants": {
            "tokenizer": "lowercase, then r'[a-z0-9]+'; no stemming, no stoplist, no resource",
            "query_normalizations": {
                "Q-RAW": "the direct-decode text verbatim -- exactly what the flight embedded",
                "Q-VAL": f"the same text minus the constant schema key tokens {sorted(SCHEMA_KEY_TOKENS)}",
            },
            "bm25": {"k1": BM25_K1, "b": BM25_B, "idf": "ln(1 + (N - df + 0.5)/(df + 0.5))"},
            "lexical_similarity": "bm25 / max_d bm25 (per query, order-preserving, bounded [0,1])",
            "fusion_rules": list(FUSION_RULES),
            "rrf_k": RRF_K,
            "linear_weight_grid": list(LINEAR_W_GRID),
            "frozen_cell": {
                "alpha": FROZEN_ALPHA,
                "tau": FROZEN_FUSE.tau,
                "m": FROZEN_FUSE.m,
                "c": FROZEN_FUSE.c,
                "top_l": FROZEN_FUSE.top_l,
                "top_k_per_dimension": FROZEN_TOP_K,
                "w_cos": FROZEN_WEIGHTS.w_cos,
                "w_prior": FROZEN_WEIGHTS.w_prior,
                "w_agree": FROZEN_WEIGHTS.w_agree,
            },
        },
        "sources": {
            "snapshot_sha256": bundle.snapshot_sha256,
            "content_facet_npz_sha256": bundle.npz_sha256,
            "content_facet_count": len(bundle.facet_ids),
            "value_vectors": "SEALED (never loaded)",
            "dev1000_byte_pins": dev1000_hashes,
            "receipt_populations": {
                "DEV-100": len(populations.dev100),
                "DEV-500": len(populations.dev500),
                "DEV-500-NEW400": len(populations.new400),
                "DEV-1000-NEW500": len(populations.new500),
            },
        },
        "lexical_index": {
            "terms": len(index.vocabulary),
            "postings": int(index.term_ptr[-1]),
            "documents": index.n_docs,
            "average_document_length": index.avg_doc_length,
            "corpus_sha256": index.corpus_sha256,
            "build_seconds": index_build_seconds,
        },
        "populations": results,
        "falsifier": {
            "text": FALSIFIER,
            "evaluated_on": "DEV-1000-NEW500 (500 unexposed) -- the population the lock used",
            "by_query_normalization": verdict,
            "recall_at_5_raised": raised,
            "verdict": "RAISED" if raised else "NOT RAISED -- the pre-registered falsifier FIRES",
        },
        "cost_note": cost_note(
            timings=all_timings["DEV-1000-NEW500/Q-RAW"], index=index
        ),
        "zero_contact_proof": {
            "registered_contacts": {"frozen_core": 0, "pinned_tool_embedding": 0, "tokenizer": 0},
            "offline_guard": {
                "armed_before_any_input_was_opened": True,
                "outbound_connection_attempts": attempts.count,
                "targets": list(attempts.targets),
            },
            "new_dependencies_installed": 0,
        },
        "wall_seconds": time.perf_counter() - started,
        "scope": (
            "DEV-tier ITERATION design input. This gates a flight and is not one: no knob is "
            "changed, no arm is re-flown, no new sample is touched, no new gold surface is opened, "
            "and FINAL60 and test remain untouched."
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    report = run(repo_root=args.repo_root, data_root=args.data_root)
    payload = json.dumps(report, indent=2, sort_keys=True, default=str)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
