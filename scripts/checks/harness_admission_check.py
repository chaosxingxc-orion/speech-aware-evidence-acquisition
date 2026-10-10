#!/usr/bin/env python3
"""Model-free gate over the living harness-admission receipt (WAVE W4).

The design note's admission gate (``docs/readiness/
2026-09-08-agent-system-episode-and-core-pressure-v1.md`` section 8) says three
things a machine can check, and until this script existed none of them was
checked:

1. **The contrast is one config key, never a second code path.** So every
   entry in ``docs/receipts/harness-admission.json`` must name the table and
   the key that switch its module, that key must resolve in one of the four
   config tables (``rails.config_tables``), and its OFF arm must be that
   table's null arm -- the arm that composes to the same config hash as the
   table being absent, which is what makes OFF a twin of the pre-table
   baseline rather than a third cell identity. A ``proof`` field names the
   test that composes both arms and asserts the one-key property, and that
   test has to exist.

2. **The default plan contains only admitted or neutral modules.** Every
   ADMITTED or NEUTRAL entry must appear in at least one default plan for its
   own carrier -- an admission that never reaches a plan is a receipt nobody
   acted on.

3. **Harmful modules never enter a plan.** Nor does a module whose admission
   is provisional with its obligation UNMET: the KC-E1f verdict note fixed
   that consequence before the verdict was known ("until then ... NO entry
   into the default plan"), and a rule that lives only in prose is not a rule.

4. **A module outside the four config tables changed no request.** Added
   2026-09-08, when W4's v2 schema met ``master``'s cross-call dispatcher: a
   scheduler is one config key and has no per-phase table entry, because it
   is per-RUN and the four tables are per-phase. Such an entry declares
   ``switch.table`` ``"run"``, its key must be on the closed allowlist
   ``rails.config_tables.RUN_LEVEL_SWITCH_KEYS``, and it must carry a
   ``switch.falsifier`` -- ``{"kind": "request-bytes-identical", "receipt":
   "<receipt dir>"}`` -- whose receipt directory exists and whose
   ``MANIFEST.sha256`` verifies here. That falsifier is the whole licence for
   being outside the tables: a module that moves one byte of the request
   cannot produce one, and belongs in a table.

5. **A per-run episode-graph module names one dotted path under
   ``native_episode``.** Added by Fable E6 (2026-09-16, v3 schema, SLURP v2
   base program design section 3) for a module that changes how many times
   an agent role runs or how the Solver samples/aggregates -- neither a mode
   of what a phase observes/is supplied with/is judged by/may call (the four
   tables) nor provably byte-identical to the request (``run``). Such an
   entry declares ``switch.table`` ``"episode"``; its key must resolve on the
   closed allowlist ``rails.config_tables.EPISODE_LEVEL_SWITCH_KEYS``, and its
   OFF arm must be that key's own null form
   (``rails.config_tables.is_episode_null_arm``).

6. **A whole named knowledge store is one ``knowledge_stores.<store_id>``
   key, in one of TWO declared arm forms.** Added alongside rule 5, for a
   module that adds a whole named store block (release/snapshot pins plus its
   own supply) rather than one entry of the ``knowledge_views`` table, which
   wraps a PHASE's material/supply and not a STORE. Such an entry declares
   ``switch.table`` ``"stores"`` and its key must resolve as
   ``rails.config_tables.resolve_stores_switch_key`` requires. Its arms are
   then read in one of two forms, and the entry SAYS WHICH:

   * the NULL form (no ``switch.form`` field), for a module that ADDS a store
     the comparator does not carry: OFF is ``null``, the named store absent
     (``rails.config_tables.is_stores_null_arm``);
   * the RE-PIN form (``switch.form`` ``"repin"``, added 2026-09-17 by E9 for
     cell B4b's module M4b), for a module that REVISES a store the comparator
     ALREADY carries: OFF and ON are both re-pin arms
     (``rails.config_tables.is_stores_repin_arm`` -- exactly ``release`` and
     ``snapshot``, each a ``{relpath, sha256}`` pin), they must DIFFER, and
     each pin whose relpath resolves to a file in this repository is hashed
     here. A pin that resolves to no such file is a ``SPEECHRL_DATA_DIR``
     relpath, which this model-free check never opens and therefore checks for
     shape alone.

   The form is declared, never inferred: an entry whose OFF arm is not the
   store's absence and which does not say ``"repin"`` is refused, because an
   OFF arm silently allowed to be anything at all is the loosening the null
   form exists to prevent.

7. **One role's toolkit is one ``phase_tools.<phase>`` key, and a module
   that WITHDRAWS it is that toolkit's RETIREMENT.** Added 2026-09-20 by
   item E25 for cell B1-notool (repair form 0-B, owner decisions 55 and
   56), whose module is the removal of the Reviewer's task-contract tool.
   The seven classes above can only say that a module ADDS something, so
   the withdrawal had no honest encoding: an entry whose ON arm was the
   absence of a mapping. Such an entry now declares ``switch.table``
   ``"phase_tools"``, its key resolves as
   ``rails.config_tables.resolve_phase_tools_switch_key`` requires (a
   literal phase id, no placeholder), its OFF arm is the role's null arm
   (``rails.config_tables.is_phase_tools_null_arm``: ``null`` or ``{}``,
   which the runtime reads as no tool authority) and its ON arm is the
   toolkit mapping the comparator carried. The entry's status is
   ``RETIRED``: the OFF arm read NEUTRAL or better against the ON arm and
   lowered cost, so the default plan carries the OFF arm. ``RETIRED``
   BLOCKS the module from every plan exactly as HARMFUL does -- the plan
   rule then proves the withdrawal was acted on -- and, unlike HARMFUL, a
   retirement with NO default plan for its carrier is refused, because a
   retirement nobody's plan reflects is as unacted-on as an admission
   nobody's plan carries. A module granting a NEW toolkit uses the same
   class the ordinary way (ADMITTED / NEUTRAL, armed in a plan).

   ``status_values`` is validated against the statuses this check knows
   (``KNOWN_STATUSES``) for the same reason ``switch_classes`` is: a
   receipt naming a status nobody enforces is a receipt nobody is checking.

8. **The composed consumption policy is one ``module`` key, and its OFF arm
   is the LOCK, proven here.** Added 2026-09-30 by migration step 6 of the
   evidence-consumption module (owner decisions 195/196/204, coordinator
   ruling R2). Such an entry declares ``switch.table`` ``"module"``; its key
   is ``native_episode.consumption_module``
   (``rails.config_tables.resolve_module_switch_key``). Its OFF arm is a
   module block whose every component is ``off`` and which declares no
   column (``rails.consumption_module.is_module_off_block``) and which names
   its carrier's CURRENT lock version in ``lock`` (v2.2 for SLURP since owner
   decision 249, 2026-10-10; a still-PENDING entry whose cell flew on an older
   lock may stay on it by naming the CURRENT lock in ``switch.lock_superseded_by``);
   its ON arm is a block that
   arms at least one component and compiles. The entry owes a
   ``switch.falsifier`` of kind ``"compiles-to-lock"`` naming the lock
   version and one or more registered cells (experiment ids) that carry
   that lock's bytes; the check COMPILES the OFF arm and requires (a) the
   compiled policy blocks to equal the named lock version's own, and (b)
   each named cell's baseline fragment to carry exactly those blocks on its
   own roster (``ComposedPolicy.values_on_roster_of``) -- the AT-M0 proof,
   made by the gate rather than believed from a label. A plan arms the key
   when its fragment declares a block that is not the OFF arm.

A "default plan" is a committed config fragment the receipt itself names in
``default_plans`` -- declared, never inferred, because an experimental ON arm
is a config fragment carrying a table too and reading those as default plans
would admit every module the moment it was first tried.

Zero model contacts, zero GPU, no network, no ``SPEECHRL_DATA_DIR`` read.

Flags: ``--repo-root``, ``--receipt``, ``--json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT_DEFAULT / "src"))

from speech_aware_evidence_acquisition.rails.config_tables import (  # noqa: E402
    CONFIG_TABLE_NAMES,
    EPISODE_SWITCH_CLASS,
    KNOWLEDGE_STORES_TABLE,
    MODULE_SWITCH_CLASS,
    NULL_ARMS,
    PHASE_TOOLS_SWITCH_CLASS,
    RUN_NULL_ARMS,
    RUN_SWITCH_CLASS,
    STORES_PIN_FIELDS,
    STORES_REPIN_FORM,
    STORES_SWITCH_CLASS,
    SWITCH_CLASS_NAMES,
    ConfigTableError,
    is_episode_null_arm,
    is_phase_tools_null_arm,
    is_run_null_arm,
    is_stores_null_arm,
    is_stores_repin_arm,
    module_block_of,
    phase_tools_role_armed,
    resolve_episode_switch_key,
    resolve_module_switch_key,
    resolve_phase_tools_switch_key,
    resolve_run_switch_key,
    resolve_stores_switch_key,
    resolve_switch_key,
    stores_arm_matches,
)

RECEIPT_RELPATH = "docs/receipts/harness-admission.json"
EXPECTED_SCHEMA = "saea-harness-admission-v3"

#: The statuses whose modules belong in a default plan, and the two that
#: never do. ``PENDING`` is neither: a registered, undecided module has
#: nothing to enforce yet. ``RETIRED`` (item E25, 2026-09-20) is the status
#: of a module whose ON arm was WITHDRAWN by a measured cell: its OFF arm
#: read NEUTRAL or better and lowered cost, so the plan carries the OFF arm
#: and the module is barred from every plan exactly as a HARMFUL one is --
#: but a retirement additionally owes a default plan for its carrier, so
#: that the bar is a statement about a plan that exists.
PLAN_STATUSES = ("ADMITTED", "NEUTRAL")
FORBIDDEN_STATUS = "HARMFUL"
RETIRED_STATUS = "RETIRED"
KNOWN_STATUSES = ("ADMITTED", "HARMFUL", "NEUTRAL", "PENDING", RETIRED_STATUS)

REQUIRED_TOP_LEVEL = (
    "default_plans",
    "entries",
    "gate",
    "schema",
    "status_values",
    "switch_rule",
)
REQUIRED_ENTRY_KEYS = ("carrier", "evidence", "module", "row", "status", "switch")
REQUIRED_SWITCH_KEYS = ("key", "off", "on", "proof", "table")

#: What a ``run``-class switch owes on top of :data:`REQUIRED_SWITCH_KEYS`.
REQUIRED_RUN_SWITCH_KEYS = ("falsifier",)

#: The only falsifier kind the ``run`` class accepts. It is not a label: the
#: check verifies the named receipt's ``MANIFEST.sha256`` before believing it.
RUN_FALSIFIER_KIND = "request-bytes-identical"

#: The only falsifier kind the ``module`` class accepts (rule 8): the check
#: compiles the OFF arm itself and compares it with the named lock and cells.
MODULE_FALSIFIER_KIND = "compiles-to-lock"

MANIFEST_NAME = "MANIFEST.sha256"


class HarnessAdmissionCheckError(RuntimeError):
    """The receipt could not be read at all."""


def _read_receipt(path: Path) -> Mapping[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise HarnessAdmissionCheckError(f"cannot read {path}: {error}") from error
    if not isinstance(document, dict):
        raise HarnessAdmissionCheckError(f"{path} must be a JSON object")
    return document


def _is_blocked(entry: Mapping[str, Any]) -> tuple[bool, str]:
    """Whether this entry's module is barred from every default plan, and why."""

    if entry.get("status") == FORBIDDEN_STATUS:
        return True, "status HARMFUL"
    if entry.get("status") == RETIRED_STATUS:
        return True, "status RETIRED (the ON arm was withdrawn; the plan carries the OFF arm)"
    provisional = entry.get("provisional")
    if isinstance(provisional, Mapping) and provisional.get("state") == "UNMET":
        return True, "provisional obligation UNMET"
    return False, ""


