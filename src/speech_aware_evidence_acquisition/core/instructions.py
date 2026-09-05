"""Task-instruction resolution (P1 scaffold): literal, or frozen template + fill.

Every pre-existing baseline fragment carries a literal ``task_instruction``
and behaves byte-identically through :func:`resolve_task_instruction`. The
Audio2Tool direct-prompt baseline instead needs the FULL tool registry inside
its instruction — content that lives under ``SPEECHRL_DATA_DIR`` (never
committed) and is far too large for a config fragment. Such a baseline
supplies:

- ``task_instruction_template``: a path under ``configs/`` (e.g.
  ``probes/r1_audio2tool_direct.txt`` — the frozen, protocol-manifest-hashed
  template; editing it after its probe ran is forbidden, see
  ``configs/probes/README.md``), and
- ``task_instruction_fill``: the name of a registered
  ``core.base.INSTRUCTION_FILLS`` entry — a callable ``(lock, root) -> str``
  rendering pinned carrier data deterministically.

v1 supports exactly ONE placeholder token, ``{tool_schemas}``, replaced by
plain string substitution (never ``str.format`` — the templates legitimately
contain JSON braces). Fail-closed everywhere: both keys together, neither
key, a template outside ``configs/``, a missing template, a template without
the placeholder, an unknown fill name, or an empty fill result all refuse
before any budget is spent (``core.driver.run.run_experiment`` resolves the
instruction BEFORE the adapter opens its attempt).

Identity: the config hash pins the template PATH and fill NAME;
``configs/probes/manifest.json`` pins the template BYTES; the umbrella lock
pins the carrier data the fill reads. Together the rendered instruction is
reproducible from committed identity plus locked assets.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Mapping

from ..data.audio2tool import render_tool_schemas
from ..data.audio2tool_tools import render_registry_compact, render_registry_grouped
from ..data.slurp import render_slurp_closed_label_inventory
from .base import INSTRUCTION_FILLS, CoreError

TOOL_SCHEMAS_PLACEHOLDER = "{tool_schemas}"

_TEMPLATE_RELPATH_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*")

INSTRUCTION_FILLS.register("audio2tool-tool-schemas", render_tool_schemas)
# The pinned Audio2Tool release's own `format_tools_compact` rendering
# ("- {signature}: {description}", sorted by tool_name), for the cell that
# mirrors the published protocol string-for-string. It is a SECOND fill, not
# a replacement: every existing cell keeps naming the JSON-per-line fill
# above and its rendered instruction is byte-identical to before.
INSTRUCTION_FILLS.register("audio2tool-registry-compact", render_registry_compact)
# The pinned Audio2Tool release's SECOND registry renderer,
# `format_tools_for_prompt(tools, include_constraints=False)`: the same 152
# rows organized by the registry's own `domain` column (sorted domain groups
# under an upper-cased header, each tool a "### {signature}" line followed by
# its description), constraints withheld. A2T-ORG-1's single factor. Fourth
# fill, same `(lock, root) -> str` shape; no existing cell names it, so every
# previously rendered instruction is byte-identical to before.
INSTRUCTION_FILLS.register("audio2tool-registry-grouped", render_registry_grouped)
# SLURP's closed label inventory (2026-09-05): the TRAIN-only ontology task
# contract the sealed DEV-1000 M0 arm already sent, plus the compact closed
# inventory that names the legal scenario/action pairs and the entity types.
# Third fill, same `(lock, root) -> str` shape; no existing cell names it, so
# every previously rendered instruction is byte-identical to before.
INSTRUCTION_FILLS.register("slurp-label-inventory", render_slurp_closed_label_inventory)


def resolve_task_instruction(
    values: Mapping[str, object], repo_root: Path, lock: Mapping[str, object], root: Path
) -> str:
    """The run's single task instruction, resolved fail-closed (module docstring)."""

    literal = values.get("task_instruction")
    template_rel = values.get("task_instruction_template")
    if literal is not None and template_rel is not None:
        raise CoreError(
            "baseline config supplies both task_instruction and "
            "task_instruction_template; exactly one is allowed"
        )
    if literal is not None:
        return str(literal)
    if template_rel is None:
        raise CoreError(
            "baseline config supplies neither task_instruction nor "
            "task_instruction_template; one is required"
        )

    if not isinstance(template_rel, str) or not _TEMPLATE_RELPATH_PATTERN.fullmatch(
        template_rel
    ):
        raise CoreError(
            f"task_instruction_template {template_rel!r} is not a plain relative path "
            "under configs/ (no absolute paths, no '..', no backslashes)"
        )
    template_path = Path(repo_root) / "configs" / template_rel
    if not template_path.is_file():
        raise CoreError(f"task instruction template missing: {template_path}")
    try:
        template_text = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CoreError(
            f"cannot read task instruction template {template_path}: {error}"
        ) from error

    fill_name = values.get("task_instruction_fill")
    if not isinstance(fill_name, str) or not fill_name.strip():
        raise CoreError(
            "task_instruction_template requires task_instruction_fill naming a "
            f"registered instruction fill; registered: {INSTRUCTION_FILLS.names()}"
        )
    if TOOL_SCHEMAS_PLACEHOLDER not in template_text:
        raise CoreError(
            f"task instruction template {template_path} carries no "
            f"{TOOL_SCHEMAS_PLACEHOLDER!r} placeholder for fill {fill_name!r}; an "
            "unfilled or unfillable template must never reach the model"
        )
    fill: Callable[[Mapping[str, object], Path], str] = INSTRUCTION_FILLS.resolve(fill_name)
    fill_text = fill(lock, root)
    if not isinstance(fill_text, str) or not fill_text.strip():
        raise CoreError(f"instruction fill {fill_name!r} rendered an empty result")
    rendered = template_text.replace(TOOL_SCHEMAS_PLACEHOLDER, fill_text)
    if TOOL_SCHEMAS_PLACEHOLDER in rendered:
        raise CoreError(
            f"task instruction still contains {TOOL_SCHEMAS_PLACEHOLDER!r} after "
            "rendering; refusing to send an unfilled template"
        )
    return rendered


