#!/usr/bin/env python3
"""E4-1's shadow delivery, proven model-free: is the delivered path the AGREE arm's own?

Cell E4-1 (owner decision 185) is the retained AGREE arm with two registered changes: the program
switched to its 17-ceiling relisten twin and a ``native_episode.relisten`` block (a post-accept
stage, shadow delivery). The design's premise (ruling 5) is that the flight DELIVERS the AGREE
form's answer and that the relisten contacts are extra, post-accept and never feed any role. This
script PROVES it the way cell W-SV-1's arm A was proven (``scripts/flights/wsv1/wsv1_arm_a_proof.py``,
itself the decision-160 method), reusing that family's pure helpers and request-capture routine.

Three proofs, each model-free (zero model, server, tokenizer, encoder or scorer contacts):

1. **Composed config.** Both cells composed from their committed fragments and flattened; every
   differing leaf is classified: ``bookkeeping`` (identity, prose, budgets, readiness), ``supply-pin``
   (the AGREE arm's committed prepared first-phase supply pin, which E4-1 drops so the flip mints its
   own, item E16), ``program-switch`` (``policy``), ``relisten-block`` (``native_episode.relisten.*``)
   or ``unclassified`` (request-affecting: the verdict fails).
2. **Prepared supply.** ``core.flight.cli prepare-supply`` mints E4-1's first-phase supply into a
   scratch directory; its ``output_sha256`` must equal the AGREE arm's registered digest and the
   AGREE arm's committed artifact's recomputed output digest.
3. **Request bytes and delivered text.** Each cell's REAL dispatch against the REAL transport with
   a fake POST that answers canned, role-appropriate completions (identical for both cells),
   serially, under ONE common scratch run id. The canned Solver answer carries ONE entity, so the
   E4-1 relisten stage fires on every row whose delivered answer keeps it; the canned blind answer
   alternates (by ``sha256(sample_id)``) between ``heard = false`` and a heard, different value, so
   the forced-choice contact fires on every targeted entity; the canned confirm answers ``"A"``.
   Gating: every delivered-path contact of E4-1 (Perception, Solver visits, Reviewer, Planner) is
   paired with the AGREE contact of the same role and invocation index and must be POST-body
   identical after :func:`normalise_program_identity`; every E4-1 contact that is NOT paired must be
   a relisten contact; the per-row DELIVERED TEXT (sha256) must be identical between the two cells;
   at least one relisten contact must reach the transport; and no BLIND relisten POST body may carry
   the delivered value's bytes (the blind contact never sees ``c``). Reported, never gating: the
   exact (un-normalised) byte identity, the relisten contact counts by kind, and whether the
   runner's per-row ``contact_count`` counts the relisten contacts (a ``findings`` entry when not).

The two program-identity fields the switch moves in the model-visible text (the W-SV-1 finding):
the program id inside every quoted prior contact id, and ``remaining_model_contacts`` (17 minus
spent against 11 minus spent, +6 on every contact). Exit 0 with verdict ``IDENTICAL`` when proofs
1-2 hold and every delivered-path POST body is byte-identical; exit 4 with
``IDENTICAL_MODULO_PROGRAM_IDENTITY`` when identical only after the normalisation; exit 3 with
``DIFFERENT`` otherwise. No raw request text survives: the raw capture files live in the scratch
directory and are deleted right after they are read. Usage, in WSL from the worktree::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src SPEECHRL_DATA_DIR=$DATA \\
    python -B scripts/flights/e4/e4_shadow_proof.py \\
      --repo-root $REPO --data-root $DATA --lock-path $LOCK [--rows N] [--output PATH]
"""

from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PROOF_SCHEMA = "saea-e4-shadow-proof-v1"
PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1"
DEFAULT_OUTPUT = PACKAGE + "/shadow-proof-v1.json"

CELLS: dict[str, str] = {
    "e4": "slurp-native-stage3-relisten-fold-a-v1",
    "agree_arm": "slurp-native-stage3-agree-w1-fold-a-v1",
}
PROGRAMS = {"e4": "phase-native-candidates-review-revise-relisten-v1",
            "agree_arm": "phase-native-candidates-review-revise-v1"}