def _switch_present(
    fragment: Mapping[str, Any],
    table: str,
    entry_key: str,
    switch: Mapping[str, Any] | None = None,
) -> bool:
    """Whether ``fragment`` arms ``entry_key`` of ``table`` with a non-null arm.

    The table's own null arm is not "present": that is the OFF arm, and a
    plan declaring it is a plan the module is switched off in. A ``run``-class
    key is FLAT, so it is looked for at the fragment's top level and its null
    arm is the key's absence or the driver's documented default.

    A ``stores``-class module in the RE-PIN form is the one case where "not
    the null arm" is not the question: its OFF arm is the incumbent's pins,
    not the store's absence, so a plan arms it only when the plan pins exactly
    the ON arm's release and snapshot bytes. That is what ``switch`` is passed
    for -- a plan still carrying the incumbent's pins has not armed the
    successor, and neither has a plan carrying no store at all.
    """

    if table == RUN_SWITCH_CLASS:
        return entry_key in fragment and not is_run_null_arm(fragment.get(entry_key))
    if table == EPISODE_SWITCH_CLASS:
        return _episode_key_present(fragment, entry_key)
    if table == PHASE_TOOLS_SWITCH_CLASS:
        return phase_tools_role_armed(fragment, entry_key)
    if table == MODULE_SWITCH_CLASS:
        from speech_aware_evidence_acquisition.rails.consumption_module import (  # noqa: PLC0415
            is_module_off_block,
        )

        block = module_block_of(fragment)
        return block is not None and not is_module_off_block(block)
    if table == STORES_SWITCH_CLASS:
        store_id = entry_key.split(".", 1)[1]
        if isinstance(switch, Mapping) and switch.get("form") == STORES_REPIN_FORM:
            return stores_arm_matches(fragment, store_id, switch.get("on"))
        stores = fragment.get(KNOWLEDGE_STORES_TABLE)
        return isinstance(stores, Mapping) and not is_stores_null_arm(stores.get(store_id))
    block = fragment.get(table)
    if any(block == arm for arm in NULL_ARMS) or not isinstance(block, Mapping):
        return False
    return _names_key(block, entry_key)


