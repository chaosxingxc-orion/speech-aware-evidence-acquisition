"""Decision 263-A, the ACE comparator column (``ace-grow-refine-v1``): reflector
material, the DETERMINISTIC curator and the ``ace-playbook`` store releases.

Design: ``docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-
ace-comparator-design.md`` sections 1.2 (invariant I-OBJ), 4.1-4.5 and 9 step 4
(item E-T2). MODEL-FREE: nothing here contacts a model, a server, a tokenizer
service, an encoder, a GPU or the network. The one tokenizer dependency is
INJECTED (:func:`make_tokenize_counter` wraps a caller-supplied
``POST /tokenize`` callable; the default is a conservative offline proxy).

Roles (spec 4.1)
----------------
* generator -- the lock v2.2 Solver, rendering the current playbook;
* reflector -- the frozen core, text-only, one contact per scenario. THIS
  module builds the request (:func:`render_reflector_request`) and parses the
  answer strictly (:func:`parse_reflector_response`). The reflector may write
  free text, because that IS the baseline;
* curator -- :func:`curate`, a pure function. It never calls a model and never
  reads a number the model wrote;
* playbook -- an itemised document (:func:`empty_playbook`) released as the
  ``ace-playbook`` store (:func:`build_playbook_release`) in the SAME authored
  ``saea-stage3-authored-deltas-v2`` / ``saea-authored-semantic-knowledge-
  source-v1`` form the delta stores use, so a supply-variant arm points at it
  with an ordinary ``release_swap``.

Invariant I-OBJ (spec 1.2)
--------------------------
Every counter, prune decision and ordering is computed from per-row OFFICIAL
credit over the sealed columns (:func:`compute_counter_updates`). The model's
output contributes ONLY proposed item text, section, scope and a one-line
rationale; the response schema has no numeric field at all.

Counter formula (documented, scripted)
--------------------------------------
For an item ``i`` in force during a sealed column and a credit row ``r`` of the
SAME iteration's ``ace`` and ``lock`` columns: ``r`` is IN SCOPE of ``i`` when
(``i.scope.scenarios == ["all"]`` or it intersects ``r.scenarios``) and
(``i.scope.slot_types`` is empty or intersects ``r.slot_types``). For each
in-scope row: ``scoped_rows += 1``; ``helpful += 1`` when ``r.ace - r.lock >
EPSILON``; ``harmful += 1`` when ``r.lock - r.ace > EPSILON``; a tie counts
only toward ``scoped_rows``. Counters are CUMULATIVE across iterations. A
modified item is a new text, so its counters reset.

Material contract (``saea-ace-reflector-material-v1``; produced by E-T3)
-----------------------------------------------------------------------
::

    {"schema": "saea-ace-reflector-material-v1",
     "iteration": <int >= 0>,        # the iteration whose sealed column this describes
     "scenario": "<scenario>",       # one reflector contact per scenario ("all" allowed)
     "source": {"column_arm": "lock" | "ace",
                "run_id": "<run id>",
                "credit_receipt_sha256": "<64 hex>"},
     "n_rows": <int >= 0>,
     "credit_tables": [{"table_id": "<slug>", "title": "<<=80 chars>",
                        "columns": ["<<=40 chars>", ...],
                        "rows": [[<int|float|null|short label>, ...], ...]}, ...],
     "item_counters": [{"item_id": "ace:i<t>:<12 hex>", "helpful": <int>,
                        "harmful": <int>, "scoped_rows": <int>}, ...],
     "material_sha256": "<sha256 of the canonical JSON of the document without this key>"}

Cells are counts, rates or short closed-vocabulary labels (scenario, intent id,
slot type, bucket); a string cell over 48 characters or over 4 words is refused,
as is any key naming text, transcript, gold, value text, utterance, response,
sample ids and so on (:data:`FORBIDDEN_MATERIAL_KEYS`), at any depth.

Credit contract (``saea-ace-credit-v1``; the input of :func:`curate`)
--------------------------------------------------------------------
::

    {"schema": "saea-ace-credit-v1",
     "playbook_iteration": <int>,    # the playbook that was in force in the column
     "rows": [{"row_digest": "<64 hex>", "scenarios": [...], "slot_types": [...],
               "lock": <float 0..1>, "ace": <float 0..1>}, ...]}

``row_digest`` is an opaque digest of the sample id (never the id itself).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .errors import RailsError
from .hashing import canonical_json_bytes, content_hash
from .proposer import _carries_sample_identifier, word_ngrams

# ---------------------------------------------------------------------------
# identifiers and constants
# ---------------------------------------------------------------------------

PLAYBOOK_SCHEMA = "saea-ace-playbook-v1"
MATERIAL_SCHEMA = "saea-ace-reflector-material-v1"
CREDIT_SCHEMA = "saea-ace-credit-v1"
REQUEST_SCHEMA = "saea-ace-reflector-request-v1"
DELTA_ITEMS_SCHEMA_ID = "saea-ace-delta-items-v1"
CONSTANTS_SCHEMA = "saea-ace-curator-constants-v1"
RELEASE_RECEIPT_SCHEMA = "saea-ace-playbook-release-receipt-v1"

#: The repo-relative instruction artefact (English; sha256-pinned by the
#: fragment that flies it; written once, never edited between iterations).
INSTRUCTION_RELPATH = "configs/probes/tfrl/ace-reflector-v1.txt"

ACE_STORE_ID = "ace-playbook"
ACE_STORE_ROLE = "stage3-deltas"
ACE_NODE_TARGET = "solver"
#: The empty release's single inert row is addressed to a node that no ACE route
#: ever serves, so the Solver slice of ``ace-playbook-i0`` is EMPTY while the
#: compiled snapshot is non-empty (the preparer and the snapshot validator both
#: refuse zero values).
ANCHOR_NODE_TARGET = "planner"
ANCHOR_FACET_ID = "ace-playbook-anchor"

SECTIONS = ("strategy", "pitfall", "format-rule")
OPS = ("add", "modify", "delete")
SCOPE_ALL = "all"

#: Pinned curator constants. ``content_hash(ACE_CONSTANTS)`` is what the
#: protocol file (``tfrl-loop-protocol-v1.json``) pins. ``lock_p99_supplied_
#: tokens`` is MEASURED at the FIT step and joins the dict via
#: :func:`with_measured_lock_p99`; ``T_cap`` is then
#: ``lock_p99_supplied_tokens + allowance_tokens`` (spec 4.3).
ACE_CONSTANTS: dict[str, object] = {
    "schema": CONSTANTS_SCHEMA,
    "algorithm": "ace-grow-refine-v1",
    "dedup_exact_normalised": True,
    "dedup_jaccard": 0.8,
    "prune_min_scoped_rows": 10,
    "prune_harm_margin": 3,
    "counter_epsilon": 1e-9,
    "max_adds_per_contact": 3,
    "max_deltas_per_contact": 6,
    "max_item_chars": 400,
    "max_rationale_chars": 200,
    "sections": list(SECTIONS),
    "t_cap_formula": "lock_p99_supplied_tokens + allowance_tokens",
    "allowance_items": 8,
    "tokens_per_supplied_item": 235,
    "allowance_tokens": 1880,
    "drop_order": (
        "rank best to worst by (net desc, created_iteration asc, item_id asc); "
        "keep the longest prefix whose rendered token count is <= T_cap; "
        "items past the prefix are dropped"
    ),
    "ngram_width": 6,
}

#: Keys that must never appear (at any depth) in reflector material or credit.
FORBIDDEN_MATERIAL_KEYS = frozenset({
    "text", "transcript", "gold", "gold_text", "value_text", "utterance",
    "sentence", "response", "response_text", "completion", "content",
    "reference", "words", "audio", "sample_id", "sample_ids", "slurp_id",
    "prompt", "answer", "answers", "entities", "values", "value",
})

_SHA256 = re.compile(r"[0-9a-f]{64}")
_SLUG = re.compile(r"[a-z0-9]+(?:[_-][a-z0-9]+)*")
_RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_SCENARIO = re.compile(r"[a-z]{1,24}")
_SLOT_TYPE = re.compile(r"[a-z_]{1,40}")
_ITEM_ID = re.compile(r"ace:i[0-9]+:[0-9a-f]{12}")
#: An item id as it appears inside a rendered prompt. The id is the first 12 hex
#: characters of a digest, so by chance it can hold a run of exactly six digits
#: (about 1 id in 14), which the bare-six-digit corpus-id detector would take for
#: a sample identifier. It is an opaque pinned handle, never a corpus id.
_ITEM_ID_IN_PROMPT = re.compile(r"(?<![0-9A-Za-z])ace:i[0-9]+:[0-9a-f]{12}(?![0-9a-f])")


def _prompt_carries_sample_identifier(prompt: str) -> bool:
    """The corpus-id detector applied to ``prompt`` with item-id handles masked."""

    return _carries_sample_identifier(_ITEM_ID_IN_PROMPT.sub("ace:item", prompt))


_TITLE = re.compile(r"[A-Za-z0-9 _.,:;()/%+=<>-]{1,80}")
_LABEL = re.compile(r"[A-Za-z0-9_:.<>=+%/ -]{1,48}")
_WORD = re.compile(r"[a-z0-9]+")
_ASCII_PRINTABLE = re.compile(r"[\x20-\x7e]*")


class AceMaterialError(RailsError):
    """A reflector request, response, playbook, credit table or release is malformed."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AceMaterialError(message)


