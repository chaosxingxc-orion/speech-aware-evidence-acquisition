"""Execution policies over the three D2-frozen arm shapes (the policy seam).

R0 implements exactly one policy: ``fixed`` — one request per sample, always
admit. X1 re-resolution (multiple requests), X3 verification/rejection loops
and X4 reward-guided action selection register here later; the arm payload
vocabulary never grows without a new D2 receipt.
"""

from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from queue import Queue
from typing import Mapping, Sequence

from ..contracts import CONSTRUCTION_VISIBLE_FIELD
from ..data.audio2tool_tools import render_openai_tools
from ..data.loader import SampleRef
from ..data.lock import load_lock, umbrella_lock_path
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .base import (
    JUDGES,
    MAX_TOKENS_POLICIES,
    POLICIES,
    RESPONSE_POSTPROCESSORS,
    CoreError,
    EvidenceItem,
    Registry,
    SampleContext,
    SampleOutcome,
)
from .tracing import set_current_trace_buffer


class ArmError(RuntimeError):
    """An arm builder was given inputs its D2-frozen field set cannot carry."""


# Native tool-calling arm (D1a): a named fill resolves a config's
# "tool_schema_fill" key into an OpenAI-format `tools` list at run time,
# mirroring core.instructions.INSTRUCTION_FILLS -- but that registry's fills
# are `(lock, root) -> str` (one text-substitution placeholder,
# "{tool_schemas}"); this arm needs `(lock, root) -> list[dict]` instead, a
# shape INSTRUCTION_FILLS was never built for. Rather than adding a second
# registry to core.base (core.policies does not own that module), the whole
# fill vocabulary lives HERE, behind this module's own Registry instance
# (the same core.base.Registry class every other seam already uses) and is
# resolved entirely inside FixedPolicy.run_sample below -- run.py's
# SampleContext.extras / config_values threading is untouched.
TOOL_SCHEMA_FILLS = Registry("tool schema fill")
TOOL_SCHEMA_FILLS.register("audio2tool-openai-tools", render_openai_tools)


@lru_cache(maxsize=1)
def _cached_umbrella_lock() -> Mapping[str, object]:
    """The umbrella lock, parsed once per process.

    A tool-schema fill is called per sample (potentially hundreds of times
    per run, from concurrent worker threads via ``run_samples`` below); the
    lock document itself never changes within a process's lifetime, so
    re-reading and re-parsing the same small committed JSON file on every
    call would be pure waste. ``data.lock.umbrella_lock_path()`` resolves a
    fixed, checkout-relative path with no arguments, so this cache carries no
    per-call parameter to key on.
    """

    return load_lock(umbrella_lock_path())


