#!/usr/bin/env python3
"""Replay the pinned upstream experience-plan applier on synthetic stores only.

This source audit imports no upstream package and contacts no model or scorer.
It executes only the reviewed AST suffix after the model response was parsed.
The supplied source must match the already registered upstream file hash.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path

SOURCE_SHA256 = "301d4a51136f6c0da620f1f2042d59316af494cee4b4c3329338ba1a1b937d04"


def audit(source: Path) -> dict:
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("source differs from the pinned upstream implementation")
    tree = ast.parse(raw)
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    method = next(node for node in cls.body
                  if isinstance(node, ast.AsyncFunctionDef) and node.name == "_batch_update")
    start = next(i for i, node in enumerate(method.body)
                 if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "max_ID" for t in node.targets))
    function = ast.FunctionDef(
        name="apply_pinned_plan",
        args=ast.arguments(posonlyargs=[], args=[ast.arg(arg="experiences"),
                           ast.arg(arg="revision_plan")], kwonlyargs=[], kw_defaults=[], defaults=[]),
        body=copy.deepcopy(method.body[start:]), decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    namespace = {"copy": copy}
    exec(compile(module, str(source), "exec"), namespace)
    apply = namespace["apply_pinned_plan"]
    cases = [
        ("dense-add", {"0": "A", "1": "B"}, [{"operation": "ADD", "content": "C"}],
         {"0": "A", "1": "B", "2": "C"}),
        ("sparse-add", {"0": "A", "2": "C"}, [{"operation": "ADD", "content": "D"}],
         {"0": "A", "2": "D"}),
        ("delete-without-content", {"0": "A", "1": "B"}, [{"operation": "DELETE", "id": "0"}],
         {"0": "A", "1": "B"}),
        ("delete-with-content", {"0": "A", "1": "B"},
         [{"operation": "DELETE", "id": "0", "content": "A"}], {"1": "B"}),
        ("unknown-update", {"0": "A", "2": "C"},
         [{"operation": "UPDATE", "id": "missing", "content": "D"}], {"0": "A", "2": "D"}),
        ("unknown-operation", {"0": "A"},
         [{"operation": "REWRITE", "id": "0", "content": "B"}], {"0": "A"}),
    ]
    result = []
    for name, before, operations, expected in cases:
        original = copy.deepcopy(before)
        with contextlib.redirect_stdout(io.StringIO()):
            after = apply(before, operations)
        if after != expected or before != original:
            raise AssertionError(f"pinned behavior changed in {name}")
        overwritten = sorted(
            key for key in before if key in after and before[key] != after[key]
            and not any(op.get("operation") == "UPDATE" and op.get("id") == key
                        for op in operations))
        result.append({"case": name, "verified": True, "before_ids": list(before),
                       "after_ids": list(after), "unrequested_existing_overwrites": overwritten,
                       "source_store_mutated": False})
    with contextlib.redirect_stdout(io.StringIO()):
        deleted = apply({"0": "A", "1": "B", "2": "C"},
                        [{"operation": "DELETE", "id": "1", "content": "B"}])
        added = apply(deleted, [{"operation": "ADD", "content": "D"}])
    if deleted != {"0": "A", "2": "C"} or added != {"0": "A", "2": "D"}:
        raise AssertionError("successive-round behavior changed")
    result.append({"case": "successive-delete-add-rounds", "verified": True,
                   "after_delete_ids": list(deleted), "after_add_ids": list(added),
                   "unrequested_existing_overwrites": ["2"]})
    return {
        "schema": "saea-upstream-consolidation-source-audit-v1",
        "source_path": str(source.resolve()), "source_sha256": SOURCE_SHA256,
        "ast_source_lines": [method.body[start].lineno, method.end_lineno],
        "cases": result, "model_contacts": 0, "scorer_contacts": 0,
        "scope": "Synthetic exact-source behavior; not task evidence or an algorithm execution.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refuse to overwrite an existing audit")
    report = audit(args.source)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write(chr(10))
    print(json.dumps({"verified_cases": len(report["cases"]),
                      "source_sha256": report["source_sha256"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
