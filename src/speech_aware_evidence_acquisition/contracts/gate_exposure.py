"""``FrozenCoreGate`` mixin: umbrella-lock carrier scope + exposure-ledger
pre-registration cross-check.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change).
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Mapping

from .errors import GateClosed
from .ledger import _CARRIER_CELL_TOKEN_SPLIT, _EXPOSURE_CARRIER_COLUMN, _EXPOSURE_RUN_COLUMN, _parse_ledger_tables
from .plan import ExecutionPlan
from .receipts import general_audio_deny_lock_keys

# The umbrella lock's speech-aware-* profiles (docs/datasets.lock.json `profiles`,
# 2026-08-04 semantic migration) that may legitimately back a plan carrier: core
# evaluation carriers, secondary public carriers, entity/rare-word diagnostics and
# small optional public assets. `speech-aware-annotations` is deliberately excluded:
# it holds annotation-only entries with no speech audio of their own, so it can
# never back a model touch. `frozen-baseline`, `local-candidates`,
# `retained-cross-domain` and `deferred` are non-speech-aware profiles and are
# never allowed here.
ALLOWED_CARRIER_PROFILES = frozenset(
    {
        "speech-aware-core",
        "speech-aware-secondary",
        "speech-aware-diagnostics",
        "speech-aware-small-public",
    }
)


class _ExposureAndCarrierMixin:
    """Carrier-scope resolution and exposure-ledger pre-registration cross-check."""

    def _lock_dataset_entries(
        self, lock: Mapping[str, object] | None = None
    ) -> dict[str, Mapping[str, object]]:
        """Every ``kind: dataset`` entry in the umbrella lock, keyed by name.

        Real speech-aware carriers live in ``asset_catalog`` alongside the
        frozen-baseline ``datasets`` list, local-candidate assets and the
        general-audio assets explicitly excluded from this study. Model entries
        live in a disjoint ``models`` list and never appear here — a plan cannot
        claim a model lock key as its speech carrier."""

        if lock is None:
            lock, _ = self._load_lock_with_hash()
        entries: dict[str, Mapping[str, object]] = {}
        for list_key in ("datasets", "asset_catalog"):
            value = lock.get(list_key)
            if not isinstance(value, list):
                continue
            for item in value:
                if (
                    isinstance(item, Mapping)
                    and item.get("kind") == "dataset"
                    and isinstance(item.get("name"), str)
                ):
                    entries[item["name"]] = item
        if not entries:
            raise GateClosed("datasets lock yields no named dataset entries")
        return entries

    def _resolve_carrier_dataset_entry(
        self, carrier_lock_key: str, lock: Mapping[str, object] | None = None
    ) -> Mapping[str, object]:
        """Resolve and scope-check a plan's carrier against the umbrella lock (I2).

        A carrier must: (a) exist as a ``kind: dataset`` entry in the umbrella lock
        — model entries and unknown keys are refused; (b) not be one of the
        general-audio assets this study explicitly excludes; and (c) carry a
        non-empty ``profiles`` list intersecting this study's speech-aware scope.
        A dataset entry with no ``profiles`` field fails closed rather than being
        assumed in scope: naming a key in the lock never by itself proves it is a
        speech-domain carrier of this study."""

        entry = self._lock_dataset_entries(lock).get(carrier_lock_key)
        if entry is None:
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} is not a dataset entry in "
                "the umbrella datasets lock (model entries and unknown keys are "
                "never a valid speech carrier); model touch refused"
            )
        if carrier_lock_key in general_audio_deny_lock_keys(self.source_root):
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} is a general-audio asset "
                "explicitly excluded from the speech-aware-evidence-acquisition "
                "study, whose scope is human speech and its linguistic content "
                "only (ASR, entities, contextual biasing, spoken QA, meeting "
                "speech); model touch refused"
            )
        profiles = entry.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} has no profiles field in "
                "the umbrella datasets lock; scope cannot be proven so the touch "
                "is refused (fail-closed)"
            )
        if not (set(profiles) & ALLOWED_CARRIER_PROFILES):
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} profiles {profiles!r} do "
                "not intersect this study's speech-only scope "
                f"{sorted(ALLOWED_CARRIER_PROFILES)}; model touch refused"
            )
        return entry

    def _require_exposure_preregistration(
        self, plan: "ExecutionPlan", lock: Mapping[str, object] | None = None
    ) -> None:
        """The pre-registered row is cross-checked field by field against the plan.

        A run id string alone proves nothing: the row must have been written with
        the same profile, split role, split identity hash and budgets the plan now
        claims, and must still read ``consumed = no``. EVERY markdown table in the
        ledger whose header carries the contract's run-id column contributes rows
        (I2) -- a second table, or a stray prose line between two data rows of one
        table, can never make a registered row invisible to the duplicate/consumed/
        budget checks below."""

        try:
            text = Path(self.exposure_ledger).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise GateClosed(
                f"exposure ledger missing or unreadable ({self.exposure_ledger}): {error}"
            ) from error
        rows = _parse_ledger_tables(text)

        def cell(row: Mapping[str, str], column_name: str) -> str:
            if column_name not in row:
                raise GateClosed(
                    f"exposure row lacks column {column_name!r} (its governing table "
                    "header does not declare it)"
                )
            return row[column_name]

        matched = [row for row in rows if cell(row, _EXPOSURE_RUN_COLUMN) == plan.run_id]
        if not matched:
            raise GateClosed(
                f"model touch refused: run {plan.run_id!r} has no pre-registered exposure "
                f"row in {self.exposure_ledger} (rows are written before results are read)"
            )
        if len(matched) > 1:
            raise GateClosed(f"run {plan.run_id!r} is pre-registered more than once")
        row = matched[0]
        for column_name, expected in (
            ("execution profile", plan.execution_profile),
            ("split role", plan.split_role),
            ("split identity hash", plan.split_identity_hash),
        ):
            actual = cell(row, column_name)
            if actual != expected:
                raise GateClosed(
                    f"exposure row disagrees with the execution plan on {column_name!r}: "
                    f"row {actual!r} vs plan {expected!r}; model touch refused"
                )
        carrier_cell = cell(row, _EXPOSURE_CARRIER_COLUMN)
        known_carrier_keys = set(self._lock_dataset_entries(lock))
        carrier_tokens = [
            token for token in _CARRIER_CELL_TOKEN_SPLIT.split(carrier_cell) if token
        ]
        named_carriers = [token for token in carrier_tokens if token in known_carrier_keys]
        if len(named_carriers) != 1:
            raise GateClosed(
                f"exposure row column {_EXPOSURE_CARRIER_COLUMN!r} ({carrier_cell!r}) must "
                "name exactly one known carrier lock key unambiguously; found "
                f"{named_carriers or 'none'}; model touch refused (I2: ambiguous carrier "
                "metadata fails closed)"
            )
        if named_carriers[0] != plan.carrier_lock_key:
            raise GateClosed(
                f"exposure row column {_EXPOSURE_CARRIER_COLUMN!r} names carrier "
                f"{named_carriers[0]!r}, not the execution plan's carrier "
                f"{plan.carrier_lock_key!r}; model touch refused (I2: carrier scope and "
                "exposure carrier must bind)"
            )
        if cell(row, "consumed").lower() != "no":
            raise GateClosed(
                f"exposure row for {plan.run_id!r} is already consumed; a consumed run "
                "cannot be re-executed"
            )
        for column_name, planned, parse in (
            ("calls", plan.planned_model_calls, int),
            ("speech audio seconds", plan.planned_speech_audio_seconds, int),
            ("gpu hours", plan.planned_gpu_hours, float),
        ):
            raw = cell(row, column_name)
            try:
                registered = parse(raw)
            except ValueError as error:
                raise GateClosed(
                    f"exposure row column {column_name!r} must be a number, got {raw!r}"
                ) from error
            if not math.isfinite(registered) or registered < 0:
                raise GateClosed(
                    f"exposure row column {column_name!r} must be a finite non-negative "
                    f"number, got {raw!r}; NaN or negative cells would disable the "
                    "budget arithmetic"
                )
            if registered < planned:
                raise GateClosed(
                    f"execution plan claims {planned} {column_name} but only {registered} "
                    "were pre-registered; model touch refused"
                )
        # Owner amendment 2026-08-06 (SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS):
        # the slice-wide summation that used to run here -- summing every
        # registered row plus AttemptStore.all_actual_usage()'s durable actuals and
        # refusing a campaign total over the frozen first-slice caps -- is retired.
        # What remains, checked above, is per-row: the matched row's registered
        # calls/speech-audio-seconds/gpu-hours must each be >= this plan's own
        # declared values, and the row itself must be unconsumed. See
        # docs/engineering.md and the amendment record for the full rationale.