def build_arm_payload(
    arm: str,
    ref: SampleRef,
    request_id: str,
    task_instruction: str,
    decoding_params: Mapping[str, object],
    evidence: list[EvidenceItem] | None = None,
    retrieval_query: str | None = None,
    exemplar_bank: Sequence[Mapping[str, object]] | None = None,
    delta_candidates: Sequence[Mapping[str, object]] | None = None,
    allow_empty_evidence: bool = False,
    speech_feature_parts: Sequence[Mapping[str, object]] | None = None,
    speech_packet_sha256: str | None = None,
    query_source: str | None = None,
    key_representation_id: str | None = None,
    matcher_policy_id: str | None = None,
    mmproj_loaded: bool | None = None,
    tool_schemas: Sequence[Mapping[str, object]] | None = None,
    construction_targets: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    if arm not in ARM_VISIBLE_FIELDS:
        raise ArmError(f"unknown arm {arm!r}; D2-frozen arms are {sorted(ARM_VISIBLE_FIELDS)}")
    arm_fields = ARM_VISIBLE_FIELDS[arm]
    payload: dict[str, object] = dict(ref.runtime_view())
    payload["request_id"] = request_id
    payload["task_instruction"] = task_instruction
    payload["history"] = []
    payload["decoding_params"] = dict(decoding_params)
    # Evidence shape is read off the arm's OWN D2-frozen field set (2026-08-13
    # fix), never a hardcoded arm-name literal: an arm naming neither
    # "supplied_evidence" nor "retrieved_evidence" is bare-core-shaped (no
    # evidence, no retrieval query); one carries exactly ONE of the two
    # (the D2 freeze never declares both on the same arm). Branching on the
    # DECLARED FIELDS rather than on which of the original three arm names
    # happened to be spelled out lets a new arm that extends
    # fixed-legal-context's own evidence shape (e.g. "exemplar-context",
    # "fixed-legal-context-replay") work correctly without a fourth name
    # literal here -- the previous name-literal branching would have
    # mis-routed any such arm into the fixed-retrieval shape (or refused it
    # as bare-core) regardless of which fields it actually declared.
    carries_supplied_evidence = "supplied_evidence" in arm_fields
    carries_retrieved_evidence = "retrieved_evidence" in arm_fields
    if not carries_supplied_evidence and not carries_retrieved_evidence:
        if evidence is not None or retrieval_query is not None:
            raise ArmError(f"arm {arm!r} carries no evidence and no retrieval query")
    else:
        # allow_empty_evidence (reproduction.replay_loop's replay_pass1_evidence
        # ="suppressed" knob, D7 delivery-gate design-gap fix, 2026-08-15):
        # default False keeps every pre-existing caller's behaviour byte
        # -identical -- an evidence-bearing arm still refuses a missing or
        # empty evidence list. Explicitly opting in (never the default) lets
        # a caller attach the arm's declared evidence KEYS with EMPTY
        # content -- the same "field present, content empty" shape
        # exemplar_bank/delta_candidates below already allow for any caller,
        # deliberately narrower here since ordinary evidence resolution
        # failures (a sample with no evidence at all) must keep failing
        # loud rather than silently downgrading to an empty tier.
        if not evidence and not allow_empty_evidence:
            raise ArmError(f"arm {arm!r} requires non-empty evidence")
        validated = [item.validate() for item in evidence or []]
        provenance = [item.provenance_view() for item in validated]
        if carries_supplied_evidence:
            if retrieval_query is not None:
                raise ArmError(f"arm {arm!r} carries no retrieval query")
            payload["supplied_evidence"] = [item.runtime_view() for item in validated]
        else:  # carries_retrieved_evidence
            if retrieval_query is None or not retrieval_query.strip():
                raise ArmError(f"arm {arm!r} requires a retrieval_query")
            payload["retrieval_query"] = retrieval_query
            payload["retrieved_evidence"] = [item.runtime_view() for item in validated]
        payload["evidence_provenance"] = provenance
    # Acoustic exemplar bank (core.exemplars module docstring, M-C-prime prep
    # infrastructure): orthogonal to the evidence/retrieval_query handling
    # above -- default None is a no-op (byte-identical payload, the pre
    # -existing shape), and a supplied bank (possibly empty -- an empty bank
    # is a legal v3 shape, core.model.transport's own module docstring) is
    # attached ONLY for an arm whose D2-frozen field set actually declares
    # "exemplar_bank" -- "exemplar-context" and "fixed-legal-context-replay"
    # do (e0.d2_leakage.ARM_VISIBLE_FIELDS, 2026-08-13); every OTHER arm
    # registered today still fails closed here rather than silently
    # dropping the bank.
    if exemplar_bank is not None:
        if "exemplar_bank" not in ARM_VISIBLE_FIELDS[arm]:
            raise ArmError(
                f"arm {arm!r} does not declare 'exemplar_bank' in its D2-frozen field "
                "set; cannot attach an exemplar bank to this arm's payload"
            )
        payload["exemplar_bank"] = [dict(pair) for pair in exemplar_bank]
    # v3 delta candidates (core.model.transport tier 3, obs-replay-loop
    # policy prep): the SAME "default None is a byte-identical no-op, a
    # supplied sequence attaches only for an arm whose D2-frozen field set
    # declares 'delta_candidates'" discipline exemplar_bank just established
    # above -- "fixed-legal-context-replay" declares it too
    # (reproduction.replay_loop's REPLAY-scoped arm, 2026-08-13); every
    # OTHER arm registered today still fails closed here rather than
    # silently dropping retrieved candidates.
    if delta_candidates is not None:
        if "delta_candidates" not in ARM_VISIBLE_FIELDS[arm]:
            raise ArmError(
                f"arm {arm!r} does not declare 'delta_candidates' in its D2-frozen "
                "field set; cannot attach delta candidates to this arm's payload"
            )
        payload["delta_candidates"] = [dict(item) for item in delta_candidates]
    speech_fields = {
        "speech_feature_parts",
        "speech_packet_sha256",
        "query_source",
        "key_representation_id",
        "matcher_policy_id",
        "mmproj_loaded",
    }
    supplied_speech_values = (
        speech_feature_parts,
        speech_packet_sha256,
        query_source,
        key_representation_id,
        matcher_policy_id,
        mmproj_loaded,
    )
    if speech_fields <= set(arm_fields):
        if not isinstance(speech_feature_parts, Sequence) or not speech_feature_parts:
            raise ArmError("speech-feature arm requires at least one packet descriptor")
        descriptors = [dict(part) for part in speech_feature_parts]
        required_descriptor = {"packet_id", "sha256", "role"}
        if any(set(part) != required_descriptor for part in descriptors):
            raise ArmError(
                "speech-feature packet descriptors must carry exact packet_id/sha256/role keys"
            )
        for part in descriptors:
            packet_id = part["packet_id"]
            packet_sha256 = part["sha256"]
            if (
                not isinstance(packet_id, str)
                or not packet_id
                or packet_id.startswith("/")
                or "\\" in packet_id
                or any(segment in {"", ".", ".."} for segment in packet_id.split("/"))
                or not isinstance(packet_sha256, str)
                or len(packet_sha256) != 64
                or any(character not in "0123456789abcdef" for character in packet_sha256)
            ):
                raise ArmError(
                    "speech-feature packet_id must be a normalized relative id and "
                    "sha256 must be lowercase 64-hex"
                )
        if sum(part["role"] == "query" for part in descriptors) != 1:
            raise ArmError("speech-feature arm requires exactly one query packet")
        if any(part["role"] not in {"query", "key"} for part in descriptors):
            raise ArmError("speech-feature packet role must be query or key")
        for field, value in (
            ("speech_packet_sha256", speech_packet_sha256),
            ("key_representation_id", key_representation_id),
            ("matcher_policy_id", matcher_policy_id),
        ):
            if not isinstance(value, str) or not value:
                raise ArmError(f"speech-feature arm requires non-empty {field}")
        query = next(part for part in descriptors if part["role"] == "query")
        if query.get("sha256") != speech_packet_sha256:
            raise ArmError("speech_packet_sha256 must equal the query packet descriptor hash")
        if query_source != "speech_features":
            raise ArmError("speech-feature arm query_source must be 'speech_features'")
        if mmproj_loaded is not False:
            raise ArmError("speech-feature arm must bind mmproj_loaded=false")
        payload.update(
            {
                "speech_feature_parts": descriptors,
                "speech_packet_sha256": speech_packet_sha256,
                "query_source": query_source,
                "key_representation_id": key_representation_id,
                "matcher_policy_id": matcher_policy_id,
                "mmproj_loaded": mmproj_loaded,
            }
        )
    elif any(value is not None for value in supplied_speech_values):
        raise ArmError(f"arm {arm!r} does not declare speech-feature fields")
    # Native tool-calling arm (D1a): "tool_schemas" (2026-09-03 D2 addition,
    # e0.d2_leakage.ARM_VISIBLE_FIELDS["bare-core-native-tools"]) follows the
    # SAME "default None is a byte-identical no-op, an arm that declares the
    # field requires it non-empty" discipline exemplar_bank/delta_candidates
    # established above -- an empty or absent tools list would silently
    # degrade a native tool-calling request into a plain chat completion,
    # defeating the whole point of this arm, so it is refused rather than
    # accepted.
    if "tool_schemas" in arm_fields:
        if (
            not isinstance(tool_schemas, Sequence)
            or isinstance(tool_schemas, (str, bytes))
            or not tool_schemas
        ):
            raise ArmError(f"arm {arm!r} requires a non-empty tool_schemas sequence")
        payload["tool_schemas"] = [dict(schema) for schema in tool_schemas]
    elif tool_schemas is not None:
        raise ArmError(
            f"arm {arm!r} does not declare 'tool_schemas' in its D2-frozen field set"
        )
    # Construction-proposer arm (E2.4, 2026-09-05): "construction_targets"
    # follows the SAME "an arm that declares the field requires it non-empty,
    # an arm that does not refuses it outright" discipline exemplar_bank,
    # delta_candidates and tool_schemas established above. Empty is refused
    # rather than accepted, because an empty target list would silently
    # degrade the proposer contact into an ungrounded free-writing request
    # while still claiming, in the audited payload, to be a construction
    # proposal.
    if CONSTRUCTION_VISIBLE_FIELD in arm_fields:
        if (
            not isinstance(construction_targets, Sequence)
            or isinstance(construction_targets, (str, bytes))
            or not construction_targets
        ):
            raise ArmError(
                f"arm {arm!r} requires a non-empty construction_targets sequence"
            )
        entries: list[dict[str, object]] = []
        for entry in construction_targets:
            if not isinstance(entry, Mapping) or set(entry) != {"sample_id", "target"}:
                raise ArmError(
                    f"arm {arm!r} construction_targets entries must carry exactly "
                    "'sample_id' and 'target'"
                )
            entries.append(dict(entry))
        payload[CONSTRUCTION_VISIBLE_FIELD] = entries
    elif construction_targets is not None:
        raise ArmError(
            f"arm {arm!r} does not declare {CONSTRUCTION_VISIBLE_FIELD!r} in its "
            "D2-frozen field set"
        )
    if set(payload) != set(ARM_VISIBLE_FIELDS[arm]):
        raise ArmError(
            f"arm {arm!r} builder produced a field set that diverges from the D2 freeze: "
            f"{sorted(set(payload) ^ set(ARM_VISIBLE_FIELDS[arm]))}"
        )
    return payload


class FixedPolicy:
    """One request per sample; responses are always admitted (R0 wiring).

    ``run_samples`` reuses the driver's existing sample-batch seam. It bounds
    concurrent requests by the protocol-bound ``obs_batch_samples`` value,
    routes each adapter trace to that sample's buffer, and preserves input
    order regardless of request completion order.
    """

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
        # Read off the arm's OWN D2-frozen field set (2026-09-03 fix, same
        # discipline build_arm_payload's own evidence branch above already
        # documents at length): "bare-core" used to be the ONLY arm carrying
        # neither "supplied_evidence" nor "retrieved_evidence", so nulling
        # ctx.evidence for exactly that literal string name was equivalent
        # to nulling it for every evidence-free arm. "bare-core-native-tools"
        # (D1a) is a SECOND such arm -- a hardcoded "!= 'bare-core'" string
        # check would pass its own ctx.evidence straight through and trip
        # build_arm_payload's "carries no evidence and no retrieval query"
        # refusal on any non-None value (including an empty list), so this
        # branches on the DECLARED FIELDS instead, exactly like build_arm_
        # payload does, and stays byte-identical for "bare-core" itself.
        arm_fields = ARM_VISIBLE_FIELDS[ctx.arm]
        carries_evidence = "supplied_evidence" in arm_fields or "retrieved_evidence" in arm_fields
        evidence = ctx.evidence if carries_evidence else None
        speech_kwargs: dict[str, object] = {}
        tool_kwargs: dict[str, object] = {}
        allow_empty_evidence = False
        if "tool_schemas" in arm_fields:
            config_values = ctx.extras.get("config_values", {})
            if not isinstance(config_values, Mapping):
                raise ArmError("tool-schema context config_values must be a mapping")
            fill_name = config_values.get("tool_schema_fill")
            if not isinstance(fill_name, str) or not fill_name.strip():
                raise ArmError(
                    f"arm {ctx.arm!r} declares 'tool_schemas' but the composed "
                    "config carries no tool_schema_fill naming a registered fill; "
                    f"registered: {TOOL_SCHEMA_FILLS.names()}"
                )
            fill = TOOL_SCHEMA_FILLS.resolve(fill_name)
            data_root = ctx.extras.get("data_root")
            if not isinstance(data_root, Path):
                raise ArmError(
                    "tool-schema context requires extras['data_root'] (a Path)"
                )
            tool_kwargs["tool_schemas"] = fill(_cached_umbrella_lock(), data_root)
        if "speech_feature_parts" in arm_fields:
            config_values = ctx.extras.get("config_values", {})
            if not isinstance(config_values, Mapping):
                raise ArmError("speech-feature context config_values must be a mapping")
            query = ctx.extras.get("speech_feature_query")
            if not isinstance(query, Mapping) or set(query) != {
                "packet_id",
                "sha256",
                "role",
            }:
                raise ArmError(
                    "speech-feature context must carry an exact packet_id/sha256/role query"
                )
            allow_empty_evidence = config_values.get(
                "allow_empty_speech_feature_evidence", False
            )
            if not isinstance(allow_empty_evidence, bool):
                raise ArmError("allow_empty_speech_feature_evidence must be boolean")
            speech_kwargs = {
                "speech_feature_parts": [dict(query)],
                "speech_packet_sha256": query["sha256"],
                "query_source": "speech_features",
                "key_representation_id": config_values.get("key_representation_id"),
                "matcher_policy_id": config_values.get("matcher_policy_id"),
                "mmproj_loaded": False,
            }
        payload = build_arm_payload(
            ctx.arm,
            ctx.sample,
            ctx.request_id_base,
            ctx.task_instruction,
            ctx.decoding_params,
            evidence=evidence,
            retrieval_query=ctx.retrieval_query,
            # M-C-prime static acoustic-supply arms (core.exemplars module
            # docstring; the "exemplar-context" D2-frozen arm, 2026-08-13):
            # ctx.exemplar_bank is resolved once per sample by
            # core.driver.run_experiment and stays None unless the composed
            # config declared exemplar_manifest_id, so this thread-through
            # is a byte-identical no-op (build_arm_payload's own "default
            # None omits the field" contract) for every arm registered
            # before "exemplar-context" -- mirroring reproduction.obs_loop's
            # own identical thread-through for its slice payloads.
            exemplar_bank=ctx.exemplar_bank,
            allow_empty_evidence=allow_empty_evidence,
            **speech_kwargs,
            **tool_kwargs,
        )
        response = ctx.adapter.request(payload)
        ctx.sink.emit(
            "USE",
            f"{ctx.request_id_base}/use",
            {"use_response_sha256": response.response_sha256, "use_admitted": True},
        )
        return SampleOutcome(
            sample_id=ctx.sample.sample_id,
            request_ids=(ctx.request_id_base,),
            text=response.text,
            admitted=True,
            request_sha256=response.request_sha256,
            response_sha256=response.response_sha256,
            # R0 repair T6 (I7): plumbing-only passthrough of the adapter's new
            # text-hash field (core.model.CoreResponse.response_text_sha256)
            # into the outputs row -- not itself a policy-behavior change.
            response_text_sha256=response.response_text_sha256,
        )

    def run_samples(self, contexts: Sequence[SampleContext]) -> list[SampleOutcome]:
        """Run whole-speech requests concurrently without changing semantics.

        All contexts are validated before the first request. When the model
        profile declares ``id_slot='per-sample'``, an in-flight request owns
        one slot from a bounded pool and releases it only after the request
        settles. Futures are read in input order after the entire pool has
        settled, so the first failure in split order wins deterministically.
        """

        contexts = list(contexts)
        if not contexts:
            return []

        batch_sizes: list[int] = []
        for ctx in contexts:
            config_values = ctx.extras.get("config_values", {})
            if not isinstance(config_values, Mapping):
                raise ArmError("fixed batch context config_values must be a mapping")
            raw_batch_size = config_values.get("obs_batch_samples", 1)
            if (
                isinstance(raw_batch_size, bool)
                or not isinstance(raw_batch_size, int)
                or raw_batch_size < 1
            ):
                raise ArmError(
                    "fixed batch obs_batch_samples must be an integer >= 1, "
                    f"got {raw_batch_size!r}"
                )
            batch_sizes.append(raw_batch_size)
            id_slot = ctx.decoding_params.get("id_slot")
            if id_slot is not None and (
                isinstance(id_slot, bool)
                or not (
                    (isinstance(id_slot, int) and id_slot >= 0)
                    or id_slot == "per-sample"
                )
            ):
                raise ArmError(
                    "fixed batch decoding_params.id_slot must be a non-negative "
                    f"integer or 'per-sample', got {id_slot!r}"
                )
        if len(set(batch_sizes)) != 1:
            raise ArmError("fixed batch contexts disagree on obs_batch_samples")

        batch_size = min(batch_sizes[0], len(contexts))
        free_slots: Queue[int] = Queue(maxsize=batch_size)
        for slot in range(batch_size):
            free_slots.put(slot)

        def one(ctx: SampleContext) -> SampleOutcome:
            decoding_params = dict(ctx.decoding_params)
            pinned_slot: int | None = None
            if decoding_params.get("id_slot") == "per-sample":
                pinned_slot = free_slots.get()
                decoding_params["id_slot"] = pinned_slot
            worker_ctx = replace(ctx, decoding_params=decoding_params)
            set_current_trace_buffer(worker_ctx.sink)
            try:
                return self.run_sample(worker_ctx)
            finally:
                set_current_trace_buffer(None)
                if pinned_slot is not None:
                    free_slots.put(pinned_slot)

        with ThreadPoolExecutor(
            max_workers=batch_size,
            thread_name_prefix="saea-fixed-sample",
        ) as pool:
            futures = [pool.submit(one, ctx) for ctx in contexts]
        return [future.result() for future in futures]


POLICIES.register("fixed", FixedPolicy())


# ---------------------------------------------------------------------------
# Per-sample ``decoding_params.max_tokens`` policies (E22 cell (b), 2026-09-06)
# ---------------------------------------------------------------------------

#: The one registered per-sample ``max_tokens`` rule. Named ``-v1`` because the
#: arithmetic below is FROZEN: a different formula is a different id, so a
#: sealed trace's per-row cap can always be re-derived from the id plus the
#: parameters the fragment declared.
DURATION_PROPORTIONAL_MAX_TOKENS_V1 = "duration-proportional-v1"


class DurationProportionalMaxTokens:
    """``min(ceiling, max(floor, ceil(alpha * seconds * wps * tpw)))``.

    The generation cap of one request, resolved from that request's OWN media
    duration instead of a single cell-wide integer. Every constant is declared
    by the config fragment and none is hard-coded here: ``alpha`` is the
    slack multiplier, ``words_per_second_p95`` a REFERENCE-side speaking-rate
    percentile, ``tokens_per_word`` the flight tokenizer's pooled tokens per
    normalized word, ``floor`` the smallest cap a sub-second clip may get and
    ``ceiling`` the cell-wide ceiling the cap may never exceed.

    Numerically identical, by construction, to
    ``analysis.e22_overgeneration.cap_tokens(alpha, seconds, wps, tpw)`` clamped
    to ``[floor, ceiling]`` -- that module is the model-free simulator whose
    projection a capped flight is measured against, so the two must agree row
    for row or the prediction check compares two different interventions.
    ``tests/unit/test_max_tokens_policies.py`` pins that equality.
    """

    #: Exactly the keys a rule object carries beside ``policy``. Fail-closed in
    #: both directions: a missing key is a rule this policy cannot evaluate, and
    #: an extra key is a knob the author believes is being honoured and is not.
    PARAMETERS = ("alpha", "words_per_second_p95", "tokens_per_word", "floor", "ceiling")

    def parameters(self, rule: Mapping[str, object]) -> dict[str, object]:
        """Validate ``rule`` and return its parameters, canonically typed.

        Raises :class:`core.base.CoreError` on anything malformed, so a cell
        that mis-declares its cap dies at composition time rather than sending
        1,500 requests under a cap nobody intended.
        """

        if not isinstance(rule, Mapping):
            raise CoreError("max_tokens rule must be a mapping")
        declared = set(rule) - {"policy"}
        missing = sorted(set(self.PARAMETERS) - declared)
        extra = sorted(declared - set(self.PARAMETERS))
        if missing or extra:
            raise CoreError(
                f"max_tokens policy {DURATION_PROPORTIONAL_MAX_TOKENS_V1!r} requires "
                f"exactly {sorted(self.PARAMETERS)}; missing={missing} extra={extra}"
            )
        numbers: dict[str, object] = {}
        for name in ("alpha", "words_per_second_p95", "tokens_per_word"):
            value = rule[name]
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0
            ):
                raise CoreError(
                    f"max_tokens rule {name!r} must be a finite positive number, "
                    f"got {value!r}"
                )
            numbers[name] = float(value)
        for name in ("floor", "ceiling"):
            value = rule[name]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise CoreError(
                    f"max_tokens rule {name!r} must be an integer >= 1, got {value!r}"
                )
            numbers[name] = int(value)
        if int(numbers["floor"]) > int(numbers["ceiling"]):
            raise CoreError(
                f"max_tokens rule floor {numbers['floor']} exceeds ceiling "
                f"{numbers['ceiling']}"
            )
        return numbers

    def resolve(self, rule: Mapping[str, object], audio_seconds: float) -> int:
        """This sample's integer cap. ``audio_seconds`` is the sample's own
        measured media duration -- the roster's, which is also what the payload
        carries and what the adapter meters."""

        params = self.parameters(rule)
        if (
            isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or not math.isfinite(float(audio_seconds))
            or float(audio_seconds) <= 0
        ):
            raise CoreError(
                "max_tokens resolution needs a finite positive audio_seconds, got "
                f"{audio_seconds!r}"
            )
        raw = math.ceil(
            float(params["alpha"])
            * float(audio_seconds)
            * float(params["words_per_second_p95"])
            * float(params["tokens_per_word"])
        )
        return min(int(params["ceiling"]), max(int(params["floor"]), int(raw)))


