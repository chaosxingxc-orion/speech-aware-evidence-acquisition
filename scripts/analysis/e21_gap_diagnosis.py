#!/usr/bin/env python3
"""e21_gap_diagnosis.py -- owner decision 163, analysis track, Earnings21 + ConEC half.

Three model-free reads over sealed bytes:

1. **The direct core on the agentic metrics.** The full-44 agentic-metric baseline
   (``SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1``: ConEC-mirror entity WER per type and
   numeric-value accuracy per kind) beside the two sealed KC-E1f repair passes, per entity
   type and numeric kind, so what the direct core gets wrong -- and what the one admitted
   knowledge module moves -- is visible by class, not only as corpus WER.
2. **Where the system form added or removed value when it did not truncate.** The sealed E35
   sub10 direct and system arms, decomposed per native window by the repository's own
   ``analysis.e21_score_window_read.decompose_scored_windows`` over their sealed first-score
   ConEC alignments (exact partition of every operation), joined by window id and split by
   the system window's delivery kind (accepted Solver draft after a Planner ACCEPT, terminal
   Solver draft, E13 abstention): S/D/I, entity type and numeric counts per group.
3. **What knowledge is supplied versus missing.** For every entity-typed reference word of
   the sealed E35 sub10 direct alignment, whether its Whisper-normalised form occurs in the
   call's ConEC context as the KC-E1 / KC-E1f brief supplied it (cap 12 entries per class),
   in the full ConEC context but beyond the cap, or nowhere in the context -- split by
   whether the direct core got the word right; plus the numeric-typed reference words'
   error shapes (deletion, substitution by a numeric token, substitution by a word).

MODEL-FREE and DESCRIPTIVE: zero model, tokenizer, encoder, scorer, server, GPU and network
contacts; the reference words are read offline from the sealed alignments only. Persisted:
ids, entity-type and numeric-kind NAMES, counts and rates. Never printed or persisted:
transcript, reference, context or hypothesis words.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

RUNS = {
    "direct": ("SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1", "attempt-e21-native-window-direct-sub10-v1"),
    "system": ("SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1", "attempt-e21-native-window-system-sub10-v1"),
}
BASELINE_SCORING = "runs/SAEA-E21-MF-AGENTIC-METRIC-BASELINE-V1/scoring"
KCE1F = {
    "kc_e1f_pass1": "runs/SAEA-E21-KC-E1F-REPAIR-44-V1/attempt-20260908T040832Z-ecda9c/SAEA-E21-KC-E1F-REPAIR-44-V1.scores.json",
    "kc_e1f_replicate": "runs/SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1/attempt-20260908T232501Z-36792e/SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1.scores.json",
}
NAMED_TYPES = ("PERSON", "ORG", "PRODUCT", "GPE", "LOC", "FAC", "NORP", "EVENT", "WEBSITE", "ABBREVIATION", "ALPHANUMERIC")
NUMERIC_TYPES = ("CARDINAL", "MONEY", "PERCENT", "DATE", "YEAR", "ORDINAL", "TIME")
CONEC_CONTEXT = "datasets/conec/earnings21/contexts"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rate(a: float, b: float) -> float | None:
    return round(100.0 * a / b, 3) if b else None


def find_score(document: Any, scorer: str) -> Mapping[str, Any]:
    """The scorer block inside a score-batch job document or a sealed scores.json."""

    if isinstance(document, Mapping):
        if scorer in document and isinstance(document[scorer], Mapping):
            return document[scorer]
        for value in document.values():
            found = find_score(value, scorer) if isinstance(value, (Mapping, list)) else None
            if found:
                return found
    if isinstance(document, list):
        for value in document:
            found = find_score(value, scorer)
            if found:
                return found
    return {}


def type_table(agg: Mapping[str, Any]) -> dict[str, dict]:
    out = {}
    for name, b in sorted((agg.get("by_entity_type") or {}).items()):
        out[name] = {
            "reference_words": b.get("reference_words"),
            "substitutions": b.get("substitutions"),
            "deletions": b.get("deletions"),
            "wer_pct": round(100.0 * float(b.get("wer") or 0.0), 3),
        }
    return out


def numeric_table(agg: Mapping[str, Any]) -> dict:
    return {
        "accuracy_pct": round(100.0 * float(agg.get("accuracy") or 0.0), 3),
        "by_kind": {
            k: {"expected": v.get("expected"), "matched": v.get("matched"), "hypothesis": v.get("hypothesis"),
                "accuracy_pct": round(100.0 * float(v.get("accuracy") or 0.0), 2)}
            for k, v in sorted((agg.get("by_kind") or {}).items())
        },
        "spurious": agg.get("spurious_numeric_words", agg.get("spurious")),
    }


class RecoveryError(RuntimeError):
    """A window's delivered text cannot be recovered exactly from sealed bytes."""


