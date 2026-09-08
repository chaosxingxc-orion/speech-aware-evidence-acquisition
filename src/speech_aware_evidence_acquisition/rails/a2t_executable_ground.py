"""Build a compact, task-wide, values-stripped Audio2Tool handbook.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``build_executable_ground`` is catalog id
``saea-tool-a2t-executable-ground-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
from typing import Mapping, Sequence

from .knowledge_build_a2t import A2tKbRow

DEFAULT_MAX_UTF8_BYTES = 65_536


class ExecutableGroundError(RuntimeError):
    """The executable-ground builder refused malformed or unsafe input."""


@dataclass(frozen=True)
class ExecutableGroundArtifact:
    """Frozen handbook text and its aggregate construction receipt."""

    text: str
    sha256: str
    report: Mapping[str, object]


_EXECUTION_RULES = """AUDIO2TOOL EXECUTABLE HANDBOOK

Purpose: map the spoken request to the exact JSON tool calls. Treat the handbook as task semantics,
never as a source of argument values.

GLOBAL EXECUTION RULES
1. Select tools by the requested operation and desired state, using each contrast group and Meaning.
2. Emit one call per requested action. For blended or multi-intent speech, decompose every supported
   action and do not add an unrequested call.
3. Use the final corrected value when the speaker revises an earlier value or action.
4. Copy argument values only from the spoken request or its same-core observation. Never copy a value from this handbook, never invent a default, and never replace an omitted optional value.
5. Choose one listed allowed argument-key set for each call. Respect the signature and constraints.
6. Ignore unrelated narrative in needle requests. Resolve implicit requests from the requested end
   state, but do not infer an argument value that was not spoken.
7. Return only one JSON array. Each element is exactly {"name": "toolName", "arguments": {...}}.
   Use exact tool and argument-key spelling. Do not return prose or Markdown.
