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

import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "saea-tfrl-archive-state-v1"
CORRECTION_SCHEMA = "saea-tfrl-archive-correction-v1"
#: A re-measurement of an already archived state (a later iteration proposed the same artefact set again). The archived state is
#: write-once and stays untouched; the new read is a sibling record under ``<archive_dir>/rereads/``.
REREAD_SCHEMA = "saea-tfrl-archive-reread-v1"
#: A refused candidate whose artefact set equals an already archived state (any status) is a duplicate of that sibling.
DUPLICATE_OF_ARCHIVED = "duplicate-of-archived"
#: A refused state that carries no measurement (the instrument could not read the candidate) names why.
UNMEASURED_REFUSAL_CODES = ("offline-family-unsupported",)
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
    run_id: str | None = None, attempt: int | None = None, refusal_code: str | None = None,
) -> dict[str, Any]:
    if verdict not in VERDICTS:
        _fail(f"verdict must be one of {VERDICTS}")
    if arm not in ARMS:
        _fail(f"arm must be one of {ARMS}")
    if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 0:
        _fail("iteration must be a non-negative integer (0 = the lock root)")
    if iteration > 0 and (operator_class is None or candidate_id is None):
        _fail("a non-root state records the operator class and candidate id that produced it")
    if refusal_code is not None:
        if verdict != "refused" or refusal_code not in UNMEASURED_REFUSAL_CODES:
            _fail(f"refusal_code is only for a refused, unmeasured state; known codes {UNMEASURED_REFUSAL_CODES}")
        if credit is not None:
            _fail("an unmeasured refusal carries no credit vector")
    if verdict == "unflown":
        if credit is not None or run_id is not None:
            _fail("an unflown state carries no credit vector and no read")
    elif refusal_code is not None:
        pass        # refused without a measurement: the refusal code stands for the read
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
    if refusal_code is not None:
        state["refusal_code"] = refusal_code
    if state["state_id"] == parent_id:
        _fail("a state cannot be its own parent")
    assert_no_text_fields(state)
    return state


def validate_correction(record: Any) -> None:
    """A correction record is identifiers and hashes only: the state, the artefact slot, the wrong and the right value, the
    cause code and the receipt the right value derives from."""

    keys = {"schema", "state_id", "artefact", "slug", "wrong", "right", "cause", "derives_from"}
    if not isinstance(record, Mapping) or set(record) != keys or record["schema"] != CORRECTION_SCHEMA:
        _fail(f"a correction record carries exactly {sorted(keys)} and schema {CORRECTION_SCHEMA}")
    if record["artefact"] not in ARTEFACT_NAMES:
        _fail(f"correction artefact must be one of {ARTEFACT_NAMES}")
    for key in ("state_id", "wrong", "right"):
        if not isinstance(record[key], str) or not _HEX64.match(record[key]):
            _fail(f"correction.{key}: must be 64 lowercase hex characters")
    if record["wrong"] == record["right"]:
        _fail("a correction must change the value")
    if not isinstance(record["slug"], str) or not re.match(r"^[a-z0-9-]{1,60}$", record["slug"]):
        _fail("correction.slug: lowercase letters, digits and dashes only")
    derives = record["derives_from"]
    if (not isinstance(derives, Mapping) or set(derives) != {"receipt", "field", "receipt_sha256"}
            or not isinstance(derives["receipt_sha256"], str) or not _HEX64.match(derives["receipt_sha256"])):
        _fail("correction.derives_from must carry receipt, field and receipt_sha256")
    assert_no_text_fields(record)


def validate_reread(record: Any) -> None:
    """A reread record is identifiers, hashes and numbers only: the archived state it re-measures, the iteration and candidate that
    proposed it again, the column it was read on, and the fitted result (a full credit vector plus the verdict clauses)."""

    keys = {"schema", "state_id", "archived_verdict", "iteration", "candidate_id", "column", "reread_verdict", "clauses", "credit"}
    if not isinstance(record, Mapping) or set(record) != keys or record["schema"] != REREAD_SCHEMA:
        _fail(f"a reread record carries exactly {sorted(keys)} and schema {REREAD_SCHEMA}")
    for key in ("state_id", "candidate_id"):
        if not isinstance(record[key], str) or not _HEX64.match(record[key]):
            _fail(f"reread.{key}: must be 64 lowercase hex characters")
    if record["archived_verdict"] not in VERDICTS or record["reread_verdict"] not in ("accepted", "refused"):
        _fail("reread verdicts: archived_verdict is a state verdict, reread_verdict is accepted or refused")
    if not isinstance(record["iteration"], int) or isinstance(record["iteration"], bool) or record["iteration"] < 1:
        _fail("reread.iteration must be an integer >= 1")
    column = record["column"]
    if not isinstance(column, Mapping) or set(column) != {"run_id", "attempt"} or not isinstance(column["attempt"], int):
        _fail("reread.column must carry exactly run_id and attempt")
    if not isinstance(record["clauses"], Mapping):
        _fail("reread.clauses must be an object")
    validate_credit(record["credit"])
    assert_no_text_fields(record)


