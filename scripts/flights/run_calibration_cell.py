#!/usr/bin/env python3
"""One generic entry point for every cell of a factorial direct-baseline flight.

``saea-driver flight`` cannot run an Audio2Tool calibration cell end to end
today: ``core.flight.FlightRuntime``'s ``packet_promoter`` seam is
fail-closed by design (``_default_packet_promoter``), its ``client_factory``
default supplies no ``speech_feature_root``/``speech_packet_bindings`` for a
speech-feature arm, its ``tool_schema_resolver`` seam is ``None`` (so a
native tool-calling arm refuses), its ``serve`` stage derives only ``-np``
and ``-c`` from the adapter's ``serving_geometry()`` and drops every other
``server_args`` flag the model fragment declares, and
``Audio2ToolAdapter.load_split("discovery")`` now resolves 608 samples (the
frozen 400 plus two 104-row post-seal AgentLoop scoring receipts) rather
than the calibration population. This script binds exactly those seams and
nothing else; it adds no model-facing behaviour of its own.

It is generic on purpose: the cells are READ from the experiment fragment's
own ``cells`` array (``cell_id`` -> ``arm`` / ``baseline_fragment`` /
``model_fragment``), so a new cell is a config edit, never a code edit. The
only two behaviours that branch are the two audio paths the factorial itself
is about:

* raw audio (``bare-core`` family): the packet plane is not used, so the
  promoter promotes nothing and says so; requests carry ``input_audio`` and
  run through ``rails.runner.run_rails_experiment`` unchanged.
* speech-feature packets (``speech-feature-query`` family): the promoter
  re-materializes the registered promotion receipt's packets through
  ``core.model.speech_features.
  materialize_legacy_cached_speech_feature_packets``, and each request
  carries exactly one ``input_speech_features`` query descriptor through
  ``FrozenCoreClient.complete(..., speech_feature_sample_id=...)``.

Modes::

    python scripts/flights/run_calibration_cell.py --cell A0prime-legacy-raw --dry-run
    python scripts/flights/run_calibration_cell.py --cell A0prime-legacy-raw --run

``--dry-run`` stops after ``FlightRuntime.preflight`` (config composition,
receipt-bound split load, ExecutionPlan validation, gate open, exposure-row
re-check, clean-tree assertion, attempt reservation and the prompt-budget
estimate). It starts no server and makes no model contact.
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
from speech_aware_evidence_acquisition.core.flight.runtime import (  # noqa: E402
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    materialize_legacy_cached_speech_feature_packets,
)
from speech_aware_evidence_acquisition.core.policies import TOOL_SCHEMA_FILLS  # noqa: E402
from speech_aware_evidence_acquisition.core.session import start_session  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient  # noqa: E402
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    ArmResult,
    RunSummary,
    run_rails_experiment,
)

DEFAULT_EXPERIMENT = "a2t-direct-calibration-400-v1"
DEFAULT_DATASET = "audio2tool-calibration-400"
RUNTIME_ROOT = Path("/home/chao")
PROMOTE_WORKERS = 8
EXPECTED_N_EMBD = 2048


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print("[%s] %s" % (stamp, message), flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_cells(experiment: str) -> dict[str, Mapping[str, object]]:
    """Every cell the experiment fragment declares, keyed by ``cell_id``."""

    path = REPO / "configs" / "experiment" / f"{experiment}.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    cells = document.get("cells")
    if not isinstance(cells, list) or not cells:
        raise SystemExit(f"experiment fragment {experiment} declares no cells")
    out: dict[str, Mapping[str, object]] = {}
    for cell in cells:
        required = {"cell_id", "arm", "baseline_fragment", "model_fragment"}
        if not isinstance(cell, Mapping) or not required <= set(cell):
            raise SystemExit(f"experiment cell must declare {sorted(required)}")
        out[str(cell["cell_id"])] = cell
    return out


def receipt_packet_id(sample_id: str) -> str:
    return sample_id.replace(":", "/")


def roster_samples(
    roster_path: Path, roster_sha256: str, data_root_path: Path
) -> tuple[Audio2ToolSample, ...]:
    """Samples built ONLY from the hash-pinned roster receipt's media facts.

    The same discipline ``scripts/a2t_g1_preprocess.py`` already applies for
    a receipt-scoped roster: no carrier task data, no gold, no expected
    calls -- identifiers, media paths and measured media identity only.
    """

    measured = sha256_file(roster_path)
    if measured != roster_sha256:
        raise SystemExit(
            "roster receipt hashes to %s, not the configured %s" % (measured, roster_sha256)
        )
    receipt = json.loads(roster_path.read_text(encoding="utf-8"))
    root = Path(data_root_path).resolve()
    samples: list[Audio2ToolSample] = []
    for item in receipt["items"]:
        sample_id = item["sample_id"]
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
    server_args = list(values["server_args"])
    declared_c = server_args[server_args.index("-c") + 1]
    declared_np = server_args[server_args.index("-np") + 1]
    if int(declared_np) != int(geometry["slots"]) or int(declared_c) != int(
        geometry["slots"]
    ) * int(geometry["slot_tokens"]):
        raise SystemExit(
            "model fragment server_args (-c %s -np %s) disagree with its declared "
            "serving_geometry %r" % (declared_c, declared_np, dict(geometry))
        )

    roster_path = REPO / str(values["a2t_calibration_subset_receipt"])
    samples = roster_samples(
        roster_path, str(values["a2t_calibration_subset_receipt_sha256"]), root
    )
    if len(samples) != int(values["a2t_calibration_count"]):
        raise SystemExit("roster resolved %d samples" % len(samples))
    split_id = str(values["split_id"])
    instruction_text = values.get("task_instruction")
    if instruction_text is not None and not isinstance(instruction_text, str):
        raise SystemExit("baseline task_instruction must be a string when declared")

    arm_fields = ARM_VISIBLE_FIELDS[arm]
    is_packet_arm = "speech_feature_parts" in arm_fields

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

    # ---- seam: packet promotion ----------------------------------------
    def packet_promoter(*, adapter, data_root, samples, workers):
        if not is_packet_arm:
            return (), {
                "audio_path": "raw-audio-mmproj",
                "packets_required": False,
                "reason": (
                    "this cell serves raw audio through the bf16 mmproj; the speech-"
                    "feature packet plane is not used and nothing is promoted"
                ),
            }
        promotion_receipt = Path(str(values["speech_packet_promotion_receipt"]))
        if not promotion_receipt.is_file():
            raise FlightRuntimeError(
                "packet cell requires the registered promotion receipt %s; run the "
                "SAEA-SN-A2T-CALIBRATION-400-PREPROCESS pass first" % promotion_receipt
            )
        promotion = json.loads(promotion_receipt.read_text(encoding="utf-8"))
        feature_root = Path(str(promotion["feature_root"]))
        legacy_cache_dir = Path(str(promotion["legacy_cache_dir"]))
        bindings = tuple(
            {
                "packet_id": receipt_packet_id(sample.sample_id),
                "audio_path": str(Path(data_root) / sample.media_relpath),
            }
            for sample in samples
        )
        packets = materialize_legacy_cached_speech_feature_packets(
            feature_root=feature_root,
            bindings=bindings,
            legacy_cache_dir=legacy_cache_dir,
            encoder_receipt_sha256=str(promotion["runtime_receipt_sha256"]),
            decoder_gguf_sha256=str(promotion["packets"][0]["decoder_gguf_sha256"]),
            mmproj_sha256=str(promotion["packets"][0]["mmproj_sha256"]),
            expected_n_embd=EXPECTED_N_EMBD,
            causal_attention=True,
            workers=workers,
        )
        registered = {entry["packet_id"]: entry["packet_sha256"] for entry in promotion["packets"]}
        for packet in packets:
            if registered.get(packet.packet_id) != packet.packet_sha256:
                raise FlightRuntimeError(
                    "packet %s does not match the registered promotion receipt"
                    % packet.packet_id
                )
        packet_promoter.bindings = {
            packet.packet_id.replace("/", ":"): {
                "packet_id": packet.packet_id,
                "sha256": packet.packet_sha256,
            }
            for packet in packets
        }
        packet_promoter.feature_root = feature_root
        return tuple(packet.packet_id for packet in packets), {
            "audio_path": "mmproj-free-speech-feature-packets",
            "packets_required": True,
            "feature_root": str(feature_root),
            "promotion_receipt": str(promotion_receipt),
            "promotion_receipt_sha256": sha256_file(promotion_receipt),
        }

    packet_promoter.bindings = {}
    packet_promoter.feature_root = None

    # ---- seam: client construction --------------------------------------
    def client_factory(**kwargs):
        if is_packet_arm:
            if not packet_promoter.bindings:
                raise FlightRuntimeError(
                    "packet cell reached run_phases with no promoted packet bindings"
                )
            kwargs["speech_feature_root"] = packet_promoter.feature_root
            kwargs["speech_packet_bindings"] = packet_promoter.bindings
        return FrozenCoreClient(**kwargs)

    # ---- seam: tool schemas ---------------------------------------------
    def tool_schema_resolver(lock_, data_root_, fill_name):
        return TOOL_SCHEMA_FILLS.resolve(fill_name)(lock_, data_root_)

    # ---- seam: the direct arm -------------------------------------------
    def rails_runner(**kwargs):
        if not is_packet_arm:
            return run_rails_experiment(**kwargs)
        # The packet audio path: rails.runner.run_rails_experiment always
        # calls core_client.complete() under the AUDIO invariant, so a
        # speech-feature arm can never travel through it (FrozenCoreClient
        # refuses: "speech-feature-query requires speech_feature_sample_id
        # and a query packet on every decision call"). This is the same one
        # contact per sample, with the one packet descriptor that arm's own
        # D2 field set requires -- no extra phase, no extra contact.
        plan = kwargs["plan"]
        adapter = kwargs["adapter"]
        core_client = kwargs["core_client"]
        decoding_params = kwargs.get("decoding_params")
        arms = tuple(kwargs.get("arms") or ("zero-supply",))
        if len(arms) != 1:
            raise FlightRuntimeError("a packet direct cell runs exactly one rails arm")
        results: list[ArmResult] = []
        for sample in adapter.load_split(kwargs["split_id"]):
            descriptor = packet_promoter.bindings[sample.sample_id]
            messages = (
                {"role": "system", "content": adapter.instruction(sample)},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_speech_features",
                            "speech_features": {
                                "packet_id": descriptor["packet_id"],
                                "sha256": descriptor["sha256"],
                                "role": "query",
                            },
                        }
                    ],
                },
            )
            response_text = core_client.complete(
                messages,
                decoding_params=decoding_params,
                speech_feature_sample_id=sample.sample_id,
                key_representation_id=str(values["speech_feature_key_representation_id"]),
                matcher_policy_id=str(values["speech_feature_matcher_policy_id"]),
            )
            results.append(
                ArmResult(
                    arm=arms[0],
                    sample_id=sample.sample_id,
                    messages=tuple(messages),
                    response_text=response_text,
                    metrics=adapter.score(sample, response_text),
                    consumption=adapter.extract_consumption(sample, None, response_text),
                )
            )
        return RunSummary(
            run_id=plan.run_id,
            protocol_hash=plan.protocol_hash,
            arms=arms,
            results=tuple(results),
            flight_lock=None,
        )

    # ---- seam: session start --------------------------------------------
    def session_starter(**kwargs):
        derived = list(kwargs.get("extra_argv") or ())
        if derived != ["-np", str(geometry["slots"]), "-c", str(
            int(geometry["slots"]) * int(geometry["slot_tokens"])
        )]:
            raise FlightRuntimeError(
                "FlightRuntime derived unexpected server argv %r from the adapter "
                "geometry" % (derived,)
            )
        # The fragment's own server_args are the authority: they already
        # carry the SAME -np/-c (asserted above, against the same geometry
        # object the adapter was built from) plus the flags FlightRuntime.
        # serve does not derive (-ngl, -fa, -ctk/-ctv, batch and cache
        # flags). Passing the derived pair alone would silently serve this
        # flight on CPU.
        kwargs["extra_argv"] = server_args
        kwargs.setdefault("ready_timeout_seconds", 1800.0)
        if is_packet_arm:
            kwargs["role"] = "inference"
        return start_session(**kwargs)

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
        packet_promoter=packet_promoter,
        client_factory=client_factory,
        tool_schema_resolver=tool_schema_resolver,
        rails_runner=rails_runner,
        session_starter=session_starter,
        lock=lock,
        campaign_active=campaign_active,
        host="127.0.0.1",
        port=int(str(values["base_url"]).rsplit(":", 1)[-1]),
        request_id_prefix="a2tcal",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--attempt-id", default=None)
    parser.add_argument("--campaign-active", action="store_true")
    parser.add_argument("--max-workers", type=int, default=4)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--run", action="store_true")
    args = parser.parse_args()

    cells = load_cells(args.experiment)
    if args.cell not in cells:
        raise SystemExit(
            "unknown cell %r; this experiment declares %s"
            % (args.cell, sorted(cells))
        )
    cell = cells[args.cell]
    experiment_document = json.loads(
        (REPO / "configs" / "experiment" / f"{args.experiment}.json").read_text(
            encoding="utf-8"
        )
    )
    run_id = args.run_id or str(experiment_document["experiment_id"])
    attempt_id = args.attempt_id or "attempt-%s-%s" % (
        datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        args.cell.replace("-", "").lower(),
    )

    runtime = build_runtime(
        cell=cell,
        dataset=args.dataset,
        experiment=args.experiment,
        run_id=run_id,
        attempt_id=attempt_id,
        campaign_active=bool(args.campaign_active),
    )

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
    runtime.preprocess()
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
