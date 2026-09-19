#!/usr/bin/env python3
"""CLI: freeze ``SLURP-DEV-2000-V1``, the grown SLURP development roster.

Owner decision 34 of 2026-09-19 (``docs/readiness/2026-09-16-slurp-next-stage-
owner-decisions-v1.md``): the fair-comparison development roster grows from the
sealed DEV-1000 to DEV-2000 -- the sealed 1,000 recordings plus 1,000 further
``devel`` recordings drawn with the same stratification, receipted as a roster.

IDENTITY ONLY, ZERO CONTACTS. The SLURP ``devel`` split is read through the
production loader for utterance id, recording id, channel and scenario;
scenario STRATIFIES the draw and is published as an AGGREGATE allocation, never
beside a sample id -- the DEV-ladder discipline (``scripts/build_dev_ladder.py``)
that ``scripts/build_slurp_dev500b_roster.py`` also keeps. No model, tokenizer,
embedder, scorer, network, GPU or audio decode is reached. The one text read is
bounded and digest-only (see "Text disjointness" below).

The capacity finding that shapes this roster
--------------------------------------------
``devel`` carries 8,690 recordings of 2,033 utterances. The DEV ladder already
consumed 1,000 utterances (DEV-1000), reserved 60 (FINAL60) and inherited 60
exposure-heavy ones (the historic probe-60), so exactly 913 utterances remain.
"1,000 further recordings, one per never-used utterance" is therefore
ARITHMETICALLY IMPOSSIBLE, and two deviations are unavoidable to reach 1,000
rows while keeping utterance-level disjointness from the sealed DEV-1000:

1. ``SLURP-DEV-500-B-V1`` -- 500 of those 913 utterances, frozen 2026-09-05 as a
   RESERVED, UNOPENED rung-3 replication roster -- is ABSORBED, its 500 exact
   recordings taken verbatim so the reserved roster survives as an exact
   sub-table of this one rather than being redrawn away.
2. 87 of the 913 utterances contribute a SECOND recording, because 913 < 1,000.
   No utterance contributes more than two, and no added utterance is a DEV-1000,
   FINAL60 or probe-60 utterance.

Both are recorded in the receipt's ``deviations`` block, not merely here.

The draw (seed 20260919, ``core.roster.freeze_roster`` throughout)
------------------------------------------------------------------
* Stage 1 -- the 500 ``SLURP-DEV-500-B-V1`` recordings, verbatim.
* Stage 2 -- the remaining 413 eligible utterances, one recording each: quotas
  equal each scenario's surviving capacity (the whole remainder is taken, so no
  quota choice is made), ``exclude_groups`` keys every recording by its
  utterance so at most one recording per utterance is selected and an excluded
  utterance takes all of its recordings with it.
* Stage 3 -- 87 SECOND recordings of stage-1/stage-2 utterances, apportioned by
  ``core.roster.mixture_quotas`` against the FULL devel scenario mixture and
  capped by capacity, ``exclude_groups`` again so no utterance reaches three.

Text disjointness
-----------------
Construction pools in this study are TRAIN-only by loader construction
(``data.slurp.load_slurp_construction_utterances`` cannot reach devel at all),
so id-level disjointness from every construction roster is structural and is
still proven id by id here. The TEXT proof follows the decontamination
precedent (``scripts/build_slurp_evo_decontamination.py``): sentences are read
inside one generator, compared as word 6-gram and whole-sentence SHA-256
digests, and what leaves this module is COUNTS plus a digest-set hash -- never a
sentence, never a gram. The same numbers are computed for the sealed DEV-1000
half, so the added half's contamination profile is read against a calibrated
baseline rather than in the abstract.

Run in WSL2 (the governed SLURP release is under ``$SPEECHRL_DATA_DIR``)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_dev2000_roster.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    RosterItem,
    freeze_roster,
    mixture_quotas,
    verify_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _governed_roots as governed_roots,
    load_slurp_construction_utterances,
    load_slurp_split,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.rails.proposer import (  # noqa: E402
    DECONTAMINATION_NGRAM,
    ngram_digest,
    word_ngrams,
)

CARRIER = "slurp"
SEED = 20260919
ADDED_TOTAL = 1000
ADDED_ROSTER_ID = "SLURP-DEV-2000-ADDED-V1"
FULL_ROSTER_ID = "SLURP-DEV-2000-V1"
ADDED_RELPATH = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
FULL_RELPATH = "docs/receipts/rosters/slurp-dev-2000-v1.json"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-19-slurp-dev-2000-roster"
)
AUTHORITY = (
    "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md owner decision 34 "
    "of 2026-09-19"
)
GENERATOR = "scripts/build_slurp_dev2000_roster.py"

DEV1000_RELPATH = "docs/receipts/probe-samples/DEV-1000.json"
FINAL60_RELPATH = "docs/receipts/probe-samples/FINAL60.json"
PROBE60_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"
DEV500B_RELPATH = "docs/receipts/rosters/slurp-dev-500-b-v1.json"
SPLIT_IDENTITY_RELPATH = "docs/receipts/knowledge/slurp-split-identity.json"

#: Every committed TRAIN construction roster, proven id-disjoint the hard way
#: rather than by the "different split" argument alone.
CONSTRUCTION_ROSTERS: tuple[str, ...] = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/rosters/slurp-evo-exemplars-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-a-v1.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v1.json",
    "docs/receipts/rosters/slurp-evo-exemplars-v1.json",
    "docs/receipts/rosters/slurp-evo-s1-proposer-r01.json",
    "docs/receipts/rosters/slurp-native-tools-engineering-4-v1.json",
)


def utterance_of(sample_id: str) -> str:
    return sample_id.rsplit(":", 1)[0]


def slurp_id_of(sample_id: str) -> str:
    return sample_id.split(":")[2]


def is_headset(media_relpath: str) -> bool:
    return "-headset" in Path(media_relpath).name


def read_json(relpath: str) -> dict:
    return json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))


def receipt_sample_ids(relpath: str) -> tuple[str, ...]:
    """The sample ids of a committed probe-sample or roster receipt."""

    document = read_json(relpath)
    ids: list[str] = []
    for item in document["items"]:
        value = item.get("sample_id") or item.get("id")
        if not isinstance(value, str) or not value:
            raise SystemExit(f"{relpath} carries a malformed item")
        ids.append(value)
    if len(set(ids)) != len(ids):
        raise SystemExit(f"{relpath} repeats a sample id")
    return tuple(ids)


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def sha256_file(relpath: str) -> str:
    return hashlib.sha256((REPO_ROOT / relpath).read_bytes()).hexdigest()


def digest_set_hash(digests: set[str]) -> str:
    return hashlib.sha256("\n".join(sorted(digests)).encode("utf-8")).hexdigest()


def devel_sentences(metadata_dir: Path, wanted: Sequence[str]) -> Iterator[str]:
    """The ``sentence`` field of exactly the wanted devel utterances.

    A generator on purpose, carried verbatim from
    ``scripts/build_slurp_evo_decontamination.py``: no caller holds the corpus,
    and what leaves this module is digests and counts.
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
            f"{len(remaining)} wanted devel utterance(s) absent from devel.jsonl"
        )


