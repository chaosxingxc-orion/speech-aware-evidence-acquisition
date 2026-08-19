"""P-A2T whole-population regression SPLIT MEASUREMENT -- model-free, zero core
contact.

Mirrors the archived Stage-2c launcher's own ``preflight-split-measurement.json``
step. Derives the 97-id EM-correct roster through the machinery's own
fail-closed ``derive_em_correct_ids``, measures the real audio load the two arms
imply, and writes ``split-measurement.json`` -- the file ``flight_plan.py``
derives this flight's ``planned_speech_audio_seconds`` from, so that number is
COMPUTED from measured bytes rather than hand-typed.

STRUCTURAL OUTPUT ONLY. ``derive_em_correct_ids`` is the preregistration's own
registered roster-sourcing path (section 2: reuse the frozen scorer over the
consumed A0 attempt, never a second implementation) -- it is a read of an
already-flown, already-consumed attempt, and the only things recorded here about
it are COUNTS: how many ids satisfy the EM-correct predicate (fail-closed at
exactly 97), how many resolve an R1 tool, how many distinct tools that is, and
the rendered roster lengths. No response text, no metric value, no per-sample
score.
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
    load_tool_registry,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import (  # noqa: E402
    A2T_POP_ARMS,
    DEFAULT_SEED,
    EM_CORRECT_N,
    build_flight_plan_from_attempt,
    derive_em_correct_ids,
    render_b1_tool_schemas,
)

MEASUREMENT_SCHEMA = "saea-a2t-pop-split-measurement-v1"


def main() -> int:
    out_path = Path(__file__).resolve().parent / "split-measurement.json"

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    split = resolve_split(REPO)
    print(f"headroom artifact: {len(split.headroom_ids)} ids (the CONSUMED 120-id headroom set)")
    print(f"consumed A0 attempt dir: {split.consumed_a0_attempt_dir}")
    print(f"split_identity_hash (machinery pinned guard PASSED): {split.split_identity_hash}")

    print("deriving the EM-correct roster (frozen scorer over the consumed A0 attempt, fail-closed at 97)")
    em_ids = derive_em_correct_ids(
        Path(split.consumed_a0_attempt_dir),
        lock,
        root,
        repo_root=REPO,
        expected_n=EM_CORRECT_N,
    )
    print(f"EM-correct roster: {len(em_ids)} ids (registered {EM_CORRECT_N}) -- fail-closed check PASSED")
    overlap = sorted(set(em_ids) & set(split.headroom_ids))
    print(
        f"disjointness from the consumed 120-id headroom set: {len(overlap)} overlapping id(s) "
        "(expected 0 -- headroom is EM==0, this population is EM==1)"
    )
    if overlap:
        raise RuntimeError(f"EM-correct roster overlaps the headroom set: {overlap[:5]}")

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    print("resolving the frozen discovery split (sha256 of every media file -- slow, model-free)")
    all_samples = adapter.load_split("discovery")
    by_id = {s.sample_id: s for s in all_samples}
    print(f"discovery split resolved: {len(all_samples)} samples")
    missing = [sid for sid in em_ids if sid not in by_id]
    if missing:
        raise RuntimeError(f"{len(missing)} EM-correct ids absent from the frozen split: {missing[:5]}")
    samples = [by_id[sid] for sid in em_ids]
    missing_media = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing_media:
        raise RuntimeError(f"{len(missing_media)} sample media missing: {missing_media[:5]}")
    one_pass = sum(s.audio_seconds for s in samples)
    longest = max(s.audio_seconds for s in samples)
    shortest = min(s.audio_seconds for s in samples)
    print(f"media resolved: {len(samples)}/{len(samples)} wav present")
    print(
        f"one pass over the EM-correct {len(samples)}: {one_pass:.2f}s audio "
        f"(mean {one_pass/len(samples):.2f}s, min {shortest:.2f}s, max {longest:.2f}s)"
    )

    registry_rows = load_tool_registry(lock, root)
    full_registry_text = render_tool_schemas(lock, root)
    print(f"tool registry: {len(registry_rows)} rows, full render {len(full_registry_text)} chars")

    plan = build_flight_plan_from_attempt(em_ids, Path(split.consumed_a0_attempt_dir), registry_rows)
    tool_counts = Counter(len(v) for v in plan.r1_tool_names_by_sample.values())
    distinct_tools = {n for names in plan.r1_tool_names_by_sample.values() for n in names}
    r1_lengths = {
        sid: len(render_b1_tool_schemas([plan.registry_index[n] for n in names]))
        for sid, names in plan.r1_tool_names_by_sample.items()
    }
    print(
        f"R1 self-supplied plan: {len(plan.sample_ids)} samples; tool count distribution "
        f"{json.dumps(dict(sorted(tool_counts.items())), sort_keys=True)}; "
        f"{len(distinct_tools)} distinct supplied tools"
    )
    print(
        f"R1 B1-form render: {min(r1_lengths.values())}-{max(r1_lengths.values())} chars "
        f"(full registry {len(full_registry_text)} chars; every R1 render must be SHORTER)"
    )
    not_shorter = [sid for sid, n in r1_lengths.items() if n >= len(full_registry_text)]
    if not_shorter:
        raise RuntimeError(f"R1 render is not shorter than the full registry for: {not_shorter}")
    print("R1 render invariant: every sample's R1 roster is strictly shorter -- OK")

    document = {
        "schema": MEASUREMENT_SCHEMA,
        "run_id": RUN_ID,
        "split_identity_hash": split.split_identity_hash,
        "consumed_a0_attempt_dir": split.consumed_a0_attempt_dir,
        "seed": DEFAULT_SEED,
        "arms": list(A2T_POP_ARMS),
        "em_correct_n": len(em_ids),
        "em_correct_sample_ids": list(em_ids),
        "headroom_overlap_count": len(overlap),
        "n_samples": len(samples),
        "one_pass_audio_seconds": round(one_pass, 3),
        "longest_sample_audio_seconds": round(longest, 3),
        "shortest_sample_audio_seconds": round(shortest, 3),
        "mean_sample_audio_seconds": round(one_pass / len(samples), 3),
        "registry_rows": len(registry_rows),
        "full_registry_render_chars": len(full_registry_text),
        "r1_render_chars_min": min(r1_lengths.values()),
        "r1_render_chars_max": max(r1_lengths.values()),
        "r1_tool_count_distribution": dict(sorted(tool_counts.items())),
        "distinct_supplied_tool_count": len(distinct_tools),
    }
    out_path.write_text(
        json.dumps(document, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    print(f"wrote {out_path}")
    print("MEASUREMENT DONE (zero model calls)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
