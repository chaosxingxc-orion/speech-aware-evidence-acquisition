"""Source-free G5 corpus, fixed16 runtime, and prompt-fit integration.

The module reads only frozen construction-corpus bytes, identity receipts, and
sealed speech-packet metadata.  It does not read task text, labels, outputs, or
audio samples and it has no model, tokenizer, scorer, or network capability.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..adapters.audio2tool import Audio2ToolSample
from ..knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from ..obs import AudioRef
from .a2t_g5_agentloop import (
    BUNDLE_ASCII_BYTE_CAP,
    DEFAULT_SPECIAL_TOKEN_RESERVE,
    EXECUTE_COMPLETION_TOKENS,
    PER_SLOT_PROMPT_TOKENS,
    PLAN_COMPLETION_TOKENS,
    PLAN_STATE_ASCII_BYTE_CAP,
    CompiledContract,
    CompiledFamilyBundle,
    FamilyTaxon,
    G5AgentLoopAdapter,
    ParsedPlan,
    _EXECUTE_INSTRUCTION,
    _PLAN_INSTRUCTION,
)


COMMITTED_CORPUS_SHA256 = (
    "92684a16e39985d3c4c6e7e6d62ac54feaa357eaa7c24c744df21950e51f95e5"
)
COMMITTED_G1_RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
COMMITTED_FIXED16_IDENTITY_SHA256 = (
    "81e3703f0529882c943f71dbe213e1c2d9bcd4e9b00fabf51e5499bae3501ffe"
)
COMMITTED_G1_PROMOTION_SHA256 = (
    "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
)

G5_FIXED16_SPLIT_ID = "A2T-G5-FIXED16"
OPERATION_TAG = "execute"
FALLBACK_FAMILY_TAGS = (
    "smart-car-charging-energy",
    "smart-home-maintenance",
    "wearables-device-state",
)
SOURCE_FIELDS = (
    "audio_seconds",
    "audio_sha256",
    "key",
    "media_relpath",
    "packet_id",
    "sample_id",
    "tier",
)


class G5CorpusIntegrationError(RuntimeError):
    """A frozen corpus, runtime identity, packet, or fit invariant failed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_ascii_json(path: Path, *, label: str) -> tuple[bytes, Mapping[str, object]]:
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("ascii")
        document = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise G5CorpusIntegrationError(f"{label} must be ASCII JSON") from error
    if not isinstance(document, Mapping):
        raise G5CorpusIntegrationError(f"{label} must be a JSON object")
    return raw, document


def _require_hash(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise G5CorpusIntegrationError(f"{label} must be lowercase 64-hex")
    return value


def _exact_family_bundle(
    corpus: Mapping[str, object], family_tags: Sequence[str]
) -> bytes:
    taxonomy = corpus.get("taxonomy")
    contracts = corpus.get("contracts")
    canonicalizers = corpus.get("canonicalizers")
    if (
        not isinstance(taxonomy, list)
        or not isinstance(contracts, list)
        or not isinstance(canonicalizers, Mapping)
    ):
        raise G5CorpusIntegrationError("corpus family surfaces are malformed")
    labels: dict[str, str] = {}
    for row in taxonomy:
        if not isinstance(row, Mapping):
            raise G5CorpusIntegrationError("corpus taxonomy row is malformed")
        tag = row.get("tag")
        label = row.get("label")
        if not isinstance(tag, str) or not tag or not isinstance(label, str) or not label:
            raise G5CorpusIntegrationError("corpus taxonomy text is malformed")
        if tag in labels:
            raise G5CorpusIntegrationError("corpus taxonomy tags are not unique")
        labels[tag] = label
    tags = tuple(family_tags)
    if not tags or len(set(tags)) != len(tags) or not set(tags).issubset(labels):
        raise G5CorpusIntegrationError("requested corpus family tags are invalid")
    selected_contracts = [
        row
        for row in contracts
        if isinstance(row, Mapping) and row.get("family_tag") in set(tags)
    ]
    payload = {
        "schema": "saea-exhaustive-action-family-bundle-v1",
        "families": [{"tag": tag, "label": labels[tag]} for tag in tags],
        "output": "Return only a JSON array of exact registered tool calls.",
        "canonicalizers": dict(canonicalizers),
        "contracts": selected_contracts,
    }
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    ).encode("ascii")


