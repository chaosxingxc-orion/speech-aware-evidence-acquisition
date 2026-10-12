#!/usr/bin/env python3
"""NX R0.3: root cause of the Solver's unparsed first drafts on the N100 simple-consumption family (zero GPU).

Programme ``docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`` (B W3, C2 R0.3).  The N100 family
(``docs/results/2026-10-08-simple-consumption-n100-complete-family.md``) reports a first raw Solver parse of
87/100 (seed), 90/100 (seed A/A) and 100/100 (review-off, solver-lookup).  This read compares, from the sealed
trace bytes only, the REQUEST structure of every role contact (decoding parameters, response_format,
tool_choice, tool schemas, history, control-message length, server-counted prompt tokens) and the structural
features of every unparsed first Solver draft (finish reason, completion tokens, leading character, code fences,
``<tool_call>`` tags, the called tool's name and argument KEYS, whether any text after the tag parses).

"First raw parse" is the member reader's definition (``analysis.slurp_solver_stage_attribution``):
``parse_slu_response`` on the response text of the row's first Solver contact.

Text discipline: no utterance text, transcript, gold value, model output text or instruction text is printed or
persisted -- only counts, lengths, hashes, key names, tool names and enum values.  Gold is not read.  Zero
model, server, tokenizer, scorer, network and GPU contacts.  Deterministic apart from ``generated_at``;
``--check`` re-derives and compares.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_solver_parse_root_cause.py \\
        --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations
import os

import argparse
import difflib
import hashlib
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-NX-SOLVER-PARSE-ROOT-CAUSE-V1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
TAG = "<tool_call>"
CLOSE = "</tool_call>"


def member(name: str) -> dict:
    up = name.upper()
    return {"label": name, "run_id": f"SAEA-SLURP-SIMPLE-CONSUMPTION-{up}-N100-AUDIO-RECOVERY1-ENTRY2-V1",
            "attempt": f"attempt-slurp-native-stage3-simple-consumption-{name}-n100-audio-recovery1-entry2-v1-generation"}


MEMBERS = tuple(member(m) for m in ("seed", "seed-aa", "review-off", "solver-lookup"))
PAIR = ("seed", "review-off")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_trace(path: Path) -> dict:
    reqs, resp, wire = {}, {}, {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            rec = json.loads(line)
            ch, rid = rec.get("channel"), rec["record_id"].split("/")[0]
            if ch == "MODEL_REQUEST":
                reqs[rid] = rec["payload"]["payload"]
            elif ch == "MODEL_RESPONSE":
                resp[rid] = rec["payload"]
            elif ch == "MODEL_WIRE_RESPONSE":
                wire[rid] = rec["payload"]
    order = sorted(reqs, key=lambda r: int(r.rsplit("-", 1)[-1]))
    return {"reqs": reqs, "resp": resp, "wire": wire, "order": order}


def role_of(payload: dict) -> str:
    return str(payload.get("key_representation_id") or "").rsplit(":", 1)[-1]


def contacts_by_role(tr: dict, role: str) -> dict:
    out = {}
    for rid in tr["order"]:
        pl = tr["reqs"][rid]
        if role_of(pl) == role:
            out.setdefault(pl["sample_id"], []).append(rid)
    return out


def control_len(pl: dict) -> int:
    return sum(len(h.get("content") or "") for h in pl.get("history") or () if h.get("role") == "control")


def dist(values) -> dict:
    return dict(sorted(Counter(str(v) for v in values).items()))


def mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return round(statistics.fmean(values), 2) if values else None


def request_profile(tr: dict) -> dict:
    out = {}
    roles = sorted({role_of(tr["reqs"][r]) for r in tr["order"]})
    for role in roles:
        rids = [r for r in tr["order"] if role_of(tr["reqs"][r]) == role]
        pls = [tr["reqs"][r] for r in rids]
        rf = [(p.get("decoding_params") or {}).get("response_format") for p in pls]
        out[role] = {
            "contacts": len(rids),
            "request_field_sets": dist(tuple(sorted(p.keys())) == tuple(sorted(pls[0].keys())) for p in pls),
            "response_format": dist(x.get("type") if isinstance(x, dict) else x for x in rf),
            "tool_choice": dist((p.get("decoding_params") or {}).get("tool_choice") for p in pls),
            "max_tokens": dist((p.get("decoding_params") or {}).get("max_tokens") for p in pls),
            "temperature": dist((p.get("decoding_params") or {}).get("temperature") for p in pls),
            "tool_schemas": dist(len(p.get("tool_schemas") or ()) for p in pls),
            "tool_names": dist(tuple(sorted(str((t.get("function") or t).get("name")) for t in p.get("tool_schemas") or ()))
                               for p in pls),
            "tool_schema_json_chars": dist(len(json.dumps(p.get("tool_schemas") or [], sort_keys=True)) for p in pls),
            "task_instruction_sha256_12": dist(hashlib.sha256((p.get("task_instruction") or "").encode()).hexdigest()[:12]
                                               for p in pls),
            "history_kinds": dist(tuple(h.get("state_kind") or h.get("role") for h in p.get("history") or ())
                                  for p in pls),
            "control_message_chars_mean": mean(control_len(p) for p in pls),
            "supplied_items_mean": mean(len(p.get("supplied_evidence") or ()) for p in pls),
            "prompt_tokens_mean": mean(tr["resp"][r]["usage"].get("prompt_tokens") for r in rids),
            "completion_tokens_mean": mean(tr["resp"][r]["usage"].get("completion_tokens") for r in rids),
            "finish_reason": dist(tr["wire"].get(r, {}).get("finish_reason") for r in rids),
            "responses_with_tool_call_tag": sum(TAG in (tr["resp"][r].get("text") or "") for r in rids),
        }
    return out


def solver_drafts(tr: dict) -> dict:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    by_sid = contacts_by_role(tr, "solver")
    first = Counter()
    fail = Counter()
    visits = Counter()
    for sid, rids in by_sid.items():
        for i, rid in enumerate(rids):
            text = tr["resp"][rid].get("text") or ""
            visits[("first" if i == 0 else "revision", "parsed", parse_slu_response(text)[3],
                    "tool_call_tag", TAG in text)] += 1
        rid = rids[0]
        text = tr["resp"][rid].get("text") or ""
        parsed = parse_slu_response(text)[3]
        first["parsed" if parsed else "unparsed"] += 1
        if parsed:
            continue
        stripped = text.lstrip()
        usage = tr["resp"][rid].get("usage") or {}
        ct = usage.get("completion_tokens") or 0
        fail["finish_reason=" + str(tr["wire"].get(rid, {}).get("finish_reason"))] += 1
        fail["completion_tokens_bucket=" + ("<50" if ct < 50 else "<100" if ct < 100 else "<200" if ct < 200
                                            else "<512" if ct < 512 else ">=512 (cap)")] += 1
        fail["leading_char=" + (stripped[:1] if stripped[:1] in "{[`<" else "alpha" if stripped[:1].isalpha()
                                else "other")] += 1
        fail["code_fence=" + str("```" in text)] += 1
        fail["tool_call_tag=" + str(TAG in text)] += 1
        fail["text_before_tag_nonblank=" + str(bool(text.split(TAG, 1)[0].strip()) if TAG in text else None)] += 1
        fail["closing_tag=" + str(CLOSE in text)] += 1
        after = text.split(CLOSE, 1)[1] if CLOSE in text else ""
        fail["text_after_close_nonblank=" + str(bool(after.strip()))] += 1
        fail["text_after_close_parses=" + str(parse_slu_response(after)[3] if after.strip() else None)] += 1
        m = re.search(re.escape(TAG) + r"(.*?)(" + re.escape(CLOSE) + r"|$)", text, re.S)
        body = m.group(1).strip() if m else ""
        try:
            obj = json.loads(body)
            name = str(obj.get("name"))
            visible = [str((t.get("function") or t).get("name")) for t in tr["reqs"][rid].get("tool_schemas") or ()]
            fail["called_tool_rendered_in_request=" + str(name in visible)] += 1
            fail["called_tool=" + name] += 1
            fail["argument_keys=" + ",".join(sorted((obj.get("arguments") or {}).keys()))] += 1
        except (ValueError, AttributeError):
            fail["tool_call_body_json=False"] += 1
        fail["revised_later=" + str(len(rids) > 1)] += 1
        fail["last_solver_draft_parses=" + str(parse_slu_response(tr["resp"][rids[-1]].get("text") or "")[3])] += 1
        del text
    return {"first_draft": dict(sorted(first.items())), "unparsed_first_draft_features": dict(sorted(fail.items())),
            "visits": {" | ".join(str(x) for x in k): v for k, v in sorted(visits.items(), key=str)}}


def paired(a: dict, b: dict) -> dict:
    """Seed vs review-off on the same 100 inputs: what differs in the Perception and first-Solver requests."""
    out = {}
    for role in ("perception", "solver"):
        A, B = contacts_by_role(a, role), contacts_by_role(b, role)
        c = Counter()
        ops = Counter()
        tok = []
        for sid in sorted(set(A) & set(B)):
            pa, pb = a["reqs"][A[sid][0]], b["reqs"][B[sid][0]]
            for key in sorted(set(pa) | set(pb)):
                if key in ("request_id", "key_representation_id", "matcher_policy_id", "evidence_provenance"):
                    continue
                va, vb = pa.get(key), pb.get(key)
                if key == "decoding_params":
                    va = {k: v for k, v in (va or {}).items() if k != "id_slot"}
                    vb = {k: v for k, v in (vb or {}).items() if k != "id_slot"}
                c[f"{key}_equal={va == vb}"] += 1
            ca = "".join(h.get("content") or "" for h in pa.get("history") or () if h.get("role") == "control")
            cb = "".join(h.get("content") or "" for h in pb.get("history") or () if h.get("role") == "control")
            sm = difflib.SequenceMatcher(None, cb, ca, autojunk=False)
            changed = tuple((t, i2 - i1, j2 - j1) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal")
            ops[json.dumps(changed)] += 1
            c[f"response_text_equal={a['resp'][A[sid][0]].get('text') == b['resp'][B[sid][0]].get('text')}"] += 1
            tok.append(a["resp"][A[sid][0]]["usage"]["prompt_tokens"] - b["resp"][B[sid][0]]["usage"]["prompt_tokens"])
        out[role] = {"rows": len(set(A) & set(B)), "field_equality": dict(sorted(c.items())),
                     "control_message_diff_shapes": {"distinct": len(ops),
                                                     "chars_removed_added": [[sum(x[1] for x in json.loads(k)),
                                                                              sum(x[2] for x in json.loads(k)), v]
                                                                             for k, v in ops.items()]},
                     "prompt_token_delta_seed_minus_review_off": dist(tok) if len(set(tok)) <= 3 else
                     {"mean": mean(tok), "min": min(tok), "max": max(tok)}}
    return out


def build(args) -> dict:
    data_root = Path(args.data_root)
    traces, members = {}, {}
    for m in MEMBERS:
        path = data_root / "runs" / m["run_id"] / m["attempt"] / f"{m['run_id']}.trace.jsonl"
        tr = load_trace(path)
        traces[m["label"]] = tr
        members[m["label"]] = {"run_id": m["run_id"], "attempt": m["attempt"],
                               "trace": [str(path.relative_to(data_root)), digest(path)],
                               "requests": request_profile(tr), "solver": solver_drafts(tr)}
    return {"read_id": READ_ID, "status": "DESCRIPTIVE",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "contacts": {"model": 0, "server": 0, "tokenizer": 0, "scorer": 0, "network": 0, "gpu": 0},
            "gold_read": False, "members": members,
            "paired_seed_vs_review_off": paired(traces[PAIR[0]], traces[PAIR[1]])}


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    report = build(args)
    out_dir = Path(args.data_root) / ANALYSIS_DIR
    text = json.dumps(report, indent=1, sort_keys=True) + "\n"
    if args.check:
        same = strip_time((out_dir / "report.json").read_text(encoding="utf-8")) == strip_time(text)
        print("check:", "IDENTICAL apart from generated_at" if same else "DIFFERS")
        return 0 if same else 1
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(text, encoding="utf-8", newline="\n")
    sha = hashlib.sha256(strip_time(text).encode("utf-8")).hexdigest()
    (out_dir / "content-sha256.json").write_text(json.dumps({"report.json": sha}, indent=2) + "\n",
                                                 encoding="utf-8", newline="\n")
    print("wrote", out_dir, sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
