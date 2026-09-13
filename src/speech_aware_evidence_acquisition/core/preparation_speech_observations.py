"""Prepare source-bound local ASR evidence through shared registered custody."""

from __future__ import annotations

import ast
import hashlib
import importlib.metadata
import math
import time
from pathlib import Path
from typing import Mapping

from ..contracts import ExecutionPlan
from ..data.splits import prefixed, split_identity_hash as roster_identity
from ..rails.speech_observation import (
    ARTIFACT_KIND, CATALOG_SCHEMA, FINALIZATION_KIND, OUTPUT_SCHEMA,
    _artifact_inputs, _confined, _exact_mapping, _ledger_row, _pinned_file,
    _read_json, _sha, _text, load_speech_observation_catalog,
)
from .preparation import (
    PreparationError, digest, hash_stable_file, load_artifact,
    prepare_artifact, prepare_artifact_batch,
)
from .preparation_runtime import verify_pinned_file

SOURCE_SCHEMA = "saea-speech-observation-source-inventory-v1"
SOURCE_KIND = "speech-observation-sources"
PROTOCOL_SCHEMA = "saea-speech-observation-preparation-protocol-v1"
_SOURCE_FIELDS = {
    "packet_id", "packet_sha256", "source_audio_relpath",
    "source_audio_sha256", "source_audio_duration_seconds",
}


def _validate_bindings(bindings, carrier, split):
    if not isinstance(bindings, Mapping) or not bindings:
        raise PreparationError("speech source bindings must be a non-empty mapping")
    _text(carrier, "source carrier")
    _sha(split, "source split")
    checked = {}
    for sample_id, binding in sorted(bindings.items()):
        _text(sample_id, "source sample")
        _exact_mapping(binding, _SOURCE_FIELDS, "speech source binding")
        _text(binding["packet_id"], "packet ID")
        _sha(binding["packet_sha256"], "packet SHA")
        _sha(binding["source_audio_sha256"], "audio SHA")
        relative = binding["source_audio_relpath"]
        if (not isinstance(relative, str) or not relative or
                relative.startswith("/") or chr(92) in relative or ":" in relative or
                any(part in {"", ".", ".."} for part in relative.split("/"))):
            raise PreparationError("source audio address must be canonical and relative")
        seconds = binding["source_audio_duration_seconds"]
        if (isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or
                not math.isfinite(seconds) or not 0 < seconds <= 30):
            raise PreparationError("full short utterance duration must be within 30 seconds")
        checked[sample_id] = {**binding, "source_audio_duration_seconds": float(seconds)}
    if roster_identity(prefixed(carrier, tuple(checked))) != split:
        raise PreparationError("speech source roster differs from split identity")
    return checked


def export_speech_observation_sources(path, *, source_bindings, carrier_lock_key, split_identity_hash):
    """Export exact packet/source metadata without reading or decoding speech."""
    bindings = _validate_bindings(source_bindings, carrier_lock_key, split_identity_hash)
    inputs = {"carrier_lock_key": carrier_lock_key, "split_identity_hash": split_identity_hash,
              "source_bindings": bindings}
    output = {"schema": SOURCE_SCHEMA, **inputs}
    return prepare_artifact(Path(path), kind=SOURCE_KIND, inputs=inputs,
                            producer=lambda: output, contact_class="model-free")


def _load_sources(pin, data_root, plan):
    normalized, path = _pinned_file(data_root, pin, "speech source inventory")
    wrapper = _read_json(path, "speech source inventory")
    output = wrapper.get("output")
    _exact_mapping(output, {"schema", "carrier_lock_key", "split_identity_hash", "source_bindings"},
                   "speech source inventory output")
    if output["schema"] != SOURCE_SCHEMA or output["carrier_lock_key"] != plan.carrier_lock_key:
        raise PreparationError("speech source inventory carrier or schema differs")
    bindings = _validate_bindings(output["source_bindings"], plan.carrier_lock_key,
                                 plan.split_identity_hash)
    inputs = {"carrier_lock_key": plan.carrier_lock_key,
              "split_identity_hash": plan.split_identity_hash, "source_bindings": bindings}
    if output["split_identity_hash"] != plan.split_identity_hash:
        raise PreparationError("speech source inventory split differs")
    load_artifact(path, expected_sha256=normalized["sha256"], kind=SOURCE_KIND, inputs=inputs)
    if wrapper.get("contact_class") != "model-free":
        raise PreparationError("speech source inventory must be model-free")
    return bindings


