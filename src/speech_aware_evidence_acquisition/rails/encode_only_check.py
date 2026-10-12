"""Structural encode-only machine check (embedder-charter adjudication,
``docs/readiness/2026-08-20-embedder-charter-adjudication.md`` section 2:
"the integration must structurally forbid generation ... enforced by a
machine check ... never by convention").

A fail-closed, importable check -- run BOTH inside ``rails.probes.
pemb3m_flight``'s own pre-flight gate (d) AND directly as a pytest
(``tests/unit/test_encode_only_check.py``, the same "importable + run as a
pytest" duality ``rails.probes.pslu_flight.assert_never_calls_ontology_miner``
already established for the ontology-miner guard). Four independent proofs,
each fail-closed on its own -- never a single combined boolean that could
hide which one actually caught a problem:

1. **IMPORT guard** (:func:`assert_module_never_imports_generation_client`):
   a pinned module's source must never IMPORT the generation-capable client
   (``rails.core_client``/``CoreClient``/``FrozenCoreClient``). Scoped to
   ``ast.Import``/``ast.ImportFrom`` nodes ONLY -- deliberately narrower than
   ``rails.probes.pslu_flight._source_references_ontology_miner``'s own
   Name/Attribute sweep, because ``core_client`` is this codebase's OWN
   established duck-typed PARAMETER name (``rails.probes.pslu_flight.
   run_pslu_flight``'s own ``core_client`` argument, module docstring:
   "duck-typed against ``rails.core_client.CoreClient``, not imported/
   annotated directly"). ``rails.probes.pemb3m_flight``'s own registered
   CASCADE-T0 supplement (pre-flight gate (c) fallback) legitimately needs
   to CALL ``.complete(...)`` on a caller-supplied frozen-core client for
   its OWN ``<=66`` generation contacts -- an import-level guard lets that
   duck-typed parameter exist and be used without a false positive, while
   still catching the ONE thing charter section 2 actually forbids: this
   package's embedding integration ever importing the generation client
   itself.
2. **ENDPOINT-STRING guard**
   (:func:`assert_source_has_no_forbidden_endpoint_strings`): a pinned
   module's source must never contain a string literal naming a
   generation-shaped HTTP path (``/completion``, ``/chat/completions``,
   ``/v1/chat``, ``/generate``, ``/infill``).
3. **CLIENT-SURFACE guard** (:func:`assert_client_surface_is_encode_only`):
   a LIVE client object's own public members (``dir()``, never trusted from
   a docstring) must carry none of a small generation-shaped verb
   vocabulary (``complete``/``chat``/``generate``/... ) and must expose at
   least one encode-shaped method (``embed_text``/``embed_audio``) -- never
   a check that could pass vacuously against an unrelated object.
4. **PAYLOAD-KEY guard** (:func:`assert_payload_has_no_forbidden_keys`): a
   request payload (any nested ``Mapping``/``list``/``tuple``) must never
   carry a sampling/generation-shaped key (``temperature``, ``top_p``,
   ``max_tokens``, ``n_predict``, ``stop``, ``seed``, ... ) at any depth.

:func:`run_encode_only_machine_check` sweeps guards 1+2 over every module in
:data:`PINNED_ENCODE_ONLY_MODULE_NAMES` (``rails.embedding_client``,
``rails.local_encoder_client``, ``rails.probes.pemb3m_flight``) and is the
function ``rails.probes.pemb3m_flight``'s own pre-flight gate (d) calls;
guards 3+4 need a constructed instance/payload and are exercised directly by
callers (the flight's own gate function, and this module's own pytest
suite) against real objects.
"""

from __future__ import annotations

import ast
import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .errors import RailsError

FORBIDDEN_IMPORT_MODULE_SUFFIXES = ("rails.core_client", "core.model.transport")
FORBIDDEN_IMPORT_NAMES = ("CoreClient", "FrozenCoreClient")

FORBIDDEN_ENDPOINT_SUBSTRINGS = (
    "/completion",
    "/chat/completions",
    "/v1/chat",
    "/generate",
    "/infill",
)

