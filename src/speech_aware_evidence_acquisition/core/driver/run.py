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
from typing import Callable, Mapping, Sequence

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
    declared_derived_media_roots,
    RunResult,
    SampleContext,
)
from ..config import ComposedConfig
from ..evidence import (
    assert_evidence_materialization_id_legal,
    resolve_declared_transform_params,
    rotated_mismatch,
)
from ..evidence_budget import apply_evidence_budget, resolve_evidence_budget_bytes
from ..evidence_derivation import DerivedEvidenceRegistry
from ..exemplars import (
    ExemplarManifest,
    assert_exemplar_manifest_id_legal,
    load_exemplar_manifest,
    resolve_exemplar_bank,
    resolve_exemplar_manifest_id,
)
from ..instructions import resolve_task_instruction
from ..legality import assert_legality_declaration_legal
from ..resources import NullSampler, ResourceSampler, cpu_seconds_snapshot
from ..model import (
    FrozenCoreAdapter,
    SliceRegistry,
    load_speech_feature_packet_ids,
    load_speech_packet_promotion_receipt,
)
from ..split_receipt import load_verified_split
from ..tracing import (
    DispatchingSink,
    TraceBuffer,
    TraceSink,
    set_current_trace_buffer,
)
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


def _obs_pipeline(values: Mapping[str, object], policy_name: str, batch_size: int):
    """The run's ``(prefetch_depth, dispatcher)``, or ``(0, None)``.

    The obs-pipeline throughput fix (2026-09-08; the module comment above
    ``reproduction.obs_loop.ObsDispatcher`` carries the measured defect and
    the design). ``obs_prefetch_depth`` defaults to 0 and 0 means the strictly
    sequential sample loop below is entered unchanged -- no pipeline object is
    built, no trace buffer is interposed, and not one byte of a request, a
    trace record or an outputs row moves.

    Resolved HERE, beside ``_sample_batch_size`` and before the adapter
    construction reserves this attempt's slot, so an illegal combination
    refuses with no budget ever spent. Legality:

    * the depth is an integer >= 0 (``reproduction.obs_loop.
      resolve_prefetch_depth``, the same validator the policy's own config
      object uses, so the two can never disagree);
    * only the slice-parallel ``obs-agent-loop`` policy is pipelined -- it is
      the one policy whose windows are provably independent of each other
      (fixed positions, no rolling tail, no runtime trim), which is exactly
      what makes overlapping two samples safe;
    * ``obs_batch_samples`` must be 1 -- the sample-batch executor already owns
      sample-level concurrency and its own slot pool, and two schedulers would
      multiply the in-flight request count.
    """

    from ...reproduction.obs_loop import (
        OBS_LOOP_POLICY_NAME,
        build_run_dispatcher,
        resolve_prefetch_depth,
    )

    try:
        depth = resolve_prefetch_depth(values)
    except Exception as error:  # ObsLoopError -- surfaced as a driver refusal
        raise CoreError(str(error)) from error
    if depth == 0:
        return 0, None
    if policy_name != OBS_LOOP_POLICY_NAME:
        raise CoreError(
            f"config obs_prefetch_depth={depth} is only defined for policy "
            f"{OBS_LOOP_POLICY_NAME!r} (its windows are the ones proven "
            f"independent), but this run declares {policy_name!r}"
        )
    if batch_size != 1:
        raise CoreError(
            f"config obs_prefetch_depth={depth} requires obs_batch_samples=1, "
            f"got {batch_size}; the sample-batch executor already owns "
            "sample-level concurrency"
        )
    try:
        dispatcher = build_run_dispatcher(values)
    except Exception as error:  # ObsLoopError -- surfaced as a driver refusal
        raise CoreError(str(error)) from error
    return depth, dispatcher


