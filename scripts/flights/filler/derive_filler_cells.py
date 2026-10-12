#!/usr/bin/env python3
"""Derive the FILLER family's cells (owner decision 162; decision 58: script-derived registrations).

Two modes, both MODEL-FREE (zero model, server, encoder, embedder, tokenizer, scorer and network
contacts; the data root is read only to hash already-sealed files):

``--base``
    Writes the FILLER BASE: cell ROLL-2's baseline and experiment fragments re-pointed from TRAIN Fold A
    to the whole 1,080-row filler roster (TRAIN Fold B) at ``w_agree`` 0.0 with no ``agreement_source``,
    allowed stage ``check`` only, readiness held, no campaign plan, no ledger row. It is the committed
    source identity the filler roster's own agreement table is built from::

        python scripts/build_slurp_intent_exemplar_agreement.py --experiment slurp-native-stage3-filler-fold-b-base-v1 \\
            --cell slurp-native-stage3-filler-fold-b-base-v1 --vote-store train-exemplars --vote-phase solver \\
            --target-store intent-boundaries --output prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1 \\
            --artifact-id SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FILLER-FOLD-B-V1 ...

``--chunks 1-6``
    For each chunk k writes, from ROLL-2's fragments plus AGREE's agreement pins: the baseline, the
    experiment and the single-cell campaign plan (chunk 1 also its four-row structural smoke); the
    readiness package ``docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-cKK-v1/`` (protocol,
    registered facts with the canonical ``stage3_measurement`` block, generation / FIT plans, the
    per-chunk read recipe, the root-admission DRAFT, the batch-driver queue step, README) and its
    preregistration; and -- with ``--write-ledger`` -- the chunk's DRAFT exposure rows plus the family's
    one model-free preparation row, replace-or-append (re-running never duplicates a row). Every cell is
    HELD with the agreement table as its only preparation requirement; the flip (``filler_flip.sh``)
    appends the decision requirement and mints each cell's own first-phase supply (item E16).

Before writing a chunk it PROVES THE COMPOSED DIFF against ROLL-2 (``filler_family.classify_composed_diff``):
every differing composed path is an agreement pin, a roster pin or run-id / budget / prose bookkeeping, or
the derivation refuses. ``tests/unit/test_filler_family.py`` re-proves it from the committed files.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src SPEECHRL_DATA_DIR=<data> \\
      python scripts/flights/filler/derive_filler_cells.py --chunks 1-6 --study-commit <sha> --write-ledger
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO_ROOT = HERE.parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import filler_family as ff  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

DERIVER = "scripts/flights/filler/derive_filler_cells.py"
LEDGER = "docs/exposure-ledger.md"
DATA_DEFAULT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
BRANCH = "fable/filler"
WORKTREE = "/home/chao/saea-worktrees/fable-filler"

STAGE3_NOTE = (
    "Filler chunks are the registered algorithm-neutral rollout substrate, exactly as cells ROLL-1, ROLL-2 and "
    "ROLL-3 declared it: the grouped Solver, its per-sample custody and its plurality commit, applying NO learned "
    "context and carrying NO credit_assignment or update operator -- hence 'shared-rollout'. The pools they seal "
    "are the rollout substrate of the training-free RL inner loop sealed-credit-system-policy-v1 (owner decision "
    "162), whose credit and update operators run OFFLINE over these sealed bytes; this cell is TRAJECTORY "
    "COLLECTION, not a policy arm, and no verdict attaches to it."
)
FAILURE_POLICY_NOTE = (
    "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, "
    "prompt, knowledge, geometry or cap change. The idle-filler queue HALTS on any STOP and never skips a failed "
    "chunk. This registration pre-authorises no recovery; a root-diagnosed recovery re-registration is a separate "
    "act. A partial manifest is never scored and never read."
)
MODEL_TOOL = (
    "Frozen Qwen3-Omni-30B-A3B-Instruct Q4_K_M decoder-only (no mmproj) at np4 x 24,576, max512, on the resident "
    "session serving-slurp-native-candidate-five-train-a-np4-v1, attached and never spawned or stopped; promoted "
    "EVO-FOLDS-V2 featcache speech packets (the sealed TRAIN Fold B packets, by id); NO native tool authority on "
    "any role; NO deliver_normaliser node (a grouped Solver forbids one); no second answering model, retriever, "
    "judge, embedder, ASR, network beyond loopback and no paid API."
)
INHERITED = (
    "All prior SLURP exposure carried forward unchanged. TRAIN Fold B was already contacted by the EVO-S1 fold "
    "packets (SAEA-SLURP-EVO-FOLD-PACKETS-V2), the one-time closed-list intent flight (SAEA-SLURP-EVO-S1-INTENT-"
    "FOLDS-V2), the EVO-S1 confirmation fold (SAEA-SLURP-EVO-S1-FOLD-B-V2) and the Fold B speech-query encoding "
    "(SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1); this row opens NO new speech identity and no split. The "
    "filler roster is disjoint by its committed receipt from TRAIN Fold A, every knowledge source of the composed "
    "system, DEV-1000, DEV-2000, DEV-2000-ADDED, the devel remainder with its FINAL60 and probe-60 carve-outs, "
    "R01 / R01C, every Stage-3 subset and the whole devel and test enumerations. No gold, reference transcript or "
    "future turn enters runtime."
)


# ---- the prepared artifacts, hashed on the data root ---------------------------------------------
def measure_prepared(data_root: Path, *, agreement: bool) -> dict:
    out = {
        "content_query_sha256": ff.sha_file(data_root / ff.CONTENT_QUERY),
        "content_query_provenance_sha256": ff.sha_file(data_root / ff.CONTENT_QUERY_PROVENANCE),
        "boundary_query_sha256": ff.sha_file(data_root / ff.BOUNDARY_QUERY["relpath"]),
        "fold_b_alias_sha256": ff.sha_file(data_root / ff.FOLD_B_ALIAS["relpath"]),
        "fold_b_encode_receipt_sha256": ff.sha_file(data_root / ff.FOLD_B_ENCODE_RECEIPT["relpath"]),
    }
    if out["boundary_query_sha256"] != ff.BOUNDARY_QUERY["sha256"]:
        raise SystemExit("the Fold B boundary query vectors do not hash to their pin")
    if out["fold_b_alias_sha256"] != ff.FOLD_B_ALIAS["sha256"]:
        raise SystemExit("the Fold B alias receipt does not hash to its pin")
    if out["fold_b_encode_receipt_sha256"] != ff.FOLD_B_ENCODE_RECEIPT["sha256"]:
        raise SystemExit("the Fold B encode receipt does not hash to its pin")
    provenance = json.loads((data_root / ff.CONTENT_QUERY_PROVENANCE).read_text(encoding="utf-8"))
    if provenance["sha256"] != out["content_query_sha256"] or provenance["parent_sha256"] != ff.BOUNDARY_QUERY["sha256"]:
        raise SystemExit("the content derivative's provenance does not bind the file and its parent")
    out["content_query_provenance"] = provenance
    if agreement:
        out["agreement_sha256"] = ff.sha_file(data_root / ff.AGREEMENT)
        out["agreement_receipt_sha256"] = ff.sha_file(data_root / ff.AGREEMENT_RECEIPT)
        receipt = json.loads((data_root / ff.AGREEMENT_RECEIPT).read_text(encoding="utf-8"))
        if receipt["artifact"]["sha256"] != out["agreement_sha256"]:
            raise SystemExit("the agreement receipt does not bind the agreement table")
        if receipt["derived_from"]["cell"] != ff.names(None, base=True)["cell"]:
            raise SystemExit("the agreement table was not built from the FILLER BASE cell")
        out["agreement_receipt"] = receipt
    return out


# ---- fragments ---------------------------------------------------------------------------------
def roster_doc(relpath: str) -> dict:
    return ff.rjson(relpath)


def derive_experiment(n: dict, *, rows: int, caps: dict, roster: dict, roster_relpath: str,
                      requirements: list, stages: list) -> tuple[str, dict]:
    parent = ff.ROLL2["smoke" if n["smoke"] else "arm"]
    raw = ff.rd(f"configs/experiment/{parent['cell']}.json")
    document = ff.replace_exact(json.loads(raw), ff.id_mapping(n))
    ids = [item["sample_id"] for item in roster["items"]]
    cell = document["cells"][0]
    if cell["dataset_fragment"] != ff.DATASET_FRAGMENT or cell["run_id"] != n["run"] or cell["cell_id"] != n["cell"]:
        raise SystemExit("the id mapping did not move the ROLL-2 cell identity")
    cell["allowed_execution_stages"] = stages
    if n["base"]:
        reason = (
            "The FILLER BASE (owner decision 162): NEVER FLOWN. Allowed stage check only; readiness held forever; no "
            "ledger row, no decision receipt, no budget authority. It is the committed source identity of the filler "
            f"roster's own agreement table ({ff.AGREEMENT}, built by {ff.AGREEMENT_BUILDER}) and the roster-move "
            "reference of the chunk cells' composed-diff proof."
        )
    else:
        reason = (
            f"Filler chunk c{n['chunk']:02d}{' four-row smoke' if n['smoke'] else ''} (owner decision {ff.OWNER_DECISION}), "
            f"registered before contact on {ff.FAMILY_DATE} by {DERIVER} from cell ROLL-2's fragments plus cell AGREE's "
            "agreement pins. HELD: root mints the chunk's admission receipt (scripts/flights/filler/filler_mint.py) and "
            "flips with scripts/flights/filler/filler_flip.sh, whose re-pin (scripts/flights/repin_cell.py --set-ready) "
            "appends the decision requirement and mints this cell's OWN first-phase supply under its own run id (item "
            "E16); the agreement-table requirement below is kept beside it (fixed 2026-09-27, relpath identity). "
            "--allow-output-change must never be passed. DESCRIPTIVE: an asset, never an admission cell."
        )
    cell["readiness"] = {"reason": reason, "requirements": requirements, "state": "held"}
    document["date"] = ff.FAMILY_DATE
    document["purpose"] = purpose(n, rows)
    population = {
        "count": rows,
        "dataset_fragment": ff.DATASET_FRAGMENT,
        "decision_population": (
            f"{rows} TRAIN Fold B rows of {roster_relpath} ({roster['roster_id']}), "
            + (f"the first {ff.SMOKE_ROWS} rows of chunk c01 by the parent's order. Structural form proof only: no "
               "score and no read." if n["smoke"] else
               "ten per scenario across 18 scenarios, drawn by seed 20260927 from the whole of TRAIN Fold B "
               f"({ff.FAMILY_ROSTER}); outside TRAIN Fold A, every evaluation roster and every knowledge source.")
        ),
        "roster_receipt": roster_relpath,
        "split_identity_hash": roster["split_identity_hash"],
    }
    document["population"] = population
    document["populations"] = [{"dataset_fragment": ff.DATASET_FRAGMENT, "ids": ids}]
    document["execution_plan"].update({
        "planned_gpu_hours": caps["gpu_hours_fit_inclusive"],
        "planned_model_calls": caps["generation_calls_cap"],
        "planned_speech_audio_seconds": caps["repeated_speech_audio_seconds_cap"],
    })
    document["family_budget"] = {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": caps["fit_endpoint_calls_cap"],
        "generation_calls_cap": caps["generation_calls_cap"],
        "gpu_hours_fit_inclusive": caps["gpu_hours_fit_inclusive"],
        "native_task_contract_calls_cap": 0,
        "official_complete_scoring_jobs": caps["official_complete_scoring_jobs"],
        "repeated_speech_audio_seconds_cap": caps["repeated_speech_audio_seconds_cap"],
    }
    document["generation_budget"] = {
        "cap": caps["generation_calls_cap"],
        "definition": (
            f"{caps['generation_calls_cap']:,} = {rows} rows x 19, where 19 is the grouped-Solver graph's OWN ceiling at "
            "samples 5 as rails.native_episode_config.load_native_episode_config resolves it: perception.max_iterations "
            "+ (max_revisions + 1) x (solver.max_iterations x solver.samples + reviewer.max_iterations + "
            "planner.max_iterations) = 1 + 2 x (1 x 5 + 3 + 1) = 19 -- cell ROLL-2's arithmetic, unchanged by the "
            "agreement pins (they move ranking, not the role graph). The target is ROLL-2's MEASURED rate, 8,996 "
            f"contacts over 1,080 rows (8.33 per row), so about {caps['expected_contacts']:,} contacts; a ceiling is a "
            "BOUND, never a target, and budgets are run-cumulative across every attempt of a run id."
        ),
        "target": caps["expected_contacts"],
    }
    document["failure_policy"] = FAILURE_POLICY_NOTE
    algorithm = document["stage3_algorithm"]
    if n["base"]:
        document["stage3_algorithm"] = {
            "id": "none",
            "note": (
                "The FILLER BASE carries NO training-free RL operator: it is never flown, and exists only as the "
                "committed source identity of a model-free agreement table and as a diff reference."
            ),
            "operators_used": [],
        }
    else:
        if algorithm.get("id") != "shared-rollout" or algorithm.get("operators_used") != ["rollout"]:
            raise SystemExit("ROLL-2's stage3_algorithm is not shared-rollout / rollout")
        algorithm["note"] = STAGE3_NOTE
    leftover = [s for s in ff._strings(document) if "fold-a" in s.lower()]
    if leftover:
        raise SystemExit(f"a Fold A identifier survived the experiment derivation: {leftover[:3]}")
    return raw, document


def purpose(n: dict, rows: int) -> str:
    if n["base"]:
        return ff.what_this_is(n, rows)
    text = (
        f"Filler chunk c{n['chunk']:02d} (owner decision {ff.OWNER_DECISION}): seal a {rows}-row x 5-sample rollout pool of "
        "the current best SLURP system on TRAIN Fold B rows, flown ONLY when the GPU would otherwise idle (the "
        "idle-filler queue: no flight running, no main-line chain ready, the np4 session resident and healthy). The "
        "pool is the rollout substrate of the training-free RL inner loop (sealed-credit-system-policy-v1), read "
        "OFFLINE at zero further GPU cost. DESCRIPTIVE by construction: no comparator, no gate, no admission claim, "
        "no superiority, transfer, generalisation or confirmatory statement. Development numbers only (owner "
        "decisions 28 and 86); never a test claim."
    )
    if n["smoke"]:
        text = (
            "Four-row structural form smoke of the filler family's composed form (ROLL-2's grouped Solver plus AGREE's "
            "agreement pins), flown before chunk c01's arm: five custodied Solver samples per row, the plurality-commit "
            "replay, the agreement table loading and the boundary channel still delivering eight entries, zero native "
            "task-contract calls, every request fitting. Scored by no one and read by no one. " + text
        )
    return text


def write_fragments(n: dict, *, prepared: dict, agreement: bool, stages: list, requirements: list,
                    roster_relpath: str) -> dict:
    roster = roster_doc(roster_relpath)
    rows = len(roster["items"])
    audio = float(roster["audio_seconds_total"])
    caps = ff.budgets(rows, audio, smoke=n["smoke"])
    roster_sha = ff.sha_file(roster_relpath)
    raw_b, baseline = ff.derive_baseline(n, prepared=prepared, rows=rows, caps=caps, agreement=agreement,
                                         roster_relpath=roster_relpath, roster_sha=roster_sha)
    raw_e, experiment = derive_experiment(n, rows=rows, caps=caps, roster=roster, roster_relpath=roster_relpath,
                                          requirements=requirements, stages=stages)
    ff.wr(f"configs/baseline/{n['baseline']}.json", ff.dump_like(raw_b, baseline))
    ff.wr(f"configs/experiment/{n['cell']}.json", ff.dump_like(raw_e, experiment))
    return {"rows": rows, "caps": caps, "roster": roster, "roster_sha": roster_sha}


# ---- composed-diff proof -------------------------------------------------------------------------
def composed(cell_id: str):
    document = ff.rjson(f"configs/experiment/{cell_id}.json")
    cell = document["cells"][0]
    return compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], cell_id), document


def prove_diff(n: dict, *, agreement: bool, prepared: dict, roster_relpath: str, roster_sha: str) -> dict:
    parent_cell = ff.ROLL2["smoke" if n["smoke"] else "arm"]["cell"]
    mine, _doc = composed(n["cell"])
    parent, _pdoc = composed(parent_cell)
    dataset_keys = set(ff.rjson(f"configs/dataset/{ff.DATASET_FRAGMENT}.json"))
    diff = ff.classify_composed_diff(parent.values, mine.values, dataset_keys)
    if n["base"]:
        # the never-flown base declares the 'none' label instead of ROLL-2's shared-rollout
        moved_label = [p for p in diff["other"] if p.startswith("stage3_algorithm.")]
        diff["bookkeeping"] += moved_label
        diff["other"] = [p for p in diff["other"] if p not in moved_label]
    if diff["other"]:
        raise SystemExit(f"{n['cell']}: composed config differs from ROLL-2 beyond the allowed pins: {diff['other']}")
    if bool(diff["agreement"]) != agreement:
        raise SystemExit(f"{n['cell']}: agreement pins present={bool(diff['agreement'])}, expected {agreement}")
    expected = ff.expected_receipts(parent.values["preparation_source_receipts"], roster_relpath=roster_relpath,
                                    roster_sha=roster_sha, prepared=prepared, agreement=agreement)
    if mine.values["preparation_source_receipts"] != expected:
        raise SystemExit(f"{n['cell']}: preparation_source_receipts is not ROLL-2's with exactly the filler edits")
    p_mine = ff.get_path(mine.values, ff.PERCEPTION)
    p_parent = ff.get_path(parent.values, ff.PERCEPTION)
    moved = {k for k in set(p_mine) | set(p_parent) if p_mine.get(k) != p_parent.get(k)}
    allowed = {"query_source", "k", "rank_weights", "agreement_source"} if agreement else {"query_source"}
    if not moved <= allowed:
        raise SystemExit(f"{n['cell']}: the boundary perception spec moved beyond {sorted(allowed)}: {sorted(moved)}")
    if agreement:
        agree, _adoc = composed(ff.AGREE_ARM)
        p_agree = ff.get_path(agree.values, ff.PERCEPTION)
        for key in ("k", "rank_weights", "fuse_coverage", "rank_policy", "tau", "fuse_policy", "facet_source"):
            if p_mine[key] != p_agree[key]:
                raise SystemExit(f"{n['cell']}: boundary {key} is not AGREE's pin")
        if p_mine["agreement_source"]["kind"] != p_agree["agreement_source"]["kind"]:
            raise SystemExit(f"{n['cell']}: agreement_source kind is not AGREE's")
    s_mine = ff.get_path(mine.values, ff.SOLVER)
    s_parent = ff.get_path(parent.values, ff.SOLVER)
    if {k: v for k, v in s_mine.items() if k != "query_source"} != {k: v for k, v in s_parent.items() if k != "query_source"}:
        raise SystemExit(f"{n['cell']}: the Solver exemplar spec moved beyond its query_source")
    return {
        "against": parent_cell,
        "agreement_pins": diff["agreement"],
        "roster_pins": [p for p in diff["roster"] if p.split(".", 1)[0] not in dataset_keys],
        "dataset_fragment_keys_moved_with_the_roster": sorted({p.split(".", 1)[0] for p in diff["roster"]} & dataset_keys),
        "bookkeeping": diff["bookkeeping"],
        "other": diff["other"],
        "rule": (
            "every composed path that differs from cell ROLL-2's is an AGREE agreement pin (perception k, "
            "rank_weights.w_agree, agreement_source), a roster pin (the two query_source pins, the population, the "
            "preparation_source_receipts edits and the TRAIN Fold B dataset view) or run-id / budget / prose "
            "bookkeeping; the boundary k / rank_weights / fuse / rank_policy / facet_source equal cell AGREE's; the "
            "Solver exemplar spec moves only its query file; anything else refuses"
        ),
        "composed_config_hash": mine.config_hash,
        "parent_composed_config_hash": parent.config_hash,
    }


# ---- package -------------------------------------------------------------------------------------
def measurement_blocks(cells: list[dict]) -> dict:
    out = {}
    for c in cells:
        n, rows = c["n"], c["rows"]
        if n["smoke"]:
            out[n["run"]] = {
                "claims_benefit": False,
                "expected_effect_pp": 0.0,
                "measurement_design": "form-proof",
                "note": (
                    "The four-row structural smoke of the filler family's composed form proves FORM and nothing else "
                    "(five custodied Solver samples per row, the plurality-commit replay, the agreement table loading, "
                    "zero native task-contract calls, every request fitting). Scored by no one and read by no one; "
                    "under the measurement instrument's rule 5 four rows can never be evidence of benefit."
                ),
                "primary_metric": "slu_f1",
                "rows": rows,
            }
        else:
            out[n["run"]] = {
                "claims_benefit": False,
                "expected_effect_pp": 0.0,
                "measurement_design": "offline-sealed-pool",
                "note": (
                    f"Filler chunk c{n['chunk']:02d} makes no effectiveness claim of its own: it seals a {rows}-row x "
                    "5-sample pool on TRAIN Fold B so that credit, selection, commit and verification rules of the "
                    "training-free RL inner loop can be computed OFFLINE over sealed bytes. It is a batch under the "
                    "instrument's 200-row MIN_BENEFIT_ROWS, so it is descriptive by size as well as by design; any "
                    "benefit claim belongs to a later read over the pooled chunks, which declares its own block."
                ),
                "primary_metric": "slu_f1",
                "rows": rows,
            }
    return out


def write_package(n_arm: dict, cells: list[dict], *, prepared: dict, study_commit: str, registered_at: str) -> dict:
    """The readiness package of one chunk. ``cells`` is [smoke?, arm] with their composed identities."""

    rd_ = n_arm["readiness_dir"]
    k = n_arm["chunk"]
    arm = cells[-1]
    smoke = cells[0] if len(cells) == 2 else None
    run_ids = [n_arm["run"], n_arm["fit_run"]] + ([smoke["n"]["run"], smoke["n"]["fit_run"]] if smoke else [])
    measurement = measurement_blocks(cells)
    agreement_receipt = prepared["agreement_receipt"]

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the CANONICAL stage3_measurement block "
            "scripts/checks/stage3_effect_floor_check.py resolves (repeated in the preregistration fence; this copy "
            "has precedence)."
        ),
        "registered_at_utc": registered_at,
        "study_commit_at_registration": study_commit,
        "owner_decision": ff.OWNER_DECISION,
        "chunk": k,
        "stage3_measurement": measurement,
        "roster": {
            "family": {"relpath": ff.FAMILY_ROSTER, "sha256": ff.sha_file(ff.FAMILY_ROSTER), "roster_id": ff.FAMILY_ROSTER_ID},
            "chunk": {"relpath": n_arm["roster"], "sha256": arm["roster_sha"], "roster_id": n_arm["roster_id"],
                      "rows": arm["rows"], "split_identity_hash": arm["roster"]["split_identity_hash"],
                      "audio_seconds_total": arm["roster"]["audio_seconds_total"],
                      "per_stratum": arm["roster"]["per_stratum"]},
            **({"smoke": {"relpath": smoke["n"]["roster"], "sha256": smoke["roster_sha"], "rows": smoke["rows"],
                          "split_identity_hash": smoke["roster"]["split_identity_hash"]}} if smoke else {}),
            "why_train_fold_b": (
                "the exemplar pool of the current best system is every TRAIN utterance except Fold A and Fold B, and "
                "the runner refuses a query row that is a knowledge source; the family roster receipt proves the "
                "admissible universe is exactly TRAIN Fold B and its disjointness from every evaluation roster."
            ),
        },
        "prepared_artifacts": {
            "boundary_query": {**ff.BOUNDARY_QUERY, "alias_receipt": ff.FOLD_B_ALIAS, "encode_receipt": ff.FOLD_B_ENCODE_RECEIPT},
            "content_query": {"relpath": ff.CONTENT_QUERY, "sha256": prepared["content_query_sha256"],
                              "provenance": {"relpath": ff.CONTENT_QUERY_PROVENANCE,
                                             "sha256": prepared["content_query_provenance_sha256"]},
                              "builder": ff.CONTENT_BUILDER, "ledger_row": ff.PREPARE_ROW,
                              "byte_identity_cross_check": (
                                  "the same transform over the same parent reproduces the independently built "
                                  "vectors/slurp-system-update-fold-b-v1/query-vectors-speech-content-v1.jsonl byte "
                                  "for byte (sha256 573a8a37a63d790d6b849c11676b9463de28c92eeb92ab3e99177181a947c67f)")},
            "agreement_table": {
                "relpath": ff.AGREEMENT, "sha256": prepared["agreement_sha256"],
                "receipt": {"relpath": ff.AGREEMENT_RECEIPT, "sha256": prepared["agreement_receipt_sha256"]},
                "builder": ff.AGREEMENT_BUILDER, "builder_sha256": agreement_receipt["builder_sha256"],
                "source_cell": agreement_receipt["derived_from"]["cell"],
                "source_split_identity_hash": agreement_receipt["derived_from"]["split_identity_hash"],
                "vote_snapshot_sha256": agreement_receipt["derived_from"]["vote_snapshot_sha256"],
                "target_snapshot_sha256": agreement_receipt["derived_from"]["target_snapshot_sha256"],
                "measured": agreement_receipt["measured"],
                "contacts": agreement_receipt["contacts"],
                "ledger_row": ff.PREPARE_ROW,
                "why_its_own_table": (
                    "AGREE's table (prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1) is keyed by TRAIN Fold A "
                    "sample ids and is self-excluded for them; a Fold B row has no line in it. The filler table is "
                    "the same builder over the same vote store, vote spec and target store, formed from the FILLER "
                    "BASE cell, whose only difference from the flown chunk cells in the vote channel is none."
                ),
            },
        },
        "composed_diff_against_roll2": {c["n"]["run"]: c["diff"] for c in cells},
        "budgets": {c["n"]["run"]: c["caps"] for c in cells},
        "expected_spend_basis": (
            "cell ROLL-2's sealed arm on the same form: 8,996 contacts for 1,080 rows over 8,558 s of campaign wall "
            "(batch-status arm-start 2026-09-26T16:00:01Z, arm-exit 18:22:39Z), i.e. 8.33 contacts and 7.92 s per row "
            "at np4. The agreement pins add +1.4 prompt tokens per row (AGREE's measured cost) and no contact."
        ),
    }
    facts_sha = ff.wjson(f"{rd_}/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "registered_at_utc": registered_at,
        "registration_base_commit": study_commit,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_ROOT_ADMISSION_AND_FLIP",
        "authority": (
            f"owner decision {ff.OWNER_DECISION} ({ff.OWNER_DECISIONS}): the standing rollout FILLER family; owner "
            "decision 161 (the agreement term retained into COMP-1, so it is part of the current best system); owner "
            "decisions 77 (GPU flights only through the batch driver scheduled task), 101 (the Stage-3 algorithm "
            f"label), 28 / 86 (development numbers only); the measurement instrument {ff.INSTRUMENT}."
        ),
        "the_form": (
            "cell ROLL-2's grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality commit at "
            "min_support 3 / similarity 0.8, program phase-native-candidates-review-revise-samples5-v1 at max_contacts "
            "19, no deliver_normaliser) composed with cell AGREE's agreement pins (intent-boundary Perception: recall "
            "k 60, w_agree 1.0, agreement_source = this roster's own self-excluded exemplar-intent table; fuse_coverage "
            "8-1-8 unchanged). Every other key -- stores, releases, snapshots, prompts, role graph, scorers, geometry, "
            "session -- is ROLL-2's, byte for byte (the composed-diff proof in registered-facts-v1.json)."
        ),
        "what_moved": {
            "roster": f"TRAIN Fold A 1,080 -> {n_arm['roster_id']} ({arm['rows']} TRAIN Fold B rows)",
            "roster_bound_pins": [ff.BOUNDARY_QUERY["relpath"], ff.CONTENT_QUERY, ff.FOLD_B_ALIAS["relpath"]],
            "agreement_pins": ["perception.k 8 -> 60", "perception.rank_weights.w_agree 0.0 -> 1.0",
                               f"perception.agreement_source -> {ff.AGREEMENT}"],
        },
        "cells": {c["n"]["run"]: {"cell": c["n"]["cell"], "composed_config_hash": c["identity"]["config_hash"],
                                  "protocol_hash": c["identity"]["protocol_hash"],
                                  "split_identity_hash": c["roster"]["split_identity_hash"], "rows": c["rows"]}
                  for c in cells},
        "run_ids": run_ids,
        "execution_profile": "bounded-discovery-probe",
        "execution_route": (
            f"core.flight.cli campaign over {n_arm['campaign']} (one cell), queued ONLY by the idle-filler queue "
            "scripts/flights/filler/filler_queue.sh through scripts/flights/filler/batch_chain_filler.sh and the "
            "SAEA-Batch-Driver path (decision 77)"
            + ("; the four-row smoke flies first through core.flight.cli worker under its own lease." if smoke else ".")
        ),
        "decision_rule": {
            "rule": "DESCRIPTIVE, structural acceptance only: a clean seal, every row delivered, exactly five custodied Solver samples per row with the five registered seeds at temperature 0.7, the plurality-commit replay reproducing the delivered answer, zero native task-contract calls.",
            "no_gate_number": "No threshold is pre-registered on any number this cell produces.",
        },
        "measurement_design": measurement,
        "claim_boundary": "DESCRIPTIVE. An asset, never an admission cell: no comparison, no gate, no superiority, transfer, generalisation, component-causal or confirmatory statement. Development numbers only (owner decisions 28 and 86); never a test claim.",
        "accounting": {c["n"]["run"]: c["caps"] for c in cells},
        "prohibited": [
            "paper-scale-confirmatory profile", "any test-split or DEV contact", "paid API spend",
            "transcript tokens anywhere", "--allow-output-change at the flip", "coordinate_fit (double-charges the FIT rows)",
            "a second recovery re-registration", "flying while a main-line chain is ready",
        ],
    }
    protocol_sha = ff.wjson(f"{rd_}/protocol-registered-v1.json", protocol)

    plan_shas = {}
    for c in cells:
        n = c["n"]
        for kind in ("generation", "fit"):
            generation = kind == "generation"
            prefix = n["plan_prefix"] if generation else n["fit_plan_prefix"]
            doc = {
                "schema": f"saea-registered-{kind}-plan-v1",
                "plan_kind": kind,
                "cell": n["cell"],
                "experiment": n["cell"],
                "composed_config_hash": c["identity"]["config_hash"],
                "execution_plan": {
                    "attempt_id": n["gen_attempt"] if generation else n["fit_attempt"],
                    "carrier_lock_key": "slurp",
                    "execution_profile": "bounded-discovery-probe",
                    "planned_gpu_hours": c["caps"]["gpu_hours_fit_inclusive"],
                    "planned_model_calls": c["caps"]["generation_calls_cap"] if generation else c["caps"]["fit_endpoint_calls_cap"],
                    "planned_speech_audio_seconds": c["caps"]["repeated_speech_audio_seconds_cap"],
                    "protocol_hash": c["identity"]["protocol_hash"],
                    "run_id": n["run"] if generation else n["fit_run"],
                    "schema": "saea-execution-plan-v1",
                    "split_identity_hash": c["roster"]["split_identity_hash"],
                    "split_role": "discovery",
                    "study": "speech-aware-evidence-acquisition",
                },
                "execution_route": protocol["execution_route"] if generation else (
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures "
                    "request envelopes only and produces no generation. coordinate_fit must NOT be run."
                ),
                "expected_session_id": ff.SESSION,
                "family_budget": {kk: c["caps"][kk] for kk in (
                    "generation_calls_cap", "fit_endpoint_calls_cap", "native_task_contract_calls_cap",
                    "repeated_speech_audio_seconds_cap", "gpu_hours_fit_inclusive", "official_complete_scoring_jobs")},
                "prepared_phase_supply": {
                    "note": "NONE committed: the flip mints this cell's OWN first-phase supply under its own run id (item E16).",
                    "relpath": f"prepared/{n['run']}/phase-supply-v1.json",
                    "sha256": "MINTED_AT_THE_FLIP",
                },
                "protocol_document": {"relpath": f"{rd_}/protocol-registered-v1.json", "sha256": protocol_sha},
                "purpose": purpose(n, c["rows"]),
                "quality_read_gate": "No read before the complete sealed manifest with exactly five custodied solver_group samples per row exists; a partial manifest is never read; a failed smoke stops the arm.",
                "registered_at_utc": registered_at,
                "registration_base_commit": study_commit,
                "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {WORKTREE}, branch {BRANCH}",
                "status": "REGISTERED_BEFORE_CONTACT_AWAITING_ROOT_ADMISSION_AND_FLIP",
                "unused_budget_is_not_attempt_authority": True,
            }
            plan_shas[(n["run"], kind)] = ff.wjson(f"{rd_}/{prefix}-plan-registered-v1.json", doc)

    recipe = {
        "schema": "saea-slurp-sealed-pool-recipe-v1",
        "recipe_id": f"slurp-stage3-{ff.chunk_base(k)}-sealed-pool-v1",
        "read_run_id": n_arm["read_id"],
        "registered_at_utc": registered_at,
        "run_ids": {"arm": n_arm["run"], "attempt": n_arm["gen_attempt"]},
        "roster": {"relpath": n_arm["roster"], "sha256": arm["roster_sha"], "rows": arm["rows"],
                   "split_identity_hash": arm["roster"]["split_identity_hash"]},
        "authority": (
            "cell ROLL-3's sealed-pool recipe (docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1/"
            "analysis-recipe-v1.json, scripts/flights/roll3/roll3_pool_read.sh, scripts/analysis/stage3_pool_spread_read.py) "
            "with TRAIN gold, exactly as cell ROLL-2's read scored TRAIN Fold A."
        ),
        "stages": {
            "1_render": "scripts/analysis/stage3_rollout_score.py --stage render: one outputs COPY per Solver sample index (0..4). Reads no gold.",
            "2_score": f"scripts/analysis/stage3_rollout_score.py --stage score --scorer-id {ff.TRAIN_SCORER}: each copy scored ONCE through the registered TRAIN-gold sibling scorer (the devel scorer refuses a TRAIN prediction). Never core.scoring_batch.",
            "3_pairs": "scripts/analysis/stage3_rollout_score.py --stage pairs: per-row best / worst and the sealed delivered score.",
            "4_spread": (
                "scripts/analysis/stage3_pool_spread_read.py --cluster-key utterance_id --channel-key headset --seed 20260915 "
                f"--draws 10000 --expected-seeds {ff.READ_SEEDS} --expected-temperature 0.7 --sealed-scorer-id "
                f"{ff.SEALED_TRAIN_SCORER}: the within-flight spread, the oracle best-of-5 ceiling (an UPPER BOUND) beside "
                "the sealed delivered score, the row accounting."
            ),
        },
        "registration_guard": (
            f"stages 2-4 run only after the READ row {n_arm['read_id']} is a countersigned (not DRAFT) contract-table row "
            "of docs/exposure-ledger.md, registered after the seal and before any number is read; "
            f"scripts/flights/filler/filler_pool_read.sh {k} refuses otherwise and prints the row to register."
        ),
        "contacts": {"model": 0, "server": 0, "encoder": 0, "tokenizer": 0, "scorer": 5},
        "claim_boundary": "DESCRIPTIVE: per-sample official SLU-F1 and intent accuracy (owner decisions 133 and 137), the within-flight spread and the oracle ceiling as an UPPER BOUND. No admission, no gate, never a test claim.",
        "output": {"analysis_root": f"analysis/{n_arm['read_id']}"},
        "privacy": "No utterance text, gold label, transcript or model output is printed or persisted by the summary files: ids, sample indices, scores, flags and hashes only.",
        "read_driver": "scripts/flights/filler/filler_pool_read.sh",
    }
    recipe_sha = ff.wjson(f"{rd_}/analysis-recipe-v1.json", recipe)

    step = {
        "order": 1, "short": f"filler-c{k:02d}", "kind": "cell",
        "experiment": n_arm["cell"], "cell": n_arm["cell"],
        "smoke_experiment": smoke["n"]["cell"] if smoke else None,
        "smoke_cell": smoke["n"]["cell"] if smoke else None,
        "smoke_run_id": smoke["n"]["run"] if smoke else None,
        "smoke_attempt_id": smoke["n"]["gen_attempt"] if smoke else None,
        "campaign_plan": n_arm["campaign"],
        "run_id": n_arm["run"], "fit_run_id": n_arm["fit_run"], "gen_attempt_id": n_arm["gen_attempt"],
        "expected_rows": arm["rows"], "contacts_per_row": 9, "ceiling_per_row": ff.CONTACTS_PER_ROW_CEILING,
        "notool": True, "owner": f"root-{n_arm['cell']}",
    }
    ff.wjson(f"{rd_}/queue-step-v1.json", step)

    draft = {
        "_draft_note": (
            "A DRAFT written by the registration agent for root to mint on the data root with "
            "scripts/flights/filler/filler_mint.py --chunks <spec>, which sets status 'decided', stamps recorded_at_utc, "
            "re-hashes every antecedent path at mint time and refuses to overwrite. It authorises nothing while its "
            "status is not 'decided' (core.flight.campaign.declared_readiness refuses it)."
        ),
        "schema": "saea-campaign-decision-v1",
        "decision_id": n_arm["decision_id"],
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": None,
        "eligible_run_ids": run_ids,
        "cell_kind": "Stage-3 rollout FILLER chunk (shared-rollout). DESCRIPTIVE asset, never an admission cell.",
        "decision": (
            f"Fly filler chunk c{k:02d} when the idle-filler queue finds the card idle: a sealed five-sample pool of the "
            f"current best SLURP system on {arm['rows']} TRAIN Fold B rows"
            + (", after its four-row structural smoke" if smoke else "") + "."
        ),
        "authorization_basis": (
            f"owner decision {ff.OWNER_DECISION} (a standing, pre-approved filler family, minted ahead in a batch; the "
            "queue flies a chunk only when no main-line chain is ready and no flight is running) and owner decision 161 "
            "(the agreement term is part of the current best system)."
        ),
        "antecedents": {
            "owner_decisions": {"path": ff.OWNER_DECISIONS, "sha256": ff.sha_file(ff.OWNER_DECISIONS)},
            "preregistration": {"path": n_arm["preregistration"], "sha256": None},
            "readiness_readme": {"path": f"{rd_}/README.md", "sha256": None},
            "protocol": {"path": f"{rd_}/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": f"{rd_}/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": f"{rd_}/analysis-recipe-v1.json", "sha256": recipe_sha},
            "chunk_roster": {"path": n_arm["roster"], "sha256": arm["roster_sha"]},
            "family_roster": {"path": ff.FAMILY_ROSTER, "sha256": ff.sha_file(ff.FAMILY_ROSTER)},
            "config_proof": {"path": "tests/unit/test_filler_family.py", "sha256": None},
            "registration_base_commit": study_commit,
        },
        "budget": {
            **{c["n"]["run"]: {kk: c["caps"][kk] for kk in ("generation_calls_cap", "fit_endpoint_calls_cap",
                                                          "repeated_speech_audio_seconds_cap", "gpu_hours_fit_inclusive",
                                                          "official_complete_scoring_jobs")} for c in cells},
            "paid_api_calls": 0,
        },
    }
    ff.wjson(f"{rd_}/root-admission-draft-v1.json", draft)

    readme = f"""# Filler chunk c{k:02d} -- sealed five-sample pool of the current best SLURP system on {arm['rows']} TRAIN Fold B rows

