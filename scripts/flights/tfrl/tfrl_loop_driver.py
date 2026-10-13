#!/usr/bin/env python3
"""The autonomous typed-loop driver (decision 263-A, design section 7): ``open --iter t`` / ``close --iter t`` / ``status``.

MODEL-FREE and 0 GPU. Every step is idempotent (a re-run with the same inputs is a no-op; a changed input is refused), writes a
receipt JSON under ``<package>/iterations/i<t>/``, refuses to run while a batch driver, a flight or a flip loop runs, and refuses to
run when the loop protocol's sha256 differs from the one pinned at the first ``open``. Nothing is written under the data root except
analysis outputs under ``analysis/SAEA-SLURP-TFRL-LOOP-V1/`` (the tables, the proposer artefacts, the playbook, the credit files).

THE FLOW (a GPU step sits between ``open --stage propose`` and ``open --stage cell``):

    open  --iter t --stage propose   tables from the sealed CONSTRUCTION-SOURCE lock column (R01C, every iteration: the lock does not change),
                                     the proposer / reflector artefacts, the two text-only cells (HELD, DRAFT ledger rows)  -> countersign checklist
    [coordinator: countersign, mint, flip, queue; GPU flies the proposer + reflector cells]
    open  --iter t --stage cell      validate the sealed candidates, curate the ACE playbook i(t), derive the column cell and its
                                     smoke (HELD, DRAFT rows), print the gates                              -> countersign checklist
    [coordinator: countersign, mint, flip, queue; GPU flies the column]
    close --iter t                   score the columns, node-local and paired reads, credit vectors, the preregistered selection rule,
                                     archive (accepted / refused / unflown), curve, meta summary, parent choice, ACE credit file
                                                                                                           -> next-iteration checklist

ARCHIVED DUPLICATES. A candidate whose artefact set equals a state archived in an earlier iteration (any status) is refused at ``open --stage cell``
as ``duplicate-of-archived`` (receipt ``duplicates_of_archived``, ``candidates.json`` ``refused``, the proposer's next refused buffer); an offline
duplicate is still re-measured at ``close`` and recorded as ``archive/rereads/<state-id>-i<t>.json`` (never a state, never a parent). A fitted
artefact set that only collides at ``close`` is recorded the same way. ``repair --iter t --duplicates-only`` applies the classification to an
iteration opened before the rule existed. ``close`` exports the per-row official scores itself (``row-scores-i<t>.json``) and always builds the
ACE credit file; ``--row-scores`` is only an override.

External analysis scripts (tables, rollout score, node-local reader, paired read, delivery fit) run only with ``--execute``;
without it the driver prints the command it would run and stops before any archive write ("planned").

MATERIAL SOURCE (coordinator resolution of 2026-10-11 to decision 263-A). The proposer's tables and the ACE reflector's material come from ONE
column flown on the construction roster R01C (``tf.CONST_*``), never from Fold B: the semantic-knowledge preparer forbids Fold B rows as carrier
ids of a delta-store registration (the construction-roster vs knowledge guard), Fold B is the held-out selection split and Fold A confirms.
Iterations 2-3 read the previous iteration's FOLD B read only for the refused-candidate buffer and the ACE counters (credit over the Fold B
``ace`` column versus ``lock``): counters are numbers, not knowledge. ACE release staging uses the committed ``stage3-deltas-v1r`` rosters
(construction scope R01C, permitted roster = a subset of R01C, forbidden Fold A / Fold B / DEV-1000) so the preparer accepts releases i1+.

Interface adaptations written in ``tfrl_loop_lib.py`` and reported: E-T3 tables -> E-T1 artefact and E-T2 material; E-T4 archive ->
E-T1 context; paired-read bytes -> credit vectors; the ACE counters' credit file is written at ``close`` and consumed by the next
``open --stage cell`` (where the reflector's deltas are first available), not at ``close``.
"""

from __future__ import annotations

import argparse
import datetime
import importlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tfrl_family as tf  # noqa: E402
import tfrl_loop_lib as lib  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
#: The tables source of EVERY iteration: the sealed construction-source lock column (``tf.CONST_RUN_ID`` / ``tf.CONST_ATTEMPT_ID``, delivering arm
#: ``lock``, TRAIN roster R01C, 625 rows), which has per-row official scores on disk. ``--source-run-id`` / ``--source-attempt`` override (tests,
#: recovery) and are recorded in the receipt. The ACE release's carrier rosters are the ``stage3-deltas-v1r`` ones (ace-playbook i0 registration).
ACE_I0_REGISTRATION = f"{tf.PACKAGE_DIR}/ace-playbook-i0-release-registration.json"
TABLES_SCRIPT = "scripts/analysis/tfrl_contrast_tables.py"
DELIVERY_FIT_SCRIPT = "scripts/analysis/tfrl_delivery_fit.py"
ROLLOUT_SCORE_SCRIPT = "scripts/analysis/stage3_rollout_score.py"
NODE_LOCAL_SCRIPT = "scripts/analysis/slurp_nx_solver_column_read.py"
PAIRED_READ_SCRIPT = "scripts/analysis/stage3_paired_read.py"
#: operator -> the archive artefact it edits (design 2 table); the digest is provisional until the E-T6 release builders land.
ARTEFACT_OF = {"exemplar-selection": "exemplar_index_release", "slot-card-subset": "slot_store_release", "knob-set": "supply_fragment",
               "deliver-rule": "delivery_rule_table", "scope-restrict": "scope_routing"}
FIT_FAMILY = {"ee5": "ee", "ee10": "ee", "ti0": "ti", "ti1": "ti", "fx-article": "article", "fx-oclock": "oclock"}
#: The refusal code of an offline candidate whose family the fitter cannot read: the candidate is archived as REFUSED (unmeasured), never skipped.
OFFLINE_UNSUPPORTED = "offline-family-unsupported"
#: A valid candidate whose artefact set equals a state archived in an EARLIER iteration (any status) is a duplicate of that sibling: refused at
#: ``open --stage cell`` with this code, never flown or read as a new state (``close`` records a re-measurement as a reread instead).
DUPLICATE_OF_ARCHIVED = "duplicate-of-archived"
ROW_SCORES_SCRIPT = "scripts/flights/tfrl/tfrl_row_scores.py"
ROOT_DISPLAY = "s0-lock-v2.2"


@dataclass
class Ctx:
    repo_root: Path
    package_dir: Path
    data_root: Path
    lock_path: Path
    runner: lib.Runner
    lister: Callable[[], "list[str] | None"] | None = None
    skip_guard: bool = False
    out: Callable[[str], None] = print

    def receipts(self, t: int) -> Path:
        return self.package_dir / "iterations" / f"i{t}"

    def analysis(self, t: int) -> Path:
        return self.data_root / tf.ANALYSIS_ROOT / f"i{t}"

    def archive(self):
        from speech_aware_evidence_acquisition.analysis.sealed_credit.archive import Archive  # noqa: PLC0415

        return Archive(self.package_dir / "archive")


# ---------------------------------------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def display_id(state: Mapping[str, Any]) -> str:
    return ROOT_DISPLAY if (state["iteration"] == 0 and state["arm"] == "typed") else state["state_id"][:48]


def resolve_display(states: list[Mapping[str, Any]], shown: str) -> Mapping[str, Any]:
    for s in states:
        if display_id(s) == shown or s["state_id"] == shown:
            return s
    raise lib.LoopError(f"no archived state is shown as {shown!r}")


def sha_file(path: Path) -> str:
    return tf.sha256_file(path)


def pin_of(ctx: Ctx, path: Path) -> dict:
    """A ``{relpath, sha256}`` pin of an analysis artefact, data-root relative."""

    return {"relpath": path.relative_to(ctx.data_root).as_posix(), "sha256": sha_file(path)}


def read_or_none(path: Path) -> Any:
    return _load_json(path) if Path(path).is_file() else None


def need_receipt(ctx: Ctx, t: int, step: str) -> dict:
    receipt = lib.read_receipt(ctx.receipts(t), step)
    if receipt is None:
        raise lib.MissingInput(f"iteration {t}: no {step} receipt (run the earlier step first)")
    return receipt


def start(ctx: Ctx, t: int, *, pin: bool) -> dict:
    if t not in tf.ITERATIONS:
        raise lib.LoopError(f"iteration must be one of {tf.ITERATIONS}")
    lib.refuse_if_busy(ctx.lister, skip=ctx.skip_guard)
    protocol = lib.check_protocol(ctx.package_dir, pin=pin)
    ctx.receipts(t).mkdir(parents=True, exist_ok=True)
    return protocol


def ensure_roots(ctx: Ctx) -> dict[str, str]:
    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    return lib.ensure_root_states(ctx.archive(), lock_hash=lib.lock_root_hash(ctx.repo_root),
                                  empty_playbook_content_hash=ace.empty_playbook()["content_hash"])


def operators_by_candidate(ctx: Ctx) -> dict[str, str]:
    """``{candidate_id: operator}`` from every iteration's candidate record (the archive stores the class only)."""

    out: dict[str, str] = {}
    for t in tf.ITERATIONS:
        record = read_or_none(ctx.receipts(t) / "candidates.json")
        for entry in (record or {}).get("candidates", []):
            out[entry["candidate_id"]] = entry["operator"]
    return out


