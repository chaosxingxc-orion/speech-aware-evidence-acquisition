"""MODEL-FREE measurement of the frozen Audio2Tool discovery split.

Produces exactly the three numbers the exposure row must register before any
core contact: how many samples ``Audio2ToolAdapter.load_split('discovery')``
resolves, the split identity hash the receipt freezes, and the REAL total
speech-audio seconds across all 400 items (the binding JSON only knows
1801.3 s for the 350 items carrying a top-level duration; the 50
tier7_multiturn items resolve their per-turn media through the adapter, so
the adapter itself is the only authority for the true total).

Opens no socket, spawns no server, reads no model.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    audio2tool_receipts,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
)


def main() -> int:
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    print(f"carrier_root (asset_dir audio2tool): {asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)}")

    receipts = audio2tool_receipts(REPO)
    print(f"audio2tool probe receipts: {sorted(receipts)}")
    for name, payload in sorted(receipts.items()):
        print(
            f"  {name}: split_role={payload.get('split_role')!r} "
            f"n_items={len(payload['items'])} "
            f"split_identity_hash={payload.get('split_identity_hash')}"
        )

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    print("resolving discovery split (sha256 of every media file -- slow, model-free)")
    samples = adapter.load_split("discovery")
    print(f"discovery split resolved: {len(samples)} samples")

    total_audio = sum(s.audio_seconds for s in samples)
    durations = sorted(s.audio_seconds for s in samples)
    tiers = Counter(s.sample_id.split(":")[0] for s in samples)
    missing = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]

    print(f"tier counts: {dict(sorted(tiers.items()))}")
    print(f"media present: {len(samples) - len(missing)}/{len(samples)}")
    if missing:
        print(f"MISSING MEDIA: {missing[:10]}")
    print(f"TOTAL AUDIO SECONDS (all {len(samples)}): {total_audio:.2f}")
    print(f"  mean {total_audio/len(samples):.3f}  min {durations[0]:.3f}  max {durations[-1]:.3f}")
    print(f"  binding JSON knew only 1801.30 s over 350 top-level-duration items")

    schemas = render_tool_schemas(lock, root)
    print(f"rendered tool schemas: {len(schemas)} chars, est {len(schemas)//4} tokens")
    prompt = (
        "You control tools. Available tools:\n" + schemas + "\n\n"
        'Respond with ONLY a JSON array of tool calls, e.g. [{"name": "x", "arguments": {}}].'
    )
    print(f"full system instruction: {len(prompt)} chars, est {len(prompt)//4} tokens")

    summary = {
        "n_samples": len(samples),
        "total_audio_seconds": round(total_audio, 3),
        "mean_audio_seconds": round(total_audio / len(samples), 3),
        "max_audio_seconds": round(durations[-1], 3),
        "system_instruction_chars": len(prompt),
        "system_instruction_est_tokens": len(prompt) // 4,
        "tier_counts": dict(sorted(tiers.items())),
        "missing_media": missing,
    }
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if out is not None:
        out.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8", newline="\n")
        print(f"summary written: {out}")
    return 0 if not missing and len(samples) == 400 else 1


if __name__ == "__main__":
    raise SystemExit(main())
