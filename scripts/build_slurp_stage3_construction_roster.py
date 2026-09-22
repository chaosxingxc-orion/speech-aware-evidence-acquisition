#!/usr/bin/env python3
"""CLI: freeze ``SLURP-STAGE3-CONSTRUCTION-R01`` (S3-1), the Stage-3 rollout roster.

Owner decisions 80-83 of 2026-09-22 (``docs/superpowers/specs/
2026-09-22-stage3-tfrl-base-loop-engineering.md`` section S3-1;
``docs/superpowers/specs/2026-09-21-slurp-stage3-training-free-rl-design.md``
decision 81): about 800 SLURP TRAIN construction rows, drawn with a
semantic-diversity rule (farthest-point coverage over the sealed content
embeddings) so semantically distant utterances are represented, for the
Stage-3 grouped-Solver rollout (S3-2) and its downstream scoring (S3-3).

IDENTITY ONLY, ZERO MODEL/TOKENIZER/ENCODER/SCORER/NETWORK CONTACT. The pool
is the sealed 9,354-utterance construction pool of
``docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json``
(builder ``scripts/build_slurp_exemplar_pool_assets.py``, which already
excludes every utterance with a recording in TRAIN A (``slurp-evo-fold-a-
v2.json``), TRAIN B (``slurp-evo-fold-b-v2.json``) and DEV-1000
(``probe-samples/DEV-1000.json``) -- its own ``EXCLUDE_ROSTER_RELPATHS``).
Decision 81 ALSO bars DEV-2000 and DEV-2000-ADDED, which
``EXCLUDE_ROSTER_RELPATHS`` does not carry, so this generator excludes them
(and the absorbed DEV-500-B subset) explicitly and PROVES disjointness id by
id against all six rosters even though the split boundary already makes the
overlap structurally zero (the same belt-and-suspenders discipline
``scripts/build_slurp_dev2000_roster.py`` uses against the construction
rosters in the other direction).

The stratum of a construction utterance is read from the KB snapshot's own
``values[].task_target`` field (``"<scenario>_<action>"``, split on the
first underscore) -- NEVER from a fresh read of TRAIN gold -- because the
snapshot is the one sealed, receipted artifact this generator is licensed to
read for stratum identity (module docstring "the stratum is on the KB
snapshot's values, never gold"). Media facts (``audio_seconds``,
``media_relpath``, ``headset``) come from the governed TRAIN loader
(``data.slurp.load_slurp_split``), which carries no sentence, no entity and
no intent -- only the loader-legal identity + media layer already used by
every other roster generator in this repository.

The draw (seed 20260922; NOT ``core.roster.freeze_roster``'s own uniform
shuffle -- see below)
--------------------------------------------------------------------------
18 strata (the SLURP scenarios). 800 rows are split as evenly as possible
across the 18 strata (``800 // 18 = 44`` remainder ``8``): the 8
alphabetically-first scenario names each take 45, the remaining 10 take 44
(FIXED and RECORDED in the receipt's ``per_stratum`` block -- never
re-derived by a reader).

Within one stratum: the eligible candidates (pool utterances of that
scenario, one recording each -- the lexicographically FIRST recording id of
each utterance, from the snapshot's own ``sample:`` provenance refs) are
sorted by ``utterance_id`` for determinism, then a farthest-point traversal
seeded ``f"{20260922}:{stratum}"`` runs over the sealed
``vectors/slurp-kus3/facet-vectors.jsonl`` content embeddings (already
L2-normalised, so cosine similarity is the plain dot product): the first
point is chosen uniformly at random from the sorted candidate list, and each
following point is the remaining candidate whose cosine similarity to its
CLOSEST already-selected neighbour is SMALLEST (i.e. farthest from the
selected set under the max-similarity-to-nearest-neighbour measure), ties
broken by ascending ``utterance_id`` then ``rng``. Each drawn item records
``draw_rank`` (0-indexed draw order within its stratum) and
``min_cosine_to_selected`` (the minimised nearest-neighbour cosine value at
the moment of selection; ``null`` for the random first point, which has no
selected set to compare against).

This is why the draw is NOT ``core.roster.freeze_roster``'s own per-stratum
uniform shuffle: that function draws UNIFORMLY, which is exactly the
DIVERSITY baseline this receipt's own ``diversity_report`` compares the
farthest-point draw against. ``freeze_roster`` is still the schema and
identity authority: this script pre-selects EXACTLY the quota-many items per
stratum via the farthest-point rule, then calls ``freeze_roster`` with those
items as the WHOLE eligible candidate pool (quota == pool size per stratum),
so its own uniform shuffle has nothing left to choose between and the
result is the farthest-point draw, frozen through the canonical
``saea-roster-receipt-v1`` schema, hash and disjointness machinery.

No utterance text, gold label, transcript or model output is read, printed
or persisted by this script -- only ids, counts, cosine values and hashes.

Run in WSL2 (the governed SLURP release and the sealed vectors are under
``$SPEECHRL_DATA_DIR``)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_stage3_construction_roster.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    CONSTRUCTION_ROSTER_ROLE,
    RosterItem,
    freeze_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.e0.d1_identity import (  # noqa: E402
    _confined_media_path,
    _probe_speech_media,
)
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_vectors,
)

CARRIER = "slurp"
SEED = 20260922
TOTAL = 800
ROSTER_ID = "SLURP-STAGE3-CONSTRUCTION-R01"
ROSTER_ROLE = CONSTRUCTION_ROSTER_ROLE
SPLIT_ROLE = "discovery"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-stage3-construction-r01.json"
RUNTIME_VIEW_RELPATH = "configs/dataset/slurp-speech-native-stage3-construction-r01.json"
SPLIT_NAME = "STAGE3-CONSTRUCTION-R01"
POOL_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json"
EXPECTED_POOL_VALUE_COUNT = 9354
VECTORS_RELPATH = "vectors/slurp-kus3/facet-vectors.jsonl"
VECTORS_SHA256 = "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"
GENERATOR = "scripts/build_slurp_stage3_construction_roster.py"
AUTHORITY = (
    "docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md section S3-1; "
    "docs/superpowers/specs/2026-09-21-slurp-stage3-training-free-rl-design.md decisions 80-83"
)

#: The six forbidden rosters (module docstring): TRAIN A/B and DEV-1000 are
#: already excluded from the pool by ``build_slurp_exemplar_pool_assets.py``'s
#: own ``EXCLUDE_ROSTER_RELPATHS``; DEV-2000/DEV-2000-ADDED/DEV-500-B (a
#: verbatim-absorbed subset of DEV-2000-ADDED) are barred by decision 81 and
#: are NOT in that list. Every one of the six is proven disjoint id-by-id
#: below even though the split boundary (TRAIN vs devel) already makes the
#: overlap structurally zero.
FORBIDDEN_ROSTERS: tuple[str, ...] = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/probe-samples/DEV-1000.json",
    "docs/receipts/rosters/slurp-dev-2000-v1.json",
    "docs/receipts/rosters/slurp-dev-2000-added-v1.json",
    "docs/receipts/rosters/slurp-dev-500-b-v1.json",
)


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utterance_id_of(slurp_numeric_id: str) -> str:
    return f"slurp:train:{int(slurp_numeric_id):06d}"


def is_headset(media_relpath: str) -> bool:
    return "-headset" in Path(media_relpath).name


def receipt_sample_ids(repo_root: Path, relpath: str) -> set[str]:
    document = json.loads((repo_root / relpath).read_text(encoding="utf-8"))
    ids: set[str] = set()
    for item in document["items"]:
        value = item.get("sample_id") if "sample_id" in item else item.get("id")
        if not isinstance(value, str) or not value:
            raise SystemExit(f"{relpath} carries a malformed item")
        ids.add(value)
    return ids


def utterance_of(sample_id: str) -> str:
    return sample_id.rsplit(":", 1)[0]


def stratum_quotas(strata: Sequence[str], *, total: int) -> dict[str, int]:
    """Split ``total`` as evenly as possible across ``strata`` (sorted
    ascending): a flat base share, plus one extra seat each for the
    alphabetically-first ``total % len(strata)`` strata. Deterministic,
    order-independent, recorded verbatim in the receipt (module docstring)."""

    names = sorted(strata)
    if not names:
        raise SystemExit("stratum_quotas: no strata")
    base, remainder = divmod(total, len(names))
    quotas = {name: base for name in names}
    for name in names[:remainder]:
        quotas[name] += 1
    if sum(quotas.values()) != total:
        raise SystemExit("stratum_quotas: internal invariant failed")
    return quotas


def load_pool(repo_root: Path, root: Path) -> tuple[dict[str, object], dict[str, object]]:
    receipt_path = repo_root / POOL_RECEIPT_RELPATH
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("value_count") != EXPECTED_POOL_VALUE_COUNT:
        raise SystemExit(
            f"construction pool receipt carries {receipt.get('value_count')} values, "
            f"expected {EXPECTED_POOL_VALUE_COUNT}"
        )
    snapshot_relpath = receipt["snapshot_artifact_relpath"]
    snapshot_path = root / snapshot_relpath
    snapshot_bytes = snapshot_path.read_bytes()
    snapshot = json.loads(snapshot_bytes)
    # The snapshot's own ``snapshot_sha256`` is canonical_sha256 of the document
    # MINUS that field (a signed/unsigned pair, like this script's own runtime
    # view below) -- NOT a raw-byte hash of the file, which differs from it.
    unsigned_snapshot = {k: v for k, v in snapshot.items() if k != "snapshot_sha256"}
    measured = canonical_sha256(unsigned_snapshot)
    if measured != receipt["snapshot_sha256"] or measured != snapshot.get("snapshot_sha256"):
        raise SystemExit(
            f"KB snapshot {snapshot_path} canonical hash {measured} disagrees with the "
            f"receipted {receipt['snapshot_sha256']} or its own recorded "
            f"{snapshot.get('snapshot_sha256')}"
        )
    if len(snapshot["values"]) != EXPECTED_POOL_VALUE_COUNT:
        raise SystemExit("KB snapshot value count disagrees with its own receipt")
    return receipt, snapshot


def pool_candidates(snapshot: Mapping[str, object]) -> dict[str, dict[str, object]]:
    """One candidate per pool utterance: stratum (from ``task_target``,
    never gold), the utterance id, and the first-by-id recording sample id
    (from the value's own ``sample:``-prefixed provenance refs)."""

    candidates: dict[str, dict[str, object]] = {}
    for value in snapshot["values"]:
        value_id = str(value["value_id"])
        if not value_id.startswith("value:"):
            raise SystemExit(f"KB snapshot value_id {value_id!r} has an unexpected shape")
        numeric_id = value_id[len("value:") :]
        utterance_id = utterance_id_of(numeric_id)
        task_target = str(value["task_target"])
        stratum = task_target.split("_", 1)[0]
        if not stratum:
            raise SystemExit(f"KB snapshot value {value_id!r} carries an empty stratum")
        recording_ids = sorted(
            ref[len("sample:") :]
            for ref in value["provenance_refs"]
            if isinstance(ref, str) and ref.startswith("sample:")
        )
        if not recording_ids:
            raise SystemExit(f"KB snapshot value {value_id!r} carries no sample provenance")
        facet_ids = value["associated_facet_ids"]
        if not isinstance(facet_ids, list) or len(facet_ids) != 1:
            raise SystemExit(f"KB snapshot value {value_id!r} carries != 1 associated facet")
        facet_id = str(facet_ids[0])
        expected_facet_id = f"facet:content:{numeric_id}"
        if facet_id != expected_facet_id:
            raise SystemExit(
                f"KB snapshot value {value_id!r} facet id {facet_id!r} disagrees with the "
                f"expected {expected_facet_id!r}"
            )
        if utterance_id in candidates:
            raise SystemExit(f"KB snapshot repeats utterance {utterance_id!r}")
        candidates[utterance_id] = {
            "utterance_id": utterance_id,
            "stratum": stratum,
            "sample_id": recording_ids[0],
            "facet_id": facet_id,
        }
    return candidates


def farthest_point_draw(
    ordered_ids: Sequence[str], vectors, quota: int, seed_text: str
) -> list[tuple[str, float | None]]:
    """Farthest-point traversal over unit vectors (module docstring).

    ``ordered_ids`` is sorted ascending; ``vectors`` is a numpy array of the
    SAME order, already treated as possibly-unnormalised (normalised here
    defensively). Returns ``[(utterance_id, min_cosine_to_selected), ...]``
    in draw order, length ``quota``.
    """

    import numpy as np  # deferred: keep the module import light

    if quota > len(ordered_ids):
        raise SystemExit(
            f"farthest_point_draw: quota {quota} exceeds the eligible pool "
            f"{len(ordered_ids)}"
        )
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    unit = vectors / norms
    n = len(ordered_ids)
    rng = random.Random(seed_text)

    first_index = rng.randrange(n)
    order: list[tuple[str, float | None]] = [(ordered_ids[first_index], None)]
    remaining = set(range(n)) - {first_index}
    closest_sim = unit @ unit[first_index]

    while len(order) < quota:
        remaining_sorted = sorted(remaining, key=lambda i: ordered_ids[i])
        min_val = min(float(closest_sim[i]) for i in remaining_sorted)
        tied = [i for i in remaining_sorted if abs(float(closest_sim[i]) - min_val) <= 1e-9]
        chosen = tied[rng.randrange(len(tied))] if len(tied) > 1 else tied[0]
        order.append((ordered_ids[chosen], float(closest_sim[chosen])))
        remaining.discard(chosen)
        closest_sim = np.maximum(closest_sim, unit @ unit[chosen])
    return order


def mean_pairwise_cosine(vectors) -> float | None:
    import numpy as np  # deferred

    k = vectors.shape[0]
    if k < 2:
        return None
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0.0] = 1.0
    unit = vectors / norms
    gram = unit @ unit.T
    total = float(gram.sum()) - k
    return total / (k * (k - 1))


