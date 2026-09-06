#!/usr/bin/env python3
"""Emit ``docs/taxonomies/semantic-high-impact/ACTIVE.json`` and its receipt.

The taxonomy is a MECHANICAL PROJECTION of the Earnings-22 semantic scan's
committed content-impact model onto the ``(reference word, hypothesis word)``
key shape ``reproduction.semantic_impact`` looks rules up by; every judgement in
it is the scan's. ``analysis.semantic_impact_taxonomy`` is the projection and
carries the reasoning, including the two HIGH triggers this key shape cannot
express.

    python scripts/build_semantic_impact_taxonomy.py

Writes the taxonomy, re-loads it through the scorer's own ``load_taxonomy`` (so
a file that would fail closed at score time fails here instead), and writes
``docs/checks/speech-aware-evidence-acquisition/2026-09-06-semantic-impact-taxonomy/``
with the E22 scan module's pinned commit, the sha256 of ITS blob bytes at that
commit, and the taxonomy's own sha256.

Zero contacts of every kind: no model, no GPU, no network, no audio, no gold.
The only inputs are two committed source modules and ``git show``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.semantic_impact_taxonomy import (  # noqa: E402
    SOURCE_MODULE,
    TAXONOMY_ID,
    build_taxonomy,
    rule_keys,
)
from speech_aware_evidence_acquisition.reproduction.semantic_impact import (  # noqa: E402
    ACTIVE_TAXONOMY_RELPATH,
    load_taxonomy,
)

CHECK_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-semantic-impact-taxonomy"
)
GENERATOR_RELPATH = "scripts/build_semantic_impact_taxonomy.py"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout


def source_pin() -> tuple[str, str]:
    """The commit that last touched the E22 scan module, and the sha256 of its
    BLOB BYTES at that commit -- the repository's stated hash authority, never
    the working-tree bytes (CLAUDE.md, "Git blob bytes are the evidence hash
    authority")."""

    commit = _git("log", "--format=%H", "-1", "--", SOURCE_MODULE).strip()
    if not commit:
        raise SystemExit(f"no commit found for {SOURCE_MODULE}")
    blob = subprocess.run(
        ["git", "show", f"{commit}:{SOURCE_MODULE}"],
        cwd=REPO,
        check=True,
        capture_output=True,
    ).stdout
    return commit, hashlib.sha256(blob).hexdigest()


def main() -> int:
    commit, blob_sha256 = source_pin()
    document = build_taxonomy(
        source_commit=commit,
        source_sha256=blob_sha256,
        generator_relpath=GENERATOR_RELPATH,
    )
    keys = rule_keys(document["rules"])  # type: ignore[arg-type]
    if len(set(keys)) != len(keys):
        raise SystemExit("the projection produced a duplicate key; the loader would refuse it")

    target = REPO / ACTIVE_TAXONOMY_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    target.write_text(text, encoding="utf-8", newline="\n")

    # Load it back through the scorer's own reader: a taxonomy this refuses is
    # a taxonomy the Earnings scoring job would refuse, and the refusal belongs
    # here rather than 600 seconds into a scoring run.
    taxonomy = load_taxonomy(target)
    if taxonomy.taxonomy_id != TAXONOMY_ID:
        raise SystemExit(f"round trip changed the taxonomy id: {taxonomy.taxonomy_id}")

    taxonomy_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    levels = {level: 0 for level in taxonomy.levels}
    for level, _ in taxonomy.rules.values():
        levels[level] = levels.get(level, 0) + 1
    receipt = {
        "schema": "saea-semantic-impact-taxonomy-receipt-v1",
        "generated_by": GENERATOR_RELPATH,
        "taxonomy_relpath": ACTIVE_TAXONOMY_RELPATH,
        "taxonomy_id": taxonomy.taxonomy_id,
        "taxonomy_sha256": taxonomy_sha256,
        "normalizer": taxonomy.normalizer,
        "levels": list(taxonomy.levels),
        "high_level": taxonomy.high_level,
        "rules": len(taxonomy.rules),
        "rules_by_level": dict(sorted(levels.items())),
        "source_module": SOURCE_MODULE,
        "source_module_commit": commit,
        "source_module_sha256": blob_sha256,
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "network": 0,
            "audio_seconds": 0,
            "gold_or_reference_reads": 0,
        },
    }
    CHECK_DIR.mkdir(parents=True, exist_ok=True)
    (CHECK_DIR / "taxonomy-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({key: receipt[key] for key in ("taxonomy_id", "rules", "rules_by_level")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
