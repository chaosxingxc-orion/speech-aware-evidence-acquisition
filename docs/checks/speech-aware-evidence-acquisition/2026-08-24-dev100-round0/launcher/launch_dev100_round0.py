"""DEV-100 campaign ROUND 0 launcher — exposure row
``SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN`` (bounded-discovery-probe).

Two arms over the same 100 DEV-100 packets, flown through
``rails.runner.run_speech_native_agent_loop`` on the ``openjiuwen-workflow-v1``
executor against the FRESH resident np8 zero-copy decoder service
(amendment 5b serving identity; composed config hash pinned below):

* **Arm M0** — plain direct decode, exactly 1 contact/sample (100 contacts):
  the registered chain's own degenerate direct-decode-only mode
  (``KbAlphaBlendController(snapshot=None, ...)`` — the same lawful path the
  module's default registry entry takes), so the M0 contact is byte-identical
  in shape to the BLEND arm's first contact.
* **Arm BLEND** — the registered C3 chain ``saea-kb-alpha-blend-v1``
  (+ ``saea-rank-wcos-prior-agree-v1``, ``saea-fuse-supplyfilter-v1``) at the
  round-0 knobs (alpha 0.60, tau 0.5, top-k 5, fusion m5/c2/l3, rank weights
  w_cos .5 / w_prior .3 / w_agree .2, TRAIN priors). The content-dimension
  query vector is the trajectory's OWN direct-decode answer text, embedded at
  runtime through the pinned ``qwen3-embedding-0.6b-gguf`` tool served
  CPU-ONLY on port 8082 — injected caller-side through the module's own
  vector-injection seam (``query_vectors_by_sample``), which is exactly the
  contract ``rails.kb_policy``'s docstring declares ("every vector this
  module consumes ... is INJECTED by the caller"). KB facet vectors come from
  the landed content-facet npz; VALUE VECTORS STAY SEALED (never loaded).
  Percept admission is facet-side (the fuser's own construction).

Round discipline carried from the preregistration (including amendment 5b):

* Gold opens SCORING-SIDE ONLY after ALL round arms complete: the runner's
  own per-loop seal-before-score is deliberately deferred one level further —
  the adapter handed to the runner returns a ``scoring_deferred`` marker and
  reads NO gold; the real ``SlurpAdapter.score`` runs in-process only after
  both arms (and the resend) have sealed.
* One identical-prompt resend pair (the pcorrf divergence lesson): after both
  arms, a 1-sample micro-run of the SAME degenerate M0 controller re-issues a
  byte-identical direct-decode prompt (same assembly code path, same frozen
  inputs) and the response pair is recorded as sha256 equality only. The
  resend is skipped, honestly and loudly, only if the round's 300-contact
  core ceiling has no headroom left.
* The server ``-np`` (8) is recorded; the round report carries per-arm
  accuracy, W->C / C->W sample-id lists, spend vs ceilings, and the
  NOT_AVAILABLE-tolerant serving descriptives.

The resident decoder is NEVER stopped by this launcher (it stays up for
round 1); the embedding sidecar gets its own session AND stop receipt.

Encode-only scope note, recorded honestly: the source-level guards 1/2 of
``rails.encode_only_check`` are scoped to embedding-only runners and are NOT
run over this launcher's own source — this launcher legitimately constructs
``FrozenCoreClient`` (a generation client) for the frozen-core arms, which is
what those guards exist to refuse in an embedding-only context. The embedding
CHANNEL keeps its full protection: the pinned-module structural sweep
(guard set a), the live-client surface check (guard 3), and the per-request
payload sweep (guard 4) all run.

Run in WSL2 (background live wrapper)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \
      python docs/checks/.../launcher/launch_dev100_round0.py
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import sys
import threading
import time
from collections.abc import Sequence as AbcSequence
from dataclasses import replace as dataclass_replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit(f"PYTHONPATH must contain the literal {REPO / 'src'}")

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if Path(_pkg.__file__ or "") != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit(f"package resolves to {_pkg.__file__}, not the main checkout")

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.base import TRANSPORTS, Registry  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose  # noqa: E402
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.resources import (  # noqa: E402
    resolve_resource_sampler,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    attach_session,
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp import (  # noqa: E402
    SLURP_LOCK_KEY,
    SlurpAdapter,
    SlurpSample,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.embedding_client import (  # noqa: E402
    EmbeddingClient,
)
from speech_aware_evidence_acquisition.rails.encode_only_check import (  # noqa: E402
    assert_client_surface_is_encode_only,
    assert_payload_has_no_forbidden_keys,
    run_encode_only_machine_check,
)
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    CONTROLLER_POLICY_ID,
    FuseKnobs,
    KbAlphaBlendController,
    RankWeights,
    default_label_normalizer,
    fuse_supplyfilter_factory,
    make_kb_alpha_blend_controller_factory,
    rank_wcos_prior_agree_factory,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    run_speech_native_agent_loop,
)

# --------------------------------------------------------------------------
# Pinned identity (campaign row + amendment 5b + landed receipts).
# --------------------------------------------------------------------------

RUN_ID = "SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"
ROUND_INDEX = 0
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np8-zcopy-speech-query-prefix-max64"
DATASET_FRAGMENT = "slurp-speech-native-dev100"
BASELINE_FRAGMENT = "slurp-dev100-kb-alpha-blend"
EXPERIMENT_FRAGMENT = "slurp-dev100-kb-alpha-blend-campaign-v1"
COMPOSED_CONFIG_SHA256 = "5397ea3ead594409b440ed9d8abc3690f6230d8b357207eb509977e411405944"
SPLIT_ID = "DEV-100"
SPLIT_IDENTITY_HASH = "e9a7b7febcf4fe3dc228370f7487e1e75dea3d63d447a07fbfe87c1404e2d853"
RUNTIME_VIEW_SHA256 = "9c7fe959ab0a258de97094a5edeb17da88de95965a093ea076deabe7a47220f7"
PROMOTION_RECEIPT_SHA256 = "8d2dc4dc9056ed604b22cbb66cd46724d3ee0246b6aca5665e6bfaf67cf0503d"
SNAPSHOT_SHA256 = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
RUNTIME_RECEIPT_RELPATH = (
    "receipts/runtime-q4km-mmproj-free-speech-batch-26802-singleton-zero-copy.json"
)
FEATURE_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
SESSION_DIR = Path(
    "/home/chao/runs/services/SAEA-SN-Q4KM-NP8-ZCOPY-DEV100-20260824T064416Z"
)
SESSION_RECEIPT_SHA256 = "555d69a9800ceb5f79c75c7cfd1dd3c64493264ab6bb8f2e18e7b8eb82a08b1b"
DECODER_PORT = 8080
EMB_PORT = 8082

# Embedder pins (umbrella lock qwen3-embedding-0.6b-gguf; the KB pass pins).
EMBEDDER_RELPATH = "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"
EMBEDDER_SHA256 = "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
EMBEDDER_DIM = 1024
EMBEDDER_RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"
EMB_SERVER_ARGS: tuple[str, ...] = (
    "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
    "-b", "4096", "-ub", "4096", "-np", "1", "-t", "16",
)

# Round-0 knobs (campaign fragment kb_campaign_round0_knobs; provenance ids
# rank_weight_id=rrf / evidence_variant=rank+prior+agreement name the sweep
# cell; the flown machinery is the FROZEN registered C3 chain).
ROUND0_ALPHA = 0.6
ROUND0_TAU = 0.5
ROUND0_TOP_K = 5
ROUND0_FUSE = FuseKnobs(tau=ROUND0_TAU, m=5, c=2, top_l=3)
ROUND0_WEIGHTS = RankWeights(w_cos=0.5, w_prior=0.3, w_agree=0.2)

# Round-0 ceilings (preregistration section 4 + campaign row).
ROUND_CORE_CEILING = 300
ROUND_TOOL_CEILING = 150
PLANNED_MODEL_CALLS = 300
PLANNED_AUDIO_SECONDS = 900
PLANNED_GPU_HOURS = 1.0

M0_POLICY_ID = "saea-direct-decode-only-m0"
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 64}

# GPU preflight facts (section 5.4), measured by the flight coordinator shell
# immediately before this launcher was started; re-verified below in-script.
GPU_PREFLIGHT = {
    "lenovo_smart_fan_mode": 3,
    "enforced_power_limit_w_at_preflight": 100.0,
    "measured_at": "2026-08-24T06:43Z (PowerShell, Windows host)",
}

OUT_CHECK_DIR = REPO / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-24-dev100-round0"


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)


def iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _port_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# Round adapter: DEV-100 runtime-view-filtered SLURP samples, scoring
# DEFERRED past the whole round (gold opens only after all arms seal).
# --------------------------------------------------------------------------


class RoundAdapter(SlurpAdapter):
    """SlurpAdapter filtered to the DEV-100 runtime view, with score()
    replaced by a gold-free deferral marker. ``load_split`` supports
    ``DEV-100`` (all 100) and ``DEV-100-RESEND-1`` (the first sample only,
    for the identical-prompt resend micro-run)."""

    def __init__(self, lock, root, *, repo_root, view_items) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._view_by_id = {item["sample_id"]: item for item in view_items}
        self._cache: dict[str, tuple[SlurpSample, ...]] = {}

    def load_split(self, split_id, **kwargs):  # noqa: D102
        if split_id not in ("DEV-100", "DEV-100-RESEND-1"):
            raise ValueError(f"RoundAdapter serves only DEV-100 views, not {split_id!r}")
        if "DEV-100" not in self._cache:
            records = load_slurp_split(self._lock, self._root, "devel")
            wanted = self._view_by_id
            picked = [record for record in records if record.sample_id in wanted]
            if len(picked) != len(wanted):
                missing = set(wanted) - {record.sample_id for record in picked}
                raise ValueError(f"devel split lacks view samples: {sorted(missing)[:5]}")
            samples = []
            for record in picked:
                item = wanted[record.sample_id]
                if record.media_relpath != item["media_relpath"]:
                    raise ValueError(f"media_relpath drift for {record.sample_id}")
                audio_ref = self._audio_ref(record.media_relpath)
                if audio_ref.sha256 != item["audio_sha256"]:
                    raise ValueError(f"audio bytes drift for {record.sample_id}")
                samples.append(
                    SlurpSample(
                        sample_id=record.sample_id,
                        audio_ref=audio_ref,
                        audio_seconds=record.audio_seconds,
                        utterance_id=record.utterance_id,
                        media_relpath=record.media_relpath,
                        scenario=record.scenario,
                        action=record.action,
                        intent=record.intent,
                        entities=record.entities,
                    )
                )
            self._cache["DEV-100"] = tuple(sorted(samples, key=lambda s: s.sample_id))
        full = self._cache["DEV-100"]
        if split_id == "DEV-100":
            return full
        return (full[0],)

    def score(self, sample, response):  # noqa: D102 — gold stays sealed in-round
        return {"scoring_deferred": True}


# --------------------------------------------------------------------------
# Runtime query-vector injection (the kb_policy caller-side seam).
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Direct-contact contract dedup (third-takeoff repair, 2026-08-24, zero
# spend). The registered chain's DIRECT contact re-renders the full task
# contract inside its instruction; the runner's protected-knowledge guard
# (rails.runner._assert_agent_control_excludes_knowledge_payloads) refused
# the very first wave because 7 TRAIN content-facet representations (short
# utterance texts such as "temperature" / "calendar" that also appear among
# the roster's example fillers) are substrings of that roster text. This is
# the SAME duplication class amendment 5b remedy 1 fixed for the EVIDENCE
# contact (commit 72096bad): the system message already carries the contract
# on every contact (rails.runner._agent_messages), so the wrapper below
# replaces the direct instruction's contract re-render with a reference —
# rendering fix only, applied caller-side without touching rails/; the model
# still sees the contract exactly once. The rewrite is a PURE dedup: it fires
# only when the instruction is byte-exactly the contract prefix + the known
# directive, and refuses (returns the plan unchanged, so the runner's guard
# still fail-closes) on anything else.
# --------------------------------------------------------------------------

DIRECT_DIRECTIVE = (
    "Answer using only the speech query; no external knowledge has been "
    "supplied yet."
)
DIRECT_REFERENCE_INSTRUCTION = (
    "Decide under the task contract already given above. " + DIRECT_DIRECTIVE
)
EVIDENCE_REFERENCE_INSTRUCTION = (
    "Decide under the task contract already given above, now "
    "considering the retrieved evidence. Answer using the speech "
    "query together with the supplied knowledge evidence."
)


def dedup_direct_contact(contact, task_contract: str):
    if getattr(contact, "contact_id", None) != "direct-decode":
        return contact
    if contact.instruction != f"{task_contract}\n{DIRECT_DIRECTIVE}":
        return contact
    return dataclass_replace(contact, instruction=DIRECT_REFERENCE_INSTRUCTION)


class DirectDedupController:
    """Delegating wrapper applying :func:`dedup_direct_contact` to the
    initial (direct-decode) contact. No other behaviour."""

    def __init__(self, inner) -> None:
        self._inner = inner

    def initial_contact(self, context):
        return dedup_direct_contact(
            self._inner.initial_contact(context), context.task_contract
        )

    def advance(self, context, contact, response_text):
        return self._inner.advance(context, contact, response_text)

    @property
    def last_winner_label(self):
        return getattr(self._inner, "last_winner_label", None)


class LazyQueryVector(AbcSequence):
    """Empty (len 0 -> cosine recall inert) until filled with the runtime
    embedding of the trajectory's own direct answer text."""

    def __init__(self) -> None:
        self._values: tuple[float, ...] | None = None

    def fill(self, values: Sequence[float]) -> None:
        if self._values is not None:
            raise RuntimeError("query vector already filled")
        self._values = tuple(float(v) for v in values)

    def __len__(self) -> int:
        return 0 if self._values is None else len(self._values)

    def __getitem__(self, index):
        if self._values is None:
            raise IndexError(index)
        return self._values[index]