def refused_buffer(ctx: Ctx, before_iteration: int) -> list[dict]:
    """E-T1's rejected-edit buffer: validator refusals of every earlier iteration plus the instrument-refused flown children."""

    rows: list[dict] = []
    for t in range(1, before_iteration):
        record = read_or_none(ctx.receipts(t) / "candidates.json") or {}
        for entry in record.get("refused", []):
            rows.append({"candidate_id": entry["candidate_id"][:16], "operator_class": entry["operator_class"],
                         "operator": entry["operator"], "refusal_code": entry["refusal_code"],
                         **({"predicted_slu_pp": entry["predicted_slu_pp"]} if entry.get("predicted_slu_pp") is not None else {}),
                         **({"realised_d_slu_pp": entry["realised_d_slu_pp"]} if entry.get("realised_d_slu_pp") is not None else {}),
                         # a duplicate shows which archived sibling it re-proposed (16-hex prefix) and that sibling's verdict
                         **({"archived_state_id": entry["archived_state_id"][:16], "archived_status": entry["archived_status"]}
                            if entry.get("archived_state_id") else {}),
                         "iteration": t})
    ops = operators_by_candidate(ctx)
    for s in ctx.archive().states():
        if s["arm"] == "typed" and s["verdict"] == "refused" and s["iteration"] < before_iteration:
            if s.get("credit") is None:         # an unmeasured refusal: the code is the whole record
                rows.append({"candidate_id": (s["candidate_id"] or "")[:16], "operator_class": s["operator_class"],
                             "operator": ops.get(s["candidate_id"] or "", "unknown"), "refusal_code": s.get("refusal_code", "unmeasured"),
                             **({"predicted_slu_pp": s["predicted_slu_pp"]} if s.get("predicted_slu_pp") is not None else {}),
                             "iteration": s["iteration"]})
                continue
            block = s["credit"].get("vs_parent") or s["credit"]["vs_lock"]
            rows.append({"candidate_id": (s["candidate_id"] or "")[:16], "operator_class": s["operator_class"],
                         "operator": ops.get(s["candidate_id"] or "", "unknown"), "refusal_code": "refused-by-instrument",
                         **({"predicted_slu_pp": s["predicted_slu_pp"]} if s.get("predicted_slu_pp") is not None else {}),
                         "realised_d_slu_pp": block["slu"]["point"], "iteration": s["iteration"]})
    return rows


def source_column(ctx: Ctx, t: int, a: argparse.Namespace) -> dict:
    """The sealed, officially scored column the tables of iteration t are read from: the CONSTRUCTION-SOURCE lock column, for every t.

    The lock does not change between iterations, so one column on the construction roster R01C serves iterations 1-3; no Fold B row is a
    material source (the delta-store preparer forbids Fold B carriers). The previous iteration's Fold B read enters only through the
    refused-candidate buffer and the ACE counters (numbers, not knowledge)."""

    override = bool(a.source_run_id or a.source_attempt or a.source_scorer)
    return {"run_id": a.source_run_id or tf.CONST_RUN_ID, "attempt": a.source_attempt or tf.CONST_ATTEMPT_ID,
            "scorer": a.source_scorer or tf.CONST_SCORER, "arm": tf.CONST_ARM, "rows": tf.CONST_ROWS, "split": "train",
            "roster": tf.CONST_ROSTER["arm"], "roster_id": tf.CONST_ROSTER_ID, "override": override,
            "note": ("the sealed construction-source lock column (plain lock, roster R01C); the same column serves every iteration. "
                     "Fold B is the held-out selection split and contributes only counters and the refused-candidate buffer.")}


def load_enums(ctx: Ctx, a: argparse.Namespace, tables: Mapping[str, Any]) -> dict:
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    if a.enums_file:
        doc = _load_json(Path(a.enums_file))
        return {"slot_types": list(doc["slot_types"]), "intents": list(doc["intents"]),
                "scenarios": list(doc.get("scenarios") or tp.SCENARIOS)}
    if getattr(a, "enums_from_gold", False):
        import importlib.util  # noqa: PLC0415

        spec = importlib.util.spec_from_file_location("v4s", ctx.repo_root / "scripts/analysis/slurp_nx_postproc_v4_search.py")
        module = importlib.util.module_from_spec(spec)       # type: ignore[arg-type]
        sys.modules[spec.name] = module                      # type: ignore[union-attr]
        spec.loader.exec_module(module)                      # type: ignore[union-attr]
        from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

        gold = module.load_gold(load_lock(ctx.lock_path), ctx.data_root, "train")
        types = sorted({e.type for g in gold.values() for e in g["entities"]})
        intents = sorted({f"{g['scenario']}_{g['action']}" for g in gold.values()})
        return {"slot_types": types, "intents": intents, "scenarios": list(tp.SCENARIOS)}
    raise lib.MissingInput("pass --enums-file {slot_types, intents[, scenarios]} or --enums-from-gold (TRAIN gold, offline)")


# ---------------------------------------------------------------------------------------------------------------------------
# the playbook of an iteration: keyed by CONTENT, bound to the release that flew
# ---------------------------------------------------------------------------------------------------------------------------


def playbook_file(ctx: Ctx, t: int) -> Path:
    return ctx.analysis(t) / "playbook" / f"playbook-i{t}.json"


def staging_playbook_file(ctx: Ctx, t: int) -> Path:
    return ctx.analysis(t) / "ace-release-staging" / f"playbook-i{t}.json"


def write_playbook_keyed(path: Path, playbook: Mapping[str, Any]) -> str:
    """Write ``playbook`` at ``path`` keyed by content: a file that already holds the same content hash is left alone; a file that holds a
    DIFFERENT one is kept as ``<stem>.superseded-<mtime>.json`` and replaced. Returns ``written`` / ``unchanged`` / ``rewritten``."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    path = Path(path)
    if not path.exists():
        ace.write_playbook(path, playbook)
        return "written"
    if json.loads(path.read_text(encoding="utf-8")).get("content_hash") == playbook["content_hash"]:
        return "unchanged"
    stamp = datetime.datetime.fromtimestamp(path.stat().st_mtime, tz=datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = path.with_name(f"{path.stem}.superseded-{stamp}.json")
    n = 1
    while target.exists():
        n += 1
        target = path.with_name(f"{path.stem}.superseded-{stamp}-{n}.json")
    path.rename(target)
    ace.write_playbook(path, playbook)
    return "rewritten"


def resolve_playbook(ctx: Ctx, t: int) -> tuple[Path, Mapping[str, Any]]:
    """The playbook iteration ``t`` flew: the file whose content hash equals the one its open-cell receipt records. The staging playbook the
    release was built from is tried first, then ``playbook/playbook-i<t>.json``; no file with that hash is an error (never a silent
    fallback to a stale file)."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    receipt = lib.read_receipt(ctx.receipts(t), "open-cell") or {}
    want = (receipt.get("ace") or {}).get("playbook_content_hash")
    order = [staging_playbook_file(ctx, t), playbook_file(ctx, t)] if (receipt.get("ace") or {}).get("release_staging") \
        else [playbook_file(ctx, t), staging_playbook_file(ctx, t)]
    for path in order:
        if path.is_file():
            playbook = ace.load_playbook(path)
            if want is None or playbook["content_hash"] == want:
                return path, playbook
    raise lib.LoopError(f"iteration {t}: no playbook file carries the content hash its open-cell receipt records ({str(want)[:12]}); "
                        f"run `repair --iter {t}`")


