"""Execution policies over the three D2-frozen arm shapes (the policy seam).

R0 implements exactly one policy: ``fixed`` — one request per sample, always
admit. X1 re-resolution (multiple requests), X3 verification/rejection loops
and X4 reward-guided action selection register here later; the arm payload
vocabulary never grows without a new D2 receipt.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from ..data.loader import SampleRef
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .base import POLICIES, EvidenceItem, SampleContext, SampleOutcome


class ArmError(RuntimeError):
    """An arm builder was given inputs its D2-frozen field set cannot carry."""


def build_arm_payload(
    arm: str,
    ref: SampleRef,
    request_id: str,
    task_instruction: str,
    decoding_params: Mapping[str, object],
    evidence: list[EvidenceItem] | None = None,
    retrieval_query: str | None = None,
    exemplar_bank: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    if arm not in ARM_VISIBLE_FIELDS:
        raise ArmError(f"unknown arm {arm!r}; D2-frozen arms are {sorted(ARM_VISIBLE_FIELDS)}")
    payload: dict[str, object] = dict(ref.runtime_view())
    payload["request_id"] = request_id
    payload["task_instruction"] = task_instruction
    payload["history"] = []
    payload["decoding_params"] = dict(decoding_params)
    if arm == "bare-core":
        if evidence is not None or retrieval_query is not None:
            raise ArmError("bare-core carries no evidence and no retrieval query")
    else:
        if not evidence:
            raise ArmError(f"arm {arm!r} requires non-empty evidence")
        validated = [item.validate() for item in evidence]
        provenance = [item.provenance_view() for item in validated]
        if arm == "fixed-legal-context":
            if retrieval_query is not None:
                raise ArmError("fixed-legal-context carries no retrieval query")
            payload["supplied_evidence"] = [item.runtime_view() for item in validated]
        else:  # fixed-retrieval
            if retrieval_query is None or not retrieval_query.strip():
                raise ArmError("fixed-retrieval requires a retrieval_query")
            payload["retrieval_query"] = retrieval_query
            payload["retrieved_evidence"] = [item.runtime_view() for item in validated]
        payload["evidence_provenance"] = provenance
    # Acoustic exemplar bank (core.exemplars module docstring, M-C-prime prep
    # infrastructure): orthogonal to the evidence/retrieval_query handling
    # above -- default None is a no-op (byte-identical payload, the pre
    # -existing shape), and a supplied bank (possibly empty -- an empty bank
    # is a legal v3 shape, core.model.transport's own module docstring) is
    # attached ONLY for an arm whose D2-frozen field set actually declares
    # "exemplar_bank"; no arm does yet (this ships ahead of any consuming
    # arm, mirroring how core.model.transport's v3 prompt order itself
    # shipped unused before this module existed), so every arm registered
    # today fails closed here rather than silently dropping the bank.
    if exemplar_bank is not None:
        if "exemplar_bank" not in ARM_VISIBLE_FIELDS[arm]:
            raise ArmError(
                f"arm {arm!r} does not declare 'exemplar_bank' in its D2-frozen field "
                "set; cannot attach an exemplar bank to this arm's payload"
            )
        payload["exemplar_bank"] = [dict(pair) for pair in exemplar_bank]
    if set(payload) != set(ARM_VISIBLE_FIELDS[arm]):
        raise ArmError(
            f"arm {arm!r} builder produced a field set that diverges from the D2 freeze: "
            f"{sorted(set(payload) ^ set(ARM_VISIBLE_FIELDS[arm]))}"
        )
    return payload


class FixedPolicy:
    """One request per sample; the response is always admitted (R0 wiring)."""

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
        evidence = ctx.evidence if ctx.arm != "bare-core" else None
        payload = build_arm_payload(
            ctx.arm,
            ctx.sample,
            ctx.request_id_base,
            ctx.task_instruction,
            ctx.decoding_params,
            evidence=evidence,
            retrieval_query=ctx.retrieval_query,
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


POLICIES.register("fixed", FixedPolicy())

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
