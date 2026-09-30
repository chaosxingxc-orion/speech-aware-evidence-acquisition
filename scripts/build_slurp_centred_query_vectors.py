#!/usr/bin/env python3
"""Build the CENTRED speech-query vector file of one TRAIN roster (K6p's query side): each row's
pinned full-utterance speech query, unit-normalised, minus the mean of the pinned R01C
construction-roster speech queries, re-normalised, at zero encoder contacts.

WHAT IT IS. The query half of the K6p key (``docs/results/2026-09-30-slurp-retrieval-key-recall-
offline.md``; key half: ``scripts/build_slurp_centred_centroid_key.py``). A Perception branch's
``key_source.query_source`` pins this file; its cosine against the centred key file is exactly
the read's ``centre_queries(q, mu_q) @ centre_keys(raw_means, mu_p).T``.

THE ARITHMETIC IS THE READ'S: ``scripts/analysis/slurp_retrieval_key_recall.py``'s
``key_construction`` (which pins and loads the R01C speech queries and returns their mean
``mu_q``), its ``unit_rows`` and its ``centre_queries``. The source query file is the pinned
``query_source`` of the cell the read took the roster from (Fold A: the AGREE arm; Fold B: the
P-SV-1 arm), verified by sha256. Every line keeps its own id, audio sha256, frame counts and
segment identity; only the one segment's vector in the ``intent-boundary`` dimension changes.

The query still carries speech and only speech (owner rule 2026-09-06): the centring statistic is
itself a mean of pinned SPEECH vectors of a construction roster disjoint from both folds; no
transcript, answer, gold label or future turn enters. ZERO CONTACTS: no model, server, encoder,
embedder, scorer, tokenizer, network or GPU contact.

    PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/build_slurp_centred_query_vectors.py \\
        --roster fold-b --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

import numpy as np  # noqa: E402

import build_slurp_centred_centroid_key as keybuild  # noqa: E402

ARTIFACT_ID = "SAEA-SLURP-CENTRED-QUERIES-V1"
BUILDER_ID = "saea-slurp-centred-query-vectors-builder-v1"
#: One exposure-ledger row per roster (each row names its own split identity).
LEDGER_ROWS = {"fold-a": "SAEA-SLURP-CENTRED-QUERIES-FOLD-A-BUILD-V1", "fold-b": "SAEA-SLURP-CENTRED-QUERIES-FOLD-B-BUILD-V1"}
RECEIPT_SCHEMA = "saea-centred-query-vectors-receipt-v1"
FILE_NAME = "query-vectors-speech-segments.jsonl"
RECEIPT_NAME = "receipt.json"
#: roster -> (the config whose Perception ``query_source`` the read used for it, its roster receipt)
ROSTERS = {
    "fold-a": ("configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json",
               "docs/receipts/rosters/slurp-evo-fold-a-v2.json"),
    "fold-b": ("configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1-resume.json",
               "docs/receipts/rosters/slurp-evo-fold-b-v2.json"),
}
LINE_KEYS = {"id", "audio_sha256", "source_frames", "source_sample_rate_hz", "segments"}
SEGMENT_KEYS = {"id", "start_frame", "end_frame", "vectors"}


class BuildError(RuntimeError):
    """Refuse a build whose inputs are not the pinned bytes."""


def source_pin(repo: Path, roster: str) -> dict:
    cfg = json.loads((repo / ROSTERS[roster][0]).read_text(encoding="utf-8"))
    return dict(cfg["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]["query_source"])


def centred_lines(raw_lines: list, recall, mu_q, dimension: str) -> tuple[list, list]:
    """Rewrite each source line with its one segment's vector centred; return (lines, ids)."""

    docs = [json.loads(line) for line in raw_lines if line.strip()]
    for doc in docs:
        if set(doc) != LINE_KEYS or len(doc["segments"]) != 1 or set(doc["segments"][0]) != SEGMENT_KEYS:
            raise BuildError("a source query line is not one-segment sealed-segment-vectors shaped")
        if set(doc["segments"][0]["vectors"]) != {dimension}:
            raise BuildError(f"a source segment carries dimensions other than {dimension!r}")
    q = recall.unit_rows([doc["segments"][0]["vectors"][dimension] for doc in docs])
    centred = recall.centre_queries(q, mu_q)
    out = []
    for doc, row in zip(docs, centred):
        segment = dict(doc["segments"][0])
        segment["vectors"] = {dimension: [float(x) for x in row]}
        new = dict(doc)
        new["segments"] = [segment]
        out.append(json.dumps(new, separators=(",", ":"), sort_keys=False))
    return out, [doc["id"] for doc in docs]


