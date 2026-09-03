"""Concrete WSL2 runtime for the semantic AgentLoop 104-row flight.

Importing and constructing this module performs local validation only. Service
processes and loopback requests occur exclusively through lifecycle hooks that
the authority-gated coordinator calls after ``--execute``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Mapping, Sequence
import urllib.request

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate
from speech_aware_evidence_acquisition.core.base import RunResult
from speech_aware_evidence_acquisition.core.bundle import (
    STATUS_COMPLETED,
    abort_attempt_if_opened,
    build_manifest,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import (
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    protocol_hash,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.core.model import LlamaServerTransport
from speech_aware_evidence_acquisition.core.session import (
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.core.split_receipt import VerifiedSplit
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.data.audio2tool import (
    AUDIO2TOOL_LOCK_KEY,
    load_tool_registry,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (
    asset_dir,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (
    CompatibilityRule,
)
from speech_aware_evidence_acquisition.rails.a2t_frozen_semantic_assets import (
    load_frozen_semantic_runtime_assets,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    render_audio2tool_instruction,
)
from speech_aware_evidence_acquisition.rails.a2t_selected_tool_ground import (
    SelectedToolDecisionGround,
)
from speech_aware_evidence_acquisition.rails.a2t_semantic_router import (
    ToolTierSemanticIndex,
)
from speech_aware_evidence_acquisition.rails.consumption import (
    build_consumption_trace,
)
from speech_aware_evidence_acquisition.rails.core_client import (
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.embedding_client import EmbeddingClient
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_semantic_agentloop import (
    AGENT_EXECUTOR_ID,
    FreshSemanticPhaseAdapter,
    MATCHED_USE_PHASE,
    OBSERVATION_PHASE,
    QUEUE_DEPTH,
    SHUFFLED_USE_PHASE,
    SLOT_COUNT,
)
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter


GENERATION_PORT = 8090
EMBEDDING_PORT = 8082
EMBEDDING_DIMENSION = 1024
EMBEDDING_MODEL_BYTES = 639_150_592
EMBEDDING_MODEL_RELPATH = (
    "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"
)
GENERATION_ARM = "speech-feature-query"
COMMITTED_CONFIG_FRAGMENTS = {
    "model": "q4km-mmproj-free-speech-native-np2-a2t-max1024",
    "dataset": "audio2tool-semantic-agentloop-104-v2",
    "baseline": "a2t-semantic-agentloop-top16",
    "experiment": "a2t-semantic-agentloop-104-v1",
}
_SHA256 = frozenset("0123456789abcdef")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read runtime JSON {path}: {error}") from error
    if not isinstance(value, Mapping):
        raise RuntimeError(f"runtime JSON must be an object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _confined_file(root: Path, raw: object, *, label: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise RuntimeError(f"{label} must be a non-empty POSIX path")
    path = Path(raw)
    resolved_root = Path(root).resolve()
    candidate = path.resolve() if path.is_absolute() else (resolved_root / path).resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise RuntimeError(f"{label} escapes its registered root")
    if not candidate.is_file():
        raise RuntimeError(f"{label} is unavailable: {candidate}")
    return candidate


def _require_hash(path: Path, expected: object, *, label: str) -> Path:
    if not _is_sha256(expected) or _sha256_file(path) != expected:
        raise RuntimeError(f"{label} SHA-256 drift")
    return path


def parse_execution_plans(
    authority: Mapping[str, object], *, roles: Sequence[str], run_id: str
) -> dict[str, ExecutionPlan]:
    """Construct the repository contract type for every ordered phase."""

    raw = authority.get("execution_plans")
    if not isinstance(raw, Mapping) or tuple(raw) != tuple(roles):
        raise RuntimeError("runtime requires the six ordered ExecutionPlans")
    plans: dict[str, ExecutionPlan] = {}
    attempts: set[str] = set()
    allowed = set(ExecutionPlan.__dataclass_fields__)
    hashes = authority.get("hashes")
    preregistration = (
        hashes.get("exposure_preregistration_sha256")
        if isinstance(hashes, Mapping)
        else None
    )
    if not _is_sha256(preregistration):
        raise RuntimeError("authority lacks the exposure preregistration SHA-256")
    for role in roles:
        value = raw[role]
        if not isinstance(value, Mapping):
            raise RuntimeError(f"ExecutionPlan {role!r} must be an object")
        if value.get("exposure_preregistration_sha256") != preregistration:
            raise RuntimeError(f"ExecutionPlan {role!r} preregistration binding drift")
        fields = {key: item for key, item in value.items() if key in allowed}
        plan = ExecutionPlan(**fields).validate()
        if (
            plan.run_id != run_id
            or plan.execution_profile != "bounded-discovery-probe"
            or plan.carrier_lock_key != AUDIO2TOOL_LOCK_KEY
            or plan.split_role != "discovery"
            or plan.split_identity_hash != authority.get("split_identity_hash")
            or plan.protocol_hash != authority.get("core_protocol_sha256")
            or plan.planned_model_calls != 624
            or plan.attempt_id in attempts
        ):
            raise RuntimeError(f"ExecutionPlan {role!r} identity or budget drift")
        assert plan.attempt_id is not None
        attempts.add(plan.attempt_id)
        plans[role] = plan
    material = {role: asdict(plans[role]) for role in roles}
    expected = authority.get("hashes", {}).get("execution_plan_set_sha256")  # type: ignore[union-attr]
    if _sha256_json(material) != expected:
        raise RuntimeError("ExecutionPlan set SHA-256 drift")
    return plans


def parse_embedding_execution_plan(
    authority: Mapping[str, object], *, protocol_sha256: str
) -> ExecutionPlan:
    """Construct the separately governed 208-contact embedding plan."""

    raw = authority.get("embedding_execution_plan")
    hashes = authority.get("hashes")
    if not isinstance(raw, Mapping) or not isinstance(hashes, Mapping):
        raise RuntimeError("authority lacks the embedding ExecutionPlan")
    preregistration = hashes.get("exposure_preregistration_sha256")
    if raw.get("exposure_preregistration_sha256") != preregistration:
        raise RuntimeError("embedding ExecutionPlan preregistration binding drift")
    allowed = set(ExecutionPlan.__dataclass_fields__)
    plan = ExecutionPlan(
        **{key: item for key, item in raw.items() if key in allowed}
    ).validate()
    if (
        plan.run_id != "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1-EMBED"
        or plan.execution_profile != "bounded-discovery-probe"
        or plan.carrier_lock_key != AUDIO2TOOL_LOCK_KEY
        or plan.split_role != "discovery"
        or plan.split_identity_hash != authority.get("split_identity_hash")
        or plan.protocol_hash != protocol_sha256
        or plan.planned_model_calls != 208
        or plan.planned_gpu_hours != 0.2
        or plan.planned_speech_audio_seconds != 1
        or not plan.attempt_id
    ):
        raise RuntimeError("embedding ExecutionPlan identity or budget drift")
    expected = hashes.get("embedding_execution_plan_sha256")
    if _sha256_json(asdict(plan)) != expected:
        raise RuntimeError("embedding ExecutionPlan SHA-256 drift")
    return plan


@dataclass(frozen=True)
class RuntimeSample:
    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


class DirectAdapter(TaskAdapter):
    """Label-free M0 adapter using only the registry task contract."""

    def __init__(self, samples: Sequence[RuntimeSample], task_contract: str) -> None:
        self.samples = tuple(samples)
        self.task_contract = task_contract

    def load_split(self, split_id: str) -> tuple[RuntimeSample, ...]:
        if not isinstance(split_id, str) or not split_id:
            raise RuntimeError("M0 split id must be non-empty")
        return self.samples

    def build_task_contract(self, sample: object, obs: object) -> str:
        return self.task_contract

    def assemble_prompt(self, sample: object, supply: object):
        if supply is not None:
            raise RuntimeError("M0 forbids supplied evidence")
        return (
            {"role": "system", "content": self.task_contract},
            {"role": "user", "content": []},
        )

    def score(self, sample: object, response: str) -> Mapping[str, object]:
        return {"scoring_deferred": True}

    def extract_consumption(self, sample: object, supply: object, response: str):
        return build_consumption_trace(span_id="full", supply=None, response_text=response)


def build_direct_task_contract(registry_contract: str) -> str:
    """Return the byte-exact historical Audio2Tool direct instruction."""

    return render_audio2tool_instruction(registry_contract)


def _semantic_bundle_material(
    summary: object,
    trace_documents: Sequence[Mapping[str, object]],
    *,
    role: str,
    umbrella_lock_sha256: str,
) -> tuple[tuple[dict[str, object], ...], dict[str, object]]:
    """Materialize one semantic role without predecessor phase whitelists."""

    allowed_roles = {
        "direct_m0",
        "obs_semantic_retrieval",
        "transcript_top16_use",
        "model_query_top16_use",
        "rrf_fused_top16_use",
        "same_stratum_shuffled_fused_use",
    }
    if role not in allowed_roles or not _is_sha256(umbrella_lock_sha256):
        raise RuntimeError("semantic bundle role or lock identity drift")
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != 104:
        raise RuntimeError("semantic phase summary must contain exactly 104 results")
    result_by_id = {getattr(item, "sample_id", None): item for item in results}
    if len(result_by_id) != 104 or None in result_by_id:
        raise RuntimeError("semantic phase results contain malformed identities")
    channels: dict[str, dict[str, Mapping[str, object]]] = {
        "MODEL_REQUEST": {}, "MODEL_RESPONSE": {}, "COST": {}
    }
    suffixes = {"MODEL_REQUEST": "/request", "MODEL_RESPONSE": "/response", "COST": "/cost"}
    for document in trace_documents:
        channel = document.get("channel") if isinstance(document, Mapping) else None
        if channel not in channels:
            continue
        record_id = document.get("record_id")
        payload = document.get("payload")
        suffix = suffixes[str(channel)]
        if not isinstance(record_id, str) or not record_id.endswith(suffix) or not isinstance(payload, Mapping):
            raise RuntimeError("semantic phase trace record is malformed")
        request_id = record_id[: -len(suffix)]
        if not request_id or request_id in channels[str(channel)]:
            raise RuntimeError("semantic phase trace request identity is duplicate")
        channels[str(channel)][request_id] = payload
    requests, responses, costs = (
        channels["MODEL_REQUEST"], channels["MODEL_RESPONSE"], channels["COST"]
    )
    if set(requests) != set(responses) or set(requests) != set(costs):
        raise RuntimeError("semantic request, response, and cost traces differ")
    request_by_sample: dict[str, str] = {}
    for request_id, outer in requests.items():
        payload = outer.get("payload")
        sample_id = payload.get("sample_id") if isinstance(payload, Mapping) else None
        if (
            not isinstance(sample_id, str)
            or sample_id in request_by_sample
            or outer.get("arm") != GENERATION_ARM
        ):
            raise RuntimeError("semantic model request identity or arm drift")
        request_by_sample[sample_id] = request_id
    if set(request_by_sample) != set(result_by_id):
        raise RuntimeError("semantic trace and summary sample identities differ")

    rows: list[dict[str, object]] = []
    totals = {"calls_used": 0, "audio_seconds_used": 0.0, "latency_seconds_total": 0.0,
              "prompt_tokens_total": 0, "completion_tokens_total": 0}
    for sample_id in sorted(result_by_id):
        request_id = request_by_sample[sample_id]
        request = requests[request_id]
        response = responses[request_id]
        text = getattr(result_by_id[sample_id], "final_response_text", None)
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str) else None
        if response.get("text") != text or response.get("response_text_sha256") != text_hash:
            raise RuntimeError(f"semantic response trace drift for {sample_id!r}")
        request_hash, response_hash = request.get("payload_sha256"), response.get("response_sha256")
        if not _is_sha256(request_hash) or not _is_sha256(response_hash):
            raise RuntimeError("semantic request or response hash is malformed")
        rows.append({
            "request_id": request_id, "sample_id": sample_id,
            "carrier_lock_key": AUDIO2TOOL_LOCK_KEY, "arm": GENERATION_ARM,
            "text": text, "admitted": True, "request_sha256": request_hash,
            "response_sha256": response_hash, "response_text_sha256": text_hash,
            "phase": role,
        })
    for cost in costs.values():
        for field in ("calls", "audio_seconds", "latency_seconds", "prompt_tokens", "completion_tokens"):
            value = cost.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
                raise RuntimeError(f"semantic cost field {field!r} is invalid")
        if float(cost["calls"]) != 1.0 or not float(cost["prompt_tokens"]).is_integer() or not float(cost["completion_tokens"]).is_integer():
            raise RuntimeError("semantic phase requires one call and integral token counts")
        totals["calls_used"] += 1
        totals["audio_seconds_used"] += float(cost["audio_seconds"])
        totals["latency_seconds_total"] += float(cost["latency_seconds"])
        totals["prompt_tokens_total"] += int(cost["prompt_tokens"])
        totals["completion_tokens_total"] += int(cost["completion_tokens"])
    if totals["calls_used"] != len(rows):
        raise RuntimeError("semantic phase cost count differs from outputs")
    return tuple(rows), {**totals, "tool_calls": 0, "umbrella_lock_sha256": umbrella_lock_sha256}


@dataclass
class PhaseState:
    role: str
    runner_phase: str
    plan: ExecutionPlan
    run_dir: Path
    session_receipt_path: Path
    client: FrozenCoreClient
    sink: TraceSink | None
    trace_manifest_hash: str | None = None
    client_summary: Mapping[str, object] | None = None
    runtime_receipt: Mapping[str, object] | None = None


def _load_ground(
    corpus: Path, rules: Sequence[CompatibilityRule]
) -> SelectedToolDecisionGround:
    return SelectedToolDecisionGround.from_path(corpus, compatibility_rules=rules)


def _load_governed_embedding_module(path: Path, expected_sha256: object) -> object:
    """Load only the sibling wrapper whose exact source bytes are authorized."""

    _require_hash(path, expected_sha256, label="governed embedding tool")
    spec = importlib.util.spec_from_file_location("saea_governed_embedding_tool", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("governed embedding tool loader is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LocalSemanticRuntime:
    """Real local service/client/trace/bundle implementation for the coordinator."""

    agent_executor_id = AGENT_EXECUTOR_ID
    slot_count = SLOT_COUNT
    queue_depth = QUEUE_DEPTH

    def __init__(
        self,
        *,
        authority: Mapping[str, object],
        roster: object,
        packets: object,
        protocol_config: Mapping[str, object],
        launcher_module: object,
    ) -> None:
        self.launcher = launcher_module
        self.authority = authority
        self.roster = roster
        self.packets = packets
        self.protocol_config = protocol_config
        self.repo = Path(getattr(launcher_module, "REPO"))
        runtime = authority.get("local_runtime")
        hashes = authority.get("hashes")
        if not isinstance(runtime, Mapping) or not isinstance(hashes, Mapping):
            raise RuntimeError("authority lacks concrete local_runtime or hashes")
        self.spec = runtime
        self.hashes = hashes
        if (
            _sha256_file(Path(__file__)) != hashes.get("local_runtime_factory_sha256")
            or _sha256_file(Path(str(getattr(launcher_module, "__file__"))))
            != hashes.get("coordinator_launcher_sha256")
        ):
            raise RuntimeError("authority does not bind the running launcher bytes")
        self.data_root = Path(str(runtime.get("data_root", ""))).resolve()
        self.runtime_root = Path(str(runtime.get("runtime_root", ""))).resolve()
        if not self.data_root.is_dir() or not self.runtime_root.is_dir():
            raise RuntimeError("runtime data_root or runtime_root is unavailable")
        self.mission_dir = self.data_root / "runs" / str(authority["run_id"]) / str(
            runtime.get("mission_id", "")
        )
        if not runtime.get("mission_id") or self.mission_dir.exists():
            raise RuntimeError("mission_id is blank or the one-shot mission already exists")

        self.plans = parse_execution_plans(
            authority,
            roles=getattr(launcher_module, "MANIFEST_ROLES"),
            run_id=str(authority["run_id"]),
        )
        self.embedding_plan = parse_embedding_execution_plan(
            authority, protocol_sha256=str(authority["core_protocol_sha256"])
        )
        self.embedding_tool_module = _load_governed_embedding_module(
            Path(__file__).with_name("governed_embedding_tool.py"),
            hashes.get("governed_embedding_tool_sha256"),
        )
        self.preregistration_path = _require_hash(
            self.repo
            / "docs/readiness/2026-09-03-a2t-semantic-agentloop-104-v1-preregistration.md",
            hashes.get("exposure_preregistration_sha256"),
            label="exposure preregistration",
        )
        self.verified_split = VerifiedSplit(
            name=str(authority.get("split_name", getattr(launcher_module, "SPLIT_ID"))),
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            split_role="discovery",
            ids=tuple(sorted(roster.sample_ids)),
            prefixed_ids=tuple(
                f"audio2tool/{sample_id}" for sample_id in sorted(roster.sample_ids)
            ),
            identity_hash=str(authority["split_identity_hash"]),
        )
        self.samples = tuple(
            RuntimeSample(
                sample_id=str(row["sample_id"]),
                audio_ref=AudioRef(
                    path=str(row["media_relpath"]), sha256=str(row["audio_sha256"])
                ).validate(),
                audio_seconds=float(row["audio_seconds"]),
            )
            for row in roster.items
        )
        lock = load_lock(umbrella_lock_path(self.repo))
        self.carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, self.data_root)
        registry = load_tool_registry(lock, self.data_root)
        self.registered_tool_names = tuple(sorted({row["tool_name"] for row in registry}))
        if len(self.registered_tool_names) != 152:
            raise RuntimeError("Audio2Tool registry must contain exactly 152 tools")
        self.task_contract = build_direct_task_contract(
            render_tool_schemas(lock, self.data_root)
        )
        self.binding = build_payload_binding(
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            samples=self.samples,
            data_root=self.data_root,
            carrier_root=self.carrier_root,
        )

        self.generation_runtime_receipt_path = _require_hash(
            _confined_file(
                self.repo / "docs",
                runtime.get("generation_runtime_receipt"),
                label="generation runtime receipt",
            ),
            hashes.get("generation_runtime_receipt_sha256"),
            label="generation runtime receipt",
        )
        self.generation_runtime_receipt = load_runtime_receipt(
            self.generation_runtime_receipt_path
        )
        self.embedding_runtime_receipt_path = _require_hash(
            _confined_file(
                self.repo / "docs",
                runtime.get("embedding_runtime_receipt"),
                label="embedding runtime receipt",
            ),
            hashes.get("embedding_runtime_receipt_sha256"),
            label="embedding runtime receipt",
        )
        self.embedding_runtime_receipt = load_runtime_receipt(
            self.embedding_runtime_receipt_path
        )
        gguf = self.embedding_runtime_receipt.get("gguf_files")
        gguf_record = gguf[0] if isinstance(gguf, list) and len(gguf) == 1 else None
        if (
            not isinstance(gguf_record, Mapping)
            or gguf_record.get("path") != EMBEDDING_MODEL_RELPATH
            or gguf_record.get("bytes") != EMBEDDING_MODEL_BYTES
            or gguf_record.get("sha256")
            != getattr(launcher_module, "QWEN3_EMBEDDING_Q8_GGUF_SHA256")
        ):
            raise RuntimeError("embedding runtime receipt GGUF identity drift")

        operational = runtime.get("composed_config")
        if not isinstance(operational, Mapping):
            raise RuntimeError("authority lacks composed operational config")
        fragments = operational.get("fragments")
        config_hash = operational.get("config_hash")
        if not isinstance(fragments, Mapping) or dict(fragments) != COMMITTED_CONFIG_FRAGMENTS:
            raise RuntimeError("composed operational config is malformed")
        self.composed = compose(
            self.repo,
            model=str(fragments["model"]),
            dataset=str(fragments["dataset"]),
            baseline=str(fragments["baseline"]),
            experiment=str(fragments["experiment"]),
        )
        values = self.composed.values
        if self.composed.config_hash != config_hash:
            raise RuntimeError("operational composed config hash drift")
        if (
            values.get("arm") != GENERATION_ARM
            or values.get("a2t_semantic_agentloop_split_name")
            != self.verified_split.name
            or protocol_hash(
                self.composed.config_hash,
                GENERATION_ARM,
                self.verified_split.identity_hash,
            )
            != authority.get("core_protocol_sha256")
        ):
            raise RuntimeError("core composed config/protocol binding drift")
        if runtime.get("generation_runtime_receipt") != runtime_receipt_relpath(values):
            raise RuntimeError("generation runtime receipt differs from committed config")

        semantic_receipt_path = _require_hash(
            self.repo
            / "docs/receipts/knowledge/a2t-semantic-agentloop-runtime-v1.json",
            hashes.get("semantic_runtime_asset_receipt_sha256"),
            label="semantic runtime asset receipt",
        )
        assets = load_frozen_semantic_runtime_assets(
            repo=self.repo,
            data_root=self.data_root,
        )
        self.index = assets.index
        if self.index.registry_tool_names != self.registered_tool_names:
            raise RuntimeError("frozen semantic index and live registry names differ")
        if self.index.index_sha256 != hashes.get("semantic_index_sha256"):
            raise RuntimeError("frozen semantic index SHA-256 drift")
        if _sha256_file(assets.centroid_artifact_path) != hashes.get(
            "semantic_centroid_artifact_sha256"
        ):
            raise RuntimeError("frozen semantic centroid artifact SHA-256 drift")
        if _sha256_file(assets.compatibility_rules_path) != hashes.get(
            "semantic_compatibility_rules_sha256"
        ):
            raise RuntimeError("frozen compatibility-rule artifact SHA-256 drift")
        semantic_sources = assets.receipt.get("sources")
        if not isinstance(semantic_sources, Mapping) or (
            semantic_sources.get("construction_rows_sha256")
            != hashes.get("construction_rows_sha256")
            or semantic_sources.get("embedding_receipt_sha256")
            != hashes.get("construction_embedding_receipt_sha256")
            or semantic_sources.get("embedding_vector_sha256")
            != hashes.get("construction_vector_artifact_sha256")
        ):
            raise RuntimeError("frozen semantic source authority binding drift")
        if _sha256_file(semantic_receipt_path) != hashes.get(
            "semantic_runtime_asset_receipt_sha256"
        ):
            raise RuntimeError("semantic runtime receipt changed after load")
        corpus_path = _require_hash(
            self.repo / "knowledge/audio2tool/g5-exhaustive-family-contracts-v1/corpus.json",
            hashes.get("selected_tool_ground_corpus_sha256"),
            label="selected-tool corpus",
        )
        self.ground = _load_ground(corpus_path, assets.compatibility_rules)
        if self.ground.compatibility_sha256 != hashes.get(
            "selected_tool_compatibility_sha256"
        ):
            raise RuntimeError("frozen selected-tool compatibility SHA-256 drift")
        snapshot_path = _require_hash(
            self.repo
            / "knowledge/audio2tool/semantic-agentloop-runtime-v1/runner-snapshot.json",
            hashes.get("runner_snapshot_sha256"),
            label="inert runner snapshot",
        )
        self.snapshot = KnowledgeSnapshot.from_frozen_json(_read_json(snapshot_path))
        if (
            self.snapshot.source_partition_role != "external-governed"
            or self.snapshot.content_hash()
            != "93dde7c9eb029e77a03ca5fd91e6772e1931439d1fad5915264e92b69db99c8e"
        ):
            raise RuntimeError("inert runner snapshot identity drift")
        if set(self.verified_split.ids) & set(self.snapshot.source_sample_ids):
            raise RuntimeError("inert runner snapshot overlaps the fresh flight split")

        self.generation = self._generation_spec()
        self.embedding = self._embedding_spec()
        self.gate = FrozenCoreGate.for_study_repo(
            self.repo,
            self.data_root,
            self.runtime_root,
            runtime_receipt_relpath=str(runtime["generation_runtime_receipt"]),
            expected_model_lock_key=str(values["model_lock_key"]),
            model_root=Path(str(values["model_materialization_root"])),
            d1_media_supplement_relpath=d1_media_supplement_relpath(values),
            d1_media_supplement_sha256=d1_media_supplement_sha256(values),
        )
        self.embedding_gate = self.embedding_tool_module.build_embedding_gate(
            repo_root=self.repo,
            data_root=self.data_root,
            runtime_root=self.runtime_root,
            model_root=self.data_root,
            composed_values=values,
        )
        self.active: str | None = None
        self.session = None
        self.window_receipts: dict[str, Mapping[str, object]] = {}
        self.window_session_paths: dict[str, Path] = {}
        self.generation_media_markers: dict[str, str] = {}
        self.generation_props_hashes: dict[str, str] = {}
        self.transports: list[object] = []
        self.phase_states: dict[str, PhaseState] = {}
        self.embedding_instance = None
        self.embedding_tool_receipt: Mapping[str, object] | None = None

    def assert_contact_ready_preflight(self) -> Mapping[str, object]:
        """Validate every local input and gate without creating an attempt or service."""

        if self.mission_dir.exists():
            raise RuntimeError("one-shot mission directory already exists")
        for plan in self.plans.values():
            attempt = self.data_root / "attempts" / plan.run_id / f"{plan.attempt_id}.json"
            if attempt.exists():
                raise RuntimeError(f"one-shot attempt already exists: {plan.attempt_id}")
            self.gate.assert_model_touch_allowed(plan, full_hash=True)
        embedding_attempt = (
            self.data_root
            / "attempts"
            / self.embedding_plan.run_id
            / f"{self.embedding_plan.attempt_id}.json"
        )
        if embedding_attempt.exists():
            raise RuntimeError(
                f"one-shot embedding attempt already exists: {self.embedding_plan.attempt_id}"
            )
        self.embedding_gate.assert_model_touch_allowed(
            self.embedding_plan, full_hash=True
        )
        self.gate.verify_media_identity(
            AUDIO2TOOL_LOCK_KEY,
            {
                sample_id: (
                    self.binding.media_relpaths[sample_id],
                    self.binding.sample_facts[sample_id][0],
                )
                for sample_id in self.binding.allowed_sample_ids
            },
        )
        return {
            "schema": "saea-a2t-semantic-agentloop-contact-ready-preflight-v1",
            "status": "CONTACT_READY_NO_CONTACT",
            "run_id": self.authority["run_id"],
            "sample_count": len(self.samples),
            "generation_plan_count": len(self.plans),
            "embedding_logical_contact_count": self.embedding_plan.planned_model_calls,
            "embedding_plan_verified": True,
            "mission_absent": True,
            "attempts_absent": True,
            "d1_media_verified": True,
            "generation_gate_verified": True,
            "contacts_made": 0,
        }

    def _generation_spec(self) -> Mapping[str, object]:
        value = self.spec.get("generation")
        if not isinstance(value, Mapping):
            raise RuntimeError("generation service spec is missing")
        args = tuple(value.get("server_args", ()))
        if (
            value.get("base_url") != "http://127.0.0.1:8090"
            or tuple(args) != tuple(self.composed.values.get("server_args", ()))
            or args.count("-c") != 1
            or args[args.index("-c") + 1] != "65536"
            or args.count("-np") != 1
            or args[args.index("-np") + 1] != "2"
            or value.get("prompt_order") != "speech-query-prefix-v2"
            or value.get("decoding_params")
            != self.composed.values.get("decoding_params")
        ):
            raise RuntimeError("generation service must pin port 8090, -c 65536, -np 2")
        env = value.get("server_env")
        composed_env = self.composed.values.get("server_env")
        if (
            not isinstance(env, Mapping)
            or not isinstance(composed_env, Mapping)
            or env.get("LLAMA_SPEECH_FEATURE_ROOT") != str(self.packets.feature_root)
            or env.get("LLAMA_SPEECH_DECODER_SHA256")
            != composed_env.get("LLAMA_SPEECH_DECODER_SHA256")
            or set(env) != {"LLAMA_SPEECH_FEATURE_ROOT", "LLAMA_SPEECH_DECODER_SHA256"}
        ):
            raise RuntimeError("generation service does not bind promoted packet root")
        return value

    def _run_decoding(self) -> dict[str, object]:
        decoding = dict(self.generation["decoding_params"])
        decoding.pop("id_slot", None)
        if decoding != {"temperature": 0, "seed": 20260803, "max_tokens": 1024}:
            raise RuntimeError("generation decoding parameters drift")
        return decoding

    def _embedding_spec(self) -> Mapping[str, object]:
        value = self.spec.get("embedding")
        if not isinstance(value, Mapping):
            raise RuntimeError("embedding service spec is missing")
        args = tuple(value.get("server_args", ()))
        if (
            value.get("base_url") != "http://127.0.0.1:8082"
            or "--embedding" not in args
            or tuple(args)
            != (
                "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
                "-b", "4096", "-ub", "4096", "-np", "1", "-t", "16",
            )
            or value.get("expected_dim") != EMBEDDING_DIMENSION
            or value.get("physical_batch_size") != 32
        ):
            raise RuntimeError("embedding service must pin port 8082, last pooling, batch 32")
        return value

    def assert_attempt_unopened(self) -> None:
        for plan in (*self.plans.values(), self.embedding_plan):
            path = self.data_root / "attempts" / plan.run_id / f"{plan.attempt_id}.json"
            if path.exists():
                raise RuntimeError(f"one-shot attempt already exists: {plan.attempt_id}")
        self.mission_dir.mkdir(parents=True)
        _write_json(
            self.mission_dir / "authority-binding.json",
            {
                "authority_sha256": _sha256_json(self.authority),
                "protocol_config": self.protocol_config,
                "plans": {role: asdict(plan) for role, plan in self.plans.items()},
                "embedding_plan": asdict(self.embedding_plan),
            },
        )

    def _post_bytes(self, url: str, body: bytes, timeout: float) -> bytes:
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()

    def _get_json(self, url: str, timeout: float) -> Mapping[str, object]:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            raw = response.read()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError(f"invalid loopback service JSON from {url}") from error
        if not isinstance(value, Mapping):
            raise RuntimeError(f"loopback service JSON is not an object: {url}")
        return value

    def start_generation(self, window: str) -> None:
        if self.active is not None or window not in {"pre-embedding", "post-embedding"}:
            raise RuntimeError("generation service order or coexistence violation")
        service_dir = self.mission_dir / "services" / f"generation-{window}"
        session_path = service_dir / "session-receipt.json"
        self.session = start_session(
            runtime_root=self.runtime_root,
            data_root=self.data_root,
            runtime_receipt=self.generation_runtime_receipt,
            host="127.0.0.1",
            port=GENERATION_PORT,
            session_id=f"{self.authority['run_id']}-{window}",
            extra_argv=tuple(self.generation["server_args"]),
            extra_env=dict(self.generation["server_env"]),
            receipt_path=session_path,
            ready_timeout_seconds=float(self.generation.get("ready_timeout_seconds", 600)),
            server_log_path=service_dir / "server.log",
            role="inference",
            model_root=Path(str(self.composed.values["model_materialization_root"])),
        )
        props = self._get_json(
            f"http://127.0.0.1:{GENERATION_PORT}/props",
            float(self.generation.get("timeout_seconds", 900)),
        )
        marker = props.get("media_marker")
        settings = props.get("default_generation_settings")
        if (
            not isinstance(marker, str)
            or not marker
            or not marker.isascii()
            or not isinstance(settings, Mapping)
            or settings.get("n_ctx") != 32_768
        ):
            raise RuntimeError("generation /props lacks its live marker or 32,768 slot")
        self.generation_media_markers[window] = marker
        self.generation_props_hashes[window] = _sha256_json(props)
        self.active = f"generation:{window}"
        self.window_session_paths[window] = session_path

    def stop_generation(self, window: str) -> None:
        if self.active != f"generation:{window}" or self.session is None:
            raise RuntimeError("cannot stop an inactive generation service")
        stop_path = self.mission_dir / "services" / f"generation-{window}" / "stop-receipt.json"
        stop = stop_session(
            self.session,
            runtime_receipt=self.generation_runtime_receipt,
            runtime_root=self.runtime_root,
            force_after_timeout=True,
            receipt_path=stop_path,
        )
        self.window_receipts[window] = {
            "session_path": str(self.window_session_paths[window]),
            "session_sha256": _sha256_file(self.window_session_paths[window]),
            "stop_path": str(stop_path),
            "stop_sha256": _sha256_file(stop_path),
            "stop": stop,
            "props_sha256": self.generation_props_hashes[window],
            "media_marker_sha256": hashlib.sha256(
                self.generation_media_markers[window].encode("ascii")
            ).hexdigest(),
        }
        self.session = None
        self.active = None

    def start_embedding(self) -> None:
        if self.active is not None:
            raise RuntimeError("embedding service cannot coexist with generation")
        service_dir = self.mission_dir / "services" / "embedding"
        session_path = service_dir / "session-receipt.json"
        raw_client = EmbeddingClient(
            base_url="http://127.0.0.1:8082",
            timeout_seconds=float(self.embedding.get("timeout_seconds", 600)),
            expected_dim=EMBEDDING_DIMENSION,
            require_marker_verification=False,
        )
        self.embedding_instance = self.embedding_tool_module.GovernedEmbeddingClient(
            client=raw_client,
            gate=self.embedding_gate,
            plan=self.embedding_plan,
            preregistration_path=self.preregistration_path,
            preregistration_sha256=str(
                self.hashes["exposure_preregistration_sha256"]
            ),
            attempts_root=self.data_root / "attempts",
            receipt_path=service_dir / "governed-tool-receipt.json",
        )
        self.embedding_instance.open()
        try:
            self.session = start_session(
                runtime_root=self.runtime_root,
                data_root=self.data_root,
                runtime_receipt=self.embedding_runtime_receipt,
                host="127.0.0.1",
                port=EMBEDDING_PORT,
                session_id=f"{self.authority['run_id']}-embedding",
                extra_argv=tuple(self.embedding["server_args"]),
                receipt_path=session_path,
                ready_timeout_seconds=float(
                    self.embedding.get("ready_timeout_seconds", 1800)
                ),
                server_log_path=service_dir / "server.log",
                model_root=self.data_root,
            )
        except Exception:
            self.embedding_tool_receipt = self.embedding_instance.abort(
                "embedding service failed to start"
            )
            raise
        self.active = "embedding"
        self.window_session_paths["embedding"] = session_path

    def stop_embedding(self) -> None:
        if self.active != "embedding" or self.session is None:
            raise RuntimeError("cannot stop an inactive embedding service")
        if (
            self.embedding_instance is None
            or self.embedding_instance.physical_request_count != 7
            or self.embedding_instance.logical_contact_count != 208
        ):
            raise RuntimeError("embedding phase must make exactly seven physical requests")
        self.embedding_tool_receipt = self.embedding_instance.close()
        stop_path = self.mission_dir / "services" / "embedding" / "stop-receipt.json"
        stop = stop_session(
            self.session,
            runtime_receipt=self.embedding_runtime_receipt,
            runtime_root=self.runtime_root,
            force_after_timeout=True,
            receipt_path=stop_path,
        )
        self.window_receipts["embedding"] = {
            "session_path": str(self.window_session_paths["embedding"]),
            "session_sha256": _sha256_file(self.window_session_paths["embedding"]),
            "stop_path": str(stop_path),
            "stop_sha256": _sha256_file(stop_path),
            "stop": stop,
            "governed_tool_receipt_path": str(
                self.embedding_instance.receipt_path
            ),
            "governed_tool_receipt_sha256": _sha256_file(
                self.embedding_instance.receipt_path
            ),
            "governed_tool_receipt": self.embedding_tool_receipt,
        }
        self.session = None
        self.active = None
        if self.embedding_tool_receipt.get("status") != "FINALIZED":
            raise RuntimeError("governed embedding tool did not finalize")

    def _new_client(self, role: str, runner_phase: str, *, sink: bool) -> PhaseState:
        if not isinstance(self.active, str) or not self.active.startswith("generation:"):
            raise RuntimeError("generation transport is not active")
        timeout = float(self.generation.get("timeout_seconds", 900))

        def post_json(endpoint: str, payload: Mapping[str, object]) -> object:
            raw = self._post_bytes(
                f"http://127.0.0.1:{GENERATION_PORT}{endpoint}",
                _canonical_bytes(payload),
                timeout,
            )
            return json.loads(raw.decode("utf-8"))

        window = (
            "pre-embedding"
            if role in {"direct_m0", "obs_semantic_retrieval"}
            else "post-embedding"
        )
        marker = self.generation_media_markers.get(window)
        if not isinstance(marker, str) or not marker:
            raise RuntimeError("generation window lacks its live /props media marker")
        budget = self.launcher.ExactPromptBudgetTransport(
            media_marker=marker,
            speech_packet_tokens=self.packets.speech_tokens,
            post_json=post_json,
            send=lambda url, body: self._post_bytes(url, body, timeout),
            request_role=role,
            allow_missing_response_format=role == "direct_m0",
        )
        transport = LlamaServerTransport(
            base_url="http://127.0.0.1:8090",
            data_root=self.data_root,
            session=self.session,
            runtime_receipt=self.generation_runtime_receipt,
            runtime_root=self.runtime_root,
            timeout_seconds=timeout,
            post=budget,
            prompt_order="speech-query-prefix-v2",
            feature_root=self.packets.feature_root,
        )
        self.transports.append(budget)
        run_dir = self.mission_dir / role
        run_dir.mkdir(parents=True)
        plan = self.plans[role]
        client_dir = run_dir if not sink else run_dir / "transport-trace"
        client = FrozenCoreClient(
            plan=plan,
            gate=self.gate,
            transport=transport,
            run_dir=client_dir,
            binding=self.binding,
            arm=GENERATION_ARM,
            request_id_prefix=role.replace("_", "-"),
            speech_feature_root=self.packets.feature_root,
            speech_packet_bindings=self.packets.bindings,
        )
        state = PhaseState(
            role=role,
            runner_phase=runner_phase,
            plan=plan,
            run_dir=run_dir,
            session_receipt_path=self.window_session_paths[window],
            client=client,
            sink=TraceSink(run_dir, str(self.authority["run_id"])) if sink else None,
        )
        self.phase_states[role] = state
        return state

    def m0_kwargs(self, bindings: Mapping[str, object]) -> Mapping[str, object]:
        state = self._new_client("direct_m0", "M0_DIRECT", sink=False)
        return {
            "adapter": DirectAdapter(self.samples, self.task_contract),
            "core_client": state.client,
            "split_id": self.verified_split.name,
            "speech_packet_bindings": bindings,
            "slot_count": SLOT_COUNT,
            "decoding_params": self._run_decoding(),
        }

    def observation_kwargs(self, bindings: Mapping[str, object]) -> Mapping[str, object]:
        state = self._new_client("obs_semantic_retrieval", OBSERVATION_PHASE, sink=True)
        return {
            "data_root": self.data_root,
            "plan": state.plan,
            "adapter": FreshSemanticPhaseAdapter(
                split_id=self.verified_split.name,
                samples=self.samples,
                phase=OBSERVATION_PHASE,
                registered_tool_names=self.registered_tool_names,
            ),
            "core_client": state.client,
            "split_id": self.verified_split.name,
            "knowledge_snapshot": self.snapshot,
            "speech_packet_bindings": bindings,
            "trace_sink": state.sink,
            "decoding_params": self._run_decoding(),
        }

    def embedding_client(self) -> object:
        if self.active != "embedding" or self.embedding_instance is None:
            raise RuntimeError("embedding client requested outside its service window")
        return self.embedding_instance

    def semantic_index(self) -> ToolTierSemanticIndex:
        return self.index

    def selected_tool_ground(self) -> SelectedToolDecisionGround:
        return self.ground

    def use_kwargs(
        self,
        public_phase: str,
        material: Mapping[str, object],
        bindings: Mapping[str, object],
    ) -> Mapping[str, object]:
        roles = {
            self.launcher.TRANSCRIPT_USE_PHASE: "transcript_top16_use",
            self.launcher.MODEL_QUERY_USE_PHASE: "model_query_top16_use",
            self.launcher.RRF_FUSED_USE_PHASE: "rrf_fused_top16_use",
            self.launcher.SHUFFLED_FUSED_USE_PHASE: "same_stratum_shuffled_fused_use",
        }
        role = roles.get(public_phase)
        if role is None:
            raise RuntimeError("unknown public USE phase")
        runner_phase = (
            SHUFFLED_USE_PHASE
            if public_phase == self.launcher.SHUFFLED_FUSED_USE_PHASE
            else MATCHED_USE_PHASE
        )
        state = self._new_client(role, runner_phase, sink=True)
        return {
            "data_root": self.data_root,
            "plan": state.plan,
            "adapter": FreshSemanticPhaseAdapter(
                split_id=self.verified_split.name,
                samples=self.samples,
                phase=runner_phase,
                use_material=material,
            ),
            "core_client": state.client,
            "split_id": self.verified_split.name,
            "knowledge_snapshot": self.snapshot,
            "speech_packet_bindings": bindings,
            "trace_sink": state.sink,
            "decoding_params": self._run_decoding(),
        }

    def prompt_budget_audits(self) -> tuple[Mapping[str, object], ...]:
        return tuple(audit for transport in self.transports for audit in transport.audits)

    def seal_runtime_receipt(self, role: str, summary: object) -> Mapping[str, object]:
        state = self.phase_states[role]
        if state.client_summary is None:
            if state.sink is None:
                client_summary = state.client.close()
                trace_hash = client_summary.get("trace_manifest_hash")
            else:
                trace_hash = state.sink.close()
                client_summary = state.client.close()
            if not _is_sha256(trace_hash) or client_summary.get("request_count") != 104:
                raise RuntimeError(f"phase {role!r} trace/contact accounting drift")
            state.trace_manifest_hash = str(trace_hash)
            state.client_summary = client_summary
        window = "pre-embedding" if role in {"direct_m0", "obs_semantic_retrieval"} else "post-embedding"
        document = {
            "schema": "saea-a2t-semantic-agentloop-phase-runtime-receipt-v1",
            "role": role,
            "status": "STOPPED",
            "runner_phase": state.runner_phase,
            "plan": asdict(state.plan),
            "generation_window": self.window_receipts[window],
            "embedding_window": self.window_receipts.get("embedding"),
            "request_count": 104,
            "trace_manifest_sha256": state.trace_manifest_hash,
            "sealed_at": datetime.now(timezone.utc).isoformat(),
        }
        path = state.run_dir / "phase-runtime-receipt.json"
        _write_json(path, document)
        descriptor = {
            "role": role,
            "status": "STOPPED",
            "path": str(path),
            "sha256": _sha256_file(path),
        }
        state.runtime_receipt = descriptor
        return descriptor

    def seal_manifest(
        self, role: str, summary: object, extras: Mapping[str, object]
    ) -> Mapping[str, object]:
        state = self.phase_states[role]
        if state.runtime_receipt is None or state.client_summary is None:
            raise RuntimeError("phase runtime receipt must seal before its manifest")
        trace_dir = state.run_dir if state.sink is not None else state.run_dir
        trace_path = trace_dir / f"{self.authority['run_id']}.trace.jsonl"
        documents = tuple(
            json.loads(line)
            for line in trace_path.read_text(encoding="utf-8").splitlines()
            if line
        )
        rows, cost = _semantic_bundle_material(
            summary,
            documents,
            role=role,
            umbrella_lock_sha256=str(state.client_summary["cost"]["umbrella_lock_sha256"]),  # type: ignore[index]
        )
        outputs = state.run_dir / f"{self.authority['run_id']}.outputs.jsonl"
        _write_jsonl(outputs, rows)
        sidecar = state.run_dir / "semantic-trace.json"
        _write_json(
            sidecar,
            {
                "schema": "saea-a2t-semantic-agentloop-phase-trace-v1",
                "role": role,
                "extras": extras,
            },
        )
        result = RunResult(
            run_id=str(self.authority["run_id"]),
            arm=GENERATION_ARM,
            outputs_path=outputs,
            trace_manifest_hash=str(state.trace_manifest_hash),
            cost=cost,
        )
        manifest = build_manifest(
            repo_root=self.repo,
            data_root=self.data_root,
            composed=self.composed,
            plan=state.plan,
            verified_split=self.verified_split,
            session_receipt_path=state.session_receipt_path,
            run_dir=state.run_dir,
            status=STATUS_COMPLETED,
            result=result,
        )
        verified = verify_bundle(manifest)
        if len(verified.outputs_rows) != 104:
            raise RuntimeError(f"manifest {role!r} did not verify as 104 complete rows")
        return {
            "role": role,
            "status": "COMPLETE",
            "complete_rows": 104,
            "manifest": str(manifest),
            "manifest_sha256": _sha256_file(manifest),
            "runtime_receipt_sha256": state.runtime_receipt["sha256"],
            "semantic_trace": str(sidecar),
            "semantic_trace_sha256": _sha256_file(sidecar),
        }

    def seal_flight(
        self,
        descriptors: Sequence[Mapping[str, object]],
        events: Sequence[str],
        config_hash: str,
        protocol_hash_value: str,
    ) -> Mapping[str, object]:
        if self.active is not None or len(descriptors) != 6:
            raise RuntimeError("flight cannot seal with an active service or missing manifest")
        document = {
            "schema": "saea-a2t-semantic-agentloop-104-flight-receipt-v1",
            "status": "SEALED",
            "run_id": self.authority["run_id"],
            "config_sha256": config_hash,
            "protocol_sha256": protocol_hash_value,
            "generation_contacts": sum(
                state.client_summary["request_count"]  # type: ignore[index]
                for state in self.phase_states.values()
            ),
            "embedding_physical_requests": self.embedding_instance.http_request_count,
            "embedding_logical_contacts": self.embedding_instance.logical_contact_count,
            "embedding_tool_receipt_sha256": self.window_receipts["embedding"][
                "governed_tool_receipt_sha256"
            ],
            "service_events": list(events),
            "manifests": list(descriptors),
            "gold_opened": False,
            "scorer_started": False,
        }
        if (
            document["generation_contacts"] != 624
            or document["embedding_physical_requests"] != 7
            or document["embedding_logical_contacts"] != 208
        ):
            raise RuntimeError("sealed flight contact accounting drift")
        path = self.mission_dir / "flight-receipt.json"
        _write_json(path, document)
        return {**document, "path": str(path), "sha256": _sha256_file(path)}

    def abort_open_attempts(self, reason: str) -> None:
        if self.embedding_instance is not None and self.embedding_tool_receipt is None:
            try:
                self.embedding_tool_receipt = self.embedding_instance.abort(
                    "flight aborted after the embedding tool opened"
                )
            except Exception:
                pass
        if self.session is not None:
            window = self.active or "failure"
            stop_session(
                self.session,
                runtime_receipt=(
                    self.embedding_runtime_receipt
                    if self.active == "embedding"
                    else self.generation_runtime_receipt
                ),
                runtime_root=self.runtime_root,
                force_after_timeout=True,
                receipt_path=self.mission_dir / "services" / str(window) / "failure-stop.json",
            )
            self.session = None
            self.active = None
        for plan in self.plans.values():
            abort_attempt_if_opened(
                self.data_root, plan.run_id, plan.attempt_id, reason=reason
            )
        _write_json(
            self.mission_dir / "failure-receipt.json",
            {"status": "ABORTED", "reason": reason},
        )


def build_runtime(
    *,
    authority: Mapping[str, object],
    roster: object,
    packets: object,
    protocol_config: Mapping[str, object],
    launcher_module: object,
) -> LocalSemanticRuntime:
    """Factory entry point consumed by ``--runtime-factory``."""

    return LocalSemanticRuntime(
        authority=authority,
        roster=roster,
        packets=packets,
        protocol_config=protocol_config,
        launcher_module=launcher_module,
    )


__all__ = [
    "LocalSemanticRuntime",
    "build_direct_task_contract",
    "build_runtime",
    "parse_execution_plans",
]
