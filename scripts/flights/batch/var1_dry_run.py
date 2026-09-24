#!/usr/bin/env python
"""The VAR-1 four-row OFFLINE dry run: what each construction variant supplies.

Model-free by construction: zero model, tokenizer, tool, network, GPU, gate, transport,
client, attempt and serving-session contacts. Each REGISTERED VAR-1 cell is composed from
its own committed fragments over the REAL released stores and walked node by node by
``speech_aware_evidence_acquisition.analysis.native_episode_dry_run``; only the four role
answers are canned, exactly as a fake frozen core would answer.

Why it walks ALL SEVEN forms and not just the smoke's: a construction-variant family's
whole question is how much each knob actually moves the supply, and that is a number the
walk produces for free on the same four rows, with no contact. The smoke registers the
VAR1-PER-K16C5 form (the only one whose contract SHAPE changes); the other six walks are
registered evidence, not a second smoke.

Three walks per form:

1. the ACCEPT path on all four rows, with the Perception answer canned to the first
   ``max_candidates`` ids of the phase's OWN legal intent enum (label-only; no utterance,
   transcript or gold is read or printed);
2. a REVISE verdict on row 1, which revisits the Solver, Reviewer and Planner and must
   acquire nothing it already holds;
3. a DUPLICATE-candidate Perception answer on row 1 (n = max_candidates, distinct = 1 --
   the shape that aborted the CELL-1 arm after 304 metered contacts), which must walk
   instead of raising.

The exit status is structural: every row of every form walks the whole graph and delivers,
every REVISE revisit acquires nothing it already holds, and every duplicate row walks. The
per-node supplied counts and instruction characters it prints are the registered structural
rule for the smoke and the registered SUPPLY PROJECTION for the other six forms.

Usage (from a worktree, in WSL)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src SPEECHRL_DATA_DIR=... \
    python -B scripts/flights/batch/var1_dry_run.py \
      --repo-root $REPO --data-root $DATA --lock-path $LOCK [--form plan] [--json out.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

#: ``form -> (experiment fragment, generation cell id)``.
FORMS = {
    "plan": ("slurp-native-stage3-var1-plan-r01c-v1", "slurp-native-stage3-var1-plan-r01c-v1"),
    "planr": ("slurp-native-stage3-var1-planr-r01c-v1", "slurp-native-stage3-var1-planr-r01c-v1"),
    "exk10": ("slurp-native-stage3-var1-ex-k10-r01c-v1", "slurp-native-stage3-var1-ex-k10-r01c-v1"),
    "exk30": ("slurp-native-stage3-var1-ex-k30-r01c-v1", "slurp-native-stage3-var1-ex-k30-r01c-v1"),
    "exdiv": ("slurp-native-stage3-var1-ex-div-r01c-v1", "slurp-native-stage3-var1-ex-div-r01c-v1"),
    "perk16c5": ("slurp-native-stage3-var1-per-k16c5-r01c-v1",
                 "slurp-native-stage3-var1-per-k16c5-r01c-v1"),
    "smoke": ("slurp-native-stage3-var1-smoke-4-v1", "slurp-native-stage3-var1-smoke-4-v1"),
}
ROWS = 4
STORE_IDS = ("intent-boundaries", "train-exemplars", "slot-contracts")


def _answers_for(candidates, *, revise_on_first_visit=False):
    perception = json.dumps(
        {"candidates": [{"intent_id": intent, "distinction": "Dry-run canned alternative.",
                         "evidence_refs": [], "unresolved_fields": []} for intent in candidates]},
        separators=(",", ":"),
    )

    def answer(role: str, visit: int) -> str:
        if role == "perception":
            return perception
        if role == "solver":
            return "intent: %s\nentities: none" % candidates[0]
        if role == "reviewer":
            return "The draft names one legal intent and no unsupported entity."
        if role == "planner":
            return "REVISE" if (revise_on_first_visit and visit == 1) else "ACCEPT"
        raise AssertionError("unexpected role %r" % role)

    return answer


def _by_store(value_ids):
    counts = {store: 0 for store in STORE_IDS}
    for item in value_ids:
        for store in STORE_IDS:
            if item.startswith("%s::" % store):
                counts[store] += 1
                break
    return counts


def _content_chars_index(baseline, data_root):
    """``{store-prefixed value id: len(rendered content)}`` over the RELEASED
    snapshots this cell pins.

    The dry run's ``instruction_chars`` measures the rendered INSTRUCTION only,
    and a knowledge store's decision does not travel there: it reaches the node
    as typed content blocks through the acquire transition. So the quantity a
    construction-variant family actually needs -- how many characters of
    knowledge each knob puts in front of each node -- is measured here, from the
    released bytes, against the value ids the walk selected.
    """
    index = {}
    for store_id, store in baseline.get("knowledge_stores", {}).items():
        snapshot = store.get("snapshot")
        if not isinstance(snapshot, dict):
            continue
        path = Path(data_root) / snapshot["relpath"]
        if not path.is_file():
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        for value in document.get("values", []):
            content = value.get("content")
            if isinstance(content, str):
                index["%s::%s" % (store_id, value["value_id"])] = len(content)
    return index


def _chars_by_store(value_ids, index):
    chars = {store: 0 for store in STORE_IDS}
    for item in value_ids:
        for store in STORE_IDS:
            if item.startswith("%s::" % store):
                chars[store] += index.get(item, 0)
                break
    return chars


def _add(into, counts):
    for key, value in counts.items():
        into[key] = into.get(key, 0) + value
    return into


def walk_form(form, *, repo_root, data_root, lock_path, runtime_root):
    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        NATIVE_ROLE_GRAPH_ORDER, compose_dry_run, dry_run_native_episode, legal_intent_ids,
    )
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime

    experiment, cell_id = FORMS[form]
    fragment = json.loads((repo_root / "configs" / "experiment" /
                           ("%s.json" % experiment)).read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == cell_id)
    baseline = json.loads((repo_root / "configs" / "baseline" /
                           ("%s.json" % cell["baseline_fragment"])).read_text(encoding="utf-8"))
    stores = baseline["knowledge_stores"]
    knobs = {
        "exemplars_k": stores["train-exemplars"]["phase_supply"]["solver"]["k"],
        "exemplars_fuse_coverage":
            stores["train-exemplars"]["phase_supply"]["solver"]["fuse_coverage"],
        "perception_k": stores["intent-boundaries"]["phase_supply"]["perception"]["k"],
        "perception_fuse_coverage":
            stores["intent-boundaries"]["phase_supply"]["perception"]["fuse_coverage"],
        "perception_fill_max_candidates":
            baseline["phase_material"]["perception"]["fill_params"]["max_candidates"],
        "slot_contracts_max_candidates":
            stores["slot-contracts"]["candidate_supply"]["solver"]["max_candidates"],
    }

    def compose():
        runtime = build_flight_runtime(
            repo_root, data_root, model=cell["model_fragment"],
            dataset=cell["dataset_fragment"], baseline=cell["baseline_fragment"],
            experiment=experiment, run_id=cell["run_id"], attempt_id=cell["attempt_id"],
            runtime_root=runtime_root, lock_path=lock_path, campaign_active=False,
        )
        return runtime, compose_dry_run(runtime, sample_limit=ROWS)

    chars_index = _content_chars_index(baseline, data_root)
    ok = True
    runtime, _binding = compose()
    roster = [item.sample_id for item in runtime._samples][:ROWS]
    legal = legal_intent_ids(runtime)
    candidates = tuple(legal[: int(knobs["perception_fill_max_candidates"])])
    report = {
        "form": form, "cell": cell_id, "experiment": experiment,
        "baseline_fragment": cell["baseline_fragment"],
        "knobs": knobs, "roster": roster, "canned_candidates": list(candidates),
        "accept_walk": {}, "revise_walk": {}, "duplicate_walk": {},
    }

    per_node_items = {}
    per_node_chars = {}
    per_node_by_store = {}
    per_node_supply_chars = {}
    per_row_supply_chars = {}
    for sample_id in roster:
        result = dry_run_native_episode(runtime, answers=_answers_for(candidates),
                                        sample_id=sample_id, sample_limit=ROWS)
        walked = tuple(node.phase for node in result.nodes)
        if walked != NATIVE_ROLE_GRAPH_ORDER:
            ok = False
        supplied = result.supplied_counts()
        chars = {node.phase: node.instruction_chars for node in result.nodes}
        by_store = {node.phase: _by_store(node.supplied_value_ids) for node in result.nodes}
        by_store["perception"] = _add(dict(by_store.get("perception", {})),
                                      _by_store(result.bootstrap_value_ids))
        supply_chars = {
            node.phase: _chars_by_store(node.supplied_value_ids, chars_index)
            for node in result.nodes
        }
        supply_chars["perception"] = _add(
            dict(supply_chars.get("perception", {})),
            _chars_by_store(result.bootstrap_value_ids, chars_index),
        )
        report["accept_walk"][sample_id] = {
            "walked": list(walked),
            "delivered_phase": result.delivered_phase,
            "first_phase_seed_source": result.first_phase_seed_source,
            "supplied_value_counts": supplied,
            "supplied_by_store": by_store,
            "supplied_content_chars_by_store": supply_chars,
            "instruction_chars": chars,
        }
        for phase, value in supplied.items():
            per_node_items[phase] = per_node_items.get(phase, 0) + value
        for phase, value in chars.items():
            per_node_chars.setdefault(phase, []).append(value)
        for phase, counts in by_store.items():
            _add(per_node_by_store.setdefault(phase, {}), counts)
        for phase, counts in supply_chars.items():
            _add(per_node_supply_chars.setdefault(phase, {}), counts)
            per_row_supply_chars.setdefault(phase, []).append(sum(counts.values()))

    report["totals"] = {
        "items_per_node": per_node_items,
        "items_per_node_by_store": per_node_by_store,
        "supplied_content_chars_per_node_by_store": per_node_supply_chars,
        "mean_supplied_content_chars_per_node_per_row": {
            phase: round(sum(values) / len(values), 1)
            for phase, values in sorted(per_row_supply_chars.items())
        },
        "max_supplied_content_chars_per_node_per_row": {
            phase: max(values) for phase, values in sorted(per_row_supply_chars.items())
        },
        "mean_instruction_chars_per_node": {
            phase: round(sum(values) / len(values), 1)
            for phase, values in sorted(per_node_chars.items())
        },
        "max_instruction_chars_per_node": {
            phase: max(values) for phase, values in sorted(per_node_chars.items())
        },
    }

    row1 = roster[0]
    runtime, _binding = compose()
    revise = dry_run_native_episode(
        runtime, answers=_answers_for(candidates, revise_on_first_visit=True), sample_id=row1,
        sample_limit=ROWS,
        node_order=NATIVE_ROLE_GRAPH_ORDER + ("solver", "reviewer", "planner"))
    second_visit_items = sum(len(node.supplied_value_ids) for node in revise.nodes[4:])
    report["revise_walk"] = {
        "sample_id": row1,
        "walked": [[node.phase, node.visit] for node in revise.nodes],
        "supplied": {"%s#%d" % (node.phase, node.visit): len(node.supplied_value_ids)
                     for node in revise.nodes},
        "second_visit_items": second_visit_items,
    }
    if second_visit_items:
        ok = False
        report["revise_walk"]["defect"] = (
            "a second visit acquired a value the episode already held"
        )

    duplicate = tuple([candidates[0]] * len(candidates))
    runtime, _binding = compose()
    dup = dry_run_native_episode(runtime, answers=_answers_for(duplicate), sample_id=row1,
                                 sample_limit=ROWS)
    report["duplicate_walk"] = {
        "sample_id": row1, "candidates": list(duplicate),
        "walked": [node.phase for node in dup.nodes],
        "supplied": {node.phase: len(node.supplied_value_ids) for node in dup.nodes},
    }
    if tuple(node.phase for node in dup.nodes) != NATIVE_ROLE_GRAPH_ORDER:
        ok = False
    report["ok"] = ok
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--runtime-root", default=str(Path.home()))
    parser.add_argument("--form", action="append", choices=sorted(FORMS),
                        help="repeatable; default is every form")
    parser.add_argument("--json", default=None, help="write the full report here")
    args = parser.parse_args(argv)

    forms = args.form or ["plan", "planr", "exk10", "exk30", "exdiv", "perk16c5", "smoke"]
    reports = {}
    ok = True
    for form in forms:
        report = walk_form(
            form,
            repo_root=Path(args.repo_root), data_root=Path(args.data_root),
            lock_path=Path(args.lock_path), runtime_root=Path(args.runtime_root),
        )
        reports[form] = report
        ok = ok and report["ok"]
        totals = report["totals"]
        print("%-9s ok=%-5s solver_items=%3d perception_items=%3d "
              "solver_supply_chars/row(mean %8.1f max %6d) "
              "perception_supply_chars/row(mean %8.1f max %6d)" % (
                  form, report["ok"],
                  totals["items_per_node"].get("solver", 0),
                  totals["items_per_node"].get("perception", 0),
                  totals["mean_supplied_content_chars_per_node_per_row"].get("solver", 0.0),
                  totals["max_supplied_content_chars_per_node_per_row"].get("solver", 0),
                  totals["mean_supplied_content_chars_per_node_per_row"].get(
                      "perception", 0.0),
                  totals["max_supplied_content_chars_per_node_per_row"].get("perception", 0),
              ))
    document = {
        "schema": "saea-var1-dry-run-v1",
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "network": 0},
        "forms": reports,
        "ok": ok,
        "what_the_verdict_is": (
            "ok means: every row of every form walked the whole graph and delivered, every "
            "REVISE revisit acquired nothing it already held, and every duplicate-candidate "
            "row walked instead of raising. The per-node counts are the registered "
            "structural rule for the four-row smoke and the registered supply projection "
            "for the other six forms."
        ),
    }
    if args.json:
        Path(args.json).write_text(
            json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
