#!/usr/bin/env python3
"""Does the locked carrier set SUPPORT speech enhancement as an observe mode?

Row ``SAEA-MF-ENHANCEMENT-SURVEY-V1`` (``model-free-check``), owner Decision
12-H of 2026-09-08. **Zero model, GPU, tokenizer, embedder, retriever, network
and paid-API contacts; zero audio seconds delivered to any service; no
enhancement model is downloaded, installed, loaded or run.**

The design note's observe-mode table names "enhancement for noisy input (a
pinned frozen enhancer with a derivation record, testbed = the Audio2Tool noisy
tier)". This script measures whether that testbed exists and where, on the
three locked carriers, a degraded condition can actually be contrasted with a
clean one. It answers four questions with sealed bytes and committed receipts:

1. **Audio2Tool.** What is the tier composition of the frozen 400 and of the
   three official-population rosters, what did the sealed official scorer
   score on each tier, and what is the acoustic difference between the seven
   single-utterance tiers and ``tier8_intent_blending`` -- the release's only
   acoustically degraded condition, one ``mixed.wav`` per item carrying a
   foreground utterance overlapped with a competing background one.
2. **SLURP.** The DEV-1000 roster mixes two SIMULTANEOUS recordings of the
   same utterance: the close-talk ``-headset.flac`` and the far-field
   ``.flac``. This measures the channel composition, the sealed comparator's
   intent and SLU-F1 per channel, and the paired same-utterance acoustic gap
   over BOTH channel files of every DEV-1000 utterance.
3. **Earnings.** The per-file sample rates of both carriers from the
   registered metadata loaders, the sealed Earnings-22 clip energy margins
   from the committed clip-boundary per-clip table, and a seeded bounded
   sample of the sealed Earnings-21 90-second obs-slices.
4. **Local inventory.** Whether any enhancement, denoising or dereverberation
   model is pinned in the umbrella lock (it is not) or present on disk.

Every audio sample is reduced immediately to 20 ms frame energies through
``analysis.e22_clip_boundary.frame_rms_dbfs`` at its committed 20 ms /
peak-30 dB / -55 dBFS settings and thrown away; nothing is written under any
dataset or derived-media root. The SLURP half opens the SECOND channel file of
each DEV-1000 utterance -- the twin the comparator did not fly -- analysis-side
only: it gains zero model exposure and stays available as an unflown twin.

The acoustic statistic is deliberately crude and is named as such everywhere it
appears. A true SNR needs a clean reference, and no carrier here has one; what
this measures is a SPEECH-TO-FLOOR MARGIN: the median level of the frames the
committed gate calls active, minus the 10th-percentile frame level of the same
clip. A clip recorded close to the mouth in a quiet room has a large margin; a
far-field clip, or one with a competing talker under the target, has a small
one. It ranks conditions; it does not measure noise power.

Usage (WSL2)::

    python scripts/run_enhancement_survey.py
    python scripts/run_enhancement_survey.py --write
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import statistics
import sys
import wave
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.e22_clip_boundary import (  # noqa: E402
    ABSOLUTE_FLOOR_DBFS,
    FRAME_MS,
    PEAK_DROP_DB,
    frame_rms_dbfs,
)
from speech_aware_evidence_acquisition.data.audio2tool import load_media_rows  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.loader import (  # noqa: E402
    load_earnings21,
    load_earnings22,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (  # noqa: E402
    load_legal_intent_inventory,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
    project_slu_label_v2,
)

ROW_ID = "SAEA-MF-ENHANCEMENT-SURVEY-V1"
SCHEMA = "saea-enhancement-observe-mode-survey-v1"
RECEIPT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-08-enhancement-survey"
)

#: The frozen Audio2Tool 400 (50 per tier). Its ``@16k`` roster carries the
#: same 400 base sample ids, which is the only thing read from it.
A2T_ROSTER_RELPATH = "docs/receipts/rosters/a2t-calibration-400-16k-v1.json"

#: The three official-population probe receipts and the verdict summaries that
#: carry their sealed official-scorer numbers.
A2T_POPULATIONS: tuple[tuple[str, str], ...] = (
    (
        "docs/receipts/probe-samples/a2t-tier1-official-population-500.json",
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-04-a2t-tier1-official-population-v1/result-summary.json",
    ),
    (
        "docs/receipts/probe-samples/a2t-tier258-official-population-1500.json",
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-04-a2t-tier258-official-population-v1/result-summary.json",
    ),
    (
        "docs/receipts/probe-samples/a2t-tier3467-official-population-2000.json",
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-04-a2t-tier3467-official-population-v1/result-summary.json",
    ),
)

#: The sealed frozen-400 calibration, read only for its per-tier table.
A2T_CALIBRATION_SUMMARY = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-04-a2t-direct-calibration-400-v1/result-summary.json"
)

#: The SLURP DEV-1000 probe receipt and the sealed comparator arm.
SLURP_RECEIPT_RELPATH = "docs/receipts/probe-samples/DEV-1000.json"
SLURP_COMPARATOR_RUN = "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1"
SLURP_COMPARATOR_ATTEMPT = "attempt-20260905T060424Z-2c5596"

#: Published anchors this read must reproduce from the sealed bytes before any
#: split of them is believed (verdicts of 2026-09-06).
SLURP_PUBLISHED_INTENT_UNPROJECTED = 71.40
SLURP_PUBLISHED_INTENT_PROJECTED_V2 = 73.10
SLURP_PUBLISHED_SLU_F1 = 35.80

#: The committed Earnings-22 clip energy margins (6,038 ESB DEV-10 clips).
E22_CLIP_TABLE_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-06-e22-clip-boundary-audit/per-clip-table.csv"
)

#: The sealed Earnings-21 90-second obs-slices of the direct baseline.
E21_SLICE_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
E21_SLICES_PER_CALL = 3
E21_SEED = 20260908

#: The local model inventory, listed read-only.
MODEL_INVENTORY_SUBDIR = "models"

#: Names that would identify an enhancement / denoising / dereverberation /
#: separation model if one were present locally or pinned in the lock.
ENHANCER_NAME_MARKERS: tuple[str, ...] = (
    "enhance",
    "denois",
    "dereverb",
    "deepfilter",
    "demucs",
    "sepformer",
    "cleanunet",
    "metricgan",
    "sgmse",
    "voicefixer",
    "clearvoice",
    "frcrn",
    "mossformer",
    "nsnet",
    "dccrn",
    "fullsubnet",
    "gtcrn",
    "resemble",
    "separation",
)


class SurveyError(RuntimeError):
    """An input is missing, has drifted, or an identity anchor failed."""


# ---------------------------------------------------------------------------
# The acoustic statistic
# ---------------------------------------------------------------------------


def clip_acoustics(samples: Any, sample_rate: int) -> dict[str, float]:
    """The crude speech-to-floor description of one clip.

    Every field comes from the committed 20 ms frame-energy gate and inherits
    its crudeness. ``speech_floor_margin_db`` is the median ACTIVE frame level
    minus the 10th-percentile frame level: large when speech sits well above a
    quiet floor, small when a competing talker or a room fills the gaps.
    """

    import numpy as np  # noqa: PLC0415

    frame_length = max(1, int(round(sample_rate * FRAME_MS / 1000.0)))
    levels = frame_rms_dbfs(samples, frame_length)
    if levels.size == 0:
        raise SurveyError("clip is shorter than one 20 ms frame")
    peak = float(levels.max())
    threshold = max(peak - PEAK_DROP_DB, ABSOLUTE_FLOOR_DBFS)
    active = levels >= threshold
    active_levels = levels[active]
    floor = float(np.percentile(levels, 10.0))
    return {
        "frames": float(levels.size),
        "seconds": float(levels.size * frame_length / sample_rate),
        "peak_dbfs": peak,
        "active_share": float(active.mean()),
        "floor_dbfs": floor,
        "median_active_dbfs": float(np.median(active_levels)) if active_levels.size else peak,
        "speech_floor_margin_db": (
            float(np.median(active_levels)) - floor if active_levels.size else 0.0
        ),
        "share_below_absolute_floor": float((levels < ABSOLUTE_FLOOR_DBFS).mean()),
    }


def read_wav_pcm(path: Path) -> tuple[Any, int]:
    """Decode one PCM wav with the standard library. No resample, no ffmpeg."""

    import numpy as np  # noqa: PLC0415

    with wave.open(str(path), "rb") as handle:
        if handle.getsampwidth() != 2:
            raise SurveyError(f"{path}: expected 16-bit PCM, got {handle.getsampwidth()} bytes")
        channels = handle.getnchannels()
        rate = handle.getframerate()
        raw = handle.readframes(handle.getnframes())
    data = np.frombuffer(raw, dtype="<i2")
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data.astype("float64"), rate


def read_soundfile(path: Path) -> tuple[Any, int]:
    """Decode one FLAC/WAV through ``soundfile`` at its NATIVE rate."""

    import numpy as np  # noqa: PLC0415
    import soundfile as sf  # noqa: PLC0415

    data, rate = sf.read(str(path), dtype="float64", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return np.asarray(data, dtype="float64") * 32768.0, int(rate)


def describe(values: Sequence[float]) -> dict[str, float]:
    """The five-number summary this read reports everywhere."""

    if not values:
        return {"n": 0}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "mean": statistics.fmean(ordered),
        "p10": _percentile(ordered, 10.0),
        "median": _percentile(ordered, 50.0),
        "p90": _percentile(ordered, 90.0),
        "min": ordered[0],
        "max": ordered[-1],
    }


def _percentile(ordered: Sequence[float], pct: float) -> float:
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * pct / 100.0
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    weight = position - low
    return float(ordered[low] * (1.0 - weight) + ordered[high] * weight)


# ---------------------------------------------------------------------------
# Audio2Tool
# ---------------------------------------------------------------------------


def _read_json(relpath: str) -> Any:
    path = REPO / relpath
    if not path.is_file():
        raise SurveyError(f"missing committed input: {relpath}")
    return json.loads(path.read_text(encoding="utf-8"))


def a2t_task_support(lock: Mapping[str, object], root: Path) -> dict[str, Any]:
    """Tier composition, sealed per-tier accuracy, and the frozen-400 acoustics."""

    roster = _read_json(A2T_ROSTER_RELPATH)
    base_ids = sorted(
        {str(item["sample_id"]).split("@", 1)[0] for item in roster["items"]}
    )
    if len(base_ids) != 400:
        raise SurveyError(f"frozen 400 resolved to {len(base_ids)} base ids")

    populations: dict[str, dict[str, Any]] = {}
    per_tier_official: dict[str, dict[str, Any]] = {}
    for receipt_relpath, summary_relpath in A2T_POPULATIONS:
        receipt = _read_json(receipt_relpath)
        summary = _read_json(summary_relpath)
        populations[Path(receipt_relpath).stem] = {
            "receipt": receipt_relpath,
            "n_items": int(receipt["n_items"]),
            "strata_counts": dict(receipt["strata_counts"]),
            "split_identity_hash": receipt["split_identity_hash"],
        }
        wanted = set(receipt["strata_counts"])
        for tier, block in _a2t_tier_blocks(summary, wanted).items():
            official = block.get("official", block)
            per_tier_official[tier] = {
                "source": summary_relpath,
                "samples": _dig(official, "tool_accuracy", "samples"),
                "tool_accuracy_pct": _dig(official, "tool_accuracy", "pct"),
                "tool_accuracy_ci90": [
                    _dig(official, "tool_accuracy", "ci90_low_pct"),
                    _dig(official, "tool_accuracy", "ci90_high_pct"),
                ],
                "exact_match_pct": _dig(official, "exact_match", "pct"),
                "paper_tool_accuracy_pct": _dig(block, "paper", "tool_accuracy"),
                "outcome": _dig(block, "decision", "outcome"),
                "domain_counts": _dig(block, "domain_slices", "counts"),
                "tool_accuracy_natural_mixture_pct": _dig(
                    block, "domain_slices", "tool_accuracy_natural_mixture_pct"
                ),
                "tool_accuracy_equal_domain_pct": _dig(
                    block, "domain_slices", "tool_accuracy_equal_domain_pct"
                ),
                "per_domain_tool_accuracy_pct": {
                    domain: _dig(slice_block, "tool_accuracy", "pct")
                    for domain, slice_block in (
                        _dig(block, "domain_slices", "per_domain") or {}
                    ).items()
                },
            }
            per_domain = per_tier_official[tier]["per_domain_tool_accuracy_pct"]
            if per_domain.get("wearables") is not None and per_domain.get("smart_home"):
                per_tier_official[tier]["wearables_minus_smart_home_pp"] = (
                    per_domain["wearables"] - per_domain["smart_home"]
                )

    calibration = _read_json(A2T_CALIBRATION_SUMMARY)

    media = load_media_rows(lock, root, base_ids)
    per_tier_rows: dict[str, list[dict[str, float]]] = {}
    csv_rows: list[dict[str, Any]] = []
    for sample_id in base_ids:
        row = media[sample_id]
        path = Path(root) / str(row["media_relpath"])
        samples, rate = read_wav_pcm(path)
        if rate != int(row["sample_rate_hz"]):
            raise SurveyError(f"{sample_id}: header rate drift")
        stats = clip_acoustics(samples, rate)
        stats["sample_rate_hz"] = float(rate)
        tier = sample_id.split(":", 1)[0]
        per_tier_rows.setdefault(tier, []).append(stats)
        csv_rows.append({"sample_id": sample_id, "tier": tier, **stats})

    rates: dict[int, int] = {}
    for row in media.values():
        rate = int(row["sample_rate_hz"])
        rates[rate] = rates.get(rate, 0) + 1

    return {
        "frozen_400": {
            "roster": A2T_ROSTER_RELPATH,
            "n": len(base_ids),
            "strata_counts": dict(_read_json(A2T_ROSTER_RELPATH)["strata_counts"]),
            "split_identity_hash": _read_json(A2T_ROSTER_RELPATH)["split_identity_hash"],
            "sample_rate_hz_counts": {str(k): v for k, v in sorted(rates.items())},
        },
        "official_populations": populations,
        "per_tier_official_scorer": per_tier_official,
        "frozen_400_calibration_per_tier": _calibration_per_tier(calibration),
        "frozen_400_acoustics": {
            tier: {
                key: describe([row[key] for row in rows])
                for key in (
                    "seconds",
                    "peak_dbfs",
                    "active_share",
                    "floor_dbfs",
                    "speech_floor_margin_db",
                    "share_below_absolute_floor",
                )
            }
            for tier, rows in sorted(per_tier_rows.items())
        },
        "_csv_rows": csv_rows,
    }


def _a2t_tier_blocks(
    summary: Mapping[str, Any], wanted: Iterable[str]
) -> dict[str, Mapping[str, Any]]:
    """Normalise the two official-population summary shapes to ``tier -> block``.

    The tiers-2/5/8 and tiers-3/4/6/7 summaries carry a ``tiers`` mapping; the
    tier-1 summary carries a ``cells`` mapping instead, because that flight ran
    two cells over one tier. Both shapes hold the SAME per-tier block keys
    (``official`` / ``paper`` / ``decision`` / ``domain_slices``), so only the
    nesting is adapted here -- no figure is recomputed and none is invented.
    """

    wanted_set = set(wanted)
    if isinstance(summary.get("tiers"), Mapping):
        return {
            tier: block
            for tier, block in summary["tiers"].items()
            if tier in wanted_set and isinstance(block, Mapping)
        }
    blocks: dict[str, Mapping[str, Any]] = {}
    for cell in (summary.get("cells") or {}).values():
        if not isinstance(cell, Mapping):
            continue
        per_tier = _dig(cell, "alignment_official_vs_v2", "per_tier")
        if not isinstance(per_tier, list) or len(per_tier) != 1:
            continue
        tier = str(per_tier[0].get("tier"))
        if tier not in wanted_set:
            continue
        samples = int(cell.get("samples") or 0)
        held = blocks.get(tier)
        if held is None or samples > int(held.get("samples") or 0):
            blocks[tier] = cell
    return blocks


def _calibration_per_tier(summary: Mapping[str, Any]) -> dict[str, Any]:
    """The frozen-400 calibration's own per-tier table, if it carries one."""

    for key in ("per_tier", "tiers", "per_tier_tool_accuracy"):
        if key in summary:
            return {"source_key": key, "table": summary[key]}
    return {"source_key": None, "table": {}}


