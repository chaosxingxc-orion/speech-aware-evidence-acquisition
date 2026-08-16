"""CJK inventory + classification for the exploring-l4-intelligence umbrella repo.

Read-only. Writes a JSON inventory to the scratchpad. Never touches studies/.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"D:\chao_workspace\exploring-l4-intelligence")
OUT = Path(sys.argv[1])

# CJK Unified Ideographs + Ext A + compatibility + CJK punctuation + fullwidth forms
CJK = re.compile(
    "[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef]"
)
# The "hard" set: ideographs only (fullwidth punctuation alone is a weaker signal)
HAN = re.compile("[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".jsonl", ".txt", ".yml", ".yaml", ".sh", ".toml",
    ".cfg", ".ini", ".lean", ".bib", ".csv", ".tsv", ".html", ".xml",
}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def classify(rel: str, han: int) -> tuple[str, str]:
    p = rel.replace("\\", "/")
    name = p.rsplit("/", 1)[-1]

    # Class C — out of scope (should not appear among tracked files, but guard anyway)
    if p.startswith("studies/") and p not in ("studies/README.md", "studies/registry.json"):
        return "C", "inside the study checkout — untouchable (live GPU campaign)"
    if p.startswith(".wiki-tmp/") or "/.worktrees/" in p or p.startswith(".worktrees/"):
        return "C", "untracked mirror / worktree copy"

    # Class B — never rewrite in place
    if p.startswith("wiki/audit/"):
        return "B", "immutable audit record (carve-out)"
    if p.startswith("wiki/archive/"):
        return "B", "immutable archive record (carve-out)"
    if p.startswith("wiki/survey/registry/"):
        return "B", "append-only survey registry / metadata receipt"
    if re.match(r"^wiki/Decision-Log-\d{4}-\d{2}\.md$", p):
        return "B", "append-only dated decision-log volume"
    if p == "wiki/Decision-Log.md":
        return "B", "decision-log index over append-only volumes"
    if re.match(r"^wiki/20\d\d.*", p):
        return "B", "historical dated wiki record (never loaded into context)"
    if "owner-" in name:
        return "B", "owner-signed authority record"
    if p.startswith("docs/checks/"):
        return "B", "hash-registered check receipt"
    if p.startswith("wiki/survey/") and (
        "ledger" in name or "registry" in name or name.endswith(".jsonl")
    ):
        return "B", "append-only survey ledger"

    # Paired-change carve-out
    if p == "wiki/AI-Collaboration.md" or p.endswith("checks/ai_context_surface_check.py"):
        return "PAIRED", "policy+oracle paired change (single coordinated edit only)"

    # Class A — translate in place
    return "A", "mutable working document on the active surface"


def main() -> None:
    rows = []
    for rel in tracked_files():
        path = REPO / rel
        if not path.exists() or path.is_dir():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        han = len(HAN.findall(text))
        cjk = len(CJK.findall(text))
        if han == 0 and cjk == 0:
            continue
        cls, reason = classify(rel, han)
        rows.append(
            {
                "path": rel.replace("\\", "/"),
                "class": cls,
                "han_chars": han,
                "cjk_chars": cjk,
                "bytes": path.stat().st_size,
                "reason": reason,
            }
        )

    rows.sort(key=lambda r: (r["class"], -r["han_chars"]))
    summary: dict[str, dict[str, int]] = {}
    for r in rows:
        s = summary.setdefault(r["class"], {"files": 0, "han_chars": 0})
        s["files"] += 1
        s["han_chars"] += r["han_chars"]

    OUT.write_text(
        json.dumps({"summary": summary, "files": rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    print(f"total files with CJK: {len(rows)}")


if __name__ == "__main__":
    main()