MAX_TOKENS_POLICIES.register(
    DURATION_PROPORTIONAL_MAX_TOKENS_V1, DurationProportionalMaxTokens()
)

# obs-agent-loop (owner directive 2026-08-08): the model-driven OBS
# segmentation loop -- N slice requests per whole-call sample, one stitched
# hypothesis out. Implementation lives in reproduction/obs_loop.py
# (deliberately outside core, P1 pattern); it registers HERE because this
# module is the one policy-registration site run_experiment resolves names
# through. The arm payload vocabulary is untouched: every iteration's
# request flows through build_arm_payload above under the same D2-frozen
# per-arm field sets.
from ..reproduction.obs_loop import OBS_LOOP_POLICY_NAME, ObsAgentLoopPolicy  # noqa: E402

POLICIES.register(OBS_LOOP_POLICY_NAME, ObsAgentLoopPolicy())

# obs-agent-loop-ojw (owner directive 2026-08-08, openJiuwen adoption): the
# SAME obs loop orchestrated by the openJiuwen framework executor
# (reproduction/ojw/ -- LoopGroup body + FuncCondition over the Pregel
# engine). Registration is free of openjiuwen imports (the framework enters
# only through the policy's lazy seam at run time and never enters
# pyproject.toml -- D2 zero-dependency gate); with openjiuwen absent the
# policy refuses with the install hint. Equivalence with the plain policy
# above is a red line, asserted by tests/unit/test_obs_loop_ojw.py.
from ..reproduction.ojw.policy import (  # noqa: E402
    OJW_POLICY_NAME,
    ObsAgentLoopOjwPolicy,
)

