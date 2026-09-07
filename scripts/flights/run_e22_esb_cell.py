#!/usr/bin/env python3
"""Thin CLI for one cell of the Earnings-22 ESB short-form alignment flight.

Sibling of ``scripts/flights/run_calibration_cell.py``, for the Earnings
carrier. Everything the harness can derive from the four config fragments is
left to ``core.flight.FlightRuntime``; what remains here is the one thing that
is genuinely not derivable -- the adapter.

``rails.adapters.earnings.Earnings21Adapter.load_split`` knows exactly two
splits, ``"discovery"`` (all 44 Earnings-21 calls) and ``"dev"`` (the
Earnings-22 subset10), and both yield WHOLE CALLS. An ESB utterance is neither:
it is a derived media item cut from a parent call at a published boundary,
carried by a hash-pinned roster receipt. This entry supplies exactly that
adapter -- the same "bind one hash-pinned roster, read the geometry and the
instruction from the composed config, change nothing in ``rails/adapters/``"
shape ``CalibrationAdapter`` already has for Audio2Tool -- and delegates the
rest.

Two things are deliberately different from the Audio2Tool sibling, and both
are consequences of the media being DERIVED rather than released:

* **``carrier_root`` is the derived-utterance root, not the carrier asset
  dir.** ``core.model.binding`` confines every payload's ``media_relpath``
  under ``binding.carrier_root``, and these WAVs live under
  ``$SPEECHRL_DATA_DIR/derived/e22-esb-utterances/<version>/`` rather than
  inside the locked ``datasets/earnings21-22/earnings22`` tree -- deliberately,
  so a derived artifact never lands inside a dataset working copy D1 hashed.
  The ``carrier_root_resolver`` seam ``FlightRuntime`` already exposes is
  pointed at the derived root instead. This TIGHTENS confinement rather than
  loosening it: the derived root holds this roster's 2,735 WAVs and nothing
  else, where the carrier root holds 125 MP3s and every transcript. The
  per-sample exact-relpath binding check and the D1 media-identity re-hash are
  both unchanged and both still run.
* **``score`` is overridden to a reference-free stub.** The base
  ``Earnings21Adapter.score_response`` scores through
  ``core.scorers.score_asr_outputs``, which resolves a CALL's ``.nlp``
  reference; for an utterance id that would raise, and it would also mean
  reading gold 2,735 times inside the run loop. The per-row ``metrics`` that
  hook produces are dropped by ``FlightRuntime._canonical_output_rows``
  anyway -- the sealed outputs row carries only identity and text -- so the
  paper-facing numbers come, as they must, from the manifest's declared
  scorers through ``core.scoring_batch``.

Modes::

    python scripts/flights/run_e22_esb_cell.py --cell E22-ESB-SMOKE-4 --dry-run
    python scripts/flights/run_e22_esb_cell.py --cell E22-ESB-SMOKE-4 --wire-check
    python scripts/flights/run_e22_esb_cell.py --cell E22-ESB-SMOKE-4 --run

``--dry-run`` stops after ``FlightRuntime.preflight``: no server, no model
contact. ``--wire-check`` drives the whole request path against a fake gate and
a fake transport: still no server and no socket.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

#: The checkout this script belongs to, resolved from the script's own location
#: exactly as ``scripts/flights/run_calibration_cell.py`` already does. The
#: guard below is unchanged in force -- the imported package must resolve inside
#: THIS tree -- so the shared-venv hijack armor still holds; what changes is that
#: a git worktree can now run a dry run or a wire check against its own configs
#: instead of silently loading the main checkout's.
REPO = Path(__file__).resolve().parents[2]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if (
    Path(_pkg.__file__ or "")
    != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
):
    raise SystemExit("package resolves to %s, not this checkout" % (_pkg.__file__,))

from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.evidence import (  # noqa: E402
    resolve_declared_transform_params,
)
from speech_aware_evidence_acquisition.core.evidence_derivation import (  # noqa: E402
    DerivedEvidenceRegistry,
)
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.earnings import (  # noqa: E402
    Earnings21Adapter,
    EarningsSample,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402

DEFAULT_EXPERIMENT = "e22-esb-shortform-alignment-v1"
DEFAULT_DATASET = "earnings22-esb-utterances-2735"
RUNTIME_ROOT = Path("/home/chao")
ROSTER_SCHEMA = "saea-e22-esb-utterance-roster-receipt-v1"
#: Where the 2026-09-04 ESB TEST utterances live. A dataset fragment may name a
#: different derived root through ``e22_esb_derived_subdir`` (the 2026-09-05 dev
#: subset10 population uses ``derived/e22-esb-utterances/dev-v1``); confinement
#: is bound to whichever root the fragment declares, so each population's root
#: still holds exactly its own roster's media and nothing else.
DERIVED_UTTERANCE_SUBDIR = "derived/e22-esb-utterances/v1"


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


def roster_samples(
    roster_path: Path,
    roster_sha256: str,
    data_root_path: Path,
    *,
    limit_sample_ids: Sequence[str] | None = None,
    derived_subdir: str = DERIVED_UTTERANCE_SUBDIR,
) -> tuple[EarningsSample, ...]:
    """Samples built ONLY from the hash-pinned roster receipt's media facts.

    The same discipline the Audio2Tool roster loader applies: identifiers,
    media paths and measured media identity only -- no reference sentence, no
    segment text, nothing a runtime path must never see. Every WAV is re-hashed
    against the roster's own record before it can become a sample, so a byte
    that moved on disk since the cut is caught here rather than at the gate.
    """

    measured = sha256_file(roster_path)
    if measured != roster_sha256:
        raise SystemExit(
            "roster receipt hashes to %s, not the configured %s" % (measured, roster_sha256)
        )
    receipt = json.loads(roster_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != ROSTER_SCHEMA or receipt.get("split_role") == "test":
        raise SystemExit("roster identity or split role is invalid")
    wanted = set(limit_sample_ids) if limit_sample_ids is not None else None
    root = Path(data_root_path).resolve()
    samples: list[EarningsSample] = []
    for item in receipt["items"]:
        sample_id = item["sample_id"]
        if wanted is not None and sample_id not in wanted:
            continue
        media_relpath = item["media_relpath"]
        if not media_relpath.startswith(derived_subdir + "/"):
            raise SystemExit("roster media path is outside the derived root: %s" % media_relpath)
        media_path = (root / media_relpath).resolve()
        media_path.relative_to(root)
        if not media_path.is_file():
            raise SystemExit("roster media file is missing: %s" % media_relpath)
        if sha256_file(media_path) != item["audio_sha256"]:
            raise SystemExit("audio bytes drift for %s" % sample_id)
        samples.append(
            EarningsSample(
                sample_id=sample_id,
                audio_ref=AudioRef(
                    path=media_relpath, sha256=item["audio_sha256"]
                ).validate(),
                audio_seconds=float(item["audio_seconds"]),
                media_relpath=media_relpath,
                carrier_lock_key=str(receipt["carrier"]),
            )
        )
    if wanted is not None and len(samples) != len(wanted):
        found = {sample.sample_id for sample in samples}
        raise SystemExit("roster does not contain %r" % sorted(wanted - found))
    return tuple(sorted(samples, key=lambda sample: sample.sample_id))


class EsbUtteranceAdapter(Earnings21Adapter):
    """``Earnings21Adapter`` bound to one hash-pinned utterance roster, with
    the instruction and the serving geometry taken from the composed config.

    Every override here is data or boundary, never new task behaviour: the
    prompt shape stays the base ``TaskAdapter.assemble_prompt`` default (one
    system message carrying the instruction, one user message carrying the
    audio), which is exactly the shape the Earnings-21 direct arm sent.
    """

    def __init__(
        self,
        lock,
        root,
        *,
        repo_root,
        split_id: str,
        samples: Sequence[EarningsSample],
        instruction_text: str,
        geometry: Mapping[str, object],
        evidence_blocks: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._split_id = split_id
        self._samples = tuple(samples)
        self._instruction_text = instruction_text
        self._evidence_blocks = dict(evidence_blocks or {})
        self.SERVING_SLOTS = int(geometry["slots"])
        self.SERVING_SLOT_TOKENS = int(geometry["slot_tokens"])
        self.SERVING_MAX_TOKENS = int(geometry["max_tokens"])

    def load_split(self, split_id):  # noqa: D102
        if split_id != self._split_id:
            raise ValueError(
                "ESB utterance adapter serves only %s, not %r" % (self._split_id, split_id)
            )
        return self._samples

    def instruction(self, sample):
        """The system message: this sample's evidence blocks, then the
        instruction (``prompt_order`` "evidence-first-system-v3").

        A cell whose baseline fragment declares ``evidence_source: "none"``
        carries no blocks and this returns the instruction unchanged, byte for
        byte -- every sealed Earnings-22 arm keeps its exact system message.

        A cell that DOES declare an evidence source gets that source's rendered
        content joined ahead of the instruction, in the same
        ``[evidence <id>] <content>`` line format ``core.model.transport``
        renders ``supplied_evidence`` in and ``rails.knowledge_provider.
        ConecContextProvider.materialize`` mirrors -- one format for a knowledge
        block in this repository, not a second spelling of it. The blocks are
        resolved ONCE, before the flight, by :func:`resolve_evidence_blocks`,
        and every one of them has already been re-derived from its own source
        bytes by ``DerivedEvidenceRegistry`` before this method can be called.

        Why the system message and not ``supplied_evidence``: this carrier flies
        the shared ``FlightRuntime`` (owner rule, one harness for every arm), and
        that harness assembles a request through ``TaskAdapter.assemble_prompt``
        rather than through ``core.policies.build_arm_payload``. Folding the
        block into the instruction keeps the payload's field set exactly
        ``ARM_VISIBLE_FIELDS["bare-core"]`` -- the sealed comparator's own -- so
        the ONE factor between the two arms is the system text and nothing else.
        """

        block = self._evidence_blocks.get(str(sample.sample_id))
        if not block:
            return self._instruction_text
        return f"{block}\n\n{self._instruction_text}"

    def score(self, sample, response):
        """Reference-free, deliberately.

        The base implementation resolves the CALL's ``.nlp`` reference through
        ``core.scorers.score_asr_outputs``; an ESB utterance has no such file,
        and the per-row ``metrics`` this hook produces are dropped by
        ``FlightRuntime._canonical_output_rows`` before anything is sealed. The
        paper-facing numbers come from the manifest's declared scorers
        (``asr-wer-esb-whisper`` / ``asr-wer-esb`` / ``cost``) through
        ``core.scoring_batch``, strictly after the run. Returning identity plus
        a length keeps the run loop free of gold entirely.
        """

        return {
            "parsed": True,
            "sample_id": sample.sample_id,
            "response_chars": len(response),
            "scored_post_hoc_by": "asr-wer-esb-whisper / asr-wer-esb via core.scoring_batch",
        }


def resolve_evidence_blocks(
    values: Mapping[str, object],
    lock,
    root: Path,
    samples: Sequence[EarningsSample],
) -> tuple[dict[str, str], dict[str, object]]:
    """Every sample's evidence, resolved and RE-DERIVED before the flight.

    Returns ``({sample_id -> rendered block text}, receipt)``. A fragment whose
    ``evidence_source`` is ``"none"`` returns an empty map and a receipt saying
    so, which is the sealed comparator's own path, unchanged.

    The rail is the one ``core.driver.run_experiment`` runs, called here rather
    than re-implemented: each item's ``DerivedEvidenceRecord`` is registered with
    ``DerivedEvidenceRegistry`` against the params THIS composed config declares
    (``core.evidence.resolve_declared_transform_params``), so the registry
    independently re-invokes the pinned transform on the same source bytes and
    refuses anything that does not reproduce. An evidence source that lied about
    its params, its transform or its content stops the flight here, before a
    server exists.

    A ``carrier_bound`` record additionally has no D1 anchor by construction
    (``core.base.DerivedEvidenceRecord``): the Earnings-22 metadata brief is
    exactly that case and says so in its own module docstring, so this function
    reports each record's ``carrier_bound`` flag into the receipt instead of
    silently implying an identity rail that did not run.
    """

    source_id = str(values.get("evidence_source", "none"))
    if source_id == "none":
        return {}, {"evidence_source": "none", "samples_with_evidence": 0, "items": 0}
    if values.get("evidence_mismatch", False):
        raise SystemExit(
            "evidence_mismatch is not supported on this entry point: the rotated "
            "mismatch decorator lives in core.driver.run_experiment, and a control "
            "this cell needs is declared as its own evidence source instead"
        )
    source = EVIDENCE_SOURCES.resolve(source_id)
    registry = DerivedEvidenceRegistry()
    blocks: dict[str, str] = {}
    digests: dict[str, str] = {}
    carrier_bound = set()
    transforms = set()
    items_total = 0
    for sample in samples:
        items = source(lock, root, sample.sample_id, sample.carrier_lock_key, values)
        if not items:
            raise SystemExit(
                "evidence source %r returned no evidence for %s; a cell that supplies "
                "knowledge to some rows and not others is not one factor"
                % (source_id, sample.sample_id)
            )
        rendered: list[str] = []
        for item in items:
            record = item.derivation
            if record is None:
                raise SystemExit(
                    "evidence source %r returned an item with no derivation record"
                    % source_id
                )
            registry.register(
                record,
                source_content=item.derivation_source_bytes,
                derived_content=item.content.encode("utf-8"),
                params=resolve_declared_transform_params(record.transform_name, values),
            )
            transforms.add(f"{record.transform_name}@{record.transform_version}")
            carrier_bound.add(bool(record.carrier_bound))
            rendered.append(f"[evidence {item.evidence_id}] {item.content}")
            items_total += 1
        block = "\n".join(rendered)
        blocks[sample.sample_id] = block
        digests[sample.sample_id] = hashlib.sha256(block.encode("utf-8")).hexdigest()
    receipt = {
        "evidence_source": source_id,
        "samples_with_evidence": len(blocks),
        "items": items_total,
        "transforms": sorted(transforms),
        "carrier_bound": sorted(carrier_bound),
        "derivation_records_verified": items_total,
        "distinct_block_digests": len(set(digests.values())),
        "blocks_sha256": hashlib.sha256(
            "\n".join(f"{key},{digests[key]}" for key in sorted(digests)).encode("utf-8")
        ).hexdigest(),
        "block_format": "[evidence <evidence_id>] <content>, joined by newlines",
        "prompt_position": "the system message, ahead of the task instruction",
    }
    return blocks, receipt


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

    roster_relpath = str(values["e22_esb_roster_receipt"])
    if roster_relpath.startswith("/") or "\\" in roster_relpath:
        raise SystemExit("e22_esb_roster_receipt must be a repo-relative POSIX path")
    derived_subdir = str(values.get("e22_esb_derived_subdir", DERIVED_UTTERANCE_SUBDIR))
    if (
        derived_subdir.startswith("/")
        or "\\" in derived_subdir
        or ".." in derived_subdir.split("/")
        or not derived_subdir.startswith("derived/")
    ):
        raise SystemExit(
            "e22_esb_derived_subdir must be a relative POSIX path under 'derived/'"
        )
    samples = roster_samples(
        REPO / roster_relpath,
        str(values["e22_esb_roster_receipt_sha256"]),
        root,
        limit_sample_ids=limit_sample_ids,
        derived_subdir=derived_subdir,
    )
    if len(samples) != int(values["e22_esb_count"]):
        raise SystemExit(
            "roster resolved %d samples, the dataset fragment declares %s"
            % (len(samples), values["e22_esb_count"])
        )

    instruction_text = values.get("task_instruction")
    if not isinstance(instruction_text, str) or not instruction_text:
        raise SystemExit("baseline fragment must declare a non-empty task_instruction")
    split_id = str(values["split_id"])

    evidence_blocks, evidence_receipt = resolve_evidence_blocks(values, lock, root, samples)
    if evidence_receipt["evidence_source"] != "none":
        log(
            "evidence %s: %d items over %d samples, %d distinct blocks, %s"
            % (
                evidence_receipt["evidence_source"],
                evidence_receipt["items"],
                evidence_receipt["samples_with_evidence"],
                evidence_receipt["distinct_block_digests"],
                evidence_receipt["blocks_sha256"][:12],
            )
        )

    def adapter_factory(lock_, root_):
        return EsbUtteranceAdapter(
            lock_,
            root_,
            repo_root=REPO,
            split_id=split_id,
            samples=samples,
            instruction_text=instruction_text,
            geometry=geometry,
            evidence_blocks=evidence_blocks,
        )

    def derived_carrier_root(_lock, _carrier_lock_key, resolved_root):
        """See this module's docstring: payload confinement is bound to the
        derived-utterance root, which holds exactly this roster's media."""

        return Path(resolved_root) / derived_subdir

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
        carrier_root_resolver=derived_carrier_root,
        lock=lock,
        campaign_active=campaign_active,
        host="127.0.0.1",
        port=int(str(values["base_url"]).rsplit(":", 1)[-1]),
        request_id_prefix="e22esb",
    )
    # What the evidence rail resolved, carried on the returned runtime so a
    # dry run's and a wire check's receipts can report it. A plain attribute
    # rather than a FlightRuntime field: the rail is this entry point's, not
    # the shared harness's, and the harness must not grow a carrier-specific
    # slot for it.
    runtime.evidence_receipt = evidence_receipt
    return runtime


