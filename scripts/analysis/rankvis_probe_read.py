#!/usr/bin/env python3
"""rankvis_probe_read.py -- the READ DRIVER for cell RANKVIS, the rank-ordered
rank-visible rendering conversion probe (owner decision 171; the read owed by
root per docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1's own
registered-facts-v1.json, ``read_rule``, written here in KPROBE's shape --
scripts/analysis/slurp_kprobe_read.py -- and CONV's -- scripts/analysis/
slurp_conv_probe_read.py).

WHAT IT MEASURES. Of the 119 TRAIN Fold A rows where the sealed AGREE arm
delivered the gold intent's boundary entry and still answered a wrong intent,
how many move to the gold intent when the delivered boundary and exemplar
blocks are rendered in retrieval-rank order with the rank shown, and nothing
else changes. ``m`` is read against the no-op expectation (15.906 rows, the
error-source read's own null save rates applied to this roster), never
against zero, and beside the 89-row synthesis subset (no-op 11.459).

THE RECIPE (preregistration.md / registered-facts-v1.json ``read_rule``),
followed step by step, refusals honoured before any number is written:

  1. the committed registered facts and roster derivation hash to their own
     pins, and the sealed manifest is COMPLETED at 119 rows with the
     registered id-list hash and this cell's registered config hash (the
     generation plan the flip mints, ``generation-plan-registered-v1.json``,
     is what names the flown attempt and the composed config hash: this
     driver refuses before that file exists, i.e. before the cell is
     flipped);
  2. THE RENDERING GATE, redefined 2026-09-28 (coordinator ruling, Fable 5.1):
     what PROVES a rendering claim is that the rank labels and the
     retrieval-rank order actually appear in the flown requests -- not
     merely that the config declares them. Two parts:
       (a) the registered baseline fragment -- the one byte the flown config
           differs from AGREE's by -- declares the expected
           ``knowledge_value_rendering`` block (order retrieval-rank,
           rank_visible true, the two named stores): a flight composed from
           it renders EVERY value of those stores with the
           ``retrieval rank <r>: `` label, by construction of the merged and
           unit-tested renderer (tests/unit/test_knowledge_value_rendering.py);
       (b) PER ROW and per named store, read directly from the SEALED
           REQUEST RECORDS themselves -- ``<run_id>.trace.jsonl`` (the
           append-only ``core.tracing.TraceSink`` every sealed run already
           writes), one JSON object per line, filtered to
           ``channel == "MODEL_REQUEST"``; ``payload["payload"]`` is the
           exact composed request body the client's transport sent (the
           same sealed artifact and field names
           scripts/slurp_knowledge_index_render_proof.py's ``read_rows`` /
           ``derive_selection`` and scripts/flights/comp1/
           comp1_g5_shared_aa_proof.py's ``contact_key`` read). Locate the
           store's rendered block -- its items in ``supplied_evidence`` /
           ``retrieved_evidence`` whose ``evidence_id`` names that store --
           in the sealed request body of the first contact that carries it,
           and assert (i) every value line of the block carries the
           ``rails.runner.RANK_VISIBLE_LABEL`` rank label, (ii) the labelled
           ranks are exactly ``1..n`` in document order (contiguous and
           strictly increasing), (iii) ``n`` equals the store's delivered
           count in the row's own sealed phase receipt
           (``final_query_state.retrieved_value_ids``, filtered to the
           store). This is the gate's own definition and PASSES on (i)-(iii)
           alone. A stricter, OPTIONAL cross-check for ``train-exemplars``
           recomputes the expected order through the REAL
           ``rails.runner.order_supply_by_retrieval_rank`` (the same
           function ``rails.runner._invoke_native_role_episode`` calls at a
           flight's own supply step, and the same one
           ``analysis.native_episode_dry_run`` now calls) over a sealed
           ``retrieval-rank-inputs`` sidecar this driver reads beside the
           run when one exists (schema below); no flight seals that sidecar
           today, so this leg is reported beside the primary one but never
           required -- its absence no longer refuses the read. Likewise the
           ``intent-boundaries`` seed-equality note (the probe's own sealed
           first-phase seed equals the same row's sealed AGREE seed -- the
           treatment changes no byte of the seed, only the label) is kept
           and reported, but informational only;
     the read refuses -- and writes a refusal receipt, never a conversion
     number -- unless every one of the 119 rows is verified on both stores
     under (b)'s primary rank-label check;
  3. the official scorer already ran ONCE over the complete manifest at
     finalize (``core.scoring_batch``); this driver READS its sealed
     per-sample ``scenario_action_exact`` and never re-runs it;
  4. the comparator (the sealed AGREE arm) is intent-wrong on all 119 rows
     BY CONSTRUCTION (the roster's own definition); the read refuses if the
     sealed official score disagrees on any row;
  5. ``m`` = rows whose probe verdict is exact; there is no reverse count
     (the comparator holds no correct row on this roster to lose);
  6. Wilson score CI95 with the exact Clopper-Pearson CI95 beside it, no
     bootstrap, reported for the full 119 and for the pre-declared 89-row
     synthesis subset;
  7. the four-way transition split (wrong to gold; the reverse, zero by
     construction; the same wrong intent; a different wrong intent), and the
     split by stage (PERCEPTION-DROP / SOLVER-CHOICE / UNPARSED);
  8. the re-declaration arithmetic, STATED and not applied:
     ``(m - 15.906) x 0.092615`` pp intent accuracy, the 43-row threshold, and
     which side of it ``m`` falls.

THE RETRIEVAL-RANK-INPUTS SIDECAR (schema
``saea-rankvis-retrieval-rank-inputs-v1``, this driver's own contract, not
yet sealed by any flight -- RANKVIS has not flown; see the report this
driver's caller returns). OPTIONAL since 2026-09-28: it feeds only the
stricter ``train-exemplars`` cross-check (step 2(b) above), never the
primary rank-label gate, so its absence does not refuse the read. Expected
beside the sealed run at
``<run_dir>/<run_id>.retrieval-rank-inputs.json``::

    {"schema": "saea-rankvis-retrieval-rank-inputs-v1",
     "rows": {"<sample_id>": {"train-exemplars": {
         "snapshot_sha256": "<hex>", "query_state_sha256": "<hex>",
         "ranking_policy_id": "<id>", "fusion_policy_id": "<id>",
         "candidates": [{"facet_id": "<id>", "score": <float>}, ...],
         "supporting_facet_ids": ["<id>", ...],
         "values": [{"value_id": "<id>", "associated_facet_ids": ["<id>", ...]}, ...]
     }}}}

Ids, hashes, policy ids and float scores only -- never a value's text.

MODEL-FREE. Zero model, tokenizer, encoder, embedder, scorer, llama-server
and network contacts; nothing under the sealed run directory is opened for
writing; nothing is written anywhere except under ``--output-root``.

TEXT DISCIPLINE. No utterance text, transcript, gold label string, intent
name, value id content or delivered answer is printed or persisted: sample
ids, store ids, counts, rates and hashes only. Gold and delivered intents
are compared in memory and discarded.

Byte-reproducible apart from ``generated_at_utc``.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/rankvis_probe_read.py \
        --repo-root . --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if not Path(_pkg.__file__).resolve().is_relative_to(SRC.resolve()):
    raise SystemExit(
        f"refusing: the imported package resolves to {_pkg.__file__}, not this checkout's src/"
    )

from speech_aware_evidence_acquisition.rails import controllers as rc  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    FusionDecision,
    RankedFacet,
    RankResult,
)
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    RANK_VISIBLE_LABEL,
    order_supply_by_retrieval_rank,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

DRIVER_ID = "slurp-rankvis-probe-read-v1"
PACKAGE = Path("docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1")
FACTS_RELPATH = PACKAGE / "registered-facts-v1.json"
ROSTER_RELPATH = PACKAGE / "roster-derivation-v1.json"
GENERATION_PLAN_RELPATH = PACKAGE / "generation-plan-registered-v1.json"
FACTS_SCHEMA = "saea-registered-facts-v1"
PROBE_RUN_ID = "SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1"
COMPARATOR_RUN_ID = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
COMPARATOR_ATTEMPT_ID = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
SCORER = "slurp-slu-official-train"
FIELD = "scenario_action_exact"
UNPARSED = "<unparsed>"
Z95 = 1.959963984540054

#: The two stores the registered treatment names, in the order the
#: preregistration lists them.
RANK_VISIBLE_STORES = ("intent-boundaries", "train-exemplars")
#: The store whose order never moves under this key (already rank-ordered by
#: the associated-values fuser); checked by seed equality, not recomputation.
SEED_ORDER_STORE = "intent-boundaries"
#: The store whose order DOES move (today lexicographic); checked by
#: recomputation through the real ``order_supply_by_retrieval_rank``.
REORDERED_STORE = "train-exemplars"
EXPECTED_RENDERING = {
    "schema": "saea-knowledge-value-rendering-v1",
    "order": "retrieval-rank",
    "rank_visible": True,
    "stores": list(RANK_VISIBLE_STORES),
}
RENDERING_SIDECAR_SCHEMA = "saea-rankvis-retrieval-rank-inputs-v1"

#: The sealed run's own append-only request trace (core.tracing.TraceSink);
#: every COMPLETED run writes one. The channel that carries the exact
#: composed request body the client's transport sent.
MODEL_REQUEST_CHANNEL = "MODEL_REQUEST"

#: Derived from rails.runner.RANK_VISIBLE_LABEL ("retrieval rank {rank}: "),
#: never duplicated: split on the one format field and re-escape the two
#: literal halves around a digit capture group.
_RANK_LABEL_PREFIX, _RANK_LABEL_SUFFIX = RANK_VISIBLE_LABEL.split("{rank}")
RANK_LABEL_RE = re.compile(
    re.escape(_RANK_LABEL_PREFIX) + r"(\d+)" + re.escape(_RANK_LABEL_SUFFIX)
)

#: The two payload fields a sealed request's knowledge value blocks travel
#: in (core.model.transport.render_request_with_receipt's own iteration
#: order); only ``supplied_evidence`` is populated by the native SLURP
#: episode this cell reads, but both are checked for the same reason the
#: transport itself checks both.
EVIDENCE_PAYLOAD_FIELDS = ("supplied_evidence", "retrieved_evidence")

#: The 2.5 pp bar is a cross-cell owner constant (decision 133); everything
#: else this driver needs -- the per-row pp headroom, the row threshold, the
#: null save rate by gold-position band and the no-op expectations -- is
#: DERIVED from the registered facts document, never hardcoded here, so this
#: driver is exercised on a synthetic roster of any size (no coincidental
#: agreement with the real 119-row sums is required).
ARM_BAR_PP = 2.5


class ReadRefused(RuntimeError):
    """A recipe gate failed; the read closes without a conversion number."""

    def __init__(self, step: int, message: str) -> None:
        super().__init__(f"step {step}: {message}")
        self.step = step


def digest_file(path: Path) -> str:
    measured = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def id_list_sha256(ids) -> str:
    return digest_text("\n".join(sorted(str(i) for i in ids)))


def _store_of(value_id: str) -> str | None:
    store, sep, _local = value_id.partition("::")
    return store if sep else None


def _store_slice(value_ids, store_id: str) -> tuple[str, ...]:
    return tuple(v for v in value_ids if _store_of(v) == store_id)


# --------------------------------------------------------------------------- intervals


def wilson_ci95(successes: int, trials: int) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("trials must be positive")
    p = successes / trials
    z2 = Z95 * Z95
    denominator = 1.0 + z2 / trials
    centre = (p + z2 / (2.0 * trials)) / denominator
    half = Z95 * math.sqrt(p * (1.0 - p) / trials + z2 / (4.0 * trials * trials)) / denominator
    return max(0.0, centre - half), min(1.0, centre + half)


def _binom_cdf(k: int, n: int, p: float) -> float:
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    total = 0.0
    for i in range(0, k + 1):
        total += math.comb(n, i) * (p**i) * ((1.0 - p) ** (n - i))
    return min(1.0, total)


def _bisect(func, target: float, lo: float = 0.0, hi: float = 1.0, iterations: int = 200) -> float:
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        if func(mid) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def clopper_pearson_ci95(successes: int, trials: int) -> tuple[float, float]:
    alpha = 0.05
    if successes <= 0:
        lower = 0.0
    else:
        lower = _bisect(lambda p: _binom_cdf(successes - 1, trials, p), 1.0 - alpha / 2.0)
    if successes >= trials:
        upper = 1.0
    else:
        upper = _bisect(lambda p: _binom_cdf(successes, trials, p), alpha / 2.0)
    return lower, upper


def rate_block(m: int, n: int, *, no_op_expected: float) -> dict:
    wilson = wilson_ci95(m, n)
    exact = clopper_pearson_ci95(m, n)
    return {
        "estimand": f"m / {n}, rows moved wrong to gold, one binomial proportion over independent rows",
        "m": m,
        "n": n,
        "point": round(m / n, 6),
        "wilson_ci95": [round(wilson[0], 6), round(wilson[1], 6)],
        "clopper_pearson_ci95": [round(exact[0], 6), round(exact[1], 6)],
        "no_bootstrap_because": "the estimand is one binomial proportion, not a paired difference of pooled metrics",
        "no_op_expectation": no_op_expected,
        "m_minus_no_op": round(m - no_op_expected, 6),
        "read_against_no_op_never_zero": True,
    }


def redeclaration_block(
    m: int, *, no_op_expected_full: float, intent_pp_per_row: float, rows_needed_net_of_no_op: int,
) -> dict:
    net = m - no_op_expected_full
    return {
        "stated_not_applied": True,
        "rule": (
            "a later 1,080-row arm with an in-chain A/A declares expected_effect_pp = "
            "(m - no-op) x intent_pp_per_row pp intent accuracy (owner decision 139)"
        ),
        "m": m,
        "no_op_expectation": no_op_expected_full,
        "net_conversions_m_minus_no_op": round(net, 6),
        "intent_pp_per_row": intent_pp_per_row,
        "expected_effect_pp": round(net * intent_pp_per_row, 6),
        "bar_pp": ARM_BAR_PP,
        "rows_needed_net_of_no_op": rows_needed_net_of_no_op,
        "m_clears_the_bar": m >= rows_needed_net_of_no_op,
        "boundary": (
            "a CONDITIONAL rate on a gold-selected TRAIN roster: not a pooled effect, not a "
            "roster-level claim; this cell cannot see harm on rows AGREE answers correctly"
        ),
    }


# --------------------------------------------------------------------------- loaders


def load_facts(repo: Path) -> tuple[dict, str]:
    path = repo / FACTS_RELPATH
    facts = load_json(path)
    if facts.get("schema") != FACTS_SCHEMA:
        raise ReadRefused(0, f"the committed registered facts carry schema {facts.get('schema')!r}, not {FACTS_SCHEMA!r}")
    if str(facts.get("cell", {}).get("run_id")) != PROBE_RUN_ID:
        raise ReadRefused(0, "the committed registered facts do not name this cell's run id")
    return facts, digest_file(path)


def load_roster(repo: Path, facts: dict) -> dict:
    roster_meta = facts["roster"]
    derivation_meta = facts["roster_derivation"]
    path = repo / ROSTER_RELPATH
    sha = digest_file(path)
    if sha != derivation_meta["sha256"]:
        raise ReadRefused(0, "the committed roster derivation does not hash to the registered facts' pin")
    document = load_json(path)
    per_row = document["roster"]["per_row"]
    ids = [str(row["sample_id"]) for row in per_row]
    if len(ids) != int(roster_meta["rows"]) or len(set(ids)) != len(ids):
        raise ReadRefused(0, "the roster derivation does not carry the registered number of distinct ids")
    listed = id_list_sha256(ids)
    if listed != roster_meta["id_list_sha256"] or listed != document["roster"]["id_list_sha256"]:
        raise ReadRefused(0, "the roster id list does not hash to the registered id-list sha256")
    synthesis_meta = facts["synthesis_subset"]
    synthesis_ids = sorted(str(row["sample_id"]) for row in per_row if bool(row.get("in_synthesis_subset")))
    if len(synthesis_ids) != int(synthesis_meta["rows"]):
        raise ReadRefused(0, "the synthesis subset row count does not match the registered facts")
    synthesis_listed = id_list_sha256(synthesis_ids)
    if synthesis_listed != synthesis_meta["id_list_sha256"] or synthesis_listed != document["synthesis_subset"]["id_list_sha256"]:
        raise ReadRefused(0, "the synthesis subset id list does not hash to the registered id-list sha256")
    null_save_rate = {str(k): float(v) for k, v in facts["no_op_expectation"]["null_save_rate"].items()}
    band_by_id = {str(row["sample_id"]): str(row["agree_gold_position_band"]) for row in per_row}
    if set(band_by_id.values()) - set(null_save_rate):
        raise ReadRefused(0, "the roster derivation names a gold-position band the registered facts do not carry a null save rate for")
    primary_by_id = {str(row["sample_id"]): str(row["primary"]) for row in per_row}
    stage_by_id = {str(row["sample_id"]): str(row["stage"]) for row in per_row}
    # A cross-check the recipe reports beside every number: the registered
    # no-op expectation reproduces from the per-row bands, exactly.
    no_op_full = float(facts["no_op_expectation"]["expected_null_conversions"])
    no_op_subset = float(facts["no_op_expectation"]["expected_null_conversions_synthesis_subset"])
    recomputed_full = sum(null_save_rate[band_by_id[i]] for i in ids)
    recomputed_subset = sum(null_save_rate[band_by_id[i]] for i in synthesis_ids)
    if abs(recomputed_full - no_op_full) > 1e-6:
        raise ReadRefused(0, "the roster's per-row gold-position bands do not reproduce the registered no-op expectation")
    if abs(recomputed_subset - no_op_subset) > 1e-6:
        raise ReadRefused(0, "the synthesis subset's per-row gold-position bands do not reproduce its registered no-op expectation")
    re_decl = facts["re_declaration_rule"]
    return {
        "relpath": str(ROSTER_RELPATH).replace("\\", "/"),
        "sha256": sha,
        "ids": sorted(ids),
        "id_list_sha256": listed,
        "split_identity_hash": document["roster"]["split_identity_hash"],
        "synthesis_subset_ids": synthesis_ids,
        "band_by_id": band_by_id,
        "primary_by_id": primary_by_id,
        "stage_by_id": stage_by_id,
        "no_op_expected_full": no_op_full,
        "no_op_expected_subset": no_op_subset,
        "intent_pp_per_row": float(re_decl["pp_per_row"]),
        "rows_needed_net_of_no_op": int(re_decl["m_needed_for_the_2p5_pp_bar"]),
    }


def load_generation_plan(repo: Path) -> dict:
    path = repo / GENERATION_PLAN_RELPATH
    if not path.is_file():
        raise ReadRefused(
            0,
            "no generation-plan-registered-v1.json: this cell has not been flipped "
            "(scripts/flights/repin_cell.py --set-ready) yet, so there is no flown attempt to read",
        )
    plan = load_json(path)
    # The registered generation plan nests the attempt identity under execution_plan (the
    # contracts.ExecutionPlan record); a top-level attempt_id is accepted only if it agrees.
    nested = (plan.get("execution_plan") or {}).get("attempt_id")
    top = plan.get("attempt_id")
    if top and nested and top != nested:
        raise ReadRefused(0, "the generation plan names two different attempt ids")
    if top or nested:
        plan = dict(plan, attempt_id=top or nested)
    for key in ("composed_config_hash", "attempt_id"):
        if not plan.get(key):
            raise ReadRefused(0, f"the generation plan carries no {key!r}")
    return plan


def load_baseline_rendering(repo: Path, facts: dict) -> dict:
    relpath = Path(str(facts["cell"]["baseline"]))
    path = repo / relpath
    sha = digest_file(path)
    baseline = load_json(path)
    repin_pin = None
    if sha != facts["cell"]["baseline_sha256"]:
        # The flip (scripts/flights/repin_cell.py --set-ready) adds exactly one key to the fragment,
        # the prepared_phase_supply pin, after the facts were registered. Accept the fragment only if
        # dropping that one key re-serialises (indent 2, trailing newline) to the registered bytes;
        # the flown bytes stay bound by the manifest's config hash against the generation plan.
        pin = baseline.get("prepared_phase_supply")
        stripped = {k: v for k, v in baseline.items() if k != "prepared_phase_supply"}
        restored = (json.dumps(stripped, indent=2, ensure_ascii=False) + chr(10)).encode("utf-8")
        if not isinstance(pin, dict) or hashlib.sha256(restored).hexdigest() != facts["cell"]["baseline_sha256"]:
            raise ReadRefused(1, "the committed baseline fragment does not hash to the registered facts' pin")
        repin_pin = pin
    rendering = (baseline.get("native_episode") or {}).get("knowledge_value_rendering")
    if rendering != EXPECTED_RENDERING:
        raise ReadRefused(
            1,
            "the registered baseline fragment does not declare the expected knowledge_value_rendering "
            "block: the flown requests would not carry the rank labels",
        )
    return {
        "relpath": str(relpath).replace("\\", "/"), "sha256": sha, "rendering": rendering,
        "registered_sha256": facts["cell"]["baseline_sha256"], "flip_added_prepared_phase_supply": repin_pin,
    }


def load_probe(data_root: Path, facts: dict, roster: dict, plan: dict) -> dict:
    run_id = str(facts["cell"]["run_id"])
    attempt_id = str(plan["attempt_id"])
    run_dir = data_root / "runs" / run_id / attempt_id
    if not run_dir.is_dir():
        raise ReadRefused(1, f"no sealed attempt directory for {run_id}/{attempt_id}")
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("status") != "COMPLETED":
        raise ReadRefused(1, f"the sealed manifest is {manifest.get('status')!r}, not COMPLETED")
    if manifest.get("run_id") != run_id or (manifest.get("attempt") or {}).get("attempt_id") != attempt_id:
        raise ReadRefused(1, "the sealed manifest does not name this run and attempt")
    split = manifest["split"]
    if int(split["count"]) != len(roster["ids"]) or len(split["ids"]) != len(roster["ids"]):
        raise ReadRefused(1, f"the sealed manifest carries {split['count']} rows, not {len(roster['ids'])}")
    if id_list_sha256(split["ids"]) != roster["id_list_sha256"]:
        raise ReadRefused(1, "the sealed manifest's id list does not hash to the committed roster's")
    if split.get("identity_hash") != roster["split_identity_hash"]:
        raise ReadRefused(1, "the sealed manifest's split identity is not the committed roster's")
    if manifest.get("study_repo_dirt"):
        raise ReadRefused(1, "the sealed manifest records a dirty study tree")
    flown_config = (manifest.get("config") or {}).get("config_hash")
    if flown_config != plan["composed_config_hash"]:
        raise ReadRefused(1, "the sealed manifest's config hash is not the registered generation plan's")

    attempt_path = data_root / "attempts" / run_id / f"{attempt_id}.json"
    attempt = load_json(attempt_path)
    if attempt.get("state") != "FINALIZED":
        raise ReadRefused(1, f"the attempt record is {attempt.get('state')!r}, not FINALIZED")

    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    scores_path = run_dir / f"{run_id}.scores.json"
    phases_path = run_dir / f"{run_id}.phases.json"
    hashes = {
        "run_manifest": digest_file(manifest_path),
        "outputs": digest_file(outputs_path),
        "scores": digest_file(scores_path),
        "phases": digest_file(phases_path),
        "attempt_record": digest_file(attempt_path),
    }
    if hashes["outputs"] != manifest["outputs"]["sha256"]:
        raise ReadRefused(1, "the outputs file does not hash to the manifest's pin")
    if hashes["scores"] != manifest["scores"]["sha256"]:
        raise ReadRefused(1, "the scores file does not hash to the manifest's pin")

    jobs_path = run_dir / "score-jobs.jsonl"
    summary_path = run_dir / "score-batch" / "batch-summary.json"
    jobs = [json.loads(line) for line in jobs_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    summary = load_json(summary_path)
    if len(jobs) != 1 or int(summary.get("job_count", 0)) != 1 or int(summary.get("succeeded", 0)) != 1:
        raise ReadRefused(3, "the sealed attempt does not carry exactly one succeeded official scoring job")
    job = summary["jobs"][0]
    score_result_path = run_dir / "score-batch" / str(job["result_file"])
    if digest_file(score_result_path) != job["result_sha256"]:
        raise ReadRefused(3, "the official scoring result does not hash to the batch summary's pin")
    if SCORER not in manifest.get("scorers", []):
        raise ReadRefused(3, f"the sealed manifest does not name the {SCORER} scorer")

    scores = load_json(scores_path)
    block = scores[SCORER]
    per_sample = {str(row["sample_id"]): row for row in block["per_sample"]}
    if sorted(per_sample) != roster["ids"]:
        raise ReadRefused(3, "the official per-sample id set is not the committed roster")
    if int(block["aggregate"]["samples"]) != len(roster["ids"]):
        raise ReadRefused(3, "the official aggregate does not count the roster")
    mean_exact = sum(float(r[FIELD]) for r in per_sample.values()) / len(per_sample)
    official_intent = float(block["aggregate"]["official"]["intent_accuracy"])
    if abs(mean_exact - official_intent) > 1e-9:
        raise ReadRefused(3, "the per-sample scenario_action_exact mean does not reproduce the official intent accuracy")

    outputs: dict[str, dict] = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            outputs[str(record["sample_id"])] = record
    if sorted(outputs) != roster["ids"]:
        raise ReadRefused(1, "the outputs file's id set is not the committed roster")

    phases_doc = load_json(phases_path)
    if phases_doc.get("schema") != "saea-flight-phase-summaries-v1":
        raise ReadRefused(2, "unexpected phase artefact schema")
    results = {str(r["sample_id"]): r for r in phases_doc["phases"][0]["results"]}
    if sorted(results) != roster["ids"]:
        raise ReadRefused(2, "the phase artefact's result rows are not the committed roster")

    return {
        "run_id": run_id,
        "attempt_id": attempt_id,
        "run_dir": run_dir,
        "manifest": manifest,
        "attempt": attempt,
        "scores_block": block,
        "per_sample": per_sample,
        "outputs": outputs,
        "phase_results": results,
        "hashes": hashes,
        "score_job": {
            "job_id": job["job_id"], "status": job["status"],
            "result_file": job["result_file"], "result_sha256": job["result_sha256"],
        },
    }


def load_comparator(data_root: Path, roster: dict) -> dict:
    run_id, attempt_id = COMPARATOR_RUN_ID, COMPARATOR_ATTEMPT_ID
    run_dir = data_root / "runs" / run_id / attempt_id
    manifest_path = run_dir / f"{run_id}.run-manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("status") != "COMPLETED":
        raise ReadRefused(4, "the sealed comparator manifest is not COMPLETED")
    scores_path = run_dir / f"{run_id}.scores.json"
    outputs_path = run_dir / f"{run_id}.outputs.jsonl"
    phases_path = run_dir / f"{run_id}.phases.json"
    hashes = {
        "run_manifest": digest_file(manifest_path),
        "scores": digest_file(scores_path),
        "outputs": digest_file(outputs_path),
        "phases": digest_file(phases_path),
    }
    if hashes["scores"] != manifest["scores"]["sha256"] or hashes["outputs"] != manifest["outputs"]["sha256"]:
        raise ReadRefused(4, "the comparator's sealed files do not hash to its manifest's pins")
    block = load_json(scores_path)[SCORER]
    wanted = set(roster["ids"])
    per_sample = {str(r["sample_id"]): r for r in block["per_sample"] if str(r["sample_id"]) in wanted}
    if sorted(per_sample) != sorted(wanted):
        raise ReadRefused(4, "the comparator's official per-sample rows do not cover the probe roster")
    wrong = [sid for sid, row in per_sample.items() if float(row[FIELD]) >= 0.5]
    if wrong:
        raise ReadRefused(
            4, f"{len(wrong)} comparator row(s) are intent-CORRECT, not intent-wrong as registered"
        )
    outputs: dict[str, dict] = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            sample_id = str(record.get("sample_id"))
            if sample_id in wanted:
                outputs[sample_id] = {"text": record.get("text") or ""}
    if sorted(outputs) != sorted(wanted):
        raise ReadRefused(4, "the comparator's outputs do not cover the probe roster")
    phases_doc = load_json(phases_path)
    results = {str(r["sample_id"]): r for r in phases_doc["phases"][0]["results"]}
    if not wanted <= set(results):
        raise ReadRefused(4, "the comparator's phase artefact does not cover the probe roster")
    initial_boundary_ids: dict[str, tuple[str, ...]] = {}
    exemplar_ids: dict[str, tuple[str, ...]] = {}
    for sample_id in roster["ids"]:
        result = results[sample_id]
        initial_ids = tuple(result["initial_query_state"]["retrieved_value_ids"])
        final_ids = tuple(result["final_query_state"]["retrieved_value_ids"])
        initial_boundary_ids[sample_id] = _store_slice(initial_ids, SEED_ORDER_STORE)
        exemplar_ids[sample_id] = _store_slice(final_ids, REORDERED_STORE)
    return {
        "run_id": run_id, "attempt_id": attempt_id, "hashes": hashes,
        "per_sample": per_sample, "outputs": outputs,
        "initial_boundary_value_ids": initial_boundary_ids,
        "exemplar_value_ids": exemplar_ids,
    }


def load_retrieval_rank_inputs(run_dir: Path, run_id: str) -> dict | None:
    """The optional sidecar the rendering gate's train-exemplars leg needs
    (module docstring). None when absent -- which is every sealed run today,
    since RANKVIS has not flown and no flight yet seals it."""

    path = run_dir / f"{run_id}.retrieval-rank-inputs.json"
    if not path.is_file():
        return None
    document = load_json(path)
    if document.get("schema") != RENDERING_SIDECAR_SCHEMA:
        raise ReadRefused(2, f"the retrieval-rank-inputs sidecar carries an unexpected schema {document.get('schema')!r}")
    return document.get("rows") or {}


def load_sealed_model_requests(run_dir: Path, run_id: str) -> dict[str, list[dict]]:
    """Every row's sealed MODEL_REQUEST contacts, in the flown trace's own
    order -- the rendering gate's primary evidence (module docstring step
    2(b)).

    Reads the sealed run's own append-only ``<run_id>.trace.jsonl``
    (``core.tracing.TraceSink``), one JSON object per line, filtered to
    ``channel == "MODEL_REQUEST"``. Each such record's shape is
    ``{"channel": ..., "record_id": ..., "payload": {"arm": ..., "payload":
    <the composed request body>, "payload_sha256": ...}}``
    (``core.model.adapter``'s own emit call) -- this is the exact technique
    scripts/slurp_knowledge_index_render_proof.py's ``read_rows`` and
    scripts/flights/comp1/comp1_g5_shared_aa_proof.py's ``contact_key``/
    ``role_of`` use to read a sealed run's own requests back. Grouped by
    ``sample_id``, contacts kept in file (visit) order per row.

    Every COMPLETED run writes this file; its absence is a real refusal, not
    an optional leg. Text discipline: only ids, counts and the rank-label
    prefix are ever read out of a payload here (:func:`rank_label_report`);
    a value's ``content`` string is matched against a regex and discarded,
    never returned or logged.
    """

    path = run_dir / f"{run_id}.trace.jsonl"
    if not path.is_file():
        raise ReadRefused(
            2, f"no sealed trace file for {run_id}: cannot verify the rendering gate "
            "from the flown requests"
        )
    by_sample: dict[str, list[dict]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("channel") != MODEL_REQUEST_CHANNEL:
                continue
            envelope = record.get("payload")
            if not isinstance(envelope, dict):
                continue
            payload = envelope.get("payload")
            if not isinstance(payload, dict):
                continue
            sample_id = str(payload.get("sample_id"))
            by_sample.setdefault(sample_id, []).append(payload)
    return by_sample


def rank_label_report(contacts: list[dict], store_id: str, delivered_count: int) -> dict:
    """(i)-(iii) of the rendering gate's primary check (module docstring step
    2(b)), for one row and one store.

    ``contacts`` is that row's own sealed MODEL_REQUEST payloads, in trace
    order (:func:`load_sealed_model_requests`). The first contact carrying
    ANY item of ``store_id`` in ``supplied_evidence``/``retrieved_evidence``
    is where the store's block is rendered; its items, taken in the document
    order they appear in those fields (the same field order
    ``core.model.transport`` itself iterates), are checked: every one must
    carry the ``rails.runner.RANK_VISIBLE_LABEL`` rank label (i), the
    labelled ranks must read exactly ``1..n`` in that order -- contiguous
    AND strictly increasing are both implied by an exact match against
    ``range(1, n + 1)`` (ii), and ``n`` must equal ``delivered_count``, the
    store's own count in the row's sealed phase receipt (iii).

    Never raises. Returns counts and booleans only -- no value content is
    read out of this function.
    """

    items: list[dict] = []
    for contact in contacts:
        found = [
            item
            for field in EVIDENCE_PAYLOAD_FIELDS
            for item in (contact.get(field) or ())
            if _store_of(str(item.get("evidence_id", ""))) == store_id
        ]
        if found:
            items = found
            break

    if not items:
        return {
            "contact_found": False,
            "rendered_count": 0,
            "unlabelled_count": 0,
            "ranks_ok": delivered_count == 0,
            "count_matches_receipt": delivered_count == 0,
            "delivered_count": delivered_count,
            "verified": delivered_count == 0,
        }

    ranks: list[int] = []
    unlabelled = 0
    for item in items:
        match = RANK_LABEL_RE.match(str(item.get("content", "")))
        if match:
            ranks.append(int(match.group(1)))
        else:
            unlabelled += 1
    ranks_ok = unlabelled == 0 and ranks == list(range(1, len(items) + 1))
    count_matches_receipt = len(items) == delivered_count
    return {
        "contact_found": True,
        "rendered_count": len(items),
        "unlabelled_count": unlabelled,
        "ranks_ok": ranks_ok,
        "count_matches_receipt": count_matches_receipt,
        "delivered_count": delivered_count,
        "verified": ranks_ok and count_matches_receipt,
    }


def _recomputed_exemplar_order(row_inputs: dict, selected_ids: tuple[str, ...]) -> tuple[str, ...]:
    """The real rails.runner.order_supply_by_retrieval_rank over one row's
    sealed retrieval-rank inputs -- reused, never re-implemented."""

    from types import SimpleNamespace

    snapshot_sha256 = str(row_inputs["snapshot_sha256"])
    query_state_sha256 = str(row_inputs["query_state_sha256"])
    rank_result = RankResult(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state_sha256,
        ranking_policy_id=str(row_inputs["ranking_policy_id"]),
        candidates=tuple(
            RankedFacet(facet_id=str(c["facet_id"]), score=float(c["score"]))
            for c in row_inputs["candidates"]
        ),
    ).validate()
    fusion_decision = FusionDecision(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state_sha256,
        rank_result_sha256=rank_result.content_hash(),
        fusion_policy_id=str(row_inputs["fusion_policy_id"]),
        supporting_facet_ids=tuple(str(f) for f in row_inputs["supporting_facet_ids"]),
        selected_value_ids=tuple(selected_ids),
    ).validate()
    supply = rc.PhaseSupply(
        rank_result=rank_result, fusion_decision=fusion_decision,
        action_target_ref="rankvis-probe-read-retrieval-rank-inputs-v1",
    ).validate()
    snapshot = SimpleNamespace(
        values=tuple(
            SimpleNamespace(
                value_id=str(v["value_id"]),
                associated_facet_ids=tuple(str(f) for f in v["associated_facet_ids"]),
            )
            for v in row_inputs["values"]
        )
    )
    reordered = order_supply_by_retrieval_rank(supply, snapshot, (REORDERED_STORE,))
    return tuple(reordered.fusion_decision.selected_value_ids)


# --------------------------------------------------------------------------- the rendering gate


def rendering_gate(
    roster: dict, probe: dict, comparator: dict, rank_inputs: dict | None,
    sealed_requests: dict[str, list[dict]] | None,
) -> dict:
    """Step 2 of the recipe, redefined 2026-09-28 (module docstring). Returns
    a report; never raises by itself -- the caller (``run``) turns an
    incomplete report into a refusal, so the report itself carries the count
    of rows verified either way.

    PRIMARY, required for ``all_rows_verified``: :func:`rank_label_report`
    on both :data:`RANK_VISIBLE_STORES`, read from ``sealed_requests`` (one
    row's own MODEL_REQUEST contacts, :func:`load_sealed_model_requests`) --
    the rank labels and the retrieval-rank order as they actually appear in
    the flown requests.

    INFORMATIONAL ONLY, reported beside the primary check but never folded
    into ``all_rows_verified``:
      * ``intent-boundaries``: the pre-RANKVIS seed-equality note (the
        probe's own sealed first-phase seed order equals the comparator's --
        the treatment changes no byte of the seed, only the label);
      * ``train-exemplars``: the OPTIONAL, stricter sidecar-based
        recomputation through the real ``order_supply_by_retrieval_rank`` --
        reported only when the sidecar is sealed beside the run; every
        sealed run today carries none (RANKVIS has not flown one), so this
        leg is silent by construction and no longer refuses the read.
    """

    seed_verified: list[str] = []
    seed_mismatched: list[str] = []
    sidecar_verified: list[str] = []
    sidecar_mismatched: list[str] = []
    sidecar_set_mismatched: list[str] = []
    sidecar_unverifiable: list[str] = []
    rank_verified: dict[str, list[str]] = {store: [] for store in RANK_VISIBLE_STORES}
    rank_failed: dict[str, list[str]] = {store: [] for store in RANK_VISIBLE_STORES}

    for sample_id in roster["ids"]:
        result = probe["phase_results"][sample_id]
        probe_initial = tuple(result["initial_query_state"]["retrieved_value_ids"])
        probe_final = tuple(result["final_query_state"]["retrieved_value_ids"])

        probe_seed = _store_slice(probe_initial, SEED_ORDER_STORE)
        if probe_seed == comparator["initial_boundary_value_ids"][sample_id]:
            seed_verified.append(sample_id)
        else:
            seed_mismatched.append(sample_id)

        probe_exemplars = _store_slice(probe_final, REORDERED_STORE)
        comparator_exemplars = comparator["exemplar_value_ids"][sample_id]
        if set(probe_exemplars) != set(comparator_exemplars):
            sidecar_set_mismatched.append(sample_id)
        else:
            row_inputs = (rank_inputs or {}).get(sample_id, {}).get(REORDERED_STORE)
            if row_inputs is None:
                sidecar_unverifiable.append(sample_id)
            else:
                expected = _recomputed_exemplar_order(row_inputs, probe_exemplars)
                if expected == probe_exemplars:
                    sidecar_verified.append(sample_id)
                else:
                    sidecar_mismatched.append(sample_id)

        contacts = (sealed_requests or {}).get(sample_id, [])
        for store in RANK_VISIBLE_STORES:
            delivered_count = len(_store_slice(probe_final, store))
            report = rank_label_report(contacts, store, delivered_count)
            (rank_verified if report["verified"] else rank_failed)[store].append(sample_id)

    n = len(roster["ids"])
    stores_block: dict[str, dict] = {}
    for store in RANK_VISIBLE_STORES:
        stores_block[store] = {
            "method": (
                "rank labels parsed from the sealed MODEL_REQUEST records themselves "
                "(rails.runner.RANK_VISIBLE_LABEL): every value line labelled, ranks "
                "1..n contiguous and strictly increasing in document order, count "
                "equal to the store's delivered count in the sealed phase receipt"
            ),
            "rows_verified": len(rank_verified[store]),
            "rows_failed": len(rank_failed[store]),
            "failed_rows": [
                {"sample_id": sample_id, "store": store} for sample_id in rank_failed[store]
            ],
        }
    stores_block[SEED_ORDER_STORE]["seed_equality_note"] = {
        "informational_only": True,
        "method": "the probe's own sealed first-phase seed order equals the comparator's (never reorders under this key)",
        "rows_verified": len(seed_verified),
        "rows_mismatched": len(seed_mismatched),
    }
    stores_block[REORDERED_STORE]["sidecar_stricter_check"] = {
        "informational_only": True,
        "optional": True,
        "method": "rails.runner.order_supply_by_retrieval_rank over the sealed retrieval-rank-inputs sidecar, when sealed",
        "sidecar_present": rank_inputs is not None,
        "rows_verified": len(sidecar_verified),
        "rows_set_mismatched": len(sidecar_set_mismatched),
        "rows_order_mismatched": len(sidecar_mismatched),
        "rows_unverifiable_no_sidecar_row": len(sidecar_unverifiable),
    }

    all_verified = all(stores_block[store]["rows_verified"] == n for store in RANK_VISIBLE_STORES)
    return {
        "expected_rendering": EXPECTED_RENDERING,
        "labels_guaranteed_by_baseline_config": True,
        "rows_total": n,
        "stores": stores_block,
        "all_rows_verified": all_verified,
    }


# --------------------------------------------------------------------------- the conversion contrast


def parsed_intent(text: str) -> str:
    scenario, action, _entities, parsed = parse_slu_response(text or "")
    if parsed and isinstance(scenario, str) and isinstance(action, str):
        return f"{scenario}_{action}"
    return UNPARSED


def contrast(ids: list[str], probe: dict, comparator: dict) -> dict:
    per_row: list[dict] = []
    classes: Counter = Counter()
    for sample_id in ids:
        probe_exact = float(probe["per_sample"][sample_id][FIELD]) >= 0.5
        probe_text = str(probe["outputs"][sample_id].get("text") or "")
        comparator_text = str(comparator["outputs"][sample_id]["text"])
        probe_intent = parsed_intent(probe_text)
        comparator_intent = parsed_intent(comparator_text)
        if probe_exact:
            transition = "wrong-to-gold"
        elif probe_intent == comparator_intent:
            transition = "unchanged-wrong"
        else:
            transition = "different-wrong"
        classes[transition] += 1
        per_row.append({
            "sample_id": sample_id, "probe_intent_exact": probe_exact, "transition": transition,
        })
    m = classes["wrong-to-gold"]
    n = len(ids)
    return {
        "rows": n,
        "m_wrong_to_gold": m,
        "r_gold_to_wrong": 0,
        "r_is_zero_by_construction": "the comparator holds no correct row on this roster to lose",
        "four_way_split": {
            "wrong_to_gold": m, "gold_to_wrong": 0,
            "same_wrong_intent": classes["unchanged-wrong"],
            "different_wrong_intent": classes["different-wrong"],
        },
        "per_row": per_row,
    }


def by_stage_block(ids: list[str], contrast_rows: dict, roster: dict) -> dict:
    by_row = {row["sample_id"]: row for row in contrast_rows["per_row"]}
    stages: dict[str, Counter] = {}
    for sample_id in ids:
        stage = roster["stage_by_id"][sample_id]
        stages.setdefault(stage, Counter())["rows"] += 1
        if by_row[sample_id]["probe_intent_exact"]:
            stages[stage]["m"] += 1
    return {
        stage: {"rows": counts["rows"], "m": counts["m"]}
        for stage, counts in sorted(stages.items())
    }


# --------------------------------------------------------------------------- rendering


def fmt_ci(bounds: list[float]) -> str:
    return f"[{100 * bounds[0]:.2f} %, {100 * bounds[1]:.2f} %]"


def render_markdown(result: dict) -> str:
    c = result["contrast"]
    rate = result["rate"]
    subset_rate = result["subset_rate"]
    g = result["rendering_gate"]
    r = result["redeclaration"]
    store_names = list(g["stores"])
    lines = [
        f"# Cell RANKVIS read: m = {c['m_wrong_to_gold']} of {c['rows']}",
        "",
        f"Generated {result['generated_at_utc']}; driver `{result['driver']['relpath']}` "
        f"sha256 `{result['driver']['sha256']}`.",
        "",
        "## Rendering gate",
        "",
        "| store | method | rows verified / total |",
        "| --- | --- | ---: |",
        f"| {store_names[0]} | {g['stores'][store_names[0]]['method']} | "
        f"{g['stores'][store_names[0]]['rows_verified']} / {g['rows_total']} |",
        f"| {store_names[1]} | {g['stores'][store_names[1]]['method']} | "
        f"{g['stores'][store_names[1]]['rows_verified']} / {g['rows_total']} |",
        "",
        f"All rows verified: **{g['all_rows_verified']}**.",
        "",
        "## The number",
        "",
        "| quantity | value |",
        "| --- | ---: |",
        f"| m, rows moved wrong to gold (of {rate['n']}) | **{rate['m']}** |",
        f"| Wilson CI95 | {fmt_ci(rate['wilson_ci95'])} |",
        f"| Clopper-Pearson CI95 (exact) | {fmt_ci(rate['clopper_pearson_ci95'])} |",
        f"| no-op expectation (never zero) | {rate['no_op_expectation']:.3f} |",
        f"| m - no-op | {rate['m_minus_no_op']:.3f} |",
        "",
        f"Synthesis subset (n = {subset_rate['n']}): m = {subset_rate['m']}, "
        f"Wilson {fmt_ci(subset_rate['wilson_ci95'])}, no-op expectation {subset_rate['no_op_expectation']:.3f}.",
        "",
        "## Four-way split",
        "",
        "| transition | rows |",
        "| --- | ---: |",
        f"| wrong to gold (m) | {c['four_way_split']['wrong_to_gold']} |",
        f"| gold to wrong (zero by construction) | {c['four_way_split']['gold_to_wrong']} |",
        f"| the same wrong intent | {c['four_way_split']['same_wrong_intent']} |",
        f"| a different wrong intent | {c['four_way_split']['different_wrong_intent']} |",
        "",
        "## By stage",
        "",
        "| stage | rows | m |",
        "| --- | ---: | ---: |",
    ]
    for stage, counts in result["by_stage"].items():
        lines.append(f"| {stage} | {counts['rows']} | {counts['m']} |")
    lines += [
        "",
        "## Re-declaration arithmetic, stated and not applied",
        "",
        f"expected_effect_pp = (m - no-op) x 0.092615 = **{r['expected_effect_pp']} pp**; "
        f"clears the {r['bar_pp']} pp bar at m >= {r['rows_needed_net_of_no_op']} net of the no-op: "
        f"**{r['m_clears_the_bar']}**.",
        "",
        r["boundary"],
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- main


def run(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()
    generated = datetime.now(timezone.utc).isoformat()
    driver = {
        # Relative to REPO_ROOT (this file's own checkout), not --repo-root:
        # a synthetic --repo-root used to unit-test this driver against a
        # fixture tree is not where rankvis_probe_read.py itself lives.
        "relpath": str(Path(__file__).resolve().relative_to(REPO_ROOT)).replace("\\", "/"),
        "sha256": digest_file(Path(__file__)),
    }
    facts, facts_sha = load_facts(repo)
    output_root = (
        Path(args.output_root) if args.output_root
        else data_root / "analysis" / f"{PROBE_RUN_ID}-READ-V1"
    )
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        roster = load_roster(repo, facts)
        plan = load_generation_plan(repo)
        load_baseline_rendering(repo, facts)
        probe = load_probe(data_root, facts, roster, plan)
        comparator = load_comparator(data_root, roster)
        rank_inputs = load_retrieval_rank_inputs(probe["run_dir"], probe["run_id"])
        sealed_requests = load_sealed_model_requests(probe["run_dir"], probe["run_id"])
        gate = rendering_gate(roster, probe, comparator, rank_inputs, sealed_requests)
        if not gate["all_rows_verified"]:
            raise ReadRefused(
                2,
                "the rendering gate did not verify every row on both configured stores "
                f"({json.dumps(gate['stores'], sort_keys=True)}); no conversion number is produced",
            )
        contrast_block = contrast(roster["ids"], probe, comparator)
    except ReadRefused as refused:
        receipt = {
            "schema": "saea-rankvis-read-refusal-v1",
            "driver": driver,
            "generated_at_utc": generated,
            "facts_sha256": facts_sha,
            "refused_at_step": refused.step,
            "reason": str(refused),
            "conversion_number_written": False,
            "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0, "server": 0, "network": 0},
        }
        path = output_root / "refusal-v1.json"
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"READ REFUSED at {refused}", file=sys.stderr)
        print(f"refusal receipt: {path}", file=sys.stderr)
        return 2

    ids = roster["ids"]
    subset_ids = roster["synthesis_subset_ids"]
    m_full = contrast_block["m_wrong_to_gold"]
    subset_rows = [row for row in contrast_block["per_row"] if row["sample_id"] in set(subset_ids)]
    m_subset = sum(1 for row in subset_rows if row["probe_intent_exact"])

    result = {
        "schema": "saea-rankvis-read-v1",
        "driver": driver,
        "generated_at_utc": generated,
        "facts": {"relpath": str(FACTS_RELPATH).replace("\\", "/"), "sha256": facts_sha},
        "roster": {
            k: v for k, v in roster.items()
            if k not in ("ids", "synthesis_subset_ids", "band_by_id", "primary_by_id", "stage_by_id")
        },
        "probe": {
            "run_id": probe["run_id"], "attempt_id": probe["attempt_id"],
            "manifest_status": probe["manifest"]["status"], "attempt_state": probe["attempt"]["state"],
            "study_commit": probe["manifest"].get("study_commit"), "hashes": probe["hashes"],
        },
        "comparator": {
            "run_id": comparator["run_id"], "attempt_id": comparator["attempt_id"], "hashes": comparator["hashes"],
        },
        "rendering_gate": gate,
        "contrast": contrast_block,
        "rate": rate_block(m_full, len(ids), no_op_expected=roster["no_op_expected_full"]),
        "subset_rate": rate_block(m_subset, len(subset_ids), no_op_expected=roster["no_op_expected_subset"]),
        "by_stage": by_stage_block(ids, contrast_block, roster),
        "redeclaration": redeclaration_block(
            m_full,
            no_op_expected_full=roster["no_op_expected_full"],
            intent_pp_per_row=roster["intent_pp_per_row"],
            rows_needed_net_of_no_op=roster["rows_needed_net_of_no_op"],
        ),
        "boundary": (
            "A development read on a TRAIN construction fold: never a test claim, never a "
            "generalisation claim. SELECTED USING GOLD, OFFLINE: a conditional rate only, no "
            "pooled or roster-level claim. This cell cannot see harm on rows AGREE answers correctly."
        ),
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "scorer": 0, "server": 0, "network": 0},
    }
    json_path = output_root / "read-v1.json"
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown = render_markdown(result)
    md_path = output_root / "read-v1.md"
    md_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"read-v1.json sha256 {digest_file(json_path)}")
    print(f"read-v1.md sha256 {digest_file(md_path)}")
    print(f"written under {output_root}")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output-root", default=None, help="defaults to analysis/<run-id>-READ-V1 under --data-root")
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_arg_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
