"""Thinking-core harness knobs (owner decision 283 A, design 2026-10-12).

Pure, dependency-free declarations for a reasoning (Thinking) core served by the pinned llama.cpp build:

* the **model-fragment knobs** -- ``reasoning_budget_tokens``, ``answer_reserve_tokens``, ``enable_thinking``,
  ``reasoning_context_policy`` and ``forced_close_message_sha256``. They are ordinary top-level keys of the model fragment, so
  they enter the fragment hash, the composed config hash and therefore the protocol hash like every other fragment key. A
  fragment that declares none of the request-shaping ones composes byte-identical request bytes to before this module existed;
* the **per-request wire fields** the knobs fold into ``decoding_params`` at composition time: ``thinking_budget_tokens`` and
  ``chat_template_kwargs = {"enable_thinking": bool}``. The forced-close sentence is NOT a request field; it is the server flag
  ``--reasoning-budget-message`` and rides the fragment's ``server_args`` (serving geometry). Its sha256 is pinned here;
* the **per-node override map** ``thinking_policy`` (``{node_id: {reasoning_budget_tokens, answer_reserve_tokens,
  enable_thinking}}``), resolved per contact by :func:`resolve_node_decoding`;
* the **answer-only fallback** decoding (decision 278): one re-ask with ``enable_thinking: false`` and ``max_tokens`` = the
  reserve, and its receipt schema.

Invariant ``max_tokens == reasoning_budget_tokens + answer_reserve_tokens`` (both present) is what lets the harness derive the
reserve from a request's own decoding params; the fallback needs no extra plumbing.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

REASONING_CONTEXT_POLICIES = frozenset({"drop-reasoning-v1"})
#: The guard value that marks a fragment as a reasoning (Thinking) fragment. Mirrors
#: ``core.model.transport.REASONING_CONTENT_GUARD_THINK_MARKER`` (duplicated here to keep this module import-free).
THINKING_FRAGMENT_GUARD = "refuse-think-marker-in-content"

#: Model-fragment keys that shape the request or the serving flag; refused on a non-reasoning (Instruct) fragment.
THINKING_ONLY_KEYS = frozenset(
    {"reasoning_budget_tokens", "answer_reserve_tokens", "enable_thinking", "forced_close_message_sha256"}
)
FRAGMENT_KNOB_KEYS = THINKING_ONLY_KEYS | {"reasoning_context_policy"}
#: Keys a per-node ``thinking_policy`` entry may carry.
NODE_POLICY_KEYS = frozenset({"reasoning_budget_tokens", "answer_reserve_tokens", "enable_thinking"})
#: Wire fields the knobs fold into ``decoding_params``.
WIRE_BUDGET_KEY = "thinking_budget_tokens"
WIRE_TEMPLATE_KWARGS_KEY = "chat_template_kwargs"
REASONING_WIRE_KEYS = frozenset({WIRE_BUDGET_KEY, WIRE_TEMPLATE_KWARGS_KEY})

BUDGET_MESSAGE_FLAG = "--reasoning-budget-message"
THINKING_FALLBACK_SCHEMA = "saea-thinking-answer-fallback-v1"
#: One answer-only re-ask per contact; a row may need one per thinking node. Family-level default used by plan ceilings.
FALLBACK_CONTACTS_PER_ROW_MODULE = 2
FALLBACK_CONTACTS_PER_ROW_DIRECT = 1

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReasoningKnobError(ValueError):
    """A reasoning knob is malformed, contradictory or declared where it is not allowed."""


def _int(value: object, name: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ReasoningKnobError(f"{name} must be an integer >= {minimum}, got {value!r}")
    return value


def is_thinking_fragment(values: Mapping[str, object]) -> bool:
    return values.get("reasoning_content_guard") == THINKING_FRAGMENT_GUARD


def budget_message_from_server_args(server_args: object) -> str | None:
    """The ``--reasoning-budget-message`` value in a fragment's ``server_args`` (both argv spellings), else None."""

    if not isinstance(server_args, Sequence) or isinstance(server_args, (str, bytes)):
        return None
    tokens = [str(token) for token in server_args]
    found: str | None = None
    for index, token in enumerate(tokens):
        if token == BUDGET_MESSAGE_FLAG:
            if index + 1 >= len(tokens):
                raise ReasoningKnobError(f"{BUDGET_MESSAGE_FLAG} has no value in server_args")
            value = tokens[index + 1]
        elif token.startswith(BUDGET_MESSAGE_FLAG + "="):
            value = token.split("=", 1)[1]
        else:
            continue
        if found is not None:
            raise ReasoningKnobError(f"{BUDGET_MESSAGE_FLAG} is declared twice in server_args")
        found = value
    return found