def normalise_text(text: str) -> str:
    """Lower-cased, whitespace-collapsed text: the exact-duplicate key."""

    return " ".join(text.lower().split())


def _tokens(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(text.lower()))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def constants_hash(constants: Mapping[str, object]) -> str:
    """Content hash of a constants dict (what the protocol file pins)."""

    return content_hash(_jsonable(constants))


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def with_measured_lock_p99(
    lock_p99_supplied_tokens: int, base: Mapping[str, object] | None = None
) -> dict[str, object]:
    """The constants dict extended with the MEASURED lock p99 of supplied
    tokens on Fold B (spec 4.3). Pure; the result is what :func:`curate`
    takes and what the receipts hash."""

    _require(
        _is_int(lock_p99_supplied_tokens) and lock_p99_supplied_tokens >= 0,
        "lock_p99_supplied_tokens must be an integer >= 0",
    )
    constants = dict(ACE_CONSTANTS if base is None else base)
    constants["lock_p99_supplied_tokens"] = lock_p99_supplied_tokens
    return constants


_REQUIRED_CONSTANT_KEYS = frozenset(ACE_CONSTANTS)


def validate_constants(constants: Mapping[str, object]) -> Mapping[str, object]:
    """Fail-closed constants check: every pinned key present, unknown keys
    refused, the thresholds in range. ``lock_p99_supplied_tokens`` is the one
    optional extra key (required by :func:`resolve_t_cap`)."""

    _require(isinstance(constants, Mapping), "constants must be a mapping")
    extra = set(constants) - _REQUIRED_CONSTANT_KEYS - {"lock_p99_supplied_tokens"}
    _require(not extra, f"constants carries unknown keys {sorted(extra)}")
    missing = _REQUIRED_CONSTANT_KEYS - set(constants)
    _require(not missing, f"constants is missing keys {sorted(missing)}")
    _require(constants["schema"] == CONSTANTS_SCHEMA, "constants schema differs")
    jac = constants["dedup_jaccard"]
    _require(
        isinstance(jac, (int, float)) and not isinstance(jac, bool) and 0.0 < jac <= 1.0,
        "dedup_jaccard must be in (0, 1]",
    )
    for key in (
        "prune_min_scoped_rows", "prune_harm_margin", "max_adds_per_contact",
        "max_deltas_per_contact", "max_item_chars", "max_rationale_chars",
        "allowance_tokens", "allowance_items", "tokens_per_supplied_item",
    ):
        _require(_is_int(constants[key]) and constants[key] >= 1, f"{key} must be an integer >= 1")
    eps = constants["counter_epsilon"]
    _require(
        isinstance(eps, (int, float)) and not isinstance(eps, bool) and eps >= 0,
        "counter_epsilon must be >= 0",
    )
    if "lock_p99_supplied_tokens" in constants:
        value = constants["lock_p99_supplied_tokens"]
        _require(_is_int(value) and value >= 0, "lock_p99_supplied_tokens must be an integer >= 0")
    return constants


def resolve_t_cap(constants: Mapping[str, object]) -> int:
    """``T_cap`` = the lock's measured p99 supplied tokens on Fold B plus the
    allowance ``A`` (spec 4.3)."""

    validate_constants(constants)
    _require(
        "lock_p99_supplied_tokens" in constants,
        "T_cap needs the measured lock_p99_supplied_tokens (use with_measured_lock_p99)",
    )
    return int(constants["lock_p99_supplied_tokens"]) + int(constants["allowance_tokens"])


# ---------------------------------------------------------------------------
# token counting and the parity helper (spec 4.3)
# ---------------------------------------------------------------------------

PROXY_COUNTER_ID = "proxy-utf8-bytes-div-3-v1"


def proxy_token_count(text: str) -> int:
    """Offline, conservative token proxy: ``ceil(utf8 bytes / 3)``. The
    flight tokenizer measured 2.96-3.03 bytes per token on this study's
    prompts (memory ``token-cap-measure-on-tokenizer``), so this never
    UNDER-counts by more than a few percent. It is the default for the
    curator's deterministic cap; the FIT step re-measures on the flight
    tokenizer through :func:`make_tokenize_counter`."""

    return math.ceil(len(text.encode("utf-8")) / 3) if text else 0


proxy_token_count.counter_id = PROXY_COUNTER_ID  # type: ignore[attr-defined]


def make_tokenize_counter(
    request_json: Callable[[str, str, dict], Mapping[str, object]],
) -> Callable[[str], int]:
    """A token counter on the SERVING tokenizer, via ``POST /tokenize`` --
    the same non-generative route the prompt fit and
    ``scripts/build_e21_brief_placebo_token_match.py`` measure on (body
    ``{"content", "add_special": false, "parse_special": true}``).

    ``request_json(method, path, body)`` is supplied by the caller (the FIT
    step owns the server client); this module opens no connection. Using this
    counter requires a resident server, so it is never called by a test or by
    the offline curator default."""

    def count(text: str) -> int:
        if not text:
            return 0
        response = request_json(
            "POST", "/tokenize",
            {"content": text, "add_special": False, "parse_special": True},
        )
        tokens = response.get("tokens") if isinstance(response, Mapping) else None
        _require(isinstance(tokens, list), "tokenize returned no token list")
        return len(tokens)

    count.counter_id = "serving-tokenize-v1"  # type: ignore[attr-defined]
    return count


def _counter_id(counter: Callable[[str], int]) -> str:
    return str(getattr(counter, "counter_id", "custom"))


def percentile99(values: Sequence[int]) -> int:
    """Nearest-rank 99th percentile (deterministic, no interpolation)."""

    _require(len(values) > 0, "percentile99 needs at least one value")
    ordered = sorted(int(v) for v in values)
    rank = max(1, math.ceil(0.99 * len(ordered)))
    return ordered[rank - 1]


def token_parity_report(
    arm_row_tokens: Mapping[str, Sequence[int]],
    *,
    lock_arm: str = "lock",
    constants: Mapping[str, object] = ACE_CONSTANTS,
    twin_arms: Sequence[str] = ("aa",),
) -> dict[str, object]:
    """Spec 4.3: every NON-TWIN arm shares one per-row ceiling on supplied
    tokens, ``T_cap = p99(lock) + A``. ``arm_row_tokens`` maps an arm id to
    its per-row supplied-token counts (measured on the serving tokenizer by
    the caller). Returns the measured p99, ``T_cap``, and per arm
    ``{rows, max, p99, over_rows, within}``; ``parity_ok`` is true when every
    non-twin arm is within ``T_cap`` on every row. The twin arms
    (``replicate_of: lock``) are reported but not gated."""

    _require(lock_arm in arm_row_tokens, f"parity needs the {lock_arm!r} arm")
    p99 = percentile99(arm_row_tokens[lock_arm])
    t_cap = p99 + int(validate_constants(constants)["allowance_tokens"])
    arms: dict[str, object] = {}
    ok = True
    for arm_id in sorted(arm_row_tokens):
        rows = [int(v) for v in arm_row_tokens[arm_id]]
        _require(all(v >= 0 for v in rows), "supplied token counts must be >= 0")
        over = sum(1 for v in rows if v > t_cap)
        within = over == 0
        gated = arm_id not in twin_arms
        if gated and not within:
            ok = False
        arms[arm_id] = {
            "rows": len(rows),
            "max": max(rows) if rows else 0,
            "p99": percentile99(rows) if rows else 0,
            "over_rows": over,
            "within": within,
            "gated": gated,
        }
    return {
        "schema": "saea-ace-token-parity-v1",
        "lock_p99_supplied_tokens": p99,
        "allowance_tokens": int(constants["allowance_tokens"]),
        "t_cap": t_cap,
        "constants_sha256": constants_hash(constants),
        "arms": arms,
        "parity_ok": ok,
    }


