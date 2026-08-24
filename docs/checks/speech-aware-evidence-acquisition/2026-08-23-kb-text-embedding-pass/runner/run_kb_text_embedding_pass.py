"""SAEA-SN-TOOL-KB-TEXT-EMB-PASS -- text-embedding pass over the frozen
KB-BUILD ``size-full`` TRAIN knowledge snapshot.

DEV-100 campaign prep prerequisite #1
(``docs/readiness/2026-08-23-dev100-campaign-preregistration.md`` section 5.1;
owner rulings ``2026-08-23-knowledge-plane-baseline-rulings.md`` section 7's
revised sequence). Registered exposure row: ``SAEA-SN-TOOL-KB-TEXT-EMB-PASS``.

What this embeds, and what it deliberately does not:

* every ``dimension == "content"`` KeyFacet's ``representation`` text (11,514)
* every ValueBundle's ``content`` text (11,514)
* label / prior / speaker facets get NO vectors -- they are recalled by prior
  mass and exact-key agreement, never by vector similarity.

Charter binding: the embedder is a PINNED TOOL-level model, never the frozen
core. It is reached only through ``rails.embedding_client.EmbeddingClient``,
whose encode-only surface is proven fail-closed by
``rails.encode_only_check`` BEFORE the server is spawned (source guards over
the pinned module set AND over this runner's own source) and again on the live
client object; every single request payload is additionally swept for
sampling/generation-shaped keys on the real wire path.

Serving discipline: CPU-ONLY (``-ngl 0``) on loopback port 8082, in its own
receipt-bound session with its own log. The resident q4km decoder (port 8080)
is never contacted, probed, restarted, or reconfigured; its own server log's
byte length and sha256 are captured before and after this pass as the proof.

Storage discipline: vectors are stored EXACTLY as the server returns them.
This pass applies no normalization of its own (the pinned llama.cpp server
returns L2-normalized pooled vectors by default; the measured norm range is
recorded in the manifest so a consumer can decide for itself).
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

# ---------------------------------------------------------------------------
# Environment armour (memory rules: literal PYTHONPATH + package-__file__
# assertion, never a hijacked editable install; no bytecode under the frozen
# scoring package).
# ---------------------------------------------------------------------------

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
UMBRELLA = REPO.parent.parent
RUN_ID = "SAEA-SN-TOOL-KB-TEXT-EMB-PASS"
EMB_PORT = 8082
RESIDENT_DECODER_PORT = 8080
RESIDENT_DECODER_PID = 607
RESIDENT_DECODER_LOG = Path(
    "/home/chao/runs/services/SAEA-SN-Q4KM-NP16-HOT-PREFIX-ZCOPY-20260823T111700Z/server.log"
)

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required (bytecode under the frozen package closes the D3 gate)")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit(f"PYTHONPATH must contain the literal {REPO / 'src'}")

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

_pkg_file = Path(_pkg.__file__ or "")
if _pkg_file != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit(f"package resolves to {_pkg_file}, not the main checkout (hijacked install)")

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
    PINNED_ENCODE_ONLY_MODULE_NAMES,
    assert_client_surface_is_encode_only,
    assert_module_never_imports_generation_client,
    assert_payload_has_no_forbidden_keys,
    assert_source_has_no_forbidden_endpoint_strings,
    run_encode_only_machine_check,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402

DATA_ROOT = Path(os.environ["SPEECHRL_DATA_DIR"])
RUNTIME_ROOT = Path(os.environ.get("LLAMA_RUNTIME_ROOT", "/home/chao"))
SNAPSHOT_DIR = DATA_ROOT / "knowledge/slurp/saea-kb-distmodel-v1/size-full"
SNAPSHOT_PATH = SNAPSHOT_DIR / "snapshot.json"

# Pinned identity (umbrella docs/datasets.lock.json -> models[qwen3-embedding-0.6b-gguf]).
EMBEDDER_LOCK_KEY = "qwen3-embedding-0.6b-gguf"
EMBEDDER_RELPATH = "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"
EMBEDDER_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
EMBEDDER_REVISION = "370f27d7550e0def9b39c1f16d3fbaa13aa67728"
EMBEDDER_DIM = 1024

# The committed runtime receipt whose llama_cpp block pins the binary this pass
# spawns. Its gguf_files describe the DECODER and are replaced below by this
# embedder's own single file (the pemb3m `embedder_runtime_receipt` pattern).
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"

# E-1 Mission C recipe + the pemb3m batch-geometry amendment, with -ngl 0
# substituted for -ngl 999: one pooled sequence per request must fit in one
# physical batch, and nothing is offloaded so the resident decoder's VRAM is
# never contested. -t 16 leaves 8 of the 24 host cores free for a concurrent
# CPU preprocessing sidecar.
SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
    "-b", "4096", "-ub", "4096", "-np", "1", "-t", "16",
)

SNAPSHOT_CONTENT_SHA256 = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"


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
        line = f"[{iso_now()}] {message}"
        print(line, flush=True)
        self._handle.write(line + "\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


def decoder_fingerprint() -> dict[str, object]:
    """Everything needed to prove the resident decoder was never touched."""

    record: dict[str, object] = {
        "pid": RESIDENT_DECODER_PID,
        "port": RESIDENT_DECODER_PORT,
        "observed_at": iso_now(),
    }
    try:
        stat = RESIDENT_DECODER_LOG.stat()
        record["server_log_path"] = str(RESIDENT_DECODER_LOG)
        record["server_log_bytes"] = stat.st_size
        record["server_log_mtime"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        record["server_log_sha256"] = sha256_file(RESIDENT_DECODER_LOG)
    except OSError as error:
        record["server_log_error"] = str(error)
    try:
        proc = subprocess.run(
            ["ps", "-o", "pid=,lstart=,etime=,args=", "-p", str(RESIDENT_DECODER_PID)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        record["ps"] = proc.stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        record["ps_error"] = str(error)
    return record


def guarded_post(timeout_seconds: float, counter: dict[str, int]):
    """The wire-path POST the embedding client is constructed with.

    Guard 4 of the encode-only check runs on EVERY request body, not merely
    the first: a sampling/generation-shaped key anywhere at any depth raises
    before the bytes leave this process.
    """

    def post(url: str, body: bytes) -> bytes:
        assert_payload_has_no_forbidden_keys(
            json.loads(body.decode("utf-8")), context=f"request#{counter['n']}"
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
    attempt_id = f"attempt-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-kbtxemb"
    if preflight_only:
        attempt_id += "-preflight"
    run_dir = DATA_ROOT / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log = Logger(run_dir / "runner.log")
    log(f"{RUN_ID} / {attempt_id}")
    log(f"run dir: {run_dir}")
    log(f"python: {sys.executable}")
    log(f"package: {_pkg_file}")

    # ---- gate (a): encode-only structural check, BEFORE any spawn ---------
    report = run_encode_only_machine_check()
    log(f"encode-only sweep PASS over pinned modules: {list(report.checked_modules)}")
    own_source = Path(__file__).resolve()
    assert_module_never_imports_generation_client(own_source)
    assert_source_has_no_forbidden_endpoint_strings(own_source)
    log(f"encode-only guards 1+2 PASS over this runner's own source: {own_source}")

    # ---- gate (b): snapshot identity -------------------------------------
    snapshot_file_sha256 = sha256_file(SNAPSHOT_PATH)
    document = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot = KnowledgeSnapshot.from_frozen_json(document)
    content_hash = snapshot.content_hash()
    if content_hash != SNAPSHOT_CONTENT_SHA256:
        raise SystemExit(
            f"snapshot content hash {content_hash} != pinned {SNAPSHOT_CONTENT_SHA256}"
        )
    log(f"snapshot {snapshot.snapshot_id}: content hash {content_hash} VERIFIED "
        f"(file sha256 {snapshot_file_sha256}, {len(snapshot.facets)} facets, {len(snapshot.values)} values)")

    content_facets = [f for f in snapshot.facets if f.dimension == "content"]
    values = list(snapshot.values)
    log(f"embed targets: {len(content_facets)} content facets + {len(values)} values "
        f"= {len(content_facets) + len(values)} texts")
    for facet in content_facets:
        if facet.representation_kind != "text":
            raise SystemExit(f"content facet {facet.facet_id} is not text-represented")

    # ---- gate (c): embedder identity -------------------------------------
    embedder_path = DATA_ROOT / EMBEDDER_RELPATH
    log(f"hashing pinned embedder {embedder_path} ...")
    measured = sha256_file(embedder_path)
    if measured != EMBEDDER_SHA256:
        raise SystemExit(f"embedder sha256 {measured} != umbrella-lock pin {EMBEDDER_SHA256}")
    log(f"embedder sha256 {measured} matches the umbrella lock pin")

    committed_runtime = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    llama_cpp = committed_runtime["llama_cpp"]
    runtime_receipt = {
        "llama_cpp": dict(llama_cpp),
        "gguf_files": [{"path": EMBEDDER_RELPATH, "sha256": measured}],
    }
    log(f"embedder runtime receipt: binary {llama_cpp['binary_path']} "
        f"sha256 {llama_cpp['binary_sha256']} build {llama_cpp['build_commit']}")

    # ---- gate (d): resident decoder fingerprint, BEFORE ------------------
    before = decoder_fingerprint()
    log(f"resident decoder BEFORE: log bytes={before.get('server_log_bytes')} "
        f"sha256={str(before.get('server_log_sha256'))[:16]}... ps={before.get('ps')!r}")

    if preflight_only:
        log("PREFLIGHT-ONLY: every pre-spawn gate PASSED; no server spawned, zero tool contacts")
        (run_dir / "outcome.json").write_text(
            json.dumps(
                {"status": "PREFLIGHT_PASS", "resident_decoder_before": before},
                indent=1, sort_keys=True, default=str,
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
        log(f"spawning CPU-only embedder session on port {EMB_PORT}: {list(SERVER_ARGS)}")
        spawn_started = time.time()
        session = start_session(
            runtime_root=RUNTIME_ROOT,
            data_root=DATA_ROOT,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=EMB_PORT,
            session_id=f"{RUN_ID}-{attempt_id}-qwen3-emb-cpu",
            extra_argv=list(SERVER_ARGS),
            receipt_path=run_dir / "session-qwen3-emb-cpu.receipt.json",
            server_log_path=run_dir / "session-qwen3-emb-cpu.server.log",
            ready_timeout_seconds=1800.0,
        )
        spawn_seconds = time.time() - spawn_started
        log(f"session up: pid={session.pid} port={session.port} (spawn+load {spawn_seconds:.1f}s)")
        log(f"session argv: {' '.join(session.argv)}")

        with urllib.request.urlopen(f"http://127.0.0.1:{EMB_PORT}/props", timeout=60) as response:
            props = json.loads(response.read().decode("utf-8"))
        props_summary = {
            key: props[key]
            for key in sorted(props)
            if key in ("pooling_type", "n_ctx", "n_batch", "n_ubatch", "model_path", "build_info", "total_slots")
        }
        log(f"server props: {json.dumps(props_summary, sort_keys=True)}")

        client = EmbeddingClient(
            base_url=f"http://127.0.0.1:{EMB_PORT}",
            post=guarded_post(600.0, counter),
            timeout_seconds=600.0,
            expected_dim=EMBEDDER_DIM,
            require_marker_verification=False,
        )
        assert_client_surface_is_encode_only(client)
        log("encode-only guard 3 PASS on the live client surface")
        client.verify_media_marker()

        # ---- jitter probe, session start ---------------------------------
        jitter_text = content_facets[0].representation
        jitter_start = client.embed_text(contact_id="jitter:start", text=jitter_text)
        log(f"jitter probe embedded at session start (dim {jitter_start.dims})")

        def embed_block(items, prefix: str, text_of, id_of, label: str):
            vectors = np.zeros((len(items), EMBEDDER_DIM), dtype=np.float32)
            ids: list[str] = []
            hashes: list[str] = []
            block_started = time.time()
            for index, item in enumerate(items):
                text = text_of(item)
                identifier = id_of(item)
                vector = client.embed_text(contact_id=f"{prefix}{identifier}", text=text)
                vectors[index] = np.asarray(vector.values, dtype=np.float32)
                ids.append(identifier)
                hashes.append(sha256_text(text))
                if (index + 1) % 500 == 0 or index + 1 == len(items):
                    elapsed = time.time() - block_started
                    rate = (index + 1) / elapsed if elapsed > 0 else 0.0
                    remaining = (len(items) - index - 1) / rate if rate > 0 else 0.0
                    log(f"{label}: {index + 1}/{len(items)} "
                        f"({rate:.2f} texts/s, ~{remaining / 60:.1f} min left)")
            return vectors, ids, hashes, time.time() - block_started

        facet_vectors, facet_ids, facet_hashes, facet_seconds = embed_block(
            content_facets, "cf:", lambda f: f.representation, lambda f: f.facet_id, "content facets"
        )
        value_vectors, value_ids, value_hashes, value_seconds = embed_block(
            values, "val:", lambda v: v.content, lambda v: v.value_id, "values"
        )

        # ---- jitter probe, session end -----------------------------------
        jitter_end = client.embed_text(contact_id="jitter:end", text=jitter_text)
        jitter_cosine = cosine(jitter_start.values, jitter_end.values)
        bit_identical = tuple(jitter_start.values) == tuple(jitter_end.values)
        log(f"jitter pair cosine = {jitter_cosine:.12f} (bit-identical: {bit_identical})")

        contacts = client.close()
        log(f"client closed: {contacts['contact_count']} embedding contacts")
        (run_dir / "contacts.json").write_text(
            json.dumps(contacts, indent=1, sort_keys=True), encoding="utf-8"
        )

        # ---- write vectors ------------------------------------------------
        facet_npz = SNAPSHOT_DIR / "vectors-content-facets.npz"
        value_npz = SNAPSHOT_DIR / "vectors-values.npz"
        np.savez(
            facet_npz,
            vectors=facet_vectors,
            ids=np.array(facet_ids),
            text_sha256=np.array(facet_hashes),
        )
        np.savez(
            value_npz,
            vectors=value_vectors,
            ids=np.array(value_ids),
            text_sha256=np.array(value_hashes),
        )
        log(f"wrote {facet_npz} ({facet_npz.stat().st_size} bytes)")
        log(f"wrote {value_npz} ({value_npz.stat().st_size} bytes)")

        def norm_stats(matrix: np.ndarray) -> dict[str, float]:
            norms = np.linalg.norm(matrix.astype(np.float64), axis=1)
            return {
                "min": float(norms.min()),
                "max": float(norms.max()),
                "mean": float(norms.mean()),
            }

        total_seconds = time.time() - started_pass
        manifest = {
            "schema": "saea-kb-text-embeddings-manifest-v1",
            "study": "speech-aware-evidence-acquisition",
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "generated_at": iso_now(),
            "authority": (
                "docs/readiness/2026-08-23-dev100-campaign-preregistration.md section 5.1 "
                "(prep prerequisite 1); owner rulings 2026-08-23-knowledge-plane-baseline-rulings.md "
                "section 7 revised sequence"
            ),
            "snapshot": {
                "snapshot_id": snapshot.snapshot_id,
                "artifact_relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-full/snapshot.json",
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
                    "count": len(facet_ids),
                    "dims": EMBEDDER_DIM,
                    "sha256": sha256_file(facet_npz),
                    "bytes": facet_npz.stat().st_size,
                    "source_field": "KeyFacet.representation where dimension == 'content'",
                    "order": "snapshot facet order (filtered to dimension == 'content'), row i <-> ids[i]",
                    "wall_seconds": round(facet_seconds, 3),
                    "l2_norms": norm_stats(facet_vectors),
                },
                "values": {
                    "file": value_npz.name,
                    "count": len(value_ids),
                    "dims": EMBEDDER_DIM,
                    "sha256": sha256_file(value_npz),
                    "bytes": value_npz.stat().st_size,
                    "source_field": "ValueBundle.content",
                    "order": "snapshot value order, row i <-> ids[i]",
                    "wall_seconds": round(value_seconds, 3),
                    "l2_norms": norm_stats(value_vectors),
                },
            },
            "not_embedded": {
                "dimensions": ["label", "prior", "speaker"],
                "facet_count": len(snapshot.facets) - len(content_facets),
                "reason": (
                    "label / prior / speaker facets are recalled by prior mass and exact-key "
                    "agreement, never by vector similarity (DEV-100 preregistration section 5.1)"
                ),
            },
            "storage": {
                "dtype": "float32",
                "arrays": ["vectors", "ids", "text_sha256"],
                "normalization_applied_by_this_pass": "none",
                "note": (
                    "vectors are stored EXACTLY as the pinned llama.cpp server returned them. "
                    "That server L2-normalizes pooled embeddings by default, which the measured "
                    "l2_norms confirm; this pass adds no normalization of its own, so a consumer "
                    "that wants a different normalization applies it at the point of use. "
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
                "guard4_payload_keys": f"PASS on all {counter['n']} request payloads",
                "result": "PASS",
            },
            "jitter_pair": {
                "text_sha256": sha256_text(jitter_text),
                "text_source": f"content facet {content_facets[0].facet_id} representation",
                "cosine": jitter_cosine,
                "bit_identical": bit_identical,
                "note": (
                    "the SAME text embedded at session start and at session end. E-1 Mission C "
                    "measured GPU-side non-bit-exactness (cosine 0.999910) for this exact model; "
                    "this pass is CPU-served, so the pair is the declared tolerance evidence."
                ),
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
                    (len(facet_ids) + len(value_ids)) / max(facet_seconds + value_seconds, 1e-9), 4
                ),
            },
            "run_dir": str(run_dir),
        }
        manifest_path = SNAPSHOT_DIR / "embeddings-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        manifest_sha256 = sha256_file(manifest_path)
        log(f"wrote {manifest_path} (sha256 {manifest_sha256})")
        outcome = {
            "status": "COMPLETED",
            "manifest_path": str(manifest_path),
            "manifest_sha256": manifest_sha256,
            "manifest": manifest,
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
                log(f"embedder session stopped: {stop['termination_signal']} (forced={stop['forced']})")
                outcome["session_stop"] = stop
            except Exception as error:  # noqa: BLE001 -- teardown must report, never mask
                log(f"TEARDOWN FAILURE: {error!r}")
                outcome["session_stop_error"] = repr(error)
        after = decoder_fingerprint()
        log(f"resident decoder AFTER: log bytes={after.get('server_log_bytes')} "
            f"sha256={str(after.get('server_log_sha256'))[:16]}... ps={after.get('ps')!r}")
        untouched = (
            before.get("server_log_bytes") == after.get("server_log_bytes")
            and before.get("server_log_sha256") == after.get("server_log_sha256")
        )
        log(f"resident decoder untouched: {untouched}")
        outcome["resident_decoder"] = {
            "before": before,
            "after": after,
            "untouched": untouched,
        }
        (run_dir / "outcome.json").write_text(
            json.dumps(outcome, indent=1, sort_keys=True, default=str), encoding="utf-8"
        )
        log(f"outcome: {outcome['status']}")
        log.close()
    return 0 if outcome["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
