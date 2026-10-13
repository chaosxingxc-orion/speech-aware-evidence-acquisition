#!/usr/bin/env python3
"""Produce the INPUT SET of ``tfrl_loop_driver.py open --stage cell`` from the sealed proposer and reflector outputs (MODEL-FREE).

Between the two GPU steps of an iteration the coordinator used to build, by hand, the files ``open --iter t --stage cell`` consumes:

* ``typed-receipts-i<t>.json``     one ``saea-tfrl-typed-candidate-receipt-v1`` per sealed proposer contact (``tp.read_typed_candidate_receipt``);
* ``predictions-i<t>.json``        ``saea-tfrl-predictions-v1``: class-level predictions, only when ``--class-predictions`` names them;
* ``reflector-answers-i<t>.json``  ``saea-tfrl-reflector-answers-v1``: the sealed reflector answer of each scenario (carrier -> roster stratum);
* ``enums-i<t>.json``              ``saea-tfrl-enums-v1``: the closed vocabularies of the propose stage's tables;
* the ACE release: staging under ``ace-release-staging/`` (curated by the driver's own :func:`tfrl_loop_driver.ace_curate`, growing from the
  release playbook of iteration t-1), the registration under the package directory, the three preparer files under
  ``knowledge/slurp/semantic/ace-playbook-i<t>/`` (``release.json``, ``snapshot.json``, ``completion.json``, written ONLY by
  ``prepare_semantic_knowledge_store``) and ``ace-release-pins-i<t>.json`` (the preparer's CONTENT hashes, never file hashes);
* ``ace-i<t>-release-files.json``  the file-level digests of the three preparer files (i1 shape);
* ``cell-stage-inputs-i<t>.json``  this tool's manifest: source run and attempt ids, the sha256 of each sealed outputs file, the sha256 of
  every artefact written, the counts, the tool version.

Default is a DRY RUN: nothing is written, the report prints what ``--execute`` would write with the hashes, and every artefact that already
exists is compared with the fresh bytes (``identical`` / ``stable-match`` / the differing top-level fields). ``--execute`` writes under
``<data-root>/analysis/SAEA-SLURP-TFRL-LOOP-V1/i<t>/`` and ``<data-root>/knowledge/slurp/semantic/ace-playbook-i<t>/`` (plus the registration
in the package directory, as the driver does). WRITE-ONCE: an existing artefact with different bytes is refused unless ``--supersede``
renames it ``<name>.superseded-<UTC timestamp><ext>`` first.

Shape discipline: the i1 artefacts were produced by hand scripts with shapes the driver tolerates; the tool KEEPS those shapes (list-form
typed receipts, ``indent=1`` JSON, the same key sets) and only ADDS a ``provenance`` object to the dict artefacts (``--no-provenance`` omits
it; the report's comparison always ignores it). Nothing here prints or persists utterance text, transcripts, gold labels or model output
text: the reflector answers file carries the sealed model JSON by design (as i1's does) and is never printed.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tfrl_family as tf  # noqa: E402
import tfrl_loop_driver as drv  # noqa: E402
import tfrl_loop_lib as lib  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

TOOL_VERSION = "tfrl-cell-stage-inputs-v1"
MANIFEST_SCHEMA = "saea-tfrl-cell-stage-inputs-v1"
ANSWERS_SCHEMA = "saea-tfrl-reflector-answers-v1"
ENUMS_SCHEMA = "saea-tfrl-enums-v1"
PREDICTIONS_SCHEMA = "saea-tfrl-predictions-v1"
ENUMS_SOURCE = "proposer-tables.json (propose stage, --enums-from-gold)"
ANSWERS_MAPPING = ("carrier sample_id -> roster stratum ({roster}); for a scenario with two carriers the first non-empty answer is kept")
PREPARED_BY = ("core.semantic_knowledge_preparation.prepare_semantic_knowledge_store over {registration}; pins = the preparer's completion.json "
               "release/snapshot entries (the snapshot pin is the content sha, not the file sha)")


class ToolError(lib.LoopError):
    pass


# ---------------------------------------------------------------------------------------------------------------------------
# bytes and comparison helpers
# ---------------------------------------------------------------------------------------------------------------------------


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def dumps(doc: Any, *, sort_keys: bool = True) -> bytes:
    """The hand scripts' serialisation: ``json.dump(indent=1)``, ASCII-escaped, no trailing newline."""

    return json.dumps(doc, indent=1, sort_keys=sort_keys).encode("utf-8")