# ---------------------------------------------------------------------------
# the delta schema (reflector output) and its strict parser
# ---------------------------------------------------------------------------


def _scope_schema(constants: Mapping[str, object] = ACE_CONSTANTS) -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["scenarios", "slot_types"],
        "properties": {
            "scenarios": {
                "type": "array",
                "minItems": 1,
                "maxItems": 18,
                "items": {"type": "string", "pattern": "^[a-z]{1,24}$"},
            },
            "slot_types": {
                "type": "array",
                "maxItems": 24,
                "items": {"type": "string", "pattern": "^[a-z_]{1,40}$"},
            },
        },
    }


def delta_items_json_schema(constants: Mapping[str, object] = ACE_CONSTANTS) -> dict[str, object]:
    """The json_schema ``saea-ace-delta-items-v1`` sent on the wire. One flat
    object per delta (``target_id`` is ``""`` for an add; ``text`` is ``""``
    for a delete); the cross-field rules are enforced by
    :func:`parse_reflector_response`. There is no numeric field."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["deltas"],
        "properties": {
            "deltas": {
                "type": "array",
                "maxItems": int(constants["max_deltas_per_contact"]),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["op", "target_id", "section", "scope", "text", "rationale"],
                    "properties": {
                        "op": {"type": "string", "enum": list(OPS)},
                        "target_id": {"type": "string", "pattern": "^(ace:i[0-9]+:[0-9a-f]{12})?$"},
                        "section": {"type": "string", "enum": list(SECTIONS)},
                        "scope": _scope_schema(constants),
                        "text": {
                            "type": "string",
                            "maxLength": int(constants["max_item_chars"]),
                        },
                        "rationale": {
                            "type": "string",
                            "maxLength": int(constants["max_rationale_chars"]),
                        },
                    },
                },
            }
        },
    }


DELTA_ITEMS_SCHEMA = delta_items_json_schema()


def response_format(constants: Mapping[str, object] = ACE_CONSTANTS) -> dict[str, object]:
    """The OpenAI-shaped ``response_format`` for the reflector contact."""

    return {
        "type": "json_schema",
        "json_schema": {
            "name": DELTA_ITEMS_SCHEMA_ID,
            "strict": True,
            "schema": delta_items_json_schema(constants),
        },
    }


def _clean_ascii(value: object, field: str, *, limit: int, allow_empty: bool) -> str:
    _require(isinstance(value, str), f"{field} must be a string")
    assert isinstance(value, str)
    _require(_ASCII_PRINTABLE.fullmatch(value.replace("\n", " ").replace("\t", " ")) is not None,
             f"{field} must be printable ASCII")
    collapsed = " ".join(value.split())
    _require(len(collapsed) <= limit, f"{field} exceeds {limit} characters")
    _require(allow_empty or collapsed != "", f"{field} must be non-empty")
    return collapsed


def _clean_scope(value: object, field: str) -> dict[str, list[str]]:
    _require(
        isinstance(value, Mapping) and set(value) == {"scenarios", "slot_types"},
        f"{field} must carry exactly scenarios and slot_types",
    )
    assert isinstance(value, Mapping)
    scenarios, slot_types = value["scenarios"], value["slot_types"]
    _require(isinstance(scenarios, list) and 1 <= len(scenarios) <= 18, f"{field}.scenarios must be a list of 1-18")
    _require(isinstance(slot_types, list) and len(slot_types) <= 24, f"{field}.slot_types must be a list of at most 24")
    for name in scenarios:
        _require(isinstance(name, str) and _SCENARIO.fullmatch(name) is not None, f"{field}.scenarios has a malformed name")
    for name in slot_types:
        _require(isinstance(name, str) and _SLOT_TYPE.fullmatch(name) is not None, f"{field}.slot_types has a malformed name")
    _require(len(set(scenarios)) == len(scenarios), f"{field}.scenarios repeats a name")
    _require(len(set(slot_types)) == len(slot_types), f"{field}.slot_types repeats a name")
    _require(SCOPE_ALL not in scenarios or scenarios == [SCOPE_ALL], f"{field}.scenarios 'all' must stand alone")
    return {"scenarios": sorted(scenarios), "slot_types": sorted(slot_types)}


def _clean_delta(raw: object, index: int, constants: Mapping[str, object]) -> dict[str, object]:
    field = f"deltas[{index}]"
    _require(
        isinstance(raw, Mapping)
        and set(raw) == {"op", "target_id", "section", "scope", "text", "rationale"},
        f"{field} must carry exactly op, target_id, section, scope, text, rationale",
    )
    assert isinstance(raw, Mapping)
    op = raw["op"]
    _require(op in OPS, f"{field}.op must be one of {OPS}")
    target = raw["target_id"]
    _require(isinstance(target, str), f"{field}.target_id must be a string")
    _require(target == "" or _ITEM_ID.fullmatch(target) is not None, f"{field}.target_id is malformed")
    section = raw["section"]
    _require(section in SECTIONS, f"{field}.section must be one of {SECTIONS}")
    scope = _clean_scope(raw["scope"], f"{field}.scope")
    text = _clean_ascii(raw["text"], f"{field}.text", limit=int(constants["max_item_chars"]), allow_empty=True)
    rationale = _clean_ascii(
        raw["rationale"], f"{field}.rationale",
        limit=int(constants["max_rationale_chars"]), allow_empty=True,
    )
    if op == "add":
        _require(target == "", f"{field}: an add carries no target_id (the curator mints ids)")
        _require(text != "", f"{field}: an add needs text")
    elif op == "modify":
        _require(target != "", f"{field}: a modify needs a target_id")
        _require(text != "", f"{field}: a modify needs text")
    else:
        _require(target != "", f"{field}: a delete needs a target_id")
        _require(text == "", f"{field}: a delete carries no text")
    return {
        "op": op, "target_id": target, "section": section, "scope": scope,
        "text": text, "rationale": rationale,
    }


def parse_reflector_response(
    payload: dict, constants: Mapping[str, object] = ACE_CONSTANTS
) -> list[dict]:
    """Strict parse of ONE reflector answer against ``saea-ace-delta-items-v1``.

    ``payload`` is the decoded JSON object ``{"deltas": [...]}``. Refused (by
    name, :class:`AceMaterialError`): a non-mapping, any key other than
    ``deltas``, a non-list, more than ``max_deltas_per_contact`` deltas or
    more than ``max_adds_per_contact`` adds, an unknown ``op`` / ``section``,
    a malformed scope or id, non-ASCII or over-long text, a counter-like or
    any other extra field, an add carrying an id, a modify/delete without a
    target, a delete carrying text. Returns the normalised deltas in input
    order; no id and no number from the model survives."""

    validate_constants(constants)
    _require(isinstance(payload, Mapping), "reflector payload must be an object")
    _require(set(payload) == {"deltas"}, "reflector payload must carry exactly 'deltas'")
    deltas = payload["deltas"]
    _require(isinstance(deltas, list), "'deltas' must be a list")
    _require(len(deltas) <= int(constants["max_deltas_per_contact"]), "too many deltas for one contact")
    cleaned = [_clean_delta(item, index, constants) for index, item in enumerate(deltas)]
    adds = sum(1 for item in cleaned if item["op"] == "add")
    _require(adds <= int(constants["max_adds_per_contact"]), "too many add deltas for one contact")
    return cleaned


def delta_id(delta: Mapping[str, object]) -> str:
    """``d:<12 hex>`` -- the digest of one NORMALISED delta (provenance key)."""

    return "d:" + content_hash(_jsonable(delta))[:12]


# ---------------------------------------------------------------------------
# playbook documents
# ---------------------------------------------------------------------------

_ITEM_KEYS = frozenset({
    "item_id", "section", "scope", "text", "helpful", "harmful", "scoped_rows",
    "created_iteration", "provenance",
})


def item_id_for(text: str, iteration: int) -> str:
    """``ace:i<t>:<sha256(normalised text)[:12]>`` (spec 4.1)."""

    return f"ace:i{iteration}:{hashlib.sha256(normalise_text(text).encode('utf-8')).hexdigest()[:12]}"


def seal_playbook(document: Mapping[str, object]) -> dict[str, object]:
    """Return ``document`` with its ``content_hash`` (over every other key)."""

    body = {key: value for key, value in document.items() if key != "content_hash"}
    sealed = dict(body)
    sealed["content_hash"] = content_hash(_jsonable(body))
    return sealed


def empty_playbook() -> dict[str, object]:
    """The iteration-0 playbook: zero items."""

    return seal_playbook({"schema": PLAYBOOK_SCHEMA, "iteration": 0, "items": [], "curation": None})


def validate_playbook(playbook: object) -> Mapping[str, object]:
    """Fail-closed playbook check, including the content hash."""

    _require(isinstance(playbook, Mapping), "playbook must be an object")
    assert isinstance(playbook, Mapping)
    _require(
        set(playbook) == {"schema", "iteration", "items", "curation", "content_hash"},
        "playbook has the wrong keys",
    )
    _require(playbook["schema"] == PLAYBOOK_SCHEMA, "playbook schema differs")
    _require(_is_int(playbook["iteration"]) and playbook["iteration"] >= 0, "playbook iteration must be an integer >= 0")
    items = playbook["items"]
    _require(isinstance(items, list), "playbook items must be a list")
    seen: set[str] = set()
    for index, item in enumerate(items):
        field = f"items[{index}]"
        _require(isinstance(item, Mapping) and set(item) == _ITEM_KEYS, f"{field} has the wrong keys")
        _require(_ITEM_ID.fullmatch(str(item["item_id"])) is not None, f"{field}.item_id is malformed")
        _require(item["item_id"] not in seen, f"{field}.item_id repeats")
        seen.add(str(item["item_id"]))
        _require(item["section"] in SECTIONS, f"{field}.section is not legal")
        _clean_scope(item["scope"], f"{field}.scope")
        _clean_ascii(item["text"], f"{field}.text", limit=10_000, allow_empty=False)
        for key in ("helpful", "harmful", "scoped_rows", "created_iteration"):
            _require(_is_int(item[key]) and item[key] >= 0, f"{field}.{key} must be an integer >= 0")
        _require(isinstance(item["provenance"], list) and item["provenance"], f"{field}.provenance must be non-empty")
    body = {key: value for key, value in playbook.items() if key != "content_hash"}
    _require(content_hash(_jsonable(body)) == playbook["content_hash"], "playbook content_hash differs")
    return playbook


def load_playbook(path: Path) -> Mapping[str, object]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_playbook(document)


def write_playbook(path: Path, playbook: Mapping[str, object]) -> str:
    """Write a validated playbook as canonical JSON; return its file sha256."""

    validate_playbook(playbook)
    raw = canonical_json_bytes(_jsonable(playbook))  # type: ignore[arg-type]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return sha256_bytes(raw)


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

SUPPLY_HEADER = "Playbook notes:"


def item_line(item: Mapping[str, object]) -> str:
    """The content of one item as the Solver sees it (also the store row's
    ``content``)."""

    return f"[{item['section']}] {item['text']}"


def rank_items(items: Sequence[Mapping[str, object]]) -> list[Mapping[str, object]]:
    """Best to worst: ``(helpful - harmful)`` desc, ``created_iteration`` asc,
    ``item_id`` asc. Also the deterministic DROP order, read from the tail."""

    return sorted(
        items,
        key=lambda item: (
            -(int(item["helpful"]) - int(item["harmful"])),
            int(item["created_iteration"]),
            str(item["item_id"]),
        ),
    )


def _render_lines(lines: Sequence[str]) -> str:
    if not lines:
        return ""
    return SUPPLY_HEADER + "\n" + "\n".join(f"- {line}" for line in lines)


def render_playbook_supply(
    playbook: dict,
    token_cap: int,
    token_counter: Callable[[str], int] = proxy_token_count,
) -> str:
    """The playbook as one supply string: ``""`` for an empty playbook (no
    header), else a header and one ``- [section] text`` line per item in rank
    order, truncated to the longest PREFIX whose token count is at most
    ``token_cap``. Deterministic; no model."""

    validate_playbook(playbook)
    _require(_is_int(token_cap) and token_cap >= 0, "token_cap must be an integer >= 0")
    lines = [item_line(item) for item in rank_items(playbook["items"])]  # type: ignore[index]
    keep = 0
    for count in range(1, len(lines) + 1):
        if token_counter(_render_lines(lines[:count])) > token_cap:
            break
        keep = count
    return _render_lines(lines[:keep])


def count_playbook_tokens(
    playbook: dict, token_counter: Callable[[str], int] = proxy_token_count
) -> int:
    """Token count of the UNTRUNCATED rendering of the playbook."""

    validate_playbook(playbook)
    lines = [item_line(item) for item in rank_items(playbook["items"])]  # type: ignore[index]
    return token_counter(_render_lines(lines))


# ---------------------------------------------------------------------------
# reflector material and request
# ---------------------------------------------------------------------------


def _scan_forbidden(value: object, where: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            _require(
                str(key).lower() not in FORBIDDEN_MATERIAL_KEYS,
                f"{where} carries the forbidden key {str(key)!r}",
            )
            _scan_forbidden(item, f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _scan_forbidden(item, f"{where}[{index}]")


def material_digest(material: Mapping[str, object]) -> str:
    return content_hash(_jsonable({k: v for k, v in material.items() if k != "material_sha256"}))


def seal_material(material: Mapping[str, object]) -> dict[str, object]:
    """Add ``material_sha256`` to a material document (E-T3 calls this)."""

    sealed = {k: v for k, v in material.items() if k != "material_sha256"}
    sealed["material_sha256"] = material_digest(sealed)
    return sealed


def _clean_cell(cell: object, where: str) -> object:
    if cell is None or isinstance(cell, bool):
        _require(cell is None, f"{where} may not be a boolean")
        return cell
    if _is_int(cell):
        return cell
    if isinstance(cell, float):
        _require(math.isfinite(cell), f"{where} must be finite")
        return cell
    _require(isinstance(cell, str), f"{where} must be a number, null or a short label")
    assert isinstance(cell, str)
    _require(_LABEL.fullmatch(cell) is not None, f"{where} is not a short closed-vocabulary label")
    _require(len(cell.split()) <= 4, f"{where} has more than 4 words")
    _require(not _carries_sample_identifier(cell), f"{where} carries a sample identifier")
    return cell


def validate_material(material: object) -> Mapping[str, object]:
    """Fail-closed material check (see the module docstring for the contract)."""

    _require(isinstance(material, Mapping), "material must be an object")
    assert isinstance(material, Mapping)
    _scan_forbidden(material, "material")
    _require(
        set(material) == {
            "schema", "iteration", "scenario", "source", "n_rows",
            "credit_tables", "item_counters", "material_sha256",
        },
        "material has the wrong keys",
    )
    _require(material["schema"] == MATERIAL_SCHEMA, "material schema differs")
    _require(_is_int(material["iteration"]) and material["iteration"] >= 0, "material iteration must be an integer >= 0")
    _require(
        isinstance(material["scenario"], str)
        and (_SCENARIO.fullmatch(material["scenario"]) is not None),
        "material scenario is malformed",
    )
    source = material["source"]
    _require(
        isinstance(source, Mapping) and set(source) == {"column_arm", "run_id", "credit_receipt_sha256"},
        "material source has the wrong keys",
    )
    assert isinstance(source, Mapping)
    _require(source["column_arm"] in ("lock", "ace"), "material source column_arm must be lock or ace")
    _require(isinstance(source["run_id"], str) and _RUN_ID.fullmatch(source["run_id"]) is not None, "material source run_id is malformed")
    _require(
        isinstance(source["credit_receipt_sha256"], str) and _SHA256.fullmatch(source["credit_receipt_sha256"]) is not None,
        "material source credit_receipt_sha256 is malformed",
    )
    _require(_is_int(material["n_rows"]) and material["n_rows"] >= 0, "material n_rows must be an integer >= 0")
    tables = material["credit_tables"]
    _require(isinstance(tables, list) and len(tables) <= 12, "material credit_tables must be a list of at most 12")
    seen_tables: set[str] = set()
    for t_index, table in enumerate(tables):
        where = f"credit_tables[{t_index}]"
        _require(
            isinstance(table, Mapping) and set(table) == {"table_id", "title", "columns", "rows"},
            f"{where} has the wrong keys",
        )
        _require(isinstance(table["table_id"], str) and _SLUG.fullmatch(table["table_id"]) is not None, f"{where}.table_id is malformed")
        _require(table["table_id"] not in seen_tables, f"{where}.table_id repeats")
        seen_tables.add(table["table_id"])
        _require(isinstance(table["title"], str) and _TITLE.fullmatch(table["title"]) is not None, f"{where}.title is malformed")
        _require(not _carries_sample_identifier(table["title"]), f"{where}.title carries a sample identifier")
        columns = table["columns"]
        _require(isinstance(columns, list) and 1 <= len(columns) <= 12, f"{where}.columns must be a list of 1-12")
        for column in columns:
            _require(isinstance(column, str) and 1 <= len(column) <= 40 and _LABEL.fullmatch(column) is not None, f"{where}.columns has a malformed name")
        rows = table["rows"]
        _require(isinstance(rows, list) and len(rows) <= 60, f"{where}.rows must be a list of at most 60")
        for r_index, row in enumerate(rows):
            _require(isinstance(row, list) and len(row) == len(columns), f"{where}.rows[{r_index}] has the wrong width")
            for c_index, cell in enumerate(row):
                _clean_cell(cell, f"{where}.rows[{r_index}][{c_index}]")
    counters = material["item_counters"]
    _require(isinstance(counters, list), "material item_counters must be a list")
    for index, entry in enumerate(counters):
        where = f"item_counters[{index}]"
        _require(
            isinstance(entry, Mapping) and set(entry) == {"item_id", "helpful", "harmful", "scoped_rows"},
            f"{where} has the wrong keys",
        )
        _require(_ITEM_ID.fullmatch(str(entry["item_id"])) is not None, f"{where}.item_id is malformed")
        for key in ("helpful", "harmful", "scoped_rows"):
            _require(_is_int(entry[key]) and entry[key] >= 0, f"{where}.{key} must be an integer >= 0")
    digest = material["material_sha256"]
    _require(isinstance(digest, str) and _SHA256.fullmatch(digest) is not None, "material_sha256 is malformed")
    _require(digest == material_digest(material), "material_sha256 differs from the document")
    return material


def load_material(path: Path) -> Mapping[str, object]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_material(document)


def _format_cell(cell: object) -> str:
    if cell is None:
        return "-"
    if isinstance(cell, float):
        return format(cell, ".4f")
    return str(cell)


def _render_tables(tables: Sequence[Mapping[str, object]]) -> str:
    if not tables:
        return "(no tables)"
    blocks = []
    for table in tables:
        lines = [f"TABLE {table['table_id']}: {table['title']}", " | ".join(table["columns"])]  # type: ignore[arg-type]
        lines.extend(" | ".join(_format_cell(cell) for cell in row) for row in table["rows"])  # type: ignore[union-attr]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _render_playbook_for_prompt(playbook: Mapping[str, object]) -> str:
    items = rank_items(playbook["items"])  # type: ignore[arg-type]
    if not items:
        return "(the playbook is empty)"
    lines = []
    for item in items:
        scope = item["scope"]
        scenarios = ",".join(scope["scenarios"])  # type: ignore[index]
        slots = ",".join(scope["slot_types"]) or "-"  # type: ignore[index]
        lines.append(
            f"{item['item_id']} [{item['section']}] scenarios={scenarios} slot_types={slots} "
            f"helpful={item['helpful']} harmful={item['harmful']} rows={item['scoped_rows']}\n  {item['text']}"
        )
    return "\n".join(lines)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_instruction(repo_root: Path | None = None) -> tuple[str, str]:
    """``(instruction text, its file sha256)``."""

    path = (repo_root or _repo_root()) / INSTRUCTION_RELPATH
    raw = path.read_bytes()
    return raw.decode("utf-8"), sha256_bytes(raw)


def render_reflector_request(
    material_path: Path,
    playbook_path: Path,
    token_cap: int,
    *,
    constants: Mapping[str, object] = ACE_CONSTANTS,
    repo_root: Path | None = None,
) -> dict:
    """Build the text-only reflector request.

    Reads the material (:func:`load_material`: forbidden keys, free text and
    sample identifiers refused, ``material_sha256`` verified) and the current
    playbook (:func:`load_playbook`), renders the instruction artefact
    ``configs/probes/tfrl/ace-reflector-v1.txt`` and returns an OpenAI-shaped
    request ``{messages, response_format, temperature, max_tokens, ...}``
    together with the identities (material, playbook, instruction, prompt,
    request) a receipt seals. ``messages`` holds ONE user message whose
    content is a plain string: zero audio parts. Never prints or logs text.
    """

    validate_constants(constants)
    _require(_is_int(token_cap) and token_cap >= 0, "token_cap must be an integer >= 0")
    material = load_material(material_path)
    playbook = load_playbook(playbook_path)
    instruction, instruction_sha = load_instruction(repo_root)
    replacements = {
        "{{scenario}}": str(material["scenario"]),
        "{{iteration}}": str(material["iteration"]),
        "{{n_rows}}": str(material["n_rows"]),
        "{{token_cap}}": str(token_cap),
        "{{playbook_tokens}}": str(count_playbook_tokens(dict(playbook))),
        "{{max_adds}}": str(constants["max_adds_per_contact"]),
        "{{max_deltas}}": str(constants["max_deltas_per_contact"]),
        "{{max_item_chars}}": str(constants["max_item_chars"]),
        "{{max_rationale_chars}}": str(constants["max_rationale_chars"]),
        "{{sections}}": ", ".join(SECTIONS),
        "{{tables}}": _render_tables(material["credit_tables"]),  # type: ignore[arg-type]
        "{{playbook}}": _render_playbook_for_prompt(playbook),
    }
    prompt = instruction
    for key, value in replacements.items():
        prompt = prompt.replace(key, value)
    _require("{{" not in prompt, "the instruction artefact has an unresolved placeholder")
    _require(not _prompt_carries_sample_identifier(prompt), "the rendered prompt carries a sample identifier")
    request = {
        "schema": REQUEST_SCHEMA,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": response_format(constants),
        "temperature": 0,
        "max_tokens": 1024,
        "material_sha256": material["material_sha256"],
        "playbook_content_hash": playbook["content_hash"],
        "instruction_relpath": INSTRUCTION_RELPATH,
        "instruction_sha256": instruction_sha,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "token_cap": token_cap,
        "constants_sha256": constants_hash(constants),
    }
    request["request_sha256"] = content_hash(_jsonable(request))
    return request


# ---------------------------------------------------------------------------
# credit, counters (I-OBJ)
# ---------------------------------------------------------------------------


def validate_credit(credit: object) -> Mapping[str, object]:
    """Fail-closed credit check. Row digests must be unique opaque digests;
    credits are finite floats in [0, 1]."""

    _require(isinstance(credit, Mapping), "credit must be an object")
    assert isinstance(credit, Mapping)
    _scan_forbidden(credit, "credit")
    _require(set(credit) == {"schema", "playbook_iteration", "rows"}, "credit has the wrong keys")
    _require(credit["schema"] == CREDIT_SCHEMA, "credit schema differs")
    _require(_is_int(credit["playbook_iteration"]) and credit["playbook_iteration"] >= 0, "credit playbook_iteration must be an integer >= 0")
    rows = credit["rows"]
    _require(isinstance(rows, list), "credit rows must be a list")
    seen: set[str] = set()
    for index, row in enumerate(rows):
        where = f"credit.rows[{index}]"
        _require(
            isinstance(row, Mapping) and set(row) == {"row_digest", "scenarios", "slot_types", "lock", "ace"},
            f"{where} has the wrong keys",
        )
        _require(isinstance(row["row_digest"], str) and _SHA256.fullmatch(row["row_digest"]) is not None, f"{where}.row_digest is malformed")
        _require(row["row_digest"] not in seen, f"{where}.row_digest repeats")
        seen.add(row["row_digest"])
        for key, pattern in (("scenarios", _SCENARIO), ("slot_types", _SLOT_TYPE)):
            names = row[key]
            _require(isinstance(names, list) and all(isinstance(n, str) and pattern.fullmatch(n) for n in names), f"{where}.{key} is malformed")
        for key in ("lock", "ace"):
            value = row[key]
            _require(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and 0.0 <= value <= 1.0,
                f"{where}.{key} must be a finite number in [0, 1]",
            )
    return credit


def _row_in_scope(scope: Mapping[str, Sequence[str]], row: Mapping[str, object]) -> bool:
    scenarios = scope["scenarios"]
    if list(scenarios) != [SCOPE_ALL] and not set(scenarios) & set(row["scenarios"]):  # type: ignore[arg-type]
        return False
    slots = scope["slot_types"]
    return not slots or bool(set(slots) & set(row["slot_types"]))  # type: ignore[arg-type]


def compute_counter_updates(
    items: Sequence[Mapping[str, object]],
    credit: Mapping[str, object],
    epsilon: float = float(ACE_CONSTANTS["counter_epsilon"]),  # type: ignore[arg-type]
) -> dict[str, dict[str, int]]:
    """Per item id: ``{helpful, harmful, scoped_rows}`` INCREMENTS from one
    sealed column pair (the counter formula in the module docstring). Pure;
    the model's claims never enter."""

    validate_credit(credit)
    rows = credit["rows"]
    updates: dict[str, dict[str, int]] = {}
    for item in items:
        helpful = harmful = scoped = 0
        for row in rows:  # type: ignore[union-attr]
            if not _row_in_scope(item["scope"], row):  # type: ignore[arg-type]
                continue
            scoped += 1
            difference = float(row["ace"]) - float(row["lock"])
            if difference > epsilon:
                helpful += 1
            elif -difference > epsilon:
                harmful += 1
        updates[str(item["item_id"])] = {"helpful": helpful, "harmful": harmful, "scoped_rows": scoped}
    return updates


