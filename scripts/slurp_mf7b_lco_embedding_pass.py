#!/usr/bin/env python3
"""MF-7b (a): the LCO-Embedding-Omni-3B encoder pass for the SLURP key audit.

Exposure row ``SAEA-SLURP-MF7B-LCO-EMBEDDING-V1``, registered before the first
contact. **Tool-level contacts only; 0 frozen-core contacts.** Preregistration:
``docs/readiness/2026-09-06-slurp-retrieval-key-audit-v2-preregistration.md``.

Four sets over MF-7's own roster, written in the ``saea-mf7-vectors-v1`` JSONL
schema so ``scripts/run_slurp_retrieval_key_audit_v2.py`` consumes them without
a code change:

* ``lco-q-speech-query-vectors.jsonl`` -- 1,000 DEV-1000 recordings, audio alone;
* ``lco-fused-q-speech-query-vectors.jsonl`` -- the same recordings with the
  sealed KU-S1c phase-1 draft response text as ONE multimodal input. The state
  text precedes the media marker, so under ``--pooling last`` the pooled vector
  sits on the final AUDIO token conditioned by the state, rather than on the
  final text token (which would be a draft-text embedding wearing an audio
  prefix). ``rails.embedding_client.EmbeddingClient.embed_audio``'s registered
  ``prompt_prefix`` is exactly that shape and no new request form is invented;
* ``lco-key-vectors.jsonl`` -- the 11,514 TRAIN utterance texts;
* ``lco-label-key-vectors.jsonl`` -- the 60 intent label descriptions built by
  the preregistered rule ``saea-mf7b-label-text-v1``.

The server is started OUTSIDE this script (one resident llama-server per
serving geometry) and this script refuses to run until ``GET /props`` verifies
the process's own randomised ``media_marker`` against the value it was given --
``EmbeddingClient(require_marker_verification=True, expected_dim=2048)`` does
that fail-closed. Audio is read with ``soundfile`` and resampled, if ever
needed, with ``librosa``: **ffmpeg is deliberately absent from this machine and
must never be installed.** No completion, chat or generation endpoint is
contacted; the held-out ``test`` split is never named; no devel sentence text
is read.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.rails.embedding_client import EmbeddingClient  # noqa: E402

from speech_aware_evidence_acquisition.analysis.slurp_mf7b_vectors import (  # noqa: E402
    RECEIPT_SCHEMA,
    dev_rows,
    draft_texts,
    label_key_texts,
    read_audio_wav_bytes,
    sha256_file,
    train_facets,
    vector_set_block,
    write_vectors_jsonl,
)

ROW_ID = "SAEA-SLURP-MF7B-LCO-EMBEDDING-V1"
ENCODER_ID = "lco-embedding-omni-3b"
DIMS = 2048
BUILD_COMMIT = "04ccc72a2207347ca76161b93fd9d846dd0a8675"
MODEL_SUBDIR = "models/lco-embedding-omni-3b-gguf"
GGUF = "LCO-Embedding-Omni-3B-Q8_0.gguf"
MMPROJ = "mmproj-LCO-Embedding-Omni-3b-F16.gguf"
#: sha256 of both files as pinned in the umbrella lock; re-verified before use.
LOCK_SHA256 = {
    GGUF: "53a9898bdb562ae599a81528a2935153457b82e7cac3aa5b10e5eecefc887d6a",
    MMPROJ: "765beb616247081f53c9a0b7fed02b96981c5bad563209b5a47ca770f056a13a",
}


def props(base_url: str) -> dict:
    with urllib.request.urlopen(base_url.rstrip("/") + "/props", timeout=30) as handle:
        return json.loads(handle.read().decode("utf-8"))


def embed_texts(
    client: EmbeddingClient, items: list[tuple[str, str]], *, batch_size: int
) -> tuple[list[str], list[tuple[float, ...]], float]:
    ids: list[str] = []
    vectors: list[tuple[float, ...]] = []
    started = time.time()
    for offset in range(0, len(items), batch_size):
        chunk = items[offset : offset + batch_size]
        for vector in client.embed_text_batch(chunk):
            ids.append(vector.contact_id)
            vectors.append(vector.values)
    return ids, vectors, time.time() - started


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8093")
    parser.add_argument("--text-batch", type=int, default=32)
    parser.add_argument(
        "--sets",
        default="speech,fused,keys,labels",
        help="comma-separated subset of speech,fused,keys,labels",
    )
    args = parser.parse_args()
    wanted = {name.strip() for name in args.sets.split(",") if name.strip()}

    root = Path(data_root())
    model_dir = root / MODEL_SUBDIR
    fingerprints = {name: sha256_file(model_dir / name) for name in LOCK_SHA256}
    for name, expected in LOCK_SHA256.items():
        if fingerprints[name] != expected:
            raise SystemExit(f"{name} sha256 {fingerprints[name]} != lock {expected}")

    out_dir = root / "vectors/slurp-mf7b"
    out_dir.mkdir(parents=True, exist_ok=True)

    live = props(args.base_url)
    marker = live.get("media_marker")
    if not isinstance(marker, str) or not marker:
        raise SystemExit("GET /props carries no media_marker; refusing to guess one")
    client = EmbeddingClient(
        base_url=args.base_url,
        expected_media_marker=marker,
        expected_dim=DIMS,
        require_marker_verification=True,
        timeout_seconds=600.0,
    )
    client.verify_media_marker()

    rows = dev_rows(root)
    facets = train_facets(root)
    drafts = draft_texts(root)
    receipt_sets: dict[str, dict] = {}
    audio_seconds = 0.0
    started_all = time.time()

    if "keys" in wanted:
        items = [(row["facet_id"], row["text"]) for row in facets]
        ids, vectors, wall = embed_texts(client, items, batch_size=args.text_batch)
        path = write_vectors_jsonl(out_dir / "lco-key-vectors.jsonl", ids, vectors)
        receipt_sets["lco-train-text"] = vector_set_block(
            path, ids, vectors, wall, extra={"batch_size": args.text_batch,
                                             "key_space": "TRAIN utterance texts"})
        print(f"keys: {len(ids)} in {wall:.1f}s")

    if "labels" in wanted:
        items = label_key_texts(root)
        ids, vectors, wall = embed_texts(client, items, batch_size=args.text_batch)
        path = write_vectors_jsonl(out_dir / "lco-label-key-vectors.jsonl", ids, vectors)
        receipt_sets["lco-label-text"] = vector_set_block(
            path, ids, vectors, wall, extra={"batch_size": args.text_batch,
                                             "key_space": "60 intent label descriptions",
                                             "label_text_rule": "saea-mf7b-label-text-v1"})
        print(f"labels: {len(ids)} in {wall:.1f}s")

    jitter: dict[str, object] | None = None
    if "speech" in wanted:
        ids: list[str] = []
        vectors: list[tuple[float, ...]] = []
        started = time.time()
        for index, row in enumerate(rows):
            wav = read_audio_wav_bytes(root / row["media_relpath"])
            vector = client.embed_audio(contact_id=row["sample_id"], audio_bytes=wav)
            ids.append(vector.contact_id)
            vectors.append(vector.values)
            audio_seconds += float(row["audio_seconds"])
            if index == 0:
                again = client.embed_audio(
                    contact_id=row["sample_id"] + "::jitter", audio_bytes=wav
                )
                jitter = {
                    "sample_id": row["sample_id"],
                    "bit_exact": again.values == vector.values,
                    "max_abs_delta": max(
                        abs(a - b) for a, b in zip(again.values, vector.values, strict=True)
                    ),
                }
            if (index + 1) % 100 == 0:
                rate = (index + 1) / (time.time() - started)
                print(f"speech {index + 1}/{len(rows)} at {rate:.2f}/s", flush=True)
        wall = time.time() - started
        path = write_vectors_jsonl(out_dir / "lco-q-speech-query-vectors.jsonl", ids, vectors)
        receipt_sets["q-speech-lco"] = vector_set_block(
            path, ids, vectors, wall,
            extra={"batch_size": 1, "audio_seconds_encoded": audio_seconds,
                   "realtime_factor": audio_seconds / wall if wall else None,
                   "request_shape": "prompt_string = media marker; multimodal_data = [wav b64]"})
        print(f"speech: {len(ids)} in {wall:.1f}s")

    if "fused" in wanted:
        ids = []
        vectors = []
        fused_seconds = 0.0
        started = time.time()
        for index, row in enumerate(rows):
            wav = read_audio_wav_bytes(root / row["media_relpath"])
            state = drafts[row["sample_id"]]
            vector = client.embed_audio(
                contact_id=row["sample_id"], audio_bytes=wav, prompt_prefix=state + "\n"
            )
            ids.append(vector.contact_id)
            vectors.append(vector.values)
            fused_seconds += float(row["audio_seconds"])
            if (index + 1) % 100 == 0:
                rate = (index + 1) / (time.time() - started)
                print(f"fused {index + 1}/{len(rows)} at {rate:.2f}/s", flush=True)
        wall = time.time() - started
        audio_seconds += fused_seconds
        path = write_vectors_jsonl(
            out_dir / "lco-fused-q-speech-query-vectors.jsonl", ids, vectors
        )
        receipt_sets["q-speech-lco-fused"] = vector_set_block(
            path, ids, vectors, wall,
            extra={"batch_size": 1, "audio_seconds_encoded": fused_seconds,
                   "realtime_factor": fused_seconds / wall if wall else None,
                   "request_shape": "prompt_string = <sealed KU-S1c draft text> + newline + "
                   "media marker; multimodal_data = [wav b64]",
                   "state_source": "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1 phase-1 draft "
                   "response text, sealed"})
        print(f"fused: {len(ids)} in {wall:.1f}s")

    total_wall = time.time() - started_all
    close = client.close()
    # Resumable by design: each set's JSONL is final the moment it is written,
    # and a later invocation merges its own sets and accounting into the
    # receipt rather than replacing the sets it did not produce.
    receipt_path = out_dir / "lco.receipt.json"
    prior = (
        json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt_path.is_file()
        else {}
    )
    prior_sets = dict(prior.get("sets", {}))
    prior_acct = dict(prior.get("accounting", {}))
    prior_passes = list(prior.get("passes", []))
    prior_passes.append({
        "sets": sorted(wanted),
        "contacts": close["contact_count"],
        "http_requests": client.http_request_count,
        "wall_seconds": total_wall,
        "speech_audio_seconds": audio_seconds,
    })
    write_json_artifact(receipt_path, {
        "schema": RECEIPT_SCHEMA,
        "exposure_ledger_row": ROW_ID,
        "embedder": {
            "encoder_id": ENCODER_ID,
            "role": "pinned TOOL-level omni embedder; never the frozen core",
            "model_dir_relpath": MODEL_SUBDIR,
            "gguf": GGUF,
            "gguf_sha256": fingerprints[GGUF],
            "mmproj": MMPROJ,
            "mmproj_sha256": fingerprints[MMPROJ],
            "server": "llama.cpp-featcache llama-server --embedding --pooling last",
            "build_commit": BUILD_COMMIT,
            "argv": "-ngl 999 -c 8192 -b 2048 -ub 2048 -np 1 -fa on",
            "dims": DIMS,
            "props": {key: live.get(key) for key in
                      ("model_path", "modalities", "media_marker", "n_ctx", "build_info",
                       "default_generation_settings", "chat_template")
                      if key in live and key != "chat_template"},
            "pooling": "last (model card: LCO uses last-token pooling)",
            "text_prefix": "",
            "gpu": True,
        },
        "sets": {**prior_sets, **receipt_sets},
        "jitter_pair": jitter if jitter is not None else prior.get("jitter_pair"),
        "passes": prior_passes,
        "accounting": {
            "frozen_core_contacts": 0,
            "embedding_tool_contacts": int(prior_acct.get("embedding_tool_contacts", 0))
            + close["contact_count"],
            "http_requests": int(prior_acct.get("http_requests", 0))
            + client.http_request_count,
            "registered_ceiling_contacts": 13600,
            "speech_audio_seconds": float(prior_acct.get("speech_audio_seconds", 0.0))
            + audio_seconds,
            "wall_seconds": float(prior_acct.get("wall_seconds", 0.0)) + total_wall,
            "gpu_hours": (float(prior_acct.get("wall_seconds", 0.0)) + total_wall) / 3600.0,
        },
        "boundary": {
            "held_out_test_split_named": False,
            "devel_sentence_text_read": False,
            "generation_endpoint_contacted": False,
        },
    })
    print(json.dumps({"contacts": close["contact_count"],
                      "http_requests": client.http_request_count,
                      "wall_seconds": round(total_wall, 1),
                      "gpu_hours": round(total_wall / 3600.0, 4)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