POLICIES.register(OJW_POLICY_NAME, ObsAgentLoopOjwPolicy())

# obs-replay-loop (listen-score-replay orchestration policy, 2026-08-13):
# assembles the already-merged organs (core.replay_signals, core.span_surgery,
# core.retrieval, core.exemplars, core.model.transport's v3 tiers) into one
# policy -- PASS 1 reuses reproduction.obs_loop.ObsAgentLoopPolicy's own
# slice-parallel pass verbatim, then SCORE/LOCATE/RETRIEVE/REPLAY/ACCEPT are
# new orchestration this module owns. Registers here for the SAME reason
# obs-agent-loop/obs-agent-loop-ojw do: this module is the one
# policy-registration site run_experiment resolves names through.
from ..reproduction.replay_loop import (  # noqa: E402
    OBS_REPLAY_LOOP_POLICY_NAME,
    ObsReplayLoopPolicy,
)

POLICIES.register(OBS_REPLAY_LOOP_POLICY_NAME, ObsReplayLoopPolicy())

# e21-entity-repair-substitutions-v1 (KC-E1f, 2026-09-07): the ONE registered
# rule that turns a second-pass response into a delivered hypothesis which can
# differ from its sealed pass-1 predecessor by bounded, token-count-preserving
# SUBSTITUTIONS only. Registers HERE for the same reason every policy above
# does: this module is a canonical core.base registration site, so a baseline
# fragment's ``response_postprocessor`` id resolves the way its ``policy`` and
# ``evidence_source`` ids do and scripts/checks/engineering_base_check.py can
# read the registered name set from source. The rule itself lives in
# core/repair_alignment.py with its refusal table.
from .repair_alignment import (  # noqa: E402
    E21_ENTITY_REPAIR_SUBSTITUTIONS_V1,
    E21_FREE_REFRESH_DELIVERY_V1,
    entity_repair_substitutions_v1,
    free_refresh_delivery_v1,
)