# ---------------------------------------------------------------------------
# the curator
# ---------------------------------------------------------------------------


def _merge_scope(a: Mapping[str, Sequence[str]], b: Mapping[str, Sequence[str]]) -> dict[str, list[str]]:
    if list(a["scenarios"]) == [SCOPE_ALL] or list(b["scenarios"]) == [SCOPE_ALL]:
        scenarios = [SCOPE_ALL]
    else:
        scenarios = sorted(set(a["scenarios"]) | set(b["scenarios"]))
    # An empty slot_types list means "every slot type": the union with an
    # empty list is therefore empty.
    if not a["slot_types"] or not b["slot_types"]:
        slots: list[str] = []
    else:
        slots = sorted(set(a["slot_types"]) | set(b["slot_types"]))
    return {"scenarios": scenarios, "slot_types": slots}


def _new_item(text: str, section: str, scope: Mapping[str, Sequence[str]], iteration: int, event: dict) -> dict[str, object]:
    return {
        "item_id": item_id_for(text, iteration),
        "section": section,
        "scope": {"scenarios": list(scope["scenarios"]), "slot_types": list(scope["slot_types"])},
        "text": text,
        "helpful": 0,
        "harmful": 0,
        "scoped_rows": 0,
        "created_iteration": iteration,
        "provenance": [event],
    }