def exclude_forbidden(
    candidates: Mapping[str, Mapping[str, object]],
    forbidden_recording_ids: Mapping[str, set[str]],
) -> tuple[dict[str, dict[str, object]], list[str]]:
    """Remove every candidate whose utterance id OR chosen recording id
    appears in ANY forbidden roster (decision 81 + the pool's own baked-in
    exclusions, module docstring). Returns the surviving candidates (a new
    dict; the input is never mutated) and the sorted list of excluded
    utterance ids."""

    forbidden_all_recordings: set[str] = set()
    for ids in forbidden_recording_ids.values():
        forbidden_all_recordings |= ids
    forbidden_all_utterances = {utterance_of(sid) for sid in forbidden_all_recordings}

    excluded = sorted(
        uid
        for uid, entry in candidates.items()
        if uid in forbidden_all_utterances or entry["sample_id"] in forbidden_all_recordings
    )
    remaining = {uid: dict(entry) for uid, entry in candidates.items() if uid not in excluded}
    return remaining, excluded


def disjointness_report(
    final_recordings: set[str],
    final_utterances: set[str],
    forbidden_recording_ids: Mapping[str, str],
) -> dict[str, dict[str, object]]:
    """Per forbidden roster (``{relpath: ids}``): item count and shared
    recording/utterance counts against the final draw. Every count is
    expected zero; the caller decides whether to fail closed on a non-zero
    one (:func:`main` does)."""

    report: dict[str, dict[str, object]] = {}
    for relpath, ids in forbidden_recording_ids.items():
        name = Path(relpath).stem
        report[name] = {
            "relpath": relpath,
            "items": len(ids),
            "shared_recordings": len(final_recordings & ids),
            "shared_utterances": len(final_utterances & {utterance_of(sid) for sid in ids}),
        }
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the roster and runtime view")
    args = parser.parse_args(argv)

    import numpy as np  # deferred: keep the module import light

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()

    pool_receipt, snapshot = load_pool(REPO_ROOT, root)
    candidates = pool_candidates(snapshot)

    vectors_table = load_sealed_vectors(
        root / VECTORS_RELPATH, expected_sha256=VECTORS_SHA256, dimensions=["content"]
    )
    missing_vectors = sorted(
        c["utterance_id"] for c in candidates.values() if c["facet_id"] not in vectors_table
    )
    if missing_vectors:
        raise SystemExit(
            f"{len(missing_vectors)} pool utterance(s) have no sealed content vector; "
            f"first: {missing_vectors[0]}"
        )

    # ---- forbidden-roster exclusion (decision 81) --------------------------
    forbidden_recording_ids: dict[str, set[str]] = {
        relpath: receipt_sample_ids(REPO_ROOT, relpath) for relpath in FORBIDDEN_ROSTERS
    }
    candidates, excluded_utterances = exclude_forbidden(candidates, forbidden_recording_ids)

    # ---- per-stratum eligible pools, sorted for determinism ----------------
    strata_present = sorted({entry["stratum"] for entry in candidates.values()})
    if len(strata_present) != 18:
        raise SystemExit(f"expected 18 strata, found {len(strata_present)}: {strata_present}")
    quotas = stratum_quotas(strata_present, total=TOTAL)

    by_stratum: dict[str, list[str]] = {name: [] for name in strata_present}
    for uid, entry in candidates.items():
        by_stratum[str(entry["stratum"])].append(uid)
    for name in by_stratum:
        by_stratum[name].sort()

    drawn_items: list[dict[str, object]] = []
    uniform_pools: dict[str, list[str]] = {}
    for stratum in strata_present:
        pool_ids = by_stratum[stratum]
        quota = quotas[stratum]
        if len(pool_ids) < quota:
            raise SystemExit(
                f"stratum {stratum!r} has {len(pool_ids)} eligible utterances, needs {quota}"
            )
        vecs = np.array(
            [vectors_table[candidates[uid]["facet_id"]]["content"] for uid in pool_ids],
            dtype=np.float64,
        )
        drawn = farthest_point_draw(pool_ids, vecs, quota, seed_text=f"{SEED}:{stratum}")
        for rank, (uid, min_cosine) in enumerate(drawn):
            entry = candidates[uid]
            drawn_items.append(
                {
                    "utterance_id": uid,
                    "stratum": stratum,
                    "sample_id": entry["sample_id"],
                    "draw_rank": rank,
                    "min_cosine_to_selected": min_cosine,
                }
            )
        # a seeded uniform draw of the SAME size from the SAME eligible pool,
        # for the diversity_report's baseline comparison.
        urng = random.Random(f"{SEED}:uniform:{stratum}")
        uniform_pools[stratum] = urng.sample(pool_ids, quota)

    if len(drawn_items) != TOTAL:
        raise SystemExit(f"draw resolved {len(drawn_items)} rows, expected {TOTAL}")

    # ---- media facts (loader-legal identity + media layer only) -----------
    wanted_sample_ids = {str(item["sample_id"]) for item in drawn_items}
    record_by_id = {
        record.sample_id: record
        for record in load_slurp_split(lock, root, "train")
        if record.sample_id in wanted_sample_ids
    }
    missing_media = sorted(wanted_sample_ids - set(record_by_id))
    if missing_media:
        raise SystemExit(f"{len(missing_media)} drawn recording(s) absent from the TRAIN loader")

    roster_candidates: list[RosterItem] = []
    for item in drawn_items:
        sample_id = str(item["sample_id"])
        record = record_by_id[sample_id]
        roster_candidates.append(
            RosterItem(
                sample_id=sample_id,
                stratum=str(item["stratum"]),
                extra={
                    "utterance_id": str(item["utterance_id"]),
                    "audio_seconds": round(float(record.audio_seconds), 9),
                    "headset": is_headset(record.media_relpath),
                    "draw_rank": int(item["draw_rank"]),
                    "min_cosine_to_selected": item["min_cosine_to_selected"],
                },
            )
        )

    receipt = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=roster_candidates,
        per_stratum=quotas,
        seed=SEED,
        split_role=SPLIT_ROLE,
        roster_id=ROSTER_ID,
        roster_role=ROSTER_ROLE,
    )
    if receipt["excluded_count"] != 0:
        raise SystemExit("freeze_roster excluded a candidate unexpectedly")
    if len(receipt["items"]) != TOTAL:
        raise SystemExit(f"frozen roster carries {len(receipt['items'])} items, expected {TOTAL}")

    # ---- disjointness proof (six forbidden rosters) ------------------------
    final_recordings = {str(item["sample_id"]) for item in receipt["items"]}
    final_utterances = {utterance_of(sid) for sid in final_recordings}
    disjointness: dict[str, object] = dict(
        disjointness_report(final_recordings, final_utterances, forbidden_recording_ids)
    )
    for name, entry in disjointness.items():
        if entry["shared_recordings"] or entry["shared_utterances"]:
            raise SystemExit(f"disjointness proof failed against {entry['relpath']}")
    disjointness["excluded_utterances_before_the_draw"] = len(excluded_utterances)

    # ---- diversity report ---------------------------------------------------
    per_stratum_diversity: dict[str, object] = {}
    for stratum in strata_present:
        drawn_ids = sorted(
            str(item["utterance_id"])
            for item in receipt["items"]
            if item["stratum"] == stratum
        )
        drawn_vecs = np.array(
            [vectors_table[candidates_by_utterance_facet(candidates, uid)]["content"] for uid in drawn_ids],
            dtype=np.float64,
        )
        uniform_ids = sorted(uniform_pools[stratum])
        uniform_vecs = np.array(
            [vectors_table[candidates_by_utterance_facet(candidates, uid)]["content"] for uid in uniform_ids],
            dtype=np.float64,
        )
        per_stratum_diversity[stratum] = {
            "n": len(drawn_ids),
            "mean_pairwise_cosine_farthest_point_draw": mean_pairwise_cosine(drawn_vecs),
            "mean_pairwise_cosine_seeded_uniform_draw": mean_pairwise_cosine(uniform_vecs),
        }
    pooled_draw_mean = sum(
        v["mean_pairwise_cosine_farthest_point_draw"] * v["n"] for v in per_stratum_diversity.values()
    ) / TOTAL
    pooled_uniform_mean = sum(
        v["mean_pairwise_cosine_seeded_uniform_draw"] * v["n"] for v in per_stratum_diversity.values()
    ) / TOTAL
    diversity_report = {
        "method": (
            "Per stratum: mean pairwise cosine (off-diagonal mean of the unit-vector Gram "
            "matrix) of the farthest-point draw versus a seeded-uniform draw of the same "
            "size from the same eligible pool (random.Random(f'{seed}:uniform:{stratum}')"
            ".sample). A lower mean for the farthest-point draw is the diversity claim; "
            "'pooled' is the n-weighted average of the per-stratum means."
        ),
        "per_stratum": per_stratum_diversity,
        "pooled": {
            "n": TOTAL,
            "mean_pairwise_cosine_farthest_point_draw": pooled_draw_mean,
            "mean_pairwise_cosine_seeded_uniform_draw": pooled_uniform_mean,
            "farthest_point_draw_is_more_diverse": pooled_draw_mean < pooled_uniform_mean,
        },
    }

    receipt["generator"] = GENERATOR
    receipt["authority"] = AUTHORITY
    receipt["pool_receipt"] = {
        "relpath": POOL_RECEIPT_RELPATH,
        "sha256": hashlib.sha256((REPO_ROOT / POOL_RECEIPT_RELPATH).read_bytes()).hexdigest(),
        "snapshot_relpath": pool_receipt["snapshot_artifact_relpath"],
        "snapshot_sha256": pool_receipt["snapshot_sha256"],
        "value_count": pool_receipt["value_count"],
    }
    receipt["vectors"] = {
        "relpath": VECTORS_RELPATH,
        "sha256": VECTORS_SHA256,
        "dimension": "content",
    }
    receipt["disjointness_proof"] = disjointness
    receipt["diversity_report"] = diversity_report
    receipt["draw_method"] = (
        "Per stratum, farthest-point traversal (module docstring): first point uniform "
        "random, each later point the remaining candidate whose cosine similarity to its "
        "closest already-selected neighbour is smallest, ties broken by ascending "
        "utterance_id then a seeded rng. core.roster.freeze_roster is then called with "
        "exactly the drawn items as the whole eligible pool per stratum (quota == pool "
        "size), so its own uniform shuffle selects all of them and the schema/hash/"
        "disjointness machinery is the canonical one."
    )
    receipt["offline_guard"] = {
        "outbound_connection_attempts": attempts.count,
        "attempted_targets": list(attempts.targets),
    }

    print(
        json.dumps(
            {
                "roster_id": receipt["roster_id"],
                "split_identity_hash": receipt["split_identity_hash"],
                "per_stratum": receipt["per_stratum"],
                "strata_counts": receipt["strata_counts"],
                "disjointness_proof": {
                    k: v for k, v in disjointness.items() if k != "excluded_utterances_before_the_draw"
                },
                "excluded_utterances_before_the_draw": disjointness[
                    "excluded_utterances_before_the_draw"
                ],
                "diversity_report_pooled": diversity_report["pooled"],
                "offline_guard": receipt["offline_guard"],
            },
            indent=2,
            sort_keys=True,
        )
    )

    if not args.write:
        return 0

    write_roster(receipt, REPO_ROOT / ROSTER_RELPATH)
    print(f"wrote {ROSTER_RELPATH}")

    # ---- runtime view (media identity only; DEV-2000-ADDED canonicalisation) --
    sample_ids_sorted = sorted(str(item["sample_id"]) for item in receipt["items"])
    view_items: list[dict[str, object]] = []
    for sample_id in sample_ids_sorted:
        record = record_by_id[sample_id]
        _, confined_path = _confined_media_path(
            root, record.media_relpath, context=f"STAGE3-CONSTRUCTION-R01 sample {sample_id!r}"
        )
        media_bytes, media_sha256, audio_seconds, sample_rate_hz = _probe_speech_media(
            confined_path
        )
        view_items.append(
            {
                "sample_id": sample_id,
                "media_relpath": record.media_relpath,
                "audio_sha256": media_sha256,
                "audio_seconds": round(float(audio_seconds), 9),
                "sample_rate_hz": int(sample_rate_hz),
                "packet_id": sample_id.replace(":", "/"),
            }
        )
    unsigned: dict[str, object] = {
        "schema": "saea-speech-native-runtime-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": SPLIT_ROLE,
        "seed": receipt["seed"],
        "split_identity_hash": receipt["split_identity_hash"],
        "source_binding_sha256": canonical_sha256(receipt),
        "d1_media_supplement": None,
        "d1_media_supplement_sha256": None,
        "d1_manifest_sha256": None,
        "count": len(view_items),
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in view_items), 9
        ),
        "items": view_items,
    }
    runtime_view = {**unsigned, "runtime_view_sha256": canonical_sha256(unsigned)}
    view_sha = write_json(REPO_ROOT / RUNTIME_VIEW_RELPATH, runtime_view)
    print(f"wrote {RUNTIME_VIEW_RELPATH} (file sha256 {view_sha})")
    print(f"runtime_view_sha256 = {runtime_view['runtime_view_sha256']}")
    return 0


def candidates_by_utterance_facet(candidates: Mapping[str, Mapping[str, object]], uid: str) -> str:
    return str(candidates[uid]["facet_id"])


if __name__ == "__main__":
    raise SystemExit(main())