def _episode_key_present(fragment: Mapping[str, Any], key: str) -> bool:
    """Whether ``fragment`` arms the dotted ``episode``-class key ``key`` --
    walks the path and asks whether what it finds is that key's own null
    form (:func:`rails.config_tables.is_episode_null_arm`)."""

    cursor: object = fragment
    for segment in key.split("."):
        if not isinstance(cursor, Mapping) or segment not in cursor:
            return False
        cursor = cursor[segment]
    return not is_episode_null_arm(key, cursor)


def _names_key(value: object, entry_key: str) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == entry_key and not any(child == arm for arm in NULL_ARMS):
                return True
            if _names_key(child, entry_key):
                return True
    return False


def _check_switch(entry: Mapping[str, Any], repo_root: Path, where: str) -> list[str]:
    failures: list[str] = []
    switch = entry.get("switch")
    if not isinstance(switch, Mapping):
        return [f"{where}: 'switch' must be an object naming the module's one key"]
    missing = sorted(set(REQUIRED_SWITCH_KEYS) - set(switch))
    if missing:
        failures.append(f"{where}.switch is missing {missing}")
        return failures
    table = switch["table"]
    if table == RUN_SWITCH_CLASS:
        return _check_run_switch(switch, repo_root, where)
    if table == EPISODE_SWITCH_CLASS:
        return _check_episode_switch(switch, repo_root, where)
    if table == STORES_SWITCH_CLASS:
        return _check_stores_switch(switch, repo_root, where)
    if table == PHASE_TOOLS_SWITCH_CLASS:
        return _check_phase_tools_switch(switch, repo_root, where)
    if table == MODULE_SWITCH_CLASS:
        return _check_module_switch(switch, repo_root, where, status=entry.get("status"))
    if table not in CONFIG_TABLE_NAMES:
        failures.append(
            f"{where}.switch.table is {table!r}; the switch classes are "
            f"{list(SWITCH_CLASS_NAMES)}"
        )
        return failures
    try:
        resolve_switch_key(table, switch["key"])
    except ConfigTableError as error:
        failures.append(f"{where}.switch.key: {error}")
    if not any(switch["off"] == arm for arm in NULL_ARMS):
        failures.append(
            f"{where}.switch.off is {switch['off']!r}; the OFF arm of a module must "
            f"be its table's null arm ({list(NULL_ARMS)}), which composes to the "
            "same config hash as the table being absent -- anything else makes the "
            "OFF arm a third cell identity rather than a twin"
        )
    if switch["on"] is None or any(switch["on"] == arm for arm in NULL_ARMS):
        failures.append(f"{where}.switch.on is the null arm; an ON arm must arm something")
    failures.extend(_check_proof(switch["proof"], repo_root, where))
    return failures