def text_profile(
    metadata_dir: Path,
    wanted_slurp_ids: Sequence[str],
    construction_sentence_digests: frozenset[str],
    construction_gram_digests: frozenset[str],
) -> dict[str, object]:
    """Digest-only text profile of one devel population against TRAIN."""

    sentence_digests: set[str] = set()
    gram_digests: set[str] = set()
    exact_sentence_hits = 0
    sharing_gram = 0
    utterances = 0
    for sentence in devel_sentences(metadata_dir, wanted_slurp_ids):
        utterances += 1
        normalized = " ".join(sentence.lower().split())
        sentence_digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        sentence_digests.add(sentence_digest)
        if sentence_digest in construction_sentence_digests:
            exact_sentence_hits += 1
        grams = {ngram_digest(gram) for gram in word_ngrams(sentence, DECONTAMINATION_NGRAM)}
        gram_digests |= grams
        if grams & construction_gram_digests:
            sharing_gram += 1
    return {
        "utterances_read": utterances,
        "distinct_sentence_digests": len(sentence_digests),
        "exact_sentence_matches_in_train_construction_pool": exact_sentence_hits,
        "utterances_sharing_a_train_6gram": sharing_gram,
        "sentence_digest_set_sha256": digest_set_hash(sentence_digests),
        "gram_digest_set_sha256": digest_set_hash(gram_digests),
    }