def strip_provenance(doc: Any) -> Any:
    return {k: v for k, v in doc.items() if k != "provenance"} if isinstance(doc, dict) else doc


def compare(existing: bytes | None, fresh_core: bytes) -> dict:
    """Compare the existing bytes of an artefact with the fresh bytes WITHOUT the provenance object."""

    if existing is None:
        return {"state": "new"}
    if existing == fresh_core:
        return {"state": "identical"}
    try:
        old, new = strip_provenance(json.loads(existing)), json.loads(fresh_core)
    except ValueError:
        return {"state": "differs", "fields": ["<unparseable>"]}
    if isinstance(old, dict) and isinstance(new, dict):
        fields = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k) or (k in old) != (k in new))
        if not fields and json.loads(existing) == old:
            return {"state": "identical-semantics", "note": "same content, different serialisation"}
        if not fields:
            return {"state": "stable-match", "note": "differs only in provenance"}
        return {"state": "differs", "fields": fields}
    return {"state": "differs", "fields": ["<document>"]}


def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def supersede_name(path: Path) -> Path:
    stamp = utc_stamp()
    target = path.with_name(f"{path.stem}.superseded-{stamp}{path.suffix}")
    n = 1
    while target.exists():
        n += 1
        target = path.with_name(f"{path.stem}.superseded-{stamp}-{n}{path.suffix}")
    return target


# ---------------------------------------------------------------------------------------------------------------------------
# sealed sources
# ---------------------------------------------------------------------------------------------------------------------------


def offered_classes(repo_root: Path, names: Mapping[str, Any]) -> dict[str, list[str]]:
    """The proposer brief's per-carrier offered class sets (``tfrl_proposer.carriers`` of the registered baseline fragment), fail-closed."""

    path = repo_root / "configs" / "baseline" / f"{names['baseline']}.json"
    if not path.is_file():
        raise lib.MissingInput(f"the proposer brief {path.relative_to(repo_root).as_posix()} is missing; the offered class set cannot be read")
    carriers = (json.loads(path.read_text(encoding="utf-8")).get("tfrl_proposer") or {}).get("carriers") or []
    out = {str(c["sample_id"]): [str(x) for x in c["allowed_classes"]] for c in carriers if c.get("allowed_classes")}
    if not out:
        raise lib.MissingInput("the proposer brief declares no per-carrier allowed_classes")
    return out


def sealed_source(data_root: Path, repo_root: Path, t: int, kind: str) -> dict:
    """The sealed outputs of iteration ``t``'s proposer (``typed``) or reflector (``ace``): ids, rows, digest, roster."""

    names = tf.names(t, kind)
    path = data_root / "runs" / names["run_id"] / names["attempt_id"] / f"{names['run_id']}.outputs.jsonl"
    if not path.is_file():
        raise lib.MissingInput(f"iteration {t}: the sealed {kind} outputs are missing ({path.relative_to(data_root).as_posix()})")
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    admitted = [r for r in rows if r.get("admitted", True)]
    roster_path = repo_root / names["carrier_roster"]
    offered = offered_classes(repo_root, names) if kind == "typed" else None
    return {"kind": kind, "offered_classes": offered, "run_id": names["run_id"], "attempt_id": names["attempt_id"], "outputs_relpath": path.relative_to(data_root).as_posix(),
            "outputs_sha256": sha256_bytes(raw), "rows": admitted, "rows_total": len(rows), "roster_relpath": names["carrier_roster"],
            "roster": json.loads(roster_path.read_text(encoding="utf-8")), "roster_sha256": sha256_bytes(roster_path.read_bytes())}


def provenance(t: int, source: Mapping[str, Any] | None, extra: Mapping[str, Any] | None = None) -> dict:
    out: dict[str, Any] = {"tool": TOOL_VERSION, "iteration": t, **(extra or {})}
    if source is not None:
        out["source"] = {k: source[k] for k in ("run_id", "attempt_id", "outputs_relpath", "outputs_sha256", "roster_relpath", "roster_sha256")}
    return out