class Archive:
    """Write-once directory of state files (plus write-once correction records under ``corrections/`` and write-once reread records
    under ``rereads/``). Neither sibling directory is a state: :meth:`states` (and so parent choice) reads ``state-*.json`` only."""

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

    # ---- corrections: a state file is write-once, so a wrong recorded value is superseded by a correction RECORD
    # (``<archive_dir>/corrections/state-<state_id>-<slug>.json``) that the readers apply. The state keeps its
    # ``state_id`` (its identity in the lineage); only the named artefact hash changes in the read view, and the view
    # carries ``corrections`` naming what was applied.

    def _correction_dir(self) -> Path:
        return self.directory / "corrections"

    def correction_paths(self) -> list[Path]:
        directory = self._correction_dir()
        return sorted(directory.glob("state-*.json")) if directory.is_dir() else []

    def put_correction(self, correction: Mapping[str, Any]) -> Path:
        """Write one correction record (write-once, exclusive open); the target state must exist and hold the wrong value."""

        validate_correction(correction)
        state = self._read_raw(correction["state_id"])
        name = correction["artefact"]
        if state["artefact_hashes"].get(name) != correction["wrong"]:
            _fail(f"state {correction['state_id'][:12]} does not record the wrong {name} the correction names")
        directory = self._correction_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"state-{correction['state_id']}-{correction['slug']}.json"
        data = json.dumps(dict(correction), indent=2, sort_keys=True) + "\n"
        try:
            with open(path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(data)
        except FileExistsError:
            _fail(f"correction {path.name} is already recorded (write-once)")
        return path

    def corrections(self) -> list[dict[str, Any]]:
        out = []
        for path in self.correction_paths():
            record = json.loads(path.read_text(encoding="utf-8"))
            validate_correction(record)
            out.append(record)
        return out

    # ---- rereads: the archived state of a duplicate proposal is never rewritten; the new measurement is a sibling record
    # ``<archive_dir>/rereads/<state_id>-i<iteration>.json`` (write-once; an identical re-run is accepted, a different one refused).

    def _reread_dir(self) -> Path:
        return self.directory / "rereads"

    def put_reread(self, record: Mapping[str, Any]) -> tuple[Path, bool]:
        """Write one reread record; the archived state must exist. Returns ``(path, created)``."""

        validate_reread(record)
        self._read_raw(record["state_id"])           # the re-measured state exists
        directory = self._reread_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{record['state_id']}-i{record['iteration']}.json"
        data = json.dumps(dict(record), indent=2, sort_keys=True) + "\n"
        try:
            with open(path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(data)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != data:
                _fail(f"reread {path.name} is already recorded with different content (write-once)")
            return path, False
        return path, True

    def reread_paths(self) -> list[Path]:
        directory = self._reread_dir()
        return sorted(directory.glob("*-i*.json")) if directory.is_dir() else []

    def rereads(self) -> list[dict[str, Any]]:
        out = []
        for path in self.reread_paths():
            record = json.loads(path.read_text(encoding="utf-8"))
            validate_reread(record)
            out.append(record)
        return out

    def _read_raw(self, state_id: str) -> dict[str, Any]:
        path = self._path(state_id)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except OSError as error:
            raise ArchiveError(f"cannot read state {state_id}: {error}") from error

    @staticmethod
    def _apply_corrections(state: dict[str, Any], records: list[Mapping[str, Any]]) -> dict[str, Any]:
        mine = [r for r in records if r["state_id"] == state["state_id"]]
        if not mine:
            return state
        view = copy.deepcopy(state)
        applied = []
        for record in sorted(mine, key=lambda r: r["slug"]):
            name = record["artefact"]
            if view["artefact_hashes"].get(name) != record["wrong"]:
                _fail(f"correction {record['slug']} of state {state['state_id'][:12]}: "
                      f"the recorded {name} is not the wrong value it names")
            view["artefact_hashes"][name] = record["right"]
            applied.append({"artefact": name, "wrong": record["wrong"], "right": record["right"], "slug": record["slug"]})
        view["artefact_hashes"] = dict(sorted(view["artefact_hashes"].items()))
        view["corrections"] = applied
        return view

    def get(self, state_id: str) -> dict[str, Any]:
        return self._apply_corrections(self._read_raw(state_id), self.corrections())

    def states(self) -> list[dict[str, Any]]:
        if not self.directory.is_dir():
            return []
        records = self.corrections()
        out = [self._apply_corrections(json.loads(p.read_text(encoding="utf-8")), records)
               for p in sorted(self.directory.glob("state-*.json"))]
        out.sort(key=lambda s: (s["iteration"], s["state_id"]))
        return out

    def children(self, state_id: str) -> list[dict[str, Any]]:
        return [s for s in self.states() if s["parent_id"] == state_id]


__all__ = [
    "ArchiveError", "Archive", "build_state", "compute_state_id", "validate_credit",
    "assert_no_text_fields", "forbidden_key", "SCHEMA", "ARTEFACT_NAMES", "VERDICTS", "ARMS",
    "CORRECTION_SCHEMA", "UNMEASURED_REFUSAL_CODES", "validate_correction",
    "REREAD_SCHEMA", "DUPLICATE_OF_ARCHIVED", "validate_reread",
]
