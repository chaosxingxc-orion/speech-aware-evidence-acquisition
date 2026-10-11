"""Config-bound Earnings-22 adapter for the shared flight factory: a THIN derivation.

Study ``CLAUDE.md`` "one base, thin derivations" and the consumption-module design
(``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md`` section 2b.2:
"Earnings-22 has a carrier descriptor and loader support but no registered runtime
TaskAdapter ... that registration is a transfer precondition"). Everything is the
Earnings-21 runtime adapter's: the same execution-route validation (direct or
native-role programs over explicit, source-bound execution units), the same serving
geometry, instruction and whole-manifest scoring rules. Only the carrier and its
whole split differ: ``earnings22-original`` and ``dev`` (the Earnings-22 subset10
calls, ``data.splits.dev_split``), loaded by the shared ``Earnings21Adapter``
loader. Scoring reuses Earnings-21's registered ``asr-wer-whisper`` (the carrier's
``TaskLayout.official_scorer_id``); Earnings-22 has no ``wer_tags`` entity layer and
no ConEC context layer, so the entity scorers and ConEC supply do not apply.

Construction subsets of the dev split use Earnings-21's ``e21_runtime_subset`` form
unchanged (the shared base now takes its parent split from ``DEFAULT_SPLIT``): the
dataset fragment names a committed probe-sample receipt whose ids must lie inside the
frozen dev split (2026-10-11, the HELD four-row form smoke of the all-off cell; the
only registered subset is ``e22-native-window-four-row-v1``). Earnings-22 has NO
measured own null: no cell on it may claim a benefit until an in-chain A/A has sealed
(design 2b.3). No flight is registered by this file; it only lets the shared factory
resolve the carrier.
"""

from __future__ import annotations

from ...core.base import CoreError
from .earnings_runtime import Earnings21RuntimeAdapter

CARRIER_LOCK_KEY = "earnings22-original"


class Earnings22RuntimeAdapter(Earnings21RuntimeAdapter):
    """Earnings-21's runtime adapter on the Earnings-22 carrier and its ``dev`` split."""

    CARRIER_LOCK_KEY = CARRIER_LOCK_KEY
    DEFAULT_SPLIT = "dev"


def build_runtime_adapter(values, lock, data_root, repo_root, *, dataset_fragment):
    """The shared factory's carrier seam; no model or preprocessing contact."""
    return Earnings22RuntimeAdapter(
        values, lock, data_root, repo_root, dataset_fragment=dataset_fragment
    )


def register_runtime_adapter():
    """Register once in the common task-adapter registry; never replace an owner."""
    from ...core.base import TASK_ADAPTERS

    if CARRIER_LOCK_KEY in TASK_ADAPTERS.names():
        if TASK_ADAPTERS.resolve(CARRIER_LOCK_KEY) is not build_runtime_adapter:
            raise CoreError(f"{CARRIER_LOCK_KEY} runtime adapter is already registered differently")
        return
    TASK_ADAPTERS.register(CARRIER_LOCK_KEY, build_runtime_adapter)
