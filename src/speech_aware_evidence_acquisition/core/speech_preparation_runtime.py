"""Run configured frozen speech-query preparation under shared custody."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from ..contracts import ExecutionPlan
from .attempts import AttemptStore
from .data_root_placeholder import expand_data_root
from .flight.lease import GenerationLease
from .preparation import canonical_bytes, hash_stable_file
from .preparation_runtime import verify_pinned_file
from .preparation_speech_queries import (
    prepare_speech_query_vectors,
    prepare_text_facet_vectors,
    segment_plan,
)
from .speech_embedding import encode, load_stack, read_audio_span, render


class SpeechPreparationError(RuntimeError):
    """Refuse a drifting or unregistered preparation."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def pinned_json(binding):
    binding = expand_data_root(binding)
    path = Path(binding["path"])
    _size, sha, fingerprint = hash_stable_file(path, "preparation binding")
    if sha != binding["sha256"]:
        raise SpeechPreparationError("preparation binding hash changed")
    value = json.loads(path.read_bytes())
    stat = path.stat()
    if (stat.st_ino, stat.st_size, stat.st_mtime_ns) != fingerprint:
        raise SpeechPreparationError("preparation binding changed during read")
    return expand_data_root(value)


def confined(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise SpeechPreparationError("artifact path must be relative")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or ".." in Path(relative).parts:
        raise SpeechPreparationError("artifact path escapes data root")
    return path


def _exclusive_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_bytes(document) + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


def admit(**kwargs):
    from ..contracts.tool_plan import assert_registered_tool_plan

    return assert_registered_tool_plan(**kwargs)


def verify_encoder(inventory, data_root):
    """Verify all recorded model files and package versions before loading."""
    if inventory.get("schema") != "saea-pinned-speech-query-encoder-inventory-v1":
        raise SpeechPreparationError("encoder inventory schema is invalid")
    directory = confined(data_root, inventory["model_dir_relpath"])
    files = inventory["files"]
    required = {
        "config.json",
        "config_sentence_transformers.json",
        "preprocessor_config.json",
        "modeling_nv_omni_embed.py",
        "tokenizer.json",
        "tokenizer_config.json",
        "model.safetensors.index.json",
        "1_Pooling/config.json",
        "additional_chat_templates/sentence_transformers.jinja",
    }
    if not required <= set(files):
        raise SpeechPreparationError("encoder inventory omits required runtime files")
    for name, entry in files.items():
        verify_pinned_file(
            confined(directory, name),
            expected_size=entry["bytes"],
            expected_sha256=entry["sha256"],
            label="frozen speech encoder",
        )
    index = json.loads((directory / "model.safetensors.index.json").read_bytes())
    if not set(index["weight_map"].values()) <= set(files):
        raise SpeechPreparationError("encoder inventory omits weight shards")
    for name, version in inventory["packages"].items():
        if importlib.metadata.version(name) != version:
            raise SpeechPreparationError(f"encoder package version changed: {name}")


def _source_key(source):
    return (source["audio_sha256"], source["start_frame"], source["end_frame"])


class BoundedAudioPrefetch:
    """Overlap bounded CPU decode/resample with one GPU encoder request."""

    def __init__(self, workers, reader=read_audio_span):
        if type(workers) is not int or not 1 <= workers <= 8:
            raise SpeechPreparationError("active preparation CPU workers must be 1..8")
        self.workers, self.reader = workers, reader
        self.pool = None
        self.pending = deque()
        self.sources = iter(())

    @property
    def pending_count(self):
        return len(self.pending)

    def prepare_sources(self, sources):
        self.pool = ThreadPoolExecutor(max_workers=self.workers)
        self.sources = iter(sources)
        for _ in range(self.workers):
            self._advance()

    def _advance(self):
        source = next(self.sources, None)
        if source is not None:
            self.pending.append(
                (_source_key(source), self.pool.submit(self.reader, source))
            )

    def take(self, source):
        key = _source_key(source)
        # Cached spans skip the encoder; discard their prefetched CPU results.
        while self.pending:
            found, future = self.pending.popleft()
            self._advance()
            if found == key:
                return future.result()
            future.result()
        raise SpeechPreparationError(
            "prefetch does not contain the requested source span"
        )

    def close(self):
        if self.pool is not None:
            self.pool.shutdown(wait=True, cancel_futures=True)


class NemotronSpeechEncoder:
    """Lazy-load the pinned tool once, preserving the historical pooling recipe."""

    def __init__(self, inventory, protocol, data_root, event):
        self.inventory, self.protocol, self.data_root = inventory, protocol, data_root
        self.event, self.stack = event, None
        self.prefetch = BoundedAudioPrefetch(protocol["cpu_workers"])

    def prepare_sources(self, sources):
        self.prefetch.prepare_sources(sources)

    def __call__(self, source):
        if self.stack is None:
            self.event("model_load_started")
            self.stack = load_stack(
                confined(self.data_root, self.inventory["model_dir_relpath"]),
                local_files_only=True,
            )
            self.event("model_load_finished")
        processor, model, template = self.stack
        self.event("data_wait_started")
        wave = self.prefetch.take(source)
        self.event("data_wait_finished")
        text = render(
            processor,
            template,
            [
                {"type": "text", "text": self.protocol["query_prompt"]},
                {"type": "audio"},
            ],
        )
        self.event("processor_started")
        result = encode(
            processor,
            model,
            [text],
            [wave],
            max_audio_samples=self.protocol["max_audio_samples"],
            require_complete_audio=True,
            max_sequence_tokens=self.protocol["max_sequence_tokens"],
            forward_event=self.event,
        )
        return result[0]

    def close(self):
        self.prefetch.close()
        self.stack = None


class NemotronPassageEncoder:
    """The same pinned stack for batch-one native-card passage keys."""

    def __init__(self, inventory, protocol, data_root, event):
        self.inventory, self.protocol, self.data_root, self.event = (
            inventory,
            protocol,
            data_root,
            event,
        )
        self.stack = None

    def __call__(self, text):
        if self.stack is None:
            self.event("model_load_started")
            self.stack = load_stack(
                confined(self.data_root, self.inventory["model_dir_relpath"]),
                local_files_only=True,
            )
            self.event("model_load_finished")
        processor, model, template = self.stack
        self.event("processor_started")
        rendered = render(
            processor,
            template,
            [{"type": "text", "text": self.protocol["passage_prompt"] + text}],
        )
        return encode(
            processor,
            model,
            [rendered],
            None,
            max_sequence_tokens=self.protocol["max_sequence_tokens"],
            forward_event=self.event,
        )[0]

    def close(self):
        self.stack = None


def start_monitor(path, state, interval):
    """Use shared read-only telemetry; local encoder has one occupied slot."""
    from .session.serving import read_host_memory
    from .session.telemetry import read_gpu

    stopped = threading.Event()

    def work():
        with path.open("x", encoding="utf-8") as handle:
            while not stopped.is_set():
                sample = {
                    "timestamp": _now(),
                    "gpu": read_gpu(),
                    "host_memory": read_host_memory(),
                    "elapsed_seconds": time.monotonic() - state["started_monotonic"],
                    state.get("contact_counter_field", "logical_encoder_contacts"): state["calls"],
                    "phase": state["phase"],
                    "busy_slots": int(state["phase"] == state.get("forward_phase", "encoder_forward_started")),
                    "total_slots": 1,
                }
                handle.write(json.dumps(sample, sort_keys=True) + "\n")
                handle.flush()
                stopped.wait(interval)

    thread = threading.Thread(target=work, name="preparation-monitor", daemon=True)
    thread.start()

    def close():
        stopped.set()
        thread.join(timeout=30)

    return close


def run_preparation(
    config, *, source_root, data_root, backend_factory=NemotronSpeechEncoder
):
    """Run a single immutable attempt; never restart or replay a failed contact."""
    source_root, data_root = Path(source_root), Path(data_root)
    plan = ExecutionPlan(**config["plan"]).validate()
    if plan.schema != "saea-execution-plan-v1":
        raise SpeechPreparationError("speech query preparation requires a speech plan")
    protocol = pinned_json(config["protocol"])
    if protocol.get("schema") != "saea-speech-query-encoding-protocol-v1":
        raise SpeechPreparationError("preparation protocol schema is invalid")
    if plan.protocol_hash != config["protocol"]["sha256"]:
        raise SpeechPreparationError(
            "execution plan protocol differs from configuration"
        )
    admit(
        plan=plan,
        source_root=source_root,
        exposure_ledger=source_root / "docs/exposure-ledger.md",
        umbrella_lock=Path(config["umbrella_lock"]["path"]),
        umbrella_lock_sha256=config["umbrella_lock"]["sha256"],
        protocol_path=Path(config["protocol"]["path"]),
        protocol_sha256=config["protocol"]["sha256"],
    )
    sources, encoder = (
        pinned_json(protocol["sources"]),
        pinned_json(protocol["encoder"]),
    )
    if sources["roster_sha256"] != protocol["roster_sha256"]:
        raise SpeechPreparationError("source roster hash differs from protocol")
    paths = {
        key: confined(data_root, protocol[key])
        for key in ("output_relpath", "query_rows_relpath", "cache_relpath")
    }
    rows = sources["rows"]
    identity = hashlib.sha256(
        "\n".join(
            sorted(f"{plan.carrier_lock_key}/{row['id']}" for row in rows)
        ).encode("utf-8")
    ).hexdigest()
    if identity != plan.split_identity_hash:
        raise SpeechPreparationError(
            "query roster does not match execution split identity"
        )
    if protocol["query_prompt"] != "query: ":
        raise SpeechPreparationError(
            "speech query must preserve the pinned query prompt"
        )
    spans = {
        (
            row["audio_sha256"],
            row["source_frames"],
            row["source_sample_rate_hz"],
            span["start_frame"],
            span["end_frame"],
        )
        for row in rows
        for span in segment_plan(
            row["source_frames"],
            row["source_sample_rate_hz"],
            max_seconds=protocol["max_seconds"],
            overlap_seconds=protocol["overlap_seconds"],
        )
    }
    audio_seconds = sum(
        (end - start) / rate for _sha, _frames, rate, start, end in spans
    )
    if (
        len(spans) != protocol["expected_unique_spans"]
        or len(spans) > plan.planned_model_calls
        or audio_seconds > plan.planned_speech_audio_seconds
    ):
        raise SpeechPreparationError(
            "source plan exceeds registered contacts or audio budget"
        )
    if (
        type(protocol["cpu_workers"]) is not int
        or not 1 <= protocol["cpu_workers"] <= 8
        or protocol["monitor_interval_seconds"] != 10
    ):
        raise SpeechPreparationError("CPU or monitor configuration is invalid")
    verify_encoder(encoder, data_root)

    def prepare(backend, contact):
        return prepare_speech_query_vectors(
            paths["output_relpath"],
            rows=rows,
            data_root=data_root,
            cache_root=paths["cache_relpath"],
            encoder=contact,
            encoder_identity={"inventory_sha256": protocol["encoder"]["sha256"]},
            protocol_id=plan.protocol_hash,
            dimension=protocol["dimension"],
            max_seconds=protocol["max_seconds"],
            overlap_seconds=protocol["overlap_seconds"],
            prepare_sources=backend.prepare_sources,
        )

    return _execute_preparation(
        config=config,
        plan=plan,
        protocol=protocol,
        data_root=data_root,
        encoder=encoder,
        backend_factory=backend_factory,
        prepare=prepare,
        row_path=paths["query_rows_relpath"],
        row_label="query",
        contact_kind="speech",
        seconds_for_source=lambda source: (
            (source["end_frame"] - source["start_frame"])
            / source["source_sample_rate_hz"]
        ),
        facts_for_source=lambda source: {
            key: source[key] for key in ("audio_sha256", "start_frame", "end_frame")
        },
        source_bindings={"source_inventory_sha256": protocol["sources"]["sha256"]},
    )


def _execute_preparation(
    *,
    config,
    plan,
    protocol,
    data_root,
    encoder,
    backend_factory,
    prepare,
    row_path,
    row_label,
    contact_kind,
    seconds_for_source,
    facts_for_source,
    source_bindings,
    finalize_prepared=None,
    contact_counter_field="logical_encoder_contacts",
    forward_phase="encoder_forward_started",
):
    """Share custody, pre-contact accounting, sealing and aborts across modalities."""
    attempt_dir = data_root / "preparation-runs" / plan.run_id / str(plan.attempt_id)
    attempt_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    state = {
        "started_monotonic": started,
        "calls": 0,
        "audio_seconds": 0.0,
        "phase": "admitted",
        "contact_counter_field": contact_counter_field,
        "forward_phase": forward_phase,
    }
    event_path = attempt_dir / "events.jsonl"

    def event(phase, **facts):
        state["phase"] = phase
        with event_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "timestamp": _now(),
                        "phase": phase,
                        "elapsed_seconds": time.monotonic() - started,
                        **facts,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())

    with GenerationLease.acquire(
        data_root,
        owner="root-speech-preparation"
        if contact_kind == "speech"
        else "root-text-facet-preparation",
        run_id=plan.run_id,
        attempt_id=plan.attempt_id,
        session_id=config["session_id"],
        study_head=config["study_head"],
    ):
        attempt = AttemptStore(data_root / "attempts").open_attempt(
            plan.run_id,
            plan.attempt_id,
            carrier_lock_key=plan.carrier_lock_key,
            reserved_calls=plan.planned_model_calls,
            reserved_audio_seconds=plan.planned_speech_audio_seconds,
            **({"contact_kind": contact_kind} if contact_kind != "speech" else {}),
        )
        stop_monitor = start_monitor(attempt_dir / "monitor.jsonl", state, 10)
        backend = None
        attempt_finalized = False
        try:
            backend = backend_factory(encoder, protocol, data_root, event)

            def contact(source, *, batch=False):
                sources = tuple(source) if batch else (source,)
                if not sources:
                    raise SpeechPreparationError("preparation batch must not be empty")
                invoke = getattr(backend, "decode_batch", None) if batch else backend
                if not callable(invoke):
                    raise SpeechPreparationError("backend does not implement the declared contact")
                seconds = sum(seconds_for_source(item) for item in sources)
                if (
                    state["calls"] + len(sources) > plan.planned_model_calls
                    or state["audio_seconds"] + seconds > plan.planned_speech_audio_seconds
                    or time.monotonic() - started >= plan.planned_gpu_hours * 3600
                ):
                    raise SpeechPreparationError("preparation budget exhausted before contact")
                state["calls"], state["audio_seconds"] = attempt.record_usage(
                    calls=len(sources), audio_seconds=seconds)
                event(
                    "contact_started",
                    ordinal=state["calls"],
                    **(
                        {"batch_size": len(sources),
                         "sources": [facts_for_source(item) for item in sources]}
                        if batch else {"source": facts_for_source(source)}
                    ),
                )
                result = invoke(sources if batch else source)
                if batch and (not isinstance(result, (tuple, list)) or len(result) != len(sources)):
                    raise SpeechPreparationError("backend batch result count differs from charged contacts")
                event("contact_finished", ordinal=state["calls"])
                return result

            prepared = prepare(backend, contact)
            if finalize_prepared is not None:
                result, finalization = finalize_prepared(prepared, state, attempt_dir)
                _exclusive_json(attempt_dir / "receipt.json", result)
                attempt.finalize_with_receipt(
                    finalization["path"], finalization["sha256"], finalization["kind"]
                )
            else:
                query_path = row_path
                content = b"".join(
                    canonical_bytes(row) + b"\n"
                    for row in prepared["artifact"]["output"]["rows"]
                )
                query_path.parent.mkdir(parents=True, exist_ok=True)
                if query_path.exists():
                    if query_path.read_bytes() != content:
                        raise SpeechPreparationError("sealed query row export differs")
                else:
                    with query_path.open("xb") as handle:
                        handle.write(content)
                        handle.flush()
                        os.fsync(handle.fileno())

                result = {
                    "schema": (
                        "saea-speech-query-preparation-receipt-v1"
                        if contact_kind == "speech"
                        else "saea-text-facet-preparation-receipt-v1"
                    ),
                    "status": "SEALED",
                    "run_id": plan.run_id,
                    "attempt_id": plan.attempt_id,
                    "protocol_sha256": plan.protocol_hash,
                    "study_head": config["study_head"],
                    **source_bindings,
                    "encoder_inventory_sha256": protocol["encoder"]["sha256"],
                    f"{row_label}_rows_path": str(query_path),
                    f"{row_label}_rows_sha256": hashlib.sha256(content).hexdigest(),
                    "index_sha256": prepared["artifact"]["sha256"],
                    state.get("contact_counter_field", "logical_encoder_contacts"): state["calls"],
                    "actual_speech_audio_seconds": state["audio_seconds"],
                    "elapsed_seconds": time.monotonic() - started,
                    "cache_accounting": prepared["accounting"],
                    "closed_at": _now(),
                }
                _exclusive_json(attempt_dir / "receipt.json", result)
                attempt.mark_finalized()
            attempt_finalized = True
            event("sealed")
            return result
        except BaseException as error:
            failure = error
            def preserve_failure(action, label):
                try:
                    action()
                except BaseException as secondary:
                    failure.add_note(f"{label} also failed: {type(secondary).__name__}: {secondary}")

            if not attempt_finalized:
                preserve_failure(lambda: attempt.mark_aborted(type(failure).__name__), "attempt abort")
            preserve_failure(
                lambda: event("aborted" if not attempt_finalized else "post_finalize_failure",
                              error_type=type(failure).__name__, error=str(failure)), "failure event")
            preserve_failure(
                lambda: _exclusive_json(attempt_dir / "abort.json", {
                    "status": "FINALIZED_WITH_POST_SEAL_ERROR" if attempt_finalized else "ABORTED",
                    "error_type": type(failure).__name__,
                    contact_counter_field: state["calls"],
                    "actual_speech_audio_seconds": state["audio_seconds"],
                    "elapsed_seconds": time.monotonic() - started,
                }), "failure receipt")
            raise
        finally:
            primary = sys.exc_info()[1]
            for label, close in (
                ("backend cleanup", backend.close if backend is not None else lambda: None),
                ("monitor cleanup", stop_monitor),
            ):
                try:
                    close()
                except BaseException as cleanup_error:
                    if primary is None:
                        primary = cleanup_error
                    else:
                        primary.add_note(f"{label} also failed: {type(cleanup_error).__name__}: {cleanup_error}")
            if sys.exc_info()[1] is None and primary is not None:
                raise primary


