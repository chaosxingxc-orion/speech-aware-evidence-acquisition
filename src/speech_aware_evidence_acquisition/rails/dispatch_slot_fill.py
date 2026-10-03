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


__all__ = [
    "DISPATCH_SLOT_FILL_KEY",
    "DISPATCH_SLOT_FILL_SCHEMA",
    "DispatchSlotFill",
    "DispatchSlotFillError",
    "parse_dispatch_slot_fill",
    "NativePrefixSlots",
    "NativePrefixSlotsError",
    "parse_native_prefix_slots",
]
