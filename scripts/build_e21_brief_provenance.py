#!/usr/bin/env python3
"""Per-call provenance for the Earnings-21 pre-meeting brief.

E5 deliverable 3: prove, call by call and hash by hash, that
``conec-class-lists`` builds an EVALUATION call's brief from that call's OWN
ConEC context and from nothing else. The renderer's boundary is asserted by
``tests/unit/test_class_lists.py`` (every path it opens is under ``contexts/``,
and two calls with disjoint vocabularies produce disjoint briefs); this script
is the other half -- the actual 44 calls, the actual files, the actual sha256s,
and the actual token cost the flight will pay.

    python scripts/build_e21_brief_provenance.py

Writes ``docs/checks/speech-aware-evidence-acquisition/
2026-09-06-e21-pre-meeting-brief-provenance/``.

**Zero contacts of every kind** and **no gold or reference read**. The two files
per call are ConEC CONTEXT -- classified ``runtime-legal-input`` by
``docs/readiness/2026-09-03-information-audit-earnings21-conec.md``, i.e. the
same pre-existing call documents a human reads before joining the call. No
reference transcript, timestamp file or ``wer_tags`` sidecar is opened, and the
paths this script can name are exactly the two the evidence source itself
resolves. Whitespace token counts only; the FLIGHT measures the brief on the
flight tokenizer and reports that distribution, which is a model-free
measurement this script deliberately does not guess at.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.e21_agentic_metric_baseline import (  # noqa: E402
    EVALUATION_CALLS,
)
from speech_aware_evidence_acquisition.core.class_lists import (  # noqa: E402
    whitespace_token_count,
)
from speech_aware_evidence_acquisition.core.evidence import (  # noqa: E402
    _conec_class_lists,
    _conec_class_lists_placebo,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.splits import discovery_split  # noqa: E402

CARRIER = "earnings21-original"
CHECK_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-pre-meeting-brief-provenance"
)
#: The construction call whose full brief is reproduced verbatim in the receipt,
#: so a reader can see the artifact rather than only its shape. A CONSTRUCTION
#: call by choice: an evaluation call's brief is the thing under test, and this
#: receipt is not the place to publish it.
EXAMPLE_CALL = "4320211"


def _lock_path() -> Path:
    """The umbrella lock. ``umbrella_lock_path`` resolves it from the registered
    ``<umbrella>/studies/<study>/`` layout, which a git WORKTREE checkout is not
    in; fall back to the sibling umbrella beside the worktree root."""

    try:
        return umbrella_lock_path()
    except Exception:  # noqa: BLE001 - the fallback is the whole point
        candidate = REPO.parent.parent / "exploring-l4-intelligence" / "docs" / "datasets.lock.json"
        if not candidate.is_file():
            raise
        return candidate


def main() -> int:
    lock_path = _lock_path()
    lock = load_lock(lock_path)
    root = data_root()
    # ``SplitSpec.ids`` are carrier-qualified ("earnings21-original/4320211");
    # every evidence source takes the bare sample id plus the carrier key.
    calls = sorted(key.rsplit("/", 1)[-1] for key in discovery_split(lock, root).ids)
    evaluation = set(EVALUATION_CALLS)

    rows: list[dict[str, object]] = []
    example: dict[str, str] = {}
    for sample_id in calls:
        items = _conec_class_lists(lock, root, sample_id, CARRIER)
        twin = _conec_class_lists_placebo(lock, root, sample_id, CARRIER)
        row: dict[str, object] = {
            "sample_id": sample_id,
            "roster": "evaluation" if sample_id in evaluation else "construction",
            "sources": [],
            "brief_whitespace_tokens": sum(whitespace_token_count(i.content) for i in items),
            "placebo_whitespace_tokens": sum(whitespace_token_count(i.content) for i in twin),
        }
        for item, twin_item in zip(items, twin):
            assert item.derivation is not None
            row["sources"].append(  # type: ignore[union-attr]
                {
                    "part": item.provenance["brief_part"],
                    "lock_key": item.provenance["lock_key"],
                    "source_relpath": item.derivation.source_relpath,
                    "source_sha256": item.derivation.source_sha256,
                    "transform": item.derivation.transform_name,
                    "derived_sha256": item.derivation.derived_sha256,
                    "whitespace_tokens": whitespace_token_count(item.content),
                    "placebo_derived_sha256": twin_item.derivation.derived_sha256,
                }
            )
        rows.append(row)
        if sample_id == EXAMPLE_CALL:
            example = {
                "sample_id": sample_id,
                "roster": str(row["roster"]),
                "brief": "\n\n".join(item.content for item in items),
                "placebo": "\n\n".join(item.content for item in twin),
            }

    # Every call's two source relpaths must be distinct from every other call's:
    # the construction/evaluation separation, stated as an assertion over the
    # real 44 rather than as a claim about the code.
    seen: dict[str, str] = {}
    for row in rows:
        for source in row["sources"]:  # type: ignore[union-attr]
            relpath = str(source["source_relpath"])
            if relpath in seen:
                raise SystemExit(
                    f"call {row['sample_id']} and call {seen[relpath]} resolve the SAME "
                    f"source file {relpath}; the per-call separation is broken"
                )
            seen[relpath] = str(row["sample_id"])
            if str(row["sample_id"]) not in relpath:
                raise SystemExit(
                    f"call {row['sample_id']}'s source {relpath} is not keyed by its own "
                    "sample id"
                )

    tokens = sorted(int(row["brief_whitespace_tokens"]) for row in rows)
    summary = {
        "schema": "saea-e21-brief-provenance-v1",
        "generated_by": "scripts/build_e21_brief_provenance.py",
        "carrier_lock_key": CARRIER,
        "evidence_sources": ["conec-class-lists", "conec-class-lists-placebo"],
        "lock_path": str(lock_path),
        "calls": len(rows),
        "construction_calls": sum(1 for row in rows if row["roster"] == "construction"),
        "evaluation_calls": sum(1 for row in rows if row["roster"] == "evaluation"),
        "distinct_source_files": len(seen),
        "per_call_separation": (
            "every call's two source files are keyed by that call's own sample id and are "
            "shared with no other call"
        ),
        "brief_whitespace_tokens": {
            "min": tokens[0],
            "median": tokens[len(tokens) // 2],
            "max": tokens[-1],
            "total": sum(tokens),
        },
        "placebo_matches_brief_token_count": all(
            row["brief_whitespace_tokens"] == row["placebo_whitespace_tokens"] for row in rows
        ),
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "network": 0,
            "audio_seconds": 0,
            "gold_or_reference_reads": 0,
        },
        "rows": rows,
    }

    CHECK_DIR.mkdir(parents=True, exist_ok=True)
    (CHECK_DIR / "brief-provenance.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    (CHECK_DIR / "example-brief.json").write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    table = ["| call | roster | roster file sha256 | context file sha256 | brief tokens |", "|---|---|---|---|---:|"]
    for row in rows:
        sources = {str(s["part"]): s for s in row["sources"]}  # type: ignore[union-attr]
        table.append(
            f"| {row['sample_id']} | {row['roster']} | "
            f"`{str(sources['roster']['source_sha256'])[:12]}` | "
            f"`{str(sources['document']['source_sha256'])[:12]}` | "
            f"{row['brief_whitespace_tokens']} |"
        )
    (CHECK_DIR / "per-call-sources.md").write_text(
        "\n".join(table) + "\n", encoding="utf-8", newline="\n"
    )

    digests = []
    for name in sorted(path.name for path in CHECK_DIR.iterdir() if path.name != "MANIFEST.sha256"):
        digest = hashlib.sha256((CHECK_DIR / name).read_bytes()).hexdigest()
        digests.append(f"{digest}  {name}")
    (CHECK_DIR / "MANIFEST.sha256").write_text(
        "\n".join(digests) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        json.dumps(
            {
                key: summary[key]
                for key in (
                    "calls",
                    "construction_calls",
                    "evaluation_calls",
                    "distinct_source_files",
                    "brief_whitespace_tokens",
                    "placebo_matches_brief_token_count",
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
