"""Run configured frozen speech-query preparation under shared custody."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from ..contracts import ExecutionPlan
from .attempts import AttemptStore
from .flight.lease import GenerationLease
from .preparation import canonical_bytes, hash_stable_file
from .preparation_runtime import verify_pinned_file
from .preparation_speech_queries import prepare_speech_query_vectors, segment_plan
from .speech_embedding import encode, load_stack, read_audio_span, render


class SpeechPreparationError(RuntimeError):
    """Refuse a drifting or unregistered preparation."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def pinned_json(binding):
    path = Path(binding["path"])
    _size, sha, fingerprint = hash_stable_file(path, "preparation binding")
    if sha != binding["sha256"]:
        raise SpeechPreparationError("preparation binding hash changed")
    value = json.loads(path.read_bytes())
    stat = path.stat()
    if (stat.st_ino, stat.st_size, stat.st_mtime_ns) != fingerprint:
        raise SpeechPreparationError("preparation binding changed during read")
    return value


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
        self.event("encoder_forward_started")
        result = encode(
            processor,
            model,
            [text],
            [wave],
            max_audio_samples=self.protocol["max_audio_samples"],
            require_complete_audio=True,
            max_sequence_tokens=self.protocol["max_sequence_tokens"],
        )
        self.event("encoder_forward_finished")
        return result[0]

    def close(self):
        self.prefetch.close()
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
                    "logical_encoder_contacts": state["calls"],
                    "phase": state["phase"],
                    "busy_slots": int(state["phase"] == "encoder_forward_started"),
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
    attempt_dir = data_root / "preparation-runs" / plan.run_id / str(plan.attempt_id)
    attempt_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    state = {
        "started_monotonic": started,
        "calls": 0,
        "audio_seconds": 0.0,
        "phase": "admitted",
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
        owner="root-speech-preparation",
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
        )
        stop_monitor = start_monitor(attempt_dir / "monitor.jsonl", state, 10)
        backend = None
        try:
            backend = backend_factory(encoder, protocol, data_root, event)

            def contact(source):
                seconds = (source["end_frame"] - source["start_frame"]) / source[
                    "source_sample_rate_hz"
                ]
                if (
                    state["calls"] + 1 > plan.planned_model_calls
                    or state["audio_seconds"] + seconds
                    > plan.planned_speech_audio_seconds
                    or time.monotonic() - started >= plan.planned_gpu_hours * 3600
                ):
                    raise SpeechPreparationError(
                        "preparation budget exhausted before contact"
                    )
                attempt.record_usage(calls=1, audio_seconds=seconds)
                state["calls"] += 1
                state["audio_seconds"] += seconds
                event(
                    "contact_started",
                    ordinal=state["calls"],
                    source={
                        key: source[key]
                        for key in ("audio_sha256", "start_frame", "end_frame")
                    },
                )
                result = backend(source)
                event("contact_finished", ordinal=state["calls"])
                return result

            prepared = prepare_speech_query_vectors(
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
            query_path = paths["query_rows_relpath"]
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
                "schema": "saea-speech-query-preparation-receipt-v1",
                "status": "SEALED",
                "run_id": plan.run_id,
                "attempt_id": plan.attempt_id,
                "protocol_sha256": plan.protocol_hash,
                "study_head": config["study_head"],
                "source_inventory_sha256": protocol["sources"]["sha256"],
                "encoder_inventory_sha256": protocol["encoder"]["sha256"],
                "query_rows_path": str(query_path),
                "query_rows_sha256": hashlib.sha256(content).hexdigest(),
                "index_sha256": prepared["artifact"]["sha256"],
                "logical_encoder_contacts": state["calls"],
                "actual_speech_audio_seconds": state["audio_seconds"],
                "elapsed_seconds": time.monotonic() - started,
                "cache_accounting": prepared["accounting"],
                "closed_at": _now(),
            }
            _exclusive_json(attempt_dir / "receipt.json", result)
            attempt.mark_finalized()
            event("sealed")
            return result
        except BaseException as error:
            attempt.mark_aborted(type(error).__name__)
            event("aborted", error_type=type(error).__name__, error=str(error))
            _exclusive_json(
                attempt_dir / "abort.json",
                {
                    "status": "ABORTED",
                    "error_type": type(error).__name__,
                    "logical_encoder_contacts": state["calls"],
                    "actual_speech_audio_seconds": state["audio_seconds"],
                    "elapsed_seconds": time.monotonic() - started,
                },
            )
            raise
        finally:
            if backend is not None:
                backend.close()
            stop_monitor()


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
    print(
        json.dumps(
            run_preparation(
                config, source_root=args.source_root, data_root=args.data_root
            ),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
