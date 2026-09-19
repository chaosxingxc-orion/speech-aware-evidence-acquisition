#!/usr/bin/env python3
"""CLI: build the SLURP construction-data SCENARIO HINTS view (item E14, cell B8c).

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
scorer, GPU or network contacts. Every number this script reads was produced by
an earlier, already-paid pass: the governed TRAIN metadata, and the sealed
content facet vectors of ``SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1``. Nothing is
embedded here, nothing is re-encoded, and no server is contacted.

The output is the pinned table the Solver scenario-hints context block renders
(``rails.scenario_hints``), released as three files under the controlled data
root plus a build receipt in the repository:

* ``$SPEECHRL_DATA_DIR/knowledge/slurp/semantic/scenario-hints-v1/snapshot.json``
  -- per intent, its construction row count and up to three CONFUSION
  NEIGHBOURS with their k-NN leakage rate, each carrying up to three
  discriminating construction cue words.
* ``.../release.json`` -- the release identity that pins the snapshot's bytes,
  its construction source and the sealed vector file the neighbours were read
  from.
* ``.../completion.json`` -- the preparation completion record: the binding, its
  hash, the zero-contact statement and the forbidden rosters.
* ``docs/receipts/knowledge/slurp-scenario-hints-v1.json`` -- the build receipt,
  naming every input and output by sha256.

CONSTRUCTION DATA ONLY, and it refuses otherwise. Four independent guards:

1. The reader is ``data.slurp.load_slurp_construction_utterances``, whose split
   is a module constant with no ``split`` parameter and no caller-supplied path,
   so a devel or test metadata file cannot be reached through it at all.
2. Every utterance with a recording in TRAIN Fold A, TRAIN Fold B or DEV-1000
   (the 2026-09-13 exclusion, ``docs/readiness/2026-09-13-slurp-semantic-
   authoring-registration-v1.json`` ``forbidden_rosters``) is removed BEFORE a
   single neighbour is read, and :func:`refuse_evaluated_rows` re-checks
   afterwards that not one of them survived -- a disjointness proof over the
   retained identity, not a comment.
3. The retained pool must carry exactly the registered 9,354 utterances and 60
   intents, and its identity hash must equal the one the E12 slot-audit receipt
   already pins for the same exclusion. Any other value stops the build, which
   is what ties this view to the pool E12 and M1 proved clean.
4. The A3 audit's own confusion pairs are NOT read. They were computed on the
   evaluated rows' gold and stay a diagnostic ceiling; this table re-derives
   its neighbours from the construction pool alone, which is the whole point
   of design section 16's boundary.

THE DERIVATION RULE, fixed in ``rails.scenario_hints`` and mirrored into the
snapshot so a loader can refuse a table built by another rule:

* neighbours: for each construction utterance of intent ``i``, its ``k = 10``
  nearest pool neighbours by cosine over the sealed content facet vectors,
  leave-one-out; ``leaked(i, j)`` counts those neighbours whose intent is
  ``j != i``, out of ``rows(i) * k``; the top 3 ``j`` at or above a 5 % leakage
  share are kept, most leaked first and ties by intent id.
* cues: for each kept pair, the content words with the highest ``+1``-prior
  log-odds of DOCUMENT frequency in ``i`` against ``j``, stopwords removed
  (``rails.scenario_hints.STOPWORDS``), a minimum of 3 documents in ``i``, the
  top 3 kept, ties by word.

Usage::

    python scripts/build_slurp_scenario_hints_view.py
    python scripts/build_slurp_scenario_hints_view.py --check   # verify only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    load_slurp_construction_utterances,
    load_slurp_train_utterance_ids,
)
from speech_aware_evidence_acquisition.e0.artifacts import (  # noqa: E402
    write_json_artifact,
)
from speech_aware_evidence_acquisition.rails.scenario_hints import (  # noqa: E402
    CUE_LIMIT,
    CUE_MIN_ROWS,
    CUE_PRIOR,
    NEIGHBOUR_K,
    NEIGHBOUR_LIMIT,
    NEIGHBOUR_MIN_LEAKAGE_SHARE,
    SCENARIO_HINTS_BUILDER_POLICY_ID,
    SCENARIO_HINTS_COMPLETION_SCHEMA,
    SCENARIO_HINTS_RELEASE_SCHEMA,
    SCENARIO_HINTS_VIEW_ID,
    SCENARIO_HINTS_VIEW_SCHEMA,
    cue_log_odds,
    is_cue_candidate,
)

GENERATOR = "scripts/build_slurp_scenario_hints_view.py"
AUTHORITY = (
    "docs/superpowers/specs/2026-09-17-node-context-policy-design.md sections 16 "
    "and 16.2 (cell B8c); "
    "docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md"
)
LEDGER_ROW = "SAEA-SLURP-E14-SCENARIO-HINTS-VIEW-V1"

NAMESPACE = "knowledge/slurp/semantic/scenario-hints-v1"
SNAPSHOT_RELPATH = f"{NAMESPACE}/snapshot.json"
RELEASE_RELPATH = f"{NAMESPACE}/release.json"
COMPLETION_RELPATH = f"{NAMESPACE}/completion.json"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-scenario-hints-v1.json"

#: The 2026-09-13 exclusion, verbatim from the E12 slot-audit builder -- which
#: took it verbatim from the exemplar-pool builder -- so all three derive the
#: SAME construction pool from the SAME three rosters.
EXCLUDE_ROSTER_RELPATHS = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/probe-samples/DEV-1000.json",
)
EXCLUSION_AUTHORITY = (
    "docs/readiness/2026-09-13-slurp-semantic-authoring-registration-v1.json"
)
EXPECTED_UTTERANCE_COUNT = 9354
EXPECTED_INTENT_COUNT = 60

#: The E12 slot-audit build receipt. This build refuses unless its own retained
#: pool agrees with that receipt on the identity hash, the utterance count and
#: the exclusion count -- the cheapest possible proof that two independent
#: builders mined the same construction pool.
POOL_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-slot-audit-v1.json"

#: The sealed content facet vectors, and the pin every committed B1/B5e
#: baseline fragment already carries for them. Omni-Embed-Nemotron-3B over the
#: 11,514 governed TRAIN utterance texts, mean-pooled and L2-normalised, one
#: vector per content facet id ``facet:content:<slurp_id>``; produced by tool
#: contact row ``SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1``. Read here, never
#: recomputed. The model's embedding width is 2,048, which this build asserts
#: per row rather than trusting.
VECTORS_RELPATH = "vectors/slurp-kus3/facet-vectors.jsonl"
VECTORS_SHA256 = "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"
VECTORS_LEDGER_ROW = "SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1"
VECTOR_DIMENSION = 2048
VECTOR_KEY = "content"

#: Rows per similarity chunk. It bounds peak memory and NOTHING else: the
#: neighbour lists are identical at every chunk size, because each row's
#: ordering is a full stable sort of its own similarity vector.
SIMILARITY_CHUNK_ROWS = 512


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(document: object) -> str:
    return _sha256_bytes(
        json.dumps(
            document, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    )


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
    AND is exactly the pool the mined table bound itself to.

    The builder's own falsifier, and the reason this view can be called
    construction-only without taking the loader's word for it. It is a function
    rather than an inline assertion so a test can hand it a poisoned pool and
    watch it refuse.
    """

    leaked = sorted(retained_utterance_ids & excluded)
    if leaked:
        raise SystemExit(
            f"REFUSED: {len(leaked)} evaluated utterance(s) survived the construction "
            f"exclusion, first {leaked[0]}; the scenario-hints view may be authored "
            f"from construction data only ({EXCLUSION_AUTHORITY})"
        )
    measured = _sha256_bytes(
        "\n".join(sorted(retained_utterance_ids)).encode("utf-8")
    )
    if measured != identity_hash:
        raise SystemExit(
            f"REFUSED: the mined pool binds identity {identity_hash}, but the retained "
            f"construction pool hashes to {measured}; the table is not bound to the "
            "pool this build proved clean"
        )