@dataclass(frozen=True)
class CorpusFamilyRecord:
    """One exact standalone exhaustive family aggregate."""

    tag: str
    label: str
    tool_names: tuple[str, ...]
    bundle_bytes: bytes
    bundle_sha256: str
    facet_id: str
    value_id: str
    contract_id: str
    representation: str

    @property
    def tool_count(self) -> int:
        return len(self.tool_names)


class CorpusFamilyCompiler:
    """Adapt the frozen exhaustive corpus to the G5 AgentLoop protocol."""

    def __init__(
        self,
        *,
        corpus_sha256: str,
        family_records: Mapping[str, CorpusFamilyRecord],
    ) -> None:
        records = dict(family_records)
        if not records:
            raise G5CorpusIntegrationError("corpus compiler requires family records")
        self.corpus_sha256 = _require_hash(corpus_sha256, label="corpus SHA-256")
        self.family_records = records
        self.taxonomy = tuple(
            FamilyTaxon(tag, (OPERATION_TAG,)).validate() for tag in sorted(records)
        )
        self.fallback_family_tags = FALLBACK_FAMILY_TAGS
        if not set(self.fallback_family_tags).issubset(records):
            raise G5CorpusIntegrationError("fallback families are absent from the corpus")
        self.registered_tool_names = tuple(
            name
            for tag in sorted(records)
            for name in records[tag].tool_names
        )
        if len(set(self.registered_tool_names)) != len(self.registered_tool_names):
            raise G5CorpusIntegrationError("registered tools are not uniquely assigned")
        source_id = f"source:g5-construction-corpus:{self.corpus_sha256}"
        self.snapshot = KnowledgeSnapshot(
            snapshot_id=f"a2t-g5-family-aggregates:{self.corpus_sha256[:16]}",
            source_split_identity_hash=self.corpus_sha256,
            source_sample_ids=(source_id,),
            source_partition_role=EXTERNAL_GOVERNED_PARTITION_ROLE,
            builder_policy_id="g5-exhaustive-family-corpus-adapter-v1",
            facets=tuple(
                KeyFacet(
                    facet_id=record.facet_id,
                    dimension="action-family",
                    representation_kind="closed-construction-family",
                    representation=record.representation,
                    source_sample_ids=(source_id,),
                )
                for record in records.values()
            ),
            values=tuple(
                ValueBundle(
                    value_id=record.value_id,
                    content=record.bundle_bytes.decode("ascii"),
                    associated_facet_ids=(record.facet_id,),
                    source_sample_ids=(source_id,),
                    provenance_refs=(
                        f"corpus-sha256:{self.corpus_sha256}",
                        f"family-bundle-sha256:{record.bundle_sha256}",
                    ),
                )
                for record in records.values()
            ),
        ).validate()
        self.compile(
            ParsedPlan(
                valid=False,
                status="INVALID_FALLBACK",
                operations=(),
                selected_family_tags=self.fallback_family_tags,
                canonical_json='{"operations":[],"status":"INVALID_FALLBACK"}',
            )
        )

    @classmethod
    def from_path(cls, path: Path) -> "CorpusFamilyCompiler":
        raw, document = _read_ascii_json(path, label="G5 corpus")
        corpus_sha256 = _sha256_bytes(raw)
        if document.get("schema") != "saea-action-family-contract-corpus-v1":
            raise G5CorpusIntegrationError("G5 corpus schema drift")
        taxonomy = document.get("taxonomy")
        contracts = document.get("contracts")
        families = document.get("families")
        if not isinstance(taxonomy, list) or not isinstance(contracts, list) or not isinstance(
            families, list
        ):
            raise G5CorpusIntegrationError("G5 corpus collections are malformed")
        family_rows: dict[str, Mapping[str, object]] = {}
        for row in families:
            if not isinstance(row, Mapping) or not isinstance(row.get("tag"), str):
                raise G5CorpusIntegrationError("G5 family record is malformed")
            tag = str(row["tag"])
            if tag in family_rows:
                raise G5CorpusIntegrationError("G5 family records are duplicated")
            family_rows[tag] = row
        label_by_tag = {
            str(row["tag"]): str(row["label"])
            for row in taxonomy
            if isinstance(row, Mapping)
            and isinstance(row.get("tag"), str)
            and isinstance(row.get("label"), str)
        }
        if len(label_by_tag) != len(taxonomy) or set(label_by_tag) != set(family_rows):
            raise G5CorpusIntegrationError("G5 taxonomy and family identities disagree")
        tool_names_by_tag: dict[str, list[str]] = {tag: [] for tag in label_by_tag}
        for row in contracts:
            if not isinstance(row, Mapping):
                raise G5CorpusIntegrationError("G5 action contract is malformed")
            tag = row.get("family_tag")
            tool_name = row.get("tool_name")
            if tag not in tool_names_by_tag or not isinstance(tool_name, str) or not tool_name:
                raise G5CorpusIntegrationError("G5 contract family/tool binding is malformed")
            tool_names_by_tag[str(tag)].append(tool_name)
        records: dict[str, CorpusFamilyRecord] = {}
        for tag in sorted(label_by_tag):
            row = family_rows[tag]
            bundle = _exact_family_bundle(document, (tag,))
            bundle_sha256 = _sha256_bytes(bundle)
            if (
                row.get("bundle_sha256") != bundle_sha256
                or row.get("bundle_utf8_bytes") != len(bundle)
                or tuple(row.get("tool_names", ())) != tuple(tool_names_by_tag[tag])
            ):
                raise G5CorpusIntegrationError(f"exact family aggregate drift for {tag!r}")
            short = bundle_sha256[:16]
            records[tag] = CorpusFamilyRecord(
                tag=tag,
                label=label_by_tag[tag],
                tool_names=tuple(tool_names_by_tag[tag]),
                bundle_bytes=bundle,
                bundle_sha256=bundle_sha256,
                facet_id=f"facet:g5:{short}",
                value_id=f"value:g5:{short}",
                contract_id=f"g5:{short}",
                representation=f"Closed action family {label_by_tag[tag]} ({tag}).",
            )
        return cls(corpus_sha256=corpus_sha256, family_records=records)

    def compile(self, plan: ParsedPlan) -> CompiledFamilyBundle:
        """Return one complete exact aggregate per requested family, in order."""

        if not isinstance(plan, ParsedPlan):
            raise G5CorpusIntegrationError("compiler input must be a parsed G5 plan")
        tags = plan.selected_family_tags
        if not tags or len(set(tags)) != len(tags) or not set(tags).issubset(
            self.family_records
        ):
            raise G5CorpusIntegrationError("compiled family request is outside the corpus")
        bundle = CompiledFamilyBundle(
            family_tags=tags,
            contracts=tuple(
                CompiledContract(
                    contract_id=self.family_records[tag].contract_id,
                    family_tag=tag,
                    facet_id=self.family_records[tag].facet_id,
                    value_id=self.family_records[tag].value_id,
                    content=self.family_records[tag].bundle_bytes.decode("ascii"),
                )
                for tag in tags
            ),
            complete=True,
            selection_mode="full-unranked-compatible",
        )
        return bundle.validate(requested_family_tags=tags)


