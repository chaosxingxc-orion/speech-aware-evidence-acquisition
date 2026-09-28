#!/usr/bin/env python3
"""CLI: item E41 four-row dry-run READ driver (receipts only).

Registered by
``docs/readiness/2026-09-27-e21-native-window-e41-v1/dry-run-analysis-recipe-v1.json``
(recipe id ``e21-native-window-e41-dry-run-receipts-read-v1``), whose package
README step 5 named this driver before it existed. It computes exactly the
recipe's three assertions (R1, R2, R3) and the tables/diagnostics the recipe
lists, on the sealed four-row dry run ``SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-
ROW-E41-V1``, beside the sealed E39b dry run and the E35 four-row DIRECT arm
the recipe names as comparators, and writes a receipts-only verdict to
``<analysis-root>/read.json`` and ``read.md``.

WHAT IT READS -- nothing beyond the recipe's named inputs:

* this arm's own COMPLETED run manifest
  (``<data-root>/runs/<run-id>/<attempt>/<run-id>.run-manifest.json``);
* this arm's sealed trace, receipt FIELDS only (``MODEL_REQUEST`` /
  ``MODEL_RESPONSE`` / ``MODEL_WIRE_RESPONSE``, ``USE`` ``native-role-
  contact``, and ``native-episode`` receipts), via the SAME loader
  (``load_trace``) and Perception note-feature code (``note_features``) as
  ``scripts/analysis/e21_e41_perception_note_trace_read.py`` -- imported,
  never copied;
* this arm's ``outputs.jsonl`` ``execution_unit_delivery`` block, compared to
  the empty string's own SHA-256
  (``e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855``) to
  decide "delivered non-empty" without ever reading delivered bytes;
* the sealed E39b dry run's own trace, read the identical receipts-only way
  (never re-scored, never re-flown);
* the sealed E35 four-row DIRECT arm's trace, for the Perception note's
  window-transcript 4-gram re-emission feature only (``DIRECT_RUNS[1]`` of
  the imported module).

PRECONDITIONS (fail-closed, checked before the trace is ever opened):

1. The recipe's own ``read_run_id`` row in ``docs/exposure-ledger.md``
   carries "root countersigned" (the ``agree_read.sh`` / ``roll2_read.sh``
   pattern: ``grep ... | grep -q "root countersigned"``, done here through
   the shared ``contracts.ledger._parse_ledger_tables`` reader instead of a
   raw grep).
2. This arm's run manifest has ``status == "COMPLETED"`` and its own
   ``run_id`` field names this exact run.

Either failure exits 3 and opens nothing else.

``--dry-run`` stops immediately after the two preconditions above and prints
record / episode / contact COUNTS from the manifest and trace only: it
writes no file and computes no R1/R2/R3 verdict. This is the only mode this
driver may be run in against the REAL sealed run outside the coordinator's
scheduled read.

BOUNDARY. No utterance, transcript, reference, gold or model-output TEXT is
ever printed or persisted. Every text-shaped fact the recipe needs is
reduced, before it leaves this process, to a boolean, a count, or a SHA-256
comparison: "delivered non-empty" is a hash compare against the empty
string's digest, and the Perception note's STRUCTURE (line count, words per
line, 6-gram repetition share, 4-gram transcript re-emission share, mode
label) comes from the imported ``note_features``, which returns counts and
labels only and never the note text itself.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python -B \\
        scripts/analysis/e21_e41_dry_run_read.py \\
        --repo-root <repo> --data-root "$SPEECHRL_DATA_DIR"

Real read only after the coordinator confirms; every other invocation here
must carry ``--dry-run``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.contracts.ledger import (  # noqa: E402
    _parse_ledger_tables,
)

RECIPE_RELPATH = Path(
    "docs/readiness/2026-09-27-e21-native-window-e41-v1/dry-run-analysis-recipe-v1.json"
)
#: The note-trace read this driver imports its trace loader and Perception
#: feature code from -- never copied (task instruction).
NOTE_MODULE_RELPATH = Path("scripts/analysis/e21_e41_perception_note_trace_read.py")

DEFAULT_RUN_ID = "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1"
DEFAULT_ANALYSIS_ROOT_NAME = "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1-READ-V1"
#: The recipe's own comparator identity (``inputs.comparators``).
E39B_RUN_ID = "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1"
E39B_ATTEMPT = "attempt-e21-native-window-system-four-row-e39b-v1"
#: SHA-256 of the empty string: the only way this driver ever learns whether
#: a delivered text was blank, without reading delivered bytes.
EMPTY_TEXT_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
#: The recipe's registered ``saea-deliver-earnings-text-v1`` normaliser id (R2).
EXPECTED_NORMALISER_ID = "saea-deliver-earnings-text-v1"
SCHEMA = "saea-e41-four-row-dry-run-receipts-read-v1"
#: The recipe's own "budget vs ceilings" table, item 5 of ``tables_required``.
REGISTERED_CEILINGS = {"generation_calls": 44, "repeated_speech_seconds": 3960}
#: instruction-token-measurement-v1.json's digit-dense worst-case compliant
#: note (the E41 bound's own completion-side headroom), quoted for R3's
#: "against the E41 bound" diagnostic -- not recomputed here (that requires
#: the vocab-only tokenizer process this receipts-only read never starts).
E41_BOUND_WORST_CASE_COMPLETION_TOKENS = 574


class DryRunReadError(RuntimeError):
    """A precondition failed, or a sealed input lacks the shape the recipe names."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def import_file(relpath: Path, name: str):
    """Import a sibling analysis SCRIPT by file path, the same ``importlib``
    idiom ``scripts/analysis/catchall_offline_read.py`` uses to reuse another
    driver's code without copying it. Returns ``(module, source_sha256)``."""

    path = REPO_ROOT / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DryRunReadError(f"cannot import {relpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, sha256_file(path)


def default_attempt(run_id: str) -> str:
    lowered = run_id.lower()
    if not lowered.startswith("saea-"):
        raise DryRunReadError(f"cannot derive an attempt id from {run_id!r}")
    return "attempt-" + lowered[len("saea-") :]


def run_dir(data_root: Path, run_id: str, attempt: str) -> Path:
    return data_root / "runs" / run_id / attempt


def load_outputs_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# Preconditions
# ---------------------------------------------------------------------------


def assert_countersigned(repo_root: Path, read_run_id: str) -> dict[str, str]:
    """Refuse unless the recipe's own READ row is "root countersigned".

    Mirrors ``scripts/flights/agree/agree_read.sh``'s
    ``grep ... | grep -q "root countersigned"`` gate, through the same
    ``contracts.ledger._parse_ledger_tables`` reader the ledger's own tests
    use, rather than a raw grep on a markdown table cell.
    """

    ledger_path = repo_root / "docs" / "exposure-ledger.md"
    if not ledger_path.exists():
        raise DryRunReadError(f"REFUSED: no exposure ledger at {ledger_path}")
    text = ledger_path.read_text(encoding="utf-8")
    rows = [
        row for row in _parse_ledger_tables(text)
        if row.get("run/experiment id") == read_run_id
    ]
    if not rows:
        raise DryRunReadError(
            f"REFUSED: no exposure-ledger row named {read_run_id!r}"
        )
    row = rows[-1]
    notes = row.get("notes", "")
    if "root countersigned" not in notes:
        raise DryRunReadError(
            f"REFUSED: the READ row {read_run_id!r} is not countersigned "
            f"(notes: {notes[:160]!r})"
        )
    return row


def manifest_path(data_root: Path, run_id: str, attempt: str) -> Path:
    return run_dir(data_root, run_id, attempt) / f"{run_id}.run-manifest.json"


def assert_completed_manifest(data_root: Path, run_id: str, attempt: str) -> dict[str, Any]:
    path = manifest_path(data_root, run_id, attempt)
    if not path.exists():
        raise DryRunReadError(f"REFUSED: no run manifest at {path}")
    manifest = load_json(path)
    if manifest.get("run_id") != run_id:
        raise DryRunReadError(
            f"REFUSED: manifest run_id {manifest.get('run_id')!r} != {run_id!r}"
        )
    if manifest.get("status") != "COMPLETED":
        raise DryRunReadError(
            f"REFUSED: {run_id}/{attempt} manifest status is "
            f"{manifest.get('status')!r}, not COMPLETED"
        )
    return manifest


def abort_history(data_root: Path, run_id: str, sealed_attempt: str) -> list[dict]:
    """Every OTHER attempt directory of this run id: an abort, refusal or
    recovery re-registration, with its cause (diagnostic 5)."""

    base = data_root / "runs" / run_id
    history: list[dict] = []
    if not base.exists():
        return history
    for attempt_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        if attempt_dir.name == sealed_attempt:
            continue
        candidate = attempt_dir / f"{run_id}.run-manifest.json"
        if not candidate.exists():
            history.append({
                "attempt_id": attempt_dir.name, "status": "unknown",
                "failure_reason": "no run manifest found beside this attempt directory",
            })
            continue
        manifest = load_json(candidate)
        history.append({
            "attempt_id": manifest.get("attempt_id") or attempt_dir.name,
            "status": manifest.get("status"),
            "failure_reason": manifest.get("failure_reason"),
        })
    return history


# ---------------------------------------------------------------------------
# R1 / R2: episode and delivery receipts
# ---------------------------------------------------------------------------


def r1_abstained_perception_or_reviewer(episodes: list[dict]) -> list[dict]:
    """R1: zero retained rows may carry a perception/reviewer
    ``terminal_disposition`` together with an abstention.

    ``rails/native_episode_receipt.py``'s ``_finite_delivery`` marks a row
    "abstention" (as opposed to "finite", which retains the last completed
    Solver) exactly when it carries an ``abstention_receipt`` -- the receipt
    field read here, unchanged from that module's own discriminator.
    """

    violations = []
    for episode in episodes:
        disposition = episode.get("terminal_disposition") or {}
        role_id = disposition.get("role_id")
        if role_id in ("perception", "reviewer") and episode.get("abstention_receipt") is not None:
            violations.append({"role_id": role_id, "reason": disposition.get("reason")})
    return violations


def terminal_disposition_table(episodes: list[dict]) -> dict[str, dict[str, int]]:
    table: dict[str, Counter] = {}
    for episode in episodes:
        disposition = episode.get("terminal_disposition") or {}
        role_id = disposition.get("role_id") or "none"
        reason = disposition.get("reason") or "none"
        table.setdefault(role_id, Counter())[reason] += 1
    return {role: dict(sorted(counter.items())) for role, counter in sorted(table.items())}


def normaliser_receipts(episodes: list[dict], expected_id: str) -> dict[str, Any]:
    present = [episode.get("deliver_normaliser") for episode in episodes]
    ids_seen = Counter((item or {}).get("normaliser_id") or "none" for item in present)
    return {
        "episodes": len(episodes),
        "with_normaliser_receipt": sum(1 for item in present if isinstance(item, dict)),
        "normaliser_id_counts": dict(sorted(ids_seen.items())),
        "all_match_expected_id": bool(present) and all(
            isinstance(item, dict) and item.get("normaliser_id") == expected_id
            for item in present
        ),
    }


def delivered_non_empty_by_window(outputs_rows: list[dict]) -> list[dict]:
    """R2's delivery table: window, delivered non-empty, by SHA-256 compare
    against the empty string's own digest -- delivered bytes are never read."""

    windows = []
    for row in outputs_rows:
        delivery = row.get("execution_unit_delivery") or {}
        for source in delivery.get("sources", []):
            windows.append({
                "execution_unit_id": source.get("execution_unit_id"),
                "delivered_non_empty": source.get("delivery_text_sha256") != EMPTY_TEXT_SHA256,
                "delivery_text_sha256": source.get("delivery_text_sha256"),
            })
    return sorted(windows, key=lambda window: str(window["execution_unit_id"]))


# ---------------------------------------------------------------------------
# R3 and diagnostics: Perception / Reviewer truncation, via the imported code
# ---------------------------------------------------------------------------


def perception_truncation_read(note_module, data_root: Path, run_id: str, attempt: str) -> dict[str, Any]:
    """R3, computed with the imported ``load_trace`` / ``note_features``.

    Perception AND Reviewer contacts are read (the recipe's R3: "the Reviewer
    truncation count at its 640 cap is reported beside it"); the window-
    transcript 4-gram re-emission feature is computed only for Perception,
    against the sealed E35 four-row DIRECT arm's own trace (``DIRECT_RUNS``),
    exactly as the imported module already does for the wider carrier.
    """

    direct: dict[str, str] = {}
    direct_inputs = []
    for direct_run, direct_attempt in note_module.DIRECT_RUNS:
        path = note_module.run_dir(data_root, direct_run, direct_attempt) / f"{direct_run}.trace.jsonl"
        if not path.exists():
            continue
        contacts, _ = note_module.load_trace(path)
        for row in contacts.values():
            if row.get("packet") and "_text" in row:
                direct[row["packet"]] = row["_text"]
        direct_inputs.append({
            "run_id": direct_run, "attempt": direct_attempt, "trace_sha256": sha256_file(path),
        })

    trace_path = note_module.run_dir(data_root, run_id, attempt) / f"{run_id}.trace.jsonl"
    contacts, episodes = note_module.load_trace(trace_path)

    perception_notes: list[dict] = []
    reviewer_notes: list[dict] = []
    for flight_id in sorted(contacts):
        row = contacts[flight_id]
        role = row.get("role")
        if role not in ("perception", "reviewer"):
            continue
        if "_text" not in row or "finish_reason" not in row or "max_tokens" not in row:
            continue
        direct_text = direct.get(row.get("packet")) if role == "perception" else None
        features = note_module.note_features(row["_text"], direct_text)
        note = {
            "flight_id": flight_id, "role": role, "finish_reason": row["finish_reason"],
            "cap": row["max_tokens"], "completion_tokens": row.get("completion_tokens"),
            "lines": features["lines"], "max_words_per_line": features["max_words_per_line"],
            "repeat_share_6gram": features["repeat_share_6gram"], "mode": features["mode"],
            "within_e41_bound": features["within_e41_bound"],
            "window_transcript_4gram_reemission": features["window_transcript_4gram_reemission"],
        }
        (perception_notes if role == "perception" else reviewer_notes).append(note)

    def block(notes: list[dict]) -> dict[str, Any]:
        truncated = [note for note in notes if note["finish_reason"] == "length"]
        return {
            "contacts": len(notes),
            "truncated": len(truncated),
            "truncated_flight_ids": [note["flight_id"] for note in truncated],
            "within_e41_bound": sum(1 for note in notes if note["within_e41_bound"]),
            "completion_tokens": note_module.quantiles(
                [note["completion_tokens"] for note in notes if note["completion_tokens"] is not None]
            ),
            "modes": dict(sorted(Counter(note["mode"] for note in truncated).items())),
            "truncated_note_structure": [
                {
                    "flight_id": note["flight_id"], "lines": note["lines"],
                    "max_words_per_line": note["max_words_per_line"],
                    "repeat_share_6gram": note["repeat_share_6gram"], "mode": note["mode"],
                }
                for note in truncated
            ],
        }

    perception_block = block(perception_notes)
    reviewer_block = block(reviewer_notes)
    return {
        "trace_sha256": sha256_file(trace_path),
        "direct_comparator_inputs": direct_inputs,
        "perception": perception_block,
        "reviewer": reviewer_block,
        "truncation_rate": (
            perception_block["truncated"] / perception_block["contacts"]
            if perception_block["contacts"] else None
        ),
        "pass": perception_block["truncated"] == 0 and reviewer_block["truncated"] == 0,
        "e41_bound": note_module.BOUND,
        "e41_bound_worst_case_completion_tokens": E41_BOUND_WORST_CASE_COMPLETION_TOKENS,
        "cap": 640,
    }


# ---------------------------------------------------------------------------
# Remaining tables / diagnostics
# ---------------------------------------------------------------------------


def role_contact_table(contacts: Mapping[str, dict]) -> dict[str, Any]:
    by_role = Counter(row.get("role") or "unknown" for row in contacts.values())
    finish_by_role: dict[str, Counter] = {}
    for row in contacts.values():
        role = row.get("role") or "unknown"
        reason = row.get("finish_reason")
        bucket = reason if reason in ("stop", "length") else "other"
        finish_by_role.setdefault(role, Counter())[bucket] += 1
    return {
        "contacts_total": len(contacts),
        "by_role": dict(sorted(by_role.items())),
        "finish_reason_by_role": {
            role: {key: counter.get(key, 0) for key in ("stop", "length", "other")}
            for role, counter in sorted(finish_by_role.items())
        },
    }


def planner_routes_table(episodes: list[dict]) -> dict[str, Any]:
    """Diagnostic 4: REVISE / ACCEPT route counts and byte-identical second
    Solver drafts, from ``response_text_sha256`` alone -- text never opened."""

    actions: Counter = Counter()
    revise_second_pass: list[dict] = []
    for episode in episodes:
        routes = episode.get("planner_routes") or []
        for route in routes:
            actions[route.get("action") or "unknown"] += 1
        solver_hashes = [
            visit.get("execution_receipt", {}).get("final_contact", {}).get("response_text_sha256")
            for visit in (episode.get("role_visits") or [])
            if isinstance(visit, dict) and visit.get("stage") == "solver"
        ]
        for index, route in enumerate(routes):
            if route.get("action") == "REVISE" and index + 1 < len(solver_hashes):
                revise_second_pass.append({
                    "revision_count": route.get("revision_count"),
                    "solver_response_text_sha256_equal": solver_hashes[index] == solver_hashes[index + 1],
                })
    return {
        "action_counts": dict(sorted(actions.items())),
        "revise_routes": actions.get("REVISE", 0),
        "accept_routes": actions.get("ACCEPT", 0),
        "revise_second_pass_byte_identical_count": sum(
            1 for row in revise_second_pass if row["solver_response_text_sha256_equal"]
        ),
        "revise_second_pass_rows": revise_second_pass,
    }


def render_markdown(document: dict) -> str:
    lines = [
        f"# {document['read_run_id']}: receipts-only read",
        "",
        f"Recipe: `{document['recipe_id']}` (`{document['recipe_path']}`, "
        f"sha256 `{document['recipe_sha256'][:16]}`)",
        "",
        f"Verdict: **{document['verdict']}**",
        "",
        document["boundary"],
        "",
        "## Arm",
        "",
        f"- run_id: `{document['arm']['run_id']}`",
        f"- attempt: `{document['arm']['attempt']}`",
        f"- status: {document['arm']['status']}",
        f"- study_commit: `{document['arm']['study_commit']}`",
        f"- trace_sha256: `{document['arm']['trace_sha256']}`",
        "",
        "## Assertions",
        "",
        "| id | pass | detail |",
        "| --- | --- | --- |",
        (
            f"| R1 | {document['assertions']['R1']['pass']} | "
            f"violations: {len(document['assertions']['R1']['violations'])} |"
        ),
        (
            f"| R2 | {document['assertions']['R2']['pass']} | windows: "
            f"{len(document['assertions']['R2']['windows'])}, non_empty: "
            f"{sum(1 for w in document['assertions']['R2']['windows'] if w['delivered_non_empty'])} |"
        ),
        (
            f"| R3 | {document['assertions']['R3']['pass']} | perception truncated: "
            f"{document['assertions']['R3']['perception']['truncated']} / "
            f"{document['assertions']['R3']['perception']['contacts']}, reviewer truncated: "
            f"{document['assertions']['R3']['reviewer']['truncated']} / "
            f"{document['assertions']['R3']['reviewer']['contacts']} |"
        ),
        "",
        "## Tables",
        "",
        "### Per-role contact counts (this arm vs E39b)",
        "",
        "```json",
        json.dumps({
            "this_arm": document["tables"]["role_contacts_this_arm"],
            "e39b": document["tables"]["role_contacts_e39b"],
        }, indent=1, sort_keys=True),
        "```",
        "",
        "### Terminal disposition (this arm vs E39b)",
        "",
        "```json",
        json.dumps({
            "this_arm": document["tables"]["terminal_disposition_this_arm"],
            "e39b": document["tables"]["terminal_disposition_e39b"],
        }, indent=1, sort_keys=True),
        "```",
        "",
        "### Delivery table",
        "",
        "| window | delivered non-empty | normaliser receipt present |",
        "| --- | --- | --- |",
    ]
    normaliser_present = document["assertions"]["R2"]["normaliser_receipts"]["all_match_expected_id"]
    for window in document["tables"]["delivery_table"]:
        lines.append(
            f"| {window['execution_unit_id']} | {window['delivered_non_empty']} | {normaliser_present} |"
        )
    lines += [
        "",
        "### Budget vs registered ceilings",
        "",
        "```json",
        json.dumps(document["tables"]["budget_vs_ceilings"], indent=1, sort_keys=True),
        "```",
        "",
        "## Diagnostics",
        "",
        "```json",
        json.dumps(document["diagnostics"], indent=1, sort_keys=True),
        "```",
        "",
        "## Comparators",
        "",
        "```json",
        json.dumps(document["comparators"], indent=1, sort_keys=True),
        "```",
        "",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_document(
    *, repo_root: Path, data_root: Path, run_id: str, attempt: str, recipe_path: Path,
    recipe: dict, read_run_id: str, ledger_row: dict, manifest: dict, note_module,
) -> dict:
    trace_path = run_dir(data_root, run_id, attempt) / f"{run_id}.trace.jsonl"
    outputs_path = run_dir(data_root, run_id, attempt) / f"{run_id}.outputs.jsonl"
    if not trace_path.exists():
        raise DryRunReadError(f"REFUSED: sealed trace not found at {trace_path}")
    if not outputs_path.exists():
        raise DryRunReadError(f"REFUSED: sealed outputs not found at {outputs_path}")

    contacts, episodes = note_module.load_trace(trace_path)
    outputs_rows = load_outputs_rows(outputs_path)

    r1_violations = r1_abstained_perception_or_reviewer(episodes)
    r1_pass = len(r1_violations) == 0

    delivery_windows = delivered_non_empty_by_window(outputs_rows)
    normaliser = normaliser_receipts(episodes, EXPECTED_NORMALISER_ID)
    r2_pass = (
        len(delivery_windows) == 4
        and all(window["delivered_non_empty"] for window in delivery_windows)
        and normaliser["episodes"] == 4
        and normaliser["all_match_expected_id"]
    )

    perception = perception_truncation_read(note_module, data_root, run_id, attempt)
    r3_pass = perception["pass"]

    e39b_trace_path = run_dir(data_root, E39B_RUN_ID, E39B_ATTEMPT) / f"{E39B_RUN_ID}.trace.jsonl"
    e39b_present = e39b_trace_path.exists()
    e39b_role_contacts = e39b_terminal = None
    if e39b_present:
        e39b_contacts, e39b_episodes = note_module.load_trace(e39b_trace_path)
        e39b_role_contacts = role_contact_table(e39b_contacts)
        e39b_terminal = terminal_disposition_table(e39b_episodes)

    role_contacts = role_contact_table(contacts)
    terminal_table = terminal_disposition_table(episodes)
    planner = planner_routes_table(episodes)
    solver_tokens = [
        row["completion_tokens"] for row in contacts.values()
        if row.get("role") == "solver" and row.get("completion_tokens") is not None
    ]
    abort_hist = abort_history(data_root, run_id, attempt)

    cost = manifest.get("cost") or {}
    ceilings_realized = {
        "generation_calls": cost.get("calls_used"),
        "repeated_speech_seconds": cost.get("audio_seconds_used"),
    }
    ceilings_pass = (
        isinstance(ceilings_realized["generation_calls"], (int, float))
        and ceilings_realized["generation_calls"] <= REGISTERED_CEILINGS["generation_calls"]
        and isinstance(ceilings_realized["repeated_speech_seconds"], (int, float))
        and ceilings_realized["repeated_speech_seconds"] <= REGISTERED_CEILINGS["repeated_speech_seconds"]
    )

    overall_pass = r1_pass and r2_pass and r3_pass
    now = datetime.now(timezone.utc).isoformat()
    direct_run, direct_attempt = note_module.DIRECT_RUNS[1]
    return {
        "schema": SCHEMA,
        "recipe_id": recipe.get("recipe_id"),
        "recipe_path": RECIPE_RELPATH.as_posix(),
        "recipe_sha256": sha256_file(recipe_path),
        "read_run_id": read_run_id,
        "measured_at_utc": now,
        "boundary": (
            "No utterance, transcript, reference, gold or model-output text is printed or "
            "persisted: this document holds ids, counts, rates, booleans and hashes only."
        ),
        "contacts_made_by_this_read": {
            "model": 0, "server": 0, "encoder": 0, "scorer": 0, "network": 0, "tokenizer": 0,
        },
        "arm": {
            "run_id": run_id, "attempt": attempt, "status": manifest.get("status"),
            "study_commit": manifest.get("study_commit"),
            "config_hash": (manifest.get("config") or {}).get("config_hash"),
            "protocol_hash": manifest.get("protocol_hash"),
            "split": manifest.get("split"), "plan": manifest.get("plan"), "cost": manifest.get("cost"),
            "trace_sha256": sha256_file(trace_path),
        },
        "ledger_row_notes_excerpt": (ledger_row.get("notes") or "")[:200],
        "assertions": {
            "R1": {
                "statement": (
                    "zero retained rows carry a perception/reviewer terminal_disposition "
                    "together with an abstention"
                ),
                "pass": r1_pass, "violations": r1_violations,
            },
            "R2": {
                "statement": (
                    "4 of 4 windows deliver non-empty text with one "
                    f"{EXPECTED_NORMALISER_ID} receipt per window"
                ),
                "pass": r2_pass, "windows": delivery_windows, "normaliser_receipts": normaliser,
            },
            "R3": {
                "statement": (
                    "Perception truncation rate, target zero; the Reviewer truncation "
                    "count at its own 640 cap is reported beside it"
                ),
                "pass": r3_pass, "perception": perception["perception"], "reviewer": perception["reviewer"],
                "truncation_rate": perception["truncation_rate"],
            },
        },
        "verdict": "PASS" if overall_pass else "FAIL",
        "tables": {
            "role_contacts_this_arm": role_contacts,
            "role_contacts_e39b": e39b_role_contacts,
            "terminal_disposition_this_arm": terminal_table,
            "terminal_disposition_e39b": e39b_terminal,
            "delivery_table": delivery_windows,
            "budget_vs_ceilings": {
                "registered_ceilings": REGISTERED_CEILINGS,
                "realized": ceilings_realized,
                "within_ceilings": ceilings_pass,
            },
        },
        "diagnostics": {
            "perception_completion_tokens_vs_cap_and_bound": {
                "distribution": perception["perception"]["completion_tokens"],
                "cap": perception["cap"],
                "e41_bound_worst_case_completion_tokens": perception["e41_bound_worst_case_completion_tokens"],
            },
            "perception_note_compliance": {
                "contacts": perception["perception"]["contacts"],
                "within_e41_bound": perception["perception"]["within_e41_bound"],
                "e41_bound": perception["e41_bound"],
            },
            "solver_completion_tokens_this_arm": note_module.quantiles(solver_tokens),
            "planner_routes": planner,
            "abort_and_recovery_history": abort_hist,
        },
        "comparators": {
            "e39b": {
                "run_id": E39B_RUN_ID, "attempt": E39B_ATTEMPT, "present": e39b_present,
                "read_structurally_never_re_scored": True,
            },
            "e35_four_row_direct": {
                "run_id": direct_run, "attempt": direct_attempt,
                "used_for_window_transcript_reemission": any(
                    entry["run_id"] == direct_run for entry in perception["direct_comparator_inputs"]
                ),
                "read_structurally_never_re_scored": True,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--attempt", default=None)
    parser.add_argument("--recipe", type=Path, default=None)
    parser.add_argument("--analysis-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    data_root = args.data_root
    recipe_path = (args.recipe or (repo_root / RECIPE_RELPATH)).resolve()
    run_id = args.run_id
    attempt = args.attempt or default_attempt(run_id)
    analysis_root = args.analysis_root or (data_root / "analysis" / DEFAULT_ANALYSIS_ROOT_NAME)

    if not recipe_path.exists():
        print(f"REFUSED: recipe not found at {recipe_path}", file=sys.stderr)
        return 3
    recipe = load_json(recipe_path)
    read_run_id = recipe.get("read_run_id")
    if not read_run_id:
        print("REFUSED: recipe carries no read_run_id", file=sys.stderr)
        return 3

    try:
        ledger_row = assert_countersigned(repo_root, read_run_id)
        manifest = assert_completed_manifest(data_root, run_id, attempt)
    except DryRunReadError as error:
        print(str(error), file=sys.stderr)
        return 3

    trace_path = run_dir(data_root, run_id, attempt) / f"{run_id}.trace.jsonl"
    outputs_path = run_dir(data_root, run_id, attempt) / f"{run_id}.outputs.jsonl"
    if not trace_path.exists():
        print(f"REFUSED: sealed trace not found at {trace_path}", file=sys.stderr)
        return 3

    note_module, _note_module_sha256 = import_file(
        NOTE_MODULE_RELPATH, "e21_e41_perception_note_trace_read"
    )

    if args.dry_run:
        contacts, episodes = note_module.load_trace(trace_path)
        outputs_rows = load_outputs_rows(outputs_path) if outputs_path.exists() else []
        with io.open(trace_path, encoding="utf-8") as handle:
            trace_records = sum(1 for _ in handle)
        summary = {
            "mode": "dry-run (validation only; nothing written, no verdict computed)",
            "read_run_id": read_run_id,
            "recipe_id": recipe.get("recipe_id"),
            "arm": {
                "run_id": run_id, "attempt": attempt, "status": manifest.get("status"),
                "study_commit": manifest.get("study_commit"),
            },
            "counts": {
                "trace_records": trace_records, "contacts": len(contacts),
                "episodes": len(episodes), "outputs_rows": len(outputs_rows),
            },
        }
        print(json.dumps(summary, indent=1, sort_keys=True))
        return 0

    document = build_document(
        repo_root=repo_root, data_root=data_root, run_id=run_id, attempt=attempt,
        recipe_path=recipe_path, recipe=recipe, read_run_id=read_run_id,
        ledger_row=ledger_row, manifest=manifest, note_module=note_module,
    )

    analysis_root.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    io.open(analysis_root / "read.json", "w", encoding="utf-8", newline="\n").write(json_text)
    io.open(analysis_root / "read.md", "w", encoding="utf-8", newline="\n").write(render_markdown(document))

    summary = {
        "verdict": document["verdict"],
        "R1_pass": document["assertions"]["R1"]["pass"],
        "R2_pass": document["assertions"]["R2"]["pass"],
        "R3_pass": document["assertions"]["R3"]["pass"],
        "perception_truncated": document["assertions"]["R3"]["perception"]["truncated"],
        "perception_contacts": document["assertions"]["R3"]["perception"]["contacts"],
        "reviewer_truncated": document["assertions"]["R3"]["reviewer"]["truncated"],
        "windows_delivered_non_empty": sum(
            1 for w in document["assertions"]["R2"]["windows"] if w["delivered_non_empty"]
        ),
        "written_to": str(analysis_root),
    }
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
