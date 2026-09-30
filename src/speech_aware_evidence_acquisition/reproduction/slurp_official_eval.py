"""Run the REAL, unmodified SLURP official evaluator as an identity check.

``reproduction.slurp_scoring`` re-implements the official
``scripts/evaluation/metrics/`` logic at per-sample granularity so
``TaskAdapter.score`` can score one response at a time; its own docstring
claims that summing per-sample TP/FP/FN across a split reproduces the
official corpus-level micro counts EXACTLY. This module is the proof: it
writes the exact input files the official ``scripts/evaluation/evaluate.py``
expects, runs that script UNMODIFIED as a subprocess against the
umbrella-governed local clone under ``SPEECHRL_DATA_DIR/repos/slurp`` (pinned
commit ``SLURP_OFFICIAL_COMMIT`` -- no network fetch, that repo's own git
history is the verification), parses its printed results, and compares them
against the port's own micro-aggregated numbers.

Official input/output formats (derived directly from
``scripts/evaluation/util.py`` at the pinned commit, read in full before
writing this module -- quoted verbatim in this study's own delivery report,
not re-derived here):

- ``load_predictions(path, load_gold=False)`` reads one JSON object per line
  and pops either ``"slurp_id"`` (``load_gold=True``, the upper-bound "gold
  transcription" mode) or ``"file"`` (the default mode) as the dict key the
  rest of the row is stored under -- the remaining fields are used AS-IS:
  ``scenario`` (str), ``action`` (str), ``entities`` (``[{"type":...,
  "filler":...}, ...]``).
- ``load_gold_data(path, load_gold=False)`` reads the SLURP "release" format
  (one JSON object per line, with ``tokens``: ``[{"id":int,"surface":str}]``,
  ``scenario``, ``action``, ``entities``: ``[{"type":str,"span":[token_id,
  ...]}]``, and ``recordings``: ``[{"file":str}, ...]``) and maps EVERY
  ``release2prediction`` line through the SAME "file" (or "slurp_id") key,
  reconstructing ``filler`` for gold entities as
  ``" ".join(tokens[i]["surface"].lower() for i in span)`` -- this is the
  join ``data.slurp._entity_filler`` already reproduces exactly, so a
  ``SlurpRecord.entities`` filler string round-trips losslessly through a
  synthetic ``tokens``/``span`` reconstruction (:func:`_tokens_and_spans`).
  Neither function's output nor ``evaluate.py``'s own scoring loop ever reads
  the release-format ``"text"`` field this module fabricates -- it exists
  only because ``release2prediction`` computes it unconditionally, so its
  exact word-splitting is irrelevant to every score.
- :func:`write_official_inputs` therefore always uses the DEFAULT
  ``load_gold=False`` ("file"-keyed) mode: this study's own outputs are
  per-recording (one row per ``SlurpRecord.sample_id``), which maps directly
  onto the official "file" key with no synthetic ``slurp_id`` needed, and
  keeps identical pairing semantics between the port's per-sample loop and
  the official corpus-level one -- both index by the SAME sample id.
- ``evaluate.py`` never reads ``args.load_gold`` outside those two loader
  calls; it prints six ``format_results`` tables in a FIXED order (scenario,
  action, ``"intent (scen_act)"``, entities, entities-distance-word,
  entities-distance-char) plus a seventh combined "SLU F1" table, and prints
  nothing else to stdout (logging/progress bars go to stderr) -- exploited by
  :func:`run_official_evaluate`'s ``--table-layout csv`` choice, which
  disables ``tabulate``'s floatfmt rounding entirely (``util.format_results``
  only rounds under the ``tabulate`` branch, never under ``csv``/``tsv``), so
  the parsed Precision/Recall/F-Measure carry full Python float precision --
  a tighter identity check than the human-readable default layout would
  allow.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..data.variant_ids import published_sample_key
from ..data.slurp import (
    SlurpRecord,
    load_slurp_intent_slot_schema,
    load_slurp_ontology,
    load_slurp_split,
)
from .slurp_scoring import (
    PROJECTION_BRANCHES,
    SLURP_LABEL_PROJECTION_ID,
    SLURP_LABEL_PROJECTION_V2_ID,
    SLURP_SCORER_VERSION,
    LegalIntentInventory,
    SlotEntity,
    SluScore,
    legal_intent_inventory,
    parse_slu_response,
    project_slu_label,
    project_slu_label_v2,
    score_slu,
)

# E4 (SLURP v2 base program, module M3): the v3 label rule and the P2 filler
# rule both live in ``rails.slurp_projection_v3`` (task instruction -- the
# shared function both the scorer and the runtime delivery transform call),
# not in ``reproduction.slurp_scoring`` beside v1/v2. Deliberately NOT
# imported at module scope: ``rails/__init__.py`` transitively imports
# ``core.scorers``, which imports THIS module, so a module-scope import here
# of anything under ``rails`` closes a cycle before this module finishes
# initializing. ``score_slurp_outputs_official`` below imports it locally
# instead (the same deferred-import discipline
# ``reproduction.slurp_delivery``'s own builders already use for their own
# ``rails`` references).
#: ``projection_version -> (rule identity, the pure rule function)`` for the
#: two rules that DO live in this package's own ``slurp_scoring`` sibling.
#: The rules are SIBLINGS, not a revision chain: v1 stays registered and
#: resolvable after v2 exists, so a verdict can pair against either. v3 is
#: resolved separately (see above) because its implementation lives in
#: ``rails``, not here.
_PROJECTION_RULES = {
    "v1": (SLURP_LABEL_PROJECTION_ID, project_slu_label),
    "v2": (SLURP_LABEL_PROJECTION_V2_ID, project_slu_label_v2),
}

#: Every ``projection_version`` value ``score_slurp_outputs_official``
#: accepts when ``project_labels=True`` -- the local table's own keys plus
#: ``"v3"``, which resolves through a deferred import instead.
_PROJECTION_VERSIONS = (*_PROJECTION_RULES, "v3")

# Pinned upstream commit (module docstring): the SAME commit
# ``reproduction.slurp_scoring``'s own docstring already names.
SLURP_OFFICIAL_COMMIT = "8eb16545762be97ace75334109d73824217311f1"
SLURP_OFFICIAL_SCORER_VERSION = f"slurp-official-{SLURP_OFFICIAL_COMMIT[:8]}"
SLURP_SLU_OFFICIAL_ALIGNED_SCORER_ID = "slurp-slu-official-aligned-v1"

# The pinned evaluator's own ``requirements.txt`` (jiwer==2.0.0, tabulate==0.8.7,
# textdistance==4.1.5, progress==1.5) is incompatible with the shared study
# venv (jiwer 4.x renamed ``truth`` -> ``reference``; tabulate 0.8.7 does not
# import on Python 3.12). The official script therefore runs, UNMODIFIED, in
# its own environment built from exactly that requirements file:
# ``~/.venvs/slurp-official-eval`` (Python 3.9, receipt
# ``docs/receipts/environments/slurp-official-eval.json``). Resolution order:
# ``SAEA_SLURP_OFFICIAL_PYTHON`` -> the default venv interpreter if present ->
# ``sys.executable`` (which will fail closed on the jiwer API mismatch).
SLURP_OFFICIAL_PYTHON_ENV = "SAEA_SLURP_OFFICIAL_PYTHON"
SLURP_OFFICIAL_VENV_PYTHON = Path.home() / ".venvs" / "slurp-official-eval" / "bin" / "python"
SLURP_OFFICIAL_ENV_RECEIPT = "docs/receipts/environments/slurp-official-eval.json"


def official_evaluator_python() -> str:
    """Interpreter that carries the evaluator's pinned requirements (above)."""

    override = os.environ.get(SLURP_OFFICIAL_PYTHON_ENV)
    if override:
        return override
    if SLURP_OFFICIAL_VENV_PYTHON.is_file():
        return str(SLURP_OFFICIAL_VENV_PYTHON)
    return sys.executable