def curate(
    playbook: dict,
    deltas: list[dict],
    credit: dict,
    constants: dict,
    *,
    token_counter: Callable[[str], int] = proxy_token_count,
    evaluation_ngram_digests: frozenset[str] | None = None,
) -> dict:
    """The DETERMINISTIC curator of spec section 4.2.

    Same inputs give a byte-identical result (and the same ``content_hash``).
    Steps, in this order:

    1. validate the playbook, the deltas (re-parsed with the strict rules),
       the credit (``None`` or an empty-rows credit means no column yet) and
       the constants (``lock_p99_supplied_tokens`` required, for ``T_cap``);
    2. COUNTERS by script (I-OBJ): increment helpful / harmful / scoped_rows
       of every item in force from the sealed column pair;
    3. APPLY the deltas, deletes then modifies then adds, each in input
       order. An unknown target is skipped and counted. Delta text is
       refused (counted) when it carries a sample identifier or, given
       ``evaluation_ngram_digests``, a word 6-gram shared with an evaluation
       query. A modify is a new text: new id, counters reset, the old id
       recorded in provenance;
    4. DE-DUPLICATE, in order (existing items first, then new): exact
       normalised text, then token Jaccard >= ``dedup_jaccard``; the later
       item is dropped, its scope unioned into and its provenance appended
       to the survivor;
    5. PRUNE any item with ``scoped_rows >= prune_min_scoped_rows`` and
       ``harmful - helpful >= prune_harm_margin``;
    6. ORDER (:func:`rank_items`) and CAP: keep the longest prefix whose
       rendering is at most ``T_cap`` tokens on ``token_counter``; the rest
       are dropped (the deterministic drop order is the reverse of the rank).

    Returns the new playbook (iteration + 1) with per-item provenance
    ``[{iteration, op, delta_id, ...}]``, the cumulative counters and a
    ``curation`` report (ids, counts and digests only), sealed with a
    ``content_hash``.
    """

    validate_playbook(playbook)
    validate_constants(constants)
    t_cap = resolve_t_cap(constants)
    parsed = [_clean_delta(delta, index, constants) for index, delta in enumerate(deltas)]
    if credit:
        validate_credit(credit)
        _require(
            credit["playbook_iteration"] == playbook["iteration"],
            "credit playbook_iteration differs from the playbook in force",
        )
        credit_rows = credit["rows"]
    else:
        credit_rows = []
    iteration_in = int(playbook["iteration"])
    iteration = iteration_in + 1
    report: dict[str, object] = {
        "iteration_in": iteration_in,
        "iteration_out": iteration,
        "constants_sha256": constants_hash(constants),
        "token_counter_id": _counter_id(token_counter),
        "playbook_in_content_hash": playbook["content_hash"],
        "credit_sha256": content_hash(_jsonable(credit)) if credit else None,
        "deltas_in": len(parsed),
    }

    # 2. counters by script
    items = [json.loads(json.dumps(item)) for item in playbook["items"]]  # type: ignore[union-attr]
    updates: dict[str, dict[str, int]] = {}
    if credit_rows:
        updates = compute_counter_updates(items, credit, float(constants["counter_epsilon"]))  # type: ignore[arg-type]
        for item in items:
            step = updates[item["item_id"]]
            item["helpful"] += step["helpful"]
            item["harmful"] += step["harmful"]
            item["scoped_rows"] += step["scoped_rows"]
    report["counter_updates"] = {key: updates[key] for key in sorted(updates)}

    # 3. apply deltas
    refused = {"unknown_target": 0, "sample_identifier": 0, "evaluation_ngram": 0, "empty_after_clean": 0}
    applied = {"add": 0, "modify": 0, "delete": 0}
    by_id = {item["item_id"]: item for item in items}
    width = int(constants["ngram_width"])  # type: ignore[arg-type]

    def content_refused(text: str) -> str | None:
        if _carries_sample_identifier(text):
            return "sample_identifier"
        if evaluation_ngram_digests:
            for gram in word_ngrams(text, width):
                if hashlib.sha256(" ".join(gram).encode("utf-8")).hexdigest() in evaluation_ngram_digests:
                    return "evaluation_ngram"
        return None

    new_items: list[dict[str, object]] = []
    removed_by_delete: list[str] = []
    replaced: dict[str, str] = {}
    for delta in (d for d in parsed if d["op"] == "delete"):
        target = str(delta["target_id"])
        if target not in by_id:
            refused["unknown_target"] += 1
            continue
        del by_id[target]
        removed_by_delete.append(target)
        applied["delete"] += 1
    for delta in (d for d in parsed if d["op"] == "modify"):
        target = str(delta["target_id"])
        if target not in by_id:
            refused["unknown_target"] += 1
            continue
        reason = content_refused(str(delta["text"]))
        if reason:
            refused[reason] += 1
            continue
        old = by_id.pop(target)
        replaced[target] = ""
        event = {"iteration": iteration, "op": "modify", "delta_id": delta_id(delta), "replaces": target}
        fresh = _new_item(str(delta["text"]), str(delta["section"]), delta["scope"], iteration, event)  # type: ignore[arg-type]
        fresh["provenance"] = list(old["provenance"]) + [event]
        replaced[target] = str(fresh["item_id"])
        new_items.append(fresh)
        applied["modify"] += 1
    for delta in (d for d in parsed if d["op"] == "add"):
        reason = content_refused(str(delta["text"]))
        if reason:
            refused[reason] += 1
            continue
        event = {"iteration": iteration, "op": "add", "delta_id": delta_id(delta)}
        new_items.append(_new_item(str(delta["text"]), str(delta["section"]), delta["scope"], iteration, event))  # type: ignore[arg-type]
        applied["add"] += 1
    report["applied"] = applied
    report["refused"] = refused

    # 4. de-duplicate: existing items (in rank order) first, then the new ones
    survivors: list[dict[str, object]] = [dict(item) for item in rank_items(list(by_id.values()))]
    normalised = [normalise_text(str(item["text"])) for item in survivors]
    token_sets = [_tokens(str(item["text"])) for item in survivors]
    threshold = float(constants["dedup_jaccard"])  # type: ignore[arg-type]
    merges: list[dict[str, str]] = []
    exact = near = 0
    for fresh in new_items:
        text_norm = normalise_text(str(fresh["text"]))
        text_tokens = _tokens(str(fresh["text"]))
        match = None
        kind = ""
        for index, existing in enumerate(normalised):
            if constants["dedup_exact_normalised"] and existing == text_norm:
                match, kind = index, "exact"
                break
            if jaccard(token_sets[index], text_tokens) >= threshold:
                match, kind = index, "near"
                break
        if match is None:
            survivors.append(fresh)
            normalised.append(text_norm)
            token_sets.append(text_tokens)
            continue
        survivor = survivors[match]
        survivor["scope"] = _merge_scope(survivor["scope"], fresh["scope"])  # type: ignore[arg-type]
        survivor["provenance"] = list(survivor["provenance"]) + [  # type: ignore[arg-type]
            {**event, "op": "merge", "merged_from": fresh["item_id"]}
            for event in fresh["provenance"][-1:]  # type: ignore[index]
        ]
        merges.append({"dropped": str(fresh["item_id"]), "into": str(survivor["item_id"]), "kind": kind})
        if kind == "exact":
            exact += 1
        else:
            near += 1
    report["dedup"] = {"exact": exact, "near": near, "merges": merges}

    # 5. prune by script-computed counters
    min_rows = int(constants["prune_min_scoped_rows"])  # type: ignore[arg-type]
    margin = int(constants["prune_harm_margin"])  # type: ignore[arg-type]
    pruned = [
        str(item["item_id"]) for item in survivors
        if int(item["scoped_rows"]) >= min_rows and int(item["harmful"]) - int(item["helpful"]) >= margin  # type: ignore[arg-type]
    ]
    survivors = [item for item in survivors if item["item_id"] not in set(pruned)]
    report["pruned"] = sorted(pruned)
    report["deleted"] = sorted(removed_by_delete)
    report["replaced"] = {key: replaced[key] for key in sorted(replaced)}

    # 6. order and cap
    ranked = [dict(item) for item in rank_items(survivors)]
    lines = [item_line(item) for item in ranked]
    keep = 0
    for count in range(1, len(lines) + 1):
        if token_counter(_render_lines(lines[:count])) > t_cap:
            break
        keep = count
    dropped = [str(item["item_id"]) for item in ranked[keep:]]
    ranked = ranked[:keep]
    report["dropped_by_cap"] = dropped
    report["t_cap"] = t_cap
    report["rendered_tokens"] = token_counter(_render_lines([item_line(item) for item in ranked]))
    report["items_out"] = len(ranked)

    return seal_playbook({
        "schema": PLAYBOOK_SCHEMA,
        "iteration": iteration,
        "items": ranked,
        "curation": report,
    })