def _dig(payload: Any, *path: str) -> Any:
    node: Any = payload
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return None
        node = node[key]
    return node


# ---------------------------------------------------------------------------
# SLURP
# ---------------------------------------------------------------------------


def _slurp_channel(sample_id: str) -> str:
    return "headset" if sample_id.endswith("-headset") else "far_field"


def _twin_id(sample_id: str) -> str:
    return (
        sample_id[: -len("-headset")]
        if sample_id.endswith("-headset")
        else f"{sample_id}-headset"
    )


def slurp_task_support(lock: Mapping[str, object], root: Path) -> dict[str, Any]:
    """Channel composition, per-channel sealed scores, paired channel acoustics."""

    receipt = _read_json(SLURP_RECEIPT_RELPATH)
    flown = [str(item["id"]) for item in receipt["items"]]
    if len(flown) != 1000:
        raise SurveyError(f"DEV-1000 receipt carries {len(flown)} items")
    channel_of = {sample_id: _slurp_channel(sample_id) for sample_id in flown}

    attempt_dir = (
        Path(root) / "runs" / SLURP_COMPARATOR_RUN / SLURP_COMPARATOR_ATTEMPT
    )
    scores_path = attempt_dir / f"{SLURP_COMPARATOR_RUN}.scores.json"
    outputs_path = attempt_dir / f"{SLURP_COMPARATOR_RUN}.outputs.jsonl"
    if not scores_path.is_file() or not outputs_path.is_file():
        raise SurveyError(f"sealed comparator artifacts missing under {attempt_dir}")
    sealed = json.loads(scores_path.read_text(encoding="utf-8"))
    per_sample = {
        str(row["sample_id"]): row for row in sealed["slurp-slu-official"]["per_sample"]
    }
    if set(per_sample) != set(flown):
        raise SurveyError("sealed per-sample ids do not match the DEV-1000 receipt")

    records = {
        record.sample_id: record
        for record in load_slurp_split(lock, root, "devel", allow_heldout=False)
    }
    gold = {
        sample_id: (records[sample_id].scenario, records[sample_id].action)
        for sample_id in flown
    }
    inventory = load_legal_intent_inventory(lock, root)

    responses: dict[str, str] = {}
    with outputs_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            sample_id = str(payload.get("sample_id"))
            if sample_id in channel_of:
                responses[sample_id] = str(payload.get("text") or "")
    if set(responses) != set(flown):
        raise SurveyError("sealed outputs do not cover the DEV-1000 roster exactly")

    rows_by_id: dict[str, dict[str, float]] = {}
    for sample_id in flown:
        row = per_sample[sample_id]
        scenario, action, _entities, parsed = parse_slu_response(responses[sample_id])
        projected = project_slu_label_v2(scenario, action, inventory, parsed=parsed)
        hit_v2 = 1 if (projected.scenario, projected.action) == gold[sample_id] else 0
        entry = {
            "intent_raw": float(row["scenario_action_exact"]),
            "intent_v2": float(hit_v2),
            "tp": 0.0,
            "fp": 0.0,
            "fn": 0.0,
        }
        for tag in ("word", "char"):
            entry["tp"] += float(row[f"slu_f1_{tag}_tp"])
            entry["fp"] += float(row[f"slu_f1_{tag}_fp"])
            entry["fn"] += float(row[f"slu_f1_{tag}_fn"])
        rows_by_id[sample_id] = entry

    per_channel = _slurp_channel_table(rows_by_id, channel_of, flown)

    anchors = {
        "intent_unprojected_pct": per_channel["pooled"]["intent_unprojected_pct"],
        "intent_projected_v2_pct": per_channel["pooled"]["intent_projected_v2_pct"],
        "slu_f1_pct": per_channel["pooled"]["slu_f1_pct"],
        "published_intent_unprojected_pct": SLURP_PUBLISHED_INTENT_UNPROJECTED,
        "published_intent_projected_v2_pct": SLURP_PUBLISHED_INTENT_PROJECTED_V2,
        "published_slu_f1_pct": SLURP_PUBLISHED_SLU_F1,
    }
    anchors["identity_check_passed"] = all(
        abs(anchors[ours] - anchors[theirs]) < 0.051
        for ours, theirs in (
            ("intent_unprojected_pct", "published_intent_unprojected_pct"),
            ("intent_projected_v2_pct", "published_intent_projected_v2_pct"),
            ("slu_f1_pct", "published_slu_f1_pct"),
        )
    )

    paired, csv_rows, twinned = _slurp_paired_acoustics(root, records, flown, channel_of)

    twin_available = sorted(twinned)
    per_channel_twinned = _slurp_channel_table(rows_by_id, channel_of, twin_available)
    contrasts = {
        "all_1000": _slurp_channel_contrast(rows_by_id, channel_of, flown),
        "twin_available_only": _slurp_channel_contrast(
            rows_by_id, channel_of, twin_available
        ),
    }

    return {
        "roster": SLURP_RECEIPT_RELPATH,
        "split_identity_hash": receipt["split_identity_hash"],
        "channel_counts": {
            "headset": sum(1 for value in channel_of.values() if value == "headset"),
            "far_field": sum(1 for value in channel_of.values() if value == "far_field"),
        },
        "twin_availability": {
            "note": (
                "a SLURP real recording session writes two files -- the close-talk "
                "'-headset.flac' and the far-field '.flac'. Where both exist the "
                "roster's own selection rule picked one of them at random, which "
                "makes the channel a randomized assignment on that subset."
            ),
            "utterances_with_both_channels": len(twin_available),
            "utterances_with_one_channel_only": len(flown) - len(twin_available),
            "by_flown_channel": {
                channel: {
                    "with_twin": sum(
                        1
                        for sample_id in twin_available
                        if channel_of[sample_id] == channel
                    ),
                    "without_twin": sum(
                        1
                        for sample_id in flown
                        if channel_of[sample_id] == channel
                        and sample_id not in twinned
                    ),
                }
                for channel in ("headset", "far_field")
            },
        },
        "comparator": {
            "run_id": SLURP_COMPARATOR_RUN,
            "attempt_id": SLURP_COMPARATOR_ATTEMPT,
            "per_channel": per_channel,
            "per_channel_twin_available_only": per_channel_twinned,
            "channel_contrasts": contrasts,
            "anchors": anchors,
        },
        "paired_channel_acoustics": paired,
        "_csv_rows": csv_rows,
    }