def recover_windows(run_dir: Path, run: str, wp: Any, execution_unit_scope: Any) -> tuple[dict, dict]:
    """Per call, the ordered native windows with their DELIVERED text, recovered from sealed bytes.

    The repository's ``analysis.delivery_windows.verified_execution_unit_windows`` refuses these
    2026-09-22 bundles at HEAD (and ``verify_bundle`` refuses them on a replaced session receipt),
    so the recovery is re-done here with an exact, hash-checked rule: a window whose delivered-text
    digest is the empty-string digest delivers ""; a window whose digest matches a sealed
    MODEL_RESPONSE text delivers that text; the remaining windows (the ones the Earnings delivery
    normaliser changed) are cut out of the sealed stitched call text between their known
    neighbours and must re-hash to the recorded digest. The stitch is then rebuilt and must equal
    the sealed outputs text byte for byte (``assert_stitch_reproduces_outputs``).
    """

    def digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    manifest = json.loads((run_dir / f"{run}.run-manifest.json").read_text(encoding="utf-8"))
    checks = {}
    for key, name in (("outputs", "outputs.jsonl"), ("raw_trace", "trace.jsonl"), ("scores", "scores.json")):
        pinned = (manifest.get(key) or {}).get("sha256")
        checks[f"{key}_sha256_matches_manifest"] = pinned == sha(run_dir / f"{run}.{name}")
    if not all(checks.values()):
        raise RecoveryError(f"{run}: sealed artifact hashes differ from the manifest: {checks}")
    texts: dict[str, str] = {}
    episodes: dict[str, Mapping] = {}
    with (run_dir / f"{run}.trace.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            payload = record.get("payload")
            if not isinstance(payload, Mapping):
                continue
            if isinstance(payload.get("text"), str):
                texts[digest(payload["text"])] = payload["text"]
            if "use_native_episode" in payload:
                episodes[str(record["record_id"]).split("/", 1)[0]] = payload["use_native_episode"]
    empty = digest("")
    windows: dict[str, tuple] = {}
    outputs_text: dict[str, str] = {}
    recovered_by_cut = 0
    with (run_dir / f"{run}.outputs.jsonl").open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    for row in rows:
        call = row["sample_id"]
        outputs_text[call] = row["text"]
        sources = row["execution_unit_delivery"]["sources"]
        known: list[str | None] = []
        for source in sources:
            h = source["delivery_text_sha256"]
            known.append("" if h == empty else texts.get(h))
        stitched, pos = row["text"], 0
        i = 0
        while i < len(sources):
            t = known[i]
            if t is None:
                # a maximal run of unrecovered windows, cut between known non-empty neighbours
                j = i
                while j < len(sources) and known[j] is None:
                    j += 1
                run_idx = list(range(i, j))
                nxt = next((known[m] for m in range(j, len(sources)) if known[m]), None)
                end_at = len(stitched) if nxt is None else stitched.find(" " + nxt, pos)
                if end_at < 0:
                    raise RecoveryError(f"{call}: cannot locate window {i + 1}'s successor in the stitch")
                cut = stitched[pos:end_at]
                hashes = [sources[m]["delivery_text_sha256"] for m in run_idx]
                parts = None
                if len(run_idx) == 1:
                    parts = [cut] if digest(cut) == hashes[0] else None
                elif len(run_idx) == 2:
                    for k, ch in enumerate(cut):
                        if ch == " " and digest(cut[:k]) == hashes[0] and digest(cut[k + 1:]) == hashes[1]:
                            parts = [cut[:k], cut[k + 1:]]
                            break
                if parts is None:
                    raise RecoveryError(f"{call}: windows {[m + 1 for m in run_idx]} cannot be cut to their digests")
                for m, part in zip(run_idx, parts):
                    known[m] = part
                    recovered_by_cut += 1
                    if part:
                        pos += len(part) + 1
                i = j
                continue
            if t:
                if stitched[pos:pos + len(t)] != t:
                    raise RecoveryError(f"{call}: window {i + 1} is not at its stitch position")
                pos += len(t) + 1
            i += 1
        spans = []
        for i, source in enumerate(sources):
            binding = source["execution_unit_binding"]
            record = binding["slice_record"]
            scope = execution_unit_scope(binding["request_key"])
            episode = episodes.get(scope)
            if episode is None:
                kind = "direct"
            elif episode.get("accepted_solver_receipt"):
                kind = "accepted"
            elif episode.get("terminal_solver_receipt"):
                kind = "terminal"
            elif episode.get("abstention_receipt"):
                kind = "abstention"
            else:
                kind = "unknown"
            spans.append(wp.WindowSpan(
                sample_id=call, window_index=i + 1, request_id=source["request_id"],
                start_seconds=float(record["start_seconds"]), end_seconds=float(record["end_seconds"]),
                audio_seconds=float(record["audio_seconds"]), text=known[i] or "",
                saturated=bool(source.get("saturated")), execution_unit_id=source.get("execution_unit_id"),
                delivery_kind=kind, skipped=bool(source.get("skipped")),
            ))
        windows[call] = tuple(spans)
    wp.assert_stitch_reproduces_outputs(windows, outputs_text)
    checks["windows_recovered_by_cut_and_rehash"] = recovered_by_cut
    checks["stitch_rebuilds_sealed_outputs"] = True
    return windows, checks


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    repo, data, out = Path(args.repo_root), Path(args.data_root), Path(args.out)
    sys.path.insert(0, str(repo / "src"))
    from speech_aware_evidence_acquisition.analysis.e21_score_window_read import decompose_scored_windows  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core import class_lists as cl  # noqa: PLC0415
    from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.execution_units import execution_unit_scope  # noqa: PLC0415
    from speech_aware_evidence_acquisition.reproduction import conec_entity_scoring as conec  # noqa: PLC0415

    sources: dict[str, str] = {}

    # ---- 1. full-44 direct baseline and KC-E1f, per type and kind --------------------
    base_conec = json.loads((data / BASELINE_SCORING / "conec-entity-wer.score.json").read_text(encoding="utf-8"))
    base_num = json.loads((data / BASELINE_SCORING / "numeric-value-accuracy.score.json").read_text(encoding="utf-8"))
    sources["baseline_conec_score_sha256"] = sha(data / BASELINE_SCORING / "conec-entity-wer.score.json")
    sources["baseline_numeric_score_sha256"] = sha(data / BASELINE_SCORING / "numeric-value-accuracy.score.json")
    full44: dict[str, Any] = {
        "direct_full44": {
            "entity": type_table(find_score(base_conec, "conec-entity-wer-official").get("aggregate") or {}),
            "numeric": numeric_table(find_score(base_num, "numeric-value-accuracy-v1").get("aggregate") or {}),
        }
    }
    for label, rel in KCE1F.items():
        doc = json.loads((data / rel).read_text(encoding="utf-8"))
        sources[f"{label}_scores_sha256"] = sha(data / rel)
        full44[label] = {
            "entity": type_table(doc["conec-entity-wer-official"]["aggregate"]),
            "numeric": numeric_table(doc["numeric-value-accuracy-v1"]["aggregate"]),
        }

    # ---- 2. E35 sub10 per-window decomposition ----------------------------------------
    windows_by_arm: dict[str, dict[str, dict]] = {}
    windows_by_arm_totals: dict[str, dict[str, int]] = {}
    spans_by_arm: dict[str, dict] = {}
    alignments: dict[str, dict[str, dict]] = {}
    for arm, (run, attempt) in RUNS.items():
        rdir = data / "runs" / run / attempt
        manifest = rdir / f"{run}.run-manifest.json"
        scores = json.loads((rdir / f"{run}.scores.json").read_text(encoding="utf-8"))
        sources[f"e35_{arm}_manifest_sha256"] = sha(manifest)
        sources[f"e35_{arm}_scores_sha256"] = sha(rdir / f"{run}.scores.json")
        spans, checks = recover_windows(rdir, run, wp, execution_unit_scope)
        sources[f"e35_{arm}_recovery_checks"] = checks
        spans_by_arm[arm] = spans
        result = decompose_scored_windows(spans, {"verified": True, "scores": scores})
        windows_by_arm[arm] = {row["window_id"]: row for row in result["rows"]}
        agg = scores["conec-entity-wer-official"]["aggregate"]["by_entity_type"]["__ALL__"]
        windows_by_arm_totals[arm] = {k: int(agg[k]) for k in ("substitutions", "deletions", "insertions", "reference_words")}
        alignments[arm] = {r["sample_id"]: r["alignment"] for r in scores["conec-entity-wer-official"]["per_sample"]}
    assert set(windows_by_arm["direct"]) == set(windows_by_arm["system"])

    # Reference-span partition (the E35 diagnosis's own convention): the reference words of a
    # window are the ones the DIRECT arm's alignment charges to it, reused for BOTH arms, so an
    # abstained system window keeps its own deletions instead of passing them to the neighbour
    # its hypothesis cursor stands in. Insertions stay with each arm's own hypothesis window.
    from speech_aware_evidence_acquisition.reproduction import numeric_value_accuracy as numeric  # noqa: PLC0415

    ref_rows: dict[str, dict[str, dict]] = {"direct": {}, "system": {}}
    for call in sorted(alignments["direct"]):
        adirect, asystem = alignments["direct"][call], alignments["system"][call]
        assert adirect["reference_words"] == asystem["reference_words"]
        owners, etypes = adirect["reference_owners"], adirect["entity_types"]
        refs = adirect["reference_words"]
        spans_d, spans_s = spans_by_arm["direct"][call], spans_by_arm["system"][call]
        norm = lambda text: " ".join(conec.hypothesis_whisper_words(text))  # noqa: E731
        ops_d = [tuple(x) for x in adirect["operations"]]
        ops_s = [tuple(x) for x in asystem["operations"]]
        b_d = wp.hypothesis_window_boundaries(spans_d, norm)
        b_s = wp.hypothesis_window_boundaries(spans_s, norm)
        charged_d = wp.charge_operations_to_windows(ops_d, b_d, len(adirect["hypothesis_words"]))
        ref_window: dict[int, int] = {}
        for k, part in enumerate(charged_d):
            for ri in wp.reference_indices(part):
                ref_window[ri] = k
        parts_s: list[list] = [[] for _ in spans_s]
        last_k = 0
        for op in ops_s:
            kind, ri, hi = op
            if ri is not None:
                last_k = ref_window[ri]
                parts_s[last_k].append(op)
            else:
                parts_s[wp.window_of_hypothesis_index(b_s, hi)].append(op)
        for arm, parts, alignment, spans in (("direct", charged_d, adirect, spans_d), ("system", parts_s, asystem, spans_s)):
            hyps = alignment["hypothesis_words"]
            for span, part in zip(spans, parts, strict=True):
                buckets = conec.entity_wer_buckets(part, owners, etypes)
                overall = buckets[conec.OVERALL_BUCKET]
                prefs = [refs[i] for i in wp.reference_indices(part)]
                phyps = [hyps[i] for i in wp.hypothesis_indices(part)]
                nc = numeric.numeric_value_counts(prefs, phyps)
                ref_rows[arm][span.identifier] = {
                    **overall,
                    "hypothesis_words": len(phyps),
                    "numeric_expected": nc["expected_numeric_words"],
                    "numeric_matched": nc["matched_numeric_words"],
                    "numeric_hypothesis": nc["hypothesis_numeric_words"],
                    "person_errors": buckets.get("PERSON", {}).get("errors", 0),
                    "entity_class_counts": {
                        name: [item["substitutions"], item["deletions"], item["reference_words"]]
                        for name, item in buckets.items()
                    },
                    "delivery_kind": span.delivery_kind,
                }
    # totals must equal the sealed aggregates on both arms
    for arm in ("direct", "system"):
        tot = collections.Counter()
        for row in ref_rows[arm].values():
            for key in ("substitutions", "deletions", "insertions", "reference_words"):
                tot[key] += int(row[key])
        sealed = windows_by_arm_totals[arm]
        assert all(tot[k] == sealed[k] for k in sealed), (arm, dict(tot), sealed)
    windows_by_arm = ref_rows

    def group_sum(ids: Sequence[str], arm: str) -> dict:
        rows = [windows_by_arm[arm][w] for w in ids]
        s = sum(int(r["substitutions"]) for r in rows)
        d = sum(int(r["deletions"]) for r in rows)
        i = sum(int(r["insertions"]) for r in rows)
        ref = sum(int(r["reference_words"]) for r in rows)
        by_type: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0, 0])
        for r in rows:
            for name, (sub, dele, refw) in r["entity_class_counts"].items():
                by_type[name][0] += sub
                by_type[name][1] += dele
                by_type[name][2] += refw
        return {
            "windows": len(rows), "reference_words": ref, "substitutions": s, "deletions": d, "insertions": i,
            "wer_pct": rate(s + d + i, ref),
            "hypothesis_words": sum(int(r["hypothesis_words"]) for r in rows),
            "numeric_expected": sum(int(r["numeric_expected"]) for r in rows),
            "numeric_matched_window_level": sum(int(r["numeric_matched"]) for r in rows),
            "numeric_hypothesis": sum(int(r["numeric_hypothesis"]) for r in rows),
            "by_entity_type": {
                name: {"substitutions": v[0], "deletions": v[1], "reference_words": v[2], "wer_pct": rate(v[0] + v[1], v[2])}
                for name, v in sorted(by_type.items())
                if name in NAMED_TYPES + NUMERIC_TYPES + ("__NON_ENTITY__",)
            },
        }

    kinds = collections.defaultdict(list)
    for wid, row in windows_by_arm["system"].items():
        kinds[str(row.get("delivery_kind"))].append(wid)
    e35 = {"partition": "reference spans from the direct arm's alignment, reused for both arms; insertions stay with each arm's own hypothesis window",
           "delivery_kind_counts": {k: len(v) for k, v in sorted(kinds.items())}, "groups": {}}
    for kind, ids in sorted(kinds.items()):
        e35["groups"][kind] = {"direct": group_sum(ids, "direct"), "system": group_sum(ids, "system")}
    all_ids = sorted(windows_by_arm["direct"])
    e35["groups"]["ALL"] = {"direct": group_sum(all_ids, "direct"), "system": group_sum(all_ids, "system")}
    # window-level saves and harms on the accepted windows (errors = S + D + I)
    acc = kinds.get("accepted", []) or kinds.get("accepted_solver", [])
    per = []
    for w in acc:
        dr, sr = windows_by_arm["direct"][w], windows_by_arm["system"][w]
        de = int(dr["substitutions"]) + int(dr["deletions"]) + int(dr["insertions"])
        se = int(sr["substitutions"]) + int(sr["deletions"]) + int(sr["insertions"])
        dp = int(dr.get("person_errors") or 0)
        sp = int(sr.get("person_errors") or 0)
        per.append((se - de, sp - dp))
    e35["accepted_window_level"] = {
        "windows": len(per),
        "fewer_errors": sum(1 for x, _ in per if x < 0),
        "more_errors": sum(1 for x, _ in per if x > 0),
        "equal_errors": sum(1 for x, _ in per if x == 0),
        "net_extra_errors": sum(x for x, _ in per),
        "person_fewer": sum(1 for _, y in per if y < 0),
        "person_more": sum(1 for _, y in per if y > 0),
        "net_extra_person_errors": sum(y for _, y in per),
    }

    # ---- 3. knowledge coverage of entity words (E35 sub10 direct alignment) -----------
    ctx = data / CONEC_CONTEXT

    def words(text: str) -> set[str]:
        return set(cl.normalize_whisper_english(text).split())

    def brief_sets(call: str) -> tuple[set[str], set[str]]:
        roster_text = (ctx / "participant_names" / f"{call}.names.txt").read_text(encoding="utf-8")
        doc_text = (ctx / f"{call}.txt").read_text(encoding="utf-8")
        entries = cl.roster_entries(roster_text)
        tokens = cl.context_tokens(doc_text)
        supplied: set[str] = set()
        for values in (cl.participant_class(entries), cl.affiliation_class(entries), cl.division_class(entries),
                       cl.company_class(tokens), cl.segment_class(tokens), cl.term_class(tokens)):
            for entry in list(values)[:12]:
                supplied |= words(entry)
        full: set[str] = set()
        for name, role in entries:
            full |= words(name) | words(role)
        for token in tokens:
            full |= words(token)
        return supplied, full

    coverage: dict[str, dict[str, int]] = collections.defaultdict(lambda: collections.Counter())
    numeric_shapes: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    digit = re.compile(r"\d")
    for call, alignment in sorted(alignments["direct"].items()):
        supplied, full = brief_sets(call)
        refs, hyps = alignment["reference_words"], alignment["hypothesis_words"]
        owners, types = alignment["reference_owners"], alignment["entity_types"]
        op_of: dict[int, tuple[str, int | None]] = {}
        for kind, ri, hi in (tuple(x) for x in alignment["operations"]):
            if ri is not None:
                op_of[ri] = (kind, hi)
        for p, word in enumerate(refs):
            ids = owners[p] or ()
            classes = sorted({types.get(i) for i in ids if types.get(i)})
            kind, hi = op_of.get(p, ("hit", None))
            correct = kind == conec.OP_HIT
            where = "brief_cap12" if word in supplied else ("context_beyond_cap" if word in full else "absent_from_context")
            for c in classes or ["__NON_ENTITY__"]:
                coverage[c][f"{'correct' if correct else 'error'}__{where}"] += 1
                if c in NUMERIC_TYPES and not correct:
                    if kind == conec.OP_DELETION:
                        numeric_shapes[c]["deletion"] += 1
                    elif hi is not None and digit.search(str(hyps[hi])):
                        numeric_shapes[c]["substituted_by_numeric_token"] += 1
                    else:
                        numeric_shapes[c]["substituted_by_word"] += 1
    coverage_out = {}
    for c, counter in sorted(coverage.items()):
        if c not in NAMED_TYPES + NUMERIC_TYPES + ("__NON_ENTITY__",):
            continue
        err = sum(v for k, v in counter.items() if k.startswith("error__"))
        ok = sum(v for k, v in counter.items() if k.startswith("correct__"))
        coverage_out[c] = {
            "reference_words": err + ok,
            "error_words": err,
            "error_in_brief_cap12": counter["error__brief_cap12"],
            "error_in_context_beyond_cap": counter["error__context_beyond_cap"],
            "error_absent_from_context": counter["error__absent_from_context"],
            "correct_in_brief_cap12": counter["correct__brief_cap12"],
            "correct_in_context_beyond_cap": counter["correct__context_beyond_cap"],
            "correct_absent_from_context": counter["correct__absent_from_context"],
            "error_share_in_brief_pct": rate(counter["error__brief_cap12"], err),
            "error_share_in_any_context_pct": rate(counter["error__brief_cap12"] + counter["error__context_beyond_cap"], err),
        }

    result = {
        "schema": "saea-xc-e21-gap-diagnosis-v1",
        "sources": sources,
        "bundle_verification_note": (
            "verify_bundle refuses both E35 sub10 bundles at HEAD on the archived session receipt of "
            "serving-e21-native-window-flightruntime-np4-max1024-v1 (live file replaced at a later restart, "
            "archive copy absent), and analysis.delivery_windows.verified_execution_unit_windows refuses the "
            "system bundle ('terminal request or response differs from delivery': 24 normaliser-changed windows "
            "whose delivered text is not a trace text). The windows are therefore recovered by the hash-checked "
            "rule of recover_windows; outputs, trace and scores hashes are checked against the manifest and the "
            "stitch rebuilds the sealed outputs text byte for byte"
        ),
        "E1_full44_direct_and_kc_e1f": full44,
        "E2_e35_sub10_by_delivery_kind": e35,
        "E3_knowledge_coverage_sub10_direct": {
            "definition": (
                "per ConEC entity type (a reference word carrying two tags counts once per type): whether the "
                "Whisper-normalised reference word occurs among the words of the KC-E1 / KC-E1f brief at cap 12 "
                "entries per class, among the words of the full ConEC roster + document context but not the "
                "capped brief, or nowhere in the context; split by the direct core's operation on that word"
            ),
            "by_type": coverage_out,
        },
        "E4_numeric_error_shapes_sub10_direct": {k: dict(v) for k, v in sorted(numeric_shapes.items())},
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0, "gpu": 0, "network": 0},
    }
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    (out / "e21-gap-diagnosis.json").write_text(text, encoding="utf-8")
    print(json.dumps({"written": str(out / "e21-gap-diagnosis.json"), "sha256": hashlib.sha256(text.encode()).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