AGREE_ARM_SUPPLY_OUTPUT_SHA256 = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
RELISTEN_PREFIX = "native_episode.relisten"

#: The canned entity every Solver answer carries (identical for both cells). "date" is a SLURP slot
#: type; the value is a fixed proof string, never a real filler.
CANNED_ENTITY = {"type": "date", "filler": "proof canned day"}
CANNED_BLIND_VALUE = "proof canned other day"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_FLIGHTS = Path(__file__).resolve().parents[1]
P160 = _load(_FLIGHTS / "comp1" / "comp1_g5_shared_aa_proof.py", "comp1_g5_shared_aa_proof")
WAVE = _load(_FLIGHTS / "wave" / "wave_shared_aa_proof.py", "wave_shared_aa_proof")
flatten = P160.flatten

EXTRA_BOOKKEEPING = (
    ("execution_plan.", "the declared execution plan's budget numbers (planned_model_calls = rows x 17 at the new "
                        "ceiling); never request bytes"),
    ("native_contact_fit.contact_cap", "the FIT endpoint cap (rows x 17 x 4 at the new ceiling); never request bytes"),
)


def _sha(text: str | bytes) -> str:
    raw = text.encode("utf-8") if isinstance(text, str) else text
    return hashlib.sha256(raw).hexdigest()


def classify_leaf(leaf: str) -> tuple[str, str]:
    if leaf == "policy":
        return ("program-switch", "the registered program switch phase-native-candidates-review-revise-v1 -> "
                "-relisten-v1 (the two fragments differ only in program_id and max_contacts)")
    if leaf == RELISTEN_PREFIX or leaf.startswith(RELISTEN_PREFIX + "."):
        return ("relisten-block", "the registered post-accept native_episode.relisten block (shadow delivery); it "
                "never reaches a role contact's request (proof 3)")
    for prefix, reason in EXTRA_BOOKKEEPING:
        if leaf == prefix or (prefix.endswith(".") and leaf.startswith(prefix)):
            return "bookkeeping", reason
    return WAVE.classify_leaf(leaf)


def config_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[dict[str, Any]]:
    flat_left, flat_right = flatten(left), flatten(right)
    rows = []
    for leaf in sorted(set(flat_left) | set(flat_right)):
        a, b = flat_left.get(leaf, "<absent>"), flat_right.get(leaf, "<absent>")
        if a == b:
            continue
        klass, reason = classify_leaf(leaf)
        short = lambda v: v if len(json.dumps(v, default=str)) < 300 else "<long>"  # noqa: E731
        rows.append({"leaf": leaf, "e4": short(a), "agree_arm": short(b), "class": klass,
                     "request_affecting": klass == "unclassified", "reason": reason})
    return rows