# ---------------------------------------------------------------------------
# the ace-playbook store release (same authored form as the delta stores)
# ---------------------------------------------------------------------------

AUTHORED_SCHEMA_V2 = "saea-stage3-authored-deltas-v2"
AUTHORED_SOURCE_SCHEMA = "saea-authored-semantic-knowledge-source-v1"
BUILDER_POLICY_ID_V2 = "saea-authored-stage3-deltas-v2"
SOURCE_WRAP_RECEIPT_SCHEMA = "saea-stage3-delta-source-wrap-receipt-v1"
REGISTRATION_SCHEMA = "saea-authored-semantic-knowledge-preparation-v1"
DEFAULT_RELEASE_DIR = "prepared/SAEA-SLURP-ACE-PLAYBOOK"


def _facets_for_scope(scope: Mapping[str, Sequence[str]], legal_intent_ids: Sequence[str]) -> list[str]:
    """The candidate-bound route intersects a row's Perception candidate
    INTENT ids with ``associated_facet_ids``. ACE has no key (D3): scope
    ``all`` is every legal intent, so any row with a candidate receives the
    item; a scenario list narrows to the intents of those scenarios. Slot
    types cannot be routed on and narrow only the counters."""

    legal = sorted(set(legal_intent_ids))
    if list(scope["scenarios"]) == [SCOPE_ALL]:
        return legal
    wanted = set(scope["scenarios"])
    return [intent for intent in legal if intent.split("_", 1)[0] in wanted]