def _speech_feature_queries(
    values: Mapping[str, object], samples: Sequence[object]
) -> dict[str, Mapping[str, str]]:
    """Preflight formal query packets before an attempt is opened.

    Packet ids come from the committed label-free dataset view; packet hashes
    come from the post-preprocessing packet manifests. All packets are loaded
    concurrently and bound to the decoder hash declared by the inference
    model profile. The transport independently validates the same hashes on
    every request.
    """

    if values.get("arm") != "speech-feature-query":
        return {}
    items = values.get("items")
    if not isinstance(items, list):
        raise CoreError("speech-feature-query requires dataset items")
    by_sample: dict[str, Mapping[str, object]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise CoreError("speech-feature-query dataset item must be a mapping")
        sample_id = item.get("sample_id")
        packet_id = item.get("packet_id")
        audio_sha256 = item.get("audio_sha256")
        if (
            not isinstance(sample_id, str)
            or sample_id in by_sample
            or not isinstance(packet_id, str)
            or packet_id != sample_id.replace(":", "/")
            or not isinstance(audio_sha256, str)
            or len(audio_sha256) != 64
        ):
            raise CoreError("speech-feature-query dataset packet identity is malformed")
        by_sample[sample_id] = item
    sample_ids = [str(sample.sample_id) for sample in samples]
    if set(by_sample) != set(sample_ids):
        raise CoreError("speech-feature-query dataset items do not exactly match the split")
    server_env = values.get("server_env")
    if not isinstance(server_env, Mapping):
        raise CoreError("speech-feature-query model profile requires server_env")
    feature_root = server_env.get("LLAMA_SPEECH_FEATURE_ROOT")
    decoder_sha256 = server_env.get("LLAMA_SPEECH_DECODER_SHA256")
    if not isinstance(feature_root, str) or not Path(feature_root).is_absolute():
        raise CoreError("speech-feature-query requires an absolute LLAMA_SPEECH_FEATURE_ROOT")
    if (
        not isinstance(decoder_sha256, str)
        or len(decoder_sha256) != 64
        or any(character not in "0123456789abcdef" for character in decoder_sha256)
    ):
        raise CoreError("speech-feature-query requires a lowercase decoder SHA-256")
    promotion_path = values.get("speech_packet_promotion_receipt")
    promotion_sha256 = values.get("speech_packet_promotion_receipt_sha256")
    if (
        not isinstance(promotion_path, str)
        or not promotion_path
        or not Path(promotion_path).is_absolute()
        or not isinstance(promotion_sha256, str)
    ):
        raise CoreError(
            "speech-feature-query requires an absolute, SHA-pinned promotion receipt"
        )
    promotion = load_speech_packet_promotion_receipt(
        Path(promotion_path),
        expected_sha256=promotion_sha256,
        expected_feature_root=Path(feature_root),
        expected_dataset_runtime_view_sha256=values.get("runtime_view_sha256"),
    )
    packets = load_speech_feature_packet_ids(
        Path(feature_root),
        [by_sample[sample_id]["packet_id"] for sample_id in sample_ids],
        workers=min(_sample_batch_size(values), 64),
        expected_decoder_gguf_sha256=decoder_sha256,
    )
    promoted_packets = promotion["packets"]
    if not isinstance(promoted_packets, list):  # loader already proves this
        raise CoreError("speech packet promotion receipt packets are malformed")
    if len(promoted_packets) != len(sample_ids):
        raise CoreError(
            "speech packet promotion receipt does not exactly cover the split"
        )
    promoted_by_id = {
        str(promoted["packet_id"]): promoted for promoted in promoted_packets
    }
    result: dict[str, Mapping[str, str]] = {}
    for sample_id, packet in zip(sample_ids, packets, strict=True):
        expected_promoted = {
            "packet_id": packet.packet_id,
            "packet_sha256": packet.packet_sha256,
            "audio_sha256": packet.audio_sha256,
            "decoder_gguf_sha256": packet.decoder_gguf_sha256,
            "mmproj_sha256": packet.mmproj_sha256,
        }
        if promoted_by_id.get(packet.packet_id) != expected_promoted:
            raise CoreError(
                f"speech feature packet disagrees with promotion receipt for {sample_id!r}"
            )
        if packet.encoder_receipt_sha256 != promotion["runtime_receipt_sha256"]:
            raise CoreError(
                f"speech feature packet has a different preprocess receipt for {sample_id!r}"
            )
        if packet.audio_sha256 != by_sample[sample_id]["audio_sha256"]:
            raise CoreError(
                f"speech feature packet audio hash disagrees with dataset item {sample_id!r}"
            )
        result[sample_id] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
            "role": "query",
        }
    return result