@dataclass(frozen=True)
class G5Fixed16RuntimeSurface:
    """Identity-only original-speech and sealed-packet runtime surface."""

    split_id: str
    split_identity_hash: str
    samples: tuple[Audio2ToolSample, ...]
    packet_bindings: Mapping[str, Mapping[str, str]]
    speech_feature_tokens_by_sample: Mapping[str, int]
    source_hashes: Mapping[str, str]
    surface_sha256: str
    source_field_names: tuple[str, ...] = SOURCE_FIELDS


def _identity_rows(document: Mapping[str, object]) -> tuple[tuple[str, str, str], ...]:
    tiers = document.get("tiers")
    if not isinstance(tiers, Mapping):
        raise G5CorpusIntegrationError("fixed16 tier identities are malformed")
    rows: list[tuple[str, str, str]] = []
    for tier in sorted(tiers):
        items = tiers[tier]
        if not isinstance(tier, str) or not isinstance(items, list):
            raise G5CorpusIntegrationError("fixed16 tier row is malformed")
        for item in items:
            if not isinstance(item, Mapping):
                raise G5CorpusIntegrationError("fixed16 identity row is malformed")
            sample_id = item.get("sample_id")
            key = item.get("key")
            if (
                not isinstance(sample_id, str)
                or not isinstance(key, str)
                or not sample_id.startswith(f"{tier}:")
            ):
                raise G5CorpusIntegrationError("fixed16 identity disagrees with tier")
            rows.append((tier, sample_id, key))
    return tuple(sorted(rows, key=lambda row: (row[0], row[1])))