def run_text_facet_preparation(
    config, *, source_root, data_root, backend_factory=NemotronPassageEncoder
):
    """Validate text-only source identity, then use the common preparation lifecycle."""
    from ..rails.knowledge import KnowledgeSnapshot

    source_root, data_root = Path(source_root), Path(data_root)
    plan = ExecutionPlan(**config["plan"]).validate()
    if plan.schema != "saea-text-encoder-plan-v1":
        raise SpeechPreparationError(
            "text facet preparation requires a text encoder plan"
        )
    protocol = pinned_json(config["protocol"])
    if protocol.get("schema") != "saea-text-facet-encoding-protocol-v1":
        raise SpeechPreparationError("text facet protocol schema is invalid")
    if plan.protocol_hash != config["protocol"]["sha256"]:
        raise SpeechPreparationError("text facet plan must bind the exact protocol")
    admit(
        plan=plan,
        source_root=source_root,
        exposure_ledger=source_root / "docs/exposure-ledger.md",
        umbrella_lock=Path(config["umbrella_lock"]["path"]),
        umbrella_lock_sha256=config["umbrella_lock"]["sha256"],
        protocol_path=Path(config["protocol"]["path"]),
        protocol_sha256=config["protocol"]["sha256"],
    )
    # Pin file bytes first. The snapshot's semantic content hash is a separate
    # identity and must never be compared to a pretty-printed file hash.
    snapshot_document = pinned_json(protocol["snapshot"])
    snapshot = KnowledgeSnapshot.from_frozen_json(snapshot_document)
    if snapshot.content_hash() != snapshot_document["snapshot_sha256"]:
        raise SpeechPreparationError("snapshot semantic content identity differs")
    snapshot_sha256 = protocol["snapshot"]["sha256"]
    facet_dimension = protocol.get("facet_dimension", "content")
    if (
        not isinstance(facet_dimension, str)
        or not facet_dimension
        or facet_dimension != facet_dimension.strip()
    ):
        raise SpeechPreparationError(
            "text facet protocol facet_dimension must be non-empty text without surrounding space"
        )
    facets = [
        {"id": facet.facet_id, "text": facet.representation}
        for facet in snapshot.facets
        if (facet.dimension == facet_dimension and facet.representation_kind == "text")
    ]
    count = protocol["expected_positive_content_facets"]
    if (
        type(count) is not int
        or count <= 0
        or len(facets) != count
        or count > plan.planned_model_calls
    ):
        raise SpeechPreparationError(
            "text facet count differs or exceeds registered calls"
        )
    identity = hashlib.sha256(
        "\n".join(
            sorted(f"{plan.carrier_lock_key}/{row['id']}" for row in facets)
        ).encode()
    ).hexdigest()
    if identity != plan.split_identity_hash:
        raise SpeechPreparationError(
            "text facet roster differs from execution identity"
        )
    for key, value in (
        ("dimension", 2048),
        ("max_sequence_tokens", 8192),
        ("cpu_workers", 1),
        ("monitor_interval_seconds", 10),
    ):
        if type(protocol.get(key)) is not int or protocol[key] != value:
            raise SpeechPreparationError(
                f"text facet protocol {key} differs from recipe"
            )
    if protocol.get("passage_prompt") != "passage: ":
        raise SpeechPreparationError("text facet passage prompt differs from recipe")
    paths = {
        key: confined(data_root, protocol[key])
        for key in ("output_relpath", "facet_rows_relpath", "cache_relpath")
    }
    encoder = pinned_json(protocol["encoder"])
    verify_encoder(encoder, data_root)

    def prepare(_backend, contact):
        return prepare_text_facet_vectors(
            paths["output_relpath"],
            facets=facets,
            cache_root=paths["cache_relpath"],
            encoder=contact,
            encoder_identity={"inventory_sha256": protocol["encoder"]["sha256"]},
            snapshot_sha256=snapshot_sha256,
            protocol_id=plan.protocol_hash,
            dimension=protocol["dimension"],
            facet_dimension=facet_dimension,
        )

    return _execute_preparation(
        config=config,
        plan=plan,
        protocol=protocol,
        data_root=data_root,
        encoder=encoder,
        backend_factory=backend_factory,
        prepare=prepare,
        row_path=paths["facet_rows_relpath"],
        row_label="facet",
        contact_kind="text-encoder",
        seconds_for_source=lambda _text: 0.0,
        facts_for_source=lambda text: {
            "text_sha256": hashlib.sha256(text.encode()).hexdigest()
        },
        source_bindings={
            "snapshot_sha256": snapshot_sha256,
            "snapshot_content_sha256": snapshot.content_hash(),
            **(
                {"facet_dimension": facet_dimension}
                if facet_dimension != "content"
                else {}
            ),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    config = pinned_json({"path": str(args.config), "sha256": args.config_sha256})
    head = subprocess.check_output(
        ["git", "-C", str(args.source_root), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != config["study_head"]:
        raise SpeechPreparationError(
            "runner checkout differs from registered code identity"
        )
    if subprocess.check_output(
        ["git", "-C", str(args.source_root), "status", "--porcelain"], text=True
    ):
        raise SpeechPreparationError("runner checkout must be frozen and clean")
    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    protocol = pinned_json(config["protocol"])
    from .preparation_speech_observations import run_speech_observation_preparation

    runners = {
        "saea-text-facet-encoding-protocol-v1": run_text_facet_preparation,
        "saea-speech-query-encoding-protocol-v1": run_preparation,
        "saea-speech-observation-preparation-protocol-v1": run_speech_observation_preparation,
    }
    runner = runners.get(protocol.get("schema"))
    if runner is None:
        raise SpeechPreparationError("unknown frozen tool preparation protocol")
    print(
        json.dumps(
            runner(config, source_root=args.source_root, data_root=args.data_root),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