FORBIDDEN_CLIENT_MEMBER_NAMES = frozenset(
    {"complete", "chat", "generate", "stream", "respond", "sample", "decode", "answer", "infer"}
)
ENCODE_SHAPED_MEMBER_NAMES = frozenset({"embed_text", "embed_audio"})

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "temperature",
        "top_p",
        "top_k",
        "min_p",
        "max_tokens",
        "n_predict",
        "stop",
        "grammar",
        "seed",
        "repeat_penalty",
        "presence_penalty",
        "frequency_penalty",
        "logit_bias",
        "tools",
        "tool_choice",
        "response_format",
        "mirostat",
        "typical_p",
        "stream",
        "messages",
        # Thinking-core harness knobs (decision 283 A): generation-side reasoning controls.
        "thinking_budget_tokens",
        "chat_template_kwargs",
        "enable_thinking",
    }
)

PINNED_ENCODE_ONLY_MODULE_NAMES: tuple[str, ...] = (
    "speech_aware_evidence_acquisition.rails.embedding_client",
    "speech_aware_evidence_acquisition.rails.local_encoder_client",
    "speech_aware_evidence_acquisition.rails.probes.pemb3m_flight",
    # P-EMB-4R (SAEA-PROBE-pemb4r-4100, docs/readiness/
    # 2026-08-20-pemb4r-preregistration-REGISTERED.md): coverage EXTENDED
    # here (this check's own logic carried unchanged) -- pemb4r_flight uses
    # the SAME embedding-client family as pemb3m_flight PLUS the SAME
    # duck-typed core_client.complete(...) escape hatch pemb3m_flight's own
    # CASCADE-T0 supplement already established (guard 1's own docstring:
    # scoped to ast.Import/ast.ImportFrom only, so a duck-typed parameter
    # never trips it) for its own C-DECODE arm.
    "speech_aware_evidence_acquisition.rails.probes.pemb4r_flight",
)


class EncodeOnlyCheckError(RailsError):
    """A generation-capable endpoint, import, client surface member, or
    sampling parameter is reachable through an embedding integration
    surface -- fail-closed, never a warning."""


# ---------------------------------------------------------------------------
# Guard 1 -- IMPORT.
# ---------------------------------------------------------------------------


def _source_imports_generation_client(source: str) -> str | None:
    """Returns a human-readable reason string the moment ``source`` imports
    the forbidden generation-client module/names, else ``None``. AST-based
    (never a substring search: this module's OWN docstrings legitimately
    name ``CoreClient``/``core_client`` in prose)."""

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if any(suffix in module for suffix in FORBIDDEN_IMPORT_MODULE_SUFFIXES):
                return f"import from {module!r}"
            for alias in node.names:
                if alias.name in FORBIDDEN_IMPORT_NAMES:
                    return f"import of {alias.name!r} from {module!r}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if any(suffix in alias.name for suffix in FORBIDDEN_IMPORT_MODULE_SUFFIXES):
                    return f"import of {alias.name!r}"
    return None


def assert_module_never_imports_generation_client(module_path: Path, *, source: str | None = None) -> None:
    text = source if source is not None else Path(module_path).read_text(encoding="utf-8")
    reason = _source_imports_generation_client(text)
    if reason is not None:
        raise EncodeOnlyCheckError(
            f"{module_path}: source contains a forbidden generation-client {reason} -- the "
            "embedding integration surface must never import the generation-capable client "
            "(embedder-charter adjudication section 2)"
        )


# ---------------------------------------------------------------------------
# Guard 2 -- ENDPOINT STRING.
# ---------------------------------------------------------------------------


def _source_endpoint_violation(source: str) -> str | None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for forbidden in FORBIDDEN_ENDPOINT_SUBSTRINGS:
                if forbidden in node.value:
                    return f"string literal {node.value!r} contains {forbidden!r}"
    return None


def assert_source_has_no_forbidden_endpoint_strings(module_path: Path, *, source: str | None = None) -> None:
    text = source if source is not None else Path(module_path).read_text(encoding="utf-8")
    violation = _source_endpoint_violation(text)
    if violation is not None:
        raise EncodeOnlyCheckError(
            f"{module_path}: {violation} -- a generation-shaped HTTP path must be unreachable "
            "by construction through the embedding integration surface"
        )


