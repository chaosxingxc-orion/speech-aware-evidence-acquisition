#!/usr/bin/env python3
"""The single registered read of the SLURP slot-stage cells KC-S1a / KC-S1b.

Scoring-side only: gold opens here, once, after both seals. Zero model, GPU,
tool, embedding and network contacts.

Everything is scored through the SAME registered scorer
(``slurp-slu-official`` -- the real, unmodified official ``evaluate.py`` at
the pinned commit, plus this study's per-sample port and their identity
check), over complete 1,000-row roster files, never sharded.

Two views of each arm, and why both exist:

* **as sealed** -- the arm's own ``<run_id>.outputs.jsonl`` rows, whose
  ``text`` is ``{"entities": [...]}``. ``parse_slu_response`` accepts that
  object with scenario and action absent, and the official script computes
  ``entities``, both distance blocks and **SLU F1** from the entity lists
  alone, so this view's entity columns -- including the primary metric --
  are the sealed numbers with no projection in their path. Its
  scenario/action/intent columns are meaningless by construction and are
  never reported as a result.
* **joined** -- a MODEL-FREE projection: ``scenario`` and ``action`` copied
  from the sealed closed-list row for the same ``sample_id``, ``entities``
  taken from the arm's sealed row. This is the full official table. Source
  and projection sha256 are recorded, intent identity against the
  closed-list arm is asserted row by row, and the joined view's entity
  columns are asserted equal to the as-sealed view's -- a free consistency
  check on the join. Same device as the 2026-09-04 alignment audit.

The comparator (``SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1``) is scored here
too, from its own sealed outputs, and must reproduce its verdict's numbers
exactly; that is the read's identity anchor.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from speech_aware_evidence_acquisition.analysis.paired import paired_contrast
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.data.slurp import (
    load_slurp_intent_slot_schema,
    load_slurp_split,
    slurp_intent_from_state_content,
)
from speech_aware_evidence_acquisition.reproduction.slurp_delivery import (
    DeliveryJoinError,
    join_slurp_rosters,
)
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
    score_slurp_outputs_official,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
SEED = 20260903
N_REPLICATES = 10000
CI_LEVEL = 0.90
CLOSED_LIST_OUTPUTS = (
    "runs/SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1/attempt-20260905T060424Z-2c5596/"
    "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1.outputs.jsonl"
)
#: Per-sample metrics paired for every contrast. ``slot_f1_exact_f1`` is the
#: primary -- the exact ({type, filler}) per-sample slot F1 the closed-list
#: verdict paired, which is the official script's own plain ``entities``
#: block -- and ``slu_f1_f1`` is the per-sample form of the official SLU-F1
#: headline, whose corpus value is the aggregate anchor. The precision and
#: recall rows say WHICH side of the recall-limited slot layer moved;
#: ``scenario_action_exact`` is carried only to demonstrate that intent is
#: identical by construction (every contrast on it must be exactly zero).
PAIRED_METRICS = (
    "slot_f1_exact_f1",
    "slu_f1_f1",
    "slu_f1_word_f1",
    "slu_f1_char_f1",
    "slot_f1_exact_precision",
    "slot_f1_exact_recall",
    "scenario_action_exact",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path: Path) -> list:
    text = Path(path).read_text(encoding="utf-8")
    return [json.loads(line) for line in text.split("\n") if line.strip()]


def text_of(row) -> str:
    text = row.get("text")
    if text is None:
        text = row.get("final_response_text")
    if not isinstance(text, str):
        raise SystemExit("row %r carries no response text" % (row.get("sample_id"),))
    return text


def write_jsonl(rows, out: Path) -> Path:
    out.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return out


def project_as_sealed(rows: list, out: Path) -> Path:
    """1:1 key projection: the sealed text verbatim, under the ``text`` key
    every registered scorer reads. No text altered, no row added or dropped."""

    return write_jsonl(
        [{"sample_id": row["sample_id"], "text": text_of(row)} for row in rows], out
    )


def project_joined(arm_rows: list, closed_list_rows: list, out: Path) -> tuple[Path, dict]:
    """Write the shared pure joined projection in the historical format."""

    try:
        projected, stats = join_slurp_rosters(arm_rows, closed_list_rows)
    except DeliveryJoinError as exc:
        raise SystemExit(str(exc)) from exc
    return write_jsonl(projected, out), stats


def receipt_ids(relpath: str) -> set:
    doc = json.loads((REPO / relpath).read_text(encoding="utf-8"))
    return {item["id"] for item in doc["items"]}


def percent(count: int, total: int) -> float:
    return round(100.0 * count / total, 2) if total else 0.0


def entity_mentions(rows: list) -> dict:
    mentions = 0
    empty = 0
    types = collections.Counter()
    for row in rows:
        _scenario, _action, entities, _parsed = parse_slu_response(text_of(row))
        mentions += len(entities)
        if not entities:
            empty += 1
        for entity in entities:
            types[entity.type] += 1
    return {
        "predicted_entity_mentions": mentions,
        "rows_with_no_entity": empty,
        "rows_with_no_entity_percent": percent(empty, len(rows)),
        "top_predicted_types": types.most_common(12),
    }


def per_type_table(gold_by_id, rows_by_arm, ids) -> list:
    """Per gold entity type: gold mentions, and per arm the strict TP/FP and
    recall. Strict = exact (type, filler) match, the official ``entities``
    block's own definition, lower-cased on both sides as the official script
    lower-cases gold."""

    def parsed_entities(text: str):
        _scenario, _action, entities, _parsed = parse_slu_response(text)
        return [(entity.type, entity.filler.strip().lower()) for entity in entities]

    gold_counts = collections.Counter()
    per_arm = {name: collections.Counter() for name in rows_by_arm}
    per_arm_fp = {name: collections.Counter() for name in rows_by_arm}
    for sample_id in ids:
        gold = [
            (entity.type, entity.filler.strip().lower())
            for entity in gold_by_id[sample_id].entities
        ]
        for pair in gold:
            gold_counts[pair[0]] += 1
        for name, rows in rows_by_arm.items():
            predicted = parsed_entities(rows[sample_id])
            remaining = list(gold)
            for pair in predicted:
                if pair in remaining:
                    remaining.remove(pair)
                    per_arm[name][pair[0]] += 1
                else:
                    per_arm_fp[name][pair[0]] += 1
    table = []
    for entity_type, gold_n in gold_counts.most_common():
        row = {"entity_type": entity_type, "gold_mentions": gold_n}
        for name in rows_by_arm:
            tp = per_arm[name][entity_type]
            fp = per_arm_fp[name][entity_type]
            row["%s_tp" % name] = tp
            row["%s_fp" % name] = fp
            row["%s_recall" % name] = percent(tp, gold_n)
        table.append(row)
    return table


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--s1a-outputs", type=Path, required=True)
    parser.add_argument("--s1b-outputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    closed_list_path = Path(root) / CLOSED_LIST_OUTPUTS

    sources = {
        "CLOSED-LIST": closed_list_path,
        "KC-S1A": args.s1a_outputs,
        "KC-S1B": args.s1b_outputs,
    }
    rows = {name: read_rows(path) for name, path in sources.items()}
    for name, entries in rows.items():
        if len(entries) != 1000:
            raise SystemExit("%s carries %d rows, expected 1000" % (name, len(entries)))

    tmpdir = Path(tempfile.mkdtemp(prefix="saea-slurp-kcs1-read-", dir=str(root)))
    inputs = {}
    scored = {}
    join_stats = {}
    for name, path in sources.items():
        proj = project_as_sealed(rows[name], tmpdir / ("%s.as-sealed.jsonl" % name))
        inputs[name] = {
            "source_path": str(path),
            "source_sha256": sha256_file(path),
            "as_sealed_projection_sha256": sha256_file(proj),
            "rows": len(rows[name]),
        }
        scored[name] = score_slurp_outputs_official(proj, lock, root, split_id="devel")
    for name in ("KC-S1A", "KC-S1B"):
        proj, stats = project_joined(
            rows[name], rows["CLOSED-LIST"], tmpdir / ("%s.joined.jsonl" % name)
        )
        inputs[name]["joined_projection_sha256"] = sha256_file(proj)
        inputs[name]["joined_projection_source_manifests"] = [
            str(sources["CLOSED-LIST"]),
            str(sources[name]),
        ]
        join_stats[name] = stats
        scored["%s-JOINED" % name] = score_slurp_outputs_official(
            proj, lock, root, split_id="devel"
        )

    per_sample = {
        name: {row["sample_id"]: row for row in result["per_sample"]}
        for name, result in scored.items()
    }

    # Intent identical by construction, asserted.
    for name in ("KC-S1A-JOINED", "KC-S1B-JOINED"):
        mismatched = [
            sample_id
            for sample_id, row in per_sample[name].items()
            if row["scenario_action_exact"]
            != per_sample["CLOSED-LIST"][sample_id]["scenario_action_exact"]
        ]
        if mismatched:
            raise SystemExit(
                "%s intent differs from the closed-list arm on %d rows; the projection "
                "must copy it verbatim" % (name, len(mismatched))
            )
    # The join must not disturb the entity blocks.
    for name in ("KC-S1A", "KC-S1B"):
        a = scored[name]["aggregate"]["official"]
        b = scored["%s-JOINED" % name]["aggregate"]["official"]
        for key in ("slu_f1", "span_f1"):
            if abs(a[key] - b[key]) > 1e-9:
                raise SystemExit(
                    "%s %s differs between the as-sealed and joined views (%s vs %s); the "
                    "join altered the entity lists" % (name, key, a[key], b[key])
                )

    gold = {record.sample_id: record for record in load_slurp_split(lock, root, "devel")}
    ids_all = sorted(per_sample["CLOSED-LIST"])
    dev500 = sorted(receipt_ids("docs/receipts/probe-samples/DEV-500.json") & set(ids_all))
    new500 = sorted(
        receipt_ids("docs/receipts/probe-samples/DEV-1000-NEW500.json") & set(ids_all)
    )

    def stratum_of(sample_id: str) -> str:
        return gold[sample_id].scenario

    def contrasts(left, right, ids, metrics=PAIRED_METRICS):
        results = paired_contrast(
            per_sample[left],
            per_sample[right],
            metrics=metrics,
            sample_ids=list(ids),
            strata_of=stratum_of,
            seed=SEED,
            n_replicates=N_REPLICATES,
            ci_level=CI_LEVEL,
        )
        return {metric: contrast.as_dict() for metric, contrast in results.items()}

    def weightings(name, ids, metric="slot_f1_exact_f1"):
        by_stratum = collections.defaultdict(list)
        for sample_id in ids:
            by_stratum[stratum_of(sample_id)].append(
                float(per_sample[name][sample_id][metric])
            )
        natural = sum(sum(v) for v in by_stratum.values()) / max(1, len(ids))
        equal = sum(sum(v) / len(v) for v in by_stratum.values()) / max(1, len(by_stratum))
        return {"natural_mixture": round(100 * natural, 2), "equal_stratum": round(100 * equal, 2)}

    text_by_arm = {
        name: {row["sample_id"]: text_of(row) for row in rows[name]}
        for name in ("CLOSED-LIST", "KC-S1A", "KC-S1B")
    }

    # Which rows KC-S1b could not give a per-intent block to, recomputed here
    # from the sealed closed-list bytes rather than trusted from the
    # pre-flight receipt: a row falls back exactly when its sealed response
    # does not parse to an intent the TRAIN schema carries, which is
    # data.slurp.render_slurp_slot_schema_for_state_detail's own rule.
    schema = load_slurp_intent_slot_schema(lock, root)
    fallback_ids = [
        sample_id
        for sample_id in ids_all
        if slurp_intent_from_state_content(text_by_arm["CLOSED-LIST"][sample_id])
        not in schema.intents
    ]

    document = {
        "schema": "saea-slurp-kc-s1-slot-stage-read-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "cells": ["KC-S1a", "KC-S1b"],
        "contacts": {"model": 0, "tool": 0, "embedding": 0, "network": 0, "gpu_seconds": 0},
        "split_id": "devel",
        "allow_heldout": False,
        "bootstrap": {"seed": SEED, "n_replicates": N_REPLICATES, "ci_level": CI_LEVEL},
        "inputs": inputs,
        "join": join_stats,
        "official": {
            name: {
                "aggregate": result["aggregate"]["official"],
                "port_micro": result["aggregate"]["port_micro"],
                "identity_check": result["aggregate"]["identity_check"],
                "scorer_version": result["aggregate"]["scorer_version"],
            }
            for name, result in scored.items()
        },
        "n_predicted": {
            name: {
                "rows_in_outputs": len(rows[name.replace("-JOINED", "")]),
                "rows_scored": len(per_sample[name]),
                "skipped": len(rows[name.replace("-JOINED", "")]) - len(per_sample[name]),
                "unparsed": sum(1 for row in per_sample[name].values() if not row["parsed"]),
            }
            for name in scored
        },
        "entity_supply": {
            name: entity_mentions(rows[name]) for name in ("CLOSED-LIST", "KC-S1A", "KC-S1B")
        },
        "schema_fallback": {
            "rows": len(fallback_ids),
            "percent": percent(len(fallback_ids), len(ids_all)),
            "sample_ids": fallback_ids,
        },
        "paired_kc_s1a_over_closed_list": {
            "pooled_1000": contrasts("CLOSED-LIST", "KC-S1A-JOINED", ids_all),
            "prior_exposed_dev500": contrasts("CLOSED-LIST", "KC-S1A-JOINED", dev500),
            "unexposed_new500": contrasts("CLOSED-LIST", "KC-S1A-JOINED", new500),
        },
        "paired_kc_s1b_over_closed_list": {
            "pooled_1000": contrasts("CLOSED-LIST", "KC-S1B-JOINED", ids_all),
            "prior_exposed_dev500": contrasts("CLOSED-LIST", "KC-S1B-JOINED", dev500),
            "unexposed_new500": contrasts("CLOSED-LIST", "KC-S1B-JOINED", new500),
        },
        "paired_kc_s1b_over_kc_s1a": {
            "pooled_1000": contrasts("KC-S1A-JOINED", "KC-S1B-JOINED", ids_all),
            "unexposed_new500": contrasts("KC-S1A-JOINED", "KC-S1B-JOINED", new500),
        },
        "weightings_slot_f1": {
            name: {
                "pooled_1000": weightings(name, ids_all),
                "unexposed_new500": weightings(name, new500),
            }
            for name in ("CLOSED-LIST", "KC-S1A-JOINED", "KC-S1B-JOINED")
        },
        "per_entity_type": per_type_table(
            gold,
            {
                "closed_list": text_by_arm["CLOSED-LIST"],
                "kc_s1a": text_by_arm["KC-S1A"],
                "kc_s1b": text_by_arm["KC-S1B"],
            },
            ids_all,
        ),
        "populations": {
            "pooled": len(ids_all),
            "prior_exposed_dev500": len(dev500),
            "unexposed_new500": len(new500),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("wrote", args.out, sha256_file(args.out))

    print()
    print("arm                scenario  action   intent   SLU-F1  span-F1")
    for name in ("CLOSED-LIST", "KC-S1A-JOINED", "KC-S1B-JOINED", "KC-S1A", "KC-S1B"):
        o = scored[name]["aggregate"]["official"]
        print(
            "%-18s %8.2f %8.2f %8.2f %8.2f %8.2f"
            % (
                name,
                100 * o["scenario_accuracy"],
                100 * o["action_accuracy"],
                100 * o["intent_accuracy"],
                100 * o["slu_f1"],
                100 * o["span_f1"],
            )
        )
    print()
    for label, block in (
        ("S1a over closed-list", "paired_kc_s1a_over_closed_list"),
        ("S1b over closed-list", "paired_kc_s1b_over_closed_list"),
        ("S1b over S1a", "paired_kc_s1b_over_kc_s1a"),
    ):
        for population in ("pooled_1000", "unexposed_new500"):
            if population not in document[block]:
                continue
            c = document[block][population]["slot_f1_exact_f1"]
            b = c["bootstrap"]
            print(
                "slot-F1 %-22s %-16s n=%d  %.2f -> %.2f  delta %+.2f pp  "
                "saves %d harms %d ties %d  p=%.3g  CI90 [%+.2f, %+.2f]"
                % (
                    label,
                    population,
                    c["n"],
                    100 * c["left_mean"],
                    100 * c["right_mean"],
                    100 * c["delta"],
                    c["saves"],
                    c["harms"],
                    c["ties"],
                    c["sign_test_p"],
                    100 * b["ci_low"],
                    100 * b["ci_high"],
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
