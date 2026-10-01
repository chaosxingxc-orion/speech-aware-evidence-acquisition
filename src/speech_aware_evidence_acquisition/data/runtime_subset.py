"""Deterministic, metadata-only subsets of a verified runtime view."""
import copy
import hashlib
from .splits import prefixed, split_identity_hash
from ..rails.hashing import content_hash


def build_runtime_subset(parent, *, seed, count, name, start=0):
    """Rank by SHA256(seed:sample_id), then retain count records from start.

    Do not read labels, transcripts or task outputs. Preserve each input binding.
    The receipt binds the original view, selection algorithm and ordered roster.
    Nonzero, zero-based offsets use a v2 receipt. The default prefix retains
    the historical v1 identity and bytes.
    """
    unsigned = {k: v for k, v in parent.items() if k != "runtime_view_sha256"}
    if parent.get("runtime_view_sha256") != content_hash(unsigned):
        raise ValueError("parent runtime view hash differs")
    items = parent["items"]
    if (parent["count"] != len(items) or len({i["sample_id"] for i in items}) != len(items)):
        raise ValueError("parent count or unique roster differs")
    if type(seed) is not int or seed < 0 or type(count) is not int or not 0 < count <= len(items):
        raise ValueError("seed or subset count is invalid")
    if type(start) is not int or start < 0 or start + count > len(items):
        raise ValueError("subset slice is invalid")
    if not isinstance(name, str) or not name or name == parent["split_name"]:
        raise ValueError("subset needs a new nonempty name")
    selected = sorted(items, key=lambda i: (hashlib.sha256(
        f"{seed}:{i['sample_id']}".encode()).hexdigest(), i["sample_id"]))[start:start + count]
    receipt = {"schema": "saea-runtime-subset-receipt-v1", "parent_runtime_view_sha256": parent["runtime_view_sha256"],
        "selection": "sha256(seed:sample_id)-ascending-v1", "seed": seed,
        "sample_ids": [i["sample_id"] for i in selected], "count": count,
        "contacts": {"model": 0, "tool": 0, "scorer": 0, "gpu": 0}}
    if start:
        receipt.update(schema="saea-runtime-subset-receipt-v2", slice_start=start)
    view = copy.deepcopy(unsigned)
    view.update(items=copy.deepcopy(selected), count=count, seed=seed, split_name=name,
        split_identity_hash=split_identity_hash(prefixed(parent["carrier_lock_key"], receipt["sample_ids"])),
        source_binding_sha256=content_hash(receipt),
        audio_seconds_total=round(sum(i["audio_seconds"] for i in selected), 9))
    view["runtime_view_sha256"] = content_hash(view)
    return view, receipt
