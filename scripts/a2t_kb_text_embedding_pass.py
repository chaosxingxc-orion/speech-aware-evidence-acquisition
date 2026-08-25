"""SAEA-SN-TOOL-A2T-KB-TEXT-EMB-PASS -- text-embedding pass over the frozen
Audio2Tool tool-shaped ``size-full`` knowledge snapshot.

Audio2Tool generality campaign, stage G1 prerequisite. The BLEND arm's
recall is a cosine sweep over CONTENT-dimension facet vectors
(``rails.kb_policy.multidim_recall`` takes ``facet_vectors`` as
``facet_id -> {dimension: vector}``), and the A2T knowledge base built at G0
carries NO vectors at all: G0 was registered at zero contacts, so it computed
a lexical reachability ceiling instead and explicitly reported that no dense
ceiling was produced. Those vectors are this pass's only product.

What this embeds, and what it deliberately does not:

* every ``dimension == "content"`` KeyFacet's ``representation`` text (12,601)
* NOT the 12,601 ValueBundle texts. The locked v1 cell admits percepts
  FACET-SIDE with VALUE VECTORS SEALED -- the DEV-1000 lock flight states in
  its own report that ``vectors-values.npz`` is never loaded -- so value
  vectors would be ~17 minutes of tool contacts producing material no arm may
  read. The SLURP pass produced them only because its own preregistration
  named both families. Recorded here rather than left as a silent difference.
* NOT the 184 label / 151 prior facets -- those are recalled by prior mass and
  exact-key agreement, never by vector similarity.

Charter binding: the embedder is a PINNED TOOL-level model, never the frozen
core. It is reached only through ``rails.embedding_client.EmbeddingClient``,
whose encode-only surface is proven fail-closed by ``rails.encode_only_check``
BEFORE the server is spawned (source guards over the pinned module set AND
over this runner's own source) and again on the live client object; every
single request payload is additionally swept for sampling/generation-shaped
keys on the real wire path.

Serving discipline: CPU-ONLY (``-ngl 0``) on loopback port 8082, in its own
receipt-bound session with its own log. The resident A2T np2 decoder (port
8090) is never contacted, probed, restarted, or reconfigured; its own server
log's byte length and sha256 are captured before and after this pass as the
proof.

Storage discipline: vectors are stored EXACTLY as the server returns them
(the pinned llama.cpp server returns L2-normalized pooled vectors by default;
the measured norm range is recorded in the manifest).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
RUN_ID = "SAEA-SN-TOOL-A2T-KB-TEXT-EMB-PASS"
EMB_PORT = 8082
RESIDENT_DECODER_PORT = 8090
RESIDENT_DECODER_SESSION_ID = "SAEA-SN-Q4KM-NP2-BASE-A2T-G1-20260825T092000Z"
RESIDENT_DECODER_LOG = (
    Path("/home/chao/runs/services") / RESIDENT_DECODER_SESSION_ID / "server.log"
)

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit(
        "PYTHONDONTWRITEBYTECODE=1 is required (bytecode under the frozen package closes the D3 gate)"
    )
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

_pkg_file = Path(_pkg.__file__ or "")
if _pkg_file != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit(
        "package resolves to %s, not the main checkout (hijacked install)" % (_pkg_file,)
    )

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.rails.embedding_client import (  # noqa: E402
    EmbeddingClient,
)
from speech_aware_evidence_acquisition.rails.encode_only_check import (  # noqa: E402
    assert_client_surface_is_encode_only,
    assert_module_never_imports_generation_client,
    assert_payload_has_no_forbidden_keys,
    assert_source_has_no_forbidden_endpoint_strings,
    run_encode_only_machine_check,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
)

DATA_ROOT = Path(os.environ["SPEECHRL_DATA_DIR"])
RUNTIME_ROOT = Path(os.environ.get("LLAMA_RUNTIME_ROOT", "/home/chao"))
SNAPSHOT_DIR = DATA_ROOT / "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full"
SNAPSHOT_PATH = SNAPSHOT_DIR / "snapshot.json"
SNAPSHOT_CONTENT_SHA256 = (
    "ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2"
)

EMBEDDER_LOCK_KEY = "qwen3-embedding-0.6b-gguf"
EMBEDDER_RELPATH = "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"
EMBEDDER_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
EMBEDDER_REVISION = "370f27d7550e0def9b39c1f16d3fbaa13aa67728"
EMBEDDER_DIM = 1024
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"

SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
    "-b", "4096", "-ub", "4096", "-np", "1", "-t", "16",
)


def iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Logger:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle = path.open("a", encoding="utf-8")

    def __call__(self, message: str) -> None:
        line = "[%s] %s" % (iso_now(), message)
        print(line, flush=True)
        self._handle.write(line + "\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


def decoder_fingerprint() -> dict[str, object]:
    """Everything needed to prove the resident A2T decoder was never touched."""

    record: dict[str, object] = {
        "session_id": RESIDENT_DECODER_SESSION_ID,
        "port": RESIDENT_DECODER_PORT,
        "observed_at": iso_now(),
    }
    try:
        stat = RESIDENT_DECODER_LOG.stat()
        record["server_log_path"] = str(RESIDENT_DECODER_LOG)
        record["server_log_bytes"] = stat.st_size
        record["server_log_sha256"] = sha256_file(RESIDENT_DECODER_LOG)
    except OSError as error:
        record["server_log_error"] = str(error)
    try:
        proc = subprocess.run(
            ["pgrep", "-af", "llama-server"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        record["llama_server_processes"] = proc.stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        record["ps_error"] = str(error)
    return record


def guarded_post(timeout_seconds: float, counter: dict[str, int]):
    """The wire-path POST the embedding client is constructed with.

    Guard 4 of the encode-only check runs on EVERY request body, not merely
    the first."""

    def post(url: str, body: bytes) -> bytes:
        assert_payload_has_no_forbidden_keys(
            json.loads(body.decode("utf-8")), context="request#%d" % counter["n"]
        )
        counter["n"] += 1
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()

    return post


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        raise RuntimeError("zero-norm vector in the jitter pair")
    return dot / (na * nb)


def main() -> int:
    preflight_only = "--preflight-only" in sys.argv
    attempt_id = "attempt-%s-a2tkbemb" % datetime.now(tz=timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    if preflight_only:
        attempt_id += "-preflight"
    run_dir = DATA_ROOT / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log = Logger(run_dir / "runner.log")
    log("%s / %s" % (RUN_ID, attempt_id))
    log("run dir: %s" % run_dir)
    log("package: %s" % _pkg_file)

    # ---- gate (a): encode-only structural check, BEFORE any spawn ---------
    report = run_encode_only_machine_check()
    log("encode-only sweep PASS over pinned modules: %r" % (list(report.checked_modules),))
    own_source = Path(__file__).resolve()
    assert_module_never_imports_generation_client(own_source)
    assert_source_has_no_forbidden_endpoint_strings(own_source)
    log("encode-only guards 1+2 PASS over this runner's own source: %s" % own_source)

    # ---- gate (b): snapshot identity -------------------------------------
    snapshot_file_sha256 = sha256_file(SNAPSHOT_PATH)
    document = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot = KnowledgeSnapshot.from_frozen_json(document)
    content_hash = snapshot.content_hash()
    if content_hash != SNAPSHOT_CONTENT_SHA256:
        raise SystemExit(
            "snapshot content hash %s != pinned %s" % (content_hash, SNAPSHOT_CONTENT_SHA256)
        )
    log(
        "snapshot %s: content hash VERIFIED (file sha256 %s, %d facets, %d values)"
        % (snapshot.snapshot_id, snapshot_file_sha256, len(snapshot.facets), len(snapshot.values))
    )

    content_facets = [f for f in snapshot.facets if f.dimension == "content"]
    log("embed targets: %d content facets (values deliberately NOT embedded)" % len(content_facets))
    for facet in content_facets:
        if facet.representation_kind != "text":
            raise SystemExit("content facet %s is not text-represented" % facet.facet_id)

    # ---- gate (c): embedder identity -------------------------------------
    embedder_path = DATA_ROOT / EMBEDDER_RELPATH
    measured = sha256_file(embedder_path)
    if measured != EMBEDDER_SHA256:
        raise SystemExit(
            "embedder sha256 %s != umbrella-lock pin %s" % (measured, EMBEDDER_SHA256)
        )
    log("embedder sha256 matches the umbrella lock pin")

    committed_runtime = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    llama_cpp = committed_runtime["llama_cpp"]
    runtime_receipt = {
        "llama_cpp": dict(llama_cpp),
        "gguf_files": [{"path": EMBEDDER_RELPATH, "sha256": measured}],
    }

    # ---- gate (d): resident decoder fingerprint, BEFORE ------------------
    before = decoder_fingerprint()
    log(
        "resident A2T decoder BEFORE: log bytes=%s sha256=%s"
        % (before.get("server_log_bytes"), str(before.get("server_log_sha256"))[:16])
    )

    if preflight_only:
        log("PREFLIGHT-ONLY: every pre-spawn gate PASSED; no server spawned, zero tool contacts")
        (run_dir / "outcome.json").write_text(
            json.dumps(
                {"status": "PREFLIGHT_PASS", "resident_decoder_before": before},
                indent=1,
                sort_keys=True,
                default=str,
            ),
            encoding="utf-8",
        )
        log.close()
        return 0

    counter = {"n": 0}
    session = None
    outcome: dict[str, object] = {"status": "ABORTED"}
    started_pass = time.time()
    try:
        log("spawning CPU-only embedder session on port %d: %r" % (EMB_PORT, list(SERVER_ARGS)))
        spawn_started = time.time()
        session = start_session(
            runtime_root=RUNTIME_ROOT,
            data_root=DATA_ROOT,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=EMB_PORT,
            session_id="%s-%s-qwen3-emb-cpu" % (RUN_ID, attempt_id),
            extra_argv=list(SERVER_ARGS),
            receipt_path=run_dir / "session-qwen3-emb-cpu.receipt.json",
            server_log_path=run_dir / "session-qwen3-emb-cpu.server.log",
            ready_timeout_seconds=1800.0,
        )
        spawn_seconds = time.time() - spawn_started
        log("session up: pid=%s port=%s (spawn+load %.1fs)" % (session.pid, session.port, spawn_seconds))

        with urllib.request.urlopen(
            "http://127.0.0.1:%d/props" % EMB_PORT, timeout=60
        ) as response:
            props = json.loads(response.read().decode("utf-8"))
        props_summary = {
            key: props[key]
            for key in sorted(props)
            if key
            in ("pooling_type", "n_ctx", "n_batch", "n_ubatch", "model_path", "build_info", "total_slots")
        }
        log("server props: %s" % json.dumps(props_summary, sort_keys=True))

        client = EmbeddingClient(
            base_url="http://127.0.0.1:%d" % EMB_PORT,
            post=guarded_post(600.0, counter),
            timeout_seconds=600.0,
            expected_dim=EMBEDDER_DIM,
            require_marker_verification=False,
        )
        assert_client_surface_is_encode_only(client)
        log("encode-only guard 3 PASS on the live client surface")
        client.verify_media_marker()

        jitter_text = content_facets[0].representation
        jitter_start = client.embed_text(contact_id="jitter:start", text=jitter_text)
        log("jitter probe embedded at session start (dim %d)" % jitter_start.dims)

        vectors = np.zeros((len(content_facets), EMBEDDER_DIM), dtype=np.float32)
        ids: list[str] = []
        hashes: list[str] = []
        block_started = time.time()
        for index, facet in enumerate(content_facets):
            text = facet.representation
            vector = client.embed_text(contact_id="cf:" + facet.facet_id, text=text)
            vectors[index] = np.asarray(vector.values, dtype=np.float32)
            ids.append(facet.facet_id)
            hashes.append(sha256_text(text))
            if (index + 1) % 500 == 0 or index + 1 == len(content_facets):
                elapsed = time.time() - block_started
                rate = (index + 1) / elapsed if elapsed > 0 else 0.0
                remaining = (len(content_facets) - index - 1) / rate if rate > 0 else 0.0
                log(
                    "content facets: %d/%d (%.2f texts/s, ~%.1f min left)"
                    % (index + 1, len(content_facets), rate, remaining / 60.0)
                )
        facet_seconds = time.time() - block_started

        jitter_end = client.embed_text(contact_id="jitter:end", text=jitter_text)
        jitter_cosine = cosine(jitter_start.values, jitter_end.values)
        bit_identical = tuple(jitter_start.values) == tuple(jitter_end.values)
        log("jitter pair cosine = %.12f (bit-identical: %s)" % (jitter_cosine, bit_identical))

        contacts = client.close()
        log("client closed: %s embedding contacts" % contacts["contact_count"])
        (run_dir / "contacts.json").write_text(
            json.dumps(contacts, indent=1, sort_keys=True), encoding="utf-8"
        )

        facet_npz = SNAPSHOT_DIR / "vectors-content-facets.npz"
        if facet_npz.exists():
            raise SystemExit("refusing to overwrite an existing %s" % facet_npz)
        np.savez(
            facet_npz,
            vectors=vectors,
            ids=np.array(ids),
            text_sha256=np.array(hashes),
        )
        log("wrote %s (%d bytes)" % (facet_npz, facet_npz.stat().st_size))

        norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
        total_seconds = time.time() - started_pass
        manifest = {
            "schema": "saea-kb-text-embeddings-manifest-v1",
            "study": "speech-aware-evidence-acquisition",
            "carrier": "audio2tool",
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "generated_at": iso_now(),
            "authority": (
                "docs/readiness/2026-08-25-a2t-generality-campaign-plan.md sections 3.4 and 3.6 "
                "(the G1 BLEND arm carries the locked cell over the A2T knowledge base) plus the "
                "G0 report docs/readiness/2026-08-25-a2t-g0-report.md section 4.1, which records "
                "that G0 produced NO dense vectors because an embedding is a tool contact"
            ),
            "snapshot": {
                "snapshot_id": snapshot.snapshot_id,
                "artifact_relpath": "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json",
                "content_sha256": content_hash,
                "file_sha256": snapshot_file_sha256,
                "builder_policy_id": snapshot.builder_policy_id,
                "source_split_identity_hash": snapshot.source_split_identity_hash,
                "facet_count": len(snapshot.facets),
                "value_count": len(snapshot.values),
            },
            "embedded": {
                "content_facets": {
                    "file": facet_npz.name,
                    "count": len(ids),
                    "dims": EMBEDDER_DIM,
                    "sha256": sha256_file(facet_npz),
                    "bytes": facet_npz.stat().st_size,
                    "source_field": "KeyFacet.representation where dimension == 'content'",
                    "order": "snapshot facet order (filtered to dimension == 'content'), row i <-> ids[i]",
                    "wall_seconds": round(facet_seconds, 3),
                    "l2_norms": {
                        "min": float(norms.min()),
                        "max": float(norms.max()),
                        "mean": float(norms.mean()),
                    },
                }
            },
            "not_embedded": {
                "values": {
                    "count": len(snapshot.values),
                    "reason": (
                        "the locked v1 cell admits percepts FACET-SIDE with VALUE VECTORS SEALED; "
                        "the DEV-1000 lock flight never loads vectors-values.npz. Embedding them "
                        "would spend tool contacts on material no arm may read. This is a "
                        "deliberate difference from the SLURP pass, whose own preregistration "
                        "named both families"
                    ),
                },
                "dimensions": ["label", "prior"],
                "facet_count": len(snapshot.facets) - len(content_facets),
                "reason": (
                    "label / prior facets are recalled by prior mass and exact-key agreement, "
                    "never by vector similarity"
                ),
            },
            "storage": {
                "dtype": "float32",
                "arrays": ["vectors", "ids", "text_sha256"],
                "normalization_applied_by_this_pass": "none",
                "note": (
                    "vectors are stored EXACTLY as the pinned llama.cpp server returned them. "
                    "text_sha256[i] is SHA-256 over the UTF-8 bytes of the exact text embedded "
                    "into row i, so a consumer can re-verify the pairing without the snapshot."
                ),
            },
            "embedder": {
                "role": "pinned TOOL-level embedder (frozen tool-level retriever clause); never the frozen core",
                "lock_key": EMBEDDER_LOCK_KEY,
                "lock_revision": EMBEDDER_REVISION,
                "gguf_relpath": EMBEDDER_RELPATH,
                "gguf_sha256": measured,
                "dims": EMBEDDER_DIM,
                "binary_path": llama_cpp["binary_path"],
                "binary_sha256": llama_cpp["binary_sha256"],
                "build_commit": llama_cpp["build_commit"],
                "server_argv": list(session.argv),
                "server_props": props_summary,
                "session_id": session.session_id,
                "session_pid": session.pid,
                "port": EMB_PORT,
                "gpu_layers": 0,
                "cpu_only": True,
            },
            "encode_only_check": {
                "pinned_modules": list(report.checked_modules),
                "runner_source": str(own_source),
                "runner_source_sha256": sha256_file(own_source),
                "guard1_import": "PASS",
                "guard2_endpoint_strings": "PASS",
                "guard3_client_surface": "PASS",
                "guard4_payload_keys": "PASS on all %d request payloads" % counter["n"],
                "result": "PASS",
            },
            "jitter_pair": {
                "text_sha256": sha256_text(jitter_text),
                "text_source": "content facet %s representation" % content_facets[0].facet_id,
                "cosine": jitter_cosine,
                "bit_identical": bit_identical,
            },
            "accounting": {
                "embedding_tool_contacts": int(contacts["contact_count"]),
                "http_requests_guarded": counter["n"],
                "frozen_core_contacts": 0,
                "speech_audio_seconds": 0,
                "gpu_hours": 0.0,
                "gpu_hours_basis": "-ngl 0: nothing offloaded; the pass is CPU-only",
                "spawn_seconds": round(spawn_seconds, 3),
                "total_wall_seconds": round(total_seconds, 3),
                "throughput_texts_per_second": round(
                    len(ids) / max(facet_seconds, 1e-9), 4
                ),
            },
            "run_dir": str(run_dir),
        }
        manifest_path = SNAPSHOT_DIR / "embeddings-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        manifest_sha256 = sha256_file(manifest_path)
        log("wrote %s (sha256 %s)" % (manifest_path, manifest_sha256))

        receipt = {
            "schema": "saea-kb-text-embeddings-receipt-v1",
            "study": "speech-aware-evidence-acquisition",
            "carrier": "audio2tool",
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "generated_at": iso_now(),
            "exposure_ledger_row": RUN_ID,
            "manifest": {
                "artifact_relpath": "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/embeddings-manifest.json",
                "bytes": manifest_path.stat().st_size,
                "sha256": manifest_sha256,
            },
            "snapshot": manifest["snapshot"],
            "vectors": manifest["embedded"],
            "not_embedded": manifest["not_embedded"],
            "embedder": manifest["embedder"],
            "encode_only_check": manifest["encode_only_check"],
            "jitter_pair": manifest["jitter_pair"],
            "accounting": manifest["accounting"],
            "storage": manifest["storage"],
            "run_dir": str(run_dir),
        }
        receipt_path = REPO / "docs" / "receipts" / "knowledge" / "a2t-kb-size-full-embeddings.json"
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        log("wrote %s" % receipt_path)
        outcome = {
            "status": "COMPLETED",
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_sha256,
            "receipt_path": str(receipt_path),
            "content_facet_npz_sha256": manifest["embedded"]["content_facets"]["sha256"],
        }
    finally:
        if session is not None:
            try:
                stop = stop_session(
                    session,
                    runtime_receipt=runtime_receipt,
                    runtime_root=RUNTIME_ROOT,
                    receipt_path=run_dir / "session-qwen3-emb-cpu.stop-receipt.json",
                    force_after_timeout=True,
                )
                log(
                    "embedder session stopped: %s (forced=%s)"
                    % (stop["termination_signal"], stop["forced"])
                )
                outcome["session_stop"] = stop
            except Exception as error:  # noqa: BLE001 -- teardown must report, never mask
                log("TEARDOWN FAILURE: %r" % (error,))
                outcome["session_stop_error"] = repr(error)
        after = decoder_fingerprint()
        untouched = (
            before.get("server_log_bytes") == after.get("server_log_bytes")
            and before.get("server_log_sha256") == after.get("server_log_sha256")
        )
        log("resident A2T decoder untouched: %s" % untouched)
        outcome["resident_decoder"] = {
            "before": before,
            "after": after,
            "untouched": untouched,
        }
        (run_dir / "outcome.json").write_text(
            json.dumps(outcome, indent=1, sort_keys=True, default=str), encoding="utf-8"
        )
        log("outcome: %s" % outcome["status"])
        log.close()
    return 0 if outcome["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