def pool_receipt_agreement(
    repo_root: Path, *, identity_hash: str, utterance_count: int, excluded_count: int,
) -> dict[str, object]:
    """Refuse unless the E12 slot-audit receipt agrees on the same pool."""

    path = Path(repo_root) / POOL_RECEIPT_RELPATH
    if not path.is_file():
        raise SystemExit(f"E12 construction-pool receipt missing: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    recorded_identity = document.get("source_split_identity_hash")
    recorded_utterances = document.get("totals", {}).get("construction_utterances")
    recorded_excluded = document.get("decontamination", {}).get(
        "excluded_train_utterance_count"
    )
    if (
        recorded_identity != identity_hash
        or recorded_utterances != utterance_count
        or recorded_excluded != excluded_count
    ):
        raise SystemExit(
            "REFUSED: this build's construction pool disagrees with the E12 receipt "
            f"({POOL_RECEIPT_RELPATH}): identity {identity_hash} vs "
            f"{recorded_identity}, utterances {utterance_count} vs "
            f"{recorded_utterances}, exclusions {excluded_count} vs {recorded_excluded}"
        )
    return {
        "relpath": POOL_RECEIPT_RELPATH,
        "root": "repo",
        "sha256": _sha256_path(path),
        "exposure_ledger_row": document.get("exposure_ledger_row"),
    }


def load_pool_vectors(
    root: Path, utterance_ids: tuple[str, ...],
) -> tuple[np.ndarray, str]:
    """The sealed content facet vector of every pool utterance, in pool order.

    ZERO CONTACTS: the file is read and its bytes are hashed against the pin
    every committed exemplar fragment already carries. Nothing is embedded and
    no number is rewritten -- the vectors are already L2-normalised, which this
    function checks rather than imposes.
    """

    path = Path(root) / VECTORS_RELPATH
    if not path.is_file():
        raise SystemExit(f"sealed facet vectors missing: {path}")
    measured = _sha256_path(path)
    if measured != VECTORS_SHA256:
        raise SystemExit(
            f"{path} hashes to {measured}, not the pinned {VECTORS_SHA256}"
        )
    wanted = {
        f"facet:{VECTOR_KEY}:{int(utterance_id.rsplit(':', 1)[1])}": index
        for index, utterance_id in enumerate(utterance_ids)
    }
    matrix = np.zeros((len(utterance_ids), VECTOR_DIMENSION), dtype=np.float64)
    seen = np.zeros(len(utterance_ids), dtype=bool)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            head = line[:80]
            if '"id"' not in head:
                raise SystemExit("sealed facet vector line does not open with its id")
            row = json.loads(line)
            index = wanted.get(row["id"])
            if index is None:
                continue
            values = row["vectors"][VECTOR_KEY]
            if len(values) != VECTOR_DIMENSION:
                raise SystemExit(
                    f"sealed facet vector {row['id']} carries {len(values)} components"
                )
            matrix[index] = values
            seen[index] = True
    if not bool(seen.all()):
        missing = int((~seen).sum())
        raise SystemExit(
            f"REFUSED: {missing} construction utterance(s) have no sealed facet "
            f"vector in {VECTORS_RELPATH}"
        )
    norms = np.linalg.norm(matrix, axis=1)
    if not np.all(np.isfinite(norms)) or float(np.abs(norms - 1.0).max()) > 1e-3:
        raise SystemExit(
            "REFUSED: the sealed facet vectors are not L2-normalised as their "
            "fragment declares"
        )
    # Cosine similarity is normalisation-invariant; a local unit-norm copy is
    # what makes the neighbour order a pure function of the sealed numbers.
    return matrix / norms[:, None], measured


def neighbour_leakage(
    matrix: np.ndarray, intents: tuple[str, ...],
) -> dict[str, dict[str, int]]:
    """``leak[i][j]``: how many of intent ``i``'s rows' k nearest pool
    neighbours carry intent ``j != i``.

    Leave-one-out (a row is never its own neighbour) and deterministic: each
    row's ordering is a FULL stable sort of its similarity vector, so ties
    break by ascending pool index and the result does not depend on the chunk
    size.
    """

    rows = matrix.shape[0]
    if rows <= NEIGHBOUR_K:
        raise SystemExit("the construction pool is smaller than the neighbourhood")
    leak: dict[str, dict[str, int]] = {}
    for start in range(0, rows, SIMILARITY_CHUNK_ROWS):
        stop = min(start + SIMILARITY_CHUNK_ROWS, rows)
        sims = matrix[start:stop] @ matrix.T
        for offset in range(stop - start):
            index = start + offset
            row_sims = sims[offset]
            row_sims[index] = -np.inf
            order = np.argsort(-row_sims, kind="stable")[:NEIGHBOUR_K]
            own = intents[index]
            counts = leak.setdefault(own, {})
            for neighbour_index in order:
                other = intents[int(neighbour_index)]
                if other == own:
                    continue
                counts[other] = counts.get(other, 0) + 1
    return leak


def document_frequencies(
    intents: tuple[str, ...], token_rows: tuple[tuple[str, ...], ...],
) -> tuple[dict[str, dict[str, int]], dict[str, int]]:
    """Per intent, how many of its rows contain each cue-candidate word, and
    how many rows it has."""

    frequencies: dict[str, dict[str, int]] = {}
    rows_by_intent: dict[str, int] = {}
    for intent, tokens in zip(intents, token_rows, strict=True):
        rows_by_intent[intent] = rows_by_intent.get(intent, 0) + 1
        counts = frequencies.setdefault(intent, {})
        for word in {token for token in tokens if is_cue_candidate(token)}:
            counts[word] = counts.get(word, 0) + 1
    return frequencies, rows_by_intent


def pair_cues(
    intent: str,
    neighbour: str,
    frequencies: dict[str, dict[str, int]],
    rows_by_intent: dict[str, int],
) -> list[dict[str, object]]:
    """The bounded discriminating cue words of one (intent, neighbour) pair."""

    own = frequencies.get(intent, {})
    other = frequencies.get(neighbour, {})
    intent_rows = rows_by_intent[intent]
    neighbour_rows = rows_by_intent[neighbour]
    scored: list[tuple[float, str, int, int]] = []
    for word, rows in own.items():
        if rows < CUE_MIN_ROWS:
            continue
        against = other.get(word, 0)
        score = cue_log_odds(rows, intent_rows, against, neighbour_rows)
        scored.append((score, word, rows, against))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [
        {
            "word": word,
            "rows": rows,
            "neighbour_rows": against,
            "log_odds": round(score, 6),
        }
        for score, word, rows, against in scored[:CUE_LIMIT]
    ]


def build_documents(repo_root: Path, root: Path) -> dict[str, object]:
    """Mine the construction pool and compose the released snapshot."""

    started = time.monotonic()
    lock = load_lock(umbrella_lock_path(repo_root))
    excluded, roster_records = excluded_utterance_ids(repo_root)
    pool = load_slurp_construction_utterances(
        lock, root, excluded_train_utterance_ids=sorted(excluded)
    )
    if frozenset(pool.excluded_train_utterance_ids) != excluded:
        raise SystemExit(
            "the loader normalised a different exclusion set than this build "
            "computed; refusing"
        )
    retained = frozenset(load_slurp_train_utterance_ids(lock, root)) - excluded
    refuse_evaluated_rows(
        retained, excluded, identity_hash=pool.source_identity_hash
    )
    if pool.utterance_count != EXPECTED_UTTERANCE_COUNT:
        raise SystemExit(
            f"construction pool carries {pool.utterance_count} utterances, not the "
            f"registered {EXPECTED_UTTERANCE_COUNT} ({EXCLUSION_AUTHORITY})"
        )
    if len(pool.intent_ids) != EXPECTED_INTENT_COUNT:
        raise SystemExit(
            f"construction pool carries {len(pool.intent_ids)} intents, not the "
            f"registered {EXPECTED_INTENT_COUNT} legal inventory"
        )
    pool_receipt = pool_receipt_agreement(
        repo_root,
        identity_hash=pool.source_identity_hash,
        utterance_count=pool.utterance_count,
        excluded_count=len(excluded),
    )
    loaded_pool = time.monotonic()

    intents = tuple(row.intent for row in pool.utterances)
    token_rows = tuple(row.tokens for row in pool.utterances)
    matrix, vectors_sha256 = load_pool_vectors(root, pool.utterance_ids)
    loaded_vectors = time.monotonic()
    leak = neighbour_leakage(matrix, intents)
    measured_neighbours = time.monotonic()
    frequencies, rows_by_intent = document_frequencies(intents, token_rows)

    snapshot_intents: list[dict[str, object]] = []
    for intent in pool.intent_ids:
        rows = rows_by_intent[intent]
        of_neighbours = rows * NEIGHBOUR_K
        candidates = sorted(
            (
                (leaked, neighbour)
                for neighbour, leaked in leak.get(intent, {}).items()
                if leaked / of_neighbours >= NEIGHBOUR_MIN_LEAKAGE_SHARE
            ),
            key=lambda item: (-item[0], item[1]),
        )[:NEIGHBOUR_LIMIT]
        snapshot_intents.append({
            "intent": intent,
            "rows": rows,
            "neighbours": [
                {
                    "intent": neighbour,
                    "leaked": leaked,
                    "of_neighbours": of_neighbours,
                    "leakage_share": round(leaked / of_neighbours, 6),
                    "cues": pair_cues(intent, neighbour, frequencies, rows_by_intent),
                }
                for leaked, neighbour in candidates
            ],
        })
    snapshot = {
        "schema": SCENARIO_HINTS_VIEW_SCHEMA,
        "view_id": SCENARIO_HINTS_VIEW_ID,
        "builder_policy_id": SCENARIO_HINTS_BUILDER_POLICY_ID,
        "source_split": pool.source_split,
        "source_split_identity_hash": pool.source_identity_hash,
        "construction_utterance_count": pool.utterance_count,
        "excluded_train_utterance_count": len(excluded),
        "neighbour_policy": {
            "k": NEIGHBOUR_K,
            "min_leakage_share": NEIGHBOUR_MIN_LEAKAGE_SHARE,
            "max_neighbours": NEIGHBOUR_LIMIT,
            "max_cues": CUE_LIMIT,
            "cue_min_rows": CUE_MIN_ROWS,
            "cue_prior": CUE_PRIOR,
            "similarity": "cosine",
            "leave_one_out": True,
            "vector_source": {
                "relpath": VECTORS_RELPATH,
                "root": "data",
                "sha256": vectors_sha256,
                "dimension": VECTOR_DIMENSION,
                "tool_contact_ledger_row": VECTORS_LEDGER_ROW,
            },
        },
        "intents": snapshot_intents,
    }
    return {
        "snapshot": snapshot,
        "roster_records": roster_records,
        "excluded": excluded,
        "pool": pool,
        "pool_receipt": pool_receipt,
        "vectors_sha256": vectors_sha256,
        "timing_seconds": {
            "load_pool": round(loaded_pool - started, 3),
            "load_vectors": round(loaded_vectors - loaded_pool, 3),
            "measure_neighbours": round(measured_neighbours - loaded_vectors, 3),
            "compose": round(time.monotonic() - measured_neighbours, 3),
        },
    }


def release_document(
    snapshot_sha256: str, snapshot: dict[str, object], built: dict[str, object],
) -> dict[str, object]:
    return {
        "schema": SCENARIO_HINTS_RELEASE_SCHEMA,
        "view_id": SCENARIO_HINTS_VIEW_ID,
        "builder_policy_id": SCENARIO_HINTS_BUILDER_POLICY_ID,
        "snapshot": {"relpath": SNAPSHOT_RELPATH, "root": "data"},
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
        "neighbour_source": snapshot["neighbour_policy"]["vector_source"],
        "construction_pool_receipt": built["pool_receipt"],
    }


def completion_document(
    snapshot_sha256: str,
    release_sha256: str,
    snapshot: dict[str, object],
    built: dict[str, object],
) -> dict[str, object]:
    binding = {
        "builder_policy_id": SCENARIO_HINTS_BUILDER_POLICY_ID,
        "construction_pool_receipt": built["pool_receipt"],
        "forbidden_rosters": [
            {
                "relpath": record["relpath"],
                "root": "repo",
                "sha256": record["file_sha256"],
            }
            for record in built["roster_records"]
        ],
        "neighbour_policy": snapshot["neighbour_policy"],
        "output_namespace": NAMESPACE,
        "source_split_identity_hash": snapshot["source_split_identity_hash"],
        "view_id": SCENARIO_HINTS_VIEW_ID,
    }
    return {
        "schema": SCENARIO_HINTS_COMPLETION_SCHEMA,
        "binding": binding,
        "binding_sha256": _canonical_sha256(binding),
        "contacts": {"encoder": 0, "model": 0, "scorer": 0, "tool": 0},
        "construction_pool": {
            "source_split": snapshot["source_split"],
            "utterance_count": snapshot["construction_utterance_count"],
            "excluded_train_utterance_count": snapshot[
                "excluded_train_utterance_count"
            ],
            "intent_count": len(snapshot["intents"]),
        },
        "generator": GENERATOR,
        "release": {"relpath": RELEASE_RELPATH, "sha256": release_sha256},
        "snapshot": {"relpath": SNAPSHOT_RELPATH, "sha256": snapshot_sha256},
    }


def totals(snapshot: dict[str, object]) -> dict[str, int]:
    pairs = [
        neighbour
        for intent in snapshot["intents"]
        for neighbour in intent["neighbours"]
    ]
    return {
        "intents": len(snapshot["intents"]),
        "intents_with_neighbour": sum(
            1 for intent in snapshot["intents"] if intent["neighbours"]
        ),
        "neighbour_pairs": len(pairs),
        "cue_rows": sum(len(neighbour["cues"]) for neighbour in pairs),
        "distinct_cue_words": len({
            cue["word"] for neighbour in pairs for cue in neighbour["cues"]
        }),
        "construction_utterances": snapshot["construction_utterance_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the released files reproduce; write nothing",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    root = data_root()
    built = build_documents(repo_root, root)
    snapshot = built["snapshot"]

    snapshot_path = root / SNAPSHOT_RELPATH
    release_path = root / RELEASE_RELPATH
    completion_path = root / COMPLETION_RELPATH
    receipt_path = repo_root / RECEIPT_RELPATH
    counts = totals(snapshot)

    if args.check:
        for path in (snapshot_path, release_path, completion_path):
            if not path.is_file():
                print(f"MISSING: {path} is not released")
                return 1
        committed = json.loads(snapshot_path.read_text(encoding="utf-8"))
        if committed != snapshot:
            print("DIFFERS: the released snapshot is not what this build produces")
            return 1
        snapshot_sha256 = _sha256_path(snapshot_path)
        release = json.loads(release_path.read_text(encoding="utf-8"))
        if release != release_document(snapshot_sha256, snapshot, built):
            print("DIFFERS: the released release is not what this build produces")
            return 1
        release_sha256 = _sha256_path(release_path)
        completion = json.loads(completion_path.read_text(encoding="utf-8"))
        if completion != completion_document(
            snapshot_sha256, release_sha256, snapshot, built
        ):
            print("DIFFERS: the released completion is not what this build produces")
            return 1
        print(
            f"OK  intents={counts['intents']}  pairs={counts['neighbour_pairs']}  "
            f"construction_rows={counts['construction_utterances']}  "
            f"snapshot_sha256={snapshot_sha256[:16]}..."
        )
        return 0

    snapshot_sha256 = write_json_artifact(snapshot_path, snapshot)
    release_sha256 = write_json_artifact(
        release_path, release_document(snapshot_sha256, snapshot, built)
    )
    completion_sha256 = write_json_artifact(
        completion_path,
        completion_document(snapshot_sha256, release_sha256, snapshot, built),
    )
    receipt = {
        "schema": "saea-scenario-hints-build-receipt-v1",
        "generator": GENERATOR,
        "authority": AUTHORITY,
        "builder_policy_id": SCENARIO_HINTS_BUILDER_POLICY_ID,
        "view_id": SCENARIO_HINTS_VIEW_ID,
        "execution_profile": "model-free-check",
        "exposure_ledger_row": LEDGER_ROW,
        "contacts": {"model": 0, "tool": 0, "scorer": 0, "encoder": 0},
        "inputs": {
            "construction_pool_receipt": built["pool_receipt"],
            "sealed_facet_vectors": {
                "relpath": VECTORS_RELPATH,
                "root": "data",
                "sha256": built["vectors_sha256"],
                "tool_contact_ledger_row": VECTORS_LEDGER_ROW,
            },
        },
        "outputs": {
            "snapshot": {
                "relpath": SNAPSHOT_RELPATH, "root": "data",
                "sha256": snapshot_sha256,
            },
            "release": {
                "relpath": RELEASE_RELPATH, "root": "data",
                "sha256": release_sha256,
            },
            "completion": {
                "relpath": COMPLETION_RELPATH, "root": "data",
                "sha256": completion_sha256,
            },
        },
        "neighbour_policy": snapshot["neighbour_policy"],
        "source_split_identity_hash": snapshot["source_split_identity_hash"],
        "totals": counts,
        "timing_seconds": built["timing_seconds"],
        "decontamination": {
            "verdict": "clean",
            "statement": (
                "Authored from the governed SLURP TRAIN split alone, through "
                "data.slurp.load_slurp_construction_utterances, whose split is a "
                "module constant with no split parameter and no caller-supplied "
                "path. Every utterance with a recording in TRAIN Fold A, TRAIN "
                "Fold B or DEV-1000 was removed before a single neighbour was "
                "read, the retained pool was checked disjoint from that exclusion, "
                "and its identity hash was checked equal to the one the E12 "
                "slot-audit receipt pins for the same exclusion. The A3 audit's "
                "own confusion pairs were not read: they were computed on the "
                "evaluated rows' gold and remain a diagnostic ceiling. The table "
                "carries construction counts, construction leakage rates and "
                "construction cue WORDS: no utterance id, no sentence, no "
                "recording, no entity filler, and no gold of any evaluated row."
            ),
            "excluded_rosters": built["roster_records"],
            "excluded_train_utterance_count": len(built["excluded"]),
            "exclusion_authority": EXCLUSION_AUTHORITY,
        },
    }
    receipt_sha256 = write_json_artifact(receipt_path, receipt)
    print(f"wrote {SNAPSHOT_RELPATH}  sha256={snapshot_sha256}")
    print(f"wrote {RELEASE_RELPATH}  sha256={release_sha256}")
    print(f"wrote {COMPLETION_RELPATH}  sha256={completion_sha256}")
    print(f"wrote {RECEIPT_RELPATH}  sha256={receipt_sha256}")
    print(
        f"  intents={counts['intents']}  with_neighbour="
        f"{counts['intents_with_neighbour']}  pairs={counts['neighbour_pairs']}"
    )
    print(
        f"  cue_rows={counts['cue_rows']}  distinct_cue_words="
        f"{counts['distinct_cue_words']}"
    )
    print(f"  construction utterances={counts['construction_utterances']}")
    print(f"  timing_seconds={built['timing_seconds']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