# ---------------------------------------------------------------------------------------------------------------------------
# artefact builders (pure)
# ---------------------------------------------------------------------------------------------------------------------------


def build_typed_receipts(source: Mapping[str, Any]) -> tuple[list[dict], dict]:
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    offered = source.get("offered_classes")           # sample_id -> offered class set, from the proposer brief (None: legacy source)
    entries = []
    for r in source["rows"]:
        entry = {"receipt": tp.read_typed_candidate_receipt(r["text"]),
                 "sample_id_sha_prefix": hashlib.sha256(str(r["sample_id"]).encode("utf-8")).hexdigest()[:12],
                 "response_sha256_prefix": r["response_sha256"][:12]}
        if offered is not None:
            if r["sample_id"] not in offered:
                raise ToolError("a sealed proposer contact has no offered class set in the proposer brief; refusing to drop the class check")
            entry["allowed_classes"] = list(offered[r["sample_id"]])
        entries.append(entry)
    codes: dict[str, int] = {}
    for entry in entries:
        for code in entry["receipt"].get("refusal_codes") or []:
            codes[code] = codes.get(code, 0) + 1
    legal = [e["receipt"] for e in entries if e["receipt"].get("legal")]
    ids = [r["candidate_id"] for r in legal]
    counts = {"contacts": len(entries), "schema_valid": len(legal), "schema_refused": len(entries) - len(legal),
              "refusal_codes": dict(sorted(codes.items())), "distinct_candidates": len(set(ids)),
              "by_class_operator": _tally(f"{r['operator_class']}/{r['operator']}" for r in legal)}
    if offered is not None:
        counts["class_not_offered"] = sum(1 for e in entries if e["receipt"].get("legal")
                                          and e["receipt"]["operator_class"] not in e["allowed_classes"])
    return entries, counts


def _tally(values) -> dict:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


def build_predictions(entries: list[dict], class_predictions: Mapping[str, Mapping[str, Any]] | None) -> tuple[dict, dict]:
    """Class-level predictions for the legal candidates whose class the ``--class-predictions`` table names; ``missing`` lists (as counts) the
    predicted-class candidates the driver will refuse as ``prediction-missing``."""

    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    table = dict(class_predictions or {})
    predictions: dict[str, dict] = {}
    needed = missing = 0
    for entry in entries:
        receipt = entry["receipt"]
        if not receipt.get("legal"):
            continue
        candidate = receipt["candidate"]
        cls = candidate["operator_class"]
        if tp._is_predicted(candidate):                       # noqa: SLF001 - the validator's own predicate
            needed += 1
            if cls not in table:
                missing += 1
        if cls in table:
            predictions[tp.candidate_id(candidate)] = {"slu_pp": float(table[cls]["slu_pp"]), "basis": str(table[cls].get("basis", ""))}
    return ({"schema": PREDICTIONS_SCHEMA, "predictions": predictions},
            {"predictions": len(predictions), "predicted_class_candidates": needed, "prediction_missing": missing})