def message_sha256(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def validate_fragment_knobs(values: Mapping[str, object]) -> None:
    """Validate the model-fragment knobs of a composed (or single model) config. No-op when none is declared."""

    declared = FRAGMENT_KNOB_KEYS & set(values)
    decoding = values.get("decoding_params")
    decoding = decoding if isinstance(decoding, Mapping) else {}
    message = budget_message_from_server_args(values.get("server_args"))
    if not declared:
        if message is not None:
            raise ReasoningKnobError(
                f"server_args carries {BUDGET_MESSAGE_FLAG} but the fragment pins no forced_close_message_sha256"
            )
        _refuse_direct_wire_keys(decoding, declared=False, values=values)
        return
    thinking = is_thinking_fragment(values)
    refused = sorted((THINKING_ONLY_KEYS & set(values)) if not thinking else ())
    if refused:
        raise ReasoningKnobError(
            f"reasoning knobs {refused} are valid only on a reasoning fragment (reasoning_content_guard); an Instruct "
            "fragment may declare reasoning_context_policy alone"
        )
    _refuse_direct_wire_keys(decoding, declared=True, values=values)
    budget = values.get("reasoning_budget_tokens")
    reserve = values.get("answer_reserve_tokens")
    enable = values.get("enable_thinking")
    if budget is not None:
        _int(budget, "reasoning_budget_tokens", minimum=0)
    if reserve is not None:
        _int(reserve, "answer_reserve_tokens", minimum=1)
        if budget is None:
            raise ReasoningKnobError("answer_reserve_tokens requires reasoning_budget_tokens")
    if "enable_thinking" in values and not isinstance(enable, bool):
        raise ReasoningKnobError("enable_thinking must be a boolean")
    if enable is False and budget is not None:
        raise ReasoningKnobError("reasoning_budget_tokens contradicts enable_thinking false")
    max_tokens = decoding.get("max_tokens")
    if budget is not None and max_tokens is not None:
        _int(max_tokens, "decoding_params.max_tokens", minimum=1)
        if reserve is not None and max_tokens != budget + reserve:
            raise ReasoningKnobError(
                f"decoding_params.max_tokens ({max_tokens}) must equal reasoning_budget_tokens + answer_reserve_tokens "
                f"({budget} + {reserve})"
            )
        if reserve is None and max_tokens <= budget:
            raise ReasoningKnobError("decoding_params.max_tokens must exceed reasoning_budget_tokens")
    if reserve is not None and max_tokens is None:
        raise ReasoningKnobError("answer_reserve_tokens requires decoding_params.max_tokens")
    policy = values.get("reasoning_context_policy")
    if "reasoning_context_policy" in values and policy not in REASONING_CONTEXT_POLICIES:
        raise ReasoningKnobError(
            f"reasoning_context_policy must be one of {sorted(REASONING_CONTEXT_POLICIES)}, got {policy!r}"
        )
    pinned = values.get("forced_close_message_sha256")
    if "forced_close_message_sha256" in values:
        if not isinstance(pinned, str) or _SHA256.fullmatch(pinned) is None:
            raise ReasoningKnobError("forced_close_message_sha256 must be a lowercase 64-hex digest")
        if message is None:
            raise ReasoningKnobError(
                f"forced_close_message_sha256 is pinned but server_args carries no {BUDGET_MESSAGE_FLAG}"
            )
        if message_sha256(message) != pinned:
            raise ReasoningKnobError(
                f"sha256 of the {BUDGET_MESSAGE_FLAG} value in server_args differs from forced_close_message_sha256"
            )
    elif message is not None:
        raise ReasoningKnobError(
            f"server_args carries {BUDGET_MESSAGE_FLAG} but the fragment pins no forced_close_message_sha256"
        )


def _refuse_direct_wire_keys(decoding: Mapping[str, object], *, declared: bool, values: Mapping[str, object]) -> None:
    """A wire field in ``decoding_params`` must come from the knobs: equal to the folded value (an already composed config
    re-validates cleanly) or absent. Without any declared knob the fields may not appear at all in a model fragment."""

    expected = fragment_wire_params(values) if declared else {}
    stray = sorted(key for key in REASONING_WIRE_KEYS & set(decoding) if decoding[key] != expected.get(key, object()))
    if stray:
        raise ReasoningKnobError(
            f"decoding_params must not carry {stray} directly; declare the reasoning knobs, which fold into them"
        )


def fragment_wire_params(values: Mapping[str, object]) -> dict[str, object]:
    """The per-request wire fields the fragment knobs fold into ``decoding_params`` (``{}`` when none is declared)."""

    wire: dict[str, object] = {}
    if values.get("reasoning_budget_tokens") is not None:
        wire[WIRE_BUDGET_KEY] = int(values["reasoning_budget_tokens"])  # type: ignore[arg-type]
    if "enable_thinking" in values:
        wire[WIRE_TEMPLATE_KWARGS_KEY] = {"enable_thinking": bool(values["enable_thinking"])}
    return wire


def fold_into_decoding(values: Mapping[str, object]) -> dict[str, object] | None:
    """A copy of ``values`` whose ``decoding_params`` carries the folded wire fields; ``None`` when nothing folds.

    The only function that turns knobs into request fields, so the fragment keys stay the single hashed source.
    """

    wire = fragment_wire_params(values)
    if not wire:
        return None
    decoding = values.get("decoding_params")
    folded = dict(decoding) if isinstance(decoding, Mapping) else {}
    folded.update(wire)
    out = dict(values)
    out["decoding_params"] = folded
    return out


def validate_request_controls(decoding_params: Mapping[str, object]) -> None:
    """Shape of the two wire fields; raises :class:`ReasoningKnobError`."""

    if WIRE_BUDGET_KEY in decoding_params:
        _int(decoding_params[WIRE_BUDGET_KEY], WIRE_BUDGET_KEY, minimum=0)
    if WIRE_TEMPLATE_KWARGS_KEY in decoding_params:
        kwargs = decoding_params[WIRE_TEMPLATE_KWARGS_KEY]
        if (
            not isinstance(kwargs, Mapping)
            or set(kwargs) != {"enable_thinking"}
            or not isinstance(kwargs["enable_thinking"], bool)
        ):
            raise ReasoningKnobError('chat_template_kwargs must be exactly {"enable_thinking": <bool>}')
        if kwargs["enable_thinking"] is False and WIRE_BUDGET_KEY in decoding_params:
            raise ReasoningKnobError("thinking_budget_tokens contradicts enable_thinking false")


# --- per-node policy -------------------------------------------------------------------------------------------------


def validate_thinking_policy(policy: object, values: Mapping[str, object]) -> None:
    """Validate a ``thinking_policy`` map against the composed config. ``None`` is absent."""

    if policy is None:
        return
    if not isinstance(policy, Mapping) or not policy:
        raise ReasoningKnobError("thinking_policy must be a non-empty mapping of node id to override")
    if not is_thinking_fragment(values):
        raise ReasoningKnobError("thinking_policy is valid only on a reasoning fragment (reasoning_content_guard)")
    decoding = values.get("decoding_params")
    base_cap = decoding.get("max_tokens") if isinstance(decoding, Mapping) else None
    base_cap = _int(base_cap, "decoding_params.max_tokens", minimum=1) if base_cap is not None else None
    folded = fold_into_decoding(values)
    base = dict((folded or values).get("decoding_params") or {}) if isinstance((folded or values).get("decoding_params"), Mapping) else {}
    for node, entry in policy.items():
        if not isinstance(node, str) or not node:
            raise ReasoningKnobError("thinking_policy node ids must be non-empty strings")
        if not isinstance(entry, Mapping) or not entry or set(entry) - NODE_POLICY_KEYS:
            raise ReasoningKnobError(
                f"thinking_policy[{node!r}] must be a non-empty mapping over {sorted(NODE_POLICY_KEYS)}"
            )
        if "reasoning_budget_tokens" in entry:
            _int(entry["reasoning_budget_tokens"], f"thinking_policy[{node!r}].reasoning_budget_tokens", minimum=0)
        if "answer_reserve_tokens" in entry:
            _int(entry["answer_reserve_tokens"], f"thinking_policy[{node!r}].answer_reserve_tokens", minimum=1)
        if "enable_thinking" in entry and not isinstance(entry["enable_thinking"], bool):
            raise ReasoningKnobError(f"thinking_policy[{node!r}].enable_thinking must be a boolean")
        # A full resolution proves the node is coherent against the fragment defaults (and the geometry cap).
        resolve_node_decoding(base, policy, node, cap=base_cap)


def resolve_node_decoding(
    base: Mapping[str, object], policy: Mapping[str, object] | None, node: str, *, cap: int | None = None
) -> dict[str, object]:
    """``base`` decoding params with the node's thinking override applied; ``base`` unchanged (a copy) without one.

    Defaults come from ``base`` itself: budget = ``thinking_budget_tokens``, reserve = ``max_tokens`` - budget, thinking on
    unless ``chat_template_kwargs.enable_thinking`` is false. Refuses a node whose ``max_tokens`` exceeds ``cap`` (the geometry).
    """

    out = dict(base)
    if not policy or node not in policy:
        return out
    entry = policy[node]
    base_budget = base.get(WIRE_BUDGET_KEY)
    base_cap = base.get("max_tokens")
    base_reserve = (
        base_cap - base_budget
        if isinstance(base_budget, int) and isinstance(base_cap, int) and not isinstance(base_budget, bool)
        else None
    )
    template_kwargs = base.get(WIRE_TEMPLATE_KWARGS_KEY)
    base_enable = template_kwargs.get("enable_thinking", True) if isinstance(template_kwargs, Mapping) else True
    budget = entry.get("reasoning_budget_tokens", base_budget)
    reserve = entry.get("answer_reserve_tokens", base_reserve)
    enable = entry.get("enable_thinking", base_enable)
    if enable is False:
        if "reasoning_budget_tokens" in entry:
            raise ReasoningKnobError(f"thinking_policy[{node!r}]: reasoning_budget_tokens contradicts enable_thinking false")
        if reserve is None:
            raise ReasoningKnobError(f"thinking_policy[{node!r}]: a no-think node needs an answer_reserve_tokens")
        out.pop(WIRE_BUDGET_KEY, None)
        out[WIRE_TEMPLATE_KWARGS_KEY] = {"enable_thinking": False}
        out["max_tokens"] = reserve
    else:
        if budget is None:
            raise ReasoningKnobError(f"thinking_policy[{node!r}]: a thinking node needs a reasoning budget")
        out[WIRE_BUDGET_KEY] = budget
        if reserve is None:
            raise ReasoningKnobError(f"thinking_policy[{node!r}]: a thinking node needs an answer reserve")
        out["max_tokens"] = budget + reserve
        if isinstance(template_kwargs, Mapping) or "enable_thinking" in entry:
            out[WIRE_TEMPLATE_KWARGS_KEY] = {"enable_thinking": True}
    if cap is not None and out["max_tokens"] > cap:
        raise ReasoningKnobError(
            f"thinking_policy[{node!r}] max_tokens {out['max_tokens']} exceeds the geometry cap {cap}"
        )
    return out


# --- fallback (decision 278) -----------------------------------------------------------------------------------------


def fallback_reserve(decoding_params: Mapping[str, object]) -> int | None:
    """The answer reserve a thinking request leaves (``max_tokens`` - budget), or None when the request is not a budgeted
    thinking request (no budget, thinking disabled, or no room for an answer): such a request has no fallback."""

    budget = decoding_params.get(WIRE_BUDGET_KEY)
    max_tokens = decoding_params.get("max_tokens")
    if isinstance(budget, bool) or not isinstance(budget, int):
        return None
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= budget:
        return None
    kwargs = decoding_params.get(WIRE_TEMPLATE_KWARGS_KEY)
    if isinstance(kwargs, Mapping) and kwargs.get("enable_thinking") is False:
        return None
    return max_tokens - budget


def answer_only_decoding(decoding_params: Mapping[str, object]) -> dict[str, object]:
    """The re-ask's decoding params: thinking off, ``max_tokens`` = the reserve, nothing else changed."""

    reserve = fallback_reserve(decoding_params)
    if reserve is None:
        raise ReasoningKnobError("this request has no answer reserve to fall back to")
    out = {key: value for key, value in decoding_params.items() if key != WIRE_BUDGET_KEY}
    out[WIRE_TEMPLATE_KWARGS_KEY] = {"enable_thinking": False}
    out["max_tokens"] = reserve
    return out


def fallback_receipt(
    *,
    agent_contact_id: object,
    first_request_id: object,
    reask_request_id: object,
    first_finish_reason: object,
    reask_finish_reason: object,
    first_tokens: Mapping[str, object],
    reask_tokens: Mapping[str, object],
    reserve: int,
    answered: bool,
) -> dict[str, object]:
    """The ``saea-thinking-answer-fallback-v1`` receipt: ids, finish reasons and token counts only -- never text."""

    def count(tokens: Mapping[str, object], key: str) -> int | None:
        value = tokens.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    return {
        "schema": THINKING_FALLBACK_SCHEMA,
        "agent_contact_id": agent_contact_id,
        "attempt": 1,
        "first_request_id": first_request_id,
        "reask_request_id": reask_request_id,
        "first_finish_reason": first_finish_reason if isinstance(first_finish_reason, str) else None,
        "reask_finish_reason": reask_finish_reason if isinstance(reask_finish_reason, str) else None,
        "first_prompt_tokens": count(first_tokens, "prompt_tokens"),
        "first_completion_tokens": count(first_tokens, "completion_tokens"),
        "reask_prompt_tokens": count(reask_tokens, "prompt_tokens"),
        "reask_completion_tokens": count(reask_tokens, "completion_tokens"),
        "reask_enable_thinking": False,
        "reask_max_tokens": reserve,
        "answered": bool(answered),
        "disposition": "answered-after-fallback" if answered else "empty-after-fallback-abstention",
    }


def fallback_contacts_per_row(policy_id: str, decoding_params: Mapping[str, object] | None) -> int:
    """Extra contacts a row's plan ceiling must allow for fallback re-asks: 0 unless the request is a budgeted thinking one."""

    if not decoding_params or fallback_reserve(decoding_params) is None:
        return 0
    if policy_id.startswith("phase-native-module-v1-c") or policy_id == "phase-native-module-v1":
        return FALLBACK_CONTACTS_PER_ROW_MODULE
    return FALLBACK_CONTACTS_PER_ROW_DIRECT


def last_cost_record(trace_buffer: object) -> tuple[str | None, Mapping[str, object]]:
    """``(record id, payload)`` of the most recent ``COST`` record in a trace buffer (duck-typed ``iter_records``)."""

    record_id: str | None = None
    cost: Mapping[str, object] = {}
    for channel, rid, payload in trace_buffer.iter_records():  # type: ignore[attr-defined]
        if channel == "COST" and isinstance(rid, str) and rid.endswith("/cost") and isinstance(payload, Mapping):
            record_id, cost = rid, payload
    return record_id, cost


def knobs_identity(values: Mapping[str, object]) -> dict[str, object]:
    """The declared knob document (fragment knobs, pinned message hash, per-node policy), for receipts and hash tests."""

    doc: dict[str, object] = {key: values[key] for key in sorted(FRAGMENT_KNOB_KEYS & set(values))}
    if values.get("thinking_policy") is not None:
        doc["thinking_policy"] = values["thinking_policy"]
    return doc


def knobs_sha256(values: Mapping[str, object]) -> str:
    blob = json.dumps(knobs_identity(values), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


#: Owner decision 286 (2026-10-12): the model's native reasoning trajectory is not a controllable input of the control plane, so its
#: bytes are never part of the sealed trace. The trace keeps only the hash of the exact bytes as received plus statistics. Recorded in
#: the transport envelope, the stored wire message and the COST record so a sealed trace says which policy produced it.
REASONING_BYTES_POLICY = "hash-and-stats-only-v1"

#: Owner ruling 330 A (2026-10-18): the ONE bounded diagnostic exception to decision 286. A transport armed with a
#: :class:`ReasoningRetention` writes the reasoning bytes of each response to a file under the data root and nowhere else; the
#: stored wire response, the envelope ``reasoning`` object and every trace record are still the decision-286 projection. The
#: exception is a constructor argument that only a plan naming :data:`DIAGNOSTIC_RUN_ID` can build; a model fragment cannot declare it.
RETAIN_DIAGNOSTIC_POLICY = "retain-diagnostic-v1"
REASONING_BYTES_POLICIES = frozenset({REASONING_BYTES_POLICY, RETAIN_DIAGNOSTIC_POLICY})
DIAGNOSTIC_RUN_ID = "SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-V1"
DIAGNOSTIC_PROFILE = "bounded-discovery-probe"
DIAGNOSTIC_ROOT_PARTS = ("diagnostics", DIAGNOSTIC_RUN_ID)
_SAMPLE_FILE_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


class ReasoningRetention:
    """Where the diagnostic run's reasoning bytes go, and the only way to obtain a writer for it.

    ``from_plan`` refuses any plan whose run id is not :data:`DIAGNOSTIC_RUN_ID` (or whose profile is not the bounded probe), and a
    data root that is not an existing directory. Files are created exclusively (one attempt per sample and budget: an existing file is
    never overwritten) under ``<data root>/diagnostics/<run id>/reasoning/``. The returned receipt carries the path relative to the
    diagnostic root, the sha256 of the exact UTF-8 bytes written and their counts -- never the text.
    """

    def __init__(self, *, _token: object, run_id: str, directory: Path) -> None:
        if _token is not _CONSTRUCTION_TOKEN:
            raise ReasoningKnobError("a ReasoningRetention is built only by ReasoningRetention.from_plan")
        self.run_id = run_id
        self.directory = Path(directory)

    @classmethod
    def from_plan(cls, plan: object, data_root: Path) -> "ReasoningRetention":
        run_id = getattr(plan, "run_id", None)
        if run_id != DIAGNOSTIC_RUN_ID:
            raise ReasoningKnobError(
                f"reasoning retention is refused: the plan names run id {run_id!r}, not the diagnostic run {DIAGNOSTIC_RUN_ID!r} (ruling 330 A)"
            )
        if getattr(plan, "execution_profile", None) != DIAGNOSTIC_PROFILE:
            raise ReasoningKnobError(f"reasoning retention requires execution profile {DIAGNOSTIC_PROFILE!r}")
        root = Path(data_root)
        if not root.is_dir():
            raise ReasoningKnobError(f"reasoning retention requires an existing data root directory, got {str(root)!r}")
        return cls(_token=_CONSTRUCTION_TOKEN, run_id=run_id, directory=root.joinpath(*DIAGNOSTIC_ROOT_PARTS, "reasoning"))

    @property
    def diagnostic_root(self) -> Path:
        return self.directory.parent

    @staticmethod
    def file_name(sample_id: str, budget: object) -> str:
        if not isinstance(sample_id, str) or not sample_id:
            raise ReasoningKnobError("reasoning retention requires a non-empty sample id")
        stem = _SAMPLE_FILE_UNSAFE.sub("_", sample_id).strip(".") or "sample"
        if isinstance(budget, bool) or not isinstance(budget, int) or budget == 3072:
            return f"{stem}.txt"
        return f"{stem}.b{budget}.txt"

    def retain(self, sample_id: str, budget: object, reasoning_text: str) -> dict[str, object]:
        if not isinstance(reasoning_text, str):
            raise ReasoningKnobError("reasoning retention writes only string reasoning bytes")
        data = reasoning_text.encode("utf-8", "surrogatepass")
        self.directory.mkdir(parents=True, exist_ok=True)
        name = self.file_name(sample_id, budget)
        target = self.directory / name
        if target.resolve().parent != self.directory.resolve():
            raise ReasoningKnobError("reasoning retention path escaped its directory")
        digest = hashlib.sha256(data).hexdigest()
        with open(target, "xb") as handle:       # exclusive: one attempt per sample and budget
            handle.write(data)
        return {
            "policy": RETAIN_DIAGNOSTIC_POLICY, "run_id": self.run_id,
            "relpath": f"reasoning/{name}", "sha256": digest, "bytes": len(data), "chars": len(reasoning_text),
        }


_CONSTRUCTION_TOKEN = object()


def reasoning_summary(
    reasoning_text: object,
    forced_close_message: str | None,
    server_reasoning_tokens: object,
    finish_reason: object,
) -> dict[str, object]:
    """The stored projection of one response's reasoning channel (decision 286); never carries the text.

    ``reasoning_content_sha256`` is the sha256 of the exact UTF-8 bytes received (``None`` when the response had no string
    reasoning). ``forced_close`` is computed from the text BEFORE the bytes are dropped.
    """

    has_tokens = isinstance(server_reasoning_tokens, int) and not isinstance(server_reasoning_tokens, bool)
    is_text = isinstance(reasoning_text, str)
    return {
        "reasoning_content_sha256": hashlib.sha256(reasoning_text.encode("utf-8", "surrogatepass")).hexdigest() if is_text else None,
        "reasoning_chars": len(reasoning_text) if is_text else 0,
        "reasoning_tokens": server_reasoning_tokens if has_tokens else None,
        "reasoning_tokens_basis": "server-usage-details" if has_tokens else "not-reported-by-server",
        "forced_close": detect_forced_close(reasoning_text, forced_close_message),
        "forced_close_basis": (
            "reasoning-ends-with-pinned-budget-message" if forced_close_message else "no-pinned-budget-message"
        ),
        "finish_reason": finish_reason,
        "reasoning_bytes_policy": REASONING_BYTES_POLICY,
    }


def project_reasoning_out_of_wire(
    parsed: object, raw: bytes, forced_close_message: str | None,
) -> tuple[bytes, dict[str, object] | None]:
    """Return ``(stored_wire_bytes, summary)`` for one parsed server response.

    A response whose first choice message carries a ``reasoning_content`` key is re-serialized with that key REMOVED and a
    ``reasoning`` object (:func:`reasoning_summary`) in its place; ``parsed`` is mutated the same way so no later reader can reach the
    bytes. Any other response returns ``(raw, None)`` untouched, byte for byte.
    """

    try:
        choice = parsed["choices"][0]  # type: ignore[index]
        message = choice["message"]
    except (KeyError, IndexError, TypeError):
        return raw, None
    if not isinstance(message, dict) or "reasoning_content" not in message:
        return raw, None
    usage = parsed.get("usage") if isinstance(parsed, Mapping) else None
    details = usage.get("completion_tokens_details") if isinstance(usage, Mapping) else None
    server_tokens = details.get("reasoning_tokens") if isinstance(details, Mapping) else None
    summary = reasoning_summary(
        message["reasoning_content"], forced_close_message, server_tokens,
        choice.get("finish_reason") if isinstance(choice, Mapping) else None,
    )
    del message["reasoning_content"]
    message["reasoning"] = dict(summary)
    return json.dumps(parsed).encode("utf-8"), summary


def detect_forced_close(reasoning_text: object, forced_close_message: str | None) -> bool | None:
    """True when the reasoning channel ends with the pinned budget message (the sampler forces MESSAGE + end tag).

    ``None`` when no message is pinned or no reasoning text came back (the close cannot be detected from bytes).
    """

    if not forced_close_message or not isinstance(reasoning_text, str) or not reasoning_text:
        return None
    return reasoning_text.rstrip().endswith(forced_close_message.strip())