def _check_run_switch(switch: Mapping[str, Any], repo_root: Path, where: str) -> list[str]:
    """Rule 4: a per-run scheduling key, on the closed allowlist, whose entry
    proves it changed no request byte.

    Everything the table classes owe is still owed -- one key, a null OFF arm,
    an ON arm that arms something, a ``proof`` test that exists -- and the
    falsifier is owed on top, because being outside the four tables is exactly
    the claim that this module never reaches the core's request.
    """

    failures: list[str] = []
    missing = sorted(set(REQUIRED_RUN_SWITCH_KEYS) - set(switch))
    if missing:
        failures.append(
            f"{where}.switch is run-class and is missing {missing}; a module outside "
            "the four config tables owes a falsifier proving it changed no request byte"
        )
    try:
        resolve_run_switch_key(switch["key"])
    except ConfigTableError as error:
        failures.append(f"{where}.switch.key: {error}")
    if not is_run_null_arm(switch["off"]):
        failures.append(
            f"{where}.switch.off is {switch['off']!r}; the OFF arm of a run-level "
            f"module must be its null arm ({list(RUN_NULL_ARMS)}) -- the key absent "
            "or the driver's documented default -- so that OFF is a twin of the "
            "pre-knob baseline rather than a third cell identity"
        )
    if is_run_null_arm(switch["on"]):
        failures.append(f"{where}.switch.on is the null arm; an ON arm must arm something")
    failures.extend(_check_proof(switch["proof"], repo_root, where))
    if not missing:
        failures.extend(_check_falsifier(switch["falsifier"], repo_root, where))
    return failures


def _check_episode_switch(switch: Mapping[str, Any], repo_root: Path, where: str) -> list[str]:
    """Rule 5: one dotted path under ``native_episode``, on the closed
    allowlist, whose OFF arm is that key's own null form."""

    failures: list[str] = []
    try:
        key = resolve_episode_switch_key(switch["key"])
    except ConfigTableError as error:
        failures.append(f"{where}.switch.key: {error}")
        failures.extend(_check_proof(switch["proof"], repo_root, where))
        return failures
    if not is_episode_null_arm(key, switch["off"]):
        failures.append(
            f"{where}.switch.off is {switch['off']!r}; the OFF arm of an 'episode' "
            f"module must be {key!r}'s own null form, so OFF is a twin of the "
            "pre-module native_episode shape rather than a third cell identity"
        )
    if is_episode_null_arm(key, switch["on"]):
        failures.append(f"{where}.switch.on is the null arm; an ON arm must arm something")
    failures.extend(_check_proof(switch["proof"], repo_root, where))
    return failures


