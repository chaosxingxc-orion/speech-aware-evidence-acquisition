"""Contract: only core/scorers.py may import the scoring-side reference reader."""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "speech_aware_evidence_acquisition"
ALLOWED = {SRC / "core" / "scorers.py", SRC / "data" / "references.py"}


def _imports_references(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.endswith("references") or any(
                alias.name == "references" for alias in node.names
            ):
                return True
        if isinstance(node, ast.Import):
            if any("references" in alias.name for alias in node.names):
                return True
    return False


def test_only_the_scoring_phase_imports_references():
    offenders = [
        str(path)
        for path in sorted(SRC.rglob("*.py"))
        if path not in ALLOWED and _imports_references(path)
    ]
    assert offenders == [], f"runtime-phase modules import data.references: {offenders}"
