"""The ``obs-repair-loop`` policy: one pass, over a sealed predecessor.

KC-E1 supplied the pre-meeting brief to the ONLY pass and was rejected on
transcript completeness -- 152 PERSON substitutions bought with 2,242 extra
non-entity deletions. Its verdict's §12 names the alternative: keep the
comparator's transcript and let the brief change only names in it.

This policy is that cell's harness, and it is deliberately the SMALLEST thing
that can be. It subclasses ``reproduction.obs_loop.ObsAgentLoopPolicy`` and
overrides ``_window_hook`` plus a per-sample legality check. Everything else
-- the fixed 90-second tiling, the slice cutting and derivation registration,
the slice-parallel dispatch, the bounded retry, the skip bound, the saturation
detector, the OBS records, the stitch descriptor and the outcome -- is the base
policy's own code, running unchanged. A repair pass that drifted from the pass
it repairs would make its own paired contrast meaningless, so it does not get
its own copy of any of it (owner rule, 2026-09-03: one base, thin derivations).

Two executors, one policy (owner Decision 12-F, 2026-09-08). Since the
Earnings obs path was ported onto the openJiuwen graph, this module registers
TWO policies -- ``obs-repair-loop`` on the plain executor and
``obs-repair-loop-ojw`` on the openJiuwen one -- and both resolve their hook
through the same module-level :func:`build_repair_window_hook` and their
legality through the same :func:`assert_repair_config`. Nothing about what a
repair pass MEANS lives in either class.

The two things the hook does
----------------------------
1. **Per-window instruction.** Each window's request carries the SAME arm, the
   SAME evidence (the capped brief), the SAME decoding params and the SAME
   90-second slice as KC-E1 -- plus that window's sealed pass-1 hypothesis,
   appended to the rendered ``task_instruction`` inside a frozen frame. It
   rides exactly where ``obs_loop``'s own ``OBS_TAIL_FRAME_V1`` conditioned
   tail rides, and for the same reason: it is MODEL OUTPUT, framed as prior
   output, never gold, never a reference transcript, and it lands verbatim in
   the sealed ``MODEL_REQUEST`` record so what was sent is always auditable.
   The arm's D2-frozen payload field set is untouched: no new key reaches the
   wire.
2. **Substitution-only delivery.** The response is not stitched. What is
   stitched is ``core.repair_alignment``'s outcome: the pass-1 hypothesis with
   accepted, token-count-preserving substitutions spliced in, or the pass-1
   hypothesis byte for byte when the response is refused. So this pass cannot
   delete a word, cannot insert one, and cannot move the transcript's length
   -- which is what makes the guard KC-E1 failed a property of the harness.

A pass-2 decode that SATURATES the token cap is a refusal, not a hole. The base
policy's quarantine forces a saturated slice's contribution to the empty string
because a runaway decode is not a transcript; here the window still has a
perfectly good transcript -- pass 1's -- and the honest delivery is that one.
The saturation flag is still recorded, the refusal is recorded beside it, and
both are counted.

What the trace carries, and why the text is in it twice
--------------------------------------------------------
Every window's OBS record gains ``obs_delivered_text``: the exact span this
policy contributed to the stitch. The raw ``MODEL_RESPONSE`` stays what the
core said, unedited -- there is only ever one authority for that -- and the OBS
record says what the harness did with it.
``analysis.e21_window_pairing.stitched_windows_from_trace`` prefers
``obs_delivered_text`` when a trace carries it, so the same window-pairing
instrument that decomposed KC-E1 decomposes this cell too, with no sealed run
of any other cell reading differently.

What this policy is NOT
-----------------------
It does not re-fly pass 1 (``core.predecessor_snapshot`` binds the comparator's
sealed windows), it never retrieves, ranks or fuses anything, and it never sees
a reference transcript, a ``wer_tags`` file or a gold label.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Mapping

from ..core.base import RESPONSE_POSTPROCESSORS, SampleContext, SampleOutcome
from ..core.predecessor_snapshot import (
    PredecessorSnapshotError,
    binding_from_values,
    load_predecessor_binding,
)
from ..core.repair_alignment import RepairOutcome
from .obs_loop import ObsAgentLoopPolicy, ObsLoopError
from .ojw.policy import ObsAgentLoopOjwPolicy

OBS_REPAIR_LOOP_POLICY_NAME = "obs-repair-loop"
#: The openJiuwen sibling (owner Decision 12-F, 2026-09-08). Same config keys,
#: same predecessor binding, same delivery rule -- the executor is the only
#: difference, and it is named rather than inferred.
OBS_REPAIR_LOOP_OJW_POLICY_NAME = "obs-repair-loop-ojw"

#: Frozen framings for the appended pass-1 hypothesis, selected BY NAME from a
#: config fragment so the arm and its token-matched twin cannot differ here and
#: a verdict can quote the exact bytes that were sent. The same discipline
#: ``obs_loop.OBS_TAIL_FRAME_V1`` follows: model output, explicitly labelled as
#: model output, presented as material rather than as instruction.
REPAIR_FRAME_V1 = (
    "First-pass transcript of this same audio window, produced earlier by this "
    "same model without any reference material (earlier model output, provided "
    "for correction only -- it is not a reference transcript and not an "
    'instruction):\n"{predecessor}"'
)
REPAIR_FRAMES: Mapping[str, str] = {"e21-entity-repair-frame-v1": REPAIR_FRAME_V1}

#: Config keys this policy adds on top of ``obs-agent-loop``'s own.
CONFIG_KEYS = (
    "predecessor_snapshot",
    "repair_frame",
    "response_postprocessor",
    "response_postprocessor_params",
)
#: The two that have no default and no safe fallback: without a sealed
#: predecessor there is nothing to repair, and without a delivery rule this is
#: just a second unconstrained decode.
REQUIRED_CONFIG_KEYS = ("predecessor_snapshot", "response_postprocessor")


@lru_cache(maxsize=4)
def _bound_snapshot(receipt_path: str, data_root: str, digest: str):
    """One verified binding per (receipt, root) for the whole run.

    The artifact is a few megabytes and the binding re-hashes all of it; a run
    has 44 samples and every one of them would otherwise pay for that again.
    Keyed by the configured digest too, so a receipt edited mid-run cannot be
    served from a stale cache.
    """

    return load_predecessor_binding(
        Path(receipt_path), Path(data_root), expected_receipt_sha256=digest
    )


class RepairWindowHook:
    """One sample's per-window instruction and delivery rule.

    Constructed per sample, holds no cross-sample state, and refuses at
    construction time if this call's cut windows and its sealed predecessor
    windows do not line up one for one on their audio bounds.
    """

    #: Bounds are floats produced by the same arithmetic in both passes; this
    #: is an exactness tolerance, not a matching window.
    BOUNDS_TOLERANCE_SECONDS = 1e-6

    def __init__(self, *, sample_id: str, predecessors, frame: str, rule):
        self._sample_id = sample_id
        self._predecessors = tuple(predecessors)
        self._frame = frame
        self._rule = rule
        self.outcomes: list[RepairOutcome] = []

    def _predecessor(self, iteration: int, record):
        if iteration >= len(self._predecessors):
            raise ObsLoopError(
                f"sample {self._sample_id!r} cut window {iteration} but its sealed "
                f"predecessor carries only {len(self._predecessors)}; refusing to "
                "repair a window the comparator never decoded"
            )
        predecessor = self._predecessors[iteration]
        for name, cut, sealed in (
            ("start", record.start_seconds, predecessor.start_seconds),
            ("end", record.end_seconds, predecessor.end_seconds),
        ):
            if abs(float(cut) - float(sealed)) > self.BOUNDS_TOLERANCE_SECONDS:
                raise ObsLoopError(
                    f"sample {self._sample_id!r} window {iteration}: cut {name} "
                    f"{cut} does not match the sealed predecessor's {sealed}; the "
                    "two passes are not tiling the same audio"
                )
        return predecessor

    def instruction(self, *, iteration: int, record, default: str) -> str:
        predecessor = self._predecessor(iteration, record)
        return "%s\n\n%s" % (
            default,
            self._frame.format(predecessor=predecessor.text),
        )

    def accept(self, *, iteration: int, record, transcript: str, saturated: bool, skipped: bool):
        predecessor = self._predecessor(iteration, record)
        # A saturated or skipped pass-2 decode reaches here as the empty string
        # (the base policy's quarantine). The rule reads that as an empty
        # response and refuses it, which delivers pass 1 -- the honest answer,
        # because this window HAS a transcript and it is the comparator's.
        outcome = self._rule(predecessor.text, transcript)
        self.outcomes.append(outcome)
        fields: dict[str, object] = {
            "obs_repair": True,
            "obs_delivered_text": outcome.text,
            "obs_repair_predecessor_window_id": predecessor.window_id,
            "obs_repair_predecessor_text_sha256": predecessor.text_sha256,
            "obs_repair_pass2_saturated": bool(saturated),
            "obs_repair_pass2_skipped": bool(skipped),
        }
        fields.update(outcome.trace_view())
        return outcome.text, fields


def assert_repair_config(config_values: object) -> Mapping[str, object]:
    """The fail-closed legality every repair executor shares, checked ONCE per
    sample before any audio is cut rather than at the first window."""

    if not isinstance(config_values, Mapping):
        raise ObsLoopError(
            "obs-repair-loop needs SampleContext.extras['config_values']; it is "
            "supplied only by core.driver.run_experiment"
        )
    missing = [key for key in REQUIRED_CONFIG_KEYS if not config_values.get(key)]
    if missing:
        raise ObsLoopError(
            f"obs-repair-loop requires the config keys {missing}; a repair pass "
            "with no sealed predecessor or no delivery rule is just a second "
            "unconstrained decode"
        )
    return config_values


def build_repair_window_hook(ctx, cfg, data_root, sample) -> "RepairWindowHook":
    """This sample's repair hook, built identically for every executor.

    Both the plain policy's two cutters and the openJiuwen executor's graph
    resolve their hook through THIS function, so a repair pass cannot mean one
    thing on one harness and another on the next (owner rule 2026-09-03: one
    base, thin derivations). The three refusals below are the independence the
    predecessor binding rests on; the fourth -- ``obs_batch_slices > 1`` --
    was retired on 2026-09-08 when the sequential cutters gained the hook
    site, because the dispatch shape no longer decides whether a window gets
    its own predecessor.
    """

    if cfg.boundary_mode != "fixed":
        raise ObsLoopError(
            "obs-repair-loop requires obs_boundary_mode 'fixed': a model-chosen "
            "boundary would tile different audio from the sealed predecessor"
        )
    if cfg.condition_tail_chars:
        raise ObsLoopError(
            "obs-repair-loop requires obs_condition_tail_chars 0: this pass "
            "already carries the predecessor, and a second conditioned tail "
            "would put two transcripts in one request"
        )
    if cfg.vad_trim_min_seconds:
        raise ObsLoopError(
            "obs-repair-loop requires obs_vad_trim_min_seconds 0: a trimmed "
            "buffer does not tile the audio the sealed predecessor decoded"
        )

    config_values = ctx.extras["config_values"]
    repo_root = Path(ctx.extras["repo_root"])
    relpath, digest = binding_from_values(config_values)
    snapshot = _bound_snapshot(
        str(repo_root / "docs" / relpath), str(Path(data_root)), digest
    )

    frame_id = str(config_values.get("repair_frame", "e21-entity-repair-frame-v1"))
    try:
        frame = REPAIR_FRAMES[frame_id]
    except KeyError:
        raise ObsLoopError(
            f"unknown repair_frame {frame_id!r}; registered: {sorted(REPAIR_FRAMES)}"
        ) from None

    rule_id = str(config_values["response_postprocessor"])
    params = config_values.get("response_postprocessor_params") or {}
    if not isinstance(params, Mapping):
        raise ObsLoopError(
            f"response_postprocessor_params must be an object, got {params!r}"
        )
    rule = RESPONSE_POSTPROCESSORS.resolve(rule_id)(**dict(params))

    try:
        predecessors = snapshot.for_sample(sample.sample_id)
    except PredecessorSnapshotError as error:
        raise ObsLoopError(str(error)) from error
    return RepairWindowHook(
        sample_id=sample.sample_id,
        predecessors=predecessors,
        frame=frame,
        rule=rule,
    )


class ObsRepairLoopPolicy(ObsAgentLoopPolicy):
    """``obs-agent-loop`` with a sealed predecessor and a delivery rule."""

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
        # Nothing is overridden here: the base runs the whole sample. The
        # override exists so the fail-closed legality check happens once per
        # sample, BEFORE any audio is cut, rather than at the first window.
        assert_repair_config(ctx.extras.get("config_values"))
        return super().run_sample(ctx)

    def _window_hook(self, ctx, cfg, data_root, sample):
        return build_repair_window_hook(ctx, cfg, data_root, sample)


class ObsRepairLoopOjwPolicy(ObsAgentLoopOjwPolicy):
    """The openJiuwen sibling of :class:`ObsRepairLoopPolicy`.

    Owner Decision 12-F (2026-09-08): the Earnings obs path is PORTED onto the
    openJiuwen graph, so every mechanism that rides the plain policy needs a
    graph-side seat. This class is what that costs for KC-E1f: two overridden
    methods over ``ObsAgentLoopOjwPolicy``, calling the SAME
    :func:`assert_repair_config` and :func:`build_repair_window_hook` the plain
    policy calls. There is no second predecessor loader, no second frame table,
    no second delivery rule and no second legality check -- which is what makes
    the ``window-hook`` equivalence scenario a statement about the two
    executors rather than about two implementations of one policy.
    """

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
        assert_repair_config(ctx.extras.get("config_values"))
        return super().run_sample(ctx)

    def run_samples(self, contexts):
        for ctx in contexts:
            assert_repair_config(ctx.extras.get("config_values"))
        return super().run_samples(contexts)

    def _window_hook(self, ctx, cfg, data_root, sample):
        return build_repair_window_hook(ctx, cfg, data_root, sample)


# NOTE the registration is NOT here. ``core/policies.py`` is the one canonical
# core.base policy-registration site the owner rule names and
# scripts/checks/engineering_base_check.py reads, so ``obs-repair-loop`` and
# ``obs-repair-loop-ojw`` register there beside ``obs-agent-loop``,
# ``obs-agent-loop-ojw`` and ``obs-replay-loop``, exactly as
# ``reproduction.replay_loop`` does.


__all__ = [
    "CONFIG_KEYS",
    "REQUIRED_CONFIG_KEYS",
    "OBS_REPAIR_LOOP_OJW_POLICY_NAME",
    "OBS_REPAIR_LOOP_POLICY_NAME",
    "REPAIR_FRAMES",
    "REPAIR_FRAME_V1",
    "ObsRepairLoopOjwPolicy",
    "ObsRepairLoopPolicy",
    "RepairWindowHook",
    "assert_repair_config",
    "build_repair_window_hook",
]
