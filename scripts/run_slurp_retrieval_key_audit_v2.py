#!/usr/bin/env python3
"""CLI: MF-7b, the SLURP retrieval-key audit against the RE-LOCKED comparator.

Exposure row ``SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2``, registered before the
first read. **Zero model, GPU, tool, embedding, network and audio contacts.**
Preregistration:
``docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2-preregistration.md``.

I/O ONLY -- every measurement lives in ``analysis.slurp_retrieval_key_audit``,
the same module MF-7 used, and every vector was produced by a separately
ledgered pass. What this runner adds over ``run_slurp_retrieval_key_audit.py``
is exactly the three things the preregistration fixed in advance:

1. the per-row baseline mask is the RE-LOCKED comparator's
   (``dev-rows-projected-v2.jsonl``, built by
   ``scripts/slurp_mf7b_comparator_mask.py`` against
   ``slurp-slu-official-projected-v2`` and anchored on its published
   73.10 / 75.20 / 71.00);
2. a SECOND key space -- the 60 intent label descriptions -- measured beside
   the 11,514 TRAIN utterance texts and reported separately, never deciding;
3. the cross-modal cosine separation of matched against unmatched pairs.

The decision table is ``analysis.slurp_retrieval_key_audit.decision_v2``: a set
echoing at or above 90 % is DEGENERATE and cannot win, and the winner must
reach 2.00 pp AND carry a CI90 lower bound above zero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    slurp_retrieval_key_audit as audit,
)
from speech_aware_evidence_acquisition.analysis.slurp_mf7b_vectors import (  # noqa: E402
    LABEL_TEXT_RULE,
    label_key_texts,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-retrieval-key-audit-v2"
)
MF7 = "vectors/slurp-mf7"
MF7B = "vectors/slurp-mf7b"
KEY_NPZ_REL = "knowledge/slurp/saea-kb-distmodel-v1/size-full/vectors-content-facets.npz"
SNAPSHOT_SHA = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
BASELINE_RUN = "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1"
DRAFT_RUN = "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1"
ROW_ID = "SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2"

_QWEN = "qwen3-embedding-0.6b-q8_0"

#: ``set id -> (query relpath, TRAIN-text key relpath or None for the sealed
#: npz, label key relpath or None when that space has no key for this encoder,
#: encoder, contains_speech, fuses_state)``.
CATALOGUE: dict[str, tuple[str, str | None, str | None, str, bool, bool]] = {
    "q-draft": (
        f"{MF7}/qwen3emb-q-draft-query-vectors.jsonl", None, None, _QWEN, False, False),
    "q-gold-text": (
        f"{MF7}/qwen3emb-q-gold-text-query-vectors.jsonl", None, None, _QWEN, False, False),
}
for _stem, _encoder, _home in (
    ("glap", "glap", MF7),
    ("lco", "lco-embedding-omni-3b", MF7B),
    ("nemotron", "omni-embed-nemotron-3b", MF7B),
):
    _keys = f"{_home}/{_stem}-key-vectors.jsonl"
    _labels = None if _stem == "glap" else f"{MF7B}/{_stem}-label-key-vectors.jsonl"
    _query = f"{_home}/{_stem}-q-speech-query-vectors.jsonl"
    CATALOGUE[f"q-speech-{_stem}"] = (_query, _keys, _labels, _encoder, True, False)
    CATALOGUE[f"q-speech-{_stem}+state"] = (_query, _keys, _labels, _encoder, True, True)
    CATALOGUE[f"q-speech-{_stem}-fused"] = (
        f"{_home}/{_stem}-fused-q-speech-query-vectors.jsonl", _keys, _labels,
        _encoder, True, False)

DEFAULT_SETS = (
    "q-draft", "q-gold-text",
    "q-speech-glap", "q-speech-glap+state",
    "q-speech-lco", "q-speech-lco+state", "q-speech-lco-fused",
    "q-speech-nemotron", "q-speech-nemotron+state", "q-speech-nemotron-fused",
)


#: A key file is shared by three query sets of the same encoder, so parsing a
#: 500 MB JSONL three times is pure waste. The cache is keyed on the resolved
#: path and holds the SAME arrays the uncached path would have produced.
_VECTOR_CACHE: dict[str, tuple[tuple[str, ...], object]] = {}
_SHA_CACHE: dict[str, str] = {}


def load_vectors_cached(path: Path):
    key = str(path)
    if key not in _VECTOR_CACHE:
        _VECTOR_CACHE[key] = audit.load_vectors_jsonl(path)
    return _VECTOR_CACHE[key]


def sha256_file(path: Path) -> str:
    key = str(path)
    if key in _SHA_CACHE:
        return _SHA_CACHE[key]
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    _SHA_CACHE[key] = digest.hexdigest()
    return _SHA_CACHE[key]


def write_manifest(directory: Path) -> None:
    lines = [
        f"{sha256_file(path)} *{path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def label_key_rows(root: Path) -> tuple[audit.KeyRow, ...]:
    """The 60 label keys, as ``KeyRow`` objects with no slots.

    A label key carries an intent and nothing else, so filler recall is
    undefined on this key space and every row's gold-slot set stays empty --
    the audit reports ``null`` rather than a misleading zero.
    """

    rows = []
    for key_id, _text in label_key_texts(root):
        intent = key_id.split(":", 1)[1]
        rows.append(audit.KeyRow(facet_id=key_id, intent=intent, entities=()).validate())
    return tuple(rows)


def build_query_set(
    set_id: str, root: Path, space: str, sealed
) -> audit.QuerySet | None:
    query_rel, key_rel, label_rel, encoder, speech, state = CATALOGUE[set_id]
    query_path = root / query_rel
    if not query_path.is_file():
        return None
    query_ids, query_vectors = load_vectors_cached(query_path)
    if space == "label":
        if label_rel is None or not (root / label_rel).is_file():
            return None
        key_path = root / label_rel
        key_ids, key_vectors = load_vectors_cached(key_path)
        key_source = {"file": label_rel, "sha256": sha256_file(key_path), "sealed": False,
                      "key_space": "60 intent label descriptions",
                      "label_text_rule": LABEL_TEXT_RULE}
    elif key_rel is None:
        key_ids, key_vectors = sealed
        key_source = {"file": KEY_NPZ_REL, "sha256": sha256_file(root / KEY_NPZ_REL),
                      "sealed": True, "key_space": "TRAIN utterance texts"}
    else:
        key_path = root / key_rel
        if not key_path.is_file():
            return None
        key_ids, key_vectors = load_vectors_cached(key_path)
        key_source = {"file": key_rel, "sha256": sha256_file(key_path), "sealed": False,
                      "key_space": "TRAIN utterance texts"}
    return audit.QuerySet(
        query_set_id=set_id, query_ids=query_ids, query_vectors=query_vectors,
        key_ids=key_ids, key_vectors=key_vectors, encoder=encoder,
        contains_speech=speech, fuses_state=state,
        provenance={
            "query_vectors": {"file": query_rel, "sha256": sha256_file(query_path)},
            "key_vectors": key_source,
        },
    )


def measure_space(space: str, set_ids, root: Path, dev_rows, weights, sealed, k: int):
    key_rows = (
        label_key_rows(root)
        if space == "label"
        else audit.load_key_rows(root / MF7 / "train-facets.jsonl")
    )
    query_sets = {}
    for set_id in set_ids:
        query_set = build_query_set(set_id, root, space, sealed)
        if query_set is not None:
            query_sets[set_id] = query_set
    if not query_sets:
        return None, None, None, None
    per_set = {
        set_id: audit.run_query_set(query_set, dev_rows, key_rows, weights)
        for set_id, query_set in query_sets.items()
    }
    return per_set, query_sets, key_rows, None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--query-set", action="append", choices=sorted(CATALOGUE), default=None)
    parser.add_argument("--decision-k", type=int, default=5)
    parser.add_argument(
        "--spaces", default="text,label", help="comma-separated: text, label")
    args = parser.parse_args()
    set_ids = tuple(args.query_set) if args.query_set else DEFAULT_SETS
    spaces = [name.strip() for name in args.spaces.split(",") if name.strip()]
    k = args.decision_k

    root = Path(data_root())
    dev_rows = audit.load_dev_rows(root / MF7B / "dev-rows-projected-v2.jsonl")
    weights = audit.RankWeights.from_policy_config(REPO_ROOT / "configs/policy/kb-policy-v1.json")
    sealed = audit.load_sealed_key_npz(root / KEY_NPZ_REL)
    mask_receipt = json.loads(
        (root / MF7B / "comparator-mask.receipt.json").read_text(encoding="utf-8"))

    accounting = {
        "frozen_core_contacts": 0,
        "gpu_hours": 0.0,
        "model_contacts_by_this_script": 0,
        "producer_receipts": sorted(
            p.name for p in (root / MF7B).glob("*.receipt.json")
        ) + sorted(p.name for p in (root / MF7).glob("*.receipt.json")),
    }

    outputs: dict[str, dict] = {}
    separations: list[dict] = []
    scenario_tables: dict[str, dict] = {}
    per_set_by_space: dict[str, dict] = {}
    query_sets_by_space: dict[str, dict] = {}

    for space in spaces:
        per_set, query_sets, key_rows, _ = measure_space(
            space, set_ids, root, dev_rows, weights, sealed, k)
        if per_set is None:
            print(f"space {space}: no vectors present, skipped")
            continue
        summary = audit.build_summary(
            per_set, query_sets, weights, decision_k=k,
            baseline_run_id=BASELINE_RUN, draft_run_id=DRAFT_RUN,
            snapshot_sha256=SNAPSHOT_SHA,
            key_npz_sha256=sha256_file(root / KEY_NPZ_REL),
            accounting=accounting,
        )
        ci_low = {
            set_id: summary["absolute_ci90"][set_id]["NEW500"]["corrective_net_pp"]["ci_low"]
            for set_id in per_set
        }
        summary["decision_v1_rule"] = summary.pop("decision")
        summary["decision"] = audit.decision_v2(
            per_set, decision_k=k, ci_low_by_set=ci_low)
        summary["exposure_ledger_rows"] = [
            ROW_ID,
            "SAEA-SLURP-MF7B-LCO-EMBEDDING-V1",
            "SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1",
            "SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V1",
            "SAEA-SLURP-MF7-EMBEDDING-CPU-V1",
        ]
        summary["key_space"] = space
        summary["comparator"] = mask_receipt["comparator"] | {
            "identity_anchors": mask_receipt["identity_anchors"],
            "mask_sha256": mask_receipt["mask"]["sha256"],
            "rows": mask_receipt["mask"]["counts"],
        }
        summary["preregistration"] = (
            "docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2-preregistration.md")
        outputs[space] = summary
        per_set_by_space[space] = per_set
        query_sets_by_space[space] = query_sets
        scenario_tables[space] = audit.build_scenario_tables(per_set, decision_k=k)
        for set_id, query_set in query_sets.items():
            if not query_set.contains_speech or query_set.fuses_state:
                continue
            key_rows_for_space = (
                label_key_rows(root) if space == "label"
                else audit.load_key_rows(root / MF7 / "train-facets.jsonl"))
            block = audit.cosine_separation(query_set, dev_rows, key_rows_for_space)
            block["key_space"] = space
            separations.append(block)

        decision = summary["decision"]
        print(f"\n=== key space: {space} ===")
        print(json.dumps(decision, indent=1))
        for set_id in per_set:
            row = summary["query_sets"][set_id]["by_k"][str(k)]["NEW500"]
            echo = row["echo_rate"]
            filler = row["filler_recall_at_k"]
            print(f"{set_id:28s} NEW500 k={k} recall {row['intent_recall_at_k']:6.2f} "
                  f"vote {row['vote_accuracy_at_k']:6.2f} saves {row['saves']:3d} "
                  f"harms {row['harms']:3d} net {row['net_pp']:+6.2f}pp "
                  f"ci90 [{ci_low[set_id]:+6.2f}, "
                  f"{summary['absolute_ci90'][set_id]['NEW500']['corrective_net_pp']['ci_high']:+6.2f}] "
                  f"filler {'  n/a' if filler is None else f'{filler:6.2f}'} "
                  f"echo {'  n/a' if echo is None else f'{echo:6.2f}'}")

    if not args.write:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for space, summary in outputs.items():
        name = "summary.json" if space == "text" else f"summary-{space}-keys.json"
        write_json_artifact(OUT_DIR / name, summary)
        table_name = ("per-query-set-table.json" if space == "text"
                      else f"per-query-set-table-{space}-keys.json")
        write_json_artifact(OUT_DIR / table_name, {
            "schema": audit.AUDIT_SCHEMA, "key_space": space,
            "tables": {set_id: summary["query_sets"][set_id]["by_k"]
                       for set_id in summary["query_sets"]}})
        scen_name = ("per-scenario-table.json" if space == "text"
                     else f"per-scenario-table-{space}-keys.json")
        write_json_artifact(OUT_DIR / scen_name, scenario_tables[space])
    write_json_artifact(OUT_DIR / "cosine-separation.json", {
        "schema": audit.AUDIT_SCHEMA,
        "note": "matched = the key's TRAIN intent equals the DEV row's gold intent; "
        "reported over all 1,000 DEV rows and every key, non-gating",
        "separations": separations,
    })
    text_space = per_set_by_space.get("text") or next(iter(per_set_by_space.values()))
    text_sets = query_sets_by_space.get("text") or next(iter(query_sets_by_space.values()))
    report = audit.decontamination_report(
        dev_rows, audit.load_key_rows(root / MF7 / "train-facets.jsonl"), text_sets.values())
    report["devel_sentence_text"] = {
        "read": False,
        "purpose": "MF-7b recomputes no q-gold-text vector; V1's sealed bytes are reused",
        "written_to_any_artifact": False,
    }
    report["label_key_space"] = {
        "keys": 60,
        "source": "the closed-list inventory's own legal (scenario, action) pairs",
        "text_rule": LABEL_TEXT_RULE,
        "decides": False,
    }
    report["comparator"] = outputs[next(iter(outputs))]["comparator"]
    write_json_artifact(OUT_DIR / "decontamination.json", report)
    write_manifest(OUT_DIR)
    print(f"\nwrote {OUT_DIR}")
    _ = text_space
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
