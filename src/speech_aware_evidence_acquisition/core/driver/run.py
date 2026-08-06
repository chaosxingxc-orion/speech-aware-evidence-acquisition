"""``run_experiment``: config + plan -> gate -> run -> outputs, and ``load_split``.

Split out of the former monolithic ``core/driver.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Callable, Mapping

from ...contracts import ExecutionPlan
from ...data.lock import asset_dir
from ...e0.artifacts import REPO_ROOT
from ..attempts import STATE_ABORTED, AttemptError, AttemptStore
from ..base import (
    CARRIERS,
    EVIDENCE_SOURCES,
    POLICIES,
    CoreError,
    PayloadBindingContext,
    RunResult,
    SampleContext,
)
from ..config import ComposedConfig, protocol_hash
from ..evidence import rotated_mismatch
from ..resources import (
    NOT_AVAILABLE,
    NullSampler,
    ResourceSampler,
    cpu_seconds_snapshot,
)
from ..model import FrozenCoreAdapter
from ..split_receipt import load_verified_split
from ..tracing import TraceSink


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
        verified_split = load_verified_split(repo_root, str(values["split_name"]), lock, root)
        sample_ids = set(verified_split.ids)
        split_hash = verified_split.identity_hash
        receipt_split_role = verified_split.split_role
        if plan.split_identity_hash != split_hash:
            raise CoreError(
                "plan split identity hash does not match the frozen splits receipt "
                f"for split {values['split_name']!r}"
            )
        if plan.split_role != receipt_split_role:
            raise CoreError(
                f"plan split role {plan.split_role!r} does not match the frozen splits "
                f"receipt split role {receipt_split_role!r} for split {values['split_name']!r}"
            )
        # M-2 (external-threat-model review): the split RECEIPT's own carrier
        # must agree with the plan's carrier too, not just its hash/role. Today
        # this is masked by the two registered carriers (earnings21-original,
        # earnings22-original) having disjoint id namespaces -- a wrong-carrier
        # split/plan pairing is indirectly caught a few lines below ("split ids
        # missing from the carrier's loaded samples") only because the ids
        # never happen to overlap. That is an accident of today's two loaders,
        # not a guarantee: `conec` is a `speech-aware-core` lock key keyed on
        # Earnings21 ids, so a future conec-aware loader sharing that id space
        # would make the indirect check silently pass on a split verified for
        # a DIFFERENT carrier than the one the plan/config actually name. This
        # check is direct and carrier-name-based, so it holds regardless of
        # whether any two carriers' id spaces happen to overlap.
        if verified_split.carrier_lock_key != plan.carrier_lock_key:
            raise CoreError(
                f"plan carrier_lock_key {plan.carrier_lock_key!r} does not match the "
                f"frozen splits receipt carrier_lock_key {verified_split.carrier_lock_key!r} "
                f"for split {values['split_name']!r} (M-2: a split verified for one carrier "
                "can never authorize a run against another)"
            )
        if str(values["carrier_lock_key"]) != plan.carrier_lock_key:
            raise CoreError(
                f"plan carrier_lock_key {plan.carrier_lock_key!r} does not match the "
                f"composed config carrier {values['carrier_lock_key']!r}"
            )
        expected_protocol = protocol_hash(composed.config_hash, arm, split_hash)
        if plan.protocol_hash != expected_protocol:
            raise CoreError(
                f"plan protocol hash {plan.protocol_hash!r} does not match the composed "
                f"config/arm/split protocol hash {expected_protocol!r}"
            )
        loader = CARRIERS.resolve(str(values["carrier_lock_key"]))
        samples = [s for s in loader(lock, root) if s.sample_id in sample_ids]
        if {s.sample_id for s in samples} != sample_ids:
            raise CoreError("split ids missing from the carrier's loaded samples")
        source = EVIDENCE_SOURCES.resolve(str(values.get("evidence_source", "none")))
        evidence_by_sample = {
            s.sample_id: source(lock, root, s.sample_id) for s in samples
        }
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
    # Minor (fix-wave2, external-threat-model review round 2): gpu hours was
    # the only budget dimension with no derived counterpart, even though
    # gpu_seconds IS measured here, per run. Feed the measured total back
    # into THIS attempt's own durable record (AttemptStore.record_gpu_seconds)
    # so it is available to any reader of this run's actual usage --
    # AttemptStore.all_actual_usage() is no longer read by a slice-wide
    # budget-cap check (that check was retired by the 2026-08-06 owner
    # amendment, SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS), but durable,
    # accurate per-run cost accounting stays useful regardless.
    # Best-effort and never allowed to turn a genuinely successful run into a
    # false failure: `resource_summary["gpu_seconds"]` legitimately reads the
    # NOT_AVAILABLE sentinel string (no sampler, or a broken nvidia-smi -- see
    # core.resources) far more often than a real run ever measures it, and a
    # durable-file write failure here is exactly the kind of sibling-
    # bookkeeping failure the failed_attempt_* read just below already
    # tolerates the same way -- this run's own request loop, outputs and
    # trace are already durable on disk by this point regardless.
    measured_gpu_seconds = resource_summary.get("gpu_seconds")
    if (
        isinstance(measured_gpu_seconds, (int, float))
        and not isinstance(measured_gpu_seconds, bool)
        and math.isfinite(measured_gpu_seconds)
        and measured_gpu_seconds >= 0
    ):
        try:
            AttemptStore(Path(root) / "attempts").handle(
                plan.run_id, plan.attempt_id
            ).record_gpu_seconds(measured_gpu_seconds)
        except (AttemptError, OSError, ValueError):
            pass
    # R0 repair T7 (I8): failed-attempt cost. Sibling attempts under this SAME
    # run_id that are (as of manifest time) ABORTED -- e.g. a crashed attempt
    # this run_id's caller retried under a fresh attempt_id -- spent real
    # calls/audio this run's OWN plan budget already counts (core.attempts.
    # AttemptStore.prior_actual_usage folds every state in), but a reader of
    # this successful attempt's OWN cost block previously had no way to see
    # that extra, wasted spend. `exclude_attempt_id` keeps this run's own
    # attempt (never itself ABORTED on this success path) out of the sum.
    #
    # T7 fix (reviewer-flagged IMPORTANT): this read happens AFTER the run has
    # already fully succeeded -- every model call made, outputs/trace already
    # durable on disk. It must therefore be best-effort, mirroring
    # core.bundle._best_effort_cost_for_aborted_attempt's identical read:
    # a corrupted or unreadable SIBLING attempt file (someone else's crash,
    # not this run's) must never raise here and turn a genuinely successful,
    # budget-spent run into a false ABORTED manifest via
    # run_experiment_bundled's `except Exception`. On failure this specific
    # pair degrades to NOT_AVAILABLE + a reason -- every OTHER cost field
    # (this run's own calls/audio/latency/tokens/gpu/cpu/evidence/tool_calls)
    # stays fully measured and the run still completes.
    try:
        failed_attempt_calls, failed_attempt_audio_seconds = AttemptStore(
            Path(root) / "attempts"
        ).actual_usage_in_states(
            plan.run_id, frozenset({STATE_ABORTED}), exclude_attempt_id=plan.attempt_id
        )
        failed_attempt_cost_reason = None
    except (AttemptError, OSError, ValueError) as error:
        failed_attempt_calls = NOT_AVAILABLE
        failed_attempt_audio_seconds = NOT_AVAILABLE
        failed_attempt_cost_reason = (
            "could not read sibling ABORTED attempts' usage for run_id "
            f"{plan.run_id!r} from the durable attempts store: {error}; this "
            "run itself succeeded and every other cost field is unaffected"
        )
    cost = dict(adapter.cost_summary())
    cost.update(
        {
            "cpu_seconds": cpu_seconds,
            "gate_setup_seconds": gate_setup_seconds,
            "supplied_evidence_bytes": supplied_evidence_bytes,
            "admitted_evidence_bytes": admitted_evidence_bytes,
            "failed_attempt_calls": failed_attempt_calls,
            "failed_attempt_audio_seconds": failed_attempt_audio_seconds,
            "failed_attempt_cost_reason": failed_attempt_cost_reason,
            # Every field above this line is genuinely measured whenever this
            # function returns a RunResult at all (I8: nothing here is a
            # silent omission) -- unlike gpu_seconds/peak_vram_mib, which
            # `resource_summary` may legitimately report as NOT_AVAILABLE
            # (with `gpu_sampling_reason`) when no sampler -- or no working
            # nvidia-smi -- was available, and unlike failed_attempt_calls/
            # failed_attempt_audio_seconds just above, which may legitimately
            # report NOT_AVAILABLE (with failed_attempt_cost_reason) when a
            # SIBLING attempt file could not be read.
            "cost_unavailable_reason": None,
        }
    )
    cost.update(resource_summary)
    return RunResult(
        run_id=plan.run_id,
        arm=arm,
        outputs_path=outputs_path,
        trace_manifest_hash=manifest_hash,
        cost=cost,
    )

