"""The dispatcher slot-fill key (owner decision 159, 2026-09-27).

What it is for
--------------
``docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md`` measured
that 27.3 % of ROLL-2's slot capacity (8,997 of 32,909 slot-seconds) sat empty
while the client prepared the next contact, 2.67 s before every first Solver
contact alone, and 1,055 s with every slot empty at once. The model-free
decomposition ``docs/results/2026-09-27-dispatcher-slot-fill.md`` locates the
mass: the first Solver contact's role input runs the train-exemplars recall --
a pure-Python cosine over every exemplar key vector, a function of the row's
own sealed speech query alone -- synchronously on the ONE event loop every row
of the flight shares, so while one row recalls, no other row can route its
next contact; and every full garbage collection over the flight's large static
heap (the loaded key vectors) freezes every thread at once.

What it changes
---------------
Scheduling only. Three independent switches, each of which leaves every byte
a node sees exactly as it is:

``recall_prefetch``
    When a row is admitted, its Perception-independent recall (the one
    ``rails.kb_policy.multidim_recall`` call its first Solver visit will make,
    on the same snapshot, the same sealed query record, the same key vectors
    and the same ``k``) is submitted to one background worker. The Solver
    visit's supply step consumes that result instead of recomputing it; every
    later step -- the agreement merge, the rank, the fusion, the candidate-bound
    slot-contract selection that DOES depend on Perception -- runs exactly as
    before. Same function, same inputs, same process: the same floats in the
    same insertion order. A revisit recomputes live, as before.
``role_input_offload``
    The episode graph's role-input builder (``settle`` -> supply -> material ->
    rendered instruction) runs on one dedicated worker thread instead of the
    shared event loop. The worker is single-threaded, so role inputs remain
    mutually exclusive across rows exactly as they are today; only the other
    rows' routing and dispatch stop waiting behind them.
``gc_freeze``
    One collection and ``gc.freeze()`` after the flight's static state is
    loaded and before the first episode, ``gc.unfreeze()`` after the last:
    the loaded snapshot and key vectors leave the collector's generations, so
    a full collection no longer traverses them while every thread waits.

Absent -- every committed configuration -- none of this code runs and the
dispatch is byte-for-byte what it was. The key is part of the composed
configuration, so it enters the config hash and a cell's identity only where
it is declared.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .errors import RailsError

DISPATCH_SLOT_FILL_KEY = "dispatch"
DISPATCH_SLOT_FILL_SCHEMA = "saea-dispatch-slot-fill-v1"
_SWITCHES = ("recall_prefetch", "role_input_offload", "gc_freeze")


class DispatchSlotFillError(RailsError):
    """A malformed ``dispatch`` block; refused before any contact."""


@dataclass(frozen=True)
class DispatchSlotFill:
    recall_prefetch: bool = False
    role_input_offload: bool = False
    gc_freeze: bool = False

    def as_json(self) -> dict[str, object]:
        return {
            "schema": DISPATCH_SLOT_FILL_SCHEMA,
            **{name: getattr(self, name) for name in _SWITCHES},
        }


def parse_dispatch_slot_fill(values: Mapping[str, object]) -> DispatchSlotFill | None:
    """The composed ``dispatch`` block, or ``None`` when it is absent.

    Strict: exact keys, boolean switches, at least one switch on. A block that
    arms nothing is refused rather than read as "off", because an armed key
    changes the config hash and a cell that declares it must mean it.
    """

    raw = values.get(DISPATCH_SLOT_FILL_KEY)
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise DispatchSlotFillError("dispatch must be a mapping")
    allowed = {"schema", *_SWITCHES}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise DispatchSlotFillError(f"dispatch declares unknown key(s) {unknown}")
    if raw.get("schema") != DISPATCH_SLOT_FILL_SCHEMA:
        raise DispatchSlotFillError(
            f"dispatch.schema must be {DISPATCH_SLOT_FILL_SCHEMA!r}"
        )
    switches = {}
    for name in _SWITCHES:
        value = raw.get(name, False)
        if not isinstance(value, bool):
            raise DispatchSlotFillError(f"dispatch.{name} must be a boolean")
        switches[name] = value
    if not any(switches.values()):
        raise DispatchSlotFillError("dispatch declares no switch; omit the key instead")
    return DispatchSlotFill(**switches)


class NativePrefixSlotsError(RailsError):
    """Refuse an incomplete or unsafe native role affinity envelope."""


@dataclass(frozen=True)
class NativePrefixSlots:
    """Immutable role-to-slot ownership; this does not assert cache residency."""

    role_slots: tuple[tuple[str, int], ...]

    def slot_bindings(self) -> dict[str, int]:
        return dict(self.role_slots)

    def as_json(self) -> dict[str, object]:
        return {"schema": "saea-native-prefix-slots-v1", "role_slots": self.slot_bindings()}

    def validate(self, config, *, slot_count: int) -> None:
        if config is None:
            raise NativePrefixSlotsError("prefix slots require a native role episode")
        if type(slot_count) is not int or slot_count <= 0:
            raise NativePrefixSlotsError("prefix slots require a positive slot count")
        if any(slot >= slot_count for _, slot in self.role_slots):
            raise NativePrefixSlotsError("prefix slot is outside the serving geometry")
        required = {role.phase_id for role in config.roles if role.max_iterations > 0}
        if config.relisten_json is not None:
            required.add("relisten")
        if set(self.slot_bindings()) != required:
            raise NativePrefixSlotsError("prefix slots must cover exactly all native roles")
        if config.context_policy_json is not None:
            from .node_context_binding import node_context_cleaning_boundaries

            # Cleaning runs during input construction, outside run_contact. A
            # trajectory-owned slot used to protect it; role ownership cannot.
            if node_context_cleaning_boundaries(config.context_policy_json):
                raise NativePrefixSlotsError("prefix slots do not admit unscheduled context cleaning")


def parse_native_prefix_slots(values: Mapping[str, object]) -> NativePrefixSlots | None:
    """Parse a separately versioned, opt-in scheduling factor without defaults."""
    if "native_prefix_slots" not in values:
        return None
    raw = values["native_prefix_slots"]
    if not isinstance(raw, Mapping) or set(raw) != {"schema", "role_slots"}:
        raise NativePrefixSlotsError("native_prefix_slots requires exactly schema and role_slots")
    if raw["schema"] != "saea-native-prefix-slots-v1":
        raise NativePrefixSlotsError("unknown native_prefix_slots schema")
    roles = raw["role_slots"]
    if not isinstance(roles, Mapping) or not roles:
        raise NativePrefixSlotsError("role_slots must be a nonempty mapping")
    if any(not isinstance(role, str) or not role.strip()
           or type(slot) is not int or slot < 0 for role, slot in roles.items()):
        raise NativePrefixSlotsError("role_slots requires role names and nonnegative integer slots")
    if len(set(roles.values())) != len(roles):
        raise NativePrefixSlotsError("each role requires a distinct prefix slot")
    return NativePrefixSlots(tuple(sorted(roles.items())))


class NativeNodeBatchError(RailsError):
    """Refuse an incomplete or conflicting node-batch execution envelope."""


@dataclass(frozen=True)
class NativeNodeBatch:
    """Bounded intermediate sample state, independent of permanent KV slots."""

    node_order: tuple[str, ...]
    batch_size: int

    def as_json(self):
        return {"schema": "saea-native-node-batch-v1", "node_order": list(self.node_order),
                "batch_size": self.batch_size}

    def validate(self, config, *, queue_depth):
        if config is None:
            raise NativeNodeBatchError("node batch requires a native role episode")
        if type(queue_depth) is not int or not 1 <= self.batch_size <= queue_depth:
            raise NativeNodeBatchError("node batch size exceeds the admitted workflow queue")
        required = {r.phase_id for r in config.roles if r.max_iterations > 0}
        if config.relisten_json is not None:
            required.add("relisten")
        if set(self.node_order) != required:
            raise NativeNodeBatchError("node batch order must cover exactly all reachable model roles")
        if config.context_policy_json is not None:
            from .node_context_binding import node_context_cleaning_boundaries
            if node_context_cleaning_boundaries(config.context_policy_json):
                raise NativeNodeBatchError("node batch refuses unscheduled model context cleaning")


def parse_native_node_batch(values: Mapping[str, object]) -> NativeNodeBatch | None:
    """Opt in explicitly; keep absent historical configurations unchanged."""
    if "native_node_batch" not in values:
        return None
    if "native_prefix_slots" in values:
        raise NativeNodeBatchError("node batch conflicts with permanent role slots")
    raw = values["native_node_batch"]
    if not isinstance(raw, Mapping) or set(raw) != {"schema", "node_order", "batch_size"}:
        raise NativeNodeBatchError("node batch needs exact schema, node_order and batch_size")
    if raw["schema"] != "saea-native-node-batch-v1":
        raise NativeNodeBatchError("unknown node batch schema")
    order, size = raw["node_order"], raw["batch_size"]
    if (not isinstance(order, list) or not order
            or any(not isinstance(n, str) or not n.strip() for n in order)
            or len(set(order)) != len(order)
            or type(size) is not int or size < 1):
        raise NativeNodeBatchError("node batch requires unique node names and positive integer size")
    return NativeNodeBatch(tuple(order), size)


class NativeNodePipelineError(RailsError):
    """Refuse an unbound panel or a hidden model call during CPU prefetch."""


@dataclass(frozen=True)
class NativeTraceSpool:
    """Bound disk-backed trace copies without claiming a full process memory cap."""

    max_record_bytes: int
    max_total_bytes: int

    def as_json(self):
        return {"schema": "saea-native-trace-spool-v1",
                "max_record_bytes": self.max_record_bytes, "max_total_bytes": self.max_total_bytes}


@dataclass(frozen=True)
class NativeNodePipeline:
    """Registered logical panel size is separate from model-slot concurrency."""

    node_order: tuple[str, ...]
    group_size: int
    prepare_workers: int
    max_jobs: int
    trace_spool: NativeTraceSpool | None = None

    def as_json(self):
        result = {"schema": "saea-native-node-pipeline-v1", "node_order": list(self.node_order),
                "group_size": self.group_size, "prepare_workers": self.prepare_workers,
                "max_jobs": self.max_jobs}
        if self.trace_spool is not None:
            result["trace_spool"] = self.trace_spool.as_json()
        return result

    def validate(self, config):
        if config is None:
            raise NativeNodePipelineError("node pipeline requires a native role episode")
        if set(self.node_order) != {r.phase_id for r in config.roles if r.max_iterations > 0}:
            raise NativeNodePipelineError("node pipeline order must cover its reachable roles")
        if config.relisten_json is not None:
            raise NativeNodePipelineError("node pipeline needs an explicit relisten preparation boundary")
        if config.context_policy_json is not None:
            from .node_context_binding import node_context_cleaning_boundaries
            if node_context_cleaning_boundaries(config.context_policy_json):
                raise NativeNodePipelineError("node pipeline refuses model context cleaning during CPU prefetch")


def parse_native_node_pipeline(values: Mapping[str, object]) -> NativeNodePipeline | None:
    """Keep the full-panel schedule an explicit, separately hashed opt-in."""
    if "native_node_pipeline" not in values:
        return None
    if any(key in values for key in ("native_prefix_slots", "native_node_batch")):
        raise NativeNodePipelineError("node pipeline conflicts with other node/slot schedulers")
    raw = values["native_node_pipeline"]
    if (not isinstance(raw, Mapping)
            or set(raw) - {"trace_spool"} != {"schema", "node_order", "group_size", "prepare_workers", "max_jobs"}
            or raw["schema"] != "saea-native-node-pipeline-v1"):
        raise NativeNodePipelineError("node pipeline needs its exact versioned configuration")
    order = raw["node_order"]
    if (not isinstance(order, list) or not order
            or any(not isinstance(n, str) or not n.strip() for n in order)
            or len(set(order)) != len(order)
            or any(type(raw[k]) is not int or raw[k] < 1
                   for k in ("group_size", "prepare_workers", "max_jobs"))
            or raw["prepare_workers"] > 8 or raw["group_size"] > raw["max_jobs"]):
        raise NativeNodePipelineError("node pipeline requires unique nodes and finite worker/job bounds")
    storage = None
    if "trace_spool" in raw:
        declared = raw["trace_spool"]
        if (not isinstance(declared, Mapping)
                or set(declared) != {"schema", "max_record_bytes", "max_total_bytes"}
                or declared["schema"] != "saea-native-trace-spool-v1"
                or any(type(declared[k]) is not int or declared[k] < 1
                       for k in ("max_record_bytes", "max_total_bytes"))
                or declared["max_record_bytes"] > declared["max_total_bytes"]):
            raise NativeNodePipelineError("trace spool needs exact positive record and total byte bounds")
        storage = NativeTraceSpool(declared["max_record_bytes"], declared["max_total_bytes"])
    return NativeNodePipeline(tuple(order), raw["group_size"], raw["prepare_workers"], raw["max_jobs"], storage)


__all__ = [
    "NativeNodePipeline", "NativeNodePipelineError", "parse_native_node_pipeline",
    "NativeNodeBatch", "NativeNodeBatchError", "parse_native_node_batch",
    "DISPATCH_SLOT_FILL_KEY",
    "DISPATCH_SLOT_FILL_SCHEMA",
    "DispatchSlotFill",
    "DispatchSlotFillError",
    "parse_dispatch_slot_fill",
    "NativePrefixSlots",
    "NativePrefixSlotsError",
    "parse_native_prefix_slots",
]
