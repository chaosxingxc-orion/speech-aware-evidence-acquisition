#!/usr/bin/env python3
"""a2t_gap_diagnosis.py -- owner decision 163, analysis track, Audio2Tool half.

Where does the sealed dual-store system (``SAEA-A2T-NATIVE-ROLE-DUAL-STORE-UNION4000-RECOVERY-V1``)
gain against the sealed direct baseline (``SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1``) and where
does it lose -- by tier, by function family (the public registry's ``domain/category``), by error
kind -- what are the Perception candidate misses, and what capability would close each gap?

Inputs (all sealed or already written, read-only):

* the two arms' sealed ``scores.json`` (official per-sample rows: parse flag, gold and predicted
  primary tool NAMES, tool and exact verdicts, parameter key counts);
* ``analysis/SAEA-A2T-ORDERED-ACTION-ATTRIBUTION-V1/rows.jsonl`` (2026-09-15): expected tool
  names in reference order, each arm's predicted tool names, the system's operative Perception
  candidate actions;
* ``analysis/SAEA-A2T-PRIMARY-PARAMETER-ATTRIBUTION-V1/rows.jsonl`` (2026-09-15): per arm the
  primary call's missing / extra / wrong-value KEY NAMES (never values);
* the public tool registry (``data.audio2tool.load_tool_registry``) for domain, category and
  whether a tool declares argument defaults;
* the A2T-AA null (``analysis/SAEA-A2T-STAGE3-AA-PAIRED-400-READ-V1/null.json``) for the
  half-widths of the zero-contact re-read on the paired 400 (decision 157, option 1).

DESCRIPTIVE and MODEL-FREE: zero model, tokenizer, encoder, scorer, server, GPU and network
contacts. Persisted: ids, tier / domain / category / tool / key NAMES, counts, rates, hashes.
Never persisted or printed: query text, transcripts, argument values, model output text.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

TIERS = (
    "tier1_direct", "tier2_parametric", "tier3_multi_intent", "tier4_implicit",
    "tier5_needle", "tier6_correction", "tier7_multiturn", "tier8_intent_blending",
)
#: arXiv:2604.22821 Table 3 (tool accuracy, exact match): Qwen3-Omni-30B, and the degraded
#: Qwen-2.5-Omni-7B floor (tool accuracy only), as pinned in the study's 2026-09-04 records.
PAPER_QWEN3 = {
    "tier1_direct": (92.4, 92.4), "tier2_parametric": (84.6, 15.6),
    "tier3_multi_intent": (74.7, 28.6), "tier4_implicit": (33.4, 11.3),
    "tier5_needle": (90.6, 36.0), "tier6_correction": (81.5, 24.8),
    "tier7_multiturn": (54.6, 16.3), "tier8_intent_blending": (41.7, 12.4),
}
PAPER_QWEN25_TOOL = {
    "tier1_direct": 79.5, "tier2_parametric": 80.6, "tier3_multi_intent": 50.2,
    "tier4_implicit": 22.4, "tier5_needle": 74.1, "tier6_correction": 68.3,
    "tier7_multiturn": 48.2, "tier8_intent_blending": 36.5,
}

DIRECT_RUN = "SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000-V1"
DIRECT_ATTEMPT = "attempt-a2t-native-role-direct-union4000-generation-v1"
SYSTEM_RUN = "SAEA-A2T-NATIVE-ROLE-DUAL-STORE-UNION4000-RECOVERY-V1"
SYSTEM_ATTEMPT = "attempt-a2t-native-role-dual-store-union4000-recovery-generation-v1"
ORDERED_ROWS = "analysis/SAEA-A2T-ORDERED-ACTION-ATTRIBUTION-V1/rows.jsonl"
PARAM_ROWS = "analysis/SAEA-A2T-PRIMARY-PARAMETER-ATTRIBUTION-V1/rows.jsonl"
AA_NULL = "analysis/SAEA-A2T-STAGE3-AA-PAIRED-400-READ-V1/null.json"
PAIRED_ROSTER = "docs/receipts/rosters/a2t-paired-400-v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iter_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def pct(a: float, b: float) -> float | None:
    return round(100.0 * a / b, 3) if b else None


def official_rows(data: Path, run: str, attempt: str) -> tuple[dict[str, dict], str]:
    path = data / "runs" / run / attempt / f"{run}.scores.json"
    scores = json.loads(path.read_text(encoding="utf-8"))
    return {r["sample_id"]: r for r in scores["a2t-toolcall-official"]["per_sample"]}, sha(path)


def error_kind(off: Mapping[str, Any], diag: Mapping[str, Any] | None, fam: Mapping[str, str]) -> str:
    """Exclusive primary-call error kind under the official protocol."""

    if not off.get("parsed"):
        return "format_unparsed"
    if not off.get("tool_correct"):
        pred, gold = off.get("predicted_tool"), off.get("gold_tool")
        if pred not in fam:
            return "wrong_tool_unregistered_name"
        return "wrong_tool_same_family" if fam.get(pred) == fam.get(gold) else "wrong_tool_cross_family"
    if off.get("exact_match"):
        return "exact"
    d = (diag or {}).get("diagnostics") or {}
    name = bool(d.get("missing_keys")) or bool(d.get("extra_keys"))
    value = bool(d.get("wrong_value_keys"))
    if name and value:
        return "arg_name_and_value"
    if name:
        missing, extra = bool(d.get("missing_keys")), bool(d.get("extra_keys"))
        if missing and not extra:
            return "arg_name_missing_key"
        if extra and not missing:
            return "arg_name_extra_key"
        return "arg_name_missing_and_extra"
    if value:
        return "arg_value_only"
    return "other_inexact"


KIND_ORDER = (
    "exact", "arg_value_only", "arg_name_extra_key", "arg_name_missing_key",
    "arg_name_missing_and_extra", "arg_name_and_value", "other_inexact",
    "wrong_tool_same_family", "wrong_tool_cross_family", "wrong_tool_unregistered_name",
    "format_unparsed",
)


_VERBS = {
    "get", "set", "start", "stop", "enable", "disable", "toggle", "adjust", "activate", "control",
    "find", "reboot", "restart", "update", "arm", "disarm", "check", "view", "stream", "open", "close",
    "lock", "unlock", "run", "play", "pause", "create", "delete", "schedule", "ramp", "flash", "calibrate",
}


def name_tokens(name: str | None) -> set[str]:
    """Lowercased camelCase / snake_case parts of a tool NAME, verbs and suffix tags removed."""

    if not name:
        return set()
    import re

    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", name.replace("_", " "))
    tokens = {t.lower() for t in parts}
    return {t for t in tokens if t not in _VERBS and t not in {"diag", "home", "car", "state", "status", "mode"}}


def near_name(a: str | None, b: str | None) -> bool:
    """Two different tool names that share an object token (e.g. a *Lock*/*Lock* pair)."""

    return bool(a and b and a != b and (name_tokens(a) & name_tokens(b)))


def call_count_kind(expected: Sequence[str], predicted: Sequence[str]) -> str:
    if len(predicted) < len(expected):
        return "missing_call"
    if len(predicted) > len(expected):
        return "extra_call"
    return "count_equal"


def strat_boot(delta: np.ndarray, tiers: np.ndarray, seed: int, draws: int) -> dict:
    rng = np.random.default_rng(seed)
    names = sorted(set(tiers.tolist()))
    idx = {t: np.flatnonzero(tiers == t) for t in names}
    stats = np.empty(draws)
    for i in range(draws):
        allp = np.concatenate([rng.choice(idx[t], size=len(idx[t]), replace=True) for t in names])
        stats[i] = delta[allp].mean()
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return {
        "mean_delta_pp": round(100.0 * float(delta.mean()), 3),
        "ci95_pp": [round(100.0 * float(lo), 3), round(100.0 * float(hi), 3)],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    repo, data, out = Path(args.repo_root), Path(args.data_root), Path(args.out)
    sys.path.insert(0, str(repo / "src"))
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry  # noqa: PLC0415
    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

    registry = load_tool_registry(load_lock(Path(args.lock)), data)
    fam = {r["tool_name"]: f"{r['domain']}/{r['category']}" for r in registry}
    has_default = {r["tool_name"]: bool(r["argument_defaults"].strip()) for r in registry}

    direct, direct_sha = official_rows(data, DIRECT_RUN, DIRECT_ATTEMPT)
    system, system_sha = official_rows(data, SYSTEM_RUN, SYSTEM_ATTEMPT)
    ordered = {r["sample_id"]: r for r in iter_jsonl(data / ORDERED_ROWS)}
    params = {r["sample_id"]: r for r in iter_jsonl(data / PARAM_ROWS)}
    ids = sorted(direct)
    assert set(ids) == set(system) == set(ordered) == set(params) and len(ids) == 4000

    rows: list[dict] = []
    for sid in ids:
        d, s, o, p = direct[sid], system[sid], ordered[sid], params[sid]
        assert d["gold_tool"] == s["gold_tool"] == p["primary_reference_tool"]
        gold = d["gold_tool"]
        union = sorted({name for action in (o.get("candidate_actions") or []) for name in action})
        available = bool((o.get("alignment") or {}).get("candidate_state_available", True))
        expected = list(o.get("expected_tool_names") or [])
        rows.append({
            "sample_id": sid,
            "tier": o["tier"],
            "domain": o["domain"],
            "gold_family": fam.get(gold, "unregistered"),
            "gold_tool": gold,
            "gold_tool_declares_defaults": has_default.get(gold),
            "reference_empty": bool(p.get("reference_empty")),
            "reference_count_class": o.get("reference_count_class"),
            "expected_count": len(expected),
            "direct_kind": error_kind(d, p.get("direct"), fam),
            "system_kind": error_kind(s, p.get("system"), fam),
            "direct_tool": bool(d.get("tool_correct")),
            "system_tool": bool(s.get("tool_correct")),
            "direct_exact": bool(d.get("exact_match")),
            "system_exact": bool(s.get("exact_match")),
            "direct_pred_tool": d.get("predicted_tool"),
            "system_pred_tool": s.get("predicted_tool"),
            "direct_call_kind": call_count_kind(expected, o.get("direct_predicted_tool_names") or []),
            "system_call_kind": call_count_kind(expected, o.get("system_predicted_tool_names") or []),
            "candidate_available": available,
            "candidate_union_size": len(union),
            "gold_in_union": gold in union if available else None,
            "union_has_gold_family": (any(fam.get(n) == fam.get(gold) for n in union) if available else None),
            "union_families": sorted({fam.get(n, "unregistered") for n in union}),
            "system_pred_in_union": (s.get("predicted_tool") in union) if available else None,
            "direct_wrong_value_keys": list(((p.get("direct") or {}).get("diagnostics") or {}).get("wrong_value_keys") or []),
            "system_wrong_value_keys": list(((p.get("system") or {}).get("diagnostics") or {}).get("wrong_value_keys") or []),
            "system_extra_keys": list(((p.get("system") or {}).get("diagnostics") or {}).get("extra_keys") or []),
            "system_extra_default_keys": list(((p.get("system") or {}).get("diagnostics") or {}).get("extra_keys_matching_declared_defaults") or []),
            "system_missing_keys": list(((p.get("system") or {}).get("diagnostics") or {}).get("missing_keys") or []),
        })

    def summarize(group: Iterable[dict]) -> dict:
        g = list(group)
        n = len(g)
        return {
            "rows": n,
            "direct_tool_pct": pct(sum(r["direct_tool"] for r in g), n),
            "system_tool_pct": pct(sum(r["system_tool"] for r in g), n),
            "delta_tool_pp": round((pct(sum(r["system_tool"] for r in g), n) or 0) - (pct(sum(r["direct_tool"] for r in g), n) or 0), 3) if n else None,
            "tool_saves": sum((not r["direct_tool"]) and r["system_tool"] for r in g),
            "tool_harms": sum(r["direct_tool"] and (not r["system_tool"]) for r in g),
            "direct_exact_pct": pct(sum(r["direct_exact"] for r in g), n),
            "system_exact_pct": pct(sum(r["system_exact"] for r in g), n),
            "delta_exact_pp": round((pct(sum(r["system_exact"] for r in g), n) or 0) - (pct(sum(r["direct_exact"] for r in g), n) or 0), 3) if n else None,
            "exact_saves": sum((not r["direct_exact"]) and r["system_exact"] for r in g),
            "exact_harms": sum(r["direct_exact"] and (not r["system_exact"]) for r in g),
            "candidate_coverage_pct": pct(sum(bool(r["gold_in_union"]) for r in g), n),
        }

    by = lambda key: {k: summarize(v) for k, v in sorted(_group(rows, key).items())}  # noqa: E731

    # T1 tiers with the paper columns
    tiers = by("tier")
    for t, row in tiers.items():
        row["paper_qwen3_tool"], row["paper_qwen3_exact"] = PAPER_QWEN3[t]
        row["paper_qwen25_tool_floor"] = PAPER_QWEN25_TOOL[t]

    # T2 families (gold primary family)
    families = by("gold_family")

    # T3 error kinds and transitions
    kinds = {
        "direct": dict(collections.Counter(r["direct_kind"] for r in rows)),
        "system": dict(collections.Counter(r["system_kind"] for r in rows)),
    }
    transitions = collections.Counter((r["direct_kind"], r["system_kind"]) for r in rows)
    transition_table = {f"{a} -> {b}": c for (a, b), c in sorted(transitions.items(), key=lambda kv: -kv[1])}
    kinds_by_tier = {
        t: {
            "direct": dict(collections.Counter(r["direct_kind"] for r in rows if r["tier"] == t)),
            "system": dict(collections.Counter(r["system_kind"] for r in rows if r["tier"] == t)),
        }
        for t in TIERS
    }
    call_kinds = {
        arm: {
            cls: dict(collections.Counter(r[f"{arm}_call_kind"] for r in rows if r["reference_count_class"] == cls))
            for cls in sorted({r["reference_count_class"] for r in rows})
        }
        for arm in ("direct", "system")
    }
    call_kinds_by_tier = {
        t: {arm: dict(collections.Counter(r[f"{arm}_call_kind"] for r in rows if r["tier"] == t)) for arm in ("direct", "system")}
        for t in TIERS
    }

    # T3b key names behind the argument errors (system, tool-correct rows)
    tool_ok = [r for r in rows if r["system_tool"]]
    key_counts = {
        "system_wrong_value_key_names": dict(collections.Counter(k for r in tool_ok for k in r["system_wrong_value_keys"]).most_common(15)),
        "direct_wrong_value_key_names": dict(collections.Counter(k for r in rows if r["direct_tool"] for k in r["direct_wrong_value_keys"]).most_common(15)),
        "system_extra_key_names": dict(collections.Counter(k for r in tool_ok for k in r["system_extra_keys"]).most_common(15)),
        "system_extra_keys_equal_to_declared_default": sum(len(r["system_extra_default_keys"]) for r in tool_ok),
        "system_extra_keys_total": sum(len(r["system_extra_keys"]) for r in tool_ok),
        "system_missing_key_names": dict(collections.Counter(k for r in tool_ok for k in r["system_missing_keys"]).most_common(15)),
        "system_extra_key_rows_reference_empty": sum(1 for r in tool_ok if r["system_extra_keys"] and r["reference_empty"]),
        "system_extra_key_rows": sum(1 for r in tool_ok if r["system_extra_keys"]),
    }

    # T4 the Perception candidate misses
    avail = [r for r in rows if r["candidate_available"]]
    misses = [r for r in avail if not r["gold_in_union"]]
    covered = [r for r in avail if r["gold_in_union"]]
    miss_profile = {
        "rows_available": len(avail),
        "rows_unavailable": len(rows) - len(avail),
        "misses": len(misses),
        "covered": len(covered),
        "miss_by_tier": {t: sum(r["tier"] == t for r in misses) for t in TIERS},
        "miss_by_domain": dict(collections.Counter(r["domain"] for r in misses)),
        "miss_by_gold_family_top15": dict(collections.Counter(r["gold_family"] for r in misses).most_common(15)),
        "miss_rate_by_gold_family": {
            f: {"rows": v["rows"], "miss_pct": round(100.0 - (v["candidate_coverage_pct"] or 0.0), 2)}
            for f, v in families.items()
        },
        "miss_union_empty": sum(r["candidate_union_size"] == 0 for r in misses),
        "miss_union_has_gold_family": sum(bool(r["union_has_gold_family"]) for r in misses),
        "miss_union_other_family_only": sum((r["candidate_union_size"] > 0) and not r["union_has_gold_family"] for r in misses),
        "miss_union_other_domain_only": sum(
            (r["candidate_union_size"] > 0) and all(f.split("/")[0] != r["domain"] for f in r["union_families"]) for r in misses
        ),
        "miss_union_size_hist": dict(collections.Counter(min(r["candidate_union_size"], 6) for r in misses)),
        "covered_union_size_hist": dict(collections.Counter(min(r["candidate_union_size"], 6) for r in covered)),
        "miss_reference_class": dict(collections.Counter(r["reference_count_class"] for r in misses)),
        "miss_direct_tool_correct": sum(r["direct_tool"] for r in misses),
        "miss_system_tool_correct": sum(r["system_tool"] for r in misses),
        "miss_direct_exact": sum(r["direct_exact"] for r in misses),
        "miss_system_exact": sum(r["system_exact"] for r in misses),
        "miss_system_pred_same_family_as_gold": sum(
            (not r["system_tool"]) and fam.get(r["system_pred_tool"]) == r["gold_family"] for r in misses
        ),
        "miss_top_gold_tools": dict(collections.Counter(r["gold_tool"] for r in misses).most_common(15)),
        "miss_top_gold_to_system_pairs": {
            f"{a} -> {b}": c
            for (a, b), c in collections.Counter(
                (r["gold_tool"], r["system_pred_tool"]) for r in misses if not r["system_tool"]
            ).most_common(15)
        },
        "covered_final_wrong": sum(not r["system_tool"] for r in covered),
        "covered_final_wrong_same_family": sum(
            (not r["system_tool"]) and fam.get(r["system_pred_tool"]) == r["gold_family"] for r in covered
        ),
        "covered_final_wrong_pred_in_union": sum((not r["system_tool"]) and bool(r["system_pred_in_union"]) for r in covered),
        "covered_direct_tool_correct": sum(r["direct_tool"] for r in covered),
        "covered_system_tool_correct": sum(r["system_tool"] for r in covered),
    }

    # T5 confusions (names only)
    def pairs(cond) -> dict:
        return {
            f"{a} -> {b}": c
            for (a, b), c in collections.Counter(
                (r["gold_tool"], r["system_pred_tool"]) for r in rows if cond(r)
            ).most_common(20)
        }

    confusions = {
        "system_new_tool_errors_top20": pairs(lambda r: r["direct_tool"] and not r["system_tool"]),
        "system_all_tool_errors_top20": pairs(lambda r: not r["system_tool"]),
        "system_new_errors_same_family": sum(
            r["direct_tool"] and not r["system_tool"] and fam.get(r["system_pred_tool"]) == r["gold_family"] for r in rows
        ),
        "system_new_errors_total": sum(r["direct_tool"] and not r["system_tool"] for r in rows),
        "direct_errors_same_family": sum((not r["direct_tool"]) and r["direct_kind"] == "wrong_tool_same_family" for r in rows),
        "direct_errors_total": sum(not r["direct_tool"] for r in rows),
    }

    # T5b near-name ("twin") confusions and the exact-match gain / loss decomposition
    def twin_share(cond, pred_key: str) -> dict:
        errs = [r for r in rows if cond(r)]
        twins = [r for r in errs if near_name(r["gold_tool"], r[pred_key])]
        return {"errors": len(errs), "near_name_twin": len(twins), "share_pct": pct(len(twins), len(errs))}

    confusions["near_name_twins"] = {
        "definition": (
            "the predicted and gold tool NAMES differ but share an object token after verbs and the tags "
            "diag/home/car/state/status/mode are removed (e.g. getLockState vs getLockStatus)"
        ),
        "direct_tool_errors": twin_share(lambda r: r["direct_kind"].startswith("wrong_tool"), "direct_pred_tool"),
        "system_tool_errors": twin_share(lambda r: r["system_kind"].startswith("wrong_tool"), "system_pred_tool"),
        "system_new_tool_errors": twin_share(lambda r: r["direct_tool"] and not r["system_tool"], "system_pred_tool"),
        "system_candidate_miss_errors": twin_share(
            lambda r: r["candidate_available"] and not r["gold_in_union"] and not r["system_tool"], "system_pred_tool"
        ),
        "system_covered_wrong_errors": twin_share(
            lambda r: r["candidate_available"] and r["gold_in_union"] and not r["system_tool"], "system_pred_tool"
        ),
        "registry_twin_pairs": sum(
            1 for i, a in enumerate(sorted(fam)) for b in sorted(fam)[i + 1:] if near_name(a, b)
        ),
    }
    exact_flow = {
        "exact_saves_by_direct_kind": dict(collections.Counter(
            r["direct_kind"] for r in rows if (not r["direct_exact"]) and r["system_exact"])),
        "exact_harms_by_system_kind": dict(collections.Counter(
            r["system_kind"] for r in rows if r["direct_exact"] and (not r["system_exact"]))),
        "exact_saves_by_tier": {t: sum((not r["direct_exact"]) and r["system_exact"] for r in rows if r["tier"] == t) for t in TIERS},
        "exact_harms_by_tier": {t: sum(r["direct_exact"] and (not r["system_exact"]) for r in rows if r["tier"] == t) for t in TIERS},
        "tool_harms_by_candidate_state": {
            "gold_in_union": sum(r["direct_tool"] and not r["system_tool"] for r in rows if r["gold_in_union"]),
            "gold_not_in_union": sum(r["direct_tool"] and not r["system_tool"] for r in rows if r["gold_in_union"] is False),
        },
        "tool_saves_by_candidate_state": {
            "gold_in_union": sum((not r["direct_tool"]) and r["system_tool"] for r in rows if r["gold_in_union"]),
            "gold_not_in_union": sum((not r["direct_tool"]) and r["system_tool"] for r in rows if r["gold_in_union"] is False),
        },
    }

    # T6 ceilings (arithmetic on sealed rows; upper bounds, never predictions)
    n = len(rows)
    sys_tool = sum(r["system_tool"] for r in rows)
    sys_exact = sum(r["system_exact"] for r in rows)
    dir_tool = sum(r["direct_tool"] for r in rows)
    covered_rate = sum(r["system_tool"] for r in covered) / len(covered)
    sk = collections.Counter(r["system_kind"] for r in rows)
    ceilings = {
        "baseline": {"direct_tool_pct": pct(dir_tool, n), "system_tool_pct": pct(sys_tool, n),
                     "direct_exact_pct": pct(sum(r["direct_exact"] for r in rows), n), "system_exact_pct": pct(sys_exact, n)},
        "C1_candidate_recall_restore_direct_on_misses": {
            "what": "misses answered at the direct arm's own correctness on those rows (no new knowledge, just no damage)",
            "system_tool_pct": pct(sys_tool - sum(r["system_tool"] for r in misses) + sum(r["direct_tool"] for r in misses), n),
            "system_exact_pct": pct(sys_exact - sum(r["system_exact"] for r in misses) + sum(r["direct_exact"] for r in misses), n),
        },
        "C1b_candidate_recall_full_at_covered_rate": {
            "what": "every miss covered and converted at the covered rows' observed rate (%.4f); an optimistic bound" % covered_rate,
            "system_tool_pct": round(100.0 * (sys_tool - sum(r["system_tool"] for r in misses) + covered_rate * len(misses)) / n, 3),
        },
        "C2_selection_within_union": {
            "what": "every covered row whose final primary tool is wrong selects the covered gold tool",
            "added_tool_rows": sum(not r["system_tool"] for r in covered),
            "system_tool_pct_alone": pct(sys_tool + sum(not r["system_tool"] for r in covered), n),
        },
        "C3_value_grounding": {
            "what": "tool-correct system rows whose ONLY defect is wrong values become exact",
            "rows": sk["arg_value_only"],
            "system_exact_pct": pct(sys_exact + sk["arg_value_only"], n),
        },
        "C4_argument_omission_default_semantics": {
            "what": "tool-correct system rows whose ONLY defect is an extra or missing key become exact",
            "rows_extra_only": sk["arg_name_extra_key"],
            "rows_missing_only": sk["arg_name_missing_key"],
            "rows_missing_and_extra": sk["arg_name_missing_and_extra"],
            "system_exact_pct": pct(sys_exact + sk["arg_name_extra_key"] + sk["arg_name_missing_key"] + sk["arg_name_missing_and_extra"], n),
        },
        "C3_plus_C4": {
            "system_exact_pct": pct(
                sys_exact + sk["arg_value_only"] + sk["arg_name_extra_key"] + sk["arg_name_missing_key"]
                + sk["arg_name_missing_and_extra"] + sk["arg_name_and_value"] + sk["other_inexact"], n),
            "what": "every tool-correct system row becomes exact (exact ceiling = system tool accuracy)",
        },
        "paper_equal_tier_mean": {
            "qwen3_tool": round(sum(v[0] for v in PAPER_QWEN3.values()) / 8, 3),
            "qwen3_exact": round(sum(v[1] for v in PAPER_QWEN3.values()) / 8, 3),
            "qwen25_tool_floor": round(sum(PAPER_QWEN25_TOOL.values()) / 8, 3),
        },
    }

    # T7 zero-contact re-read on the paired 400 at the A2T-AA half-widths
    roster = json.loads((repo / PAIRED_ROSTER).read_text(encoding="utf-8"))
    pids = [str(i["sample_id"]) for i in roster["items"]]
    aa_path = data / AA_NULL
    aa = json.loads(aa_path.read_text(encoding="utf-8"))
    byid = {r["sample_id"]: r for r in rows}
    ptiers = np.array([byid[s]["tier"] for s in pids])
    reread: dict[str, Any] = {"rows": len(pids), "aa_null_sha256": sha(aa_path),
                              "h_A2T_natural_pp": aa["h_A2T"]["natural_mixture_pp"],
                              "aa_request_identical_by_recipe_letter": aa["step2_request_identity"]["identical"]}
    for metric, dk, sk_ in (("official_tool_accuracy", "direct_tool", "system_tool"),
                            ("official_exact_match", "direct_exact", "system_exact")):
        delta = np.array([float(byid[s][sk_]) - float(byid[s][dk]) for s in pids])
        block = strat_boot(delta, ptiers, 20260903, 10000)
        h = aa["h_A2T"]["natural_mixture_pp"]["official_tool_accuracy" if metric == "official_tool_accuracy" else "official_exact_match"]
        block["h_pp"] = round(h, 3)
        block["point_in_h_units"] = round(block["mean_delta_pp"] / h, 2) if h else None
        block["direct_pct"] = pct(sum(byid[s][dk] for s in pids), len(pids))
        block["system_pct"] = pct(sum(byid[s][sk_] for s in pids), len(pids))
        block["per_tier_delta_pp"] = {
            t: round(100.0 * float(np.mean([float(byid[s][sk_]) - float(byid[s][dk]) for s in pids if byid[s]["tier"] == t])), 1)
            for t in TIERS
        }
        reread[metric] = block

    result = {
        "schema": "saea-xc-a2t-gap-diagnosis-v1",
        "sources": {
            "direct_scores_sha256": direct_sha, "system_scores_sha256": system_sha,
            "ordered_rows_sha256": sha(data / ORDERED_ROWS), "param_rows_sha256": sha(data / PARAM_ROWS),
            "registry_tools": len(registry), "registry_families": len(set(fam.values())),
        },
        "T1_by_tier": tiers,
        "T1b_by_domain": by("domain"),
        "T2_by_gold_family": families,
        "T3_error_kinds": kinds,
        "T3_error_kind_transitions": transition_table,
        "T3_error_kinds_by_tier": kinds_by_tier,
        "T3_call_count_kinds": call_kinds,
        "T3_call_count_kinds_by_tier": call_kinds_by_tier,
        "T3b_argument_key_names": key_counts,
        "T4_candidate_misses": miss_profile,
        "T5_confusions": confusions,
        "T5c_exact_and_tool_flow": exact_flow,
        "T6_ceilings": ceilings,
        "T7_paired400_zero_contact_reread": reread,
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0, "gpu": 0, "network": 0},
    }
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (out / "a2t-gap-diagnosis.json").write_text(text, encoding="utf-8")
    print(json.dumps({"written": str(out / "a2t-gap-diagnosis.json"),
                      "sha256": hashlib.sha256(text.encode()).hexdigest()}))
    return 0


def _group(rows: Sequence[dict], key: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        out[str(r[key])].append(r)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