def _pinned_whisper_version(source_path, bound):
    """Read a pinned literal version without importing or executing Whisper."""
    path = source_path / "whisper/version.py"
    raw = path.read_bytes()
    if len(raw) != bound["bytes"] or hashlib.sha256(raw).hexdigest() != bound["sha256"]:
        raise PreparationError("Whisper version source changed after source verification")
    try:
        module = ast.parse(raw.decode("utf-8"))
    except (SyntaxError, UnicodeError) as error:
        raise PreparationError("Whisper version source is not a literal assignment") from error
    if len(module.body) != 1:
        raise PreparationError("Whisper version source must contain one literal assignment")
    statement = module.body[0]
    if not (
        isinstance(statement, ast.Assign) and len(statement.targets) == 1
        and isinstance(statement.targets[0], ast.Name)
        and statement.targets[0].id == "__version__"
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str) and statement.value.value
    ):
        raise PreparationError("Whisper version source must assign a literal __version__")
    return statement.value.value


def verify_whisper_inventory(inventory):
    """Verify explicit installed-distribution or pinned-source package identity.

    Historical v1 inventories require distribution metadata. V2 explicitly
    identifies Whisper through its hash-bound source version; dependencies
    continue to require exact installed distribution versions. Never infer a
    fallback merely because installed metadata is missing.
    """
    source_version = (
        isinstance(inventory, Mapping)
        and inventory.get("schema") == "saea-local-whisper-runtime-inventory-v2"
    )
    fields = {"schema", "model", "checkpoint", "whisper_source_path", "source_files", "packages"}
    if source_version:
        fields.add("whisper_version_source")
    _exact_mapping(inventory, fields, "Whisper runtime inventory")
    if inventory["schema"] not in {
        "saea-local-whisper-runtime-inventory-v1", "saea-local-whisper-runtime-inventory-v2",
    } or inventory["model"] != "large-v3":
        raise PreparationError("Whisper runtime inventory identity differs")
    if source_version:
        version_source = _exact_mapping(
            inventory["whisper_version_source"], {"kind", "relpath"}, "Whisper version source",
        )
        if version_source != {
            "kind": "pinned-source-file", "relpath": "whisper/version.py",
        }:
            raise PreparationError("Whisper version source must name pinned whisper/version.py")
    checkpoint = _exact_mapping(inventory["checkpoint"], {"path", "bytes", "sha256"}, "Whisper checkpoint")
    checkpoint_path = Path(checkpoint["path"])
    source_path = Path(inventory["whisper_source_path"])
    if not checkpoint_path.is_absolute() or not source_path.is_absolute():
        raise PreparationError("Whisper checkpoint and source roots must be explicit local paths")
    verify_pinned_file(checkpoint_path, expected_size=checkpoint["bytes"],
                       expected_sha256=checkpoint["sha256"], label="Whisper checkpoint")
    files = inventory["source_files"]
    required = {"whisper/__init__.py", "whisper/audio.py", "whisper/decoding.py",
                "whisper/model.py", "whisper/tokenizer.py", "whisper/assets/mel_filters.npz",
                "whisper/assets/multilingual.tiktoken"}
    if source_version:
        required.add("whisper/version.py")
    if not isinstance(files, Mapping) or not required <= set(files):
        raise PreparationError("Whisper inventory omits required source or tokenizer assets")
    for relative, bound in files.items():
        _exact_mapping(bound, {"bytes", "sha256"}, "Whisper source file")
        _, path = _confined(source_path, relative, "Whisper source file")
        verify_pinned_file(path, expected_size=bound["bytes"], expected_sha256=bound["sha256"],
                           label="Whisper source file")
    packages = inventory["packages"]
    if not isinstance(packages, Mapping) or not {"openai-whisper", "torch", "numpy", "tiktoken"} <= set(packages):
        raise PreparationError("Whisper runtime package versions are incomplete")
    for name, version in packages.items():
        actual = (
            _pinned_whisper_version(source_path, files["whisper/version.py"])
            if source_version and name == "openai-whisper"
            else importlib.metadata.version(name)
        )
        if actual != version:
            raise PreparationError(f"Whisper runtime package version changed: {name}")
    return {"schema": "saea-local-whisper-backend-inventory-v1", "model": "large-v3",
            "checkpoint_path": str(checkpoint_path), "checkpoint_sha256": checkpoint["sha256"],
            "whisper_source_path": str(source_path)}