def load_fixed16_runtime_surface(
    *,
    g1_receipt_path: Path,
    fixed16_identity_path: Path,
    promotion_receipt_path: Path,
    expected_g1_sha256: str | None = None,
    expected_fixed16_sha256: str | None = None,
    expected_promotion_sha256: str | None = None,
) -> G5Fixed16RuntimeSurface:
    """Build fixed16 samples and packet bindings without opening speech bytes."""

    g1_raw, g1 = _read_ascii_json(g1_receipt_path, label="G1 identity receipt")
    fixed_raw, fixed = _read_ascii_json(
        fixed16_identity_path, label="G5 fixed16 identity receipt"
    )
    promotion_raw, promotion = _read_ascii_json(
        promotion_receipt_path, label="G1 promotion receipt"
    )
    source_hashes = {
        "g1_receipt_sha256": _sha256_bytes(g1_raw),
        "fixed16_identity_sha256": _sha256_bytes(fixed_raw),
        "promotion_receipt_sha256": _sha256_bytes(promotion_raw),
    }
    for key, expected in (
        ("g1_receipt_sha256", expected_g1_sha256),
        ("fixed16_identity_sha256", expected_fixed16_sha256),
        ("promotion_receipt_sha256", expected_promotion_sha256),
    ):
        if expected is not None and source_hashes[key] != expected:
            raise G5CorpusIntegrationError(f"{key} drift")
    if g1.get("schema") != "saea-a2t-subset-receipt-v1":
        raise G5CorpusIntegrationError("G1 identity receipt schema drift")
    if fixed.get("schema") != "saea-a2t-g5-fixed16-identity-receipt-v1":
        raise G5CorpusIntegrationError("G5 fixed16 identity schema drift")
    if fixed.get("split_name") != G5_FIXED16_SPLIT_ID:
        raise G5CorpusIntegrationError("G5 fixed16 split identity drift")
    selection = fixed.get("selection")
    if not isinstance(selection, Mapping) or selection.get("uses_task_text") is not False:
        raise G5CorpusIntegrationError("fixed16 selection is not task-text-free")
    rows = _identity_rows(fixed)
    if len(rows) != 16 or selection.get("selected_count") != 16:
        raise G5CorpusIntegrationError("G5 fixed16 identity must contain sixteen rows")
    canonical = "".join(f"{tier}\t{sample_id}\n" for tier, sample_id, _key in rows)
    split_hash = _sha256_bytes(canonical.encode("ascii"))
    if fixed.get("split_identity_hash") != split_hash:
        raise G5CorpusIntegrationError("G5 fixed16 canonical identity hash drift")
    g1_items = g1.get("items")
    if not isinstance(g1_items, list):
        raise G5CorpusIntegrationError("G1 identity rows are malformed")
    g1_by_id = {
        row.get("sample_id"): row for row in g1_items if isinstance(row, Mapping)
    }
    if len(g1_by_id) != len(g1_items):
        raise G5CorpusIntegrationError("G1 sample identities are malformed")
    promotion_rows = promotion.get("packets")
    if not isinstance(promotion_rows, list):
        raise G5CorpusIntegrationError("G1 promotion packet rows are malformed")
    promotion_by_id = {
        row.get("packet_id"): row
        for row in promotion_rows
        if isinstance(row, Mapping) and isinstance(row.get("packet_id"), str)
    }
    if len(promotion_by_id) != len(promotion_rows):
        raise G5CorpusIntegrationError("G1 promotion packet identities are malformed")
    if promotion.get("subset_receipt_sha256") != source_hashes["g1_receipt_sha256"]:
        raise G5CorpusIntegrationError("G1 promotion receipt is bound to another identity")

    packet_root = Path(promotion_receipt_path).resolve().parent
    samples: list[Audio2ToolSample] = []
    bindings: dict[str, Mapping[str, str]] = {}
    speech_tokens: dict[str, int] = {}
    surface_rows: list[dict[str, object]] = []
    for tier, sample_id, key in rows:
        item = g1_by_id.get(sample_id)
        if not isinstance(item, Mapping) or item.get("key") != key or item.get("tier") != tier:
            raise G5CorpusIntegrationError("fixed16 identity is absent from G1")
        packet_id = item.get("packet_id")
        media_relpath = item.get("media_relpath")
        audio_sha256 = item.get("audio_sha256")
        audio_seconds = item.get("audio_seconds")
        if (
            not isinstance(packet_id, str)
            or not packet_id
            or Path(packet_id).is_absolute()
            or ".." in Path(packet_id).parts
            or not isinstance(media_relpath, str)
            or not media_relpath
            or Path(media_relpath).is_absolute()
            or not isinstance(audio_seconds, (int, float))
            or isinstance(audio_seconds, bool)
            or float(audio_seconds) <= 0
        ):
            raise G5CorpusIntegrationError("G1 runtime media identity is malformed")
        audio_hash = _require_hash(audio_sha256, label="G1 audio SHA-256")
        promoted = promotion_by_id.get(packet_id)
        if not isinstance(promoted, Mapping) or promoted.get("audio_sha256") != audio_hash:
            raise G5CorpusIntegrationError("sealed packet and G1 audio identity disagree")
        packet_hash = _require_hash(
            promoted.get("packet_sha256"), label="promoted packet SHA-256"
        )
        packet_path = (packet_root / packet_id / "packet.json").resolve()
        if not packet_path.is_relative_to(packet_root) or not packet_path.is_file():
            raise G5CorpusIntegrationError("sealed packet metadata is unavailable")
        _packet_raw, packet = _read_ascii_json(packet_path, label="speech packet")
        chunks = packet.get("chunks")
        if (
            packet.get("schema") != "saea-speech-feature-packet-v1"
            or packet.get("packet_id") != packet_id
            or packet.get("packet_sha256") != packet_hash
            or packet.get("audio_sha256") != audio_hash
            or not isinstance(chunks, list)
            or not chunks
        ):
            raise G5CorpusIntegrationError("sealed packet metadata drift")
        feature_tokens = 0
        for chunk in chunks:
            count = chunk.get("n_tokens") if isinstance(chunk, Mapping) else None
            if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
                raise G5CorpusIntegrationError("sealed speech token count is malformed")
            feature_tokens += count
        samples.append(
            Audio2ToolSample(
                sample_id=sample_id,
                audio_ref=AudioRef(path=media_relpath, sha256=audio_hash).validate(),
                audio_seconds=float(audio_seconds),
                media_relpath=media_relpath,
            )
        )
        bindings[sample_id] = {"packet_id": packet_id, "sha256": packet_hash}
        speech_tokens[sample_id] = feature_tokens
        surface_rows.append(
            {
                "sample_id": sample_id,
                "media_relpath": media_relpath,
                "audio_sha256": audio_hash,
                "packet_id": packet_id,
                "packet_sha256": packet_hash,
                "speech_feature_tokens": feature_tokens,
            }
        )
    surface_sha256 = _sha256_bytes(
        json.dumps(surface_rows, sort_keys=True, separators=(",", ":")).encode("ascii")
    )
    return G5Fixed16RuntimeSurface(
        split_id=G5_FIXED16_SPLIT_ID,
        split_identity_hash=split_hash,
        samples=tuple(samples),
        packet_bindings=dict(sorted(bindings.items())),
        speech_feature_tokens_by_sample=dict(sorted(speech_tokens.items())),
        source_hashes=source_hashes,
        surface_sha256=surface_sha256,
    )


