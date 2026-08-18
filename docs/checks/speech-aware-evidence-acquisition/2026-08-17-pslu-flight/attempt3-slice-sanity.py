"""Attempt-3 sanity: the colon-bearing SLURP sample id that aborted attempt 2
must now yield a colon-free, path-safe slice relpath without raising.

Model-free. Touches no data: SliceRegistry is constructed with a synthetic
parent-fact map, so nothing is read from or written to the data root.
"""

from __future__ import annotations

from pathlib import Path

from speech_aware_evidence_acquisition.core.model.slices import SliceRegistry

ABORT_ID = "slurp:devel:005518:audio-1490203960"
A2T_ID = "tier1_direct:000001"

registry = SliceRegistry(
    data_root=Path("/tmp/does-not-need-to-exist"),
    run_id="SAEA-PROBE-pslu-n60",
    parent_facts={ABORT_ID: ("0" * 64, 3.0), A2T_ID: ("1" * 64, 3.0)},
)

for raw_id in (ABORT_ID, A2T_ID):
    relpath = registry.slice_relpath(raw_id, 0)
    print(f"slice_relpath({raw_id!r}, 0) -> {relpath}")
    assert ":" not in relpath, f"colon survived into {relpath!r}"
    for component in Path(relpath).parts:
        assert ":" not in component, f"colon in path component {component!r}"

# Injectivity spot-check: two ids differing only in the colon positions must
# not collide on the same directory.
a = registry.slice_relpath(ABORT_ID, 0)
b = SliceRegistry(
    data_root=Path("/tmp/does-not-need-to-exist"),
    run_id="SAEA-PROBE-pslu-n60",
    parent_facts={"slurp:devel:005518:audio:1490203960": ("2" * 64, 3.0)},
).slice_relpath("slurp:devel:005518:audio:1490203960", 0)
print(f"injectivity: {a} != {b} -> {a != b}")
assert a != b, "distinct ids collided on one slice path"

print("SLICE PATH SANITY: PASS (colon-free, path-safe, injective)")