RESPONSE_POSTPROCESSORS.register(
    E21_ENTITY_REPAIR_SUBSTITUTIONS_V1, entity_repair_substitutions_v1
)

# The UNCONSTRAINED sibling (DR-1f, owner Decision 13-J, 2026-09-09): the same
# seam with the span bound, the anchor floor and the substitution ceiling
# removed, so a cell that asks the core to REFRESH a draft rather than repair
# names in it moves exactly one registered id. It registers here for the same
# reason the bounded rule does, and beside it, so a reader of the one canonical
# registration site sees both deliveries a second pass may have.
RESPONSE_POSTPROCESSORS.register(
    E21_FREE_REFRESH_DELIVERY_V1, free_refresh_delivery_v1
)

# obs-repair-loop (KC-E1f second-pass entity repair, 2026-09-07): the same
# fixed 90-second tiling as obs-agent-loop, one contact per window, but each
# request carries that window's SEALED pass-1 hypothesis and what the run
# stitches is the substitution-only delivery core.repair_alignment computes --
# so a pass that repairs names cannot delete or insert a word. It subclasses
# ObsAgentLoopPolicy and overrides ONE method (_window_hook); registers here
# for the same reason obs-agent-loop, obs-agent-loop-ojw and obs-replay-loop
# do -- this module is the one policy-registration site run_experiment
# resolves names through.
from ..reproduction.repair_loop import (  # noqa: E402
    OBS_REPAIR_LOOP_OJW_POLICY_NAME,
    OBS_REPAIR_LOOP_POLICY_NAME,
    ObsRepairLoopOjwPolicy,
    ObsRepairLoopPolicy,
)

