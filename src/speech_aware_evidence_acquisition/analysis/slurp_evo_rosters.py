"""The three EVO-S1 loop rosters on SLURP TRAIN (model-free, identity only).

Exposure row ``SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V1``. Authority
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` sections
4c and 5; capacity ``docs/checks/speech-aware-evidence-acquisition/
2026-09-06-slurp-evo-construction-capacity/capacity.json``.

Three slices, one set of quotas per scenario, all through
:func:`core.roster.freeze_roster` -- the one roster freezer -- with
``split_role="discovery"`` and ``roster_role="construction"``:

* ``SLURP-EVO-FOLD-A-V1``  -- 30 utterances per scenario, the round's
  selection population;
* ``SLURP-EVO-FOLD-B-V1``  -- 30 per scenario, disjoint, the confirmation
  population;
* ``SLURP-EVO-EXEMPLARS-V1`` -- 24 ENTITY-BEARING utterances per scenario,
  disjoint from both folds, and the only roster whose gold the
  ``construction-proposer-text`` arm may read.

Two rules that are decisions rather than mechanics, stated here once.

**The block is the utterance, not the recording.** SLURP writes a sentence
once and several speakers read it into a headset and a far-field microphone:
11,514 utterances, 50,628 recordings. ``exclude_groups`` keys every recording
by its utterance, so at most one recording per utterance is ever drawn and
excluding an utterance takes all of its recordings with it. Without that, fold
B could confirm a candidate on the very sentence fold A selected it on.

**Folds are drawn first and the exemplars come out of the remainder.** The
reverse order would remove entity-bearing utterances from the pool before the
folds are drawn and leave the reward population thinner in entities than the
scenario really is -- on ``audio``, where only 57 of 290 utterances carry an
entity, visibly so. The folds have to look like their scenario; the exemplar
pool only has to be large enough that three seeded draws of ``M = 8`` differ.

No channel quota is imposed. TRAIN's natural mixture is 47.82 % headset and
DEV-1000's realized mixture under the same one-recording-per-utterance rule is
47.8 %, so a uniform draw over an utterance's recordings already reproduces
the read population's channel mix.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from ..core.roster import CONSTRUCTION_ROSTER_ROLE, RosterItem, freeze_roster
from ..data.slurp import SlurpRecord

FOLD_A_ID = "SLURP-EVO-FOLD-A-V1"
FOLD_B_ID = "SLURP-EVO-FOLD-B-V1"
EXEMPLARS_ID = "SLURP-EVO-EXEMPLARS-V1"
CARRIER = "slurp"
SEED = 20260906
SPLIT_ROLE = "discovery"

FOLD_QUOTA = 30
EXEMPLAR_QUOTA = 24

SELECTION_RULE = (
    "core.roster.freeze_roster, one shared random.Random(seed) advanced across "
    "the scenarios in ascending name order over each scenario's id-sorted "
    "recording pool. exclude_groups keys every recording by its utterance, so "
    "at most one recording per utterance is ever selected and an excluded "
    "utterance takes all of its recordings with it; the recording that lands "
    "is whichever of that utterance's recordings the shuffle reaches first, "
    "which is uniform over the utterance's recordings and imposes no headset / "
    "far-field quota. Draw order: fold A from the whole TRAIN pool, fold B "
    "from the pool minus fold A's utterances, exemplars from the pool minus "
    "both folds' utterances and restricted to utterances carrying at least one "
    "gold entity. Every TRAIN utterance this study has already touched -- the "
    "739 named by the committed probe-sample receipts, speech-native dataset "
    "fragments, D1 supplements and g0 bindings -- is excluded from the "
    "candidate pool before any of the three draws."
)


#: Every committed record that NAMES a SLURP ``train`` identity: the probe
#: rosters this study has actually contacted and the g0 bindings that placed
#: TRAIN recordings into a knowledge plane. Their union is the set of TRAIN
#: utterances a fold must not contain if the folds are to be reported as an
#: untouched construction population. Listed explicitly, never globbed, so a
#: receipt can name its own exclusion sources and a reviewer can recount them.
TOUCHED_TRAIN_SOURCES: tuple[str, ...] = (
    "configs/probes/g0-binding/speech-native-train-binding.json",
    "configs/probes/g0-binding/speech-native-train-binding-effect-c108.json",
    "configs/probes/g0-binding/speech-native-train-binding-evidence-e108.json",
    "configs/probes/g0-binding/speech-native-train-binding-evidence-e108-data-knowledge.json",
    "configs/probes/g0-binding/speech-native-train-binding-evidence-e108-information-complete-knowledge.json",
    "configs/probes/g0-binding/speech-native-train-binding-factor-d108.json",
    "configs/probes/g0-binding/speech-native-train-binding-gate-c36.json",
    "configs/probes/g0-binding/speech-native-train-binding-x108.json",
    "docs/receipts/probe-samples/DISCOVERY-X108.json",
    "docs/receipts/probe-samples/EFFECT-C108.json",
    "docs/receipts/probe-samples/ENG-GATE8.json",
    "docs/receipts/probe-samples/EVIDENCE-E108.json",
    "docs/receipts/probe-samples/FACTOR-D108.json",
    "docs/receipts/probe-samples/GATE-C36.json",
    "docs/receipts/probe-samples/GATE18.json",
    "docs/receipts/probe-samples/KEY18.json",
    "docs/receipts/probe-samples/OPT-A36.json",
    "docs/receipts/probe-samples/OPT-B18.json",
    "docs/receipts/probe-samples/TRAIN90.json",
)

_TRAIN_UTTERANCE_RE = re.compile(r"slurp:train:\d{6}")


class RosterSourceError(ValueError):
    """A declared exclusion source is missing or names no TRAIN identity."""


def touched_train_utterances(
    repo_root: Path, sources: Sequence[str] = TOUCHED_TRAIN_SOURCES
) -> tuple[set[str], list[dict[str, object]]]:
    """``(union, per-source account)`` of already-touched TRAIN utterances."""

    union: set[str] = set()
    rows: list[dict[str, object]] = []
    for relpath in sources:
        path = Path(repo_root) / relpath
        if not path.is_file():
            raise RosterSourceError(f"touched-TRAIN source missing: {relpath}")
        found = set(_TRAIN_UTTERANCE_RE.findall(path.read_text(encoding="utf-8")))
        if not found:
            raise RosterSourceError(
                f"touched-TRAIN source names no train identity: {relpath}"
            )
        rows.append(
            {
                "relpath": relpath,
                "utterances": len(found),
                "new_utterances": len(found - union),
            }
        )
        union |= found
    return union, rows


def utterance_of(sample_id: str) -> str:
    """``slurp:train:001206:audio-1489503509`` -> ``slurp:train:001206``."""

    return sample_id.rsplit(":", 1)[0]


def candidates(records: Sequence[SlurpRecord]) -> tuple[list[RosterItem], dict[str, str]]:
    """``(items, groups)`` for :func:`core.roster.freeze_roster`.

    ``extra`` carries the two audit facts the loop's budget and its media
    artifacts need -- the utterance block and the recording's duration -- and
    the legacy ``id``/``key`` pair every SLURP receipt in this repository
    already publishes. Gold entities never enter the receipt: only the boolean
    the exemplar filter needs.
    """

    items = [
        RosterItem(
            sample_id=record.sample_id,
            stratum=record.scenario,
            extra={
                "id": record.sample_id,
                "key": f"{CARRIER}:{record.sample_id}",
                "utterance_id": utterance_of(record.sample_id),
                "audio_seconds": record.audio_seconds,
                "headset": record.media_relpath.endswith("-headset.flac"),
            },
        )
        for record in records
    ]
    groups = {record.sample_id: utterance_of(record.sample_id) for record in records}
    return items, groups


def _sample_ids_of(receipt: Mapping[str, object]) -> set[str]:
    return {str(item["sample_id"]) for item in receipt["items"]}  # type: ignore[index]


def _utterances_of(receipt: Mapping[str, object]) -> set[str]:
    return {utterance_of(sample_id) for sample_id in _sample_ids_of(receipt)}


def freeze_evo_rosters(
    records: Sequence[SlurpRecord],
    *,
    seed: int = SEED,
    fold_quota: int = FOLD_QUOTA,
    exemplar_quota: int = EXEMPLAR_QUOTA,
    exclude_sample_ids: Sequence[str] = (),
) -> dict[str, dict[str, object]]:
    """Freeze fold A, fold B and the exemplar pool, in that order.

    ``exclude_sample_ids`` is the set of TRAIN identities this study has
    already TOUCHED -- every ``slurp:train:...`` id named by a committed
    probe-sample receipt, speech-native dataset fragment, D1 supplement or
    g0 binding. Naming one recording of an utterance removes the whole
    utterance, because ``exclude_groups`` keys recordings by utterance. A
    construction roster does not strictly have to avoid them (construction
    rows are read with their gold by design), but a fold that contains a
    recording the frozen core has already been shown cannot be reported as
    an untouched construction population, and the corpus is large enough
    that the cleanliness costs nothing.
    """

    items, groups = candidates(records)
    excluded = sorted(set(exclude_sample_ids))
    fold_a = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=items,
        per_stratum=fold_quota,
        seed=seed,
        split_role=SPLIT_ROLE,
        exclude_sample_ids=excluded,
        exclude_groups=groups,
        roster_id=FOLD_A_ID,
        roster_role=CONSTRUCTION_ROSTER_ROLE,
    )
    fold_b = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=items,
        per_stratum=fold_quota,
        seed=seed,
        split_role=SPLIT_ROLE,
        exclude_sample_ids=sorted(set(excluded) | _sample_ids_of(fold_a)),
        exclude_groups=groups,
        roster_id=FOLD_B_ID,
        roster_role=CONSTRUCTION_ROSTER_ROLE,
    )
    entity_bearing = [
        item
        for record, item in zip(records, items, strict=True)
        if record.entities
    ]
    exemplars = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=entity_bearing,
        per_stratum=exemplar_quota,
        seed=seed,
        split_role=SPLIT_ROLE,
        exclude_sample_ids=sorted(
            set(excluded) | _sample_ids_of(fold_a) | _sample_ids_of(fold_b)
        ),
        exclude_groups=groups,
        roster_id=EXEMPLARS_ID,
        roster_role=CONSTRUCTION_ROSTER_ROLE,
    )
    return {"fold_a": fold_a, "fold_b": fold_b, "exemplars": exemplars}


def disjointness_proof(
    cut: Mapping[str, Mapping[str, object]],
    *,
    devel_ids: Sequence[str],
    test_ids: Sequence[str],
    contacted_train_utterances: Sequence[str],
) -> dict[str, object]:
    """Every overlap the receipts refuse to be written with; all must be 0.

    ``devel_ids`` and ``test_ids`` are RECORDING ids and come from the
    committed frozen enumeration
    ``docs/receipts/knowledge/slurp-split-identity.json``, never from a live
    read of those splits. ``contacted_train_utterances`` are UTTERANCE ids
    (``slurp:train:001206``), the granularity at which a previously touched
    sentence has to be kept out of a fold.
    """

    names = ("fold_a", "fold_b", "exemplars")
    ids = {name: _sample_ids_of(cut[name]) for name in names}
    blocks = {name: _utterances_of(cut[name]) for name in names}
    devel = set(devel_ids)
    test = set(test_ids)
    contacted = set(contacted_train_utterances)
    proof: dict[str, object] = {}
    for left, right in (("fold_a", "fold_b"), ("fold_a", "exemplars"), ("fold_b", "exemplars")):
        proof[f"shared_recordings_{left}_{right}"] = len(ids[left] & ids[right])
        proof[f"shared_utterances_{left}_{right}"] = len(blocks[left] & blocks[right])
    for name in names:
        recordings_per_block = Counter(
            utterance_of(sample_id) for sample_id in ids[name]
        )
        proof[f"max_recordings_per_utterance_{name}"] = (
            max(recordings_per_block.values()) if recordings_per_block else 0
        )
        proof[f"non_train_ids_{name}"] = sum(
            1 for sample_id in ids[name] if not sample_id.startswith("slurp:train:")
        )
        proof[f"shared_with_devel_{name}"] = len(ids[name] & devel)
        proof[f"shared_with_test_{name}"] = len(ids[name] & test)
        proof[f"shared_with_contacted_train_{name}"] = len(blocks[name] & contacted)
    return proof


def roster_documents(
    cut: Mapping[str, Mapping[str, object]],
    *,
    proof: Mapping[str, object],
    shared: Mapping[str, object],
) -> list[tuple[str, dict[str, object]]]:
    """``(stem, receipt)`` pairs ready for :func:`core.roster.write_roster`."""

    stems = {
        "fold_a": "slurp-evo-fold-a-v1",
        "fold_b": "slurp-evo-fold-b-v1",
        "exemplars": "slurp-evo-exemplars-v1",
    }
    documents: list[tuple[str, dict[str, object]]] = []
    for name, stem in stems.items():
        receipt = dict(cut[name])
        items = list(receipt["items"])  # type: ignore[arg-type]
        blocks = {utterance_of(str(item["sample_id"])) for item in items}
        headset = sum(1 for item in items if item.get("headset"))
        seconds = sum(float(item["audio_seconds"]) for item in items)
        receipt.update(dict(shared))
        receipt.update(
            {
                "selection_rule": SELECTION_RULE,
                "block_unit": "utterance id",
                "distinct_utterances": len(blocks),
                "audio_seconds_total": round(seconds, 6),
                "headset_recordings": headset,
                "far_field_recordings": len(items) - headset,
                "headset_share": round(headset / len(items), 6) if items else 0.0,
                "disjointness_proof": dict(proof),
            }
        )
        documents.append((stem, receipt))
    return documents


__all__ = [
    "CARRIER",
    "TOUCHED_TRAIN_SOURCES",
    "RosterSourceError",
    "touched_train_utterances",
    "EXEMPLARS_ID",
    "EXEMPLAR_QUOTA",
    "FOLD_A_ID",
    "FOLD_B_ID",
    "FOLD_QUOTA",
    "SEED",
    "SELECTION_RULE",
    "candidates",
    "disjointness_proof",
    "freeze_evo_rosters",
    "roster_documents",
    "utterance_of",
]
