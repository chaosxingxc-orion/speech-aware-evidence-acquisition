#!/usr/bin/env python3
"""Ratchet guard against engineering-base regrowth (owner rules, 2026-09-03).

Study ``CLAUDE.md`` section "Engineering base and experiment rules (owner,
2026-09-03)" forbids new per-experiment forks: no new module under
``rails/probes/``, no ``TaskAdapter`` or Agent-controller subclass outside
``rails/adapters/`` / ``rails/controllers.py`` / ``rails/kb_policy.py``
(the migration source, allowed until disposal), no ``launcher/`` directory
under ``docs/checks/``, and every ``policy`` / ``evidence_source`` /
``scorers`` / ``judges`` value (plus the knowledge-plane policy-chain ids,
and -- WAVE W3, 2026-09-08 -- every ``tools`` list of catalog ids) in
``configs/`` must resolve in a ``core.base`` registry.

The September tree already violates every one of these rules at scale, so
this check runs in RATCHET mode: a committed baseline
(``engineering_base_baseline.json``) lists today's offenders per rule; the
check FAILs only on offenders NOT already in the baseline (regrowth), and
WARNs (exit 0) when a baseline entry no longer reproduces (so the baseline
can be shrunk as disposal proceeds). One rule -- the adapter line budget --
is never ratcheted: it fails outright on any offender, today included.

Two tree-reading modes share every rule's detection logic:

* "live" (default): reads the working tree exactly as it sits on disk, dirty
  or not -- this is what the check evaluates on every ordinary run, native
  Windows Python included.
* "committed" (``--write-baseline`` only): reads file lists and contents
  through ``git ls-tree`` / ``git show HEAD:<path>``, so concurrent
  uncommitted edits from other agents can never leak into a freshly captured
  baseline. Refuses if git is unavailable.

Registered names for ``policy`` / ``evidence_source`` / ``scorers`` /
``judges`` / knowledge-plane ids are resolved WITHOUT importing the (torch-dependent)
package: a regex scan of the five canonical ``core.base`` population sites
(``core/policies.py``, ``core/evidence.py``, ``core/scorers.py``,
``rails/kb_policy.py``, ``rails/knowledge_build.py``,
``rails/controllers.py``, ``rails/knowledge_provider.py``) for
``<REGISTRY_VAR>.register(<literal-or-constant>, ...)`` calls, with a
second pass over every ``src/`` module resolving bare-identifier arguments
(e.g. ``OBS_LOOP_POLICY_NAME``) to their module-level string assignment,
wherever in the tree that assignment lives.

Flags: ``--repo-root``, ``--baseline``, ``--write-baseline``, ``--json``.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

# ---------------------------------------------------------------------------
# Fixed repository layout this check understands.
# ---------------------------------------------------------------------------

PACKAGE_ROOT = "src/speech_aware_evidence_acquisition"
PROBES_DIR = f"{PACKAGE_ROOT}/rails/probes"
ADAPTERS_DIR = f"{PACKAGE_ROOT}/rails/adapters"
CONTROLLERS_MODULE = f"{PACKAGE_ROOT}/rails/controllers.py"
KB_POLICY_MODULE = f"{PACKAGE_ROOT}/rails/kb_policy.py"
KNOWLEDGE_PROVIDER_MODULE = f"{PACKAGE_ROOT}/rails/knowledge_provider.py"
TOOLS_MODULE = f"{PACKAGE_ROOT}/rails/tools.py"
DOCS_CHECKS_DIR = "docs/checks"
CONFIG_DIRS = ("configs/baseline", "configs/experiment")
LAUNCHER_DIR_NAME = "launcher"
ADAPTER_LINE_BUDGET = 260

# The six files the owner rule names as the ONE place each registry may be
# populated (study CLAUDE.md "Read first" / this check's own docstring
# above). A ``<REGISTRY_VAR>.register(...)`` call anywhere else (e.g. a
# probe's own locally-instantiated ``core.base.Registry()`` bound to a
# similarly-named local variable) is exactly the fragmentation this check
# exists to catch, and must NOT be mistaken for a real registration.
CANONICAL_REGISTRY_FILES = (
    f"{PACKAGE_ROOT}/core/model/native_evidence_projection.py",
    f"{PACKAGE_ROOT}/core/model/native_slot_binding_view.py",
    f"{PACKAGE_ROOT}/core/policies.py",
    f"{PACKAGE_ROOT}/core/evidence.py",
    f"{PACKAGE_ROOT}/core/scorers.py",
    KB_POLICY_MODULE,
    f"{PACKAGE_ROOT}/rails/knowledge_build.py",
    # Slice C4a (2026-09-03): the four phase-program controller ids register
    # into AGENT_CONTROLLERS from rails/controllers.py at import time; it is
    # one of the four bases the owner rule names, so it is a canonical
    # registration site too.
    CONTROLLERS_MODULE,
    # E6 (2026-09-06): core.base.KNOWLEDGE_PROVIDERS is populated from
    # rails/knowledge_provider.py -- the registry object moved to core.base
    # so a baseline fragment's phase_supply.provider resolves like every
    # other component id, but the three register() calls stay beside the
    # provider classes. This file is therefore a canonical registration
    # site, exactly as rails/kb_policy.py is for the ranker/fuser ids it
    # registers beside their implementations.
    KNOWLEDGE_PROVIDER_MODULE,
    # WAVE W3 (2026-09-08): the tool catalog registers every pinned,
    # SYSTEM-invoked tool into TOOL_CATALOG from rails/tools.py, beside the
    # manifests, for the same reason the provider ids register beside the
    # provider classes. See the "WAVE W3" block below for the config rule.
    TOOLS_MODULE,
    f"{PACKAGE_ROOT}/rails/phase_planner.py",
    # Owner decisions 195/196 (2026-09-29, design docs/superpowers/specs/
    # 2026-09-29-slurp-consumption-module-design.md section 2.1): the
    # evidence-consumption module registers into core.base.
    # CONSUMPTION_MODULES beside its own compiler.
    f"{PACKAGE_ROOT}/rails/consumption_module.py",
)

# FAMILY registrations (coordinator ruling R1 on the consumption-module
# design, 2026-09-29): a canonical file may register a closed family of ids
# through ONE loop over a module-level tuple of string literals, instead of
# one literal ``register`` call per id. The tuple is read from source (AST,
# literals only -- anything else refuses), every member is a registered name
# of the named registry, and the loop variable is the only bare identifier
# such a loop may pass to ``<REGISTRY_VAR>.register(...)``.
# tuple constant name -> (canonical file, registry variable)
FAMILY_ID_TUPLES = {
    "MODULE_PROGRAM_FAMILY_IDS": (CONTROLLERS_MODULE, "AGENT_CONTROLLERS"),
}

# config key -> core.base registry variable, top-level only (the flat
# "arm program" fragment shape used throughout configs/baseline/*.json and
# most configs/experiment/*.json).
# ``policy`` resolves in POLICIES for a one-contact arm program and in
# AGENT_CONTROLLERS for a phase-program id (``configs/policy/phase-*.json``,
# registered by rails/controllers.py): ``core.flight.FlightRuntime.run_phases``
# dispatches on exactly that distinction. The owner rule is that every
# ``policy`` value RESOLVES IN A core.base REGISTRY, so both are legal and a
# value in neither is still an offender.
TOP_LEVEL_STRING_KEYS = {
    "policy": ("POLICIES", "AGENT_CONTROLLERS"),
    "evidence_source": ("EVIDENCE_SOURCES",),
    "native_evidence_projection": ("NATIVE_EVIDENCE_PROJECTIONS",),
}
TOP_LEVEL_LIST_KEY = ("scorers", "SCORERS")

# config key -> core.base registry variable, for a LIST of ids matched at ANY
# depth/path in the JSON document. ``scorers`` above is top-level only because
# that is where the arm-program shape puts it; a ``judges`` list is declared
# per PHASE, inside a baseline fragment's ``phase_review`` object
# (``rails.phase_review``), so the parent object name would have to be
# hard-coded to find it -- the same reason NESTED_ID_KEYS is an any-depth
# search. Matching at any depth also catches a future top-level ``judges``
# list (the design note's own "judges config table with a null arm") without a
# second rule.
#
# Owner Decision 11-B change #1, 2026-09-08: every ``judges`` value in
# ``configs/`` must resolve in ``core.base.JUDGES``, exactly as every
# ``policy`` / ``evidence_source`` / ``scorers`` value resolves in its own
# registry. An unregistered judge id is the same defect class as an
# unregistered policy id: a config that reads as if it reviews and does not.
NESTED_LIST_ID_KEYS = {
    "judges": "JUDGES",
}

# config key -> core.base registry variable, matched at ANY depth/path in the
# JSON document (observed nested under e.g. "kb_campaign_policy_chain" /
# "kb_campaign_knowledge_snapshot" -- the parent object name is not stable
# enough to hard-code, so this is a recursive any-depth key search instead).
# Both the names actually observed in configs/ today (controller_policy_id,
# ranker_policy_id, fuser_policy_id, builder_policy_id) and the originally
# proposed aliases are covered so a future config using either spelling is
# still checked.
NESTED_ID_KEYS = {
    "planner_policy_id": "PHASE_PLANNERS",
    "controller_policy_id": "AGENT_CONTROLLERS",
    "agent_controller_policy_id": "AGENT_CONTROLLERS",
    "ranker_policy_id": "KNOWLEDGE_RANKERS",
    "knowledge_ranker_id": "KNOWLEDGE_RANKERS",
    "fuser_policy_id": "KNOWLEDGE_FUSERS",
    "knowledge_fuser_id": "KNOWLEDGE_FUSERS",
    "builder_policy_id": "KNOWLEDGE_BUILDERS",
    "knowledge_builder_id": "KNOWLEDGE_BUILDERS",
    # E1 (2026-09-05): a phase program's per-phase structured-output
    # contract, declared both in configs/policy/phase-*.json and, per phase,
    # under a baseline fragment's "phase_material" object.
    "response_format_id": "RESPONSE_FORMATS",
    # E6 (2026-09-06): a baseline fragment's "phase_supply" object declares,
    # per supplied phase, which knowledge provider ranks and fuses the
    # frozen snapshot and under which registered rank/fuse policy. All three
    # resolve in a core.base registry like every other component id.
    "provider": "KNOWLEDGE_PROVIDERS",
    "knowledge_provider_id": "KNOWLEDGE_PROVIDERS",
    "rank_policy": "KNOWLEDGE_RANKERS",
    "fuse_policy": "KNOWLEDGE_FUSERS",
    # Owner decisions 195/196 (2026-09-29): a native_episode.consumption_module
    # block names its module; the id resolves in core.base.CONSUMPTION_MODULES.
    "module_id": "CONSUMPTION_MODULES",
}

# E22 cell (b) (2026-09-06): a config fragment may declare
# ``decoding_params.max_tokens`` as a PER-SAMPLE RULE OBJECT naming a policy id
# instead of a plain integer (``core.flight.runtime.MAX_TOKENS_POLICY_KEY``);
# that id must resolve in ``core.base.MAX_TOKENS_POLICIES`` like every other
# component id a config declares.
#
# It is matched by PATH, not by bare key name, for one reason: the key inside
# the rule object is spelled ``policy``, which at top level already means an
# arm program's own ``POLICIES``/``AGENT_CONTROLLERS`` id. Adding ``policy`` to
# NESTED_ID_KEYS would make every ``"policy": "fixed"`` in the tree an offender
# against the wrong registry.
#
# ``decoding_params`` lives in a MODEL fragment by this repository's
# convention (67 model fragments declare it, no baseline fragment does), and
# ``core.config.compose`` merges the four fragments' top-level keys into one
# flat mapping, so the key is looked for in the model directory as well as in
# the two CONFIG_DIRS above -- wherever the fragment author put it.
DECODING_PARAMS_KEY = "decoding_params"
MAX_TOKENS_KEY = "max_tokens"
MAX_TOKENS_POLICY_KEY = "policy"
MAX_TOKENS_POLICY_VAR = "MAX_TOKENS_POLICIES"
DECODING_CONFIG_DIRS = ("configs/model", *CONFIG_DIRS)

# Stage-3 iteration 3 (2026-09-24): a stage3-deltas ``context_supply.<node>``
# route may declare an APPLICATION gate -- ``{"scenario_gate": {"policy":
# "<id>", "scenarios": [...]}}`` -- deciding, per ROW, whether that node takes
# the store's supply at all. The policy id must resolve in
# ``core.base.STAGE3_SUPPLY_GATE_POLICIES`` like every other component id a
# config declares (``rails/knowledge_provider.py`` registers it beside the
# delta provider ids).
#
# Matched by PATH rather than by bare key name, for exactly the reason
# DECODING_PARAMS_KEY above is: the key inside the gate object is spelled
# ``policy``, which at top level already means an arm program's own
# ``POLICIES``/``AGENT_CONTROLLERS`` id, so adding ``policy`` to
# NESTED_ID_KEYS would check every ``"policy": "fixed"`` in the tree against
# the wrong registry. The CONTAINER key, ``scenario_gate``, is unambiguous,
# and the gate lives per node under ``knowledge_stores.<store>.context_supply
# .<node>`` -- a path whose middle segments are store and node NAMES, so the
# container is found at any depth rather than by a hard-coded path.
SCENARIO_GATE_KEY = "scenario_gate"
SCENARIO_GATE_POLICY_KEY = "policy"
SCENARIO_GATE_POLICY_VAR = "STAGE3_SUPPLY_GATE_POLICIES"

# --- WAVE W3 (tool catalog, 2026-09-08) ------------------------------------
# Every ``tools`` LIST in ``configs/`` names catalog ids and must resolve in
# ``rails.tools.TOOL_CATALOG`` (registered from TOOLS_MODULE above), exactly as
# every ``policy`` / ``evidence_source`` / ``scorers`` value must resolve in its
# own ``core.base`` registry. The toolkit table that carries these lists is
# ``configs/toolkit/task-toolkits-v1.json`` (task type -> role -> tools).
#
# LIST-shaped, deliberately, and for the same kind of reason the max_tokens rule
# above is matched by PATH rather than by bare key name: ``configs/knowledge/
# a2t-kc-a1/targets-*.json`` already carry a ``tools`` key whose value is an
# OBJECT of Audio2Tool function names with per-function notes. That is carrier
# PAYLOAD -- the 152-tool registry the task itself is about -- not a list of
# catalog ids, and turning it into an offender would be checking the wrong
# object. A ``tools`` list of catalog ids and a ``tools`` object of Audio2Tool
# function names are two different things that happen to share a spelling.
#
# The scan covers ALL of ``configs/`` at any depth, not just CONFIG_DIRS: a
# toolkit table is not a baseline or an experiment fragment and lives in its own
# directory.
TOOL_LIST_KEY = "tools"
TOOL_REGISTRY_VAR = "TOOL_CATALOG"
TOOL_CONFIG_ROOT = "configs"
# --- end WAVE W3 -----------------------------------------------------------

ALL_REGISTRY_VARS = (
    {var for vars_ in TOP_LEVEL_STRING_KEYS.values() for var in vars_}
    | {TOP_LEVEL_LIST_KEY[1]}
    | set(NESTED_ID_KEYS.values())
    | set(NESTED_LIST_ID_KEYS.values())
    | {MAX_TOKENS_POLICY_VAR}
    | {SCENARIO_GATE_POLICY_VAR}
    | {TOOL_REGISTRY_VAR}  # WAVE W3
)

RATCHETED_RULES = (
    "probe_modules",
    "adapter_subclasses_outside_adapters",
    "controller_classes_outside_controllers",
    "launcher_dirs",
    "unregistered_config_values",
)
BASELINE_SCHEMA = "engineering-base-baseline-v1"

_STRING_LITERAL = r'(?:"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')'
_REGISTER_CALL_RE = re.compile(
    rf"\b(?P<var>[A-Z][A-Z0-9_]*)\.register\(\s*(?P<arg>{_STRING_LITERAL}|[A-Za-z_][A-Za-z0-9_]*)"
)
_CONST_ASSIGN_RE = re.compile(
    rf"^(?P<name>[A-Z][A-Z0-9_]*)\s*(?::\s*[^=\n]+)?=\s*(?P<val>{_STRING_LITERAL})\s*$",
    re.MULTILINE,
)


class EngineeringBaseError(RuntimeError):
    """The check itself cannot run: bad baseline, unreadable file, git unavailable."""


# ---------------------------------------------------------------------------
# Tree readers: "live" (working tree, default) and "committed" (git HEAD,
# --write-baseline only). Both expose the same surface so every rule below
# is written once and works against either.
# ---------------------------------------------------------------------------


class LiveTreeReader:
    """Reads the working tree on disk exactly as it sits -- dirty or not."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def list_files(self, prefix: str = "") -> list[str]:
        base = self.root / prefix if prefix else self.root
        if not base.exists():
            return []
        out = []
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(self.root).as_posix()
            if "__pycache__" in rel.split("/") or rel.startswith(".git/"):
                continue
            out.append(rel)
        return sorted(out)

    def read_text(self, relpath: str) -> str:
        try:
            return (self.root / relpath).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise EngineeringBaseError(f"cannot read {relpath}: {exc}") from exc

    def file_exists(self, relpath: str) -> bool:
        return (self.root / relpath).is_file()

    def find_dirs_named(self, name: str, under: str) -> list[str]:
        base = self.root / under
        if not base.exists():
            return []
        out = []
        for path in base.rglob(name):
            if path.is_dir():
                out.append(path.relative_to(self.root).as_posix())
        return sorted(out)