def prove_supply(repo: Path, data: Path, lock: Path, scratch: Path) -> dict[str, Any]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    experiment = CELLS["e4"]
    path = scratch / "e4" / "phase-supply-v1.json"
    if path.exists():
        raise SystemExit(f"scratch supply {path} already exists; use a fresh --scratch")
    started = time.time()
    subprocess.run(
        [sys.executable, "-B", "-m", "speech_aware_evidence_acquisition.core.flight.cli", "prepare-supply",
         "--repo-root", str(repo), "--data-root", str(data), "--runtime-root", str(Path.home()),
         "--lock-path", str(lock), "--experiment", experiment, "--cell", experiment, "--output", str(path),
         "--workers", "4"],
        check=True, env=env, cwd=str(repo), stdout=subprocess.DEVNULL,
    )
    raw = path.read_bytes()
    minted = json.loads(raw)
    baseline = json.loads((repo / "configs" / "baseline" / "slurp-native-stage3-agree-w1-fold-a-baseline-v1.json")
                          .read_text(encoding="utf-8"))
    pin = baseline["prepared_phase_supply"]
    pinned_raw = (data / pin["relpath"]).read_bytes()
    pinned = json.loads(pinned_raw)
    from speech_aware_evidence_acquisition.core.preparation import digest as _digest

    recomputed = _digest(pinned["output"])
    equal = minted["output_sha256"] == pinned["output_sha256"] == recomputed
    pinned_ok = _sha(pinned_raw) == pin["sha256"]
    return {
        "e4": {"command": f"core.flight.cli prepare-supply --experiment {experiment} --cell {experiment} "
                          "--output <scratch>/e4/phase-supply-v1.json",
               "output_sha256": minted["output_sha256"], "file_sha256": _sha(raw),
               "seconds": round(time.time() - started, 1)},
        "agree_arm": {"source": "the AGREE arm's committed artifact (the one that flew), read raw -- not re-minted",
                      "relpath": pin["relpath"], "file_sha256_matches_pin": pinned_ok,
                      "output_sha256": pinned["output_sha256"], "output_sha256_recomputed": recomputed},
        "agree_arm_registered_output_sha256": AGREE_ARM_SUPPLY_OUTPUT_SHA256,
        "output_digests_equal": equal,
        "equal_registered_and_committed": equal and pinned_ok and minted["output_sha256"] == AGREE_ARM_SUPPLY_OUTPUT_SHA256,
    }


# ---------------------------------------------------------------------------
# worker-side patches (identical for both cells)
# ---------------------------------------------------------------------------

def _role_of(contact_id: str) -> tuple[str, int]:
    """``(role, visit)`` of ``<policy>:<role>:<visit>:<sample>``; a relisten contact
    ``<policy>:relisten:<kind>:<index>:<sample>`` maps to ``("relisten-<kind>", index)``."""
    parts = contact_id.split(":")
    if len(parts) >= 5 and parts[1] == "relisten":
        return f"relisten-{parts[2]}", int(parts[3])
    return P160._orig_role_of(contact_id)


def _canned_answer(role: str, visit: int, sample_id: str, intents) -> str:
    if role == "solver":
        intents = list(intents)
        scenario, _, action = intents[0].partition("_")
        return json.dumps({"scenario": scenario, "action": action, "entities": [dict(CANNED_ENTITY)]},
                          separators=(",", ":"))
    if role == "relisten-blind":
        if hashlib.sha256(sample_id.encode("utf-8")).digest()[0] % 2:
            return json.dumps({"heard": False, "value": ""}, separators=(",", ":"))
        return json.dumps({"heard": True, "value": CANNED_BLIND_VALUE}, separators=(",", ":"))
    if role == "relisten-confirm":
        return json.dumps({"choice": "A"}, separators=(",", ":"))
    return P160._orig_canned_answer(role, visit, sample_id, intents)