def enrich(sample_id: str, record_by_id: Mapping[str, object]) -> dict[str, object]:
    record = record_by_id[sample_id]
    return {
        "sample_id": sample_id,
        "id": sample_id,
        "key": f"{CARRIER}:{sample_id}",
        "utterance_id": utterance_of(sample_id),
        "headset": is_headset(record.media_relpath),  # type: ignore[attr-defined]
        "audio_seconds": round(float(record.audio_seconds), 9),  # type: ignore[attr-defined]
    }


def identity_block(items: Sequence[Mapping[str, object]]) -> dict[str, object]:
    ids = [str(item["sample_id"]) for item in items]
    return {
        "count": len(ids),
        "split_identity_hash": split_identity_hash(prefixed(CARRIER, ids)),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipts")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    records = load_slurp_split(lock, root, "devel")
    record_by_id = {record.sample_id: record for record in records}

    scenario_by_utterance: dict[str, str] = {}
    recordings_by_utterance: dict[str, list[str]] = defaultdict(list)
    for record in records:
        utterance = utterance_of(record.sample_id)
        scenario_by_utterance[utterance] = record.scenario
        recordings_by_utterance[utterance].append(record.sample_id)
    for utterance in recordings_by_utterance:
        recordings_by_utterance[utterance].sort()
    devel_mixture = Counter(scenario_by_utterance.values())

    dev1000_ids = receipt_sample_ids(DEV1000_RELPATH)
    final60_ids = receipt_sample_ids(FINAL60_RELPATH)
    probe60_ids = receipt_sample_ids(PROBE60_RELPATH)
    dev500b_ids = receipt_sample_ids(DEV500B_RELPATH)
    if len(dev1000_ids) != 1000 or len(final60_ids) != 60 or len(probe60_ids) != 60:
        raise SystemExit("the sealed DEV-1000 / FINAL60 / probe-60 receipts changed shape")
    if len(dev500b_ids) != 500:
        raise SystemExit("SLURP-DEV-500-B-V1 no longer carries 500 items")
    for name, ids in (
        ("DEV-1000", dev1000_ids),
        ("FINAL60", final60_ids),
        ("probe-60", probe60_ids),
        ("DEV-500-B", dev500b_ids),
    ):
        missing = [sid for sid in ids if sid not in record_by_id]
        if missing:
            raise SystemExit(f"{name} names {len(missing)} id absent from the devel loader")

    dev1000_utterances = {utterance_of(sid) for sid in dev1000_ids}
    final60_utterances = {utterance_of(sid) for sid in final60_ids}
    probe60_utterances = {utterance_of(sid) for sid in probe60_ids}
    dev500b_utterances = {utterance_of(sid) for sid in dev500b_ids}
    blocked = dev1000_utterances | final60_utterances | probe60_utterances
    if dev500b_utterances & blocked:
        raise SystemExit("SLURP-DEV-500-B-V1 overlaps a blocked utterance set")
    eligible_utterances = set(scenario_by_utterance) - blocked
    if not dev500b_utterances <= eligible_utterances:
        raise SystemExit("SLURP-DEV-500-B-V1 is not inside the eligible remainder")

    # ---- stage 1: absorb the reserved rung-3 roster verbatim --------------
    stage1 = sorted(dev500b_ids)

    # ---- stage 2: the whole remaining utterance pool, one recording each --
    stage2_pool_utterances = eligible_utterances - dev500b_utterances
    stage2_capacity = Counter(
        scenario_by_utterance[utterance] for utterance in stage2_pool_utterances
    )
    stage2_quotas = {
        scenario: int(stage2_capacity.get(scenario, 0)) for scenario in sorted(devel_mixture)
    }
    candidates = [
        RosterItem(
            sample_id=record.sample_id,
            stratum=record.scenario,
            extra={"utterance_id": utterance_of(record.sample_id)},
        )
        for record in records
    ]
    groups = {record.sample_id: utterance_of(record.sample_id) for record in records}
    stage2_excluded_ids = [
        sample_id
        for utterance in sorted(blocked | dev500b_utterances)
        for sample_id in recordings_by_utterance.get(utterance, ())
    ]
    stage2_receipt = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=candidates,
        per_stratum=stage2_quotas,
        seed=SEED,
        split_role="dev",
        exclude_sample_ids=stage2_excluded_ids,
        exclude_groups=groups,
        roster_id=f"{ADDED_ROSTER_ID}-STAGE2",
        roster_role="evaluation",
    )
    stage2 = sorted(str(item["sample_id"]) for item in stage2_receipt["items"])
    if len(stage2) != len(stage2_pool_utterances):
        raise SystemExit("stage 2 did not take the whole remaining utterance pool")

    # ---- stage 3: second recordings, mixture-apportioned ------------------
    added_utterances = dev500b_utterances | {utterance_of(sid) for sid in stage2}
    used_ids = set(stage1) | set(stage2)
    stage3_total = ADDED_TOTAL - len(used_ids)
    if stage3_total < 0:
        raise SystemExit("stages 1+2 already exceed the added total")
    stage3_candidates = [
        RosterItem(
            sample_id=record.sample_id,
            stratum=record.scenario,
            extra={"utterance_id": utterance_of(record.sample_id)},
        )
        for record in records
        if utterance_of(record.sample_id) in added_utterances
        and record.sample_id not in used_ids
    ]
    stage3_capacity = Counter(
        scenario_by_utterance[utterance]
        for utterance in sorted(
            {utterance_of(item.sample_id) for item in stage3_candidates}
        )
    )
    stage3_quotas = mixture_quotas(stage3_total, devel_mixture, stage3_capacity)
    stage3_receipt = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=stage3_candidates,
        per_stratum=stage3_quotas,
        seed=SEED,
        split_role="dev",
        exclude_groups={item.sample_id: groups[item.sample_id] for item in stage3_candidates},
        roster_id=f"{ADDED_ROSTER_ID}-STAGE3",
        roster_role="evaluation",
    )
    stage3 = sorted(str(item["sample_id"]) for item in stage3_receipt["items"])

    added_ids = sorted(set(stage1) | set(stage2) | set(stage3))
    if len(added_ids) != ADDED_TOTAL:
        raise SystemExit(
            f"added roster resolved {len(added_ids)} recordings, expected {ADDED_TOTAL}"
        )
    recordings_per_added_utterance = Counter(utterance_of(sid) for sid in added_ids)
    if max(recordings_per_added_utterance.values()) > 2:
        raise SystemExit("an added utterance contributed more than two recordings")

    added_items = [enrich(sid, record_by_id) for sid in added_ids]
    dev1000_items = [enrich(sid, record_by_id) for sid in sorted(dev1000_ids)]
    full_items = dev1000_items + added_items
    full_items.sort(key=lambda item: str(item["sample_id"]))
    if len({str(item["sample_id"]) for item in full_items}) != 2000:
        raise SystemExit("DEV-2000 does not carry 2,000 distinct recordings")

    # ---- disjointness proofs ---------------------------------------------
    split_identity = read_json(SPLIT_IDENTITY_RELPATH)
    test_ids = set(split_identity["splits"]["test"]["ids"])
    devel_ids_frozen = set(split_identity["splits"]["devel"]["ids"])
    construction_ids: set[str] = set()
    construction_sources: list[dict[str, object]] = []
    for relpath in CONSTRUCTION_ROSTERS:
        ids = set(receipt_sample_ids(relpath))
        construction_sources.append(
            {
                "relpath": relpath,
                "items": len(ids),
                "receipt_file_sha256": sha256_file(relpath),
                "shared_with_added": len(ids & set(added_ids)),
            }
        )
        construction_ids |= ids

    added_id_set = set(added_ids)
    added_utterance_set = {utterance_of(sid) for sid in added_ids}
    disjointness = {
        "shared_with_dev1000_recordings": len(added_id_set & set(dev1000_ids)),
        "shared_with_dev1000_utterances": len(added_utterance_set & dev1000_utterances),
        "shared_with_final60_utterances": len(added_utterance_set & final60_utterances),
        "shared_with_probe60_utterances": len(added_utterance_set & probe60_utterances),
        "shared_with_test_recordings": len(added_id_set & test_ids),
        "shared_with_train_construction_recordings": len(added_id_set & construction_ids),
        "non_devel_ids_added": len(added_id_set - devel_ids_frozen),
        "max_recordings_per_added_utterance": max(recordings_per_added_utterance.values()),
        "added_utterances_with_two_recordings": sum(
            1 for count in recordings_per_added_utterance.values() if count == 2
        ),
    }
    for key, value in disjointness.items():
        if key.startswith("shared_with") and value:
            raise SystemExit(f"DEV-2000 disjointness proof failed: {key} = {value}")
    if disjointness["non_devel_ids_added"]:
        raise SystemExit("an added id is not a member of the frozen devel enumeration")

    # ---- text proof (digest only) ----------------------------------------
    construction_pool = load_slurp_construction_utterances(lock, root)
    construction_sentence_digests: set[str] = set()
    construction_gram_digests: set[str] = set()
    for row in construction_pool.utterances:
        text = " ".join(row.tokens)
        if not text:
            continue
        construction_sentence_digests.add(
            hashlib.sha256(" ".join(text.lower().split()).encode("utf-8")).hexdigest()
        )
        construction_gram_digests |= {
            ngram_digest(gram) for gram in word_ngrams(text, DECONTAMINATION_NGRAM)
        }
    _, _, metadata_dir = governed_roots(lock, root)
    added_profile = text_profile(
        metadata_dir,
        sorted({slurp_id_of(sid) for sid in added_ids}),
        frozenset(construction_sentence_digests),
        frozenset(construction_gram_digests),
    )
    dev1000_profile = text_profile(
        metadata_dir,
        sorted({slurp_id_of(sid) for sid in dev1000_ids}),
        frozenset(construction_sentence_digests),
        frozenset(construction_gram_digests),
    )
    shared_sentence_digests = (
        added_profile["sentence_digest_set_sha256"] == dev1000_profile["sentence_digest_set_sha256"]
    )
    if shared_sentence_digests:
        raise SystemExit("the added half and DEV-1000 resolved the same sentence set")

    text_block = {
        "method": (
            "Digest only, after scripts/build_slurp_evo_decontamination.py: sentences are "
            "read inside one generator, compared as whole-sentence SHA-256 digests and as "
            f"word {DECONTAMINATION_NGRAM}-gram digests (rails.proposer.word_ngrams / "
            "ngram_digest), and only counts and digest-set hashes are written. No sentence "
            "and no gram is written anywhere."
        ),
        "train_construction_pool": {
            "pool_id": construction_pool.pool_id,
            "utterance_count": construction_pool.utterance_count,
            "source_identity_hash": construction_pool.source_identity_hash,
            "sentence_digests": len(construction_sentence_digests),
            "gram_digests": len(construction_gram_digests),
        },
        "added": added_profile,
        "dev1000_baseline": dev1000_profile,
        "reading": (
            "Construction pools are TRAIN-only by loader construction, so the id-level "
            "proof is structural; these counts say how much of the added half's TEXT a "
            "TRAIN-built knowledge store could already contain, measured against the "
            "sealed DEV-1000 half under the identical method."
        ),
    }

    # ---- receipts ---------------------------------------------------------
    added_scenarios = Counter(
        scenario_by_utterance[utterance_of(sid)] for sid in added_ids
    )
    full_scenarios = Counter(
        scenario_by_utterance[utterance_of(str(item["sample_id"]))] for item in full_items
    )
    dev1000_scenarios = Counter(
        scenario_by_utterance[utterance_of(sid)] for sid in dev1000_ids
    )
    channel_counts = {
        "added": {
            "headset": sum(1 for item in added_items if item["headset"]),
            "far_field": sum(1 for item in added_items if not item["headset"]),
        },
        "dev1000": {
            "headset": sum(1 for item in dev1000_items if item["headset"]),
            "far_field": sum(1 for item in dev1000_items if not item["headset"]),
        },
    }
    candidate_pool = {
        "devel_recordings": len(records),
        "devel_utterances": len(scenario_by_utterance),
        "blocked_utterances": len(blocked),
        "eligible_utterances": len(eligible_utterances),
        "eligible_recordings": sum(
            len(recordings_by_utterance[utterance]) for utterance in eligible_utterances
        ),
        "eligible_utterances_by_scenario": dict(
            sorted(
                Counter(
                    scenario_by_utterance[utterance] for utterance in eligible_utterances
                ).items()
            )
        ),
        "devel_mixture_by_scenario": dict(sorted(devel_mixture.items())),
        "blocked_sources": [
            {"relpath": DEV1000_RELPATH, "utterances": len(dev1000_utterances)},
            {"relpath": FINAL60_RELPATH, "utterances": len(final60_utterances)},
            {"relpath": PROBE60_RELPATH, "utterances": len(probe60_utterances)},
        ],
    }
    composition = {
        "stage_1_dev500b_verbatim": len(stage1),
        "stage_2_remaining_utterances": len(stage2),
        "stage_3_second_recordings": len(stage3),
        "distinct_added_utterances": len(added_utterance_set),
    }
    deviations = [
        {
            "id": "DEV2000-D1",
            "statement": (
                "SLURP-DEV-500-B-V1, frozen 2026-09-05 as a RESERVED and UNOPENED rung-3 "
                "replication roster, is absorbed whole into the added half; its 500 exact "
                "recordings are taken verbatim, so it survives as an exact sub-table of "
                "DEV-2000 and its 500-row read stays recoverable, but it stops being "
                "reserved the moment the DEV-2000 comparators fly."
            ),
            "why_unavoidable": (
                "Only 913 devel utterances survive the DEV-1000 / FINAL60 / probe-60 "
                "exclusions, and 413 of them (9 of 18 scenarios) remain if DEV-500-B is "
                "held back -- too few for 1,000 rows and too narrow for a per-stratum "
                "table."
            ),
            "owner_action": "acknowledge or redirect before the comparator flights fly",
        },
        {
            "id": "DEV2000-D2",
            "statement": (
                f"{len(stage3)} of the {len(added_utterance_set)} added utterances "
                "contribute a SECOND recording, because 913 < 1,000. No utterance "
                "contributes three, and paired analyses must cluster by utterance_id."
            ),
            "why_unavoidable": "Arithmetic: the devel remainder is 913 utterances.",
            "owner_action": (
                "accept 1,000 rows over 913 utterances, or accept a 913-row addition "
                "(DEV-1913) instead"
            ),
        },
        {
            "id": "DEV2000-D3",
            "statement": (
                "The added half cannot reproduce DEV-1000's equal-per-scenario allocation: "
                "the ladder already drained alarm, audio, cooking, datetime, music, news, "
                "recommendation, social and takeaway. Stage 2 takes the whole remainder, so "
                "no quota choice is made, and stage 3 apportions its 87 seats against the "
                "full devel mixture."
            ),
            "why_unavoidable": "Capacity, not choice; see eligible_utterances_by_scenario.",
            "owner_action": (
                "report every DEV-2000 verdict under both natural-mixture and "
                "equal-stratum weighting, per the 2026-09-03 reporting rule"
            ),
        },
    ]
    common = {
        "authority": AUTHORITY,
        "generator": GENERATOR,
        "seed": SEED,
        "carrier_lock_key": CARRIER,
        "split_role": "dev",
        "roster_role": "evaluation",
        "schema": "saea-roster-receipt-v1",
        "status": "FROZEN; MODEL-FREE, ZERO CONTACTS",
        "item_fields": ["audio_seconds", "headset", "id", "key", "sample_id", "utterance_id"],
        "stratum_withheld_per_item": True,
        "selection_rule": (
            "Stage 1 takes the 500 SLURP-DEV-500-B-V1 recordings verbatim. Stage 2 freezes "
            "the whole remaining eligible utterance pool through core.roster.freeze_roster "
            "(seed 20260919, quotas equal to each scenario's surviving capacity, "
            "exclude_groups keyed by utterance so at most one recording per utterance is "
            "selected and an excluded utterance takes all of its recordings with it). "
            "Stage 3 freezes second recordings of stage-1/stage-2 utterances through the "
            "same function, apportioned by core.roster.mixture_quotas against the full "
            "devel scenario mixture and capped by capacity, with exclude_groups again so no "
            "utterance reaches three recordings."
        ),
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
        "split_identity_receipt": {
            "relpath": SPLIT_IDENTITY_RELPATH,
            "devel_identity_hash": split_identity["splits"]["devel"]["identity_hash"],
            "devel_ids": split_identity["splits"]["devel"]["count"],
            "test_identity_hash": split_identity["splits"]["test"]["identity_hash"],
            "test_ids": split_identity["splits"]["test"]["count"],
        },
        "one_shot_rule": (
            "The DEV-2000 direct baseline and the DEV-2000 anchor fly ONCE on the added "
            "rows and are never re-flown; a later mechanism is compared against those "
            "sealed outputs, not against a fresh comparator pass."
        ),
        "target_gold_opened_before_receipt": False,
    }

    added_receipt = {
        **common,
        "roster_id": ADDED_ROSTER_ID,
        "design": (
            "The 1,000 devel recordings ADDED to the sealed DEV-1000 by owner decision 34. "
            "This is the roster the DEV-2000 comparator flights bind: the sealed half is "
            "already flown and is never re-flown."
        ),
        "parent_rosters": {
            "sealed_half": {
                "relpath": DEV1000_RELPATH,
                "roster_id": "DEV-1000",
                "count": len(dev1000_ids),
                "receipt_file_sha256": sha256_file(DEV1000_RELPATH),
                "run_identity_hash": read_json(DEV1000_RELPATH)["run_identity_hash"],
            },
            "absorbed": {
                "relpath": DEV500B_RELPATH,
                "roster_id": "SLURP-DEV-500-B-V1",
                "count": len(dev500b_ids),
                "receipt_file_sha256": sha256_file(DEV500B_RELPATH),
                "split_identity_hash": read_json(DEV500B_RELPATH)["split_identity_hash"],
            },
        },
        "composition": composition,
        "candidate_pool": candidate_pool,
        "scenario_allocation": dict(sorted(added_scenarios.items())),
        "channel_counts": channel_counts["added"],
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in added_items), 9
        ),
        "disjointness_proof": disjointness,
        "construction_rosters_checked": construction_sources,
        "text_disjointness": text_block,
        "deviations": deviations,
        "items": added_items,
        "excluded_count": len(records) - len(added_ids),
        "per_stratum": {
            "stage_2": dict(sorted(stage2_quotas.items())),
            "stage_3": dict(sorted(stage3_quotas.items())),
        },
        "strata_counts": dict(sorted(added_scenarios.items())),
        "split_identity_hash": identity_block(added_items)["split_identity_hash"],
    }

    full_receipt = {
        **common,
        "roster_id": FULL_ROSTER_ID,
        "design": (
            "The grown SLURP development roster: the 1,000 sealed DEV-1000 recordings plus "
            f"the {ADDED_TOTAL} recordings of {ADDED_ROSTER_ID}. Its halves keep separate "
            "identities on purpose -- the sealed half already has comparator outputs and is "
            "never re-flown, and only the added half is ever dispatched."
        ),
        "halves": {
            "sealed_dev1000": {
                "relpath": DEV1000_RELPATH,
                "count": len(dev1000_ids),
                "split_identity_hash": identity_block(dev1000_items)["split_identity_hash"],
                "run_identity_hash": read_json(DEV1000_RELPATH)["run_identity_hash"],
                "scenario_allocation": dict(sorted(dev1000_scenarios.items())),
                "channel_counts": channel_counts["dev1000"],
            },
            "added": {
                "relpath": ADDED_RELPATH,
                "count": len(added_ids),
                "split_identity_hash": identity_block(added_items)["split_identity_hash"],
                "scenario_allocation": dict(sorted(added_scenarios.items())),
                "channel_counts": channel_counts["added"],
            },
        },
        "composition": composition,
        "candidate_pool": candidate_pool,
        "scenario_allocation": dict(sorted(full_scenarios.items())),
        "channel_counts": {
            "headset": channel_counts["added"]["headset"] + channel_counts["dev1000"]["headset"],
            "far_field": channel_counts["added"]["far_field"]
            + channel_counts["dev1000"]["far_field"],
        },
        "distinct_utterances": len(
            {utterance_of(str(item["sample_id"])) for item in full_items}
        ),
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in full_items), 9
        ),
        "disjointness_proof": disjointness,
        "text_disjointness": text_block,
        "deviations": deviations,
        "items": full_items,
        "excluded_count": len(records) - len(full_items),
        "per_stratum": dict(sorted(full_scenarios.items())),
        "strata_counts": dict(sorted(full_scenarios.items())),
        "split_identity_hash": identity_block(full_items)["split_identity_hash"],
    }

    verify_roster(added_receipt)
    verify_roster(full_receipt)

    summary = {
        "added_roster_id": ADDED_ROSTER_ID,
        "added_split_identity_hash": added_receipt["split_identity_hash"],
        "full_roster_id": FULL_ROSTER_ID,
        "full_split_identity_hash": full_receipt["split_identity_hash"],
        "composition": composition,
        "added_scenario_allocation": added_receipt["scenario_allocation"],
        "dev1000_scenario_allocation": dict(sorted(dev1000_scenarios.items())),
        "full_scenario_allocation": full_receipt["scenario_allocation"],
        "channel_counts": channel_counts,
        "disjointness_proof": disjointness,
        "text_disjointness": {
            "added": added_profile,
            "dev1000_baseline": dev1000_profile,
        },
        "audio_seconds_total_added": added_receipt["audio_seconds_total"],
        "audio_seconds_total_full": full_receipt["audio_seconds_total"],
        "offline_guard": common["offline_guard"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.write:
        write_roster(added_receipt, REPO_ROOT / ADDED_RELPATH)
        write_roster(full_receipt, REPO_ROOT / FULL_RELPATH)
        check_dir = REPO_ROOT / CHECK_DIR
        check_dir.mkdir(parents=True, exist_ok=True)
        proof = {
            "schema": "saea-dev2000-roster-disjointness-v1",
            "study": "speech-aware-evidence-acquisition",
            "authority": AUTHORITY,
            "generator": GENERATOR,
            "rosters": {
                ADDED_ROSTER_ID: {
                    "relpath": ADDED_RELPATH,
                    "split_identity_hash": added_receipt["split_identity_hash"],
                    "receipt_file_sha256": sha256_file(ADDED_RELPATH),
                },
                FULL_ROSTER_ID: {
                    "relpath": FULL_RELPATH,
                    "split_identity_hash": full_receipt["split_identity_hash"],
                    "receipt_file_sha256": sha256_file(FULL_RELPATH),
                },
            },
            "disjointness_proof": disjointness,
            "construction_rosters_checked": construction_sources,
            "text_disjointness": text_block,
            "candidate_pool": candidate_pool,
            "composition": composition,
            "deviations": deviations,
            "offline_guard": common["offline_guard"],
        }
        proof["proof_sha256"] = canonical_sha256(proof)
        (check_dir / "disjointness.json").write_text(
            json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {ADDED_RELPATH}")
        print(f"wrote {FULL_RELPATH}")
        print(f"wrote {CHECK_DIR}/disjointness.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