class CommittedTreeReader:
    """Reads file lists/contents from the committed HEAD tree via git, never
    the working tree -- so concurrent uncommitted edits from other agents
    cannot leak into a freshly captured baseline."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._commit: str | None = None
        self._all_files: list[str] | None = None

    def _git(self, args: Sequence[str]) -> bytes:
        try:
            completed = subprocess.run(
                ["git", "-C", str(self.root), *args],
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise EngineeringBaseError(f"git is unavailable: {exc}") from exc
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip()
            raise EngineeringBaseError(f"git {' '.join(args)} failed: {detail}")
        return completed.stdout

    def commit_hash(self) -> str:
        if self._commit is None:
            self._commit = self._git(["rev-parse", "HEAD"]).decode("ascii").strip()
        return self._commit

    def _all_tracked(self) -> list[str]:
        if self._all_files is None:
            raw = self._git(["ls-tree", "-r", "--name-only", "-z", "HEAD"])
            self._all_files = sorted(p for p in raw.decode("utf-8").split("\0") if p)
        return self._all_files

    def list_files(self, prefix: str = "") -> list[str]:
        files = self._all_tracked()
        if not prefix:
            return list(files)
        pfx = prefix.rstrip("/") + "/"
        return [f for f in files if f == prefix or f.startswith(pfx)]

    def read_text(self, relpath: str) -> str:
        raw = self._git(["show", f"HEAD:{relpath}"])
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EngineeringBaseError(
                f"non-UTF-8 committed content at HEAD:{relpath}: {exc}"
            ) from exc

    def file_exists(self, relpath: str) -> bool:
        return relpath in self._all_tracked()

    def find_dirs_named(self, name: str, under: str) -> list[str]:
        out = set()
        for f in self.list_files(prefix=under):
            parts = f.split("/")
            for i, part in enumerate(parts[:-1]):
                if part == name:
                    out.add("/".join(parts[: i + 1]))
        return sorted(out)


TreeReader = LiveTreeReader | CommittedTreeReader


# ---------------------------------------------------------------------------
# Registered-name resolution (no package import).
# ---------------------------------------------------------------------------


def _read_family_registrations(
    text: str, relpath: str, registered: dict[str, set[str]]
) -> set[tuple[str, str]]:
    """Apply :data:`FAMILY_ID_TUPLES` to one canonical file: add every
    literal member of each declared family tuple to its registry's name set,
    and return the ``(loop variable, registry variable)`` pairs of the loops
    ``for <var> in <TUPLE>:`` that iterate such a tuple -- the only bare
    identifiers a family registration may hand to ``register``."""

    families = {
        name: var for name, (source, var) in FAMILY_ID_TUPLES.items() if source == relpath
    }
    if not families:
        return set()
    try:
        tree = ast.parse(text, filename=relpath)
    except SyntaxError as exc:
        raise EngineeringBaseError(f"cannot parse {relpath}: {exc}") from exc
    found: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if not isinstance(target, ast.Name) or target.id not in families:
            continue
        if not isinstance(value, ast.Tuple) or not all(
            isinstance(element, ast.Constant) and isinstance(element.value, str)
            for element in value.elts
        ):
            raise EngineeringBaseError(
                f"family tuple {target.id} in {relpath} must be a tuple of string literals"
            )
        registered[families[target.id]].update(element.value for element in value.elts)
        found.add(target.id)
    missing = sorted(set(families) - found)
    if missing:
        raise EngineeringBaseError(
            f"declared family tuple(s) {missing} not found at module level in {relpath}"
        )
    loop_vars: set[tuple[str, str]] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.For)
            and isinstance(node.iter, ast.Name)
            and node.iter.id in families
            and isinstance(node.target, ast.Name)
        ):
            loop_vars.add((node.target.id, families[node.iter.id]))
    return loop_vars


def build_registered_names(reader: TreeReader) -> dict[str, set[str]]:
    """Registered name sets for the ``core.base`` registries this check
    cares about, resolved via regex over the canonical population
    files (:data:`CANONICAL_REGISTRY_FILES`) -- never by importing the
    package.

    Pass 1 scans only the canonical files for ``<REGISTRY_VAR>.register(...)``
    calls; a literal string argument is used directly, a bare-identifier
    argument (e.g. ``OBS_LOOP_POLICY_NAME``, defined in
    ``reproduction/obs_loop.py`` rather than in ``core/policies.py`` itself)
    is queued. Pass 2 searches every ``src/`` module, but ONLY for the small,
    exact set of identifiers pass 1 actually needs -- never a blanket map of
    every module-level ALL-CAPS constant in the tree (which collides: many
    unrelated modules define their own same-shaped ``SOME_ID = "..."``
    constant, e.g. ``EXPOSURE_ROW_ID``, for unrelated purposes).
    """

    registered: dict[str, set[str]] = {name: set() for name in ALL_REGISTRY_VARS}
    needed: dict[str, list[tuple[str, str]]] = {}  # identifier -> [(var, source_relpath)]
    for relpath in CANONICAL_REGISTRY_FILES:
        if not reader.file_exists(relpath):
            # canonical file absent from this tree snapshot; nothing to
            # resolve from it (e.g. a synthetic test repo).
            continue
        text = reader.read_text(relpath)
        family_loop_vars = _read_family_registrations(text, relpath, registered)
        for match in _REGISTER_CALL_RE.finditer(text):
            var = match.group("var")
            if var not in ALL_REGISTRY_VARS:
                continue
            arg = match.group("arg")
            if arg[0] in "\"'":
                registered[var].add(ast.literal_eval(arg))
            elif (arg, var) in family_loop_vars:
                continue
            else:
                needed.setdefault(arg, []).append((var, relpath))

    if needed:
        for py_relpath in reader.list_files(prefix=PACKAGE_ROOT):
            if not py_relpath.endswith(".py"):
                continue
            text = reader.read_text(py_relpath)
            for match in _CONST_ASSIGN_RE.finditer(text):
                name = match.group("name")
                if name not in needed:
                    continue
                value = ast.literal_eval(match.group("val"))
                for var, source_relpath in needed[name]:
                    registered[var].add(value)
                del needed[name]
            if not needed:
                break

    if needed:
        unresolved = ", ".join(
            f"{var}.register({name}, ...) in {source}"
            for name, entries in needed.items()
            for var, source in entries
        )
        raise EngineeringBaseError(
            f"cannot resolve registration identifier(s) to a literal string: {unresolved}"
        )
    return registered


# ---------------------------------------------------------------------------
# AST helpers for R2 / R3.
# ---------------------------------------------------------------------------


def _parse(reader: TreeReader, relpath: str) -> ast.Module:
    source = reader.read_text(relpath)
    try:
        return ast.parse(source, filename=relpath)
    except SyntaxError as exc:
        raise EngineeringBaseError(f"cannot parse {relpath}: {exc}") from exc


def _classes_with_base(tree: ast.Module, base_name: str) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == base_name:
                names.append(node.name)
                break
            if isinstance(base, ast.Attribute) and base.attr == base_name:
                names.append(node.name)
                break
    return names


def _classes_with_methods(tree: ast.Module, method_names: set[str]) -> list[str]:
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        defined = {
            item.name
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if method_names <= defined:
            names.append(node.name)
    return names


def _launcher_py_candidates(reader: TreeReader) -> list[str]:
    """Every ``.py`` file that lives inside a directory literally named
    ``launcher`` anywhere under ``docs/checks/``."""

    out = []
    for f in reader.list_files(prefix=DOCS_CHECKS_DIR):
        if not f.endswith(".py"):
            continue
        if LAUNCHER_DIR_NAME in f.split("/")[:-1]:
            out.append(f)
    return out


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def rule_probe_modules(reader: TreeReader) -> list[str]:
    prefix = PROBES_DIR + "/"
    offenders = []
    for relpath in reader.list_files(prefix=PROBES_DIR):
        if not relpath.startswith(prefix) or not relpath.endswith(".py"):
            continue
        if relpath.rsplit("/", 1)[-1] == "__init__.py":
            continue
        offenders.append(relpath)
    return sorted(offenders)



def rule_adapter_subclasses_outside_adapters(reader: TreeReader) -> list[str]:
    adapters_prefix = ADAPTERS_DIR + "/"
    candidates = [
        f for f in reader.list_files(prefix=PACKAGE_ROOT) if f.endswith(".py")
    ] + _launcher_py_candidates(reader)
    offenders = []
    for relpath in sorted(set(candidates)):
        if relpath.startswith(adapters_prefix):
            continue
        tree = _parse(reader, relpath)
        for cls_name in _classes_with_base(tree, "TaskAdapter"):
            offenders.append(f"{relpath}::{cls_name}")
    return sorted(offenders)


def rule_controller_classes_outside_controllers(reader: TreeReader) -> list[str]:
    excluded = {CONTROLLERS_MODULE, KB_POLICY_MODULE}
    candidates = [
        f for f in reader.list_files(prefix=PACKAGE_ROOT) if f.endswith(".py")
    ] + _launcher_py_candidates(reader)
    offenders = []
    for relpath in sorted(set(candidates)):
        if relpath in excluded:
            continue
        tree = _parse(reader, relpath)
        for cls_name in _classes_with_methods(tree, {"initial_contact", "advance"}):
            offenders.append(f"{relpath}::{cls_name}")
    return sorted(offenders)


def rule_launcher_dirs(reader: TreeReader) -> list[str]:
    return sorted(reader.find_dirs_named(LAUNCHER_DIR_NAME, under=DOCS_CHECKS_DIR))


def _walk_nested_id_keys(node: object, path_prefix: str = ""):
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path_prefix}.{key}" if path_prefix else key
            if key in NESTED_ID_KEYS:
                yield here, key, value
            yield from _walk_nested_id_keys(value, here)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk_nested_id_keys(item, f"{path_prefix}[{index}]")


def _walk_scenario_gates(node: object, path_prefix: str = ""):
    """``(dotted path, gate object)`` for every :data:`SCENARIO_GATE_KEY`
    container at any depth -- the path counterpart of
    :func:`_walk_nested_id_keys`, keyed on the CONTAINER rather than on the
    ambiguous ``policy`` key inside it."""

    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path_prefix}.{key}" if path_prefix else key
            if key == SCENARIO_GATE_KEY and isinstance(value, dict):
                yield here, value
            yield from _walk_scenario_gates(value, here)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk_scenario_gates(item, f"{path_prefix}[{index}]")


def _walk_nested_list_id_keys(node: object, path_prefix: str = ""):
    """``(dotted path, key, value)`` for every :data:`NESTED_LIST_ID_KEYS` key
    at any depth -- the list counterpart of :func:`_walk_nested_id_keys`."""

    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path_prefix}.{key}" if path_prefix else key
            if key in NESTED_LIST_ID_KEYS:
                yield here, key, value
            yield from _walk_nested_list_id_keys(value, here)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk_nested_list_id_keys(item, f"{path_prefix}[{index}]")


# --- WAVE W3 (tool catalog, 2026-09-08) ------------------------------------


def _walk_tool_lists(node: object, path_prefix: str = ""):
    """Yield ``(dotted path, list)`` for every ``tools`` LIST at any depth
    (see the WAVE W3 constants block for why lists only)."""

    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{path_prefix}.{key}" if path_prefix else key
            if key == TOOL_LIST_KEY and isinstance(value, list):
                yield here, value
            yield from _walk_tool_lists(value, here)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk_tool_lists(item, f"{path_prefix}[{index}]")


def rule_unregistered_tool_ids(
    reader: TreeReader, registered: Mapping[str, set[str]]
) -> tuple[list[str], list[str]]:
    """Every ``tools`` list value under ``configs/`` must resolve in
    ``rails.tools.TOOL_CATALOG``. Returns (sorted offenders, sorted keys seen)."""

    offenders: list[str] = []
    keys_found: set[str] = set()
    known = registered[TOOL_REGISTRY_VAR]
    for relpath in reader.list_files(prefix=TOOL_CONFIG_ROOT):
        if not relpath.endswith(".json"):
            continue
        try:
            doc = json.loads(reader.read_text(relpath))
        except json.JSONDecodeError as exc:
            raise EngineeringBaseError(f"cannot parse JSON {relpath}: {exc}") from exc
        for dotted_path, values in _walk_tool_lists(doc):
            keys_found.add(TOOL_LIST_KEY)
            for index, entry in enumerate(values):
                if not isinstance(entry, str) or entry not in known:
                    offenders.append(f"{relpath}::{dotted_path}[{index}]={entry}")
    return sorted(offenders), sorted(keys_found)


# --- end WAVE W3 -----------------------------------------------------------


def rule_unregistered_config_values(
    reader: TreeReader, registered: Mapping[str, set[str]]
) -> tuple[list[str], list[str]]:
    """Returns (sorted offenders, sorted key names actually observed)."""

    offenders: list[str] = []
    keys_found: set[str] = set()
    scorers_key, scorers_var = TOP_LEVEL_LIST_KEY
    for config_dir in CONFIG_DIRS:
        depth = config_dir.count("/") + 1
        for relpath in reader.list_files(prefix=config_dir):
            if not relpath.endswith(".json") or relpath.count("/") != depth:
                continue
            try:
                doc = json.loads(reader.read_text(relpath))
            except json.JSONDecodeError as exc:
                raise EngineeringBaseError(f"cannot parse JSON {relpath}: {exc}") from exc
            if not isinstance(doc, dict):
                continue

            for key, variables in TOP_LEVEL_STRING_KEYS.items():
                value = doc.get(key)
                if not isinstance(value, str):
                    continue
                keys_found.add(key)
                if not any(value in registered[var] for var in variables):
                    offenders.append(f"{relpath}::{key}={value}")

            scorers_value = doc.get(scorers_key)
            if isinstance(scorers_value, list):
                keys_found.add(scorers_key)
                for index, entry in enumerate(scorers_value):
                    if isinstance(entry, str) and entry not in registered[scorers_var]:
                        offenders.append(f"{relpath}::{scorers_key}[{index}]={entry}")

            for dotted_path, key, value in _walk_nested_id_keys(doc):
                if not isinstance(value, str):
                    continue
                keys_found.add(key)
                var = NESTED_ID_KEYS[key]
                if value not in registered[var]:
                    offenders.append(f"{relpath}::{dotted_path}={value}")

            for dotted_path, key, value in _walk_nested_list_id_keys(doc):
                if not isinstance(value, list):
                    continue
                keys_found.add(key)
                var = NESTED_LIST_ID_KEYS[key]
                for index, entry in enumerate(value):
                    if isinstance(entry, str) and entry not in registered[var]:
                        offenders.append(f"{relpath}::{dotted_path}[{index}]={entry}")

            for dotted_path, gate in _walk_scenario_gates(doc):
                dotted = f"{dotted_path}.{SCENARIO_GATE_POLICY_KEY}"
                keys_found.add(f"{SCENARIO_GATE_KEY}.{SCENARIO_GATE_POLICY_KEY}")
                value = gate.get(SCENARIO_GATE_POLICY_KEY)
                if (
                    not isinstance(value, str)
                    or value not in registered[SCENARIO_GATE_POLICY_VAR]
                ):
                    offenders.append(f"{relpath}::{dotted}={value}")

    # The per-sample max_tokens rule, matched by PATH (see
    # DECODING_PARAMS_KEY's own comment for why not by bare key name).
    for config_dir in DECODING_CONFIG_DIRS:
        depth = config_dir.count("/") + 1
        for relpath in reader.list_files(prefix=config_dir):
            if not relpath.endswith(".json") or relpath.count("/") != depth:
                continue
            try:
                doc = json.loads(reader.read_text(relpath))
            except json.JSONDecodeError as exc:
                raise EngineeringBaseError(f"cannot parse JSON {relpath}: {exc}") from exc
            if not isinstance(doc, dict):
                continue
            decoding = doc.get(DECODING_PARAMS_KEY)
            if not isinstance(decoding, dict):
                continue
            rule = decoding.get(MAX_TOKENS_KEY)
            if not isinstance(rule, dict):
                continue
            dotted = f"{DECODING_PARAMS_KEY}.{MAX_TOKENS_KEY}.{MAX_TOKENS_POLICY_KEY}"
            keys_found.add(dotted)
            value = rule.get(MAX_TOKENS_POLICY_KEY)
            if not isinstance(value, str) or value not in registered[MAX_TOKENS_POLICY_VAR]:
                offenders.append(f"{relpath}::{dotted}={value}")

    return sorted(offenders), sorted(keys_found)


def rule_adapter_line_budget(reader: TreeReader) -> tuple[list[str], dict[str, int]]:
    prefix = ADAPTERS_DIR + "/"
    line_counts: dict[str, int] = {}
    offenders: list[str] = []
    for relpath in reader.list_files(prefix=ADAPTERS_DIR):
        if not relpath.startswith(prefix) or not relpath.endswith(".py"):
            continue
        if relpath.rsplit("/", 1)[-1] == "__init__.py":
            continue
        count = len(reader.read_text(relpath).splitlines())
        line_counts[relpath] = count
        if count > ADAPTER_LINE_BUDGET:
            offenders.append(f"{relpath}: {count} lines (limit {ADAPTER_LINE_BUDGET})")
    return sorted(offenders), line_counts


# ---------------------------------------------------------------------------
# Evaluation + baseline comparison
# ---------------------------------------------------------------------------


def evaluate(reader: TreeReader, baseline_doc: Mapping[str, object] | None) -> dict:
    registered = build_registered_names(reader)
    config_offenders, config_keys_found = rule_unregistered_config_values(reader, registered)
    # --- WAVE W3 (tool catalog, 2026-09-08): the same rule, one more registry.
    tool_offenders, tool_keys_found = rule_unregistered_tool_ids(reader, registered)
    config_offenders = sorted(set(config_offenders) | set(tool_offenders))
    config_keys_found = sorted(set(config_keys_found) | set(tool_keys_found))
    # --- end WAVE W3 -------------------------------------------------------
    adapter_offenders, adapter_line_counts = rule_adapter_line_budget(reader)

    raw = {
        "probe_modules": rule_probe_modules(reader),
        "adapter_subclasses_outside_adapters": rule_adapter_subclasses_outside_adapters(reader),
        "controller_classes_outside_controllers": rule_controller_classes_outside_controllers(
            reader
        ),
        "launcher_dirs": rule_launcher_dirs(reader),
        "unregistered_config_values": config_offenders,
    }

    baseline_rules = {}
    if baseline_doc:
        baseline_rules = baseline_doc.get("rules", {}) or {}

    rules_report: dict[str, dict] = {}
    new_offenders: list[str] = []
    obsolete_entries: list[str] = []
    for name in RATCHETED_RULES:
        offenders = raw[name]
        baseline_set = set(baseline_rules.get(name, []))
        offender_set = set(offenders)
        new = sorted(offender_set - baseline_set)
        obsolete = sorted(baseline_set - offender_set)
        rules_report[name] = {
            "offenders": offenders,
            "new_offenders": new,
            "obsolete_baseline_entries": obsolete,
            "ratcheted": True,
        }
        new_offenders.extend(f"{name}: {item}" for item in new)
        obsolete_entries.extend(f"{name}: {item}" for item in obsolete)

    rules_report["adapter_line_budget"] = {
        "offenders": adapter_offenders,
        "new_offenders": adapter_offenders,
        "obsolete_baseline_entries": [],
        "ratcheted": False,
        "line_counts": adapter_line_counts,
    }
    new_offenders.extend(f"adapter_line_budget: {item}" for item in adapter_offenders)

    return {
        "registered_names": {name: sorted(values) for name, values in registered.items()},
        "config_keys_found": config_keys_found,
        "rules": rules_report,
        "new_offenders": new_offenders,
        "obsolete_baseline_entries": obsolete_entries,
        "passed": not new_offenders,
    }


def build_baseline_document(reader: CommittedTreeReader) -> dict:
    data = evaluate(reader, baseline_doc=None)
    return {
        "schema": BASELINE_SCHEMA,
        "captured_at_commit": reader.commit_hash(),
        "rules": {
            name: info["offenders"]
            for name, info in data["rules"].items()
            if name in RATCHETED_RULES
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_baseline_path(repo_root: Path) -> Path:
    return repo_root / "scripts" / "checks" / "engineering_base_baseline.json"


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="study repository root (default: two levels above this script)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="baseline JSON path (default: <repo-root>/scripts/checks/engineering_base_baseline.json)",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="regenerate the baseline from the COMMITTED HEAD tree (via git) and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print only the machine-readable report to stdout",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    baseline_path = (
        args.baseline.resolve() if args.baseline else _default_baseline_path(repo_root)
    )

    try:
        if args.write_baseline:
            reader = CommittedTreeReader(repo_root)
            baseline_doc = build_baseline_document(reader)
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            baseline_path.write_text(
                json.dumps(baseline_doc, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            if args.json:
                print(json.dumps(baseline_doc, indent=2, sort_keys=True))
            else:
                print(
                    "engineering base check: wrote baseline "
                    f"{baseline_path} at commit {baseline_doc['captured_at_commit']}"
                )
                for name in RATCHETED_RULES:
                    print(f"  {name}: {len(baseline_doc['rules'][name])} offender(s)")
            return 0

        reader = LiveTreeReader(repo_root)
        baseline_doc: dict = {"rules": {}}
        if baseline_path.exists():
            try:
                baseline_doc = json.loads(baseline_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise EngineeringBaseError(f"cannot load baseline {baseline_path}: {exc}") from exc

        data = evaluate(reader, baseline_doc)
    except EngineeringBaseError as exc:
        print(f"engineering base check: FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for warning in data["obsolete_baseline_entries"]:
        print(f"engineering base check: WARN: obsolete baseline entry: {warning}")

    if data["new_offenders"]:
        for item in data["new_offenders"]:
            print(f"engineering base check: FAIL offender: {item}")
        print(f"engineering base check: FAIL ({len(data['new_offenders'])} new offender(s))")
        return 1

    print("engineering base check: PASS")
    return 0

def _python_module_for_path(relpath: str) -> str:
    parts = relpath[:-3].replace("/", ".").split(".")
    if parts[-1] == "__init__":
        parts.pop()
    package_parts = PACKAGE_ROOT.split("/")[1:]
    if relpath.startswith(PACKAGE_ROOT + "/"):
        return ".".join(package_parts + parts[len(package_parts) + 1:])
    return ".".join(parts)


def _resolve_import_module(module: str, current: str, level: int) -> str:
    if not level:
        return module
    package = current.split(".")[:-1]
    if level > 1:
        package = package[: -(level - 1)] if level - 1 <= len(package) else []
    return ".".join([*package, module] if module else package)


def _class_candidates(reader: TreeReader) -> list[str]:
    prefixes = (PACKAGE_ROOT, "scripts", "flights")
    return sorted({path for prefix in prefixes for path in reader.list_files(prefix=prefix) if path.endswith(".py")} | set(_launcher_py_candidates(reader)))


def find_subclasses(reader: TreeReader, base_module: str, base_name: str, candidates: Sequence[str] | None = None) -> list[str]:
    """Return class definitions transitively derived from an imported base."""
    paths = list(candidates) if candidates is not None else _class_candidates(reader)
    classes: dict[str, ast.ClassDef] = {}
    imports: dict[str, dict[str, str]] = {}
    for relpath in paths:
        tree = _parse(reader, relpath)
        module = _python_module_for_path(relpath)
        aliases: dict[str, str] = {}
        for node in tree.body:
            if isinstance(node, ast.Import):
                for item in node.names:
                    aliases[item.asname or item.name.split(".")[0]] = item.name
            elif isinstance(node, ast.ImportFrom):
                source = _resolve_import_module(node.module or "", module, node.level)
                for item in node.names:
                    if item.name != "*":
                        aliases[item.asname or item.name] = ".".join(part for part in (source, item.name) if part)
        imports[module] = aliases
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes[module + "." + node.name] = node

    def resolve(expr: ast.expr, module: str) -> str | None:
        aliases = imports[module]
        if isinstance(expr, ast.Name):
            return aliases.get(expr.id, module + "." + expr.id)
        if isinstance(expr, ast.Attribute):
            parent = resolve(expr.value, module)
            return parent + "." + expr.attr if parent else None
        return None

    edges: dict[str, set[str]] = {}
    for qname, node in classes.items():
        module = qname.rsplit(".", 1)[0]
        edges[qname] = {base for expr in node.bases if (base := resolve(expr, module)) is not None}

    target = base_module + "." + base_name
    derived: set[str] = set()
    changed = True
    while changed:
        changed = False
        for qname, bases in edges.items():
            if qname not in derived and (target in bases or bases & derived):
                derived.add(qname)
                changed = True
    results = []
    for relpath in paths:
        module = _python_module_for_path(relpath)
        for qname in derived:
            if qname.rsplit(".", 1)[0] == module:
                results.append(relpath + "::" + qname.rsplit(".", 1)[1])
    return sorted(set(results))


if __name__ == "__main__":
    sys.exit(main())
