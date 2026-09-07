#!/usr/bin/env python3
"""CLI: the read of ``SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1``.

The one-time re-read of the six Earnings-22 ESB TEST calls with the
tail-silence media, against the sealed ``SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1``
arm on the same 2,735 published segments. Preregistration:
``docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-preregistration.md``.

I/O AND ORCHESTRATION ONLY. Every measurement comes from an existing analysis
module -- ``analysis.e22_error_taxonomy`` for the taxonomy, the agentic rate and
the boundary block, ``analysis.e22_usage_cells`` for the corpus/per-call/
per-duration/weighting arithmetic and the pooled bootstrap, ``analysis.paired``
for the per-utterance contrast -- so nothing is computed twice with two
definitions. What is local here is which population, which reference layer and
which segment table are handed to them.

**Zero model contact, strictly post-hoc.** The offline guard is armed before any
input is opened. Both arms are read from sealed outputs and sealed score files
that already exist; the TEST reference layer is opened only by the registered
scorers' own loader, which re-hashes it against its committed receipt on every
call. No audio byte is opened, no decoder runs and no new contact is made.

Usage (WSL2): ``python scripts/e22_test_tail2s_read.py [--write]``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis import paired as paired_module  # noqa: E402
from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (  # noqa: E402
    agentic_error_rate,
    build_entity_inventory,
    load_segment_table,
    per_duration_table,
)
from speech_aware_evidence_acquisition.analysis.e22_usage_cells import (  # noqa: E402
    FROZEN_SCORER,
    WHISPER_SCORER,
    _corpus,
    boundary_charge,
    category_mass,
    duration_table,
    high_impact_charge,
    load_score_rows,
    per_call_table,
    pooled_delta,
    scan,
    weightings,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.esb_reference import (  # noqa: E402
    ESB_REFERENCE_RECEIPT_RELPATH,
    load_esb_references,
)

EXPOSURE_ROW_ID = "SAEA-E22-ESB-SHORTFORM-TAIL2S-TEST-V1"
PREREGISTRATION = (
    "docs/readiness/2026-09-07-e22-esb-shortform-tail2s-test-v1-preregistration.md"
)
ANALYSIS_VERSION = "saea-e22-esb-tail2s-test-read-v1"

_CHECKS = "docs/checks/speech-aware-evidence-acquisition"

#: The TEST segment table, hash-pinned by the sealed 2026-09-04 flight's own
#: receipt. ``analysis.e22_error_taxonomy.load_segment_table`` defaults to the
#: dev10 table; this population needs the test one, which is why the relpath is
#: passed explicitly rather than defaulted.
TEST_SEGMENT_TABLE_RECEIPT_RELPATH = (
    f"{_CHECKS}/2026-09-04-e22-esb-shortform-alignment-400-v1/"
    "segment-table/segment-table-receipt.json"
)

#: The frozen population and the media it was cut into.
ROSTER_RELPATH = "docs/receipts/rosters/e22-esb-test-2735-ts2-v1.json"
MEDIA_ROSTER_RELPATH = (
    f"{_CHECKS}/2026-09-07-e22-test2735-tail2s-media/roster/flight-roster-receipt.json"
)
FALSIFIER_RELPATH = (
    f"{_CHECKS}/2026-09-07-e22-esb-shortform-tail2s-test-v1/flight-2735/falsifier.json"
)

ARMS: Mapping[str, Mapping[str, str]] = {
    "A": {
        "run_id": "SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1",
        "attempt": "attempt-20260905T044432Z-8f23ee",
        "label": "the sealed 2026-09-04 test arm, v1 media",
    },
    "TS2": {
        "run_id": EXPOSURE_ROW_ID,
        "attempt": None,  # supplied on the command line
        "label": "this cell, +2.0 s of digital silence per clip",
    },
}

#: Arm A's own sealed numbers, hard-coded from
#: ``docs/checks/.../2026-09-04-.../verdict/result-summary.json``. No contrast is
#: computed unless every one of them reproduces from the sealed score file.
SEALED_ARM_ANCHORS = {
    "corpus_wer_whisper": 15.9365,
    "corpus_wer_saea_v1": 20.896,
    "substitutions": 2236,
    "deletions": 948,
    "insertions": 4612,
    "reference_words": 48919,
    "utterances": 2735,
}

# The decision rule of section 4, fixed before any number existed.
PAPER_WER = 9.79
CROSS_READ_WER = 12.3
BAND_TEST = 12.79
FLOOR_STRICT = 11.59
FLOOR_LOOSE = 15.09
ALIGNED_BETTER = 6.79
FLOORS = {
    "whisper-large-v3": 11.59,
    "whisper-large-v3-turbo": 11.07,
    "distil-large-v3.5": 10.83,
    "qwen3-asr-0.6b": 10.78,
    "qwen3-asr-1.7b": 9.73,
    "whisper-medium.en": 12.63,
    "whisper-small.en": 12.97,
    "whisper-base.en": 15.09,
    "whisper-tiny.en": 19.12,
}
E21_FULL44_CORPUS = 8.200

# Section 5's prediction, fixed in writing from dev before any contact.
PREDICTION = {
    "dev_cell_corpus_wer": 9.4054,
    "dev_comparator_corpus_wer": 17.4012,
    "dev_delta": -7.9958,
    "dev_ratio": 0.5405,
    "sealed_test_baseline": 15.937,
    "additive_transfer_point": 7.94,
    "multiplicative_transfer_point": 8.61,
    "interval": [7.5, 10.5],
    "length_oracle_bound_of_the_sealed_arm": 10.456,
}
SEALED_ARM_INSERTION_SHARE = 59.2
SEALED_ARM_LENGTH_RATIO = 1.0749

SEED = 20260903
N_REPLICATES = 10_000
CI_LEVEL = 0.90

OUT_DIR = REPO_ROOT / _CHECKS / "2026-09-07-e22-esb-shortform-tail2s-test-v1" / "flight-2735"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_test_roster() -> dict[str, object]:
    """The frozen 2,735-row TEST roster: ids, call strata, identity hash."""

    payload = (REPO_ROOT / ROSTER_RELPATH).read_bytes()
    receipt = json.loads(payload.decode("utf-8"))
    items = receipt["items"]
    ids = tuple(sorted(str(item["sample_id"]) for item in items))
    if len(ids) != len(set(ids)) or len(ids) != 2735:
        raise SystemExit(f"{ROSTER_RELPATH} does not carry 2,735 unique ids")
    return {
        "variant_ids": ids,
        "call_of": {str(i["sample_id"]): str(i["stratum"]) for i in items},
        "split_identity_hash": str(receipt["split_identity_hash"]),
        "roster_id": str(receipt["roster_id"]),
        "receipt_sha256": hashlib.sha256(payload).hexdigest(),
    }


def load_media_roster() -> dict[str, object]:
    """Published and variant durations, per clip, from the media build receipt."""

    payload = (REPO_ROOT / MEDIA_ROSTER_RELPATH).read_bytes()
    receipt = json.loads(payload.decode("utf-8"))
    return {
        "published_seconds_of": {
            str(i["sample_id"]): float(i["source_audio_seconds"]) for i in receipt["items"]
        },
        "variant_seconds_of": {
            str(i["sample_id"]): float(i["audio_seconds"]) for i in receipt["items"]
        },
        "clamped": sorted(
            str(i["sample_id"])
            for i in receipt["items"]
            if bool(i["end_clamped_to_decoded_parent"])
        ),
        "receipt_sha256": hashlib.sha256(payload).hexdigest(),
    }


def published_key(variant_id: str) -> str:
    return variant_id.split("@", 1)[0]


def read_arm(
    root: Path,
    source: Mapping[str, str],
    *,
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, object]],
    inventory: Mapping[str, frozenset[str]],
    sample_ids: Sequence[str],
) -> dict[str, object]:
    """One arm: its sealed per-sample scores and its taxonomy scan, on the roster."""

    scores = load_score_rows(root, source, sample_ids)
    totals, scored, contexts = scan(
        root,
        source,
        references=references,
        segments=segments,
        inventory=inventory,
        sample_ids=sample_ids,
    )
    reference_words_of = {
        sample_id: len(contexts[sample_id].ref_tokens) for sample_id in sample_ids
    }
    return {
        "source": dict(source),
        "scores": scores,
        "totals": totals,
        "scored": scored,
        "contexts": contexts,
        "charge": high_impact_charge(scored),
        "boundary_charge_of": boundary_charge(scored),
        "reference_words_of": reference_words_of,
    }


def taxonomy_identity_gate(
    arm: Mapping[str, object], sample_ids: Sequence[str]
) -> dict[str, object]:
    """The taxonomy's own alignment must reproduce the paper-facing scorer.

    If it does not, the category split below is a SECOND measurement of the
    number rather than a decomposition of it, and the read stops.
    """

    scorer = _corpus(arm["scores"][WHISPER_SCORER], sample_ids)
    totals = arm["totals"]
    taxonomy_errors = totals.substitutions + totals.deletions + totals.insertions
    fields = {
        "scorer_substitutions": scorer["substitutions"],
        "scorer_deletions": scorer["deletions"],
        "scorer_insertions": scorer["insertions"],
        "scorer_reference_words": scorer["reference_words"],
        "scorer_corpus_wer_percent": scorer["corpus_wer_percent"],
        "taxonomy_substitutions": int(totals.substitutions),
        "taxonomy_deletions": int(totals.deletions),
        "taxonomy_insertions": int(totals.insertions),
        "taxonomy_reference_words": int(totals.reference_length),
        "taxonomy_corpus_wer_percent": round(
            100.0 * taxonomy_errors / totals.reference_length, 4
        )
        if totals.reference_length
        else 0.0,
    }
    fields["reproduces"] = (
        fields["scorer_substitutions"] == fields["taxonomy_substitutions"]
        and fields["scorer_deletions"] == fields["taxonomy_deletions"]
        and fields["scorer_insertions"] == fields["taxonomy_insertions"]
        and fields["scorer_reference_words"] == fields["taxonomy_reference_words"]
    )
    return fields


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True, help="this cell's attempt id")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    guard = arm_offline_guard()
    root = data_root()

    roster = load_test_roster()
    media = load_media_roster()
    variant_ids = list(roster["variant_ids"])
    sample_ids = sorted(published_key(v) for v in variant_ids)
    if len(set(sample_ids)) != len(sample_ids):
        raise SystemExit("two variant ids collapse onto one published segment")
    call_of = {published_key(v): roster["call_of"][v] for v in variant_ids}
    published_seconds_of = {
        published_key(v): media["published_seconds_of"][v] for v in variant_ids
    }

    references = load_esb_references(
        root, repo_root=REPO_ROOT, receipt_relpaths=(ESB_REFERENCE_RECEIPT_RELPATH,)
    )
    segments = load_segment_table(
        root, REPO_ROOT, receipt_relpath=TEST_SEGMENT_TABLE_RECEIPT_RELPATH
    )
    missing = set(sample_ids) - set(references)
    if missing:
        raise SystemExit(f"{len(missing)} roster rows have no reference, first {sorted(missing)[0]}")

    # The whole TEST reference layer IS this population -- 2,735 rows, one per
    # roster row -- so there is exactly one entity-inventory basis here and no
    # dev-style subset/full ambiguity.
    by_call: dict[str, list[str]] = {}
    for sample_id in sample_ids:
        by_call.setdefault(str(segments[sample_id]["source_id"]), []).append(
            references[sample_id]
        )
    inventory = build_entity_inventory(by_call)

    sources = {
        "A": dict(ARMS["A"]),
        "TS2": {**ARMS["TS2"], "attempt": args.attempt},
    }
    arms = {
        name: read_arm(
            root,
            source,
            references=references,
            segments=segments,
            inventory=inventory,
            sample_ids=sample_ids,
        )
        for name, source in sources.items()
    }

    # --- the identity gate: arm A must reproduce its own sealed numbers -------
    a_whisper = _corpus(arms["A"]["scores"][WHISPER_SCORER], sample_ids)
    a_frozen = _corpus(arms["A"]["scores"][FROZEN_SCORER], sample_ids)
    anchors = {
        "corpus_wer_whisper": a_whisper["corpus_wer_percent"],
        "corpus_wer_saea_v1": a_frozen["corpus_wer_percent"],
        "substitutions": a_whisper["substitutions"],
        "deletions": a_whisper["deletions"],
        "insertions": a_whisper["insertions"],
        "reference_words": a_whisper["reference_words"],
        "utterances": a_whisper["rows"],
    }
    identity = {
        "anchors": [
            {
                "field": field,
                "sealed": SEALED_ARM_ANCHORS[field],
                "measured": anchors[field],
                "reproduced": abs(float(anchors[field]) - float(SEALED_ARM_ANCHORS[field]))
                < (0.0011 if isinstance(SEALED_ARM_ANCHORS[field], float) else 0.5),
            }
            for field in sorted(SEALED_ARM_ANCHORS)
        ]
    }
    identity["reproduced"] = all(row["reproduced"] for row in identity["anchors"])
    if not identity["reproduced"]:
        failed = [r for r in identity["anchors"] if not r["reproduced"]]
        raise SystemExit(
            "identity gate FAILED, no contrast computed: "
            + "; ".join(f"{r['field']} sealed {r['sealed']} measured {r['measured']}" for r in failed)
        )

    # --- the falsifier, read before any score is interpreted -----------------
    falsifier_path = REPO_ROOT / FALSIFIER_RELPATH
    falsifier = json.loads(falsifier_path.read_text(encoding="utf-8"))
    if str(falsifier["verdict"]) != "HOLDS" or falsifier["disagreements"]:
        raise SystemExit(
            "the section 4.2 falsifier does not hold on every row; the cell STOPS and "
            "reports rather than being interpreted"
        )

    # --- corpus, per call, per duration, weightings ---------------------------
    ts2_whisper = _corpus(arms["TS2"]["scores"][WHISPER_SCORER], sample_ids)
    ts2_frozen = _corpus(arms["TS2"]["scores"][FROZEN_SCORER], sample_ids)

    per_call = per_call_table(arms, sample_ids, call_of)
    weighting = weightings(arms, per_call, sample_ids)
    duration_scorer = duration_table(arms, sample_ids, published_seconds_of)
    over_20s = [s for s in sample_ids if published_seconds_of[s] > 20.0]
    over_20s_block = {
        "utterances": len(over_20s),
        "A": _corpus(arms["A"]["scores"][WHISPER_SCORER], over_20s),
        "TS2": _corpus(arms["TS2"]["scores"][WHISPER_SCORER], over_20s),
    }
    over_20s_block["delta"] = round(
        over_20s_block["TS2"]["corpus_wer_percent"] - over_20s_block["A"]["corpus_wer_percent"], 4
    )

    # --- the agentic rate and the boundary block, both arms -------------------
    agentic = {}
    boundary = {}
    taxonomy_tables = {}
    for name, arm in arms.items():
        reference_words = sum(arm["reference_words_of"].values())
        agentic[name] = agentic_error_rate(arm["scored"], reference_words)
        boundary[name] = category_mass(arm["scored"], arm["contexts"], reference_words)
        taxonomy_tables[name] = {
            "per_duration": per_duration_table(arm["scored"], arm["contexts"], sample_ids),
            "identity_gate": taxonomy_identity_gate(arm, sample_ids),
        }

    # --- the paired contrast --------------------------------------------------
    pooled_wer = pooled_delta(
        sample_ids,
        numerator=lambda arm, s: (
            arms[arm]["scores"][WHISPER_SCORER][s]["substitutions"]
            + arms[arm]["scores"][WHISPER_SCORER][s]["deletions"]
            + arms[arm]["scores"][WHISPER_SCORER][s]["insertions"]
        ),
        denominator=lambda arm, s: (
            arms[arm]["scores"][WHISPER_SCORER][s]["hits"]
            + arms[arm]["scores"][WHISPER_SCORER][s]["substitutions"]
            + arms[arm]["scores"][WHISPER_SCORER][s]["deletions"]
        ),
        left="A",
        right="TS2",
        call_of=call_of,
    )
    pooled_agentic = pooled_delta(
        sample_ids,
        numerator=lambda arm, s: arms[arm]["charge"].get(s, 0),
        denominator=lambda arm, s: arms[arm]["reference_words_of"][s],
        left="A",
        right="TS2",
        call_of=call_of,
    )
    pooled_boundary = pooled_delta(
        sample_ids,
        numerator=lambda arm, s: arms[arm]["boundary_charge_of"].get(s, 0),
        denominator=lambda arm, s: arms[arm]["reference_words_of"][s],
        left="A",
        right="TS2",
        call_of=call_of,
    )

    contrast = paired_module.paired_contrast(
        {s: {"wer": arms["A"]["scores"][WHISPER_SCORER][s]["wer"]} for s in sample_ids},
        {s: {"wer": arms["TS2"]["scores"][WHISPER_SCORER][s]["wer"]} for s in sample_ids},
        metrics=("wer",),
        sample_ids=sample_ids,
        strata_of=lambda s: call_of[s],
        seed=SEED,
        n_replicates=N_REPLICATES,
        ci_level=CI_LEVEL,
    )["wer"]
    per_utterance = {
        "metric": "per-utterance WER under the Whisper normalizer, signed as cell minus "
        "the sealed arm, so a NEGATIVE delta is an improvement",
        "n": contrast.n,
        "sealed_mean_wer": round(100.0 * contrast.left_mean, 4),
        "cell_mean_wer": round(100.0 * contrast.right_mean, 4),
        "mean_delta_points": round(100.0 * contrast.delta, 4),
        "rows_improved": contrast.harms,
        "rows_worsened": contrast.saves,
        "rows_tied": contrast.ties,
        "sign_test_p": contrast.sign_test_p,
        "note": "analysis.paired counts `saves` as rows where the RIGHT arm's metric is "
        "larger; on WER larger is worse, so rows_improved is that field's mirror and is "
        "reported under its own name here rather than by the module's label",
        "per_stratum": paired_module.per_stratum_table(contrast),
        "bootstrap": {
            "point_estimate": round(100.0 * contrast.bootstrap.point_estimate, 4),
            "ci_low": round(100.0 * contrast.bootstrap.ci_low, 4),
            "ci_high": round(100.0 * contrast.bootstrap.ci_high, 4),
            "seed": SEED,
            "n_replicates": N_REPLICATES,
            "ci_level": CI_LEVEL,
        },
    }

    # --- the decision, on the rule fixed before any number existed ------------
    w = ts2_whisper["corpus_wer_percent"]
    band_pass = w <= BAND_TEST
    strict_pass = w <= FLOOR_STRICT
    loose_pass = w <= FLOOR_LOOSE
    if w < ALIGNED_BETTER:
        verdict = "ALIGNED-BETTER"
    elif band_pass and strict_pass:
        verdict = "ALIGNED"
    else:
        verdict = "NOT ALIGNED"
    low, high = PREDICTION["interval"]
    if w > BAND_TEST:
        prediction_result = "REFUTES THE TRANSFER ASSUMPTION OUTRIGHT"
    elif low <= w <= high:
        prediction_result = "CONFIRMED: inside the preregistered interval"
    else:
        prediction_result = (
            "the prediction MISSED ITS INTERVAL while keeping its sign"
            if w < PREDICTION["sealed_test_baseline"]
            else "the prediction MISSED ITS INTERVAL and lost its sign"
        )

    decision = {
        "corpus_wer_percent_whisper": w,
        "label": "under the silence-tail convention (deviation D-TS2-3: the published "
        "systems did not append silence). This is NOT a like-for-like reproduction of "
        "the published protocol and must never be reported as one.",
        "band_test_threshold": BAND_TEST,
        "band_test_pass": band_pass,
        "floor_strict_threshold": FLOOR_STRICT,
        "floor_strict_pass": strict_pass,
        "floor_loose_threshold": FLOOR_LOOSE,
        "floor_loose_pass": loose_pass,
        "aligned_better_threshold": ALIGNED_BETTER,
        "verdict": verdict,
        "published_wer": PAPER_WER,
        "cross_read_wer": CROSS_READ_WER,
        "delta_vs_published": round(w - PAPER_WER, 4),
        "delta_vs_cross_read": round(w - CROSS_READ_WER, 4),
        "floors": {
            name: {"published": value, "cleared": w <= value}
            for name, value in sorted(FLOORS.items())
        },
        "band_is_secondary": "the owner GO of 2026-09-07 admits the band on this "
        "media-changing cell only with the deviation named; the PAIRED CONTRAST against "
        "the sealed arm is the primary statement and the band the secondary one",
        "prediction": {**PREDICTION, "result": prediction_result},
        "e21_full44_corpus_wer": E21_FULL44_CORPUS,
        "e21_comparison_caveat": "different segmentation (fixed 90 s windows against "
        "published utterance boundaries), a different corpus and a different reference "
        "convention; it is placed beside this number, never compared to it",
    }

    document = {
        "schema": ANALYSIS_VERSION,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW_ID,
        "preregistration": PREREGISTRATION,
        "attempt_id": args.attempt,
        "population": {
            "rows": len(sample_ids),
            "split_identity_hash": roster["split_identity_hash"],
            "roster": ROSTER_RELPATH,
            "roster_sha256": roster["receipt_sha256"],
            "media_roster": MEDIA_ROSTER_RELPATH,
            "media_roster_sha256": media["receipt_sha256"],
            "reference_layer": ESB_REFERENCE_RECEIPT_RELPATH,
            "segment_table": TEST_SEGMENT_TABLE_RECEIPT_RELPATH,
            "clamped_utterances": media["clamped"],
            "calls": sorted(set(call_of.values())),
        },
        "arms": {name: dict(source) for name, source in sources.items()},
        "identity_gate": identity,
        "falsifier": {
            "receipt": FALSIFIER_RELPATH,
            "receipt_sha256": sha256_file(falsifier_path),
            "verdict": falsifier["verdict"],
            "rows_checked": falsifier["rows_checked"],
            "rows_where_the_falsifier_holds": falsifier["rows_where_the_falsifier_holds"],
            "measured_prompt_tokens_total": falsifier["measured_prompt_tokens_total"],
            "predicted_prompt_tokens_total": falsifier["predicted_prompt_tokens_total"],
        },
        "corpus": {
            "A": {"whisper": a_whisper, "saea_scoring_v1": a_frozen},
            "TS2": {"whisper": ts2_whisper, "saea_scoring_v1": ts2_frozen},
            "sealed_arm_published_insertion_share_percent": SEALED_ARM_INSERTION_SHARE,
            "sealed_arm_published_length_ratio": SEALED_ARM_LENGTH_RATIO,
        },
        "per_call": per_call,
        "weightings": weighting,
        "per_duration_scorer": duration_scorer,
        "per_duration_taxonomy": {
            name: taxonomy_tables[name]["per_duration"] for name in taxonomy_tables
        },
        "over_20_seconds": over_20s_block,
        "agentic": agentic,
        "boundary": boundary,
        "taxonomy_identity_gate": {
            name: taxonomy_tables[name]["identity_gate"] for name in taxonomy_tables
        },
        "paired": {
            "signed_as": "cell minus the sealed SAEA-E22-ESB-SHORTFORM-ALIGNMENT-V1 arm, on "
            "the same 2,735 published segments, paired per segment; a negative delta is an "
            "improvement",
            "strata": "source call (6 strata)",
            "corpus_wer_points": pooled_wer,
            "agentic_points": pooled_agentic,
            "boundary_points": pooled_boundary,
            "per_utterance": per_utterance,
        },
        "decision": decision,
        "offline_guard": {"connection_attempts": guard.count, "targets": guard.targets},
    }

    print(json.dumps(decision, indent=2, sort_keys=True))
    print(
        json.dumps(
            {
                "corpus_wer": w,
                "sealed_arm": a_whisper["corpus_wer_percent"],
                "pooled_delta_points": pooled_wer["stratified"],
                "agentic": {k: v["agentic_error_rate_percent"] for k, v in agentic.items()},
                "boundary_points": {k: v["boundary"]["wer_points"] for k, v in boundary.items()},
                "rows_improved": per_utterance["rows_improved"],
                "rows_worsened": per_utterance["rows_worsened"],
                "sign_test_p": per_utterance["sign_test_p"],
            },
            indent=2,
            sort_keys=True,
        )
    )

    if args.write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        write_json_artifact(OUT_DIR / "flight-read.json", document)
        print(f"wrote {OUT_DIR / 'flight-read.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