POLICIES.register(OBS_REPAIR_LOOP_POLICY_NAME, ObsRepairLoopPolicy())

# obs-repair-loop-ojw (owner Decision 12-F, 2026-09-08): the same repair pass
# on the openJiuwen executor. The Earnings obs path is being PORTED onto the
# openJiuwen graph, so the one mechanism that rides the plain policy's
# _window_hook needs a graph-side seat; the sibling class overrides the same
# two methods over ObsAgentLoopOjwPolicy and calls the SAME hook builder and
# the SAME legality check, so there is no second repair implementation to
# drift. Registration is free of openjiuwen imports for exactly the reason
# obs-agent-loop-ojw's is (D2 zero-dependency gate).
POLICIES.register(OBS_REPAIR_LOOP_OJW_POLICY_NAME, ObsRepairLoopOjwPolicy())

# The Reviewer's judges (owner Decision 11-B change #2, 2026-09-08). They
# register HERE for the same reason every policy and the one response
# postprocessor above do: this module is a canonical core.base registration
# site, so a baseline fragment's ``phase_review.<phase>.judges`` ids resolve
# the way its ``policy`` and ``evidence_source`` ids do and
# scripts/checks/engineering_base_check.py can read the registered name set
# from source. The judges themselves live in core/judges.py, each a thin
# adapter over a FROZEN function that already shipped -- the legal-label
# parser and inventory, the MF-9 slot schema rule, the Earnings numeric-format
# classification, the substitution-only alignment's refusal table, the replay
# decode-confidence flag source and the roster-band near-miss detector. No
# rule is added or changed by registering them; what is added is that a cell
# can now DECLARE one and a receipt can quote its version.
#
# core.base.JudgeRegistry checks each entry at the door: callable, identified,
# and declaring criticism_only=True -- a judge scores and flags and never
# proposes a revision (owner Decision 11-C).
from .judges import (  # noqa: E402
    A2T_HARD_VALIDITY_JUDGE_V1,
    E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1,
    E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1,
    EARNINGS_NUMERIC_FORMAT_JUDGE_V1,
    REPLAY_LOGPROB_JUDGE_V1,
    ROSTER_BAND_JUDGE_V1,
    SLURP_INTENT_TOKEN_LOGPROB_JUDGE_V1,
    SLURP_LEGAL_LABEL_JUDGE_V1,
    SLURP_SLOT_SCHEMA_JUDGE_V1,
    A2tHardValidityJudge,
    BriefNameNearMissJudge,
    EarningsNumericFormatJudge,
    ReplayLogprobJudge,
    RosterBandJudge,
    SlurpIntentTokenLogprobJudge,
    SlurpLegalLabelJudge,
    SlurpSlotSchemaJudge,
    SubstitutionAlignmentJudge,
)