def _check_phase_tools_switch(
    switch: Mapping[str, Any], repo_root: Path, where: str
) -> list[str]:
    """Rule 7: one role's toolkit -- ``phase_tools.<phase>`` -- whose OFF arm is
    the role's null arm and whose ON arm is a non-empty toolkit mapping."""

    failures: list[str] = []
    try:
        resolve_phase_tools_switch_key(switch["key"])
    except ConfigTableError as error:
        failures.append(f"{where}.switch.key: {error}")
    if not is_phase_tools_null_arm(switch["off"]):
        failures.append(
            f"{where}.switch.off is {switch['off']!r}; the OFF arm of a 'phase_tools' "
            "module must be the role's null arm (null or {}: no tool authority), so "
            "that OFF is a twin of the tool-free episode rather than a third cell "
            "identity"
        )
    on = switch["on"]
    if is_phase_tools_null_arm(on) or not isinstance(on, Mapping):
        failures.append(
            f"{where}.switch.on is {on!r}; the ON arm of a 'phase_tools' module must "
            "be the role's non-empty toolkit mapping -- a toolkit is what this class "
            "grants or withdraws, and the absence of one is never an ON arm"
        )
    failures.extend(_check_proof(switch["proof"], repo_root, where))
    return failures


def _check_module_switch(
    switch: Mapping[str, Any], repo_root: Path, where: str, status: object = None,
) -> list[str]:
    """Rule 8: ``native_episode.consumption_module``, whose OFF arm is the
    all-off block on the carrier's CURRENT lock and whose licence -- the OFF
    arm compiles to that lock, and the named cells carry it -- is recomputed
    here, model-free, from the repository's own fragments."""

    from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: PLC0415

    failures: list[str] = []
    try:
        resolve_module_switch_key(switch["key"])
    except ConfigTableError as error:
        failures.append(f"{where}.switch.key: {error}")
    failures.extend(_check_proof(switch["proof"], repo_root, where))
    off, on = switch["off"], switch["on"]
    if not cm.is_module_off_block(off, repo_root=repo_root):
        failures.append(
            f"{where}.switch.off is not the module's OFF arm: a well-formed block with every "
            "component 'off' and no column, which compiles to its lock layer"
        )
        return failures
    try:
        hooks = cm.resolve_carrier_hooks(off["profile"], repo_root=repo_root)
    except cm.ConsumptionModuleConfigError as error:
        return failures + [f"{where}.switch.off: {error}"]
    superseded = switch.get("lock_superseded_by")
    if superseded is not None and off.get("lock") is not None and off.get("lock") != hooks.current_lock:
        # Owner decision 249 (2026-10-10): a registered, still-PENDING entry keeps the lock its
        # cell flew on when CURRENT_LOCK moves, and names the lock that superseded it (which
        # must be CURRENT now). Any other status must sit on the CURRENT lock.
        if superseded != hooks.current_lock or status != "PENDING":
            failures.append(
                f"{where}.switch.lock_superseded_by is {superseded!r}; it must name the CURRENT lock "
                f"({hooks.current_lock!r}) and only a PENDING entry may stay on its registered lock"
            )
    elif off.get("lock") is None or off.get("lock") != hooks.current_lock:
        failures.append(
            f"{where}.switch.off names lock {off.get('lock')!r}; the OFF arm of a 'module' "
            f"entry names its carrier's CURRENT lock ({hooks.current_lock!r}) -- the null "
            "arm of every composed read registered now"
        )
    if not isinstance(on, Mapping) or cm.is_module_off_block(on, repo_root=repo_root):
        failures.append(f"{where}.switch.on must be a module block that arms at least one component")
    else:
        try:
            on_policy = cm.compile_module(on, hooks, repo_root=repo_root)
        except cm.ConsumptionModuleConfigError as error:
            failures.append(f"{where}.switch.on does not compile: {error}")
        else:
            if on_policy.lock_version != off.get("lock"):
                failures.append(
                    f"{where}.switch.on composes onto lock {on_policy.lock_version!r}; the two "
                    "arms of one module entry sit on ONE lock"
                )
    falsifier = switch.get("falsifier")
    if not isinstance(falsifier, Mapping) or falsifier.get("kind") != MODULE_FALSIFIER_KIND:
        failures.append(
            f"{where}.switch.falsifier must be an object of kind {MODULE_FALSIFIER_KIND!r} naming "
            "the lock and the registered cells that carry it"
        )
        return failures
    cells = falsifier.get("cells")
    if falsifier.get("lock") != off.get("lock") or not isinstance(cells, list) or not cells:
        failures.append(
            f"{where}.switch.falsifier must name the OFF arm's lock and a non-empty 'cells' list"
        )
        return failures
    try:
        compiled = cm.compile_module(off, hooks, repo_root=repo_root)
        lock_blocks = dict((hooks.lock_versions or {})[off["lock"]]())
    except (cm.ConsumptionModuleConfigError, KeyError) as error:
        return failures + [f"{where}.switch.off does not compile to a lock: {error}"]
    diff = cm.differing_paths(compiled.values(), json.loads(json.dumps(lock_blocks)))
    if diff:
        failures.append(f"{where}.switch.off compiles to blocks differing from lock {off['lock']} at {diff[:8]}")
    for experiment in cells:
        path = repo_root / "configs" / "experiment" / f"{experiment}.json"
        try:
            cell = json.loads(path.read_text(encoding="utf-8"))["cells"][0]
            baseline = json.loads(
                (repo_root / "configs" / "baseline" / f"{cell['baseline_fragment']}.json").read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, ValueError, KeyError, IndexError, TypeError) as error:
            failures.append(f"{where}.switch.falsifier.cells: cannot read {experiment}: {error}")
            continue
        cell_diff = cm.differing_paths(
            compiled.values_on_roster_of(baseline), cm.policy_owned_values(baseline)
        )
        if cell_diff:
            failures.append(
                f"{where}.switch.falsifier.cells: {experiment} does not carry lock {off['lock']}'s "
                f"policy blocks on its own roster; differs at {cell_diff[:8]}"
            )
    return failures