def assert_playbook_binding(ctx: Ctx, t: int, opened: Mapping[str, Any], playbook: Mapping[str, Any]) -> str:
    """The state's ``playbook_release`` hash must equal the hash of the playbook behind the pinned release: the open-cell receipt's hash and,
    when the release was staged, the staging playbook's. Returns that hash."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    behind = opened["ace"]["playbook_content_hash"]
    staged = staging_playbook_file(ctx, t)
    if staged.is_file():
        staged_hash = ace.load_playbook(staged)["content_hash"]
        if staged_hash != behind:
            raise lib.LoopError(f"iteration {t}: the staged release playbook ({staged_hash[:12]}) is not the one the open-cell receipt "
                                f"records ({behind[:12]})")
    if playbook["content_hash"] != behind:
        raise lib.LoopError(f"iteration {t}: the playbook to archive ({playbook['content_hash'][:12]}) is not the one behind the pinned "
                            f"release ({behind[:12]})")
    return behind


def checklist(ctx: Ctx, title: str, items: list[str]) -> list[str]:
    lines = [f"== {title} =="] + [f"  [{k + 1}] {text}" for k, text in enumerate(items)]
    for line in lines:
        ctx.out(line)
    return lines


# ---------------------------------------------------------------------------------------------------------------------------
# open: propose stage
# ---------------------------------------------------------------------------------------------------------------------------


def open_propose(ctx: Ctx, t: int, a: argparse.Namespace) -> dict:
    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    start(ctx, t, pin=True)
    if t > 1:
        need_receipt(ctx, t - 1, "close")
    if lib.read_receipt(ctx.receipts(t), "open-cell"):
        raise lib.LoopError(f"iteration {t} is already past its propose stage")
    roots = ensure_roots(ctx)
    src = source_column(ctx, t, a)
    A = ctx.analysis(t)
    tables_path = A / "tables" / "tables-v1.json"
    argv = [TABLES_SCRIPT, "--run-id", src["run_id"], "--attempt", src["attempt"], "--arm", src["arm"], "--scorer", src["scorer"],
            "--split", src["split"], "--rows", src["rows"], "--data-root", ctx.data_root, "--lock", ctx.lock_path,
            "--out-dir", A / "tables"]
    ctx.runner.run("tables", argv, produces=[tables_path])
    if ctx.runner.planned:
        return {"status": "planned", "commands": [r.argv for r in ctx.runner.planned]}
    tables = _load_json(tables_path)
    enums = load_enums(ctx, a, tables)
    states = ctx.archive().states()
    typed_states = [s for s in states if s["arm"] == "typed"]
    parent_record = read_or_none(ctx.receipts(t - 1) / "parent.json") if t > 1 else None
    parent_state = (resolve_display(states, parent_record["parent_display_id"]) if parent_record
                    else next(s for s in typed_states if s["iteration"] == 0))
    ops = operators_by_candidate(ctx)
    proposer_tables = lib.adapt_tables_for_proposer(tables, iteration=t, enums=enums, states=typed_states, operators=ops)
    tables_pin_path = A / "proposer-tables.json"
    lib.write_json_new(tables_pin_path, proposer_tables)
    from speech_aware_evidence_acquisition.analysis.sealed_credit import meta_summary  # noqa: PLC0415

    meta_summary.build_meta_summary(states, "typed")          # asserts the never-shipped document is clean
    archive_sha = lib.archive_sha256(ctx.package_dir / "archive")
    context = lib.build_proposer_context(iteration=t, parent_state_id=display_id(parent_state), archive_sha256=archive_sha,
                                         refused_buffer=refused_buffer(ctx, t), states=states)
    context_path = A / "proposer-context.json"
    lib.write_json_new(context_path, context)
    # the ACE playbook in force and its reflector materials (one per scenario)
    if t == 1:
        playbook = ace.empty_playbook()
        playbook_path = A / "playbook" / "playbook-i0.json"
        if not playbook_path.exists():
            ace.write_playbook(playbook_path, playbook)
    else:
        playbook_path, loaded = resolve_playbook(ctx, t - 1)
        playbook = dict(loaded)
    credit_receipt_sha = sha_file(tables_path)
    materials: dict[str, dict] = {}
    for scenario in tp.SCENARIOS:
        material = lib.build_reflector_material(
            tables, scenario=scenario, iteration=t - 1 if t > 1 else 0, column_arm="lock", run_id=src["run_id"],
            credit_receipt_sha256=credit_receipt_sha, playbook=playbook)
        path = A / "ace-material" / f"material-{scenario}.json"
        lib.write_json_new(path, material)
        materials[scenario] = pin_of(ctx, path)
    p99 = a.lock_p99_supplied_tokens
    if p99 is None:
        p99 = (((tables.get("table_d") or {}).get("overall") or {}).get("supplied_tokens") or {}).get("p99")
    if p99 is None:
        raise lib.MissingInput("T_cap needs the MEASURED lock p99 of supplied tokens: pass --lock-p99-supplied-tokens (the tables ran "
                               "with the trace pass skipped, or the p99 cell is suppressed)")
    constants = ace.with_measured_lock_p99(int(round(float(p99))))
    t_cap = ace.resolve_t_cap(constants)
    pins = {
        "typed": {"tables": pin_of(ctx, tables_pin_path), "context": pin_of(ctx, context_path)},
        "ace": {"playbook": pin_of(ctx, playbook_path), "token_cap": t_cap, "materials": materials},
    }
    registered: dict[str, Any] = {"status": "not-registered"}
    if not a.no_register:
        import write_tfrl_iteration_registration as reg  # noqa: PLC0415

        commit = a.study_commit or "0" * 40
        at = a.registered_at or "%sT00:00:00.000000+00:00" % tf.DATE
        for kind in ("typed", "ace"):
            import derive_tfrl_iteration_cells as dv  # noqa: PLC0415

            dv.derive_text_only(t, kind, pins[kind], repo_root=ctx.repo_root)
        proposers = reg.proposers_package(ctx.repo_root, t, commit, at)
        # prompt_sha256 is omitted: the writer resolves it from configs/probes/tfrl/{typed-proposer,ace-reflector}-v1.txt
        artefacts = {"typed": {"tables_sha256": proposer_tables["tables_sha256"], "archive_sha256": archive_sha},
                     "ace": {"tables_sha256": credit_receipt_sha, "archive_sha256": archive_sha}}
        rows = reg.draft_text_only_rows(ctx.repo_root, t, proposers["ids"], proposers["shas"], at, artefacts, commit)
        reg.wr(ctx.repo_root, f"{proposers['package']}/draft-ledger-rows.md", rows)
        registered = {"status": "DRAFT-HELD", "package": proposers["package"], "cells": {k: v["cell"] for k, v in proposers["ids"].items()}}
    payload = {
        "status": "done", "iteration": t, "stage": "propose", "source_column": src, "roots": roots,
        "parent_display_id": display_id(parent_state), "tables_sha256": tables["tables_sha256"],
        "proposer_tables_sha256": proposer_tables["tables_sha256"], "proposer_context_file_sha256": sha_file(context_path),
        "archive_sha256": archive_sha, "ace": {"playbook_iteration": playbook["iteration"], "t_cap": t_cap,
                                              "lock_p99_supplied_tokens": constants["lock_p99_supplied_tokens"],
                                              "constants_sha256": ace.constants_hash(ace.ACE_CONSTANTS), "materials": len(materials)},
        "pins": pins, "registration": registered, "protocol_sha256": json.loads(
            (ctx.package_dir / lib.STATE_FILE).read_text(encoding="utf-8"))["protocol_sha256"],
        "edit_budget_L_t": tp.edit_budget(t),
    }
    inputs = {"iteration": t, "stage": "propose", "tables_file_sha256": sha_file(tables_path), "enums": enums,
              "p99": constants["lock_p99_supplied_tokens"], "archive_sha256": archive_sha, "register": not a.no_register}
    lib.write_receipt(ctx.receipts(t), "open-propose", payload, inputs=inputs)
    if lib.read_receipt(ctx.receipts(t), "open-propose")["inputs_sha256"] != tf.canonical_sha256(inputs):
        raise lib.ReceiptConflict("open-propose receipt differs")
    checklist(ctx, f"countersign checklist, iteration {t} proposer + reflector cells (HELD)", [
        f"countersign the DRAFT rows in {registered.get('package', '<proposers package>')}/draft-ledger-rows.md (coordinator)",
        "mint the decision receipts for the two text-only cells (scripts/flights/tfrl/tfrl_mint_receipt.py --kind proposers)",
        "run the loop-form flip (scripts/flights/tfrl/tfrl_i1_flip.sh proposers), refresh the plan pins, flip again, run the gates",
        "queue the cells through scripts/flights/tfrl/batch_chain_tfrl_i1.sh proposers; start SAEA-Batch-Driver from PowerShell (human)",
        "after the seal: python -B scripts/flights/tfrl/tfrl_loop_driver.py open --iter %d --stage cell --typed-receipts F "
        "--reflector-answers F ..." % t,
    ])
    return payload


# ---------------------------------------------------------------------------------------------------------------------------
# open: cell stage
# ---------------------------------------------------------------------------------------------------------------------------


def _artefact_hashes(parent_hashes: Mapping[str, str], operator: str, applications: Any, override: Mapping[str, str] | None) -> dict:
    name = ARTEFACT_OF[operator]
    digest = (override or {}).get(name) or tf.canonical_sha256({"operator": operator, "applications": applications})
    return {**parent_hashes, name: digest}


def find_archived_duplicate(states: list[Mapping[str, Any]], t: int, parent_state: Mapping[str, Any], operator: str, applications: Any,
                            override: Mapping[str, str] | None = None) -> "Mapping[str, Any] | None":
    """The state archived in an EARLIER iteration whose artefact set equals the one this candidate would produce under ``parent_state``.

    ``override`` is the builder's artefact hash (``None``: the provisional ``{operator, applications}`` digest that an unflown or an
    unfitted offline state carries). States of iteration ``t`` itself are ignored, so a re-run of the same step stays idempotent.
    A state is matched on its artefact set (the corrected view included), not on its candidate id: the id of a re-proposal differs (it
    carries the iteration), the artefact set does not."""

    hashes = _artefact_hashes(parent_state["artefact_hashes"], operator, applications, override)
    from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar  # noqa: PLC0415

    sid = ar.compute_state_id(hashes)
    for s in states:
        if s["iteration"] < t and (s["state_id"] == sid or s["artefact_hashes"] == hashes):
            return s
    return None


def duplicate_refusal(entry: Mapping[str, Any], archived: Mapping[str, Any]) -> dict:
    """The refused-list record of a duplicate: the code, the archived sibling and its verdict (and its realised SLU delta when measured)."""

    credit = archived.get("credit")
    realised = None
    if credit is not None:
        realised = (credit.get("vs_parent") or credit["vs_lock"])["slu"]["point"]
    return {"candidate_id": entry["candidate_id"], "operator_class": entry["operator_class"], "operator": entry["operator"],
            "refusal_code": DUPLICATE_OF_ARCHIVED, "archived_state_id": archived["state_id"], "archived_status": archived["verdict"],
            **({"predicted_slu_pp": entry["predicted_slu_pp"]} if entry.get("predicted_slu_pp") is not None else {}),
            **({"realised_d_slu_pp": realised} if realised is not None else {})}


def supersede_file(path: Path) -> Path:
    """Rename ``path`` to ``<stem>.superseded-<UTC mtime stamp><ext>`` (``-n`` on a clash); returns the new name."""

    stamp = datetime.datetime.fromtimestamp(path.stat().st_mtime, tz=datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = path.with_name(f"{path.stem}.superseded-{stamp}{path.suffix}")
    n = 1
    while target.exists():
        n += 1
        target = path.with_name(f"{path.stem}.superseded-{stamp}-{n}{path.suffix}")
    path.rename(target)
    return target


def knob_spec(candidate: Mapping[str, Any]) -> dict:
    """A ``knob-set`` candidate as a supply-column spec: the tail becomes the ``knowledge_stores.<tail>`` override path."""

    overrides = {f"knowledge_stores.{app['tail']}": int(app["value"]) for app in candidate["applications"]}
    return {"overrides": overrides}


def load_builder(spec: str | None) -> Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]] | None:
    if not spec:
        return None
    module_name, _, func = spec.partition(":")
    return getattr(importlib.import_module(module_name), func)


def open_cell(ctx: Ctx, t: int, a: argparse.Namespace) -> dict:
    from speech_aware_evidence_acquisition.analysis.sealed_credit import parent_choice  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    start(ctx, t, pin=False)
    propose = need_receipt(ctx, t, "open-propose")
    A = ctx.analysis(t)
    archive = ctx.archive()
    states = archive.states()
    parent_state = resolve_display(states, propose["parent_display_id"])
    tables_doc = tp.parse_tables(_load_json(A / "proposer-tables.json"))
    typed_states = [s for s in states if s["arm"] == "typed"]
    view = tp.ArchiveView(
        iteration=t, parent_state_id=display_id(parent_state),
        known_state_ids=frozenset(display_id(s) for s in typed_states),
        archived_candidate_ids=frozenset(s["candidate_id"] for s in typed_states if s.get("candidate_id")),
        masked_classes=frozenset(parent_choice.masked_classes(states, parent_state["state_id"])),
        entry_ids={"deliver-rule": frozenset(), "slot-card": frozenset()},
    )
    predictor = tp.FilePredictor(Path(a.predictions)) if a.predictions else None
    entries = _load_json(Path(a.typed_receipts)) if a.typed_receipts else []
    if not entries and not a.typed_arm_empty:
        raise lib.MissingInput("pass --typed-receipts F (sealed candidate receipts) or --typed-arm-empty (a legal state: the typed arm "
                               "is empty when no candidate cleared the bar)")
    valid, refused, rereads = [], [], []
    seen: set[str] = set()
    layouts = sorted({lib.typed_entry_layout(e) for e in entries})
    with_classes = sum(1 for e in entries if e.get("allowed_classes"))
    for entry in entries:
        receipt = entry["receipt"]
        if not receipt.get("legal"):
            refused.append({"candidate_id": receipt.get("response_sha256", "unparsed")[:16], "operator_class": "unknown",
                            "operator": "unknown", "refusal_code": (receipt.get("refusal_codes") or ["schema"])[0]})
            continue
        candidate = receipt["candidate"]
        result = tp.validate_candidate(candidate, enums=tables_doc.enums, archive=view, predictor=predictor,
                                       allowed_classes=entry.get("allowed_classes"), pool_sizes=tables_doc.pool_sizes())
        cid = result.candidate_id
        if lib.FINDING_CLASS_NOT_OFFERED in result.codes:
            # named finding (ruling 300 A): the class is not in the carrier's offered set. The same artefact offered by a carrier that WAS
            # offered the class stays eligible, so this refusal never enters ``seen``.
            refused.append({"candidate_id": cid, "operator_class": candidate["operator_class"], "operator": candidate["operator"],
                            "refusal_code": lib.FINDING_CLASS_NOT_OFFERED, "offered_classes": list(entry.get("allowed_classes") or [])})
            continue
        if cid in seen:
            continue
        seen.add(cid)
        if result.accepted:
            archived = find_archived_duplicate(states, t, parent_state, candidate["operator"], candidate["applications"])
            if archived is not None:          # the same artefact set as an earlier sibling: refused as a duplicate, never flown or read anew
                dup = {"candidate_id": cid, "operator_class": candidate["operator_class"], "operator": candidate["operator"],
                       "predicted_slu_pp": result.prediction.slu_pp if result.prediction else None}
                refused.append(duplicate_refusal(dup, archived))
                if result.read == "offline":  # an offline duplicate is still re-measured on this iteration's column (a reread, never a state)
                    rereads.append({"candidate_id": cid, "operator_class": candidate["operator_class"], "operator": candidate["operator"],
                                    "archived_state_id": archived["state_id"], "candidate": candidate})
                continue
            valid.append({"candidate_id": cid, "operator_class": candidate["operator_class"], "operator": candidate["operator"],
                          "read": result.read, "predicted_slu_pp": result.prediction.slu_pp if result.prediction else None,
                          "candidate": candidate})
        else:
            refused.append({"candidate_id": cid, "operator_class": candidate["operator_class"], "operator": candidate["operator"],
                            "refusal_code": result.codes[0],
                            **({"predicted_slu_pp": result.prediction.slu_pp} if result.prediction else {})})
    sf = sorted((v for v in valid if v["read"] == "sf"), key=lambda v: (-(v["predicted_slu_pp"] or 0.0), v["candidate_id"]))
    builder = load_builder(a.artefact_builder)
    typed_spec, chosen, not_flown, late_duplicates = None, None, [], set()
    for candidate in sf:
        if chosen is not None:
            not_flown.append({**candidate, "reason": "lower-predicted-than-the-flown-candidate"})
            continue
        if candidate["operator"] == "knob-set":
            spec, hashes = knob_spec(candidate["candidate"]), None
        elif builder is not None:
            built = builder(candidate["candidate"], {"parent": parent_state["artefact_hashes"]})
            spec, hashes = {k: built[k] for k in ("overrides", "release_swap", "alternates") if built.get(k)}, built.get("artefact_hashes")
        else:
            not_flown.append({**candidate, "reason": "artefact-builder-missing"})
            continue
        archived = find_archived_duplicate(states, t, parent_state, candidate["operator"], candidate["candidate"]["applications"], hashes)
        if archived is not None:              # the builder's artefact set equals an archived sibling: refuse it, the next candidate may fly
            refused.append(duplicate_refusal(candidate, archived))
            late_duplicates.add(candidate["candidate_id"])
            continue
        chosen, typed_spec = {**candidate, "artefact_override": hashes}, spec
    valid = [v for v in valid if v["candidate_id"] not in late_duplicates]
    offline = [v for v in valid if v["read"] == "offline"]
    # the accumulated typed parent is the previous accepted state's column spec
    parent_spec = None
    if parent_state["iteration"] > 0:
        parent_spec = read_or_none(ctx.package_dir / "archive-specs" / f"{parent_state['state_id']}.json")
        if parent_spec is None:
            raise lib.MissingInput("the accepted parent has no recorded column spec")
    # unflown / proposed-not-flown archive states
    from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar  # noqa: PLC0415

    for entry in not_flown:
        state = ar.build_state(
            artefact_hashes=_artefact_hashes(parent_state["artefact_hashes"], entry["operator"], entry["candidate"]["applications"], None),
            parent_id=parent_state["state_id"], iteration=t, operator_class=entry["operator_class"], candidate_id=entry["candidate_id"],
            verdict="unflown", arm="typed", predicted_slu_pp=entry["predicted_slu_pp"])
        lib.put_state_idempotent(archive, state)
    # ACE: deltas from the reflector's sealed answers, curated into playbook i(t)
    ace_state = ace_section(ctx, t, a, A, propose)
    spec = {"typed": typed_spec, "parent": parent_spec, "ace": ace_state["ace_pins"]}
    if chosen is not None:
        state_hashes = _artefact_hashes(parent_state["artefact_hashes"], chosen["operator"], chosen["candidate"]["applications"],
                                        chosen["artefact_override"])
        (ctx.package_dir / "archive-specs").mkdir(parents=True, exist_ok=True)
        lib.write_json_new(ctx.package_dir / "archive-specs" / f"pending-i{t}.json", {"spec": typed_spec, "artefact_hashes": state_hashes})
    import write_tfrl_iteration_registration as reg  # noqa: PLC0415

    predicted = chosen["predicted_slu_pp"] if chosen else 0.0
    commit = a.study_commit or "0" * 40
    at = a.registered_at or "%sT00:00:00.000000+00:00" % tf.DATE
    written = reg.write_iteration(ctx.repo_root, t, spec, commit, at, predicted_effect_pp=predicted or 0.0, with_proposers=False)
    arms = written["column"]["arms"]
    record = {"iteration": t, "parent_display_id": display_id(parent_state), "parent_state_id": parent_state["state_id"],
              "edit_budget_L_t": parent_choice.edit_budget(t),
              "candidates": [{"candidate_id": v["candidate_id"], "operator_class": v["operator_class"], "operator": v["operator"],
                              "read": v["read"], "predicted_slu_pp": v["predicted_slu_pp"]} for v in valid],
              "refused": refused, "flown": chosen["candidate_id"] if chosen else None,
              "offered_class_check": {"entries": len(entries), "entries_with_offered_classes": with_classes, "entry_layouts": layouts,
                                      "applied": bool(entries) and with_classes == len(entries),
                                      "class_not_offered": sum(1 for r in refused if r.get("refusal_code") == lib.FINDING_CLASS_NOT_OFFERED)},
              "offline": [v["candidate_id"] for v in offline], "not_flown": [{"candidate_id": n["candidate_id"], "reason": n["reason"]} for n in not_flown]}
    lib.write_json_new(ctx.receipts(t) / "candidates.json", record)
    # offline candidates keep their candidate documents for the close step (family + guard)
    lib.write_json_new(ctx.receipts(t) / "offline-candidates.json",
                       {"candidates": [{"candidate_id": v["candidate_id"], "operator_class": v["operator_class"],
                                        "operator": v["operator"], "candidate": v["candidate"]} for v in offline],
                        **({"reread_candidates": rereads} if rereads else {})})
    payload = {
        "status": "done", "iteration": t, "stage": "cell", "arms": arms, "program": written["column"]["package"] and
        f"phase-native-module-v1-c{tf.ceiling(t, typed_present=bool(typed_spec), parent_present=bool(parent_spec))}",
        "typed_arm": "empty (legal)" if chosen is None else {"candidate_id": chosen["candidate_id"], "predicted_slu_pp": chosen["predicted_slu_pp"]},
        # EMPTY BY MEASUREMENT: candidates were read and none cleared the bar. Distinct from ``inputs.typed_arm_empty`` (the --typed-arm-empty flag,
        # which only declares that no candidate receipts were passed).
        "typed_arm_empty_by_measurement": bool(chosen is None and entries),
        "parent_display_id": display_id(parent_state), "ace": ace_state["receipt"], "column_package": written["column"]["package"],
        "blockers": written["column"]["blockers"], "loader_verification": written["loader_verification"],
        "valid": len(valid), "refused": len(refused), "offline": len(offline), "not_flown": len(not_flown),
        "duplicates_of_archived": [{"candidate_id": r["candidate_id"], "archived_state_id": r["archived_state_id"],
                                    "archived_status": r["archived_status"]}
                                   for r in refused if r.get("refusal_code") == DUPLICATE_OF_ARCHIVED],
    }
    inputs = {"iteration": t, "stage": "cell", "typed_receipts": tf.canonical_sha256(entries), "typed_arm_empty": bool(a.typed_arm_empty),
              "reflector_answers": sha_file(Path(a.reflector_answers)) if a.reflector_answers else None,
              "predictions": sha_file(Path(a.predictions)) if a.predictions else None, "propose": propose["inputs_sha256"]}
    lib.write_receipt(ctx.receipts(t), "open-cell", payload, inputs=inputs)
    checklist(ctx, f"countersign checklist, iteration {t} column cell (HELD)", [
        f"read {written['column']['package']}/README.md for the blockers: {[b['id'] for b in written['column']['blockers']] or 'none'}",
        "prepare the ace-playbook release (prepare_semantic_knowledge_store over the registration printed in the receipt); put its pins in "
        "--ace-release-pins and re-run open --stage cell",
        "FIT measure the arms (tokenizer /tokenize, zero generation) and compare to T_cap; run the 4-row dry run (P-ACE-0, I7, I7v)",
        "run the gates: engineering_base, harness_admission, finite_completion_policy, stage3_algorithm_label, stage3_effect_floor, "
        "tool_catalog, flight_registration_check --cell %s" % tf.names(t, "arm")["experiment"],
        f"countersign the DRAFT rows in {written['column']['package']}/draft-ledger-rows.md; mint, flip (loop form), refresh the plan "
        "pins, flip again, queue; start SAEA-Batch-Driver from PowerShell (human)",
        "after the seal: python -B scripts/flights/tfrl/tfrl_loop_driver.py close --iter %d --execute" % t,
    ])
    return payload


def ace_curate(ctx: Ctx, t: int, answers: Mapping[str, str], propose: Mapping[str, Any]) -> dict:
    """The pure curation step of iteration ``t``: previous playbook + the reflector's parsed deltas + the previous iteration's credit.

    Shared by :func:`ace_section` and ``tfrl_cell_stage_inputs.py`` so both run ONE curator code path. Reads only; writes nothing.
    Returns ``{playbook, deltas_in, illegal, credit}``."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    previous = dict(resolve_playbook(ctx, t - 1)[1]) if t > 1 else dict(ace.load_playbook(ctx.analysis(t) / "playbook" / "playbook-i0.json"))
    deltas: list[dict] = []
    illegal = 0
    for scenario in sorted(answers):
        try:
            payload = json.loads(answers[scenario])
            deltas.extend(ace.parse_reflector_response(dict(payload)))
        except (ValueError, ace.AceMaterialError):
            illegal += 1
    credit = read_or_none(ctx.analysis(t - 1) / "ace-credit.json") if t > 1 else None
    constants = ace.with_measured_lock_p99(int(propose["ace"]["lock_p99_supplied_tokens"]))
    playbook = ace.curate(previous, deltas, credit or {}, constants)
    return {"playbook": playbook, "deltas_in": len(deltas), "illegal": illegal, "credit": credit}


