#!/usr/bin/env python3
"""Item E36b: the model-free REPLAY of the findings-keyed re-query over a sealed run's own
ACQUIRE rows (owner decisions 90 and 70; design note ``docs/superpowers/specs/
2026-09-22-e36b-findings-keyed-requery-design.md`` section 6).

For a sealed run's own ``<attempt>.outputs.jsonl``, every row whose ``native_episode_receipt``
carries at least one ``acquisition`` entry is replayed: the cell's own composite knowledge
snapshot is rebuilt through the REAL loaders (``core.config.compose`` +
``rails.knowledge_stores.load_knowledge_store_binding``), the cell's own baseline is composed and
re-armed with the two E36b keys (``acquisition.budget.max_items_per_acquisition`` and
``acquisition.retrieval``), and the PRODUCTION callable
(``core.flight.runtime.FlightRuntime._acquisition_requery_binding``) is built and called with the
row's own recorded ``state_filters`` -- the exact tokens a live flight would have carried.

This driver never contacts a model, a tokenizer, an encoder or a server, and it never writes
anywhere under ``SPEECHRL_DATA_DIR``: it opens the sealed run read-only, reads the cell's
committed config fragments and the frozen knowledge-store release files, and writes exactly one
receipt to the path ``--receipt-out`` names (a scratchpad path, never the data root).

Nothing this driver reports is utterance text, gold, knowledge-value content or model output: a
row's own ``state_filters`` are counted and classified (kept / dropped, and why -- too-short,
too-common, visible-in-row, absent-from-snapshot) but never printed as text; a candidate value is
reported by its id's STORE prefix and its numeric score only, never its content.

For every row this driver ALSO independently recomputes the same ranking with a plain,
self-contained tokenizer/scorer (this module's own ``_diagnose_row``) so it can report the
per-token drop reasons the production closure does not expose, and it ASSERTS that the two agree
on the final ranked id list before trusting either -- a disagreement raises rather than silently
reporting the diagnostic-only computation as if it were the flown one.

Usage::

    python scripts/analysis/acquisition_requery_replay.py \\
        --run-id SAEA-SLURP-NATIVE-PLAN-ACQUISITION-B9A-RECOVERY-V1 \\
        --attempt-id attempt-slurp-native-plan-acquisition-b9a-recovery-train-fold-a-generation-v1 \\
        --experiment slurp-native-plan-acquisition-b9a-recovery-v1 \\
        --k 5 \\
        --receipt-out /path/to/scratchpad/e36b-replay-receipt.json
"""

from __future__ import annotations

import argparse
import collections
import copy
import glob
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "saea-e36b-acquisition-requery-replay-v1"

#: The SAME token pattern ``core.flight.runtime._E36B_TOKEN`` uses: lowercase letters and digits,
#: split on everything else. Duplicated here (not imported as a private name across a module
#: boundary) because this script's own ``_diagnose_row`` is a deliberately independent
#: reimplementation the production call is cross-checked against, not a caller of its internals.
_TOKEN_RE = re.compile(r"[a-z0-9]+")

#: The registered E36b retrieval policy id and its default parameters (the design note's proposed
#: rule, and the values ``rails.acquisition.RetrievalPolicy`` validates).
DEFAULT_RETRIEVAL_POLICY_ID = "saea-requery-idf-v1"
DEFAULT_MIN_TOKEN_CHARS = 4
DEFAULT_MAX_DOCUMENT_FREQUENCY = 0.05
DEFAULT_EXCLUDE_VISIBLE_TOKENS = True
DEFAULT_K = 5


class ReplayError(RuntimeError):
    """A precondition of the replay is not met; refuse rather than guess."""