class RuntimeEmbeddedBlendController:
    """Delegating wrapper: on the direct-decode response, embeds that text
    (ONE pinned-tool contact) into the injected content-dimension cell, then
    lets the REGISTERED controller advance. Adds no policy behaviour."""

    def __init__(self, inner, *, sample_id: str, cell: LazyQueryVector, embed) -> None:
        self._inner = inner
        self._sample_id = sample_id
        self._cell = cell
        self._embed = embed
        self._filled = False

    def initial_contact(self, context):
        return self._inner.initial_contact(context)

    def advance(self, context, contact, response_text):
        if (
            contact.contact_id == "direct-decode"
            and isinstance(response_text, str)
            and not self._filled
        ):
            vector = self._embed(self._sample_id, response_text)
            self._cell.fill(vector)
            self._filled = True
        return self._inner.advance(context, contact, response_text)

    @property
    def last_winner_label(self):
        return getattr(self._inner, "last_winner_label", None)


# --------------------------------------------------------------------------
# Embedding contact meter (round-0 tool sub-ceiling, fail-closed).
# --------------------------------------------------------------------------


class EmbeddingMeter:
    def __init__(self, ceiling: int, contact_log: Path) -> None:
        self.ceiling = ceiling
        self.count = 0
        self.latency_total = 0.0
        self._log = contact_log
        self._lock = threading.Lock()

    def charge(self, contact_id: str) -> None:
        with self._lock:
            if self.count + 1 > self.ceiling:
                raise RuntimeError(
                    f"embedding tool ceiling: round 0 registers <= {self.ceiling} "
                    f"contacts and {self.count} are already spent; refusing"
                )
            self.count += 1

    def record(self, contact_id: str, latency: float, dims: int, text_sha256: str) -> None:
        with self._lock:
            self.latency_total += latency
            with self._log.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "index": self.count,
                            "contact_id": contact_id,
                            "latency_seconds": round(latency, 4),
                            "dims": dims,
                            "text_sha256": text_sha256,
                        }
                    )
                    + "\n"
                )


