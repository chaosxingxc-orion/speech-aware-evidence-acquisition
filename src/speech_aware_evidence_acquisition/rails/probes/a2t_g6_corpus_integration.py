"""Contact-free corpus and runtime integration for the frozen G6 sweep.

The adapter maps the already validated construction corpus into the pure G6
core.  It reads only identity receipts and sealed packet metadata for runtime
assembly.  It has no model, network, retriever, scorer, audio-decoding, task
text, gold, output, or reward capability.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..adapters.audio2tool import Audio2ToolSample
from ..obs import AudioRef
from .a2t_g6_corpus_renderer import G6Contract, G6CorpusRenderer
from .a2t_g6_family_sweep import (
    FAMILY_COUNT,
    OPERATIONAL_HEADROOM_TOKENS,
    PER_SLOT_CONTEXT_TOKENS,
    ArgumentSpec,
    ContactContext,
    FamilyBundle,
    G6FamilySweep,
    ToolContract,
)


COMMITTED_CORPUS_SHA256 = (
    "92684a16e39985d3c4c6e7e6d62ac54feaa357eaa7c24c744df21950e51f95e5"
)
COMMITTED_G1_RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
COMMITTED_G6_ROSTER_SHA256 = (
    "fcc8350312710b6a5831185e265a3b92fe619279acd0924da7b83268b07ff25b"
)
COMMITTED_G1_PROMOTION_SHA256 = (
    "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
)

G6_FIXED16_SPLIT_ID = "A2T-G6-FAMILY-SWEEP-FIXED16"
G6_MAX_FINAL_CALLS = 5
SOURCE_FIELDS = (
    "audio_seconds",
    "audio_sha256",
    "key",
    "media_relpath",
    "packet_id",
    "sample_id",
    "tier",
)
_SELECTION_PROHIBITION_FLAGS = (
    "uses_task_text",
    "uses_audio",
    "uses_gold",
    "uses_outputs",
    "uses_scores",
    "uses_rewards",
    "uses_test",
    "uses_future_turns",
    "uses_model_or_tool",
    "uses_network_or_tokenizer_or_scorer",
)


class G6CorpusIntegrationError(RuntimeError):
    """A corpus mapping, roster, packet, or prompt-fit invariant failed."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_ascii_json(path: Path, *, label: str) -> tuple[bytes, Mapping[str, object]]:
    raw = Path(path).read_bytes()
    try:
        document = json.loads(raw.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise G6CorpusIntegrationError(f"{label} must be ASCII JSON") from error
    if not isinstance(document, Mapping):
        raise G6CorpusIntegrationError(f"{label} must be a JSON object")
    return raw, document


def _require_hash(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise G6CorpusIntegrationError(f"{label} must be lowercase 64-hex")
    return value


def _identity(value: object) -> object:
    return value


def _boolean(value: object) -> object:
    if isinstance(value, str) and value.casefold() in {"true", "false"}:
        return value.casefold() == "true"
    return value


_CANONICALIZERS: Mapping[str, Callable[[object], object]] = {
    "boolean": _boolean,
    "null": _identity,
    "url": _identity,
    "entity": _identity,
    "list": _identity,
    "period": _identity,
    "nested-schedule": _identity,
}


def _required_keys(contract: G6Contract) -> set[str]:
    skeletons = contract.legal_key_skeletons
    if not skeletons:
        raise G6CorpusIntegrationError("corpus contract lacks legal key skeletons")
    return set(skeletons[0]).intersection(*map(set, skeletons[1:]))


def _reference_parts(reference: str) -> tuple[str, tuple[str, ...]]:
    marker = "\n\nContract: "
    prefix, separator, tail = reference.partition(marker)
    if not separator:
        raise G6CorpusIntegrationError("rendered family reference lacks contracts")
    blocks = tuple("Contract: " + part.rstrip("\n") for part in tail.split(marker))
    if not prefix or not blocks:
        raise G6CorpusIntegrationError("rendered family reference is malformed")
    return prefix, blocks


class G6CorpusAdapter:
    """Map each frozen family into one bundle of contract-local core records."""

    def __init__(self, renderer: G6CorpusRenderer) -> None:
        if not isinstance(renderer, G6CorpusRenderer):
            raise G6CorpusIntegrationError("adapter requires a G6CorpusRenderer")
        self.renderer = renderer
        self.corpus_sha256 = renderer.corpus_sha256
        bundles: list[FamilyBundle] = []
        reference_hashes: dict[str, str] = {}
        for family_tag in renderer.family_tags:
            reference = renderer.render_family(family_tag)
            prefix, content_blocks = _reference_parts(reference)
            # The validated renderer owns this immutable registry.  Reading its
            # family-local tuple avoids reparsing or independently trusting the
            # corpus bytes in the integration layer.
            source_contracts = renderer._contracts_by_family[family_tag]
            if len(source_contracts) != len(content_blocks):
                raise G6CorpusIntegrationError("family reference and registry disagree")
            contracts: list[ToolContract] = []
            for index, (source, block) in enumerate(
                zip(source_contracts, content_blocks, strict=True)
            ):
                required = _required_keys(source)
                content = f"{prefix}\n\n{block}" if index == 0 else block
                contracts.append(
                    ToolContract(
                        contract_id=source.contract_id,
                        family_tag=source.family_tag,
                        tool_name=source.tool_name,
                        arguments=tuple(
                            ArgumentSpec(
                                key=key,
                                required=key in required,
                                canonicalizer_ids=source.canonicalization_rules,
                            )
                            for key, _kind in source.types
                        ),
                        content=content,
                        legal_key_skeletons=source.legal_key_skeletons,
                    )
                )
            bundles.append(FamilyBundle(family_tag, tuple(contracts)).validate())
            reference_hashes[family_tag] = _sha256_bytes(reference.encode("ascii"))
        if len(bundles) != FAMILY_COUNT:
            raise G6CorpusIntegrationError("adapter requires exactly 28 corpus families")
        self.family_bundles = tuple(bundles)
        self.family_reference_sha256s = dict(reference_hashes)

    @classmethod
    def from_path(cls, path: Path) -> "G6CorpusAdapter":
        renderer = G6CorpusRenderer.from_path(path)
        if renderer.corpus_sha256 != COMMITTED_CORPUS_SHA256:
            raise G6CorpusIntegrationError("frozen G6 corpus SHA-256 drift")
        return cls(renderer)

    def build_sweep(
        self,
        *,
        max_final_calls: int = G6_MAX_FINAL_CALLS,
        canonicalizers: Mapping[str, Callable[[object], object]] | None = None,
    ) -> G6FamilySweep:
        """Return the frozen core with no contact or sample-dependent operation."""

        selected = dict(_CANONICALIZERS if canonicalizers is None else canonicalizers)
        return G6FamilySweep(
            family_bundles=self.family_bundles,
            max_final_calls=max_final_calls,
            canonicalizers=selected,
        )


@dataclass(frozen=True)
class G6Fixed16RuntimeSurface:
    """Identity-only original-speech and sealed-packet runtime surface."""

    split_id: str
    split_identity_hash: str
    samples: tuple[Audio2ToolSample, ...]
    packet_bindings: Mapping[str, Mapping[str, str]]
    speech_feature_tokens_by_sample: Mapping[str, int]
    source_hashes: Mapping[str, str]
    surface_sha256: str
    source_field_names: tuple[str, ...] = SOURCE_FIELDS


def _manifest_identity_hash(rows: Sequence[Mapping[str, object]]) -> str:
    ids = []
    for row in rows:
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise G6CorpusIntegrationError("G6 roster sample identity is malformed")
        ids.append(f"audio2tool/{sample_id}")
    if len(set(ids)) != len(ids):
        raise G6CorpusIntegrationError("G6 roster sample identities are duplicated")
    return _sha256_bytes("\n".join(sorted(ids)).encode("ascii"))


def load_g6_runtime_surface(
    *,
    g1_receipt_path: Path,
    g6_roster_path: Path,
    promotion_receipt_path: Path,
    expected_g1_sha256: str | None = None,
    expected_g6_roster_sha256: str | None = None,
    expected_promotion_sha256: str | None = None,
) -> G6Fixed16RuntimeSurface:
    """Load the frozen G6 roster without opening speech or task-bearing fields."""

    g1_raw, g1 = _read_ascii_json(g1_receipt_path, label="G1 identity receipt")
    roster_raw, roster = _read_ascii_json(g6_roster_path, label="G6 identity roster")
    promotion_raw, promotion = _read_ascii_json(
        promotion_receipt_path, label="G1 promotion receipt"
    )
    source_hashes = {
        "g1_receipt_sha256": _sha256_bytes(g1_raw),
        "g6_roster_sha256": _sha256_bytes(roster_raw),
        "promotion_receipt_sha256": _sha256_bytes(promotion_raw),
    }
    for key, expected in (
        ("g1_receipt_sha256", expected_g1_sha256),
        ("g6_roster_sha256", expected_g6_roster_sha256),
        ("promotion_receipt_sha256", expected_promotion_sha256),
    ):
        if expected is not None and source_hashes[key] != expected:
            raise G6CorpusIntegrationError(f"{key} drift")
    if g1.get("schema") != "saea-a2t-subset-receipt-v1":
        raise G6CorpusIntegrationError("G1 identity receipt schema drift")
    if roster.get("schema") != "saea-a2t-g6-family-sweep-fixed16-identity-receipt-v1":
        raise G6CorpusIntegrationError("G6 identity roster schema drift")
    if roster.get("split_name") != G6_FIXED16_SPLIT_ID:
        raise G6CorpusIntegrationError("G6 split identity drift")
    selection = roster.get("selection")
    if not isinstance(selection, Mapping) or any(
        selection.get(flag) is not False for flag in _SELECTION_PROHIBITION_FLAGS
    ):
        raise G6CorpusIntegrationError("G6 roster selection is not source-free")
    selected = roster.get("selected")
    tier_order = roster.get("tier_order")
    tier_counts = roster.get("selected_tier_counts")
    if (
        not isinstance(selected, list)
        or len(selected) != 16
        or not isinstance(tier_order, list)
        or len(tier_order) != 8
        or len(set(tier_order)) != 8
        or not all(isinstance(tier, str) and tier for tier in tier_order)
        or not isinstance(tier_counts, Mapping)
        or set(tier_counts) != set(tier_order)
        or any(tier_counts.get(tier) != 2 for tier in tier_order)
        or selection.get("items_per_tier") != 2
        or any(not isinstance(row, Mapping) for row in selected)
    ):
        raise G6CorpusIntegrationError("G6 roster must contain two rows in each tier")
    selected_rows = tuple(row for row in selected if isinstance(row, Mapping))
    computed_split_hash = _manifest_identity_hash(selected_rows)
    if (
        roster.get("manifest_split_identity_hash") != computed_split_hash
        or roster.get("split_identity_hash") != computed_split_hash
    ):
        raise G6CorpusIntegrationError("G6 roster manifest identity hash drift")
    actual_counts = {
        tier: sum(row.get("tier") == tier for row in selected_rows) for tier in tier_order
    }
    if actual_counts != dict(tier_counts):
        raise G6CorpusIntegrationError("G6 roster tier membership drift")
    roster_sources = roster.get("source_hashes")
    if (
        not isinstance(roster_sources, Mapping)
        or roster_sources.get("g1") != source_hashes["g1_receipt_sha256"]
    ):
        raise G6CorpusIntegrationError("G6 roster is bound to another G1 identity")

    g1_items = g1.get("items")
    if not isinstance(g1_items, list) or any(
        not isinstance(row, Mapping) for row in g1_items
    ):
        raise G6CorpusIntegrationError("G1 identity rows are malformed")
    g1_by_id = {
        row.get("sample_id"): row for row in g1_items if isinstance(row, Mapping)
    }
    if len(g1_by_id) != len(g1_items):
        raise G6CorpusIntegrationError("G1 sample identities are malformed")
    promotion_rows = promotion.get("packets")
    if not isinstance(promotion_rows, list) or any(
        not isinstance(row, Mapping) for row in promotion_rows
    ):
        raise G6CorpusIntegrationError("G1 promotion packet rows are malformed")
    promotion_by_id = {
        row.get("packet_id"): row
        for row in promotion_rows
        if isinstance(row, Mapping) and isinstance(row.get("packet_id"), str)
    }
    if len(promotion_by_id) != len(promotion_rows):
        raise G6CorpusIntegrationError("G1 promotion packet identities are malformed")
    if promotion.get("subset_receipt_sha256") != source_hashes["g1_receipt_sha256"]:
        raise G6CorpusIntegrationError("G1 promotion is bound to another identity")

    packet_root = Path(promotion_receipt_path).resolve().parent
    samples: list[Audio2ToolSample] = []
    bindings: dict[str, Mapping[str, str]] = {}
    speech_tokens: dict[str, int] = {}
    surface_rows: list[dict[str, object]] = []
    for roster_row in selected_rows:
        sample_id = roster_row.get("sample_id")
        key = roster_row.get("key")
        tier = roster_row.get("tier")
        item = g1_by_id.get(sample_id)
        if (
            not isinstance(sample_id, str)
            or not isinstance(key, str)
            or not isinstance(tier, str)
            or not isinstance(item, Mapping)
            or item.get("key") != key
            or item.get("tier") != tier
        ):
            raise G6CorpusIntegrationError("G6 roster row is absent from G1")
        packet_id = item.get("packet_id")
        media_relpath = item.get("media_relpath")
        audio_seconds = item.get("audio_seconds")
        if (
            not isinstance(packet_id, str)
            or not packet_id
            or Path(packet_id).is_absolute()
            or ".." in Path(packet_id).parts
            or not isinstance(media_relpath, str)
            or not media_relpath
            or Path(media_relpath).is_absolute()
            or isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or float(audio_seconds) <= 0
        ):
            raise G6CorpusIntegrationError("G1 runtime media identity is malformed")
        audio_hash = _require_hash(item.get("audio_sha256"), label="G1 audio SHA-256")
        promoted = promotion_by_id.get(packet_id)
        if not isinstance(promoted, Mapping) or promoted.get("audio_sha256") != audio_hash:
            raise G6CorpusIntegrationError("sealed packet and G1 audio identity disagree")
        packet_hash = _require_hash(
            promoted.get("packet_sha256"), label="promoted packet SHA-256"
        )
        packet_path = (packet_root / packet_id / "packet.json").resolve()
        if not packet_path.is_relative_to(packet_root) or not packet_path.is_file():
            raise G6CorpusIntegrationError("sealed packet metadata is unavailable")
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
            raise G6CorpusIntegrationError("sealed packet metadata drift")
        feature_tokens = 0
        for chunk in chunks:
            count = chunk.get("n_tokens") if isinstance(chunk, Mapping) else None
            if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
                raise G6CorpusIntegrationError("sealed speech token count is malformed")
            feature_tokens += count
        sample = Audio2ToolSample(
            sample_id=sample_id,
            audio_ref=AudioRef(path=media_relpath, sha256=audio_hash).validate(),
            audio_seconds=float(audio_seconds),
            media_relpath=media_relpath,
        )
        samples.append(sample)
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
    return G6Fixed16RuntimeSurface(
        split_id=G6_FIXED16_SPLIT_ID,
        split_identity_hash=computed_split_hash,
        samples=tuple(samples),
        packet_bindings=dict(sorted(bindings.items())),
        speech_feature_tokens_by_sample=dict(sorted(speech_tokens.items())),
        source_hashes=source_hashes,
        surface_sha256=surface_sha256,
    )


def measure_contact_prompt_fit(
    *,
    context: ContactContext,
    rendered_request: str,
    runtime: G6Fixed16RuntimeSurface,
    sample_id: str,
    token_counter: Callable[[str], int],
) -> dict[str, object]:
    """Measure one exact rendered request without contacting any service."""

    if not isinstance(context, ContactContext):
        raise G6CorpusIntegrationError("prompt fit requires a ContactContext")
    if not isinstance(rendered_request, str) or not rendered_request or not rendered_request.isascii():
        raise G6CorpusIntegrationError("rendered request must be nonempty ASCII text")
    if not callable(token_counter):
        raise G6CorpusIntegrationError("token_counter must be callable")
    if sample_id not in runtime.speech_feature_tokens_by_sample:
        raise G6CorpusIntegrationError("prompt-fit sample is outside the runtime surface")
    binding = runtime.packet_bindings.get(sample_id)
    if (
        not isinstance(binding, Mapping)
        or context.speech_packet_id != binding.get("packet_id")
        or context.speech_packet_sha256 != binding.get("sha256")
    ):
        raise G6CorpusIntegrationError(
            "prompt-fit context is bound to another sealed speech packet"
        )
    text_tokens = token_counter(rendered_request)
    speech_tokens = runtime.speech_feature_tokens_by_sample[sample_id]
    if isinstance(text_tokens, bool) or not isinstance(text_tokens, int) or text_tokens < 0:
        raise G6CorpusIntegrationError("token_counter must return a nonnegative integer")
    total = (
        text_tokens
        + speech_tokens
        + context.completion_token_ceiling
        + 512
    )
    remaining = PER_SLOT_CONTEXT_TOKENS - total
    return {
        "status": "PASS" if remaining >= OPERATIONAL_HEADROOM_TOKENS else "FAIL",
        "contact_id": context.contact_id,
        "stage": context.stage,
        "sample_id": sample_id,
        "rendered_request_ascii_bytes": len(rendered_request.encode("ascii")),
        "rendered_request_sha256": _sha256_bytes(rendered_request.encode("ascii")),
        "text_tokens": text_tokens,
        "speech_feature_tokens": speech_tokens,
        "special_token_reserve": 512,
        "completion_token_ceiling": context.completion_token_ceiling,
        "total_tokens": total,
        "remaining_tokens": remaining,
        "nominated_contract_count": len(context.contracts) if context.stage == "RESOLVE" else 0,
        "refuse_contact": remaining < OPERATIONAL_HEADROOM_TOKENS,
    }


def build_prompt_fit_report(
    *,
    adapter: G6CorpusAdapter,
    runtime: G6Fixed16RuntimeSurface,
    task_contract: str,
    token_counter: Callable[[str], int],
    render_request: Callable[[ContactContext], str] | None = None,
) -> dict[str, object]:
    """Measure all 448 exact SCAN controls; defer RESOLVE until reports exist."""

    if not isinstance(adapter, G6CorpusAdapter):
        raise G6CorpusIntegrationError("prompt fit requires a G6CorpusAdapter")
    renderer = render_request or (lambda context: context.render_control_text())
    sweep = adapter.build_sweep()
    family_maxima: dict[str, dict[str, object]] = {}
    exact_count = 0
    all_pass = True
    for sample in runtime.samples:
        binding = runtime.packet_bindings[sample.sample_id]
        contexts = sweep.build_scan_contexts(
            speech_packet_id=binding["packet_id"],
            speech_packet_sha256=binding["sha256"],
            task_contract=task_contract,
        )
        for context in contexts:
            measured = measure_contact_prompt_fit(
                context=context,
                rendered_request=renderer(context),
                runtime=runtime,
                sample_id=sample.sample_id,
                token_counter=token_counter,
            )
            exact_count += 1
            all_pass = all_pass and measured["status"] == "PASS"
            tag = context.family_tag
            if tag is None:
                raise G6CorpusIntegrationError("SCAN context lacks its family tag")
            current = family_maxima.get(tag)
            if current is None or int(measured["total_tokens"]) > int(
                current["total_tokens"]
            ):
                family_maxima[tag] = measured
    return {
        "schema": "saea-a2t-g6-fixed16-model-free-prompt-fit-v1",
        "status": "PASS" if all_pass else "FAIL",
        "sources": {
            "corpus_sha256": adapter.corpus_sha256,
            **dict(runtime.source_hashes),
        },
        "runtime": {
            "split_id": runtime.split_id,
            "split_identity_hash": runtime.split_identity_hash,
            "sample_count": len(runtime.samples),
            "runtime_surface_sha256": runtime.surface_sha256,
            "task_text_fields_read": 0,
            "gold_fields_read": 0,
            "outputs_read": 0,
            "test_rows_read": 0,
        },
        "corpus": {
            "family_count": len(adapter.family_bundles),
            "tool_count": sum(len(bundle.contracts) for bundle in adapter.family_bundles),
            "family_reference_sha256s": dict(adapter.family_reference_sha256s),
            "full_family_reference_entries_per_scan": 1,
            "ranking_or_pruning_applied": False,
        },
        "scan": {
            "exact_context_count": exact_count,
            "family_maxima": family_maxima,
            "all_require_operational_headroom_tokens": OPERATIONAL_HEADROOM_TOKENS,
        },
        "resolve": {
            "precomputed": False,
            "rule": (
                "After all 28 raw SCAN responses are sealed and parsed, render and "
                "measure the exact RESOLVE request before its sole contact; refuse "
                "when fewer than 8192 tokens remain."
            ),
        },
        "contacts": {
            "frozen_core": 0,
            "network": 0,
            "retriever": 0,
            "scorer": 0,
        },
    }


__all__ = [
    "COMMITTED_CORPUS_SHA256",
    "COMMITTED_G1_PROMOTION_SHA256",
    "COMMITTED_G1_RECEIPT_SHA256",
    "COMMITTED_G6_ROSTER_SHA256",
    "G6_FIXED16_SPLIT_ID",
    "G6_MAX_FINAL_CALLS",
    "G6CorpusAdapter",
    "G6CorpusIntegrationError",
    "G6Fixed16RuntimeSurface",
    "SOURCE_FIELDS",
    "build_prompt_fit_report",
    "load_g6_runtime_surface",
    "measure_contact_prompt_fit",
]