def _worst_compatible_family_union(
    compiler: CorpusFamilyCompiler,
) -> tuple[CompiledFamilyBundle, int]:
    """Exact additive search for the largest compatible EXECUTE text surface."""

    # State: rendered bundle bytes including a virtual trailing newline ->
    # (execute family text bytes, selected tags).  Keeping the best objective
    # per exact bundle size is an exact 0/1 dynamic program, not ranking.
    states: dict[int, tuple[int, tuple[str, ...]]] = {0: (0, ())}
    for taxon in compiler.taxonomy:
        tag = taxon.family_tag
        record = compiler.family_records[tag]
        single = compiler.compile(
            ParsedPlan(True, "VALID", (), (tag,), '{"operations":[]}')
        )
        bundle_weight = len(single.render().encode("ascii")) + 1
        objective_weight = bundle_weight + len(record.representation.encode("ascii"))
        for used, (objective, selected) in tuple(states.items()):
            candidate_size = used + bundle_weight
            rendered_size = candidate_size - 1
            if rendered_size > BUNDLE_ASCII_BYTE_CAP:
                continue
            candidate = (objective + objective_weight, selected + (tag,))
            current = states.get(candidate_size)
            if current is None or candidate[0] > current[0] or (
                candidate[0] == current[0] and candidate[1] < current[1]
            ):
                states[candidate_size] = candidate
    _objective, tags = max(
        states.values(), key=lambda item: (item[0], tuple(reversed(item[1])))
    )
    bundle = compiler.compile(ParsedPlan(True, "VALID", (), tags, '{"operations":[]}'))
    facet_bytes = sum(
        len(compiler.family_records[tag].representation.encode("ascii")) for tag in tags
    )
    return bundle, facet_bytes


