"""SAEA-SLURP-KU-S1-QUERY-EMBEDDING-V1 -- the draft-response ("Q-draft")
embedding pass for the SLURP consumption dimension.

WHAT THIS ARTIFACT IS, AFTER THE OWNER RULE OF 2026-09-06
---------------------------------------------------------

This pass was commissioned as cell KU-S1's pre-flight QUERY vectors. Before
it ran, the owner ruled -- binding, 2026-09-06 -- that **the retrieval query
must contain the speech signal**: it may be speech, or speech plus an agent
intermediate state (speech + the draft answer), but it can never be
text-only. These vectors embed response TEXT. They are therefore **NOT**
cell KU-S1's query vectors, and that cell's ``query_source`` is deliberately
left un-closed until MF-7 fixes a speech-containing embedder.

What they ARE, and why the pass still ran:

1. the **Q-draft** arm of the MF-7 retrieval-key audit -- the text-only
   baseline every speech-carrying key is measured against. MF-7 reads this
   exact file (``vectors/slurp-ku-s1/query-vectors.jsonl``) and this exact
   receipt; the path and the hash are stable and citable.
2. the **STATE half** of a future ``speech+state`` fusion: if MF-7's
   decision table picks the fused form, the state component is the row's own
   draft answer, which is precisely what is embedded here.

Everything below describes how the vectors were produced. It does not
authorize using them as a flight query.

Why a pre-flight pass at all, and what it is NOT
------------------------------------------------

The DEV-1000 BLEND lock did not embed the query. It embedded, IN FLIGHT and
one tool contact per row, **the trajectory's own direct-decode response
text** (``RuntimeEmbeddedBlendController.advance`` ->
``LazyQueryVector.fill``). Enabler E6's ``phase_supply`` config seam ships
only the ``sealed-vectors`` kind and refuses ``embedding-server`` by name:
a pre-flight file can be hashed, pinned in the config and re-verified at
preflight, which is what makes a supplied cell reproducible, whereas an
in-flight sidecar is a second serving geometry, an ExecutionPlan tool clause
and one ledger row per contact that the config seam does not own.

So this pass reproduces the lock's own SIGNAL FAMILY from SEALED bytes: it
embeds, once each, the 1,000 phase-1 ("draft") response texts of the sealed
KU-S1c run ``SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1``. Those are the
closest sealed stand-in for a KU-S1 phase-1 answer -- same phase-program
path through ``rails.phase_runner``, same byte-identical closed-list system
message, same static phase-1 directive (``probes/slurp_phase_direct.txt``,
which KU-S1's own ``direct`` phase reuses unchanged).

Two things this signal is not, stated rather than hidden. It is **text-only**,
which the 2026-09-06 owner rule forbids as a retrieval query. And even as a
state component it cannot see a future flight's OWN phase-1 answer: it is a
different run's answer to the same question for the same row. The alternative
signal considered and NOT chosen is recorded in the receipt.

What is read, and what is not
-----------------------------

Exactly two fields per row of the sealed phases file: the sample id and the
model's own response text. No gold, no reference transcript, no SLURP devel
sentence text, no audio, no other run's material. The sealed run manifest's
sha256 and the phases file's sha256 are both verified against the pins the
KU-S1c verdict recorded BEFORE a single response text is read.

Charter binding: the embedder is a PINNED TOOL-level model, never the frozen
core. It is reached only through ``rails.embedding_client.EmbeddingClient``,
whose encode-only surface is proven fail-closed by ``rails.encode_only_check``
BEFORE the server is spawned (source guards over the pinned module set AND
over this script's own source) and again on the live client object; every
request payload is additionally swept for sampling/generation-shaped keys on
the real wire path.

Serving discipline: CPU-ONLY (``-ngl 0``) on loopback port 8082, in its own
receipt-bound session with its own log, at ``-t 6`` rather than the 2026-08-24
KB pass's ``-t 16`` because a GPU flight owns the host while this runs. No
GPU server is spawned, contacted, probed or reconfigured; the live
``llama-server`` process list is captured before and after as the proof.

Storage discipline: vectors are written EXACTLY as the server returns them
(the pinned llama.cpp server returns L2-normalized pooled vectors by
default; the measured norm range is recorded in the receipt). No
normalization and no rounding are applied here.

Usage (WSL2, from the study repository root)::

    python scripts/slurp_ku_s1_query_embedding_pass.py --preflight-only
    python scripts/slurp_ku_s1_query_embedding_pass.py
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO = Path(__file__).resolve().parents[1]
RUN_ID = "SAEA-SLURP-KU-S1-QUERY-EMBEDDING-V1"
EMB_PORT = 8082

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit(
        "PYTHONDONTWRITEBYTECODE=1 is required (bytecode under the frozen "
        "package closes the D3 gate)"
    )
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

_pkg_file = Path(_pkg.__file__ or "")
if _pkg_file != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit(
        "package resolves to %s, not this checkout (hijacked install)" % (_pkg_file,)
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

DATA_ROOT = Path(os.environ["SPEECHRL_DATA_DIR"])
RUNTIME_ROOT = Path(os.environ.get("LLAMA_RUNTIME_ROOT", "/home/chao"))

# ---------------------------------------------------------------------------
# The SEALED source: KU-S1c's phase-1 responses.
# ---------------------------------------------------------------------------

SOURCE_RUN_ID = "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1"
SOURCE_ATTEMPT_ID = "attempt-20260906T042946Z-44720f"
SOURCE_DIR = DATA_ROOT / "runs" / SOURCE_RUN_ID / SOURCE_ATTEMPT_ID
SOURCE_MANIFEST = SOURCE_DIR / ("%s.run-manifest.json" % SOURCE_RUN_ID)
SOURCE_PHASES = SOURCE_DIR / ("%s.phases.json" % SOURCE_RUN_ID)

#: docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-verdict.md section 5
#: ("seal | run manifest sha256 1b5143aa...1a74d ... phases file f6ed3c14...4e63").
SOURCE_MANIFEST_SHA256 = (
    "1b5143aa1958a6dbdd16feaa13a09138275c9241175a1f4709175b71de11a74d"
)
SOURCE_PHASES_SHA256 = (
    "f6ed3c1495778f53ab660ec6f90b2360ab059aed98541b9947cefffffa264e63"
)
SOURCE_PHASE_NAME = "draft"
SOURCE_CONTROLLER_POLICY_ID = "phase-draft-revise-v1:draft"
SPLIT_IDENTITY_HASH = (
    "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
)
EXPECTED_ROWS = 1000

# ---------------------------------------------------------------------------
# The PINNED tool-level embedder (umbrella docs/datasets.lock.json).
# ---------------------------------------------------------------------------

EMBEDDER_LOCK_KEY = "qwen3-embedding-0.6b-gguf"
EMBEDDER_RELPATH = "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"
EMBEDDER_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
EMBEDDER_REVISION = "370f27d7550e0def9b39c1f16d3fbaa13aa67728"
EMBEDDER_DIM = 1024
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"

#: The 2026-08-24 KB pass's own geometry with ONE change: -t 6 instead of
#: -t 16, because a GPU flight owns the host while this pass runs.
SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
    "-b", "4096", "-ub", "4096", "-np", "1", "-t", "6",
)

#: Registered ceiling on this row's tool contacts (exposure ledger row
#: SAEA-SLURP-KU-S1-QUERY-EMBEDDING-V1): 1,000 query texts + 2 jitter probes
#: + 48 retry margin. Enforced fail-closed below, before every contact.
TOOL_CONTACT_CEILING = 1050

DIMENSION = "content"
OUTPUT_RELPATH = "vectors/slurp-ku-s1/query-vectors.jsonl"

RECEIPT_DIR = (
    REPO
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-06-slurp-ku-s1-vectors"
)
RECEIPT_PATH = RECEIPT_DIR / "query-vectors.json"

#: What this pass actually embedded, in English. It is deliberately NOT
#: copied into a fragment's ``query_source.embedded_signal``: under the owner
#: rule of 2026-09-06 a text-only signal is not a legal retrieval query, and
#: ``rails.phase_supply`` refuses one by name.
EMBEDDED_SIGNAL = (
    "TEXT-ONLY, and therefore NOT a legal retrieval query under the owner "
    "rule of 2026-09-06: "
    "the SEALED phase-1 ('draft') response text of each DEV-1000 row of run "
    "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1 (attempt "
    "attempt-20260906T042946Z-44720f, phases file sha256 f6ed3c14...264e63), "
    "embedded once before the flight by the pinned tool-level embedder "
    "qwen3-embedding-0.6b-gguf (Qwen3-Embedding-0.6B-Q8_0.gguf, sha256 "
    "06507c7b...e439, 1,024 dimensions, llama.cpp featcache 04ccc72a, "
    "--embedding --pooling last, -ngl 0, CPU only). This reproduces the SIGNAL "
    "the DEV-1000 BLEND lock recalled on -- a direct-decode answer's embedding "
    "-- from a SEALED prior run instead of in flight. KU-S1c's draft phase is "
    "the closest sealed stand-in for KU-S1's own phase 1: same phase-program "
    "path, same byte-identical closed-list system message, same static "
    "directive probes/slurp_phase_direct.txt. The one deviation, stated and "
    "not hidden: the pre-flight vector cannot see THIS flight's own phase-1 "
    "answer."
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
        self._handle = path.open("a", encoding="utf-8")

    def __call__(self, message: str) -> None:
        line = "[%s] %s" % (iso_now(), message)
        print(line, flush=True)
        self._handle.write(line + "\n")
        self._handle.flush()

    def close(self) -> None:
        self._handle.close()


class ContactMeter:
    """Fail-closed meter on this row's registered tool-contact ceiling."""

    def __init__(self, ceiling: int) -> None:
        self._ceiling = int(ceiling)
        self.charged = 0

    def charge(self, contact_id: str) -> None:
        if self.charged + 1 > self._ceiling:
            raise SystemExit(
                "tool-contact ceiling: the ledger row registers <= %d embedding "
                "contacts and %r would be number %d"
                % (self._ceiling, contact_id, self.charged + 1)
            )
        self.charged += 1


