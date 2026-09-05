#!/usr/bin/env python3
"""Thin CLI for one cell of the SLURP closed-list direct baseline flight.

Third sibling of ``scripts/flights/run_calibration_cell.py`` (Audio2Tool) and
``scripts/flights/run_e22_esb_cell.py`` (Earnings), for the SLURP carrier.
Everything the harness can derive from the four config fragments is left to
``core.flight.FlightRuntime``; what remains here is the one thing that is
genuinely not derivable -- the adapter -- plus the two assertions that make
this particular cell's identity checkable before takeoff.

**This is the first SLURP cell ever flown through ``FlightRuntime``.** Every
sealed SLURP arm before it went through ``rails.runner``'s speech-native agent
loop, which is why the 2026-09-04 scoring-alignment audit found those attempt
directories carrying ``flight-state.json`` and ``arm*-outputs.jsonl`` but no
``*.run-manifest.json``, and rows keyed ``final_response_text`` where every
registered scorer reads ``text``. Sealing through ``FlightRuntime.seal`` fixes
both, durably, for this carrier.

Why an adapter subclass here at all. ``FlightRuntime`` reads its system message
from ``adapter.instruction(sample)`` and has no config seam of its own, and the
stock ``SlurpAdapter.load_split("devel")`` returns all 8,690 devel recordings
WITH their gold SLU layer attached. This entry supplies an adapter that

* is bound to ONE hash-pinned roster -- the frozen DEV-1000 runtime view the
  sealed 2026-08-25 lock arms flew, read id-for-id, with every media file
  re-hashed against the view's own record before it can become a sample;
* is **label-free by construction**: samples are built from the runtime view,
  which carries media identity only. ``scenario``/``action``/``intent``/
  ``entities`` are left empty and ``gold()`` refuses outright, so no SLURP
  gold label is ever loaded into the process that talks to the model. The
  paper-facing numbers come, as they must, from the manifest's declared
  scorers through ``core.scoring_batch`` after the seal;
* takes its instruction from the composed config
  (``core.instructions.resolve_active_task_instruction``), so the closed label
  inventory lives in a hash-pinned template plus a registered fill rather than
  in this file.

The subclass lives here rather than under ``rails/adapters/`` deliberately:
``scripts/checks/engineering_base_check.py`` scans ``src/`` and
``docs/checks/**/launcher/`` for ``TaskAdapter`` subclasses, and both existing
flight scripts already put their roster-bound adapter in exactly this place.
``rails/adapters/slurp.py`` is not edited by this campaign.

Modes::

    python scripts/flights/run_slurp_closed_list_cell.py --cell <id> --dry-run
    python scripts/flights/run_slurp_closed_list_cell.py --cell <id> --wire-check
    python scripts/flights/run_slurp_closed_list_cell.py --cell <id> --run

``--dry-run`` stops after ``FlightRuntime.preflight``: no server, no model
contact. ``--wire-check`` drives the whole request path against a fake gate and
a fake transport: still no server and no socket.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if (
    Path(_pkg.__file__ or "")
    != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
):
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime  # noqa: E402
from speech_aware_evidence_acquisition.core.instructions import (  # noqa: E402
    resolve_active_task_instruction,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SlurpAdapter,
    SlurpSample,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    parse_slu_response,
)

DEFAULT_EXPERIMENT = "slurp-dev1000-closed-list-direct-v1"
RUNTIME_ROOT = Path("/home/chao")
RUNTIME_VIEW_SCHEMA = "saea-speech-native-runtime-view-v1"

# The sealed comparator this cell's prompt must extend by a pure suffix
# (configs/baseline/slurp-direct-closed-list.json "instruction_basis"): the
# whole system message all 1,000 sealed DEV-1000 M0 MODEL_REQUEST records
# carried, as sha256 over its UTF-8 bytes, and its length.
SEALED_M0_INSTRUCTION_SHA256 = (
    "cef527896e9beef5774305e01dc29192fc2d5ca89fba5143e82f0b91a7cb86b8"
)
SEALED_M0_INSTRUCTION_CHARS = 5747


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print("[%s] %s" % (stamp, message), flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_experiment(experiment: str) -> Mapping[str, object]:
    path = REPO / "configs" / "experiment" / f"{experiment}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_cells(experiment: str) -> dict[str, Mapping[str, object]]:
    cells = load_experiment(experiment).get("cells")
    if not isinstance(cells, list) or not cells:
        raise SystemExit(f"experiment fragment {experiment} declares no cells")
    out: dict[str, Mapping[str, object]] = {}
    for cell in cells:
        required = {"cell_id", "arm", "baseline_fragment", "model_fragment"}
        if not isinstance(cell, Mapping) or not required <= set(cell):
            raise SystemExit(f"experiment cell must declare {sorted(required)}")
        out[str(cell["cell_id"])] = cell
    return out


def population_ids(
    experiment_doc: Mapping[str, object], dataset: str
) -> list[str] | None:
    """Explicit sample ids for this dataset fragment, or ``None`` for the
    whole roster.

    Read from the REGISTERED fragment, never from a command line, so a smoke
    can never quietly fly four different rows than the ones its exposure row
    names (the SAEA-E22-ESB precedent, applied unchanged).
    """

    populations = experiment_doc.get("populations")
    if not isinstance(populations, list):
        return None
    for entry in populations:
        if not isinstance(entry, Mapping):
            continue
        if entry.get("dataset_fragment") != dataset:
            continue
        ids = entry.get("ids")
        if isinstance(ids, list) and ids:
            return [str(sample_id) for sample_id in ids]
    return None


def roster_samples(
    values: Mapping[str, object],
    data_root_path: Path,
    *,
    limit_sample_ids: Sequence[str] | None = None,
    workers: int = 16,
) -> tuple[SlurpSample, ...]:
    """LABEL-FREE samples built only from the frozen runtime view's own media
    facts, each media file re-hashed against the view's record.

    The runtime view (``configs/dataset/slurp-speech-native-dev1000.json``) is
    a ``saea-speech-native-runtime-view-v1`` document that carries, per item,
    ``sample_id``/``media_relpath``/``audio_sha256``/``audio_seconds``/
    ``sample_rate_hz``/``packet_id`` and NOTHING ELSE -- no scenario, no
    action, no entity, no sentence. The ``SlurpSample`` fields that would hold
    SLURP's gold SLU layer are therefore filled with empty values here, and
    :meth:`ClosedListSlurpAdapter.gold` refuses to be called at all, so gold
    cannot reach the request path even by accident.
    """

    items = values.get("items")
    if values.get("schema") != RUNTIME_VIEW_SCHEMA or not isinstance(items, list):
        raise SystemExit("dataset fragment is not a %s runtime view" % RUNTIME_VIEW_SCHEMA)
    declared_count = values.get("count")
    if isinstance(declared_count, int) and declared_count != len(items):
        raise SystemExit(
            "runtime view count %s disagrees with its own %d items"
            % (declared_count, len(items))
        )
    wanted = set(limit_sample_ids) if limit_sample_ids is not None else None
    root = Path(data_root_path).resolve()
    selected: list[Mapping[str, object]] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise SystemExit("runtime view item must be an object")
        sample_id = str(item["sample_id"])
        if wanted is not None and sample_id not in wanted:
            continue
        if sample_id.startswith("slurp:test:"):
            raise SystemExit(
                "runtime view names the HELD OUT test split sample %r; refusing" % sample_id
            )
        selected.append(item)
    if wanted is not None:
        missing = wanted - {str(item["sample_id"]) for item in selected}
        if missing:
            raise SystemExit("runtime view lacks requested sample id(s): %s" % sorted(missing))

    def build(item: Mapping[str, object]) -> SlurpSample:
        sample_id = str(item["sample_id"])
        media_relpath = str(item["media_relpath"])
        media_path = root / media_relpath
        measured = sha256_file(media_path)
        if measured != str(item["audio_sha256"]):
            raise SystemExit(
                "media %s hashes to %s, not the runtime view's %s"
                % (media_relpath, measured, item["audio_sha256"])
            )
        return SlurpSample(
            sample_id=sample_id,
            audio_ref=AudioRef(path=media_relpath, sha256=measured).validate(),
            audio_seconds=float(item["audio_seconds"]),
            utterance_id=sample_id.split(":")[2],
            media_relpath=media_relpath,
            scenario="",
            action="",
            intent="",
            entities=(),
        )

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        samples = list(pool.map(build, selected))
    return tuple(sorted(samples, key=lambda sample: sample.sample_id))


class ClosedListSlurpAdapter(SlurpAdapter):
    """``SlurpAdapter`` bound to one hash-pinned, label-free roster, with the
    system instruction taken from the composed config.

    Both overrides are DATA, not behaviour. ``load_split`` returns the roster
    this instance was constructed with instead of re-reading the whole devel
    split; ``instruction`` returns the config-resolved text instead of the
    module-level ``_INSTRUCTION`` constant. The serving geometry is left
    exactly as ``rails/adapters/slurp.py`` declares it (8 slots x 8,192 slot
    tokens, 64 completion tokens), which is already the geometry the sealed
    M0 arm flew (``-np 8 -c 65536``, ``max_tokens 64``); the flight asserts
    that against the model fragment's own ``server_args`` rather than
    silently overriding either side.
    """

    def __init__(
        self,
        lock,
        root,
        *,
        repo_root: Path,
        split_id: str,
        samples: Sequence[SlurpSample],
        instruction_text: str,
    ) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._split_id = split_id
        self._samples = tuple(samples)
        if not isinstance(instruction_text, str) or not instruction_text:
            raise SystemExit("closed-list cell requires a non-empty resolved instruction")
        self._instruction_text = instruction_text

    def load_split(self, split_id, *, allow_heldout=False, allow_synthetic=False):  # noqa: D102
        if allow_heldout or allow_synthetic:
            raise SystemExit("closed-list cell never opens the held-out or synthetic splits")
        if split_id != self._split_id:
            raise ValueError(
                "closed-list adapter serves only %s, not %r" % (self._split_id, split_id)
            )
        return self._samples

    def instruction(self, sample):  # noqa: D102
        return self._instruction_text

    def gold(self, sample):  # noqa: D102
        raise SystemExit(
            "closed-list cell is label-free: gold never enters the flight process. "
            "The paper-facing numbers come from the manifest's declared scorers "
            "through core.scoring_batch, after the seal."
        )

    def score(self, sample, response: str):  # noqa: D102
        """Reference-free per-row stub.

        ``FlightRuntime._canonical_output_rows`` drops per-row ``metrics``
        from the sealed outputs entirely, so this hook's only job is to not
        need gold. ``parsed`` is genuinely useful, though: it is the
        JSON-parse outcome of the response, computed by the same
        ``reproduction.slurp_scoring.parse_slu_response`` the official scorer
        will use later, so an unparseable-response problem shows up in the
        run log rather than only after the seal.
        """

        _scenario, _action, _entities, parsed = parse_slu_response(response)
        return {
            "sample_id": sample.sample_id,
            "parsed": parsed,
            "response_chars": len(response),
            "scored_post_hoc_by": "slurp-slu-official through core.scoring_batch",
        }


def assert_instruction_extends_sealed_m0(instruction: str, sealed_head: str | None) -> dict:
    """Fail closed unless the wire instruction is the sealed DEV-1000 M0
    instruction plus a pure suffix.

    This is the whole scientific claim of the cell expressed as an assertion:
    if the prompt were rewritten rather than extended, the paired contrast
    against the sealed M0 rows would measure a prompt rewrite instead of the
    closed label inventory. ``sealed_head`` is optional -- the hash and the
    length are pinned above and are checked whenever the caller can supply the
    sealed text; without it the check still verifies that the rendered
    instruction is longer than the sealed one and that its first
    ``SEALED_M0_INSTRUCTION_CHARS`` characters hash to the pinned value.
    """

    prefix = instruction[:SEALED_M0_INSTRUCTION_CHARS]
    measured = hashlib.sha256(prefix.encode("utf-8")).hexdigest()
    if measured != SEALED_M0_INSTRUCTION_SHA256:
        raise SystemExit(
            "the first %d characters of the resolved instruction hash to %s, not the "
            "sealed DEV-1000 M0 instruction's %s; this cell must EXTEND that prompt, "
            "never replace it"
            % (SEALED_M0_INSTRUCTION_CHARS, measured, SEALED_M0_INSTRUCTION_SHA256)
        )
    if len(instruction) <= SEALED_M0_INSTRUCTION_CHARS:
        raise SystemExit("the resolved instruction adds no closed label inventory at all")
    if sealed_head is not None and not instruction.startswith(sealed_head):
        raise SystemExit("the resolved instruction is not a prefix-extension of the sealed text")
    suffix = instruction[SEALED_M0_INSTRUCTION_CHARS:]
    return {
        "sealed_m0_instruction_sha256": measured,
        "sealed_m0_instruction_chars": SEALED_M0_INSTRUCTION_CHARS,
        "resolved_instruction_sha256": hashlib.sha256(instruction.encode("utf-8")).hexdigest(),
        "resolved_instruction_chars": len(instruction),
        "added_suffix_sha256": hashlib.sha256(suffix.encode("utf-8")).hexdigest(),
        "added_suffix_chars": len(suffix),
        "relation": "resolved == sealed_m0_instruction + suffix",
    }


def assert_geometry_matches_server_args(values: Mapping[str, object]) -> dict:
    """The model fragment's ``-np``/``-c`` must already equal the adapter's
    declared geometry -- ``FlightRuntime.serve`` overrides both, so a silent
    override can never be the thing that makes them agree."""

    slots = int(SlurpAdapter.SERVING_SLOTS)
    slot_tokens = int(SlurpAdapter.SERVING_SLOT_TOKENS)
    args = [str(item) for item in values.get("server_args", [])]
    def flag(name: str) -> int:
        if name not in args:
            raise SystemExit("model fragment server_args declares no %s" % name)
        return int(args[args.index(name) + 1])
    if flag("-np") != slots:
        raise SystemExit("model fragment -np %d != adapter slots %d" % (flag("-np"), slots))
    if flag("-c") != slots * slot_tokens:
        raise SystemExit(
            "model fragment -c %d != slots x slot_tokens %d"
            % (flag("-c"), slots * slot_tokens)
        )
    max_tokens = int(SlurpAdapter.SERVING_MAX_TOKENS)
    declared = values.get("decoding_params")
    if isinstance(declared, Mapping) and int(declared.get("max_tokens", max_tokens)) != max_tokens:
        raise SystemExit(
            "model fragment decoding_params.max_tokens %s != adapter max_tokens %d"
            % (declared.get("max_tokens"), max_tokens)
        )
    return {"slots": slots, "slot_tokens": slot_tokens, "max_tokens": max_tokens}


def build_runtime(
    *,
    cell: Mapping[str, object],
    dataset: str,
    experiment: str,
    run_id: str,
    attempt_id: str,
    campaign_active: bool,
    limit_sample_ids: Sequence[str] | None,
    sealed_head: str | None = None,
) -> tuple[FlightRuntime, dict]:
    model = str(cell["model_fragment"])
    baseline = str(cell["baseline_fragment"])
    composed = compose(REPO, model, dataset, baseline, experiment)
    values = composed.values
    if values.get("arm") != cell["arm"]:
        raise SystemExit(
            "composed arm %r != cell arm %r" % (values.get("arm"), cell["arm"])
        )
    lock = load_lock(umbrella_lock_path())
    root = data_root()

    geometry = assert_geometry_matches_server_args(values)
    instruction = resolve_active_task_instruction(values, REPO, lock, root)
    if instruction is None:
        raise SystemExit(
            "the closed-list cell's baseline fragment must declare an ACTIVE "
            "task_instruction_template (task_instruction_template_active: true)"
        )
    identity = assert_instruction_extends_sealed_m0(instruction, sealed_head)
    identity["config_hash"] = composed.config_hash
    identity["serving_geometry"] = geometry
    identity["instruction_template"] = values.get("task_instruction_template")
    identity["instruction_fill"] = values.get("task_instruction_fill")

    samples = roster_samples(values, root, limit_sample_ids=limit_sample_ids)
    if not samples:
        raise SystemExit("roster resolved to zero samples")
    leaked = [
        sample.sample_id
        for sample in samples
        if sample.scenario or sample.action or sample.intent or sample.entities
    ]
    if leaked:
        raise SystemExit("roster carries gold on %d sample(s); refusing" % len(leaked))
    identity["sample_count"] = len(samples)
    identity["roster_view_sha256"] = values.get("runtime_view_sha256")

    split_id = str(values["split_id"])

    def adapter_factory(lock_, root_):
        return ClosedListSlurpAdapter(
            lock_,
            root_,
            repo_root=REPO,
            split_id=split_id,
            samples=samples,
            instruction_text=instruction,
        )

    runtime = FlightRuntime(
        REPO,
        root,
        model=model,
        dataset=dataset,
        baseline=baseline,
        experiment=experiment,
        run_id=run_id,
        attempt_id=attempt_id,
        runtime_root=RUNTIME_ROOT,
        adapter_factory=adapter_factory,
        lock=lock,
        campaign_active=campaign_active,
        host="127.0.0.1",
        port=int(str(values["base_url"]).rsplit(":", 1)[-1]),
        request_id_prefix="slurpcl",
    )
    return runtime, identity


def _write_receipt(path: Path, document: Mapping[str, object]) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, indent=2, sort_keys=True, default=str) + "\n"
    path.write_text(payload, encoding="utf-8", newline="\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--campaign-active", action="store_true")
    parser.add_argument("--preprocess-workers", type=int, default=None)
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--sealed-instruction", default=None)
    parser.add_argument("--output", type=Path, default=None)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--wire-check", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)

    experiment_doc = load_experiment(args.experiment)
    cells = load_cells(args.experiment)
    if args.cell not in cells:
        raise SystemExit("unknown cell %r; known: %s" % (args.cell, sorted(cells)))
    cell = cells[args.cell]
    dataset = args.dataset or str(cell["dataset_fragment"])
    run_id = args.run_id or str(experiment_doc["experiment_id"])
    attempt_id = args.attempt_id or "attempt-%s-%s" % (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        hashlib.sha256(f"{run_id}{args.cell}".encode()).hexdigest()[:6],
    )
    sealed_head = (
        Path(args.sealed_instruction).read_text(encoding="utf-8")
        if args.sealed_instruction
        else None
    )

    runtime, identity = build_runtime(
        cell=cell,
        dataset=dataset,
        experiment=args.experiment,
        run_id=run_id,
        attempt_id=attempt_id,
        campaign_active=args.campaign_active,
        limit_sample_ids=population_ids(experiment_doc, dataset),
        sealed_head=sealed_head,
    )
    log(
        "instruction: %d chars = sealed M0 %d + suffix %d (%s)"
        % (
            identity["resolved_instruction_chars"],
            identity["sealed_m0_instruction_chars"],
            identity["added_suffix_chars"],
            identity["resolved_instruction_sha256"][:16],
        )
    )
    log("roster: %d samples, config hash %s" % (identity["sample_count"], identity["config_hash"]))

    if args.dry_run:
        log("dry run: preflight only, no server, no contact")
        receipt = runtime.preflight()
        aborted = runtime.abort("dry-run: preflight only, no server and no model contact")
        document = {
            "schema": "saea-slurp-closed-list-dry-run-v1",
            "study": "speech-aware-evidence-acquisition",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "run_id": run_id,
            "attempt_id": attempt_id,
            "cell_id": args.cell,
            "model_contacts": 0,
            "identity": identity,
            "preflight": receipt,
            "attempt_aborted": aborted,
        }
        if args.output is not None:
            log("receipt sha256 %s -> %s" % (_write_receipt(args.output, document), args.output))
        else:
            print(json.dumps(document, indent=2, sort_keys=True, default=str))
        return 0

    if args.wire_check:
        log("wire check: whole request path, fake gate and transport, zero sockets")
        receipt = dict(runtime.wire_check(max_workers=args.max_workers))
        receipt["cell_id"] = args.cell
        seal = receipt["seal_and_score"]
        document = {
            "schema": "saea-slurp-closed-list-wire-check-v1",
            "study": "speech-aware-evidence-acquisition",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "flight_run_id": run_id,
            "cells_checked": [args.cell],
            "model_contacts": 0,
            "servers_started": 0,
            "identity": identity,
            "boundary": (
                "zero model contacts: the only fakes are the gate and the transport "
                "(core.flight.runtime.WireCheckGate / WireCheckTransport, which never opens a "
                "socket). Any score below is computed over the transport's canned response and "
                "is not a measurement of anything."
            ),
            "cells": [receipt],
        }
        log(
            "  arm=%s contacts=%d payload_keys=%d seal_and_score=%s"
            % (
                receipt["arm"],
                receipt["contact_count"],
                len(receipt["payload_keys"]),
                seal["status"],
            )
        )
        if seal["status"] == "REFUSED":
            log("  seal/score refused: %s" % seal.get("reason"))
        if args.output is not None:
            log("receipt sha256 %s -> %s" % (_write_receipt(args.output, document), args.output))
        else:
            print(json.dumps(document, indent=2, sort_keys=True, default=str))
        return 0 if seal["status"] != "REFUSED" else 1

    log("flight: %s cell %s attempt %s" % (run_id, args.cell, attempt_id))
    stages: dict[str, object] = {}
    stages["preflight"] = runtime.preflight()
    log("preflight ok: %d samples" % stages["preflight"]["sample_count"])
    stages["preprocess"] = runtime.preprocess(workers=args.preprocess_workers)
    log("preprocess: %d packets" % stages["preprocess"]["packet_count"])
    stages["serve"] = runtime.serve()
    log("served")
    try:
        stages["run_phases"] = runtime.run_phases(workers=args.workers)
        log(
            "run_phases: %d contacts in %.1f s"
            % (
                stages["run_phases"]["contact_count"],
                stages["run_phases"]["wall_seconds"],
            )
        )
        stages["seal"] = runtime.seal()
        log("sealed: %s" % stages["seal"]["manifest_path"])
        stages["score"] = runtime.score(max_workers=args.max_workers)
        log("scored")
    except BaseException as failure:  # noqa: BLE001 -- re-raised below
        # An attempt that opened and then died must be recorded ABORTED, not
        # left dangling: core.attempts treats (run_id, attempt_id) as a
        # one-time key and the plan's budget is metered cumulatively across
        # every attempt of a run id.
        log("ABORTING attempt: %s: %s" % (type(failure).__name__, failure))
        try:
            runtime.abort("%s: %s" % (type(failure).__name__, failure))
        except Exception as abort_failure:  # noqa: BLE001
            log("abort itself failed: %s" % (abort_failure,))
        raise
    finally:
        stages["stop_serving"] = runtime.stop_serving()
        log("server stopped")

    document = {
        "schema": "saea-slurp-closed-list-flight-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": run_id,
        "attempt_id": attempt_id,
        "cell_id": args.cell,
        "experiment": args.experiment,
        "dataset": dataset,
        "identity": identity,
        "stages": stages,
    }
    if args.output is not None:
        log("receipt sha256 %s -> %s" % (_write_receipt(args.output, document), args.output))
    else:
        print(json.dumps(document, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
