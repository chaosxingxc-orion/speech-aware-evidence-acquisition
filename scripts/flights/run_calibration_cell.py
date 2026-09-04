#!/usr/bin/env python3
"""Thin CLI for one cell of a factorial direct-baseline flight.

Everything this script used to bind by hand is now a config-driven default
inside ``core.flight.FlightRuntime`` (2026-09-04, Phase 2a): the packet
promoter resolves the baseline fragment's ``speech_packet_promotion_receipt``,
the client factory supplies ``speech_feature_root``/``speech_packet_bindings``
for a speech-feature arm, the tool-schema resolver goes through
``core.policies.TOOL_SCHEMA_FILLS``, ``serve`` preserves the model fragment's
whole ``server_args`` (plus its ``role`` and model root), and ``run_phases``
carries the one-contact packet path itself.

What remains here is the ONE thing that is genuinely not derivable from the
four fragments: the adapter. ``saea-driver flight`` builds a bare
``Audio2ToolAdapter``, whose ``load_split("discovery")`` now resolves 608
samples (the frozen 400 plus two 104-row post-seal AgentLoop scoring
receipts), whose serving geometry is its own class constant rather than the
model fragment's, and whose ``instruction()`` always renders the legacy
registry -- none of which suits a receipt-scoped factorial cell. This entry
supplies exactly that adapter and delegates the rest.

The cells themselves are READ from the experiment fragment's own ``cells``
array, so a new cell is a config edit, never a code edit.

Modes::

    python scripts/flights/run_calibration_cell.py --cell A0prime-legacy-raw --dry-run
    python scripts/flights/run_calibration_cell.py --cell A0prime-legacy-raw --run

``--dry-run`` stops after ``FlightRuntime.preflight``: no server, no model
contact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
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
from speech_aware_evidence_acquisition.core.flight.queue import FlightQueue  # noqa: E402
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402

DEFAULT_EXPERIMENT = "a2t-direct-calibration-400-v1"
DEFAULT_DATASET = "audio2tool-calibration-400"
RUNTIME_ROOT = Path("/home/chao")


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
    """Every cell the experiment fragment declares, keyed by ``cell_id``."""

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


def roster_samples(
    roster_path: Path,
    roster_sha256: str,
    data_root_path: Path,
    *,
    limit_sample_ids: Sequence[str] | None = None,
) -> tuple[Audio2ToolSample, ...]:
    """Samples built ONLY from the hash-pinned roster receipt's media facts.

    The same discipline ``scripts/a2t_g1_preprocess.py`` already applies for
    a receipt-scoped roster: no carrier task data, no gold, no expected
    calls -- identifiers, media paths and measured media identity only.
    ``limit_sample_ids`` narrows the roster to a registered smoke subset and
    fails closed on any id the roster does not contain.
    """

    measured = sha256_file(roster_path)
    if measured != roster_sha256:
        raise SystemExit(
            "roster receipt hashes to %s, not the configured %s" % (measured, roster_sha256)
        )
    receipt = json.loads(roster_path.read_text(encoding="utf-8"))
    wanted = set(limit_sample_ids) if limit_sample_ids is not None else None
    root = Path(data_root_path).resolve()
    samples: list[Audio2ToolSample] = []
    for item in receipt["items"]:
        sample_id = item["sample_id"]
        if wanted is not None and sample_id not in wanted:
            continue
        media_relpath = item["media_relpath"]
        media_path = (root / media_relpath).resolve()
        media_path.relative_to(root)
        if not media_path.is_file():
            raise SystemExit("roster media file is missing: %s" % media_relpath)
        if sha256_file(media_path) != item["audio_sha256"]:
            raise SystemExit("audio bytes drift for %s" % sample_id)
        samples.append(
            Audio2ToolSample(
                sample_id=sample_id,
                audio_ref=AudioRef(
                    path=media_relpath, sha256=item["audio_sha256"]
                ).validate(),
                audio_seconds=float(item["audio_seconds"]),
                media_relpath=media_relpath,
            )
        )
    if wanted is not None and len(samples) != len(wanted):
        found = {sample.sample_id for sample in samples}
        raise SystemExit("roster does not contain %r" % sorted(wanted - found))
    return tuple(sorted(samples, key=lambda sample: sample.sample_id))


class CalibrationAdapter(Audio2ToolAdapter):
    """``Audio2ToolAdapter`` bound to one hash-pinned roster, with the
    system instruction and the serving geometry taken from the composed
    config rather than from this class.

    Both overrides are data, not behaviour: ``instruction`` returns the
    baseline fragment's literal ``task_instruction`` when it declares one
    (the native tool-calling cells, whose registry travels in the request's
    ``tools`` field instead of the system message) and otherwise falls
    through to the unchanged legacy registry template; the serving-geometry
    class attributes are shadowed by per-instance values read from the model
    fragment's own ``serving_geometry`` object, so the fragment stays the
    single authority for ``-np``/``-c`` and ``rails/adapters/audio2tool.py``
    is never edited.
    """

    def __init__(
        self,
        lock,
        root,
        *,
        repo_root,
        split_id: str,
        samples: Sequence[Audio2ToolSample],
        instruction_text: str | None,
        geometry: Mapping[str, object],
    ) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._split_id = split_id
        self._samples = tuple(samples)
        self._instruction_text = instruction_text
        self.SERVING_SLOTS = int(geometry["slots"])
        self.SERVING_SLOT_TOKENS = int(geometry["slot_tokens"])
        self.SERVING_MAX_TOKENS = int(geometry["max_tokens"])

    def load_split(self, split_id):  # noqa: D102
        if split_id != self._split_id:
            raise ValueError(
                "calibration adapter serves only %s, not %r" % (self._split_id, split_id)
            )
        return self._samples

    def instruction(self, sample):  # noqa: D102
        if self._instruction_text is not None:
            return self._instruction_text
        return super().instruction(sample)


def build_runtime(
    *,
    cell: Mapping[str, object],
    dataset: str,
    experiment: str,
    run_id: str,
    attempt_id: str,
    campaign_active: bool,
    limit_sample_ids: Sequence[str] | None = None,
) -> FlightRuntime:
    model = str(cell["model_fragment"])
    baseline = str(cell["baseline_fragment"])
    arm = str(cell["arm"])
    composed = compose(REPO, model, dataset, baseline, experiment)
    values = composed.values
    if values.get("arm") != arm:
        raise SystemExit(
            "cell %r declares arm %r but its baseline fragment declares %r"
            % (cell["cell_id"], arm, values.get("arm"))
        )
    lock = load_lock(umbrella_lock_path())
    root = data_root()

    geometry = values.get("serving_geometry")
    if not isinstance(geometry, Mapping) or set(geometry) != {
        "slots",
        "slot_tokens",
        "max_tokens",
    }:
        raise SystemExit(
            "model fragment must declare an exact serving_geometry "
            "{slots, slot_tokens, max_tokens} object"
        )
    # FlightRuntime.serve now merges the fragment's own server_args and only
    # overrides -np/-c from this geometry; assert the two already agree so a
    # silent override can never be the thing that makes them agree.
    server_args = [str(value) for value in values["server_args"]]
    declared_c = server_args[server_args.index("-c") + 1]
    declared_np = server_args[server_args.index("-np") + 1]
    if int(declared_np) != int(geometry["slots"]) or int(declared_c) != int(
        geometry["slots"]
    ) * int(geometry["slot_tokens"]):
        raise SystemExit(
            "model fragment server_args (-c %s -np %s) disagree with its declared "
            "serving_geometry %r" % (declared_c, declared_np, dict(geometry))
        )

    samples = roster_samples(
        REPO / str(values["a2t_calibration_subset_receipt"]),
        str(values["a2t_calibration_subset_receipt_sha256"]),
        root,
        limit_sample_ids=limit_sample_ids,
    )
    if limit_sample_ids is None and len(samples) != int(values["a2t_calibration_count"]):
        raise SystemExit("roster resolved %d samples" % len(samples))
    split_id = str(values["split_id"])
    instruction_text = values.get("task_instruction")
    if instruction_text is not None and not isinstance(instruction_text, str):
        raise SystemExit("baseline task_instruction must be a string when declared")

    def adapter_factory(lock_, root_):
        return CalibrationAdapter(
            lock_,
            root_,
            repo_root=REPO,
            split_id=split_id,
            samples=samples,
            instruction_text=instruction_text,
            geometry=geometry,
        )

    return FlightRuntime(
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
        request_id_prefix="a2tcal",
    )


def _run_wire_check(*, selected, runtimes, run_id, output, max_workers) -> int:
    """Run ``FlightRuntime.wire_check`` for every requested cell and write one
    receipt covering all of them.

    Generic by construction: the cells come from the experiment fragment and
    the check itself lives in the harness, so any carrier that flies through
    ``FlightRuntime`` gets the same proof for free.
    """

    cells: list[Mapping[str, object]] = []
    for cell_id, runtime in zip(selected, runtimes, strict=True):
        log("wire check: %s" % cell_id)
        receipt = dict(runtime.wire_check(max_workers=max_workers))
        receipt["cell_id"] = cell_id
        cells.append(receipt)
        seal = receipt["seal_and_score"]
        log(
            "  arm=%s contacts=%d payload_keys=%d tool_schemas=%d id_slot=%s "
            "packets_verified=%d seal_and_score=%s"
            % (
                receipt["arm"],
                receipt["contact_count"],
                len(receipt["payload_keys"]),
                receipt["tool_schemas_count"],
                receipt["id_slot"],
                len(receipt["speech_packets_verified"]),
                seal["status"],
            )
        )
        if seal["status"] == "REFUSED":
            log("  seal/score refused: %s" % seal["reason"])
    document = {
        "schema": "saea-a2t-calibration-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "flight_run_id": run_id,
        "cells_checked": list(selected),
        "model_contacts": 0,
        "servers_started": 0,
        "boundary": (
            "zero model contacts: the only fakes are the gate and the transport "
            "(core.flight.runtime.WireCheckGate / WireCheckTransport, which never "
            "opens a socket). Any score below is computed over the transport's canned "
            "response and is not a measurement of anything."
        ),
        "cells": cells,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    log("wire-check receipt written: %s (sha256 %s)" % (output, sha256_file(output)[:12]))
    return 0


def _run_queue(*, selected, runtimes, run_id, dry_run, max_workers) -> int:
    """Run several cells through ``core.flight.FlightQueue``.

    The queue is the owner rule's own realization: one resident server per
    serving geometry, reused across same-geometry cells, stopped on a
    genuine geometry change, with each sealed cell's official scoring
    overlapped onto the next cell's generation. ``shutdown()`` in the
    ``finally`` is what guarantees no llama-server is left resident if a
    cell raises mid-queue.
    """

    queue = FlightQueue(runtimes, dry_run=dry_run)
    summary: list[Mapping[str, object]] = []
    try:
        log("queue: %d cell(s) -> %s" % (len(selected), ", ".join(selected)))
        entries = queue.run()
        if len(entries) != len(runtimes):
            raise SystemExit(
                "queue dispatched %d of %d cells; a cell that never became ready "
                "was left pending rather than silently dropped"
                % (len(entries), len(runtimes))
            )
        scores = queue.drain_scores()
        for entry, score in zip(entries, scores, strict=True):
            summary.append(
                {
                    "attempt_id": entry.flight.attempt_id,
                    "dry_run": entry.dry_run,
                    "served_geometry": entry.served_geometry,
                    "receipts": entry.flight.receipts.as_json(),
                    "score": score,
                }
            )
    finally:
        queue.shutdown()
        log("queue: shut down; no server left resident")
    print(
        json.dumps(
            {"run_id": run_id, "cells": selected, "entries": summary},
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument(
        "--cell",
        default=None,
        help="one cell id; mutually exclusive with --cells",
    )
    parser.add_argument(
        "--cells",
        default=None,
        help=(
            "comma-separated cell ids run through core.flight.FlightQueue, which "
            "keeps ONE resident server per serving geometry, reuses it across "
            "same-geometry cells, stops it on a genuine geometry change, and "
            "overlaps each sealed cell's scoring with the next cell's generation"
        ),
    )
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument(
        "--sample-ids",
        default=None,
        help=(
            "comma-separated roster sample ids to narrow the flight to a registered "
            "smoke subset; omit to fly the whole roster"
        ),
    )
    parser.add_argument("--campaign-active", action="store_true")
    parser.add_argument("--preprocess-workers", type=int, default=None)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument(
        "--wire-check-out",
        type=Path,
        default=(
            REPO
            / "docs/checks/speech-aware-evidence-acquisition"
            / "2026-09-04-a2t-direct-calibration-400-v1"
            / "wire-check"
            / "wire-check.json"
        ),
        help="where --wire-check writes its receipt",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument(
        "--wire-check",
        action="store_true",
        help=(
            "contact-free wiring proof: drive every requested cell's real client, "
            "adapter, payload binding, tool schemas and promoted packets against a "
            "fake transport, then seal and score the result. Starts no server and "
            "makes zero model contacts"
        ),
    )
    args = parser.parse_args()

    cells = load_cells(args.experiment)
    if bool(args.cell) == bool(args.cells):
        raise SystemExit("give exactly one of --cell or --cells")
    selected = (
        [args.cell]
        if args.cell
        else [part.strip() for part in args.cells.split(",") if part.strip()]
    )
    unknown = [name for name in selected if name not in cells]
    if unknown:
        raise SystemExit(
            "unknown cell(s) %r; this experiment declares %s" % (unknown, sorted(cells))
        )
    run_id = args.run_id or str(load_experiment(args.experiment)["experiment_id"])
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    limit_sample_ids = (
        tuple(part.strip() for part in args.sample_ids.split(",") if part.strip())
        if args.sample_ids
        else None
    )

    def attempt_for(cell_id: str) -> str:
        if args.attempt_id and len(selected) == 1:
            return args.attempt_id
        return "attempt-%s-%s" % (stamp, cell_id.replace("-", "").lower())

    runtimes = [
        build_runtime(
            cell=cells[cell_id],
            dataset=args.dataset,
            experiment=args.experiment,
            run_id=run_id,
            attempt_id=attempt_for(cell_id),
            campaign_active=bool(args.campaign_active),
            limit_sample_ids=limit_sample_ids,
        )
        for cell_id in selected
    ]

    if args.wire_check:
        return _run_wire_check(
            selected=selected,
            runtimes=runtimes,
            run_id=run_id,
            output=Path(args.wire_check_out),
            max_workers=args.max_workers,
        )

    if len(selected) > 1:
        return _run_queue(
            selected=selected,
            runtimes=runtimes,
            run_id=run_id,
            dry_run=bool(args.dry_run),
            max_workers=args.max_workers,
        )

    cell = cells[selected[0]]
    attempt_id = attempt_for(selected[0])
    runtime = runtimes[0]
    args.cell = selected[0]

    if args.dry_run:
        receipt = runtime.preflight()
        runtime.abort("dry-run: preflight only, no server and no model contact")
        print(
            json.dumps(
                {
                    "cell": args.cell,
                    "arm": cell["arm"],
                    "baseline": cell["baseline_fragment"],
                    "model": cell["model_fragment"],
                    "run_id": run_id,
                    "attempt_id": attempt_id,
                    "sample_count": len(limit_sample_ids or ()) or None,
                    "dry_run": True,
                    "receipt": receipt,
                },
                indent=2,
                sort_keys=True,
                default=str,
            )
        )
        return 0

    log("cell %s: preflight" % args.cell)
    runtime.preflight()
    log("cell %s: preprocess" % args.cell)
    runtime.preprocess(workers=args.preprocess_workers)
    log("cell %s: serve" % args.cell)
    runtime.serve()
    log("cell %s: run_phases" % args.cell)
    runtime.run_phases()
    log("cell %s: seal" % args.cell)
    runtime.seal()
    log("cell %s: score" % args.cell)
    runtime.score(max_workers=args.max_workers)
    print(
        json.dumps(
            {
                "cell": args.cell,
                "run_id": run_id,
                "attempt_id": attempt_id,
                "receipts": runtime.receipts.as_json(),
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