# ---------------------------------------------------------------------------
# Guard 3 -- CLIENT SURFACE (runtime introspection).
# ---------------------------------------------------------------------------


def assert_client_surface_is_encode_only(client: object) -> None:
    public_members = {name for name in dir(client) if not name.startswith("_")}
    forbidden = public_members & FORBIDDEN_CLIENT_MEMBER_NAMES
    if forbidden:
        raise EncodeOnlyCheckError(
            f"{type(client).__name__} exposes generation-shaped public member(s) "
            f"{sorted(forbidden)} -- an embedding integration client's public surface must be "
            "encode()-shaped only"
        )
    if not (public_members & ENCODE_SHAPED_MEMBER_NAMES):
        raise EncodeOnlyCheckError(
            f"{type(client).__name__} exposes neither {sorted(ENCODE_SHAPED_MEMBER_NAMES)} -- not "
            "a recognizable encode-only client surface (this check must never pass vacuously)"
        )


# ---------------------------------------------------------------------------
# Guard 4 -- PAYLOAD KEY (recursive).
# ---------------------------------------------------------------------------


def assert_payload_has_no_forbidden_keys(payload: object, *, context: str = "payload") -> None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_PAYLOAD_KEYS:
                raise EncodeOnlyCheckError(
                    f"{context}: payload carries the forbidden sampling/generation key {key!r}"
                )
            assert_payload_has_no_forbidden_keys(value, context=f"{context}.{key}")
    elif isinstance(payload, (list, tuple)):
        for index, item in enumerate(payload):
            assert_payload_has_no_forbidden_keys(item, context=f"{context}[{index}]")


# ---------------------------------------------------------------------------
# Sweep entry point (pre-flight gate (d) + this module's own pytest suite).
# ---------------------------------------------------------------------------


def _module_file_path(module_name: str) -> Path:
    module = importlib.import_module(module_name)
    module_file = getattr(module, "__file__", None)
    if not module_file:
        raise EncodeOnlyCheckError(f"module {module_name!r} carries no __file__ to inspect")
    return Path(module_file)


@dataclass(frozen=True)
class EncodeOnlyCheckReport:
    checked_modules: tuple[str, ...]


def run_encode_only_machine_check(
    *, module_names: Sequence[str] = PINNED_ENCODE_ONLY_MODULE_NAMES
) -> EncodeOnlyCheckReport:
    """The full source-level sweep (guards 1+2) over every pinned module.
    Fail-closed: the first violation raises :class:`EncodeOnlyCheckError`
    immediately, never collected into a soft report. This is the function
    ``rails.probes.pemb3m_flight``'s own pre-flight gate (d) calls, and the
    SAME function ``tests/unit/test_encode_only_check.py`` calls directly."""

    checked: list[str] = []
    for module_name in module_names:
        path = _module_file_path(module_name)
        assert_module_never_imports_generation_client(path)
        assert_source_has_no_forbidden_endpoint_strings(path)
        checked.append(module_name)
    return EncodeOnlyCheckReport(checked_modules=tuple(checked))


__all__ = [
    "ENCODE_SHAPED_MEMBER_NAMES",
    "FORBIDDEN_CLIENT_MEMBER_NAMES",
    "FORBIDDEN_ENDPOINT_SUBSTRINGS",
    "FORBIDDEN_IMPORT_MODULE_SUFFIXES",
    "FORBIDDEN_IMPORT_NAMES",
    "FORBIDDEN_PAYLOAD_KEYS",
    "PINNED_ENCODE_ONLY_MODULE_NAMES",
    "EncodeOnlyCheckError",
    "EncodeOnlyCheckReport",
    "assert_client_surface_is_encode_only",
    "assert_module_never_imports_generation_client",
    "assert_payload_has_no_forbidden_keys",
    "assert_source_has_no_forbidden_endpoint_strings",
    "run_encode_only_machine_check",
]
