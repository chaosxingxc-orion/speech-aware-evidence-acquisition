#!/usr/bin/env python3
"""Thin CLI for one round of the EVO-S1 PROPOSER flight (text only, no audio).

Fourth sibling of ``run_calibration_cell.py``, ``run_e22_esb_cell.py`` and
``run_slurp_closed_list_cell.py``. Everything the harness can derive from the four
config fragments is left to ``core.flight.FlightRuntime``, which already carries
this arm end to end (``_run_construction_proposer``, the ``construction_targets``
payload field, and ``_wire_check_construction_problems``). What remains here is
what is genuinely not derivable:

* THE ADAPTER, bound to the round roster's own draw ANCHORS and label-free. The
  system message of a proposer contact is NOT the adapter's instruction: it is that
  draw's rendered proposer instruction, so the adapter only has to name the right
  samples and refuse to resolve gold.
* THE CONSTRUCTION MATERIAL RESOLVER. ``core.flight.runtime.
  _default_construction_material`` is Audio2Tool's -- it reads
  ``data.audio2tool.load_query_rows`` and a tool registry. SLURP's material is the
  pair of TRAIN slot schemas plus ``(intent, sentence, gold entities)`` rows, which
  ``rails.evolution_carrier.load_carrier_material`` already assembles for the
  model-free propose step. This entry injects that through the seam the runtime
  already exposes, so no base module learns a second carrier.

One contact per draw, serial, in roster order. No audio part is sent at all: the
``construction-proposer-text`` arm's D2-frozen field set carries no speech field.
The rendered instruction is never written to a receipt -- it carries construction
utterance text and gold entities -- and the sealed outputs the candidates step
reads carry the model's ANSWER, which is a schema block set, not a gold row.

Modes (identical in shape to the closed-list cell)::

    python scripts/flights/run_slurp_evo_proposer_cell.py --round 1 --dry-run
    python scripts/flights/run_slurp_evo_proposer_cell.py --round 1 --wire-check
    python scripts/flights/run_slurp_evo_proposer_cell.py --round 1 --run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
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

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit("package resolves to %s, not the main checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root, load_lock, umbrella_lock_path)
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SlurpAdapter, SlurpSample)
from speech_aware_evidence_acquisition.rails.evolution import (  # noqa: E402
    LoopConfig, build_proposer_material)
from speech_aware_evidence_acquisition.rails.evolution_carrier import (  # noqa: E402
    load_carrier_material, load_state)
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402

RUNTIME_ROOT = Path("/home/chao")
LOOP_CONFIG = "configs/knowledge/slurp-evo-s1/loop-v1.json"
DATASET_FRAGMENT = "slurp-speech-native-evo-exemplars-430"
BASELINE_FRAGMENT = "slurp-evo-s1-proposer"
RUNTIME_VIEW_SCHEMA = "saea-speech-native-runtime-view-v1"
# The proposer prompt is a few thousand tokens and its answer is capped at 1,536,
# so one 16,384-token slot holds it with room to spare and the server geometry is
# the reward cells' own -- the fewest resident geometries the GPU has to see.
SERVING_SLOTS, SERVING_SLOT_TOKENS, SERVING_MAX_TOKENS = 4, 16384, 1536


def log(message: str) -> None:
    print("[%s] %s" % (datetime.now(timezone.utc).strftime("%H:%M:%SZ"), message), flush=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ProposerSlurpAdapter(SlurpAdapter):
    """``SlurpAdapter`` bound to ONE round's draw anchors, label-free.

    Both overrides are DATA. ``load_split`` returns the anchors this instance was
    built with instead of re-reading the whole TRAIN split; ``gold`` refuses
    outright, because a proposer answer is an artifact and not an answer to a
    scored row. ``instruction`` is never the wire system message on this arm --
    ``FlightRuntime._run_construction_proposer`` sends the draw's own rendered
    proposer instruction -- and returns a marker that would be obvious in any
    receipt if it ever were.
    """

    SERVING_SLOTS = SERVING_SLOTS
    SERVING_SLOT_TOKENS = SERVING_SLOT_TOKENS
    SERVING_MAX_TOKENS = SERVING_MAX_TOKENS

    def __init__(self, lock, root, *, repo_root, split_id, samples) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._split_id = split_id
        self._samples = tuple(samples)

    def load_split(self, split_id, *, allow_heldout=False, allow_synthetic=False):  # noqa: D102
        if allow_heldout or allow_synthetic:
            raise SystemExit("the proposer cell never opens the held-out or synthetic splits")
        if split_id != self._split_id:
            raise ValueError("proposer adapter serves only %s" % self._split_id)
        return self._samples

    def instruction(self, sample):  # noqa: D102
        return (
            "UNUSED ON THIS ARM: the system message of a construction-proposer contact "
            "is the draw's own rendered proposer instruction."
        )

    def gold(self, sample):  # noqa: D102
        raise SystemExit("the proposer cell is label-free at the adapter; gold never enters it")

    def score(self, sample, response: str):  # noqa: D102
        return {"sample_id": sample.sample_id, "response_chars": len(response),
                "scored": "never -- a proposer answer is an artifact, harvested model-free"}


def anchors(values: Mapping[str, object], roster: Mapping[str, object]) -> tuple[SlurpSample, ...]:
    """The round's draw anchors, as label-free samples with measured media facts.

    The runtime view is the identity statement for the WHOLE exemplar pool; the
    round roster names which of its rows are this round's anchors. Taking the media
    facts from the view (and re-hashing each file against them) is what makes the
    anchors' D1 supplement -- built for the pool -- the one a real model touch then
    re-verifies.
    """

    items = values.get("items")
    if values.get("schema") != RUNTIME_VIEW_SCHEMA or not isinstance(items, list):
        raise SystemExit("dataset fragment is not a %s runtime view" % RUNTIME_VIEW_SCHEMA)
    wanted = {str(item["sample_id"]) for item in roster["items"]}
    by_id = {str(item["sample_id"]): item for item in items}
    missing = sorted(wanted - set(by_id))
    if missing:
        raise SystemExit("the exemplar runtime view lacks anchor(s): %s" % missing[:5])
    root = data_root()
    samples = []
    for sample_id in sorted(wanted):
        item = by_id[sample_id]
        if not sample_id.startswith("slurp:train:"):
            raise SystemExit("a proposer anchor must be a TRAIN row; %r is not" % sample_id)
        measured = sha256_file(root / str(item["media_relpath"]))
        if measured != str(item["audio_sha256"]):
            raise SystemExit("media %s hashes to %s" % (item["media_relpath"], measured))
        samples.append(SlurpSample(
            sample_id=sample_id,
            audio_ref=AudioRef(path=str(item["media_relpath"]), sha256=measured).validate(),
            audio_seconds=float(item["audio_seconds"]), utterance_id=sample_id.split(":")[2],
            media_relpath=str(item["media_relpath"]),
            scenario="", action="", intent="", entities=()))
    return tuple(samples)


def slurp_construction_material(round_index: int):
    """The ``construction_material_resolver`` seam, SLURP's half.

    Same contract as ``core.flight.runtime._default_construction_material`` and the
    same fail-closed roster reading; only the CARRIER material differs, and it is
    resolved by the module that already owns that edge for the model-free steps.
    """

    def resolve(values, *, lock, data_root, repo_root, samples):
        config = LoopConfig.from_json(
            json.loads((Path(repo_root) / LOOP_CONFIG).read_text(encoding="utf-8")))
        relpath = values.get("construction_proposer_roster_receipt")
        if not isinstance(relpath, str) or not relpath:
            raise SystemExit("the per-round experiment fragment must name the proposer roster")
        path = Path(repo_root) / relpath
        declared = values.get("construction_proposer_roster_receipt_sha256")
        if isinstance(declared, str) and declared and sha256_file(path) != declared:
            raise SystemExit("proposer roster receipt %s hashes to %s" % (relpath, sha256_file(path)))
        roster = json.loads(path.read_text(encoding="utf-8"))
        state = load_state(Path(repo_root), config, round_index)
        carrier = load_carrier_material(
            Path(repo_root), config, step="propose", lock=lock, data_root=Path(data_root))
        return build_proposer_material(
            roster,
            registry_rows=carrier.registry_rows,
            target_tools=config.targets,
            incumbent_overrides=state.incumbent_overrides,
            exemplar_rows=carrier.exemplar_rows,
            carrier_lock_key=config.carrier_lock_key,
            artifact_family=config.artifact_family,
            artifact_keys={t: config.keys_of_target(t) for t in config.targets},
            slot_schema=carrier.slot_schema,
            unfloored_schema=carrier.unfloored_schema,
            entity_type_names=carrier.entity_type_names,
            min_members=1 if config.target_kind == "scenario" else 2,
        )

    return resolve


def _write(path: Path, document: Mapping[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
                    encoding="utf-8", newline="\n")
    return sha256_file(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--experiment", default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--campaign-active", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--outputs-jsonl", type=Path, default=None,
                        help="where to copy the sealed responses the candidates step reads")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--wire-check", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)

    config = LoopConfig.from_json(json.loads((REPO / LOOP_CONFIG).read_text(encoding="utf-8")))
    experiment = args.experiment or f"{config.slug}-proposer-r{args.round:02d}"
    document = json.loads(
        (REPO / config.experiments_reldir / f"{experiment}.json").read_text(encoding="utf-8"))
    cells = [cell for cell in document["cells"] if isinstance(cell, Mapping)]
    if not cells:
        raise SystemExit("experiment fragment declares no cells")
    model = str(cells[0]["model_fragment"])
    if len({str(cell["model_fragment"]) for cell in cells}) != 1:
        raise SystemExit("a round's proposer cells must share one model fragment")
    run_id = str(document["experiment_id"])
    attempt_id = args.attempt_id or f"attempt-r{args.round}-p"

    composed = compose(REPO, model, DATASET_FRAGMENT, BASELINE_FRAGMENT, experiment)
    values = composed.values
    lock, root = load_lock(umbrella_lock_path()), data_root()
    roster_relpath = str(values["construction_proposer_roster_receipt"])
    roster = json.loads((REPO / roster_relpath).read_text(encoding="utf-8"))
    samples = anchors(values, roster)
    log("round %d: %d draws, %d anchors, config %s"
        % (args.round, len(roster["items"]), len(samples), composed.config_hash[:16]))
    if len(samples) != len(roster["items"]):
        raise SystemExit("one contact per draw: %d anchors for %d draws"
                         % (len(samples), len(roster["items"])))

    identity = {
        "config_hash": composed.config_hash,
        "model_fragment": model,
        "dataset_fragment": DATASET_FRAGMENT,
        "baseline_fragment": BASELINE_FRAGMENT,
        "experiment_fragment": experiment,
        "proposer_roster_receipt": roster_relpath,
        "proposer_roster_receipt_sha256": sha256_file(REPO / roster_relpath),
        "proposer_roster_split_identity_hash": str(roster["split_identity_hash"]),
        "draws": len(roster["items"]),
        "anchors": len(samples),
        "anchor_audio_seconds": round(sum(s.audio_seconds for s in samples), 6),
        "serving_geometry": {"slots": SERVING_SLOTS, "slot_tokens": SERVING_SLOT_TOKENS,
                             "max_tokens": SERVING_MAX_TOKENS},
        "decoding_max_tokens": int(values["decoding_params"]["max_tokens"]),
        "audio_parts_sent": 0,
    }
    if identity["decoding_max_tokens"] != SERVING_MAX_TOKENS:
        raise SystemExit("model fragment max_tokens %s != the arm's %d"
                         % (identity["decoding_max_tokens"], SERVING_MAX_TOKENS))

    runtime = FlightRuntime(
        REPO, root, model=model, dataset=DATASET_FRAGMENT, baseline=BASELINE_FRAGMENT,
        experiment=experiment, run_id=run_id, attempt_id=attempt_id, runtime_root=RUNTIME_ROOT,
        adapter_factory=lambda lock_, root_: ProposerSlurpAdapter(
            lock_, root_, repo_root=REPO, split_id=str(values["split_id"]), samples=samples),
        construction_material_resolver=slurp_construction_material(args.round),
        lock=lock, campaign_active=args.campaign_active, host="127.0.0.1",
        port=int(str(values["base_url"]).rsplit(":", 1)[-1]), request_id_prefix="slurpevoprop")

    if args.dry_run:
        log("dry run: preflight only, no server, no contact")
        receipt = runtime.preflight()
        document_out = {
            "schema": "saea-slurp-evo-proposer-dry-run-v1", "run_id": run_id,
            "attempt_id": attempt_id, "round": args.round, "model_contacts": 0,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "identity": identity, "preflight": receipt,
            "attempt_aborted": runtime.abort("dry-run: preflight only, no contact")}
    elif args.wire_check:
        log("wire check: whole request path, fake gate and transport, zero sockets")
        receipt = dict(runtime.wire_check(max_workers=1))
        document_out = {
            "schema": "saea-slurp-evo-proposer-wire-check-v1", "flight_run_id": run_id,
            "round": args.round, "model_contacts": 0, "servers_started": 0,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "identity": identity, "cells": [receipt],
            "boundary": ("zero model contacts: the only fakes are the gate and the transport "
                         "(core.flight.runtime.WireCheckGate / WireCheckTransport, which never "
                         "opens a socket)")}
        log("  arm=%s contacts=%d problems=%s"
            % (receipt["arm"], receipt["contact_count"], receipt.get("problems")))
    else:
        log("flight: %s attempt %s" % (run_id, attempt_id))
        stages: dict[str, object] = {"preflight": runtime.preflight()}
        log("preflight ok: %d samples" % stages["preflight"]["sample_count"])
        stages["preprocess"] = runtime.preprocess(workers=1)
        stages["serve"] = runtime.serve()
        log("served")
        try:
            stages["run_phases"] = runtime.run_phases(workers=1)
            log("run_phases: %d contacts in %.1f s"
                % (stages["run_phases"]["contact_count"], stages["run_phases"]["wall_seconds"]))
            stages["seal"] = runtime.seal()
            log("sealed: %s" % stages["seal"]["manifest_path"])
        except BaseException as failure:  # noqa: BLE001 -- re-raised below
            log("ABORTING attempt: %s: %s" % (type(failure).__name__, failure))
            try:
                runtime.abort("%s: %s" % (type(failure).__name__, failure))
            except Exception as abort_failure:  # noqa: BLE001
                log("abort itself failed: %s" % (abort_failure,))
            raise
        finally:
            stages["stop_serving"] = runtime.stop_serving()
            log("server stopped")
        if args.outputs_jsonl is not None:
            source = Path(str(stages["seal"]["manifest_path"])).parent
            rows = sorted(source.glob("*.outputs.jsonl"))
            if len(rows) != 1:
                raise SystemExit("expected exactly one sealed outputs file, found %d" % len(rows))
            args.outputs_jsonl.parent.mkdir(parents=True, exist_ok=True)
            args.outputs_jsonl.write_bytes(rows[0].read_bytes())
            log("copied %s -> %s" % (rows[0], args.outputs_jsonl))
        document_out = {
            "schema": "saea-slurp-evo-proposer-flight-receipt-v1", "run_id": run_id,
            "attempt_id": attempt_id, "round": args.round, "experiment": experiment,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "identity": identity, "stages": stages}

    document_out["study"] = "speech-aware-evidence-acquisition"
    if args.output is not None:
        log("receipt sha256 %s -> %s" % (_write(args.output, document_out), args.output))
    else:
        print(json.dumps(document_out, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
