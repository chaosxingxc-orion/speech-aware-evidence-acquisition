#!/usr/bin/env python3
"""Measure cell E4-1's relisten cost basis and its smoke roster from sealed bytes (model-free).

Reads the sealed AGREE arm (SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1) and its request-form re-fly, the
wave shared A/A (SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1), both on TRAIN Fold A 1,080, and the Fold A
dataset fragment's per-row audio seconds. It parses each delivered answer with the official SLURP
prediction parser (``reproduction.slurp_scoring.parse_slu_response``) and keeps COUNTS ONLY:

* delivered entities per row, and the blind-contact count the relisten stage would spend on the
  sealed AGREE answers: sum over rows of min(entities, max_slots_per_row = 3);
* the audio the blind contacts would re-send: sum over rows of min(entities, 3) x row audio
  seconds (each relisten contact re-sends the row's own speech packet, spec section 1);
* the ceiling: 6 contacts per row, 6 x the Fold A total audio;
* entity-set instability between the two sealed flights (rows whose delivered entity SETS differ),
  the cheapest model-free proxy for a blind disagreement;
* the smoke roster: the first four rows in roster order with >= 3 delivered entities in the sealed
  AGREE arm AND an unstable entity set.

No gold label is read. No utterance text, filler, transcript or model output is printed or
persisted: only sample ids, counts and set-inequality booleans.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src python -B scripts/flights/e4/e4_cost_measure.py \\
        --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

AGREE = ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1")
WAVE_AA = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
DATASET_FRAGMENT = "configs/dataset/slurp-speech-native-evo-fold-a-1080.json"
OUT = "analysis/SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COST-MEASURE-V1/cost-measure-v1.json"
MAX_SLOTS = 3
CONTACTS_PER_ENTITY = 2


def _outputs(data: Path, run: str) -> tuple[Path, dict[str, list[tuple[str, str]]], int]:
    paths = sorted((data / "runs" / run).glob(f"attempt-*generation*/{run}.outputs.jsonl"))
    if len(paths) != 1:
        raise SystemExit(f"{run}: expected exactly one generation outputs file, found {len(paths)}")
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    out, parsed_rows = {}, 0
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            _s, _a, entities, ok = parse_slu_response(row.get("text") or "")
            parsed_rows += int(ok)
            out[row["sample_id"]] = sorted((e.type, e.filler) for e in entities)
    return paths[0], out, parsed_rows


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True, type=Path)
    args = parser.parse_args(argv)
    items = json.loads((REPO_ROOT / DATASET_FRAGMENT).read_text(encoding="utf-8"))["items"]
    order = [i["sample_id"] for i in items]
    audio = {i["sample_id"]: float(i["audio_seconds"]) for i in items}
    agree_path, agree, agree_parsed = _outputs(args.data_root, AGREE[0])
    aa_path, aa, _ = _outputs(args.data_root, WAVE_AA)
    if set(agree) != set(order) or set(aa) != set(order):
        raise SystemExit("a sealed flight does not cover the Fold A roster exactly")
    counts = {s: len(agree[s]) for s in order}
    blind = {s: min(n, MAX_SLOTS) for s, n in counts.items()}
    unstable = {s: agree[s] != aa[s] for s in order}
    smoke = [s for s in order if counts[s] >= 3 and unstable[s]][:4]
    total_audio = sum(audio.values())
    blind_audio = sum(blind[s] * audio[s] for s in order)
    report = {
        "schema": "saea-e4-relisten-cost-measure-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "tool": "scripts/flights/e4/e4_cost_measure.py",
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "gold_read": False,
        "sources": {
            "agree_outputs": {"path": str(agree_path.relative_to(args.data_root)), "sha256": _sha(agree_path)},
            "wave_aa_outputs": {"path": str(aa_path.relative_to(args.data_root)), "sha256": _sha(aa_path)},
            "dataset_fragment": {"path": DATASET_FRAGMENT, "sha256": _sha(REPO_ROOT / DATASET_FRAGMENT)},
        },
        "rows": len(order),
        "agree_parsed_rows": agree_parsed,
        "agree_delivered_entities_total": sum(counts.values()),
        "agree_rows_by_delivered_entity_count": {str(k): v for k, v in sorted(collections.Counter(counts.values()).items())},
        "blind_contacts_on_the_sealed_agree_answers": sum(blind.values()),
        "blind_contacts_per_row_mean": round(sum(blind.values()) / len(order), 4),
        "rows_with_at_least_one_blind_contact": sum(1 for v in blind.values() if v),
        "blind_audio_seconds_on_the_sealed_agree_answers": round(blind_audio, 4),
        "fold_a_audio_seconds_total": total_audio,
        "ceiling": {
            "extra_contacts_per_row": MAX_SLOTS * CONTACTS_PER_ENTITY,
            "extra_audio_seconds": round(MAX_SLOTS * CONTACTS_PER_ENTITY * total_audio, 4),
            "extra_audio_seconds_per_row_mean": round(MAX_SLOTS * CONTACTS_PER_ENTITY * total_audio / len(order), 4),
            "extra_audio_seconds_if_every_triggered_entity_fires_its_confirm": round(2 * blind_audio, 4),
            "extra_contacts_if_every_triggered_entity_fires_its_confirm": 2 * sum(blind.values()),
        },
        "entity_set_instability_agree_vs_wave_aa": {
            "rows_differing": sum(unstable.values()),
            "rows_differing_with_at_least_one_agree_entity": sum(1 for s in order if unstable[s] and counts[s]),
        },
        "smoke_selection": {
            "rule": "the first four Fold A roster rows (roster order) with >= 3 delivered entities in the sealed AGREE arm "
                    "and a delivered entity set that differs between the sealed AGREE arm and the wave A/A re-fly",
            "sample_ids": smoke,
            "roster_positions": [order.index(s) for s in smoke],
            "agree_delivered_entities": [counts[s] for s in smoke],
            "blind_contacts": sum(blind[s] for s in smoke),
            "audio_seconds": round(sum(audio[s] for s in smoke), 7),
            "candidates_total": sum(1 for s in order if counts[s] >= 3 and unstable[s]),
        },
        "boundary": "counts, ids and set-inequality booleans only; no filler, utterance text, transcript, gold label or "
                    "model output is printed or persisted",
    }
    out = args.data_root / OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    out.write_text(text, encoding="utf-8")
    print(json.dumps({"written": str(out), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      **{k: report[k] for k in ("blind_contacts_on_the_sealed_agree_answers",
                                                "blind_audio_seconds_on_the_sealed_agree_answers", "ceiling",
                                                "entity_set_instability_agree_vs_wave_aa", "smoke_selection")}},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
