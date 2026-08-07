"""``run_experiment``: config + plan -> gate -> run -> outputs, and ``load_split``.

Split out of the former monolithic ``core/driver.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). R0 repair refactor stage 2 (part C):
the split<->plan<->config cross-checks moved to ``split_check.py``'s
``_verify_split_for_run``, and the post-loop cost assembly moved to
``cost.py``'s ``_assemble_run_cost`` -- both again purely for file size and
again pure moves, each taking exactly the inputs it needs and returning
exactly what ``run_experiment`` folds back in.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Mapping

from ...contracts import ExecutionPlan
from ...data.lock import asset_dir
from ...e0.artifacts import REPO_ROOT
from ..base import (
    CARRIERS,
    EVIDENCE_SOURCES,
    POLICIES,
    CoreError,
    EvidenceError,
    PayloadBindingContext,
    RunResult,
    SampleContext,
)
from ..config import ComposedConfig
from ..evidence import evidence_file_relpath, rotated_mismatch
from ..resources import NullSampler, ResourceSampler, cpu_seconds_snapshot
from ..model import FrozenCoreAdapter
from ..split_receipt import load_verified_split
from ..tracing import TraceSink
from .cost import _assemble_run_cost
from .split_check import _verify_split_for_run


def load_split(
    repo_root: Path, split_name: str, lock: Mapping[str, object], root: Path
) -> tuple[set[str], str, str]:
    """Thin wrapper: strictly parsed AND live-recomputed split (delegates to
    :func:`core.split_receipt.load_verified_split`; see that module for the
    trust boundary this closes)."""

    verified = load_verified_split(repo_root, split_name, lock, root)
    return set(verified.ids), verified.identity_hash, verified.split_role


_NO_SAMPLER_PROVIDED_REASON = (
    "no resource sampler was provided to core.driver.run_experiment; only the "
    "live CLI run path (core.driver._cli_run) supplies "
    "core.resources.resolve_resource_sampler() -- every other caller, "
    "including every test, gets an explicit NOT_AVAILABLE record here rather "
    "than a default that could silently shell out to nvidia-smi"
)


def run_experiment(
    composed: ComposedConfig,
    plan: ExecutionPlan,
    gate: object,
    lock: Mapping[str, object],
    root: Path,
    run_dir: Path,
    transport: Callable[[bytes], bytes],
    repo_root: Path = REPO_ROOT,
    *,
    resource_sampler: ResourceSampler | None = None,
) -> RunResult:
    # R0 repair T7 (I8): the run-level cost window opens here, before ANY
    # setup work (split/carrier/evidence resolution, gate check, attempt
    # reservation) -- gpu_seconds/cpu_seconds below cover the whole run, not
    # merely the per-sample request loop. See core/resources.py for why the
    # default here is a no-op NullSampler rather than an implicit real one.
    sampler: ResourceSampler = (
        resource_sampler if resource_sampler is not None else NullSampler(_NO_SAMPLER_PROVIDED_REASON)
    )
    cpu_start = cpu_seconds_snapshot()
    setup_started = time.monotonic()
    sampler.start()
    try:
        values = composed.values
        arm = str(values["arm"])
        # R0 repair refactor stage 2 (part C): the split<->plan<->config
        # cross-checks (M-2, split identity hash/role/carrier, protocol hash)
        # live in split_check._verify_split_for_run now -- same checks, same
        # order, same CoreError messages.
        verified_split = _verify_split_for_run(composed, plan, lock, root, repo_root)
        sample_ids = set(verified_split.ids)
        loader = CARRIERS.resolve(str(values["carrier_lock_key"]))
        samples = [s for s in loader(lock, root) if s.sample_id in sample_ids]
        if {s.sample_id for s in samples} != sample_ids:
            raise CoreError("split ids missing from the carrier's loaded samples")
        source = EVIDENCE_SOURCES.resolve(str(values.get("evidence_source", "none")))
        # R0 repair refactor stage 2 (part B): every evidence source now takes
        # the sample's own carrier_lock_key explicitly (core.evidence module
        # docstring) so a carrier-aware source (e.g. conec-contexts) can
        # resolve its layout via that carrier's own CarrierDescriptor instead
        # of guessing/hardcoding a single carrier's path.
        evidence_by_sample = {
            s.sample_id: source(lock, root, s.sample_id, s.carrier_lock_key) for s in samples
        }
        # IMPORTANT 1 (external-threat-model review round 4): the D1
        # evidence-identity rail's facts (core.model.lifecycle's own
        # verify_evidence_identity call), built from the ORIGINAL
        # (pre-rotation) evidence_by_sample -- i.e. exactly the sample ids
        # this run's evidence source itself supplied non-empty evidence for,
        # using each sample's OWN D1-recorded evidence file
        # (core.evidence.evidence_file_relpath -- never hand-coded, module
        # docstring). Computed BEFORE any evidence_mismatch/rotated_mismatch
        # reassignment below so this checks the byte-integrity of the
        # evidence CORPUS the run's evidence source drew from, independent of
        # which sample a later negative-control experiment happens to route
        # that content to (see gate_evidence_identity's own docstring for why
        # this scoping is deliberate, not an oversight).
        evidence_relpaths: dict[str, str] = {}
        for s in samples:
            if not evidence_by_sample[s.sample_id]:
                continue
            try:
                evidence_relpaths[s.sample_id] = evidence_file_relpath(
                    lock, s.carrier_lock_key, s.sample_id
                )
            except EvidenceError as error:
                raise CoreError(
                    f"cannot resolve a D1 evidence-identity path for sample "
                    f"{s.sample_id!r}: {error}"
                ) from error
        if values.get("evidence_mismatch", False):
            evidence_by_sample = rotated_mismatch(evidence_by_sample)
        policy = POLICIES.resolve(str(values["policy"]))
        sink = TraceSink(run_dir, plan.run_id)
        # Payload<->plan<->split binding context (R0 repair T3, I3/I4): built here,
        # from exactly the verified split ids and the same loader's SampleRef
        # facts already used above to validate the carrier's loaded samples --
        # never from anything a payload later claims about itself.
        carrier_root = asset_dir(lock, str(values["carrier_lock_key"]), root)
        binding = PayloadBindingContext(
            carrier_lock_key=str(values["carrier_lock_key"]),
            allowed_sample_ids=frozenset(sample_ids),
            sample_facts={s.sample_id: (s.audio_seconds, s.sample_rate_hz) for s in samples},
            # I-4: the SAME loader's per-sample media_relpath, so
            # core.model.FrozenCoreAdapter can ask the gate to re-verify
            # exactly this run's split against D1's frozen media identity --
            # never a parallel/independently-derived path string.
            media_relpaths={s.sample_id: s.media_relpath for s in samples},
            # IMPORTANT 1: the evidence-layer counterpart, see above.
            evidence_relpaths=evidence_relpaths,
            data_root=Path(root),
            carrier_root=carrier_root,
        )
        adapter = FrozenCoreAdapter(
            gate=gate, plan=plan, arm=arm, transport=transport, sink=sink, binding=binding
        )
        # R0 repair T7 (I8): "setup" ends here -- split/carrier/evidence
        # resolution plus the gate check and attempt reservation the adapter's
        # own construction just performed. Everything from here down is the
        # per-sample request loop.
        gate_setup_seconds = time.monotonic() - setup_started
        outputs_path = Path(run_dir) / f"{plan.run_id}.outputs.jsonl"
        try:
            outputs_handle = outputs_path.open("x", encoding="utf-8", newline="\n")
        except FileExistsError as error:
            raise CoreError(
                f"outputs file already exists: {outputs_path}; a re-run must use a "
                "fresh attempt directory, not overwrite a prior attempt's outputs"
            ) from error
        # R0 repair T7 (I8): evidence volume. `supply_content_bytes` was
        # already computed per sample for the SUPPLY trace record below --
        # this aggregates exactly that figure, never a parallel computation.
        # "admitted" bytes narrows to samples whose SampleOutcome.admitted the
        # policy actually set True (today's only policy, FixedPolicy, always
        # admits, so the two totals coincide in R0 -- the split exists for a
        # future rejecting policy, e.g. X3).
        supplied_evidence_bytes = 0
        admitted_evidence_bytes = 0
        with outputs_handle as outputs:
            for index, sample in enumerate(sorted(samples, key=lambda s: s.sample_id), start=1):
                request_id_base = f"req-{index:04d}"
                view = sample.runtime_view()
                sink.emit(
                    "OBS",
                    f"{request_id_base}/obs",
                    {
                        "obs_speech_ref": view["speech_ref"],
                        "obs_audio_seconds": view["audio_seconds"],
                    },
                )
                evidence = evidence_by_sample.get(sample.sample_id, [])
                sample_evidence_bytes = 0
                if evidence:
                    sample_evidence_bytes = sum(
                        len(item.content.encode("utf-8")) for item in evidence
                    )
                    supplied_evidence_bytes += sample_evidence_bytes
                    sink.emit(
                        "ORG",
                        f"{request_id_base}/org",
                        {
                            "org_evidence_count": len(evidence),
                            "org_source_lock_keys": sorted(
                                {item.provenance["lock_key"] for item in evidence}
                            ),
                        },
                    )
                    sink.emit(
                        "SUPPLY",
                        f"{request_id_base}/supply",
                        {
                            "supply_evidence_ids": [item.evidence_id for item in evidence],
                            "supply_content_bytes": sample_evidence_bytes,
                        },
                    )
                ctx = SampleContext(
                    sample=sample,
                    evidence=evidence,
                    adapter=adapter,
                    sink=sink,
                    arm=arm,
                    task_instruction=str(values["task_instruction"]),
                    decoding_params=dict(values.get("decoding_params", {})),
                    request_id_base=request_id_base,
                    retrieval_query=values.get("retrieval_query"),
                )
                outcome = policy.run_sample(ctx)
                if evidence and outcome.admitted:
                    admitted_evidence_bytes += sample_evidence_bytes
                outputs.write(
                    json.dumps(
                        {
                            "request_id": request_id_base,
                            "sample_id": outcome.sample_id,
                            "carrier_lock_key": sample.carrier_lock_key,
                            "arm": arm,
                            "text": outcome.text,
                            "admitted": outcome.admitted,
                            "request_sha256": outcome.request_sha256,
                            "response_sha256": outcome.response_sha256,
                            "response_text_sha256": outcome.response_text_sha256,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
        manifest_hash = sink.close()
    finally:
        sampler.stop()
    resource_summary = dict(sampler.summary())
    cpu_seconds = cpu_seconds_snapshot() - cpu_start
    # R0 repair refactor stage 2 (part C): durable GPU-seconds recording,
    # best-effort sibling-ABORTED-attempt cost folding, and the final cost
    # dict assembly all live in cost._assemble_run_cost now -- same fields,
    # same best-effort/never-raise discipline (I8), see that function's own
    # comments (carried verbatim there).
    cost = _assemble_run_cost(
        root=root,
        plan=plan,
        adapter=adapter,
        resource_summary=resource_summary,
        cpu_seconds=cpu_seconds,
        gate_setup_seconds=gate_setup_seconds,
        supplied_evidence_bytes=supplied_evidence_bytes,
        admitted_evidence_bytes=admitted_evidence_bytes,
    )
    return RunResult(
        run_id=plan.run_id,
        arm=arm,
        outputs_path=outputs_path,
        trace_manifest_hash=manifest_hash,
        cost=cost,
    )

