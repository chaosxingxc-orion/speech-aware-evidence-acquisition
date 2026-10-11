"""File-backed archive of typed system STATES (owner decision 263 A, RSI shape; spec
``docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md``
section 1.3 and 5.4).

One JSON file per state, ``<archive_dir>/state-<state_id>.json``, created with exclusive
open: a state is write-once, and a second write of the same ``state_id`` (a candidate
byte-identical to an archived state) is refused. Refused candidates are stored too; they
are siblings and negative evidence.

``state_id`` = sha256 over the canonical JSON of the sorted ``"<artefact>:<hash>"`` pairs
of the state's artefact set (name-qualified so one hash used in two slots cannot collide
with a different assignment).

The archive carries identifiers, hashes and numbers only. Every record is scanned for
text-bearing keys and for free-text string values before it is written (I-OBJ; no
utterance text, transcript, gold label or model output is ever persisted here).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "saea-tfrl-archive-state-v1"
ARTEFACT_NAMES = (
    "exemplar_index_release", "slot_store_release", "key_view", "supply_fragment",
    "delivery_rule_table", "scope_routing", "playbook_release",
)
VERDICTS = ("accepted", "refused", "unflown")
ARMS = ("typed", "ace")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_IDENT = re.compile(r"^[A-Za-z0-9_.:/@+\-]{0,200}$")
_FORBIDDEN_EXACT = frozenset({
    "answer", "answers", "output", "outputs", "prompt", "prompts", "response", "responses",
    "gold", "gold_label", "gold_labels", "label", "labels", "reference", "slot_value", "slot_values",
    "raw", "completion", "content", "message", "messages", "note", "notes", "summary", "hypothesis",
})
_FORBIDDEN_SUBSTRINGS = ("text", "transcript", "utterance", "sentence")
METRICS = ("slu", "intent")
CREDIT_KEYS = (
    "slu_f1", "intent", "vs_lock", "vs_twin", "vs_parent", "per_scenario",
    "false_fill", "non_empty_exact", "contacts_per_row",
)


class ArchiveError(RuntimeError):
    pass


def _fail(message: str) -> None:
    raise ArchiveError(message)


def forbidden_key(key: str) -> bool:
    k = str(key).lower()
    return k in _FORBIDDEN_EXACT or any(s in k for s in _FORBIDDEN_SUBSTRINGS)


def assert_no_text_fields(value: Any, where: str = "$") -> None:
    """Refuse any text-bearing key or free-text string value, recursively."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(f"{where}: non-string key {key!r}")
            if forbidden_key(key):
                _fail(f"{where}.{key}: text-bearing field name is forbidden")
            assert_no_text_fields(item, f"{where}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            assert_no_text_fields(item, f"{where}[{index}]")
    elif isinstance(value, str):
        if not _IDENT.match(value):
            _fail(f"{where}: free-text string value refused (identifiers only)")
    elif isinstance(value, float):
        if not math.isfinite(value):
            _fail(f"{where}: non-finite number")


def compute_state_id(artefact_hashes: Mapping[str, str]) -> str:
    if not artefact_hashes:
        _fail("a state needs at least one artefact hash")
    pairs = []
    for name, digest in artefact_hashes.items():
        if name not in ARTEFACT_NAMES:
            _fail(f"unknown artefact {name!r}; allowed {ARTEFACT_NAMES}")
        if not isinstance(digest, str) or not _HEX64.match(digest):
            _fail(f"artefact {name!r}: hash must be 64 lowercase hex characters")
        pairs.append(f"{name}:{digest}")
    payload = json.dumps(sorted(pairs), separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _check_ci(ci: Any, where: str) -> None:
    if not isinstance(ci, Mapping) or set(ci) != {"point", "lo", "hi"}:
        _fail(f"{where}: must be an object with exactly point, lo, hi (percentage points)")
    for key in ("point", "lo", "hi"):
        if isinstance(ci[key], bool) or not isinstance(ci[key], (int, float)) or not math.isfinite(ci[key]):
            _fail(f"{where}.{key}: must be a finite number")
    if not ci["lo"] <= ci["point"] <= ci["hi"]:
        _fail(f"{where}: requires lo <= point <= hi")


def _check_delta_block(block: Any, where: str) -> None:
    if not isinstance(block, Mapping) or set(block) != set(METRICS):
        _fail(f"{where}: must carry exactly {METRICS}")
    for metric in METRICS:
        _check_ci(block[metric], f"{where}.{metric}")


def validate_credit(credit: Any) -> None:
    """Credit vector layout (all deltas in percentage points, paired, CI95):

    ``slu_f1`` / ``intent``: the column's own official score (points);
    ``vs_lock`` (required), ``vs_twin`` and ``vs_parent`` (null when no such column):
    ``{"slu": {point, lo, hi}, "intent": {point, lo, hi}}``;
    ``per_scenario``: ``{scenario_id: {"slu": pp, "intent": pp}}``;
    ``false_fill`` / ``non_empty_exact``: ``{"n": int, "delta_pp": pp}`` (empty vs non-empty gold);
    ``contacts_per_row``: float.
    """

    if not isinstance(credit, Mapping) or set(credit) != set(CREDIT_KEYS):
        _fail(f"credit must carry exactly {CREDIT_KEYS}")
    for key in ("slu_f1", "intent", "contacts_per_row"):
        if isinstance(credit[key], bool) or not isinstance(credit[key], (int, float)):
            _fail(f"credit.{key}: must be a number")
    _check_delta_block(credit["vs_lock"], "credit.vs_lock")
    for key in ("vs_twin", "vs_parent"):
        if credit[key] is not None:
            _check_delta_block(credit[key], f"credit.{key}")
    scen = credit["per_scenario"]
    if not isinstance(scen, Mapping):
        _fail("credit.per_scenario must be an object")
    for sid, row in scen.items():
        if not isinstance(row, Mapping) or set(row) != set(METRICS):
            _fail(f"credit.per_scenario.{sid}: must carry exactly {METRICS}")
        for metric in METRICS:
            if isinstance(row[metric], bool) or not isinstance(row[metric], (int, float)):
                _fail(f"credit.per_scenario.{sid}.{metric}: must be a number")
    for key in ("false_fill", "non_empty_exact"):
        block = credit[key]
        if not isinstance(block, Mapping) or set(block) != {"n", "delta_pp"}:
            _fail(f"credit.{key}: must carry exactly n and delta_pp")
        if not isinstance(block["n"], int) or isinstance(block["n"], bool) or block["n"] < 0:
            _fail(f"credit.{key}.n: must be a non-negative integer")


def build_state(
    *, artefact_hashes: Mapping[str, str], parent_id: str | None, iteration: int,
    operator_class: str | None, candidate_id: str | None, verdict: str, arm: str = "typed",
    credit: Mapping[str, Any] | None = None, predicted_slu_pp: float | None = None,
    run_id: str | None = None, attempt: int | None = None,
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        _fail(f"verdict must be one of {VERDICTS}")
    if arm not in ARMS:
        _fail(f"arm must be one of {ARMS}")
    if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 0:
        _fail("iteration must be a non-negative integer (0 = the lock root)")
    if iteration > 0 and (operator_class is None or candidate_id is None):
        _fail("a non-root state records the operator class and candidate id that produced it")
    if verdict == "unflown":
        if credit is not None or run_id is not None:
            _fail("an unflown state carries no credit vector and no read")
    else:
        if credit is None:
            _fail(f"a {verdict} state needs its measured credit vector")
        if run_id is None or attempt is None:
            _fail(f"a {verdict} state needs the read's run id and attempt")
        validate_credit(credit)
    state = {
        "schema": SCHEMA,
        "state_id": compute_state_id(artefact_hashes),
        "artefact_hashes": dict(sorted(artefact_hashes.items())),
        "parent_id": parent_id,
        "iteration": iteration,
        "arm": arm,
        "operator_class": operator_class,
        "candidate_id": candidate_id,
        "predicted_slu_pp": predicted_slu_pp,
        "verdict": verdict,
        "credit": dict(credit) if credit is not None else None,
        "read": {"run_id": run_id, "attempt": attempt} if run_id is not None else None,
    }
    if state["state_id"] == parent_id:
        _fail("a state cannot be its own parent")
    assert_no_text_fields(state)
    return state


class Archive:
    """Write-once directory of state files."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)

    def _path(self, state_id: str) -> Path:
        if not _HEX64.match(state_id):
            _fail(f"bad state id {state_id!r}")
        return self.directory / f"state-{state_id}.json"

    def put(self, state: Mapping[str, Any]) -> Path:
        if state.get("schema") != SCHEMA:
            _fail("not an archive state (use build_state)")
        if compute_state_id(state["artefact_hashes"]) != state["state_id"]:
            _fail("state_id does not match its artefact hashes")
        assert_no_text_fields(state)
        parent = state["parent_id"]
        if parent is not None and not self._path(parent).exists():
            _fail(f"parent {parent} is not in the archive")
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(state["state_id"])
        data = json.dumps(state, indent=2, sort_keys=True) + "\n"
        try:
            with open(path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(data)
        except FileExistsError:
            _fail(
                f"state {state['state_id']} is already archived (write-once; a candidate "
                "identical to an archived state is refused)"
            )
        return path

    def get(self, state_id: str) -> dict[str, Any]:
        path = self._path(state_id)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise ArchiveError(f"cannot read state {state_id}: {error}") from error

    def states(self) -> list[dict[str, Any]]:
        if not self.directory.is_dir():
            return []
        out = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(self.directory.glob("state-*.json"))]
        out.sort(key=lambda s: (s["iteration"], s["state_id"]))
        return out

    def children(self, state_id: str) -> list[dict[str, Any]]:
        return [s for s in self.states() if s["parent_id"] == state_id]


__all__ = [
    "ArchiveError", "Archive", "build_state", "compute_state_id", "validate_credit",
    "assert_no_text_fields", "forbidden_key", "SCHEMA", "ARTEFACT_NAMES", "VERDICTS", "ARMS",
]