def _check_stores_switch(switch: Mapping[str, Any], repo_root: Path, where: str) -> list[str]:
    """Rule 6: ``knowledge_stores.<store_id>``, in one of the class's two
    DECLARED arm forms -- the null form, whose OFF arm is the named store's
    absence, and the re-pin form, whose OFF and ON arms are the incumbent's
    and the successor's release/snapshot pins."""

    failures: list[str] = []
    try:
        resolve_stores_switch_key(switch["key"])
    except ConfigTableError as error:
        failures.append(f"{where}.switch.key: {error}")
        failures.extend(_check_proof(switch["proof"], repo_root, where))
        return failures
    form = switch.get("form")
    if form is not None and form != STORES_REPIN_FORM:
        failures.append(
            f"{where}.switch.form is {form!r}; a 'stores' entry is in one of two "
            f"forms -- no 'form' field (the null form: OFF is the named store "
            f"absent) or {STORES_REPIN_FORM!r} (the re-pin form: OFF and ON are the "
            "incumbent's and the successor's release/snapshot pins)"
        )
        failures.extend(_check_proof(switch["proof"], repo_root, where))
        return failures
    if form == STORES_REPIN_FORM:
        failures.extend(_check_stores_repin_arms(switch, repo_root, where))
    else:
        if not is_stores_null_arm(switch["off"]):
            failures.append(
                f"{where}.switch.off is {switch['off']!r}; the OFF arm of a 'stores' "
                "module must be null -- the named store absent -- so OFF is a twin of "
                "the pre-module knowledge_stores shape rather than a third cell "
                f"identity. A module that RE-PINS a store the comparator already "
                f"carries is the class's other form and must declare "
                f"'form': {STORES_REPIN_FORM!r}"
            )
        if is_stores_null_arm(switch["on"]):
            failures.append(
                f"{where}.switch.on is the null arm; an ON arm must arm something"
            )
    failures.extend(_check_proof(switch["proof"], repo_root, where))
    return failures


def _check_stores_repin_arms(
    switch: Mapping[str, Any], repo_root: Path, where: str
) -> list[str]:
    """The re-pin form's own rules: two well-formed pin arms, DIFFERENT from
    each other, and every pin this repository actually holds re-hashed here.

    A re-pin twin is not a null twin, and saying so out loud is the whole
    point of the form: OFF is a config the comparator really flew, so the
    check cannot fall back on "absent means off". What it can do instead is
    insist that the two arms move the two pin leaves and nothing else, and
    that they are not the same bytes wearing two names.
    """

    failures: list[str] = []
    for arm_name in ("off", "on"):
        if not is_stores_repin_arm(switch[arm_name]):
            failures.append(
                f"{where}.switch.{arm_name} is {switch[arm_name]!r}; a re-pin arm must "
                f"carry exactly {list(STORES_PIN_FIELDS)}, each an object of 'relpath' "
                "and a lowercase 64-hex 'sha256' -- the two leaves a store re-pin "
                "moves and the only two it may move"
            )
    if failures:
        return failures
    if switch["off"] == switch["on"]:
        failures.append(
            f"{where}.switch.off equals {where}.switch.on; a re-pin whose two arms pin "
            "the same release and snapshot bytes switches nothing at all, and a module "
            "that switches nothing is not a module"
        )
    for arm_name in ("off", "on"):
        for field in STORES_PIN_FIELDS:
            failures.extend(
                _check_stores_pin(
                    switch[arm_name][field],
                    repo_root,
                    f"{where}.switch.{arm_name}.{field}",
                )
            )
    return failures


def _check_stores_pin(
    pin: Mapping[str, Any], repo_root: Path, where: str
) -> list[str]:
    """One release or snapshot pin of a re-pin arm.

    A store pin is either REPO-relative -- and then its bytes are in this
    repository and are re-hashed here, because a pin whose file moved is not a
    pin -- or a ``SPEECHRL_DATA_DIR`` relpath, which this model-free check
    never opens (it reads no data root) and so checks for shape alone. Which
    of the two it is, is decided by looking. The one case in between is
    fail-closed: a relpath whose DIRECTORY is in this repository but whose
    file is not is a repo-relative pin that names nothing.
    """

    relpath = str(pin["relpath"])
    path = repo_root / relpath
    if path.is_file():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != pin["sha256"]:
            return [
                f"{where} pins {relpath} at {pin['sha256']}, but that file's bytes in "
                f"this repository hash to {digest}"
            ]
        return []
    if path.parent.is_dir():
        return [
            f"{where} names {relpath}, whose directory is in this repository but whose "
            "file is not; a repo-relative store pin must name a file that exists"
        ]
    return []