def build(repo: Path, root: Path, out_root: Path, roster: str) -> dict:
    from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_segment_vectors

    recall, diag, cbuild = keybuild.recall_modules(repo)
    pin = source_pin(repo, roster)
    source_path = root / pin["relpath"]
    raw = source_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != pin["sha256"]:
        raise BuildError(f"{pin['relpath']} does not hash to its pinned {pin['sha256']}")
    kc = recall.key_construction(root, diag, cbuild)
    lines, ids = centred_lines(raw.decode("utf-8").splitlines(), recall, kc["mu_q"], recall.IB_DIM)
    roster_rel = ROSTERS[roster][1]
    roster_ids = recall.roster_ids(repo / roster_rel)
    if sorted(ids) != sorted(roster_ids):
        raise BuildError(f"the source query file does not cover exactly the {roster} roster")
    text = "\n".join(lines) + "\n"

    out_dir = out_root / "prepared" / ARTIFACT_ID / roster
    path, receipt_path = out_dir / FILE_NAME, out_dir / RECEIPT_NAME
    if path.exists() or receipt_path.exists():
        raise BuildError(f"refusing to overwrite an existing artifact under {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    sha = keybuild.digest_file(path)
    loaded = load_sealed_segment_vectors(path, expected_sha256=sha, dimensions=(recall.IB_DIM,))
    source = load_sealed_segment_vectors(source_path, expected_sha256=pin["sha256"], dimensions=(recall.IB_DIM,))
    if set(loaded) != set(ids):
        raise BuildError("the emitted query file does not cover the source ids exactly")
    for sid in ids:
        if loaded[sid].audio_sha256 != source[sid].audio_sha256:
            raise BuildError(f"{sid}: the audio identity moved")
    norms = np.linalg.norm(recall.unit_rows([loaded[s].segments[0][recall.IB_DIM] for s in ids]), axis=1)
    receipt = {
        "schema": RECEIPT_SCHEMA, "artifact_id": ARTIFACT_ID, "roster": roster, "builder_id": BUILDER_ID,
        "builder_sha256": keybuild.digest_file(Path(__file__)), "exposure_ledger_row": LEDGER_ROWS[roster],
        "generated_at": datetime.now(timezone.utc).isoformat(), "contact_class": "model-free",
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0, "tokenizer": 0,
                     "network": 0, "gpu": 0, "paid_api": 0},
        "artifact": {
            "relpath": str(Path("prepared") / ARTIFACT_ID / roster / FILE_NAME).replace("\\", "/"),
            "sha256": sha, "rows": len(lines), "kind": "sealed-segment-vectors", "dimension": recall.IB_DIM,
            "loader": "speech_aware_evidence_acquisition.rails.phase_supply.load_sealed_segment_vectors",
            "read_back_through_the_production_loader": True, "unit_norm_rows": int((abs(norms - 1.0) < 1e-12).sum()),
        },
        "source": {"relpath": pin["relpath"], "sha256": pin["sha256"],
                   "tool_contact_ledger_row": pin["tool_contact_ledger_row"], "config": ROSTERS[roster][0]},
        "roster_receipt": {"relpath": roster_rel, "sha256": keybuild.digest_file(repo / roster_rel), "rows": len(roster_ids)},
        "centring": {
            "rule": "unit_rows(unit_rows(q) - mu_q): the row's unit speech query minus the R01C speech-query mean, re-normalised",
            "arithmetic_source": {"relpath": str(keybuild.RECALL), "sha256": keybuild.digest_file(repo / keybuild.RECALL),
                                  "functions_used": ["key_construction", "unit_rows", "centre_queries"]},
            "statistics_query_file": {"relpath": recall.STATS_QUERY[0], "sha256": recall.STATS_QUERY[1]},
            "centring_roster": {"relpath": keybuild.CENTRING_ROSTER,
                                "sha256": keybuild.digest_file(repo / keybuild.CENTRING_ROSTER)},
            "statistics_rows": len(kc["stats_ids"]), "statistics_overlap": kc["stats_overlap"],
            "query_mean_sha256_f8le": keybuild.vector_sha(kc["mu_q"]),
        },
        "embedded_signal_for_the_pin": (
            f"speech: the TRAIN {roster} rows' own sealed full-utterance speech segments in the intent-boundary "
            "dimension (the pinned source query file), each unit-normalised and centred by the mean of the pinned R01C "
            "construction-roster speech queries, re-normalised; no transcript, answer, gold label or future turn."
        ),
        "boundary": ("A pre-computed model-free input, never an authorization: it opens no attempt, reserves no "
                     "contact and states no effectiveness claim; no new speech byte is read or encoded."),
    }
    receipt_path.write_bytes((json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return {"file": str(path), "sha256": sha, "receipt": str(receipt_path),
            "receipt_sha256": keybuild.digest_file(receipt_path), "rows": len(lines),
            "query_mean_sha256_f8le": receipt["centring"]["query_mean_sha256_f8le"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--roster", required=True, choices=sorted(ROSTERS))
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        print(json.dumps({"error": "PYTHONDONTWRITEBYTECODE=1 is required"}), file=sys.stderr)
        return 1
    root = Path(args.data_root).resolve()
    out_root = Path(args.output_root).resolve() if args.output_root else root
    print(json.dumps(build(Path(args.repo_root).resolve(), root, out_root, args.roster), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
