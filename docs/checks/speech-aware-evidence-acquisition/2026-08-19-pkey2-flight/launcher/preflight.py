"""P-KEY flight PRE-FLIGHT check -- ZERO model contact.

Verifies, before any core contact:
  1. the committed flight config passes the machinery's own fail-closed
     config/code parity guard (assert_pinned_text_matches_config: T0
     instruction + TXT template text and their sha256 companions);
  2. the frozen n=60 sample manifest resolves against the devel split, its
     split_identity_hash equals the machinery's pinned
     EXPECTED_SPLIT_IDENTITY_HASH verbatim, all 60 flac files exist, total
     audio matches the preregistration;
  3. the roster table loads under its own legality checks and the A3-form
     100-entry packet builds via the SAME frozen pslu_supply_packet;
  4. the 3 silence-swap sample ids are inside the frozen 60 AND re-derive
     exactly from the registered seed rule
     sorted(random.Random(f"{seed}:silence-swap").sample(sorted(ids), 3));
  5. the exposure row SAEA-PROBE-pkey2-338 exists exactly once, consumed=no,
     its split-identity-hash cell agrees VERBATIM with the manifest, and its
     budget cells agree with the plan;
  6. the ExecutionPlan validates and the registered call arithmetic
     (60x5 + 3 swap + 35 txt-duplicate = 338 <= 340) plus the audio-seconds
     arithmetic hold -- both the CONTENT figure and the METERED figure that
     includes the TXT arms' payload-bookkeeping duration;
  7. the RUN-TOTAL budget is actually feasible for a fresh attempt:
     core.model.adapter charges every sibling attempt's durable spend on this
     run_id against the SAME plan ceiling, so a re-fly after an aborted attempt
     does not start from zero. This is the check that REFUSED the predecessor
     run SAEA-PROBE-pkey-303 (183 durably spent + 338 needed > 340 registered);
     under the successor row SAEA-PROBE-pkey2-338 prior spend is 0 and the
     registered ceiling is 360, so it must now pass.
Also checks the 2026-08-19 amendment's txt_duplicate sub-block (count, frozen
membership, seeded re-derivation under the 'txt-duplicate' salt, arm).
Nothing here opens a socket, spawns a server, or reads a model.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.contracts.ledger import (
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash as compute_protocol_hash
from speech_aware_evidence_acquisition.data.lock import (
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SLURP_LOCK_KEY, SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pkey_flight import (
    EXPECTED_SILENCE_SWAP_COUNT,
    EXPECTED_SPLIT_IDENTITY_HASH,
    PKEY_ARMS,
    assert_pinned_text_matches_config,
    t0_instruction_sha256,
    txt_template_sha256,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
    load_pslu_rosters,
    load_pslu_sample_manifest,
    select_pslu_samples,
    pslu_supply_packet,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flight_identity import RUN_ID, build_values, config_hash_of  # noqa: E402

FLIGHT_CFG = json.loads(
    (REPO / "configs/probes/g0-binding/pkey-flight.json").read_text(encoding="utf-8")
)


def main() -> int:
    problems: list[str] = []
    print(f"repo module root: {Path(__import__('speech_aware_evidence_acquisition').__file__).parent}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    carrier_root = asset_dir(lock, SLURP_LOCK_KEY, root)
    print(f"carrier_root (asset_dir slurp): {carrier_root}")

    # ---- 1. config/code parity (fail-closed machinery guard) -------------
    try:
        assert_pinned_text_matches_config(FLIGHT_CFG)
    except Exception as error:  # noqa: BLE001 -- fail-closed: any raise is a preflight problem
        problems.append(f"CONFIG/CODE PARITY FAILED: {type(error).__name__}: {error}")
    else:
        print("config/code parity: t0_instruction + txt_template + both sha256 companions agree -- PASS")
    print(f"  t0_instruction_sha256: {t0_instruction_sha256()}")
    print(f"  txt_template_sha256:   {txt_template_sha256()}")
    if list(FLIGHT_CFG["arms"]) != list(PKEY_ARMS):
        problems.append(
            f"config arms {FLIGHT_CFG['arms']!r} != machinery PKEY_ARMS {list(PKEY_ARMS)!r}"
        )
    else:
        print(f"arms: config == machinery PKEY_ARMS == {list(PKEY_ARMS)}")

    # ---- 2. sample manifest + split identity -----------------------------
    manifest = load_pslu_sample_manifest(REPO / FLIGHT_CFG["sample_manifest"])
    print(f"manifest: n={len(manifest.sample_ids)} seed={manifest.seed}")
    print(f"split_identity_hash (full, from binding JSON): {manifest.split_identity_hash}")
    if manifest.split_identity_hash != EXPECTED_SPLIT_IDENTITY_HASH:
        problems.append(
            f"manifest split_identity_hash {manifest.split_identity_hash!r} != machinery pin "
            f"{EXPECTED_SPLIT_IDENTITY_HASH!r}"
        )
    else:
        print("split identity: manifest == machinery EXPECTED_SPLIT_IDENTITY_HASH verbatim -- PASS")
    if FLIGHT_CFG["execution_plan"]["split_identity_hash"] != manifest.split_identity_hash:
        problems.append("flight config execution_plan.split_identity_hash != manifest hash")

    # ---- roster table + A3 packet ----------------------------------------
    rosters = load_pslu_rosters(REPO / FLIGHT_CFG["roster_table"])
    print(
        f"rosters: {len(rosters.scenario_rosters)} scenarios, "
        f"{len(rosters.global_types)} global types, "
        f"{len(rosters.full_roster)} full-roster entries, "
        f"{len(rosters.derangement)} derangement keys"
    )
    a3 = pslu_supply_packet("A3", scenario=None, rosters=rosters)
    print(f"A3 packet: {len(a3.items)} items, dose n_items={a3.dose.n_items} (prereg: 100-entry roster)")
    if a3.dose.n_items != 100:
        problems.append(f"A3 packet dose n_items {a3.dose.n_items} != 100")

    # ---- devel split resolution ------------------------------------------
    adapter = SlurpAdapter(lock, root, repo_root=REPO)
    all_devel = adapter.load_split("devel")
    print(f"devel split resolved: {len(all_devel)} samples")
    samples = select_pslu_samples(all_devel, manifest)
    print(f"frozen sample set selected: {len(samples)}")

    missing = [s.sample_id for s in samples if not (root / s.media_relpath).is_file()]
    if missing:
        problems.append(f"{len(missing)} sample media missing: {missing[:5]}")
    total_audio = sum(s.audio_seconds for s in samples)
    print(f"media resolved: {len(samples) - len(missing)}/{len(samples)} flac present")
    print(f"total audio seconds: {total_audio:.2f} (prereg: 182.26), mean {total_audio/len(samples):.2f}")

    # ---- 4. silence-swap ids: membership + seeded re-derivation ----------
    swap_ids = list(FLIGHT_CFG["silence_swap"]["sample_ids"])
    seed = int(FLIGHT_CFG["silence_swap"]["seed"])
    frozen = {s.sample_id for s in samples}
    outside = [i for i in swap_ids if i not in frozen]
    print(f"silence-swap ids: {swap_ids}")
    if len(swap_ids) != EXPECTED_SILENCE_SWAP_COUNT:
        problems.append(f"config carries {len(swap_ids)} swap ids, machinery expects {EXPECTED_SILENCE_SWAP_COUNT}")
    if outside:
        problems.append(f"silence-swap ids outside the frozen 60: {outside}")
    else:
        print("silence-swap ids: all 3 inside the frozen 60 -- OK")
    rederived = sorted(
        random.Random(f"{seed}:silence-swap").sample(sorted(manifest.sample_ids), EXPECTED_SILENCE_SWAP_COUNT)
    )
    if rederived != swap_ids:
        problems.append(
            f"seeded re-derivation {rederived!r} != config silence_swap.sample_ids {swap_ids!r}"
        )
    else:
        print(f"silence-swap seeded re-derivation (seed {seed}): matches config verbatim -- PASS")
    if FLIGHT_CFG["silence_swap"]["arm"] != "AUD-SUP":
        problems.append(f"silence_swap.arm {FLIGHT_CFG['silence_swap']['arm']!r} != 'AUD-SUP'")

    # ---- 4b. txt_duplicate sub-block (2026-08-19 amendment item 4) -------
    dup_block = FLIGHT_CFG["txt_duplicate"]
    dup_ids = list(dup_block["sample_ids"])
    dup_count = int(dup_block["count"])
    dup_seed = int(dup_block["seed"])
    print(f"txt-duplicate sub-block: count={dup_count}, {len(dup_ids)} ids listed")
    if len(dup_ids) != dup_count:
        problems.append(f"txt_duplicate lists {len(dup_ids)} ids but declares count={dup_count}")
    if len(set(dup_ids)) != len(dup_ids):
        problems.append("txt_duplicate.sample_ids carries a duplicate id")
    dup_outside = [i for i in dup_ids if i not in frozen]
    if dup_outside:
        problems.append(f"txt_duplicate ids outside the frozen 60: {dup_outside}")
    else:
        print(f"txt-duplicate ids: all {len(dup_ids)} inside the frozen 60 -- OK")
    dup_rederived = sorted(
        random.Random(f"{dup_seed}:txt-duplicate").sample(sorted(manifest.sample_ids), dup_count)
    )
    if dup_rederived != sorted(dup_ids):
        only_derived = sorted(set(dup_rederived) - set(dup_ids))
        only_config = sorted(set(dup_ids) - set(dup_rederived))
        problems.append(
            "txt-duplicate seeded re-derivation != config txt_duplicate.sample_ids "
            f"(only in re-derivation: {only_derived[:3]}; only in config: {only_config[:3]})"
        )
    else:
        print(
            f"txt-duplicate seeded re-derivation (seed {dup_seed}, salt 'txt-duplicate'): "
            "matches config verbatim -- PASS"
        )
    if dup_block["arm"] != "TXT-NOSUP":
        problems.append(f"txt_duplicate.arm {dup_block['arm']!r} != 'TXT-NOSUP'")
    collide = sorted(set(dup_ids) & set(swap_ids))
    print(
        f"draw overlap (silence-swap AND txt-duplicate): {collide or 'none'} "
        "(informational -- different arms, no interference)"
    )

    # ---- 5. exposure ledger row ------------------------------------------
    rows = _parse_ledger_tables((REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8"))
    matched = [r for r in rows if r.get(_EXPOSURE_RUN_COLUMN) == RUN_ID]
    ledger_calls_cell = matched[0].get("calls") if len(matched) == 1 else "<unresolved>"
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
        if row.get("split identity hash") != manifest.split_identity_hash:
            problems.append(
                "LEDGER CELL MISMATCH: 'split identity hash' cell is "
                f"{row.get('split identity hash')!r} but the plan will carry the full 64-hex "
                f"{manifest.split_identity_hash!r}; FrozenCoreGate compares these verbatim "
                "(gate_exposure._require_exposure_preregistration) -- the gate WILL refuse."
            )
        if str(row.get("consumed", "")).lower() != "no":
            problems.append(f"exposure row consumed={row.get('consumed')!r}, must be 'no'")
        # CEILING semantics, matching the gate's own comparison
        # (contracts.gate_exposure: refuse when registered < planned), not
        # equality: 01583dc tightened planned_model_calls 340 -> 338 while the
        # registered row keeps its 340 ceiling.
        for cell_name, planned_value, caster in (
            ("calls", FLIGHT_CFG["execution_plan"]["planned_model_calls"], int),
            ("speech audio seconds", FLIGHT_CFG["execution_plan"]["planned_speech_audio_seconds"], int),
            ("gpu hours", FLIGHT_CFG["execution_plan"]["planned_gpu_hours"], float),
        ):
            try:
                registered_value = caster(str(row.get(cell_name, "")).strip())
            except ValueError:
                problems.append(f"ledger cell {cell_name!r} is not numeric: {row.get(cell_name)!r}")
                continue
            if registered_value < caster(planned_value):
                problems.append(
                    f"ledger {cell_name!r} cell registers {registered_value} but the plan "
                    f"declares {planned_value}; FrozenCoreGate refuses when registered < planned"
                )
            else:
                print(f"  budget cell {cell_name!r}: registered {registered_value} >= planned {planned_value} -- OK")

    # ---- 6. plan + registered call/audio arithmetic ----------------------
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), manifest.split_identity_hash)
    print(f"config_hash: {cfg_hash}")
    print(f"protocol_hash: {phash}")
    print(f"server_env: {values['server_env']}")
    print(f"server_args: {values['server_args']}")
    print(f"decoding_params: {values['decoding_params']}")
    plan = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile=FLIGHT_CFG["execution_plan"]["execution_profile"],
        carrier_lock_key=FLIGHT_CFG["execution_plan"]["carrier_lock_key"],
        split_role=FLIGHT_CFG["execution_plan"]["split_role"],
        split_identity_hash=manifest.split_identity_hash,
        planned_model_calls=int(FLIGHT_CFG["execution_plan"]["planned_model_calls"]),
        planned_gpu_hours=float(FLIGHT_CFG["execution_plan"]["planned_gpu_hours"]),
        planned_speech_audio_seconds=int(
            FLIGHT_CFG["execution_plan"]["planned_speech_audio_seconds"]
        ),
        protocol_hash=phash,
        attempt_id="attempt-preflight-000000",
    ).validate()
    print(f"ExecutionPlan validates: profile={plan.execution_profile} role={plan.split_role}")
    registered_calls = 60 * 5 + 3 + dup_count
    print(
        f"registered call arithmetic: 60 (T0) + 60 (AUD-NOSUP) + 60 (AUD-SUP) + 60 (TXT-NOSUP) "
        f"+ 60 (TXT-SUP) + 3 (swap) + {dup_count} (txt-duplicate) = {registered_calls} "
        f"<= plan ceiling {plan.planned_model_calls}"
    )
    if registered_calls > plan.planned_model_calls:
        problems.append("registered call arithmetic exceeds the plan ceiling")
    swap_audio = sum(s.audio_seconds for s in samples if s.sample_id in set(swap_ids))
    dup_audio = sum(s.audio_seconds for s in samples if s.sample_id in set(dup_ids))
    content_audio = total_audio * 3 + swap_audio
    # The bridge's payload-binding bookkeeping field: every TXT-* request also
    # carries its own sample's real duration (flight config's ENGINEERING
    # NOTE) and the adapter METERS that number, so the figure the budget check
    # actually sees is the bookkeeping-inclusive total, not the content total.
    metered_audio = content_audio + total_audio * 2 + dup_audio
    print(
        f"audio-seconds arithmetic (content actually decoded): {total_audio:.2f} x 3 audio passes "
        f"+ {swap_audio:.2f} swap = {content_audio:.2f}"
    )
    print(
        f"audio-seconds arithmetic (METERED, incl. TXT bookkeeping): {content_audio:.2f} "
        f"+ {total_audio:.2f} (TXT-NOSUP) + {total_audio:.2f} (TXT-SUP) + {dup_audio:.2f} (txt-dup) "
        f"= {metered_audio:.2f} <= plan ceiling {plan.planned_speech_audio_seconds}"
    )
    if metered_audio > plan.planned_speech_audio_seconds:
        problems.append("metered audio-seconds estimate exceeds the plan ceiling")

    # ---- 7. RUN-TOTAL budget feasibility across sibling attempts ---------
    # core.model.adapter.FrozenCoreAdapter.request refuses when
    #   sibling_calls + calls_used + 1 > plan.planned_model_calls
    # where sibling_calls re-reads EVERY other attempt file on this run_id
    # (core.attempts.store.prior_actual_usage sums all states, including an
    # aborted attempt stuck at OPENED). A fresh attempt therefore does NOT
    # start from zero: whatever attempt-1 durably spent is already charged.
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
            f"RUN-TOTAL CALL BUDGET INFEASIBLE: a fresh attempt needs {registered_calls} calls but "
            f"only {headroom_calls} remain under plan ceiling {plan.planned_model_calls} "
            f"({prior_calls} already durably spent by prior attempt(s) on this run_id). "
            f"FrozenCoreAdapter.request would refuse at request {headroom_calls + 1} with 'call "
            f"budget exhausted'. Registered ledger ceiling is "
            f"{ledger_calls_cell} calls, so even restoring "
            "planned_model_calls to the ledger value does not make a full re-fly fit "
            f"({prior_calls} + {registered_calls} = {prior_calls + registered_calls}). "
            "Resolution is a REGISTRATION act (owner/coordinator): amend the row's ceiling, or "
            "open a new registered run_id -- NOT an implementer edit."
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