JUDGES.register(SLURP_LEGAL_LABEL_JUDGE_V1, SlurpLegalLabelJudge())
JUDGES.register(SLURP_SLOT_SCHEMA_JUDGE_V1, SlurpSlotSchemaJudge())
JUDGES.register(EARNINGS_NUMERIC_FORMAT_JUDGE_V1, EarningsNumericFormatJudge())
JUDGES.register(E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1, SubstitutionAlignmentJudge())
JUDGES.register(REPLAY_LOGPROB_JUDGE_V1, ReplayLogprobJudge())
JUDGES.register(ROSTER_BAND_JUDGE_V1, RosterBandJudge())
# WAVE R7 (2026-09-08): the seventh judge. It wraps the same frozen
# ``validate_hard_validity`` the retired A2T repair controller consulted in
# private, so a cell can now DECLARE the check instead of inheriting it from
# a controller class nobody could switch off.
JUDGES.register(A2T_HARD_VALIDITY_JUDGE_V1, A2tHardValidityJudge())

# LP-2 (2026-09-09): the ninth judge, and the first registered here whose
# threshold is a FROZEN NUMBER READ OFF SEALED DATA rather than a rule with no
# free parameter. It is the preregistered successor of the whole-answer
# ``replay-logprob-flag-v1`` reading, which flew as
# ``SAEA-SLURP-DEV1000-CLOSED-LIST-LOGPROB-V1`` and came back NOT ADMITTED
# because 491 of 1,000 rows put their least-confident token on JSON
# punctuation. Registering it makes the successor DECLARABLE and its version
# quotable; it decides nothing, and the decision is the fresh replicate read
# of ``docs/readiness/
# 2026-09-09-slurp-label-token-logprob-judge-lp2-v1-preregistration.md``.
JUDGES.register(SLURP_INTENT_TOKEN_LOGPROB_JUDGE_V1, SlurpIntentTokenLogprobJudge())

