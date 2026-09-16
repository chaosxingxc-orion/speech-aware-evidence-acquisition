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
  rendering pinned carrier data deterministically, and
- optionally ``task_instruction_fill_params``: a JSON object of NAMED
  arguments for a fill whose signature declares them. The resolver reads the
  fill's own signature and passes exactly those names (plus an injected
  ``repo_root``); it never splats the object. A fill that declares no
  parameter refuses params outright, so every pre-existing fragment — none
  of which carries the key — resolves byte-identically. The first
  parameterized fill is ``evolved-artifact-v1``
  (:func:`render_evolved_registry`), whose ``artifact_relpath`` /
  ``artifact_sha256`` pin the evolution loop's hash-verified override
  artifact under ``configs/``.

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

import hashlib
import inspect
import json
import re
from pathlib import Path
from typing import Callable, Mapping

from ..data.audio2tool import load_tool_registry, render_tool_schemas
from ..data.audio2tool_tools import (
    render_registry_compact,
    render_registry_compact_rows,
    render_registry_grouped,
)
from ..data.slurp import (
    render_slurp_closed_label_inventory,
    render_slurp_closed_label_inventory_with_slot_schema,
)
from ..data.slurp_contract_cache import (
    SLURP_LABEL_INVENTORY_FILL,
    load_cached_slurp_label_inventory,
)
from .base import INSTRUCTION_FILLS, CoreError

TOOL_SCHEMAS_PLACEHOLDER = "{tool_schemas}"

_TEMPLATE_RELPATH_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*")

#: The name of the evolution loop's registered fill. ``rails.evolution``
#: writes exactly this string into every candidate baseline fragment it
#: emits (its own ``EVOLVED_FILL_NAME``); the two must agree, and a test
#: pins that they do.
EVOLVED_FILL_NAME = "evolved-artifact-v1"

#: Keyword arguments a fill never receives from ``task_instruction_fill_params``:
#: ``lock``/``root`` are the fill's own two positional arguments, and
#: ``repo_root`` is INJECTED by the resolver -- a config able to set it would
#: choose which tree the fill reads from, which is the one thing the
#: repo-root-relative artifact rule exists to prevent.
_RESERVED_FILL_PARAM_NAMES = frozenset({"lock", "root", "repo_root"})


