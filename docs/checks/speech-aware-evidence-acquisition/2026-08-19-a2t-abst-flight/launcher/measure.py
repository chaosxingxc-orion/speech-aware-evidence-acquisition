"""P-A2T abstention-asymmetry SPLIT MEASUREMENT -- model-free, zero core contact.

Mirrors the archived Stage-2c launcher's own ``preflight-split-measurement.json``
step. Resolves the seeded n=11 draw, measures the real audio load it implies,
and writes ``split-measurement.json`` -- the file ``flight_plan.py`` derives this
flight's ``planned_speech_audio_seconds`` from, so that number is COMPUTED from
measured bytes rather than hand-typed (the Stage-2c precedent hand-typed 2621
into its own flight_plan.py after measuring; deriving it removes the retyping
step and its drift risk).

STRUCTURAL OUTPUT ONLY. The tool-removal plan is built here (it is a prompt
ingredient, not a result), but nothing is scored, and the only things recorded
about the consumed A0 attempt are COUNTS -- how many samples resolved a correct
tool, how many distinct tools that is, and the rendered registry lengths. No
response text, no metric value.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_identity import RUN_ID, resolve_split  # noqa: E402

from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    load_tool_registry,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes.a2t_abst_flight import (  # noqa: E402
    A2T_ABST_CELLS,
    ABST_N,
    DEFAULT_SEED,
    build_flight_plan_from_attempt,
    seeded_abst_draw,
)

MEASUREMENT_SCHEMA = "saea-a2t-abst-split-measurement-v1"


def main() -> int:
    out_path = Path(__file__).resolve().parent / "split-measurement.json"

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    split = resolve_split(REPO)
    print(f"headroom artifact: {len(split.headroom_ids)} ids")
    print(f"consumed A0 attempt dir: {split.consumed_a0_attempt_dir}")
    print(f"split_identity_hash (pinned cross-check PASSED): {split.split_identity_hash}")

    drawn = seeded_abst_draw(split.headroom_ids, seed=DEFAULT_SEED, n=ABST_N)
    print(f"seeded draw (seed {DEFAULT_SEED}, n={ABST_N}): {len(drawn)} ids")
    for sample_id in drawn:
        print(f"  {sample_id}")
    if len(set(drawn)) != ABST_N:
        raise RuntimeError(f"seeded draw is not {ABST_N} distinct ids")
    outside = [sid for sid in drawn if sid not in set(split.headroom_ids)]
    if outside:
        raise RuntimeError(f"drawn ids outside the frozen headroom list: {outside}")
    print("draw membership: all inside the frozen 120-id headroom list -- OK")

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    print("resolving the frozen discovery split (sha256 of every media file -- slow, model-free)")
    all_samples = adapter.load_split("discovery")
    by_id = {s.sample_id: s for s in all_samples}
    print(f"discovery split resolved: {len(all_samples)} samples")
    missing = [sid for sid in drawn if sid not in by_id]
    if missing:
        raise RuntimeError(f"{len(missing)} drawn ids absent from the frozen split: {missing}")
    samples = [by_id[sid] for sid in drawn]
    missing_media = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing_media:
        raise RuntimeError(f"{len(missing_media)} drawn sample media missing: {missing_media}")
    one_pass = sum(s.audio_seconds for s in samples)
    longest = max(s.audio_seconds for s in samples)
    shortest = min(s.audio_seconds for s in samples)
    print(f"media resolved: {len(samples)}/{len(samples)} wav present")
    print(
        f"one pass over the drawn {len(samples)}: {one_pass:.2f}s audio "
        f"(mean {one_pass/len(samples):.2f}s, min {shortest:.2f}s, max {longest:.2f}s)"
    )

    registry_rows = load_tool_registry(lock, root)
    full_registry_text = render_tool_schemas(lock, root)
    print(f"tool registry: {len(registry_rows)} rows, full render {len(full_registry_text)} chars")

    plan = build_flight_plan_from_attempt(
        drawn, Path(split.consumed_a0_attempt_dir), registry_rows
    )
    tool_counts = Counter(len(v) for v in plan.correct_tool_names_by_sample.values())
    distinct_tools = {n for names in plan.correct_tool_names_by_sample.values() for n in names}
    tw_lengths = {sid: len(text) for sid, text in plan.tw_registry_text_by_sample.items()}
    print(
        f"tool-removal plan: {len(plan.sample_ids)} samples; correct-tool count distribution "
        f"{json.dumps(dict(sorted(tool_counts.items())), sort_keys=True)}; "
        f"{len(distinct_tools)} distinct withheld tools"
    )
    print(
        f"TW registry render: {min(tw_lengths.values())}-{max(tw_lengths.values())} chars "
        f"(full registry {len(full_registry_text)} chars; every TW render must be SHORTER)"
    )
    not_shorter = [sid for sid, n in tw_lengths.items() if n >= len(full_registry_text)]
    if not_shorter:
        raise RuntimeError(f"TW render is not shorter than the full registry for: {not_shorter}")
    print("TW render invariant: every sample's TW registry is strictly shorter -- OK")

    document = {
        "schema": MEASUREMENT_SCHEMA,
        "run_id": RUN_ID,
        "split_identity_hash": split.split_identity_hash,
        "consumed_a0_attempt_dir": split.consumed_a0_attempt_dir,
        "seed": DEFAULT_SEED,
        "n_draw": ABST_N,
        "cells": list(A2T_ABST_CELLS),
        "drawn_sample_ids": list(drawn),
        "n_samples": len(samples),
        "one_pass_audio_seconds": round(one_pass, 3),
        "longest_sample_audio_seconds": round(longest, 3),
        "shortest_sample_audio_seconds": round(shortest, 3),
        "mean_sample_audio_seconds": round(one_pass / len(samples), 3),
        "registry_rows": len(registry_rows),
        "full_registry_render_chars": len(full_registry_text),
        "tw_registry_render_chars_min": min(tw_lengths.values()),
        "tw_registry_render_chars_max": max(tw_lengths.values()),
        "correct_tool_count_distribution": dict(sorted(tool_counts.items())),
        "distinct_withheld_tool_count": len(distinct_tools),
    }
    out_path.write_text(
        json.dumps(document, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    print(f"wrote {out_path}")
    print("MEASUREMENT DONE (zero model calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
