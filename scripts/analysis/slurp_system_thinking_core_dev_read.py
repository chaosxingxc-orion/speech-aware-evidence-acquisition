#!/usr/bin/env python3
"""slurp_system_thinking_core_dev_read.py -- the preregistered READ of the P3.1 replicate (the locked SLURP system on the Thinking core, DEV-2000-ADDED).

Package ``docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1/``. Two stages:

  smoke   the four-row Thinking-system smoke: per-NODE decode cost from the sealed trace and the wall-hour projection at the measured throughput.
          Nothing is scored; the coordinator reads it to sign off the arms.
  read    the full read over four sealed, scored arms on the SAME 1,000-row DEV-2000-ADDED roster:
            lock   the Thinking system arm (this package)             aa    its request-identical twin (this package)
            inst   the sealed Instruct NX R5 composed column          bare  the bare Instruct core (B6 direct arm); NO bare Thinking core exists here
          Paired, utterance-cluster bootstrap (10,000 draws, seed 20261011): d_system = SLU(lock) - SLU(inst) (cross-flight), o_twin = SLU(aa) -
          SLU(lock) (the in-chain A/A), orientation d_vs_bare = SLU(lock) - SLU(bare); each also for intent (scenario_action exact), per scenario
          (natural and equal-scenario weightings), the cap-hit / empty / parse-failure / forced-close table and the cost per contact PER NODE.
          Roster identity is asserted for every arm (the run manifest's split identity hash equals the DEV-2000-ADDED roster's AND the per-sample id
          set equals the roster's).

Verdict (preregistered; registry P3.1; development numbers only, never a test claim; claims_benefit is false):
  HARM           d_system <= -2.5 pp and the CI95 upper bound < -|o_twin|
  NOMINATED      the CI95 lower bound of d_system > |o_twin|, the intent guard holds (intent CI95 lower bound >= -0.65 pp) and no reasoning marker was delivered
  NOT-NOMINATED  otherwise
Reported beside the word, not part of it: the point against the 2.5 pp cross-flight bar and the decision-299 completion rate (>= 0.99).

Model-free. Every sealed byte is opened read-only. NO utterance text, transcript, gold label, model output or reasoning text is printed or persisted:
contact text is reduced to booleans and counts at read time and dropped; the governed devel loader supplies the scenario of each id IN MEMORY only.

    python -B scripts/analysis/slurp_system_thinking_core_dev_read.py --stage smoke --data-root $SPEECHRL_DATA_DIR
    python -B scripts/analysis/slurp_system_thinking_core_dev_read.py --stage read  --data-root $SPEECHRL_DATA_DIR
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Callable, Mapping, Sequence

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _path in (str(_REPO / "src"), str(_HERE), str(_REPO / "scripts" / "flights" / "direct"), str(_REPO / "scripts" / "flights" / "tfrl")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import slurp_direct_fold_b_core_read as base  # noqa: E402
import slurp_system_thinking_core_read as fold_b  # noqa: E402
import thinking_system_dev_family as fam  # noqa: E402

SCHEMA_SMOKE = "saea-slurp-system-thinking-core-dev-read-smoke-v1"
SCHEMA_READ = "saea-slurp-system-thinking-core-dev-read-v1"
VERDICT_WORDS = ("NOMINATED", "NOT-NOMINATED", "HARM")
BAR_PP = base.BAR_PP
INTENT_GUARD_PP = fold_b.INTENT_GUARD_PP
INTENT_FIELD, ReadError, CONTACTS_ZERO = base.INTENT_FIELD, base.ReadError, base.CONTACTS_ZERO
UMBRELLA_LOCK_DEFAULT = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")

wire_flags, node_contacts, node_table = fold_b.wire_flags, fold_b.node_contacts, fold_b.node_table
per_scenario_table = fold_b.per_scenario_table


def _node_table(contacts: Sequence[Mapping]) -> dict:
    return node_table(contacts, cap=fam.THINK_MAX_TOKENS, rows=fam.ROWS, slots=fam.THINK_SLOTS)


def smoke_stage(contacts: Sequence[Mapping], *, rows: int = fam.ROWS) -> dict:
    nodes = node_table(contacts, cap=fam.THINK_MAX_TOKENS, rows=rows, slots=fam.THINK_SLOTS)
    return {"schema": SCHEMA_SMOKE, "status": "DECODE-COST PER NODE (no score, no read)", "nodes": nodes,
            "projection": {"rows": rows, "per_pass_gpu_hours_by_node_sum": sum(v["slot_normalised_gpu_hours_per_pass"] for v in nodes.values()),
                           "expected_wall_hours_at_measured_rate": fam.expected_wall_hours(rows),
                           "registered_plan_gpu_hours_per_arm": fam.CELLS["lock"]["gpu_hours"], "measured_rows_per_minute": fam.MEASURED_ROWS_PER_MINUTE},
            "contacts": CONTACTS_ZERO}


def paired_contrasts(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], *, seed: int, draws: int) -> dict:
    """The Fold B contrasts (lock, aa, inst, bare), with the 266-E transfer share replaced by the share of the 268-B Fold B contrast."""

    out = fold_b.paired_contrasts(arms, ids, cluster_of, seed=seed, draws=draws)
    slu = out["slu_f1"]
    d = slu["d_system_lock_vs_inst"]["point_pp"]
    slu.pop("transfer_share_of_bare_delta", None)
    slu["replication_of_fold_b"] = {"d_system_pp": d, "fold_b_d_system_pp": fam.FOLD_B_DELTA_SLU_PP, "share": d / fam.FOLD_B_DELTA_SLU_PP}
    return out


def verdict(contrast: Mapping, marker_total: int, bar_pp: float = BAR_PP, guard_pp: float = INTENT_GUARD_PP) -> str:
    slu, intent = contrast["slu_f1"], contrast["intent"]
    d, o = slu["d_system_lock_vs_inst"], slu["o_twin_aa_vs_lock"]
    margin = abs(o["point_pp"])
    guard_ok = intent["d_system_lock_vs_inst"]["ci95_lo_pp"] >= -guard_pp
    if d["point_pp"] <= -bar_pp and d["ci95_hi_pp"] < -margin:
        return "HARM"
    if d["ci95_lo_pp"] > margin and guard_ok and marker_total == 0:
        return "NOMINATED"
    return "NOT-NOMINATED"


def read_stage(arms: Mapping[str, Mapping[str, Mapping[str, float]]], ids: Sequence[str], cluster_of: Callable[[str], str], scenario_of: Callable[[str], str],
               flags: Mapping[str, Mapping[str, Mapping]], contacts_by_arm: Mapping[str, Sequence[Mapping]], *,
               seed: int = base.DEFAULT_SEED, draws: int = base.DEFAULT_DRAWS) -> dict:
    contrast = paired_contrasts(arms, ids, cluster_of, seed=seed, draws=draws)
    delivered = {key: base.flag_counts(flags[key]) for key in sorted(flags)}
    contacts = [c for key in contacts_by_arm for c in contacts_by_arm[key]]
    markers = sum(v["reasoning_leak"] for v in delivered.values()) + sum(1 for c in contacts if c.get("marker_in_content"))
    lock_nodes = _node_table(contacts_by_arm.get("lock", []))
    completion = fold_b.p3_trigger(contrast, lock_nodes)
    return {
        "schema": SCHEMA_READ, "status": "PREREGISTERED-READ (development numbers; never a test claim; claims_benefit false)",
        "verdict": verdict(contrast, markers), "verdict_words": list(VERDICT_WORDS), "bar_pp": BAR_PP, "intent_guard_pp": INTENT_GUARD_PP,
        "interval": {"kind": "utterance-cluster bootstrap", "draws": draws, "seed": seed, "level": "CI95"},
        "contrast": contrast, "per_scenario": per_scenario_table(arms, ids, scenario_of),
        "nodes_by_arm": {key: _node_table(contacts_by_arm[key]) for key in sorted(contacts_by_arm)},
        "reported_beside_the_word": {
            "point_vs_cross_flight_bar": bool(contrast["slu_f1"]["d_system_lock_vs_inst"]["point_pp"] >= BAR_PP),
            "decision_299_conditions_on_this_roster": completion,
            "note": "reported, not part of the verdict word; the registry rule for NOMINATED is the CI95 lower bound against the twin offset and the intent guard"},
        "delivered_content": delivered, "reasoning_marker_total": markers,
        "scorer_parse_failures": {key: sum(1 for row in arms[key].values() if row.get("parsed", 1.0) == 0.0) for key in sorted(arms)},
        "comparators": {"inst": {"run_id": fam.COMPARATOR_COLUMN, "attempt_id": fam.COMPARATOR_ATTEMPT},
                        "bare": {"run_id": fam.BARE_RUN, "attempt_id": fam.BARE_ATTEMPT, "kind": fam.BARE_KIND}, "bare_thinking_core": "none on this roster"},
        "contacts": CONTACTS_ZERO,
    }


def render_markdown(result: Mapping) -> str:
    lines = [f"# P3.1 read -- verdict {result.get('verdict', 'n/a')}", ""]
    beside = result.get("reported_beside_the_word")
    if beside:
        p3 = beside["decision_299_conditions_on_this_roster"]
        yes_no = {True: "yes", False: "no"}
        conditions = ", ".join(f"{k}={yes_no[bool(v)]}" for k, v in p3["conditions"].items())
        lines += [f"Reported beside the word: point >= {BAR_PP} pp bar: {yes_no[beside['point_vs_cross_flight_bar']]}; decision-299 conditions "
                  f"{p3['met']}/3 ({conditions}); completion {p3['lock_completion_rate']:.4f} over {p3['lock_contacts']} contacts", ""]
    c = result.get("contrast")
    if c:
        s, i = c["slu_f1"], c["intent"]
        lines += ["| metric | Instruct lock (NX R5 composed) | bare Instruct core | Thinking system | twin | d_system (pp) | CI95 | twin offset (pp) | vs bare Instruct (pp) |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |"]
        for name, block in (("SLU-F1", s), ("intent", i)):
            d, o, b = block["d_system_lock_vs_inst"], block["o_twin_aa_vs_lock"], block["d_vs_bare_lock_vs_bare"]
            lines.append(f"| {name} | {block['inst_pct']:.2f} | {block['bare_pct']:.2f} | {block['lock_pct']:.2f} | {block['aa_pct']:.2f} | {d['point_pp']:+.2f} | "
                         f"[{d['ci95_lo_pp']:+.2f}, {d['ci95_hi_pp']:+.2f}] | {o['point_pp']:+.2f} | {b['point_pp']:+.2f} |")
        share = s["replication_of_fold_b"]
        lines += ["", f"Share of the 268-B Fold B contrast (+{share['fold_b_d_system_pp']:.2f} pp) this roster reproduces: {100 * share['share']:.1f} %.", ""]
    sc = result.get("per_scenario")
    if sc:
        lines += ["| scenario | n | SLU d_system (pp) | intent d_system (pp) | SLU vs bare Instruct (pp) |", "| --- | ---: | ---: | ---: | ---: |"]
        for name, e in sc["scenarios"].items():
            lines.append(f"| {name} | {e['n']} | {e['slu_d_system_pp']:+.2f} | {e['intent_d_system_pp']:+.2f} | {e['slu_d_vs_bare_pp']:+.2f} |")
        nat, eq = sc["natural_mixture"], sc["equal_scenario"]
        lines += [f"| natural mixture | | {nat['slu_d_system_pp']:+.2f} | {nat['intent_d_system_pp']:+.2f} | {nat['slu_d_vs_bare_pp']:+.2f} |",
                  f"| equal scenario | | {eq.get('slu_d_system_pp', float('nan')):+.2f} | {eq.get('intent_d_system_pp', float('nan')):+.2f} | {eq.get('slu_d_vs_bare_pp', float('nan')):+.2f} |", ""]
    for arm, nodes in sorted((result.get("nodes_by_arm") or {}).items()):
        lines += [f"Nodes of `{arm}`:", "", "| node | contacts | cap hits | length finishes | empty | no JSON | forced closes | tokens p50 / p99 | s per contact |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
        for node, t in nodes.items():
            lines.append(f"| {node} | {t['contacts']} | {t['cap_hits']} | {t['finish_reason_length']} | {t['empty_content']} | {t['no_json_object']} | "
                         f"{t['forced_closes']} | {t['completion_tokens']['p50']:.0f} / {t['completion_tokens']['p99']:.0f} | {t['seconds_per_contact']['mean']:.2f} |")
        lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- the sealed-run adapter and the CLI


def assert_split_identity(manifest: Mapping, run_id: str, expected: str) -> None:
    got = (manifest.get("plan") or {}).get("split_identity_hash")
    if got != expected:
        raise ReadError(f"{run_id}: the run manifest's split identity {got!r} is not the DEV-2000-ADDED roster's {expected!r}")


def load_scored(data_root: Path, run_id: str, attempt_id: str, *, split_identity: str | None = None) -> dict:
    """Per-row official scores (scorer ``slurp-slu-official``) and the delivered-content flags of a COMPLETED sealed run (no trace)."""

    paths = base.run_paths(data_root, run_id, attempt_id)
    for name in ("outputs", "scores", "manifest"):
        if not paths[name].exists():
            raise ReadError(f"{run_id}: missing sealed file {paths[name]}")
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    if str(manifest.get("status", "")).upper() != "COMPLETED":
        raise ReadError(f"{run_id}: run manifest status is {manifest.get('status')!r}, not COMPLETED")
    if split_identity is not None:
        # the run manifest keeps its plan beside it; older seals keep it in the generation manifest
        if "plan" not in manifest:
            generation = paths["dir"] / f"{run_id}.generation-manifest.json"
            manifest = dict(manifest, plan=json.loads(generation.read_text(encoding="utf-8")).get("plan", {})) if generation.exists() else manifest
        assert_split_identity(manifest, run_id, split_identity)
    return {"rows": base.rows_table(json.loads(paths["scores"].read_text(encoding="utf-8")), fam.SCORER), "flags": base.load_output_flags(paths["outputs"]),
            "hashes": {n: base.sha256_file(paths[n]) for n in ("outputs", "scores", "manifest")}}


def roster_ids_and_utterances(repo_root: Path) -> tuple[list[str], dict[str, str], str]:
    view = json.loads((repo_root / fam.ROSTER["arm"]).read_text(encoding="utf-8"))
    receipt = json.loads((repo_root / fam.ROSTER_RECEIPT).read_text(encoding="utf-8"))
    utterance = {str(i["sample_id"]): str(i["utterance_id"]) for i in receipt["items"]}
    ids = [str(i["sample_id"]) for i in view["items"]]
    if set(ids) != set(utterance):
        raise ReadError("the runtime view's ids are not the roster receipt's")
    return ids, utterance, str(view["split_identity_hash"])


def gold_scenarios(lock_path: Path, data_root: Path, ids: Sequence[str]) -> dict[str, str]:
    """Scenario of each roster id from the governed devel loader, IN MEMORY only (the roster withholds strata per item)."""

    spec = importlib.util.spec_from_file_location("slurp_nx_postproc_v4_search", _REPO / "scripts" / "analysis" / "slurp_nx_postproc_v4_search.py")
    drv = importlib.util.module_from_spec(spec)
    sys.modules["slurp_nx_postproc_v4_search"] = drv
    spec.loader.exec_module(drv)  # type: ignore[union-attr]
    from speech_aware_evidence_acquisition.data.lock import load_lock

    gold = drv.load_gold(load_lock(Path(lock_path)), data_root, "devel")
    missing = [i for i in ids if i not in gold]
    if missing:
        raise ReadError(f"{len(missing)} roster ids absent from the devel gold")
    return {i: str(gold[i]["scenario"]) for i in ids}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("smoke", "read"), required=True)
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "."))
    parser.add_argument("--repo-root", type=Path, default=_REPO)
    parser.add_argument("--lock", type=Path, default=UMBRELLA_LOCK_DEFAULT)
    parser.add_argument("--analysis-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=base.DEFAULT_SEED)
    parser.add_argument("--draws", type=int, default=base.DEFAULT_DRAWS)
    args = parser.parse_args(argv)
    root = args.analysis_root or (args.data_root / "analysis" / fam.READ_RUN_ID)
    root.mkdir(parents=True, exist_ok=True)
    cells = fam.CELLS
    try:
        if args.stage == "smoke":
            trace = base.run_paths(args.data_root, cells["smoke"]["run"], cells["smoke"]["attempt"])["trace"]
            if not trace.exists():
                raise ReadError(f"missing sealed trace {trace}")
            result = smoke_stage(node_contacts(trace))
            result["sealed_trace_sha256"] = base.sha256_file(trace)
            out = root / "smoke-decode-cost.json"
        else:
            ids, utterance, split_identity = roster_ids_and_utterances(args.repo_root)
            loaded = {key: load_scored(args.data_root, cells[key]["run"], cells[key]["attempt"], split_identity=split_identity) for key in fam.ARM_KEYS}
            loaded["inst"] = load_scored(args.data_root, fam.COMPARATOR_COLUMN, fam.COMPARATOR_ATTEMPT, split_identity=split_identity)
            loaded["bare"] = load_scored(args.data_root, fam.BARE_RUN, fam.BARE_ATTEMPT, split_identity=split_identity)
            for key, arm in loaded.items():
                if set(arm["rows"]) != set(ids):
                    raise ReadError(f"{key}: the per-sample id set is not the frozen DEV-2000-ADDED roster's")
            scenarios = gold_scenarios(args.lock, args.data_root, ids)
            contacts_by_arm = {}
            for key in fam.ARM_KEYS:
                trace = base.run_paths(args.data_root, cells[key]["run"], cells[key]["attempt"])["trace"]
                contacts_by_arm[key] = node_contacts(trace)
                loaded[key]["hashes"]["trace"] = base.sha256_file(trace)
            result = read_stage({k: loaded[k]["rows"] for k in loaded}, ids, utterance.__getitem__, scenarios.__getitem__, {k: loaded[k]["flags"] for k in loaded},
                                contacts_by_arm, seed=args.seed, draws=args.draws)
            result["sealed_hashes"] = {k: loaded[k]["hashes"] for k in sorted(loaded)}
            out = root / "read.json"
    except ReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    if out.exists():
        print(f"REFUSED: {out} exists (write-once)", file=sys.stderr)
        return 6
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / ("smoke-decode-cost.md" if args.stage == "smoke" else "README.md")).write_text(
        render_markdown(result) if args.stage == "read" else json.dumps(result.get("nodes"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(out), "verdict": result.get("verdict")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