def render_evolved_registry(
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    artifact_relpath: str,
    artifact_sha256: str,
) -> str:
    """The compact Audio2Tool registry with an EVOLVED ARTIFACT's description
    overrides applied -- the evolution loop's state ``A_r`` on the wire.

    ``rails.evolution.write_candidate_fragments`` writes two files per
    portfolio: the artifact itself (``{tool_name: description}`` as canonical
    JSON, under ``configs/``) and a baseline fragment naming this fill plus a
    ``task_instruction_fill_params`` object carrying ``artifact_relpath``
    (relative to the REPOSITORY ROOT) and ``artifact_sha256`` (over the
    artifact file's bytes as written). This function closes that loop: it
    reads those bytes, re-hashes them, and renders the same 152-line block
    :func:`~..data.audio2tool_tools.render_registry_compact` renders, with
    only the description column of the named tools replaced.

    Identity, and why each refusal is fail-closed:

    * ``artifact_relpath`` must be a plain relative path UNDER ``configs/``
      (the same ``_TEMPLATE_RELPATH_PATTERN`` every template path already
      passes, plus the ``configs/`` prefix). An artifact outside the
      committed config surface would not be pinned by the fragment's config
      hash, so a round could be re-run against bytes nobody can recover.
    * the file's sha256 must equal ``artifact_sha256``. The config hash pins
      the PATH and the HASH; the hash pins the BYTES. An artifact edited
      after its fragment was emitted is refused rather than silently flown.
    * ``A_0`` -- an artifact with no overrides at all -- is refused. An empty
      override set renders the released registry, which is the sealed
      baseline's own fill; naming this one for it would make two arms that
      are byte-identical on the wire look like two mechanisms in the ledger.

    Everything else is delegated: the override RULE (one line per tool, same
    order, same signature half, fail-closed on an unknown tool name, an empty
    replacement, or a newline) is
    :func:`~..data.audio2tool_tools.render_registry_compact_rows`, unchanged.
    """

    if not isinstance(artifact_relpath, str) or not _TEMPLATE_RELPATH_PATTERN.fullmatch(
        artifact_relpath
    ):
        raise CoreError(
            f"evolved artifact_relpath {artifact_relpath!r} is not a plain relative "
            "path (no absolute paths, no '..', no backslashes)"
        )
    if not artifact_relpath.startswith("configs/"):
        raise CoreError(
            f"evolved artifact_relpath {artifact_relpath!r} is not under configs/; an "
            "evolved artifact must live on the committed config surface its fragment's "
            "config hash pins"
        )
    if not isinstance(artifact_sha256, str) or len(artifact_sha256) != 64:
        raise CoreError(
            "evolved artifact_sha256 must be a 64-character sha256 hex digest, got "
            f"{artifact_sha256!r}"
        )
    artifact_path = Path(repo_root) / artifact_relpath
    if not artifact_path.is_file():
        raise CoreError(f"evolved artifact missing: {artifact_path}")
    try:
        artifact_bytes = artifact_path.read_bytes()
    except OSError as error:
        raise CoreError(
            f"cannot read evolved artifact {artifact_path}: {error}"
        ) from error
    measured = hashlib.sha256(artifact_bytes).hexdigest()
    if measured != artifact_sha256:
        raise CoreError(
            f"evolved artifact {artifact_path} hashes to {measured}, not the configured "
            f"{artifact_sha256}"
        )
    try:
        overrides = json.loads(artifact_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CoreError(
            f"evolved artifact {artifact_path} is not UTF-8 JSON: {error}"
        ) from error
    if not isinstance(overrides, Mapping) or not overrides:
        raise CoreError(
            f"evolved artifact {artifact_path} must be a non-empty JSON object of "
            "tool_name -> description; an empty override set renders the released "
            "registry, which is the baseline fill's own output"
        )
    return render_registry_compact_rows(
        load_tool_registry(lock, root), description_overrides=overrides
    )


def _fill_parameter_shape(
    fill: Callable[..., str],
) -> tuple[frozenset[str], frozenset[str], bool]:
    """``(accepted_named, required_named, accepts_var_keyword)`` for a fill.

    ``accepted_named`` are the keyword-passable parameters BEYOND the two
    positional ones every fill takes (``lock``, ``root``); ``required_named``
    are those of them with no default; ``accepts_var_keyword`` is whether the
    fill declares ``**kwargs``, in which case it absorbs any named key -- how
    ``rails.phase_material``'s existing ``(lock, root, **params)`` fills
    already behave.

    A fill whose signature cannot be read at all counts as taking no
    parameters, so params against it are refused rather than splatted blind.
    """

    try:
        signature = inspect.signature(fill)
    except (TypeError, ValueError):
        return frozenset(), frozenset(), False
    accepted: set[str] = set()
    required: set[str] = set()
    var_keyword = False
    for index, (name, parameter) in enumerate(signature.parameters.items()):
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            var_keyword = True
            continue
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.POSITIONAL_ONLY,
        ):
            continue
        if index < 2 and parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD:
            continue  # the (lock, root) pair every fill takes positionally
        accepted.add(name)
        if parameter.default is inspect.Parameter.empty:
            required.add(name)
    return frozenset(accepted), frozenset(required), var_keyword