def _write_receipt(path: Path, document: Mapping[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return sha256_file(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", required=True)
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--dataset", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--campaign-active", action="store_true")
    parser.add_argument("--workers", type=int, default=None)
    parser.add_argument("--preprocess-workers", type=int, default=None)
    parser.add_argument(
        "--include-per-sample",
        action="store_true",
        help=(
            "forward include_per_sample to core.scoring_batch, exactly as the SLURP "
            "sibling scripts/flights/run_slurp_closed_list_cell.py already does. The "
            "PAIRED analysis reads it: analysis.paired contrasts a cell against the "
            "sealed comparator ROW BY ROW, which needs the per-sample scores the "
            "batch otherwise summarizes away. Off by default, so every existing "
            "cell's receipt shape is unchanged"
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--wire-check", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()

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

    # A cell whose population entry enumerates explicit ``ids`` (the smoke)
    # narrows the roster to exactly those rows and fails closed on any id the
    # roster does not contain; a cell that enumerates none flies the whole
    # roster. The narrowing is READ FROM THE REGISTERED FRAGMENT, never from a
    # command-line list, so a smoke can never quietly fly a different four rows
    # than the ones its exposure row names.
    limit = None
    populations = experiment_doc.get("populations")
    if isinstance(populations, Mapping):
        for value in populations.values():
            if isinstance(value, Mapping) and value.get("dataset_fragment") == dataset:
                if isinstance(value.get("ids"), list):
                    limit = [str(sample_id) for sample_id in value["ids"]]
                break

    runtime = build_runtime(
        cell=cell,
        dataset=dataset,
        experiment=args.experiment,
        run_id=run_id,
        attempt_id=attempt_id,
        campaign_active=args.campaign_active,
        limit_sample_ids=limit,
    )

    if args.dry_run:
        log("dry run: preflight only, no server, no contact")
        receipt = dict(runtime.preflight())
        receipt["evidence"] = runtime.evidence_receipt
        print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
        return 0

    if args.wire_check:
        log("wire check: whole request path, fake gate and transport, zero sockets")
        receipt = dict(runtime.wire_check(max_workers=1))
        receipt["cell_id"] = args.cell
        receipt["evidence"] = runtime.evidence_receipt
        document = {
            "schema": "saea-e22-esb-wire-check-v1",
            "study": "speech-aware-evidence-acquisition",
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "flight_run_id": run_id,
            "cells_checked": [args.cell],
            "model_contacts": 0,
            "servers_started": 0,
            "boundary": (
                "zero model contacts: the only fakes are the gate and the transport "
                "(core.flight.runtime.WireCheckGate / WireCheckTransport, which never opens a "
                "socket). Any score below is computed over the transport's canned response and "
                "is not a measurement of anything."
            ),
            "cells": [receipt],
        }
        seal = receipt["seal_and_score"]
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
            log("  seal/score refused: %s" % seal["reason"])
        if args.output is not None:
            log("receipt sha256 %s -> %s" % (_write_receipt(args.output, document), args.output))
        else:
            print(json.dumps(document, indent=2, sort_keys=True, default=str))
        return 0 if seal["status"] != "REFUSED" else 1

    log("flight: %s cell %s attempt %s" % (run_id, args.cell, attempt_id))
    stages: dict[str, object] = {}
    stages["preflight"] = runtime.preflight()
    log("preflight ok: %d samples" % stages["preflight"]["sample_count"])
    # FLIGHT_STAGES requires preprocess before serve for every arm. For this
    # raw-audio arm the builtin promoter promotes nothing and says so
    # ("this arm's D2 field set carries no speech_feature_parts"); the stage
    # is still run, because skipping it is what FlightStageOrderError exists
    # to catch and because the receipt it writes is the record that no packet
    # plane was involved in this number.
    stages["preprocess"] = runtime.preprocess(workers=args.preprocess_workers)
    log(
        "preprocess: %s, %d packets"
        % (
            stages["preprocess"]["promoter_meta"].get("audio_path"),
            stages["preprocess"]["packet_count"],
        )
    )
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
        stages["score"] = runtime.score(include_per_sample=args.include_per_sample)
        log("scored")
    except BaseException as failure:  # noqa: BLE001 -- re-raised below
        # An attempt that opened and then died must be recorded ABORTED, not
        # left dangling: core.attempts treats (run_id, attempt_id) as a
        # one-time key and the plan's budget is metered cumulatively across
        # every attempt of a run id, so the durable spend has to be visible to
        # whatever recovery follows.
        log("ABORTING attempt: %s: %s" % (type(failure).__name__, failure))
        try:
            runtime.abort("%s: %s" % (type(failure).__name__, failure))
        except Exception as abort_failure:  # noqa: BLE001
            log("abort itself failed: %s" % (abort_failure,))
        raise
    finally:
        stopped = runtime.stop_serving()
        stages["stop_serving"] = stopped
        log("server stopped")

    document = {
        "schema": "saea-e22-esb-flight-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "run_id": run_id,
        "attempt_id": attempt_id,
        "cell_id": args.cell,
        "experiment": args.experiment,
        "dataset": dataset,
        "stages": stages,
    }
    if args.output is not None:
        log("receipt sha256 %s -> %s" % (_write_receipt(args.output, document), args.output))
    else:
        print(json.dumps(document, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