def build_prompt_fit_report(
    *,
    compiler: CorpusFamilyCompiler,
    runtime: G5Fixed16RuntimeSurface,
) -> dict[str, object]:
    """Measure exact ASCII bytes and a receipt-bound conservative token ceiling."""

    adapter = G5AgentLoopAdapter(
        runtime.samples,
        split_id=runtime.split_id,
        taxonomy=compiler.taxonomy,
    )
    task_contract = adapter.build_task_contract(runtime.samples[0], None)
    maximum_speech = max(runtime.speech_feature_tokens_by_sample.values())
    maximum_speech_sample = min(
        sample_id
        for sample_id, count in runtime.speech_feature_tokens_by_sample.items()
        if count == maximum_speech
    )
    plan_text_bytes = sum(
        len(text.encode("ascii")) for text in (task_contract, _PLAN_INSTRUCTION)
    )
    worst_bundle, facet_bytes = _worst_compatible_family_union(compiler)
    execute_text_bytes = sum(
        (
            len(task_contract.encode("ascii")),
            len(_EXECUTE_INSTRUCTION.encode("ascii")),
            PLAN_STATE_ASCII_BYTE_CAP,
            len(worst_bundle.render().encode("ascii")),
            facet_bytes,
        )
    )

    def envelope(text_bytes: int, completion: int) -> int:
        return (
            text_bytes
            + maximum_speech
            + DEFAULT_SPECIAL_TOKEN_RESERVE
            + completion
        )

    plan_envelope = envelope(plan_text_bytes, PLAN_COMPLETION_TOKENS)
    execute_envelope = envelope(execute_text_bytes, EXECUTE_COMPLETION_TOKENS)
    fallback = compiler.compile(
        ParsedPlan(
            False,
            "INVALID_FALLBACK",
            (),
            compiler.fallback_family_tags,
            '{"operations":[],"status":"INVALID_FALLBACK"}',
        )
    )
    status = (
        "PASS"
        if max(plan_envelope, execute_envelope) <= PER_SLOT_PROMPT_TOKENS
        else "FAIL"
    )
    return {
        "schema": "saea-a2t-g5-fixed16-model-free-prompt-fit-v1",
        "status": status,
        "sources": {
            "corpus_sha256": compiler.corpus_sha256,
            **dict(runtime.source_hashes),
        },
        "runtime": {
            "split_id": runtime.split_id,
            "split_identity_hash": runtime.split_identity_hash,
            "sample_count": len(runtime.samples),
            "runtime_surface_sha256": runtime.surface_sha256,
            "maximum_speech_feature_tokens": maximum_speech,
            "maximum_speech_feature_tokens_sample_id": maximum_speech_sample,
            "source_fields_read": list(runtime.source_field_names),
            "task_text_fields_read": 0,
            "gold_fields_read": 0,
            "outputs_read": 0,
            "test_rows_read": 0,
            "fresh_rows_read": 0,
        },
        "corpus": {
            "family_count": len(compiler.taxonomy),
            "tool_count": len(compiler.registered_tool_names),
            "operation_tag": OPERATION_TAG,
            "contract_entries_per_requested_family": 1,
            "ranking_or_pruning_applied": False,
            "taxonomy_sha256": _sha256_bytes(
                json.dumps(
                    [(row.family_tag, row.operation_tags) for row in compiler.taxonomy],
                    separators=(",", ":"),
                ).encode("ascii")
            ),
            "knowledge_snapshot_sha256": compiler.snapshot.content_hash(),
        },
        "fallback": {
            "selection_basis": (
                "construction-only maximum tool coverage with at least one family "
                "from smart-car, smart-home, and wearables under the rendered bundle cap"
            ),
            "family_tags": list(compiler.fallback_family_tags),
            "family_count": len(compiler.fallback_family_tags),
            "tool_count": sum(
                compiler.family_records[tag].tool_count
                for tag in compiler.fallback_family_tags
            ),
            "registry_tool_coverage": sum(
                compiler.family_records[tag].tool_count
                for tag in compiler.fallback_family_tags
            )
            / len(compiler.registered_tool_names),
            "rendered_ascii_bytes": len(fallback.render().encode("ascii")),
            "content_sha256": fallback.content_hash(),
        },
        "accounting": {
            "method": "exact ASCII bytes with a conservative ceiling of one text token per byte",
            "ascii_bytes_per_text_token_ceiling": 1,
            "speech_tokens_source": "sealed packet chunk n_tokens",
            "special_token_reserve": DEFAULT_SPECIAL_TOKEN_RESERVE,
            "per_slot_token_limit": PER_SLOT_PROMPT_TOKENS,
            "tokenizer_contacts": 0,
        },
        "plan": {
            "message_ascii_bytes": plan_text_bytes,
            "speech_feature_tokens": maximum_speech,
            "completion_reserve_tokens": PLAN_COMPLETION_TOKENS,
            "maximum_envelope_tokens": plan_envelope,
            "margin_tokens": PER_SLOT_PROMPT_TOKENS - plan_envelope,
        },
        "execute": {
            "message_ascii_bytes": execute_text_bytes,
            "state_ascii_bytes": PLAN_STATE_ASCII_BYTE_CAP,
            "bundle_ascii_bytes": len(worst_bundle.render().encode("ascii")),
            "family_facet_ascii_bytes": facet_bytes,
            "worst_compatible_family_tags": list(worst_bundle.family_tags),
            "bundle_content_sha256": worst_bundle.content_hash(),
            "speech_feature_tokens": maximum_speech,
            "completion_reserve_tokens": EXECUTE_COMPLETION_TOKENS,
            "maximum_envelope_tokens": execute_envelope,
            "margin_tokens": PER_SLOT_PROMPT_TOKENS - execute_envelope,
        },
        "contacts": {
            "frozen_core": 0,
            "network": 0,
            "retriever": 0,
            "tokenizer": 0,
            "scorer": 0,
        },
    }


__all__ = [
    "COMMITTED_CORPUS_SHA256",
    "COMMITTED_FIXED16_IDENTITY_SHA256",
    "COMMITTED_G1_PROMOTION_SHA256",
    "COMMITTED_G1_RECEIPT_SHA256",
    "FALLBACK_FAMILY_TAGS",
    "G5_FIXED16_SPLIT_ID",
    "CorpusFamilyCompiler",
    "CorpusFamilyRecord",
    "G5CorpusIntegrationError",
    "G5Fixed16RuntimeSurface",
    "build_prompt_fit_report",
    "load_fixed16_runtime_surface",
]