def _emit_sample_preamble(
    sink: object,
    request_id_base: str,
    sample,
    evidence,
    exemplar_manifest: ExemplarManifest | None = None,
    exemplar_bank: object = None,
) -> int:
    """The per-sample OBS/ORG/SUPPLY records run_experiment emits BEFORE the
    policy runs — one code path for both the sequential loop (real sink) and
    the batch path (per-sample TraceBuffer). Returns the sample's supplied
    evidence bytes (the figure the SUPPLY record itself carries).

    ``exemplar_manifest``/``exemplar_bank`` (core.exemplars module
    docstring): optional and defaulted, so every pre-existing call site
    (there is none outside this module, but the defaults keep the signature
    self-contained) is unaffected. Gated purely on ``exemplar_manifest is
    not None`` -- i.e. the run's composed config actually declared
    ``exemplar_manifest_id`` -- so an absent key emits NO new trace record
    at all (deliverable 1's byte-identity contract), independent of whether
    this particular sample's evidence is empty."""

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
    if exemplar_manifest is not None:
        sink.emit(
            "ORG",
            f"{request_id_base}/org-exemplars",
            {
                "org_exemplar_manifest_id": exemplar_manifest.manifest_id,
                "org_exemplar_manifest_sha256": exemplar_manifest.sha256,
                "org_exemplar_count": len(exemplar_bank or ()),
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
        # SUPPLY dose knob (evidence_budget_bytes, optional baseline-config
        # key): resolved and validated HERE, before any other per-run work
        # (split verification, evidence resolution, the gate/attempt
        # reservation below) -- a malformed value refuses with nothing yet
        # spent, same fail-closed discipline as ObsLoopConfig.from_values
        # (reproduction.obs_loop). See core.evidence_budget's own module
        # docstring for the single application seam below.
        evidence_budget_bytes = resolve_evidence_budget_bytes(values)
        # derived-candidates key-legality matrix (core.evidence module
        # docstring): resolved and validated HERE too, same "before any
        # other per-run work" placement as evidence_budget_bytes above -- a
        # baseline fragment that sets evidence_materialization_id under any
        # OTHER evidence_source refuses before any per-run work happens,
        # rather than the source dispatch below simply never reading (and
        # therefore never catching) a stray key.
        assert_evidence_materialization_id_legal(values)
        # exemplar_manifest_id key-legality matrix (core.exemplars module
        # docstring): resolved and validated HERE too, same "before any
        # other per-run work" placement -- legal only alongside the model
        # fragment's own prompt_order == "evidence-first-system-v3", checked
        # on this SAME flat `values` mapping (core.config.compose already
        # merged the model and baseline fragments' keys into it before this
        # function ever saw it -- the one seam where both are visible).
        assert_exemplar_manifest_id_legal(values)
        # E1-prime (2026-08-16, docs/readiness/2026-08-15-legality-doctrine.md
        # + docs/p2-branch-rule-pins.md vocabulary): the machine-checked
        # either-field rule + oracle-lineage-consistency rule for the three
        # optional span_source/reference_source/legality_tier baseline-config
        # keys. Same "resolved and validated HERE, before any other per-run
        # work" placement as assert_evidence_materialization_id_legal/
        # assert_exemplar_manifest_id_legal above -- a REFUSED declaration
        # spends no attempt budget and touches the frozen core zero times. A
        # merely-missing declaration on an evidence-bearing arm only warns
        # (grandfathering, core.legality module docstring); core.bundle.
        # manifest independently recomputes and records the same three
        # fields verbatim in every run manifest (deliverable 3), so nothing
        # from this call needs to be threaded any further here.
        assert_legality_declaration_legal(values, root)
        # R0 repair refactor stage 2 (part C): the split<->plan<->config
        # cross-checks (M-2, split identity hash/role/carrier, protocol hash)
        # live in split_check._verify_split_for_run now -- same checks, same
        # order, same CoreError messages.
        verified_split = _verify_split_for_run(composed, plan, lock, root, repo_root)
        sample_ids = set(verified_split.ids)
        loader = CARRIERS.resolve(str(values["carrier_lock_key"]))
        configured_loader = getattr(loader, "load_for_config", None)
        if callable(configured_loader):
            dataset_name = composed.fragments.get("dataset")
            if not isinstance(dataset_name, str) or not dataset_name:
                raise CoreError("composed config lacks its dataset fragment identity")
            dataset_path = (
                Path(repo_root) / "configs" / "dataset" / f"{dataset_name}.json"
            )
            carrier_samples = configured_loader(
                lock,
                root,
                dataset_path=dataset_path,
                values=values,
            )
        else:
            carrier_samples = loader(lock, root)
        samples = [s for s in carrier_samples if s.sample_id in sample_ids]
        if {s.sample_id for s in samples} != sample_ids:
            raise CoreError("split ids missing from the carrier's loaded samples")
        speech_feature_query_by_sample = _speech_feature_queries(values, samples)
        # Acoustic exemplar banks (core.exemplars module docstring):
        # resolved HERE, right after `samples` becomes available -- same
        # "before any other per-run work" family as evidence_budget_bytes/
        # evidence_materialization_id above (legality already checked at the
        # top of this function), independent of the evidence pipeline below.
        # exemplar_manifest stays None exactly when the composed config
        # never declared exemplar_manifest_id, so every downstream reader
        # (SampleContext.exemplar_bank, _emit_sample_preamble's ORG record)
        # sees EXACTLY the pre-existing absent state -- byte-identical to
        # before this feature existed.
        exemplar_manifest_id = resolve_exemplar_manifest_id(values)
        if exemplar_manifest_id is not None:
            exemplar_manifest = load_exemplar_manifest(root, exemplar_manifest_id)
            exemplar_bank_by_sample = {
                s.sample_id: resolve_exemplar_bank(exemplar_manifest, s.sample_id)
                for s in samples
            }
        else:
            exemplar_manifest = None
            exemplar_bank_by_sample = {}
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
        # 2026-09-06 (KC-E1): accumulated per item, not assigned per sample.
        # ``conec-class-lists`` returns TWO carrier-bound items per call and the
        # old ``evidence_relpaths[sid] = record.source_relpath`` kept only the
        # last one, so the participant-roster half of the pre-meeting brief was
        # never identity-checked at all. Single-item sources still produce a
        # plain ``str`` value below, byte-identical to before.
        evidence_relpath_lists: dict[str, list[str]] = {}
        # IMPROVEMENT (fifth external-threat-model review): the SAME
        # already-read content, keyed identically to evidence_relpaths --
        # gives the D1 evidence-identity rail something to check that is
        # bound to the bytes this run will actually put in the prompt,
        # rather than a second, later read of the file (see
        # contracts.gate_evidence_identity's own module docstring for the
        # check<->send race this closes). Built here, from exactly the same
        # evidence_by_sample this loop already reads for evidence_relpaths --
        # never a fresh disk read.
        evidence_content_lists: dict[str, list[bytes]] = {}
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
                    evidence_relpath_lists.setdefault(s.sample_id, []).append(
                        record.source_relpath
                    )
                    evidence_content_lists.setdefault(s.sample_id, []).append(
                        item.derivation_source_bytes
                    )
        # One file stays a bare value; several become an ordered tuple whose
        # i-th relpath pairs with the i-th content (core.base.
        # PayloadBindingContext.evidence_relpaths).
        evidence_relpaths: dict[str, str | tuple[str, ...]] = {
            sample_id: (paths[0] if len(paths) == 1 else tuple(paths))
            for sample_id, paths in evidence_relpath_lists.items()
        }
        evidence_contents: dict[str, bytes | tuple[bytes, ...]] = {
            sample_id: (blobs[0] if len(blobs) == 1 else tuple(blobs))
            for sample_id, blobs in evidence_content_lists.items()
        }
        if values.get("evidence_mismatch", False):
            evidence_by_sample = rotated_mismatch(evidence_by_sample)
        # SUPPLY dose knob (continued from the composition-time validation
        # above): applied ONCE per sample, HERE -- before _emit_sample_
        # preamble's OBS/ORG/SUPPLY byte accounting below and before ANY
        # policy's per-slice fan-out (obs-agent-loop sends N requests per
        # sample; this dict is built once, so every one of them reads the
        # SAME already-truncated content). Applied AFTER the derivation
        # -chain registry above (which must see each source's untouched,
        # self-verified content) and AFTER evidence_mismatch rotation (so a
        # mismatched-evidence negative control is budgeted exactly like a
        # normal run). budget_bytes<=0 is unlimited and returns
        # evidence_by_sample untouched -- byte-identical prompts.
        evidence_by_sample = apply_evidence_budget(evidence_by_sample, evidence_budget_bytes)
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
        # Sample-level PREFETCH + the run's request dispatcher (obs-pipeline
        # throughput fix, 2026-09-08). Resolved beside the batch decision and
        # for the same reason: an illegal combination must refuse before the
        # adapter below opens this attempt.
        prefetch_depth, obs_dispatcher = _obs_pipeline(
            values, str(values["policy"]), batch_size
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
        carrier_root_resolver = getattr(loader, "carrier_root", None)
        carrier_root = (
            carrier_root_resolver(lock, root)
            if callable(carrier_root_resolver)
            else asset_dir(lock, str(values["carrier_lock_key"]), root)
        )
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
            # DERIVED-MEDIA CONFINEMENT: the additional legal media roots THIS
            # composed dataset fragment declares, each vouched for by its own
            # hash-pinned D1 media supplement. Empty for every fragment that
            # declares none, which is every fragment that predates derived media.
            derived_media_roots=declared_derived_media_roots(values, Path(root)),
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
        # sink exactly as before. The prefetch pipeline is the second reader
        # of that same seam -- it runs prefetch_depth+1 samples at once, so it
        # needs the identical per-sample routing; at depth 0 this expression
        # is exactly what it has always been.
        adapter_sink = (
            sink if (batch_size == 1 and prefetch_depth == 0) else DispatchingSink(sink)
        )
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
        # Exhausted-slice skip, aggregated per RUN (Task 2, 2026-08-09,
        # continues the obs-loop E-001 retry finding): the SAME "sum
        # whatever the outcome already reports" pattern as
        # saturated_slice_total above -- SampleOutcome.skipped_slices is 0
        # for every non-slicing policy (FixedPolicy), so this aggregate is
        # exact and free of a policy-name branch.
        skipped_slice_total = 0
        skipped_sample_ids: list[str] = []
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
                # Acoustic exemplar bank (core.exemplars module docstring):
                # None when exemplar_bank_by_sample is empty (no
                # exemplar_manifest_id declared), else this sample's own
                # (possibly empty) resolved bank -- the SAME sample_id keys
                # `samples` was built from above.
                exemplar_bank=exemplar_bank_by_sample.get(sample.sample_id),
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
                    # The run's shared dispatch-slot pool, or None at
                    # obs_prefetch_depth 0 (every config before 2026-09-08).
                    # reproduction.obs_loop's slice-parallel pass reads it and
                    # falls back to its historical per-sample pool when absent.
                    "obs_dispatcher": obs_dispatcher,
                    **(
                        {
                            "speech_feature_query": speech_feature_query_by_sample[
                                sample.sample_id
                            ]
                        }
                        if sample.sample_id in speech_feature_query_by_sample
                        else {}
                    ),
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
        begin_request_window = getattr(sampler, "begin_request_window", None)
        end_request_window = getattr(sampler, "end_request_window", None)
        if callable(begin_request_window):
            begin_request_window()
        try:
            with outputs_handle as outputs:
                if batch_size == 1 and prefetch_depth > 0:
                    # PIPELINED sequential path (obs-pipeline throughput fix,
                    # 2026-09-08; the module comment above
                    # reproduction.obs_loop.ObsDispatcher carries the measured
                    # defect). Same one sample at a time in EVERY observable
                    # respect -- rows are written in split-id order, each
                    # sample's whole trace block is flushed into the real sink
                    # in split-id order, and a failure surfaces as the first
                    # failed sample in that same order. The only difference is
                    # that prefetch_depth samples of LOOKAHEAD are already
                    # running: sample N+1 decodes, cuts, encodes and registers
                    # its windows while sample N's are still being answered,
                    # and the run's shared ObsDispatcher lets N+1's first
                    # requests occupy the slots N's tail is releasing.
                    #
                    # Consequence stated plainly: a run that aborts on sample
                    # N has already sent some of sample N+1..N+depth's
                    # requests, so a failed attempt's durable spend is up to
                    # depth samples larger than the sequential path's. The
                    # budget is run-cumulative and sized for the whole roster,
                    # so this changes what a dead attempt costs, never what a
                    # complete one does. Cutting audio is NOT spend: the
                    # prefetch's decode/cut/encode/register phase never touches
                    # the adapter, and metering still happens per request, at
                    # the moment it is sent.
                    from concurrent.futures import ThreadPoolExecutor

                    def _pipeline_entry(index, sample):
                        """Build one sample's buffered context on the MAIN
                        thread (deterministic preamble bytes), ready to run."""

                        request_id_base = f"req-{index:04d}"
                        evidence = evidence_by_sample.get(sample.sample_id, [])
                        buffer = TraceBuffer(plan.run_id)
                        sample_evidence_bytes = _emit_sample_preamble(
                            buffer, request_id_base, sample, evidence,
                            exemplar_manifest, exemplar_bank_by_sample.get(sample.sample_id),
                        )
                        ctx = _sample_context(sample, evidence, request_id_base, buffer)
                        return (
                            sample, evidence, sample_evidence_bytes, buffer, ctx,
                            request_id_base,
                        )

                    def _pipeline_run(entry):
                        ctx = entry[4]
                        # The batch-policy contract (core.tracing): bind this
                        # worker to its own sample's buffer so the shared
                        # adapter's records land in the right block.
                        set_current_trace_buffer(ctx.sink)
                        try:
                            return policy.run_sample(ctx)
                        finally:
                            set_current_trace_buffer(None)

                    pending: list = []
                    next_index = 0
                    total_samples = len(ordered_samples)
                    with ThreadPoolExecutor(
                        max_workers=prefetch_depth + 1,
                        thread_name_prefix="saea-obs-pipeline",
                    ) as pipeline_pool:

                        def _pipeline_submit():
                            nonlocal next_index
                            if next_index >= total_samples:
                                return
                            entry = _pipeline_entry(
                                next_index + 1, ordered_samples[next_index]
                            )
                            next_index += 1
                            pending.append((entry, pipeline_pool.submit(_pipeline_run, entry)))

                        for _ in range(prefetch_depth + 1):
                            _pipeline_submit()
                        while pending:
                            entry, future = pending.pop(0)
                            (
                                sample, evidence, sample_evidence_bytes, buffer, _ctx,
                                request_id_base,
                            ) = entry
                            # Blocks in SPLIT-ID order: the first failure in
                            # split order wins, exactly as the batch path
                            # promises, and a prefetched sample's exception is
                            # raised on ITS OWN sample, never swallowed and
                            # never attributed to a neighbour.
                            outcome = future.result()
                            # Flushed only now, so an aborted run's trace
                            # carries no half-finished lookahead sample.
                            buffer.flush_into(sink)
                            supplied_evidence_bytes += sample_evidence_bytes
                            if evidence and outcome.admitted:
                                admitted_evidence_bytes += sample_evidence_bytes
                            if outcome.saturated_slices:
                                saturated_slice_total += outcome.saturated_slices
                                saturated_sample_ids.append(outcome.sample_id)
                            if outcome.skipped_slices:
                                skipped_slice_total += outcome.skipped_slices
                                skipped_sample_ids.append(outcome.sample_id)
                            _write_row(outputs, request_id_base, sample, outcome)
                            _pipeline_submit()
                elif batch_size == 1:
                    for index, sample in enumerate(ordered_samples, start=1):
                        request_id_base = f"req-{index:04d}"
                        evidence = evidence_by_sample.get(sample.sample_id, [])
                        sample_evidence_bytes = _emit_sample_preamble(
                            sink, request_id_base, sample, evidence,
                            exemplar_manifest, exemplar_bank_by_sample.get(sample.sample_id),
                        )
                        supplied_evidence_bytes += sample_evidence_bytes
                        ctx = _sample_context(sample, evidence, request_id_base, sink)
                        outcome = policy.run_sample(ctx)
                        if evidence and outcome.admitted:
                            admitted_evidence_bytes += sample_evidence_bytes
                        if outcome.saturated_slices:
                            saturated_slice_total += outcome.saturated_slices
                            saturated_sample_ids.append(outcome.sample_id)
                        if outcome.skipped_slices:
                            skipped_slice_total += outcome.skipped_slices
                            skipped_sample_ids.append(outcome.sample_id)
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
                            buffer, request_id_base, sample, evidence,
                            exemplar_manifest, exemplar_bank_by_sample.get(sample.sample_id),
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
                        if outcome.skipped_slices:
                            skipped_slice_total += outcome.skipped_slices
                            skipped_sample_ids.append(outcome.sample_id)
                        _write_row(outputs, request_id_base, sample, outcome)
        finally:
            if callable(end_request_window):
                end_request_window()
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
        skipped_slice_count=skipped_slice_total,
        skipped_sample_ids=sorted(skipped_sample_ids),
    )
    return RunResult(
        run_id=plan.run_id,
        arm=arm,
        outputs_path=outputs_path,
        trace_manifest_hash=manifest_hash,
        cost=cost,
    )