def build_reflector_answers(source: Mapping[str, Any], t: int) -> tuple[dict, dict, dict]:
    """One answer per scenario: carrier sample id -> roster stratum; a scenario with several carriers keeps the first NON-EMPTY answer."""

    from speech_aware_evidence_acquisition.rails import tfrl_ace_material as ace  # noqa: PLC0415

    sid2scn = {item["sample_id"]: item["stratum"] for item in source["roster"]["items"]}
    answers: dict[str, str] = {}
    dropped: list[dict] = []
    replaced: list[dict] = []          # an empty first answer superseded by a later non-empty one (the i1 hand script did this silently)
    parsed = rejected = 0
    rejected_codes: dict[str, int] = {}
    deltas_by: dict[str, int] = {}
    kept_prefix: dict[str, str] = {}

    def count(text: str) -> int:
        try:
            return len(json.loads(text).get("deltas", []))
        except (ValueError, AttributeError):
            return 0

    for row in source["rows"]:
        if row["sample_id"] not in sid2scn:
            raise ToolError(f"iteration {t}: a sealed reflector contact is not a carrier of the roster {source['roster_relpath']}")
        scn, text = sid2scn[row["sample_id"]], row["text"]
        try:
            ace.parse_reflector_response(dict(json.loads(text)))
            parsed += 1
        except (ValueError, TypeError, ace.AceMaterialError) as error:
            rejected += 1
            rejected_codes[type(error).__name__] = rejected_codes.get(type(error).__name__, 0) + 1
        n = count(text)
        if scn in answers:
            prev_n = count(answers[scn])
            if prev_n > 0 or n == 0:
                dropped.append({"scenario": scn, "response_sha256_prefix": row["response_sha256"][:10], "deltas": n})
                continue
            replaced.append({"scenario": scn, "response_sha256_prefix": kept_prefix[scn], "deltas": prev_n})
        answers[scn] = text
        kept_prefix[scn] = row["response_sha256"][:10]
        deltas_by[scn] = n
    doc = {"schema": ANSWERS_SCHEMA, "run_id": source["run_id"],
           "mapping": ANSWERS_MAPPING.format(roster=source["roster_relpath"]), "dropped_duplicates": dropped, "answers": answers}
    doc_extra = {"replaced_empty_answers": replaced}
    counts = {"contacts": len(source["rows"]), "parsed": parsed, "rejected": rejected, "rejected_codes": dict(sorted(rejected_codes.items())),
              "scenarios": len(answers), "scenarios_with_deltas": sum(1 for n in deltas_by.values() if n), "deltas_in_kept_answers": sum(deltas_by.values()),
              "dropped_duplicates": len(dropped), "replaced_empty_answers": len(replaced)}
    return doc, counts, doc_extra


def build_enums(analysis: Path) -> dict:
    tables = json.loads((analysis / "proposer-tables.json").read_text(encoding="utf-8"))
    enums = tables.get("enums") or {}
    if not enums:
        raise ToolError("proposer-tables.json carries no enums")
    return {"schema": ENUMS_SCHEMA, "source": ENUMS_SOURCE, **{k: sorted(v) for k, v in enums.items()}}


# ---------------------------------------------------------------------------------------------------------------------------
# the ACE release
# ---------------------------------------------------------------------------------------------------------------------------