def _fill_call_kwargs(
    fill: Callable[..., str],
    fill_name: object,
    params: Mapping[str, object] | None,
    repo_root: Path,
) -> dict[str, object]:
    """The keyword arguments ``fill`` is called with for ``params``.

    NAMED KEYS ONLY: this resolver never splats a config object into a fill.
    It reads the fill's own signature and passes exactly the parameters that
    signature declares -- plus ``repo_root``, which is injected (never
    configurable) for a fill that declares it.

    Fail-closed on: a non-object ``task_instruction_fill_params``; params at
    all against a fill that declares none and takes no ``**kwargs``; a params
    key naming one of the reserved/injected arguments; and a REQUIRED named
    parameter of the fill that the params do not supply.

    A key the fill neither declares nor can absorb through ``**kwargs`` is
    PROVENANCE, not an argument: ``rails.evolution.write_candidate_fragments``
    writes ``portfolio_sha256``/``round``/``k`` into the same object so the
    fragment's config hash pins which round and which portfolio produced the
    artifact. Those keys are pinned by that hash and are not passed on.

    ``params`` empty or ``None`` returns an empty mapping for every fill that
    declares no ``repo_root``, so all four pre-existing fills are still called
    as exactly ``fill(lock, root)``.
    """

    if params is None:
        params = {}
    if not isinstance(params, Mapping):
        raise CoreError(
            "task_instruction_fill_params must be a JSON object of named fill "
            f"arguments, got {type(params).__name__}"
        )
    accepted, required, var_keyword = _fill_parameter_shape(fill)
    reserved = sorted(_RESERVED_FILL_PARAM_NAMES & set(params))
    if reserved:
        raise CoreError(
            f"task_instruction_fill_params for fill {fill_name!r} names reserved "
            f"argument(s) {reserved}; lock/root are the fill's own positional "
            "arguments and repo_root is injected by the resolver"
        )
    if params and not accepted and not var_keyword:
        raise CoreError(
            f"instruction fill {fill_name!r} accepts no fill parameters, but "
            f"task_instruction_fill_params supplies {sorted(params)}"
        )
    kwargs: dict[str, object] = {}
    if "repo_root" in accepted:
        kwargs["repo_root"] = Path(repo_root)
    for key in sorted(params):
        if key in accepted or var_keyword:
            kwargs[key] = params[key]
    missing = sorted(required - set(kwargs))
    if missing:
        raise CoreError(
            f"instruction fill {fill_name!r} requires fill parameter(s) {missing}; "
            f"task_instruction_fill_params supplies {sorted(params)}"
        )
    return kwargs


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
# SLURP's closed label inventory followed by the per-intent TRAIN slot
# schema (program prerequisite MF-3): a PURE SUFFIX of the fill above, so a
# cell naming it differs from the sealed closed-list baseline by the schema
# and by nothing else. Same `(lock, root) -> str` shape; no existing cell
# names it, so every previously rendered instruction is byte-identical.
INSTRUCTION_FILLS.register(
    "slurp-intent-slot-schema", render_slurp_closed_label_inventory_with_slot_schema
)
# Opt-in projection of the same TRAIN-only ontology to legal intent pairs and
# entity-type names, with no example fillers. The historical fill above and
# every existing config keep their exact rendering.
INSTRUCTION_FILLS.register(
    SLURP_LABEL_INVENTORY_FILL, load_cached_slurp_label_inventory
)
# The evolution loop's state A_r (2026-09-05): the SAME compact registry the
# `audio2tool-registry-compact` fill renders, with the description column of
# the targeted tools replaced from a hash-pinned artifact under `configs/`.
# The FIFTH fill, and the first that takes parameters -- `repo_root` is
# injected by the resolver, `artifact_relpath`/`artifact_sha256` come from the
# baseline fragment's `task_instruction_fill_params`. No existing cell names
# it and no existing fill declares a parameter, so every previously rendered
# instruction is byte-identical to before.
INSTRUCTION_FILLS.register(EVOLVED_FILL_NAME, render_evolved_registry)


