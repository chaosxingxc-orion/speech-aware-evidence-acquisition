"""The Reviewer's credit table over sealed SLURP pools, and the offline policy grid (owner decision 165).

Owner decision 165 (2026-09-27, translated): "nodes like the Reviewer can all be optimised and improved;
do not mechanically throw them away -- use training-free RL to optimise its behaviour on its own." This
driver is the REWARD SIGNAL and the OFFLINE INNER LOOP of that optimisation. It is model-free: it reads
sealed phase artefacts, outputs and scores, loads SLURP gold OFFLINE on the scoring side only through
``data.slurp.load_slurp_split``, and scores drafts with the in-process port of the official metric
(``reproduction.slurp_scoring.score_slu``) after the runtime's own deliver projection
(``rails.slurp_projection_v3.apply_slurp_projection_v3_delivery``). Zero model, server, tokenizer, encoder,
embedder, scorer-subprocess, network and GPU contacts. Nothing under ``runs/`` is opened for writing.

What it produces (under ``$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-REVIEWER-CREDIT-TABLE-V1/``):

* ``visits.jsonl`` -- one record per Reviewer visit: pool, sample id, visit index, the pre-review draft's
  error class, the Planner route that followed, gold-free Reviewer-text flags (stance, tool narration,
  answer echo, mention of another shortlisted intent), whether the revision changed the intent / the
  entity multiset, and the offline outcome of the visit (helped / hurt / neutral on intent and on the
  row's entity errors). Ids, classes, booleans and counts only: no utterance, transcript, gold string,
  Reviewer text or delivered answer is persisted.
* ``report.json`` -- the credit table by pool group, the loop's net value per pool (as built against its
  own first draft), the gold-free trigger features' reach, and the offline policy grid (gate x scope)
  with paired cluster-bootstrap intervals and a two-fold cross-fitted selection on the SELECTION pools
  only (TRAIN R01C, outside Fold A). Fold A and DEV pools enter the descriptive credit table and the
  per-pool loop value only; no candidate policy is ever evaluated on them.
* ``tables.md`` -- the tables the note quotes.

Selection data rule (the brief): candidate Reviewer policies are selected on TRAIN rows outside Fold A
only. The R01C construction roster is disjoint from Fold A (checked here from the committed dataset
fragments, by recording AND by utterance id). Fold A gold is read for the descriptive credit table
only, never for selection.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.slurp_projection_v3 import (  # noqa: E402
    apply_slurp_projection_v3_delivery,
)
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (  # noqa: E402
    load_legal_intent_inventory,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    SlotEntity,
    _prf,
    parse_slu_response,
    score_slu,
)

READ_ID = "SAEA-SLURP-STAGE3-REVIEWER-CREDIT-TABLE-V1"
RECIPE = "slurp-stage3-reviewer-credit-table-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ANALYSIS_DIR = f"analysis/{READ_ID}"
IB_PREFIX = "intent-boundaries::intent-boundary:"
EX_PREFIX = "train-exemplars::value:"
EX_SNAPSHOTS = (
    "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json",
    "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
)
ROSTERS = {
    "r01c": "configs/dataset/slurp-speech-native-stage3-construction-r01c.json",
    "fold-a": "configs/dataset/slurp-speech-native-evo-fold-a-1080.json",
    "fold-b": "configs/dataset/slurp-speech-native-evo-fold-b-1080.json",
    "dev2000-added": "configs/dataset/slurp-speech-native-dev2000-added.json",
}
BOOT_DRAWS = 2000
BOOT_SEED = 20260927
#: The cross-fitted selection keeps a policy only if its mean SLU-F1 delta on the choosing fold is not
#: below this (the guard of owner decision 133, applied as a point constraint inside the inner loop).
SLU_GUARD_PP = -0.10

# (label, run id, use, form, roster)
# use: selection (TRAIN R01C, outside Fold A) | fold-a (descriptive only) | dev (descriptive only)
# form: which Reviewer/Planner instruction pair the pool flew
POOLS = (
    ("var1-plan", "SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1", "selection", "locked-v1", "r01c"),
    ("var1-planr", "SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1", "selection", "locked-v1", "r01c"),
    ("var1-ex-div", "SAEA-SLURP-STAGE3-VAR1-EX-DIV-R01C-V1", "selection", "locked-v1", "r01c"),
    ("var1-ex-k10", "SAEA-SLURP-STAGE3-VAR1-EX-K10-R01C-V1", "selection", "locked-v1", "r01c"),
    ("var1-ex-k30", "SAEA-SLURP-STAGE3-VAR1-EX-K30-R01C-V1", "selection", "locked-v1", "r01c"),
    ("var1-per-k16c5", "SAEA-SLURP-STAGE3-VAR1-PER-K16C5-R01C-V1", "selection", "locked-v1", "r01c"),
    ("f10-control", "SAEA-SLURP-STAGE3-F10-CONTROL-R01C-V1", "selection", "locked-v1", "r01c"),
    ("f10-empty", "SAEA-SLURP-STAGE3-F10-EMPTY-R01C-V1", "selection", "locked-v1", "r01c"),
    ("evpath-control", "SAEA-SLURP-STAGE3-EVIDENCE-PATH-CONTROL-R01C-V1", "selection", "locked-v1", "r01c"),
    ("roll-1", "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1", "selection", "locked-v1-grouped5", "r01c"),
    ("roll-aa", "SAEA-SLURP-STAGE3-ROLL-AA-V1", "selection", "locked-v1-grouped2", "r01c"),
    ("candrec", "SAEA-SLURP-NATIVE-STAGE3-CANDIDATE-RECOVERY-CONTROL-R01C-SEAL-RECOVERY1-V1", "selection",
     "contrastive-candrec", "r01c"),
    ("plan-lock", "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1", "fold-a", "locked-v1", "fold-a"),
    ("planr", "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1", "fold-a", "locked-v1", "fold-a"),
    ("agree-aa", "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1", "fold-a", "locked-v1", "fold-a"),
    ("agree-w1", "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "fold-a", "locked-v1", "fold-a"),
    ("roll-2", "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1", "fold-a", "locked-v1-grouped5", "fold-a"),
    ("r-prim", "SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-V1", "fold-a", "primitives", "fold-a"),
    ("p1", "SAEA-SLURP-NATIVE-PRUNE-REVIEWER1-V1", "fold-a", "locked-v1-review1", "fold-a"),
    ("roll-3", "SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1", "dev", "locked-v1-grouped5", "dev2000-added"),
    ("plan-dev", "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1", "dev", "locked-v1", "dev2000-added"),
    ("plan-dev-r", "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1", "dev", "locked-v1",
     "dev2000-added"),
)
PRE_CLASSES = ("UNPARSED", "CORRECT", "ENT-FP", "ENT-FN", "ENT-MIXED", "INT-SHORTLIST", "INT-OFFLIST")

_NARRATION = re.compile(r"tool[_ ]?call|tool result|\"tool\"\s*:|get_task_contract|task[-_ ]contract", re.I)
_ISSUE = re.compile(
    r"\b(incorrect|is wrong|are wrong|should be (?:changed|revised|corrected|replaced|updated)|should instead|"
    r"missing|omitted|omits|not (?:mentioned|supported|present|spoken|explicitly)|mismatch|inconsistent|"
    r"does not (?:match|capture|reflect|align|fully)|lacks|reconsider|should revise|"
    r"recommend(?:s|ed)? (?:a )?revis|decision:\s*revise|supported[- ]issue)", re.I)
_ENDORSE = re.compile(
    r"(no revision (?:is )?(?:needed|required|necessary)|should (?:be )?accept|"
    r"accept(?:ed)? the (?:proposal|draft)|decision:\s*accept|\bis correct|are correct|"
    r"correctly (?:identified|extracted|captures?)|no (?:issues?|concerns?|errors?|problems?)|"
    r"no supported issue|\baccurate(?:ly)?\b|consistent with)", re.I)


class ReadError(RuntimeError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pct(num: float, den: float) -> float:
    return round(100.0 * num / den, 2) if den else 0.0


def utterance_of(sample_id: str) -> str:
    parts = sample_id.split(":")
    return ":".join(parts[:3]) if len(parts) >= 3 else sample_id


# ---------------------------------------------------------------------------
# rosters, gold, exemplar pool


def roster_ids(relpath: str) -> set:
    document = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
    return {item["sample_id"] for item in document["items"]}


def roster_checks() -> dict:
    ids = {name: roster_ids(path) for name, path in ROSTERS.items()}
    utt = {name: {utterance_of(s) for s in v} for name, v in ids.items()}
    return {
        "sizes": {k: len(v) for k, v in ids.items()},
        "r01c_and_fold_a_recordings": len(ids["r01c"] & ids["fold-a"]),
        "r01c_and_fold_a_utterances": len(utt["r01c"] & utt["fold-a"]),
        "r01c_and_fold_b_recordings": len(ids["r01c"] & ids["fold-b"]),
        "ids": ids,
    }


def load_gold(lock, data_root: Path, splits, cache: Path | None = None) -> dict:
    """Gold by sample id, OFFLINE, on the scoring side only. ``cache`` (a local scratch pickle outside
    the repository, never committed) only saves the governed loader's flac-header re-verification on a
    re-run; it is written from, and keyed by, the same loader output."""
    import pickle

    key = ",".join(splits)
    if cache is not None and cache.is_file():
        stored = pickle.loads(cache.read_bytes())
        if stored.get("splits") == key:
            return stored["gold"]
    gold = {}
    for split in splits:
        for record in load_slurp_split(lock, data_root, split, workers=4):
            gold[record.sample_id] = {
                "intent": record.intent,
                "entities": tuple(SlotEntity(e.type, e.filler) for e in record.entities)}
    if cache is not None:
        cache.write_bytes(pickle.dumps({"splits": key, "gold": gold}))
    return gold


def load_exemplar_intents(data_root: Path) -> dict:
    """value key -> intent label, union over the two released exemplar pools (bodies stay in-process)."""
    table, hashes = {}, {}
    for relpath in EX_SNAPSHOTS:
        path = data_root / relpath
        document = json.loads(path.read_text(encoding="utf-8"))
        hashes[relpath] = digest(path)
        for value in document["values"]:
            parts = [p.strip() for p in (value.get("content") or "").split(" | ")]
            if len(parts) == 3:
                table[value["value_id"].split("value:", 1)[-1]] = parts[1]
    return {"intents": table, "sha256": hashes}


# ---------------------------------------------------------------------------
# sealed pools


def attempt_dir(data_root: Path, run_id: str) -> Path:
    hits = sorted((data_root / "runs" / run_id).glob(f"*/{run_id}.phases.json"))
    if len(hits) != 1:
        raise ReadError(f"{run_id}: expected one attempt carrying phases, found {len(hits)}")
    return hits[0].parent


def parse_answer(text: str, inventory) -> dict:
    outcome = apply_slurp_projection_v3_delivery(text or "", carrier_lock_key="slurp", inventory=inventory)
    scenario, action, entities, parsed = parse_slu_response(outcome.text)
    ok = bool(parsed) and scenario is not None and action is not None
    return {"parsed": ok, "scenario": scenario, "action": action,
            "intent": f"{scenario}_{action}" if ok else None,
            "entities": tuple(SlotEntity(e.type, e.filler) for e in entities) if ok else ()}


def slu_counts(gold_entities, pred_entities) -> tuple:
    score = score_slu(gold_scenario="s", gold_action="a", gold_entities=list(gold_entities),
                      predicted_scenario="s", predicted_action="a", predicted_entities=list(pred_entities))
    return (score.slu_f1_word_tp + score.slu_f1_char_tp, score.slu_f1_word_fp + score.slu_f1_char_fp,
            score.slu_f1_word_fn + score.slu_f1_char_fn)


def entity_key(answer: dict) -> list:
    return sorted((e.type, e.filler) for e in answer["entities"])


def outcome_of(answer: dict, gold_row: dict) -> dict:
    tp, fp, fn = slu_counts(gold_row["entities"], answer["entities"])
    return {"intent_ok": answer["intent"] == gold_row["intent"], "tp": tp, "fp": fp, "fn": fn,
            "ent_exact": fp < 1e-9 and fn < 1e-9}


def pre_class(answer: dict, out: dict, gold_row: dict, shortlist: list) -> str:
    if not answer["parsed"]:
        return "UNPARSED"
    if not out["intent_ok"]:
        return "INT-SHORTLIST" if gold_row["intent"] in shortlist else "INT-OFFLIST"
    if out["ent_exact"]:
        return "CORRECT"
    if out["fp"] > 1e-9 and out["fn"] > 1e-9:
        return "ENT-MIXED"
    return "ENT-FP" if out["fp"] > 1e-9 else "ENT-FN"


def reviewer_flags(text: str, shortlist: list, draft_intent) -> dict:
    """Gold-free, deterministic features of one Reviewer response (the text itself is never persisted)."""
    text = text or ""
    narration = bool(_NARRATION.search(text))
    stripped = text.strip()
    echo = False
    if stripped.startswith("{"):
        _s, _a, _e, parsed = parse_slu_response(stripped)
        echo = bool(parsed) and "tool" not in stripped[:40].lower()
    issue, endorse = bool(_ISSUE.search(text)), bool(_ENDORSE.search(text))
    stance = "ISSUE" if issue else ("ENDORSE" if endorse else "NONE")
    alternatives = [c for c in shortlist if c and c != draft_intent]
    mentions_alt = any(c in text for c in alternatives)
    return {"narration": narration, "echo": echo, "stance": stance, "mentions_alt": mentions_alt}


def load_pool(data_root: Path, pool: tuple, gold: dict, inventory, ex_intents: dict) -> dict:
    label, run_id, use, form, roster = pool
    directory = attempt_dir(data_root, run_id)
    phases_path = directory / f"{run_id}.phases.json"
    document = json.loads(phases_path.read_text(encoding="utf-8"))
    if document.get("schema") != "saea-flight-phase-summaries-v1" or len(document["phases"]) != 1:
        raise ReadError(f"{label}: unexpected phase artefact")
    outputs = {}
    outputs_path = directory / f"{run_id}.outputs.jsonl"
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                outputs[record["sample_id"]] = record.get("text") or ""
    scores_path = directory / f"{run_id}.scores.json"
    sealed_scores, scorer = {}, None
    if scores_path.exists():
        block = json.loads(scores_path.read_text(encoding="utf-8"))
        for key in sorted(block):
            value = block[key]
            if isinstance(value, dict) and value.get("per_sample") and key.startswith("slurp-slu-official"):
                scorer = key
                sealed_scores = {str(s["sample_id"]): s for s in value["per_sample"]}
                break
    manifest_path = directory / f"{run_id}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    rows, checks = {}, Counter()
    for result in document["phases"][0]["results"]:
        sample_id = result["sample_id"]
        g = gold.get(sample_id)
        if g is None:
            checks["gold_missing"] += 1
            continue
        states = result.get("agent_states") or []
        shortlist = []
        for state in states:
            if state.get("state_kind") == "phase:perception":
                try:
                    payload = json.loads(state.get("content") or "")
                    shortlist = [str(c.get("intent_id")) for c in payload.get("candidates") or ()]
                except (ValueError, AttributeError, TypeError):
                    shortlist = []
                break
        drafts = [s.get("content") or "" for s in states if s.get("state_kind") == "phase:solver"]
        reviews = [s.get("content") or "" for s in states if s.get("state_kind") == "phase:reviewer"]
        receipt = result.get("native_episode_receipt") or {}
        routes = [str(r.get("action")) for r in receipt.get("planner_routes") or ()]
        boundary = [v.split(IB_PREFIX, 1)[-1] for v in (result.get("initial_query_state") or {}).get(
            "retrieved_value_ids") or () if v.startswith(IB_PREFIX)]
        exemplars = []
        for wave in result.get("waves") or ():
            selected = (wave.get("fusion_decision") or {}).get("selected_value_ids") or []
            if any(v.startswith(EX_PREFIX) for v in selected):
                exemplars = [v.split(EX_PREFIX, 1)[-1] for v in selected if v.startswith(EX_PREFIX)]
                break
        votes = Counter(ex_intents["intents"][k] for k in exemplars if k in ex_intents["intents"])
        checks["exemplar_keys_unresolved"] += sum(1 for k in exemplars if k not in ex_intents["intents"])
        vote_top = votes.most_common(1)[0][0] if votes else None
        answers = [parse_answer(d, inventory) for d in drafts]
        final = parse_answer(outputs.get(sample_id, ""), inventory)
        final_out = outcome_of(final, g)
        sealed = sealed_scores.get(sample_id)
        if sealed is not None:
            checks["sealed_rows"] += 1
            checks["port_intent_agrees_with_sealed"] += int(
                final_out["intent_ok"] == bool(sealed["scenario_action_exact"]))
            s_tp = sealed["slu_f1_word_tp"] + sealed["slu_f1_char_tp"]
            s_fp = sealed["slu_f1_word_fp"] + sealed["slu_f1_char_fp"]
            s_fn = sealed["slu_f1_word_fn"] + sealed["slu_f1_char_fn"]
            checks["port_slu_counts_agree_with_sealed"] += int(
                abs(final_out["tp"] - s_tp) < 1e-9 and abs(final_out["fp"] - s_fp) < 1e-9
                and abs(final_out["fn"] - s_fn) < 1e-9)
        last = answers[-1] if answers else None
        if last is not None:
            checks["final_equals_projected_last_draft"] += int(
                last["intent"] == final["intent"] and last["entities"] == final["entities"])
        checks["rows"] += 1
        rows[sample_id] = {"shortlist": shortlist, "answers": answers, "reviews": reviews, "routes": routes,
                           "boundary": boundary, "vote_top": vote_top, "final": final,
                           "final_out": final_out}
    del document
    return {"label": label, "run_id": run_id, "use": use, "form": form, "roster": roster,
            "directory": str(directory.relative_to(data_root)),
            "phases_sha256": digest(phases_path), "outputs_sha256": digest(outputs_path),
            "scores_sha256": digest(scores_path) if scores_path.exists() else None, "scorer": scorer,
            "manifest_status": manifest.get("status"), "rows": rows, "checks": dict(sorted(checks.items()))}


# ---------------------------------------------------------------------------
# visits and the credit table


def visit_records(pool: dict, gold: dict) -> list:
    out = []
    for sample_id, row in sorted(pool["rows"].items()):
        g = gold[sample_id]
        answers, reviews, routes = row["answers"], row["reviews"], row["routes"]
        for j, review in enumerate(reviews):
            if j >= len(answers):
                break
            pre = answers[j]
            pre_out = outcome_of(pre, g)
            route = routes[j] if j < len(routes) else "NONE"
            revised = route == "REVISE" and j + 1 < len(answers)
            post = answers[j + 1] if revised else pre
            post_out = outcome_of(post, g) if revised else pre_out
            flags = reviewer_flags(review, row["shortlist"], pre["intent"])
            if pre_out["intent_ok"] != post_out["intent_ok"]:
                intent_effect = "helped" if post_out["intent_ok"] else "hurt"
            else:
                intent_effect = "neutral"
            pre_err, post_err = pre_out["fp"] + pre_out["fn"], post_out["fp"] + post_out["fn"]
            if post_err < pre_err - 1e-9:
                ent_effect = "helped"
            elif post_err > pre_err + 1e-9:
                ent_effect = "hurt"
            else:
                ent_effect = "neutral"
            out.append({
                "pool": pool["label"], "use": pool["use"], "form": pool["form"], "sample_id": sample_id,
                "visit": j, "pre_class": pre_class(pre, pre_out, g, row["shortlist"]),
                "route": route, "revised": revised,
                "stance": flags["stance"], "narration": flags["narration"], "echo": flags["echo"],
                "mentions_alt": flags["mentions_alt"],
                "intent_changed": revised and post["intent"] != pre["intent"],
                "entities_changed": revised and entity_key(post) != entity_key(pre),
                "post_intent_on_shortlist": revised and post["intent"] in row["shortlist"],
                "intent_effect": intent_effect, "entity_effect": ent_effect,
                "entity_errors_pre": round(pre_err, 4), "entity_errors_post": round(post_err, 4),
                "pre_is_perception_first": bool(row["shortlist"]) and pre["intent"] == row["shortlist"][0],
                "pre_on_shortlist": pre["intent"] in row["shortlist"],
                "pre_is_vote_top": row["vote_top"] is not None and pre["intent"] == row["vote_top"],
                "pre_boundary_pos": (row["boundary"].index(pre["intent"]) + 1)
                if pre["intent"] in row["boundary"] else None,
                "shortlist_n": len(row["shortlist"]),
            })
    return out


def credit_table(visits: list) -> dict:
    by = defaultdict(Counter)
    for v in visits:
        c = by[v["pre_class"]]
        c["visits"] += 1
        c["route_" + v["route"]] += 1
        c["stance_" + v["stance"]] += 1
        c["narration"] += int(v["narration"])
        c["echo"] += int(v["echo"])
        if v["revised"]:
            c["revised"] += 1
            c["revised_intent_changed"] += int(v["intent_changed"])
            c["revised_entities_changed"] += int(v["entities_changed"])
            c["intent_helped"] += int(v["intent_effect"] == "helped")
            c["intent_hurt"] += int(v["intent_effect"] == "hurt")
            c["entity_helped"] += int(v["entity_effect"] == "helped")
            c["entity_hurt"] += int(v["entity_effect"] == "hurt")
            c["entity_errors_delta"] += v["entity_errors_post"] - v["entity_errors_pre"]
    table = {}
    for cls in PRE_CLASSES:
        table[cls] = dict(sorted(by.get(cls, Counter()).items()))
    total = Counter()
    for c in by.values():
        total.update(c)
    table["ALL"] = dict(sorted(total.items()))
    return table


def stance_route_table(visits: list) -> dict:
    t = defaultdict(Counter)
    for v in visits:
        t[v["stance"]]["visits"] += 1
        t[v["stance"]]["route_" + v["route"]] += 1
        t[v["stance"]]["narration"] += int(v["narration"])
    return {k: dict(sorted(c.items())) for k, c in sorted(t.items())}


# ---------------------------------------------------------------------------
# policies: gate x scope over the sealed revision events (offline, exact)


def merge(pre: dict, post: dict, scope: str) -> dict:
    if scope == "full":
        return post
    if not pre["parsed"] or not post["parsed"]:
        return pre
    if scope == "intent-only":
        scenario, action, entities = post["scenario"], post["action"], pre["entities"]
    elif scope == "entities-only":
        scenario, action, entities = pre["scenario"], pre["action"], post["entities"]
    else:
        raise ReadError(scope)
    return {"parsed": True, "scenario": scenario, "action": action, "intent": f"{scenario}_{action}",
            "entities": tuple(entities)}


NONE_GATE = "none (review never changes the answer)"
GATES = {
    "all (as built)": lambda e: True,
    NONE_GATE: lambda e: False,
    "revision changes the intent": lambda e: e["intent_changed"],
    "revision keeps the intent": lambda e: not e["intent_changed"],
    "revised intent on Perception's shortlist": lambda e: e["post_on_shortlist"],
    "intent change to a shortlisted candidate": lambda e: e["intent_changed"] and e["post_on_shortlist"],
    "intent change to the exemplar-vote top": lambda e: e["intent_changed"] and e["post_is_vote_top"],
    "draft was not Perception's first": lambda e: not e["pre_is_perception_first"],
    "draft was not the exemplar-vote top": lambda e: not e["pre_is_vote_top"],
    "draft off the shortlist or not vote top": lambda e: (not e["pre_on_shortlist"]) or not e["pre_is_vote_top"],
    "Reviewer text raises an issue": lambda e: e["stance"] == "ISSUE",
    "Reviewer names another shortlisted intent": lambda e: e["mentions_alt"],
    "Reviewer does not narrate a tool": lambda e: not e["narration"],
}
SCOPES = ("full", "intent-only", "entities-only")


def revision_events(pool: dict) -> dict:
    events = {}
    for sample_id, row in pool["rows"].items():
        answers, routes = row["answers"], row["routes"]
        if len(answers) >= 2 and routes and routes[0] == "REVISE":
            pre, post = answers[0], answers[1]
            review = row["reviews"][0] if row["reviews"] else ""
            flags = reviewer_flags(review, row["shortlist"], pre["intent"])
            events[sample_id] = {
                "pre": pre, "post": post, "intent_changed": post["intent"] != pre["intent"],
                "post_on_shortlist": post["intent"] in row["shortlist"],
                "post_is_vote_top": row["vote_top"] is not None and post["intent"] == row["vote_top"],
                "pre_is_perception_first": bool(row["shortlist"]) and pre["intent"] == row["shortlist"][0],
                "pre_on_shortlist": pre["intent"] in row["shortlist"],
                "pre_is_vote_top": row["vote_top"] is not None and pre["intent"] == row["vote_top"],
                "stance": flags["stance"], "mentions_alt": flags["mentions_alt"], "narration": flags["narration"]}
    return events


def policy_answers(pool: dict, events: dict, gate, scope: str) -> dict:
    """The answer per row under one gate x scope. A row with no revision event delivers its only draft
    (the sealed final up to the deliver projection, which every answer here receives identically); a row
    with a second REVISE route after its one revision delivers the revised draft as built, and the
    policy treats that revision exactly like any other."""
    answers = {}
    for sample_id, row in pool["rows"].items():
        event = events.get(sample_id)
        if event is not None and gate(event):
            answers[sample_id] = merge(event["pre"], event["post"], scope)
        elif event is not None:
            answers[sample_id] = event["pre"]
        else:
            answers[sample_id] = row["answers"][0] if row["answers"] else row["final"]
    return answers


def per_row_scores(answers: dict, gold: dict) -> dict:
    return {s: outcome_of(a, gold[s]) for s, a in answers.items()}


def aggregate(scores: dict, ids) -> tuple:
    n = len(ids)
    intent = sum(scores[s]["intent_ok"] for s in ids)
    tp = sum(scores[s]["tp"] for s in ids)
    fp = sum(scores[s]["fp"] for s in ids)
    fn = sum(scores[s]["fn"] for s in ids)
    return (100.0 * intent / n if n else 0.0), 100.0 * _prf(tp, fp, fn)[2]


def paired_delta(a: dict, b: dict, ids: list, rng: random.Random, draws: int = BOOT_DRAWS) -> dict:
    """b minus a, with a whole-utterance cluster bootstrap CI95 (the instrument's own resampling unit)."""
    ia, sa = aggregate(a, ids)
    ib, sb = aggregate(b, ids)
    clusters = defaultdict(list)
    for s in ids:
        clusters[utterance_of(s)].append(s)
    keys = sorted(clusters)
    di, ds = [], []
    for _ in range(draws):
        pick = [s for k in (rng.choice(keys) for _ in keys) for s in clusters[k]]
        xa = aggregate(a, pick)
        xb = aggregate(b, pick)
        di.append(xb[0] - xa[0])
        ds.append(xb[1] - xa[1])
    di.sort()
    ds.sort()
    lo, hi = int(0.025 * draws), int(0.975 * draws) - 1
    return {"intent_pp": round(ib - ia, 3), "intent_ci95": [round(di[lo], 3), round(di[hi], 3)],
            "slu_pp": round(sb - sa, 3), "slu_ci95": [round(ds[lo], 3), round(ds[hi], 3)]}


def fold_of(sample_id: str) -> int:
    return int(hashlib.sha256(utterance_of(sample_id).encode()).hexdigest(), 16) % 2


def evaluate_grid(pools: list, gold: dict) -> dict:
    """Every gate x scope over each selection pool, against the pool AS BUILT and against its own first
    draft (review off), plus a two-fold (by utterance) cross-fitted choice per Reviewer-form group."""
    results, group_of = {}, {}
    for pool in pools:
        events = revision_events(pool)
        ids = sorted(pool["rows"])
        built = {s: pool["rows"][s]["final_out"] for s in ids}
        first = per_row_scores(policy_answers(pool, events, GATES[NONE_GATE], "full"), gold)
        entry = {"rows": len(ids), "revision_events": len(events), "policies": {}}
        for gname, gate in GATES.items():
            for scope in SCOPES:
                if gname == NONE_GATE and scope != "full":
                    continue
                scores = per_row_scores(policy_answers(pool, events, gate, scope), gold)
                cell = {"honoured": sum(1 for e in events.values() if gate(e))}
                for f in (0, 1):
                    fids = [s for s in ids if fold_of(s) == f]
                    bi, bs = aggregate(built, fids)
                    pi, ps = aggregate(scores, fids)
                    cell[f"fold{f}"] = {"intent_pp": pi - bi, "slu_pp": ps - bs, "n": len(fids)}
                bi, bs = aggregate(built, ids)
                pi, ps = aggregate(scores, ids)
                fi, fsl = aggregate(first, ids)
                cell["vs_as_built"] = {"intent_pp": round(pi - bi, 3), "slu_pp": round(ps - bs, 3)}
                cell["vs_first_draft"] = {"intent_pp": round(pi - fi, 3), "slu_pp": round(ps - fsl, 3)}
                cell["_scores"] = scores
                entry["policies"][f"{gname} | {scope}"] = cell
        results[pool["label"]] = entry
        group_of[pool["label"]] = "contrastive-candrec" if pool["form"] == "contrastive-candrec" else "locked-v1"
    crossfit = {}
    for group in sorted(set(group_of.values())):
        labels = [lb for lb, g in group_of.items() if g == group]
        keys = list(results[labels[0]]["policies"])

        def score_on(key, fold, labels=labels):
            vals = [results[lb]["policies"][key][f"fold{fold}"] for lb in labels]
            return (sum(v["intent_pp"] for v in vals) / len(vals), sum(v["slu_pp"] for v in vals) / len(vals))

        chosen = {}
        for f in (0, 1):
            def rank(k, f=f):
                mi, ms = score_on(k, f)
                return (mi if ms >= SLU_GUARD_PP else -99.0, ms)
            best = max(keys, key=rank)
            chosen[str(f)] = {"selected_on_fold": f, "policy": best,
                              "train_fold_value": [round(x, 3) for x in score_on(best, f)],
                              "held_out_fold_value": [round(x, 3) for x in score_on(best, 1 - f)]}
        in_sample = {}
        for key in keys:
            vals = [results[lb]["policies"][key]["vs_as_built"] for lb in labels]
            firsts = [results[lb]["policies"][key]["vs_first_draft"] for lb in labels]
            in_sample[key] = {"mean_intent_pp": round(sum(v["intent_pp"] for v in vals) / len(vals), 3),
                              "mean_slu_pp": round(sum(v["slu_pp"] for v in vals) / len(vals), 3),
                              "mean_intent_pp_vs_first_draft": round(
                                  sum(v["intent_pp"] for v in firsts) / len(firsts), 3),
                              "mean_slu_pp_vs_first_draft": round(sum(v["slu_pp"] for v in firsts) / len(firsts), 3),
                              "pools_intent_negative": sum(v["intent_pp"] < 0 for v in vals),
                              "mean_honoured": round(sum(results[lb]["policies"][key]["honoured"]
                                                         for lb in labels) / len(labels), 1),
                              "pools": len(vals)}
        crossfit[group] = {"pools": labels, "folds": chosen, "in_sample_mean_vs_as_built": in_sample}
    return {"per_pool": results, "crossfit": crossfit}


def trigger_reach(visits: list) -> dict:
    """Gold-free first-visit features: how many rows each fires on, and what it catches."""
    feats = {
        "draft not Perception's first": lambda v: not v["pre_is_perception_first"],
        "draft off the shortlist": lambda v: not v["pre_on_shortlist"],
        "draft not the exemplar-vote top": lambda v: not v["pre_is_vote_top"],
        "draft not at boundary position 1": lambda v: v["pre_boundary_pos"] != 1,
        "shortlist of 3 or more": lambda v: v["shortlist_n"] >= 3,
        "not vote top OR not Perception's first": lambda v: (not v["pre_is_vote_top"])
        or not v["pre_is_perception_first"],
        "not vote top AND not boundary position 1": lambda v: (not v["pre_is_vote_top"])
        and v["pre_boundary_pos"] != 1,
        "Reviewer text raises an issue": lambda v: v["stance"] == "ISSUE",
        "Planner routed REVISE": lambda v: v["route"] == "REVISE",
    }
    first = [v for v in visits if v["visit"] == 0]
    wrong_classes = ("INT-SHORTLIST", "INT-OFFLIST")
    sl = [v for v in first if v["pre_class"] == "INT-SHORTLIST"]
    out = {"first_visits": len(first), "intent_wrong": sum(1 for v in first if v["pre_class"] in wrong_classes),
           "int_shortlist": len(sl), "features": {}}
    for name, f in feats.items():
        fire = [v for v in first if f(v)]
        wrong = sum(1 for v in fire if v["pre_class"] in wrong_classes)
        caught = sum(1 for v in fire if v["pre_class"] == "INT-SHORTLIST")
        out["features"][name] = {
            "fires": len(fire), "fire_rate_pct": pct(len(fire), len(first)),
            "intent_wrong_caught": wrong, "precision_intent_wrong_pct": pct(wrong, len(fire)),
            "int_shortlist_caught": caught, "recall_int_shortlist_pct": pct(caught, len(sl)),
            "correct_rows_fired": sum(1 for v in fire if v["pre_class"] == "CORRECT")}
    return out


def form_selection(visits: list, rows_per_pool: dict) -> dict:
    """The Reviewer-FORM selection statistic over the SELECTION pools only: per row, the contrastive
    form's intent loop value (sum over that row's Reviewer visits of +1 helped / -1 hurt) minus the mean
    of the locked form's loop value over the locked pools that carry the row, paired on the same R01C
    rows, with a whole-utterance cluster bootstrap CI95. A row with no revision contributes zero."""
    per = defaultdict(lambda: defaultdict(float))
    for v in visits:
        if v["use"] != "selection":
            continue
        per[v["pool"]][v["sample_id"]] += {"helped": 1.0, "hurt": -1.0, "neutral": 0.0}[v["intent_effect"]]
    contrastive = [p for p, f in rows_per_pool.items() if f["form"] == "contrastive-candrec"]
    locked = [p for p, f in rows_per_pool.items() if f["form"].startswith("locked-v1")]
    if len(contrastive) != 1 or not locked:
        return {}
    cand = contrastive[0]
    ids = sorted(rows_per_pool[cand]["ids"])

    def locked_mean(sample_id: str) -> float:
        vals = [per[p].get(sample_id, 0.0) for p in locked if sample_id in rows_per_pool[p]["ids"]]
        return sum(vals) / len(vals) if vals else 0.0

    diff = {s: per[cand].get(s, 0.0) - locked_mean(s) for s in ids}
    clusters = defaultdict(list)
    for s in ids:
        clusters[utterance_of(s)].append(s)
    keys = sorted(clusters)
    rng = random.Random(BOOT_SEED)
    draws = []
    for _ in range(BOOT_DRAWS):
        pick = [s for k in (rng.choice(keys) for _ in keys) for s in clusters[k]]
        draws.append(100.0 * sum(diff[s] for s in pick) / len(pick))
    draws.sort()
    lo, hi = int(0.025 * BOOT_DRAWS), int(0.975 * BOOT_DRAWS) - 1
    locked_values = [100.0 * sum(per[p].values()) / len(rows_per_pool[p]["ids"]) for p in locked]
    return {
        "contrastive_pool": cand, "locked_pools": locked, "rows": len(ids),
        "contrastive_loop_intent_pp": round(100.0 * sum(per[cand].values()) / len(ids), 3),
        "locked_loop_intent_pp_mean": round(sum(locked_values) / len(locked_values), 3),
        "paired_difference_intent_pp": round(100.0 * sum(diff.values()) / len(ids), 3),
        "paired_difference_ci95": [round(draws[lo], 3), round(draws[hi], 3)],
        "unit": "whole-utterance cluster bootstrap", "draws": BOOT_DRAWS, "seed": BOOT_SEED,
    }


# ---------------------------------------------------------------------------
# rendering


def md_table(header: list, rows: list) -> str:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def render(report: dict) -> str:
    out = [f"# {READ_ID} tables", ""]
    out.append("## Pools")
    out.append(md_table(
        ["pool", "use", "form", "rows", "reviewer visits", "REVISE routes", "port intent agrees",
         "port SLU counts agree", "final = projected last draft"],
        [[p["label"], p["use"], p["form"], p["checks"].get("rows"), p["visits"], p["revise_routes"],
          p["checks"].get("port_intent_agrees_with_sealed"), p["checks"].get("port_slu_counts_agree_with_sealed"),
          p["checks"].get("final_equals_projected_last_draft")] for p in report["pools"]]))
    for group, table in report["credit"].items():
        out += ["", f"## Credit table: {group}"]
        rows = []
        for cls, c in table.items():
            rows.append([cls, c.get("visits", 0), c.get("route_REVISE", 0),
                         pct(c.get("route_REVISE", 0), c.get("visits", 0)), c.get("stance_ISSUE", 0),
                         c.get("narration", 0), c.get("revised", 0), c.get("revised_intent_changed", 0),
                         c.get("revised_entities_changed", 0), c.get("intent_helped", 0), c.get("intent_hurt", 0),
                         c.get("entity_helped", 0), c.get("entity_hurt", 0),
                         round(c.get("entity_errors_delta", 0.0), 2)])
        out.append(md_table(
            ["pre-review class", "visits", "REVISE", "REVISE %", "text raises issue", "narrates a tool", "revised",
             "intent changed", "entities changed", "intent helped", "intent hurt", "entity helped", "entity hurt",
             "entity-error delta"], rows))
    for group, st in report["stance_route"].items():
        out += ["", f"## Reviewer-text stance vs Planner route: {group}"]
        out.append(md_table(["stance", "visits", "ACCEPT", "REVISE", "narrates a tool"],
                            [[k, c.get("visits", 0), c.get("route_ACCEPT", 0), c.get("route_REVISE", 0),
                              c.get("narration", 0)] for k, c in st.items()]))
    out += ["", "## Loop value per pool (as built minus its own first draft, paired, cluster CI95)"]
    out.append(md_table(
        ["pool", "use", "rows", "revision events", "intent pp", "CI95", "SLU-F1 pp", "CI95"],
        [[lb, v["use"], v["rows"], v["revision_events"], v["as_built_vs_first_draft"]["intent_pp"],
          v["as_built_vs_first_draft"]["intent_ci95"], v["as_built_vs_first_draft"]["slu_pp"],
          v["as_built_vs_first_draft"]["slu_ci95"]] for lb, v in report["loop_value"].items()]))
    for group, t in report["triggers"].items():
        out += ["", f"## Gold-free trigger reach: {group} (first Reviewer visit)"]
        out.append(f"first visits {t['first_visits']}, intent wrong {t['intent_wrong']}, of which gold on the "
                   f"shortlist {t['int_shortlist']}")
        out.append("")
        out.append(md_table(
            ["feature", "fires", "fire %", "intent-wrong caught", "precision %", "INT-SHORTLIST caught", "recall %",
             "CORRECT rows fired"],
            [[k, v["fires"], v["fire_rate_pct"], v["intent_wrong_caught"], v["precision_intent_wrong_pct"],
              v["int_shortlist_caught"], v["recall_int_shortlist_pct"], v["correct_rows_fired"]]
             for k, v in t["features"].items()]))
    for group, cf in report["grid"]["crossfit"].items():
        out += ["", f"## Policy grid, {group}: mean over pools {', '.join(cf['pools'])}"]
        rows = sorted(cf["in_sample_mean_vs_as_built"].items(), key=lambda kv: -kv[1]["mean_intent_pp"])
        out.append(md_table(
            ["gate | scope", "honoured (mean)", "intent pp vs built", "SLU-F1 pp vs built", "intent pp vs first draft",
             "SLU-F1 pp vs first draft", "pools with intent < 0", "pools"],
            [[k, v["mean_honoured"], v["mean_intent_pp"], v["mean_slu_pp"], v["mean_intent_pp_vs_first_draft"],
              v["mean_slu_pp_vs_first_draft"], v["pools_intent_negative"], v["pools"]] for k, v in rows]))
        out.append("")
        for f, c in cf["folds"].items():
            out.append(f"- chosen on fold {f}: `{c['policy']}`; choosing-fold (intent, SLU-F1) = "
                       f"{c['train_fold_value']}; held-out fold = {c['held_out_fold_value']}")
    fs = report.get("form_selection") or {}
    if fs:
        out += ["", "## Reviewer-form selection (selection pools only, paired on the same R01C rows)"]
        out.append(md_table(
            ["contrastive pool", "rows", "contrastive loop intent pp", "locked loop intent pp (mean of pools)",
             "paired difference pp", "CI95"],
            [[fs["contrastive_pool"], fs["rows"], fs["contrastive_loop_intent_pp"], fs["locked_loop_intent_pp_mean"],
              fs["paired_difference_intent_pp"], fs["paired_difference_ci95"]]]))
    out += ["", "## Selected policies, per pool, paired against the pool as built (cluster CI95)"]
    for key, per in report["selected_intervals"].items():
        out.append(f"### {key}")
        out.append(md_table(["pool", "intent pp", "CI95", "SLU-F1 pp", "CI95"],
                            [[lb, d["intent_pp"], d["intent_ci95"], d["slu_pp"], d["slu_ci95"]]
                             for lb, d in per.items()]))
        out.append("")
    return "\n".join(out) + "\n"


def strip_time(document: dict) -> dict:
    return {k: v for k, v in document.items() if k != "generated_at"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--skip-dev", action="store_true", help="omit the DEV-2000-ADDED descriptive pools")
    parser.add_argument("--gold-cache", default=None,
                        help="optional local scratch pickle OUTSIDE the repository (never committed)")
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    rc = roster_checks()
    if rc["r01c_and_fold_a_recordings"] or rc["r01c_and_fold_a_utterances"]:
        raise ReadError("R01C overlaps Fold A; the selection rule cannot hold")
    pools_spec = [p for p in POOLS if not (args.skip_dev and p[2] == "dev")]
    splits = ["train"] + ([] if args.skip_dev else ["devel"])
    gold = load_gold(lock, data_root, splits, Path(args.gold_cache) if args.gold_cache else None)
    inventory = load_legal_intent_inventory(lock, data_root)
    ex_intents = load_exemplar_intents(data_root)
    pools, visits = [], []
    for spec in pools_spec:
        pool = load_pool(data_root, spec, gold, inventory, ex_intents)
        pool["checks"]["rows_equal_roster"] = int(set(pool["rows"]) == rc["ids"][spec[4]])
        vs = visit_records(pool, gold)
        visits += vs
        pool["visits"] = len(vs)
        pool["revise_routes"] = sum(1 for r in pool["rows"].values() for a in r["routes"] if a == "REVISE")
        pools.append(pool)
        print(f"loaded {spec[0]}: visits {len(vs)} checks {pool['checks']}", flush=True)
    groups = {
        "selection / locked-v1": lambda v: v["use"] == "selection" and v["form"].startswith("locked-v1"),
        "selection / contrastive-candrec": lambda v: v["use"] == "selection" and v["form"] == "contrastive-candrec",
        "fold-a / locked-v1 (descriptive)": lambda v: v["use"] == "fold-a" and v["form"].startswith("locked-v1"),
        "fold-a / primitives (descriptive)": lambda v: v["use"] == "fold-a" and v["form"] == "primitives",
        "dev / locked-v1 (descriptive)": lambda v: v["use"] == "dev",
    }
    credit = {name: credit_table([v for v in visits if f(v)]) for name, f in groups.items()}
    stance_route = {name: stance_route_table([v for v in visits if f(v)]) for name, f in groups.items()}
    triggers = {name: trigger_reach([v for v in visits if f(v)]) for name, f in groups.items()}
    loop_value = {}
    for pool in pools:
        events = revision_events(pool)
        ids = sorted(pool["rows"])
        built = {s: pool["rows"][s]["final_out"] for s in ids}
        first = per_row_scores(policy_answers(pool, events, GATES[NONE_GATE], "full"), gold)
        loop_value[pool["label"]] = {"use": pool["use"], "rows": len(ids), "revision_events": len(events),
                                     "as_built_vs_first_draft": paired_delta(first, built, ids,
                                                                             random.Random(BOOT_SEED))}
    selection = [p for p in pools if p["use"] == "selection"]
    grid = evaluate_grid(selection, gold)
    selection_stat = form_selection(visits, {p["label"]: {"form": p["form"], "ids": set(p["rows"])}
                                             for p in selection})
    selected_intervals = {}
    for cf in grid["crossfit"].values():
        for c in cf["folds"].values():
            key = c["policy"]
            if key in selected_intervals:
                continue
            per = {}
            for lb in cf["pools"]:
                pool = next(p for p in pools if p["label"] == lb)
                ids = sorted(pool["rows"])
                built = {s: pool["rows"][s]["final_out"] for s in ids}
                per[lb] = paired_delta(built, grid["per_pool"][lb]["policies"][key]["_scores"], ids,
                                       random.Random(BOOT_SEED))
            selected_intervals[key] = per
    for entry in grid["per_pool"].values():
        for cell in entry["policies"].values():
            cell.pop("_scores", None)
    report = {
        "read_id": READ_ID, "recipe": RECIPE, "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer_subprocess": 0, "gpu": 0},
        "roster_checks": {k: v for k, v in rc.items() if k != "ids"},
        "exemplar_snapshots_sha256": ex_intents["sha256"],
        "pools": [{k: v for k, v in p.items() if k != "rows"} for p in pools],
        "credit": credit, "stance_route": stance_route, "triggers": triggers, "loop_value": loop_value,
        "grid": grid, "selected_intervals": selected_intervals, "form_selection": selection_stat,
    }
    out_dir = data_root / ANALYSIS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    with (out_dir / "visits.jsonl").open("w", encoding="utf-8") as handle:
        for v in visits:
            handle.write(json.dumps(v, sort_keys=True) + "\n")
    (out_dir / "tables.md").write_text(render(report), encoding="utf-8")
    hashes = {"report.json (generated_at removed)": hashlib.sha256(
        json.dumps(strip_time(report), indent=1, sort_keys=True).encode("utf-8")).hexdigest(),
        "visits.jsonl": digest(out_dir / "visits.jsonl"), "tables.md": digest(out_dir / "tables.md")}
    (out_dir / "content-sha256.json").write_text(json.dumps(hashes, indent=1, sort_keys=True) + "\n",
                                                 encoding="utf-8")
    print(json.dumps(hashes, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