def _check_falsifier(falsifier: object, repo_root: Path, where: str) -> list[str]:
    """The run class's licence, verified rather than believed."""

    if not isinstance(falsifier, Mapping):
        return [f"{where}.switch.falsifier must be an object with 'kind' and 'receipt'"]
    missing = sorted({"kind", "receipt"} - set(falsifier))
    if missing:
        return [f"{where}.switch.falsifier is missing {missing}"]
    if falsifier["kind"] != RUN_FALSIFIER_KIND:
        return [
            f"{where}.switch.falsifier.kind is {falsifier['kind']!r}; the run class "
            f"accepts only {RUN_FALSIFIER_KIND!r}"
        ]
    directory = repo_root / str(falsifier["receipt"])
    if not directory.is_dir():
        return [
            f"{where}.switch.falsifier.receipt names {falsifier['receipt']}, which is "
            "not a directory in this repository"
        ]
    return _verify_manifest(directory, f"{where}.switch.falsifier.receipt")


def _verify_manifest(directory: Path, where: str) -> list[str]:
    """``MANIFEST.sha256`` over ``directory``, re-hashed here.

    The repository's own convention: one ``<sha256> *<relpath>`` line per file,
    the manifest itself excluded. A named receipt whose bytes moved is not a
    proof of anything, so this is fail-closed on a missing, malformed, short or
    mismatching manifest.
    """

    manifest = directory / MANIFEST_NAME
    if not manifest.is_file():
        return [f"{where}: {directory.name} carries no {MANIFEST_NAME}"]
    try:
        lines = manifest.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        return [f"{where}: cannot read {MANIFEST_NAME}: {error}"]
    problems: list[str] = []
    listed = 0
    for line in lines:
        if not line.strip():
            continue
        digest, _, relpath = line.partition(" *")
        if not relpath or len(digest) != 64:
            problems.append(f"malformed line {line!r}")
            continue
        listed += 1
        target = directory / relpath
        if not target.is_file():
            problems.append(f"{relpath} is listed and missing")
            continue
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            problems.append(f"{relpath} does not match its listed sha256")
    if not listed:
        problems.append(f"{MANIFEST_NAME} carries zero entries")
    if problems:
        return [f"{where}: {MANIFEST_NAME} does not verify: " + "; ".join(problems)]
    return []


def _check_proof(proof: object, repo_root: Path, where: str) -> list[str]:
    if not isinstance(proof, str) or "::" not in proof:
        return [f"{where}.switch.proof must be a '<test file>::<test name>' node id"]
    relpath, _, test_name = proof.partition("::")
    path = repo_root / relpath
    if not path.is_file():
        return [f"{where}.switch.proof names {relpath}, which does not exist"]
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return [f"{where}.switch.proof: cannot read {relpath}: {error}"]
    if f"def {test_name}(" not in source:
        return [f"{where}.switch.proof names {test_name}, which {relpath} does not define"]
    return []


def _load_plans(document: Mapping[str, Any], repo_root: Path) -> tuple[list[str], list[dict]]:
    failures: list[str] = []
    plans: list[dict] = []
    declared = document.get("default_plans")
    if not isinstance(declared, list):
        return ["'default_plans' must be a list (empty is legal and is a statement)"], []
    for index, plan in enumerate(declared):
        where = f"default_plans[{index}]"
        if not isinstance(plan, Mapping):
            failures.append(f"{where} must be an object with 'carrier' and 'config'")
            continue
        missing = sorted({"carrier", "config"} - set(plan))
        if missing:
            failures.append(f"{where} is missing {missing}")
            continue
        path = repo_root / str(plan["config"])
        if not path.is_file():
            failures.append(f"{where} names {plan['config']}, which does not exist")
            continue
        try:
            fragment = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            failures.append(f"{where}: cannot read {plan['config']}: {error}")
            continue
        if not isinstance(fragment, dict):
            failures.append(f"{where}: {plan['config']} must be a JSON object")
            continue
        plans.append(
            {"carrier": plan["carrier"], "config": str(plan["config"]), "fragment": fragment}
        )
    return failures, plans