def port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1.0)
        return probe.connect_ex((host, port)) != 0


def llama_server_fingerprint() -> dict[str, object]:
    """Everything needed to prove no OTHER llama.cpp server was touched."""

    record: dict[str, object] = {"observed_at": iso_now()}
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
        record["pgrep_error"] = str(error)
    return record


def guarded_post(timeout_seconds: float, counter: dict[str, int]):
    """The wire-path POST the embedding client is constructed with.

    Guard 4 of the encode-only check runs on EVERY request body, not merely
    the first: a sampling/generation-shaped key anywhere at any depth raises
    before the bytes leave this process."""

    import urllib.request

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


def load_sealed_draft_responses(log) -> tuple[list[tuple[str, str]], str, str]:
    """``([(sample_id, draft response text)], manifest sha256, phases sha256)``.

    Reads TWO fields per row and nothing else. Both file hashes are verified
    against the pins the KU-S1c verdict recorded before any text is read."""

    measured_manifest = sha256_file(SOURCE_MANIFEST)
    if measured_manifest != SOURCE_MANIFEST_SHA256:
        raise SystemExit(
            "sealed run manifest %s hashes to %s, not the verdict's pin %s"
            % (SOURCE_MANIFEST, measured_manifest, SOURCE_MANIFEST_SHA256)
        )
    measured_phases = sha256_file(SOURCE_PHASES)
    if measured_phases != SOURCE_PHASES_SHA256:
        raise SystemExit(
            "sealed phases file %s hashes to %s, not the verdict's pin %s"
            % (SOURCE_PHASES, measured_phases, SOURCE_PHASES_SHA256)
        )
    log("sealed manifest and phases file BOTH hash to the KU-S1c verdict's pins")

    document = json.loads(SOURCE_PHASES.read_text(encoding="utf-8"))
    if document.get("run_id") != SOURCE_RUN_ID:
        raise SystemExit("phases file carries run_id %r" % (document.get("run_id"),))
    phases = document["phases"]
    matching = [
        phase
        for phase in phases
        if phase.get("controller_policy_id") == SOURCE_CONTROLLER_POLICY_ID
    ]
    if len(matching) != 1:
        raise SystemExit(
            "expected exactly one %r phase, found %d"
            % (SOURCE_CONTROLLER_POLICY_ID, len(matching))
        )
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for result in matching[0]["results"]:
        sample_id = str(result["sample_id"])
        text = str(result["final_response_text"])
        if sample_id in seen:
            raise SystemExit("duplicate sample id %r in the sealed phase" % sample_id)
        if not text.strip():
            raise SystemExit("sample %r has an empty sealed response" % sample_id)
        seen.add(sample_id)
        rows.append((sample_id, text))
    if len(rows) != EXPECTED_ROWS:
        raise SystemExit("sealed phase carries %d rows, expected %d" % (len(rows), EXPECTED_ROWS))
    lengths = sorted(len(text) for _, text in rows)
    log(
        "read %d (sample_id, draft response) pairs; response chars min %d / median "
        "%d / max %d. No gold, transcript or audio was opened"
        % (len(rows), lengths[0], lengths[len(lengths) // 2], lengths[-1])
    )
    return rows, measured_manifest, measured_phases


def main() -> int:
    preflight_only = "--preflight-only" in sys.argv
    attempt_id = "attempt-%s-kus1qemb" % datetime.now(tz=timezone.utc).strftime(
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
    log("encode-only guards 1+2 PASS over this script's own source: %s" % own_source)

    # ---- gate (b): the sealed source, hash-verified before it is read -----
    rows, measured_manifest, measured_phases = load_sealed_draft_responses(log)

    # ---- gate (c): embedder identity -------------------------------------
    embedder_path = DATA_ROOT / EMBEDDER_RELPATH
    measured_embedder = sha256_file(embedder_path)
    if measured_embedder != EMBEDDER_SHA256:
        raise SystemExit(
            "embedder sha256 %s != umbrella-lock pin %s"
            % (measured_embedder, EMBEDDER_SHA256)
        )
    log("embedder sha256 matches the umbrella lock pin")

    committed_runtime = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    llama_cpp = committed_runtime["llama_cpp"]
    runtime_receipt = {
        "llama_cpp": dict(llama_cpp),
        "gguf_files": [{"path": EMBEDDER_RELPATH, "sha256": measured_embedder}],
    }
    log(
        "embedder runtime receipt: binary %s build %s"
        % (llama_cpp["binary_path"], llama_cpp["build_commit"])
    )

    # ---- gate (d): the host's other servers, BEFORE -----------------------
    before = llama_server_fingerprint()
    log("llama-server processes BEFORE: %r" % (before.get("llama_server_processes"),))
    if not port_is_free("127.0.0.1", EMB_PORT):
        raise SystemExit("something already listens on 127.0.0.1:%d" % EMB_PORT)
    log("port %d is free" % EMB_PORT)

    output_path = DATA_ROOT / OUTPUT_RELPATH
    if output_path.exists():
        raise SystemExit("refusing to overwrite an existing %s" % output_path)

    if preflight_only:
        log("PREFLIGHT-ONLY: every pre-spawn gate PASSED; no server spawned, zero contacts")
        (run_dir / "outcome.json").write_text(
            json.dumps(
                {"status": "PREFLIGHT_PASS", "llama_server_before": before},
                indent=1, sort_keys=True, default=str,
            ),
            encoding="utf-8",
        )
        log.close()
        return 0

    counter = {"n": 0}
    meter = ContactMeter(TOOL_CONTACT_CEILING)
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
        log(
            "session up: pid=%s port=%s (spawn+load %.1fs)"
            % (session.pid, session.port, spawn_seconds)
        )

        import urllib.request

        with urllib.request.urlopen(
            "http://127.0.0.1:%d/props" % EMB_PORT, timeout=60
        ) as response:
            props = json.loads(response.read().decode("utf-8"))
        props_summary = {
            key: props[key]
            for key in sorted(props)
            if key
            in (
                "pooling_type",
                "n_ctx",
                "n_batch",
                "n_ubatch",
                "model_path",
                "build_info",
                "total_slots",
            )
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

        # ---- jitter probe, session start ---------------------------------
        jitter_text = rows[0][1]
        meter.charge("jitter:start")
        jitter_start = client.embed_text(contact_id="jitter:start", text=jitter_text)
        log("jitter probe embedded at session start (dim %d)" % jitter_start.dims)

        vectors = np.zeros((len(rows), EMBEDDER_DIM), dtype=np.float32)
        ids: list[str] = []
        hashes: list[str] = []
        block_started = time.time()
        for index, (sample_id, text) in enumerate(rows):
            contact_id = "query:%s" % sample_id
            meter.charge(contact_id)
            vector = client.embed_text(contact_id=contact_id, text=text)
            values = np.asarray(vector.values, dtype=np.float32)
            if values.shape != (EMBEDDER_DIM,):
                raise SystemExit(
                    "sample %r returned %r components" % (sample_id, values.shape)
                )
            vectors[index] = values
            ids.append(sample_id)
            hashes.append(sha256_text(text))
            if (index + 1) % 100 == 0 or index + 1 == len(rows):
                elapsed = time.time() - block_started
                rate = (index + 1) / elapsed if elapsed > 0 else 0.0
                remaining = (len(rows) - index - 1) / rate if rate > 0 else 0.0
                log(
                    "query vectors: %d/%d (%.2f texts/s, ~%.1f min left)"
                    % (index + 1, len(rows), rate, remaining / 60.0)
                )
        embed_seconds = time.time() - block_started

        # ---- jitter probe, session end -----------------------------------
        meter.charge("jitter:end")
        jitter_end = client.embed_text(contact_id="jitter:end", text=jitter_text)
        jitter_cosine = cosine(jitter_start.values, jitter_end.values)
        bit_identical = tuple(jitter_start.values) == tuple(jitter_end.values)
        log("jitter pair cosine = %.12f (bit-identical: %s)" % (jitter_cosine, bit_identical))

        contacts = client.close()
        log("client closed: %s embedding contacts" % contacts["contact_count"])
        (run_dir / "contacts.json").write_text(
            json.dumps(contacts, indent=1, sort_keys=True), encoding="utf-8"
        )

        # ---- write the sealed-vectors JSONL -------------------------------
        # The line form is what rails.phase_supply.load_sealed_vectors reads
        # and it admits EXACTLY the keys "id" and "vectors" -- the row's
        # tool_contact_ledger_row / embedded_signal provenance lives in the
        # config fragment's query_source object and in this pass's receipt,
        # which is where that schema puts it.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="\n") as handle:
            for index, sample_id in enumerate(ids):
                components = [float(value) for value in vectors[index]]
                if any(not math.isfinite(value) for value in components):
                    raise SystemExit("row %s carries a non-finite component" % sample_id)
                handle.write(
                    json.dumps(
                        {"id": sample_id, "vectors": {DIMENSION: components}},
                        sort_keys=True,
                    )
                    + "\n"
                )
        output_sha256 = sha256_file(output_path)
        output_bytes = output_path.stat().st_size
        log(
            "wrote %s (%d bytes, sha256 %s)"
            % (output_path, output_bytes, output_sha256)
        )

        from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: PLC0415
            load_sealed_vectors,
        )

        table = load_sealed_vectors(
            output_path, expected_sha256=output_sha256, dimensions=(DIMENSION,)
        )
        if len(table) != len(ids):
            raise SystemExit(
                "reload produced %d rows, expected %d" % (len(table), len(ids))
            )
        max_abs_delta = 0.0
        for index, sample_id in enumerate(ids):
            restored = table[sample_id][DIMENSION]
            if len(restored) != EMBEDDER_DIM:
                raise SystemExit("reloaded row %s has width %d" % (sample_id, len(restored)))
            for position, value in enumerate(restored):
                delta = abs(value - float(vectors[index][position]))
                if delta > max_abs_delta:
                    max_abs_delta = delta
        if max_abs_delta != 0.0:
            raise SystemExit("round trip is not exact: max |delta| = %r" % (max_abs_delta,))
        log(
            "round trip through rails.phase_supply.load_sealed_vectors is EXACT "
            "(%d rows, max |delta| 0.0)" % len(table)
        )

        norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
        total_seconds = time.time() - started_pass
        receipt = {
            "schema": "saea-query-vector-pass-receipt-v1",
            "study": "speech-aware-evidence-acquisition",
            "carrier": "slurp",
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "exposure_ledger_row": RUN_ID,
            "execution_profile": "bounded-discovery-probe",
            "generated_at": iso_now(),
            "generator": "scripts/slurp_ku_s1_query_embedding_pass.py",
            "generator_sha256": sha256_file(own_source),
            "authority": (
                "docs/readiness/2026-09-06-slurp-consumption-ku-s1-v2-preregistration.md; "
                "enabler E6 (rails.phase_supply ships only the 'sealed-vectors' kind and "
                "refuses 'embedding-server' by name)"
            ),
            "purpose": (
                "One embedding tool contact per DEV-1000 row over the SEALED phase-1 "
                "('draft') response of KU-S1c. Commissioned as cell KU-S1's pre-flight "
                "query vectors and RE-SCOPED by the owner rule of 2026-09-06 before it "
                "ran; see owner_rule_2026_09_06 below for what this artifact now is."
            ),
            "owner_rule_2026_09_06": {
                "rule": (
                    "The retrieval QUERY must contain the speech signal. It may be "
                    "speech plus an agent intermediate state (for example the speech "
                    "plus the draft answer), but it can never be text-only."
                ),
                "consequence_for_this_artifact": (
                    "These vectors embed response TEXT and are therefore NOT cell "
                    "KU-S1's query vectors. configs/baseline/slurp-phase-blend-cl-v1.json "
                    "leaves phase_supply.evidence.query_source.sha256 at the 64-f "
                    "placeholder until MF-7 fixes a speech-containing embedder, and "
                    "rails.phase_supply now REFUSES any query_source whose "
                    "embedded_signal does not declare 'speech:' or 'speech+state:'."
                ),
                "roles_this_artifact_keeps": [
                    "the Q-draft (text-only) arm of the MF-7 retrieval-key audit, which "
                    "reads this exact path and this exact receipt",
                    "the STATE half of a future speech+state fusion, if MF-7's decision "
                    "table picks the fused form",
                ],
                "path_is_stable": (
                    "vectors/slurp-ku-s1/query-vectors.jsonl and this receipt keep their "
                    "paths so MF-7 (worktree wt-mf7) can cite them without a copy."
                ),
            },
            "embedded_signal": EMBEDDED_SIGNAL,
            "embedded_signal_modality": "text-only",
            "deviation_from_the_lock": (
                "The DEV-1000 BLEND lock embedded the trajectory's OWN direct answer IN "
                "FLIGHT (launch_dev1000_baseline_lock.py's RuntimeEmbeddedBlendController). "
                "This pass embeds a SEALED prior run's answer to the same question for the "
                "same row, before takeoff. Same embedder, same signal family, different "
                "provenance: a pre-flight vector cannot see a flight's own phase-1 answer. "
                "The lock's own recall signal was text-only too, which is exactly what the "
                "2026-09-06 owner rule now forbids as a retrieval query -- so this receipt "
                "records a property of the LOCK as much as of this pass."
            ),
            "alternative_not_chosen": {
                "candidate": (
                    "the sealed one-contact CLOSED-LIST direct baseline responses "
                    "(SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1, run manifest sha256 "
                    "f908ff4c7b0267322b34c7bf2ca9ad29d6db97ee8bb3cf18bf8824a057ebc94c)"
                ),
                "why_not": (
                    "those rows were produced by a policy:'fixed' one-contact arm whose "
                    "request carries NO phase control turn at all. KU-S1's own phase 1 is "
                    "a phase-program contact that sends probes/slurp_phase_direct.txt after "
                    "the audio, and the KU-S1c verdict measured that this control turn is "
                    "worth +1.2 of the +1.5 intent points that arm gained -- i.e. the two "
                    "populations of answers are measurably different. KU-S1c's draft phase "
                    "is the same program path, the same system message and the same static "
                    "directive KU-S1's phase 1 will send, so it is the closer stand-in. "
                    "Recorded so the choice is auditable rather than assumed."
                ),
            },
            "source": {
                "run_id": SOURCE_RUN_ID,
                "attempt_id": SOURCE_ATTEMPT_ID,
                "run_manifest_sha256": measured_manifest,
                "phases_file_sha256": measured_phases,
                "phase": SOURCE_PHASE_NAME,
                "controller_policy_id": SOURCE_CONTROLLER_POLICY_ID,
                "fields_read": ["sample_id", "final_response_text"],
                "fields_not_read": (
                    "everything else: no gold, no reference transcript, no SLURP devel "
                    "sentence text, no audio, no other run's material"
                ),
                "rows": len(rows),
                "split_identity_hash": SPLIT_IDENTITY_HASH,
                "split_role": "dev",
                "roster_receipt": "docs/receipts/probe-samples/DEV-1000.json",
            },
            "output": {
                "artifact_relpath": OUTPUT_RELPATH,
                "sha256": output_sha256,
                "bytes": output_bytes,
                "rows": len(table),
                "dims": EMBEDDER_DIM,
                "dimension": DIMENSION,
                "line_form": '{"id": "<sample id>", "vectors": {"content": [<1024 floats>]}}',
                "id_space": "DEV-1000 runtime-view sample ids (slurp:devel:<utt>:<recording>)",
                "round_trip": {
                    "reader": "rails.phase_supply.load_sealed_vectors",
                    "max_abs_delta_vs_server_response": 0.0,
                    "exact": True,
                },
                "text_sha256_first": hashes[0],
                "text_sha256_last": hashes[-1],
            },
            "storage": {
                "dtype_in_flight": "float32",
                "normalization_applied_by_this_pass": "none",
                "rounding_applied_by_this_pass": "none",
                "note": (
                    "vectors are written EXACTLY as the pinned llama.cpp server returned "
                    "them (that server L2-normalizes pooled embeddings by default, which "
                    "the measured norms confirm). Each float32 is widened to the exactly "
                    "equal Python float and serialised with the shortest decimal that "
                    "round-trips that double."
                ),
                "l2_norms": {
                    "min": float(norms.min()),
                    "max": float(norms.max()),
                    "mean": float(norms.mean()),
                },
            },
            "embedder": {
                "role": (
                    "pinned TOOL-level embedder (frozen tool-level retriever clause); "
                    "never the frozen core"
                ),
                "lock_key": EMBEDDER_LOCK_KEY,
                "lock_revision": EMBEDDER_REVISION,
                "gguf_relpath": EMBEDDER_RELPATH,
                "gguf_sha256": measured_embedder,
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
                "threads": 6,
                "threads_note": (
                    "-t 6, not the 2026-08-24 KB pass's -t 16: a GPU flight owns the host "
                    "while this pass runs and the CPU budget is shared."
                ),
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
                "text_source": "sealed draft response of %s" % ids[0],
                "cosine": jitter_cosine,
                "bit_identical": bit_identical,
                "note": (
                    "the SAME text embedded at session start and at session end; the pass "
                    "is CPU-served, so this pair is the declared tolerance evidence."
                ),
            },
            "accounting": {
                "embedding_tool_contacts": int(contacts["contact_count"]),
                "embedding_tool_contacts_charged": meter.charged,
                "registered_tool_contact_ceiling": TOOL_CONTACT_CEILING,
                "http_requests_guarded": counter["n"],
                "frozen_core_contacts": 0,
                "speech_audio_seconds": 0,
                "gpu_hours": 0.0,
                "gpu_hours_basis": "-ngl 0: nothing offloaded; the pass is CPU-only",
                "gold_reads": 0,
                "paid_api_spend": 0,
                "spawn_seconds": round(spawn_seconds, 3),
                "embed_seconds": round(embed_seconds, 3),
                "total_wall_seconds": round(total_seconds, 3),
                "throughput_texts_per_second": round(
                    len(ids) / max(embed_seconds, 1e-9), 4
                ),
            },
            "run_dir": str(run_dir),
        }
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        RECEIPT_PATH.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        log("wrote %s" % RECEIPT_PATH)
        outcome = {
            "status": "COMPLETED",
            "output_path": str(output_path),
            "output_sha256": output_sha256,
            "receipt_path": str(RECEIPT_PATH),
            "embedding_tool_contacts": meter.charged,
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
        after = llama_server_fingerprint()
        outcome["llama_server"] = {"before": before, "after": after}
        log("llama-server processes AFTER: %r" % (after.get("llama_server_processes"),))
        (run_dir / "outcome.json").write_text(
            json.dumps(outcome, indent=1, sort_keys=True, default=str), encoding="utf-8"
        )
        log("outcome: %s" % outcome["status"])
        log.close()
    return 0 if outcome["status"] == "COMPLETED" else 1


if __name__ == "__main__":
    sys.exit(main())