def resolve_active_task_instruction(
    values: Mapping[str, object], repo_root: Path, lock: Mapping[str, object], root: Path
) -> str | None:
    """The wire instruction a ``core.flight.FlightRuntime`` cell sends, or
    ``None`` to fall through to the adapter's own hard-coded text.

    Three sources, in the order a baseline fragment may declare them:

    * a literal ``task_instruction``;
    * ``task_instruction_template`` + ``task_instruction_fill`` **with
      ``task_instruction_template_active: true``**, resolved through
      :func:`resolve_task_instruction`;
    * neither -- the adapter's own instruction.

    Why the opt-in third key rather than honouring the template pair
    unconditionally. Several sealed cells (``a2t-direct-calibration``,
    ``a2t-direct-packets``) ALREADY carry a template pair that their flight
    never read: they went on the wire with the adapter's hard-coded text,
    which is what their prompt-fit receipts record and what their
    ``protocol_hash`` was computed over. Honouring the pair unconditionally
    would silently rewrite what those sealed cells mean on any re-run. The
    flag lets a NEW fragment say plainly that its template is the wire text
    while every existing fragment stays byte-identical.

    This is the shared form of the resolver ``scripts/flights/
    run_calibration_cell.py`` introduced locally; a flight script calls it
    and hands the result to its roster-bound adapter, because
    ``FlightRuntime`` reads the system message from
    ``adapter.instruction(sample)`` and has no config seam of its own.
    """

    literal = values.get("task_instruction")
    if literal is not None:
        if not isinstance(literal, str) or not literal:
            raise CoreError("baseline task_instruction must be a non-empty string")
        if values.get("task_instruction_template_active"):
            raise CoreError(
                "baseline declares both a literal task_instruction and an active "
                "task_instruction_template; exactly one may be the wire text"
            )
        return literal
    if not values.get("task_instruction_template_active"):
        return None
    if values.get("task_instruction_template") is None:
        raise CoreError(
            "task_instruction_template_active is set but no task_instruction_template "
            "is declared"
        )
    return resolve_task_instruction(values, repo_root, lock, root)