def render_template_with_fill(
    template_relpath: object,
    fill_name: object,
    repo_root: Path,
    lock: Mapping[str, object],
    root: Path,
    params: Mapping[str, object] | None = None,
) -> str:
    """One frozen ``configs/`` template rendered through one registered fill.

    Factored verbatim out of :func:`resolve_task_instruction` (whose body is
    now this function plus its own literal/template dispatch) so a SECOND
    caller can render the same hash-pinned template-plus-fill material
    without going through the baseline fragment's single
    ``task_instruction`` slot: :mod:`rails.phase_material` renders one such
    instruction per PHASE of a phase program, and a phase program has as
    many instructions as it has phases.

    Every refusal is the one ``resolve_task_instruction`` already made, in
    the same order and with the same message: a template path that is not a
    plain relative path under ``configs/``, a missing or unreadable
    template, a missing/blank fill name, a template without the single
    ``{tool_schemas}`` placeholder, an unknown fill, an empty fill result,
    and a rendered text that still carries the placeholder. Substitution is
    ``str.replace``, never ``str.format`` -- the templates legitimately
    contain JSON braces.

    ``params`` are passed to the fill as NAMED keyword arguments -- never as
    a blind ``**params`` splat -- through :func:`_fill_call_kwargs`, which
    reads the fill's own signature, injects ``repo_root`` for a fill that
    declares it, refuses params against a fill that accepts none, refuses a
    required parameter the params do not supply, and treats a key the fill
    cannot accept as provenance (see that function). A fill registered with
    the plain ``(lock, root)`` shape every pre-existing entry uses receives
    no keyword arguments at all and is called exactly as before.
    """

    if not isinstance(template_relpath, str) or not _TEMPLATE_RELPATH_PATTERN.fullmatch(
        template_relpath
    ):
        raise CoreError(
            f"task_instruction_template {template_relpath!r} is not a plain relative path "
            "under configs/ (no absolute paths, no '..', no backslashes)"
        )
    template_path = Path(repo_root) / "configs" / template_relpath
    if not template_path.is_file():
        raise CoreError(f"task instruction template missing: {template_path}")
    try:
        template_text = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise CoreError(
            f"cannot read task instruction template {template_path}: {error}"
        ) from error

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
    fill: Callable[..., str] = INSTRUCTION_FILLS.resolve(fill_name)
    kwargs = _fill_call_kwargs(fill, fill_name, params, repo_root)
    fill_text = fill(lock, root, **kwargs) if kwargs else fill(lock, root)
    if not isinstance(fill_text, str) or not fill_text.strip():
        raise CoreError(f"instruction fill {fill_name!r} rendered an empty result")
    rendered = template_text.replace(TOOL_SCHEMAS_PLACEHOLDER, fill_text)
    if TOOL_SCHEMAS_PLACEHOLDER in rendered:
        raise CoreError(
            f"task instruction still contains {TOOL_SCHEMAS_PLACEHOLDER!r} after "
            "rendering; refusing to send an unfilled template"
        )
    return rendered


def resolve_task_instruction(
    values: Mapping[str, object], repo_root: Path, lock: Mapping[str, object], root: Path
) -> str:
    """The run's single task instruction, resolved fail-closed (module docstring).

    A baseline fragment may additionally declare ``task_instruction_fill_params``:
    a JSON object of NAMED arguments for a fill that declares them (the
    ``evolved-artifact-v1`` fill's ``artifact_relpath``/``artifact_sha256``,
    say). It is refused when it is not an object, when the fragment carries a
    literal ``task_instruction`` instead of a template (there is no fill to
    parameterize), and -- inside :func:`_fill_call_kwargs` -- when the named
    fill cannot accept it. Omitting the key is exactly the pre-existing
    behaviour: no fill is called with any keyword argument.
    """

    literal = values.get("task_instruction")
    template_rel = values.get("task_instruction_template")
    params = values.get("task_instruction_fill_params")
    if params is not None and not isinstance(params, Mapping):
        raise CoreError(
            "task_instruction_fill_params must be a JSON object of named fill "
            f"arguments, got {type(params).__name__}"
        )
    if literal is not None and template_rel is not None:
        raise CoreError(
            "baseline config supplies both task_instruction and "
            "task_instruction_template; exactly one is allowed"
        )
    if literal is not None:
        if params is not None:
            raise CoreError(
                "baseline config supplies task_instruction_fill_params beside a "
                "literal task_instruction; fill parameters belong to a "
                "task_instruction_template + task_instruction_fill pair"
            )
        return str(literal)
    if template_rel is None:
        raise CoreError(
            "baseline config supplies neither task_instruction nor "
            "task_instruction_template; one is required"
        )

    return render_template_with_fill(
        template_rel,
        values.get("task_instruction_fill"),
        repo_root,
        lock,
        root,
        params,
    )


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