def playbook_release_rows(
    playbook: Mapping[str, object],
    *,
    carrier_sample_ids: Sequence[str],
    legal_intent_ids: Sequence[str],
) -> list[dict[str, object]]:
    """The authored ``saea-stage3-authored-deltas-v2`` rows of a playbook.

    One row per item: ``value_id`` ``delta:<created_iteration>:<12 hex>``,
    ``content`` the item line, ``associated_facet_ids`` per
    :func:`_facets_for_scope`, ``node_target`` ``solver``, ``task_target``
    ``solver:ace-playbook:<section>``, ``prior_score`` strictly decreasing in
    rank and inside (0, 1] as ``(total - rank) / total`` (the snapshot requires a probability; so the route's ``prior_score`` ordering reproduces the playbook's
    rank order), ``source_sample_ids`` the carrier rows, ``provenance_refs``
    the item's provenance events. An EMPTY playbook yields ONE inert anchor row
    addressed to :data:`ANCHOR_NODE_TARGET`, which the Solver route never
    serves: the snapshot is non-empty (the runtime refuses empty snapshots)
    and the Solver slice is empty."""

    validate_playbook(playbook)
    carriers = sorted(set(carrier_sample_ids))
    _require(len(carriers) > 0, "carrier_sample_ids must be non-empty")
    iteration = int(playbook["iteration"])  # type: ignore[arg-type]
    items = rank_items(playbook["items"])  # type: ignore[arg-type]
    if not items:
        anchor_text = f"ace-playbook anchor i{iteration} (never routed to the Solver)"
        return [{
            "value_id": f"delta:{iteration}:{hashlib.sha256(anchor_text.encode('utf-8')).hexdigest()[:12]}",
            "content": anchor_text,
            "associated_facet_ids": [ANCHOR_FACET_ID],
            "source_sample_ids": carriers,
            "provenance_refs": [f"ace-playbook:i{iteration}:anchor"],
            "task_target": f"{ANCHOR_NODE_TARGET}:ace-playbook:anchor",
            "prior_score": 0.0,
            "node_target": ANCHOR_NODE_TARGET,
        }]
    rows = []
    total = len(items)
    for rank, item in enumerate(items):
        facets = _facets_for_scope(item["scope"], legal_intent_ids)  # type: ignore[arg-type]
        _require(len(facets) > 0, f"item {item['item_id']} resolves to no legal intent facet")
        digest = str(item["item_id"]).rsplit(":", 1)[1]
        refs = [
            f"ace-playbook:i{iteration}:{item['item_id']}",
            *[
                f"ace:i{event['iteration']}:{event['op']}:{event.get('delta_id', 'n/a')}"
                for event in item["provenance"]  # type: ignore[union-attr]
            ],
        ]
        rows.append({
            "value_id": f"delta:{item['created_iteration']}:{digest}",
            "content": item_line(item),
            "associated_facet_ids": facets,
            "source_sample_ids": carriers,
            "provenance_refs": sorted(set(refs)),
            "task_target": f"{ACE_NODE_TARGET}:ace-playbook:{item['section']}",
            "prior_score": (total - rank) / total,
            "node_target": ACE_NODE_TARGET,
        })
    return rows