# Fallback content-identity mechanism (used only when ``git`` cannot verify
# the checkout's own HEAD -- :func:`official_evaluator_root`'s docstring):
# SHA-256 of the four evaluator source files this module depends on, at the
# pinned commit above. Computed 2026-09-03 directly against the
# umbrella-governed local clone (``sha256sum`` over each file, cross-checked
# byte-for-byte from both the Windows and WSL mount of the same volume).
_PINNED_FILE_SHA256: Mapping[str, str] = {
    "evaluate.py": "88c86ea55c646962537cba2b5f53fddc95e49431c9e9353b32eeeb0afea2a650",
    "util.py": "92c42ed926d2bf131913433e6238bac3b3c93da714802d9ecb53a380a13fbc27",
    "metrics/metrics.py": "4569d2c98c549a4e92f53f123e7a63fa48a1e10fead9df9fb35d1e053d9efd96",
    "metrics/distance.py": "48a1307c01505090d5bbcc43d2eb64711a0096b4b312a8ff02b32cc35ad70d4b",
}

# The seven ``format_results`` blocks ``evaluate.py`` prints, in the FIXED
# order its ``__main__`` body prints them (module docstring) -- positional
# parsing is safe because the official script never varies this order and
# always prints exactly these seven tables, unconditionally.
_BLOCK_KEYS: tuple[str, ...] = (
    "scenario",
    "action",
    "intent",
    "entities",
    "entities_distance_word",
    "entities_distance_char",
    "slu_f1",
)


class SlurpOfficialEvalError(RuntimeError):
    """The official evaluator checkout, its input files, or the subprocess
    run could not be verified/produced/executed."""


# ---------------------------------------------------------------------------
# Evaluator checkout identity
# ---------------------------------------------------------------------------


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_by_content_hash(evaluation_dir: Path) -> None:
    for relpath, expected in _PINNED_FILE_SHA256.items():
        path = evaluation_dir / relpath
        if not path.is_file():
            raise SlurpOfficialEvalError(
                f"official SLURP evaluator file missing: {path} (pinned commit "
                f"{SLURP_OFFICIAL_COMMIT})"
            )
        actual = _hash_file(path)
        if actual != expected:
            raise SlurpOfficialEvalError(
                f"official SLURP evaluator file {relpath!r} content hash mismatch: "
                f"expected {expected}, got {actual} (pinned commit {SLURP_OFFICIAL_COMMIT}); "
                "the umbrella-governed clone has drifted from the pinned upstream bytes"
            )


def official_evaluator_root(root: Path) -> Path:
    """Resolve and verify ``<root>/repos/slurp/scripts/evaluation``.

    Two independent verification mechanisms, either sufficient alone
    (module docstring): first, ``git -C <checkout> rev-parse HEAD`` is
    compared against :data:`SLURP_OFFICIAL_COMMIT` -- the checkout's own git
    history IS the identity proof when it succeeds. When ``git`` cannot be
    invoked at all, or the checkout carries no git metadata (``rev-parse``
    exits non-zero), this falls back to hashing the four evaluator source
    files this module actually depends on and comparing them against
    :data:`_PINNED_FILE_SHA256`. Both mechanisms fail closed
    (:class:`SlurpOfficialEvalError`); neither is ever skipped silently.
    """

    checkout = Path(root) / "repos" / "slurp"
    if not checkout.is_dir():
        raise SlurpOfficialEvalError(f"SLURP official evaluator checkout missing: {checkout}")
    evaluation_dir = checkout / "scripts" / "evaluation"
    if not evaluation_dir.is_dir():
        raise SlurpOfficialEvalError(
            f"SLURP official evaluator directory missing: {evaluation_dir}"
        )

    git_head: str | None = None
    try:
        completed = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        completed = None
    if completed is not None and completed.returncode == 0:
        git_head = completed.stdout.strip()

    if git_head is not None:
        if git_head != SLURP_OFFICIAL_COMMIT:
            raise SlurpOfficialEvalError(
                f"SLURP official evaluator checkout {checkout} is at commit {git_head!r}, "
                f"expected the pinned commit {SLURP_OFFICIAL_COMMIT!r}"
            )
    else:
        # git unavailable or the checkout carries no git metadata -- fall
        # back to content-hash verification (module docstring).
        _verify_by_content_hash(evaluation_dir)

    return evaluation_dir


# ---------------------------------------------------------------------------
# Official input-file construction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictedSlurpSample:
    """One model prediction, shaped exactly like the official prediction-file
    row (module docstring): ``scenario``/``action`` are ``None`` on a failed
    parse (:func:`reproduction.slurp_scoring.parse_slu_response`'s own
    fail-closed convention), never coerced to a placeholder string."""

    sample_id: str
    scenario: str | None
    action: str | None
    entities: tuple[SlotEntity, ...]


