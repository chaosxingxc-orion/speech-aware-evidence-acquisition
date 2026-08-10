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
from ..evidence import resolve_declared_transform_params, rotated_mismatch
from ..evidence_derivation import DerivedEvidenceRegistry
from ..instructions import resolve_task_instruction
from ..resources import NullSampler, ResourceSampler, cpu_seconds_snapshot
from ..model import FrozenCoreAdapter, SliceRegistry
from ..split_receipt import load_verified_split
from ..tracing import DispatchingSink, TraceBuffer, TraceSink
from .cost import _assemble_run_cost
from .split_check import _verify_split_for_run


def _sample_batch_size(values: Mapping[str, object]) -> int:
    """The sample-level concurrency knob (owner batching directive
    2026-08-08). Declared in the baseline fragment (-> config_hash ->
    protocol_hash); 1 (the default) is exactly the pre-batching sequential
    path; anything unusable refuses fail-closed."""

    raw = values.get("obs_batch_samples", 1)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise CoreError(
            f"config obs_batch_samples must be an integer >= 1 (1 = sequential), "
            f"got {raw!r}"
        )
    return raw


def _emit_sample_preamble(sink: object, request_id_base: str, sample, evidence) -> int:
    """The per-sample OBS/ORG/SUPPLY records run_experiment emits BEFORE the
    policy runs — one code path for both the sequential loop (real sink) and
    the batch path (per-sample TraceBuffer). Returns the sample's supplied
    evidence bytes (the figure the SUPPLY record itself carries)."""

    view = sample.runtime_view()
    sink.emit(
        "OBS",
        f"{request_id_base}/obs",
        {
            "obs_speech_ref": view["speech_ref"],
            "obs_audio_seconds": view["audio_seconds"],
        },
    )
    sample_evidence_bytes = 0
    if evidence:
        sample_evidence_bytes = sum(len(item.content.encode("utf-8")) for item in evidence)
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
    return sample_evidence_bytes


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
        # B-2a (core.evidence module docstring): every evidence source ALSO
        # takes this run's composed config `values` (optional on the
        # function signature -- every pre-existing source ignores it), the
        # SAME `values` mapping `resolve_task_instruction` above already
        # reads knobs from, so a source-specific knob (e.g. `conec-bias-
        # list`'s `bias_list_max_entries`) is config plumbing only, never a
        # new call site.
        evidence_by_sample = {
            s.sample_id: source(lock, root, s.sample_id, s.carrier_lock_key, values)
            for s in samples
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
        # IMPROVEMENT (fifth external-threat-model review): the SAME
        # already-read content, keyed identically to evidence_relpaths --
        # gives the D1 evidence-identity rail something to check that is
        # bound to the bytes this run will actually put in the prompt,
        # rather than a second, later read of the file (see
        # contracts.gate_evidence_identity's own module docstring for the
        # check<->send race this closes). Built here, from exactly the same
        # evidence_by_sample this loop already reads for evidence_relpaths --
        # never a fresh disk read.
        evidence_contents: dict[str, bytes] = {}
        # Derivation-chain rail (2026-08-09, docs/readiness/2026-08-09-conec-
        # evidence-shape.md "Blocking gap"): a fresh registry per run, no
        # shared state across runs (mirrors core.model.slices.SliceRegistry).
        # Every sample's evidence item(s) must carry a DerivedEvidenceRecord
        # this registry can independently re-verify -- source bytes actually
        # read, a registered pinned transform, params matching THIS run's own
        # config, and the content this run will actually send re-hashing to
        # the claimed derived_sha256 -- before this run is allowed to
        # proceed. Computed BEFORE any evidence_mismatch/rotated_mismatch
        # reassignment below, same discipline as the (unchanged) D1
        # evidence-identity facts just below: this checks the derivation
        # integrity of the evidence CORPUS the run's evidence source itself
        # produced, independent of which sample a later negative-control
        # experiment happens to route that content to.
        derivation_registry = DerivedEvidenceRegistry()
        for s in samples:
            items = evidence_by_sample[s.sample_id]
            if not items:
                continue
            for item in items:
                record = item.derivation
                if record is None:
                    raise CoreError(
                        f"evidence source {values.get('evidence_source')!r} returned "
                        f"evidence for sample {s.sample_id!r} with no derivation "
                        "record; identity can never be proven for evidence that does "
                        "not chain to a verified source (docs/readiness/2026-08-09-"
                        "conec-evidence-shape.md)"
                    )
                if record.sample_id != s.sample_id:
                    raise CoreError(
                        f"evidence derivation record sample_id {record.sample_id!r} "
                        f"does not match the sample it was returned for "
                        f"({s.sample_id!r})"
                    )
                try:
                    params = resolve_declared_transform_params(record.transform_name, values)
                except EvidenceError as error:
                    raise CoreError(
                        f"cannot resolve declared params for evidence transform "
                        f"{record.transform_name!r} (sample {s.sample_id!r}): {error}"
                    ) from error
                try:
                    derivation_registry.register(
                        record,
                        source_content=item.derivation_source_bytes,
                        derived_content=item.content.encode("utf-8"),
                        params=params,
                    )
                except EvidenceError as error:
                    raise CoreError(
                        f"evidence derivation chain refused for sample "
                        f"{s.sample_id!r}: {error}"
                    ) from error
                if record.carrier_bound:
                    # IMPORTANT 1 (external-threat-model review round 4,
                    # UNCHANGED rail): re-verify exactly the SOURCE facts a
                    # carrier_bound record chains to against D1's frozen
                    # per-sample identity -- never the derived/transformed
                    # content (the blocking gap docs/readiness/2026-08-09-
                    # conec-evidence-shape.md recorded, and core.evidence_
                    # derivation's own module docstring, condition 1). A
                    # carrier_bound=False record (core.base.
                    # DerivedEvidenceRecord docstring) has no D1 anchor at
                    # all and is deliberately excluded here -- its identity
                    # rests solely on the self-verified chain above.
                    evidence_relpaths[s.sample_id] = record.source_relpath
                    evidence_contents[s.sample_id] = item.derivation_source_bytes
        if values.get("evidence_mismatch", False):
            evidence_by_sample = rotated_mismatch(evidence_by_sample)
        policy = POLICIES.resolve(str(values["policy"]))
        # Sample batching (owner directive 2026-08-08): resolved and checked
        # HERE, before the adapter construction below reserves the one-time
        # attempt slot -- a config that demands batching from a policy that
        # only implements run_sample must refuse with no budget ever spent.
        batch_size = _sample_batch_size(values)
        if batch_size > 1 and not callable(getattr(policy, "run_samples", None)):
            raise CoreError(
                f"config obs_batch_samples={batch_size} requires a batch-capable "
                f"policy (run_samples), but policy {values['policy']!r} implements "
                "only run_sample; set obs_batch_samples to 1 or use a "
                "batch-capable policy"
            )
        # P1 scaffold: the run's single task instruction resolves HERE -- a
        # literal `task_instruction` passes through unchanged (every
        # pre-existing config), a `task_instruction_template` +
        # `task_instruction_fill` pair renders the frozen template from
        # pinned carrier data (core.instructions). Resolved once, BEFORE the
        # adapter construction below opens the attempt, so an unrenderable
        # instruction refuses with no budget ever spent.
        task_instruction = resolve_task_instruction(values, repo_root, lock, root)
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
            # IMPROVEMENT: the already-read content bound to the same keys, see
            # above.
            evidence_contents=evidence_contents,
            data_root=Path(root),
            carrier_root=carrier_root,
        )
        # obs-agent-loop rail (owner directive 2026-08-08): the per-run slice
        # registry, built from EXACTLY the same loader facts the binding above
        # carries. Always constructed (an empty registry admits nothing, so
        # whole-file policies are untouched); the adapter consults it in
        # _enforce_payload_binding, and a slice-cutting policy reaches the SAME
        # object through SampleContext.extras below -- one registry, two ends
        # of the derivation chain.
        slice_registry = SliceRegistry(
            data_root=Path(root),
            run_id=plan.run_id,
            parent_facts={s.sample_id: (s.media_relpath, s.audio_seconds) for s in samples},
        )
        # Batch mode routes the shared adapter's per-request records to the
        # CURRENT sample task's TraceBuffer (core.tracing.DispatchingSink,
        # contextvar-driven); sequential mode keeps the adapter on the real
        # sink exactly as before.
        adapter_sink = sink if batch_size == 1 else DispatchingSink(sink)
        adapter = FrozenCoreAdapter(
            gate=gate, plan=plan, arm=arm, transport=transport, sink=adapter_sink,
            binding=binding, slice_registry=slice_registry,
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
        # Per-slice decode-cap saturation, aggregated per RUN (2026-08-09,
        # continues the obs-loop E-001 retry finding): SampleOutcome.
        # saturated_slices is 0 for every non-slicing policy (FixedPolicy),
        # so this aggregate is exact and free of a policy-name branch --
        # exactly the same "sum whatever the outcome already reports" pattern
        # supplied/admitted_evidence_bytes use above.
        saturated_slice_total = 0
        saturated_sample_ids: list[str] = []
        def _sample_context(sample, evidence, request_id_base, ctx_sink):
            return SampleContext(
                sample=sample,
                evidence=evidence,
                adapter=adapter,
                sink=ctx_sink,
                arm=arm,
                task_instruction=task_instruction,
                decoding_params=dict(values.get("decoding_params", {})),
                request_id_base=request_id_base,
                retrieval_query=values.get("retrieval_query"),
                # obs-agent-loop rail: run facts a slice-cutting policy
                # needs (the SAME slice_registry the adapter enforces
                # against, the controlled roots, and the composed config
                # values its obs_* knobs live in). A fresh dict per sample
                # so no policy can leak per-sample mutations across
                # samples; whole-file policies simply never read these.
                extras={
                    "slice_registry": slice_registry,
                    "data_root": Path(root),
                    "run_dir": Path(run_dir),
                    "repo_root": Path(repo_root),
                    "config_values": values,
                },
            )

        def _write_row(outputs, request_id_base, sample, outcome):
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

        ordered_samples = sorted(samples, key=lambda s: s.sample_id)
        with outputs_handle as outputs:
            if batch_size == 1:
                for index, sample in enumerate(ordered_samples, start=1):
                    request_id_base = f"req-{index:04d}"
                    evidence = evidence_by_sample.get(sample.sample_id, [])
                    sample_evidence_bytes = _emit_sample_preamble(
                        sink, request_id_base, sample, evidence
                    )
                    supplied_evidence_bytes += sample_evidence_bytes
                    ctx = _sample_context(sample, evidence, request_id_base, sink)
                    outcome = policy.run_sample(ctx)
                    if evidence and outcome.admitted:
                        admitted_evidence_bytes += sample_evidence_bytes
                    if outcome.saturated_slices:
                        saturated_slice_total += outcome.saturated_slices
                        saturated_sample_ids.append(outcome.sample_id)
                    _write_row(outputs, request_id_base, sample, outcome)
            else:
                # Batch path (owner directive 2026-08-08): each sample's
                # ENTIRE trace (driver preamble + policy records + the shared
                # adapter's per-request records, routed by DispatchingSink)
                # buffers in its own TraceBuffer; the policy's run_samples
                # executes up to batch_size samples concurrently and returns
                # outcomes aligned to the contexts (raising the FIRST failed
                # sample's error in split-id order after all tasks settle);
                # rows and trace blocks then land strictly in split-id order
                # -- deterministic by construction, never completion order.
                entries = []
                for index, sample in enumerate(ordered_samples, start=1):
                    request_id_base = f"req-{index:04d}"
                    evidence = evidence_by_sample.get(sample.sample_id, [])
                    buffer = TraceBuffer(plan.run_id)
                    sample_evidence_bytes = _emit_sample_preamble(
                        buffer, request_id_base, sample, evidence
                    )
                    supplied_evidence_bytes += sample_evidence_bytes
                    ctx = _sample_context(sample, evidence, request_id_base, buffer)
                    entries.append(
                        (sample, evidence, sample_evidence_bytes, buffer, ctx, request_id_base)
                    )
                outcomes = policy.run_samples([entry[4] for entry in entries])
                if not isinstance(outcomes, list) or len(outcomes) != len(entries):
                    raise CoreError(
                        f"policy {values['policy']!r} run_samples returned "
                        f"{type(outcomes).__name__} of length "
                        f"{len(outcomes) if isinstance(outcomes, list) else 'n/a'} "
                        f"for {len(entries)} samples; refusing a misaligned batch"
                    )
                for (sample, evidence, sample_evidence_bytes, buffer, ctx, request_id_base), outcome in zip(
                    entries, outcomes
                ):
                    buffer.flush_into(sink)
                    if evidence and outcome.admitted:
                        admitted_evidence_bytes += sample_evidence_bytes
                    if outcome.saturated_slices:
                        saturated_slice_total += outcome.saturated_slices
                        saturated_sample_ids.append(outcome.sample_id)
                    _write_row(outputs, request_id_base, sample, outcome)
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
        saturated_slice_count=saturated_slice_total,
        saturated_sample_ids=sorted(saturated_sample_ids),
    )
    return RunResult(
        run_id=plan.run_id,
        arm=arm,
        outputs_path=outputs_path,
        trace_manifest_hash=manifest_hash,
        cost=cost,
    )