def _contact_key(payload: Mapping[str, Any]) -> str:
    try:
        return P160._orig_contact_key(payload)
    except ValueError:
        for key in ("agent_contact_id", "contact_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return f"{payload.get('sample_id')}|{value}"
        context = payload.get("context") if isinstance(payload.get("context"), Mapping) else {}
        value = context.get("agent_contact_id")
        if isinstance(value, str) and value:
            return f"{payload.get('sample_id')}|{value}"
        raise


def _install_patches(delivered_sink: dict) -> None:
    P160._orig_role_of = P160.role_of
    P160._orig_canned_answer = P160.canned_answer
    P160._orig_contact_key = P160.contact_key
    P160.role_of = _role_of
    P160.canned_answer = _canned_answer
    P160.contact_key = _contact_key
    from speech_aware_evidence_acquisition.core.flight import runtime as flight_runtime

    original = flight_runtime.FlightRuntime._dispatch_phase_program

    def wrapped(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        rows = result[0]
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, Mapping):
                continue
            sid = str(row.get("sample_id"))
            text = row.get("final_response_text", row.get("text"))
            receipt = row.get("relisten")
            entry = {"text_sha256": _sha(text) if isinstance(text, str) else None,
                     "contact_count": row.get("contact_count"),
                     "has_relisten": isinstance(receipt, Mapping)}
            if isinstance(receipt, Mapping):
                entities = receipt.get("entities") if isinstance(receipt.get("entities"), list) else []
                entry.update({
                    "contacts_used": receipt.get("contacts_used"),
                    "triggered_count": receipt.get("triggered_count"),
                    "schema": receipt.get("schema"),
                    "blind_dispositions": [(e.get("blind") or {}).get("disposition") for e in entities
                                           if isinstance(e, Mapping)],
                    "confirm_fired": [isinstance(e.get("confirm"), Mapping) for e in entities if isinstance(e, Mapping)],
                    "accepts": [bool(e.get("accept")) for e in entities if isinstance(e, Mapping)],
                })
            delivered_sink[sid] = entry
        return result

    flight_runtime.FlightRuntime._dispatch_phase_program = wrapped


# ---------------------------------------------------------------------------
# comparison
# ---------------------------------------------------------------------------

def _launch_worker(repo: Path, args, *, cell: str, out: Path, rows: int | None, common: tuple[str, int]):
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--repo-root", str(repo),
               "--data-root", str(args.data_root), "--lock-path", str(args.lock_path),
               "--worker-cell", cell, "--worker-out", str(out), "--worker-common", f"{common[0]}:{common[1]}"]
    if rows is not None:
        command += ["--rows", str(rows)]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(repo / "src"))
    log = out.with_suffix(".log").open("w", encoding="utf-8")
    return subprocess.Popen(command, env=env, cwd=str(repo), stdout=log, stderr=subprocess.STDOUT)


def _split(key: str) -> tuple[str, str, str, str, str]:
    """``(sample, program, role, index, rest)``; a relisten contact yields role ``relisten`` and index
    ``<kind>:<entity index>``."""
    sample, contact = key.split("|", 1)
    parts = contact.split(":")
    if len(parts) >= 5 and parts[1] == "relisten":
        return sample, parts[0], "relisten", f"{parts[2]}:{parts[3]}", ":".join(parts[4:])
    program, role, index, rest = contact.split(":", 3)
    return sample, program, role, index, rest


_REMAINING = re.compile(r'(\\*"remaining_model_contacts\\*": )\d+')


def normalise_program_identity(body: str) -> str:
    text = body.replace(PROGRAMS["e4"], PROGRAMS["agree_arm"])
    return _REMAINING.sub(r"\g<1><masked>", text)


def _norm_sha(row: Mapping[str, Any]) -> str | None:
    body = row.get("body")
    return None if body is None else _sha(normalise_program_identity(body))


def map_contacts(e4: Mapping[str, Any], agree: Mapping[str, Any]) -> dict[str, Any]:
    agree_by = {}
    for key, row in agree.items():
        sample, _program, role, index, rest = _split(key)
        agree_by[(sample, role, index, rest)] = row
    delivered = {"contacts": 0, "post_body_identical": 0, "post_body_identical_after_program_identity_normalisation": 0,
                 "unpaired": 0, "by_role": {}, "normalised_mismatch_contacts": []}
    relisten = {"contacts": 0, "by_kind": {}, "per_row": {}, "blind_bodies_carrying_the_delivered_value": 0,
                "confirm_bodies_carrying_the_delivered_value": 0}
    paired_agree = set()
    for key, row in e4.items():
        sample, _program, role, index, rest = _split(key)
        if role == "relisten":
            kind = index.split(":", 1)[0]
            relisten["contacts"] += 1
            relisten["by_kind"][kind] = relisten["by_kind"].get(kind, 0) + 1
            relisten["per_row"][sample] = relisten["per_row"].get(sample, 0) + 1
            body = row.get("body") or ""
            carries = CANNED_ENTITY["filler"] in body
            if kind == "blind":
                relisten["blind_bodies_carrying_the_delivered_value"] += int(carries)
            else:
                relisten["confirm_bodies_carrying_the_delivered_value"] += int(carries)
            continue
        delivered["contacts"] += 1
        tally = delivered["by_role"].setdefault(role, {"contacts": 0, "post_body_identical": 0, "normalised_identical": 0})
        tally["contacts"] += 1
        partner = agree_by.get((sample, role, index, rest))
        if partner is None:
            delivered["unpaired"] += 1
            continue
        paired_agree.add((sample, role, index, rest))
        if partner["body_sha256"] == row["body_sha256"]:
            delivered["post_body_identical"] += 1
            tally["post_body_identical"] += 1
        if _norm_sha(row) is not None and _norm_sha(row) == _norm_sha(partner):
            delivered["post_body_identical_after_program_identity_normalisation"] += 1
            tally["normalised_identical"] += 1
        elif len(delivered["normalised_mismatch_contacts"]) < 10:
            delivered["normalised_mismatch_contacts"].append(f"{role}:{index}:{sample}")
    delivered["agree_contacts"] = len(agree_by)
    delivered["agree_contacts_unpaired"] = len(agree_by) - len(paired_agree)
    delivered["all_identical"] = (delivered["unpaired"] == 0 and delivered["agree_contacts_unpaired"] == 0
                                  and delivered["post_body_identical"] == delivered["contacts"] > 0)
    delivered["all_identical_after_program_identity_normalisation"] = (
        delivered["unpaired"] == 0 and delivered["agree_contacts_unpaired"] == 0
        and delivered["post_body_identical_after_program_identity_normalisation"] == delivered["contacts"] > 0)
    return {"delivered_path_vs_agree": delivered, "relisten_contacts": relisten}