Registered before contact {registered_at[:10]} at study commit `{study_commit}` by `{DERIVER}`; every cell **held**.
Owner decision {ff.OWNER_DECISION}: a standing filler family flown ONLY when the GPU would otherwise idle. DESCRIPTIVE:
an asset, never an admission cell. Family note: `{ff.FAMILY_DIR}/README.md`.

| file | what it holds |
|---|---|
| `../{Path(n_arm['preregistration']).name}` | the preregistration, with the `stage3_measurement` fence |
| `protocol-registered-v1.json` | identities, hashes, budgets, claim boundary |
| `registered-facts-v1.json` | the canonical `stage3_measurement` block, the roster, the prepared artifacts, the composed diff against ROLL-2 |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's ExecutionPlan and FIT spend identity |
{'| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke (chunk c01 only) |' + chr(10) if smoke else ''}| `analysis-recipe-v1.json` | the sealed-pool read (ROLL-3's recipe against TRAIN gold) |
| `root-admission-draft-v1.json` | the DRAFT receipt root mints with `scripts/flights/filler/filler_mint.py` |
| `queue-step-v1.json` | the batch-driver step `scripts/flights/filler/batch_chain_filler.sh {k}` writes |

**Numbers.** Arm: {arm['rows']} rows, ceiling 19 per row, generation cap {arm['caps']['generation_calls_cap']:,}, FIT cap
{arm['caps']['fit_endpoint_calls_cap']:,}, repeated speech {arm['caps']['repeated_speech_audio_seconds_cap']:,} s, GPU-hour cap
{arm['caps']['gpu_hours_fit_inclusive']}, one official complete score. Expected about {arm['caps']['expected_contacts']:,} contacts
and about {arm['caps']['expected_wall_minutes']} GPU-minutes at ROLL-2's measured rate.{(' Smoke: ' + str(smoke['rows']) + ' rows, ' + str(smoke['caps']['generation_calls_cap']) + ' / ' + str(smoke['caps']['fit_endpoint_calls_cap']) + ' / ' + str(smoke['caps']['repeated_speech_audio_seconds_cap']) + ' s / 1.0 GPU-h, no score.') if smoke else ''}

**Flip and flight.** `filler_mint.py --chunks {k}` (root) -> `filler_flip.sh {k}` (root; loop form, one HEAD) ->
the idle-filler queue launches `batch_chain_filler.sh {k}` when the card is idle. `--allow-output-change` must never
be passed. Read: `filler_pool_read.sh {k}` after the seal and after the READ row `{n_arm['read_id']}` is countersigned.
"""
    ff.wr(f"{rd_}/README.md", readme)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, sort_keys=True)
    ids_list = ", ".join(run_ids)
    prereg = f"""# Preregistration -- filler chunk c{k:02d} (owner decision {ff.OWNER_DECISION})

Registered before contact {registered_at[:10]} at study commit `{study_commit}`. Package `{rd_}/`.

## What flies

The current best SLURP system -- the locked PLAN plan plus the agreement term retained into COMP-1 (owner decision
161: w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, fuse 8-1-8) -- in cell ROLL-2's
grouped-Solver form (samples 5, temperature 0.7, seed_offset 0, plurality commit at min_support 3), on the {arm['rows']}
TRAIN Fold B rows of `{n_arm['roster']}` (split identity `{arm['roster']['split_identity_hash']}`).{(' Chunk c01 first flies a four-row structural smoke on `' + smoke['n']['roster'] + '`.') if smoke else ''}
Run ids: {ids_list}.

## Composed identity

{chr(10).join('- `' + c['n']['cell'] + '`: composed config `' + c['identity']['config_hash'] + '`, protocol hash `' + c['identity']['protocol_hash'] + '`' for c in cells)}

Every composed path that differs from cell ROLL-2 is an agreement pin, a roster pin or run-id / budget / prose
bookkeeping (`registered-facts-v1.json`, `composed_diff_against_roll2`; re-proved by `tests/unit/test_filler_family.py`).

## Measurement declaration

DESCRIPTIVE by construction. `registered-facts-v1.json` carries the canonical block; repeated here:

```json
{fence}
```

## Budgets and stops

Ceilings are BOUNDS, never targets, and run-cumulative across attempts: {'; '.join(c['n']['run'] + ' generation ' + str(c['caps']['generation_calls_cap']) + ', FIT ' + str(c['caps']['fit_endpoint_calls_cap']) + ', speech ' + str(c['caps']['repeated_speech_audio_seconds_cap']) + ' s, GPU ' + str(c['caps']['gpu_hours_fit_inclusive']) + ' h' for c in cells)}.
Stop and preserve on the first failure; the idle-filler queue HALTS on a STOP and never skips a failed chunk. No
paper-scale profile, no test-split or DEV contact, no comparator flight, no admission entry, no transcript tokens.

## Read

`analysis-recipe-v1.json` via `scripts/flights/filler/filler_pool_read.sh {k}`, registered as `{n_arm['read_id']}`
after the seal and before any number is read. TRAIN gold (`{ff.TRAIN_SCORER}`); development numbers only.
"""
    ff.wr(n_arm["preregistration"], prereg)
    return {"plan_shas": plan_shas, "protocol_sha": protocol_sha, "facts_sha": facts_sha, "recipe_sha": recipe_sha,
            "run_ids": run_ids}


# ---- ledger ----------------------------------------------------------------------------------------
LEDGER_HEADER = (
    "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
    "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
)


def _row(cells: list[str]) -> str:
    for cell in cells:
        if "|" in cell:
            raise SystemExit("a literal '|' in a ledger cell")
    return "| " + " | ".join(cells) + " |"


def ledger_rows(n_arm: dict, cells: list[dict], pkg: dict, *, study_commit: str) -> dict:
    rows = {}
    k = n_arm["chunk"]
    for c in cells:
        n = c["n"]
        for kind in ("generation", "fit"):
            generation = kind == "generation"
            prefix = n["plan_prefix"] if generation else n["fit_plan_prefix"]
            run = n["run"] if generation else n["fit_run"]
            attempt = n["gen_attempt"] if generation else n["fit_attempt"]
            label = f"filler chunk c{k:02d}" + (" four-row smoke" if n["smoke"] else "")
            scope = (
                (f"The rollout FILLER family (owner decision {ff.OWNER_DECISION}), {label}: a sealed five-sample pool of the "
                 "current best SLURP system (locked PLAN plus the agreement term, owner decision 161) in cell ROLL-2's "
                 f"grouped-Solver form on {c['rows']} TRAIN Fold B rows, flown only when the GPU would otherwise idle. "
                 "DESCRIPTIVE asset, never an admission cell." + (" Structural form proof only." if n["smoke"] else ""))
                if generation else
                f"FIT spend identity of {label} (same population, stores and form). Never flown as a generation cell."
            )
            notes = (
                f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {ff.FAMILY_DATE} at study commit "
                f"{study_commit} by the filler registration agent (worktree {WORKTREE}, branch {BRANCH}); this "
                f"registration performs no contact and authorises none. Plan SHA256 {pkg['plan_shas'][(n['run'], kind)]}; "
                f"attempt {attempt}. Protocol hash {c['identity']['protocol_hash']}; composed config "
                f"{c['identity']['config_hash']}; expected session {ff.SESSION} (attach only, never spawn or stop). "
                f"READINESS HELD: root mints {n_arm['decision_relpath']} (decision id {n_arm['decision_id']}) with "
                f"scripts/flights/filler/filler_mint.py (eligible run ids {', '.join(pkg['run_ids'])}) and flips with "
                "scripts/flights/filler/filler_flip.sh, whose re-pin mints this cell's OWN first-phase supply (item E16) "
                f"and keeps the agreement-table requirement {ff.AGREEMENT}; --allow-output-change must never be passed; "
                "every hash in this row moves at the flip and the re-pin tool rewrites it. Measurement declaration: "
                + (f"form-proof, expected_effect_pp 0.0, claims_benefit false, rows {c['rows']}" if n["smoke"] else
                   f"offline-sealed-pool, expected_effect_pp 0.0, claims_benefit false, rows {c['rows']}")
                + f" (top level of {n_arm['readiness_dir']}/registered-facts-v1.json). stage3_algorithm shared-rollout / "
                f"rollout. Ceiling {c['caps']['generation_calls_cap']} = {c['rows']} x 19; expected about "
                f"{c['caps']['expected_contacts']} contacts and {c['caps']['expected_wall_minutes']} GPU-minutes at ROLL-2's "
                "measured rate. Queued ONLY by the idle-filler queue (no flight running, no main-line chain ready); "
                "stop and preserve on the first failure and the queue halts. No paper-scale profile, no test or DEV "
                "contact, no comparator flight, no admission entry."
            )
            rows[run] = _row([
                ff.FAMILY_DATE, run, "bounded-discovery-probe", scope, MODEL_TOOL,
                f"slurp {n['roster_id']} TRAIN construction {c['rows']}", "discovery",
                c["roster"]["split_identity_hash"], "no",
                str(c["caps"]["generation_calls_cap"] if generation else c["caps"]["fit_endpoint_calls_cap"]),
                str(c["caps"]["repeated_speech_audio_seconds_cap"]), str(c["caps"]["gpu_hours_fit_inclusive"]),
                INHERITED, f"{n_arm['readiness_dir']}/{prefix}-plan-registered-v1.json", notes,
            ])
    return rows


def prepare_row(prepared: dict, *, study_commit: str) -> str:
    receipt = prepared["agreement_receipt"]
    return _row([
        ff.FAMILY_DATE, ff.PREPARE_ROW, "model-free-check",
        (
            f"The rollout FILLER family's model-free preparation (owner decision {ff.OWNER_DECISION}): (1) freeze the "
            f"family roster {ff.FAMILY_ROSTER} (the whole of TRAIN Fold B, proven the only admissible TRAIN universe of "
            "the current best system) and its six 180-row chunk rosters plus the chunk-1 four-row smoke roster; (2) the "
            f"Fold B content-dimension query derivative {ff.CONTENT_QUERY} by {ff.CONTENT_BUILDER}; (3) the filler "
            f"roster's own exemplar-intent agreement table {ff.AGREEMENT} by {ff.AGREEMENT_BUILDER} from the committed "
            "FILLER BASE cell slurp-native-stage3-filler-fold-b-base-v1. Zero model, server, encoder, embedder, "
            "tokenizer, scorer, network, GPU and paid-API contacts."
        ),
        "no model or tool contact; local id and vector arithmetic over receipt-pinned files",
        f"slurp {ff.FAMILY_ROSTER_ID} TRAIN construction 1080 (identity only; the derivations re-read sealed Fold B vectors)",
        "discovery", receipt["derived_from"]["split_identity_hash"], "no", "0", "0", "0",
        "No new speech exposure: no speech byte is read; every vector read was sealed by SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1. Prior exposure inherited in full.",
        ff.AGREEMENT_RECEIPT,
        (
            f"RUN BEFORE THIS ROW WAS WRITTEN, MODEL-FREE (DRAFT, root countersignature pending) {ff.FAMILY_DATE} at "
            f"study commit {study_commit}: the three preparations above are deterministic reads of sealed bytes and "
            f"their outputs are ids, shares and hashes, no score. Content derivative SHA256 {prepared['content_query_sha256']} "
            f"(provenance {prepared['content_query_provenance_sha256']}; byte-identical to the independently built "
            "vectors/slurp-system-update-fold-b-v1 file). Agreement table SHA256 "
            f"{prepared['agreement_sha256']}, receipt SHA256 {prepared['agreement_receipt_sha256']}; measured: "
            f"{receipt['measured']['roster_rows']} rows, vote totals {receipt['measured']['vote_total_histogram']}, "
            f"{receipt['measured']['rows_with_a_self_excluded_exemplar']} rows with a self-excluded exemplar, "
            f"{receipt['measured']['rows_with_no_vote']} rows with no vote, "
            f"{receipt['measured']['distinct_facets_ever_voted_for']} boundary facets reachable. It constructs no "
            "ExecutionPlan, reserves no contact and authorises nothing."
        ),
    ])


def replace_or_append(rows: dict, *, header_title: str) -> str:
    text = ff.rd(LEDGER)
    lines = text.split("\n")
    fresh = dict(rows)
    replaced = 0
    for index, line in enumerate(lines):
        parts = line.split("|")
        if line.startswith("|") and len(parts) > 3 and parts[2].strip() in fresh:
            lines[index] = fresh.pop(parts[2].strip())
            replaced += 1
    body = "\n".join(lines)
    if fresh:
        suffix = "" if body.endswith("\n") else "\n"
        body = body + suffix + f"\n## {header_title}\n\n" + LEDGER_HEADER + "\n".join(fresh.values()) + "\n"
    ff.wr(LEDGER, body)
    return f"replaced {replaced}, appended {len(fresh)}"


# ---- main ------------------------------------------------------------------------------------------
def identity(cell_id: str, roster: dict) -> dict:
    c, _ = composed(cell_id)
    return {"config_hash": c.config_hash,
            "protocol_hash": protocol_hash(c.config_hash, c.values["arm"], roster["split_identity_hash"])}


def run_base(data_root: Path) -> dict:
    prepared = measure_prepared(data_root, agreement=False)
    n = ff.names(None, base=True)
    out = write_fragments(n, prepared=prepared, agreement=False, stages=["check"], requirements=[],
                          roster_relpath=ff.FAMILY_ROSTER)
    diff = prove_diff(n, agreement=False, prepared=prepared, roster_relpath=ff.FAMILY_ROSTER, roster_sha=out["roster_sha"])
    return {"cell": n["cell"], "rows": out["rows"], "diff_other": diff["other"], "roster_pins": diff["roster_pins"],
            "composed_config_hash": diff["composed_config_hash"]}


def run_chunks(chunks: list[int], data_root: Path, *, study_commit: str, registered_at: str, write_ledger: bool) -> dict:
    prepared = measure_prepared(data_root, agreement=True)
    requirement = {
        "kind": "preparation",
        "reason": (
            "The filler roster's OWN pre-computed exemplar-intent AGREEMENT table this cell's boundary channel ranks "
            f"with (w_agree 1.0), built model-free by {ff.AGREEMENT_BUILDER} from the committed FILLER BASE cell "
            "slurp-native-stage3-filler-fold-b-base-v1 -- the pinned exemplar snapshot, the pinned pool key vectors "
            "and the sealed TRAIN Fold B speech query vectors, through the same rails.phase_supply."
            "build_bootstrap_selection recall/rank/fuse the flight runs at the Solver. Zero model, server, encoder, "
            f"embedder, scorer, network and GPU contacts (ledger row {ff.PREPARE_ROW})."
        ),
        "relpath": ff.AGREEMENT,
        "sha256": prepared["agreement_sha256"],
    }
    report = {}
    ledger = {}
    for k in chunks:
        n_arm = ff.names(k)
        cells = []
        variants = ([ff.names(k, smoke=True)] if k == 1 else []) + [n_arm]
        for n in variants:
            stages = ["check", "prepare-supply", "worker"] + ([] if n["smoke"] else ["campaign"])
            out = write_fragments(n, prepared=prepared, agreement=True, stages=stages, requirements=[requirement],
                                  roster_relpath=n["roster"])
            diff = prove_diff(n, agreement=True, prepared=prepared, roster_relpath=n["roster"], roster_sha=out["roster_sha"])
            cells.append({"n": n, **out, "diff": diff, "identity": identity(n["cell"], out["roster"])})
        ff.wr(n_arm["campaign"], json.dumps({"cells": [{"cell": n_arm["cell"], "experiment": n_arm["cell"]}],
                                             "schema": "saea-campaign-plan-v1"}, indent=2, sort_keys=True) + "\n")
        pkg = write_package(n_arm, cells, prepared=prepared, study_commit=study_commit, registered_at=registered_at)
        ledger.update(ledger_rows(n_arm, cells, pkg, study_commit=study_commit))
        report[f"c{k:02d}"] = {
            "cells": {c["n"]["cell"]: {"rows": c["rows"], "config_hash": c["identity"]["config_hash"],
                                       "protocol_hash": c["identity"]["protocol_hash"],
                                       "caps": c["caps"], "agreement_pins": c["diff"]["agreement_pins"],
                                       "roster_pins": c["diff"]["roster_pins"], "other": c["diff"]["other"]}
                      for c in cells},
            "run_ids": pkg["run_ids"],
        }
    if write_ledger:
        ledger[ff.PREPARE_ROW] = prepare_row(prepared, study_commit=study_commit)
        report["ledger"] = replace_or_append(
            ledger,
            header_title=(
                f"The rollout FILLER family (owner decision {ff.OWNER_DECISION}): chunks "
                f"{', '.join(f'c{k:02d}' for k in chunks)} and the family's model-free preparation (DRAFT, root "
                "countersignature pending)"
            ),
        )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--base", action="store_true")
    mode.add_argument("--chunks")
    parser.add_argument("--study-commit", default="")
    parser.add_argument("--registered-at", default=f"{ff.FAMILY_DATE}T00:00:00.000000+00:00")
    parser.add_argument("--write-ledger", action="store_true")
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    data_root = Path(os.environ.get("SPEECHRL_DATA_DIR", DATA_DEFAULT))
    if args.base:
        print(json.dumps(run_base(data_root), indent=2))
        return 0
    if not args.study_commit:
        raise SystemExit("--study-commit is required for --chunks")
    print(json.dumps(run_chunks(ff.parse_chunks(args.chunks), data_root, study_commit=args.study_commit,
                                registered_at=args.registered_at, write_ledger=args.write_ledger), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