"""


def _required_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutableGroundError(f"registry {field} must be non-empty text")
    return value.strip()


def _render_keys(keys: frozenset[str]) -> str:
    return "{" + ", ".join(sorted(keys)) + "}"


def _argument_summary(
    patterns: frozenset[frozenset[str]],
) -> tuple[str, str, str]:
    if not patterns:
        return (
            "follow the registry signature",
            "none declared beyond the signature",
            "not observed in the construction partition; follow the signature",
        )
    intersection = set(next(iter(patterns)))
    union: set[str] = set()
    for pattern in patterns:
        intersection.intersection_update(pattern)
        union.update(pattern)
    optional = union - intersection
    required_text = ", ".join(sorted(intersection)) or "none"
    optional_text = ", ".join(sorted(optional)) or "none"
    pattern_text = "; ".join(
        _render_keys(pattern)
        for pattern in sorted(patterns, key=lambda item: (len(item), sorted(item)))
    )
    return required_text, optional_text, pattern_text


def build_executable_ground(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
) -> ExecutableGroundArtifact:
    """Render full task knowledge without utterances, argument values, or defaults."""

    if (
        isinstance(max_utf8_bytes, bool)
        or not isinstance(max_utf8_bytes, int)
        or max_utf8_bytes <= 0
    ):
        raise ExecutableGroundError("max_utf8_bytes must be a positive integer")
    registry: dict[str, dict[str, str]] = {}
    for raw in registry_rows:
        name = _required_text(raw.get("tool_name"), field="tool_name")
        if name in registry:
            raise ExecutableGroundError(f"duplicate registry tool {name!r}")
        registry[name] = {
            "domain": _required_text(raw.get("domain"), field=f"{name}.domain"),
            "category": _required_text(
                raw.get("category"), field=f"{name}.category"
            ),
            "signature": _required_text(
                raw.get("signature"), field=f"{name}.signature"
            ),
            "description": _required_text(
                raw.get("description"), field=f"{name}.description"
            ),
            "constraints": str(raw.get("argument_constraints") or "").strip(),
            "defaults": str(raw.get("argument_defaults") or "").strip(),
        }
    if not registry:
        raise ExecutableGroundError("registry must contain at least one tool")

    patterns_by_tool: dict[str, set[frozenset[str]]] = defaultdict(set)
    argument_keys: set[str] = set()
    source_sample_ids: set[str] = set()
    for row in construction_rows:
        if row.tool_name not in registry:
            raise ExecutableGroundError(
                f"construction tool {row.tool_name!r} is outside the registry"
            )
        if any(not isinstance(key, str) or not key for key in row.arg_signature):
            raise ExecutableGroundError(
                f"construction row {row.unit_id!r} has an invalid argument key"
            )
        pattern = frozenset(row.arg_signature)
        patterns_by_tool[row.tool_name].add(pattern)
        argument_keys.update(pattern)
        source_sample_ids.update(row.sample_ids)

    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for name, entry in registry.items():
        grouped[(entry["domain"], entry["category"])].append(name)

    sections = [_EXECUTION_RULES.rstrip()]
    for (domain, category), names in sorted(grouped.items()):
        ordered_names = sorted(names)
        sections.append(
            "\n".join(
                (
                    f"CONTRAST GROUP {domain} / {category}",
                    "Candidate tools in this contrast group: "
                    + ", ".join(ordered_names),
                    "Choose among them by matching the requested operation to each Meaning; "
                    "shared device nouns do not decide the tool.",
                )
            )
        )
        for name in ordered_names:
            entry = registry[name]
            patterns = frozenset(patterns_by_tool.get(name, set()))
            required, optional, allowed = _argument_summary(patterns)
            constraints = entry["constraints"] or "none beyond the signature"
            sections.append(
                "\n".join(
                    (
                        f"TOOL {name}",
                        f"Meaning: {entry['description']}",
                        f"Signature: {entry['signature']}",
                        f"Required arguments: {required}",
                        f"Optional arguments: {optional}",
                        f"Allowed argument-key sets: {allowed}",
                        f"Constraints: {constraints}",
                    )
                )
            )

    text = "\n\n".join(sections) + "\n"
    if not text.isascii():
        raise ExecutableGroundError("handbook must be ASCII English before model use")
    default_matches = sorted(
        name
        for name, entry in registry.items()
        if entry["defaults"] and entry["defaults"] in text
    )
    if default_matches:
        raise ExecutableGroundError(
            "handbook contains literal registry defaults for tools "
            f"{default_matches!r}"
        )
    rendered = text.encode("utf-8")
    if len(rendered) > max_utf8_bytes:
        raise ExecutableGroundError(
            f"handbook exceeds byte budget: {len(rendered)} > {max_utf8_bytes}"
        )
    pattern_count = sum(len(patterns) for patterns in patterns_by_tool.values())
    report = {
        "schema": "saea-a2t-executable-ground-build-report-v1",
        "registry_tool_count": len(registry),
        "construction_tool_count": len(patterns_by_tool),
        "registry_only_tool_count": len(set(registry) - set(patterns_by_tool)),
        "argument_pattern_family_count": pattern_count,
        "argument_key_count": len(argument_keys),
        "source_sample_count": len(source_sample_ids),
        "contrast_group_count": len(grouped),
        "ascii_only": text.isascii(),
        "default_literal_match_count": len(default_matches),
        "invocation_texts_rendered": 0,
        "argument_values_rendered": 0,
        "utf8_bytes": len(rendered),
        "characters": len(text),
        "line_count": len(text.splitlines()),
        "max_utf8_bytes": max_utf8_bytes,
    }
    return ExecutableGroundArtifact(
        text=text,
        sha256=hashlib.sha256(rendered).hexdigest(),
        report=report,
    )


__all__ = [
    "DEFAULT_MAX_UTF8_BYTES",
    "ExecutableGroundArtifact",
    "ExecutableGroundError",
    "build_executable_ground",
]