def _slurp_channel_table(
    rows_by_id: Mapping[str, Mapping[str, float]],
    channel_of: Mapping[str, str],
    subset: Sequence[str],
) -> dict[str, dict[str, float]]:
    """Per-channel and pooled figures over ``subset``."""

    buckets: dict[str, dict[str, float]] = {
        name: {"intent_raw": 0.0, "intent_v2": 0.0, "tp": 0.0, "fp": 0.0, "fn": 0.0, "n": 0.0}
        for name in ("headset", "far_field", "pooled")
    }
    for sample_id in subset:
        entry = rows_by_id[sample_id]
        for name in (channel_of[sample_id], "pooled"):
            bucket = buckets[name]
            bucket["n"] += 1.0
            for key in ("intent_raw", "intent_v2", "tp", "fp", "fn"):
                bucket[key] += entry[key]
    return {name: _slurp_bucket_summary(bucket) for name, bucket in buckets.items()}


def _slurp_channel_contrast(
    rows_by_id: Mapping[str, Mapping[str, float]],
    channel_of: Mapping[str, str],
    subset: Sequence[str],
    *,
    replicates: int = 10000,
    seed: int = E21_SEED,
) -> dict[str, Any]:
    """far-field minus headset, with an UNPAIRED percentile bootstrap CI90.

    The two channels carry different utterances, so this is not a paired
    contrast and is never reported as an admission result. It is a headroom
    observation: it answers "does the acoustically worse channel score worse",
    and the interval says how much of an answer the roster can give.
    """

    groups = {
        name: [rows_by_id[s] for s in subset if channel_of[s] == name]
        for name in ("far_field", "headset")
    }
    point = {
        metric: _group_metric(groups["far_field"], metric)
        - _group_metric(groups["headset"], metric)
        for metric in ("intent_v2", "intent_raw", "slu_f1")
    }
    rng = random.Random(seed)
    draws: dict[str, list[float]] = {metric: [] for metric in point}
    for _ in range(replicates):
        resampled = {
            name: [rows[rng.randrange(len(rows))] for _ in rows]
            for name, rows in groups.items()
        }
        for metric in point:
            draws[metric].append(
                _group_metric(resampled["far_field"], metric)
                - _group_metric(resampled["headset"], metric)
            )
    return {
        "definition": "far_field minus headset, percentage points",
        "unpaired": True,
        "n_far_field": len(groups["far_field"]),
        "n_headset": len(groups["headset"]),
        "replicates": replicates,
        "seed": seed,
        "ci_level": 0.90,
        "metrics": {
            metric: {
                "delta_pp": point[metric],
                "ci90": [
                    _percentile(sorted(draws[metric]), 5.0),
                    _percentile(sorted(draws[metric]), 95.0),
                ],
            }
            for metric in point
        },
    }


