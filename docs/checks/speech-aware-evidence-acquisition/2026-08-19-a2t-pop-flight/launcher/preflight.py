"""P-A2T whole-population regression PRE-FLIGHT check -- ZERO model contact.

Structurally the archived Stage-2c pre-flight
(``docs/checks/speech-aware-evidence-acquisition/2026-08-18-a2t-s2c-flight/
launcher/preflight.py``), with the Stage-2c arm-plan items replaced by this
probe's own roster-derivation items. Verifies, before any core contact:

  1. the consumed A0 read's own published headroom artifact loads through the
     machinery's OWN loader and passes the machinery's OWN fail-closed
     ``assert_split_identity_hash_pinned``;
  2. the EM-correct roster derives to EXACTLY 97 ids through
     ``derive_em_correct_ids`` (the frozen scorer over the consumed A0 attempt,
     never a second implementation), is deterministic across two derivations,
     and is DISJOINT from the consumed 120-id headroom set -- the structural
     signature of the EM==1 vs EM==0 partition;
  3. the 97 resolve against the frozen discovery split and every wav is
     present; the measured one-pass audio agrees with ``split-measurement.json``;
  4. the R1 self-supplied plan builds: every sample resolves at least one tool
     from the CONSUMED A0 attempt, every named tool is present in the 152-row
     registry, and every B1-form render is strictly shorter than the full
     registry (structural counts only -- nothing is scored);
  5. the exposure row ``SAEA-PROBE-a2t-pop-194`` exists exactly once,
     consumed=no, its split-identity-hash cell agrees VERBATIM, and its budget
     cells cover the plan AND match the preregistration's own section-4
     ceilings;
  6. the ExecutionPlan validates and the registered call arithmetic
     (97 x 2 = 194 <= 210 planned <= 220 registered) plus the metered audio
     arithmetic hold;
  7. the RUN-TOTAL budget is feasible for a fresh attempt.

Nothing here opens a socket, spawns a server, or reads a model.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.contracts.ledger import (  # noqa: E402
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash as compute_protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    load_tool_registry,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes.a2t_pop_flight import (  # noqa: E402
    A2T_POP_ARMS,
    EM_CORRECT_N,
    build_flight_plan_from_attempt,
    derive_em_correct_ids,
    render_b1_tool_schemas,
)

from flight_identity import RUN_ID, build_values, config_hash_of, resolve_split  # noqa: E402
from flight_plan import (  # noqa: E402
    CALLS_CEILING,
    EXPECTED_REQUESTS,
    PLANNED_GPU_HOURS,
    PLANNED_MODEL_CALLS,
    PLANNED_SPEECH_AUDIO_SECONDS,
    REGISTERED_CALLS,
    REGISTERED_GPU_HOURS,
    REGISTERED_SPEECH_AUDIO_SECONDS,
)


def main() -> int:
    problems: list[str] = []
    print(f"repo module root: {Path(__import__('speech_aware_evidence_acquisition').__file__).parent}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    print(f"carrier_root (asset_dir audio2tool): {asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)}")

    # ---- 1. headroom artifact + pinned split identity ----------------------
    split = resolve_split(REPO)
    print(f"headroom artifact: {len(split.headroom_ids)} consumed headroom ids")
    print(f"consumed A0 attempt dir: {split.consumed_a0_attempt_dir}")
    print(f"split_identity_hash: {split.split_identity_hash}")
    print("split identity: machinery assert_split_identity_hash_pinned PASSED")
    if len(split.headroom_ids) != 120:
        problems.append(f"headroom artifact carries {len(split.headroom_ids)} ids, expected 120")
    if not Path(split.consumed_a0_attempt_dir).is_dir():
        problems.append(f"consumed A0 attempt dir missing: {split.consumed_a0_attempt_dir}")

    # ---- 2. EM-correct roster ----------------------------------------------
    em_ids = derive_em_correct_ids(
        Path(split.consumed_a0_attempt_dir), lock, root, repo_root=REPO, expected_n=EM_CORRECT_N
    )
    print(f"EM-correct roster: {len(em_ids)} ids (registered {EM_CORRECT_N}) -- fail-closed check PASSED")
    re_em = derive_em_correct_ids(
        Path(split.consumed_a0_attempt_dir), lock, root, repo_root=REPO, expected_n=EM_CORRECT_N
    )
    if re_em != em_ids:
        problems.append("EM-correct derivation is not deterministic across two calls")
    else:
        print("EM-correct roster: deterministic across repeated derivation -- PASS")
    if len(set(em_ids)) != len(em_ids):
        problems.append("EM-correct roster carries duplicate ids")
    overlap = sorted(set(em_ids) & set(split.headroom_ids))
    print(f"disjointness from the consumed 120-id headroom set: {len(overlap)} overlapping id(s)")
    if overlap:
        problems.append(f"EM-correct roster overlaps the headroom set: {overlap[:5]}")
    else:
        print("  partition invariant OK: EM==1 population and EM==0 headroom set are disjoint")
    print(f"arms: machinery A2T_POP_ARMS == {list(A2T_POP_ARMS)}")
    # 217 tool-correct = 120 headroom (EM==0) + 97 EM-correct (EM==1); the other
    # 183 of the frozen 400 are tool-selection failures, excluded by the prereg.
    print(
        f"population accounting: {len(em_ids)} EM-correct + {len(split.headroom_ids)} headroom = "
        f"{len(em_ids) + len(split.headroom_ids)} tool-correct of the frozen 400; "
        f"{400 - len(em_ids) - len(split.headroom_ids)} tool-selection failures excluded "
        "(recorded limitation, prereg section 1)"
    )

    # ---- 3. split resolution + measurement agreement ------------------------
    adapter = Audio2ToolAdapter(lock, root, repo_root=REPO)
    print("resolving the frozen discovery split (sha256 of every media file -- slow, model-free)")
    all_samples = adapter.load_split("discovery")
    by_id = {s.sample_id: s for s in all_samples}
    print(f"discovery split resolved: {len(all_samples)} samples")
    missing = [sid for sid in em_ids if sid not in by_id]
    if missing:
        problems.append(f"{len(missing)} EM-correct ids absent from the frozen split: {missing[:5]}")
    samples = [by_id[sid] for sid in em_ids if sid in by_id]
    missing_media = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing_media:
        problems.append(f"{len(missing_media)} sample media missing: {missing_media[:5]}")
    else:
        print(f"media resolved: {len(samples)}/{len(samples)} wav present")
    one_pass = sum(s.audio_seconds for s in samples)
    longest = max(s.audio_seconds for s in samples)
    print(
        f"one pass over the EM-correct {len(samples)}: {one_pass:.2f}s "
        f"(mean {one_pass/max(len(samples),1):.2f}s, longest {longest:.2f}s)"
    )
    measurement_path = Path(__file__).resolve().parent / "split-measurement.json"
    measurement = json.loads(measurement_path.read_text(encoding="utf-8"))
    if abs(float(measurement["one_pass_audio_seconds"]) - one_pass) > 0.01:
        problems.append(
            f"split-measurement.json records one_pass {measurement['one_pass_audio_seconds']} but "
            f"this pre-flight measures {one_pass:.3f}"
        )
    else:
        print("split measurement agreement: preflight == split-measurement.json -- PASS")
    if list(measurement["em_correct_sample_ids"]) != list(em_ids):
        problems.append("split-measurement.json em_correct_sample_ids disagree with the re-derived roster")

    # ---- 4. R1 self-supplied plan ------------------------------------------
    registry_rows = load_tool_registry(lock, root)
    full_registry_text = render_tool_schemas(lock, root)
    print(f"tool registry: {len(registry_rows)} rows, full render {len(full_registry_text)} chars")
    fplan = build_flight_plan_from_attempt(em_ids, Path(split.consumed_a0_attempt_dir), registry_rows)
    tool_counts = Counter(len(v) for v in fplan.r1_tool_names_by_sample.values())
    distinct_tools = {n for names in fplan.r1_tool_names_by_sample.values() for n in names}
    print(
        f"R1 self-supplied plan: {len(fplan.sample_ids)} samples; tool count distribution "
        f"{json.dumps(dict(sorted(tool_counts.items())), sort_keys=True)}; "
        f"{len(distinct_tools)} distinct supplied tools"
    )
    if set(fplan.sample_ids) != set(em_ids):
        problems.append("flight plan sample ids do not equal the EM-correct roster")
    empty = [sid for sid, names in fplan.r1_tool_names_by_sample.items() if not names]
    if empty:
        problems.append(f"{len(empty)} sample(s) resolved no R1 tool: {empty[:5]}")
    r1_lengths = {
        sid: len(render_b1_tool_schemas([fplan.registry_index[n] for n in names]))
        for sid, names in fplan.r1_tool_names_by_sample.items()
    }
    not_shorter = [sid for sid, n in r1_lengths.items() if n >= len(full_registry_text)]
    if not_shorter:
        problems.append(f"R1 render is not shorter than the full registry for: {not_shorter[:5]}")
    else:
        print(
            f"R1 render invariant: every R1 roster strictly shorter "
            f"({min(r1_lengths.values())}-{max(r1_lengths.values())} vs full "
            f"{len(full_registry_text)} chars) -- PASS"
        )

    # ---- 5. exposure ledger row --------------------------------------------
    print()
    rows = _parse_ledger_tables((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8"))
    matched = [r for r in rows if r.get(_EXPOSURE_RUN_COLUMN) == RUN_ID]
    print(f"exposure rows matching run id {RUN_ID!r}: {len(matched)}")
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
        if row.get("split identity hash") != split.split_identity_hash:
            problems.append(
                "LEDGER CELL MISMATCH: 'split identity hash' cell is "
                f"{row.get('split identity hash')!r} but the plan will carry "
                f"{split.split_identity_hash!r}; FrozenCoreGate compares these verbatim"
            )
        if str(row.get("consumed", "")).lower() != "no":
            problems.append(f"exposure row consumed={row.get('consumed')!r}, must be 'no'")
        for cell_name, registered_expected, planned_value, caster in (
            ("calls", REGISTERED_CALLS, PLANNED_MODEL_CALLS, int),
            (
                "speech audio seconds",
                REGISTERED_SPEECH_AUDIO_SECONDS,
                PLANNED_SPEECH_AUDIO_SECONDS,
                int,
            ),
            ("gpu hours", REGISTERED_GPU_HOURS, PLANNED_GPU_HOURS, float),
        ):
            try:
                registered_value = caster(str(row.get(cell_name, "")).strip())
            except ValueError:
                problems.append(f"ledger cell {cell_name!r} is not numeric: {row.get(cell_name)!r}")
                continue
            if registered_value != caster(registered_expected):
                problems.append(
                    f"ledger {cell_name!r} cell registers {registered_value} but the "
                    f"preregistration section 4 declares {registered_expected}"
                )
            if registered_value < caster(planned_value):
                problems.append(
                    f"ledger {cell_name!r} cell registers {registered_value} but the plan declares "
                    f"{planned_value}; FrozenCoreGate refuses when registered < planned"
                )
            else:
                print(
                    f"  budget cell {cell_name!r}: registered {registered_value} == prereg "
                    f"{registered_expected} >= planned {planned_value} -- OK"
                )

    # ---- 6. plan + registered arithmetic ------------------------------------
    print()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), split.split_identity_hash)
    print(f"config_hash: {cfg_hash}")
    print(f"protocol_hash: {phash}")
    print(f"server_env: {values['server_env']}")
    print(f"server_args: {values['server_args']}")
    print(f"decoding_params: {values['decoding_params']}")
    argv = list(values["server_args"])  # type: ignore[arg-type]
    if "-np" in argv and argv[argv.index("-np") + 1] != "1":
        problems.append(
            "server_args carries -np != 1; R0 is A0's own full-152-row request and overflows a "
            "12288-token slot"
        )
    else:
        print("server_args -np delta: 4 -> 1 applied (R0 is A0's own registry-sized request) -- OK")
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=split.split_identity_hash,
        planned_model_calls=PLANNED_MODEL_CALLS,
        planned_gpu_hours=PLANNED_GPU_HOURS,
        planned_speech_audio_seconds=PLANNED_SPEECH_AUDIO_SECONDS,
        protocol_hash=phash,
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role}")
    registered_calls = len(A2T_POP_ARMS) * len(em_ids)
    print(
        f"registered call arithmetic: {len(em_ids)} samples x {len(A2T_POP_ARMS)} arms = "
        f"{registered_calls} (prereg {EXPECTED_REQUESTS}) <= plan ceiling {plan.planned_model_calls} "
        f"<= mission/registered ceiling {CALLS_CEILING}"
    )
    if registered_calls != EXPECTED_REQUESTS:
        problems.append(f"call arithmetic yields {registered_calls}, the prereg declares {EXPECTED_REQUESTS}")
    if registered_calls > plan.planned_model_calls:
        problems.append("registered call arithmetic exceeds the plan ceiling")
    metered_audio = one_pass * len(A2T_POP_ARMS)
    print(
        f"audio-seconds arithmetic (METERED; R0 and R1 each re-send their sample's real audio): "
        f"{one_pass:.2f} x {len(A2T_POP_ARMS)} arms = {metered_audio:.2f} <= plan ceiling "
        f"{plan.planned_speech_audio_seconds} <= registered {REGISTERED_SPEECH_AUDIO_SECONDS}"
    )
    if metered_audio > plan.planned_speech_audio_seconds:
        problems.append("metered audio-seconds estimate exceeds the plan ceiling")

    # ---- 7. RUN-TOTAL budget feasibility ------------------------------------
    from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: PLC0415

    store = AttemptStore(attempts_root=root / "attempts")
    prior_calls, prior_audio = store.prior_actual_usage(RUN_ID, exclude_attempt_id=None)
    print()
    print("=== run-total budget feasibility (sibling attempts count) ===")
    print(f"prior durable spend on {RUN_ID}: calls={prior_calls}, audio_seconds={prior_audio:.2f}")
    headroom_calls = plan.planned_model_calls - prior_calls
    headroom_audio = plan.planned_speech_audio_seconds - prior_audio
    print(f"headroom for a FRESH attempt: calls={headroom_calls}, audio_seconds={headroom_audio:.2f}")
    print(f"this flight needs: calls={registered_calls}, metered audio_seconds={metered_audio:.2f}")
    if registered_calls > headroom_calls:
        problems.append(
            f"RUN-TOTAL CALL BUDGET INFEASIBLE: needs {registered_calls}, {headroom_calls} remain "
            f"({prior_calls} already durably spent). Resolution is a REGISTRATION act."
        )
    else:
        print("call headroom: sufficient for a full fresh attempt -- OK")
    if metered_audio > headroom_audio:
        problems.append(
            f"RUN-TOTAL AUDIO BUDGET INFEASIBLE: needs {metered_audio:.2f}s, {headroom_audio:.2f}s remain"
        )
    else:
        print("audio headroom: sufficient for a full fresh attempt -- OK")

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