def _tokens_and_spans(
    entities: Sequence[SlotEntity],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Build a synthetic ``tokens``/``entities`` pair whose official
    ``release2prediction`` reconstruction recovers each entity's exact
    ``filler`` string (module docstring): each entity gets its own disjoint
    block of one-word tokens, so ``" ".join(tokens[i]["surface"].lower() for
    i in span) == filler`` exactly (``filler`` is already lowercased --
    ``data.slurp`` module docstring -- so ``.lower()`` on these tokens is a
    no-op, not a transformation). An entity with an empty ``filler`` gets an
    empty span, round-tripping to ``""`` via ``" ".join([])`` -- no crash,
    no special case.
    """

    tokens: list[dict[str, object]] = []
    span_entities: list[dict[str, object]] = []
    next_id = 0
    for entity in entities:
        words = entity.filler.split()
        span: list[int] = []
        for word in words:
            tokens.append({"id": next_id, "surface": word})
            span.append(next_id)
            next_id += 1
        span_entities.append({"type": entity.type, "span": span})
    return tokens, span_entities


def write_official_inputs(
    gold_records: Sequence[SlurpRecord],
    predictions: Sequence[PredictedSlurpSample],
    out_dir: Path,
) -> tuple[Path, Path]:
    """Write the official gold/prediction JSONL files (module docstring's
    "file"-keyed, ``load_gold=False`` mode) into ``out_dir``.

    Each of ``gold_records``/``predictions`` must carry a unique
    ``sample_id`` within its own list (enforced here, fail-closed) -- pairing
    across the two files happens purely through that shared id, exactly as
    ``evaluate.py``'s own ``gold_id in pred_examples`` loop pairs by "file".
    """

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    gold_path = out_dir / "gold.jsonl"
    pred_path = out_dir / "predictions.jsonl"

    seen_gold: set[str] = set()
    with gold_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in gold_records:
            if record.sample_id in seen_gold:
                raise SlurpOfficialEvalError(
                    f"duplicate gold sample_id {record.sample_id!r} in write_official_inputs"
                )
            seen_gold.add(record.sample_id)
            tokens, span_entities = _tokens_and_spans(record.entities)
            document = {
                "tokens": tokens,
                "scenario": record.scenario,
                "action": record.action,
                "entities": span_entities,
                "recordings": [{"file": record.sample_id}],
            }
            handle.write(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n")

    seen_pred: set[str] = set()
    with pred_path.open("w", encoding="utf-8", newline="\n") as handle:
        for prediction in predictions:
            if prediction.sample_id in seen_pred:
                raise SlurpOfficialEvalError(
                    f"duplicate prediction sample_id {prediction.sample_id!r} in "
                    "write_official_inputs"
                )
            seen_pred.add(prediction.sample_id)
            document = {
                "file": prediction.sample_id,
                "scenario": prediction.scenario,
                "action": prediction.action,
                "entities": [
                    {"type": entity.type, "filler": entity.filler} for entity in prediction.entities
                ],
            }
            handle.write(json.dumps(document, ensure_ascii=False, sort_keys=True) + "\n")

    return gold_path, pred_path


# ---------------------------------------------------------------------------
# Subprocess execution + stdout parsing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OfficialSluResult:
    """The official ``evaluate.py``'s printed results, parsed.

    ``scenario_accuracy``/``action_accuracy``/``intent_accuracy`` are each
    read from that block's ``F-Measure`` column: for micro-averaged
    single-label multiclass ``FMeasure`` (every example gets exactly one
    predicted label), micro precision, recall and F-measure are all
    identically the plain accuracy (every mismatch contributes one FP AND one
    FN, so ``sum(FP) == sum(FN) == wrong count`` and TP/(TP+FP) ==
    TP/(TP+FN)) -- not a separate computation, the SAME number under three
    names. ``slu_f1``/``span_f1`` are the official headline "SLU F1" and
    plain "entities" (exact-match) blocks respectively -- ``span_f1`` is the
    same metric this study's own port names ``slot_f1_exact``.
    """

    scenario_accuracy: float
    action_accuracy: float
    intent_accuracy: float
    slu_f1: float
    span_f1: float
    raw: Mapping[str, Mapping[str, object]]
    stdout: str
    command: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_accuracy": self.scenario_accuracy,
            "action_accuracy": self.action_accuracy,
            "intent_accuracy": self.intent_accuracy,
            "slu_f1": self.slu_f1,
            "span_f1": self.span_f1,
            "raw": {key: dict(value) for key, value in self.raw.items()},
            "stdout": self.stdout,
            "command": list(self.command),
        }


def _parse_official_stdout(stdout: str) -> dict[str, dict[str, object]]:
    """Parse ``--table-layout csv`` stdout into the seven fixed-order blocks
    (module docstring). Each block is a ``"{Label},Precision,Recall,
    F-Measure,TP,FP,FN"`` header line immediately followed by an
    ``"OVERALL,..."`` data line (``--errors`` widens the header to include
    TP/FP/FN; no ``--full`` means exactly one data row per block)."""

    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    blocks: list[tuple[list[str], list[str]]] = []
    index = 0
    while index + 1 < len(lines):
        header_cells = lines[index].split(",")
        row_cells = lines[index + 1].split(",")
        if row_cells and row_cells[0] == "OVERALL" and len(header_cells) == len(row_cells):
            blocks.append((header_cells, row_cells))
            index += 2
        else:
            index += 1

    if len(blocks) != len(_BLOCK_KEYS):
        raise SlurpOfficialEvalError(
            f"could not parse official evaluate.py output: expected {len(_BLOCK_KEYS)} "
            f"'OVERALL' metric blocks (scenario/action/intent/entities/entities-distance-"
            f"word/entities-distance-char/SLU-F1), found {len(blocks)}; full stdout:\n{stdout}"
        )

    raw: dict[str, dict[str, object]] = {}
    for key, (header_cells, row_cells) in zip(_BLOCK_KEYS, blocks):
        column_index = {name: position for position, name in enumerate(header_cells)}
        try:
            raw[key] = {
                "official_label": header_cells[0],
                "precision": float(row_cells[column_index["Precision"]]),
                "recall": float(row_cells[column_index["Recall"]]),
                "f_measure": float(row_cells[column_index["F-Measure"]]),
                "tp": float(row_cells[column_index["TP"]]),
                "fp": float(row_cells[column_index["FP"]]),
                "fn": float(row_cells[column_index["FN"]]),
            }
        except (KeyError, ValueError) as error:
            raise SlurpOfficialEvalError(
                f"could not parse official evaluate.py {key!r} metric block "
                f"(header={header_cells!r}, row={row_cells!r}): {error}"
            ) from error
    return raw


def run_official_evaluate(
    gold_path: Path,
    pred_path: Path,
    *,
    evaluator_root: Path,
    python_executable: str | None = None,
    average: str = "micro",
) -> OfficialSluResult:
    """Run the REAL, unmodified ``evaluate.py`` as a subprocess.

    ``cwd=evaluator_root`` (module docstring): the script's own top-level
    ``from metrics import ErrorMetric`` is a relative import that resolves
    through the interpreter's own module search path, whose first entry
    Python always sets to the directory containing the script argument --
    an ABSOLUTE script path still resolves to that same directory, so this
    is robust regardless of the caller's own cwd.
    ``--table-layout csv --errors`` (no ``--full``): exactly one
    machine-parseable ``OVERALL`` row per metric block, at full float
    precision (module docstring). Fails closed on a non-zero exit or
    unparsable stdout.
    """

    script_path = Path(evaluator_root) / "evaluate.py"
    if not script_path.is_file():
        raise SlurpOfficialEvalError(f"official evaluate.py missing: {script_path}")
    if python_executable is None:
        python_executable = official_evaluator_python()
    command = [
        str(python_executable),
        str(script_path),
        "-g",
        str(gold_path),
        "-p",
        str(pred_path),
        "--average",
        average,
        "--errors",
        "--table-layout",
        "csv",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(evaluator_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as error:
        raise SlurpOfficialEvalError(
            f"could not launch official evaluate.py: {error}; command={command!r}"
        ) from error
    if completed.returncode != 0:
        raise SlurpOfficialEvalError(
            f"official evaluate.py exited {completed.returncode}; command={command!r}; "
            f"stdout={completed.stdout!r}; stderr={completed.stderr!r}"
        )
    raw = _parse_official_stdout(completed.stdout)
    return OfficialSluResult(
        scenario_accuracy=raw["scenario"]["f_measure"],
        action_accuracy=raw["action"]["f_measure"],
        intent_accuracy=raw["intent"]["f_measure"],
        slu_f1=raw["slu_f1"]["f_measure"],
        span_f1=raw["entities"]["f_measure"],
        raw=raw,
        stdout=completed.stdout,
        command=tuple(command),
    )


# ---------------------------------------------------------------------------
# Port <-> official aggregation + identity check
# ---------------------------------------------------------------------------


def _aggregate_slu_score(scores: Sequence[SluScore]) -> SluScore:
    """Sum per-sample :class:`SluScore` ingredients into one corpus-level
    ``SluScore`` -- reuses that dataclass's own ``slu_f1``/``slot_f1_exact``
    properties (``reproduction.slurp_scoring``'s own micro-summing identity)
    instead of re-deriving precision/recall/F1 here."""

    return SluScore(
        scenario_action_exact=sum(score.scenario_action_exact for score in scores),
        scenario_exact=sum(score.scenario_exact for score in scores),
        action_exact=sum(score.action_exact for score in scores),
        slot_f1_exact_tp=sum(score.slot_f1_exact_tp for score in scores),
        slot_f1_exact_fp=sum(score.slot_f1_exact_fp for score in scores),
        slot_f1_exact_fn=sum(score.slot_f1_exact_fn for score in scores),
        slu_f1_word_tp=sum(score.slu_f1_word_tp for score in scores),
        slu_f1_word_fp=sum(score.slu_f1_word_fp for score in scores),
        slu_f1_word_fn=sum(score.slu_f1_word_fn for score in scores),
        slu_f1_char_tp=sum(score.slu_f1_char_tp for score in scores),
        slu_f1_char_fp=sum(score.slu_f1_char_fp for score in scores),
        slu_f1_char_fn=sum(score.slu_f1_char_fn for score in scores),
    )


_IDENTITY_TOLERANCE = 1e-6


def load_legal_intent_inventory(
    lock: Mapping[str, object], root: Path
) -> LegalIntentInventory:
    """The closed label space and the TRAIN prior the legal-label projection
    (:func:`reproduction.slurp_scoring.project_slu_label`) may emit into.

    Both halves are mined from ``train.jsonl`` and nothing else: the pairing
    from :func:`data.slurp.load_slurp_ontology` (``include_synthetic=False``,
    the same TRAIN-only inventory the locked closed-list baseline's own prompt
    suffix renders) and the prior from
    :func:`data.slurp.load_slurp_intent_slot_schema`, whose per-intent ``n`` is
    "TRAIN utterances with this intent". TRAIN is construction data; no devel
    or test label reaches the rule.
    """

    ontology = load_slurp_ontology(lock, root)
    schema = load_slurp_intent_slot_schema(lock, root)
    return legal_intent_inventory(
        ontology.actions_by_scenario,
        {intent: profile.n for intent, profile in schema.intents.items()},
    )


def score_slurp_outputs_official(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    split_id: str = "devel",
    allow_heldout: bool = False,
    project_labels: bool = False,
    projection_version: str = "v1",
    project_fillers: bool = False,
) -> dict[str, object]:
    """Score one run's outputs JSONL both ways: the per-sample port
    (``reproduction.slurp_scoring.score_slu``) and the REAL official
    ``evaluate.py`` subprocess, and report their identity.

    Registered as the ``"slurp-slu"``/``"slurp-slu-official"``
    ``core.base.SCORERS`` entries (``core/scorers.py``) with the uniform
    ``scorer(outputs_path, lock, root)`` signature every scorer shares;
    ``split_id``/``allow_heldout`` are keyword-only extras with defaults, so
    the 3-positional call ``core.scorers.score_bundle`` always makes still
    resolves correctly.

    HELD-OUT DISCIPLINE (mirrors ``data.slurp.load_slurp_split``'s own,
    module docstring): fails closed, before touching the data root at all,
    the moment ANY outputs row names a ``"slurp:test:..."`` sample id (or
    ``split_id="test"`` itself) unless ``allow_heldout=True`` is passed
    explicitly. ``load_slurp_split`` enforces the ``split_id="test"`` case a
    second time on its own -- deliberate defense in depth, not redundancy
    this function relies on alone.

    LEGAL-LABEL PROJECTION (``project_labels``, default ``False`` -- the
    unprojected path is byte-for-byte what it always was, and loads no TRAIN
    inventory at all). When ``True``, every parsed prediction naming a
    ``(scenario, action)`` pair OUTSIDE the 60 TRAIN intents is first mapped
    onto the nearest legal one by
    :func:`reproduction.slurp_scoring.project_slu_label`, and the official
    ``evaluate.py`` then scores THAT label, unchanged. The parse itself
    (:func:`reproduction.slurp_scoring.parse_slu_response`) is untouched: the
    projection runs strictly between the parse and the official prediction
    file, so an unparsed response stays unparsed and entities are never
    rewritten. The aggregate carries a ``projection`` block (rule id,
    eligible / changed / unchanged counts, per-branch counts, and the full
    ``from -> to`` map, itself split by branch) and every per-sample row
    carries ``projected`` / ``projected_from`` / ``projected_to`` /
    ``projected_branch``, so a receipt can inspect every changed label and
    count which branch carried it.

    ``projection_version`` selects WHICH rule projects (``_PROJECTION_RULES``)
    and is meaningful only when ``project_labels=True``: ``"v1"``
    (:func:`reproduction.slurp_scoring.project_slu_label`, nearest legal label
    by edit distance), ``"v2"``
    (:func:`reproduction.slurp_scoring.project_slu_label_v2`, promote an
    action-named scenario to its owning scenario, else v1), or ``"v3"``
    (:func:`rails.slurp_projection_v3.project_slu_label_v3`, rule ``R_action``
    then v2 unchanged -- module M3, A1-decided). An unknown version fails
    closed rather than silently scoring under the default rule.

    FILLER NORMALISATION (``project_fillers``, default ``False`` -- module
    M3's other half, A1's P2 rule). When ``True``, every predicted entity's
    filler is rewritten by :func:`rails.slurp_projection_v3.
    normalize_filler_p2` (the full four-rung rule; no support filter of any
    kind) BEFORE either the port's ``score_slu`` or the official
    ``evaluate.py`` subprocess ever sees it. Asymmetric by construction, the
    SAME asymmetry the official script's own gold-lowercasing already is
    (module docstring of ``reproduction.slurp_scoring``): gold fillers are
    never touched here. Independent of ``project_labels`` -- a caller may
    turn either on alone -- but module M3's own scorers turn both on
    together. Each per-sample row then carries ``fillers_changed`` (the
    count of that row's predicted entities whose filler text changed) and
    the aggregate carries a ``filler_normalization`` block mirroring the
    ``projection`` block's own shape.
    """

    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SlurpOfficialEvalError(f"cannot read outputs {outputs_path}: {error}") from error
    # Same record-separator discipline as core.scorers.score_asr_outputs:
    # split on "\n" only, never str.splitlines(), so raw U+2028/U+2029 inside
    # a JSON string value never cuts one valid row in two.
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise SlurpOfficialEvalError(f"outputs file {outputs_path} is empty")

    rows: list[Mapping[str, object]] = []
    seen: set[str] = set()
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise SlurpOfficialEvalError(f"outputs line {number} malformed: {error}") from error
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise SlurpOfficialEvalError(f"outputs line {number} lacks a sample_id")
        if sample_id in seen:
            raise SlurpOfficialEvalError(f"outputs carry a duplicate sample_id {sample_id!r}")
        seen.add(sample_id)
        rows.append(row)

    if not allow_heldout:
        for row in rows:
            sample_id = row["sample_id"]
            if isinstance(sample_id, str) and sample_id.startswith("slurp:test:"):
                raise SlurpOfficialEvalError(
                    f"outputs sample_id {sample_id!r} names the HELD OUT 'test' split; "
                    "pass allow_heldout=True explicitly for a pre-registered confirmatory read, "
                    "never during discovery iteration"
                )

    gold_records = load_slurp_split(lock, root, split_id, allow_heldout=allow_heldout)
    gold_by_id = {record.sample_id: record for record in gold_records}

    # Built ONLY when the projection is requested: the unprojected path must
    # not acquire a TRAIN-corpus read it never had.
    if project_labels and projection_version not in _PROJECTION_VERSIONS:
        raise SlurpOfficialEvalError(
            f"unknown projection_version {projection_version!r}; "
            f"registered rules are {sorted(_PROJECTION_VERSIONS)}"
        )
    if project_labels and projection_version == "v3":
        # Deferred import: module docstring above ``_PROJECTION_RULES``
        # explains why v3 cannot be a module-scope import of ``rails``.
        from ..rails.slurp_projection_v3 import (  # noqa: PLC0415
            SLURP_LABEL_PROJECTION_V3_ID,
            project_slu_label_v3,
        )

        projection_id, project = SLURP_LABEL_PROJECTION_V3_ID, project_slu_label_v3
    else:
        projection_id, project = _PROJECTION_RULES[
            projection_version if project_labels else "v1"
        ]
    inventory = load_legal_intent_inventory(lock, root) if project_labels else None
    projection_counts = {"eligible": 0, "changed": 0, "unchanged": 0, "ineligible": 0}
    branch_counts = {branch: 0 for branch in PROJECTION_BRANCHES}
    projection_map: dict[str, int] = {}
    branch_map: dict[str, dict[str, int]] = {}
    total_fillers_changed = 0
    normalize_filler_p2 = None
    filler_normalization_rule_id = None
    if project_fillers:
        # Deferred import for the same reason v3's label rule is deferred
        # above: this module must not import ``rails`` at module scope.
        from ..rails.slurp_projection_v3 import (  # noqa: PLC0415
            SLURP_FILLER_NORMALIZATION_P2_ID as filler_normalization_rule_id,
            normalize_filler_p2,
        )

    per_sample: list[dict[str, object]] = []
    predictions: list[PredictedSlurpSample] = []
    gold_selected: list[SlurpRecord] = []
    sample_scores: list[SluScore] = []

    for row in rows:
        sample_id = row["sample_id"]
        # VARIANT-ID RAIL (2026-09-07 cross-carrier silence-tail
        # preregistration section 6.2): a derived-media population carries
        # <published id>@<variant> ids (data.variant_ids), and the gold a row
        # is scored against is the PUBLISHED sample's own. Inert for every
        # unsuffixed id, and never a skeleton key -- a foreign published key
        # still refuses here, naming the RAW id that was flown. The published
        # key is also what goes into the official evaluator's "file" field
        # below, on BOTH sides, because that is the key evaluate.py pairs on.
        published_id = published_sample_key(sample_id)
        gold_record = gold_by_id.get(published_id)
        if gold_record is None:
            raise SlurpOfficialEvalError(
                f"outputs sample_id {sample_id!r} is not part of SLURP split {split_id!r}"
            )
        model_text = row.get("text")
        if not isinstance(model_text, str):
            raise SlurpOfficialEvalError(f"outputs row for {sample_id!r} lacks a text field")
        pred_scenario, pred_action, pred_entities, parsed = parse_slu_response(model_text)
        projected = False
        projected_from: str | None = None
        projected_to: str | None = None
        projected_branch: str | None = None
        if inventory is not None:
            outcome = project(pred_scenario, pred_action, inventory, parsed=parsed)
            projected_branch = outcome.branch
            branch_counts[outcome.branch] = branch_counts.get(outcome.branch, 0) + 1
            if not outcome.eligible:
                projection_counts["ineligible"] += 1
            elif outcome.changed:
                projection_counts["eligible"] += 1
                projection_counts["changed"] += 1
                projected = True
                projected_from = outcome.source_intent
                projected_to = outcome.projected_intent
                key = f"{projected_from} -> {projected_to}"
                projection_map[key] = projection_map.get(key, 0) + 1
                per_branch = branch_map.setdefault(outcome.branch, {})
                per_branch[key] = per_branch.get(key, 0) + 1
            else:
                projection_counts["eligible"] += 1
                projection_counts["unchanged"] += 1
            pred_scenario, pred_action = outcome.scenario, outcome.action
        fillers_changed = 0
        if project_fillers:
            normalized_entities: list[SlotEntity] = []
            for entity in pred_entities:
                new_filler = normalize_filler_p2(entity.filler)
                if new_filler != entity.filler:
                    fillers_changed += 1
                    normalized_entities.append(SlotEntity(type=entity.type, filler=new_filler))
                else:
                    normalized_entities.append(entity)
            pred_entities = normalized_entities
            total_fillers_changed += fillers_changed
        predictions.append(
            PredictedSlurpSample(
                sample_id=published_id,
                scenario=pred_scenario,
                action=pred_action,
                entities=tuple(pred_entities),
            )
        )
        gold_selected.append(gold_record)
        sample_score = score_slu(
            gold_scenario=gold_record.scenario,
            gold_action=gold_record.action,
            gold_entities=gold_record.entities,
            predicted_scenario=pred_scenario,
            predicted_action=pred_action,
            predicted_entities=pred_entities,
        )
        sample_scores.append(sample_score)
        entry = sample_score.as_metrics_dict()
        entry["sample_id"] = sample_id
        entry["parsed"] = parsed
        if inventory is not None:
            entry["projected"] = projected
            entry["projected_from"] = projected_from
            entry["projected_to"] = projected_to
            entry["projected_branch"] = projected_branch
        if project_fillers:
            entry["fillers_changed"] = fillers_changed
        per_sample.append(entry)

    aggregate_score = _aggregate_slu_score(sample_scores)
    slu_p, slu_r, slu_f1_measure = aggregate_score.slu_f1
    span_p, span_r, span_f1_measure = aggregate_score.slot_f1_exact
    n_samples = len(per_sample)
    port_micro = {
        "samples": n_samples,
        "slu_f1": slu_f1_measure,
        "slu_f1_precision": slu_p,
        "slu_f1_recall": slu_r,
        # "span_f1" == the port's own "slot_f1_exact" (module docstring):
        # exact {type, filler} match, mirrors the official plain "entities"
        # row, never the paper's headline SLU-F1.
        "span_f1": span_f1_measure,
        "span_f1_precision": span_p,
        "span_f1_recall": span_r,
        "scenario_accuracy": (
            sum(item["scenario_exact"] for item in per_sample) / n_samples if n_samples else 0.0
        ),
        "action_accuracy": (
            sum(item["action_exact"] for item in per_sample) / n_samples if n_samples else 0.0
        ),
        "intent_accuracy": (
            sum(item["scenario_action_exact"] for item in per_sample) / n_samples
            if n_samples
            else 0.0
        ),
    }

    with tempfile.TemporaryDirectory(prefix="saea-slurp-official-") as tmp:
        tmp_dir = Path(tmp)
        gold_path, pred_path = write_official_inputs(gold_selected, predictions, tmp_dir)
        evaluator_root = official_evaluator_root(Path(root))
        official = run_official_evaluate(gold_path, pred_path, evaluator_root=evaluator_root)

    slu_f1_diff = abs(port_micro["slu_f1"] - official.slu_f1)
    span_f1_diff = abs(port_micro["span_f1"] - official.span_f1)
    identity_check = {
        "slu_f1_abs_diff": slu_f1_diff,
        "span_f1_abs_diff": span_f1_diff,
        "passed": slu_f1_diff < _IDENTITY_TOLERANCE and span_f1_diff < _IDENTITY_TOLERANCE,
        "tolerance": _IDENTITY_TOLERANCE,
    }

    aggregate = {
        "split_id": split_id,
        "samples": n_samples,
        "port_scorer_version": SLURP_SCORER_VERSION,
        "official": official.as_dict(),
        "port_micro": port_micro,
        "identity_check": identity_check,
        "scorer_version": SLURP_OFFICIAL_SCORER_VERSION,
        "evaluator_commit": SLURP_OFFICIAL_COMMIT,
        "official_python": official.command[0],
        "official_environment_receipt": SLURP_OFFICIAL_ENV_RECEIPT,
        "projection": (
            {
                "applied": False,
                "projection_id": None,
            }
            if inventory is None
            else {
                "applied": True,
                "projection_id": projection_id,
                "projection_version": projection_version,
                "legal_intents": len(inventory.pairs),
                "legal_scenarios": len(inventory.scenarios),
                "counts": dict(projection_counts),
                "branch_counts": dict(branch_counts),
                "map": dict(sorted(projection_map.items())),
                "map_by_branch": {
                    branch: dict(sorted(entries.items()))
                    for branch, entries in sorted(branch_map.items())
                },
            }
        ),
        "filler_normalization": (
            {"applied": False, "rule_id": None}
            if not project_fillers
            else {
                "applied": True,
                "rule_id": filler_normalization_rule_id,
                "changed_count": total_fillers_changed,
            }
        ),
    }
    return {"per_sample": per_sample, "aggregate": aggregate}


def score_slurp_outputs_official_projected(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    split_id: str = "devel",
    allow_heldout: bool = False,
) -> dict[str, object]:
    """:func:`score_slurp_outputs_official` with the legal-label projection
    ON -- the registered ``"slurp-slu-official-projected"`` /
    ``"slurp-slu-projected"`` scorers (``core/scorers.py``).

    A thin keyword binding, never a second implementation: the parse, the
    port, the official ``evaluate.py`` subprocess and the identity check are
    the exact same code path, so the two scorer families can never drift
    apart. It exists as a named function rather than a ``functools.partial``
    only so the uniform ``scorer(outputs_path, lock, root)`` signature stays
    readable in a traceback.
    """

    return score_slurp_outputs_official(
        outputs_path,
        lock,
        root,
        split_id=split_id,
        allow_heldout=allow_heldout,
        project_labels=True,
        projection_version="v1",
    )


def score_slurp_outputs_official_projected_v2(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    split_id: str = "devel",
    allow_heldout: bool = False,
) -> dict[str, object]:
    """:func:`score_slurp_outputs_official` with the SUCCESSOR legal-label
    projection on -- the registered ``"slurp-slu-official-projected-v2"`` /
    ``"slurp-slu-projected-v2"`` scorers (``core/scorers.py``),
    preregistration
    ``docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md``.

    The same thin keyword binding v1's function is, differing from it in one
    argument: the parse, the port, the official ``evaluate.py`` subprocess and
    the identity check are the exact same code path, so the three scorer
    families (unprojected, v1, v2) can never drift apart.
    """

    return score_slurp_outputs_official(
        outputs_path,
        lock,
        root,
        split_id=split_id,
        allow_heldout=allow_heldout,
        project_labels=True,
        projection_version="v2",
    )


def score_slurp_outputs_official_projected_v3(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    split_id: str = "devel",
    allow_heldout: bool = False,
) -> dict[str, object]:
    """:func:`score_slurp_outputs_official` with USE projection v3 on -- the
    registered ``"slurp-slu-official-projected-v3"`` / ``"slurp-slu-
    projected-v3"`` scorers (``core/scorers.py``), module M3
    (``docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md``
    section 3, decided by ``docs/results/
    2026-09-17-slurp-a1-use-projection-audit-v1.md``).

    v3 turns BOTH ``project_labels`` (``projection_version="v3"``: rule
    ``R_action`` then the registered v2 fallback,
    :func:`rails.slurp_projection_v3.project_slu_label_v3`) and
    ``project_fillers`` (the full four-rung P2 filler normalisation, no
    support filter) on together -- module M3 is the two halves applied as
    one unit, never one alone. Otherwise the exact same thin keyword
    binding every projected sibling above is: the parse, the port, the
    official ``evaluate.py`` subprocess and the identity check are the same
    code path, so v1/v2/v3 can never drift apart.
    """

    return score_slurp_outputs_official(
        outputs_path,
        lock,
        root,
        split_id=split_id,
        allow_heldout=allow_heldout,
        project_labels=True,
        projection_version="v3",
        project_fillers=True,
    )


def score_slurp_outputs_official_train(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    allow_heldout: bool = False,
) -> dict[str, object]:
    """:func:`score_slurp_outputs_official` against the TRAIN gold -- the
    registered ``"slurp-slu-official-train"`` / ``"slurp-slu-train"`` scorers.

    The same thin keyword binding the projected siblings are, differing in one
    argument: ``split_id="train"``. The parse, the port, the official
    ``evaluate.py`` subprocess at the pinned commit and the identity check are
    the exact same code path, so no scorer family can drift from another.

    WHY IT EXISTS. Every construction-role roster this study draws -- the
    EVO-S1 reward folds above all -- is TRAIN, and the default binding resolves
    gold from ``devel`` and therefore refuses a TRAIN prediction outright
    ("outputs sample_id ... is not part of SLURP split 'devel'"). That refusal
    is correct and must stay: a devel read must never silently score against
    another split's gold. What a TRAIN construction fold needs is the same
    official scorer pointed at the split its own rows came from, declared in
    the arm's own ``scorers`` list so a run manifest names which gold it was
    scored against.

    It changes nothing about a DEVEL cell. ``allow_heldout`` is accepted for
    signature uniformity and is meaningless here: ``split_id`` is fixed to
    ``"train"`` and the held-out refusal above keys on the sample ids
    themselves.
    """

    return score_slurp_outputs_official(
        outputs_path, lock, root, split_id="train", allow_heldout=allow_heldout
    )


def score_slurp_outputs_official_test(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    allow_heldout: bool = True,
) -> dict[str, object]:
    """:func:`score_slurp_outputs_official` against the TEST gold -- the
    registered ``"slurp-slu-official-test"`` scorer.

    The one legal route the one-read protocol names
    (``docs/readiness/2026-09-19-slurp-test-split-one-read-protocol-v1-draft.md``
    section 3.4): ``core.scorers.score_bundle`` calls every scorer with three
    positional arguments, so ``split_id`` and ``allow_heldout`` cannot be
    threaded through the registered scoring path at call time; a test read
    needs its own registry entry, exactly as the ``-train`` siblings were
    added. The same evaluator at the same pinned commit with the same flags;
    only the gold split differs.

    Registering it is NOT authority to read anything. The test gold is opened
    only when a sealed ``final-report`` manifest is scored, and such a
    manifest exists only after a plan passed
    ``contracts.plan.require_owner_split_allowance`` and the gate's
    one-attempt budget. Two refusals are local to this binding and run before
    the data root is touched:

    * ``allow_heldout`` must stay ``True`` -- the keyword exists for signature
      uniformity with the siblings; passing ``False`` would silently turn this
      into the DEVEL-refusing path and is refused outright;
    * every outputs row must name a ``"slurp:test:..."`` sample id: a test
      scorer must never score a devel or train row against test gold.
    """

    if allow_heldout is not True:
        raise SlurpOfficialEvalError(
            "slurp-slu-official-test binds allow_heldout=True by construction; "
            "refusing a call that would turn it into another split's scorer"
        )
    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise SlurpOfficialEvalError(f"cannot read outputs {outputs_path}: {error}") from error
    for number, line in enumerate(text.split("\n"), start=1):
        if not line:
            continue
        try:
            sample_id = json.loads(line).get("sample_id")
        except (json.JSONDecodeError, AttributeError) as error:
            raise SlurpOfficialEvalError(f"outputs line {number} malformed: {error}") from error
        if not isinstance(sample_id, str) or not sample_id.startswith("slurp:test:"):
            raise SlurpOfficialEvalError(
                f"outputs line {number} names {sample_id!r}, not a 'slurp:test:' sample; "
                "the test scorer never scores another split's row against test gold"
            )
    return score_slurp_outputs_official(
        outputs_path, lock, root, split_id="test", allow_heldout=True
    )


#: The registered official SLURP scorer ids ``--strata-inside-scorer`` (``core.scoring_strata``)
#: may stratify under, and the gold split + held-out flag each one is bound to -- exactly the
#: bindings of ``score_slurp_outputs_official`` / ``_train`` / ``_test`` above.
OFFICIAL_GOLD_SPLIT_OF_SCORER: dict[str, tuple[str, bool]] = {
    "slurp-slu": ("devel", False),
    "slurp-slu-official": ("devel", False),
    "slurp-slu-official-train": ("train", False),
    "slurp-slu-official-test": ("test", True),
}


def official_gold_intents(
    scorer_id: str,
    sample_ids: Sequence[str],
    lock: Mapping[str, object],
    root: Path,
) -> dict[str, str]:
    """``{sample_id: gold intent scenario_action}`` for exactly ``sample_ids``, read through the
    SAME gold binding the registered official scorer ``scorer_id`` scores against.

    The one gold channel of the official-scoring step's ``--strata-inside-scorer`` mode
    (coordinator ruling 2026-09-30): the caller keeps the mapping in memory to stratify its
    aggregates and never persists it. Refuses, before the data root is touched, a scorer id
    outside :data:`OFFICIAL_GOLD_SPLIT_OF_SCORER` and -- for the test binding -- any id that is
    not a ``"slurp:test:..."`` row, mirroring :func:`score_slurp_outputs_official_test`.
    """

    if scorer_id not in OFFICIAL_GOLD_SPLIT_OF_SCORER:
        raise SlurpOfficialEvalError(
            f"{scorer_id!r} is not an official SLURP scorer binding; known: "
            f"{sorted(OFFICIAL_GOLD_SPLIT_OF_SCORER)}"
        )
    split_id, allow_heldout = OFFICIAL_GOLD_SPLIT_OF_SCORER[scorer_id]
    prefix = f"slurp:{split_id}:"
    for sample_id in sample_ids:
        if not isinstance(sample_id, str) or not published_sample_key(sample_id).startswith(prefix):
            raise SlurpOfficialEvalError(
                f"{scorer_id} scores {split_id!r} rows only; a roster row names another split"
            )
    gold_records = load_slurp_split(lock, root, split_id, allow_heldout=allow_heldout)
    gold_by_id = {record.sample_id: record.intent for record in gold_records}
    out: dict[str, str] = {}
    for sample_id in sample_ids:
        intent = gold_by_id.get(published_sample_key(sample_id))
        if intent is None:
            raise SlurpOfficialEvalError(
                f"a roster row is not part of SLURP split {split_id!r} (gold binding of {scorer_id})"
            )
        out[sample_id] = intent
    return out


def score_slurp_outputs_official_projected_v2_train(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    allow_heldout: bool = False,
) -> dict[str, object]:
    """:func:`score_slurp_outputs_official_train` with the SUCCESSOR
    legal-label projection on -- the registered
    ``"slurp-slu-official-projected-v2-train"`` scorer.

    The re-lock of 2026-09-06 made ``slurp-legal-label-projection-v2`` the rule
    every pending SLURP cell reads its LABEL columns through; a TRAIN
    construction fold reports its own one-contact intent comparator on that
    same scale, and the entity columns are structurally unchanged by any
    projection.
    """

    return score_slurp_outputs_official(
        outputs_path,
        lock,
        root,
        split_id="train",
        allow_heldout=allow_heldout,
        project_labels=True,
        projection_version="v2",
    )


def score_slurp_outputs_official_projected_v3_train(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    allow_heldout: bool = False,
) -> dict[str, object]:
    """:func:`score_slurp_outputs_official_train` with USE projection v3 on
    -- the registered ``"slurp-slu-official-projected-v3-train"`` scorer.

    Module M3's own TRAIN-gold sibling, exactly the reason
    ``score_slurp_outputs_official_projected_v2_train`` exists beside v2: an
    EVO/construction fold's rows are TRAIN, and this points the same v3
    projection at the split those rows came from.
    """

    return score_slurp_outputs_official(
        outputs_path,
        lock,
        root,
        split_id="train",
        allow_heldout=allow_heldout,
        project_labels=True,
        projection_version="v3",
        project_fillers=True,
    )


# ---------------------------------------------------------------------------
# THE NORMALIZED SLU SCORER -- ``slurp-slu-f1-normalized-v1``.
#
# The Whisper-normalizer analogue for slot values, and it sits beside the
# official number in exactly the way ``asr-wer-whisper`` sits beside
# ``asr-wer``: this function runs the REAL, unmodified official ``evaluate.py``
# on the RAW inputs first, reports its numbers unchanged, checks the port
# against them, and only then reports a SECOND set of numbers computed with
# ``reproduction.slurp_slot_normalizer`` applied SYMMETRICALLY to the gold and
# the predicted filler. The official column is never overwritten and never
# recomputed; a caller that reads only ``aggregate["official"]`` gets byte-for-
# byte what ``score_slurp_outputs_official`` would have given it.
#
# Why the normalized half cannot go through the subprocess: the pinned
# ``evaluate.py`` reads its gold from the corpus file, so a normalizer that
# must touch the GOLD side has no seam there. It therefore runs through the
# study's own per-sample port, whose identity with the official script is
# asserted on every call at ``_IDENTITY_TOLERANCE`` and which MF-9 already
# re-anchored from the same sealed bytes. That assertion is the licence for
# the normalized column: the same code path, one string rewrite apart.
# ---------------------------------------------------------------------------


def score_slurp_outputs_slu_normalized_view(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    split_id: str = "devel",
    allow_heldout: bool = False,
    per_rule: bool = True,
) -> dict[str, object]:
    """Compute the raw-label normalized view without an official subprocess.

    This is the shared pure-scoring half used by both the legacy normalized
    scorer and the aligned scorer below. Predicted scenario/action labels are
    parsed directly from the recorded response and are never projected.
    """

    from .slurp_slot_normalizer import (  # noqa: PLC0415 (import cost)
        SLURP_SLOT_NORMALIZER_ID,
        SLURP_SLOT_NORMALIZER_RULES,
        SLURP_SLU_NORMALIZED_SCORER_ID,
        load_slot_normalizer_inventory,
        normalize_slot_entities,
    )

    inventory = load_slot_normalizer_inventory(lock, root)
    gold_records = load_slurp_split(lock, root, split_id, allow_heldout=allow_heldout)
    gold_by_id = {record.sample_id: record for record in gold_records}

    text = Path(outputs_path).read_text(encoding="utf-8")
    lines = [line for line in text.split("\n") if line.strip()]
    parsed_rows: list[tuple[str, str | None, str | None, list[SlotEntity]]] = []
    for line in lines:
        row = json.loads(line)
        sample_id = str(row["sample_id"])
        scenario, action, entities, _parsed = parse_slu_response(str(row["text"]))
        parsed_rows.append((sample_id, scenario, action, entities))

    prefixes: list[tuple[str, ...]] = (
        [
            SLURP_SLOT_NORMALIZER_RULES[: n + 1]
            for n in range(len(SLURP_SLOT_NORMALIZER_RULES))
        ]
        if per_rule
        else [SLURP_SLOT_NORMALIZER_RULES]
    )
    by_prefix: dict[tuple[str, ...], list[SluScore]] = {}
    per_sample_full: dict[str, dict[str, object]] = {}
    for prefix in prefixes:
        gold_cache: dict[tuple[str, str], str] = {}
        pred_cache: dict[tuple[str, str], str] = {}
        scores: list[SluScore] = []
        for sample_id, scenario, action, entities in parsed_rows:
            gold_record = gold_by_id[published_sample_key(sample_id)]
            score = score_slu(
                gold_scenario=gold_record.scenario,
                gold_action=gold_record.action,
                gold_entities=normalize_slot_entities(
                    gold_record.entities, inventory, rules=prefix, cache=gold_cache
                ),
                predicted_scenario=scenario,
                predicted_action=action,
                predicted_entities=normalize_slot_entities(
                    entities, inventory, rules=prefix, cache=pred_cache
                ),
            )
            scores.append(score)
            if prefix == SLURP_SLOT_NORMALIZER_RULES:
                per_sample_full[sample_id] = score.as_metrics_dict()
        by_prefix[prefix] = scores

    def _micro(scores: Sequence[SluScore]) -> dict[str, float]:
        aggregate = _aggregate_slu_score(scores)
        slu_p, slu_r, slu_f1_measure = aggregate.slu_f1
        span_p, span_r, span_f1_measure = aggregate.slot_f1_exact
        _wp, _wr, word_f1 = aggregate.slu_f1_word
        _cp, _cr, char_f1 = aggregate.slu_f1_char
        return {
            "samples": len(scores),
            "slu_f1": slu_f1_measure,
            "slu_f1_precision": slu_p,
            "slu_f1_recall": slu_r,
            "span_f1": span_f1_measure,
            "span_f1_precision": span_p,
            "span_f1_recall": span_r,
            "word_f1": word_f1,
            "char_f1": char_f1,
        }

    # The false-merge audit: distinct gold surface forms of ONE type that the
    # normalizer collapses onto a shared string. Reported whether zero or not.
    merged: dict[str, dict[str, list[str]]] = {}
    merge_cache: dict[tuple[str, str], str] = {}
    for record in gold_records:
        for entity in record.entities:
            normalized = normalize_slot_entities(
                (entity,),
                inventory,
                rules=SLURP_SLOT_NORMALIZER_RULES,
                cache=merge_cache,
            )[0].filler
            bucket = merged.setdefault(str(entity.type), {}).setdefault(normalized, [])
            if entity.filler not in bucket:
                bucket.append(entity.filler)
    false_merges = {
        f"{entity_type}:{normalized}": sorted(sources)
        for entity_type, buckets in sorted(merged.items())
        for normalized, sources in sorted(buckets.items())
        if len(sources) > 1
    }

    aggregate: dict[str, object] = {
        "scorer_id": SLURP_SLU_NORMALIZED_SCORER_ID,
        "normalizer_id": SLURP_SLOT_NORMALIZER_ID,
        "rules": list(SLURP_SLOT_NORMALIZER_RULES),
        "applies_to": "gold and prediction alike, before the official distance blocks",
        "replaces_official": False,
        "inventory": inventory.as_json(),
        "micro": _micro(by_prefix[SLURP_SLOT_NORMALIZER_RULES]),
        "false_merges": false_merges,
        "false_merge_count": len(false_merges),
    }
    document: dict[str, object] = {"aggregate": aggregate}
    if per_rule:
        document["aggregate_per_rule"] = {
            "+".join(prefix): _micro(scores) for prefix, scores in by_prefix.items()
        }
    document["per_sample"] = [
        {"sample_id": sample_id, **per_sample_full[sample_id]}
        for sample_id, _scenario, _action, _entities in parsed_rows
    ]
    return document


def score_slurp_outputs_slu_normalized(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    split_id: str = "devel",
    allow_heldout: bool = False,
    per_rule: bool = True,
) -> dict[str, object]:
    """Preserve the legacy raw-official plus normalized scorer document.

    The official evaluator is still invoked first on raw labels. The pure
    normalized helper then reconstructs the historical aggregate additions
    and per-row ``normalized`` overlays without changing their keys or values.
    """

    document = score_slurp_outputs_official(
        outputs_path,
        lock,
        root,
        split_id=split_id,
        allow_heldout=allow_heldout,
    )
    if not document["aggregate"]["identity_check"]["passed"]:  # type: ignore[index]
        raise SlurpOfficialEvalError(
            "the port disagrees with the official evaluate.py on these outputs; "
            "the normalized column is not computed on a broken identity"
        )
    view = score_slurp_outputs_slu_normalized_view(
        outputs_path,
        lock,
        root,
        split_id=split_id,
        allow_heldout=allow_heldout,
        per_rule=per_rule,
    )
    normalized_by_id = {
        str(entry["sample_id"]): {
            key: value for key, value in entry.items() if key != "sample_id"
        }
        for entry in view["per_sample"]  # type: ignore[union-attr]
    }
    for entry in document["per_sample"]:  # type: ignore[index]
        entry["normalized"] = normalized_by_id[str(entry["sample_id"])]
    document["aggregate"]["normalized"] = view["aggregate"]  # type: ignore[index]
    if per_rule:
        document["aggregate"]["normalized_per_rule"] = view[  # type: ignore[index]
            "aggregate_per_rule"
        ]
    return document


def score_slurp_outputs_slu_normalized_train(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    allow_heldout: bool = False,
    per_rule: bool = True,
) -> dict[str, object]:
    """:func:`score_slurp_outputs_slu_normalized` against the TRAIN gold -- the
    registered ``"slurp-slu-f1-normalized-v1-train"`` scorer
    (``core/scorers.py``), owner decision 14 of 2026-09-17,
    ``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``.

    The same thin keyword binding :func:`score_slurp_outputs_official_train`
    is, differing from its DEV sibling in exactly one argument:
    ``split_id="train"``. The parse, the port, the official ``evaluate.py``
    subprocess at the pinned commit, the identity check that licenses the
    symmetric column at all, the slot normalizer itself (mined from TRAIN and
    only from TRAIN whichever split is being scored -- see
    :func:`reproduction.slurp_slot_normalizer.load_slot_normalizer_inventory`)
    and the returned document's schema are the exact same code path, so the
    two siblings can never drift apart.

    WHY IT EXISTS. Owner decision 7 of 2026-09-17 requires the
    symmetric-normalised number beside every official number, and the DEV
    binding resolves gold from ``devel`` and therefore refuses a TRAIN
    prediction outright ("outputs sample_id ... is not part of SLURP split
    'devel'"). That refusal is correct and stays -- a devel read must never
    silently score against another split's gold, and this sibling refuses a
    devel id in exactly the same way, naming ``'train'``. Every TRAIN A cell
    of the SLURP v2 base program is scored on the construction fold's own
    rows, so decision 7 was not evaluable there (cells B0r and B4b record it
    as such); this is the same scorer pointed at the split those rows came
    from, declared as its own registered id so a run manifest or an offline
    re-read names which gold it was scored against
    (``aggregate["split_id"]``).

    What makes the normalized column a metric rather than a mechanism is
    untouched: the normalizer is applied SYMMETRICALLY to the gold and to the
    predicted filler, so an arm cannot gain under it by writing its answers
    differently from the corpus, only by saying what the corpus says.

    ``allow_heldout`` is accepted for signature uniformity and is meaningless
    here, exactly as in :func:`score_slurp_outputs_official_train`:
    ``split_id`` is fixed to ``"train"`` and the held-out refusal keys on the
    sample ids themselves.
    """

    return score_slurp_outputs_slu_normalized(
        outputs_path,
        lock,
        root,
        split_id="train",
        allow_heldout=allow_heldout,
        per_rule=per_rule,
    )


def score_slurp_outputs_official_aligned(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    split_id: str = "devel",
    allow_heldout: bool = False,
    per_rule: bool = True,
) -> dict[str, object]:
    """Return projected-v2 official primary and raw-label normalized view.

    Exactly one official ``evaluate.py`` invocation occurs, in the primary
    projected-v2 scorer. The normalized secondary is computed by the pure
    port helper and is kept under ``views.normalized`` so its raw labels cannot
    overlay the projected primary rows.
    """

    from .slurp_slot_normalizer import (  # noqa: PLC0415 (import cost)
        SLURP_SLOT_NORMALIZER_ID,
        SLURP_SLU_NORMALIZED_SCORER_ID,
    )

    document = score_slurp_outputs_official_projected_v2(
        outputs_path,
        lock,
        root,
        split_id=split_id,
        allow_heldout=allow_heldout,
    )
    if not document["aggregate"]["identity_check"]["passed"]:  # type: ignore[index]
        raise SlurpOfficialEvalError(
            "the projected-v2 port disagrees with the official evaluate.py; "
            "the normalized view is not computed on a broken identity"
        )
    normalized = score_slurp_outputs_slu_normalized_view(
        outputs_path,
        lock,
        root,
        split_id=split_id,
        allow_heldout=allow_heldout,
        per_rule=per_rule,
    )
    normalized["provenance"] = {
        "view_id": "normalized",
        "prediction_labels": "raw-unprojected",
        "projection": {"applied": False, "projection_id": None},
        "normalizer_id": SLURP_SLOT_NORMALIZER_ID,
        "scorer_id": SLURP_SLU_NORMALIZED_SCORER_ID,
        "official_evaluate_invocations": 0,
        "scoring_route": "pure-slurp-port",
    }
    document["aggregate"]["aligned_views"] = {  # type: ignore[index]
        "scorer_id": SLURP_SLU_OFFICIAL_ALIGNED_SCORER_ID,
        "official_evaluate_invocations": 1,
        "primary": {
            "view_id": "primary",
            "prediction_labels": "projected-v2",
            "projection_id": SLURP_LABEL_PROJECTION_V2_ID,
            "official_evaluate_invocations": 1,
            "official_scorer_version": SLURP_OFFICIAL_SCORER_VERSION,
        },
        "normalized": {
            "view_id": "normalized",
            "prediction_labels": "raw-unprojected",
            "projection_id": None,
            "normalizer_id": SLURP_SLOT_NORMALIZER_ID,
            "scorer_id": SLURP_SLU_NORMALIZED_SCORER_ID,
            "official_evaluate_invocations": 0,
            "scoring_route": "pure-slurp-port",
        },
    }
    document["views"] = {"normalized": normalized}
    return document

__all__ = [
    "SLURP_OFFICIAL_COMMIT",
    "SLURP_OFFICIAL_SCORER_VERSION",
    "SLURP_SLU_OFFICIAL_ALIGNED_SCORER_ID",
    "OfficialSluResult",
    "PredictedSlurpSample",
    "SlurpOfficialEvalError",
    "OFFICIAL_GOLD_SPLIT_OF_SCORER",
    "load_legal_intent_inventory",
    "official_gold_intents",
    "official_evaluator_python",
    "official_evaluator_root",
    "run_official_evaluate",
    "score_slurp_outputs_official",
    "score_slurp_outputs_official_train",
    "score_slurp_outputs_official_projected_v2_train",
    "score_slurp_outputs_official_projected_v3_train",
    "score_slurp_outputs_official_projected",
    "score_slurp_outputs_official_projected_v2",
    "score_slurp_outputs_official_projected_v3",
    "score_slurp_outputs_official_aligned",
    "score_slurp_outputs_slu_normalized",
    "score_slurp_outputs_slu_normalized_train",
    "score_slurp_outputs_slu_normalized_view",
    "write_official_inputs",
]