def evaluate(repo_root: Path, receipt_path: Path | None = None) -> dict[str, Any]:
    path = receipt_path or (repo_root / RECEIPT_RELPATH)
    document = _read_receipt(path)
    failures: list[str] = []

    missing = sorted(set(REQUIRED_TOP_LEVEL) - set(document))
    if missing:
        failures.append(f"the receipt is missing top-level key(s) {missing}")
    if document.get("schema") != EXPECTED_SCHEMA:
        failures.append(
            f"schema is {document.get('schema')!r}, expected {EXPECTED_SCHEMA!r}"
        )
    classes = document.get("switch_classes")
    if classes is not None and list(classes) != list(SWITCH_CLASS_NAMES):
        failures.append(
            f"'switch_classes' is {list(classes)}; this check knows "
            f"{list(SWITCH_CLASS_NAMES)}. The field is the receipt's own version "
            "marker for the switch vocabulary, and a receipt that names a class "
            "this check cannot enforce is a receipt nobody is checking"
        )
    statuses = document.get("status_values")
    known_statuses = set(statuses) if isinstance(statuses, Mapping) else set()
    unenforced = sorted(known_statuses - set(KNOWN_STATUSES))
    if unenforced:
        failures.append(
            f"'status_values' names {unenforced}, which this check does not enforce; "
            f"the statuses it knows are {list(KNOWN_STATUSES)}"
        )

    plan_failures, plans = _load_plans(document, repo_root)
    failures.extend(plan_failures)

    entries = document.get("entries")
    if not isinstance(entries, list):
        failures.append("'entries' must be a list")
        entries = []

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries):
        where = f"entries[{index}]"
        if not isinstance(entry, Mapping):
            failures.append(f"{where} must be an object")
            continue
        entry_missing = sorted(set(REQUIRED_ENTRY_KEYS) - set(entry))
        if entry_missing:
            failures.append(f"{where} is missing {entry_missing}")
            continue
        module = str(entry["module"])
        carrier = str(entry["carrier"])
        where = f"entries[{index}] ({module!r} on {carrier!r})"
        if (module, carrier) in seen:
            failures.append(f"{where}: a second entry decides the same module and carrier")
        seen.add((module, carrier))
        status = entry["status"]
        if known_statuses and status not in known_statuses:
            failures.append(
                f"{where}: status {status!r} is not one of {sorted(known_statuses)}"
            )
        switch_failures = _check_switch(entry, repo_root, where)
        failures.extend(switch_failures)

        blocked, reason = _is_blocked(entry)
        table = entry["switch"].get("table") if isinstance(entry["switch"], Mapping) else None
        entry_key = None
        if not switch_failures and table in CONFIG_TABLE_NAMES:
            entry_key = resolve_switch_key(table, entry["switch"]["key"])
        elif not switch_failures and table == RUN_SWITCH_CLASS:
            entry_key = resolve_run_switch_key(entry["switch"]["key"])
        elif not switch_failures and table == EPISODE_SWITCH_CLASS:
            entry_key = resolve_episode_switch_key(entry["switch"]["key"])
        elif not switch_failures and table == STORES_SWITCH_CLASS:
            entry_key = resolve_stores_switch_key(entry["switch"]["key"])
        elif not switch_failures and table == PHASE_TOOLS_SWITCH_CLASS:
            entry_key = resolve_phase_tools_switch_key(entry["switch"]["key"])
        elif not switch_failures and table == MODULE_SWITCH_CLASS:
            entry_key = resolve_module_switch_key(entry["switch"]["key"])

        carrying = (
            [
                plan["config"]
                for plan in plans
                if plan["carrier"] == carrier
                and _switch_present(
                    plan["fragment"], table, entry_key, entry["switch"]
                )
            ]
            if entry_key is not None
            else []
        )
        if blocked and carrying:
            failures.append(
                f"{where}: {reason}, but it is armed in default plan(s) {carrying}; a "
                "module in this state never enters a plan"
            )
        if status == RETIRED_STATUS and not any(
            plan["carrier"] == carrier for plan in plans
        ):
            failures.append(
                f"{where}: status RETIRED, but no default plan exists for {carrier!r}; "
                "a retirement is a statement that the plan carries the OFF arm, and "
                "there is no plan to carry it"
            )
        if not blocked and status in PLAN_STATUSES and not carrying:
            failures.append(
                f"{where}: status {status} with no blocking obligation, but no default "
                f"plan for {carrier!r} arms {entry['switch']['key']!r}; an admitted "
                "module that reaches no plan is a receipt nobody acted on"
            )
        rows.append(
            {
                "blocked": blocked,
                "blocked_reason": reason,
                "carrier": carrier,
                "in_default_plans": carrying,
                "module": module,
                "status": status,
                "switch_form": entry["switch"].get("form"),
                "switch_key": entry["switch"].get("key"),
                "table": table,
            }
        )

    return {
        "schema": "saea-harness-admission-check-v1",
        "receipt": str(path),
        "repo_root": str(repo_root),
        "default_plans": [
            {"carrier": plan["carrier"], "config": plan["config"]} for plan in plans
        ],
        "entries": rows,
        "failures": failures,
        "passed": not failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--receipt", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        data = evaluate(args.repo_root.resolve(), args.receipt)
    except HarnessAdmissionCheckError as exc:
        print(f"harness admission check: FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for failure in data["failures"]:
        print(f"harness admission check: FAIL: {failure}")
    if data["failures"]:
        print(f"harness admission check: FAIL ({len(data['failures'])} finding(s))")
        return 1

    blocked = sum(1 for row in data["entries"] if row["blocked"])
    print(
        "harness admission check: PASS "
        f"({len(data['entries'])} module(s), {blocked} barred from every default "
        f"plan, {len(data['default_plans'])} default plan(s))"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