def ace_stage_release(ctx: Ctx, t: int, playbook: dict, legal_intents: list[str], *, data_root: Path | None = None,
                      registration_path: Path | None = None) -> dict:
    """Write the release staging inputs of playbook ``t`` (and its registration) through ``build_playbook_release``.

    ``data_root`` / ``registration_path`` default to the context's; ``tfrl_cell_stage_inputs.py`` passes scratch locations for its dry run."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    binding = lib.ace_release_binding(ctx.repo_root)
    return ace.build_playbook_release(
        playbook, data_root=data_root or ctx.data_root, carrier_sample_ids=binding["carrier_sample_ids"], legal_intent_ids=legal_intents,
        source_split_identity_hash=binding["source_split_identity_hash"],
        release_dir=f"{tf.ANALYSIS_ROOT}/i{t}/ace-release-staging", registration_binding=binding["registration_binding"],
        registration_path=registration_path or (ctx.package_dir / f"ace-playbook-i{t}-release-registration.json"),
        registration_id=f"SAEA-SLURP-ACE-PLAYBOOK-PREPARATION-I{t}", output_namespace=f"knowledge/slurp/semantic/ace-playbook-i{t}")


def ace_section(ctx: Ctx, t: int, a: argparse.Namespace, A: Path, propose: Mapping[str, Any]) -> dict:
    """Curate playbook i(t) from the reflector's answers and the previous iteration's credit; stage its release inputs."""

    answers = (_load_json(Path(a.reflector_answers)) if a.reflector_answers else {}).get("answers", {})
    curated = ace_curate(ctx, t, answers, propose)
    playbook, credit = curated["playbook"], curated["credit"]
    illegal = curated["illegal"]
    playbook_path = A / "playbook" / f"playbook-i{t}.json"
    playbook_file_status = write_playbook_keyed(playbook_path, playbook)         # keyed by content; a stale file is kept as superseded
    legal_intents = _load_json(Path(a.enums_file))["intents"] if a.enums_file else []
    release = None
    if legal_intents:
        release = ace_stage_release(ctx, t, playbook, legal_intents)
    pins_file = read_or_none(Path(a.ace_release_pins)) if a.ace_release_pins else None
    ace_pins = {"iteration": t}
    if pins_file:
        ace_pins.update(pins_file)
    receipt = {"playbook_iteration": playbook["iteration"], "playbook_content_hash": playbook["content_hash"], "items": len(playbook["items"]),
               "playbook_file": playbook_file_status,
               "deltas_in": curated["deltas_in"], "illegal_answers": illegal, "curation": playbook.get("curation") and {
                   k: v for k, v in playbook["curation"].items() if k in ("deltas_in", "counter_updates", "constants_sha256", "token_counter_id")},
               "release_staging": None if release is None else {
                   **{k: release[k] for k in ("row_count", "empty")}, "registration": release["registration"],
                   "carrier_roster": lib.ACE_CARRIER_ROSTER_RELPATH, "carriers": tf.ACE_CARRIERS,
                   "source_split_identity_hash": lib.ace_release_binding(ctx.repo_root)["source_split_identity_hash"]},
               "release_pins": "supplied" if pins_file else "pending (zeros until the release is prepared)",
               "credit_used": credit is not None}
    return {"ace_pins": ace_pins, "receipt": receipt, "playbook": playbook}


# ---------------------------------------------------------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------------------------------------------------------


def _own(summary: Mapping[str, Any], arm: str) -> tuple[float, float]:
    official = summary["arms"][arm]["official"]
    return 100.0 * float(official["slu_f1"]), 100.0 * float(official["intent_accuracy"])


def plan_offline_fits(ctx: Ctx, t: int, run: str, attempt: str, *, key: str = "candidates") -> tuple[list, list]:
    """Queue one fit per offline candidate whose family the fitter reads; the rest are returned as ``unsupported`` (never dropped).

    ``key`` selects the list of ``offline-candidates.json``: ``candidates`` (new states) or ``reread_candidates`` (duplicates of an
    archived state, re-measured on this iteration's column and recorded as rereads)."""

    A = ctx.analysis(t)
    offline = (read_or_none(ctx.receipts(t) / "offline-candidates.json") or {}).get(key, [])
    fit_jobs, unsupported = [], []
    for entry in offline:
        app = entry["candidate"]["applications"][0]
        family = FIT_FAMILY.get(app.get("family", ""))
        if family is None:
            unsupported.append(entry)
            continue
        out = A / "offline" / entry["candidate_id"][:16]
        argv = [DELIVERY_FIT_SCRIPT, "--family", family, "--run-id", run, "--attempt", attempt, "--scorer", "slurp-slu-official-train",
                "--split", "train", "--rows", tf.ROWS, "--data-root", ctx.data_root, "--lock", ctx.lock_path, "--out-dir", out]
        if family == "oclock":          # the candidate's own scope restricts the paired apply-versus-not read
            if app.get("types"):
                argv += ["--types", ",".join(app["types"])]
            if app.get("intents"):
                argv += ["--intents", ",".join(app["intents"])]
        report = out / f"fit-report-{family}-v1.json"
        ctx.runner.run(f"delivery-fit-{entry['candidate_id'][:8]}", argv, produces=[report], ok_codes=(0, 3))   # exit 3 = refused, report written
        fit_jobs.append((entry, report))
    return fit_jobs, unsupported


def put_reread(archive: Any, held: Mapping[str, Any], t: int, candidate_id: str, run: str, report: Mapping[str, Any], status: str,
               clauses: Mapping[str, Any]) -> dict:
    """Record the re-measurement of the archived state ``held`` by candidate ``candidate_id`` of iteration ``t`` (write-once sibling
    record under ``archive/rereads/``; the archived state is not touched)."""

    from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar  # noqa: PLC0415

    record = {"schema": ar.REREAD_SCHEMA, "state_id": held["state_id"], "archived_verdict": held["verdict"], "iteration": t,
              "candidate_id": candidate_id, "column": {"run_id": run, "attempt": 1}, "reread_verdict": status,
              "clauses": json.loads(json.dumps(clauses)), "credit": lib.offline_credit_from_fit_report(report)}
    path, created = archive.put_reread(record)
    cross = report["cross_fitted"]
    return {"reread": True, "state_id": held["state_id"], "archived_status": held["verdict"], "status": status, "clauses": clauses,
            "candidate_id": candidate_id, "path": path.name, "created": created,
            "cross_fitted": {"delta_slu_pp": cross["delta_slu_pp"], "ci95_slu_pp": cross["ci95_slu_pp"], "rows_edited": cross.get("rows_edited")}}


def archive_rereads(ctx: Ctx, t: int, run: str, reread_jobs: list) -> list[dict]:
    """Record the offline re-measurement of every duplicate proposal (``reread_candidates``) as a reread of the archived sibling it names."""

    archive = ctx.archive()
    by_id = {s["state_id"]: s for s in archive.states()}
    out: list[dict] = []
    for entry, report_path in reread_jobs:
        report = _load_json(report_path)
        status, clauses = lib.offline_verdict(report)
        held = by_id.get(entry["archived_state_id"])
        if held is None:
            raise lib.LoopError(f"iteration {t}: reread candidate {entry['candidate_id'][:12]} names an unarchived state")
        out.append(put_reread(archive, held, t, entry["candidate_id"], run, report, status, clauses))
    return out


def archive_offline(ctx: Ctx, t: int, parent_state: Mapping[str, Any], run: str, candidates: Mapping[str, Any],
                    fit_jobs: list, unsupported: list) -> list[dict]:
    """Archive every offline candidate: a fitted one with its cross-fitted credit, an unsupported one as REFUSED (unmeasured) with the
    code ``offline-family-unsupported``. Idempotent."""

    from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar  # noqa: PLC0415

    archive = ctx.archive()
    out: list[dict] = []
    for entry, report_path in fit_jobs:
        report = _load_json(report_path)
        status, clauses = lib.offline_verdict(report)
        record = next(c for c in candidates["candidates"] if c["candidate_id"] == entry["candidate_id"])
        state = ar.build_state(
            artefact_hashes=_artefact_hashes(parent_state["artefact_hashes"], entry["operator"], entry["candidate"]["applications"],
                                             {"delivery_rule_table": (report.get("rule_table") and tf.canonical_sha256(report["rule_table"])) or None}
                                             if entry["operator"] == "deliver-rule" else None),
            parent_id=parent_state["state_id"], iteration=t, operator_class=entry["operator_class"], candidate_id=entry["candidate_id"],
            verdict=status, arm="typed", credit=lib.offline_credit_from_fit_report(report), predicted_slu_pp=record["predicted_slu_pp"],
            run_id=run, attempt=1)
        held = next((s for s in archive.states() if s["state_id"] == state["state_id"] or s["artefact_hashes"] == state["artefact_hashes"]),
                    None)
        if held is not None and not (held["iteration"] == t and held["candidate_id"] == entry["candidate_id"]):
            # the fitted artefact set equals a state archived by another proposal: the archive stays untouched, the read is a reread
            out.append(put_reread(archive, held, t, entry["candidate_id"], run, report, status, clauses))
            continue
        lib.put_state_idempotent(archive, state)
        cross = report["cross_fitted"]
        out.append({"state_id": state["state_id"], "status": status, "clauses": clauses,
                    "family": entry["candidate"]["applications"][0].get("family"),
                    "cross_fitted": {"delta_slu_pp": cross["delta_slu_pp"], "ci95_slu_pp": cross["ci95_slu_pp"],
                                     "rows_edited": cross.get("rows_edited")}})
    for entry in unsupported:
        record = next(c for c in candidates["candidates"] if c["candidate_id"] == entry["candidate_id"])
        state = ar.build_state(
            artefact_hashes=_artefact_hashes(parent_state["artefact_hashes"], entry["operator"], entry["candidate"]["applications"], None),
            parent_id=parent_state["state_id"], iteration=t, operator_class=entry["operator_class"], candidate_id=entry["candidate_id"],
            verdict="refused", arm="typed", predicted_slu_pp=record["predicted_slu_pp"], refusal_code=OFFLINE_UNSUPPORTED)
        lib.put_state_idempotent(archive, state)
        out.append({"state_id": state["state_id"], "status": "refused", "refusal_code": OFFLINE_UNSUPPORTED,
                    "family": entry["candidate"]["applications"][0].get("family")})
    return out


def close_iteration(ctx: Ctx, t: int, a: argparse.Namespace) -> dict:
    from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar  # noqa: PLC0415
    from speech_aware_evidence_acquisition.analysis.sealed_credit import meta_summary, parent_choice, selection  # noqa: PLC0415

    start(ctx, t, pin=False)
    opened = need_receipt(ctx, t, "open-cell")
    names = tf.names(t, "arm")
    run, attempt = names["run_id"], names["attempt_id"]
    arms = list(opened["arms"])
    rundir = ctx.data_root / "runs" / run / attempt
    A = ctx.analysis(t)
    roster_rel = tf.ROSTER["arm"]
    sv = rundir / "supply-variants"
    ctx.runner.run("score-columns", [ROLLOUT_SCORE_SCRIPT, "--mode", "supply-variants", "--run", run, "--attempt", attempt, "--roster",
                                     roster_rel, "--analysis-root", sv, "--scorer-id", tf.SCORER, "--stage", "all", "--repo-root",
                                     ctx.repo_root, "--data-root", ctx.data_root], produces=[sv / "score-summary.json"])
    # the ACE credit needs the per-row official scores that score-columns just wrote: export them here (write-once, by script) unless the
    # coordinator passed its own file, so the credit can never be skipped (the i1 close skipped it)
    if a.row_scores:
        row_scores_path = Path(a.row_scores)
        if not row_scores_path.is_file():
            raise lib.MissingInput(f"--row-scores {row_scores_path} does not exist (omit the flag and close exports the row scores itself)")
    else:
        row_scores_path = A / f"row-scores-i{t}.json"
        if tf.ARM_ACE in arms:
            ctx.runner.run("row-scores", [ROW_SCORES_SCRIPT, "--run-id", run, "--attempt", attempt, "--scorer", tf.SCORER,
                                          "--out", row_scores_path, "--data-root", ctx.data_root, "--lock", ctx.lock_path],
                           produces=[row_scores_path])
    ctx.runner.run("node-local", [NODE_LOCAL_SCRIPT, "--data-root", ctx.data_root, "--lock", ctx.lock_path, "--run-id", run,
                                  "--attempt-id", attempt, "--split", "train", "--out-dir", A / "node-local"],
                   produces=[A / "node-local" / "report.json"])
    roster_doc = _load_json(ctx.repo_root / roster_rel)
    pairs = [(arm, tf.DELIVERING) for arm in arms if arm != tf.DELIVERING]
    if tf.ARM_TYPED in arms and tf.ARM_PARENT in arms:
        pairs.append((tf.ARM_TYPED, tf.ARM_PARENT))
    for right, left in pairs:
        out = A / "pairs" / f"{right}-vs-{left}"
        ctx.runner.run(f"paired-{right}-vs-{left}", [
            PAIRED_READ_SCRIPT, "--per-scenario", "--stage", "all", "--left-run", run, "--left-attempt", attempt, "--left-column", left,
            "--left-label", left, "--right-run", run, "--right-attempt", attempt, "--right-column", right, "--right-label", right,
            "--scorer-id", tf.SCORER, "--expected-split-role", "discovery", "--roster", roster_rel, "--cluster-key", "sample_id",
            "--split-identity-hash", roster_doc["split_identity_hash"], "--repo-root", ctx.repo_root, "--data-root", ctx.data_root,
            "--seed", 20260915, "--draws", 10000, "--recipe-id", names["recipe_id"], "--title", f"loop i{t} {right} vs {left}",
            "--analysis-root", out], produces=[out / "score-contrasts.json"])
    fit_jobs, unsupported = plan_offline_fits(ctx, t, run, attempt)
    reread_jobs, _reread_unsupported = plan_offline_fits(ctx, t, run, attempt, key="reread_candidates")
    if ctx.runner.planned:
        return {"status": "planned", "commands": [r.argv for r in ctx.runner.planned]}
    # the ACE credit file is built BEFORE any archive write, so a failure here leaves nothing half-closed
    ace_credit_path = A / "ace-credit.json"
    ace_credit_status = "not-applicable"
    if tf.ARM_ACE in arms:
        credit_doc = lib.ace_credit_from_row_scores(_load_json(row_scores_path), playbook_iteration=t)
        lib.write_json_new(ace_credit_path, credit_doc)
        ace_credit_status = "written"
    summary = _load_json(sv / "score-summary.json")
    node_local = _load_json(A / "node-local" / "report.json")
    contacts = float(len(arms) + 1)

    def contrasts(right: str, left: str) -> dict:
        return _load_json(A / "pairs" / f"{right}-vs-{left}" / "score-contrasts.json")

    def per_scen(right: str, left: str) -> Any:
        return read_or_none(A / "pairs" / f"{right}-vs-{left}" / "per-scenario-tables.json")

    credits: dict[str, dict] = {}
    twin = contrasts(tf.TWIN, tf.DELIVERING)
    for arm in arms:
        if arm == tf.DELIVERING:
            continue
        own_slu, own_intent = _own(summary, arm)
        vs_parent = contrasts(tf.ARM_TYPED, tf.ARM_PARENT) if (arm == tf.ARM_TYPED and tf.ARM_PARENT in arms) else None
        credits[arm] = lib.credit_from_contrasts(
            contrasts(arm, tf.DELIVERING), own_slu_f1=own_slu, own_intent=own_intent, contacts_per_row=contacts,
            per_scenario_tables=per_scen(arm, tf.DELIVERING), node_local=node_local, arm=arm,
            versus_twin=None if arm == tf.TWIN else twin, versus_parent=vs_parent)
    rules = selection.rules_from_floor_table(tf.ROWS, ctx.repo_root)
    lock_id = {"role": "lock", "n_rows": tf.ROWS}
    archive = ctx.archive()
    states = archive.states()
    parent_state = resolve_display(states, opened["parent_display_id"])
    verdicts: dict[str, Any] = {}
    # ---- the typed child (a flown SF candidate)
    candidates = _load_json(ctx.receipts(t) / "candidates.json")
    if tf.ARM_TYPED in credits and candidates["flown"]:
        child = credits[tf.ARM_TYPED]
        parent_credit = credits.get(tf.ARM_PARENT)
        verdict = selection.select(child, lock_id, credits[tf.TWIN], parent_credit, rules)
        pending = _load_json(ctx.package_dir / "archive-specs" / f"pending-i{t}.json")
        entry = next(c for c in candidates["candidates"] if c["candidate_id"] == candidates["flown"])
        state = ar.build_state(artefact_hashes=pending["artefact_hashes"], parent_id=parent_state["state_id"], iteration=t,
                               operator_class=entry["operator_class"], candidate_id=entry["candidate_id"],
                               verdict=verdict.status, arm="typed", credit=child, predicted_slu_pp=entry["predicted_slu_pp"],
                               run_id=run, attempt=1)
        lib.put_state_idempotent(archive, state)
        if verdict.accepted:
            lib.write_json_new(ctx.package_dir / "archive-specs" / f"{state['state_id']}.json", pending["spec"])
        verdicts["typed"] = {"state_id": state["state_id"], **verdict.to_dict()}
    # ---- the offline (delivery / scope) candidates: read by the fitter, or recorded as refused-unmeasured; never skipped
    offline_all = archive_offline(ctx, t, parent_state, run, candidates, fit_jobs, unsupported)
    reread_verdicts = [v for v in offline_all if v.get("reread")] + archive_rereads(ctx, t, run, reread_jobs)
    offline_verdicts = [v for v in offline_all if not v.get("reread")]
    if offline_verdicts:
        verdicts["offline"] = offline_verdicts
    if reread_verdicts:
        verdicts["rereads"] = reread_verdicts
    # ---- the ACE state: always the child of the previous ACE state (a refused state still generates the next reflection)
    ace_states = [s for s in states if s["arm"] == "ace" and s["iteration"] < t]
    previous_ace = sorted(ace_states, key=lambda s: (s["iteration"], s["state_id"]))[-1]
    if tf.ARM_ACE in credits:
        verdict = selection.select(credits[tf.ARM_ACE], lock_id, credits[tf.TWIN], None, rules)
        _playbook_path, playbook = resolve_playbook(ctx, t)             # the playbook the flown release was built from
        behind = assert_playbook_binding(ctx, t, opened, playbook)
        state = ar.build_state(artefact_hashes={"playbook_release": playbook["content_hash"]}, parent_id=previous_ace["state_id"],
                               iteration=t, operator_class="playbook", candidate_id=f"ace-i{t}", verdict=verdict.status, arm="ace",
                               credit=credits[tf.ARM_ACE], run_id=run, attempt=1)
        if state["artefact_hashes"]["playbook_release"] != behind:      # the consistency assert: state hash == hash behind the release
            raise lib.LoopError(f"iteration {t}: the ACE state's playbook_release is not the hash behind the pinned release")
        lib.put_state_idempotent(archive, state)
        verdicts["ace"] = {"state_id": lib.stored_state_id(archive, state), "clause_d": "vacuous (no previous-ACE-state column in this flight)",
                           **verdict.to_dict()}
    # ---- curve, meta summary, parent choice
    states = archive.states()
    curves = {arm: selection.curve(states, arm) for arm in ("typed", "ace")}
    meta = meta_summary.build_meta_summary(states, "typed", rereads=archive.rereads())
    chosen = parent_choice.choose_parent(states, "typed")
    parent_shown = display_id(next(s for s in states if s["state_id"] == chosen["parent_id"]))
    cdir = ctx.receipts(t)
    lib.write_json_new(cdir / "curve.json", curves)
    lib.write_json_new(cdir / "proposer-meta.json", meta)
    lib.write_json_new(cdir / "parent.json", {"parent_state_id": chosen["parent_id"], "parent_display_id": parent_shown,
                                              "masked_classes": chosen["masked_classes"], "ranking": chosen["ranking"]})
    done = selection.loop_complete(t)
    payload = {
        "status": "done", "iteration": t, "column": {"run_id": run, "attempt": attempt}, "arms": arms, "rules": rules,
        "verdicts": verdicts, "credit_gaps": ["per-scenario deltas parsed leniently from per-scenario-tables.json",
                                              "false-fill / non-empty exact from the node-local report when present"],
        "curve": {arm: [{"iteration": p["iteration"], "level": p["level"], "marked": p["marked"]} for p in pts] for arm, pts in curves.items()},
        "parent_for_next": parent_shown, "ace_credit": ace_credit_status, "loop_complete": done,
        "row_scores": {"source": "override" if a.row_scores else "exported", "relpath_or_path": str(row_scores_path)
                       if a.row_scores else row_scores_path.relative_to(ctx.data_root).as_posix()},
        "next_iteration": selection.next_iteration(t), "typed_arm_was_empty": not candidates["flown"],
        # ruling 300 A: the per-carrier class set is checked at validation; a candidate outside its carrier's offered set is refused as
        # class-not-allowed. applied=false means the receipts predate the fix (iterations 1-3 flew with the class check off).
        "typed_class_check": candidates.get("offered_class_check") or {"applied": False, "class_not_offered": 0,
                                                                         "entry_layouts": [lib.TYPED_ENTRY_LAYOUT_V1]},
    }
    inputs = {"iteration": t, "column": [run, attempt], "summary": sha_file(sv / "score-summary.json"),
              "row_scores": sha_file(row_scores_path) if row_scores_path.is_file() else None,
              "ace_credit": sha_file(ace_credit_path) if ace_credit_path.is_file() else None, "open_cell": opened["inputs_sha256"]}
    lib.write_receipt(ctx.receipts(t), "close", payload, inputs=inputs)
    if done:
        checklist(ctx, "loop complete (three iterations); next steps are human", [
            "Fold A confirmation: lock, aa, the typed final state, the ACE final state (one attempt, thresholds fitted on Fold B)",
            "DEV-2000-ADDED composed read of the same four arms", "results note: the curve, the ACE comparison, per-stratum tables",
            "owner rules the lock-admission path (design R4)"])
    else:
        checklist(ctx, f"next iteration {t + 1}", [
            f"the ACE credit file is written ({ace_credit_path.name}); row scores came from "
            f"{'the --row-scores override' if a.row_scores else 'close itself (' + row_scores_path.name + ')'}",
            f"open --iter {t + 1} --stage propose (tables from the delivered column of iteration {t}; parent {parent_shown})",
            "countersign, mint, flip and queue (humans), as in iteration %d" % t])
    return payload


# ---------------------------------------------------------------------------------------------------------------------------
# repair: a one-off, idempotent reconciliation of a closed iteration (stale playbook file, wrong archived hash, unread offline candidates)
# ---------------------------------------------------------------------------------------------------------------------------

CORRECTION_SLUG = "playbook-hash"
CORRECTION_CAUSE = "stale-playbook-file-written-by-superseded-open-cell-run"


def reclassify_duplicates(ctx: Ctx, t: int) -> dict:
    """Idempotent: classify the offline candidates of the OPENED (not yet closed) iteration ``t`` that duplicate a state archived in an
    earlier iteration as ``refused`` / ``duplicate-of-archived`` (what ``open --stage cell`` now does), for an iteration opened before that
    rule existed. Nothing sealed is rewritten: ``candidates.json``, ``offline-candidates.json`` and the open-cell receipt are renamed
    ``<name>.superseded-<ts>.json`` and re-written (the i1 precedent); the duplicate stays in ``offline-candidates.json`` as a
    ``reread_candidates`` entry so ``close`` still re-measures it (a reread record, never a state). A flown candidate is never reclassified."""

    opened = need_receipt(ctx, t, "open-cell")
    record = read_or_none(ctx.receipts(t) / "candidates.json")
    if record is None:
        return {"status": "no-candidates", "duplicates": []}
    states = ctx.archive().states()
    parent_state = resolve_display(states, opened["parent_display_id"])
    offline_doc = read_or_none(ctx.receipts(t) / "offline-candidates.json") or {"candidates": []}
    offline_by_id = {e["candidate_id"]: e for e in offline_doc["candidates"]}
    moved: list[tuple[dict, dict, Mapping[str, Any]]] = []
    for c in record["candidates"]:
        entry = offline_by_id.get(c["candidate_id"])
        if entry is None or c["candidate_id"] == record.get("flown"):
            continue
        archived = find_archived_duplicate(states, t, parent_state, c["operator"], entry["candidate"]["applications"])
        if archived is not None:
            moved.append((c, entry, archived))
    if not moved:
        return {"status": "unchanged", "duplicates": []}
    ids = {c["candidate_id"] for c, _e, _a in moved}
    new_record = {**record, "candidates": [c for c in record["candidates"] if c["candidate_id"] not in ids],
                  "offline": [i for i in record["offline"] if i not in ids],
                  "refused": list(record["refused"]) + [duplicate_refusal(c, arc) for c, _e, arc in moved]}
    new_offline = {**offline_doc, "candidates": [e for e in offline_doc["candidates"] if e["candidate_id"] not in ids],
                   "reread_candidates": list(offline_doc.get("reread_candidates", [])) +
                   [{"candidate_id": e["candidate_id"], "operator_class": e["operator_class"], "operator": e["operator"],
                     "archived_state_id": arc["state_id"], "candidate": e["candidate"]} for _c, e, arc in moved]}
    duplicates = [{"candidate_id": c["candidate_id"], "archived_state_id": arc["state_id"], "archived_status": arc["verdict"]}
                  for c, _e, arc in moved]
    payload = {k: v for k, v in opened.items() if k not in ("schema", "step", "inputs_sha256", "inputs")}
    payload.update({"valid": len(new_record["candidates"]), "refused": len(new_record["refused"]), "offline": len(new_record["offline"]),
                    "duplicates_of_archived": list(payload.get("duplicates_of_archived", [])) + duplicates})
    inputs = {**opened["inputs"], "duplicate_reclassification": tf.canonical_sha256(sorted(
        (d["candidate_id"], d["archived_state_id"]) for d in duplicates))}
    superseded = [supersede_file(ctx.receipts(t) / name).name
                  for name in ("candidates.json", "offline-candidates.json", "open-cell-receipt.json")]
    lib.write_json_new(ctx.receipts(t) / "candidates.json", new_record)
    lib.write_json_new(ctx.receipts(t) / "offline-candidates.json", new_offline)
    lib.write_receipt(ctx.receipts(t), "open-cell", payload, inputs=inputs)
    return {"status": "reclassified", "duplicates": duplicates, "superseded": superseded}


def repair_iteration(ctx: Ctx, t: int, a: argparse.Namespace) -> dict:
    """Reconcile closed iteration ``t``:

    1. ``playbook/playbook-i<t>.json`` is made the playbook behind the pinned release (the stale file is kept as ``.superseded-<ts>.json``);
    2. an archived ACE state whose ``playbook_release`` is not that playbook's hash gets a CORRECTION RECORD (``archive/corrections/``;
       the state file itself is never edited);
    3. every offline candidate with no archive state is read (or archived as refused-unmeasured) exactly as ``close`` does.
    """

    from speech_aware_evidence_acquisition.analysis.sealed_credit import archive as ar  # noqa: PLC0415

    start(ctx, t, pin=False)
    opened = need_receipt(ctx, t, "open-cell")
    steps: dict[str, Any] = {}
    # 0. archived duplicates of an iteration that is still open (no close receipt): the only step that applies before close
    if lib.read_receipt(ctx.receipts(t), "close") is None:
        steps["duplicates"] = reclassify_duplicates(ctx, t)
        if a.duplicates_only:
            payload = {"status": "done", "iteration": t, "steps": steps}
            if steps["duplicates"]["status"] == "reclassified":
                opened = need_receipt(ctx, t, "open-cell")
            lib.write_receipt(ctx.receipts(t), "repair-duplicates", payload, inputs={"iteration": t, "open_cell": opened["inputs_sha256"]})
            return payload
        opened = need_receipt(ctx, t, "open-cell")
    elif a.duplicates_only:
        raise lib.LoopError(f"iteration {t} is closed; --duplicates-only applies before close")
    # 1. the playbook file
    behind = opened["ace"]["playbook_content_hash"]
    staged = staging_playbook_file(ctx, t)
    if a.skip_playbook_file:
        steps["playbook_file"] = "skipped"
    elif staged.is_file():
        from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

        staged_playbook = ace.load_playbook(staged)
        if staged_playbook["content_hash"] != behind:
            raise lib.LoopError(f"iteration {t}: the staged release playbook is not the one the open-cell receipt records")
        steps["playbook_file"] = write_playbook_keyed(playbook_file(ctx, t), staged_playbook)
    else:
        steps["playbook_file"] = "no-staged-release"
    # 2. the correction record
    archive = ctx.archive()
    receipt_path = ctx.receipts(t) / "open-cell-receipt.json"
    try:
        receipt_rel = receipt_path.relative_to(ctx.repo_root).as_posix()
    except ValueError:
        receipt_rel = receipt_path.as_posix()
    corrections = []
    for state in archive.states():
        if state["arm"] != "ace" or state["iteration"] != t or state["artefact_hashes"].get("playbook_release") == behind:
            continue
        record = {"schema": ar.CORRECTION_SCHEMA, "state_id": state["state_id"], "artefact": "playbook_release", "slug": CORRECTION_SLUG,
                  "wrong": state["artefact_hashes"]["playbook_release"], "right": behind, "cause": CORRECTION_CAUSE,
                  "derives_from": {"receipt": receipt_rel, "field": "ace.playbook_content_hash", "receipt_sha256": sha_file(receipt_path)}}
        path = archive.put_correction(record)
        corrections.append({"state_id": state["state_id"], "wrong": record["wrong"], "right": behind, "path": path.name})
    steps["corrections_written"] = corrections
    steps["playbook_binding"] = [{"state_id": s["state_id"], "ok": s["artefact_hashes"].get("playbook_release") == behind,
                                  "corrected": bool(s.get("corrections"))}
                                 for s in ctx.archive().states() if s["arm"] == "ace" and s["iteration"] == t]
    # 3. the offline candidates without a state
    candidates = read_or_none(ctx.receipts(t) / "candidates.json")
    names = tf.names(t, "arm")
    fit_jobs, unsupported = plan_offline_fits(ctx, t, names["run_id"], names["attempt_id"])
    reread_jobs, _reread_unsupported = plan_offline_fits(ctx, t, names["run_id"], names["attempt_id"], key="reread_candidates")
    if ctx.runner.planned:
        steps["planned"] = [r.argv for r in ctx.runner.planned]
        return {"status": "planned", "iteration": t, "steps": steps, "commands": steps["planned"]}
    archived_ids = {s["candidate_id"] for s in ctx.archive().states()}
    fit_jobs = [(e, r) for e, r in fit_jobs if e["candidate_id"] not in archived_ids]
    unsupported = [e for e in unsupported if e["candidate_id"] not in archived_ids]
    states = ctx.archive().states()
    parent_state = resolve_display(states, opened["parent_display_id"])
    offline_all = archive_offline(ctx, t, parent_state, names["run_id"], candidates or {"candidates": []}, fit_jobs, unsupported) \
        if candidates else []
    steps["offline"] = [v for v in offline_all if not v.get("reread")]
    steps["rereads"] = [v for v in offline_all if v.get("reread")] + archive_rereads(ctx, t, names["run_id"], reread_jobs)
    payload = {"status": "done", "iteration": t, "steps": steps}
    lib.write_receipt(ctx.receipts(t), "repair", payload, inputs={"iteration": t, "open_cell": opened["inputs_sha256"],
                                                                  "skip_playbook_file": bool(a.skip_playbook_file)})
    return payload


# ---------------------------------------------------------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------------------------------------------------------


def status(ctx: Ctx) -> dict:
    protocol = lib.check_protocol(ctx.package_dir, pin=False) if (ctx.package_dir / "tfrl-loop-protocol-v1.json").is_file() else None
    archive = ctx.archive()
    states = archive.states()
    out: dict[str, Any] = {"protocol_sha256": protocol and protocol["protocol_sha256"], "archive_sha256": lib.archive_sha256(ctx.package_dir / "archive"),
                           "states": [{"state_id": s["state_id"][:12], "arm": s["arm"], "iteration": s["iteration"], "verdict": s["verdict"]}
                                      for s in states], "iterations": {}}
    next_action = "open --iter 1 --stage propose"
    for t in tf.ITERATIONS:
        steps = [name for name in ("open-propose", "open-cell", "close") if lib.read_receipt(ctx.receipts(t), name)]
        out["iterations"][str(t)] = steps
        if "close" in steps:
            next_action = f"open --iter {t + 1} --stage propose" if t < tf.STOP_AFTER_ITERATIONS else "loop complete: Fold A confirmation (human)"
        elif "open-cell" in steps:
            next_action = f"(humans: countersign, flip, queue, fly) then close --iter {t}"
        elif "open-propose" in steps:
            next_action = f"(humans: countersign, flip, queue, fly the proposer + reflector cells) then open --iter {t} --stage cell"
            break
    out["next_action"] = next_action
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--package-dir", type=Path, default=None, help="default: <repo-root>/" + tf.PACKAGE_DIR)
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", DEFAULT_DATA_ROOT)))
    parser.add_argument("--lock", type=Path, default=Path(DEFAULT_LOCK))
    parser.add_argument("--execute", action="store_true", help="run the external model-free analysis scripts (default: plan only)")
    parser.add_argument("--skip-process-guard", action="store_true", help="tests only")
    sub = parser.add_subparsers(dest="command", required=True)
    o = sub.add_parser("open")
    o.add_argument("--iter", type=int, required=True, dest="iteration")
    o.add_argument("--stage", choices=("auto", "propose", "cell"), default="auto")
    o.add_argument("--source-run-id"), o.add_argument("--source-attempt"), o.add_argument("--source-scorer")
    o.add_argument("--enums-file"), o.add_argument("--enums-from-gold", action="store_true")
    o.add_argument("--lock-p99-supplied-tokens", type=float, default=None)
    o.add_argument("--no-register", action="store_true"), o.add_argument("--study-commit"), o.add_argument("--registered-at")
    o.add_argument("--typed-receipts"), o.add_argument("--typed-arm-empty", action="store_true")
    o.add_argument("--reflector-answers"), o.add_argument("--predictions"), o.add_argument("--artefact-builder")
    o.add_argument("--ace-release-pins")
    c = sub.add_parser("close")
    c.add_argument("--iter", type=int, required=True, dest="iteration")
    c.add_argument("--row-scores", default=None)
    r = sub.add_parser("repair", help="one-off, idempotent reconciliation of a closed iteration (see repair_iteration)")
    r.add_argument("--iter", type=int, required=True, dest="iteration")
    r.add_argument("--skip-playbook-file", action="store_true", help="do not touch the data-root playbook file")
    r.add_argument("--duplicates-only", action="store_true",
                   help="before close: only classify offline candidates that duplicate an archived state (duplicate-of-archived)")
    sub.add_parser("status")
    return parser


def make_ctx(args: argparse.Namespace, *, runner: lib.Runner | None = None, lister=None, out=print) -> Ctx:
    package_dir = args.package_dir or (args.repo_root / tf.PACKAGE_DIR)
    return Ctx(repo_root=args.repo_root, package_dir=package_dir, data_root=args.data_root, lock_path=args.lock,
               runner=runner or lib.Runner(execute=args.execute, cwd=args.repo_root), lister=lister,
               skip_guard=args.skip_process_guard, out=out)


def main(argv: list[str] | None = None, *, runner: lib.Runner | None = None, lister=None, out=print) -> int:
    args = build_parser().parse_args(argv)
    ctx = make_ctx(args, runner=runner, lister=lister, out=out)
    try:
        if args.command == "status":
            result = status(ctx)
        elif args.command == "open":
            stage = args.stage
            if stage == "auto":
                stage = "cell" if lib.read_receipt(ctx.receipts(args.iteration), "open-propose") else "propose"
            result = (open_propose if stage == "propose" else open_cell)(ctx, args.iteration, args)
        elif args.command == "repair":
            result = repair_iteration(ctx, args.iteration, args)
        else:
            result = close_iteration(ctx, args.iteration, args)
    except lib.LoopError as error:
        out(f"REFUSED: {error}")
        return 3
    out(json.dumps({k: v for k, v in result.items() if k not in ("pins",)}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
