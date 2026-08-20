"""P-EMB flight PRE-FLIGHT check -- ZERO model contact, ZERO server spawn.

Runs for ONE run (``--run A`` / ``--run B``). Structurally the archived P-TRAP
pre-flight, with the generation-specific items replaced by this probe's own
embedding-tier items. Verifies, before any core contact:

  1. the machinery's own import-time ontology-miner guard passes (Run A) and
     the run's ``split_identity_hash`` equals the committed machinery pin
     VERBATIM -- Run A against ``rails.probes.pemb_flight.
     EXPECTED_RUN_A_SPLIT_IDENTITY_HASH`` and the frozen 60-sample manifest,
     Run B against ``EXPECTED_RUN_B_SPLIT_IDENTITY_HASH`` cross-checked with
     the committed ``rails.probes.a2t_pop_flight.SPLIT_IDENTITY_HASH``;
  2. the run's own inputs resolve to EXACTLY the registered counts (Run A: 60
     devel samples + 18 canonical roster labels; Run B: 400 discovery samples
     + 152 registry rows), with no duplicate id and every media file present;
  3. the audio payload profile (min/mean/max seconds, total metered seconds)
     -- an operational feasibility statement for the embedding server's own
     pooled-sequence capacity, and the metered-audio arithmetic for the plan;
  4. the exposure row exists exactly once, consumed=no, its split-identity-hash
     cell agrees VERBATIM, and its budget cells cover the plan AND match the
     launcher's transcribed ``REGISTERED_CEILINGS``;
  5. the ExecutionPlan validates, the contact arithmetic holds, and the
     embedding server's own argv carries ``--embedding --pooling mean``,
     ``-ngl 999``, ``-np 1`` and its own port -- never the generation port;
  6. ``LLAMA_MEDIA_MARKER`` is pinned in this process's environment (the value
     itself is re-verified against the LIVE server's ``GET /props`` at flight
     time -- this check only proves the pin EXISTS, never that it is right);
  7. nothing is listening on the generation port (coexistence guard, dry-run of
     the same ``assert_no_conflicting_generation_server`` the launcher calls);
  8. the RUN-TOTAL budget is feasible for a fresh attempt.

Nothing here opens a socket to a model, spawns a server, or embeds anything.
"""

from __future__ import annotations

import argparse
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
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (  # noqa: E402
    RUN_A_AUDIO_N,
    RUN_A_LABEL_N,
    RUN_B_AUDIO_N,
    RUN_B_ROW_N,
    _assert_this_module_never_calls_ontology_miner,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    assert_never_calls_ontology_miner,
)

from flight_identity import (  # noqa: E402
    EMBEDDING_PORT,
    EXECUTION_PROFILE,
    GENERATION_PORT,
    PREREGISTRATION_RELPATH,
    ROSTER_TABLE_RELPATH,
    RUNS,
    SAMPLE_MANIFEST_RELPATH,
    SPLIT_ROLE,
    build_values,
    config_hash_of,
    run_id_for,
    split_identity_hash_for,
)