def _link_prepared(scratch: Path, data_root: Path, repo_root: Path) -> None:
    """Copy the data-root roster inputs of the preparer (the R01C construction scope and permitted roster, pinned by the i0 registration) into a
    scratch root; the preparer confines every pin to its root, so a symlink would escape it."""

    registration = json.loads((repo_root / lib.ACE_I0_REGISTRATION_RELPATH).read_text(encoding="utf-8"))
    pins = [registration["construction_scope"], registration["permitted_roster"], *registration["forbidden_rosters"]]
    for pin in pins:
        if pin.get("root") == "data":
            if not (data_root / pin["relpath"]).is_file():
                raise ToolError(f"the preparer's data-root input {pin['relpath']} is missing")
            target = scratch / pin["relpath"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(data_root / pin["relpath"], target)


def stage_in_scratch(ctx: drv.Ctx, t: int, playbook: dict, intents: list[str], scratch: Path) -> dict:
    reg = scratch / "registration" / f"ace-playbook-i{t}-release-registration.json"
    release = drv.ace_stage_release(ctx, t, playbook, intents, data_root=scratch, registration_path=reg)
    files = {p.name: p for p in sorted((scratch / tf.ANALYSIS_ROOT / f"i{t}" / "ace-release-staging").iterdir())}
    return {"release": release, "registration": reg, "files": files}


def staging_bytes(path: Path, scratch: Path, data_root: Path) -> bytes:
    """A staged file's bytes as the real data root would hold them: the wrap receipt records ABSOLUTE paths of the authored and source files,
    so the scratch prefix is replaced by the data root (every other staged file is path-free)."""

    return path.read_bytes().replace(str(scratch).encode(), str(data_root).encode())


def prepare_in(data_root: Path, repo_root: Path, registration: Path) -> Mapping[str, Any]:
    from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import prepare_semantic_knowledge_store  # noqa: PLC0415

    return prepare_semantic_knowledge_store(registration, repo_root=repo_root, data_root=data_root)


def namespace_files(namespace: Path) -> dict[str, bytes]:
    return {name: (namespace / name).read_bytes() for name in ("release.json", "snapshot.json", "completion.json") if (namespace / name).is_file()}


def release_files_doc(t: int, files: Mapping[str, bytes]) -> dict:
    return {name: {"relpath": f"knowledge/slurp/semantic/ace-playbook-i{t}/{name}", "sha256": sha256_bytes(files[name]), "bytes": len(files[name])}
            for name in ("release.json", "snapshot.json", "completion.json")}


def pins_doc(t: int, completion: Mapping[str, Any], registration_relpath: str) -> dict:
    return {"release_relpath": completion["release"]["relpath"], "release_sha256": completion["release"]["sha256"],
            "snapshot_relpath": completion["snapshot"]["relpath"], "snapshot_sha256": completion["snapshot"]["sha256"],
            "snapshot_file_sha256": completion.get("snapshot_file_sha256"),
            "prepared_by": PREPARED_BY.format(registration=registration_relpath)}


# ---------------------------------------------------------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------------------------------------------------------


def make_ctx(args: argparse.Namespace) -> drv.Ctx:
    package_dir = args.package_dir or (args.repo_root / tf.PACKAGE_DIR)
    return drv.Ctx(repo_root=args.repo_root, package_dir=package_dir, data_root=args.data_root, lock_path=args.lock,
                   runner=lib.Runner(execute=False, cwd=args.repo_root), skip_guard=True)


def run(args: argparse.Namespace) -> dict:
    t = args.iteration
    if t not in tf.ITERATIONS:
        raise ToolError(f"iteration must be one of {tf.ITERATIONS}")
    ctx = make_ctx(args)
    execute = bool(args.execute)
    A = ctx.analysis(t)
    with_prov = not args.no_provenance
    typed = sealed_source(ctx.data_root, ctx.repo_root, t, "typed")
    refl = sealed_source(ctx.data_root, ctx.repo_root, t, "ace")
    propose = drv.need_receipt(ctx, t, "open-propose")
    class_predictions = None
    if args.class_predictions:
        class_predictions = json.loads(Path(args.class_predictions).read_text(encoding="utf-8"))

    # ---- the four plain artefacts
    entries, typed_counts = build_typed_receipts(typed)
    predictions_doc, pred_counts = build_predictions(entries, class_predictions)
    answers_doc, answer_counts, answers_extra = build_reflector_answers(refl, t)
    enums_doc = build_enums(A)
    plain: dict[str, tuple[Any, bytes, bool, dict]] = {}      # name -> (doc, core bytes, sort_keys, provenance)
    plain[f"typed-receipts-i{t}.json"] = (entries, dumps(entries), True, provenance(t, typed))
    plain[f"predictions-i{t}.json"] = (predictions_doc, dumps(predictions_doc), True, provenance(t, typed))
    plain[f"reflector-answers-i{t}.json"] = (answers_doc, dumps(answers_doc), True, provenance(t, refl, answers_extra))
    plain[f"enums-i{t}.json"] = (enums_doc, dumps(enums_doc, sort_keys=False), False, provenance(t, None))

    # ---- the ACE curation (the driver's own curator) and release staging (scratch first: dry run and conflict check use the same bytes)
    curated = drv.ace_curate(ctx, t, answers_doc["answers"], propose)
    playbook = curated["playbook"]
    plan: list[dict] = []

    def add(name: str, target: Path, core: bytes, full: bytes, group: str) -> dict:
        existing = target.read_bytes() if target.is_file() else None
        entry = {"name": name, "target": target, "core": core, "full": full, "group": group, "fresh_sha256": sha256_bytes(full),
                 "compare": {"state": "identical"} if existing is not None and existing in (core, full) else compare(existing, core)}
        plan.append(entry)
        return entry

    def plain_entries() -> None:
        for name, (doc, core, sort_keys, prov) in plain.items():
            full = core
            if with_prov and isinstance(doc, dict):
                full = dumps({**doc, "provenance": prov}, sort_keys=sort_keys)
            add(name, A / name, core, full, "analysis")

    def release_entries(namespace_bytes: Mapping[str, bytes], namespace: Path, reg_rel: str) -> dict:
        for fname, raw in namespace_bytes.items():
            add(f"knowledge/slurp/semantic/ace-playbook-i{t}/{fname}", namespace / fname, raw, raw, "release")
        pins = pins_doc(t, json.loads(namespace_bytes["completion.json"]), reg_rel)
        pins_core = dumps(pins)
        pins_full = dumps({**pins, "schema": "saea-tfrl-ace-release-pins-v1", "provenance": provenance(t, None)}) if with_prov else pins_core
        add(f"ace-release-pins-i{t}.json", A / f"ace-release-pins-i{t}.json", pins_core, pins_full, "pins")
        files_core = dumps(release_files_doc(t, namespace_bytes), sort_keys=False)
        add(f"ace-i{t}-release-files.json", A / f"ace-i{t}-release-files.json", files_core, files_core, "pins")
        return pins

    with tempfile.TemporaryDirectory(prefix="tfrl-cell-stage-") as scratch_name:
        scratch = Path(scratch_name)
        _link_prepared(scratch, ctx.data_root, ctx.repo_root)
        staged = stage_in_scratch(ctx, t, playbook, enums_doc["intents"], scratch)
        reg_target = ctx.package_dir / f"ace-playbook-i{t}-release-registration.json"
        reg_rel = reg_target.relative_to(ctx.repo_root).as_posix()
        reg_fresh = staged["registration"].read_bytes()
        namespace = ctx.data_root / "knowledge" / "slurp" / "semantic" / f"ace-playbook-i{t}"
        scratch_namespace = scratch / "knowledge" / "slurp" / "semantic" / f"ace-playbook-i{t}"

        plain_entries()
        for fname, path in staged["files"].items():
            raw = staging_bytes(path, scratch, ctx.data_root)
            add(f"ace-release-staging/{fname}", A / "ace-release-staging" / fname, raw, raw, "analysis")
        add(reg_rel, reg_target, reg_fresh, reg_fresh, "registration")

        # the preparer reads the registration from the repository: it can run in the scratch root only once the registration holds the fresh bytes
        prepare_status = "deferred (the registration is not yet in the repository; --execute writes it, then prepares)"
        scratch_ns: dict[str, bytes] = {}
        pins: dict = {}

        def scratch_prepare() -> dict:
            nonlocal scratch_ns, prepare_status
            prepare_in(scratch, ctx.repo_root, reg_target)
            scratch_ns = namespace_files(scratch_namespace)
            prepare_status = "prepared in a scratch root (the real namespace is written only by --execute)"
            return release_entries(scratch_ns, namespace, reg_rel)

        if reg_target.is_file() and reg_target.read_bytes() == reg_fresh:
            pins = scratch_prepare()

        report: dict[str, Any] = {
            "schema": MANIFEST_SCHEMA, "iteration": t, "tool": TOOL_VERSION,
            "sources": {"typed": {k: typed[k] for k in ("run_id", "attempt_id", "outputs_relpath", "outputs_sha256", "rows_total", "roster_relpath", "roster_sha256")},
                        "ace": {k: refl[k] for k in ("run_id", "attempt_id", "outputs_relpath", "outputs_sha256", "rows_total", "roster_relpath", "roster_sha256")},
                        "open_propose_inputs_sha256": propose.get("inputs_sha256")},
            "counts": {"typed": typed_counts, "predictions": pred_counts, "reflector": answer_counts,
                       "playbook": {"items_before": len(drv.resolve_playbook(ctx, t - 1)[1]["items"]) if t > 1 else 0, "items_after": len(playbook["items"]),
                                    "deltas_applied": curated["deltas_in"], "illegal_answers": curated["illegal"], "credit_used": curated["credit"] is not None,
                                    "content_hash": playbook["content_hash"], "release_rows": staged["release"]["row_count"]}},
            "ace_release": {"registration": reg_rel, "registration_sha256": sha256_bytes(reg_fresh)},
        }
        conflicts = [p["name"] for p in plan if p["compare"]["state"] == "differs"]
        if not execute:
            report["ace_release"]["prepare"] = prepare_status
            if pins:
                report["pins"] = pins
            report["artefacts"] = [_row(ctx, p) for p in plan]
            report["conflicts_if_executed"] = conflicts
            report["mode"] = "dry-run"
            return report

        # ---- EXECUTE (write-once)
        if conflicts and not args.supersede:
            raise ToolError("write-once: existing artefacts hold different bytes (use --supersede to rename them first): " + ", ".join(conflicts))
        ns_existing = namespace_files(namespace) if namespace.is_dir() else {}
        for p in plan:
            if p["group"] in ("analysis", "registration"):
                _install(p, args.supersede)
        if not scratch_ns:
            pins = scratch_prepare()                                  # the registration is in the repository now
        if ns_existing and ns_existing != scratch_ns:
            if not args.supersede:
                raise ToolError("write-once: the release namespace holds different bytes (use --supersede)")
            namespace.rename(namespace.with_name(f"{namespace.name}.superseded-{utc_stamp()}"))
            ns_existing = {}
        if not ns_existing:
            prepare_in(ctx.data_root, ctx.repo_root, reg_target)
        if namespace_files(namespace) != scratch_ns:
            raise ToolError("the real preparer output differs from the scratch preparer output")
        for p in plan:
            if p["group"] == "release":
                p["installed"] = "unchanged" if ns_existing else "written (by the preparer)"
            elif p["group"] == "pins":
                _install(p, args.supersede)
        report["ace_release"]["prepare"] = "prepared (scratch and real outputs byte-identical)"
        report["pins"] = pins
        report["artefacts"] = [_row(ctx, p, brief=True) for p in plan]
        manifest_path = A / f"cell-stage-inputs-i{t}.json"
        manifest_bytes = dumps(report)
        if manifest_path.is_file() and manifest_path.read_bytes() != manifest_bytes:
            if not args.supersede:
                raise ToolError("write-once: the cell-stage-inputs manifest holds different bytes (use --supersede)")
            manifest_path.rename(supersede_name(manifest_path))
        if not manifest_path.is_file():
            manifest_path.write_bytes(manifest_bytes)
        result = dict(report)
        result["mode"] = "execute"
        result["artefacts"] = [_row(ctx, p) for p in plan]
        result["manifest"] = {"relpath": manifest_path.relative_to(ctx.data_root).as_posix(), "sha256": sha256_bytes(manifest_bytes)}
        return result


def _install(p: dict, supersede: bool) -> None:
    target: Path = p["target"]
    if target.is_file():
        if p["compare"]["state"] != "differs":
            p["installed"] = "unchanged"
            return
        if not supersede:
            raise ToolError(f"write-once: {p['name']} holds different bytes (use --supersede)")
        target.rename(supersede_name(target))
        p["installed"] = "superseded-and-rewritten"
    else:
        p["installed"] = "written"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(p["full"])


def _row(ctx: drv.Ctx, p: Mapping[str, Any], *, brief: bool = False) -> dict:
    """One artefact row; ``brief`` (the manifest) leaves out what depends on the run (the comparison with the existing bytes, the install state)."""

    target: Path = p["target"]
    try:
        where = target.relative_to(ctx.data_root).as_posix()
    except ValueError:
        where = "repo:" + target.relative_to(ctx.repo_root).as_posix()
    row = {"name": p["name"], "where": where, "sha256": p["fresh_sha256"], "core_sha256": sha256_bytes(p["core"])}
    if brief:
        return row
    row["vs_existing"] = p["compare"]
    if "installed" in p:
        row["installed"] = p["installed"]
    return row


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--iter", type=int, required=True, dest="iteration")
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", drv.DEFAULT_DATA_ROOT)))
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--package-dir", type=Path, default=None)
    parser.add_argument("--lock", type=Path, default=Path(drv.DEFAULT_LOCK))
    parser.add_argument("--execute", action="store_true", help="write the artefacts (default: dry run)")
    parser.add_argument("--supersede", action="store_true", help="rename an existing artefact with different bytes to .superseded-<ts> instead of refusing")
    parser.add_argument("--class-predictions", default=None,
                        help="JSON {operator_class: {slu_pp, basis}}: class-level predictions for the predicted classes (default: none)")
    parser.add_argument("--no-provenance", action="store_true", help="omit the provenance object (the exact hand-script shape)")
    return parser


def main(argv: list[str] | None = None, *, out=print) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args)
    except lib.LoopError as error:
        out(f"REFUSED: {error}")
        return 3
    out(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
