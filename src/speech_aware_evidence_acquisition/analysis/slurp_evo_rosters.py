"""The three EVO-S1 loop rosters on SLURP TRAIN (model-free, identity only).

Exposure rows ``SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V1`` (the 30-per-scenario
draw of 2026-09-06) and ``SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V2`` (the
60-per-scenario re-draw the coordinator ordered the same day). Authority
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` sections
4c and 5; capacity ``docs/checks/speech-aware-evidence-acquisition/
2026-09-06-slurp-evo-construction-capacity/capacity.json``.

Three slices, one set of quotas per scenario, all through
:func:`core.roster.freeze_roster` -- the one roster freezer -- with
``split_role="discovery"`` and ``roster_role="construction"``:

* ``SLURP-EVO-FOLD-A-<version>``  -- the round's selection population;
* ``SLURP-EVO-FOLD-B-<version>``  -- the same shape on disjoint utterances,
  the confirmation population;
* ``SLURP-EVO-EXEMPLARS-<version>`` -- 24 ENTITY-BEARING utterances per
  scenario, disjoint from both folds, and the only roster whose gold the
  ``construction-proposer-text`` arm may read.

**Why there are two versions.** V1 drew 30 per scenario. Scaling KC-S1b's
measured per-stratum saves down to 30 rows clears the stage-one count gate
(``saves >= 4, harms <= 1, net >= 3``) in only three of eighteen scenarios,
so the preregistered kill result "no scenario admitted in rounds 1 and 2"
would most likely fire for a statistical reason rather than a mechanism one.
The coordinator took remedy (b) of preregistration section 16 open point 1 --
60 per scenario, 1,080 rows per fold -- and this module takes that as its
``version="V2"`` argument. Nothing else changed: same seed, same exclusions,
same draw order, same proofs. The V1 receipts stay committed as history and
are never overwritten.

:func:`stage_one_power` prices that gate at any fold size from KC-S1b's own
per-stratum table, and the receipt under ``docs/checks/
speech-aware-evidence-acquisition/2026-09-06-slurp-evo-stage-one-power/`` is
the audited answer: **three of eighteen at 30 rows and seven of eighteen at
60**, not the nine an earlier draft of the preregistration asserted. The
re-draw is still worth its price -- it more than doubles the admissible set
-- but the gain is smaller than it was written down as, and one scenario
(``transport``) LEAVES the admissible set at 60 because the harms bound is
an absolute row count that does not scale with the fold.

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

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Collection, Mapping, Sequence

from ..core.roster import CONSTRUCTION_ROSTER_ROLE, RosterItem, freeze_roster
from ..data.slurp import SlurpRecord

AUTHORITY = "docs/readiness/2026-09-05-three-dimension-experiment-program.md"
PREREGISTRATION = (
    "docs/readiness/2026-09-06-slurp-evo-s1-slot-schema-evolution-v1-preregistration.md"
)
CAPACITY_ROW_ID = "SAEA-SLURP-MF-EVO-CONSTRUCTION-CAPACITY-V1"
CAPACITY_RECEIPT = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-06-slurp-evo-construction-capacity/capacity.json"
)
SPLIT_IDENTITY_RECEIPT = "docs/receipts/knowledge/slurp-split-identity.json"
RESERVED_ROSTER_NOTE = (
    "SLURP-DEV-500-B-V1 is not opened here. Its own receipt declares carrier "
    "slurp and split_role 'dev', so every one of its identities is a member of "
    "the devel enumeration above, which these rosters are proved disjoint from "
    "id by id."
)

#: The three slices, in draw order, with the slug each roster id and each
#: receipt stem is built from. One version string parameterises all three,
#: so a re-draw is a new argument rather than a second module: the V2 draw
#: of 2026-09-06 (60 utterances per scenario, coordinator decision 1 on
#: preregistration section 16 open point 1) is this module at
#: ``version="V2"``, and the V1 receipts stay committed as history.
ROSTER_SLUGS: Mapping[str, str] = {
    "fold_a": "fold-a",
    "fold_b": "fold-b",
    "exemplars": "exemplars",
}
DEFAULT_VERSION = "V1"

CARRIER = "slurp"
SEED = 20260906
SPLIT_ROLE = "discovery"

FOLD_QUOTA = 30
EXEMPLAR_QUOTA = 24

#: Coordinator decision 1 of 2026-09-06: remedy (b) of open point 1, folds at
#: 60 utterances per scenario, exemplars unchanged, same seed, same
#: exclusions, same proofs.
FOLD_QUOTA_V2 = 60
EXEMPLAR_QUOTA_V2 = 24

#: The smallest exemplar pool a scenario may end with. ``M = 8`` utterances
#: are drawn per proposer slot and a round has three slots, so a pool of
#: ``2 * M`` still makes the three seeded draws differ in MEMBERSHIP and not
#: only in order -- which is the whole reason the target is 3 x M. Below this
#: the draw is refused rather than quietly weakened.
EXEMPLAR_FLOOR = 16


def _checked_version(version: str) -> str:
    """A roster version is ``V`` followed by digits; anything else is refused."""

    if (
        not isinstance(version, str)
        or len(version) < 2
        or version[0] != "V"
        or not version[1:].isdigit()
    ):
        raise RosterSourceError(f"roster version must look like 'V2'; got {version!r}")
    return version


def roster_id(name: str, version: str = DEFAULT_VERSION) -> str:
    """``("fold_a", "V2")`` -> ``"SLURP-EVO-FOLD-A-V2"``."""

    return f"SLURP-EVO-{ROSTER_SLUGS[name].upper()}-{_checked_version(version)}"


def roster_stem(name: str, version: str = DEFAULT_VERSION) -> str:
    """``("fold_a", "V2")`` -> ``"slurp-evo-fold-a-v2"`` (the receipt stem)."""

    return f"slurp-evo-{ROSTER_SLUGS[name]}-{_checked_version(version).lower()}"


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


def exemplar_quotas(
    entity_bearing: Sequence[RosterItem],
    *,
    spent: Collection[str],
    groups: Mapping[str, str],
    target: int,
    floor: int = EXEMPLAR_FLOOR,
) -> tuple[dict[str, int], dict[str, object]]:
    """``(per-scenario quota, the policy record)`` for the exemplar draw.

    The folds are drawn first and they are the scientific population: they
    have to look like their scenario, in entity density as in everything
    else. Drawing the exemplars first would fix that ordering problem by
    creating a worse one -- on ``audio``, where only 57 of 290 TRAIN
    utterances carry an entity, reserving 24 entity-bearing sentences before
    the folds would strip about a third of the fold rows that can score at
    all. So the folds keep their full quota and the exemplar target yields
    where the remainder cannot meet it.

    At 60 utterances per scenario per fold (the V2 draw) exactly one scenario
    hits that wall: ``audio`` has 22 entity-bearing utterances left after both
    folds, against a target of 24. Its pool is capped at 22, which is still
    2.75 x ``M``, and the cap is RECORDED per scenario rather than absorbed.
    A scenario that cannot reach ``floor`` is refused outright.
    """

    # A floor above the target is incoherent -- it would refuse a draw the
    # caller never asked for -- so the target caps it.
    floor = min(floor, target)
    spent_ids = set(spent)
    spent_groups = {groups[sid] for sid in spent_ids if sid in groups}
    # ``freeze_roster`` picks at most one recording per group, so a stratum's
    # capacity is its count of eligible UTTERANCES, never of recordings.
    eligible: dict[str, set[str]] = {}
    for item in entity_bearing:
        group = groups.get(item.sample_id, item.sample_id)
        if item.sample_id in spent_ids or group in spent_groups:
            continue
        eligible.setdefault(item.stratum, set()).add(group)
    quotas = {stratum: min(target, len(blocks)) for stratum, blocks in eligible.items()}
    short = {
        stratum: count for stratum, count in quotas.items() if count < target
    }
    starved = sorted(stratum for stratum, count in quotas.items() if count < floor)
    if starved:
        raise RosterSourceError(
            f"exemplar pool below the floor of {floor} in {starved}; the draw is "
            "refused rather than weakened"
        )
    return dict(sorted(quotas.items())), {
        "target_per_scenario": target,
        "floor_per_scenario": floor,
        "realized_per_scenario": dict(sorted(quotas.items())),
        "capped_scenarios": dict(sorted(short.items())),
        "rule": (
            "the folds are drawn first and keep their full quota, because they "
            "are the scientific population and must carry their scenario's own "
            "entity density; the exemplar target yields to whatever "
            "entity-bearing utterances the remainder holds, never below the "
            "floor, and every capped scenario is named here."
        ),
    }


def freeze_evo_rosters(
    records: Sequence[SlurpRecord],
    *,
    seed: int = SEED,
    fold_quota: int = FOLD_QUOTA,
    exemplar_quota: int = EXEMPLAR_QUOTA,
    exemplar_floor: int = EXEMPLAR_FLOOR,
    exclude_sample_ids: Sequence[str] = (),
    version: str = DEFAULT_VERSION,
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

    ``exemplar_quota`` is a TARGET, not a promise: see :func:`exemplar_quotas`
    for what happens when the remainder after the folds cannot fill it.
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
        roster_id=roster_id("fold_a", version),
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
        roster_id=roster_id("fold_b", version),
        roster_role=CONSTRUCTION_ROSTER_ROLE,
    )
    entity_bearing = [
        item
        for record, item in zip(records, items, strict=True)
        if record.entities
    ]
    spent = set(excluded) | _sample_ids_of(fold_a) | _sample_ids_of(fold_b)
    quotas, policy = exemplar_quotas(
        entity_bearing,
        spent=spent,
        groups=groups,
        target=exemplar_quota,
        floor=exemplar_floor,
    )
    exemplars = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=entity_bearing,
        per_stratum=quotas,
        seed=seed,
        split_role=SPLIT_ROLE,
        exclude_sample_ids=sorted(spent),
        exclude_groups=groups,
        roster_id=roster_id("exemplars", version),
        roster_role=CONSTRUCTION_ROSTER_ROLE,
    )
    exemplars["exemplar_quota_policy"] = policy
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


def summary_lines(
    documents: Sequence[tuple[str, Mapping[str, object]]]
) -> list[str]:
    """One line per roster plus its strata, for the generator's stdout."""

    lines: list[str] = []
    for _stem, document in documents:
        lines.append(
            f"{document['roster_id']}: {len(document['items'])} recordings, "  # type: ignore[arg-type]
            f"{document['distinct_utterances']} utterances, "
            f"{float(document['audio_seconds_total']):.4f} s, "
            f"{float(document['headset_share']) * 100:.1f} % headset, "
            f"identity {document['split_identity_hash']}"
        )
        lines.append(f"  strata: {document['strata_counts']}")
    return lines


