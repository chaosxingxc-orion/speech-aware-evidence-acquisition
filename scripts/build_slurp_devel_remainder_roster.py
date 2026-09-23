#!/usr/bin/env python3
"""CLI: freeze ``SLURP-DEVEL-REMAINDER-V<n>``, the rest of the SLURP devel split.

Owner decision 107 of 2026-09-23 (``docs/readiness/2026-09-16-slurp-next-stage-
owner-decisions-v1.md``): the development side may expand up to the FULL SLURP
``devel`` split as the development-side validation resource, prepared with the
same pipeline as DEV-2000-ADDED, built ahead of time and in parallel. Two
thirds of that expansion are already sealed -- DEV-1000
(``docs/receipts/probe-samples/DEV-1000.json``, 1,000 recordings) and
DEV-2000-ADDED (``docs/receipts/rosters/slurp-dev-2000-added-v1.json``, 1,000
recordings). This generator freezes the THIRD part: every devel recording that
is in neither, so that

    DEV-1000  U  DEV-2000-ADDED  U  DEVEL-REMAINDER  ==  the complete devel split

and the three parts are pairwise disjoint at recording granularity. Both
identities are proven here id by id, not asserted.

IDENTITY ONLY, ZERO CONTACTS. The SLURP ``devel`` split is read through the
production loader for utterance id, recording id, channel and scenario;
scenario STRATIFIES the take-all freeze and is published as an AGGREGATE
allocation, never beside a sample id -- the DEV-ladder discipline
(``scripts/build_dev_ladder.py``) that ``scripts/build_slurp_dev2000_roster.py``
also keeps. No model, tokenizer, embedder, scorer, network, GPU or audio decode
is reached. The one text read is bounded and digest-only (see "Text
disjointness" below).

The draw is a TAKE-ALL freeze, not a sample
-------------------------------------------
There is nothing to choose: the remainder is defined by subtraction. The draw
is therefore ``core.roster.freeze_roster`` with the WHOLE devel population as
candidates, the two sealed rosters as ``exclude_sample_ids``, and a per-stratum
quota equal to each scenario's surviving capacity -- the same trick
``scripts/build_slurp_stage3_construction_roster.py`` uses to freeze a
pre-selected population through the canonical schema/hash/disjointness
machinery (quota == pool size per stratum, so the shuffle has nothing left to
choose between). Seed 20260923 is recorded for reproducibility even though the
result does not depend on it. ``exclude_groups`` is deliberately NOT used: the
remainder takes EVERY surviving recording, including several recordings of the
same utterance, because "the complete devel split" is the target.

What this roster shares with the two sealed halves
--------------------------------------------------
Recording-level disjointness is exact and proven. UTTERANCE-level disjointness
is IMPOSSIBLE and is reported rather than enforced: devel carries 8,690
recordings of only 2,033 utterances, so most remainder recordings are further
recordings of utterances the sealed halves already read. The receipt's
``utterance_overlap`` block states the counts, and deviation ``REM-D2`` states
the consequence for analysis (cluster by ``utterance_id``; a remainder result
and a DEV-1000/DEV-2000-ADDED result are not independent utterance samples).

Reserved sets inside the remainder, and the carve-out
-----------------------------------------------------
"Everything that is not DEV-1000 or DEV-2000-ADDED" necessarily includes the
60 ``reserved-final-unread`` FINAL60 recordings and the 60 historic probe-60
recordings that the DEV ladder held back. V1 kept them and put the choice to
the owner as deviation ``REM-D1``.

The coordinator ruling of 2026-09-23 (provisional decision 109) answers it: the
remainder must NOT spend the FINAL60 reservation and must stay contact-fresh, so
BOTH sets are carved out and the roster is re-frozen as a NEW version rather
than rewritten in place. ``--exclude-receipt`` is how a carve-out is expressed
on the command line (repeatable, one committed receipt per flag) and
``--version`` is which version is being frozen, so the freeze is reproducible
from a single line::

    python scripts/build_slurp_devel_remainder_roster.py --version 2 \\
      --exclude-receipt docs/receipts/probe-samples/FINAL60.json \\
      --exclude-receipt configs/probes/g0-binding/pslu-sample-devel-n60.json --write

A carve-out is proven, never asserted: the receipt carries the per-receipt and
union counts, a SHA-256 over the sorted excluded id list, the pairwise overlap
between the carved sets, and a ``shared_with_carved_out_*`` line per set in the
disjointness proof. The completeness identity grows a fourth part (DEV-1000 U
DEV-2000-ADDED U CARVED-OUT U REMAINDER == the complete devel split), so nothing
is lost -- it is accounted for.

What a recording-level carve-out does NOT remove is the reserved UTTERANCES:
devel carries several recordings of one utterance, so sibling recordings of the
carved-out utterances stay in the remainder. Their exact count is in
``carved_out_reserved_sets.remainder_recordings_of_carved_out_utterances`` and in
deviation ``REM-D1``; it is reported, not silently absorbed.

Text disjointness
-----------------
Construction pools in this study are TRAIN-only by loader construction
(``data.slurp.load_slurp_construction_utterances`` cannot reach devel at all),
so id-level disjointness from every construction roster is structural and is
still proven id by id here. The TEXT proof follows the decontamination
precedent (``scripts/build_slurp_evo_decontamination.py``) exactly as
``scripts/build_slurp_dev2000_roster.py`` does: sentences are read inside one
generator, compared as word 6-gram and whole-sentence SHA-256 digests, and what
leaves this module is COUNTS plus a digest-set hash -- never a sentence, never
a gram. The same numbers are computed for the sealed DEV-1000 half, so the
remainder's contamination profile is read against a calibrated baseline.

Run in WSL2 (the governed SLURP release is under ``$SPEECHRL_DATA_DIR``)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_devel_remainder_roster.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    RosterItem,
    freeze_roster,
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
SEED = 20260923
DEFAULT_VERSION = 1
AUTHORITY = (
    "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md owner decision 107 "
    "of 2026-09-23"
)
CARVE_OUT_AUTHORITY = (
    "coordinator ruling of 2026-09-23 (provisional decision 109): the remainder must not "
    "spend the FINAL60 reservation and must stay contact-fresh, so both reserved sets are "
    "carved out and the roster is re-frozen as a new version"
)
GENERATOR = "scripts/build_slurp_devel_remainder_roster.py"

#: The label the two DEV-ladder reservations keep wherever they are named, so
#: ``reserved_sets_inside_the_remainder``, ``carved_out_reserved_sets`` and the
#: disjointness proof agree key for key. Any other ``--exclude-receipt`` gets a
#: label derived from its file stem.
CARVE_OUT_LABELS: dict[str, str] = {
    "docs/receipts/probe-samples/FINAL60.json": "final60",
    "configs/probes/g0-binding/pslu-sample-devel-n60.json": "historic_probe60",
}


def roster_id(version: int) -> str:
    """``2`` -> ``SLURP-DEVEL-REMAINDER-V2``."""

    return f"SLURP-DEVEL-REMAINDER-V{int(version)}"


def roster_relpath(version: int) -> str:
    return f"docs/receipts/rosters/slurp-devel-remainder-v{int(version)}.json"


def check_dir(version: int) -> str:
    """V1 keeps its committed check directory name; a later version gets its own."""

    base = "docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder"
    return f"{base}-roster" if int(version) == 1 else f"{base}-v{int(version)}-roster"


def carve_out_label(relpath: str) -> str:
    known = CARVE_OUT_LABELS.get(relpath)
    if known:
        return known
    return "".join(
        character if character.isalnum() else "_" for character in Path(relpath).stem.lower()
    )


ROSTER_ID = roster_id(DEFAULT_VERSION)
ROSTER_RELPATH = roster_relpath(DEFAULT_VERSION)
CHECK_DIR = check_dir(DEFAULT_VERSION)

DEV1000_RELPATH = "docs/receipts/probe-samples/DEV-1000.json"
DEV2000_ADDED_RELPATH = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
DEV2000_FULL_RELPATH = "docs/receipts/rosters/slurp-dev-2000-v1.json"
DEV500_RELPATH = "docs/receipts/probe-samples/DEV-500.json"
DEV100_RELPATH = "docs/receipts/probe-samples/DEV-100.json"
DEV500B_RELPATH = "docs/receipts/rosters/slurp-dev-500-b-v1.json"
FINAL60_RELPATH = "docs/receipts/probe-samples/FINAL60.json"
PROBE60_RELPATH = "configs/probes/g0-binding/pslu-sample-devel-n60.json"
SPLIT_IDENTITY_RELPATH = "docs/receipts/knowledge/slurp-split-identity.json"

#: Every committed TRAIN construction / knowledge-source roster the
#: DEV-2000-ADDED receipt proved itself disjoint from, in that receipt's own
#: order (``construction_rosters_checked``), plus the two Stage-3 construction
#: rosters frozen after it. Disjointness is structural (TRAIN vs devel) and is
#: still proven id by id, the same belt-and-suspenders discipline.
CONSTRUCTION_ROSTERS: tuple[str, ...] = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/rosters/slurp-evo-exemplars-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-a-v1.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v1.json",
    "docs/receipts/rosters/slurp-evo-exemplars-v1.json",
    "docs/receipts/rosters/slurp-evo-s1-proposer-r01.json",
    "docs/receipts/rosters/slurp-native-tools-engineering-4-v1.json",
    "docs/receipts/rosters/slurp-stage3-construction-r01.json",
    "docs/receipts/rosters/slurp-stage3-construction-r01c.json",
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
    ``scripts/build_slurp_dev2000_roster.py`` (itself from
    ``scripts/build_slurp_evo_decontamination.py``): no caller holds the
    corpus, and what leaves this module is digests and counts.
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipts")
    parser.add_argument(
        "--version",
        type=int,
        default=DEFAULT_VERSION,
        help=(
            "which DEVEL-REMAINDER version to freeze (default %d); the roster id, the "
            "receipt relpath and the check directory all follow from it" % DEFAULT_VERSION
        ),
    )
    parser.add_argument(
        "--exclude-receipt",
        action="append",
        default=[],
        metavar="RELPATH",
        dest="exclude_receipt",
        help=(
            "a committed receipt whose sample ids are carved OUT of the remainder, on top "
            "of the two sealed halves (repeatable; order does not affect the result)"
        ),
    )
    args = parser.parse_args(argv)

    if args.version < 1:
        raise SystemExit("--version must be a positive integer")
    version = int(args.version)
    this_roster_id = roster_id(version)
    this_roster_relpath = roster_relpath(version)
    this_check_dir = check_dir(version)
    carve_relpaths: tuple[str, ...] = tuple(dict.fromkeys(args.exclude_receipt))
    for relpath in carve_relpaths:
        if not (REPO_ROOT / relpath).is_file():
            raise SystemExit(f"--exclude-receipt names a missing file: {relpath}")
    if len({carve_out_label(relpath) for relpath in carve_relpaths}) != len(carve_relpaths):
        raise SystemExit("two --exclude-receipt paths derive the same carve-out label")

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
    added_ids = receipt_sample_ids(DEV2000_ADDED_RELPATH)
    dev2000_ids = receipt_sample_ids(DEV2000_FULL_RELPATH)
    dev500_ids = receipt_sample_ids(DEV500_RELPATH)
    dev100_ids = receipt_sample_ids(DEV100_RELPATH)
    dev500b_ids = receipt_sample_ids(DEV500B_RELPATH)
    final60_ids = receipt_sample_ids(FINAL60_RELPATH)
    probe60_ids = receipt_sample_ids(PROBE60_RELPATH)
    if len(dev1000_ids) != 1000 or len(added_ids) != 1000:
        raise SystemExit("the sealed DEV-1000 / DEV-2000-ADDED receipts changed shape")
    for name, ids in (
        ("DEV-1000", dev1000_ids),
        ("DEV-2000-ADDED", added_ids),
        ("FINAL60", final60_ids),
        ("probe-60", probe60_ids),
    ):
        missing = [sid for sid in ids if sid not in record_by_id]
        if missing:
            raise SystemExit(f"{name} names {len(missing)} id absent from the devel loader")

    # ---- the nesting proofs the exclusion relies on -----------------------
    nesting = {
        "dev100_subset_of_dev500": set(dev100_ids) <= set(dev500_ids),
        "dev500_subset_of_dev1000": set(dev500_ids) <= set(dev1000_ids),
        "dev100_subset_of_dev1000": set(dev100_ids) <= set(dev1000_ids),
        "dev500b_subset_of_dev2000_added": set(dev500b_ids) <= set(added_ids),
        "dev2000_equals_dev1000_union_added": set(dev2000_ids)
        == set(dev1000_ids) | set(added_ids),
        "counts": {
            "DEV-100": len(dev100_ids),
            "DEV-500": len(dev500_ids),
            "DEV-1000": len(dev1000_ids),
            "DEV-500-B": len(dev500b_ids),
            "DEV-2000-ADDED": len(added_ids),
            "DEV-2000": len(dev2000_ids),
        },
        "reading": (
            "DEV-100 and DEV-500 are exact sub-tables of DEV-1000 and DEV-500-B is an "
            "exact sub-table of DEV-2000-ADDED, so excluding the two sealed rosters "
            "excludes every rung of the DEV ladder with them; nothing else has to be "
            "subtracted."
        ),
    }
    for key in (
        "dev100_subset_of_dev500",
        "dev500_subset_of_dev1000",
        "dev100_subset_of_dev1000",
        "dev500b_subset_of_dev2000_added",
        "dev2000_equals_dev1000_union_added",
    ):
        if not nesting[key]:
            raise SystemExit(f"the DEV-ladder nesting proof failed: {key}")

    sealed_ids = set(dev1000_ids) | set(added_ids)
    if len(sealed_ids) != 2000:
        raise SystemExit("the two sealed halves are not disjoint at recording level")

    # ---- the carve-out, proven id by id before it is applied --------------
    carve_ids_by_label: dict[str, set[str]] = {}
    carve_sources: list[dict[str, object]] = []
    for relpath in carve_relpaths:
        label = carve_out_label(relpath)
        ids = set(receipt_sample_ids(relpath))
        outside = sorted(sid for sid in ids if sid not in record_by_id)
        if outside:
            raise SystemExit(
                f"--exclude-receipt {relpath} names {len(outside)} id absent from the "
                "devel loader"
            )
        carve_ids_by_label[label] = ids
        carve_sources.append(
            {
                "label": label,
                "relpath": relpath,
                "receipt_file_sha256": sha256_file(relpath),
                "recordings": len(ids),
                "recordings_already_excluded_by_a_sealed_half": len(ids & sealed_ids),
                "recordings_carved_out_by_this_version": len(ids - sealed_ids),
                "utterances": len({utterance_of(sid) for sid in ids}),
            }
        )
    carved_ids: set[str] = set()
    for ids in carve_ids_by_label.values():
        carved_ids |= ids
    carved_ids -= sealed_ids
    excluded_ids = sealed_ids | carved_ids

    # ---- the take-all freeze ----------------------------------------------
    remainder_capacity = Counter(
        record.scenario for record in records if record.sample_id not in excluded_ids
    )
    quotas = {scenario: int(remainder_capacity.get(scenario, 0)) for scenario in sorted(devel_mixture)}
    candidates = [
        RosterItem(
            sample_id=record.sample_id,
            stratum=record.scenario,
            extra={"utterance_id": utterance_of(record.sample_id)},
        )
        for record in records
    ]
    receipt_draw = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=candidates,
        per_stratum=quotas,
        seed=SEED,
        split_role="dev",
        exclude_sample_ids=sorted(excluded_ids),
        roster_id=this_roster_id,
        roster_role="evaluation",
    )
    remainder_ids = sorted(str(item["sample_id"]) for item in receipt_draw["items"])
    if set(remainder_ids) != set(record_by_id) - excluded_ids:
        raise SystemExit("the take-all freeze did not take the whole remainder")
    if receipt_draw["excluded_count"] != len(excluded_ids):
        raise SystemExit("freeze_roster excluded a different number of candidates")

    items = [enrich(sid, record_by_id) for sid in remainder_ids]
    remainder_set = set(remainder_ids)
    remainder_utterances = {utterance_of(sid) for sid in remainder_ids}
    dev1000_utterances = {utterance_of(sid) for sid in dev1000_ids}
    added_utterances = {utterance_of(sid) for sid in added_ids}

    # ---- disjointness proofs ----------------------------------------------
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
                "shared_with_remainder": len(ids & remainder_set),
            }
        )
        construction_ids |= ids

    disjointness = {
        "shared_with_dev1000_recordings": len(remainder_set & set(dev1000_ids)),
        "shared_with_dev2000_added_recordings": len(remainder_set & set(added_ids)),
        "shared_with_dev2000_recordings": len(remainder_set & set(dev2000_ids)),
        "shared_with_test_recordings": len(remainder_set & test_ids),
        "shared_with_train_construction_recordings": len(remainder_set & construction_ids),
        "non_devel_ids_in_remainder": len(remainder_set - devel_ids_frozen),
        "max_recordings_per_remainder_utterance": max(
            Counter(utterance_of(sid) for sid in remainder_ids).values()
        ),
    }
    # The carve-out is proven the same way every other exclusion is: by id, in
    # the receipt, with a zero the reader can check rather than a promise.
    for label in sorted(carve_ids_by_label):
        disjointness["shared_with_carved_out_%s_recordings" % label] = len(
            remainder_set & carve_ids_by_label[label]
        )
    if carved_ids:
        disjointness["shared_with_any_carved_out_recording"] = len(remainder_set & carved_ids)
    for key, value in disjointness.items():
        if key.startswith("shared_with") and value:
            raise SystemExit(f"DEVEL-REMAINDER disjointness proof failed: {key} = {value}")
    if disjointness["non_devel_ids_in_remainder"]:
        raise SystemExit("a remainder id is not a member of the frozen devel enumeration")

    # ---- the completeness identity ----------------------------------------
    # Without a carve-out the identity has three parts; a carve-out adds a
    # fourth so that nothing disappears from the accounting -- the reserved
    # recordings are named and set aside, not subtracted into silence.
    parts: list[tuple[str, set[str]]] = [
        ("DEV-1000", set(dev1000_ids)),
        ("DEV-2000-ADDED", set(added_ids)),
    ]
    if carved_ids:
        parts.append(("CARVED-OUT", set(carved_ids)))
    parts.append(("DEVEL-REMAINDER", remainder_set))
    parts_union: set[str] = set()
    for _, member in parts:
        parts_union |= member
    parts_disjoint = all(
        not (parts[left][1] & parts[right][1])
        for left in range(len(parts))
        for right in range(left + 1, len(parts))
    )
    sum_key = "four_parts_sum" if carved_ids else "three_parts_sum"
    completeness = {
        "devel_recordings": len(records),
        "dev1000_recordings": len(dev1000_ids),
        "dev2000_added_recordings": len(added_ids),
        "remainder_recordings": len(remainder_ids),
        sum_key: sum(len(member) for _, member in parts),
        "union_equals_the_complete_devel_split": parts_union == set(record_by_id),
        "parts_are_pairwise_disjoint": parts_disjoint,
        "statement": (
            (
                "The expanded development read is DEV-1000 U DEV-2000-ADDED U "
                "DEVEL-REMAINDER, and that union is the COMPLETE SLURP devel split at "
                "recording granularity: 1,000 + 1,000 + "
                f"{len(remainder_ids)} = {len(records)} recordings, pairwise disjoint."
            )
            if not carved_ids
            else (
                "The expanded development read is DEV-1000 U DEV-2000-ADDED U "
                "DEVEL-REMAINDER, and with the CARVED-OUT reservations it is the COMPLETE "
                "SLURP devel split at recording granularity: 1,000 + 1,000 + "
                f"{len(remainder_ids)} + {len(carved_ids)} = {len(records)} recordings, "
                "pairwise disjoint. The carved-out recordings are accounted for, not lost: "
                "they stay reserved and this roster never reads them."
            )
        ),
    }
    if carved_ids:
        completeness["carved_out_recordings"] = len(carved_ids)
    if not completeness["union_equals_the_complete_devel_split"]:
        raise SystemExit("the parts do not cover the devel split")
    if not completeness["parts_are_pairwise_disjoint"]:
        raise SystemExit("the parts are not pairwise disjoint")
    if completeness[sum_key] != len(records):
        raise SystemExit("the parts do not sum to the devel split size")

    # ---- utterance overlap (reported, never enforced) ---------------------
    utterance_overlap = {
        "devel_utterances": len(scenario_by_utterance),
        "remainder_utterances": len(remainder_utterances),
        "remainder_utterances_also_in_dev1000": len(remainder_utterances & dev1000_utterances),
        "remainder_utterances_also_in_dev2000_added": len(
            remainder_utterances & added_utterances
        ),
        "remainder_utterances_also_in_either_sealed_half": len(
            remainder_utterances & (dev1000_utterances | added_utterances)
        ),
        "remainder_utterances_never_read_before": len(
            remainder_utterances - (dev1000_utterances | added_utterances)
        ),
        "recordings_per_remainder_utterance": dict(
            sorted(
                Counter(
                    Counter(utterance_of(sid) for sid in remainder_ids).values()
                ).items()
            )
        ),
        "reading": (
            "devel carries 8,690 recordings of 2,033 utterances, so utterance-level "
            "disjointness from the two sealed halves is arithmetically impossible for a "
            "remainder that must cover the whole split. These counts are the exact size of "
            "the sharing; see deviation REM-D2 for what an analysis has to do about it."
        ),
    }

    # ---- reserved sets that the remainder necessarily absorbs -------------
    final60_utterances = {utterance_of(sid) for sid in final60_ids}
    probe60_utterances = {utterance_of(sid) for sid in probe60_ids}
    reserved = {
        "final60": {
            "relpath": FINAL60_RELPATH,
            "receipt_file_sha256": sha256_file(FINAL60_RELPATH),
            "split_role": read_json(FINAL60_RELPATH)["split_role"],
            "recordings": len(final60_ids),
            "recordings_inside_the_remainder": len(set(final60_ids) & remainder_set),
            "utterances": len(final60_utterances),
            "remainder_recordings_of_those_utterances": sum(
                1 for sid in remainder_ids if utterance_of(sid) in final60_utterances
            ),
        },
        "historic_probe60": {
            "relpath": PROBE60_RELPATH,
            "receipt_file_sha256": sha256_file(PROBE60_RELPATH),
            "recordings": len(probe60_ids),
            "recordings_inside_the_remainder": len(set(probe60_ids) & remainder_set),
            "utterances": len(probe60_utterances),
            "remainder_recordings_of_those_utterances": sum(
                1 for sid in remainder_ids if utterance_of(sid) in probe60_utterances
            ),
        },
        "final60_and_probe60_share_a_recording": len(set(final60_ids) & set(probe60_ids)),
        "final60_and_probe60_share_an_utterance": len(final60_utterances & probe60_utterances),
        "reading": (
            (
                "These two sets were HELD BACK by the DEV ladder, not consumed by it, so "
                "they are not in either sealed half and a remainder defined by subtraction "
                "contains them. They are neither dropped nor quietly read here: the roster "
                "carries them and deviation REM-D1 asks the owner to acknowledge or carve "
                "them out before the remainder is read as evidence."
            )
            if not carved_ids
            else (
                "These two sets were HELD BACK by the DEV ladder, not consumed by it, so a "
                "remainder defined by subtraction alone would contain them. This version "
                "CARVES THEM OUT (see carved_out_reserved_sets): "
                "recordings_inside_the_remainder is 0 for both, so the FINAL60 reservation "
                "is not spent and no already-contacted probe-60 recording is on the roster. "
                "remainder_recordings_of_those_utterances is what a recording-level "
                "carve-out cannot remove -- sibling recordings of the same utterances -- "
                "and deviation REM-D1 puts that residue to the owner."
            )
        ),
    }

    # ---- what the carve-out removed, and what it could not remove ---------
    carve_utterances = {utterance_of(sid) for sid in carved_ids}
    carve_labels = sorted(carve_ids_by_label)
    pairwise_recordings: dict[str, int] = {}
    pairwise_utterances: dict[str, int] = {}
    for left_index, left in enumerate(carve_labels):
        for right in carve_labels[left_index + 1 :]:
            key = f"{left}|{right}"
            pairwise_recordings[key] = len(
                carve_ids_by_label[left] & carve_ids_by_label[right]
            )
            pairwise_utterances[key] = len(
                {utterance_of(sid) for sid in carve_ids_by_label[left]}
                & {utterance_of(sid) for sid in carve_ids_by_label[right]}
            )
    carve_block = {
        "authority": CARVE_OUT_AUTHORITY,
        "receipts": carve_sources,
        "union_recordings": len(carved_ids),
        "union_utterances": len(carve_utterances),
        "union_sample_id_list_sha256": hashlib.sha256(
            "\n".join(sorted(carved_ids)).encode("utf-8")
        ).hexdigest(),
        "pairwise_shared_recordings": pairwise_recordings,
        "pairwise_shared_utterances": pairwise_utterances,
        "carved_out_recordings_still_in_the_remainder": len(remainder_set & carved_ids),
        "carved_out_utterances_still_represented_in_the_remainder": len(
            remainder_utterances & carve_utterances
        ),
        "remainder_recordings_of_carved_out_utterances": sum(
            1 for sid in remainder_ids if utterance_of(sid) in carve_utterances
        ),
        "reading": (
            "The carve-out is exact at RECORDING granularity and is proven here and in "
            "disjointness_proof: zero carved-out recordings survive in the remainder. It "
            "is NOT exact at UTTERANCE granularity and cannot be, because devel carries "
            "several recordings of one utterance: "
            f"{len(remainder_utterances & carve_utterances)} of the carved-out utterances "
            "still have sibling recordings on this roster "
            f"({sum(1 for sid in remainder_ids if utterance_of(sid) in carve_utterances)} "
            "recordings). Reading them exposes the same sentence and the same gold as the "
            "reserved recordings would, through a different microphone. Deviation REM-D1 "
            "puts that residue to the owner rather than absorbing it."
        ),
    }

    # ---- text proof (digest only) ------------------------------------------
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
    remainder_profile = text_profile(
        metadata_dir,
        sorted({slurp_id_of(sid) for sid in remainder_ids}),
        frozenset(construction_sentence_digests),
        frozenset(construction_gram_digests),
    )
    dev1000_profile = text_profile(
        metadata_dir,
        sorted({slurp_id_of(sid) for sid in dev1000_ids}),
        frozenset(construction_sentence_digests),
        frozenset(construction_gram_digests),
    )
    text_block = {
        "method": (
            "Digest only, after scripts/build_slurp_evo_decontamination.py and "
            "scripts/build_slurp_dev2000_roster.py: sentences are read inside one "
            "generator, compared as whole-sentence SHA-256 digests and as word "
            f"{DECONTAMINATION_NGRAM}-gram digests (rails.proposer.word_ngrams / "
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
        "remainder": remainder_profile,
        "dev1000_baseline": dev1000_profile,
        "reading": (
            "Construction pools are TRAIN-only by loader construction, so the id-level "
            "proof is structural; these counts say how much of the remainder's TEXT a "
            "TRAIN-built knowledge store could already contain, measured against the "
            "sealed DEV-1000 half under the identical method."
        ),
    }

    # ---- aggregates --------------------------------------------------------
    remainder_scenarios = Counter(
        scenario_by_utterance[utterance_of(sid)] for sid in remainder_ids
    )
    dev1000_scenarios = Counter(
        scenario_by_utterance[utterance_of(sid)] for sid in dev1000_ids
    )
    added_scenarios = Counter(scenario_by_utterance[utterance_of(sid)] for sid in added_ids)
    channel_counts = {
        "headset": sum(1 for item in items if item["headset"]),
        "far_field": sum(1 for item in items if not item["headset"]),
    }
    audio_total = round(sum(float(item["audio_seconds"]) for item in items), 9)
    audio_values = [float(item["audio_seconds"]) for item in items]

    if carved_ids:
        rem_d1 = {
            "id": "REM-D1",
            "statement": (
                f"The {len(carved_ids)} reserved recordings -- the {len(final60_ids)} "
                "FINAL60 recordings (receipt split_role 'reserved-final-unread', held back "
                f"on 2026-08-23) and the {len(probe60_ids)} historic probe-60 recordings "
                "already contacted by early probes -- are CARVED OUT of this version, so "
                "the FINAL60 reservation is not spent and no already-contacted recording "
                "is on the roster. What the carve-out cannot remove is the reserved "
                f"UTTERANCES: {len(remainder_utterances & carve_utterances)} of them still "
                "have sibling recordings here "
                f"({sum(1 for sid in remainder_ids if utterance_of(sid) in carve_utterances)} "
                "recordings of the same sentences through different microphones)."
            ),
            "why_unavoidable": (
                "Arithmetic again: devel carries several recordings of one utterance, so a "
                "recording-level reservation cannot be enforced at utterance level without "
                "dropping recordings that were never reserved."
            ),
            "owner_action": (
                "decide whether the utterance-level residue also has to go (that is a "
                f"further {sum(1 for sid in remainder_ids if utterance_of(sid) in carve_utterances)} "
                "recordings and a third version of this roster), or accept that the "
                "reservation is enforced at recording granularity only; the counts needed "
                "for either choice are in carved_out_reserved_sets"
            ),
        }
    else:
        rem_d1 = {
            "id": "REM-D1",
            "statement": (
                f"The remainder contains the {len(final60_ids)} FINAL60 recordings "
                "(receipt split_role 'reserved-final-unread', held back by the DEV ladder "
                f"on 2026-08-23) and the {len(probe60_ids)} historic probe-60 recordings. "
                "Reading the remainder therefore spends a reservation that was created to "
                "stay unread."
            ),
            "why_unavoidable": (
                "Decision 107 expands the development side to the FULL devel split, and "
                "the remainder is defined by subtracting the two sealed halves; neither "
                "half contains these 120 recordings."
            ),
            "owner_action": (
                "acknowledge that decision 107 releases the FINAL60 reservation, or carve "
                "the 120 recordings out of the remainder before it is read (the counts "
                "needed for the carve-out are in reserved_sets_inside_the_remainder)"
            ),
        }
    deviations = [
        rem_d1,
        {
            "id": "REM-D2",
            "statement": (
                f"{utterance_overlap['remainder_utterances_also_in_either_sealed_half']} of "
                f"the {len(remainder_utterances)} remainder utterances already have a "
                "recording in DEV-1000 or DEV-2000-ADDED; only "
                f"{utterance_overlap['remainder_utterances_never_read_before']} remainder "
                "utterances were never read before, and one utterance contributes up to "
                f"{disjointness['max_recordings_per_remainder_utterance']} remainder "
                "recordings."
            ),
            "why_unavoidable": (
                "Arithmetic: devel carries 8,690 recordings of 2,033 utterances."
            ),
            "owner_action": (
                "cluster every paired analysis by utterance_id, and never report a "
                "remainder result and a DEV-1000 / DEV-2000-ADDED result as independent "
                "utterance samples"
            ),
        },
        {
            "id": "REM-D3",
            "statement": (
                "No equal-per-scenario allocation is possible: the remainder is whatever "
                "the two sealed halves left, so its scenario mixture is the devel mixture "
                "minus their draws (see scenario_allocation)."
            ),
            "why_unavoidable": "Capacity, not choice; the roster is a take-all remainder.",
            "owner_action": (
                "report every DEVEL-REMAINDER verdict under both natural-mixture and "
                "equal-stratum weighting, per the 2026-09-03 reporting rule"
            ),
        },
    ]

    extra_keys: dict[str, object] = {}
    if version != DEFAULT_VERSION:
        extra_keys["roster_version"] = version
        parent_relpath = roster_relpath(version - 1)
        if (REPO_ROOT / parent_relpath).is_file():
            parent = read_json(parent_relpath)
            extra_keys["supersedes"] = {
                "roster_id": parent["roster_id"],
                "relpath": parent_relpath,
                "receipt_file_sha256": sha256_file(parent_relpath),
                "split_identity_hash": parent["split_identity_hash"],
                "recordings": len(parent["items"]),
                "reading": (
                    "The parent receipt stays committed exactly as it was frozen and is "
                    "NEVER rewritten: several committed documents pin its "
                    "receipt_file_sha256, so adding a superseded_by key to it would break "
                    "every one of those pins. The supersession is recorded here and in the "
                    "preparation plan note instead."
                ),
            }
    if carve_relpaths:
        extra_keys["carved_out_reserved_sets"] = carve_block
    authority_text = (
        AUTHORITY if not carve_relpaths else f"{AUTHORITY}; {CARVE_OUT_AUTHORITY}"
    )

    receipt = {
        **receipt_draw,
        **extra_keys,
        "authority": authority_text,
        "generator": GENERATOR,
        "status": "FROZEN; MODEL-FREE, ZERO CONTACTS",
        "design": (
            "Every SLURP devel recording that is in neither the sealed DEV-1000 nor "
            "DEV-2000-ADDED. With those two it is the complete devel split, which is what "
            "owner decision 107 authorises the development side to grow to."
        ),
        "item_fields": ["audio_seconds", "headset", "id", "key", "sample_id", "utterance_id"],
        "stratum_withheld_per_item": True,
        "target_gold_opened_before_receipt": False,
        "selection_rule": (
            "TAKE-ALL, not a sample. core.roster.freeze_roster (seed 20260923) is called "
            "with the WHOLE devel population as candidates, the 2,000 sealed DEV-1000 + "
            "DEV-2000-ADDED recordings as exclude_sample_ids, and a per-stratum quota "
            "equal to each scenario's surviving capacity, so the shuffle has nothing left "
            "to choose between and the result is the whole remainder frozen through the "
            "canonical schema, hash and disjointness machinery. exclude_groups is "
            "deliberately not used: several recordings of one utterance are wanted here."
        ),
        "parent_rosters": {
            "sealed_dev1000": {
                "relpath": DEV1000_RELPATH,
                "roster_id": "DEV-1000",
                "count": len(dev1000_ids),
                "receipt_file_sha256": sha256_file(DEV1000_RELPATH),
                "run_identity_hash": read_json(DEV1000_RELPATH)["run_identity_hash"],
                "scenario_allocation": dict(sorted(dev1000_scenarios.items())),
            },
            "sealed_dev2000_added": {
                "relpath": DEV2000_ADDED_RELPATH,
                "roster_id": "SLURP-DEV-2000-ADDED-V1",
                "count": len(added_ids),
                "receipt_file_sha256": sha256_file(DEV2000_ADDED_RELPATH),
                "split_identity_hash": read_json(DEV2000_ADDED_RELPATH)[
                    "split_identity_hash"
                ],
                "scenario_allocation": dict(sorted(added_scenarios.items())),
            },
        },
        "dev_ladder_nesting": nesting,
        "completeness": completeness,
        "utterance_overlap": utterance_overlap,
        "reserved_sets_inside_the_remainder": reserved,
        "scenario_allocation": dict(sorted(remainder_scenarios.items())),
        "channel_counts": channel_counts,
        "audio_seconds_total": audio_total,
        "audio_seconds_summary": {
            "count": len(audio_values),
            "mean": round(audio_total / len(audio_values), 9),
            "min": round(min(audio_values), 9),
            "max": round(max(audio_values), 9),
            "declared_ceiling": int(math.ceil(audio_total)),
        },
        "disjointness_proof": disjointness,
        "construction_rosters_checked": construction_sources,
        "text_disjointness": text_block,
        "deviations": deviations,
        "items": items,
        "split_identity_receipt": {
            "relpath": SPLIT_IDENTITY_RELPATH,
            "devel_identity_hash": split_identity["splits"]["devel"]["identity_hash"],
            "devel_ids": split_identity["splits"]["devel"]["count"],
            "test_identity_hash": split_identity["splits"]["test"]["identity_hash"],
            "test_ids": split_identity["splits"]["test"]["count"],
        },
        "one_shot_rule": (
            "The DEVEL-REMAINDER comparators fly ONCE on these rows; a later mechanism is "
            "compared against those sealed outputs, not against a fresh comparator pass. "
            "The two sealed halves are never re-flown for this expansion."
        ),
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    }
    measured = split_identity_hash(prefixed(CARRIER, [str(i["sample_id"]) for i in items]))
    if measured != receipt["split_identity_hash"]:
        raise SystemExit("the enriched items changed the split identity hash")
    verify_roster(receipt)

    summary = {
        **extra_keys,
        "roster_id": this_roster_id,
        "split_identity_hash": receipt["split_identity_hash"],
        "count": len(items),
        "audio_seconds_total": audio_total,
        "audio_seconds_summary": receipt["audio_seconds_summary"],
        "scenario_allocation": receipt["scenario_allocation"],
        "channel_counts": channel_counts,
        "completeness": completeness,
        "utterance_overlap": utterance_overlap,
        "reserved_sets_inside_the_remainder": reserved,
        "disjointness_proof": disjointness,
        "dev_ladder_nesting": nesting,
        "text_disjointness": {
            "remainder": remainder_profile,
            "dev1000_baseline": dev1000_profile,
        },
        "offline_guard": receipt["offline_guard"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.write:
        write_roster(receipt, REPO_ROOT / this_roster_relpath)
        proof_dir = REPO_ROOT / this_check_dir
        proof_dir.mkdir(parents=True, exist_ok=True)
        proof = {
            "schema": "saea-devel-remainder-roster-disjointness-v1",
            "study": "speech-aware-evidence-acquisition",
            "authority": authority_text,
            "generator": GENERATOR,
            **extra_keys,
            "roster": {
                "roster_id": this_roster_id,
                "relpath": this_roster_relpath,
                "split_identity_hash": receipt["split_identity_hash"],
                "receipt_file_sha256": sha256_file(this_roster_relpath),
                "count": len(items),
                "audio_seconds_total": audio_total,
            },
            "completeness": completeness,
            "dev_ladder_nesting": nesting,
            "disjointness_proof": disjointness,
            "construction_rosters_checked": construction_sources,
            "utterance_overlap": utterance_overlap,
            "reserved_sets_inside_the_remainder": reserved,
            "text_disjointness": text_block,
            "scenario_allocation": receipt["scenario_allocation"],
            "channel_counts": channel_counts,
            "deviations": deviations,
            "offline_guard": receipt["offline_guard"],
        }
        proof["proof_sha256"] = canonical_sha256(proof)
        (proof_dir / "disjointness.json").write_text(
            json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {this_roster_relpath}")
        print(f"wrote {this_check_dir}/disjointness.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
