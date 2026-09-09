"""Receipt-bound Audio2Tool speech-feature preprocessing and packet promotion.

Exposure row ``SAEA-SN-A2T-G1-PREPROCESS`` (contract
``configs/experiment/a2t-g1-preprocess.json``). Label-free engineering: the
G1 decoder serves ``--no-mmproj`` and therefore cannot encode audio itself,
so every arm needs an audited speech-feature packet per sample. Campaign
plan ``docs/readiness/2026-08-25-a2t-generality-campaign-plan.md`` section
8.1 item 3.

Two phases, in one invocation:

1. ENCODE -- a CPU-only llama-server sidecar on port 8081 (``-ngl 0
   --no-mmproj-offload``, ``runtime-q4km-preprocess.json``: decoder + mmproj)
   is spawned under its own session receipt, driven with one contact per
   subset sample at ``max_tokens`` 1, and stopped with its own stop receipt.
   Its ``LLAMA_MTMD_FEAT_CACHE_DIR`` is a SEPARATE directory
   ``/home/chao/feat-cache/audio2tool-q4km-04ccc72a``: the pre-existing
   ``audio2tool-q4km`` cache is warm for all 104 items but was written by
   the EARLIER A2T flights under the OLDER featcache build ``5d9dfcb5``, and
   promoting those bytes would smuggle a cross-build feature assumption into
   the flight. Re-encoding under the serving build is the honest option and
   it is cheap.

   The prompt is a fixed minimal instruction, NOT the 152-tool registry. The
   legacy feature-cache key is the FNV-1a hash of the media bytes ALONE
   (``core.model.speech_features.legacy_audio_feature_cache_key``), so the
   prompt cannot affect the cached features, and sending the registry to a
   CPU-only server would cost a 13,236-token prefill per item for nothing.
   No response is read semantically; gold is never opened.

2. PROMOTE -- ``core.model.speech_features.
   materialize_legacy_cached_speech_feature_packets`` promotes the warm
   entries into audited packets under
   ``/home/chao/feat-cache/a2t-q4km-packets-04ccc72a``, and an A2T promotion
   receipt is written beside them. The ``saea-driver promote-speech-packets``
   CLI is deliberately NOT used: it is hard-wired to
   ``data.slurp.load_slurp_engineering_gate``, which refuses any view whose
   ``carrier_lock_key`` is not ``slurp``. The promotion PRIMITIVE it calls is
   carrier-agnostic and is what this script calls directly. Nothing under
   ``src/`` is modified.

Modes::

    # zero contacts: print the composed identity for the ledger row
    python scripts/a2t_g1_preprocess.py --emit-identity

    # zero contacts: verify every input, no session, no gate
    python scripts/a2t_g1_preprocess.py --preflight-only

    # the registered pass
    python scripts/a2t_g1_preprocess.py --run

    # select successor profiles before one of the modes above
    python scripts/a2t_g1_preprocess.py --cpv2 --emit-identity
    python scripts/a2t_g1_preprocess.py --ground-qual --emit-identity
    python scripts/a2t_g1_preprocess.py --semantic-agentloop --emit-identity
    python scripts/a2t_g1_preprocess.py --semantic-agentloop-select-fill --emit-identity
    python scripts/a2t_g1_preprocess.py --calibration-400 --emit-identity
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# The checkout this script lives in, derived from its own location: a git
# worktree runs against ITS OWN ``src`` and ``configs``, never the main
# checkout's. On the main checkout this resolves to the literal path that
# used to be hardcoded here, and no receipt this script writes embeds REPO
# (state, promotion receipt and report carry data-root and packet paths
# only), so no receipt byte moves.
REPO = Path(__file__).resolve().parents[1]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

if (
    Path(_pkg.__file__ or "")
    != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
):
    raise SystemExit(
        "package resolves to %s, not this checkout's src" % (_pkg.__file__,)
    )

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.analysis.a2t_packet_token_gate import (  # noqa: E402
    summarize_packet_tokens,
)
from speech_aware_evidence_acquisition.core.base import TRANSPORTS  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    PACKET_MANIFEST_NAME,
    legacy_audio_feature_cache_key,
    materialize_legacy_cached_speech_feature_packets,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402

RUN_ID = "SAEA-SN-A2T-G1-PREPROCESS"
MODEL_FRAGMENT = "q4km-preprocess-featcache-cpu-sidecar-a2t"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "speech-native-preprocess"
EXPERIMENT_FRAGMENT = "a2t-g1-preprocess"

SUBSET_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-G1-104.json"
SUBSET_RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
SPLIT_IDENTITY_HASH = "f5a030189cf80dcbc52899e2fa5f819bac03874f2ad3f9645fdc60c432a9bf3a"
SUBSET_COUNT = 104
SUBSET_AUDIO_SECONDS = 587.017

RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"
SIDECAR_PORT = 8081
LEGACY_CACHE_DIR = Path("/home/chao/feat-cache/audio2tool-q4km-04ccc72a")
PACKET_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = PACKET_ROOT / "A2T-G1-104-promotion.json"
PRIOR_LEGACY_CACHE_DIR = Path("/home/chao/feat-cache/audio2tool-q4km")
PRIOR_BUILD_RECEIPT = "docs/receipts/runtime-q4km-featcache.json"
EXPECTED_N_EMBD = 2048
PROMOTE_WORKERS = 8

# Registered ceilings for this row (sized from the measured subset).
PLAN_CALLS = 120
PLAN_AUDIO = 700
PLAN_GPU_HOURS = 0.2
ATTEMPT_CORE_CEILING = 110

PREPROCESS_INSTRUCTION = (
    "Observe the complete speech signal for deterministic feature "
    "preprocessing. Respond with OK."
)
DECODING_PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 1}

OUT_CHECK_DIR = (
    REPO / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-25-a2t-g1"
)
PREPROCESS_SPLIT_NAME = "A2T-G1-104"
DATASET_RECEIPT_HASH_KEY = "a2t_g1_subset_receipt_sha256"
DATASET_RUN_IDENTITY_KEY = "a2t_g1_run_identity_hash"
ATTEMPT_SUFFIX = "a2tg1pre"
REQUEST_ID_PREFIX = "a2tg1pre"
STATE_SCHEMA = "saea-a2t-g1-preprocess-v1"
REPORT_SCHEMA = "saea-a2t-g1-preprocess-report-v1"
PROMPT_FIT_SPEECH_TOKEN_CEILING = 455
RECEIPT_IDENTITY_KEY = "run_identity_hash"
DIRECT_RECEIPT_SAMPLES = False
DYNAMIC_INFERENCE_PROMPT_FIT = False

profile_flags = tuple(
    flag
    for flag in (
        "--cpv2",
        "--ground-qual",
        "--semantic-agentloop",
        "--semantic-agentloop-select-fill",
        "--calibration-400",
    )
    if flag in sys.argv
)
if len(profile_flags) > 1:
    raise SystemExit("select at most one Audio2Tool preprocessing profile")

if "--cpv2" in sys.argv:
    RUN_ID = "SAEA-SN-A2T-CPV2-PREPROCESS"
    DATASET_FRAGMENT = "audio2tool-cpv2-104"
    EXPERIMENT_FRAGMENT = "a2t-cpv2-preprocess"
    SUBSET_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-CPV2-104.json"
    SUBSET_RECEIPT_SHA256 = (
        "8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783"
    )
    SPLIT_IDENTITY_HASH = (
        "401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1"
    )
    SUBSET_AUDIO_SECONDS = 536.05
    PREPROCESS_SPLIT_NAME = "A2T-CPV2-104"
    PROMOTION_RECEIPT = PACKET_ROOT / "A2T-CPV2-104-promotion.json"
    PLAN_AUDIO = 650
    DATASET_RECEIPT_HASH_KEY = "a2t_cpv2_subset_receipt_sha256"
    DATASET_RUN_IDENTITY_KEY = "a2t_cpv2_run_identity_hash"
    ATTEMPT_SUFFIX = "a2tcpv2pre"
    REQUEST_ID_PREFIX = "a2tcpv2pre"
    STATE_SCHEMA = "saea-a2t-cpv2-preprocess-v1"
    REPORT_SCHEMA = "saea-a2t-cpv2-preprocess-report-v1"
    OUT_CHECK_DIR = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-contract-preserving-cascade-104-v2"
    )

if "--ground-qual" in sys.argv:
    RUN_ID = "SAEA-SN-A2T-GROUND-QUAL-104-PREPROCESS"
    DATASET_FRAGMENT = "audio2tool-ground-qual-104"
    EXPERIMENT_FRAGMENT = "a2t-ground-qual-preprocess"
    SUBSET_RECEIPT_RELPATH = "docs/receipts/a2t/A2T-GROUND-QUAL-104.json"
    SUBSET_RECEIPT_SHA256 = (
        "eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16"
    )
    SPLIT_IDENTITY_HASH = (
        "fbd4addd541ff29214cbff7c35564b15f27e2fb7f438202b79d694b1c5961d4b"
    )
    SUBSET_AUDIO_SECONDS = 543.107
    PREPROCESS_SPLIT_NAME = "A2T-GROUND-QUAL-104"
    PROMOTION_RECEIPT = PACKET_ROOT / "A2T-GROUND-QUAL-104-promotion.json"
    PLAN_AUDIO = 650
    DATASET_RECEIPT_HASH_KEY = "a2t_ground_qual_subset_receipt_sha256"
    DATASET_RUN_IDENTITY_KEY = "a2t_ground_qual_run_identity_hash"
    ATTEMPT_SUFFIX = "a2tgroundqualpre"
    REQUEST_ID_PREFIX = "a2tgroundqualpre"
    STATE_SCHEMA = "saea-a2t-ground-qual-preprocess-v1"
    REPORT_SCHEMA = "saea-a2t-ground-qual-preprocess-report-v1"
    OUT_CHECK_DIR = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-02-a2t-ground-qual-104-preprocess"
    )

if "--semantic-agentloop" in sys.argv:
    RUN_ID = "SAEA-SN-A2T-SEMANTIC-AGENTLOOP-104-PREPROCESS-V2"
    DATASET_FRAGMENT = "audio2tool-semantic-agentloop-104-v2"
    EXPERIMENT_FRAGMENT = "a2t-semantic-agentloop-preprocess-v2"
    SUBSET_RECEIPT_RELPATH = (
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-03-a2t-fresh-agentloop-roster/flight-roster-receipt.json"
    )
    SUBSET_RECEIPT_SHA256 = (
        "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e"
    )
    SPLIT_IDENTITY_HASH = (
        "84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0"
    )
    SUBSET_AUDIO_SECONDS = 554.255707
    PREPROCESS_SPLIT_NAME = "A2T-AGENTLOOP-FRESH-FLIGHT"
    PACKET_ROOT = Path(
        "/home/chao/feat-cache/a2t-semantic-agentloop-v1-packets-04ccc72a"
    )
    PROMOTION_RECEIPT = PACKET_ROOT / "A2T-SEMANTIC-AGENTLOOP-104-V1-promotion.json"
    PLAN_AUDIO = 650
    DATASET_RECEIPT_HASH_KEY = "a2t_semantic_agentloop_subset_receipt_sha256"
    DATASET_RUN_IDENTITY_KEY = "a2t_semantic_agentloop_split_identity_hash"
    RECEIPT_IDENTITY_KEY = "split_identity_hash"
    DIRECT_RECEIPT_SAMPLES = True
    DYNAMIC_INFERENCE_PROMPT_FIT = True
    ATTEMPT_SUFFIX = "a2tsemanticagentloopprev2"
    REQUEST_ID_PREFIX = "a2tsemanticagentloopprev2"
    STATE_SCHEMA = "saea-a2t-semantic-agentloop-preprocess-v2"
    REPORT_SCHEMA = "saea-a2t-semantic-agentloop-preprocess-report-v2"
    OUT_CHECK_DIR = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-03-a2t-semantic-agentloop-104-v1"
    )

if "--semantic-agentloop-select-fill" in sys.argv:
    RUN_ID = "SAEA-SN-A2T-SEMANTIC-AGENTLOOP-SELECT-FILL-104-PREPROCESS-V1"
    DATASET_FRAGMENT = "audio2tool-semantic-agentloop-select-fill-104-v1"
    EXPERIMENT_FRAGMENT = "a2t-semantic-agentloop-select-fill-preprocess-v1"
    SUBSET_RECEIPT_RELPATH = (
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-03-a2t-select-fill-fresh-roster-v1/flight-roster-receipt.json"
    )
    SUBSET_RECEIPT_SHA256 = (
        "dea74114430ed5e45e29d908dc2ecebf41788edfa2704435a2966f260de5bc4f"
    )
    SPLIT_IDENTITY_HASH = (
        "bcbad5405aa8522ff53a91d624c54a909e01f8a31612b5165844b8e2cbca6eb3"
    )
    SUBSET_AUDIO_SECONDS = 549.489916
    PREPROCESS_SPLIT_NAME = "A2T-SELECT-FILL-FRESH-FLIGHT"
    PACKET_ROOT = Path(
        "/home/chao/feat-cache/"
        "a2t-semantic-agentloop-select-fill-v1-packets-04ccc72a"
    )
    PROMOTION_RECEIPT = (
        PACKET_ROOT / "A2T-SEMANTIC-AGENTLOOP-SELECT-FILL-104-V1-promotion.json"
    )
    PLAN_AUDIO = 650
    DATASET_RECEIPT_HASH_KEY = (
        "a2t_semantic_agentloop_select_fill_subset_receipt_sha256"
    )
    DATASET_RUN_IDENTITY_KEY = (
        "a2t_semantic_agentloop_select_fill_split_identity_hash"
    )
    RECEIPT_IDENTITY_KEY = "split_identity_hash"
    DIRECT_RECEIPT_SAMPLES = True
    DYNAMIC_INFERENCE_PROMPT_FIT = True
    ATTEMPT_SUFFIX = "a2tsemanticagentloopselectfillprev1"
    REQUEST_ID_PREFIX = "a2tsemanticagentloopselectfillprev1"
    STATE_SCHEMA = "saea-a2t-semantic-agentloop-select-fill-preprocess-v1"
    REPORT_SCHEMA = "saea-a2t-semantic-agentloop-select-fill-preprocess-report-v1"
    OUT_CHECK_DIR = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-03-a2t-select-fill-fresh-preprocess-v1"
    )

if "--calibration-400" in sys.argv:
    # Direct-baseline calibration flight (SAEA-A2T-DIRECT-CALIBRATION-V1):
    # the population is the FROZEN 400-row Audio2Tool discovery split, not a
    # fresh draw, so this profile's roster receipt only re-expresses the
    # parent probe receipt in the flight-roster schema. Two of the four
    # calibration cells serve mmproj-free and therefore need one audited
    # packet per row.
    RUN_ID = "SAEA-SN-A2T-CALIBRATION-400-PREPROCESS"
    DATASET_FRAGMENT = "audio2tool-calibration-400"
    EXPERIMENT_FRAGMENT = "a2t-calibration-400-preprocess"
    SUBSET_RECEIPT_RELPATH = (
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-04-a2t-calibration-400-roster/flight-roster-receipt.json"
    )
    SUBSET_RECEIPT_SHA256 = (
        "6f352ea583d0bb91f77aad62e07bdad4d3210d066440fbfaee8e2af504853fe7"
    )
    SPLIT_IDENTITY_HASH = (
        "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
    )
    SUBSET_COUNT = 400
    SUBSET_AUDIO_SECONDS = 2159.688
    PREPROCESS_SPLIT_NAME = "A2T-CALIBRATION-400"
    PACKET_ROOT = Path("/home/chao/feat-cache/a2t-calibration-400-packets-04ccc72a")
    PROMOTION_RECEIPT = PACKET_ROOT / "A2T-CALIBRATION-400-promotion.json"
    PLAN_CALLS = 400
    PLAN_AUDIO = 2300
    PLAN_GPU_HOURS = 0.3
    ATTEMPT_CORE_CEILING = 420
    # Owner CPU-preprocessing baseline: ~20 workers on the 24-core host when
    # no GPU campaign is flying (8 while one is). Promotion is the only
    # parallel phase here -- the encode loop is one contact at a time
    # against a single CPU-only sidecar.
    PROMOTE_WORKERS = 20
    # The frozen 400's longest item is 35.714 s; at the registered 14.4
    # speech tokens per second that is 514 packet tokens, well past the
    # 104-row rosters' 455 ceiling. 560 leaves headroom without hiding an
    # outlier -- and under DYNAMIC_INFERENCE_PROMPT_FIT this figure only
    # annotates the promotion receipt's token summary; every later inference
    # request still has to prove its own exact required window.
    PROMPT_FIT_SPEECH_TOKEN_CEILING = 560
    DATASET_RECEIPT_HASH_KEY = "a2t_calibration_subset_receipt_sha256"
    DATASET_RUN_IDENTITY_KEY = "a2t_calibration_split_identity_hash"
    RECEIPT_IDENTITY_KEY = "split_identity_hash"
    DIRECT_RECEIPT_SAMPLES = True
    DYNAMIC_INFERENCE_PROMPT_FIT = True
    ATTEMPT_SUFFIX = "a2tcalibration400prep"
    REQUEST_ID_PREFIX = "a2tcalibration400prep"
    STATE_SCHEMA = "saea-a2t-calibration-400-preprocess-v1"
    REPORT_SCHEMA = "saea-a2t-calibration-400-preprocess-report-v1"
    OUT_CHECK_DIR = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-04-a2t-direct-calibration-400-v1"
    )


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print("[%s] %s" % (stamp, message), flush=True)


def iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


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


def receipt_packet_id(item: object) -> str:
    """Return an explicit packet id or derive one from the receipt sample id."""

    if not isinstance(item, dict):
        raise ValueError("receipt item must be an object")
    value = item.get("packet_id")
    if value is None:
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError("receipt item sample_id must be non-empty text")
        value = sample_id.replace(":", "/")
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or any(part in ("", ".", "..") for part in value.split("/"))
    ):
        raise ValueError("receipt packet_id must be a safe relative POSIX path")
    return value


def build_receipt_bound_samples(
    receipt: object, root: Path
) -> tuple[Audio2ToolSample, ...]:
    """Build samples only from receipt media identity, never carrier task data."""

    if not isinstance(receipt, dict) or not isinstance(receipt.get("items"), list):
        raise ValueError("receipt items must be a list")
    root = Path(root).resolve()
    samples: list[Audio2ToolSample] = []
    sample_ids: set[str] = set()
    packet_ids: set[str] = set()
    for item in receipt["items"]:
        if not isinstance(item, dict):
            raise ValueError("receipt item must be an object")
        sample_id = item.get("sample_id")
        media_relpath = item.get("media_relpath")
        expected_sha256 = item.get("audio_sha256")
        audio_seconds = item.get("audio_seconds")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError("receipt sample_id must be non-empty text")
        if sample_id in sample_ids:
            raise ValueError("duplicate receipt sample_id: %s" % sample_id)
        if (
            not isinstance(media_relpath, str)
            or not media_relpath
            or media_relpath.startswith("/")
            or "\\" in media_relpath
        ):
            raise ValueError("receipt media_relpath must be a relative POSIX path")
        media_path = (root / media_relpath).resolve()
        try:
            media_path.relative_to(root)
        except ValueError as error:
            raise ValueError("receipt media path escapes the data root") from error
        if not media_path.is_file():
            raise ValueError("receipt media file is missing: %s" % media_relpath)
        if (
            not isinstance(expected_sha256, str)
            or len(expected_sha256) != 64
            or any(char not in "0123456789abcdef" for char in expected_sha256)
        ):
            raise ValueError("receipt audio_sha256 must be lowercase 64-hex")
        measured_sha256 = sha256_file(media_path)
        if measured_sha256 != expected_sha256:
            raise ValueError("audio bytes drift for %s" % sample_id)
        if (
            isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or float(audio_seconds) <= 0
        ):
            raise ValueError("receipt audio_seconds must be positive")
        packet_id = receipt_packet_id(item)
        if packet_id in packet_ids:
            raise ValueError("duplicate receipt packet_id: %s" % packet_id)
        sample_ids.add(sample_id)
        packet_ids.add(packet_id)
        samples.append(
            Audio2ToolSample(
                sample_id=sample_id,
                audio_ref=AudioRef(
                    path=media_relpath, sha256=expected_sha256
                ).validate(),
                audio_seconds=float(audio_seconds),
                media_relpath=media_relpath,
            )
        )
    return tuple(samples)


class A2TG1PreprocessAdapter(Audio2ToolAdapter):
    """``Audio2ToolAdapter`` restricted to the frozen G1 subset, with the
    task contract replaced by a minimal preprocessing instruction and gold
    PERMANENTLY sealed.

    The registry is deliberately absent: the legacy feature-cache key is the
    FNV-1a hash of the media bytes alone, so the prompt cannot change a
    single cached feature byte, and a 13,236-token registry prefill on a
    CPU-only server would cost minutes per item for nothing."""

    def __init__(self, lock, root, *, repo_root, subset_ids) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        self._subset_ids = frozenset(subset_ids)
        self._cache: tuple[Audio2ToolSample, ...] | None = None

    def load_split(self, split_id):  # noqa: D102
        if split_id != PREPROCESS_SPLIT_NAME:
            raise ValueError(
                "A2T preprocess adapter serves only %s, not %r"
                % (PREPROCESS_SPLIT_NAME, split_id)
            )
        if self._cache is None:
            exposed = super().load_split("discovery")
            picked = tuple(
                sample for sample in exposed if sample.sample_id in self._subset_ids
            )
            if len(picked) != len(self._subset_ids):
                missing = self._subset_ids - {s.sample_id for s in picked}
                raise ValueError(
                    "subset ids missing from the carrier: %r" % (sorted(missing)[:5],)
                )
            self._cache = picked
        return self._cache

    def build_task_contract(self, sample, obs):  # noqa: D102
        return PREPROCESS_INSTRUCTION

    def score(self, sample, response):  # noqa: D102 -- gold stays sealed
        return {"scoring_deferred": True}


def load_subset() -> dict:
    receipt_path = REPO / SUBSET_RECEIPT_RELPATH
    measured = sha256_file(receipt_path)
    if measured != SUBSET_RECEIPT_SHA256:
        raise SystemExit(
            "subset receipt hashes to %s, not the registered %s"
            % (measured, SUBSET_RECEIPT_SHA256)
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (
        receipt["split_name"] != PREPROCESS_SPLIT_NAME
        or receipt["count"] != SUBSET_COUNT
        or receipt[RECEIPT_IDENTITY_KEY] != SPLIT_IDENTITY_HASH
    ):
        raise SystemExit("subset receipt identity drifted")
    if abs(float(receipt["audio_seconds_total"]) - SUBSET_AUDIO_SECONDS) > 1e-6:
        raise SystemExit("subset receipt audio total drifted")
    return receipt


def composed_identity():
    composed = compose(
        REPO, MODEL_FRAGMENT, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT
    )
    return composed


def main() -> int:
    receipt = load_subset()
    composed = composed_identity()
    values = composed.values
    if values[DATASET_RECEIPT_HASH_KEY] != SUBSET_RECEIPT_SHA256:
        raise SystemExit("dataset fragment pins a different subset receipt")
    if values[DATASET_RUN_IDENTITY_KEY] != SPLIT_IDENTITY_HASH:
        raise SystemExit("dataset fragment pins a different split identity")
    if values["experiment_id"] != RUN_ID:
        raise SystemExit("experiment fragment names a different run id")

    if "--emit-identity" in sys.argv:
        print(
            json.dumps(
                {
                    "run_id": RUN_ID,
                    "config_hash": composed.config_hash,
                    "protocol_hash": composed.config_hash,
                    "fragments": dict(composed.fragments),
                    "split_identity_hash": SPLIT_IDENTITY_HASH,
                    "count": SUBSET_COUNT,
                    "audio_seconds_total": SUBSET_AUDIO_SECONDS,
                    "plan_calls": PLAN_CALLS,
                    "plan_audio_seconds": PLAN_AUDIO,
                    "plan_gpu_hours": PLAN_GPU_HOURS,
                    "legacy_cache_dir": str(LEGACY_CACHE_DIR),
                    "packet_root": str(PACKET_ROOT),
                    "promotion_receipt": str(PROMOTION_RECEIPT),
                    "subset_receipt_sha256": SUBSET_RECEIPT_SHA256,
                    "d1_media_supplement": d1_media_supplement_relpath(values),
                    "d1_media_supplement_sha256": d1_media_supplement_sha256(values),
                    "prompt_fit_speech_token_ceiling": (
                        None
                        if DYNAMIC_INFERENCE_PROMPT_FIT
                        else PROMPT_FIT_SPEECH_TOKEN_CEILING
                    ),
                    "inference_prompt_fit_policy": (
                        "exact-current-request-required-window"
                        if DYNAMIC_INFERENCE_PROMPT_FIT
                        else "inherit-fixed-text-envelope-if-speech-token-ceiling-passes"
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    if DIRECT_RECEIPT_SAMPLES:
        samples = list(build_receipt_bound_samples(receipt, root))
    else:
        subset_ids = [item["sample_id"] for item in receipt["items"]]
        adapter = A2TG1PreprocessAdapter(
            lock, root, repo_root=REPO, subset_ids=subset_ids
        )
        samples = list(adapter.load_split(PREPROCESS_SPLIT_NAME))
    if len(samples) != SUBSET_COUNT:
        raise SystemExit("adapter resolved %d samples" % len(samples))
    by_id = {sample.sample_id: sample for sample in samples}
    for item in receipt["items"]:
        sample = by_id[item["sample_id"]]
        if sample.media_relpath != item["media_relpath"]:
            raise SystemExit("media_relpath drift for %s" % item["sample_id"])
        if sample.audio_ref.sha256 != item["audio_sha256"]:
            raise SystemExit("audio bytes drift for %s" % item["sample_id"])
    loop_audio = sum(float(sample.audio_seconds) for sample in samples)
    log(
        "subset verified: %d samples, %.6f audio-s, receipt %s"
        % (len(samples), loop_audio, SUBSET_RECEIPT_SHA256[:12])
    )
    legacy_cache_entries = 0
    existing_packet_manifests = 0
    for item in receipt["items"]:
        sample = by_id[item["sample_id"]]
        audio_bytes = (root / sample.media_relpath).read_bytes()
        cache_key = legacy_audio_feature_cache_key(audio_bytes)
        if any(LEGACY_CACHE_DIR.glob("%s_o*.feat" % cache_key)):
            legacy_cache_entries += 1
        if (PACKET_ROOT / receipt_packet_id(item) / PACKET_MANIFEST_NAME).exists():
            existing_packet_manifests += 1
    artifact_preflight = {
        "current_build_legacy_cache_entries": legacy_cache_entries,
        "existing_packet_manifests": existing_packet_manifests,
        "promotion_receipt_exists": PROMOTION_RECEIPT.exists(),
    }
    log(
        "artifact preflight: current cache %d/%d; packet manifests %d/%d; "
        "promotion receipt exists=%s"
        % (
            legacy_cache_entries,
            SUBSET_COUNT,
            existing_packet_manifests,
            SUBSET_COUNT,
            PROMOTION_RECEIPT.exists(),
        )
    )
    if PROMOTION_RECEIPT.exists() or existing_packet_manifests:
        raise SystemExit(
            "receipt-bound preprocessing requires an absent promotion receipt and zero "
            "pre-existing packet manifests"
        )

    if "--preflight-only" in sys.argv and DIRECT_RECEIPT_SAMPLES:
        preflight_gate = FrozenCoreGate.for_study_repo(
            REPO,
            root,
            Path("/home/chao"),
            runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
            expected_model_lock_key=str(values["model_lock_key"]),
            d1_media_supplement_relpath=d1_media_supplement_relpath(values),
            d1_media_supplement_sha256=d1_media_supplement_sha256(values),
        )
        preflight_binding = build_payload_binding(
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            samples=samples,
            data_root=root,
            carrier_root=asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root),
        )
        preflight_gate.verify_media_identity(
            AUDIO2TOOL_LOCK_KEY,
            {
                sample_id: (
                    preflight_binding.media_relpaths[sample_id],
                    preflight_binding.sample_facts[sample_id][0],
                )
                for sample_id in sorted(preflight_binding.allowed_sample_ids)
            },
        )
        log(
            "PREFLIGHT-ONLY PASS: receipt paths, hashes, headers, and D1 successor "
            "verified; zero contacts, no socket checks, no session"
        )
        return 0

    # Legacy profile preflights retain their registered port checks. The direct
    # receipt profile performs them only in run mode, never in contact-free
    # preflight mode.
    import socket

    def reachable(port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                return True
        except OSError:
            return False

    if reachable(SIDECAR_PORT):
        raise SystemExit("something already listens on %d" % SIDECAR_PORT)
    decoder_up_before = reachable(8090)
    log("preflight: 8081 free; GPU decoder on 8090 reachable=%s" % decoder_up_before)

    if "--preflight-only" in sys.argv:
        log(
            "PREFLIGHT-ONLY PASS: inputs verified, zero model contacts, no session, no gate"
        )
        return 0
    if "--run" not in sys.argv:
        raise SystemExit(
            "usage: [--cpv2 | --ground-qual | --semantic-agentloop | "
            "--semantic-agentloop-select-fill | --calibration-400] "
            "(--emit-identity | --preflight-only | --run)"
        )

    attempt_id = "attempt-%s-%s" % (
        datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        ATTEMPT_SUFFIX,
    )
    run_dir = root / "runs" / RUN_ID / attempt_id
    run_dir.mkdir(parents=True, exist_ok=True)
    LEGACY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PACKET_ROOT.mkdir(parents=True, exist_ok=True)
    if PROMOTION_RECEIPT.exists():
        raise SystemExit("promotion receipt already exists: %s" % PROMOTION_RECEIPT)

    state = {
        "schema": STATE_SCHEMA,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "started_at": iso_now(),
        "config_hash": composed.config_hash,
        "count": len(samples),
        "audio_seconds_total": round(loop_audio, 6),
        "legacy_cache_dir": str(LEGACY_CACHE_DIR),
        "packet_root": str(PACKET_ROOT),
        "gpu_decoder_reachable_before": decoder_up_before,
        "artifact_preflight": artifact_preflight,
    }

    def save_state() -> None:
        (run_dir / "preprocess-state.json").write_text(
            json.dumps(state, indent=1, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    save_state()

    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile=str(values["execution_profile"]),
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=PLAN_CALLS,
        planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO,
        protocol_hash=composed.config_hash,
        attempt_id=attempt_id,
    ).validate()

    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        Path("/home/chao"),
        runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=str(values["model_lock_key"]),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values),
    )
    payload_binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root),
    )
    media_facts = {
        sample_id: (
            payload_binding.media_relpaths[sample_id],
            payload_binding.sample_facts[sample_id][0],
        )
        for sample_id in sorted(payload_binding.allowed_sample_ids)
    }
    gate.verify_media_identity(AUDIO2TOOL_LOCK_KEY, media_facts)
    log("D1 media identity PASS for %d samples before sidecar start" % len(media_facts))
    log("running the FULL frozen-core gate (decoder + mmproj attestation)")
    gate_started = time.time()
    lock_sha256 = gate.assert_model_touch_allowed(plan, full_hash=True)
    log(
        "frozen-core gate PASS in %.1fs (lock %s)"
        % (time.time() - gate_started, lock_sha256[:12])
    )
    state["gate"] = {"umbrella_lock_sha256": lock_sha256}
    save_state()

    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    if runtime_receipt.get("role") != "preprocess":
        raise SystemExit("runtime receipt role must be preprocess")
    session_receipt_path = run_dir / "session-preprocess.receipt.json"
    stop_receipt_path = run_dir / "session-preprocess.stop-receipt.json"

    log("spawning the CPU-only preprocessing sidecar on %d" % SIDECAR_PORT)
    session = start_session(
        runtime_root=Path("/home/chao"),
        data_root=root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=SIDECAR_PORT,
        session_id="%s-%s-cpu-sidecar" % (RUN_ID, attempt_id),
        extra_argv=list(values["server_args"]),
        extra_env=dict(values["server_env"]),
        receipt_path=session_receipt_path,
        server_log_path=run_dir / "session-preprocess.server.log",
        role="preprocess",
        ready_timeout_seconds=1800.0,
    )
    log("sidecar up: pid=%s port=%s" % (session.pid, session.port))
    state["sidecar"] = {"pid": session.pid, "port": session.port}
    save_state()

    contacts = 0
    failures: list[str] = []
    stop_out = None
    try:
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values,
            root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=Path("/home/chao"),
        )
        client = FrozenCoreClient(
            plan=plan,
            gate=gate,
            transport=transport,
            run_dir=run_dir,
            binding=payload_binding,
            request_id_prefix=REQUEST_ID_PREFIX,
        )
        loop_started = time.time()
        for index, sample in enumerate(samples, start=1):
            if contacts + 1 > ATTEMPT_CORE_CEILING:
                raise SystemExit(
                    "attempt core ceiling %d reached" % ATTEMPT_CORE_CEILING
                )
            messages = (
                {"role": "system", "content": PREPROCESS_INSTRUCTION},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_audio", "media_relpath": sample.media_relpath}
                    ],
                },
            )
            try:
                client.complete(messages, decoding_params=DECODING_PARAMS)
                contacts += 1
            except Exception as error:  # noqa: BLE001 -- report, never mask
                failures.append("%s: %r" % (sample.sample_id, error))
                log("contact FAILED for %s: %r" % (sample.sample_id, error))
            if index % 10 == 0 or index == len(samples):
                log(
                    "encode %d/%d (%d contacts, %d failures, %.1fs)"
                    % (
                        index,
                        len(samples),
                        contacts,
                        len(failures),
                        time.time() - loop_started,
                    )
                )
        core_receipt = client.close()
        state["core_client"] = {
            "trace_manifest_hash": core_receipt.get("trace_manifest_hash"),
            "cost": core_receipt.get("cost"),
        }
        state["contacts"] = contacts
        state["failures"] = failures
        save_state()
    finally:
        stop_out = stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=Path("/home/chao"),
            receipt_path=stop_receipt_path,
            force_after_timeout=True,
        )
        log(
            "sidecar stopped: %s forced=%s"
            % (stop_out.get("termination_signal"), stop_out.get("forced"))
        )
        state["sidecar_stop"] = {
            "termination_signal": stop_out.get("termination_signal"),
            "forced": stop_out.get("forced"),
        }
        save_state()

    if failures:
        raise SystemExit(
            "%d encode contacts failed; refusing to promote a partial cache: %r"
            % (len(failures), failures[:5])
        )

    # ---- PROMOTE (zero contacts; the sidecar is provably stopped) ---------
    gguf_files = runtime_receipt["gguf_files"]
    decoder = [
        entry
        for entry in gguf_files
        if "mmproj" not in Path(str(entry["path"])).name.lower()
    ]
    mmproj = [
        entry
        for entry in gguf_files
        if "mmproj" in Path(str(entry["path"])).name.lower()
    ]
    if len(decoder) != 1 or len(mmproj) != 1:
        raise SystemExit(
            "preprocess receipt must bind exactly one decoder and one mmproj"
        )
    bindings = tuple(
        {
            "packet_id": receipt_packet_id(item),
            "audio_path": str(root / item["media_relpath"]),
        }
        for item in receipt["items"]
    )
    log("promoting %d packets into %s" % (len(bindings), PACKET_ROOT))
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=PACKET_ROOT,
        bindings=bindings,
        legacy_cache_dir=LEGACY_CACHE_DIR,
        encoder_receipt_sha256=canonical_sha256(runtime_receipt),
        decoder_gguf_sha256=str(decoder[0]["sha256"]),
        mmproj_sha256=str(mmproj[0]["sha256"]),
        expected_n_embd=EXPECTED_N_EMBD,
        causal_attention=True,
        workers=PROMOTE_WORKERS,
    )
    if len(packets) != SUBSET_COUNT:
        raise SystemExit("promotion produced %d packets" % len(packets))
    audio_by_packet = {
        receipt_packet_id(item): item["audio_sha256"] for item in receipt["items"]
    }
    for packet in packets:
        if packet.audio_sha256 != audio_by_packet[packet.packet_id]:
            raise SystemExit(
                "promoted packet %s carries a different audio sha256" % packet.packet_id
            )
    packet_token_counts = {
        packet.packet_id: sum(chunk.n_tokens for chunk in packet.chunks)
        for packet in packets
    }
    token_summary = summarize_packet_tokens(
        packet_token_counts,
        ceiling=PROMPT_FIT_SPEECH_TOKEN_CEILING,
    )
    if token_summary["distribution"]["count"] != SUBSET_COUNT:
        raise SystemExit("token accounting did not cover every promoted packet")
    log(
        "packet tokens: min=%d median=%.1f p90=%d p95=%d max=%d ceiling=%d pass=%s"
        % (
            token_summary["distribution"]["min"],
            token_summary["distribution"]["median"],
            token_summary["distribution"]["p90"],
            token_summary["distribution"]["p95"],
            token_summary["distribution"]["max"],
            PROMPT_FIT_SPEECH_TOKEN_CEILING,
            token_summary["within_ceiling"],
        )
    )

    if DIRECT_RECEIPT_SAMPLES:
        prior_cache_disclosure = (
            "The fresh roster was loaded directly from its hash-pinned receipt, "
            "without opening carrier task data. Every promoted legacy-cache entry "
            "is read from the current-build cache directory and bound to the current "
            "runtime receipt; no older-build cache provenance is accepted."
        )
    else:
        prior_cache_disclosure = (
            "The pre-existing legacy cache %s was warm for all %d subset items "
            "before this pass, but it was written by the EARLIER A2T flights "
            "under the OLDER featcache build (%s). Those bytes were NOT "
            "promoted. This pass re-encoded every item under the serving build "
            "%s into a separate cache directory, so the promoted packets' "
            "encoder provenance is the same build that serves them."
        ) % (
            PRIOR_LEGACY_CACHE_DIR,
            SUBSET_COUNT,
            PRIOR_BUILD_RECEIPT,
            runtime_receipt["llama_cpp"]["build_commit"],
        )
    promotion = {
        "schema": "saea-a2t-speech-packet-promotion-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": AUDIO2TOOL_LOCK_KEY,
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "subset_receipt": SUBSET_RECEIPT_RELPATH,
        "subset_receipt_sha256": SUBSET_RECEIPT_SHA256,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "config_hash": composed.config_hash,
        "preprocess_session_id": session.session_id,
        "preprocess_session_receipt_sha256": sha256_file(session_receipt_path),
        "preprocess_stop_receipt_sha256": sha256_file(stop_receipt_path),
        "preprocess_stop_signal": stop_out.get("termination_signal"),
        "preprocess_stop_forced": bool(stop_out.get("forced")),
        "runtime_receipt": RUNTIME_RECEIPT_RELPATH,
        "runtime_receipt_sha256": canonical_sha256(runtime_receipt),
        "llama_cpp_build_commit": runtime_receipt["llama_cpp"]["build_commit"],
        "legacy_cache_dir": str(LEGACY_CACHE_DIR),
        "feature_root": str(PACKET_ROOT),
        "encode_contacts": contacts,
        "encode_audio_seconds": round(loop_audio, 6),
        "count": len(packets),
        "speech_feature_tokens": token_summary,
        "prior_cache_disclosure": prior_cache_disclosure,
        "packets": [
            {
                "packet_id": packet.packet_id,
                "packet_sha256": packet.packet_sha256,
                "audio_sha256": packet.audio_sha256,
                "decoder_gguf_sha256": packet.decoder_gguf_sha256,
                "mmproj_sha256": packet.mmproj_sha256,
                "n_tokens": packet_token_counts[packet.packet_id],
            }
            for packet in packets
        ],
    }
    PROMOTION_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    with PROMOTION_RECEIPT.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(promotion, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    promotion_sha = sha256_file(PROMOTION_RECEIPT)
    state["promotion"] = {
        "receipt": str(PROMOTION_RECEIPT),
        "sha256": promotion_sha,
        "count": len(packets),
        "speech_feature_tokens": token_summary,
    }
    state["finished_at"] = iso_now()
    save_state()

    OUT_CHECK_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": REPORT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "attempt_id": attempt_id,
        "generated_at": iso_now(),
        "config_hash": composed.config_hash,
        "fragments": dict(composed.fragments),
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "subset_receipt": SUBSET_RECEIPT_RELPATH,
        "subset_receipt_sha256": SUBSET_RECEIPT_SHA256,
        "count": SUBSET_COUNT,
        "encode_contacts": contacts,
        "encode_failures": failures,
        "audio_seconds_total": round(loop_audio, 6),
        "core_client": state.get("core_client"),
        "sidecar": state.get("sidecar"),
        "sidecar_stop": state.get("sidecar_stop"),
        "gpu_decoder_reachable_before": decoder_up_before,
        "gpu_decoder_reachable_after": reachable(8090),
        "gate": state.get("gate"),
        "artifact_preflight": artifact_preflight,
        "promotion_receipt": str(PROMOTION_RECEIPT),
        "promotion_receipt_sha256": promotion_sha,
        "packets_promoted": len(packets),
        "speech_feature_tokens": token_summary,
        "prompt_fit_inheritance_allowed": (
            None if DYNAMIC_INFERENCE_PROMPT_FIT else token_summary["within_ceiling"]
        ),
        "prompt_fit_overflow_action": (
            "No packet is truncated. Every later inference request must add exact "
            "rendered text, this packet's measured speech tokens, special tokens, and "
            "its completion ceiling, then require the complete window to be at most "
            "24,576 tokens."
            if DYNAMIC_INFERENCE_PROMPT_FIT
            else (
                "No packet is truncated. Qualification remains closed until a separately "
                "registered exact prompt-fit successor."
                if not token_summary["within_ceiling"]
                else "The landed full-handbook prompt-fit receipt may be inherited."
            )
        ),
        "legacy_cache_dir": str(LEGACY_CACHE_DIR),
        "packet_root": str(PACKET_ROOT),
        "llama_cpp_build_commit": runtime_receipt["llama_cpp"]["build_commit"],
        "prior_cache_disclosure": promotion["prior_cache_disclosure"],
        "plan": {
            "planned_model_calls": PLAN_CALLS,
            "planned_speech_audio_seconds": PLAN_AUDIO,
            "planned_gpu_hours": PLAN_GPU_HOURS,
            "attempt_core_ceiling": ATTEMPT_CORE_CEILING,
        },
        "boundary": (
            "label-free: gold never opened, no response read semantically, the "
            "registered completion is one token; the GPU decoder on 8090 was "
            "never started, stopped, reconfigured or sent a request; its loopback "
            "reachability was observed before and after"
        ),
        "run_dir": str(run_dir),
    }
    report_path = OUT_CHECK_DIR / "preprocess-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    log("preprocess report written: %s" % report_path)
    log(
        "DONE: %d contacts, %d packets promoted, promotion receipt %s"
        % (contacts, len(packets), promotion_sha[:12])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
