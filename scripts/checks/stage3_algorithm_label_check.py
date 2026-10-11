#!/usr/bin/env python3
"""Model-free gate: every Stage-3 cell names the training-free RL it uses.

Owner decision 101 (2026-09-22, translated): *"in the Stage-3 experiment
set-up, different experiments must explicitly mark which training-free RL they
use; you may explore several groups of training-free RL algorithms."* Recorded
as row 101 of
``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``.

Layer A of Stage 3 flies at least three families -- Training-Free GRPO, GEPA,
ACE -- on the SAME ROLL-1 rollouts and the SAME locked plan. That only reads as
a comparison if each cell says, in machine-checked form, which family it is an
instance of and which loop operator it exercises. A verdict table whose arms
are distinguished only by a run id and a prose purpose is a table nobody can
re-read a month later.

So: every Stage-3 EXPERIMENT fragment carries a top-level ``stage3_algorithm``
object ::

    "stage3_algorithm": {
      "id": "<id registered in core.base.STAGE3_ALGORITHMS>",
      "operators_used": ["credit_assignment"],
      "note": "one sentence"
    }

and this script is the rule. A rule that lives only in a spec is not a rule.

**What counts as a Stage-3 cell** (rule 1). A fragment under
``configs/experiment/`` is in scope when ANY of:

* its file stem or its ``experiment_id`` carries the token ``stage3``; or
* its text names one of the two Stage-3 specs
  (:data:`STAGE3_SPEC_RELPATHS`) -- the readiness reason or preregistration
  pointer of a Stage-3 cell always does; or
* it is listed in :data:`EXPLICIT_STAGE3_CELLS` -- a Stage-3 cell whose name
  and text predate the Stage-3 vocabulary, named here one by one with its
  reason.

Deliberately NOT in scope: a fragment that merely mentions "Stage 3" in prose.
Sixty-odd Stage-2 fragments say things like "belongs to Stage-3" in a purpose
or a prohibition, and treating those as Stage-3 cells would make this gate a
noise generator rather than a rule.

**What every in-scope cell must satisfy** (rule 2). Its ``stage3_algorithm``
label is present, its ``id`` resolves in ``core.base.STAGE3_ALGORITHMS``, its
``note`` is a non-empty sentence, and its ``operators_used`` is a
non-repeating subset of the operators that algorithm DEFINES (the ``none``
record defines none, so its cells declare an empty list). The validation is
the registry's own -- ``core.stage3_algorithms.validate_stage3_algorithm_label``
-- so this gate and any consumer of the label agree on what a label is.

**The pre-decision-101 allowlist** (:data:`ALLOWLIST`). Editing an experiment
fragment moves its fragment hash and therefore the composed hash its readiness
package pinned. Cells whose plans are already registered and pinned are
therefore NOT edited: R-PRIM (``SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-*``,
readiness ``ready``, registered plans under
``docs/readiness/2026-09-22-slurp-review-primitives-v1/``) and the S3-1 packet
promotion (config hash pinned in
``docs/readiness/2026-09-22-slurp-stage3-construction-r01-preparations-v1.md``
and carried by DRAFT ledger rows). Each is allowlisted here WITH the label it
wears in prose in its own readiness note, and that prose id must itself
resolve in the registry -- an allowlist entry can name a dead id exactly as
easily as a fragment can, and neither is allowed. A cell leaves the allowlist
the next time it is re-pinned (``scripts/flights/repin_cell.py``), which is
the only path that recomputes a package's dependent hashes in one cycle.

Exact historical metadata corrections are separately hash-pinned to both the
original fragment and a root disposition. They are disclosed in the table and
JSON, retain the original label, and grant no runtime admission. The corrected
label still passes the same registry validator. Never rewrite frozen fragments.

Exit 0 prints the table (cell -> algorithm id). Exit 1 prints one message per
offending cell.

Zero model contacts, zero GPU, no network, no ``SPEECHRL_DATA_DIR`` read.

Flags: ``--repo-root``, ``--json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]

EXPERIMENT_DIR = Path("configs/experiment")

#: The two Stage-3 specifications. A fragment that names either one is a
#: Stage-3 cell whatever it is called.
STAGE3_SPEC_RELPATHS = (
    "docs/superpowers/specs/2026-09-21-slurp-stage3-training-free-rl-design.md",
    "docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md",
)

#: The token a Stage-3 fragment's stem / ``experiment_id`` carries.
STAGE3_NAME_TOKEN = "stage3"

#: Stage-3 cells whose names predate the Stage-3 vocabulary, one line each.
EXPLICIT_STAGE3_CELLS: dict[str, str] = {
    "slurp-native-review-primitives-v1": (
        "Cell R-PRIM (item E37, owner decision 84): the design spec's own order of the "
        "first Stage-3 cells is E37 -> the decision-85 pruning cells -> the layer-A base "
        "loop, so R-PRIM is a Stage-3 cell even though its name carries no Stage-3 token."
    ),
    "slurp-native-review-primitives-smoke-4-v1": (
        "The four-row smoke of the R-PRIM cell above; same package, same scope."
    ),
}

#: Pre-decision-101 cells that are NOT edited because their composed hashes are
#: pinned: fragment stem -> (the algorithm id it wears in prose, the reason).
ALLOWLIST: dict[str, tuple[str, str]] = {
    "slurp-native-review-primitives-v1": (
        "none",
        "READY and flight-pinned: docs/readiness/2026-09-22-slurp-review-primitives-v1/"
        "generation-plan-registered-v1.json and its siblings pin this fragment's composed "
        "hash, and the exposure ledger registers run id "
        "SAEA-SLURP-NATIVE-REVIEW-PRIMITIVES-V1 against it. The label is prose in that "
        "package's README.md until the cell is next re-pinned.",
    ),
    "slurp-native-review-primitives-smoke-4-v1": (
        "none",
        "The four-row smoke of the cell above, pinned by the same package "
        "(smoke-generation-plan-registered-v1.json) and the same ledger rows.",
    ),
    "slurp-stage3-construction-r01-preprocess-recovery-v1": (
        "none",
        "The one recovery of the S3-1 packet promotion (run "
        "SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS-RECOVERY-V1), registered in the "
        "exposure ledger and IN FLIGHT from study commit c2df0d40 when decision 101's "
        "label landed; its composed hash is recorded by the run's own receipt, so the "
        "fragment is not edited. Label is prose in the preparations note (section 7).",
    ),
    "slurp-stage3-construction-r01-preprocess": (
        "none",
        "The S3-1 packet-promotion preparation (SAEA-SN-STAGE3-CONSTRUCTION-R01-PREPROCESS). "
        "Its composed config hash is pinned in docs/readiness/"
        "2026-09-22-slurp-stage3-construction-r01-preparations-v1.md and carried by that "
        "note's DRAFT ledger rows; it is a model-free preparation with no training-free RL "
        "operator, and its label is prose in that note.",
    ),
}


# Exact historical catalogue errata never change runtime fragments or admission.
# Any byte change requires a new prospective correction instead of a broad exemption.
METADATA_CORRECTIONS: dict[str, dict[str, str]] = {'slurp-native-stage3-system-text-native-capacity-v1': {'fragment_sha256': '3e907901e3a857c4523adefd54ad91cdbeef4a1802e2bd1836d377c08f3c28e2',
                                                        'receipt_relpath': 'docs/receipts/continuation/2026-10-06-historical-capacity-algorithm-label-correction.json',
                                                        'receipt_sha256': 'd11b742025050037cd2a132754a10a17295689d6afc3829e5f0193e410f58c95'},
 'slurp-native-stage3-system-text-native-capacity-recovery1-v1': {'fragment_sha256': '61efa82978b64e71bc148bde6f2e1cf7d135a301c83cceedba3b488bc7403c23',
                                                                  'receipt_relpath': 'docs/receipts/continuation/2026-10-06-historical-capacity-algorithm-label-correction.json',
                                                                  'receipt_sha256': 'd11b742025050037cd2a132754a10a17295689d6afc3829e5f0193e410f58c95'}}


def _metadata_label(repo_root: Path, path: Path, document: Any) -> tuple[object, dict | None]:
    """Resolve only pinned catalogue metadata; preserve strict label validation."""
    binding = METADATA_CORRECTIONS.get(path.stem)
    if binding is None:
        return document.get("stage3_algorithm") if isinstance(document, dict) else None, None
    receipt_path = repo_root / binding["receipt_relpath"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != binding["fragment_sha256"]:
        raise ValueError("Historical fragment bytes differ from the exact correction")
    receipt_bytes = receipt_path.read_bytes()
    if hashlib.sha256(receipt_bytes).hexdigest() != binding["receipt_sha256"]:
        raise ValueError("Historical correction receipt hash differs")
    receipt = json.loads(receipt_bytes)
    if (receipt["schema"] != "saea-historical-algorithm-metadata-correction-v1"
            or receipt["authority"] != "owner227" or receipt["status"] != "decided"
            or receipt["scope"] != "historical-metadata-only"
            or receipt["runtime_admission"] is not False):
        raise ValueError("Historical correction has no exact metadata-only disposition")
    correction = receipt["corrections"][path.stem]
    if (correction["fragment_sha256"] != binding["fragment_sha256"]
            or correction["original_label"] != document.get("stage3_algorithm")):
        raise ValueError("Historical correction does not bind the original label")
    return correction["corrected_label"], {
        **binding, "original_label": correction["original_label"],
        "runtime_admission": False,
    }


class Stage3AlgorithmLabelCheckError(RuntimeError):
    """The check cannot run: an unreadable tree or an unimportable registry."""


def _load_registry(repo_root: Path) -> Any:
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from speech_aware_evidence_acquisition.core import (  # noqa: PLC0415
            stage3_algorithms,
        )
    except Exception as error:  # pragma: no cover - import environment problem
        raise Stage3AlgorithmLabelCheckError(
            f"cannot import the Stage-3 algorithm registry from {src}: {error}"
        ) from error
    return stage3_algorithms


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Stage3AlgorithmLabelCheckError(f"{path} is unreadable: {error}") from error


def is_stage3_fragment(stem: str, document: Any, text: str) -> tuple[bool, str]:
    """``(in scope, why)`` for one experiment fragment."""

    if stem in EXPLICIT_STAGE3_CELLS:
        return True, "explicit-list"
    if STAGE3_NAME_TOKEN in stem.lower():
        return True, "fragment-name"
    experiment_id = document.get("experiment_id") if isinstance(document, dict) else None
    if isinstance(experiment_id, str) and STAGE3_NAME_TOKEN in experiment_id.lower():
        return True, "experiment-id"
    for relpath in STAGE3_SPEC_RELPATHS:
        if relpath in text:
            return True, "names-stage3-spec"
    return False, ""


def evaluate(repo_root: Path) -> dict[str, Any]:
    registry = _load_registry(repo_root)

    for stem, (prose_id, _reason) in sorted(ALLOWLIST.items()):
        try:
            registry.resolve_stage3_algorithm(prose_id)
        except registry.Stage3AlgorithmError as error:
            raise Stage3AlgorithmLabelCheckError(
                f"allowlist entry {stem!r} names an unregistered algorithm: {error}"
            ) from None

    directory = repo_root / EXPERIMENT_DIR
    if not directory.is_dir():
        raise Stage3AlgorithmLabelCheckError(f"missing {EXPERIMENT_DIR.as_posix()}")

    rows: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    scanned = 0

    for path in sorted(directory.glob("*.json")):
        scanned += 1
        text = path.read_text(encoding="utf-8")
        document = _read_json(path)
        stem = path.stem
        in_scope, why = is_stage3_fragment(stem, document, text)
        if not in_scope:
            continue

        cell = f"{EXPERIMENT_DIR.as_posix()}/{path.name}"
        if stem in ALLOWLIST:
            prose_id, reason = ALLOWLIST[stem]
            rows.append(
                {
                    "cell": stem,
                    "in_scope_because": why,
                    "algorithm_id": prose_id,
                    "operators_used": [],
                    "source": "allowlist-prose",
                    "reason": reason,
                }
            )
            continue

        try:
            label, correction = _metadata_label(repo_root, path, document)
        except (OSError, ValueError, KeyError, TypeError) as error:
            violations.append({"cell": stem, "kind": "invalid-metadata-correction", "message": str(error)})
            continue
        if label is None:
            violations.append(
                {
                    "cell": stem,
                    "kind": "missing-label",
                    "message": (
                        f"{cell}: Stage-3 cell ({why}) carries no top-level "
                        f"{registry.LABEL_KEY!r}; owner decision 101 requires one whose id "
                        f"resolves in core.base.STAGE3_ALGORITHMS "
                        f"({registry.registered_ids()})"
                    ),
                }
            )
            continue
        try:
            record, used = registry.validate_stage3_algorithm_label(label, cell=cell)
        except registry.Stage3AlgorithmError as error:
            violations.append(
                {"cell": stem, "kind": "invalid-label", "message": str(error)}
            )
            continue
        rows.append(
            {
                "cell": stem,
                "in_scope_because": why,
                "algorithm_id": record.id,
                "operators_used": list(used),
                **({"columns": registry.columns_of(label)} if registry.columns_of(label) else {}),
                "source": "hash-pinned-metadata-correction" if correction else "fragment",
                "reason": "Pinned historical catalogue correction; no runtime admission." if correction else None,
                **({"metadata_correction": correction} if correction else {}),
            }
        )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["algorithm_id"]] = counts.get(row["algorithm_id"], 0) + 1

    return {
        "schema": "saea-stage3-algorithm-label-check-v1",
        "repo_root": str(repo_root),
        "experiment_dir": EXPERIMENT_DIR.as_posix(),
        "registered_algorithms": registry.registered_ids(),
        "operators": list(registry.STAGE3_OPERATORS),
        "scanned_fragments": scanned,
        "stage3_cells": sorted(rows, key=lambda row: row["cell"]),
        "allowlisted_cells": sorted(stem for stem in ALLOWLIST),
        "cells_per_algorithm": dict(sorted(counts.items())),
        "violations": sorted(violations, key=lambda row: row["cell"]),
        "passed": not violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        data = evaluate(args.repo_root.resolve())
    except Stage3AlgorithmLabelCheckError as error:
        print(f"stage3 algorithm label check: FAIL: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for violation in data["violations"]:
        print(f"stage3 algorithm label check: FAIL: {violation['message']}")

    summary = (
        f"{len(data['stage3_cells'])} Stage-3 cell(s) of {data['scanned_fragments']} "
        f"experiment fragment(s); {len(data['allowlisted_cells'])} allowlisted "
        f"(pre-decision-101, flight-pinned)"
    )
    if not data["passed"]:
        print(
            f"stage3 algorithm label check: FAIL ({len(data['violations'])} finding(s); "
            f"{summary})"
        )
        return 1

    width = max((len(row["cell"]) for row in data["stage3_cells"]), default=0)
    for row in data["stage3_cells"]:
        operators = ", ".join(row["operators_used"]) or "-"
        marker = " [allowlisted, prose]" if row["source"] == "allowlist-prose" else ""
        if row["source"] == "hash-pinned-metadata-correction":
            marker = " [hash-pinned historical correction]"
        print(f"  {row['cell']:<{width}}  {row['algorithm_id']}  ({operators}){marker}")
    print(f"stage3 algorithm label check: PASS ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
