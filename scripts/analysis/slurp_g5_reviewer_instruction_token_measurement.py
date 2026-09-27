#!/usr/bin/env python3
"""slurp_g5_reviewer_instruction_token_measurement.py -- item G5: the Reviewer
instruction that orders a retired tool, measured and repaired.

WHAT IT MEASURES. ``docs/results/2026-09-26-slurp-reviewer-planner-global-state-
audit.md`` (G5) found that the locked PLAN plan's Reviewer instruction opens by
ordering the Reviewer to call a task-contract tool that was RETIRED as item E25
(``docs/receipts/harness-admission.json``, the ``phase_tools.reviewer`` entry
with status ``RETIRED``, after ``docs/results/2026-09-20-slurp-b1-notool-
verdict.md``), and priced the stale order at 52 of the instruction's 82 tokens
(63 %). Owner decisions 135 and 153 (``docs/readiness/2026-09-16-slurp-next-
stage-owner-decisions-v1.md``) deferred and then admitted its repair as a
row-127 no-harm item for round 3. This script:

1. RESOLVES the Reviewer node's instruction file from the locked PLAN cell's
   composed config (``core.config.compose``) and lists every composed path
   that names it, plus every committed fragment under ``configs/`` that pins
   the same file -- so the reader sees exactly what the one pin moves;
2. REPRODUCES the audit's measurement with the audit's own tokenizer and
   split: the local ``llama-tokenize`` binary loading the pinned GGUF vocab in
   a local process (``--no-bos --no-escape --show-count --log-disable
   --ids``, exactly ``scripts/analysis/slurp_reviewer_planner_global_state_
   audit.py``), the instruction partitioned at ``"Then review"`` into the
   retired-tool order and the review order;
3. WRITES (``--write-repaired``) or VERIFIES the repaired instruction
   ``configs/probes/slurp_native_role_reviewer_v1_g5_v1.txt`` -- the review
   order alone, byte for byte: every clause that orders, describes or depends
   on the retired tool deleted and NOTHING added -- and PROVES the edit is
   deletion-only at word level (``difflib`` opcodes: ``equal`` and ``delete``
   only) and at byte level (old == deleted head + new);
4. READS the sealed PLAN arm's Reviewer contact rate from its own phase
   summaries (``native_episode_receipt.role_visits``) and cross-checks the
   visit total against the sealed run manifest's ``cost.calls_used``, so the
   per-row saving is a sealed fact times a measured delta;
5. writes one receipt (``instruction-token-measurement-v1.json``) under the
   G5 readiness package: hashes, counts, token counts and the deleted clause
   -- the committed instruction's own words, never an utterance, a
   transcript, a gold label or a model output.

MODEL-FREE. Zero model, server, encoder, embedder, scorer, network, GPU and
paid-API contacts; port 8080 is never touched. The only process it starts is
the vocab-only tokenizer, and the receipt counts its invocations.

    python scripts/analysis/slurp_g5_reviewer_instruction_token_measurement.py \\
        --data-root "$SPEECHRL_DATA_DIR" --write-repaired
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import io
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402

PARENT_EXPERIMENT = "slurp-native-default-plan-lock-v1"
PARENT_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
PARENT_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
ROLL2_RUN = "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1"
ROLL2_ATTEMPT = "attempt-slurp-native-stage3-roll-2-fold-a-v1-generation"

OLD_RELPATH = "probes/slurp_native_role_reviewer_v1.txt"
NEW_RELPATH = "probes/slurp_native_role_reviewer_v1_g5_v1.txt"
COMPOSED_PATH = "phase_material.reviewer.instruction_template"

#: The audit's own split marker: everything before it is the order to call the
#: retired task-contract tool, everything from it on is the order to review.
SPLIT_MARKER = "Then review"

#: The audit's own tokenizer, argv for argv.
DEFAULT_TOKENIZE = Path("/home/chao/llama.cpp/build/bin/llama-tokenize")
GGUF_RELPATH = (
    "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/"
    "Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf"
)

AUDIT_NOTE = "docs/results/2026-09-26-slurp-reviewer-planner-global-state-audit.md"
AUDIT_SCRIPT = "scripts/analysis/slurp_reviewer_planner_global_state_audit.py"
AUDIT_WHOLE, AUDIT_HEAD = 82, 52

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1"
RECEIPT_NAME = "instruction-token-measurement-v1.json"


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rd(path: Path) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


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
        argv = [
            str(self.binary), "-m", str(self.model), "-f", str(path), "--no-bos",
            "--no-escape", "--show-count", "--log-disable", "--ids",
        ]
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.invocations += 1
        path.unlink()
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                count = int(line.split(":")[1].strip())
                self.cache[key] = count
                return count
        raise RuntimeError(f"local tokenizer produced no count for {label}")


def walk(node, prefix=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, f"{prefix}.{key}" if prefix else str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, f"{prefix}[{index}]")
    else:
        yield prefix, node


def resolve_instruction(repo: Path) -> dict:
    """The Reviewer node's instruction file, from the locked PLAN cell's composed config."""

    document = json.loads(rd(repo / "configs" / "experiment" / f"{PARENT_EXPERIMENT}.json"))
    cell = document["cells"][0]
    composed = compose(repo, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], PARENT_EXPERIMENT)
    naming = sorted(path for path, value in walk(composed.values) if value == OLD_RELPATH)
    if naming != [COMPOSED_PATH]:
        raise SystemExit(f"the locked PLAN composed config names {OLD_RELPATH} at {naming}, expected [{COMPOSED_PATH}]")
    reviewer = composed.values["phase_material"]["reviewer"]
    fragments_pinning = sorted(
        str(path.relative_to(repo)).replace("\\", "/")
        for path in (repo / "configs").rglob("*.json")
        if OLD_RELPATH in rd(path)
    )
    carriers = {
        kind: name for kind, name in composed.fragments.items()
        if OLD_RELPATH in rd(repo / "configs" / kind / f"{name}.json")
    }
    return {
        "parent_cell": {
            "experiment": PARENT_EXPERIMENT, "run_id": PARENT_RUN,
            "composed_config_hash": composed.config_hash, "fragments": dict(composed.fragments),
        },
        "composed_paths_naming_the_file": naming,
        "reviewer_phase_material_as_composed": {
            key: reviewer[key] for key in sorted(reviewer)
        },
        "fragment_of_the_locked_cell_that_carries_the_pin": carriers,
        "committed_fragments_pinning_the_same_file": {
            "count": len(fragments_pinning), "relpaths": fragments_pinning,
        },
        "how_the_bytes_reach_the_wire": [
            "rails/phase_material.py::load_phase_material_specs reads the template under configs/ by the relpath above (text bytes, verbatim)",
            "rails/runner.py:2559 appends '\\n\\nNative episode limits: ' + json(limits) to the instruction and sends it as the role query",
            "core/model/native_framework_history.py:313-317 renders the role query as the LAST text part of the user turn, once per contact of this role",
            "the control record history[-1] re-embeds the same bytes in the sealed framework envelope (custody only, never sent), so the deletion shrinks the sealed record by the same amount",
        ],
    }


def deletion_only_proof(old: str, new: str) -> dict:
    """Word-level and byte-level proof that ``new`` is ``old`` minus deletions."""

    old_words, new_words = old.split(), new.split()
    matcher = difflib.SequenceMatcher(a=old_words, b=new_words, autojunk=False)
    opcodes = [(tag, i1, i2, j1, j2) for tag, i1, i2, j1, j2 in matcher.get_opcodes()]
    kinds = Counter(tag for tag, *_ in opcodes)
    deleted_spans = [
        {"old_word_range": [i1, i2], "words": old_words[i1:i2]}
        for tag, i1, i2, _j1, _j2 in opcodes if tag == "delete"
    ]
    head, marker, tail = old.partition(SPLIT_MARKER)
    return {
        "word_level": {
            "old_words": len(old_words), "new_words": len(new_words),
            "deleted_words": sum(i2 - i1 for tag, i1, i2, *_ in opcodes if tag == "delete"),
            "opcode_kinds": dict(kinds),
            "only_equal_and_delete": set(kinds) <= {"equal", "delete"},
            "new_is_a_subsequence_of_old": kinds.get("insert", 0) == 0 and kinds.get("replace", 0) == 0,
            "deleted_spans": deleted_spans,
        },
        "byte_level": {
            "old_bytes": len(old.encode("utf-8")), "new_bytes": len(new.encode("utf-8")),
            "old_equals_deleted_head_plus_new": (head + new) == old and new == marker + tail,
            "deleted_head_sha256": sha_text(head),
            "deleted_head_chars": len(head),
            "new_starts_with_the_split_marker": new.startswith(SPLIT_MARKER),
        },
    }


def role_visits(data_root: Path, run_id: str, attempt_id: str) -> dict:
    """Per-role contact counts from a sealed arm's own phase summaries, cross-checked
    against its run manifest's ``cost.calls_used``. Ids and counts only."""

    attempt_dir = data_root / "runs" / run_id / attempt_id
    phases = json.loads(rd(attempt_dir / f"{run_id}.phases.json"))
    manifest = json.loads(rd(attempt_dir / f"{run_id}.run-manifest.json"))
    per_role: Counter = Counter()
    rows = 0
    rows_with_reviewer: Counter = Counter()
    contact_records = 0
    routes: Counter = Counter()
    for result in phases["phases"][0]["results"]:
        rows += 1
        visits = [visit["role_id"] for visit in result["native_episode_receipt"]["role_visits"]]
        per_role.update(visits)
        rows_with_reviewer[visits.count("reviewer")] += 1
        contact_records += len(result.get("contacts") or [])
        routes.update(route["action"] for route in result["native_episode_receipt"].get("planner_routes") or [])
    total = sum(per_role.values())
    calls_used = manifest["cost"]["calls_used"]
    return {
        "run_id": run_id, "attempt_id": attempt_id,
        "status": manifest["status"], "study_commit": manifest["study_commit"],
        "rows": rows, "role_visits": dict(sorted(per_role.items())), "role_visits_total": total,
        "per_row_contact_records_total": contact_records,
        "planner_routes": dict(sorted(routes.items())),
        "run_manifest_cost": {
            key: manifest["cost"][key]
            for key in ("calls_used", "prompt_tokens_total", "completion_tokens_total", "audio_seconds_used", "tool_calls")
        },
        "role_visits_total_equals_calls_used": total == calls_used,
        "calls_used_minus_role_visits": calls_used - total,
        "note": "role_visits is the per-role identity of every sealed contact; cost.calls_used is the run-level counter and may also count contacts that never became a role visit (a context-fit re-request or a refused attempt); the Reviewer rate is taken from role_visits",
        "reviewer_contacts": per_role.get("reviewer", 0),
        "reviewer_contacts_per_row": round(per_role.get("reviewer", 0) / rows, 6) if rows else None,
        "rows_by_reviewer_contact_count": {str(k): v for k, v in sorted(rows_with_reviewer.items())},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZE)
    parser.add_argument("--scratch", type=Path, default=Path("/tmp/saea-g5-tokenize"))
    parser.add_argument("--out", default=f"{PACKAGE}/{RECEIPT_NAME}", help="repo-relative receipt path")
    parser.add_argument("--write-repaired", action="store_true", help="write the repaired instruction file if absent")
    parser.add_argument("--skip-roll2", action="store_true")
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    if not str(args.data_root):
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) is required for the sealed trace facts and the GGUF vocab")

    resolution = resolve_instruction(repo)
    old_path = repo / "configs" / OLD_RELPATH
    new_path = repo / "configs" / NEW_RELPATH
    old = rd(old_path)
    head, marker, tail = old.partition(SPLIT_MARKER)
    if not marker:
        raise SystemExit(f"{OLD_RELPATH} does not contain the audit's split marker {SPLIT_MARKER!r}")
    repaired = marker + tail
    if new_path.exists():
        new = rd(new_path)
        if new != repaired:
            raise SystemExit(f"{NEW_RELPATH} exists and is not the review order of {OLD_RELPATH} byte for byte")
        written = "verified-existing"
    elif args.write_repaired:
        io.open(new_path, "w", encoding="utf-8", newline="").write(repaired)
        new = repaired
        written = "written"
    else:
        raise SystemExit(f"{NEW_RELPATH} is absent; pass --write-repaired to write the review order as the repaired file")
    proof = deletion_only_proof(old, new)
    if not (proof["word_level"]["only_equal_and_delete"] and proof["byte_level"]["old_equals_deleted_head_plus_new"]):
        raise SystemExit("the repaired instruction is not a pure deletion of the old one")

    tokenizer = Tokenizer(args.tokenizer, args.data_root / GGUF_RELPATH, args.scratch)
    counts = {
        "old_whole": tokenizer.count(old, "g5-old-whole"),
        "old_retired_tool_order_head": tokenizer.count(head, "g5-old-head"),
        "old_review_order_tail": tokenizer.count(repaired, "g5-old-tail"),
        "new_whole": tokenizer.count(new, "g5-new-whole"),
    }
    # Two narrower cuts a reader might ask about, counted so the choice is a number
    # and not a taste: the sequencing adverb the deleted step leaves behind, and the
    # anti-fabrication clause that names 'a tool result'. Both are KEPT (see the
    # receipt's 'kept_on_purpose'); these counts only price the alternative.
    variants = {
        "also_delete_then": tokenizer.count(new.replace("Then review", "review", 1), "g5-var-then"),
        "also_delete_or_invent_a_tool_result": tokenizer.count(
            new.replace(" or invent a tool result", "", 1), "g5-var-invent"),
    }
    delta = counts["new_whole"] - counts["old_whole"]
    share = counts["old_retired_tool_order_head"] / counts["old_whole"]

    plan = role_visits(args.data_root, PARENT_RUN, PARENT_ATTEMPT)
    roll2 = None if args.skip_roll2 else role_visits(args.data_root, ROLL2_RUN, ROLL2_ATTEMPT)
    saved_per_row = -delta * plan["reviewer_contacts_per_row"]
    saved_per_flight = -delta * plan["reviewer_contacts"]

    receipt = {
        "schema": "saea-g5-reviewer-instruction-token-measurement-v1",
        "item": "G5 -- the Reviewer instruction's retired-tool order (owner decisions 135 and 153; audit " + AUDIT_NOTE + " section G5)",
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "retired_tool": {
            "what": "the Reviewer's task-contract toolkit saea-tool-task-contract-v1 (phase_tools.reviewer)",
            "retirement": "item E25: docs/receipts/harness-admission.json, the entry with row SAEA-SLURP-NATIVE-EXEMPLARS-K20-NOTOOL-V1, status RETIRED (switch class phase_tools), added by docs/results/2026-09-20-slurp-b1-notool-verdict.md under owner decisions 55, 56 and 61",
            "sealed_evidence": "0 tool schemas in every contact of the lock arm (audit section 1) and tool_calls 0 in the sealed PLAN run manifest cost block (below)",
        },
        "instruction": {
            "old": {"relpath": "configs/" + OLD_RELPATH, "sha256": sha_text(old), "bytes": len(old.encode("utf-8"))},
            "new": {"relpath": "configs/" + NEW_RELPATH, "sha256": sha_text(new), "bytes": len(new.encode("utf-8")), "file": written},
            "split_marker": SPLIT_MARKER,
            "deleted_clauses_verbatim": head,
            "kept_on_purpose": {
                "Then": "the sequencing adverb survives verbatim: deleting it would force a case change on 'review', which is a rephrase, not a deletion; priced at " + str(variants["also_delete_then"]) + " tokens if deleted",
                "or invent a tool result": "kept: it neither orders, describes nor depends on the retired tool -- it forbids fabricating one, which is exactly the downstream failure the 2026-09-26 system-summary diagnostic recorded; priced at " + str(variants["also_delete_or_invent_a_tool_result"]) + " tokens if deleted",
            },
        },
        "resolution": resolution,
        "deletion_only_proof": proof,
        "tokenizer": {
            "binary": str(args.tokenizer), "model": str(args.data_root / GGUF_RELPATH),
            "argv_tail": ["--no-bos", "--no-escape", "--show-count", "--log-disable", "--ids"],
            "same_as": AUDIT_SCRIPT, "invocations": tokenizer.invocations,
        },
        "tokens": {
            **counts,
            "delta_per_reviewer_contact": delta,
            "retired_tool_share_of_old": round(share, 6),
            "retired_tool_share_of_old_pct": round(100 * share, 1),
            "variants_priced_not_applied": variants,
            "audit_reference": {"whole": AUDIT_WHOLE, "head": AUDIT_HEAD, "pct": 63},
            "reproduces_the_audit": counts["old_whole"] == AUDIT_WHOLE and counts["old_retired_tool_order_head"] == AUDIT_HEAD,
            "head_plus_tail_minus_whole": counts["old_retired_tool_order_head"] + counts["old_review_order_tail"] - counts["old_whole"],
        },
        "sealed_reviewer_contact_rate": {"plan": plan, "roll2": roll2,
                                         "note": "the PLAN arm is the comparator this cell is read against; ROLL-2 (five Solver samples per row) is reported beside it and is not the rate used"},
        "saving": {
            "tokens_per_reviewer_contact": -delta,
            "reviewer_contacts_per_row_sealed_plan": plan["reviewer_contacts_per_row"],
            "tokens_per_row_at_the_sealed_plan_rate": round(saved_per_row, 4),
            "tokens_per_1080_row_flight_at_the_sealed_plan_count": saved_per_flight,
            "share_of_the_sealed_plan_prompt_tokens_total": round(saved_per_flight / plan["run_manifest_cost"]["prompt_tokens_total"], 8),
            "note": "prefill tokens only; no cap of this family is denominated in tokens, so no cap moves -- the saving widens the FIT margin against the 24,576-token slot",
        },
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0, "network": 0, "gpu": 0, "paid_api": 0,
                     "tokenizer_process_vocab_only": tokenizer.invocations},
        "boundary": "No utterance text, transcript, gold label or model output is read, printed or persisted: the receipt holds hashes, counts, token counts and the committed instruction's own deleted clause.",
    }
    out = repo / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    io.open(out, "w", encoding="utf-8", newline="").write(text)
    print(json.dumps({
        "receipt": str(args.out), "receipt_sha256": sha_text(text), "tokens": receipt["tokens"],
        "new_instruction_sha256": sha_text(new), "saving": receipt["saving"],
        "plan_reviewer_contacts": plan["reviewer_contacts"], "plan_rows": plan["rows"],
        "plan_role_visits": plan["role_visits"], "plan_total_equals_calls_used": plan["role_visits_total_equals_calls_used"],
        "deletion_only": proof["word_level"]["only_equal_and_delete"] and proof["byte_level"]["old_equals_deleted_head_plus_new"],
        "deleted_words": proof["word_level"]["deleted_words"], "old_words": proof["word_level"]["old_words"], "new_words": proof["word_level"]["new_words"],
        "tokenizer_invocations": tokenizer.invocations,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
