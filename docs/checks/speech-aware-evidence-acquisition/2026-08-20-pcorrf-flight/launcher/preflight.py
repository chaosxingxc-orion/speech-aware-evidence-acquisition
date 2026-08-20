"""P-CORR-F flight PRE-FLIGHT check -- ZERO model contact, ZERO gold.

Structurally the archived P-TRAP pre-flight
(``docs/checks/speech-aware-evidence-acquisition/2026-08-19-ptrap-flight/
launcher/preflight.py``), with P-TRAP's gold zero-overlap items replaced by
this probe's own three legality guards (the gold zero-overlap check is an
ORACLE here -- preregistration section 4: "A corrective entry MAY equal gold;
that is the point"). Verifies, before any core contact:

  1. the machinery's own import-time guards pass when called explicitly -- the
     ontology-miner ban (reused verbatim from ``pslu_flight``), this module's
     own ontology-miner self-check, and the source-introspection
     forbidden-gold-symbol AST guard -- and the pinned binding-config sha256
     has not drifted;
  2. the frozen 60-sample manifest's ``split_identity_hash`` equals
     ``rails.probes.pcorrf_flight.EXPECTED_SPLIT_IDENTITY_HASH`` VERBATIM;
  3. the roster table loads under its own legality checks and the A3-form
     100-entry packet builds via the SAME frozen ``pslu_supply_packet``;
  4. the frozen 60 resolve against the devel split and every flac is present;
  5. the corrective binding re-derives to the SAME tri-derivation binding hash
     AND the SAME canonical document hash as the reviewed binding step
     (guard 1, sites #1 and #2 here; site #3 fires inside
     ``run_pcorrf_flight`` before it issues any request), and every structural
     invariant holds: W2 length-matched to W1, W2 fixed-point-free, W4-added
     entries disjoint from L1, per-arm K within the registration's own
     measured yield;
  6. the legality declarations resolve ``legal`` through ``core.legality``;
  7. the exposure row ``SAEA-PROBE-pcorrf-240`` exists exactly once,
     consumed=no, its split-identity-hash cell agrees VERBATIM with the
     manifest, and its budget cells cover the plan; and the CONSUMED source
     row ``SAEA-PROBE-pslu-n60`` reads consumed=yes;
  8. the ``contracts.ExecutionPlan`` validates through the machinery's own
     ``build_execution_plan`` and the registered arithmetic holds
     (60 x 4 = 240 <= 260 calls; 4 passes of metered audio <= 730 planned <=
     1000 ceiling; 0.15 <= 0.35 GPU-h);
  9. the RUN-TOTAL budget is feasible for a fresh attempt;
 10. no P-CORR-F run/attempt directory exists yet on the data root.

Nothing here opens a socket, spawns a server, or reads a model. The corrective
binding it re-derives is the registered supply-content sourcing step, not a
result read: no response is scored, ranked or displayed.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.contracts.ledger import (  # noqa: E402
    _EXPOSURE_RUN_COLUMN,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.config import protocol_hash as compute_protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.core.retrieval import normalize_term  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.slurp import SLURP_LOCK_KEY, SlurpAdapter  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes.pcorrf_flight import (  # noqa: E402
    CEILING_AUDIO_SECONDS,
    CEILING_CALLS,
    CEILING_GPU_HOURS,
    CONSUMED_PSLU_RUN_EXPERIMENT_ID,
    DEFAULT_PLANNED_GPU_HOURS,
    DEFAULT_PLANNED_MODEL_CALLS,
    DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS,
    EXPECTED_SPLIT_IDENTITY_HASH,
    PCORRF_ARMS,
    W1_ARM,
    W2_ARM,
    W4_ARM,
    _assert_this_module_never_calls_ontology_miner,
    assert_binding_config_sha256,
    assert_ledger_row_consumed,
    assert_never_calls_ontology_miner,
    assert_never_references_forbidden_gold_symbols,
    assert_pcorrf_legality,
    assert_split_identity_hash,
    assert_within_registered_ceilings,
    binding_config_sha256,
    build_execution_plan,
    pcorrf_supply_packet,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_rosters,
    load_pslu_sample_manifest,
    pslu_supply_packet,
    select_pslu_samples,
)

from binding import (  # noqa: E402
    SAMPLE_MANIFEST_RELPATH,
    arm_k_by_sample,
    build_binding,
    canonical_hash,
    consumed_attempt_dir,
    stats_document,
)
from flight_identity import RUN_ID, build_values, config_hash_of  # noqa: E402

ROSTER_TABLE_RELPATH = "configs/probes/g0-binding/pslu-rosters-train-only.json"

# The registration's own measured yield (section 1 / the machinery's build
# receipt), re-asserted here so a silent construction drift is caught before
# any request is issued rather than discovered in the read.
EXPECTED_L1_K_ZERO_SAMPLES = 20
EXPECTED_L1_K_MAX = 4
EXPECTED_W4_K_MEAN = 2.0


def main() -> int:
    problems: list[str] = []
    print(f"repo module root: {Path(__import__('speech_aware_evidence_acquisition').__file__).parent}")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    print(f"data_root: {root}")
    print(f"carrier_root (asset_dir slurp): {asset_dir(lock, SLURP_LOCK_KEY, root)}")

    # ---- 1. machinery guards + binding-config pin ---------------------------
    print()
    print("=== legality guards (explicitly re-run; they also fire at import time) ===")
    for label, fn in (
        ("assert_never_calls_ontology_miner (pslu_flight, reused verbatim)", assert_never_calls_ontology_miner),
        ("_assert_this_module_never_calls_ontology_miner (pcorrf_flight source)", _assert_this_module_never_calls_ontology_miner),
        ("assert_never_references_forbidden_gold_symbols (AST, guard 2)", assert_never_references_forbidden_gold_symbols),
        ("assert_binding_config_sha256 (arm table / seed / pool / L2b / legality pin)", assert_binding_config_sha256),
    ):
        try:
            fn()
        except Exception as error:  # noqa: BLE001 -- fail-closed
            problems.append(f"GUARD FAILED [{label}]: {type(error).__name__}: {error}")
        else:
            print(f"  OK: {label}")
    print(f"  binding_config_sha256: {binding_config_sha256()}")

    # ---- 2. split identity ---------------------------------------------------
    print()
    manifest = load_pslu_sample_manifest(REPO / SAMPLE_MANIFEST_RELPATH)
    print(f"manifest: n={len(manifest.sample_ids)} seed={manifest.seed}")
    print(f"split_identity_hash (full, from binding JSON): {manifest.split_identity_hash}")
    try:
        assert_split_identity_hash(manifest.split_identity_hash)
    except Exception as error:  # noqa: BLE001 -- fail-closed
        problems.append(f"SPLIT IDENTITY PIN FAILED: {type(error).__name__}: {error}")
    else:
        print("split identity: manifest == machinery EXPECTED_SPLIT_IDENTITY_HASH verbatim -- PASS")
    print(f"  machinery pin: {EXPECTED_SPLIT_IDENTITY_HASH}")
    print(f"arms: machinery PCORRF_ARMS == {list(PCORRF_ARMS)}")

    # ---- 3. roster table + A3 packet -----------------------------------------
    print()
    rosters = load_pslu_rosters(REPO / ROSTER_TABLE_RELPATH)
    print(
        f"rosters: {len(rosters.scenario_rosters)} scenarios, {len(rosters.global_types)} global types, "
        f"{len(rosters.full_roster)} full-roster entries, {len(rosters.derangement)} derangement keys"
    )
    a3 = pslu_supply_packet("A3", scenario=None, rosters=rosters)
    print(f"A3 packet: {len(a3.items)} items, dose n_items={a3.dose.n_items} (prereg: 100-entry roster)")
    if a3.dose.n_items != 100:
        problems.append(f"A3 packet dose n_items {a3.dose.n_items} != 100")
    if len(rosters.full_roster) != 100:
        problems.append(f"full_roster carries {len(rosters.full_roster)} entries, expected 100")

    # ---- 4. devel split resolution -------------------------------------------
    print()
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
    print(f"total audio seconds: {total_audio:.2f} (registration: 182.26), mean {total_audio/len(samples):.2f}")

    # ---- 5. corrective binding: re-derive, hash-check, invariants -------------
    print()
    print("=== corrective binding (REGISTERED supply-content sourcing; zero model calls, zero gold) ===")
    print(f"consumed A0 attempt dir: {consumed_attempt_dir()}")
    reviewed_path = Path(__file__).resolve().parent / "corrective-binding.json"
    if not reviewed_path.is_file():
        problems.append(f"reviewed corrective binding missing: {reviewed_path} (run run_binding.sh first)")
        reviewed_doc_hash = None
        reviewed_binding_hash = None
    else:
        reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
        reviewed_doc_hash = canonical_hash(reviewed)
        reviewed_binding_hash = str(reviewed["binding_hash"])
    table, document = build_binding()
    rebuilt_doc_hash = canonical_hash(document)
    print(f"re-derived tri-derivation binding_hash: {table.binding_hash}")
    print(f"reviewed   tri-derivation binding_hash: {reviewed_binding_hash}")
    print(f"re-derived document_hash: {rebuilt_doc_hash}")
    print(f"reviewed   document_hash: {reviewed_doc_hash}")
    if reviewed_binding_hash is not None and reviewed_binding_hash != table.binding_hash:
        problems.append("TRI-DERIVATION DISAGREEMENT: reviewed binding_hash != re-derived binding_hash")
    if reviewed_doc_hash is not None and reviewed_doc_hash != rebuilt_doc_hash:
        problems.append("corrective binding is not reproducible: reviewed document hash != re-derived hash")
    if reviewed_binding_hash == table.binding_hash and reviewed_doc_hash == rebuilt_doc_hash:
        print("corrective binding reproducibility: PASS (deterministic from consumed A0 + train pool + seed)")

    stats = stats_document(document, rebuilt_doc_hash)
    k_by_arm = arm_k_by_sample(document)
    print(f"train pool: {json.dumps(stats['train_pool'], sort_keys=True)}")
    print(f"A0 emitted (type, filler) slots total: {stats['emitted_slot_total']}")
    for arm in PCORRF_ARMS:
        block = stats["per_arm"][arm]
        print(
            f"  {arm}: K dist {json.dumps(block['k_distribution'], sort_keys=True)} | total "
            f"{block['k_total']} mean {block['k_mean']} max {block['k_max']} | K=0 {block['k_zero_sample_count']}"
        )
    print(f"W2 length-matched to W1 on every sample: {stats['w2_length_matched_to_w1']}")
    print(f"W2 donor breadth: {stats['w2_donor_breadth']} distinct origins over {stats['w2_donor_entry_total']} entries")

    if not stats["w2_length_matched_to_w1"]:
        problems.append(
            f"W2 is not length-matched to W1 on {len(stats['w2_shortfall_sample_ids'])} sample(s) "
            f"{stats['w2_shortfall_sample_ids'][:5]} -- donor pool ran dry"
        )
    w1_block = stats["per_arm"][W1_ARM]
    if w1_block["k_zero_sample_count"] != EXPECTED_L1_K_ZERO_SAMPLES:
        problems.append(
            f"L1 K=0 sample count {w1_block['k_zero_sample_count']} != the registration's own measured "
            f"{EXPECTED_L1_K_ZERO_SAMPLES}"
        )
    if w1_block["k_max"] != EXPECTED_L1_K_MAX:
        problems.append(f"L1 K max {w1_block['k_max']} != the registration's own measured {EXPECTED_L1_K_MAX}")
    w4_mean = stats["per_arm"][W4_ARM]["k_mean"]
    if abs(float(w4_mean) - EXPECTED_W4_K_MEAN) > 1e-9:
        problems.append(f"W4 (L2b) mean K {w4_mean} != the registration's own measured {EXPECTED_W4_K_MEAN}")

    fixed_point_violations: list[str] = []
    dedupe_violations: list[str] = []
    for sample_id, block in document["corrective_sets"].items():
        for entry in block["w2_entries"]:
            if entry["origin_sample_id"] == sample_id:
                fixed_point_violations.append(sample_id)
        l1_keys = {(e["type"], normalize_term(e["filler"])) for e in block["l1_entries"]}
        for entry in block["w4_added_entries"]:
            if (entry["type"], normalize_term(entry["filler"])) in l1_keys:
                dedupe_violations.append(sample_id)
    for label, offenders in (
        ("W2 fixed-point (origin_sample_id == target)", fixed_point_violations),
        ("W4-added entry duplicates an L1 entry", dedupe_violations),
    ):
        if offenders:
            problems.append(f"BINDING VIOLATION -- {label}: {sorted(set(offenders))[:5]}")
        else:
            print(f"binding invariant OK: no sample violates [{label}]")
    l1_origin_ok = all(
        entry["origin_sample_id"] == sample_id
        for sample_id, block in document["corrective_sets"].items()
        for entry in block["l1_entries"]
    )
    print(f"L1 self-percept origin invariant (every entry's origin == its own target): {l1_origin_ok}")
    if not l1_origin_ok:
        problems.append("an L1 corrective entry's origin_sample_id is not its own target sample")

    # Render every arm's packet once, offline, so a rendering defect surfaces
    # here rather than mid-flight. Shapes only -- never printed content.
    print()
    print("=== supply packet rendering dry run (shapes only; content never printed) ===")
    for arm in PCORRF_ARMS:
        n_none = 0
        n_items_total = 0
        for sample in samples:
            packet = pcorrf_supply_packet(
                arm,
                sample.sample_id,
                base_roster_entries=rosters.full_roster,
                corrective_set=table.corrective_sets[sample.sample_id],
            )
            if packet is None:
                n_none += 1
            else:
                n_items_total += packet.dose.n_items
        expected_items = sum(k_by_arm[arm].values()) + (0 if arm == "W3" else 100 * (len(samples) - 0))
        print(
            f"  {arm}: {len(samples)} packets, {n_none} zero-supply (None), "
            f"{n_items_total} rendered items total (expected {expected_items})"
        )
        if n_items_total != expected_items:
            problems.append(f"arm {arm}: rendered item total {n_items_total} != expected {expected_items}")
        if arm == "W3" and n_none != stats["per_arm"][W1_ARM]["k_zero_sample_count"]:
            problems.append(
                f"arm W3: {n_none} zero-supply packets but {stats['per_arm'][W1_ARM]['k_zero_sample_count']} K=0 samples"
            )
        if arm != "W3" and n_none != 0:
            problems.append(f"arm {arm}: {n_none} packets rendered None but the A3 base is always present")

    # ---- 6. legality declarations --------------------------------------------
    print()
    try:
        # Same root the flight itself will pass (the machinery's own unit-suite
        # convention): core.legality's only root-relative lookups are
        # evidence-materialization records, which this probe never declares.
        resolved = assert_pcorrf_legality(root)
    except Exception as error:  # noqa: BLE001 -- fail-closed
        problems.append(f"LEGALITY DECLARATION REFUSED: {type(error).__name__}: {error}")
    else:
        print(f"legality declaration resolves: {resolved}")

    # ---- 7. exposure ledger rows ---------------------------------------------
    print()
    ledger_text = (REPO / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    try:
        assert_ledger_row_consumed(ledger_text, run_experiment_id=CONSUMED_PSLU_RUN_EXPERIMENT_ID)
    except Exception as error:  # noqa: BLE001 -- fail-closed
        problems.append(f"CONSUMED SOURCE ROW CHECK FAILED: {type(error).__name__}: {error}")
    else:
        print(f"consumed source row {CONSUMED_PSLU_RUN_EXPERIMENT_ID}: consumed=yes -- OK")

    rows = _parse_ledger_tables(ledger_text)
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
                f"{row.get('split identity hash')!r} but the plan will carry "
                f"{manifest.split_identity_hash!r}; FrozenCoreGate compares these verbatim"
            )
        if str(row.get("consumed", "")).lower() != "no":
            problems.append(f"exposure row consumed={row.get('consumed')!r}, must be 'no'")
        for cell_name, planned_value, caster in (
            ("calls", DEFAULT_PLANNED_MODEL_CALLS, int),
            ("speech audio seconds", DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS, int),
            ("gpu hours", DEFAULT_PLANNED_GPU_HOURS, float),
        ):
            try:
                registered_value = caster(str(row.get(cell_name, "")).strip())
            except ValueError:
                problems.append(f"ledger cell {cell_name!r} is not numeric: {row.get(cell_name)!r}")
                continue
            if registered_value < caster(planned_value):
                problems.append(
                    f"ledger {cell_name!r} cell registers {registered_value} but the plan declares "
                    f"{planned_value}; FrozenCoreGate refuses when registered < planned"
                )
            else:
                print(f"  budget cell {cell_name!r}: registered {registered_value} >= planned {planned_value} -- OK")

    # ---- 8. plan + registered arithmetic --------------------------------------
    print()
    values = build_values(REPO)
    cfg_hash = config_hash_of(values)
    phash = compute_protocol_hash(cfg_hash, str(values["arm"]), manifest.split_identity_hash)
    print(f"config_hash: {cfg_hash}")
    print(f"protocol_hash (flight, core.config.protocol_hash): {phash}")
    print(f"server_env: {values['server_env']}")
    print(f"server_args: {values['server_args']}")
    print(f"decoding_params: {values['decoding_params']}")
    machinery_plan = build_execution_plan(attempt_id="attempt-preflight-000000")
    print(
        f"machinery build_execution_plan validates: profile={machinery_plan.execution_profile} "
        f"role={machinery_plan.split_role} protocol_hash={machinery_plan.protocol_hash}"
    )
    registered_calls = len(PCORRF_ARMS) * len(samples)
    print(
        f"registered call arithmetic: {len(samples)} x {len(PCORRF_ARMS)} arms = {registered_calls} "
        f"<= plan {DEFAULT_PLANNED_MODEL_CALLS} <= registered ceiling {CEILING_CALLS}"
    )
    if registered_calls > DEFAULT_PLANNED_MODEL_CALLS:
        problems.append("registered call arithmetic exceeds the planned model calls")
    metered_audio = total_audio * len(PCORRF_ARMS)
    print(
        f"audio-seconds arithmetic (METERED): {total_audio:.2f} x {len(PCORRF_ARMS)} arms = "
        f"{metered_audio:.2f} <= plan {DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS} <= ceiling {CEILING_AUDIO_SECONDS}"
    )
    if metered_audio > DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS:
        problems.append("metered audio-seconds estimate exceeds the planned speech audio seconds")
    try:
        assert_within_registered_ceilings(
            calls=registered_calls, audio_seconds=metered_audio, gpu_hours=DEFAULT_PLANNED_GPU_HOURS
        )
    except Exception as error:  # noqa: BLE001 -- fail-closed
        problems.append(f"CEILING REFUSAL: {type(error).__name__}: {error}")
    else:
        print(
            f"registered ceilings OK: calls {registered_calls}<={CEILING_CALLS}, audio "
            f"{metered_audio:.2f}<={CEILING_AUDIO_SECONDS}, gpu {DEFAULT_PLANNED_GPU_HOURS}<={CEILING_GPU_HOURS}"
        )

    # ---- 9. RUN-TOTAL budget feasibility ---------------------------------------
    from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: PLC0415

    store = AttemptStore(attempts_root=root / "attempts")
    prior_calls, prior_audio = store.prior_actual_usage(RUN_ID, exclude_attempt_id=None)
    print()
    print("=== run-total budget feasibility (sibling attempts count) ===")
    print(f"prior durable spend on {RUN_ID}: calls={prior_calls}, audio_seconds={prior_audio:.2f}")
    headroom_calls = DEFAULT_PLANNED_MODEL_CALLS - prior_calls
    headroom_audio = DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS - prior_audio
    print(f"headroom for a FRESH attempt: calls={headroom_calls}, audio_seconds={headroom_audio:.2f}")
    print(f"this flight needs: calls={registered_calls}, metered audio_seconds={metered_audio:.2f}")
    if registered_calls > headroom_calls:
        problems.append(
            f"RUN-TOTAL CALL BUDGET INFEASIBLE: needs {registered_calls}, {headroom_calls} remain "
            f"({prior_calls} already durably spent). Registered ledger ceiling {ledger_calls_cell}. "
            "Resolution is a REGISTRATION act, not an implementer edit."
        )
    else:
        print("call headroom: sufficient for a full fresh attempt -- OK")
    if metered_audio > headroom_audio:
        problems.append(
            f"RUN-TOTAL AUDIO BUDGET INFEASIBLE: needs {metered_audio:.2f}s, {headroom_audio:.2f}s remain"
        )
    else:
        print("audio headroom: sufficient for a full fresh attempt -- OK")

    # ---- 10. no pre-existing run dir -------------------------------------------
    print()
    data_dir = Path(os.environ["SPEECHRL_DATA_DIR"])
    for label, path in (("runs", data_dir / "runs" / RUN_ID), ("attempts", data_dir / "attempts" / RUN_ID)):
        existing = sorted(p.name for p in path.iterdir()) if path.is_dir() else []
        print(f"{label}/{RUN_ID}: {existing if existing else '(absent)'}")
        if existing:
            problems.append(
                f"a P-CORR-F {label} directory already exists with {len(existing)} entry(ies) "
                f"{existing[:3]}; one-shot attempt semantics require an explicit resume decision"
            )

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
