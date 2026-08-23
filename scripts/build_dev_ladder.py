#!/usr/bin/env python3
"""Build the DEV-ladder identity governance receipts (work item C2-receipts,
owner-approved 2026-08-23 knowledge-plane baseline program; authority
``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md`` sections
2.2 and 5).

Model-free / gold-free by construction: this script reads SLURP ``devel``
metadata through the production loader (``data.slurp.load_slurp_split``)
ONLY to resolve sample identity (utterance id, scenario, media path) --
scenario is read for STRATIFICATION AT BUILD TIME only, never written into a
receipt item. Every receipt under ``docs/receipts/probe-samples/`` carries
identity fields ONLY (``id``/``key``), exactly the shape
``reproduction.probe_split.load_verified_probe_split`` already consumes for
the SLURP GATE18/TRAIN90/... family -- no scenario, action, entity, or
transcript field is ever written per item.

Governance objects produced (owner ruling 2026-08-23 section 2.2):

* ``FINAL60`` -- 60 utterances, scenario-stratified as evenly as the devel
  split allows, EXCLUDING the historic frozen probe-60 receipt
  (``configs/probes/g0-binding/pslu-sample-devel-n60.json``, split identity
  hash ``fc9de436...``) whose ids are exposure-heavy. ``split_role`` is
  ``"reserved-final-unread"`` -- deliberately OUTSIDE
  ``reproduction.probe_split``'s Stage-2 role allowlist
  (``{"discovery", "dev"}``), so this receipt fails closed under
  ``load_verified_probe_split`` and cannot be resolved through the same
  split<->plan<->config seam a run would use. That refusal IS the "reserved,
  unread" contract for this governance object -- TEST remains untouched
  until a future registered amendment (ruling document section 4.4).
* ``DEV-100`` / ``DEV-500`` / ``DEV-1000`` -- nested scenario-stratified
  samples of devel MINUS the historic probe-60 MINUS FINAL60, seed
  ``20260823``, ``split_role: "dev"``. DEV-100 is an exact subset of DEV-500,
  which is an exact subset of DEV-1000 (construction below), so results
  across the ladder are monotone-comparable.

Two-hash discipline (matches ``reproduction.probe_split`` module docstring):
every receipt carries BOTH (1) the receipt-key hash
(``reproduction.sampling.split_identity_hash`` over the carrier-prefixed
``key`` strings -- the value ``load_verified_probe_split`` recomputes
fail-closed) and (2) the run-identity hash
(``data.splits.split_identity_hash`` over ``data.splits.prefixed(...)`` --
the E0 ledger slash convention an ``ExecutionPlan``/run manifest would
carry).

Allocation algorithm (``even_allocation``): a capacity-aware "as evenly as
the pool allows" apportionment -- iterative water-filling saturates any
stratum whose pool is smaller than the current fair share (taking that
stratum's ENTIRE remaining pool and redistributing the shortfall across the
rest), then the final round splits the remaining total across the
still-unsaturated strata with a floor share plus a one-each remainder,
tie-broken by ascending scenario name (every remaining stratum's fair share
is numerically identical at that point, so name order is the only
deterministic tie-break available -- this is the degenerate, exact case of
the "largest remainder method" the historic probe-60 receipt's own
selection_rule text names). This is DELIBERATELY an EQUAL per-scenario
target, not proportional to devel's natural scenario distribution (which is
what the historic, now-excluded probe-60 receipt drew) -- ruling document
section 2.2 calls for "scenario-stratified ... allocate as evenly as the
split allows" for FINAL60, and this script reuses the identical algorithm
for the DEV-1000 draw for consistency and auditability.

Nesting (DEV-100 (sub) DEV-500 (sub) DEV-1000): rather than three
independent seeded draws (which risks apportionment non-monotonicity, the
"Alabama paradox" family, across different totals), DEV-500's per-scenario
POOL is DEV-1000's own per-scenario selected utterance list (not the
original devel pool), and DEV-100's per-scenario pool is DEV-500's own
per-scenario selected list in turn. Each tier is therefore a genuine seeded
SUBSET (an index-sampled, sorted prefix in the same style as
``reproduction.sampling.stratified_sample``) of the previous tier, per
scenario, so the subset relation holds by construction, not by
coincidence.

Exclusion is applied at UTTERANCE granularity, not merely at the exact
recording (sample_id) the historic probe-60 receipt happened to read: SLURP
utterances carry between 1 and 60 recordings each in devel, and drawing a
DIFFERENT recording of an already-read utterance would still leak
information tied to that utterance's gold scenario/action/entities. Every
recording of every historic-probe-60 utterance is therefore excluded from
both FINAL60 and the DEV ladder pool -- a strictly more conservative
reading than "exclude exactly those sample ids" (deviation recorded in the
mission's final report).

One recording per selected utterance is resolved via
``random.Random(f"{seed}:{scenario}:{utterance_id}")``, mirroring the
historic probe-60 receipt's own selection_rule text convention
(``"...via random.Random(f'{seed}:{scenario}:{utterance_id}')"``) for
auditability, even though this is a new governance object with its own
independent draw.

Runs in WSL2 (data root on /mnt/e); writes
``docs/receipts/probe-samples/{FINAL60,DEV-100,DEV-500,DEV-1000}.json``.
Deterministic: item lists are sorted by id before writing and JSON is
rendered with fixed formatting, so re-running produces byte-identical
receipts.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    SlurpRecord,
    load_slurp_split,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash as run_identity_hash,
)
from speech_aware_evidence_acquisition.reproduction.sampling import (  # noqa: E402
    split_identity_hash as key_hash,
)

SEED = 20260823
GENERATED_DATE = "2026-08-23"
AUTHORITY = (
    "docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md sections 2.2 and 5"
)
CARRIER = "slurp"
OUT_DIR = REPO_ROOT / "docs" / "receipts" / "probe-samples"
PROBE60_RECEIPT_PATH = (
    REPO_ROOT / "configs" / "probes" / "g0-binding" / "pslu-sample-devel-n60.json"
)

SELECTION_RULE = (
    "Scenario-stratified over the 18 devel scenarios, as evenly as the eligible pool "
    "allows (capacity-aware water-filling apportionment: a stratum smaller than the "
    "current fair share is taken WHOLE and the shortfall is redistributed across the "
    "remaining strata; the final round splits any remainder one-each in ascending "
    "scenario-name order, since every remaining stratum's fair share is numerically "
    "identical at that point). Within a scenario, the utterances are drawn via "
    "random.Random(f'{seed}:{stage}:{scenario}').sample over the id-sorted eligible "
    "pool (mirrors reproduction.sampling.stratified_sample's own per-stratum seeding "
    "convention). One recording per selected utterance is resolved via "
    "random.Random(f'{seed}:{scenario}:{utterance_id}') over the utterance's "
    "id-sorted recordings, mirroring the historic probe-60 receipt's own "
    "selection_rule convention. DEV-500 and DEV-100 are drawn the SAME way but over "
    "DEV-1000's (respectively DEV-500's) own per-scenario selected utterance lists as "
    "the eligible pool, rather than the original devel pool, so each tier is an exact "
    "seeded SUBSET of the tier above it."
)


def even_allocation(total: int, capacities: Mapping[str, int]) -> dict[str, int]:
    """Apportion ``total`` across ``capacities``' keys as evenly as possible.

    Capacity-aware water-filling: any stratum whose capacity sits at or below
    the current fair share is saturated (assigned its FULL capacity) and
    removed from further consideration, with its capacity subtracted from the
    remaining total; this repeats until no stratum saturates in a round. The
    remaining (unsaturated) strata then split the remaining total evenly,
    floor share plus a one-each remainder assigned in ascending key order
    (every remaining stratum's fair share ties exactly at that point, so
    ascending-name order is the only deterministic tie-break available).
    """

    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ValueError("even_allocation: total must be a non-negative int")
    total_capacity = sum(capacities.values())
    if total > total_capacity:
        raise ValueError(
            f"even_allocation: total {total} exceeds total capacity {total_capacity}"
        )
    alloc: dict[str, int] = {key: 0 for key in capacities}
    remaining_keys = set(capacities)
    remaining_total = total
    while remaining_keys:
        quota = remaining_total / len(remaining_keys)
        saturated = sorted(key for key in remaining_keys if capacities[key] <= quota)
        if not saturated:
            break
        for key in saturated:
            alloc[key] = capacities[key]
            remaining_total -= capacities[key]
            remaining_keys.discard(key)
    if remaining_keys:
        count = len(remaining_keys)
        base = remaining_total // count
        remainder = remaining_total - base * count
        ordered = sorted(remaining_keys)
        for key in ordered:
            alloc[key] = base
        for key in ordered[:remainder]:
            alloc[key] += 1
    if sum(alloc.values()) != total:
        raise RuntimeError("even_allocation: internal invariant violated (total mismatch)")
    for key, cap in capacities.items():
        if alloc[key] > cap:
            raise RuntimeError("even_allocation: internal invariant violated (capacity exceeded)")
    return alloc


def pick_subset(
    pool_by_scenario: Mapping[str, list[str]], target_total: int, seed_tag: str
) -> dict[str, list[str]]:
    """Seeded, order-independent per-scenario subset draw (module docstring):
    ``target_total`` utterance ids apportioned via :func:`even_allocation`,
    then ``random.Random(f"{seed_tag}:{scenario}")`` picks the per-scenario
    count from the id-sorted pool -- mirrors
    ``reproduction.sampling.stratified_sample``'s own per-stratum RNG
    convention, generalized to a non-uniform per-stratum count."""

    capacities = {scenario: len(ids) for scenario, ids in pool_by_scenario.items()}
    counts = even_allocation(target_total, capacities)
    selected: dict[str, list[str]] = {}
    for scenario in sorted(pool_by_scenario):
        members = sorted(pool_by_scenario[scenario], key=int)
        count = counts[scenario]
        if count >= len(members):
            selected[scenario] = members
            continue
        rng = random.Random(f"{seed_tag}:{scenario}")
        indices = sorted(rng.sample(range(len(members)), count))
        selected[scenario] = [members[index] for index in indices]
    return selected


def load_devel_utterances(
    lock: Mapping[str, object], root: Path
) -> tuple[dict[str, str], dict[str, list[SlurpRecord]]]:
    """(utterance_id -> scenario, utterance_id -> id-sorted recordings) over
    the FULL devel split (2,033 distinct utterances; devel carries between 1
    and 60 recordings per utterance)."""

    records = load_slurp_split(lock, root, "devel")
    by_utterance: dict[str, list[SlurpRecord]] = {}
    for record in records:
        by_utterance.setdefault(record.utterance_id, []).append(record)
    scenario_of: dict[str, str] = {}
    for utterance_id, recordings in by_utterance.items():
        scenarios = {recording.scenario for recording in recordings}
        if len(scenarios) != 1:
            raise SystemExit(
                f"utterance {utterance_id!r} has inconsistent scenario across its own "
                f"recordings: {sorted(scenarios)}"
            )
        scenario_of[utterance_id] = recordings[0].scenario
        by_utterance[utterance_id] = sorted(recordings, key=lambda r: r.sample_id)
    return scenario_of, by_utterance


def resolve_recording(
    utterance_id: str,
    scenario: str,
    recordings: list[SlurpRecord],
) -> SlurpRecord:
    if len(recordings) == 1:
        return recordings[0]
    rng = random.Random(f"{SEED}:{scenario}:{utterance_id}")
    return recordings[rng.randrange(len(recordings))]


def load_probe60_excluded_utterances() -> tuple[set[str], str]:
    payload = json.loads(PROBE60_RECEIPT_PATH.read_text(encoding="utf-8"))
    items = payload["items"]
    utterance_ids = {item["utterance_id"] for item in items}
    if len(utterance_ids) != 60:
        raise SystemExit(
            f"historic probe-60 receipt resolved to {len(utterance_ids)} distinct "
            "utterance ids, expected exactly 60"
        )
    split_identity_hash = payload["split_identity_hash"]
    if not split_identity_hash.startswith("fc9de436"):
        raise SystemExit(
            "historic probe-60 receipt split_identity_hash no longer starts with "
            f"'fc9de436' (got {split_identity_hash!r}); refusing -- the exclusion set "
            "identity must be pinned"
        )
    return utterance_ids, split_identity_hash


def build_items(
    utterance_ids_by_scenario: Mapping[str, list[str]],
    by_utterance: Mapping[str, list[SlurpRecord]],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for scenario, utterance_ids in utterance_ids_by_scenario.items():
        for utterance_id in utterance_ids:
            recording = resolve_recording(utterance_id, scenario, by_utterance[utterance_id])
            items.append({"id": recording.sample_id, "key": f"{CARRIER}:{recording.sample_id}"})
    items.sort(key=lambda item: item["id"])
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        raise RuntimeError("build_items: duplicate resolved sample ids within one tier")
    return items


def scenario_allocation_counts(utterance_ids_by_scenario: Mapping[str, list[str]]) -> dict[str, int]:
    return {scenario: len(ids) for scenario, ids in sorted(utterance_ids_by_scenario.items())}


def write_receipt(name: str, payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"wrote {path.relative_to(REPO_ROOT)}  items={len(payload['items'])}  "
        f"split_identity_hash={payload['split_identity_hash'][:16]}...  "
        f"run_identity_hash={payload['run_identity_hash'][:16]}..."
    )


def receipt_payload(
    *,
    probe: str,
    split_role: str,
    n_items: int,
    pool_size: int,
    scenario_allocation: dict[str, int],
    items: list[dict[str, str]],
    exclusions: dict[str, object],
    nesting: dict[str, object] | None = None,
) -> dict[str, object]:
    keys = [item["key"] for item in items]
    ids = [item["id"] for item in items]
    payload: dict[str, object] = {
        "schema": "saea-dev-ladder-v1",
        "generator": "scripts/build_dev_ladder.py",
        "generated_date": GENERATED_DATE,
        "authority": AUTHORITY,
        "probe": probe,
        "carrier": CARRIER,
        "split": "devel",
        "split_role": split_role,
        "seed": SEED,
        "selection_rule": SELECTION_RULE,
        "pool_size": pool_size,
        "n_items": n_items,
        "scenario_allocation": scenario_allocation,
        "exclusions": exclusions,
        "items": items,
        "split_identity_hash": key_hash(keys),
        "split_identity_hash_basis": (
            "sha256 over the LF-joined, sorted, carrier-prefixed item 'key' strings "
            "(reproduction.sampling.split_identity_hash -- the receipt-integrity "
            "convention reproduction.probe_split.load_verified_probe_split recomputes "
            "fail-closed)"
        ),
        "run_identity_hash": run_identity_hash(prefixed(CARRIER, ids)),
        "run_identity_hash_basis": (
            "sha256 over the LF-joined, sorted carrier-prefixed sample ids "
            "(f'{carrier}/{id}') -- data.splits.split_identity_hash, the E0 ledger "
            "convention an ExecutionPlan/run manifest carries "
            "(reproduction.probe_split.VerifiedSplit.identity_hash)"
        ),
    }
    if nesting is not None:
        payload["nesting"] = nesting
    if len(items) != n_items:
        raise RuntimeError(f"receipt_payload: item count {len(items)} != n_items {n_items}")
    return payload


def main() -> int:
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    scenario_of, by_utterance = load_devel_utterances(lock, root)
    devel_scenarios = sorted(set(scenario_of.values()))
    if len(devel_scenarios) != 18:
        raise SystemExit(
            f"SLURP devel resolved {len(devel_scenarios)} distinct scenarios, expected 18: "
            f"{devel_scenarios}"
        )

    probe60_uids, probe60_hash = load_probe60_excluded_utterances()

    pool_all_by_scenario: dict[str, list[str]] = {scenario: [] for scenario in devel_scenarios}
    for utterance_id, scenario in scenario_of.items():
        if utterance_id in probe60_uids:
            continue
        pool_all_by_scenario[scenario].append(utterance_id)
    pool_all_size = sum(len(ids) for ids in pool_all_by_scenario.values())

    # ---- FINAL60 : reserved, unread ----------------------------------
    final60_by_scenario = pick_subset(pool_all_by_scenario, 60, f"{SEED}:final60")
    final60_uids = {uid for ids in final60_by_scenario.values() for uid in ids}
    final60_items = build_items(final60_by_scenario, by_utterance)
    final60_payload = receipt_payload(
        probe="dev-ladder-final60",
        split_role="reserved-final-unread",
        n_items=60,
        pool_size=pool_all_size,
        scenario_allocation=scenario_allocation_counts(final60_by_scenario),
        items=final60_items,
        exclusions={
            "historic_probe60": {
                "receipt": "configs/probes/g0-binding/pslu-sample-devel-n60.json",
                "split_identity_hash": probe60_hash,
                "excluded_utterance_count": len(probe60_uids),
                "note": (
                    "exclusion is at UTTERANCE granularity (every recording of every "
                    "historic-probe-60 utterance), not merely the exact recording that "
                    "receipt happened to read -- see module docstring"
                ),
            }
        },
    )
    write_receipt("FINAL60", final60_payload)

    # ---- DEV-1000 / DEV-500 / DEV-100 : dev, nested ------------------
    pool_dev_by_scenario = {
        scenario: [uid for uid in ids if uid not in final60_uids]
        for scenario, ids in pool_all_by_scenario.items()
    }
    pool_dev_size = sum(len(ids) for ids in pool_dev_by_scenario.values())

    dev1000_by_scenario = pick_subset(pool_dev_by_scenario, 1000, f"{SEED}:dev1000")
    dev1000_items = build_items(dev1000_by_scenario, by_utterance)
    dev_exclusions = {
        "historic_probe60": {
            "receipt": "configs/probes/g0-binding/pslu-sample-devel-n60.json",
            "split_identity_hash": probe60_hash,
            "excluded_utterance_count": len(probe60_uids),
            "note": (
                "exclusion is at UTTERANCE granularity (every recording of every "
                "historic-probe-60 utterance), not merely the exact recording that "
                "receipt happened to read -- see module docstring"
            ),
        },
        "final60": {
            "receipt": "docs/receipts/probe-samples/FINAL60.json",
            "split_identity_hash": final60_payload["split_identity_hash"],
            "excluded_utterance_count": 60,
        },
    }
    dev1000_payload = receipt_payload(
        probe="dev-ladder-dev1000",
        split_role="dev",
        n_items=1000,
        pool_size=pool_dev_size,
        scenario_allocation=scenario_allocation_counts(dev1000_by_scenario),
        items=dev1000_items,
        exclusions=dev_exclusions,
    )
    write_receipt("DEV-1000", dev1000_payload)

    dev500_pool_by_scenario = {
        scenario: sorted(ids, key=int) for scenario, ids in dev1000_by_scenario.items()
    }
    dev500_by_scenario = pick_subset(dev500_pool_by_scenario, 500, f"{SEED}:dev500")
    dev500_items = build_items(dev500_by_scenario, by_utterance)
    dev500_payload = receipt_payload(
        probe="dev-ladder-dev500",
        split_role="dev",
        n_items=500,
        pool_size=1000,
        scenario_allocation=scenario_allocation_counts(dev500_by_scenario),
        items=dev500_items,
        exclusions=dev_exclusions,
        nesting={
            "parent_tier": "DEV-1000",
            "parent_receipt": "docs/receipts/probe-samples/DEV-1000.json",
            "parent_split_identity_hash": dev1000_payload["split_identity_hash"],
            "is_exact_subset_of_parent": True,
        },
    )
    write_receipt("DEV-500", dev500_payload)

    dev100_pool_by_scenario = {
        scenario: sorted(ids, key=int) for scenario, ids in dev500_by_scenario.items()
    }
    dev100_by_scenario = pick_subset(dev100_pool_by_scenario, 100, f"{SEED}:dev100")
    dev100_items = build_items(dev100_by_scenario, by_utterance)
    dev100_payload = receipt_payload(
        probe="dev-ladder-dev100",
        split_role="dev",
        n_items=100,
        pool_size=500,
        scenario_allocation=scenario_allocation_counts(dev100_by_scenario),
        items=dev100_items,
        exclusions=dev_exclusions,
        nesting={
            "parent_tier": "DEV-500",
            "parent_receipt": "docs/receipts/probe-samples/DEV-500.json",
            "parent_split_identity_hash": dev500_payload["split_identity_hash"],
            "is_exact_subset_of_parent": True,
        },
    )
    write_receipt("DEV-100", dev100_payload)

    # ---- cross-tier sanity (fail loudly before any receipt is trusted) ----
    final60_ids = {item["id"] for item in final60_items}
    dev1000_ids = {item["id"] for item in dev1000_items}
    dev500_ids = {item["id"] for item in dev500_items}
    dev100_ids = {item["id"] for item in dev100_items}
    probe60_sample_ids = {
        item["sample_id"]
        for item in json.loads(PROBE60_RECEIPT_PATH.read_text(encoding="utf-8"))["items"]
    }
    if not final60_ids.isdisjoint(dev1000_ids):
        raise RuntimeError("FINAL60 intersects DEV-1000")
    if not dev100_ids <= dev500_ids <= dev1000_ids:
        raise RuntimeError("DEV ladder nesting is not exact")
    for name, ids in (
        ("FINAL60", final60_ids),
        ("DEV-1000", dev1000_ids),
        ("DEV-500", dev500_ids),
        ("DEV-100", dev100_ids),
    ):
        if not ids.isdisjoint(probe60_sample_ids):
            raise RuntimeError(f"{name} intersects the historic probe-60 sample ids")
    print("cross-tier sanity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
