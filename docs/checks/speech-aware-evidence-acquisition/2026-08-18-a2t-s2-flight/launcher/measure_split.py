"""Model-free measurement for the P-A2T Stage-2 supply-probe flight.

Builds the FULL deterministic four-arm flight plan (the same
``rails.probes.a2t_s2_flight.build_flight_plan`` the launcher will rebuild
byte-identically from the same inputs) and measures what the flight will
actually cost:

  * the real audio-second load, arm by arm -- every S1p/S2/S4 request re-sends
    the sample's own audio, so the metered total is 3 x sum(120) + sum(N0r 40),
    NOT one pass over the 120;
  * per-arm prompt sizing (chars / whitespace-token estimate), so the
    ``-np 1`` context decision can be checked against the WORST arm (N0r, the
    full 152-row registry) rather than the narrowed ones;
  * the S4 derangement's fixed-point-freeness and the N0r tier apportionment.

Zero model contact: nothing here opens a socket, spawns a server, or reads a
model. The A0 ``outputs.jsonl`` read is a read of an ALREADY-FLOWN,
ALREADY-CONSUMED attempt's own recorded output (the S1' tool-source binding the
flight config's ``a0_selected_tool_source`` block documents), never a new
contact and never a gold read.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_identity import build_values  # noqa: E402

from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_tool_registry,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (  # noqa: E402
    N0R_ARM,
    S1P_ARM,
    S2_ARM,
    S4_ARM,
    assemble_roster_prompt,
    build_flight_plan,
    derive_a0_selected_tools,
    load_headroom_manifest,
    render_roster_prompt_block,
    roster_supply_packet,
)

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/a2t-s2-flight.json").read_text(encoding="utf-8")
)


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    values = build_values(REPO)

    headroom_path = REPO / str(FLIGHT_CFG["headroom_manifest"])
    headroom = load_headroom_manifest(headroom_path)
    print(f"headroom manifest: {headroom_path}")
    print(f"  ids: {len(headroom.sample_ids)}  attempt_dir: {headroom.attempt_dir}")
    print(f"  split_identity_hash: {headroom.split_identity_hash}")

    attempt_dir = Path(headroom.attempt_dir)
    print(f"deriving A0 selected tools from {attempt_dir} (already-flown, already-consumed)")
    selected = derive_a0_selected_tools(attempt_dir, headroom.sample_ids)
    multi = {sid: names for sid, names in selected.items() if len(names) > 1}
    print(f"  derived for {len(selected)} samples; {len(multi)} carry >1 distinct tool")

    registry_rows = load_tool_registry(lock, root)
    print(f"tool registry rows: {len(registry_rows)}")

    plan = build_flight_plan(
        headroom, selected, registry_rows, seed=int(FLIGHT_CFG["seed"])
    )
    print(f"flight plan built (seed {FLIGHT_CFG['seed']})")
    fixed_points = [t for t, d in plan.s4_derangement.items() if t == d]
    print(f"  S4 derangement over {len(plan.s4_derangement)} distinct tools, fixed points: {fixed_points}")
    s4_self = [
        sid
        for sid in plan.headroom_ids
        if plan.s4_tool_name_by_sample[sid] in set(plan.s1p_tool_names_by_sample[sid])
    ]
    print(f"  S4 samples whose supplied tool is one of their OWN selections: {len(s4_self)} (must be 0)")
    s2_sizes = Counter(len(plan.s2_tool_names_by_sample[s]) for s in plan.headroom_ids)
    print(f"  S2 roster sizes: {dict(s2_sizes)} (must be exactly {{9: 120}})")
    s1p_sizes = Counter(len(plan.s1p_tool_names_by_sample[s]) for s in plan.headroom_ids)
    print(f"  S1p roster sizes: {dict(s1p_sizes)}")
    n0r_tiers = Counter(sid.split(":", 1)[0] for sid in plan.n0r_sample_ids)
    all_tiers = Counter(sid.split(":", 1)[0] for sid in plan.headroom_ids)
    print(f"  N0r draw: {len(plan.n0r_sample_ids)} ids, tiers {dict(sorted(n0r_tiers.items()))}")
    print(f"  headroom tiers: {dict(sorted(all_tiers.items()))}")

    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    print("resolving discovery split (sha256 of every media file -- slow, model-free)")
    samples = adapter.load_split("discovery")
    by_id = {s.sample_id: s for s in samples}
    print(f"discovery split resolved: {len(samples)} samples")
    missing = [sid for sid in plan.headroom_ids if sid not in by_id]
    if missing:
        print(f"FATAL: {len(missing)} headroom ids absent from the split: {missing[:5]}")
        return 1

    headroom_samples = [by_id[sid] for sid in plan.headroom_ids]
    n0r_samples = [by_id[sid] for sid in plan.n0r_sample_ids]
    media_missing = [s.sample_id for s in headroom_samples if not (root / s.media_relpath).is_file()]
    if media_missing:
        print(f"FATAL: {len(media_missing)} headroom media missing: {media_missing[:5]}")
        return 1
    print(f"headroom media present: {len(headroom_samples)}/{len(headroom_samples)}")

    audio_120 = sum(s.audio_seconds for s in headroom_samples)
    audio_n0r = sum(s.audio_seconds for s in n0r_samples)
    total_audio = 3.0 * audio_120 + audio_n0r
    max_item = max(s.audio_seconds for s in headroom_samples)
    print(f"audio seconds: one pass over the 120 = {audio_120:.2f}")
    print(f"audio seconds: N0r 40 = {audio_n0r:.2f}")
    print(f"audio seconds: METERED TOTAL 3x120 + 40 = {total_audio:.2f}")
    print(f"audio seconds: longest single headroom item = {max_item:.2f}")
    print(f"audio seconds: + 50 retries worst case = {total_audio + 50 * max_item:.2f}")

    # ---- prompt sizing, arm by arm ------------------------------------------
    full_registry_text = render_tool_schemas(lock, root)
    arm_chars: dict[str, list[int]] = {S1P_ARM: [], S2_ARM: [], S4_ARM: [], N0R_ARM: []}
    for sid in plan.headroom_ids:
        sample = by_id[sid]
        for arm, names in (
            (S1P_ARM, plan.s1p_tool_names_by_sample[sid]),
            (S2_ARM, plan.s2_tool_names_by_sample[sid]),
            (S4_ARM, (plan.s4_tool_name_by_sample[sid],)),
        ):
            rows = [plan.registry_index[n] for n in names]
            block = render_roster_prompt_block(rows)
            messages = assemble_roster_prompt(sample, block)
            arm_chars[arm].append(len(str(messages[0]["content"])))
    for sid in plan.n0r_sample_ids:
        messages = adapter.assemble_prompt(by_id[sid], None)
        arm_chars[N0R_ARM].append(len(str(messages[0]["content"])))

    arm_stats: dict[str, dict[str, float]] = {}
    for arm, chars in arm_chars.items():
        stats = {
            "n": len(chars),
            "min_chars": min(chars),
            "mean_chars": sum(chars) / len(chars),
            "max_chars": max(chars),
            "max_est_tokens": max(chars) // 4,
        }
        arm_stats[arm] = stats
        print(
            f"  arm {arm:4s}: n={stats['n']:3d} chars min={stats['min_chars']:6d} "
            f"mean={stats['mean_chars']:9.1f} max={stats['max_chars']:6d} "
            f"(max est {stats['max_est_tokens']} tokens)"
        )
    print(f"  full 152-row registry text: {len(full_registry_text)} chars")

    # SupplyPacket dose bookkeeping (the module's own convention).
    doses = {}
    for arm, sid in ((S1P_ARM, plan.headroom_ids[0]), (S2_ARM, plan.headroom_ids[0]), (S4_ARM, plan.headroom_ids[0])):
        names = (
            plan.s1p_tool_names_by_sample[sid]
            if arm == S1P_ARM
            else plan.s2_tool_names_by_sample[sid]
            if arm == S2_ARM
            else (plan.s4_tool_name_by_sample[sid],)
        )
        packet = roster_supply_packet(arm, sid, [plan.registry_index[n] for n in names])
        doses[arm] = {"n_items": packet.dose.n_items, "token_count": packet.dose.token_count}
    print(f"  sample-0 supply doses: {json.dumps(doses, sort_keys=True)}")

    # ---- context sizing ------------------------------------------------------
    argv = [str(t) for t in values["server_args"]]
    ctx = int(argv[argv.index("-c") + 1])
    npar = int(argv[argv.index("-np") + 1])
    per_slot = ctx // npar
    worst_tokens = max(stats["max_est_tokens"] for stats in arm_stats.values())
    max_out = int(values["decoding_params"].get("max_tokens", 0))
    print(f"server_args (after the -np delta): {argv}")
    print(f"per-slot context: {ctx}/{npar} = {per_slot} tokens")
    print(f"worst-arm prefill est {worst_tokens} tokens + ~500 audio + {max_out} out")
    if npar != 1:
        print("FATAL: -np delta did not apply")
        return 1
    if per_slot < worst_tokens + 500 + max_out:
        print("FATAL: per-slot context cannot hold the worst arm's sequence")
        return 1

    document = {
        "run_id": "SAEA-PROBE-a2t-s2-120",
        "headroom_ids": list(plan.headroom_ids),
        "n0r_sample_ids": list(plan.n0r_sample_ids),
        "n_requests": 3 * len(plan.headroom_ids) + len(plan.n0r_sample_ids),
        "audio_seconds": {
            "one_pass_120": round(audio_120, 3),
            "n0r_40": round(audio_n0r, 3),
            "metered_total": round(total_audio, 3),
            "longest_item": round(max_item, 3),
        },
        "arm_prompt_stats": arm_stats,
        "s4_fixed_points": fixed_points,
        "s4_self_supplied": s4_self,
        "s2_roster_sizes": dict(s2_sizes),
        "s1p_roster_sizes": dict(s1p_sizes),
        "n0r_tier_counts": dict(sorted(n0r_tiers.items())),
        "headroom_tier_counts": dict(sorted(all_tiers.items())),
        "context": {"n_ctx": ctx, "n_parallel": npar, "per_slot": per_slot},
    }
    if out_path is not None:
        out_path.write_text(
            json.dumps(document, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
        )
        print(f"measurement written: {out_path}")
    print("MEASUREMENT CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