def build_playbook_release(
    playbook: dict,
    *,
    data_root: Path,
    carrier_sample_ids: Sequence[str],
    legal_intent_ids: Sequence[str],
    source_split_identity_hash: str,
    release_dir: str = DEFAULT_RELEASE_DIR,
    registration_binding: Mapping[str, object] | None = None,
    registration_path: Path | None = None,
    registration_id: str | None = None,
    output_namespace: str | None = None,
) -> dict[str, object]:
    """Write the ``ace-playbook`` release inputs for one playbook and return a
    receipt of paths and digests (no text).

    Under ``<data_root>/<release_dir>/`` it writes the playbook
    (``playbook-i<t>.json``), the authored document
    (``authored-ace-playbook-i<t>.json``, schema ``saea-stage3-authored-
    deltas-v2``), the release-ready wrapper (``source-ace-playbook-i<t>.json``,
    schema ``saea-authored-semantic-knowledge-source-v1``, builder
    ``saea-authored-stage3-deltas-v2``) and the wrap receipt -- exactly the
    artefacts ``scripts/build_slurp_stage3_delta_store.py`` writes for the
    delta stores. With ``registration_binding`` (the roster pins of the
    release: ``construction_scope``, ``permitted_roster``, ``forbidden_rosters``)
    and ``registration_path`` it also writes the
    ``saea-authored-semantic-knowledge-preparation-v1`` registration whose
    ``output_namespace`` defaults to ``knowledge/slurp/semantic/ace-playbook-i<t>``;
    ``prepare_semantic_knowledge_store`` then compiles and releases it unchanged.
    Deterministic bytes (canonical JSON), so a re-run reproduces the pins."""

    validate_playbook(playbook)
    _require(
        isinstance(source_split_identity_hash, str) and _SHA256.fullmatch(source_split_identity_hash) is not None,
        "source_split_identity_hash must be a lowercase 64-hex SHA-256",
    )
    iteration = int(playbook["iteration"])
    rows = playbook_release_rows(
        playbook, carrier_sample_ids=carrier_sample_ids, legal_intent_ids=legal_intent_ids
    )
    base = Path(data_root) / release_dir
    base.mkdir(parents=True, exist_ok=True)
    playbook_path = base / f"playbook-i{iteration}.json"
    playbook_sha = write_playbook(playbook_path, playbook)
    authored = {"schema": AUTHORED_SCHEMA_V2, "iteration": iteration, "rows": rows}
    authored_raw = canonical_json_bytes(authored)
    authored_path = base / f"authored-ace-playbook-i{iteration}.json"
    authored_path.write_bytes(authored_raw)
    source = {
        "schema": AUTHORED_SOURCE_SCHEMA,
        "builder_policy_id": BUILDER_POLICY_ID_V2,
        "source_split_identity_hash": source_split_identity_hash,
        "rows": rows,
    }
    source_raw = canonical_json_bytes(source)
    source_path = base / f"source-ace-playbook-i{iteration}.json"
    source_path.write_bytes(source_raw)
    wrap = {
        "schema": SOURCE_WRAP_RECEIPT_SCHEMA,
        "authored": {
            "relpath": str(authored_path),
            "sha256": sha256_bytes(authored_raw),
            "authored_schema": AUTHORED_SCHEMA_V2,
            "iteration": iteration,
            "facet_rule": None,
            "twin_of_seed": None,
            "row_count": len(rows),
        },
        "source": {"relpath": str(source_path), "sha256": sha256_bytes(source_raw)},
        "builder_policy_id": BUILDER_POLICY_ID_V2,
        "source_split_identity_hash": source_split_identity_hash,
    }
    wrap_raw = canonical_json_bytes(wrap)
    wrap_path = base / f"source-ace-playbook-i{iteration}-wrap-receipt.json"
    wrap_path.write_bytes(wrap_raw)
    receipt: dict[str, object] = {
        "schema": RELEASE_RECEIPT_SCHEMA,
        "iteration": iteration,
        "empty": not playbook["items"],
        "row_count": len(rows),
        "playbook": {"relpath": f"{release_dir}/{playbook_path.name}", "sha256": playbook_sha,
                     "content_hash": playbook["content_hash"]},
        "authored": {"relpath": f"{release_dir}/{authored_path.name}", "sha256": sha256_bytes(authored_raw)},
        "source": {"relpath": f"{release_dir}/{source_path.name}", "sha256": sha256_bytes(source_raw)},
        "wrap_receipt": {"relpath": f"{release_dir}/{wrap_path.name}", "sha256": sha256_bytes(wrap_raw)},
        "registration": None,
    }
    if registration_binding is not None:
        _require(registration_path is not None, "registration_path is required with registration_binding")
        required = {"construction_scope", "permitted_roster", "forbidden_rosters"}
        _require(set(registration_binding) == required, f"registration_binding must carry exactly {sorted(required)}")
        namespace = output_namespace or f"knowledge/slurp/semantic/ace-playbook-i{iteration}"
        registration = {
            "schema": REGISTRATION_SCHEMA,
            "registration_id": registration_id or f"SAEA-SLURP-ACE-PLAYBOOK-PREPARATION-I{iteration}",
            "carrier_lock_key": "slurp",
            "source_partition_role": "train",
            "source_split_identity_hash": source_split_identity_hash,
            "builder_policy_id": BUILDER_POLICY_ID_V2,
            "store_id": ACE_STORE_ID,
            "store_role": ACE_STORE_ROLE,
            "authored_source": {
                "relpath": f"{release_dir}/{source_path.name}",
                "root": "data",
                "sha256": sha256_bytes(source_raw),
            },
            "construction_scope": registration_binding["construction_scope"],
            "permitted_roster": registration_binding["permitted_roster"],
            "forbidden_rosters": registration_binding["forbidden_rosters"],
            "output_namespace": namespace,
        }
        registration_raw = canonical_json_bytes(registration)
        Path(registration_path).parent.mkdir(parents=True, exist_ok=True)  # type: ignore[arg-type]
        Path(registration_path).write_bytes(registration_raw)  # type: ignore[arg-type]
        receipt["registration"] = {"path": str(registration_path), "sha256": sha256_bytes(registration_raw),
                                   "output_namespace": namespace}
    return receipt


__all__ = [
    "ACE_CONSTANTS", "ACE_NODE_TARGET", "ACE_STORE_ID", "ACE_STORE_ROLE", "ANCHOR_NODE_TARGET",
    "AceMaterialError", "CREDIT_SCHEMA", "DELTA_ITEMS_SCHEMA", "DELTA_ITEMS_SCHEMA_ID",
    "FORBIDDEN_MATERIAL_KEYS", "INSTRUCTION_RELPATH", "MATERIAL_SCHEMA", "PLAYBOOK_SCHEMA",
    "build_playbook_release", "compute_counter_updates", "constants_hash", "count_playbook_tokens",
    "curate", "delta_id", "empty_playbook", "item_id_for", "load_material", "load_playbook",
    "make_tokenize_counter", "parse_reflector_response", "percentile99", "playbook_release_rows",
    "proxy_token_count", "render_playbook_supply", "render_reflector_request", "resolve_t_cap",
    "seal_material", "seal_playbook", "token_parity_report", "validate_constants",
    "validate_credit", "validate_material", "validate_playbook", "with_measured_lock_p99",
    "write_playbook",
]