def _port_reachable(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, choices=("A", "B"))
    args = parser.parse_args()
    run_key = args.run
    block = RUNS[run_key]
    problems: list[str] = []

    print(f"repo module root: {Path(__import__('speech_aware_evidence_acquisition').__file__).parent}")
    print(f"preregistration: {PREREGISTRATION_RELPATH}")
    print(f"P-EMB Run {run_key}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    run_id = run_id_for(run_key)
    carrier = str(block["carrier_lock_key"])
    print(f"run id: {run_id}")
    print(f"data_root: {root}")
    print(f"carrier_root (asset_dir {carrier}): {asset_dir(lock, carrier, root)}")

    # ---- 1. guards + split identity ----------------------------------------
    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    print("ontology-miner guards (parent + pemb_flight self-source): PASS")
    split_hash = split_identity_hash_for(run_key)
    print(f"split_identity_hash (pinned, machinery-checked): {split_hash}")
    if run_key == "A":
        from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
            load_pslu_sample_manifest,
        )

        manifest = load_pslu_sample_manifest(REPO / SAMPLE_MANIFEST_RELPATH)
        print(f"frozen manifest: n={len(manifest.sample_ids)} seed={manifest.seed}")
        if manifest.split_identity_hash != split_hash:
            problems.append(
                f"frozen manifest hash {manifest.split_identity_hash!r} != machinery Run A pin "
                f"{split_hash!r}"
            )
        else:
            print("Run A: frozen manifest hash == machinery pin, verbatim -- PASS")

    # ---- 2/3. inputs + audio profile ---------------------------------------
    if run_key == "A":
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
        text_inputs = list(canonical_scenario_labels(rosters))
        text_label = "canonical scenario labels"
        expected_audio_n, expected_text_n = RUN_A_AUDIO_N, RUN_A_LABEL_N
        print(f"canonical scenario labels: {len(text_inputs)} -> {text_inputs}")
    else:
        from speech_aware_evidence_acquisition.data.audio2tool import (
            load_tool_registry,
            render_registry_row,
        )
        from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter

        adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
        samples = list(adapter.load_split("discovery"))
        text_inputs = list(load_tool_registry(lock, root))
        text_label = "tool registry rows"
        expected_audio_n, expected_text_n = RUN_B_AUDIO_N, RUN_B_ROW_N
        names = [row.get("tool_name") for row in text_inputs]
        print(f"tool registry rows: {len(text_inputs)}; distinct tool_name: {len(set(names))}")
        if len(set(names)) != len(names):
            problems.append("duplicate tool_name across registry rows")
        rendered = [render_registry_row(row) for row in text_inputs]
        print(
            f"rendered row text: min {min(map(len, rendered))} chars, "
            f"mean {sum(map(len, rendered))/len(rendered):.1f}, max {max(map(len, rendered))}"
        )

    print(f"audio samples resolved: {len(samples)} (expect {expected_audio_n})")
    print(f"{text_label} resolved: {len(text_inputs)} (expect {expected_text_n})")
    if len(samples) != expected_audio_n:
        problems.append(f"audio sample count {len(samples)} != registered {expected_audio_n}")
    if len(text_inputs) != expected_text_n:
        problems.append(f"{text_label} count {len(text_inputs)} != registered {expected_text_n}")
    sample_ids = [s.sample_id for s in samples]
    if len(set(sample_ids)) != len(sample_ids):
        problems.append("duplicate sample_id in the resolved audio samples")

    missing = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing:
        problems.append(f"{len(missing)} sample media missing: {missing[:5]}")
    print(f"media resolved: {len(samples) - len(missing)}/{len(samples)} present")

    seconds = [float(s.audio_seconds) for s in samples]
    total_audio = sum(seconds)
    byte_sizes = [(root / s.media_relpath).stat().st_size for s in samples if (root / s.media_relpath).is_file()]
    print(
        f"audio profile: total {total_audio:.2f}s, min {min(seconds):.2f}s, "
        f"mean {total_audio/len(seconds):.2f}s, max {max(seconds):.2f}s"
    )
    print(
        f"media byte profile: min {min(byte_sizes)} B, mean {sum(byte_sizes)/len(byte_sizes):.0f} B, "
        f"max {max(byte_sizes)} B (base64 inflates ~4/3 on the wire)"
    )

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
            launcher_ceiling = caster(block["registered_ceilings"][key])  # type: ignore[index]
            planned_value = caster(block["planned_budgets"][key])  # type: ignore[index]
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

    # ---- 5. plan + server argv ---------------------------------------------
    print()
    values = build_values(REPO, run_key)
    cfg_hash = config_hash_of(values)
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split_hash)
    print(f"config_hash: {cfg_hash}")
    print(f"protocol_hash: {phash}")
    print(f"base_url: {values['base_url']}")
    print(f"server_env: {values['server_env']}")
    print(f"server_args: {values['server_args']}")
    print(f"embedding dim (pinned): {EMBEDDING_DIM}")
    argv = [str(t) for t in values["server_args"]]
    for expected in ("--embedding", "--pooling", "mean", "-ngl", "999"):
        if expected not in argv:
            problems.append(f"server_args is missing the E-0-pinned token {expected!r}")
    if argv.count("-np") != 1 or argv[argv.index("-np") + 1] != "1":
        problems.append(f"server_args must carry exactly '-np 1', got {argv!r}")
    if str(values["base_url"]).endswith(f":{GENERATION_PORT}"):
        problems.append("base_url still points at the GENERATION port")
    if not str(values["base_url"]).endswith(f":{EMBEDDING_PORT}"):
        problems.append(f"base_url does not point at the embedding port {EMBEDDING_PORT}")
    if "temperature" in json.dumps(values["server_args"]):
        problems.append("a sampling parameter leaked into the embedding server argv")

    plan = ExecutionPlan(
        run_id=run_id,
        execution_profile=EXECUTION_PROFILE,
        carrier_lock_key=carrier,
        split_role=SPLIT_ROLE,
        split_identity_hash=split_hash,
        planned_model_calls=int(block["planned_budgets"]["model_calls"]),  # type: ignore[index]
        planned_gpu_hours=float(block["planned_budgets"]["gpu_hours"]),  # type: ignore[index]
        planned_speech_audio_seconds=int(block["planned_budgets"]["speech_audio_seconds"]),  # type: ignore[index]
        protocol_hash=phash,
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role}")
    total_contacts = len(samples) + len(text_inputs)
    print(
        f"contact arithmetic: {len(samples)} audio + {len(text_inputs)} text = {total_contacts} "
        f"<= plan ceiling {plan.planned_model_calls} <= registered ceiling "
        f"{block['registered_ceilings']['model_calls']}"  # type: ignore[index]
    )
    if total_contacts != plan.planned_model_calls:
        problems.append(
            f"contact arithmetic {total_contacts} != the plan's declared {plan.planned_model_calls}"
        )
    print(
        f"audio-seconds arithmetic (METERED): {total_audio:.2f} (one pass, each sample embedded "
        f"exactly once) <= plan ceiling {plan.planned_speech_audio_seconds}"
    )
    if total_audio > plan.planned_speech_audio_seconds:
        problems.append("metered audio-seconds estimate exceeds the plan ceiling")

    # ---- 6. media-marker pin ------------------------------------------------
    print()
    try:
        marker = resolve_expected_media_marker()
    except EmbeddingClientError as error:
        problems.append(f"{LLAMA_MEDIA_MARKER_ENV} pin missing: {error}")
        marker = None
    else:
        print(f"{LLAMA_MEDIA_MARKER_ENV} pinned in this environment: {marker!r}")
        print(
            "  (the VALUE is re-verified against the live server's GET /props at flight time, "
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
    print(f"this run needs: calls={total_contacts}, metered audio_seconds={total_audio:.2f}")
    if total_contacts > headroom_calls:
        problems.append(
            f"RUN-TOTAL CALL BUDGET INFEASIBLE: needs {total_contacts}, {headroom_calls} remain "
            f"({prior_calls} already durably spent). Resolution is a REGISTRATION act."
        )
    else:
        print("call headroom: sufficient for a full fresh attempt -- OK")
    if total_audio > headroom_audio:
        problems.append(
            f"RUN-TOTAL AUDIO BUDGET INFEASIBLE: needs {total_audio:.2f}s, {headroom_audio:.2f}s remain"
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
