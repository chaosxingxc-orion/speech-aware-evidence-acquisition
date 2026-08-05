"""Execution policies over the three D2-frozen arm shapes (the policy seam).

R0 implements exactly one policy: ``fixed`` — one request per sample, always
admit. X1 re-resolution (multiple requests), X3 verification/rejection loops
and X4 reward-guided action selection register here later; the arm payload
vocabulary never grows without a new D2 receipt.
"""

from __future__ import annotations

from typing import Mapping

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
        )


POLICIES.register("fixed", FixedPolicy())
