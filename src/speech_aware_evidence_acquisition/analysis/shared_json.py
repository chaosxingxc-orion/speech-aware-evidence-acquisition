"""Deterministic, reversible sharing of repeated JSON values for model contexts."""
from __future__ import annotations

from collections import Counter
import json

SCHEMA = "saea-shared-json-v1"


def _key(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def share_json(value):
    """Share repeated values; escape reserved objects so source data cannot alias refs."""
    counts = Counter()

    def count(node):
        counts[_key(node)] += 1
        if isinstance(node, dict):
            for item in node.values():
                count(item)
        elif isinstance(node, list):
            for item in node:
                count(item)

    count(value)
    references, pool = {}, {}

    def encode(node):
        key = _key(node)
        shared = counts[key] > 1 and len(key) > 60
        if shared and key in references:
            return {"$ref": references[key]}
        if isinstance(node, dict):
            pairs = [[k, encode(v)] for k, v in sorted(node.items())]
            result = ({"$object": pairs} if {"$ref", "$object"} & node.keys()
                      else dict(pairs))
        elif isinstance(node, list):
            result = [encode(v) for v in node]
        else:
            result = node
        if shared:
            reference = "p" + str(len(pool) + 1)
            references[key] = reference
            pool[reference] = result
            return {"$ref": reference}
        return result

    root = encode(value)
    return {"schema": SCHEMA, "episode": root, "shared": pool}


def restore_json(document):
    """Expand refs, rejecting cycles, missing refs and malformed literal-object escapes."""
    if not isinstance(document, dict) or set(document) != {"schema", "episode", "shared"}:
        raise ValueError("shared JSON has wrong fields")
    if document["schema"] != SCHEMA or not isinstance(document["shared"], dict):
        raise ValueError("shared JSON has wrong schema or pool")
    pool, active, restored, used = document["shared"], set(), {}, set()

    def decode(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                if set(node) != {"$ref"} or not isinstance(ref, str) or ref not in pool:
                    raise ValueError("shared JSON has an invalid reference")
                if ref in active:
                    raise ValueError("shared JSON contains a cycle")
                used.add(ref)
                if ref not in restored:
                    active.add(ref)
                    restored[ref] = decode(pool[ref])
                    active.remove(ref)
                return restored[ref]
            if "$object" in node:
                pairs = node["$object"]
                if (set(node) != {"$object"} or not isinstance(pairs, list)
                        or any(not isinstance(p, list) or len(p) != 2
                               or not isinstance(p[0], str) for p in pairs)):
                    raise ValueError("shared JSON has a malformed literal object")
                if len({p[0] for p in pairs}) != len(pairs):
                    raise ValueError("shared JSON literal object has duplicate keys")
                return {k: decode(v) for k, v in pairs}
            return {k: decode(v) for k, v in node.items()}
        if isinstance(node, list):
            return [decode(v) for v in node]
        return node

    value = decode(document["episode"])
    if used != set(pool):
        raise ValueError("shared JSON contains unreachable content")
    return value