# --- WAVE R7: the frozen-historical A2T AgentLoop policy ids ----------------
#
# Group C of the reuse map (assessment §6.3): seventeen ``policy`` values that
# every Audio2Tool AgentLoop baseline fragment declares and that resolved in NO
# core.base registry. They are NOT registrations of live behaviour -- see
# core/frozen_historical.py for the scan that established that 28 of the 31
# Group C ids appear nowhere in src/ at all, and that every fragment carrying
# one is cited by a sealed receipt and therefore may not be archived or edited.
#
# Each entry RESOLVES (so the engineering-base gate can read the name out of
# this canonical registration site, as it does for every other component id)
# and REFUSES every use, naming the fragment and the sealed receipt instead. An
# A2T cell that must fly again is re-expressed as a registered phase program on
# rails.controllers.EvidenceAgentController -- never by resurrecting the probe
# launcher this name used to reach.
#
# The ids are STRING LITERALS at the call, for the same reason
# rails/tools.py's registration block spells its ids out: the gate reads this
# file's SOURCE without importing the package.
from .frozen_historical import frozen_policy  # noqa: E402

POLICIES.register(
    "fixed-construction-semantic-ground-v2",
    frozen_policy("fixed-construction-semantic-ground-v2"),
)
POLICIES.register(
    "training-free-contract-preserving-self-transcript-cascade-v2",
    frozen_policy("training-free-contract-preserving-self-transcript-cascade-v2"),
)
POLICIES.register(
    "fixed-full-executable-ground-qualification-v1",
    frozen_policy("fixed-full-executable-ground-qualification-v1"),
)
POLICIES.register(
    "training-free-factor-top1-v1", frozen_policy("training-free-factor-top1-v1")
)
POLICIES.register(
    "a2t-g3-plain-english-k32-hard-validity-v1",
    frozen_policy("a2t-g3-plain-english-k32-hard-validity-v1"),
)
POLICIES.register(
    "saea-a2t-g4-executable-microground-single-contact-v1",
    frozen_policy("saea-a2t-g4-executable-microground-single-contact-v1"),
)
POLICIES.register(
    "saea-a2t-g5-plan-compile-execute-v1",
    frozen_policy("saea-a2t-g5-plan-compile-execute-v1"),
)
POLICIES.register(
    "saea-a2t-g6-exhaustive-family-sweep-v1",
    frozen_policy("saea-a2t-g6-exhaustive-family-sweep-v1"),
)
POLICIES.register(
    "saea-a2t-g7-multimodal-exhaustive-example-ground-v2",
    frozen_policy("saea-a2t-g7-multimodal-exhaustive-example-ground-v2"),
)
POLICIES.register(
    "saea-a2t-g8-action-support-reachability-v1",
    frozen_policy("saea-a2t-g8-action-support-reachability-v1"),
)
POLICIES.register(
    "saea-a2t-g8b-action-support-reachability-v1",
    frozen_policy("saea-a2t-g8b-action-support-reachability-v1"),
)
POLICIES.register(
    "saea-a2t-g8c-action-support-reachability-v1",
    frozen_policy("saea-a2t-g8c-action-support-reachability-v1"),
)
POLICIES.register(
    "native-structured-action-screen-v1",
    frozen_policy("native-structured-action-screen-v1"),
)
POLICIES.register(
    "training-free-self-consistency-v1",
    frozen_policy("training-free-self-consistency-v1"),
)
POLICIES.register(
    "training-free-self-transcript-cascade-v1",
    frozen_policy("training-free-self-transcript-cascade-v1"),
)
POLICIES.register(
    "semantic-agentloop-select-fill-top32-v1",
    frozen_policy("semantic-agentloop-select-fill-top32-v1"),
)
POLICIES.register(
    "semantic-agentloop-top16-v1", frozen_policy("semantic-agentloop-top16-v1")
)
# --- end WAVE R7 -----------------------------------------------------------

# e21-brief-name-near-miss-v1 (E21-LOOP-1, 2026-09-08): the design note's
# "brief-name near-miss detector", the one judge in that table that had no
# implementation. Registered here for the same reason the six above are.
JUDGES.register(E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1, BriefNameNearMissJudge())

# Registered SLURP delivery rules. The historical rule preserves predecessor
# intent authority; the joint-hypothesis rule validates alternatives while
# making the final response authoritative for intent and entities.
from ..reproduction.slurp_delivery import (  # noqa: E402
    slurp_hard_first_hypothesis_delivery_v1,
    slurp_intent_slots_delivery_v1,
    slurp_joint_hypothesis_delivery_v1,
    slurp_shortlist_joint_hypothesis_delivery_v1,
)

RESPONSE_POSTPROCESSORS.register(
    "slurp-intent-slots-delivery-v1", slurp_intent_slots_delivery_v1
)
RESPONSE_POSTPROCESSORS.register(
    "slurp-joint-hypothesis-delivery-v1",
    slurp_joint_hypothesis_delivery_v1,
)

RESPONSE_POSTPROCESSORS.register(
    "slurp-hard-first-hypothesis-delivery-v1",
    slurp_hard_first_hypothesis_delivery_v1,
)

RESPONSE_POSTPROCESSORS.register(
    "slurp-shortlist-joint-hypothesis-delivery-v1",
    slurp_shortlist_joint_hypothesis_delivery_v1,
)
