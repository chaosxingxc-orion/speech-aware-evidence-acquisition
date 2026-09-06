#!/usr/bin/env python3
"""Build KC-A1's contrast-note artifact and KC-A1c's category-only control.

Model-free, zero contacts. Reads ``tools_registry.csv`` through the umbrella
lock plus a committed target spec -- ``--targets-spec``, default
``configs/knowledge/a2t-kc-a1/targets-v1.json`` and, since the owner took
option B on 2026-09-06, ``configs/knowledge/a2t-kc-a1/targets-lighting-v1.json``
for the cell that flies (whose tool lists are re-verified against the MF-1
audit receipt), then
writes both override artifacts, both baseline fragments -- through
``rails.evolution.write_candidate_fragments``, official-protocol fragment as
base -- and one receipt with the per-tool character deltas and each rendered
block's line and character totals. The note/control CONSTRUCTION rule is
``rails.proposer.contrast_note_records``; every prose statement recorded is
the spec's. Tokens are ESTIMATED (spec ``statements.token_method``); the
prompt fit before takeoff measures them.

Usage (WSL2): ``python scripts/build_a2t_contrast_notes.py --targets-spec
configs/knowledge/a2t-kc-a1/targets-lighting-v1.json --write``.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "configs/knowledge/a2t-kc-a1/targets-v1.json"
ARTIFACTS = REPO / "configs/knowledge/a2t-kc-a1"
OUT_DIR = (
    REPO / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-a2t-kc-a1-contrast-notes-4000-v1"
)
BASE = REPO / "configs/baseline/a2t-direct-official-protocol.json"
#: ``(arm, record key, artifact file name, baseline fragment file name)``.
ARMS = (
    ("kc-a1", "kc_a1", "contrast-notes-v1.json", "a2t-kc-a1-contrast-notes.json"),
    ("kc-a1c", "kc_a1c", "category-only-v1.json", "a2t-kc-a1c-category-only.json"),
)
CHARS_PER_TOKEN = 347.0 / 87.0


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def est(text: str) -> int:
    return round(len(text) / CHARS_PER_TOKEN)


def verify_spec(spec) -> dict[str, dict[str, str]]:
    """The spec's ``{target_id: {tool: note}}``, refused unless every tool list
    is the MF-1 audit receipt's own."""
    source = spec["source_receipt"]
    receipt = REPO / str(source["path"])
    measured = digest(receipt.read_bytes())
    if measured != source["sha256"]:
        raise SystemExit(f"audit receipt hashes to {measured}, not {source['sha256']}")
    audited = {
        str(entry["target_id"]): sorted(str(tool) for tool in entry["tools"])
        for entry in json.loads(receipt.read_text(encoding="utf-8"))
        ["primary_population"]["targets"]["targets"]
    }
    targets: dict[str, dict[str, str]] = {}
    for target in spec["targets"]:
        target_id = str(target["target_id"])
        if audited.get(target_id) != sorted(target["tools"]):
            raise SystemExit(f"target {target_id} is not the audit receipt's")
        targets[target_id] = {
            tool: str(body["note"]) for tool, body in target["tools"].items()
        }
    return targets


def arm_block(arm, k, records, key, rows, compact):
    """``(candidate, receipt block)`` for one arm: its whole 152-line rendering
    measured against the compact baseline, then every form and decontamination
    gate ``rails.proposer`` owns. The token slack is reported, never hidden: 0
    means the artifact clears the program's own +40-token form cap, and any
    other value is how far that cap would have to move."""
    from speech_aware_evidence_acquisition.data.audio2tool_tools import (
        render_registry_compact_rows,
    )
    from speech_aware_evidence_acquisition.rails.proposer import (
        TOKEN_HEADROOM, CandidateArtifact, validate_candidate_artifact,
    )

    overrides = {str(record["tool_name"]): str(record[key]) for record in records}
    rendered = render_registry_compact_rows(rows, description_overrides=overrides)
    estimate = est(rendered) - est(compact)
    slack = max(0, estimate - TOKEN_HEADROOM)
    shape = {
        "tools_overridden": len(overrides),
        "rendered_lines": len(rendered.split("\n")), "rendered_chars": len(rendered),
        "rendered_sha256": digest(rendered.encode("utf-8")),
        "compact_chars": len(compact), "compact_sha256": digest(compact.encode("utf-8")),
        "added_chars": len(rendered) - len(compact), "estimated_added_tokens": estimate,
        "program_token_headroom": TOKEN_HEADROOM,
        "estimated_tokens_over_headroom": slack,
        "within_program_token_headroom": slack == 0,
    }
    draft = CandidateArtifact(
        candidate_id="", family="deterministic", target_id=arm, round=0, k=k,
        descriptions=dict(sorted(overrides.items())),
        cue=("the registry's own domain, category, argument names and constraints"
             if arm == "kc-a1" else None),
        proposer_prompt_sha256=None, exemplar_ids=(),
    )
    candidate = dataclasses.replace(
        draft, candidate_id=draft.expected_candidate_id()
    ).validate()
    validation = validate_candidate_artifact(
        candidate, registry_rows=rows, token_counter=est,
        compact_baseline_tokens=est(compact) + slack,
        evaluation_query_texts=(), registry_text=compact,
    )
    return candidate, {
        "measurement": shape, "candidate": candidate.as_json(),
        "validation": validation.as_json(), "token_headroom_slack_granted": slack,
    }