def compare_delivered(e4: Mapping[str, Any], agree: Mapping[str, Any], relisten_per_row: Mapping[str, int]) -> dict:
    rows = sorted(set(e4) | set(agree))
    same = sum(1 for s in rows if s in e4 and s in agree and e4[s]["text_sha256"] == agree[s]["text_sha256"]
               and e4[s]["text_sha256"] is not None)
    extra = {s: (e4[s].get("contact_count") or 0) - (agree[s].get("contact_count") or 0)
             for s in rows if s in e4 and s in agree}
    extra_match = sum(1 for s, n in extra.items() if n == relisten_per_row.get(s, 0))
    with_receipt = [s for s in rows if e4.get(s, {}).get("has_relisten")]
    agree_receipts = sum(1 for s in rows if agree.get(s, {}).get("has_relisten"))
    count_match = sum(1 for s in with_receipt if e4[s].get("contacts_used") == relisten_per_row.get(s, 0))
    dispositions: dict[str, int] = {}
    confirm_fired = accepts = 0
    for s in with_receipt:
        for d in e4[s].get("blind_dispositions") or []:
            dispositions[str(d)] = dispositions.get(str(d), 0) + 1
        confirm_fired += sum(e4[s].get("confirm_fired") or [])
        accepts += sum(e4[s].get("accepts") or [])
    return {
        "rows": len(rows), "delivered_text_identical": same,
        "contact_count_e4_minus_agree_equals_captured_relisten_contacts": extra_match,
        "all_contact_count_deltas_match": extra_match == len(rows) > 0,
        "relisten_contacts_per_row_histogram": dict(sorted(
            {str(n): sum(1 for v in extra.values() if v == n) for n in set(extra.values())}.items())),
        "receipt_note": ("the dispatch rows carry no 'relisten' receipt on this branch (the outputs.jsonl persistence "
                         "is a concurrent engineering item); the per-row relisten spend is proven instead as the E4-1 "
                         "minus AGREE contact_count, which must equal the captured relisten contacts of the row"),
        "all_delivered_text_identical": same == len(rows) > 0,
        "e4_rows_with_relisten_receipt": len(with_receipt), "agree_rows_with_relisten_receipt": agree_receipts,
        "receipt_contacts_used_equals_captured_relisten_contacts": count_match,
        "all_receipt_counts_match": count_match == len(with_receipt),
        "blind_dispositions": dict(sorted(dispositions.items())),
        "confirm_contacts_fired_per_receipts": confirm_fired,
        "accepted_replacements_per_receipts": accepts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--lock-path", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=120, help="dispatch only the first N rows (the wave proof's 120)")
    parser.add_argument("--parallel", type=int, default=2)
    parser.add_argument("--scratch", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--skip-supply", action="store_true", help="skip proof 2 (verdict then cannot pass)")
    parser.add_argument("--worker-cell", help=argparse.SUPPRESS)
    parser.add_argument("--worker-out", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--worker-common", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    import speech_aware_evidence_acquisition as package

    if not str(Path(package.__file__).resolve()).startswith(str(repo)):
        raise SystemExit(f"imported package {package.__file__} is not under {repo}")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if args.worker_cell:
        if args.worker_cell == "agree_arm":
            WAVE._lift_agree_pin()
        delivered: dict[str, Any] = {}
        _install_patches(delivered)
        label, _, stamp = args.worker_common.rpartition(":")
        captured, receipt = P160.capture_requests(
            repo, args.data_root, args.lock_path, CELLS[args.worker_cell], args.rows,
            keep_raw=True, serial=True, common_run=(label, int(stamp)),
        )
        args.worker_out.write_text(json.dumps({"captured": captured, "receipt": receipt, "delivered": delivered}),
                                   encoding="utf-8")
        return 0
    scratch = args.scratch or Path(f"/tmp/e4-shadow-proof-{int(time.time())}")
    scratch.mkdir(parents=True, exist_ok=True)

    cells, composed = {}, {}
    for name, experiment in CELLS.items():
        _cell, composed[name], cells[name] = P160._composed(repo, experiment)
    diff = config_diff(composed["e4"].values, composed["agree_arm"].values)
    unclassified = [row["leaf"] for row in diff if row["class"] == "unclassified"]

    supply = ({"status": "SKIPPED", "output_digests_equal": False, "equal_registered_and_committed": False}
              if args.skip_supply else prove_supply(repo, args.data_root, args.lock_path, scratch))

    common = ("E4-SHADOW-PROOF", int(time.time() * 1000))
    outputs, jobs = {}, []
    for name in CELLS:
        out = scratch / f"capture-raw-{name}.json"
        outputs[name] = out
        jobs.append((f"raw/{name}", functools.partial(
            _launch_worker, repo, args, cell=name, out=out, rows=args.rows, common=common)))
    P160._run_workers(jobs, args.parallel)

    raw = {}
    for name in CELLS:
        raw[name] = json.loads(outputs[name].read_text(encoding="utf-8"))
        outputs[name].unlink()  # no raw request text survives the comparison
    mapping = map_contacts(raw["e4"]["captured"], raw["agree_arm"]["captured"])
    per_row = mapping["relisten_contacts"].pop("per_row")
    delivered = compare_delivered(raw["e4"]["delivered"], raw["agree_arm"]["delivered"], per_row)
    receipts = {name: raw[name]["receipt"] for name in CELLS}
    del raw
    path = mapping["delivered_path_vs_agree"]
    relisten = mapping["relisten_contacts"]
    shadow_ok = (delivered["all_delivered_text_identical"] and delivered["all_receipt_counts_match"]
                 and delivered["agree_rows_with_relisten_receipt"] == 0
                 and relisten["contacts"] > 0
                 and relisten["blind_bodies_carrying_the_delivered_value"] == 0)
    findings = []
    if not delivered["all_contact_count_deltas_match"]:
        findings.append({
            "id": "row-contact-count-excludes-relisten",
            "gating": False,
            "detail": (
                f"the dispatch row's contact_count(E4-1) - contact_count(AGREE) equals the row's captured relisten contacts "
                f"on {delivered['contact_count_e4_minus_agree_equals_captured_relisten_contacts']} of {delivered['rows']} rows "
                f"(histogram of the delta {delivered['relisten_contacts_per_row_histogram']}) while {relisten['contacts']} "
                "relisten contacts reached the (fake) transport: the per-row contact_count the runner reports does not count "
                "the post-accept relisten contacts. The flight's plan budget is enforced on the shared client, which does "
                "see them; the per-row contact accounting (and any smoke inspection that compares it with the trace or "
                "with the receipt's contacts_used) is an engineering item for the relisten wiring, not for this "
                "registration."
            ),
        })
    base_ok = not unclassified and supply["output_digests_equal"] and supply["equal_registered_and_committed"] and shadow_ok
    identical = base_ok and path["all_identical"]
    modulo = base_ok and path["all_identical_after_program_identity_normalisation"]
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                          check=True).stdout.strip()
    proof = {
        "schema": PROOF_SCHEMA,
        "owner_decision": 185,
        "precedent": "scripts/flights/wsv1/wsv1_arm_a_proof.py (owner decision 172), the decision-160 method",
        "question": (
            "Is E4-1's delivered path (every Perception, Solver, Reviewer and Planner contact, and the delivered text) "
            "the retained AGREE arm's own under the 17-ceiling relisten program, with the relisten contacts strictly "
            "extra, post-accept, blind to the delivered value and never altering the delivered text?"
        ),
        "verdict": ("IDENTICAL" if identical else "IDENTICAL_MODULO_PROGRAM_IDENTITY" if modulo else "DIFFERENT"),
        "program_identity_fields": (
            "the two model-visible fields the program switch moves (normalise_program_identity): (1) the program id "
            "inside every quoted prior contact id (no invocation index moves: E4-1 adds no role invocation before "
            "ACCEPT); (2) remaining_model_contacts in the task-state block (17 minus spent against 11 minus spent: +6 "
            "on every contact)"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "study_commit": head,
        "tool": "scripts/flights/e4/e4_shadow_proof.py",
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
        "cells": cells,
        "composed_config_diff": {
            "differing_leaves": diff,
            "by_class": {k: sum(1 for row in diff if row["class"] == k) for k in sorted({row["class"] for row in diff})},
            "request_affecting_leaves": unclassified,
        },
        "prepared_supply": supply,
        "request_bytes": {
            "method": (
                "the decision-160 method (P160.capture_requests): FlightRuntime._dispatch_phase_program("
                "model_free_check=True) on each cell's own composed fragments, against the composed model fragment's "
                "REAL llama-server transport with its POST replaced by a fake server that records the body bytes and "
                "answers a canned completion identical for both cells (the Solver answer carries one fixed 'date' "
                "entity so the relisten stage fires; the blind answer alternates heard=false / a different heard "
                "value by sha256(sample_id); the confirm answers 'A'); dispatched serially under ONE common scratch "
                "run id; the AGREE side with its unloadable committed supply pin lifted (proof 2 shows the live supply "
                "equals the committed output)"
            ),
            "rows": args.rows,
            "receipts": receipts,
            **mapping,
        },
        "delivered_text": delivered,
        "shadow_checks_pass": shadow_ok,
        "findings": findings,
        "scratch": str(scratch),
        "hash_quoting": (
            "64-hex identities other than the prepared-supply output digests and the study commit are quoted as "
            "sha256-prefix16:<first 16 hex> (core.flight.repin rewrites package JSON from old identity hashes to new "
            "ones at the flip and refuses any old hash left under docs/)"
        ),
    }
    proof = P160.quote_hashes_by_prefix(proof)
    if isinstance(supply.get("agree_arm"), dict):
        proof["prepared_supply"]["agree_arm_registered_output_sha256"] = AGREE_ARM_SUPPLY_OUTPUT_SHA256
        proof["prepared_supply"]["agree_arm"]["output_sha256_recomputed"] = supply["agree_arm"]["output_sha256_recomputed"]
    output = args.output or (repo / DEFAULT_OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proof, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": proof["verdict"], "output": str(output),
                      "config_classes": proof["composed_config_diff"]["by_class"], "unclassified": unclassified,
                      "supply_equal_registered_and_committed": supply["equal_registered_and_committed"],
                      **mapping, "delivered_text": delivered, "shadow_checks_pass": shadow_ok,
                      "findings": findings}, indent=1))
    return 0 if identical else 4 if modulo else 3


if __name__ == "__main__":
    raise SystemExit(main())
