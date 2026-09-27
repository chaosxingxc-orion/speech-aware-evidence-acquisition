#!/usr/bin/env python3
"""e21_e41_perception_note_trace_read.py -- item E41: why the Earnings Perception
note truncates, read off the sealed traces, and what the bounded note costs.

WHAT IT READS. Owner decision 103 (row 103 of
``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``) names item
E41 -- "a bounded Perception note (structured / length-constrained instruction)
with its own dry run before the sub10 re-read of the Earnings system form" --
after the E39 and E39b four-row dry runs both failed R3 on a length-truncated
Perception contact (caps 320 and 640; the E35 parent lost a window at 1,024).
This script reads every sealed Perception contact of the Earnings system form:

* E35 sub10 system arm (342 windows, cap 1,024),
* E35 four-row system arm (recovery-v4, 4 windows, cap 1,024),
* E39 four-row dry run (4 windows, cap 320),
* E39b four-row dry run (4 windows, cap 640),

joins each contact to its wire ``finish_reason`` and ``usage.completion_tokens``,
and measures the STRUCTURE of each note -- word, line and list-item counts, the
6-gram repetition share, the loop onset and period, and the share of the SAME
window's direct-arm transcript 4-grams the note re-emits (the sealed E35 direct
arms, sub10 and four-row) -- then assigns every truncated note to exactly one
mode by a fixed rule (``MODE_RULE``). The receipt holds counts, rates, ids and
hashes only: no utterance, transcript, reference, gold or model output text is
printed or persisted. Note text is held in memory for the counts and dropped.

WHAT IT MEASURES (``--tokens``). The prompt-side token cost of the bounded note
(Perception instruction v1 vs v2, alone and as the wire renders it: instruction
+ ``"\\n\\nNative episode limits: "`` + the sealed limits object), and the
completion-side bound a compliant note implies, with the local vocab-only
``llama-tokenize`` process over the pinned Q4_K_M GGUF vocab (argv exactly
``scripts/analysis/slurp_g5_reviewer_instruction_token_measurement.py``): a
typical compliant note and a digit-dense worst case, both synthetic strings
built here from the instruction's own form, never from speech.

MODEL-FREE. Zero model, server, encoder, embedder, scorer, network, GPU and
paid-API contacts; ports 8080 / 8081 are never touched. The only process it
starts is the vocab-only tokenizer (``--tokens``), and the receipt counts it.

    python scripts/analysis/e21_e41_perception_note_trace_read.py \\
        --data-root "$SPEECHRL_DATA_DIR" --tokens --write
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import statistics
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = "docs/readiness/2026-09-27-e21-native-window-e41-v1"
TRACE_RECEIPT = "perception-trace-read-v1.json"
TOKEN_RECEIPT = "instruction-token-measurement-v1.json"

OLD_PROBE = "configs/probes/e21_native_window_system_perception_v1.txt"
NEW_PROBE = "configs/probes/e21_native_window_system_perception_v2.txt"

#: The sealed system arms whose Perception contacts are read, with their cap.
SYSTEM_RUNS = (
    ("E35-sub10", "SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1", "attempt-e21-native-window-system-sub10-v1"),
    ("E35-four-row", "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1", "attempt-e21-native-window-system-four-row-recovery-v4"),
    ("E39", "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39-V1", "attempt-e21-native-window-system-four-row-e39-v1"),
    ("E39b", "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1", "attempt-e21-native-window-system-four-row-e39b-v1"),
)
#: The sealed direct arms that give each window's transcript 4-gram set.
DIRECT_RUNS = (
    ("SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1", "attempt-e21-native-window-direct-sub10-v1"),
    ("SAEA-E21-NATIVE-WINDOW-DIRECT-FOUR-ROW-V1", "attempt-e21-native-window-direct-four-row-v1"),
)

#: The E41 bound, as the v2 instruction states it.
BOUND = {"max_lines": 5, "max_words_per_line": 20, "max_quoted_words_per_reading": 4, "readings_per_line": 2}
MODE_RULE = (
    "applied in order, first match wins: LOOP if the 6-gram repetition share >= 0.20; TRANSCRIPT if the note "
    "re-emits >= 0.50 of the same window's direct-arm transcript 4-gram set; ENUMERATION if it has >= 10 "
    "non-empty lines (twice the E41 line bound); PROSE otherwise"
)
LOOP_SHARE, TRANSCRIPT_SHARE, ENUMERATION_LINES = 0.20, 0.50, 10

DEFAULT_TOKENIZE = Path("/home/chao/llama.cpp/build/bin/llama-tokenize")
GGUF_RELPATH = "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf"
LIMITS_PREFIX = "\n\nNative episode limits: "

WORD = re.compile(r"[a-z0-9']+")
ITEM = re.compile(r"\s*([-*•]|\d+[.)])\s")


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def grams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def quantiles(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    ordered = sorted(values)

    def at(q: float) -> float:
        return ordered[min(len(ordered) - 1, int(q * (len(ordered) - 1) + 0.5))]

    return {"n": len(ordered), "min": ordered[0], "p25": at(0.25), "p50": statistics.median(ordered),
            "p75": at(0.75), "p90": at(0.90), "p95": at(0.95), "max": ordered[-1]}


def load_trace(path: Path) -> tuple[dict, list[dict]]:
    """Per-contact fields keyed by flight id, and the per-window episode receipts."""

    contacts: dict[str, dict] = {}
    episodes: list[dict] = []
    for line in io.open(path, encoding="utf-8"):
        record = json.loads(line)
        rid, channel, payload = record["record_id"], record["channel"], record["payload"]
        if rid.startswith("flight-"):
            fid = rid.split("/")[0]
            row = contacts.setdefault(fid, {})
            if channel == "MODEL_REQUEST":
                inner = payload["payload"]
                row["packet"] = inner.get("speech_packet_sha256")
                row["max_tokens"] = inner["decoding_params"]["max_tokens"]
                if row.get("role") in (None, "perception"):
                    row["_history"] = inner.get("history")
            elif channel == "MODEL_RESPONSE":
                row["_text"] = payload["text"]
                row["completion_tokens"] = payload["usage"]["completion_tokens"]
            elif channel == "MODEL_WIRE_RESPONSE":
                row["finish_reason"] = payload["finish_reason"]
            elif channel == "USE" and rid.endswith("native-role-contact"):
                row["role"] = payload["use_role_id"]
        elif rid.endswith("/native-episode"):
            episodes.append(payload["use_native_episode"])
    return contacts, episodes


def run_dir(data_root: Path, run: str, attempt: str) -> Path:
    return data_root / "runs" / run / attempt


def note_features(text: str, direct_text: str | None) -> dict:
    tokens = words(text)
    six = grams(tokens, 6)
    repeat_share = 1 - len(set(six)) / len(six) if six else 0.0
    onset = period = None
    seen: set = set()
    for index, gram in enumerate(six):
        if gram in seen:
            onset = index
            break
        seen.add(gram)
    if six:
        top, count = Counter(six).most_common(1)[0]
        if count > 1:
            first_two = [i for i, g in enumerate(six) if g == top][:2]
            period = first_two[1] - first_two[0]
    lines = [line for line in text.splitlines() if line.strip()]
    ws_words = text.split()
    reemit = None
    if direct_text:
        window_four = set(grams(words(direct_text), 4))
        reemit = len(set(grams(tokens, 4)) & window_four) / len(window_four) if window_four else None
    if repeat_share >= LOOP_SHARE:
        mode = "LOOP"
    elif reemit is not None and reemit >= TRANSCRIPT_SHARE:
        mode = "TRANSCRIPT"
    elif len(lines) >= ENUMERATION_LINES:
        mode = "ENUMERATION"
    else:
        mode = "PROSE"
    max_line_words = max((len(line.split()) for line in lines), default=0)
    return {
        "words": len(tokens), "whitespace_words": len(ws_words), "lines": len(lines),
        "list_items": sum(1 for line in lines if ITEM.match(line)), "max_words_per_line": max_line_words,
        "repeat_share_6gram": round(repeat_share, 4), "loop_onset_word": onset, "loop_period_words": period,
        "window_transcript_4gram_reemission": None if reemit is None else round(reemit, 4), "mode": mode,
        "within_e41_bound": len(lines) <= BOUND["max_lines"] and max_line_words <= BOUND["max_words_per_line"],
    }


def trace_read(data_root: Path) -> dict:
    direct: dict[str, str] = {}
    direct_inputs = []
    for run, attempt in DIRECT_RUNS:
        path = run_dir(data_root, run, attempt) / f"{run}.trace.jsonl"
        contacts, _ = load_trace(path)
        for row in contacts.values():
            if row.get("packet") and "_text" in row:
                direct[row["packet"]] = row["_text"]
        direct_inputs.append({"run_id": run, "attempt": attempt, "trace_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    runs, all_notes, limits_objects = [], [], set()
    for label, run, attempt in SYSTEM_RUNS:
        path = run_dir(data_root, run, attempt) / f"{run}.trace.jsonl"
        contacts, episodes = load_trace(path)
        notes = []
        for fid in sorted(contacts):
            row = contacts[fid]
            if row.get("role") != "perception":
                continue
            history = row.get("_history") or []
            for turn in history:
                content = turn.get("content")
                if isinstance(content, str) and "Native episode limits: " in content:
                    envelope = json.loads(content)
                    for message in envelope.get("messages", []):
                        text = message.get("content", "")
                        if message.get("role") == "user" and LIMITS_PREFIX in text:
                            limits_objects.add(text.split(LIMITS_PREFIX, 1)[1])
            features = note_features(row["_text"], direct.get(row.get("packet")))
            ct = row["completion_tokens"]
            features.update({
                "flight_id": fid, "finish_reason": row["finish_reason"], "cap": row["max_tokens"],
                "completion_tokens": ct,
                "tokens_per_whitespace_word": round(ct / max(1, features["whitespace_words"]), 4),
                "direct_window_bound": row.get("packet") in direct,
            })
            notes.append(features)
        truncated = [n for n in notes if n["finish_reason"] == "length"]
        stopped = [n for n in notes if n["finish_reason"] != "length"]
        terminal = Counter(
            (e.get("terminal_disposition") or {}).get("role_id") or "none" for e in episodes
        )

        def block(group: list[dict]) -> dict:
            return {
                "count": len(group),
                "modes": dict(sorted(Counter(n["mode"] for n in group).items())),
                "completion_tokens": quantiles([n["completion_tokens"] for n in group]),
                "words": quantiles([n["words"] for n in group]),
                "lines": quantiles([n["lines"] for n in group]),
                "list_items": quantiles([n["list_items"] for n in group]),
                "repeat_share_6gram": quantiles([n["repeat_share_6gram"] for n in group]),
                "window_transcript_4gram_reemission": quantiles(
                    [n["window_transcript_4gram_reemission"] for n in group if n["window_transcript_4gram_reemission"] is not None]),
                "tokens_per_whitespace_word": quantiles([n["tokens_per_whitespace_word"] for n in group]),
                "within_e41_bound": sum(1 for n in group if n["within_e41_bound"]),
                "reemit_ge_half_window": sum(1 for n in group if (n["window_transcript_4gram_reemission"] or 0) >= TRANSCRIPT_SHARE),
            }

        loops = [n for n in truncated if n["mode"] == "LOOP"]
        runs.append({
            "label": label, "run_id": run, "attempt": attempt,
            "trace_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "perception_caps": dict(Counter(str(n["cap"]) for n in notes)),
            "windows": len(episodes), "perception_contacts": len(notes),
            "direct_window_bound": sum(1 for n in notes if n["direct_window_bound"]),
            "terminal_disposition_role_ids": dict(sorted(terminal.items())),
            "truncated": block(truncated), "stopped": block(stopped),
            "truncated_loops": {
                "count": len(loops),
                "loop_onset_word": quantiles([n["loop_onset_word"] for n in loops if n["loop_onset_word"] is not None]),
                "loop_period_words": quantiles([n["loop_period_words"] for n in loops if n["loop_period_words"] is not None]),
                "onset_within_100_words": sum(1 for n in loops if n["loop_onset_word"] is not None and n["loop_onset_word"] <= 100),
                "with_duplicate_lines_or_single_line": sum(1 for n in loops if n["lines"] <= 1 or n["list_items"] > 0),
            },
            "per_contact": [
                {key: n[key] for key in ("flight_id", "finish_reason", "cap", "completion_tokens", "words", "lines",
                                          "list_items", "max_words_per_line", "repeat_share_6gram", "loop_onset_word",
                                          "loop_period_words", "window_transcript_4gram_reemission", "mode", "within_e41_bound")}
                for n in notes
            ],
        })
        all_notes.extend(notes)

    truncated_all = [n for n in all_notes if n["finish_reason"] == "length"]
    tpw_all = [n["tokens_per_whitespace_word"] for n in all_notes]
    return {
        "direct_inputs": direct_inputs,
        "runs": runs,
        "limits_objects_seen": sorted(limits_objects),
        "pooled": {
            "perception_contacts": len(all_notes),
            "truncated": len(truncated_all),
            "truncated_modes": dict(sorted(Counter(n["mode"] for n in truncated_all).items())),
            "truncated_within_e41_bound": sum(1 for n in truncated_all if n["within_e41_bound"]),
            "tokens_per_whitespace_word": quantiles(tpw_all),
            "stopped_within_e41_bound": sum(1 for n in all_notes if n["finish_reason"] != "length" and n["within_e41_bound"]),
            "stopped": sum(1 for n in all_notes if n["finish_reason"] != "length"),
        },
    }


class Tokenizer:
    """The local llama.cpp tokenizer: one vocab-only process per distinct text."""

    def __init__(self, binary: Path, model: Path, scratch: Path) -> None:
        self.binary, self.model, self.scratch = binary, model, scratch
        self.cache: dict[str, int] = {}
        self.invocations = 0

    def count(self, text: str, label: str) -> int:
        key = sha_text(text)
        if key in self.cache:
            return self.cache[key]
        self.scratch.mkdir(parents=True, exist_ok=True)
        path = self.scratch / f"{label}.txt"
        path.write_bytes(text.encode("utf-8"))
        argv = [str(self.binary), "-m", str(self.model), "-f", str(path), "--no-bos",
                "--no-escape", "--show-count", "--log-disable", "--ids"]
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.invocations += 1
        path.unlink()
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                self.cache[key] = int(line.split(":")[1].strip())
                return self.cache[key]
        raise RuntimeError(f"local tokenizer produced no count for {label}")


def synthetic_notes() -> dict[str, str]:
    """Compliant notes built from the v2 form alone (no speech): typical and digit-dense worst case."""

    typical = "\n".join([
        "1. NAME near 12 s: Kaplan or Caplan",
        "2. NUMBER near 37 s: fifteen percent or fifty percent",
        "3. BOUNDARY near 55 s: in sight or insight",
        "4. MISSING near 71 s: and the or and",
        "5. NAME near 84 s: Northwind Holdings or North Wind Holdings",
    ])
    dense_reading = "1,234,567.89 9,876,543.21 5,432,109.87 6,789,012.34"
    worst = "\n".join(
        f"{i}. NUMBER near 8{i} s: {dense_reading} or {dense_reading}" for i in range(1, 6)
    )
    return {"typical_compliant_note": typical, "digit_dense_worst_case_compliant_note": worst}


def token_measurement(repo: Path, data_root: Path, tokenize: Path, scratch: Path, limits_objects: list[str],
                      trace: dict) -> dict:
    model = data_root / GGUF_RELPATH
    tokenizer = Tokenizer(tokenize, model, scratch)
    old = io.open(repo / OLD_PROBE, encoding="utf-8", newline="").read()
    new = io.open(repo / NEW_PROBE, encoding="utf-8", newline="").read()
    limits = limits_objects[0] if limits_objects else "{}"
    counts = {
        "old_instruction": tokenizer.count(old, "old"),
        "new_instruction": tokenizer.count(new, "new"),
        "old_as_wire_user_turn": tokenizer.count(old + LIMITS_PREFIX + limits, "old-wire"),
        "new_as_wire_user_turn": tokenizer.count(new + LIMITS_PREFIX + limits, "new-wire"),
    }
    notes = synthetic_notes()
    note_counts = {}
    for name, text in notes.items():
        lines = text.splitlines()
        note_counts[name] = {
            "tokens": tokenizer.count(text, name), "lines": len(lines),
            "max_words_per_line": max(len(line.split()) for line in lines), "sha256": sha_text(text),
        }
    delta = counts["new_as_wire_user_turn"] - counts["old_as_wire_user_turn"]
    sub10_perception = next(r for r in trace["runs"] if r["label"] == "E35-sub10")["perception_contacts"]
    tpw_max = trace["pooled"]["tokens_per_whitespace_word"]["max"]
    ratio_bound = BOUND["max_lines"] * BOUND["max_words_per_line"] * tpw_max
    worst = note_counts["digit_dense_worst_case_compliant_note"]["tokens"]
    return {
        "tokenizer": {"binary": str(tokenize), "model_relpath": GGUF_RELPATH,
                      "argv_shape": "-m <gguf> -f <file> --no-bos --no-escape --show-count --log-disable --ids",
                      "invocations": tokenizer.invocations, "mode": "vocab-only local process: no server, no port, no GPU"},
        "instruction_files": {
            "old": {"relpath": OLD_PROBE, "sha256": hashlib.sha256((repo / OLD_PROBE).read_bytes()).hexdigest(), "bytes": len(old.encode())},
            "new": {"relpath": NEW_PROBE, "sha256": hashlib.sha256((repo / NEW_PROBE).read_bytes()).hexdigest(), "bytes": len(new.encode())},
        },
        "limits_object_sha256": sha_text(limits),
        "prompt_side_tokens": counts,
        "prompt_side_delta_per_perception_contact": delta,
        "prompt_side_delta_per_flight": {"four_row_dry_run": delta * 4, "sub10_re_read": delta * sub10_perception,
                                         "note": "one Perception contact per window (role_max_iterations 1); the instruction is sent once, as the last text part of that contact's user turn"},
        "completion_side_bound": {
            "bound": BOUND,
            "synthetic_compliant_notes": note_counts,
            "ratio_bound_tokens": round(ratio_bound, 1),
            "ratio_bound_derivation": f"{BOUND['max_lines']} lines x {BOUND['max_words_per_line']} words x {tpw_max} tokens per whitespace word (the MAXIMUM observed over every sealed Perception note of this carrier)",
            "cap": 640, "worst_case_headroom_tokens": 640 - worst,
            "note": "the digit-dense worst case fills every reading with four 12-character numerals (one token per digit or separator on this vocabulary); a note that obeys the v2 form cannot exceed the cap, so any length-truncated contact under v2 is a NON-compliant note by construction, which the dry run's R3 counts",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--repo-root", default=REPO_ROOT, type=Path)
    parser.add_argument("--tokens", action="store_true", help="run the vocab-only tokenizer measurement")
    parser.add_argument("--tokenize-binary", default=DEFAULT_TOKENIZE, type=Path)
    parser.add_argument("--scratch", default=Path("/tmp/saea-e41-tokenize"), type=Path)
    parser.add_argument("--write", action="store_true", help="write the receipts into the E41 package")
    args = parser.parse_args()
    repo, data_root = args.repo_root.resolve(), args.data_root
    now = datetime.now(timezone.utc).isoformat()
    trace = trace_read(data_root)
    boundary = ("No utterance, transcript, reference, gold or model output text is printed or persisted: the receipt "
                "holds counts, rates, ids and hashes; note text is held in memory for the counts and dropped.")
    receipt = {
        "schema": "saea-e41-perception-trace-read-v1", "item": "E41 (owner decisions 103, 158)",
        "measured_at_utc": now, "boundary": boundary, "mode_rule": MODE_RULE, "e41_bound": BOUND,
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0, "network": 0, "gpu": 0,
                     "paid_api": 0, "tokenizer_process_vocab_only": 0},
        **trace,
    }
    receipt.pop("limits_objects_seen")
    receipt["limits_objects_seen"] = len(trace["limits_objects_seen"])
    outputs = {TRACE_RECEIPT: receipt}
    if args.tokens:
        tokens = token_measurement(repo, data_root, args.tokenize_binary, args.scratch,
                                   trace["limits_objects_seen"], trace)
        outputs[TOKEN_RECEIPT] = {
            "schema": "saea-e41-instruction-token-measurement-v1", "item": "E41 (owner decisions 103, 158)",
            "measured_at_utc": now, "boundary": boundary.replace("note text", "synthetic note text"),
            "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0, "network": 0, "gpu": 0,
                         "paid_api": 0, "tokenizer_process_vocab_only": tokens["tokenizer"]["invocations"]},
            **tokens,
        }
    for name, document in outputs.items():
        text = json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
        if args.write:
            target = repo / PACKAGE / name
            target.parent.mkdir(parents=True, exist_ok=True)
            io.open(target, "w", encoding="utf-8", newline="\n").write(text)
            print(f"wrote {target.relative_to(repo).as_posix()} sha256 {sha_text(text)}")
    summary = {"pooled": trace["pooled"], "per_run": [
        {"label": r["label"], "caps": r["perception_caps"], "contacts": r["perception_contacts"],
         "truncated": r["truncated"]["count"], "truncated_modes": r["truncated"]["modes"],
         "stopped_within_bound": r["stopped"]["within_e41_bound"], "loops": r["truncated_loops"]["count"],
         "loop_onset_within_100": r["truncated_loops"]["onset_within_100_words"]} for r in trace["runs"]]}
    if TOKEN_RECEIPT in outputs:
        t = outputs[TOKEN_RECEIPT]
        summary["tokens"] = {"prompt": t["prompt_side_tokens"], "delta": t["prompt_side_delta_per_perception_contact"],
                             "synthetic": {k: v["tokens"] for k, v in t["completion_side_bound"]["synthetic_compliant_notes"].items()},
                             "ratio_bound": t["completion_side_bound"]["ratio_bound_tokens"]}
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
