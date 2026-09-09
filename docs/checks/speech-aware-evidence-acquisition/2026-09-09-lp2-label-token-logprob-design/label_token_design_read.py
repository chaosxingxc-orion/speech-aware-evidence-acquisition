#!/usr/bin/env python3
"""The LP-2 DESIGN read: what the label-token judge would have flagged.

Exposure row ``SAEA-SLURP-MF-LP2-DESIGN-V1``, ``model-free-check``, registered
before this script opened a single sealed byte. **Zero contacts of every
kind**: no model, GPU, server, socket, tokenizer, tool, embedder, retriever or
network; no waveform is decoded and no MP3 is opened.

**Every number this script prints is a DESIGN READ, and none of them is a
result.** The judge's threshold was fixed from exactly these 1,000 sealed rows
-- it is the value that flags 86 of them, quoted from the predecessor's own
committed receipt -- so measuring the judge here measures a rule against the
data that chose it. That is a legitimate way to DESIGN a rule and an
illegitimate way to DECIDE one. The decision belongs to
``docs/readiness/2026-09-09-slurp-label-token-logprob-judge-lp2-v1-
preregistration.md``, which sends it to a fresh replicate of the same cell.

What it does, in order:

1. **Reproduces the predecessor's alignment.** For all 1,000 rows it computes
   the two intent-span statistics twice -- once through the registered judge
   ``core.judges.SlurpIntentTokenLogprobJudge.statistics``, once through
   ``scripts/slurp_logprob_judge_read.py::row_confidence``, the read that was
   written and unit-tested BEFORE the probe flew -- and refuses unless they
   agree to the last bit on every row. Two implementations of one alignment is
   exactly the drift the engineering base rule forbids; this is the proof they
   are one alignment.
2. **Re-derives the frozen thresholds** as the values that flag 86 rows, ties
   at the boundary included, and refuses unless they equal the constants the
   judge ships.
3. **Runs the REGISTERED judge** over all 1,000 rows at those frozen
   thresholds -- the real ``JUDGES`` entry, through the real ``Judge``
   protocol, on the real sealed record -- and measures precision and recall of
   its flags against this arm's own official intent errors.
4. Measures the same for the free **legality judge** recomputed on this arm,
   for their **union**, and for the predecessor's failed whole-answer flag, so
   the successor is priced against what it would replace.
5. Reports the **precision-recall curve** of each statistic, whole, and the
   speaker-clustered CI90 of every quantity the preregistered rule turns on.

Usage (WSL2)::

    python docs/checks/speech-aware-evidence-acquisition/\
2026-09-09-lp2-label-token-logprob-design/label_token_design_read.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]

SEED = 20260909
N_REPLICATES = 10_000
CI_LEVEL = 0.90

#: The predecessor's flag budget, carried over unchanged so the successor is
#: read at the operating point the failed rule was read at.
FLAG_BUDGET = 86

#: The sealed inputs. The first two are the probe arm's own run directory; the
#: last three are the read products that arm's own registered read produced and
#: whose sha256 its committed receipt already carries.
RUN_DIR = Path(
    "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs"
    "/SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1/attempt-20260909T052142Z-07ca9c"
)
SCRATCH = Path(
    "/mnt/c/Users/35686/AppData/Local/Temp/claude"
    "/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition"
    "/62b2d346-98b9-4cf6-a6b9-45874290076d/scratchpad/slurp-logprob"
)
INPUTS = {
    "trace": RUN_DIR / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.trace.jsonl",
    "outputs": RUN_DIR / "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1.outputs.jsonl",
    "per_sample": SCRATCH / "per-sample.json",
    "clusters": SCRATCH / "clusters.json",
    "label_inventory": SCRATCH / "label-inventory.json",
}

#: sha256 the predecessor's committed receipt publishes for four of the five
#: inputs (``verdict/read-inputs-provenance.json`` and
#: ``verdict/score-provenance.json``). The trace's own hash is not published
#: there, so this read publishes it rather than asserting it.
PUBLISHED_SHA256 = {
    "outputs": "44a9e5b6fd29a8eb66c28b6f9707b056281ee033d7a65582dd66c6aac0329921",
    "per_sample": "936e0512ff5152623d75aa57c81a89dc5b60da959620a98cf6e57e91504a8cf0",
    "clusters": "9d6ec916a02dbcbe7464282450f814eef9bc2b47541ebc4bb5df949c8b11f9c1",
    "label_inventory": "faedea31126710078580f0d1270c829330e4870ab467b7a5805a4448809dbc8d",
}


class DesignReadError(RuntimeError):
    """The design read refuses rather than reporting a number it cannot stand behind."""


def _load_predecessor_read() -> Any:
    """``scripts/slurp_logprob_judge_read.py``, imported BY PATH.

    The shared venv ships an unrelated top-level ``scripts`` package (verl), so
    ``import scripts.slurp_logprob_judge_read`` resolves to the wrong tree.
    """

    path = REPO / "scripts" / "slurp_logprob_judge_read.py"
    spec = importlib.util.spec_from_file_location("saea_lp1_read", path)
    if spec is None or spec.loader is None:
        raise DesignReadError(f"cannot import the predecessor read at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _flag_at_budget(scores: Mapping[str, float], budget: int) -> tuple[set[str], float]:
    """The ``budget`` least-confident rows and the STATISTIC cutoff selecting them.

    ``scores`` are the statistic's own values (lower = less confident). Ties at
    the boundary are INCLUDED, because a threshold cannot split identical
    evidence, so the returned set may exceed ``budget`` and the caller reports
    the actual count.
    """

    if budget <= 0:
        raise DesignReadError("flag budget must be positive")
    ordered = sorted(scores.items(), key=lambda item: (item[1], item[0]))
    if budget >= len(ordered):
        return set(scores), math.inf
    cutoff = ordered[budget - 1][1]
    return {key for key, value in scores.items() if value <= cutoff}, cutoff


def _precision_recall(flagged: set[str], errors: Mapping[str, bool]) -> dict[str, float | int]:
    error_ids = {key for key, value in errors.items() if value}
    hit = len(flagged & error_ids)
    return {
        "flagged": len(flagged),
        "errors": len(error_ids),
        "caught": hit,
        "precision": 100.0 * hit / len(flagged) if flagged else 0.0,
        "recall": 100.0 * hit / len(error_ids) if error_ids else 0.0,
    }


def _precision_over_sequence(
    ids: Sequence[str], *, flagged: set[str], errors: Mapping[str, bool]
) -> float:
    """Precision of a FIXED flag set over a resampled id sequence.

    ``analysis.paired.resampled_statistic`` hands its statistic a sequence in
    which ids repeat; collapsing to a set would throw the resampling away and
    narrow the interval the admission rule turns on, so the multiplicity is
    kept.
    """

    drawn = [sample_id for sample_id in ids if sample_id in flagged]
    if not drawn:
        return 0.0
    return 100.0 * sum(1 for sample_id in drawn if errors.get(sample_id, False)) / len(drawn)


def _pr_curve(
    scores: Mapping[str, float], errors: Mapping[str, bool]
) -> list[dict[str, float | int]]:
    """One point per distinct cutoff: rows flagged against errors caught."""

    curve: list[dict[str, float | int]] = []
    for cutoff in sorted({value for value in scores.values()}):
        flagged = {key for key, value in scores.items() if value <= cutoff}
        point = dict(_precision_recall(flagged, errors))
        point["statistic_cutoff"] = cutoff
        curve.append(point)
    return curve


def build(*, seed: int, replicates: int) -> dict[str, Any]:
    sys.path.insert(0, str(REPO / "src"))
    from speech_aware_evidence_acquisition.analysis.paired import (
        resampled_statistic,
    )
    from speech_aware_evidence_acquisition.core import judges as cj
    from speech_aware_evidence_acquisition.core.base import JUDGES
    from speech_aware_evidence_acquisition.core.policies import (  # noqa: F401
        POLICIES,  # registers the judges
    )

    lp1 = _load_predecessor_read()

    provenance = {}
    for name, path in INPUTS.items():
        if not path.exists():
            raise DesignReadError(f"sealed input {name} is missing at {path}")
        digest = _sha256(path)
        published = PUBLISHED_SHA256.get(name)
        if published is not None and digest != published:
            raise DesignReadError(
                f"{name}: sha256 {digest} does not match the predecessor receipt's "
                f"published {published}; the design read refuses to measure bytes the "
                "landed verdict did not measure"
            )
        provenance[name] = {
            "path": str(path),
            "sha256": digest,
            "matches_published_receipt": published is not None,
        }

    trace = lp1.load_jsonl(INPUTS["trace"])
    outputs = lp1.load_jsonl(INPUTS["outputs"])
    per_sample_doc = json.loads(INPUTS["per_sample"].read_text(encoding="utf-8"))
    per_sample = (
        per_sample_doc["per_sample"]
        if isinstance(per_sample_doc, Mapping)
        else per_sample_doc
    )
    clusters = json.loads(INPUTS["clusters"].read_text(encoding="utf-8"))
    inventory = json.loads(INPUTS["label_inventory"].read_text(encoding="utf-8"))

    logprobs_by_request = lp1.logprobs_by_request(trace)
    labels = lp1.error_labels(per_sample)
    judge = JUDGES.resolve(cj.SLURP_INTENT_TOKEN_LOGPROB_JUDGE_V1)

    rows: dict[str, dict[str, Any]] = {}
    disagreements: list[str] = []
    prefix_only: list[str] = []
    for row in outputs:
        sample_id = str(row["sample_id"])
        request_id = str(row["request_id"])
        text = str(row["text"])
        record = logprobs_by_request[request_id]

        # (1) the two implementations of one alignment
        mine = judge.statistics(text, record)
        theirs = lp1.row_confidence(record)
        for statistic in cj.SLURP_INTENT_LOGPROB_STATISTICS:
            if mine[statistic] != theirs[statistic]:
                disagreements.append(sample_id)
                break
        if mine["reconstructed_prefix_only"]:
            prefix_only.append(sample_id)

        rows[sample_id] = {
            "statistics": {
                statistic: mine[statistic]
                for statistic in cj.SLURP_INTENT_LOGPROB_STATISTICS
            },
            "whole_answer_min": theirs["min_token_logprob"],
            "label_token_count": mine["label_token_count"],
            "labels": labels[sample_id],
            "judges": lp1.deterministic_judges(text, inventory),
            "text": text,
            "record": record,
        }
    if disagreements:
        raise DesignReadError(
            f"{len(disagreements)} row(s) disagree between the judge's alignment and the "
            f"predecessor read's, e.g. {disagreements[:3]}"
        )
    unusable = [
        sample_id
        for sample_id, row in rows.items()
        if any(row["statistics"][statistic] is None for statistic in row["statistics"])
    ]

    sample_ids = sorted(rows)
    intent_errors = {
        sample_id: bool(rows[sample_id]["labels"]["intent_error"])
        for sample_id in sample_ids
    }
    legality_flagged = {
        sample_id for sample_id in sample_ids if rows[sample_id]["judges"]["legality"]
    }
    schema_flagged = {
        sample_id for sample_id in sample_ids if rows[sample_id]["judges"]["schema"]
    }

    def cluster_of(sample_id: str) -> str:
        return str(clusters[sample_id])

    document: dict[str, Any] = {
        "schema": "saea-lp2-label-token-logprob-design-read-v1",
        "row": "SAEA-SLURP-MF-LP2-DESIGN-V1",
        "model_contacts": 0,
        "reading": (
            "DESIGN READ. The thresholds below were fixed from exactly these rows, so "
            "every precision, recall and AUROC here is measured on the data that chose "
            "the rule. None of it is quotable as a result; the decision is the fresh "
            "replicate of the LP-2 preregistration"
        ),
        "predecessor": {
            "run_id": "SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1",
            "attempt_id": "attempt-20260909T052142Z-07ca9c",
            "verdict": "NOT ADMITTED",
            "verdict_note": (
                "docs/readiness/2026-09-09-slurp-logprob-judge-probe-v1-verdict.md"
            ),
        },
        "inputs": provenance,
        "n": len(sample_ids),
        "clusters": len({cluster_of(sample_id) for sample_id in sample_ids}),
        "intent_error_rows": sum(intent_errors.values()),
        "seed": seed,
        "n_replicates": replicates,
        "ci_level": CI_LEVEL,
        "alignment_agreement": {
            "rows_compared": len(sample_ids),
            "statistics_compared": list(cj.SLURP_INTENT_LOGPROB_STATISTICS),
            "disagreements": len(disagreements),
            "rows_whose_stream_is_a_proper_prefix": len(prefix_only),
            "rows_without_a_locatable_label": len(unusable),
            "note": (
                "core.judges.SlurpIntentTokenLogprobJudge.statistics against "
                "scripts/slurp_logprob_judge_read.py::row_confidence, the read written "
                "and unit-tested before the probe flew; equality is exact, not within a "
                "tolerance"
            ),
        },
        "judge": {
            "id": judge.id,
            "version": judge.version,
            "criticism_only": judge.criticism_only,
            "default_statistic": cj.SLURP_INTENT_LOGPROB_DEFAULT_STATISTIC,
            "frozen_floors": dict(cj.SLURP_INTENT_LOGPROB_FLOORS),
        },
        "statistics": {},
        "free_judges": {},
    }

    # (2)+(3)+(4)+(5), per statistic
    for statistic in cj.SLURP_INTENT_LOGPROB_STATISTICS:
        values = {
            sample_id: float(rows[sample_id]["statistics"][statistic])
            for sample_id in sample_ids
            if rows[sample_id]["statistics"][statistic] is not None
        }
        derived_flagged, derived_cutoff = _flag_at_budget(values, FLAG_BUDGET)
        frozen = cj.SLURP_INTENT_LOGPROB_FLOORS[statistic]
        if derived_cutoff != frozen:
            raise DesignReadError(
                f"{statistic}: the {FLAG_BUDGET}-flag cutoff re-derived from the sealed "
                f"rows is {derived_cutoff!r}, but the judge ships {frozen!r}"
            )

        # The registered judge, driven exactly as a Reviewer would drive it.
        judge_flagged: set[str] = set()
        not_located: set[str] = set()
        for sample_id in sample_ids:
            verdict = judge(
                rows[sample_id]["text"],
                {"statistic": statistic},
                {"logprobs": rows[sample_id]["record"]},
            )
            codes = {flag.code for flag in verdict.flags}
            if "low_intent_label_confidence" in codes:
                judge_flagged.add(sample_id)
            if "intent_label_tokens_not_located" in codes:
                not_located.add(sample_id)
        if judge_flagged != derived_flagged:
            raise DesignReadError(
                f"{statistic}: the registered judge flags {len(judge_flagged)} rows but "
                f"the frozen threshold selects {len(derived_flagged)}"
            )

        flag_score = {sample_id: -value for sample_id, value in values.items()}

        def auroc_over(ids: Sequence[str], _score=flag_score) -> float:
            return lp1.auroc(
                [_score[sample_id] for sample_id in ids],
                [intent_errors[sample_id] for sample_id in ids],
            )

        auroc_boot = resampled_statistic(
            sample_ids=sorted(values),
            statistic=auroc_over,
            seed=seed,
            n_replicates=replicates,
            ci_level=CI_LEVEL,
            cluster_of=cluster_of,
        )

        def precision_over(ids: Sequence[str], _score=flag_score) -> float:
            return lp1.precision_at_budget_over_sequence(
                ids,
                scores=_score,
                errors=intent_errors,
                budget=FLAG_BUDGET,
                population=len(_score),
            )

        precision_boot = resampled_statistic(
            sample_ids=sorted(values),
            statistic=precision_over,
            seed=seed,
            n_replicates=replicates,
            ci_level=CI_LEVEL,
            cluster_of=cluster_of,
        )

        union = judge_flagged | legality_flagged

        def union_precision(ids: Sequence[str], _union=union) -> float:
            return _precision_over_sequence(ids, flagged=_union, errors=intent_errors)

        union_boot = resampled_statistic(
            sample_ids=sample_ids,
            statistic=union_precision,
            seed=seed,
            n_replicates=replicates,
            ci_level=CI_LEVEL,
            cluster_of=cluster_of,
        )

        document["statistics"][statistic] = {
            "frozen_threshold": frozen,
            "frozen_threshold_basis": (
                f"the value that flags {FLAG_BUDGET} of this arm's 1,000 rows, ties at "
                "the boundary included; quoted from the predecessor verdict's "
                "successor_diagnostic_NOT_PREREGISTERED and re-derived here"
            ),
            "rows_carrying_the_statistic": len(values),
            "rows_flagged_by_the_registered_judge": len(judge_flagged),
            "rows_flagged_as_label_not_located": len(not_located),
            "intent_error": _precision_recall(judge_flagged, intent_errors),
            "auroc_intent_error": {
                "auroc": auroc_boot.point_estimate,
                "ci90": [auroc_boot.ci_low, auroc_boot.ci_high],
                "sigma_hat": auroc_boot.sigma_hat,
            },
            "precision_bootstrap": {
                "precision": precision_boot.point_estimate,
                "ci90": [precision_boot.ci_low, precision_boot.ci_high],
                "note": (
                    "the flag budget is rescaled to each replicate's own size, exactly "
                    "as the predecessor's own precision arm was bootstrapped"
                ),
            },
            "union_with_legality_judge": {
                **_precision_recall(union, intent_errors),
                "precision_ci90": [union_boot.ci_low, union_boot.ci_high],
                "rows_only_the_confidence_flag_reaches": len(
                    judge_flagged - legality_flagged
                ),
                "rows_only_the_legality_judge_reaches": len(
                    legality_flagged - judge_flagged
                ),
                "rows_both_reach": len(judge_flagged & legality_flagged),
            },
            "precision_recall_curve": _pr_curve(values, intent_errors),
        }

    # The free judges and the predecessor's own flag, on the same rows.
    def legality_precision(ids: Sequence[str]) -> float:
        return _precision_over_sequence(ids, flagged=legality_flagged, errors=intent_errors)

    legality_boot = resampled_statistic(
        sample_ids=sample_ids,
        statistic=legality_precision,
        seed=seed,
        n_replicates=replicates,
        ci_level=CI_LEVEL,
        cluster_of=cluster_of,
    )
    whole_answer = {
        sample_id: float(rows[sample_id]["whole_answer_min"]) for sample_id in sample_ids
    }
    whole_flagged, whole_cutoff = _flag_at_budget(whole_answer, FLAG_BUDGET)
    document["free_judges"] = {
        "legality": {
            **_precision_recall(legality_flagged, intent_errors),
            "precision_ci90": [legality_boot.ci_low, legality_boot.ci_high],
            "definition": (
                "the row's (scenario, action) pair is not one of the 60 legal TRAIN "
                "pairs; recomputed on this arm by the predecessor read's own "
                "deterministic_judges, free and zero-latency"
            ),
        },
        "schema": {
            **_precision_recall(schema_flagged, intent_errors),
            "definition": (
                "unparsed, or an entity type outside the 55-type TRAIN vocabulary, or a "
                "repeated type; recomputed on this arm under the probe's own stricter "
                "reading, NOT the MF-9 constant"
            ),
        },
        "predecessor_whole_answer_min_token_logprob": {
            **_precision_recall(whole_flagged, intent_errors),
            "statistic_cutoff": whole_cutoff,
            "definition": (
                "the failed primary: the minimum logprob over the WHOLE answer, at the "
                "same 86-flag budget. Reported so the successor is priced against what "
                "it replaces"
            ),
        },
    }
    return document


def _render_readme(document: Mapping[str, Any]) -> str:
    mean = document["statistics"]["intent_mean_token_logprob"]
    minimum = document["statistics"]["intent_min_token_logprob"]
    legality = document["free_judges"]["legality"]
    predecessor = document["free_judges"]["predecessor_whole_answer_min_token_logprob"]

    def row(name: str, entry: Mapping[str, Any]) -> str:
        point = entry["intent_error"] if "intent_error" in entry else entry
        return (
            f"| {name} | {point['flagged']} | {point['caught']} | "
            f"{point['precision']:.2f} | {point['recall']:.2f} |"
        )

    lines = [
        "# LP-2 label-token logprob judge — the DESIGN read — `SAEA-SLURP-MF-LP2-DESIGN-V1`",
        "",
        "**Zero contacts of every kind.** No model, GPU, server, socket, tokenizer, tool,",
        "embedder, retriever or network; no waveform is decoded and no MP3 is opened, so the",
        "pinned absence of `ffmpeg` is preserved. Five already-sealed files are read and",
        "nothing else.",
        "",
        "**Every number here is a DESIGN READ and none of them is a result.** The judge's",
        "threshold is the value that flags 86 of *these* 1,000 rows, so this page measures a",
        "rule against the data that chose it. The decision lives in",
        "`docs/readiness/2026-09-09-slurp-label-token-logprob-judge-lp2-v1-preregistration.md`,",
        "which sends it to a fresh replicate of the same cell read under the frozen rule.",
        "",
        "Runner: `label_token_design_read.py` (in this directory). Machine-readable half:",
        "`design-read.json`. Judge: `core.judges.SlurpIntentTokenLogprobJudge`, registered as",
        f"`{document['judge']['id']}` version `{document['judge']['version']}`.",
        "",
        "## The frozen thresholds",
        "",
        "| statistic | frozen floor | rows it flags | basis |",
        "|---|---:|---:|---|",
        (
            f"| `intent_mean_token_logprob` **(chosen)** | `{mean['frozen_threshold']!r}` | "
            f"{mean['rows_flagged_by_the_registered_judge']} | the 86-flag cutoff on the "
            "predecessor arm |"
        ),
        (
            f"| `intent_min_token_logprob` | `{minimum['frozen_threshold']!r}` | "
            f"{minimum['rows_flagged_by_the_registered_judge']} | the 86-flag cutoff on the "
            "predecessor arm |"
        ),
        "",
        "A row is flagged when its statistic is **at or below** the floor: boundary ties are",
        "included, because a threshold cannot split identical evidence.",
        "",
        "## The design read, against this arm's own official intent errors",
        "",
        f"{document['intent_error_rows']} of {document['n']} rows carry an intent error.",
        "",
        "| flag | flagged | caught | precision % | recall % |",
        "|---|---:|---:|---:|---:|",
        row("`intent_mean_token_logprob` at its frozen floor", mean),
        row("`intent_min_token_logprob` at its frozen floor", minimum),
        row("legality judge (free, recomputed on this arm)", legality),
        row("union: mean-statistic flag + legality judge", mean["union_with_legality_judge"]),
        row("the predecessor's whole-answer minimum, 86 flags", predecessor),
        "",
        "## What the fresh pass has to beat",
        "",
        "AUROC for intent error, speaker-cluster bootstrap, "
        f"{document['n_replicates']:,} replicates, seed {document['seed']}, CI90 over "
        f"{document['clusters']} clusters:",
        "",
        "| statistic | AUROC | CI90 |",
        "|---|---:|---|",
        (
            f"| `intent_mean_token_logprob` | {mean['auroc_intent_error']['auroc']:.4f} | "
            f"[{mean['auroc_intent_error']['ci90'][0]:.4f}, "
            f"{mean['auroc_intent_error']['ci90'][1]:.4f}] |"
        ),
        (
            f"| `intent_min_token_logprob` | {minimum['auroc_intent_error']['auroc']:.4f} | "
            f"[{minimum['auroc_intent_error']['ci90'][0]:.4f}, "
            f"{minimum['auroc_intent_error']['ci90'][1]:.4f}] |"
        ),
        "",
        "## The two proofs this read owes",
        "",
        "1. **One alignment, not two.** The judge's label-token locator and the predecessor",
        f"   read's are compared on all {document['alignment_agreement']['rows_compared']}",
        "   rows for both statistics and agree exactly, to the last bit, with",
        f"   {document['alignment_agreement']['disagreements']} disagreements. The read",
        "   refuses rather than reporting a number if they ever differ.",
        "2. **The threshold is re-derived, not trusted.** Both frozen floors are recomputed",
        "   from the sealed rows as the 86-flag cutoff and asserted equal to the constants",
        "   the judge ships; the registered judge's own flag set is then asserted equal to",
        "   the set that cutoff selects.",
        "",
        "## Files",
        "",
        "| file | what it holds |",
        "|---|---|",
        "| `label_token_design_read.py` | the runner, zero contacts |",
        "| `design-read.json` | every number above, plus both whole precision-recall curves |",
        "| `MANIFEST.sha256` | this directory's byte manifest |",
        "",
        "## Reproducing",
        "",
        "```bash",
        "source ~/.venvs/speechrl/bin/activate",
        "export PYTHONDONTWRITEBYTECODE=1",
        "export PYTHONPATH=$REPO/src",
        "export CUDA_VISIBLE_DEVICES=",
        "export SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data",
        "cd $REPO && python docs/checks/speech-aware-evidence-acquisition/\\",
        "2026-09-09-lp2-label-token-logprob-design/label_token_design_read.py --write",
        "```",
        "",
        "The receipt carries no timestamp, so two consecutive writes reproduce the same",
        "`MANIFEST.sha256`.",
        "",
    ]
    return "\n".join(lines)


def _write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--replicates", type=int, default=N_REPLICATES)
    args = parser.parse_args(argv)

    document = build(seed=args.seed, replicates=args.replicates)
    if not args.write:
        summary = {
            key: value
            for key, value in document.items()
            if key not in ("statistics", "free_judges", "inputs")
        }
        print(json.dumps(summary, indent=2, sort_keys=True, default=str))
        for statistic, entry in document["statistics"].items():
            trimmed = {
                key: value
                for key, value in entry.items()
                if key != "precision_recall_curve"
            }
            print(statistic, json.dumps(trimmed, indent=2, sort_keys=True, default=str))
        print(json.dumps(document["free_judges"], indent=2, sort_keys=True, default=str))
        return 0

    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "design-read.json").write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (HERE / "README.md").write_text(
        _render_readme(document), encoding="utf-8", newline="\n"
    )
    _write_manifest(HERE)
    print((HERE / "MANIFEST.sha256").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