def assert_clean_cut(proof: Mapping[str, object]) -> None:
    """Refuse a cut whose proof is not perfect; the write never sees it.

    Every count in the proof must be 0 except the per-roster
    ``max_recordings_per_utterance_*`` entries, which must be exactly 1.
    """

    def expected(key: str) -> int:
        return 1 if key.startswith("max_recordings_per_utterance") else 0

    offenders = {
        key: value for key, value in proof.items() if value != expected(key)
    }
    if offenders:
        raise RosterSourceError(f"the EVO-S1 cut is not disjoint: {offenders}")


def pool_block(
    records: Sequence[SlurpRecord],
    *,
    touched: Collection[str],
    excluded_recordings: int,
    touched_rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """The ``pool`` block every roster receipt carries: what the draw saw."""

    blocks = {utterance_of(record.sample_id) for record in records}
    return {
        "source": "the governed SLURP train split, every real recording",
        "train_recordings": len(records),
        "train_utterances": len(blocks),
        "entity_bearing_utterances": len(
            {utterance_of(record.sample_id) for record in records if record.entities}
        ),
        "touched_train_utterances": len(set(touched)),
        "touched_train_recordings": excluded_recordings,
        "eligible_utterances": len(blocks - set(touched)),
        "touched_train_source_count": len(TOUCHED_TRAIN_SOURCES),
        "touched_train_sources": list(touched_rows),
    }


def exposure_row_id(version: str = DEFAULT_VERSION) -> str:
    """The model-free exposure row that covers one draw."""

    return f"SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-{_checked_version(version)}"


def supersedes_block(
    rosters_dir: Path, version: str, decision: str
) -> dict[str, object]:
    """Name, by relpath and file SHA-256, the receipts a re-draw replaces.

    The superseded receipts stay committed and are never overwritten; a
    re-draw re-uses none of their identities, so it inherits none of their
    exposure either -- neither draw has ever been contacted.
    """

    if not decision:
        raise RosterSourceError("a superseding draw must name the ruling that ordered it")
    rows: list[dict[str, object]] = []
    for name in ROSTER_SLUGS:
        path = Path(rosters_dir) / f"{roster_stem(name, version)}.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        rows.append(
            {
                "relpath": f"docs/receipts/rosters/{path.name}",
                "roster_id": document["roster_id"],
                "recordings": len(document["items"]),
                "split_identity_hash": document["split_identity_hash"],
                "receipt_file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return {
        "version": version,
        "exposure_row": exposure_row_id(version),
        "rosters": rows,
        "decision": decision,
        "history_note": (
            "The superseded receipts stay committed and are never overwritten; "
            "this draw re-uses none of their identities and inherits none of "
            "their exposure, because neither draw has been contacted."
        ),
    }


def shared_block(
    records: Sequence[SlurpRecord],
    *,
    touched: Collection[str],
    touched_rows: Sequence[Mapping[str, object]],
    excluded_recordings: int,
    split_identity: Mapping[str, object],
    version: str,
    offline_guard: Mapping[str, object],
    supersedes: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """The provenance block every roster receipt of one draw carries."""

    splits = split_identity["splits"]  # type: ignore[index]
    block: dict[str, object] = {
        "authority": AUTHORITY,
        "preregistration": PREREGISTRATION,
        "generator": "scripts/build_slurp_evo_fold_rosters.py",
        "roster_version": _checked_version(version),
        "exposure_row": exposure_row_id(version),
        "capacity_row": CAPACITY_ROW_ID,
        "capacity_receipt": CAPACITY_RECEIPT,
        "pool": pool_block(
            records,
            touched=touched,
            excluded_recordings=excluded_recordings,
            touched_rows=touched_rows,
        ),
        "split_identity_receipt": {
            "relpath": SPLIT_IDENTITY_RECEIPT,
            "devel_identity_hash": splits["devel"]["identity_hash"],
            "devel_ids": splits["devel"]["count"],
            "test_identity_hash": splits["test"]["identity_hash"],
            "test_ids": splits["test"]["count"],
        },
        "reserved_roster_note": RESERVED_ROSTER_NOTE,
        "offline_guard": dict(offline_guard),
    }
    if supersedes is not None:
        block["supersedes"] = dict(supersedes)
    return block


def roster_documents(
    cut: Mapping[str, Mapping[str, object]],
    *,
    proof: Mapping[str, object],
    shared: Mapping[str, object],
    version: str = DEFAULT_VERSION,
) -> list[tuple[str, dict[str, object]]]:
    """``(stem, receipt)`` pairs ready for :func:`core.roster.write_roster`."""

    stems = {name: roster_stem(name, version) for name in ROSTER_SLUGS}
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


# ---------------------------------------------------------------------------
# Stage-one power: what a fold size buys, priced on KC-S1b's own measured table.
# ---------------------------------------------------------------------------

#: Preregistration section 6 step 4. All three are ABSOLUTE row counts, not
#: rates, because a reviewer has to be able to recount a stage-one decision by
#: hand. The consequence is that the gate is NOT scale-free: doubling the fold
#: doubles a scenario's expected harms while the harms bound stays at one.
ADMISSION_GATES: Mapping[str, int] = {"saves": 4, "harms": 1, "net": 3}

#: The only measured per-scenario save/harm table this study owns for the
#: mechanism EVO-S1 evolves: KC-S1b against the closed-list direct baseline,
#: pooled over the 1,000 DEV rows, on the reward metric.
KC_S1B_READ_RECEIPT = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-slurp-slot-stage-kc-s1-v1/read.json"
)
KC_S1B_CONTRAST = "paired_kc_s1b_over_closed_list"
KC_S1B_POPULATION = "pooled_1000"
REWARD_METRIC = "slot_f1_exact_f1"


def stage_one_power(
    per_stratum: Mapping[str, Mapping[str, object]],
    rows_per_scenario: int,
    *,
    gates: Mapping[str, int] = ADMISSION_GATES,
) -> list[dict[str, object]]:
    """Price the stage-one gate at ``rows_per_scenario``, per scenario.

    The scaling rule, stated once because the answer is sensitive to it: a
    scenario's measured saves and harms are turned into per-row RATES on the
    population they were measured on, multiplied by the fold size, and
    compared against the gate's own absolute constants WITHOUT rounding. No
    other reading is preregistered -- rounding the expected counts, or
    scaling the harms bound with the fold, each admits scenarios this one
    does not, and the difference is not cosmetic.
    """

    if rows_per_scenario <= 0:
        raise ValueError("rows_per_scenario must be positive")
    table: list[dict[str, object]] = []
    for scenario in sorted(per_stratum):
        row = per_stratum[scenario]
        measured = int(row["n"])  # type: ignore[arg-type]
        if measured <= 0:
            raise ValueError(f"stratum {scenario} has no measured rows")
        saves = int(row["saves"])  # type: ignore[arg-type]
        harms = int(row["harms"])  # type: ignore[arg-type]
        expected_saves = rows_per_scenario * saves / measured
        expected_harms = rows_per_scenario * harms / measured
        table.append(
            {
                "scenario": scenario,
                "measured_rows": measured,
                "measured_saves": saves,
                "measured_harms": harms,
                "expected_saves": round(expected_saves, 4),
                "expected_harms": round(expected_harms, 4),
                "expected_net": round(expected_saves - expected_harms, 4),
                "clears_gate": (
                    expected_saves >= gates["saves"]
                    and expected_harms <= gates["harms"]
                    and expected_saves - expected_harms >= gates["net"]
                ),
            }
        )
    return table


def stage_one_power_summary(
    table: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """``clears`` / ``scenarios`` / the names, for a receipt or a document."""

    clearing = [str(row["scenario"]) for row in table if row["clears_gate"]]
    return {
        "clears": len(clearing),
        "scenarios": len(table),
        "clearing_scenarios": clearing,
    }


__all__ = [
    "ADMISSION_GATES",
    "KC_S1B_CONTRAST",
    "KC_S1B_POPULATION",
    "KC_S1B_READ_RECEIPT",
    "REWARD_METRIC",
    "stage_one_power",
    "stage_one_power_summary",
    "CARRIER",
    "assert_clean_cut",
    "summary_lines",
    "pool_block",
    "TOUCHED_TRAIN_SOURCES",
    "RosterSourceError",
    "touched_train_utterances",
    "AUTHORITY",
    "CAPACITY_RECEIPT",
    "CAPACITY_ROW_ID",
    "DEFAULT_VERSION",
    "EXEMPLAR_FLOOR",
    "EXEMPLAR_QUOTA",
    "EXEMPLAR_QUOTA_V2",
    "FOLD_QUOTA",
    "FOLD_QUOTA_V2",
    "ROSTER_SLUGS",
    "SEED",
    "SELECTION_RULE",
    "candidates",
    "disjointness_proof",
    "exemplar_quotas",
    "exposure_row_id",
    "freeze_evo_rosters",
    "roster_documents",
    "roster_id",
    "roster_stem",
    "shared_block",
    "supersedes_block",
    "utterance_of",
]