def _audio_sources(bindings, data_root):
    import soundfile

    sources = []
    for binding in bindings.values():
        _, path = _confined(data_root, binding["source_audio_relpath"], "ASR original audio")
        _size, sha, fingerprint = hash_stable_file(path, "ASR original audio")
        if sha != binding["source_audio_sha256"]:
            raise PreparationError("ASR source bytes changed")
        info = soundfile.info(path)
        duration = info.frames / info.samplerate
        if not math.isclose(duration, binding["source_audio_duration_seconds"], rel_tol=0, abs_tol=1e-6):
            raise PreparationError("ASR source duration differs from its bound full utterance")
        after = path.stat()
        if (after.st_ino, after.st_size, after.st_mtime_ns) != fingerprint:
            raise PreparationError("ASR source changed while checking its header")
        sources.append({"media_path": str(path), "audio_sha256": sha,
            "verified_fingerprint": fingerprint, "source_frames": info.frames,
            "source_sample_rate_hz": info.samplerate, "start_frame": 0, "end_frame": info.frames})
    return sources


def _validate_outputs(outputs):
    for value in outputs:
        _exact_mapping(value, {"schema", "status", "transcript", "diagnostics"}, "ASR output")
        if value["schema"] != OUTPUT_SCHEMA or value["status"] not in {"ok", "empty", "timeout", "unsupported"}:
            raise PreparationError("ASR output schema or status is invalid")
        if not isinstance(value["transcript"], str) or not isinstance(value["diagnostics"], Mapping):
            raise PreparationError("ASR output transcript or diagnostics is invalid")
        if value["status"] == "ok" and not value["transcript"].strip():
            raise PreparationError("usable ASR output must contain a transcript")
        if value["status"] != "ok" and value["transcript"]:
            raise PreparationError("unusable ASR output must not supply a transcript")
    return outputs