def guarded_post(timeout_seconds: float):
    import urllib.request

    def post(url: str, body: bytes) -> bytes:
        assert_payload_has_no_forbidden_keys(json.loads(body.decode("utf-8")), context="emb-request")
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()

    return post


def main() -> int:
    attempt_id = f"attempt-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-dev100r0"
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"ROUND 0 launcher — {RUN_ID} / {attempt_id}")
    log(f"run dir: {run_dir}")

    flight: dict[str, object] = {
        "schema": "saea-dev100-round0-flight-v1",
        "run_id": RUN_ID,
        "round_index": ROUND_INDEX,
        "attempt_id": attempt_id,
        "started_at": iso_now(),
        "gpu_preflight": dict(GPU_PREFLIGHT),
    }

    def save_flight() -> None:
        (run_dir / "flight-state.json").write_text(
            json.dumps(flight, indent=1, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    save_flight()

    # ---- GPU preflight re-verification (power limit; fan mode is Windows) --
    import subprocess

    smi = subprocess.run(
        ["nvidia-smi", "--query-gpu=enforced.power.limit", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=30, check=True,
    )
    enforced_w = float(smi.stdout.strip().split()[0])
    if enforced_w < 95.0:
        raise SystemExit(f"GPU preflight: enforced power limit {enforced_w} W < 95 W")
    flight["gpu_preflight"]["enforced_power_limit_w_in_wsl"] = enforced_w
    log(f"GPU preflight: enforced power limit {enforced_w} W (>= 95), SmartFanMode 3 (host-recorded)")

    # ---- composition ------------------------------------------------------
    composed = compose(REPO, MODEL_FRAGMENT, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT)
    values = composed.values
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise SystemExit(
            f"composed config hash {composed.config_hash} != registered {COMPOSED_CONFIG_SHA256}"
        )
    server_args = list(values["server_args"])
    server_np = int(server_args[server_args.index("-np") + 1])
    if server_np != 8:
        raise SystemExit(f"composed -np is {server_np}, expected 8")
    log(f"composed config hash verified: {composed.config_hash} (-np {server_np})")
    flight["config_hash"] = composed.config_hash
    flight["server_np"] = server_np

    # ---- runtime view + promotion receipt ---------------------------------
    view = json.loads(
        (REPO / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json").read_text(encoding="utf-8")
    )
    if view["runtime_view_sha256"] != RUNTIME_VIEW_SHA256:
        raise SystemExit("runtime view sha256 drifted")
    if view["split_identity_hash"] != SPLIT_IDENTITY_HASH or view["count"] != 100:
        raise SystemExit("runtime view identity drifted")
    promotion_path = FEATURE_ROOT / "DEV-100-promotion.json"
    measured_promotion = sha256_file(promotion_path)
    if measured_promotion != PROMOTION_RECEIPT_SHA256:
        raise SystemExit(f"promotion receipt hashes to {measured_promotion}, not the pin")
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    if promotion.get("dataset_runtime_view_sha256") != RUNTIME_VIEW_SHA256:
        raise SystemExit("promotion receipt binds a different runtime view")
    log(f"DEV-100 promotion receipt verified ({measured_promotion[:12]}…)")

    # ---- knowledge snapshot + SEALED-value discipline ---------------------
    snapshot_path = root / "knowledge/slurp/saea-kb-distmodel-v1/size-full/snapshot.json"
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != SNAPSHOT_SHA256:
        raise SystemExit("knowledge snapshot content hash mismatch")
    log(f"TRAIN snapshot verified: {len(snapshot.facets)} facets / {len(snapshot.values)} values")

    emb_receipt = json.loads(
        (REPO / "docs" / "receipts" / "knowledge" / "slurp-kb-size-full-embeddings.json").read_text(
            encoding="utf-8"
        )
    )
    facet_block = emb_receipt["vectors"]["content_facets"]
    facet_npz_path = snapshot_path.parent / facet_block["file"]
    measured_npz = sha256_file(facet_npz_path)
    if measured_npz != facet_block["sha256"]:
        raise SystemExit("content-facet npz hash mismatch vs the landed receipt")
    npz = np.load(facet_npz_path)
    facet_ids = [str(v) for v in npz["ids"]]
    facet_matrix = npz["vectors"]
    if facet_matrix.shape != (len(facet_ids), EMBEDDER_DIM):
        raise SystemExit(f"unexpected facet vector shape {facet_matrix.shape}")
    log(
        f"content-facet vectors loaded: {facet_matrix.shape} ({measured_npz[:12]}…). "
        "VALUE VECTORS SEALED: vectors-values.npz is NOT loaded by this flight."
    )
    facet_vector_table: dict[str, Mapping[str, tuple[float, ...]]] = {}
    for index, facet_id in enumerate(facet_ids):
        facet_vector_table[facet_id] = {"content": tuple(facet_matrix[index].tolist())}

    def facet_vectors(facet_id: str) -> Mapping[str, tuple[float, ...]]:
        return facet_vector_table.get(facet_id, {})

    flight["knowledge"] = {
        "snapshot_sha256": SNAPSHOT_SHA256,
        "facet_vectors_npz_sha256": measured_npz,
        "value_vectors_loaded": False,
        "percept_admission": "facet-side (fuser construction)",
    }
    save_flight()

    # ---- samples (model-free; hashes only the 100 view files) -------------
    adapter = RoundAdapter(lock, root, repo_root=REPO, view_items=view["items"])
    log("loading the 100 DEV-100 samples (per-file sha256 against the view)")
    samples = adapter.load_split(SPLIT_ID)
    if len(samples) != 100:
        raise SystemExit(f"{len(samples)} samples, expected 100")
    one_pass_audio = sum(float(s.audio_seconds) for s in samples)
    log(f"samples verified: 100 ids, one metered pass = {one_pass_audio:.6f}s")

    packet_bindings: dict[str, dict[str, str]] = {}
    for item in view["items"]:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        packet_bindings[item["sample_id"]] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }
    if set(packet_bindings) != {s.sample_id for s in samples}:
        raise SystemExit("packet bindings do not cover the split")
    log("speech packet bindings materialized for all 100 samples")

    payload_binding = build_payload_binding(
        carrier_lock_key=SLURP_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=asset_dir(lock, SLURP_LOCK_KEY, root),
    )
    log("payload binding built (inputs complete, still pre-gate)")

    # ---- guard simulation: BOTH flown instructions vs protected material --
    # Runs the runner's own protected-material construction offline (model-
    # free) and refuses BEFORE takeoff if either reference-form instruction
    # would trip the knowledge-payload guard the third takeoff died on.
    from speech_aware_evidence_acquisition.rails.runner import (  # noqa: PLC0415
        _protected_knowledge_material,
    )

    protected = _protected_knowledge_material(snapshot)
    for name, text in (
        ("direct-reference", DIRECT_REFERENCE_INSTRUCTION),
        ("evidence-reference", EVIDENCE_REFERENCE_INSTRUCTION),
    ):
        hits = [m for m in protected if m in text.casefold()]
        if hits:
            raise SystemExit(
                f"guard simulation: {name} instruction embeds protected knowledge "
                f"payloads {hits[:3]!r}; refusing before takeoff"
            )
    log(
        "guard simulation PASS: both reference-form instructions are free of all "
        f"{len(protected)} protected knowledge payloads"
    )

    if "--preflight-only" in sys.argv:
        flight["outcome_status"] = "PREFLIGHT_ONLY_PASS"
        save_flight()
        log("PREFLIGHT-ONLY PASS: every input verified; zero contacts, no gate, no attach")
        return 0

    # ---- execution plan + FULL frozen-core gate ---------------------------
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=SLURP_LOCK_KEY,
        split_role="dev",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=PLANNED_MODEL_CALLS,
        planned_gpu_hours=PLANNED_GPU_HOURS,
        planned_speech_audio_seconds=PLANNED_AUDIO_SECONDS,
        protocol_hash=composed.config_hash,
        attempt_id=attempt_id,
    ).validate()
    (run_dir / "execution-plan.json").write_text(
        json.dumps(
            {
                "attempt_id": plan.attempt_id,
                "carrier_lock_key": plan.carrier_lock_key,
                "execution_profile": plan.execution_profile,
                "planned_gpu_hours": plan.planned_gpu_hours,
                "planned_model_calls": plan.planned_model_calls,
                "planned_speech_audio_seconds": plan.planned_speech_audio_seconds,
                "protocol_hash": plan.protocol_hash,
                "run_id": plan.run_id,
                "schema": "saea-execution-plan-v1",
                "split_identity_hash": plan.split_identity_hash,
                "split_role": plan.split_role,
                "study": "speech-aware-evidence-acquisition",
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path("/home/chao"),
        runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=str(values["model_lock_key"]),
    )
    log("running the FULL frozen-core gate (q4km GGUF attestation; minutes of I/O)")
    gate_started = time.time()
    lock_sha256 = gate.assert_model_touch_allowed(plan, full_hash=True)
    log(f"frozen-core gate PASS in {time.time() - gate_started:.1f}s (lock {lock_sha256[:12]}…)")
    flight["gate"] = {"umbrella_lock_sha256": lock_sha256, "seconds": round(time.time() - gate_started, 1)}
    save_flight()

    # ---- attach to the resident np8 service -------------------------------
    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    receipt_path = SESSION_DIR / "session-receipt.json"
    measured_receipt = sha256_file(receipt_path)
    if measured_receipt != SESSION_RECEIPT_SHA256:
        raise SystemExit(
            f"resident session receipt hashes to {measured_receipt}, not the registered "
            f"{SESSION_RECEIPT_SHA256}; the service was restarted or mutated"
        )
    session = attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=Path("/home/chao"))
    if list(session.argv) != [session.argv[0], "--host", "127.0.0.1", "--port", str(DECODER_PORT)] + [
        "-m", session.argv[6], "--no-mmproj"] + server_args:
        raise SystemExit("resident session argv does not match the np8 composition")
    log(f"attached to resident np8 session pid={session.pid} (receipt {measured_receipt[:12]}…)")
    flight["decoder_session"] = {
        "session_id": session.session_id,
        "pid": session.pid,
        "port": session.port,
        "receipt_sha256": measured_receipt,
        "np": server_np,
    }
    save_flight()

    transport = TRANSPORTS.resolve(str(values["transport"]))(
        values, root, session=session, runtime_receipt=runtime_receipt, runtime_root=Path("/home/chao")
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=payload_binding,
        arm="speech-feature-query",
        request_id_prefix="dev100r0",
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=packet_bindings,
    )
    log(f"FrozenCoreClient constructed (arm {client.arm})")

    # ---- embedding sidecar (own session + stop receipt) -------------------
    emb_report = run_encode_only_machine_check()
    log(f"encode-only structural sweep PASS: {list(emb_report.checked_modules)}")
    embedder_path = root / EMBEDDER_RELPATH
    measured_embedder = sha256_file(embedder_path)
    if measured_embedder != EMBEDDER_SHA256:
        raise SystemExit("embedder GGUF hash mismatch vs the umbrella lock pin")
    committed_pre = load_runtime_receipt(REPO / "docs" / EMBEDDER_RUNTIME_RECEIPT_RELPATH)
    emb_runtime_receipt = {
        "llama_cpp": dict(committed_pre["llama_cpp"]),
        "gguf_files": [{"path": EMBEDDER_RELPATH, "sha256": measured_embedder}],
    }
    if _port_reachable("127.0.0.1", EMB_PORT):
        raise SystemExit(f"something already listens on {EMB_PORT}")
    log(f"spawning CPU-only embedder sidecar on {EMB_PORT}: {list(EMB_SERVER_ARGS)}")
    emb_session = start_session(
        runtime_root=Path("/home/chao"),
        data_root=root,
        runtime_receipt=emb_runtime_receipt,
        host="127.0.0.1",
        port=EMB_PORT,
        session_id=f"{RUN_ID}-{attempt_id}-qwen3-emb-cpu",
        extra_argv=list(EMB_SERVER_ARGS),
        receipt_path=run_dir / "session-qwen3-emb-cpu.receipt.json",
        server_log_path=run_dir / "session-qwen3-emb-cpu.server.log",
        ready_timeout_seconds=900.0,
    )
    log(f"embedder sidecar up: pid={emb_session.pid} port={emb_session.port}")

    meter = EmbeddingMeter(ROUND_TOOL_CEILING, run_dir / "embedding-contacts.jsonl")
    emb_client = EmbeddingClient(
        base_url=f"http://127.0.0.1:{EMB_PORT}",
        post=guarded_post(600.0),
        timeout_seconds=600.0,
        expected_dim=EMBEDDER_DIM,
        require_marker_verification=False,
    )
    assert_client_surface_is_encode_only(emb_client)
    emb_client.verify_media_marker()
    embed_lock = threading.Lock()
    query_vector_log = run_dir / "query-vectors.jsonl"

    def embed_query_text(sample_id: str, text: str) -> tuple[float, ...]:
        contact_id = f"query:{sample_id}"
        with embed_lock:
            meter.charge(contact_id)
            started = time.time()
            vector = emb_client.embed_text(contact_id=contact_id, text=text)
            elapsed = time.time() - started
            meter.record(contact_id, elapsed, vector.dims, sha256_text(text))
            with query_vector_log.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "contact_id": contact_id,
                            "text_sha256": sha256_text(text),
                            "dims": vector.dims,
                            "values": list(vector.values),
                        }
                    )
                    + "\n"
                )
            return tuple(vector.values)

    # Jitter probe uses a snapshot facet REPRESENTATION (text), mirroring the
    # KB pass: the representation of the first content facet id.
    facet_repr_by_id = {
        facet.facet_id: facet.representation for facet in snapshot.facets
    }
    jitter_text = facet_repr_by_id[sorted(facet_vector_table)[0]]
    with embed_lock:
        meter.charge("jitter:start")
        t0 = time.time()
        jitter_start = emb_client.embed_text(contact_id="jitter:start", text=jitter_text)
        meter.record("jitter:start", time.time() - t0, jitter_start.dims, sha256_text(jitter_text))
    log("embedding sidecar verified (surface encode-only; jitter start embedded)")

    # ---- serving telemetry (NOT_AVAILABLE-tolerant) -----------------------
    sampler = resolve_resource_sampler(slots_url=f"http://127.0.0.1:{DECODER_PORT}/slots")
    sampler.start()
    sampler.begin_request_window()

    arm_results: dict[str, object] = {}
    winner_labels: dict[str, str | None] = {}
    outcome_status = "ABORTED"
    contact_total = 0
    flight_started = time.time()
    try:
        # ---------------- Arm M0 ----------------
        def m0_factory(sample_id: str):
            return DirectDedupController(
                KbAlphaBlendController(
                    snapshot=None,
                    query_vectors={},
                    facet_vectors=lambda facet_id: {},
                    normalizer=default_label_normalizer,
                    ranker=rank_wcos_prior_agree_factory(
                        RankWeights(w_cos=0.0, w_prior=0.0, w_agree=0.0)
                    ),
                    fuser=fuse_supplyfilter_factory(FuseKnobs(tau=1.0, m=1, c=1, top_l=1)),
                    alpha=0.5,
                    top_k_per_dimension=1,
                )
            )

        m0_registry = Registry("dev100 round0 M0 controller")
        m0_registry.register(M0_POLICY_ID, m0_factory)
        log("ARM M0 START: 100 direct-decode contacts")
        m0_buffer = TraceBuffer(plan.run_id)
        m0_started = time.time()
        m0_summary = run_speech_native_agent_loop(
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=client,
            split_id=SPLIT_ID,
            knowledge_snapshot=snapshot,
            speech_packet_bindings=packet_bindings,
            controller_policy_id=M0_POLICY_ID,
            max_contacts=1,
            slot_count=server_np,
            queue_depth=server_np,
            trace_sink=m0_buffer,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params=DECODING_PARAMS,
            controller_registry=m0_registry,
        )
        client.flush_trace_buffer(m0_buffer)
        m0_contacts = sum(len(result.contacts) for result in m0_summary.results)
        contact_total += m0_contacts
        log(f"ARM M0 DONE in {time.time() - m0_started:.1f}s: {m0_contacts} contacts")
        arm_results["M0"] = m0_summary

        # ---------------- Arm BLEND ----------------
        cells = {sample.sample_id: LazyQueryVector() for sample in samples}
        kb_factory = make_kb_alpha_blend_controller_factory(
            snapshot=snapshot,
            query_vectors_by_sample={
                sample_id: {"content": cell} for sample_id, cell in cells.items()
            },
            facet_vectors=facet_vectors,
            normalizer=default_label_normalizer,
            rank_weights=ROUND0_WEIGHTS,
            fuse_knobs=ROUND0_FUSE,
            alpha=ROUND0_ALPHA,
            top_k_per_dimension=ROUND0_TOP_K,
        )
        blend_controllers: dict[str, RuntimeEmbeddedBlendController] = {}

        def blend_factory(sample_id: str):
            controller = RuntimeEmbeddedBlendController(
                kb_factory(sample_id),
                sample_id=sample_id,
                cell=cells[sample_id],
                embed=embed_query_text,
            )
            blend_controllers[sample_id] = controller
            return DirectDedupController(controller)

        blend_registry = Registry("dev100 round0 BLEND controller")
        blend_registry.register(CONTROLLER_POLICY_ID, blend_factory)
        log("ARM BLEND START: <=200 core contacts + <=100 embedding tool contacts")
        blend_buffer = TraceBuffer(plan.run_id)
        blend_started = time.time()
        blend_summary = run_speech_native_agent_loop(
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=client,
            split_id=SPLIT_ID,
            knowledge_snapshot=snapshot,
            speech_packet_bindings=packet_bindings,
            controller_policy_id=CONTROLLER_POLICY_ID,
            max_contacts=2,
            slot_count=server_np,
            queue_depth=server_np,
            trace_sink=blend_buffer,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params=DECODING_PARAMS,
            controller_registry=blend_registry,
        )
        client.flush_trace_buffer(blend_buffer)
        blend_contacts = sum(len(result.contacts) for result in blend_summary.results)
        contact_total += blend_contacts
        log(f"ARM BLEND DONE in {time.time() - blend_started:.1f}s: {blend_contacts} contacts")
        arm_results["BLEND"] = blend_summary
        winner_labels = {
            sample_id: controller.last_winner_label
            for sample_id, controller in blend_controllers.items()
        }

        # ---------------- identical-prompt resend pair ----------------
        resend_record: dict[str, object]
        if contact_total + 1 <= ROUND_CORE_CEILING:
            first_sample = samples[0]
            resend_registry = Registry("dev100 round0 resend controller")
            resend_registry.register(M0_POLICY_ID, m0_factory)
            resend_buffer = TraceBuffer(plan.run_id)
            resend_summary = run_speech_native_agent_loop(
                data_root=root,
                plan=plan,
                adapter=adapter,
                core_client=client,
                split_id="DEV-100-RESEND-1",
                knowledge_snapshot=snapshot,
                speech_packet_bindings={
                    first_sample.sample_id: packet_bindings[first_sample.sample_id]
                },
                controller_policy_id=M0_POLICY_ID,
                max_contacts=1,
                slot_count=1,
                queue_depth=1,
                trace_sink=resend_buffer,
                agent_executor_id="openjiuwen-workflow-v1",
                decoding_params=DECODING_PARAMS,
                controller_registry=resend_registry,
            )
            client.flush_trace_buffer(resend_buffer)
            contact_total += 1
            base_text = next(
                result.final_response_text
                for result in m0_summary.results
                if result.sample_id == first_sample.sample_id
            )
            resend_text = resend_summary.results[0].final_response_text
            resend_record = {
                "flown": True,
                "sample_id": first_sample.sample_id,
                "server_np": server_np,
                "response_a_sha256": sha256_text(base_text),
                "response_b_sha256": sha256_text(resend_text),
                "byte_identical": sha256_text(base_text) == sha256_text(resend_text),
                "note": (
                    "byte-identical direct-decode prompt by construction: the SAME "
                    "assembly path (rails.runner._agent_messages over the same frozen "
                    "adapter/contract/packet/instruction inputs) re-issued once against "
                    "the same resident -np 8 session. sha256 equality only."
                ),
            }
            log(
                f"resend pair (sample {first_sample.sample_id}, -np {server_np}): "
                f"byte_identical={resend_record['byte_identical']}"
            )
        else:
            resend_record = {
                "flown": False,
                "reason": (
                    f"round core ceiling {ROUND_CORE_CEILING} fully consumed by the two "
                    f"arms ({contact_total} contacts); the resend is skipped and disclosed "
                    "rather than breaching the registered ceiling"
                ),
            }
            log("resend SKIPPED: no core-contact headroom (disclosed)")
        flight["resend_pair"] = resend_record
        outcome_status = "CONTACTS_COMPLETE"
    finally:
        sampler.end_request_window()
        sampler.stop()
        telemetry = dict(sampler.summary())
        flight["serving_descriptives"] = telemetry
        flight["core_contacts_total"] = contact_total
        flight["outcome_status"] = outcome_status
        save_flight()

        # jitter end + embedding accounting + sidecar stop (always) ----------
        try:
            with embed_lock:
                meter.charge("jitter:end")
                t0 = time.time()
                jitter_end = emb_client.embed_text(contact_id="jitter:end", text=jitter_text)
                meter.record("jitter:end", time.time() - t0, jitter_end.dims, sha256_text(jitter_text))
            dot = sum(a * b for a, b in zip(jitter_start.values, jitter_end.values))
            na = sum(a * a for a in jitter_start.values) ** 0.5
            nb = sum(b * b for b in jitter_end.values) ** 0.5
            flight["embedding_jitter_pair"] = {
                "cosine": dot / (na * nb),
                "bit_identical": tuple(jitter_start.values) == tuple(jitter_end.values),
                "text_sha256": sha256_text(jitter_text),
            }
        except Exception as error:  # noqa: BLE001 — teardown reports, never masks
            flight["embedding_jitter_pair"] = {"error": repr(error)}
        try:
            emb_contacts = emb_client.close()
            flight["embedding_accounting"] = {
                "tool_contacts": meter.count,
                "client_contact_count": emb_contacts.get("contact_count"),
                "ceiling": ROUND_TOOL_CEILING,
                "latency_seconds_total": round(meter.latency_total, 3),
            }
        except Exception as error:  # noqa: BLE001
            flight["embedding_accounting"] = {"error": repr(error), "tool_contacts": meter.count}
        try:
            stop = stop_session(
                emb_session,
                runtime_receipt=emb_runtime_receipt,
                runtime_root=Path("/home/chao"),
                receipt_path=run_dir / "session-qwen3-emb-cpu.stop-receipt.json",
                force_after_timeout=True,
            )
            flight["embedding_session_stop"] = {
                "termination_signal": stop.get("termination_signal"),
                "forced": stop.get("forced"),
            }
            log(f"embedder sidecar stopped ({stop.get('termination_signal')}, forced={stop.get('forced')})")
        except Exception as error:  # noqa: BLE001
            flight["embedding_session_stop"] = {"error": repr(error)}
            log(f"embedder sidecar stop FAILED: {error!r}")
        save_flight()

    # ---- core client receipt (trace manifest + cost) ----------------------
    timings = client.timings
    contact_latency_total = sum(t.latency_seconds for t in timings) if timings else 0.0
    core_receipt = client.close()
    flight["core_client"] = {
        "trace_manifest_hash": core_receipt.get("trace_manifest_hash"),
        "cost": core_receipt.get("cost"),
        "request_count": len(timings),
        "contact_latency_seconds_total": round(contact_latency_total, 3),
    }
    flight["gpu_active_hours_contact_basis"] = round(contact_latency_total / 3600.0, 6)
    flight["wall_seconds"] = round(time.time() - flight_started, 1)
    save_flight()
    log(
        f"core client closed: {len(timings)} requests, contact latency "
        f"{contact_latency_total:.1f}s, wall {flight['wall_seconds']}s"
    )

    # ---- POST-SEAL scoring: gold opens HERE, after all arms ---------------
    log("ALL ROUND ARMS SEALED — opening devel gold scoring-side (iteration tier)")
    scorer = SlurpAdapter(lock, root, repo_root=REPO)
    scores: dict[str, dict[str, dict[str, object]]] = {}
    sample_by_id = {sample.sample_id: sample for sample in samples}
    for arm_id, summary in arm_results.items():
        arm_scores: dict[str, dict[str, object]] = {}
        for result in summary.results:
            metrics = dict(scorer.score(sample_by_id[result.sample_id], result.final_response_text))
            arm_scores[result.sample_id] = {
                "correct": bool(metrics.get("scenario_action_exact")),
                "scenario_exact": bool(metrics.get("scenario_exact")),
                "action_exact": bool(metrics.get("action_exact")),
                "parsed": metrics.get("parsed"),
                "slot_f1_exact_f1": metrics.get("slot_f1_exact_f1"),
                "contacts": len(result.contacts),
                "response_sha256": sha256_text(result.final_response_text),
            }
        scores[arm_id] = arm_scores

    outputs_path = run_dir / "round0-outputs.jsonl"
    with outputs_path.open("w", encoding="utf-8") as sink:
        for arm_id, summary in arm_results.items():
            for result in summary.results:
                sink.write(
                    json.dumps(
                        {
                            "arm": arm_id,
                            "sample_id": result.sample_id,
                            "final_response_text": result.final_response_text,
                            "contacts": len(result.contacts),
                            "slot_ids": [record.slot_id for record in result.contacts],
                            "winner_label": winner_labels.get(result.sample_id)
                            if arm_id == "BLEND"
                            else None,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
    log(f"outputs written: {outputs_path}")

    m0_correct = {sid for sid, row in scores["M0"].items() if row["correct"]}
    blend_correct = {sid for sid, row in scores["BLEND"].items() if row["correct"]}
    wrong_to_correct = sorted(blend_correct - m0_correct)
    correct_to_wrong = sorted(m0_correct - blend_correct)
    blend_evidence_dispatched = sum(
        1 for row in scores["BLEND"].values() if row["contacts"] == 2
    )
    audio_seconds_metered = None
    cost = flight["core_client"]["cost"]
    if isinstance(cost, Mapping):
        audio_seconds_metered = cost.get("audio_seconds_used")

    round_report = {
        "schema": "saea-dev100-round0-report-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "round_index": ROUND_INDEX,
        "attempt_id": attempt_id,
        "generated_at": iso_now(),
        "authority": (
            "docs/readiness/2026-08-23-dev100-campaign-preregistration.md including "
            "amendment 5b; campaign exposure row SAEA-DEV100-KB-ALPHA-BLEND-CAMPAIGN"
        ),
        "config_hash": composed.config_hash,
        "server_np": server_np,
        "decoder_session_receipt_sha256": measured_receipt,
        "gpu_preflight": flight["gpu_preflight"],
        "round0_knobs": {
            "alpha": ROUND0_ALPHA,
            "rank_weight_id": "rrf",
            "evidence_variant": "rank+prior+agreement",
            "tau": ROUND0_TAU,
            "top_k_per_dimension": ROUND0_TOP_K,
            "fusion": {"m": ROUND0_FUSE.m, "c": ROUND0_FUSE.c, "l": ROUND0_FUSE.top_l},
            "rank_weights": {"w_cos": 0.5, "w_prior": 0.3, "w_agree": 0.2},
            "prior_source": "train",
            "m11_pair_boundary_stage": False,
            "value_vectors": "SEALED (never loaded)",
            "percept_admission": "facet-side",
        },
        "arms": {
            "M0": {
                "accuracy_scenario_action_exact": len(m0_correct) / 100.0,
                "correct_count": len(m0_correct),
                "contacts": sum(row["contacts"] for row in scores["M0"].values()),
                "parsed_count": sum(1 for row in scores["M0"].values() if row["parsed"]),
            },
            "BLEND": {
                "accuracy_scenario_action_exact": len(blend_correct) / 100.0,
                "correct_count": len(blend_correct),
                "contacts": sum(row["contacts"] for row in scores["BLEND"].values()),
                "evidence_contact_dispatched_samples": blend_evidence_dispatched,
                "parsed_count": sum(1 for row in scores["BLEND"].values() if row["parsed"]),
                "embedding_tool_contacts": flight["embedding_accounting"].get("tool_contacts"),
            },
        },
        "wrong_to_correct_sample_ids": wrong_to_correct,
        "correct_to_wrong_sample_ids": correct_to_wrong,
        "deviations": [
            {
                "id": "direct-contact-contract-dedup",
                "kind": "rendering fix only, harness-side",
                "detail": (
                    "The registered chain's direct-decode contact re-renders the "
                    "full task contract inside its instruction; the runner's "
                    "protected-knowledge guard refused the first wave because 7 "
                    "TRAIN content-facet representations are substrings of the "
                    "roster text (third takeoff, zero core contacts). The launcher "
                    "replaces that instruction with a reference to the contract "
                    "already present in the system message — the exact remedy-1 "
                    "pattern of amendment 5b (commit 72096bad), extended to the "
                    "direct contact caller-side without touching rails/. The model "
                    "sees the contract exactly once either way; no knob, grammar, "
                    "or policy-id change. A rails-side fix mirroring 72096bad is "
                    "recommended to the coordinator for round 1."
                ),
                "flown_direct_instruction": DIRECT_REFERENCE_INSTRUCTION,
            }
        ],
        "spend_vs_ceilings": {
            "core_contacts": {"used": contact_total, "round_ceiling": ROUND_CORE_CEILING, "campaign_ceiling": 1800},
            "embedding_tool_contacts": {"used": meter.count, "round_ceiling": ROUND_TOOL_CEILING, "campaign_ceiling": 1500},
            "metered_audio_seconds": {"used": audio_seconds_metered, "campaign_ceiling": 2400},
            "gpu_active_hours_contact_basis": {
                "used": flight["gpu_active_hours_contact_basis"],
                "campaign_ceiling": 2.0,
            },
        },
        "resend_pair": flight["resend_pair"],
        "serving_descriptives": flight["serving_descriptives"],
        "embedding_jitter_pair": flight.get("embedding_jitter_pair"),
        "core_client": flight["core_client"],
        "run_dir": str(run_dir),
        "hard_stop": (
            "Round 0 lands and STOPS. No round-1 flight, no knob change: the "
            "coordinator decides round-1 knobs after the owner sync."
        ),
    }
    OUT_CHECK_DIR.mkdir(parents=True, exist_ok=True)
    report_path = OUT_CHECK_DIR / "round0-report.json"
    report_path.write_text(
        json.dumps(round_report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (run_dir / "round0-scores.json").write_text(
        json.dumps(scores, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    flight["outcome_status"] = "ROUND0_LANDED"
    flight["report_path"] = str(report_path)
    save_flight()
    log(f"round-0 report written: {report_path}")
    log(f"report sha256: {sha256_file(report_path)}")
    log(
        f"SUMMARY: M0 {len(m0_correct)}/100, BLEND {len(blend_correct)}/100, "
        f"W->C {len(wrong_to_correct)}, C->W {len(correct_to_wrong)}, "
        f"core contacts {contact_total}/{ROUND_CORE_CEILING}, tool {meter.count}/{ROUND_TOOL_CEILING}"
    )
    log("RESIDENT DECODER LEFT UP for round 1 (never stopped by this launcher)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
