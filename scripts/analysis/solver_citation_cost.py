#!/usr/bin/env python3
"""Price the Solver's cited-answer contract on the pinned vocab, model-free.

Gap G1 plumbing (``rails.solver_citation``). The audit that named the gap
(``docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md``)
priced a citation at about 11.6 tokens per id from the labels already on the
wire. This script measures the ACTUAL contract on the Fold A rows the locked
plan flew:

* the INSTRUCTION side: the token delta between the committed cited Solver
  template and the locked plan's own Solver template. The Solver template is
  static (no fill), and the appended ``Native episode limits`` control is
  identical under both, so the delta is one number for every row;
* the OUTPUT side: the token cost of the envelope skeleton the model must
  emit around its answer, and the per-id cost measured on the ids each Fold A
  Solver contact was actually shown (read off the sealed PLAN trace's
  ``MODEL_REQUEST`` payloads), from which the design floor (one intent id,
  one entity with one id) and the contract cap (3 + 6 x 3 ids) follow.

Tokens come from the local ``llama-tokenize`` binary loading the pinned GGUF
vocab in a local process -- no server, no port, no GPU, no encoder, no
scorer, zero model contacts. Ids, counts, token counts and hashes only: no
utterance, transcript, gold label, knowledge body, model output or rendered
instruction is printed or persisted, and the trace's texts are never
retained past the id extraction.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DEFAULT_DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
DEFAULT_TOKENIZE = Path("/home/chao/llama.cpp/build/bin/llama-tokenize")
GGUF_RELPATH = (
    "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf"
)
PRIMARY_RUN = "SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1"
BASE_TEMPLATE = "probes/slurp_native_role_solver_v2.txt"
CITED_TEMPLATE = "probes/slurp_native_role_solver_cited_v1.txt"
SOLVER_ROLE = "solver"
WORKERS = 4

#: The envelope with an EMPTY answer and no citation: the fixed output
#: overhead of the contract over the bare answer.
SKELETON = '{"schema":"saea-solver-cited-answer-v1","answer":{},"citations":{"intent":[],"entities":[]}}'
BARE = "{}"
#: One entity citation entry with no id; the type is a placeholder of the
#: shortest SLURP slot-type shape, priced separately from the ids.
ENTITY_ENTRY = '{"type":"date","evidence_ids":[]}'


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Tokenizer:
    def __init__(self, binary: Path, gguf: Path, scratch: Path) -> None:
        self.binary, self.gguf, self.scratch = binary, gguf, scratch
        self.calls = 0

    def count(self, text: str, label: str) -> int:
        self.scratch.mkdir(parents=True, exist_ok=True)
        path = self.scratch / (label + ".txt")
        path.write_bytes(text.encode("utf-8"))
        argv = [
            str(self.binary), "-m", str(self.gguf), "-f", str(path), "--no-bos",
            "--no-escape", "--show-count", "--log-disable", "--ids",
        ]
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.calls += 1
        path.unlink()
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                return int(line.split(":")[1].strip())
        raise RuntimeError("local tokenizer produced no count for " + label)


def measure(
    jobs: dict[str, str], tokenizer: Tokenizer, cache_path: Path | None, *, workers: int = WORKERS,
) -> dict[str, int]:
    cached: dict[str, int] = {}
    if cache_path is not None and cache_path.exists():
        cached = {k: int(v) for k, v in json.loads(cache_path.read_text(encoding="utf-8")).items()}
    keys = sorted(key for key in jobs if key not in cached)
    with ThreadPoolExecutor(max_workers=max(1, min(WORKERS, workers))) as pool:
        counts = list(pool.map(lambda key: tokenizer.count(jobs[key], key[:24]), keys))
    cached.update(zip(keys, counts))
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cached, indent=0, sort_keys=True), encoding="utf-8")
    return {key: cached[key] for key in jobs}


def solver_supplied_ids(trace: Path) -> dict[str, list[str]]:
    """``{sample_id: evidence ids}`` of each row's FIRST Solver contact.

    Only the ``evidence_id`` fields are kept; every text in the payload is
    dropped as soon as the line is parsed.
    """

    roles, ids_by_flight, samples = {}, {}, {}
    wanted = ('"MODEL_REQUEST"', 'native-role-contact"')
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            if not any(token in line for token in wanted):
                continue
            record = json.loads(line)
            channel, record_id = record["channel"], record["record_id"]
            flight = record_id.split("/")[0]
            if channel == "MODEL_REQUEST":
                payload = record["payload"]["payload"]
                samples[flight] = payload["sample_id"]
                ids_by_flight[flight] = [
                    item["evidence_id"]
                    for field in ("supplied_evidence", "retrieved_evidence")
                    for item in payload.get(field, [])
                ]
            elif channel == "USE" and record_id.endswith("native-role-contact"):
                roles[flight] = record["payload"]["use_role_id"]
    per_sample: dict[str, list[str]] = {}
    for flight in sorted(ids_by_flight, key=lambda name: int(name.split("-")[1])):
        if roles.get(flight) != SOLVER_ROLE:
            continue
        per_sample.setdefault(samples[flight], ids_by_flight[flight])
    return per_sample


def stats(values):
    ordered = sorted(values)
    if not ordered:
        return {"n": 0}
    def pct(p):
        return ordered[min(len(ordered) - 1, int(round(p * (len(ordered) - 1))))]
    return {
        "n": len(ordered), "mean": round(statistics.fmean(ordered), 2),
        "p50": pct(0.5), "p90": pct(0.9), "max": ordered[-1], "min": ordered[0],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--tokenize", type=Path, default=DEFAULT_TOKENIZE)
    parser.add_argument("--run-id", default=PRIMARY_RUN)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--workers", type=int, default=WORKERS, help="at most %d" % WORKERS)
    args = parser.parse_args(argv)

    repo, data = args.repo_root.resolve(), args.data_root
    gguf = data / GGUF_RELPATH
    base = (repo / "configs" / BASE_TEMPLATE).read_text(encoding="utf-8")
    cited = (repo / "configs" / CITED_TEMPLATE).read_text(encoding="utf-8")
    traces = sorted((data / "runs" / args.run_id).glob("*/" + args.run_id + ".trace.jsonl"))
    if not traces:
        print("no sealed trace for " + args.run_id, file=sys.stderr)
        return 2
    per_sample = solver_supplied_ids(traces[0])

    jobs: dict[str, str] = {}
    def job(text: str) -> str:
        key = sha(text)
        jobs[key] = text
        return key

    base_key, cited_key = job(base), job(cited)
    skeleton_key, bare_key, entity_key = job(SKELETON), job(BARE), job(ENTITY_ENTRY)
    row_keys = {sample: job(json.dumps(ids)) for sample, ids in per_sample.items() if ids}
    tokenizer = Tokenizer(args.tokenize, gguf, args.scratch)
    counts = measure(jobs, tokenizer, args.cache, workers=args.workers)

    per_id = []
    all_ids_bound = []
    id_counts = []
    for sample, key in row_keys.items():
        n = len(per_sample[sample])
        tokens = counts[key]
        id_counts.append(n)
        all_ids_bound.append(tokens)
        per_id.append(tokens / n)
    id_tokens = statistics.fmean(per_id) if per_id else 0.0
    skeleton_tokens = counts[skeleton_key] - counts[bare_key]
    entity_tokens = counts[entity_key]
    floor_tokens = skeleton_tokens + entity_tokens + 2 * id_tokens
    cap_tokens = skeleton_tokens + 6 * entity_tokens + 21 * id_tokens

    report = {
        "schema": "saea-solver-citation-cost-v1",
        "contact_class": "model-free",
        "contacts": {"model": 0, "server": 0, "gpu": 0, "encoder": 0, "scorer": 0, "network": 0},
        "tokenizer": {
            "binary": str(args.tokenize), "vocab_gguf_relpath": GGUF_RELPATH,
            "invocations": tokenizer.calls, "distinct_texts": len(jobs),
        },
        "source": {
            "run_id": args.run_id,
            "trace_relpath": str(traces[0].relative_to(data)),
            "solver_rows": len(per_sample),
            "solver_rows_with_evidence": len(row_keys),
        },
        "instruction": {
            "base_template": BASE_TEMPLATE, "base_sha256": sha(base), "base_tokens": counts[base_key],
            "cited_template": CITED_TEMPLATE, "cited_sha256": sha(cited), "cited_tokens": counts[cited_key],
            "added_tokens_per_solver_contact": counts[cited_key] - counts[base_key],
            "note": "static per phase (no instruction_fill); the appended episode-limits control is identical under both templates, so this delta holds on every Fold A row",
        },
        "output": {
            "skeleton_tokens_over_bare_answer": skeleton_tokens,
            "entity_entry_tokens_without_ids": entity_tokens,
            "supplied_ids_per_solver_row": stats(id_counts),
            "tokens_per_supplied_id": {
                "mean": round(id_tokens, 2),
                "per_row_mean_distribution": stats([round(v, 2) for v in per_id]),
                "how": "tokens of the JSON array of a row's supplied ids divided by its id count",
            },
            "all_supplied_ids_cited_bound_tokens": stats(all_ids_bound),
            "design_floor_tokens": {
                "shape": "skeleton + one entity entry + 1 intent id + 1 entity id",
                "tokens": round(floor_tokens, 1),
            },
            "contract_cap_tokens": {
                "shape": "skeleton + 6 entity entries + (3 + 6 x 3) ids",
                "tokens": round(cap_tokens, 1),
            },
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "instruction_added_tokens": report["instruction"]["added_tokens_per_solver_contact"],
        "skeleton_tokens": skeleton_tokens,
        "tokens_per_id_mean": round(id_tokens, 2),
        "floor_tokens": round(floor_tokens, 1),
        "cap_tokens": round(cap_tokens, 1),
        "rows": len(row_keys),
        "invocations": tokenizer.calls,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
