#!/usr/bin/env python3
"""Contact-free wire check for the Earnings-21 OBS-E1b context-unit seam.

Exposure row `SAEA-E21-MF-OBS-E1B-SEAM-V1` (`model-free-check`). The OBS-E1
seam check (`scripts/e21_obs_e1_seam_wire_check.py`) recorded that the
speaker-turn cell composes and that its units tile; this one records the
successor facts for OBS-E1b -- that BOTH its cells compose, that the v3 plans
load and re-prove their own context invariants, that the cutter really cuts the
DELIVERED span, that the ownership stitch really decides what each unit
contributes, and that the turn-restricted concatenation still reproduces the
sealed audio byte for byte.

**Zero contacts of every kind.** No model, no server, no socket, no GPU, no
tokenizer, no network, no paid API, no forced aligner. Nothing here constructs
a transport, a gate, an attempt store or a `FrozenCoreAdapter`; the only
stand-in is a local scripted object that records the payload it is handed and
returns a fixed string, so the "contacts" this check reports are simulated by
construction and the real contact count is zero. No MP3 is decoded and no audio
is resampled, so the pinned absence of `ffmpeg` is preserved: the only audio
read is a local PCM read of the sealed 90-second obs-slices the comparator
itself wrote.

THE FIVE HALVES
---------------
**Composition.** `core.config.compose` over each cell's own four fragments,
then `ObsLoopConfig.from_values` through the REAL loader. Records the composed
`config_hash`, the `protocol_hash` against the frozen discovery split identity,
and the plan facts the loader proved -- including that the plan declares
context and that `has_context` is true.

**Coverage.** Every one of the 44 frozen discovery calls has a plan block, and
every block's `decoded_duration_seconds` equals the total of that call's own
SEALED 90-second window durations, at full scale and for free.

**Request half.** A contact-free four-call dry run through the REAL
`obs-agent-loop` policy, the REAL `SliceRegistry` derivation chain and the REAL
`TraceSink`. Each call's PCM is reconstructed from its own sealed window
slices, and every unit of every one of those calls is checked: the DELIVERED
span on the record, the tail riding on top exactly once, `pre_sha256` chaining
to the untailed cut, the unit's id / speaker / end cut / TURN bounds / context
margins in the OBS trace, the ownership fields and `obs_delivered_text` beside
them, and the payload's key set equal to `bare-core`'s D2-frozen field set and
nothing more.

**Falsifier.** For each dry-run call, cutting each delivered slice back to its
own TURN sub-range, dropping the 2.0-second tail, and concatenating those must
reproduce that call's COMMITTED `saea-diarization-v1` `audio_sha256`. This is
the OBS-E1 falsifier's successor and it is strictly stronger: it holds if and
only if the turns still tile AND the context bounds are exactly where the plan
says they are.

**Payload-binding stage.** The shared `rails.core_client.payload_binding_stage`
over each cell's own 44-row roster.

Usage (WSL2)::

    python scripts/e21_obs_e1b_seam_wire_check.py
    python scripts/e21_obs_e1b_seam_wire_check.py --out-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import statistics
import subprocess
import wave
from array import array
from pathlib import Path
from typing import Any, Mapping, NamedTuple

#: Resolved from the script's own location, so this check runs against
#: WHICHEVER checkout (or git worktree) it is invoked from.
REPO = Path(__file__).resolve().parents[1]

OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-08-e21-obs-e1b-seam"
)

EXPERIMENTS = ("e21-obs-e1b-context-units-v1", "e21-obs-e1b-uniform-twin-v1")
RUN_ID = "SAEA-E21-MF-OBS-E1B-SEAM-V1"
PREREGISTRATION = (
    "docs/readiness/2026-09-08-e21-obs-e1b-context-units-v1-preregistration.md"
)

FULL44_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)
TS2_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e21-buf90-tail2s-media/roster/flight-roster-receipt.json"
)
DIARIZATION_INPUTS = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-diarization-obs/inputs.json"
)
SPLITS = REPO / "docs/receipts/splits.json"

RATE = 16000
TAIL_SECONDS = 2.0

#: The four calls the dry run cuts, by the SAME rule the OBS-E1 seam check
#: fixed: the three shortest of the frozen 44 plus 4366522, the no-pause call
#: reported apart. Every window and every unit of each, never a sample.
DRY_RUN_EXTRA_CALL = "4366522"
DRY_RUN_SHORTEST = 3


class _RosterAudioRef(NamedTuple):
    path: str


class _RosterSample(NamedTuple):
    sample_id: str
    audio_ref: _RosterAudioRef
    audio_seconds: float


class _ContactFreeResponse:
    """Shaped exactly like ``core.model.CoreResponse`` in the attributes the
    policy reads, and nothing in it ever touched a socket."""

    def __init__(self, text: str, tag: str) -> None:
        self.text = text
        self.request_sha256 = hashlib.sha256(f"req-{tag}".encode()).hexdigest()
        self.response_sha256 = hashlib.sha256(f"resp-{tag}".encode()).hexdigest()
        self.response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.usage: dict[str, object] = {}


class _ContactFreeAdapter:
    """Records every payload the policy builds and answers locally.

    The answers are DELIBERATELY overlapping: request n returns a fixed
    vocabulary window, so consecutive units share three or more words exactly
    as a real context margin would make them, and the ownership stitch is
    exercised on its ``anchor`` branch rather than on its fallback.
    """

    _WORDS = [f"w{index:04d}" for index in range(4000)]

    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def request(self, payload):
        self.payloads.append(dict(payload))
        index = len(self.payloads)
        start = 6 * (index - 1)
        text = " ".join(self._WORDS[start : start + 9])
        return _ContactFreeResponse(text, tag=str(index))


def log(message: str) -> None:
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def git(*argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()


def read_wav_16k_mono(path: Path) -> array:
    with wave.open(str(path), "rb") as handle:
        if (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) != (
            RATE,
            1,
            2,
        ):
            raise SystemExit(f"{path} is not 16 kHz mono int16")
        return array("h", handle.readframes(handle.getnframes()))


def wav_bytes(samples: array) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(samples.tobytes())
    return buffer.getvalue()


def sealed_windows_by_call(ts2: Mapping[str, Any]) -> dict[str, list[dict]]:
    by_call: dict[str, list[dict]] = {}
    for row in ts2["items"]:
        by_call.setdefault(str(row["call_sample_id"]), []).append(dict(row))
    for rows in by_call.values():
        rows.sort(key=lambda row: int(row["obs_iteration"]))
    return by_call


def unit_statistics(plan) -> dict[str, Any]:
    turns = sorted(
        unit.end_seconds - unit.start_seconds
        for units in plan.units_by_sample.values()
        for unit in units
    )
    cuts = sorted(
        unit.cut_end_seconds - unit.cut_start_seconds
        for units in plan.units_by_sample.values()
        for unit in units
    )
    return {
        "calls": len(plan.units_by_sample),
        "units": len(cuts),
        "declares_context": plan.has_context,
        "turn_seconds_total": round(sum(turns), 6),
        "delivered_cut_seconds_total": round(sum(cuts), 6),
        "delivered_seconds_total": round(sum(cuts) + TAIL_SECONDS * len(cuts), 6),
        "context_seconds_total": round(sum(cuts) - sum(turns), 6),
        "delivered_cut_min": round(cuts[0], 6),
        "delivered_cut_median": round(statistics.median(cuts), 6),
        "delivered_cut_max": round(cuts[-1], 6),
        "delivered_cut_mean": round(statistics.fmean(cuts), 6),
        "units_without_context": sum(
            1
            for units in plan.units_by_sample.values()
            for unit in units
            if unit.cut_end_seconds - unit.cut_start_seconds
            <= unit.end_seconds - unit.start_seconds + 1e-9
        ),
    }


def main() -> int:  # noqa: PLR0915 (one linear check, read top to bottom)
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--experiment", action="append", default=None)
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help=(
            "TEST-ONLY. A wire check certifies a COMMITTED tree; without this it "
            "refuses a dirty one rather than recording a study_commit that "
            "describes different bytes than the ones it exercised"
        ),
    )
    args = parser.parse_args()
    experiments = tuple(args.experiment or EXPERIMENTS)

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if os.environ.get("CUDA_VISIBLE_DEVICES", "") != "":
        raise SystemExit("CUDA_VISIBLE_DEVICES must be empty for a contact-free check")
    if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
        raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

    import speech_aware_evidence_acquisition as _pkg

    if (
        Path(_pkg.__file__ or "")
        != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
    ):
        raise SystemExit(f"package resolves to {_pkg.__file__}, not this checkout")

    import speech_aware_evidence_acquisition.core  # noqa: F401 (registries)
    from speech_aware_evidence_acquisition.core.base import (
        SampleContext,
        declared_derived_media_roots,
    )
    from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
    from speech_aware_evidence_acquisition.core.model import SliceRegistry
    from speech_aware_evidence_acquisition.core.tracing import TraceSink
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.loader import SampleRef
    from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
    from speech_aware_evidence_acquisition.rails.core_client import payload_binding_stage
    from speech_aware_evidence_acquisition.reproduction.obs_audio import (
        SLICE_TAIL_SILENCE_TRANSFORM,
    )
    from speech_aware_evidence_acquisition.reproduction.obs_loop import (
        OBS_UNIT_PLAN_BOUNDARY_MODE,
        OBS_UNIT_PLAN_SCHEMA_V3,
        ObsAgentLoopPolicy,
        ObsLoopConfig,
    )
    from speech_aware_evidence_acquisition.reproduction.obs_ownership import (
        OWNERSHIP_PROTOCOL,
        RULE_ANCHOR,
        RULE_NO_OVERLAP,
        RULE_PROPORTIONAL,
        RULE_SHORT_ANCHOR,
    )

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is dirty; a wire check certifies committed bytes:\n" + dirty
        )
    study_commit = git("rev-parse", "HEAD")
    log("%s tree at %s" % ("DIRTY (allowed)" if dirty else "clean", study_commit[:8]))

    failures: list[str] = []
    root = data_root()
    lock = load_lock(umbrella_lock_path())
    roster = load_json(FULL44_ROSTER)
    roster_ids = [str(call["sample_id"]) for call in roster["calls"]]
    ts2 = load_json(TS2_ROSTER)
    sealed_by_call = sealed_windows_by_call(ts2)
    diarization = {
        str(call["sample_id"]): dict(call)
        for call in load_json(DIARIZATION_INPUTS)["calls"]
    }
    by_seconds = sorted(roster["calls"], key=lambda call: float(call["audio_seconds"]))
    dry_run_ids = [str(call["sample_id"]) for call in by_seconds[:DRY_RUN_SHORTEST]]
    if DRY_RUN_EXTRA_CALL not in dry_run_ids:
        dry_run_ids.append(DRY_RUN_EXTRA_CALL)
    splits = load_json(SPLITS)

    scratch = root / "runs" / RUN_ID
    if scratch.name != RUN_ID or scratch.parent.name != "runs":  # pragma: no cover
        raise SystemExit(f"refusing to clear {scratch}")
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True, exist_ok=True)

    cells: list[dict[str, Any]] = []
    input_paths: set[Path] = {FULL44_ROSTER, TS2_ROSTER, DIARIZATION_INPUTS, SPLITS}

    for experiment in experiments:
        log(f"--- {experiment}")
        experiment_doc = load_json(REPO / "configs" / "experiment" / f"{experiment}.json")
        cell = dict(experiment_doc["cells"][0])
        composed = compose(
            REPO,
            str(cell["model_fragment"]),
            str(cell["dataset_fragment"]),
            str(cell["baseline_fragment"]),
            experiment,
        )
        values = composed.values
        split_block = splits["splits"][str(values["split_name"])]
        if str(split_block["carrier_lock_key"]) != str(values["carrier_lock_key"]):
            raise SystemExit(
                "the composed carrier %r is not the %r split's own %r"
                % (
                    values["carrier_lock_key"],
                    values["split_name"],
                    split_block["carrier_lock_key"],
                )
            )
        split_identity = str(split_block["identity_hash"])
        cell_protocol_hash = protocol_hash(
            composed.config_hash, str(values["arm"]), split_identity
        )
        cfg = ObsLoopConfig.from_values(values, REPO)
        if cfg.unit_plan is None:
            raise SystemExit(f"{experiment}: the composed config carries no unit plan")
        if cfg.unit_plan.schema != OBS_UNIT_PLAN_SCHEMA_V3 or not cfg.unit_plan.has_context:
            raise SystemExit(f"{experiment}: the plan does not declare context")
        plan_stats = unit_statistics(cfg.unit_plan)
        log(
            "  composed config_hash=%s protocol_hash=%s"
            % (composed.config_hash[:12], cell_protocol_hash[:12])
        )
        log(
            "  plan %s: %s units, %s delivered cut seconds (%s)"
            % (
                cfg.unit_plan.relpath.rsplit("/", 1)[-1],
                plan_stats["units"],
                plan_stats["delivered_cut_seconds_total"],
                cfg.unit_plan.sha256[:12],
            )
        )

        uncovered = [
            sample_id
            for sample_id in roster_ids
            if sample_id not in cfg.unit_plan.units_by_sample
        ]
        if uncovered:
            failures.append(f"{experiment}: the plan covers no units for {uncovered}")
        duration_mismatch = []
        for sample_id in roster_ids:
            sealed_seconds = round(
                sum(
                    float(row["source_audio_seconds"])
                    for row in sealed_by_call[sample_id]
                ),
                6,
            )
            declared = cfg.unit_plan.duration_by_sample.get(sample_id)
            if declared is None or abs(declared - sealed_seconds) > 1e-6:
                duration_mismatch.append(
                    {
                        "sample_id": sample_id,
                        "plan_seconds": declared,
                        "sealed_window_seconds": sealed_seconds,
                    }
                )
        if duration_mismatch:
            failures.append(
                f"{experiment}: plan durations disagree with the sealed window totals "
                f"for {len(duration_mismatch)} call(s)"
            )

        expected_fields = set(ARM_VISIBLE_FIELDS[str(values["arm"])])
        per_call: list[dict[str, Any]] = []
        rule_totals: dict[str, int] = {}
        for sample_id in dry_run_ids:
            sealed = sealed_by_call[sample_id]
            pcm = array("h")
            for row in sealed:
                pcm.extend(read_wav_16k_mono(root / str(row["source_media_relpath"])))
            duration = len(pcm) / RATE
            planned = cfg.unit_plan.units_for(sample_id, duration)

            call_root = scratch / experiment / sample_id
            data_dir = call_root / "data"
            run_dir = call_root / "run"
            parent_relpath = str(
                next(c for c in roster["calls"] if str(c["sample_id"]) == sample_id)[
                    "media_relpath"
                ]
            )
            (data_dir / parent_relpath).parent.mkdir(parents=True, exist_ok=True)
            (data_dir / parent_relpath).write_bytes(
                b"contact-free-dry-run-" + sample_id.encode()
            )
            registry = SliceRegistry(
                data_root=data_dir,
                run_id=RUN_ID,
                parent_facts={sample_id: (parent_relpath, duration)},
            )
            adapter = _ContactFreeAdapter()
            sink = TraceSink(run_dir, RUN_ID)
            from speech_aware_evidence_acquisition.reproduction import obs_loop as _obs

            original_decode = _obs.decode_parent_pcm
            _obs.decode_parent_pcm = lambda path, rate=RATE, _pcm=pcm: _pcm
            try:
                outcome = ObsAgentLoopPolicy().run_sample(
                    SampleContext(
                        sample=SampleRef(
                            carrier_lock_key=str(values["carrier_lock_key"]),
                            sample_id=sample_id,
                            media_relpath=parent_relpath,
                            audio_seconds=duration,
                            sample_rate_hz=RATE,
                        ),
                        evidence=[],
                        adapter=adapter,
                        sink=sink,
                        arm=str(values["arm"]),
                        task_instruction=str(values["task_instruction"]),
                        decoding_params=dict(values["decoding_params"]),
                        request_id_base=f"{RUN_ID}-{sample_id}",
                        extras={
                            "slice_registry": registry,
                            "data_root": data_dir,
                            "run_dir": run_dir,
                            "repo_root": REPO,
                            "config_values": values,
                        },
                    )
                )
            finally:
                _obs.decode_parent_pcm = original_decode

            trace = {
                document["record_id"]: document["payload"]
                for document in (
                    json.loads(line)
                    for line in (run_dir / f"{RUN_ID}.trace.jsonl")
                    .read_text(encoding="utf-8")
                    .splitlines()
                    if line
                )
                if document["record_id"].endswith("/obs")
            }
            call_failures: list[str] = []
            if len(adapter.payloads) != len(planned):
                call_failures.append(
                    f"{len(adapter.payloads)} contact(s) for {len(planned)} planned units"
                )
            rebuilt = array("h")
            tail_samples = int(TAIL_SECONDS * RATE)
            delivered_texts: list[str] = []
            call_rules: dict[str, int] = {}
            for index, (unit, payload) in enumerate(zip(planned, adapter.payloads)):
                record = registry.lookup(sample_id, str(payload["media_relpath"]))
                delivered = (data_dir / record.media_relpath).read_bytes()
                untailed = array("h", delivered[44:])[:-tail_samples]
                obs = trace.get(f"{RUN_ID}-{sample_id}-i{index:04d}/obs", {})
                if set(payload) != expected_fields:
                    call_failures.append(
                        f"unit {unit.unit_id} payload key set {sorted(set(payload))}"
                    )
                # The record's span is the DELIVERED cut, and audio_seconds
                # still equals it -- the rail that refuses a moved cut.
                if abs(record.start_seconds - unit.cut_start_seconds) > 1e-6:
                    call_failures.append(f"unit {unit.unit_id} cut start {record.start_seconds}")
                if abs(record.end_seconds - unit.cut_end_seconds) > 1e-6:
                    call_failures.append(f"unit {unit.unit_id} cut end {record.end_seconds}")
                if abs(record.audio_seconds - (record.end_seconds - record.start_seconds)) > 1e-9:
                    call_failures.append(f"unit {unit.unit_id} audio_seconds moved")
                if record.iteration != unit.unit_index - 1:
                    call_failures.append(f"unit {unit.unit_id} iteration {record.iteration}")
                if record.preprocess != (f"{SLICE_TAIL_SILENCE_TRANSFORM}-2s",):
                    call_failures.append(f"unit {unit.unit_id} preprocess {record.preprocess}")
                if record.pre_sha256 != hashlib.sha256(wav_bytes(untailed)).hexdigest():
                    call_failures.append(f"unit {unit.unit_id} pre_sha256 does not chain")
                if len(delivered) != 44 + 2 * (len(untailed) + tail_samples):
                    call_failures.append(f"unit {unit.unit_id} delivered byte count")
                if obs.get("obs_unit_id") != unit.unit_id:
                    call_failures.append(f"unit {unit.unit_id} trace id {obs.get('obs_unit_id')}")
                if obs.get("obs_unit_speaker") != unit.speaker:
                    call_failures.append(f"unit {unit.unit_id} trace speaker")
                if obs.get("obs_unit_end_cut") != unit.end_cut:
                    call_failures.append(f"unit {unit.unit_id} trace end cut")
                if abs(float(obs.get("obs_unit_turn_start_seconds", -1)) - unit.start_seconds) > 1e-6:
                    call_failures.append(f"unit {unit.unit_id} trace turn start")
                if abs(float(obs.get("obs_unit_turn_end_seconds", -1)) - unit.end_seconds) > 1e-6:
                    call_failures.append(f"unit {unit.unit_id} trace turn end")
                if obs.get("obs_ownership_protocol") != OWNERSHIP_PROTOCOL:
                    call_failures.append(f"unit {unit.unit_id} trace ownership protocol")
                if "obs_delivered_text" not in obs:
                    call_failures.append(f"unit {unit.unit_id} declares no delivered text")
                keep_from = int(obs.get("obs_ownership_keep_from", -1))
                keep_to = int(obs.get("obs_ownership_keep_to", -1))
                if not 0 <= keep_from <= keep_to:
                    call_failures.append(f"unit {unit.unit_id} ownership range")
                if bool(obs.get("obs_final_window")) != (index == len(planned) - 1):
                    call_failures.append(f"unit {unit.unit_id} final flag")
                rule = str(obs.get("obs_ownership_right_rule", ""))
                if index < len(planned) - 1:
                    call_rules[rule] = call_rules.get(rule, 0) + 1
                    rule_totals[rule] = rule_totals.get(rule, 0) + 1
                delivered_texts.append(str(obs.get("obs_delivered_text", "")))
                # THE FALSIFIER, per unit: the TURN's own samples, taken out of
                # the delivered cut at the offset the plan declares.
                turn_start = int(round(unit.start_seconds * RATE)) - int(
                    round(unit.cut_start_seconds * RATE)
                )
                turn_end = turn_start + (
                    int(round(unit.end_seconds * RATE))
                    - int(round(unit.start_seconds * RATE))
                )
                if turn_start < 0 or turn_end > len(untailed):
                    call_failures.append(f"unit {unit.unit_id} turn falls outside its cut")
                else:
                    rebuilt.extend(untailed[turn_start:turn_end])

            stitched = " ".join(piece for piece in delivered_texts if piece)
            if stitched != outcome.text:
                call_failures.append(
                    "the OBS records' delivered texts do not rebuild the outcome"
                )
            sealed_sha256 = str(diarization[sample_id]["audio_sha256"])
            rebuilt_sha256 = hashlib.sha256(wav_bytes(rebuilt)).hexdigest()
            if rebuilt_sha256 != sealed_sha256:
                call_failures.append(
                    "the turn-restricted concatenation does not reproduce the sealed "
                    f"audio_sha256 ({rebuilt_sha256} vs {sealed_sha256})"
                )
            derivation = load_json(run_dir / f"{RUN_ID}.obs-derivation.{sample_id}.json")
            if derivation["boundary_mode"] != OBS_UNIT_PLAN_BOUNDARY_MODE:
                call_failures.append(f"derivation boundary_mode {derivation['boundary_mode']}")
            if derivation["unit_plan_sha256"] != cfg.unit_plan.sha256:
                call_failures.append("derivation does not name the pinned plan")
            if derivation["text_ownership"] != OWNERSHIP_PROTOCOL:
                call_failures.append("derivation does not name the ownership protocol")

            per_call.append(
                {
                    "sample_id": sample_id,
                    "sealed_windows": len(sealed),
                    "planned_units": len(planned),
                    "contacts_simulated": len(adapter.payloads),
                    "decoded_duration_seconds": round(duration, 6),
                    "turn_seconds": round(
                        sum(unit.end_seconds - unit.start_seconds for unit in planned), 6
                    ),
                    "delivered_cut_seconds": round(
                        sum(
                            unit.cut_end_seconds - unit.cut_start_seconds
                            for unit in planned
                        ),
                        6,
                    ),
                    "delivered_seconds": round(
                        sum(
                            unit.cut_end_seconds - unit.cut_start_seconds
                            for unit in planned
                        )
                        + TAIL_SECONDS * len(planned),
                        6,
                    ),
                    "delivered_cut_min": round(
                        min(
                            unit.cut_end_seconds - unit.cut_start_seconds
                            for unit in planned
                        ),
                        6,
                    ),
                    "delivered_cut_max": round(
                        max(
                            unit.cut_end_seconds - unit.cut_start_seconds
                            for unit in planned
                        ),
                        6,
                    ),
                    "boundary_rules": dict(sorted(call_rules.items())),
                    "first_unit": planned[0].unit_id,
                    "last_unit": planned[-1].unit_id,
                    "sealed_audio_sha256": sealed_sha256,
                    "rebuilt_audio_sha256": rebuilt_sha256,
                    "falsifier": "PASS" if rebuilt_sha256 == sealed_sha256 else "FAIL",
                    "stitched_response_sha256": outcome.response_sha256,
                    "payload_field_set": sorted(expected_fields),
                    "failures": call_failures,
                }
            )
            failures.extend(f"{experiment}/{sample_id}: {m}" for m in call_failures)
            log(
                "  dry run %s: %d units from %d sealed windows, rules %s, falsifier %s"
                % (
                    sample_id,
                    len(planned),
                    len(sealed),
                    dict(sorted(call_rules.items())),
                    "PASS" if rebuilt_sha256 == sealed_sha256 else "FAIL",
                )
            )

        by_id = {str(call["sample_id"]): call for call in roster["calls"]}
        binding_samples = tuple(
            _RosterSample(
                sample_id=sample_id,
                audio_ref=_RosterAudioRef(path=str(by_id[sample_id]["media_relpath"])),
                audio_seconds=float(by_id[sample_id]["audio_seconds"]),
            )
            for sample_id in roster_ids
        )
        binding_stage = payload_binding_stage(
            dataset_fragment=str(cell["dataset_fragment"]),
            carrier_lock_key=str(values["carrier_lock_key"]),
            samples=binding_samples,
            data_root=root,
            carrier_root=asset_dir(lock, str(values["carrier_lock_key"]), root),
            derived_media_roots=declared_derived_media_roots(values, root),
        )
        if not binding_stage.bound:
            failures.append(
                f"{experiment}: payload-binding stage did not bind: "
                f"{binding_stage.failures!r}"
            )
        log(
            "  payload-binding stage: %s (%d/%d rows checked)"
            % (
                "PASS" if binding_stage.bound else "FAIL",
                len(binding_stage.rows_checked),
                binding_stage.rows_total,
            )
        )

        input_paths.update(
            {
                REPO / cfg.unit_plan.relpath,
                REPO / "configs/experiment" / f"{experiment}.json",
                REPO / "configs/baseline" / f"{cell['baseline_fragment']}.json",
                REPO / "configs/dataset" / f"{cell['dataset_fragment']}.json",
                REPO / "configs/model" / f"{cell['model_fragment']}.json",
            }
        )
        cells.append(
            {
                "experiment": experiment,
                "cell_id": str(cell["cell_id"]),
                "fragments": composed.fragments,
                "config_hash": composed.config_hash,
                "protocol_hash": cell_protocol_hash,
                "arm": str(values["arm"]),
                "policy": str(values["policy"]),
                "evidence_source": str(values["evidence_source"]),
                "split_name": str(values["split_name"]),
                "split_identity_hash": split_identity,
                "task_instruction_sha256": hashlib.sha256(
                    str(values["task_instruction"]).encode("utf-8")
                ).hexdigest(),
                "obs_keys": {
                    key: values[key]
                    for key in sorted(values)
                    if isinstance(key, str) and key.startswith("obs_")
                },
                "unit_plan": {
                    "relpath": cfg.unit_plan.relpath,
                    "sha256": cfg.unit_plan.sha256,
                    "schema": cfg.unit_plan.schema,
                    "pin_matches_fragment": cfg.unit_plan.sha256
                    == str(values["obs_unit_plan_sha256"]),
                    **plan_stats,
                    "proved_by": (
                        "analysis.e21_speaker_turn_units.assert_tiles AND assert_context, "
                        "re-run by the loader on the bytes it actually read, per call"
                    ),
                },
                "coverage": {
                    "roster_calls": len(roster_ids),
                    "calls_without_units": uncovered,
                    "duration_mismatches": duration_mismatch,
                },
                "dry_run": {
                    "rule": (
                        "the three shortest calls of the frozen 44 plus 4366522, the "
                        "no-pause call; every window and every unit of each"
                    ),
                    "calls": per_call,
                    "units_total": sum(row["planned_units"] for row in per_call),
                    "contacts_simulated_total": sum(
                        row["contacts_simulated"] for row in per_call
                    ),
                    "boundary_rules_total": dict(sorted(rule_totals.items())),
                    "falsifier": (
                        "cutting each delivered slice back to its own TURN sub-range, "
                        "dropping the 2.0-second tail and concatenating those "
                        "reproduces the call's committed saea-diarization-v1 "
                        "audio_sha256 -- which holds only if the turns tile AND the "
                        "context bounds are exactly where the plan says"
                    ),
                    "falsifier_result": (
                        "PASS" if all(r["falsifier"] == "PASS" for r in per_call) else "FAIL"
                    ),
                },
                "payload_binding_stage": binding_stage.as_receipt(),
            }
        )

    receipt = {
        "schema": "saea-e21-obs-e1b-seam-wire-check-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "execution_profile": "model-free-check",
        "exposure_row": RUN_ID,
        "preregistration": PREREGISTRATION,
        "study_commit": study_commit,
        "result": "PASS" if not failures else "FAIL",
        "failures": failures,
        "ownership_protocol": OWNERSHIP_PROTOCOL,
        "ownership_rules": sorted(
            {RULE_ANCHOR, RULE_SHORT_ANCHOR, RULE_PROPORTIONAL, RULE_NO_OVERLAP}
        ),
        "zero_contact": (
            "No frozen core, server, socket, GPU, tokenizer, embedder, network, paid "
            "API or forced aligner. Nothing here constructs a transport, gate, attempt "
            "store or FrozenCoreAdapter; the policy's adapter is a local scripted "
            "object that records payloads and returns a fixed overlapping vocabulary, "
            "so every 'contact' reported is simulated by construction. No MP3 decode "
            "and no resample, so the pinned absence of ffmpeg is preserved: the only "
            "audio read is a local PCM read of the sealed obs-slices the comparator "
            "itself wrote."
        ),
        "model_contacts": 0,
        "sockets_opened": 0,
        "cells": cells,
        "inputs": {
            str(path.relative_to(REPO)).replace("\\", "/"): sha256_file(path)
            for path in sorted(input_paths)
        },
        "not_authorized": (
            "This receipt records two compositions and a contact-free dry run. It is "
            "not an authorization: OBS-E1b needs its own exposure row and the owner's "
            "GO, and this check registers neither. OBS-E1 remains REJECTED."
        ),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    document = out_dir / "wire-check.json"
    document.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    manifest = out_dir / "MANIFEST.sha256"
    manifest.write_text(
        "".join(
            f"{sha256_file(path)}  {path.name}\n"
            for path in sorted(out_dir.iterdir())
            if path.name != "MANIFEST.sha256"
        ),
        encoding="utf-8",
        newline="\n",
    )
    log(f"wrote {document} ({receipt['result']})")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
