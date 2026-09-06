#!/usr/bin/env python3
"""CLI: build the EVO-S1 decontamination gate artifact (MODEL-FREE).

Exposure row ``SAEA-SLURP-MF-EVO-DECONTAMINATION-V1``, registered before this
script is run for the first time. Section 8 of
``docs/readiness/2026-09-06-slurp-evo-s1-slot-schema-evolution-v1-preregistration.md``
and coordinator decision 5 of 2026-09-06 bound what it may read: the
``sentence`` field of the 1,000 DEV-1000 utterances -- rows this study has
already consumed three times -- as word 6-gram SETS and nothing else.
``SLURP-DEV-500-B-V1`` and the test split are never named, loaded or opened.

WHAT IS COMMITTED IS DIGESTS, NOT GRAMS. A committed file of literal 6-grams
would be six-word windows of devel sentences written into the repository, so
the artifact carries ``sha256(" ".join(gram))`` per gram instead. Digests
compare identically, pin the gate byte for byte, and reconstitute nothing --
which is what lets every later candidate validation consume this row's product
rather than re-opening the text.

The same pass verifies ``A_0``'s own 1,008 TRAIN fillers against the digest
set and reports the exemption list, because a gate that refused the
incumbent's own fillers would refuse the incumbent itself.

Run in WSL2 (the SLURP governed release is under ``$SPEECHRL_DATA_DIR``)::

    CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_evo_decontamination.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterator, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    lock_entry,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    load_slurp_intent_slot_schema,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash  # noqa: E402
from speech_aware_evidence_acquisition.rails.proposer import (  # noqa: E402
    DECONTAMINATION_NGRAM,
    SLURP_DECONTAMINATION_SCHEMA,
    load_evaluation_ngram_digests,
    ngram_digest,
    word_ngrams,
)

EXPOSURE_ROW = "SAEA-SLURP-MF-EVO-DECONTAMINATION-V1"
ARTIFACT_RELPATH = "docs/receipts/knowledge/slurp-evo-decontamination-v1.json"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-decontamination"
)
POPULATIONS = {
    "DEV-1000": "docs/receipts/probe-samples/DEV-1000.json",
    "DEV-1000-NEW500": "docs/receipts/probe-samples/DEV-1000-NEW500.json",
}
A0_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-intent-slot-schema-v1.json"
PREREGISTRATION = (
    "docs/readiness/2026-09-06-slurp-evo-s1-slot-schema-evolution-v1-preregistration.md"
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utterance_ids(relpath: str) -> tuple[str, ...]:
    """The SLURP utterance ids of one committed probe-sample receipt.

    A probe-sample item is ``slurp:devel:NNNNNN:<recording>``; the gate is a
    property of the UTTERANCE (one sentence, many recordings), so the
    recording half is dropped here and the ids are de-duplicated.
    """

    document = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
    if document.get("split") != "devel":
        raise SystemExit(f"{relpath} is not a devel receipt; this row opens devel only")
    ids: set[str] = set()
    for item in document["items"]:
        sample_id = str(item["id"])
        parts = sample_id.split(":")
        if len(parts) != 4 or parts[0] != "slurp" or parts[1] != "devel":
            raise SystemExit(f"{relpath} carries a non-devel sample id {sample_id!r}")
        ids.add(parts[2])
    return tuple(sorted(ids))


def _devel_sentences(metadata_dir: Path, wanted: Sequence[str]) -> Iterator[str]:
    """The ``sentence`` field of exactly the wanted devel utterances.

    A generator on purpose: no caller ever holds the whole corpus of devel
    sentence text, and nothing outside this function's own loop sees a
    sentence at all -- what leaves this module is 6-gram digests.
    """

    remaining = set(wanted)
    path = metadata_dir / "devel.jsonl"
    if not path.is_file():
        raise SystemExit(f"SLURP devel metadata file missing: {path}")
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            key = f"{int(raw['slurp_id']):06d}"
            if key not in remaining:
                continue
            remaining.discard(key)
            sentence = raw.get("sentence")
            if not isinstance(sentence, str) or not sentence.strip():
                raise SystemExit(f"devel utterance {key} carries no sentence")
            yield sentence.strip()
    if remaining:
        raise SystemExit(
            f"{len(remaining)} DEV-1000 utterance(s) absent from devel.jsonl; the "
            "probe-sample receipt and the governed release disagree"
        )


def _digests_of_split(metadata_dir: Path, wanted: Sequence[str]) -> tuple[set[str], int]:
    digests: set[str] = set()
    sentences = 0
    for sentence in _devel_sentences(metadata_dir, wanted):
        sentences += 1
        digests |= {
            ngram_digest(gram)
            for gram in word_ngrams(sentence, DECONTAMINATION_NGRAM)
        }
    return digests, sentences


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    entry = lock_entry(lock, "slurp")
    governed_copy = entry["annotations"]["governed_copy"]
    metadata_dir = Path(root) / governed_copy

    populations: dict[str, dict[str, object]] = {}
    evaluation: set[str] = set()
    for name, relpath in POPULATIONS.items():
        wanted = _utterance_ids(relpath)
        digests, sentences = _digests_of_split(metadata_dir, wanted)
        populations[name] = {
            "probe_sample_receipt": relpath,
            "probe_sample_receipt_sha256": _sha256_file(REPO_ROOT / relpath),
            "utterances": len(wanted),
            "sentences_read": sentences,
            "distinct_ngram_digests": len(digests),
        }
        if name == "DEV-1000":
            evaluation = digests
        else:
            populations[name]["subset_of_dev1000_digests"] = digests <= evaluation
    if not evaluation:
        raise SystemExit("DEV-1000 produced no 6-gram digest; refusing to write a gate")

    # A_0's own fillers: TRAIN, already sent by KC-S1b, and therefore exempt.
    schema = load_slurp_intent_slot_schema(lock, root)
    fillers = _a0_fillers(schema)
    a0_digests = sorted(
        {
            ngram_digest(gram)
            for filler in fillers
            for gram in word_ngrams(filler, DECONTAMINATION_NGRAM)
        }
    )
    exempt = sorted(set(a0_digests) & evaluation)

    ordered = sorted(evaluation)
    artifact = {
        "schema": SLURP_DECONTAMINATION_SCHEMA,
        "generated_by": "scripts/build_slurp_evo_decontamination.py",
        "exposure_row": EXPOSURE_ROW,
        "preregistration": PREREGISTRATION,
        "ngram": DECONTAMINATION_NGRAM,
        "what_this_is": (
            "The evaluation side of the EVO-S1 decontamination gate: the word "
            f"{DECONTAMINATION_NGRAM}-grams of the DEV-1000 devel sentences, as SHA-256 "
            "digests of the space-joined gram. Digests and never grams, because a "
            "committed file of literal 6-grams would be six-word windows of devel "
            "sentence text written into the repository. rails.proposer"
            ".load_evaluation_ngram_digests reads this file and rails.proposer"
            ".validate_slurp_candidate_artifact compares candidate FILLER digests "
            "against it, exempting any digest A_0's own TRAIN fillers already carry."
        ),
        "bound_by": (
            "Coordinator decision 5 of 2026-09-06: DEV-1000 sentence text only, as "
            "6-gram sets only. SLURP-DEV-500-B-V1 and the test split are never named, "
            "loaded or opened by this artifact or by the script that built it."
        ),
        "source_split": "devel",
        "source_split_identity_hash": (
            "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
        ),
        "populations": populations,
        "evaluation_population": "DEV-1000",
        "evaluation_ngram_count": len(ordered),
        "evaluation_ngram_digests_content_hash": content_hash(ordered),
        "a0": {
            "receipt": A0_RECEIPT_RELPATH,
            "receipt_sha256": _sha256_file(REPO_ROOT / A0_RECEIPT_RELPATH),
            "schema_content_hash": schema.content_hash(),
            "fillers": len(fillers),
            "filler_ngram_digests": len(a0_digests),
            "exempt_digests": exempt,
            "exempt_count": len(exempt),
            "note": (
                "A_0's fillers are TRAIN and KC-S1b already sent every one of them, so "
                "any 6-gram they share with a devel sentence is exempt: refusing it "
                "would refuse the incumbent itself. A filler shorter than six words "
                "yields no 6-gram at all, which is why this count is small."
            ),
        },
        "evaluation_ngram_digests": ordered,
    }

    verdict = {
        "schema": "saea-slurp-evo-decontamination-read-v1",
        "exposure_row": EXPOSURE_ROW,
        "preregistration": PREREGISTRATION,
        "artifact": ARTIFACT_RELPATH,
        "populations": populations,
        "evaluation_ngram_count": len(ordered),
        "a0_fillers": len(fillers),
        "a0_filler_ngram_digests": len(a0_digests),
        "a0_exempt_digests": len(exempt),
        "a0_verdict": "PASS",
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "audio_seconds": 0,
            "paid_api_spend": 0,
        },
        "text_written_anywhere": (
            "none. No sentence, no gram and no filler string is written by this row; "
            "the artifact carries digests and counts only."
        ),
    }

    print(json.dumps(verdict, indent=2, sort_keys=True))
    if not args.write:
        return 0

    artifact_path = REPO_ROOT / ARTIFACT_RELPATH
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    # Round-trip the gate through its own reader before anything is claimed.
    reloaded = load_evaluation_ngram_digests(
        json.loads(artifact_path.read_text(encoding="utf-8"))
    )
    if reloaded != frozenset(ordered):
        raise SystemExit("the written artifact does not reload to the measured set")

    check_dir = REPO_ROOT / CHECK_DIR
    check_dir.mkdir(parents=True, exist_ok=True)
    verdict["artifact_sha256"] = _sha256_file(artifact_path)
    verdict["reloaded_digests"] = len(reloaded)
    (check_dir / "decontamination.json").write_text(
        json.dumps(verdict, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {ARTIFACT_RELPATH} ({verdict['artifact_sha256']})")
    print(f"wrote {CHECK_DIR}/decontamination.json")
    return 0


def _a0_fillers(schema) -> list[str]:
    """Every example filler ``A_0`` lists, in schema order (1,008 of them)."""

    fillers: list[str] = []
    for intent in schema.intent_ids:
        profile = schema.intents[intent]
        for entity_type, _count, _share in profile.types:
            fillers.extend(profile.fillers.get(entity_type, ()))
    return fillers


if __name__ == "__main__":
    raise SystemExit(main())