def _tokenize(text: str) -> frozenset:
    return frozenset(_TOKEN_RE.findall(text.casefold()))


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(document, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")


@dataclass(frozen=True)
class Args:
    repo_root: Path
    data_root: Path
    run_id: str
    attempt_id: str
    experiment: str
    cell_id: str
    k: int
    min_token_chars: int
    max_document_frequency: float
    exclude_visible_tokens: bool
    receipt_out: Path | None


def parse_args(argv=None) -> Args:
    import os

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--data-root", type=Path,
        default=Path(os.environ["SPEECHRL_DATA_DIR"]) if "SPEECHRL_DATA_DIR" in os.environ else None,
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--experiment", required=True, help="configs/experiment/<name>.json")
    parser.add_argument("--cell-id", default=None, help="defaults to --experiment")
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument("--min-token-chars", type=int, default=DEFAULT_MIN_TOKEN_CHARS)
    parser.add_argument(
        "--max-document-frequency", type=float, default=DEFAULT_MAX_DOCUMENT_FREQUENCY,
    )
    parser.add_argument(
        "--exclude-visible-tokens", dest="exclude_visible_tokens",
        action="store_true", default=DEFAULT_EXCLUDE_VISIBLE_TOKENS,
    )
    parser.add_argument(
        "--no-exclude-visible-tokens", dest="exclude_visible_tokens", action="store_false",
    )
    parser.add_argument("--receipt-out", type=Path, default=None)
    parsed = parser.parse_args(argv)
    if parsed.data_root is None:
        raise ReplayError("--data-root is required (or set SPEECHRL_DATA_DIR)")
    return Args(
        repo_root=parsed.repo_root, data_root=parsed.data_root,
        run_id=parsed.run_id, attempt_id=parsed.attempt_id,
        experiment=parsed.experiment, cell_id=parsed.cell_id or parsed.experiment,
        k=parsed.k, min_token_chars=parsed.min_token_chars,
        max_document_frequency=parsed.max_document_frequency,
        exclude_visible_tokens=parsed.exclude_visible_tokens,
        receipt_out=parsed.receipt_out,
    )


# ---------------------------------------------------------------------------
# 1. Rebuild the cell's own composite snapshot and an E36b-armed native config.
# ---------------------------------------------------------------------------


def _load_cell(repo_root: Path, experiment: str, cell_id: str) -> dict:
    experiment_path = repo_root / "configs" / "experiment" / f"{experiment}.json"
    if not experiment_path.is_file():
        raise ReplayError(f"no such experiment fragment: {experiment_path}")
    document = _load_json(experiment_path)
    for cell in document.get("cells", []):
        if cell.get("cell_id") == cell_id:
            return cell
    raise ReplayError(f"cell {cell_id!r} not found in {experiment_path}")


def build_composed_and_binding(args: Args):
    sys.path.insert(0, str(args.repo_root / "src"))
    from speech_aware_evidence_acquisition.core.config import compose  # noqa: PLC0415
    from speech_aware_evidence_acquisition.rails.knowledge_stores import (  # noqa: PLC0415
        load_knowledge_store_binding,
    )

    cell = _load_cell(args.repo_root, args.experiment, args.cell_id)
    composed = compose(
        args.repo_root, cell["model_fragment"], cell["dataset_fragment"],
        cell["baseline_fragment"], args.experiment,
    )
    binding = load_knowledge_store_binding(composed.values, data_root=args.data_root)
    if binding is None:
        raise ReplayError(f"cell {args.cell_id!r} declares no knowledge_stores")
    return composed, binding


def _armed_native_episode_values(composed_values: dict, args: Args) -> dict:
    """The cell's own composed values, with EXACTLY the two E36b keys added to
    ``native_episode.acquisition`` -- nothing else moves. Refuses if the cell is not already an
    armed ``knowledge-requery`` acquisition (kind (a)): a v1-shaped cell (no acquisition at all)
    has no ACQUIRE rows to replay in the first place."""

    values = copy.deepcopy(dict(composed_values))
    episode = values.get("native_episode")
    if not isinstance(episode, dict) or "acquisition" not in episode:
        raise ReplayError(
            "the cell's own baseline does not arm native_episode.acquisition; nothing to replay"
        )
    acquisition_block = dict(episode["acquisition"])
    budget_block = dict(acquisition_block["budget"])
    budget_block["max_items_per_acquisition"] = args.k
    acquisition_block["budget"] = budget_block
    acquisition_block["retrieval"] = {
        "policy": DEFAULT_RETRIEVAL_POLICY_ID,
        "min_token_chars": args.min_token_chars,
        "max_document_frequency": args.max_document_frequency,
        "exclude_visible_tokens": args.exclude_visible_tokens,
    }
    episode["acquisition"] = acquisition_block
    values["native_episode"] = episode
    return values


def build_native_config(repo_root: Path, armed_values: dict):
    from speech_aware_evidence_acquisition.rails.controllers import (  # noqa: PLC0415
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.native_episode_config import (  # noqa: PLC0415
        load_native_episode_config,
    )

    program = default_phase_program(armed_values["policy"])
    config = load_native_episode_config(armed_values, program)
    if config is None or config.max_items_per_acquisition is None:
        raise ReplayError(
            "the re-armed config did not compose with max_items_per_acquisition set"
        )
    return config


def build_production_requery(native_config, store_binding):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime  # noqa: PLC0415

    fake_self = SimpleNamespace(_knowledge_store_binding=store_binding)
    requery = FlightRuntime._acquisition_requery_binding(
        fake_self, native_config, lambda *_a, **_k: None, None,
    )
    if requery is None:
        raise ReplayError("the armed config did not build a knowledge-requery callable")
    return requery


def store_of(binding, value_id: str) -> str:
    from speech_aware_evidence_acquisition.rails.knowledge_stores import STORE_SEPARATOR  # noqa: PLC0415

    for store_id in binding.store_ids:
        if value_id.startswith(f"{store_id}{STORE_SEPARATOR}"):
            return store_id
    return "?"


# ---------------------------------------------------------------------------
# 2. The independent diagnostic scorer (cross-checked against the production call).
# ---------------------------------------------------------------------------


def build_vocabulary(values_by_id: dict) -> tuple[dict, "collections.Counter"]:
    value_tokens: dict[str, frozenset] = {}
    document_frequency: collections.Counter = collections.Counter()
    for value_id, value in values_by_id.items():
        text = value.content + " " + " ".join(value.associated_facet_ids)
        tokens = _tokenize(text)
        value_tokens[value_id] = tokens
        document_frequency.update(tokens)
    return value_tokens, document_frequency


def _diagnose_row(
    *, filters, exclude_value_ids: frozenset, value_tokens: dict,
    document_frequency: "collections.Counter", total_values: int,
    min_token_chars: int, max_document_frequency: float, exclude_visible_tokens: bool, k: int,
) -> dict:
    query_tokens = _tokenize(" ".join(str(token) for token in filters))
    visible_tokens: frozenset = frozenset()
    if exclude_visible_tokens:
        for value_id in exclude_value_ids:
            visible_tokens |= value_tokens.get(value_id, frozenset())
    dropped_by_reason: collections.Counter = collections.Counter()
    kept: list[str] = []
    for token in sorted(query_tokens):
        if len(token) < min_token_chars:
            dropped_by_reason["too-short"] += 1
            continue
        document_count = document_frequency.get(token, 0)
        if document_count == 0:
            dropped_by_reason["absent-from-snapshot"] += 1
            continue
        if total_values and document_count / total_values > max_document_frequency:
            dropped_by_reason["too-common"] += 1
            continue
        if exclude_visible_tokens and token in visible_tokens:
            dropped_by_reason["visible-in-row"] += 1
            continue
        kept.append(token)
    result = {
        "tokens_total": len(query_tokens),
        "tokens_kept": len(kept),
        "tokens_dropped_by_reason": dict(dropped_by_reason),
        "candidates": 0,
        "top": [],
    }
    if not kept:
        return result
    weights = {
        token: math.log(total_values / document_frequency[token]) for token in kept
    }
    scored: list[tuple[str, float]] = []
    for value_id, tokens in value_tokens.items():
        if value_id in exclude_value_ids:
            continue
        matched = [token for token in kept if token in tokens]
        if not matched:
            continue
        scored.append((value_id, sum(weights[token] for token in matched)))
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    result["candidates"] = len(scored)
    result["top"] = scored[:k]
    return result


# ---------------------------------------------------------------------------
# 3. The sealed run's own ACQUIRE rows and their already-visible (excluded) ids.
# ---------------------------------------------------------------------------


def _find_outputs_path(data_root: Path, run_id: str, attempt_id: str) -> Path:
    run_dir = data_root / "runs" / run_id / attempt_id
    matches = sorted(glob.glob(str(run_dir / "*.outputs.jsonl")))
    if not matches:
        raise ReplayError(f"no outputs.jsonl under {run_dir}")
    return Path(matches[0])


def _load_prepared_supply_values(data_root: Path, run_id: str) -> dict:
    """The row's own ALREADY-VISIBLE ids, reconstructed from this run's OWN prepared
    first-phase supply artifact (E16: a prepared artifact is evidence only for the
    implementation that produced it). The acquisition receipt itself never carries
    ``supplied_value_ids`` (only ``provenance_ids``, the ACQUIRED ones), so this is the same
    reconstruction the 2026-09-22 design-note replay used: the Solver's own separately-supplied
    exemplar store is not covered by this artifact, so a row's ``visible`` count here is a lower
    bound and its candidate/match counts are correspondingly upper bounds (design note section 6).
    """

    matches = sorted(
        glob.glob(str(data_root / "prepared" / run_id / "phase-supply-v*.json"))
    )
    if not matches:
        return {}
    supply = _load_json(Path(matches[-1]))
    return (supply.get("output") or {}).get("values") or {}


def visible_ids_for(sample_id: str, supply_values: dict) -> frozenset:
    ids: set[str] = set()
    for _phase, rows in supply_values.items():
        for value_id in rows.get(sample_id) or ():
            ids.add(value_id)
    return frozenset(ids)


def iter_acquire_rows(outputs_path: Path):
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            receipt = row.get("native_episode_receipt") or {}
            acquisitions = (receipt.get("acquisition") or {}).get("acquisitions") or []
            if not acquisitions:
                continue
            yield row["sample_id"], acquisitions


# ---------------------------------------------------------------------------
# 4. Drive the replay.
# ---------------------------------------------------------------------------


def run_replay(args: Args) -> dict:
    composed, binding = build_composed_and_binding(args)
    armed_values = _armed_native_episode_values(composed.values, args)
    native_config = build_native_config(args.repo_root, armed_values)
    requery = build_production_requery(native_config, binding)

    values_by_id = {value.value_id: value for value in binding.composite_snapshot.values}
    value_tokens, document_frequency = build_vocabulary(values_by_id)
    total_values = len(values_by_id)

    outputs_path = _find_outputs_path(args.data_root, args.run_id, args.attempt_id)
    supply_values = _load_prepared_supply_values(args.data_root, args.run_id)

    per_row: list[dict] = []
    store_mix = collections.Counter()
    for sample_id, acquisitions in iter_acquire_rows(outputs_path):
        visible = visible_ids_for(sample_id, supply_values)
        for entry in acquisitions:
            filters = tuple(entry.get("state_filters") or ())
            diagnosis = _diagnose_row(
                filters=filters, exclude_value_ids=visible, value_tokens=value_tokens,
                document_frequency=document_frequency, total_values=total_values,
                min_token_chars=args.min_token_chars,
                max_document_frequency=args.max_document_frequency,
                exclude_visible_tokens=args.exclude_visible_tokens, k=args.k,
            )
            produced = list(requery(
                phase_id=None, filters=filters, exclude_value_ids=visible,
                scope={"kinds": ["knowledge-requery"]}, context=None,
            ))
            produced_ids = [item.evidence_id for item in produced]
            diagnosed_ids = [value_id for value_id, _score in diagnosis["top"]]
            if produced_ids != diagnosed_ids:
                raise ReplayError(
                    "the production callable and the diagnostic scorer disagree on sample "
                    f"{sample_id!r}: {produced_ids!r} != {diagnosed_ids!r}"
                )
            top_stores = [store_of(binding, value_id) for value_id in produced_ids]
            top_scores = [score for _value_id, score in diagnosis["top"]]
            store_mix.update(top_stores)
            per_row.append({
                "sample_id": sample_id,
                "visit_index": entry.get("visit_index"),
                "visible_ids_count": len(visible),
                "tokens_total": diagnosis["tokens_total"],
                "tokens_kept": diagnosis["tokens_kept"],
                "tokens_dropped_by_reason": diagnosis["tokens_dropped_by_reason"],
                "candidates": diagnosis["candidates"],
                "top_k_count": len(produced_ids),
                "top_k_stores": top_stores,
                "top_k_scores": top_scores,
            })

    rows_with_item = sum(1 for row in per_row if row["top_k_count"] >= 1)
    tokens_kept_values = sorted(row["tokens_kept"] for row in per_row)
    median_tokens_kept = (
        tokens_kept_values[len(tokens_kept_values) // 2] if tokens_kept_values else 0
    )
    aggregates = {
        "rows_replayed": len(per_row),
        "rows_with_at_least_one_item": rows_with_item,
        "store_mix_of_top_k": dict(store_mix),
        "median_tokens_kept": median_tokens_kept,
        "candidates_min": min((row["candidates"] for row in per_row), default=0),
        "candidates_max": max((row["candidates"] for row in per_row), default=0),
    }
    return {
        "schema": SCHEMA,
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "network": 0},
        "run_id": args.run_id,
        "attempt_id": args.attempt_id,
        "experiment": args.experiment,
        "cell_id": args.cell_id,
        "composite_snapshot_values": total_values,
        "store_ids": list(binding.store_ids),
        "retrieval_policy": {
            "policy": DEFAULT_RETRIEVAL_POLICY_ID,
            "min_token_chars": args.min_token_chars,
            "max_document_frequency": args.max_document_frequency,
            "exclude_visible_tokens": args.exclude_visible_tokens,
            "max_items_per_acquisition": args.k,
        },
        "per_row": per_row,
        "aggregates": aggregates,
        "caveat": (
            "visible_ids_count is reconstructed from this run's own prepared first-phase supply "
            "artifact only; the Solver's own separately-supplied exemplar store is not covered "
            "by that artifact, so visible counts are lower bounds and candidate/top-k counts are "
            "correspondingly upper bounds (design note section 6)."
        ),
    }


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        receipt = run_replay(args)
    except ReplayError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    if args.receipt_out is not None:
        _write_json(args.receipt_out, receipt)
        print(f"wrote {args.receipt_out}")
    print(json.dumps(receipt["aggregates"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
