#!/usr/bin/env python3
"""CLI: build the SLURP construction-data SLOT AUDIT view (item E12, cell B8b).

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
scorer, GPU or network contacts. The output is the pinned table the Reviewer
slot-audit context block renders (``rails.slot_audit``), released as two
committed repository files plus a build receipt:

* ``knowledge/slurp/semantic/slot-audit-v1/snapshot.json`` -- per intent, the
  entity types attested with it in the CONSTRUCTION POOL and the share of that
  intent's construction rows carrying each; the share of its rows carrying no
  entity at all; and the two released ``date`` / ``time`` representation
  conventions, quoted from slot store v2.
* ``knowledge/slurp/semantic/slot-audit-v1/release.json`` -- the release
  identity that pins the snapshot's bytes and its construction source.
* ``docs/receipts/knowledge/slurp-slot-audit-v1.json`` -- the build receipt.

CONSTRUCTION DATA ONLY, and it refuses otherwise. Three independent guards:

1. The reader is ``data.slurp.load_slurp_intent_row_profiles``, whose split is
   a module constant with no ``split`` parameter and no caller-supplied path,
   so a devel or test metadata file cannot be reached through it at all.
2. Every utterance with a recording in TRAIN Fold A, TRAIN Fold B or DEV-1000
   (the 2026-09-13 exclusion, ``docs/readiness/2026-09-13-slurp-semantic-
   authoring-registration-v1.json`` ``forbidden_rosters``) is removed BEFORE a
   single count is accumulated, and :func:`refuse_evaluated_rows` re-checks
   afterwards that not one of them survived -- a disjointness proof over the
   retained identity, not a comment.
3. The retained pool must carry exactly the registered 9,354 utterances, the
   same number ``scripts/build_slurp_exemplar_pool_assets.py`` pins for the
   same exclusion; any other number stops the build.

The date / time conventions are quoted from the released slot store v2 under
``SPEECHRL_DATA_DIR`` and pinned by that snapshot's sha256, so the rule the
block states is the rule the ORG channel already ships -- never a second
wording. That store is read at BUILD time only; the runtime block reads the
two committed files and nothing else.

Usage::

    python scripts/build_slurp_slot_audit_view.py
    python scripts/build_slurp_slot_audit_view.py --check   # verify only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    load_slurp_intent_row_profiles,
    load_slurp_train_utterance_ids,
)
from speech_aware_evidence_acquisition.e0.artifacts import (  # noqa: E402
    write_json_artifact,
)
from speech_aware_evidence_acquisition.rails.slot_audit import (  # noqa: E402
    SLOT_AUDIT_BUILDER_POLICY_ID,
    SLOT_AUDIT_RELEASE_SCHEMA,
    SLOT_AUDIT_VIEW_ID,
    SLOT_AUDIT_VIEW_SCHEMA,
    SPOKEN_FORM_FORBIDDEN_CHARACTERS,
    SPOKEN_FORM_RULE_ID,
)

GENERATOR = "scripts/build_slurp_slot_audit_view.py"
AUTHORITY = (
    "docs/superpowers/specs/2026-09-17-node-context-policy-design.md section 16 "
    "(cell B8b); docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md "
    "section 3 item E12; docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md"
)
LEDGER_ROW = "SAEA-SLURP-E12-SLOT-AUDIT-VIEW-V1"

RELEASE_RELPATH = "knowledge/slurp/semantic/slot-audit-v1/release.json"
SNAPSHOT_RELPATH = "knowledge/slurp/semantic/slot-audit-v1/snapshot.json"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-slot-audit-v1.json"

#: The 2026-09-13 exclusion, verbatim from the exemplar-pool builder so both
#: derive the SAME construction pool from the SAME three rosters.
EXCLUDE_ROSTER_RELPATHS = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/probe-samples/DEV-1000.json",
)
EXCLUSION_AUTHORITY = (
    "docs/readiness/2026-09-13-slurp-semantic-authoring-registration-v1.json"
)
EXPECTED_UTTERANCE_COUNT = 9354

#: The released slot store v2, whose ``Admissible formats`` sentences are the
#: representation conventions this view quotes. Read at build time only.
SLOT_STORE_V2_SNAPSHOT_RELPATH = (
    "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
)
SLOT_STORE_V2_SNAPSHOT_SHA256 = (
    "a48ed83eb7878e9eaedfe4dbdf4ea747e3e582e08899ff1f0edfdfe438ae8904"
)
#: The two slot types whose cards carry a spoken-form rule, and the sentence
#: prefix that opens the card section the rule lives in.
CONVENTION_ENTITY_TYPES = ("date", "time")
ADMISSIBLE_FORMATS_HEADING = "Admissible formats:"


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _utterance_id(sample_id: str) -> str | None:
    """The canonical TRAIN utterance id a roster sample id names, or ``None``
    for an id of another split (DEV-1000's ``slurp:devel:...`` rows)."""

    parts = sample_id.split(":")
    if len(parts) < 3 or parts[0] != "slurp" or parts[1] != "train":
        return None
    return f"slurp:train:{parts[2]}"


def excluded_utterance_ids(
    repo_root: Path,
) -> tuple[frozenset[str], list[dict[str, object]]]:
    """Every TRAIN utterance the three forbidden rosters name, plus per-roster
    provenance. Recording-scoped ids collapse to their utterance prefix, so
    excluding one recording excludes every sibling of that utterance."""

    excluded: set[str] = set()
    records: list[dict[str, object]] = []
    for relpath in EXCLUDE_ROSTER_RELPATHS:
        path = Path(repo_root) / relpath
        document = json.loads(path.read_text(encoding="utf-8"))
        ids = {
            str(item["sample_id"] if "sample_id" in item else item["id"])
            for item in document["items"]
        }
        utterances = {
            utterance
            for utterance in (_utterance_id(sample_id) for sample_id in ids)
            if utterance is not None
        }
        before = len(excluded)
        excluded |= utterances
        records.append({
            "relpath": relpath,
            "file_sha256": _sha256_path(path),
            "roster_id": document.get("roster_id"),
            "split_identity_hash": document.get("split_identity_hash"),
            "sample_count": len(ids),
            "train_utterance_count": len(utterances),
            "new_exclusions": len(excluded) - before,
        })
    return frozenset(excluded), records


def refuse_evaluated_rows(
    retained_utterance_ids: frozenset[str],
    excluded: frozenset[str],
    *,
    identity_hash: str,
) -> None:
    """Refuse unless the retained pool is DISJOINT from the forbidden rosters
    AND is exactly the pool the mined profile bound itself to.

    The builder's own falsifier, and the reason the view can be called
    construction-only without taking the loader's word for it. It is a
    function rather than an inline assertion so a test can hand it a poisoned
    pool and watch it refuse.
    """

    leaked = sorted(retained_utterance_ids & excluded)
    if leaked:
        raise SystemExit(
            f"REFUSED: {len(leaked)} evaluated utterance(s) survived the "
            f"construction exclusion, first {leaked[0]}; the slot-audit view may be "
            f"authored from construction data only ({EXCLUSION_AUTHORITY})"
        )
    measured = _sha256_bytes(
        "\n".join(sorted(retained_utterance_ids)).encode("utf-8")
    )
    if measured != identity_hash:
        raise SystemExit(
            f"REFUSED: the mined profile binds identity {identity_hash}, but the "
            f"retained construction pool hashes to {measured}; the table is not "
            "bound to the pool this build proved clean"
        )


def representation_conventions(root: Path) -> list[dict[str, str]]:
    """The ``date`` and ``time`` spoken-form sentences, quoted from the
    released slot store v2 and pinned by its own sha256."""

    path = Path(root) / SLOT_STORE_V2_SNAPSHOT_RELPATH
    if not path.is_file():
        raise SystemExit(f"released slot store v2 missing: {path}")
    measured = _sha256_path(path)
    if measured != SLOT_STORE_V2_SNAPSHOT_SHA256:
        raise SystemExit(
            f"{path} hashes to {measured}, not the pinned "
            f"{SLOT_STORE_V2_SNAPSHOT_SHA256}"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    contents = {
        str(value["value_id"]): str(value["content"])
        for value in document["values"]
    }
    conventions: list[dict[str, str]] = []
    for entity_type in CONVENTION_ENTITY_TYPES:
        value_id = f"slot-contract:{entity_type}"
        content = contents.get(value_id)
        if content is None:
            raise SystemExit(f"slot store v2 carries no card {value_id!r}")
        statement = _admissible_format_sentence(content, entity_type=entity_type)
        conventions.append({
            "entity_type": entity_type,
            "rule_id": SPOKEN_FORM_RULE_ID,
            "statement": statement,
            "forbidden_characters": SPOKEN_FORM_FORBIDDEN_CHARACTERS,
        })
    return conventions


def _admissible_format_sentence(content: str, *, entity_type: str) -> str:
    """The LAST ``Admissible formats`` bullet of one slot card, verbatim.

    The card's own wording is the authority the block quotes; this function
    selects it and never rewrites it. The last bullet is the representation
    rule in both released cards (``time``: the spoken-number sentence;
    ``date``: the "do not resolve it to an ISO date" sentence).
    """

    lines = content.split("\n")
    try:
        start = lines.index(ADMISSIBLE_FORMATS_HEADING)
    except ValueError:
        raise SystemExit(
            f"slot card {entity_type!r} has no {ADMISSIBLE_FORMATS_HEADING!r} section"
        ) from None
    bullets: list[str] = []
    for line in lines[start + 1:]:
        if not line.startswith("- "):
            break
        bullets.append(line[2:].strip())
    if not bullets:
        raise SystemExit(f"slot card {entity_type!r} lists no admissible format")
    return bullets[-1]


def build_documents(repo_root: Path, root: Path) -> dict[str, object]:
    """Mine the construction pool and compose the two released documents."""

    lock = load_lock(umbrella_lock_path(repo_root))
    excluded, roster_records = excluded_utterance_ids(repo_root)
    profiles = load_slurp_intent_row_profiles(
        lock, root, excluded_train_utterance_ids=sorted(excluded)
    )
    if frozenset(profiles.excluded_train_utterance_ids) != excluded:
        raise SystemExit(
            "the loader normalised a different exclusion set than this build "
            "computed; refusing"
        )
    retained = frozenset(load_slurp_train_utterance_ids(lock, root)) - excluded
    refuse_evaluated_rows(
        retained, excluded, identity_hash=profiles.source_identity_hash
    )
    if profiles.utterance_count != EXPECTED_UTTERANCE_COUNT:
        raise SystemExit(
            f"construction pool carries {profiles.utterance_count} utterances, not "
            f"the registered {EXPECTED_UTTERANCE_COUNT} ({EXCLUSION_AUTHORITY})"
        )
    conventions = representation_conventions(root)
    intents = []
    for intent in profiles.intent_ids:
        profile = profiles.intents[intent]
        rows = profile.rows
        types = sorted(
            profile.type_rows.items(), key=lambda item: (-item[1], item[0])
        )
        intents.append({
            "intent": intent,
            "rows": rows,
            "rows_with_entity": profile.rows_with_entity,
            "types": [
                {
                    "entity_type": entity_type,
                    "rows": type_rows,
                    "row_share": round(type_rows / rows, 6) if rows else 0.0,
                }
                for entity_type, type_rows in types
            ],
        })
    snapshot = {
        "schema": SLOT_AUDIT_VIEW_SCHEMA,
        "view_id": SLOT_AUDIT_VIEW_ID,
        "builder_policy_id": SLOT_AUDIT_BUILDER_POLICY_ID,
        "source_split": profiles.source_split,
        "source_split_identity_hash": profiles.source_identity_hash,
        "construction_utterance_count": profiles.utterance_count,
        "excluded_train_utterance_count": len(excluded),
        "conventions": conventions,
        "intents": intents,
    }
    return {
        "snapshot": snapshot,
        "roster_records": roster_records,
        "excluded": excluded,
        "profiles": profiles,
    }


def _release_document(snapshot_sha256: str, snapshot: dict[str, object]) -> dict[str, object]:
    return {
        "schema": SLOT_AUDIT_RELEASE_SCHEMA,
        "view_id": SLOT_AUDIT_VIEW_ID,
        "builder_policy_id": SLOT_AUDIT_BUILDER_POLICY_ID,
        "snapshot": {"relpath": SNAPSHOT_RELPATH, "root": "repo"},
        "snapshot_sha256": snapshot_sha256,
        "source": {
            "carrier": "slurp",
            "split": snapshot["source_split"],
            "construction_utterance_count": snapshot[
                "construction_utterance_count"
            ],
            "excluded_train_utterance_count": snapshot[
                "excluded_train_utterance_count"
            ],
            "exclusion_authority": EXCLUSION_AUTHORITY,
            "forbidden_rosters": list(EXCLUDE_ROSTER_RELPATHS),
        },
        "source_split_identity_hash": snapshot["source_split_identity_hash"],
        "representation_source": {
            "relpath": SLOT_STORE_V2_SNAPSHOT_RELPATH,
            "root": "data",
            "sha256": SLOT_STORE_V2_SNAPSHOT_SHA256,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed files reproduce; write nothing",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    built = build_documents(repo_root, data_root())
    snapshot = built["snapshot"]

    snapshot_path = repo_root / SNAPSHOT_RELPATH
    release_path = repo_root / RELEASE_RELPATH
    receipt_path = repo_root / RECEIPT_RELPATH

    if args.check:
        if not snapshot_path.is_file() or not release_path.is_file():
            print("MISSING: the released slot-audit view is not committed")
            return 1
        committed = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if committed != snapshot:
            print("DIFFERS: the committed snapshot is not what this build produces")
            return 1
        snapshot_sha256 = _sha256_path(snapshot_path)
        release = json.loads(release_path.read_text(encoding="utf-8"))
        if release != _release_document(snapshot_sha256, snapshot):
            print("DIFFERS: the committed release is not what this build produces")
            return 1
        print(
            f"OK  intents={len(snapshot['intents'])}  "
            f"construction_rows={snapshot['construction_utterance_count']}  "
            f"snapshot_sha256={snapshot_sha256[:16]}..."
        )
        return 0

    snapshot_sha256 = write_json_artifact(snapshot_path, snapshot)
    release_sha256 = write_json_artifact(
        release_path, _release_document(snapshot_sha256, snapshot)
    )
    distinct_types = sorted({
        row["entity_type"]
        for intent in snapshot["intents"]
        for row in intent["types"]
    })
    receipt = {
        "schema": "saea-slot-audit-build-receipt-v1",
        "generator": GENERATOR,
        "authority": AUTHORITY,
        "builder_policy_id": SLOT_AUDIT_BUILDER_POLICY_ID,
        "view_id": SLOT_AUDIT_VIEW_ID,
        "execution_profile": "model-free-check",
        "exposure_ledger_row": LEDGER_ROW,
        "contacts": {"model": 0, "tool": 0, "scorer": 0, "encoder": 0},
        "release": {"relpath": RELEASE_RELPATH, "sha256": release_sha256},
        "snapshot": {"relpath": SNAPSHOT_RELPATH, "sha256": snapshot_sha256},
        "source_split_identity_hash": snapshot["source_split_identity_hash"],
        "totals": {
            "intents": len(snapshot["intents"]),
            "distinct_entity_types": len(distinct_types),
            "listed_type_rows": sum(
                len(intent["types"]) for intent in snapshot["intents"]
            ),
            "construction_utterances": snapshot["construction_utterance_count"],
            "conventions": len(snapshot["conventions"]),
        },
        "decontamination": {
            "verdict": "clean",
            "statement": (
                "Authored from the governed SLURP TRAIN split alone, through "
                "data.slurp.load_slurp_intent_row_profiles, whose split is a module "
                "constant with no split parameter and no caller-supplied path. Every "
                "utterance with a recording in TRAIN Fold A, TRAIN Fold B or DEV-1000 "
                "was removed before a single count was accumulated, and the retained "
                "pool was checked disjoint from that exclusion. The table carries "
                "counts and shares only: no filler, no sentence, no utterance id, no "
                "recording, and no gold of any evaluated row."
            ),
            "excluded_rosters": built["roster_records"],
            "excluded_train_utterance_count": len(built["excluded"]),
            "exclusion_authority": EXCLUSION_AUTHORITY,
        },
    }
    receipt_sha256 = write_json_artifact(receipt_path, receipt)
    print(f"wrote {SNAPSHOT_RELPATH}  sha256={snapshot_sha256[:16]}...")
    print(f"wrote {RELEASE_RELPATH}  sha256={release_sha256[:16]}...")
    print(f"wrote {RECEIPT_RELPATH}  sha256={receipt_sha256[:16]}...")
    print(f"  intents={len(snapshot['intents'])}  types={len(distinct_types)}")
    print(f"  construction utterances={snapshot['construction_utterance_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