def _group_metric(rows: Sequence[Mapping[str, float]], metric: str) -> float:
    if not rows:
        return 0.0
    if metric in ("intent_v2", "intent_raw"):
        return 100.0 * sum(row[metric] for row in rows) / len(rows)
    tp = sum(row["tp"] for row in rows)
    fp = sum(row["fp"] for row in rows)
    fn = sum(row["fn"] for row in rows)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return 100.0 * (
        2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    )


def _slurp_bucket_summary(bucket: Mapping[str, float]) -> dict[str, float]:
    n = float(bucket["n"]) or 1.0
    tp, fp, fn = bucket["tp"], bucket["fp"], bucket["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "n": int(bucket["n"]),
        "intent_unprojected_pct": 100.0 * bucket["intent_raw"] / n,
        "intent_projected_v2_pct": 100.0 * bucket["intent_v2"] / n,
        "slu_f1_pct": 100.0 * f1,
        "slu_precision_pct": 100.0 * precision,
        "slu_recall_pct": 100.0 * recall,
    }


def _slurp_paired_acoustics(
    root: Path,
    records: Mapping[str, Any],
    flown: Sequence[str],
    channel_of: Mapping[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    """Both channel files of every DEV-1000 utterance, reduced to frame energies."""

    csv_rows: list[dict[str, Any]] = []
    twinned: set[str] = set()
    deltas: dict[str, list[float]] = {}
    alignment: list[float] = []
    per_channel_rows: dict[str, list[dict[str, float]]] = {"headset": [], "far_field": []}
    missing_twins = 0
    for sample_id in flown:
        twin_id = _twin_id(sample_id)
        if twin_id not in records:
            missing_twins += 1
            continue
        pair: dict[str, dict[str, float]] = {}
        for member in (sample_id, twin_id):
            path = Path(root) / records[member].media_relpath
            samples, rate = read_soundfile(path)
            stats = clip_acoustics(samples, rate)
            stats["sample_rate_hz"] = float(rate)
            pair[_slurp_channel(member)] = stats
            per_channel_rows[_slurp_channel(member)].append(stats)
        twinned.add(sample_id)
        csv_rows.append(
            {
                "utterance_sample_id": sample_id,
                "flown_channel": channel_of[sample_id],
                **{f"headset_{k}": v for k, v in pair["headset"].items()},
                **{f"far_field_{k}": v for k, v in pair["far_field"].items()},
            }
        )
        for key in ("peak_dbfs", "active_share", "floor_dbfs", "speech_floor_margin_db"):
            deltas.setdefault(key, []).append(pair["headset"][key] - pair["far_field"][key])
        alignment.append(abs(pair["headset"]["seconds"] - pair["far_field"]["seconds"]))

    return (
        {
            "utterances_paired": len(csv_rows),
            "utterances_without_twin": missing_twins,
            "per_channel": {
                channel: {
                    key: describe([row[key] for row in rows])
                    for key in (
                        "seconds",
                        "peak_dbfs",
                        "active_share",
                        "floor_dbfs",
                        "speech_floor_margin_db",
                    )
                }
                for channel, rows in per_channel_rows.items()
            },
            "headset_minus_far_field": {
                key: describe(values) for key, values in sorted(deltas.items())
            },
            "channel_time_alignment": {
                "note": (
                    "the two channel files of one recording session are NOT frame "
                    "aligned: they are separately trimmed renditions of the same "
                    "utterance by the same speaker. A study can pair them by "
                    "utterance, never by sample."
                ),
                "abs_duration_delta_seconds": describe(alignment),
                "share_within_0p02_s": (
                    sum(1 for value in alignment if value <= 0.02) / len(alignment)
                    if alignment
                    else 0.0
                ),
                "share_within_0p10_s": (
                    sum(1 for value in alignment if value <= 0.10) / len(alignment)
                    if alignment
                    else 0.0
                ),
            },
        },
        csv_rows,
        twinned,
    )


# ---------------------------------------------------------------------------
# Earnings
# ---------------------------------------------------------------------------


def earnings_task_support(lock: Mapping[str, object], root: Path) -> dict[str, Any]:
    """Per-file sample rates, the sealed E22 clip margins, sampled E21 slices."""

    carriers: dict[str, Any] = {}
    for name, loader in (
        ("earnings21-original", load_earnings21),
        ("earnings22-original", load_earnings22),
    ):
        samples = loader(lock, root)
        rates: dict[int, int] = {}
        for sample in samples:
            rates[sample.sample_rate_hz] = rates.get(sample.sample_rate_hz, 0) + 1
        carriers[name] = {
            "files": len(samples),
            "sample_rate_hz_counts": {str(k): v for k, v in sorted(rates.items())},
            "audio_hours": sum(sample.audio_seconds for sample in samples) / 3600.0,
            "duration_seconds": describe([sample.audio_seconds for sample in samples]),
        }

    e22_clips = _e22_clip_margins()
    e21_slices, e21_rows = _e21_slice_acoustics(root)
    return {
        "carriers": carriers,
        "earnings22_sealed_clip_margins": e22_clips,
        "earnings21_sampled_slice_acoustics": e21_slices,
        "_csv_rows": e21_rows,
    }


def _e22_clip_margins() -> dict[str, Any]:
    path = REPO / E22_CLIP_TABLE_RELPATH
    if not path.is_file():
        raise SurveyError(f"missing committed input: {E22_CLIP_TABLE_RELPATH}")
    peaks: list[float] = []
    active: list[float] = []
    leading: list[float] = []
    trailing: list[float] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            peaks.append(float(row["peak_dbfs"]))
            active.append(float(row["active_share"]))
            leading.append(float(row["leading_silence_seconds"]))
            trailing.append(float(row["trailing_silence_seconds"]))
    return {
        "source": E22_CLIP_TABLE_RELPATH,
        "clips": len(peaks),
        "peak_dbfs": describe(peaks),
        "active_share": describe(active),
        "leading_silence_seconds": describe(leading),
        "trailing_silence_seconds": describe(trailing),
    }


def _e21_slice_acoustics(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    slices_dir = Path(root) / "derived" / "obs-slices" / E21_SLICE_RUN
    if not slices_dir.is_dir():
        raise SurveyError(f"sealed Earnings-21 slices missing: {slices_dir}")
    rng = random.Random(E21_SEED)
    rows: list[dict[str, Any]] = []
    stats_rows: list[dict[str, float]] = []
    for call_dir in sorted(p for p in slices_dir.iterdir() if p.is_dir()):
        wavs = sorted(call_dir.glob("*.wav"))
        if not wavs:
            continue
        picked = sorted(rng.sample(wavs, min(E21_SLICES_PER_CALL, len(wavs))))
        for wav in picked:
            samples, rate = read_wav_pcm(wav)
            stats = clip_acoustics(samples, rate)
            stats["sample_rate_hz"] = float(rate)
            stats_rows.append(stats)
            rows.append({"call": call_dir.name, "slice": wav.name, **stats})
    return (
        {
            "source_run": E21_SLICE_RUN,
            "seed": E21_SEED,
            "slices_per_call": E21_SLICES_PER_CALL,
            "slices_measured": len(stats_rows),
            **{
                key: describe([row[key] for row in stats_rows])
                for key in (
                    "seconds",
                    "peak_dbfs",
                    "active_share",
                    "floor_dbfs",
                    "speech_floor_margin_db",
                )
            },
        },
        rows,
    )


# ---------------------------------------------------------------------------
# Local inventory
# ---------------------------------------------------------------------------


def local_enhancer_inventory(lock: Mapping[str, object], root: Path) -> dict[str, Any]:
    """Is any enhancer pinned in the umbrella lock, or present on disk?"""

    models = lock.get("models")
    lock_keys = []
    if isinstance(models, list):
        for entry in models:
            if isinstance(entry, Mapping):
                key = entry.get("key") or entry.get("name")
                if key:
                    lock_keys.append(str(key))
    models_dir = Path(root) / MODEL_INVENTORY_SUBDIR
    on_disk = (
        sorted(p.name for p in models_dir.iterdir() if p.is_dir())
        if models_dir.is_dir()
        else []
    )
    return {
        "lock_model_keys": sorted(lock_keys),
        "on_disk_model_dirs": on_disk,
        "lock_matches": sorted(_marker_matches(lock_keys)),
        "on_disk_matches": sorted(_marker_matches(on_disk)),
        "markers": list(ENHANCER_NAME_MARKERS),
    }


def _marker_matches(names: Iterable[str]) -> set[str]:
    return {
        name
        for name in names
        if any(marker in name.lower() for marker in ENHANCER_NAME_MARKERS)
    }


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def enhancement_ceilings(
    a2t: Mapping[str, Any], slurp: Mapping[str, Any], earnings: Mapping[str, Any]
) -> dict[str, Any]:
    """What is the MOST an enhancement observe mode could buy, per carrier.

    Priced from the measured quantities only. Where no clean counterpart of the
    degraded rows exists, that is stated instead of estimated: a ceiling that
    cannot be computed is not guessed here.
    """

    tier8 = a2t["per_tier_official_scorer"]["tier8_intent_blending"]
    # The FLOWN population is 500 rows per tier (the ``samples`` the official
    # scorer reports); a probe receipt registers only the items no earlier
    # receipt already covered, so its ``strata_counts`` are smaller and are
    # NOT the denominator here.
    flown_counts = {
        tier: int(block["samples"])
        for tier, block in a2t["per_tier_official_scorer"].items()
    }
    union_total = sum(flown_counts.values())
    tier8_share = flown_counts["tier8_intent_blending"] / union_total
    domain_gaps = {
        tier: block.get("wearables_minus_smart_home_pp")
        for tier, block in a2t["per_tier_official_scorer"].items()
    }
    clean_gaps = [
        value
        for tier, value in domain_gaps.items()
        if value is not None and tier != "tier8_intent_blending"
    ]

    contrast = slurp["comparator"]["channel_contrasts"]["twin_available_only"]["metrics"]
    far_field_share = slurp["channel_counts"]["far_field"] / (
        slurp["channel_counts"]["far_field"] + slurp["channel_counts"]["headset"]
    )

    return {
        "audio2tool": {
            "degraded_condition": "tier8_intent_blending (foreground + competing background utterance in one wav)",
            "clean_counterpart_exists": False,
            "clean_counterpart_note": (
                "the release ships ONE mixed.wav per tier-8 item and no isolated "
                "foreground rendition, so 'the degraded rows scored as if clean' "
                "cannot be computed on this corpus at all -- only bounded."
            ),
            "flown_rows_per_tier": flown_counts,
            "flown_union_rows": union_total,
            "degraded_share_of_union": tier8_share,
            "degraded_tool_accuracy_pct": tier8["tool_accuracy_pct"],
            "unreachable_upper_bound_on_union_pp": tier8_share
            * (100.0 - float(tier8["tool_accuracy_pct"])),
            "unreachable_upper_bound_note": (
                "what a PERFECT tier-8 score would add to the union's natural-mixture "
                "accuracy. It is an arithmetic bound, never a target: tier 8 is the "
                "one tier already ALIGNED against the published row."
            ),
            "device_domain_gap_pp": {
                "tier8": domain_gaps.get("tier8_intent_blending"),
                "clean_tiers_median": statistics.median(clean_gaps) if clean_gaps else None,
                "clean_tiers_max": max(clean_gaps) if clean_gaps else None,
                "note": (
                    "wearables minus smart_home tool accuracy. Present on every tier, "
                    "with and without a background talker, which is what says the "
                    "dominant error axis is device-domain disambiguation and not the "
                    "acoustic condition."
                ),
            },
        },
        "slurp": {
            "degraded_condition": "far-field channel ('.flac'), against its own simultaneous close-talk twin ('-headset.flac')",
            "clean_counterpart_exists": True,
            "degraded_share_of_roster": far_field_share,
            "measured_on": "the 766 DEV-1000 utterances whose session has BOTH channel files, where the roster's own rule chose between them at random",
            "headset_minus_far_field_intent_pp": -float(contrast["intent_v2"]["delta_pp"]),
            "headset_minus_far_field_intent_ci90": [
                -float(contrast["intent_v2"]["ci90"][1]),
                -float(contrast["intent_v2"]["ci90"][0]),
            ],
            "headset_minus_far_field_slu_f1_pp": -float(contrast["slu_f1"]["delta_pp"]),
            "headset_minus_far_field_slu_f1_ci90": [
                -float(contrast["slu_f1"]["ci90"][1]),
                -float(contrast["slu_f1"]["ci90"][0]),
            ],
            "roster_ceiling_intent_pp": far_field_share
            * (-float(contrast["intent_v2"]["delta_pp"])),
            "roster_ceiling_slu_f1_pp": far_field_share
            * (-float(contrast["slu_f1"]["delta_pp"])),
            "note": (
                "a PERFECT enhancer that turned every far-field row into its own "
                "headset twin could buy at most the channel gap on the far-field "
                "share. Both gaps' CI90s contain zero at this roster size."
            ),
        },
        "earnings": {
            "degraded_condition": None,
            "clean_counterpart_exists": False,
            "note": (
                "neither Earnings carrier ships a second channel or a clean "
                "reference rendition of the same audio, so no clean-versus-degraded "
                "contrast and no 'scored as if clean' ceiling exists here. What IS "
                "measurable is sample-rate heterogeneity (a bandwidth and resampling "
                "question) and clip-boundary bleed (a segmentation question); neither "
                "is what a denoiser does."
            ),
            "earnings21_sample_rate_hz_counts": earnings["carriers"]["earnings21-original"][
                "sample_rate_hz_counts"
            ],
            "earnings22_sample_rate_hz_counts": earnings["carriers"]["earnings22-original"][
                "sample_rate_hz_counts"
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="land the receipt")
    parser.add_argument(
        "--umbrella-lock",
        default=os.environ.get("SAEA_UMBRELLA_LOCK", ""),
        help=(
            "path to the umbrella docs/datasets.lock.json. Only needed when this "
            "checkout is a git worktree parked outside the registered "
            "<umbrella>/studies/<study>/ layout, where the locator cannot find it."
        ),
    )
    args = parser.parse_args()

    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    lock_path = Path(args.umbrella_lock) if args.umbrella_lock else umbrella_lock_path(REPO)
    if not lock_path.is_file():
        raise SurveyError(f"umbrella lock not found at {lock_path}")
    lock = load_lock(lock_path)
    root = data_root()

    a2t = a2t_task_support(lock, root)
    slurp = slurp_task_support(lock, root)
    earnings = earnings_task_support(lock, root)
    inventory = local_enhancer_inventory(lock, root)

    a2t_rows = a2t.pop("_csv_rows")
    slurp_rows = slurp.pop("_csv_rows")
    e21_rows = earnings.pop("_csv_rows")

    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "execution_profile": "model-free-check",
        "exposure_row": ROW_ID,
        "authority": "owner Decision 12-H, 2026-09-08",
        "umbrella_lock_sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "paid_api_spend": 0,
            "audio_seconds_delivered": 0,
        },
        "acoustic_statistic": {
            "frame_ms": FRAME_MS,
            "peak_drop_db": PEAK_DROP_DB,
            "absolute_floor_dbfs": ABSOLUTE_FLOOR_DBFS,
            "note": (
                "a crude frame-energy gate, not a VAD and not an SNR. "
                "speech_floor_margin_db is the median ACTIVE frame level minus the "
                "10th-percentile frame level of the same clip; it ranks conditions "
                "and does not measure noise power. No carrier here has a clean "
                "reference, so a true SNR cannot be computed for any of them."
            ),
        },
        "audio2tool": a2t,
        "slurp": slurp,
        "earnings": earnings,
        "enhancement_ceilings": enhancement_ceilings(a2t, slurp, earnings),
        "local_enhancer_inventory": inventory,
    }

    receipt_dir = REPO / RECEIPT_RELPATH
    if args.write:
        receipt_dir.mkdir(parents=True, exist_ok=True)
        (receipt_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_csv(receipt_dir / "a2t-frozen400-acoustics.csv", a2t_rows)
        write_csv(receipt_dir / "slurp-channel-acoustics.csv", slurp_rows)
        write_csv(receipt_dir / "e21-slice-acoustics.csv", e21_rows)
        write_manifest(receipt_dir)
        print(f"wrote {RECEIPT_RELPATH}")
    else:
        print(json.dumps(summary, indent=2, sort_keys=True))
        print("(print only; pass --write to land the receipt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