def write_arms(portfolios, manipulation: str) -> dict[str, dict[str, str]]:
    """The two artifacts and the two baseline fragments, then renamed.
    ``write_candidate_fragments`` names both files after the portfolio digest,
    and that digest is over the override MAPPING, so renaming an artifact to
    its cell-facing name leaves the recorded ``artifact_sha256`` exactly right
    and only ``artifact_relpath`` has to follow it."""
    from speech_aware_evidence_acquisition.rails.evolution import (
        write_candidate_fragments,
    )

    base = json.loads(BASE.read_text(encoding="utf-8"))
    base.pop("task_instruction_fill")
    staged = OUT_DIR / "staged-fragments"
    emitted = write_candidate_fragments(
        portfolios, base_fragment=base, out_dir=staged, artifact_dir=ARTIFACTS,
        artifact_relpath_base=REPO,
    )
    written: dict[str, dict[str, str]] = {}
    for (arm, _, artifact_name, fragment_name), path in zip(ARMS, emitted, strict=True):
        fragment = json.loads(path.read_text(encoding="utf-8"))
        params = fragment["task_instruction_fill_params"]
        (REPO / str(params["artifact_relpath"])).replace(ARTIFACTS / artifact_name)
        params["artifact_relpath"] = f"configs/knowledge/a2t-kc-a1/{artifact_name}"
        fragment["manipulation"] = manipulation.format(artifact=params["artifact_relpath"])
        (REPO / "configs/baseline" / fragment_name).write_text(
            json.dumps(fragment, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        path.unlink()
        written[arm] = {
            "baseline_fragment": f"configs/baseline/{fragment_name}",
            "artifact_relpath": str(params["artifact_relpath"]),
            "artifact_sha256": str(params["artifact_sha256"]),
            "portfolio_sha256": str(params["portfolio_sha256"]),
        }
    staged.rmdir()
    return written


def main() -> int:
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry
    from speech_aware_evidence_acquisition.data.audio2tool_tools import (
        render_registry_compact_rows,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        data_root, load_lock, umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.rails.evolution import assemble_portfolio
    from speech_aware_evidence_acquisition.rails.proposer import contrast_note_records

    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--targets", default=None, help="price a SUBSET; writes nothing")
    parser.add_argument(
        "--targets-spec",
        type=Path,
        default=SPEC,
        help=(
            "the COMMITTED target spec to build from. A spec may carry any subset of "
            "the MF-1 targets -- every tool list it does carry is still re-verified "
            "against the audit receipt -- so the owner's option-B lighting-only cell "
            "is a committed file rather than a command-line filter. --targets stays "
            "what it was: an ad-hoc pricing filter that writes nothing"
        ),
    )
    args = parser.parse_args()
    if args.targets and args.write:
        raise SystemExit("--targets prices a subset; it never writes the committed arms")
    spec_path = Path(args.targets_spec)
    if not spec_path.is_absolute():
        spec_path = REPO / spec_path
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    targets = verify_spec(spec)
    if args.targets:
        wanted = {part.strip() for part in args.targets.split(",") if part.strip()}
        if not wanted <= set(targets):
            raise SystemExit(f"unknown target(s) {sorted(wanted - set(targets))}")
        targets = {key: value for key, value in targets.items() if key in wanted}
    rows = list(load_tool_registry(load_lock(umbrella_lock_path(REPO)), data_root()))
    compact = render_registry_compact_rows(rows)
    records = contrast_note_records(
        rows, targets,
        function_words=spec["note_rules"]["function_words"],
        prefix=str(spec["note_rules"]["prefix"]),
        filler=str(spec["control_rules"]["filler"]),
    )

    arms: dict[str, object] = {}
    portfolios = []
    for index, (arm, key, _, _) in enumerate(ARMS):
        candidate, block = arm_block(arm, index, records, key, rows, compact)
        arms[arm] = block
        portfolios.append(assemble_portfolio({}, {arm: candidate}))
        print("%-6s %s" % (arm, json.dumps(block["measurement"], sort_keys=True)))

    per_target: dict[str, dict[str, int]] = {}
    for record in records:
        block = per_target.setdefault(
            str(record["target_id"]), {"tools": 0, "added_chars": 0}
        )
        block["tools"] += 1
        block["added_chars"] += int(record["note_chars"])
    for target, block in sorted(per_target.items()):
        block["estimated_added_tokens"] = round(block["added_chars"] / CHARS_PER_TOKEN)
        print("  %-18s %s" % (target, json.dumps(block, sort_keys=True)))

    receipt = {
        "schema": "saea-a2t-kc-a1-artifact-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "builder": "scripts/build_a2t_contrast_notes.py", "model_contacts": 0,
        "target_spec": {
            "path": spec_path.resolve().relative_to(REPO).as_posix(),
            "sha256": digest(spec_path.read_bytes()),
            "audit_receipt": spec["source_receipt"],
            "target_ids": sorted(targets),
        },
        "registry": {"rows": len(rows), "lock_key": "audio2tool"},
        "token_method": spec["statements"]["token_method"],
        "decontamination": spec["statements"]["decontamination"],
        "per_tool": records, "per_target": per_target, "arms": arms,
    }
    if args.write:
        receipt["files"] = write_arms(portfolios, str(spec["statements"]["manipulation"]))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / "artifact-receipt.json"
        path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        print("written: %s (sha256 %s)" % (path, digest(path.read_bytes())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