def run_speech_observation_preparation(config, *, source_root, data_root, backend_factory=None):
    """Reuse the common preparation executor; never acquire outside its registered lease."""
    from . import speech_preparation_runtime as shared
    from .speech_observation_backend import LocalWhisperBackend, _validate_protocol

    source_root, data_root = Path(source_root), Path(data_root)
    plan = ExecutionPlan(**config["plan"]).validate()
    plan_pin, plan_path = _pinned_file(source_root, config["execution_plan"], "ASR execution plan")
    envelope = _read_json(plan_path, "ASR execution plan")
    if ExecutionPlan(**envelope["execution_plan"]).validate() != plan:
        raise PreparationError("ASR execution plan envelope differs from configured plan")
    ledger_pin = _ledger_row(source_root, config["ledger_row"], plan)
    protocol = shared.pinned_json(config["protocol"])
    _exact_mapping(protocol, {"schema", "sources", "checkpoint_receipt", "decoding",
                             "monitor_interval_seconds", "catalog_id", "output_relpath",
                             "artifacts_relpath"}, "ASR preparation protocol")
    if protocol["schema"] != PROTOCOL_SCHEMA or plan.protocol_hash != config["protocol"]["sha256"]:
        raise PreparationError("ASR preparation protocol identity differs")
    _validate_protocol(protocol["decoding"])
    if protocol["monitor_interval_seconds"] != 10:
        raise PreparationError("ASR preparation monitor interval must be ten seconds")
    bindings = _load_sources(protocol["sources"], data_root, plan)
    seconds = sum(row["source_audio_duration_seconds"] for row in bindings.values())
    if len(bindings) > plan.planned_model_calls or seconds > plan.planned_speech_audio_seconds:
        raise PreparationError("ASR complete roster exceeds registered budget")
    checkpoint_pin, checkpoint_path = _pinned_file(
        source_root, protocol["checkpoint_receipt"], "ASR checkpoint receipt")
    inventory = _read_json(checkpoint_path, "ASR checkpoint receipt")
    output_relpath, output_path = _confined(data_root, protocol["output_relpath"], "ASR catalog")
    artifacts_relpath, _ = _confined(data_root, protocol["artifacts_relpath"], "ASR artifacts")
    prefix = f"prepared/{plan.run_id}/{plan.attempt_id}/"
    if not output_relpath.startswith(prefix) or not artifacts_relpath.startswith(prefix):
        raise PreparationError("ASR outputs must be namespaced to the registered attempt")
    catalog = {
        "schema": CATALOG_SCHEMA, "catalog_id": _text(protocol["catalog_id"], "catalog ID"),
        "use_split_identity_hash": plan.split_identity_hash,
        "checkpoint_receipt": checkpoint_pin, "decoding_config_sha256": digest(protocol["decoding"]),
        "producer": {"run_id": plan.run_id, "attempt_id": plan.attempt_id,
            "execution_plan": plan_pin, "protocol_sha256": plan.protocol_hash,
            "ledger_row": ledger_pin, "contacts": {"calls": len(bindings), "audio_seconds": seconds}},
        "observations": [],
    }
    if output_path.exists():
        sha = hashlib.sha256(output_path.read_bytes()).hexdigest()
        loaded = load_speech_observation_catalog(
            {"prepared_speech_observations": {"relpath": output_relpath, "sha256": sha}},
            data_root=data_root, source_audio_bindings=bindings,
            split_identity_hash=plan.split_identity_hash, repo_root=source_root)
        prior = _read_json(output_path, "ASR catalog")
        # The persisted attempt owns the charged floating-point total. Roster
        # metadata is validated separately; it must not replace that total on reuse.
        expected = {key: value for key, value in catalog.items() if key != "observations"}
        expected["producer"] = {**expected["producer"], "contacts": prior["producer"]["contacts"]}
        if (prior["producer"]["contacts"]["calls"] != len(bindings)
                or {key: value for key, value in prior.items() if key != "observations"} != expected):
            raise PreparationError("warm ASR catalog differs from registered producer configuration")
        return {**loaded.receipt(), "status": "SEALED", "cache": "warm", "new_neural_contacts": 0}
    canonical_ledger = source_root / "docs/exposure-ledger.md"
    if hashlib.sha256(canonical_ledger.read_bytes()).hexdigest() != ledger_pin["sha256"]:
        raise PreparationError("pinned ASR ledger differs from the canonical admission ledger")
    shared.admit(plan=plan, source_root=source_root,
        exposure_ledger=source_root / ledger_pin["relpath"],
        umbrella_lock=Path(config["umbrella_lock"]["path"]),
        umbrella_lock_sha256=config["umbrella_lock"]["sha256"],
        protocol_path=Path(config["protocol"]["path"]), protocol_sha256=plan.protocol_hash)
    backend_inventory = verify_whisper_inventory(inventory)
    sources = _audio_sources(bindings, data_root)
    measured_seconds = sum(source["source_frames"] / source["source_sample_rate_hz"] for source in sources)
    if not math.isclose(measured_seconds, seconds, rel_tol=0, abs_tol=1e-6):
        raise PreparationError("total source duration differs from the bound roster")
    rows = []
    for index, (sample_id, bound) in enumerate(bindings.items()):
        rows.append({"sample_id": sample_id,
            "speech_packet_id": bound["packet_id"], "speech_packet_sha256": bound["packet_sha256"],
            "source_audio_relpath": bound["source_audio_relpath"],
            "source_audio_sha256": bound["source_audio_sha256"],
            "source_audio_duration_seconds": bound["source_audio_duration_seconds"],
            "span": {"kind": "full-utterance", "start_seconds": 0.0,
                     "end_seconds": bound["source_audio_duration_seconds"]},
            "artifact_relpath": f"{artifacts_relpath}/{index:06d}.json",
            "artifact_sha256": "", "output_sha256": ""})
    selected_factory = backend_factory or (
        lambda inventory, protocol, root, event: LocalWhisperBackend(
            inventory, protocol["decoding"], root, event)
    )

    def prepare(backend, contact):
        backend.prepare_sources(sources)
        batch_size = protocol["decoding"]["batch_size"]
        for start in range(0, len(rows), batch_size):
            batch_rows, batch_sources = rows[start:start + batch_size], sources[start:start + batch_size]
            items = [{"path": data_root / row["artifact_relpath"],
                      "inputs": _artifact_inputs(row, catalog, catalog["producer"])}
                     for row in batch_rows]
            receipts = prepare_artifact_batch(items, kind=ARTIFACT_KIND,
                producer=lambda indices: _validate_outputs(contact(
                    [batch_sources[index] for index in indices], batch=True)),
                contact_class="speech-tool")
            for row, receipt in zip(batch_rows, receipts, strict=True):
                row["artifact_sha256"] = receipt["sha256"]
                artifact = _read_json(Path(receipt["path"]), "prepared ASR artifact")
                row["output_sha256"] = artifact["output_sha256"]
        return rows

    def finalize(prepared, state, _attempt_dir):
        if state["calls"] != len(rows) or not math.isclose(state["audio_seconds"], seconds, rel_tol=0, abs_tol=1e-6):
            raise PreparationError("ASR finalized catalog accounting differs from new contacts")
        catalog["observations"] = prepared
        catalog["producer"]["contacts"] = {"calls": state["calls"], "audio_seconds": state["audio_seconds"]}
        shared._exclusive_json(output_path, catalog)
        sha = hashlib.sha256(output_path.read_bytes()).hexdigest()
        result = {"schema": "saea-speech-observation-preparation-receipt-v1", "status": "SEALED",
            "run_id": plan.run_id, "attempt_id": plan.attempt_id, "protocol_sha256": plan.protocol_hash,
            "catalog_relpath": output_relpath, "catalog_sha256": sha,
            "logical_speech_tool_contacts": state["calls"], "actual_speech_audio_seconds": state["audio_seconds"],
            "elapsed_seconds": time.monotonic() - state["started_monotonic"],
            "closed_at": shared._now(), "study_head": config["study_head"],
            "batch_size": protocol["decoding"]["batch_size"], "source_inventory": protocol["sources"],
            "checkpoint_receipt": checkpoint_pin, "decoding_config_sha256": digest(protocol["decoding"])}
        return result, {"path": output_relpath, "sha256": sha, "kind": FINALIZATION_KIND}

    return shared._execute_preparation(
        config=config, plan=plan, protocol=protocol, data_root=data_root,
        encoder=backend_inventory, backend_factory=selected_factory, prepare=prepare,
        row_path=None, row_label="observation", contact_kind="speech",
        seconds_for_source=lambda source: (source["end_frame"] - source["start_frame"]) / source["source_sample_rate_hz"],
        facts_for_source=lambda source: {key: source[key] for key in ("audio_sha256", "start_frame", "end_frame")},
        source_bindings={"source_inventory_sha256": protocol["sources"]["sha256"]},
        finalize_prepared=finalize, contact_counter_field="logical_speech_tool_contacts",
        forward_phase="speech_tool_forward_started")
