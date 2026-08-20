"""P-EMB-3L flight PRE-FLIGHT check -- ZERO model contact, ZERO server spawn.

Structurally the archived P-EMB pre-flight, extended with this probe's own
three-arm / two-session items. Verifies, before any core contact:

  1. the machinery's own import-time ontology-miner guards pass, the binding
     config's LIVE sha256 equals the pinned ``BINDING_CONFIG_SHA256``, and the
     sweep's ``split_identity_hash`` equals the committed machinery pin
     VERBATIM (cross-checked against the frozen 60-sample manifest);
  2. the surface resolves to EXACTLY the registered counts (60 devel samples +
     18 canonical roster labels), with no duplicate id and every media file
     present;
  3. the audio payload profile (min/mean/max seconds, one-pass total) and the
     THREE-PASS metered arithmetic this sweep actually spends;
  4. the exposure row exists exactly once, consumed=no, its split-identity-hash
     cell agrees VERBATIM, and its budget cells cover the plan AND match the
     launcher's transcribed REGISTERED_CEILINGS;
  5. the ExecutionPlan validates, the contact arithmetic holds (3 x 78 = 234),
     and BOTH sessions' argv carry ``--embedding``, ``-ngl 999``, ``-np 1``,
     their OWN ``--pooling`` value and the embedding port -- never the
     generation port, never a sampling parameter;
  6. ``LLAMA_MEDIA_MARKER`` is pinned in this process's environment (the value
     itself is re-verified against each LIVE server's ``GET /props`` at flight
     time -- this check only proves the pin EXISTS, never that it is right);
  7. nothing is listening on the generation port (coexistence guard, dry-run of
     the same ``assert_no_conflicting_generation_server`` the launcher calls)
     and the embedding port is free;
  8. the RUN-TOTAL budget is feasible for a fresh attempt.

Nothing here opens a socket to a model, spawns a server, or embeds anything.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.contracts.ledger import (  # noqa: E402
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash as compute_protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.embedding_client import (  # noqa: E402
    EMBEDDING_DIM,
    LLAMA_MEDIA_MARKER_ENV,
    EmbeddingClientError,
    assert_no_conflicting_generation_server,
    resolve_expected_media_marker,
)
from speech_aware_evidence_acquisition.rails.probes.pemb3l_flight import (  # noqa: E402
    ARM_AUDIO_N,
    ARM_IDS,
    ARM_LABEL_N,
    ARM_TOTAL_N,
    ARMS,
    AUDIO_INSTRUCT_PREFIX,
    BINDING_CONFIG_SHA256,
    CITED_MEAN_BARE_ACCURACY,
    EXPECTED_TOTAL_CONTACTS,
    TEXT_INSTRUCT_PREFIX,
    _assert_this_module_never_calls_ontology_miner as _pemb3l_source_guard,
    arm_run_id,
    assert_binding_config_sha256,
    binding_config_sha256,
)
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (  # noqa: E402
    _assert_this_module_never_calls_ontology_miner as _pemb_source_guard,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    assert_never_calls_ontology_miner,
)

from flight_identity import (  # noqa: E402
    EMBEDDING_PORT,
    EXECUTION_PROFILE,
    GENERATION_PORT,
    PLANNED_BUDGETS,
    PREREGISTRATION_RELPATH,
    REGISTERED_CEILINGS,
    ROSTER_TABLE_RELPATH,
    SAMPLE_MANIFEST_RELPATH,
    SPLIT_ROLE,
    CARRIER_LOCK_KEY,
    build_values,
    config_hash_of,
    run_id as resolve_run_id,
    session_argv,
    session_plan,
    split_identity_hash as resolve_split_identity_hash,
)


def _port_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    problems: list[str] = []

    print(f"repo module root: {Path(__import__('speech_aware_evidence_acquisition').__file__).parent}")
    print(f"preregistration: {PREREGISTRATION_RELPATH}")
    print("P-EMB-3L local construction sweep (3 arms, 2 sessions)")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    run_id = resolve_run_id()
    print(f"run id: {run_id}")
    print(f"data_root: {root}")
    print(f"carrier_root (asset_dir {CARRIER_LOCK_KEY}): {asset_dir(lock, CARRIER_LOCK_KEY, root)}")

    # ---- 1. guards + binding config + split identity ------------------------
    assert_never_calls_ontology_miner()
    _pemb_source_guard()
    _pemb3l_source_guard()
    print("ontology-miner guards (pslu parent + pemb_flight + pemb3l_flight self-source): PASS")

    assert_binding_config_sha256()
    live_binding = binding_config_sha256()
    print(f"binding config sha256 (LIVE recompute): {live_binding}")
    print(f"binding config sha256 (pinned):         {BINDING_CONFIG_SHA256}")
    if live_binding != BINDING_CONFIG_SHA256:
        problems.append("binding config sha256 drift")
    else:
        print("binding config sha256: LIVE == pinned, verbatim -- PASS")
    print(f"audio instruct prefix (EXACT, trailing space load-bearing): {AUDIO_INSTRUCT_PREFIX!r}")
    print(f"text  instruct prefix (EXACT, trailing space load-bearing): {TEXT_INSTRUCT_PREFIX!r}")
    print("arm table (committed, frozen):")
    for arm in ARMS:
        print(
            f"  {arm.arm_id:20s} pooling={arm.pooling_mode:5s} "
            f"audio_prefix={arm.audio_prefix!r} text_prefix={arm.text_prefix!r} "
            f"-> manifest run_id {arm_run_id(arm.arm_id)!r}"
        )
    print(f"cited mean-bare comparator (NOT re-flown): {CITED_MEAN_BARE_ACCURACY}")

    split_hash = resolve_split_identity_hash()
    print(f"split_identity_hash (pinned, machinery-checked): {split_hash}")

    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
        load_pslu_sample_manifest,
    )

    manifest = load_pslu_sample_manifest(REPO / SAMPLE_MANIFEST_RELPATH)
    print(f"frozen manifest: n={len(manifest.sample_ids)} seed={manifest.seed}")
    if manifest.split_identity_hash != split_hash:
        problems.append(
            f"frozen manifest hash {manifest.split_identity_hash!r} != machinery pin {split_hash!r}"
        )
    else:
        print("frozen manifest hash == machinery pin, verbatim -- PASS")

    # ---- 2/3. inputs + audio profile ---------------------------------------
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
    from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
        load_pslu_rosters,
        select_pslu_samples,
    )
    from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import (
        canonical_scenario_labels,
    )

    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    all_devel = adapter.load_split("devel")
    print(f"devel split resolved: {len(all_devel)} samples")
    samples = list(select_pslu_samples(all_devel, manifest))
    rosters = load_pslu_rosters(REPO / ROSTER_TABLE_RELPATH)
    labels = list(canonical_scenario_labels(rosters))
    print(f"canonical scenario labels: {len(labels)} -> {labels}")

    print(f"audio samples resolved: {len(samples)} (expect {ARM_AUDIO_N})")
    print(f"canonical labels resolved: {len(labels)} (expect {ARM_LABEL_N})")
    if len(samples) != ARM_AUDIO_N:
        problems.append(f"audio sample count {len(samples)} != registered {ARM_AUDIO_N}")
    if len(labels) != ARM_LABEL_N:
        problems.append(f"canonical label count {len(labels)} != registered {ARM_LABEL_N}")
    sample_ids = [s.sample_id for s in samples]
    if len(set(sample_ids)) != len(sample_ids):
        problems.append("duplicate sample_id in the resolved audio samples")
    if len(set(labels)) != len(labels):
        problems.append("duplicate canonical label")

    missing = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing:
        problems.append(f"{len(missing)} sample media missing: {missing[:5]}")
    print(f"media resolved: {len(samples) - len(missing)}/{len(samples)} present")

    seconds = [float(s.audio_seconds) for s in samples]
    one_pass_audio = sum(seconds)
    sweep_audio = one_pass_audio * len(ARMS)
    byte_sizes = [(root / s.media_relpath).stat().st_size for s in samples if (root / s.media_relpath).is_file()]
    print(
        f"audio profile (one pass): total {one_pass_audio:.3f}s, min {min(seconds):.2f}s, "
        f"mean {one_pass_audio/len(seconds):.2f}s, max {max(seconds):.2f}s"
    )
    print(
        f"media byte profile: min {min(byte_sizes)} B, mean {sum(byte_sizes)/len(byte_sizes):.0f} B, "
        f"max {max(byte_sizes)} B (base64 inflates ~4/3 on the wire)"
    )
    print(
        f"THREE-PASS metered audio (each arm re-embeds the SAME 60 clips): "
        f"{len(ARMS)} x {one_pass_audio:.3f} = {sweep_audio:.3f}s"
    )

    # Pooled-sequence feasibility: the P-EMB-2 receipt bracketed the encoder at
    # 13 tokens per ~1 s, and embedding mode forces n_batch = n_ubatch = 512.
    # This surface's longest clip is the SAME one P-EMB-1 already flew at 512.
    worst_tokens = 2 + 13 * (int(max(seconds) / 0.9983) + 1)
    print(
        f"pooled-sequence feasibility: longest clip {max(seconds):.2f}s -> <= ~{worst_tokens} tokens "
        f"at the P-EMB-2 worst-case chunk length (embedding mode forces n_batch=n_ubatch=512); "
        f"the SAME 60 clips already flew inside 512 in the consumed P-EMB-1"
    )
    if worst_tokens > 512:
        problems.append(f"worst-case pooled sequence {worst_tokens} tokens exceeds the 512 budget")

    # ---- 4. exposure ledger row --------------------------------------------
    print()
    rows = _parse_ledger_tables((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8"))
    matched = [r for r in rows if r.get(_EXPOSURE_RUN_COLUMN) == run_id]
    print(f"exposure rows matching run id {run_id!r}: {len(matched)}")
    if len(matched) != 1:
        problems.append(f"expected exactly 1 exposure row, found {len(matched)}")
    else:
        row = matched[0]
        for col in (
            "execution profile",
            "split role",
            "split identity hash",
            "consumed",
            "calls",
            "speech audio seconds",
            "gpu hours",
        ):
            print(f"  ledger[{col!r}] = {row.get(col)!r}")
        if row.get("split identity hash") != split_hash:
            problems.append(
                f"LEDGER CELL MISMATCH: 'split identity hash' cell is {row.get('split identity hash')!r} "
                f"but the plan will carry {split_hash!r}; FrozenCoreGate compares these verbatim"
            )
        if str(row.get("consumed", "")).lower() != "no":
            problems.append(f"exposure row consumed={row.get('consumed')!r}, must be 'no'")
        if str(row.get("execution profile", "")).strip() != EXECUTION_PROFILE:
            problems.append(f"exposure row execution profile != {EXECUTION_PROFILE!r}")
        if str(row.get("split role", "")).strip() != SPLIT_ROLE:
            problems.append(f"exposure row split role != {SPLIT_ROLE!r}")
        for cell_name, key, caster in (
            ("calls", "model_calls", int),
            ("speech audio seconds", "speech_audio_seconds", int),
            ("gpu hours", "gpu_hours", float),
        ):
            try:
                registered_value = caster(str(row.get(cell_name, "")).strip())
            except ValueError:
                problems.append(f"ledger cell {cell_name!r} is not numeric: {row.get(cell_name)!r}")
                continue
            launcher_ceiling = caster(REGISTERED_CEILINGS[key])  # type: ignore[arg-type]
            planned_value = caster(PLANNED_BUDGETS[key])  # type: ignore[arg-type]
            if registered_value != launcher_ceiling:
                problems.append(
                    f"launcher REGISTERED_CEILINGS[{key!r}]={launcher_ceiling} disagrees with the LIVE "
                    f"ledger cell {cell_name!r}={registered_value}"
                )
            if registered_value < planned_value:
                problems.append(
                    f"ledger {cell_name!r} cell registers {registered_value} but the plan declares "
                    f"{planned_value}; FrozenCoreGate refuses when registered < planned"
                )
            else:
                print(
                    f"  budget cell {cell_name!r}: registered {registered_value} >= planned "
                    f"{planned_value} -- OK"
                )

    # ---- 5. plan + per-session server argv ----------------------------------
    print()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split_hash)
    print(f"config_hash: {cfg_hash}")
    print(f"protocol_hash: {phash}")
    print(f"base_url: {values['base_url']}")
    print(f"server_env: {values['server_env']}")
    print(f"common server_args (NO --pooling; per-session argv below is what spawns): {values['server_args']}")
    print(f"embedding dim (pinned): {EMBEDDING_DIM}")

    routing = session_plan()
    print(f"session routing ({len(routing)} sequential sessions, one per pooling mode):")
    for block in routing:
        key = str(block["session_key"])
        argv = session_argv(values, key)
        print(f"  session {key!r} flies arms {block['arm_ids']}")
        print(f"    argv: {argv}")
        for expected in ("--embedding", "-ngl", "999"):
            if expected not in argv:
                problems.append(f"session {key!r} argv is missing the E-0-pinned token {expected!r}")
        if argv.count("--pooling") != 1:
            problems.append(f"session {key!r} argv must carry exactly one --pooling pair, got {argv!r}")
        elif argv[argv.index("--pooling") + 1] != key:
            problems.append(
                f"session {key!r} argv carries --pooling {argv[argv.index('--pooling') + 1]!r}, expected {key!r}"
            )
        if argv.count("-np") != 1 or argv[argv.index("-np") + 1] != "1":
            problems.append(f"session {key!r} argv must carry exactly '-np 1', got {argv!r}")
        if "temperature" in json.dumps(argv):
            problems.append(f"a sampling parameter leaked into session {key!r} argv")
    if "--pooling" in [str(t) for t in values["server_args"]]:
        problems.append("the COMMON server_args must not carry a --pooling pair (it is per-session)")
    if str(values["base_url"]).endswith(f":{GENERATION_PORT}"):
        problems.append("base_url still points at the GENERATION port")
    if not str(values["base_url"]).endswith(f":{EMBEDDING_PORT}"):
        problems.append(f"base_url does not point at the embedding port {EMBEDDING_PORT}")

    plan = ExecutionPlan(
        run_id=run_id,
        execution_profile=EXECUTION_PROFILE,
        carrier_lock_key=CARRIER_LOCK_KEY,
        split_role=SPLIT_ROLE,
        split_identity_hash=split_hash,
        planned_model_calls=int(PLANNED_BUDGETS["model_calls"]),  # type: ignore[arg-type]
        planned_gpu_hours=float(PLANNED_BUDGETS["gpu_hours"]),  # type: ignore[arg-type]
        planned_speech_audio_seconds=int(PLANNED_BUDGETS["speech_audio_seconds"]),  # type: ignore[arg-type]
        protocol_hash=phash,
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role}")

    per_arm = len(samples) + len(labels)
    total_contacts = per_arm * len(ARMS)
    print(
        f"contact arithmetic: ({len(samples)} audio + {len(labels)} text) x {len(ARMS)} arms "
        f"= {total_contacts} <= plan ceiling {plan.planned_model_calls} <= registered ceiling "
        f"{REGISTERED_CEILINGS['model_calls']}"
    )
    if per_arm != ARM_TOTAL_N:
        problems.append(f"per-arm contact count {per_arm} != machinery ARM_TOTAL_N {ARM_TOTAL_N}")
    if total_contacts != EXPECTED_TOTAL_CONTACTS:
        problems.append(
            f"sweep contact count {total_contacts} != machinery EXPECTED_TOTAL_CONTACTS {EXPECTED_TOTAL_CONTACTS}"
        )
    if total_contacts != plan.planned_model_calls:
        problems.append(
            f"contact arithmetic {total_contacts} != the plan's declared {plan.planned_model_calls}"
        )
    print(f"arm ids (flight order): {list(ARM_IDS)}")
    print(
        f"audio-seconds arithmetic (METERED, three passes): {sweep_audio:.3f} <= plan ceiling "
        f"{plan.planned_speech_audio_seconds}"
    )
    if sweep_audio > plan.planned_speech_audio_seconds:
        problems.append("metered audio-seconds estimate exceeds the plan ceiling")

    # ---- 6. media-marker pin ------------------------------------------------
    print()
    try:
        marker = resolve_expected_media_marker()
    except EmbeddingClientError as error:
        problems.append(f"{LLAMA_MEDIA_MARKER_ENV} pin missing: {error}")
    else:
        print(f"{LLAMA_MEDIA_MARKER_ENV} pinned in this environment: {marker!r}")
        print(
            "  (the VALUE is re-verified against EACH live server's GET /props at flight time, "
            "fail-closed -- this check proves only that the pin exists)"
        )

    # ---- 7. coexistence guard (dry run) ------------------------------------
    try:
        assert_no_conflicting_generation_server(
            generation_server_reachable=lambda: _port_reachable("127.0.0.1", GENERATION_PORT),
            generation_base_url=f"http://127.0.0.1:{GENERATION_PORT}",
        )
    except EmbeddingClientError as error:
        problems.append(f"COEXISTENCE GUARD: {error}")
    else:
        print(f"coexistence guard: nothing answers on the generation port {GENERATION_PORT} -- PASS")
    if _port_reachable("127.0.0.1", EMBEDDING_PORT):
        problems.append(f"something is ALREADY listening on the embedding port {EMBEDDING_PORT}")
    else:
        print(f"embedding port {EMBEDDING_PORT}: free -- PASS")

    # ---- 8. RUN-TOTAL budget feasibility ------------------------------------
    from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: PLC0415

    store = AttemptStore(attempts_root=root / "attempts")
    prior_calls, prior_audio = store.prior_actual_usage(run_id, exclude_attempt_id=None)
    print()
    print("=== run-total budget feasibility (sibling attempts count) ===")
    print(f"prior durable spend on {run_id}: calls={prior_calls}, audio_seconds={prior_audio:.3f}")
    headroom_calls = plan.planned_model_calls - prior_calls
    headroom_audio = plan.planned_speech_audio_seconds - prior_audio
    print(f"headroom for a FRESH attempt: calls={headroom_calls}, audio_seconds={headroom_audio:.3f}")
    print(f"this sweep needs: calls={total_contacts}, metered audio_seconds={sweep_audio:.3f}")
    if prior_calls != 0 or prior_audio != 0.0:
        problems.append(
            f"registration declares prior spend 0 on {run_id} but the durable store reports "
            f"calls={prior_calls}, audio_seconds={prior_audio:.3f}"
        )
    else:
        print("prior spend is 0, as the registration's feasibility statement declares -- OK")
    if total_contacts > headroom_calls:
        problems.append(
            f"RUN-TOTAL CALL BUDGET INFEASIBLE: needs {total_contacts}, {headroom_calls} remain "
            f"({prior_calls} already durably spent). Resolution is a REGISTRATION act."
        )
    else:
        print("call headroom: sufficient for a full fresh attempt -- OK")
    if sweep_audio > headroom_audio:
        problems.append(
            f"RUN-TOTAL AUDIO BUDGET INFEASIBLE: needs {sweep_audio:.3f}s, {headroom_audio:.3f}s remain"
        )
    else:
        print("audio headroom: sufficient for a full fresh attempt -- OK")

    print()
    print(f"environment SAEA_FEAT_CACHE_DIR: {os.environ.get('SAEA_FEAT_CACHE_DIR')!r}")
    print(f"resolved server_env feat cache:  {values['server_env']['LLAMA_MTMD_FEAT_CACHE_DIR']!r}")

    print()
    if problems:
        print(f"PRE-FLIGHT PROBLEMS ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("PRE-FLIGHT CLEAN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
