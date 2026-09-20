"""Cell B8b-anchor resume-recovery proof: one declared repair, bookkeeping, and nothing else.

The B8b-anchor arm aborted at 2,016 of about 5,400 contacts on 2026-09-19T22:15Z: with the Reviewer
slot-audit attachment armed, 2 of 410 Reviewer visits spent all three of their ReAct iterations
calling ``saea-tool-task-contract-v1`` without producing an answer, and
``reproduction.ojw.native_episode._ApplyRole`` raised ``NativeEpisodeError`` because the harness had
no disposition for ReAct exhaustion. Item E22 supplies the disposition
(``native_episode.react_exhaustion_policy = "continue-without-answer"``), and owner decision 22 of
2026-09-18 makes the one root-diagnosed recovery a RESUME-RECOVERY (harness item E10): the aborted
attempt's COMPLETE rows are kept without selection and only the rest are flown, under the SAME run
id and a new attempt id.

These tests pin exactly that, on the committed fragments and -- for the composed assertions --
through the repository's own ``core.config.compose``, which is what ``core.flight.cli check`` uses:

1. the resume experiment loads through ``load_campaign_cells`` with a valid ``resume_from``
   declaration naming the ABORTED attempt and its trace SHA-256, keeps the aborted cell's run id,
   model and dataset fragments, and stays readiness ``held`` with a pinned ``preparation``
   requirement and no decision requirement (the coordinator's re-pin adds that);
2. the resume baseline differs from the aborted arm's baseline -- as that baseline stands on master,
   with item E22 already armed on it -- in exactly two bookkeeping keys: the native-fit ATTEMPT id
   and the free-English note. The fit RUN id, the contact cap and both WAVE R7 speech-feature
   identity strings are HELD, because a resume must not move a request byte;
3. both failure-mode keys are armed, and the ReAct-exhaustion key is the ONLY behavioural change
   this recovery declares;
4. the resume experiment's registered ceilings, roster, population, split identity and service
   session are the aborted arm's, unchanged, and the run-cumulative budget covers the predecessor's
   spend plus this attempt's worst case;
5. composed end to end, the two configurations differ only in bookkeeping keys -- every model-facing
   key is byte-identical -- and the campaign plan resolves to the resume cell;
6. and, where the data root is present, the trace SHA-256 the cell declares is the real file's, and
   the replay of that file partitions the registered roster into the kept 378 and the flown 702, the
   two partial ids included.

Model-free: it reads committed JSON, composes it, and (only in the last test) hashes and scans one
aborted attempt's trace read-only. No model, tokenizer, encoder, scorer or server is contacted, and
every test but the last runs without a data root.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "configs" / "baseline"
EXPERIMENT_DIR = REPO_ROOT / "configs" / "experiment"
CAMPAIGN_DIR = REPO_ROOT / "configs" / "campaign"

MODEL_FRAGMENT = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"

ABORTED_BASELINE = "slurp-native-anchor-reviewer-audit-train-fold-a-v1"
ABORTED_EXPERIMENT = "slurp-native-reviewer-audit-anchor-train-fold-a-v1"
RESUME_BASELINE = ABORTED_BASELINE + "-resume"
RESUME_EXPERIMENT = ABORTED_EXPERIMENT + "-resume"

#: The run id is SHARED with the aborted attempt. That is what a resume is.
RUN = "SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1"
ABORTED_ATTEMPT = "attempt-slurp-native-reviewer-audit-anchor-train-fold-a-generation-v1"
RESUME_ATTEMPT = ABORTED_ATTEMPT + "-resume"
FIT_RUN = "SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-FIT-V1"
ABORTED_FIT_ATTEMPT = "attempt-slurp-native-reviewer-audit-anchor-train-fold-a-fit-v1"
RESUME_FIT_ATTEMPT = ABORTED_FIT_ATTEMPT + "-resume"

SPLIT_IDENTITY = "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"
TRACE_SHA256 = "d495661dc7904eebb51818d4b35996a175de37af08d07ae56e904528fd6a84e3"
KEPT_IDS_SHA256 = "19b8b9e059d8a67bd83b8d7c72f86dc3d319617ea6fb123d32340faa91cfaccf"
PROGRAM_ID = "phase-native-candidates-review-revise-v1"

ROSTER_ROWS = 1080
KEPT_ROWS = 378
FLOWN_ROWS = 702
PARTIAL_ROWS = 2
STARTED_ROWS = 380
PREDECESSOR_CONTACTS = 2016
PROGRAM_MAX_CONTACTS = 11
PLANNED_MODEL_CALLS = 11880
CONTACT_CAP = 47520

PARTIAL_SAMPLE_IDS = (
    "slurp:train:004389:audio-1502113264",
    "slurp:train:004534:audio-1498647066-headset",
)

# The only baseline keys this resume moves, measured against the aborted baseline AS IT STANDS ON
# MASTER -- item E22 armed ``react_exhaustion_policy`` on that baseline too (commit 97e90a9b), after
# the attempt had already flown without it at commit c905ddf0. Neither key shapes a rendered
# request: the fit ATTEMPT id namespaces the fit receipt root (prepared/<fit run>/<fit attempt>/),
# and the note is English. ``prepared_phase_supply`` joins them only AFTER the coordinator's re-pin
# cycle, which rebuilds the artifact because core.preparation.artifact_inputs binds the cell
# identity.
BASELINE_BOOKKEEPING = {"native_contact_fit", "what_this_is"}
BASELINE_BOOKKEEPING_AFTER_REPIN = BASELINE_BOOKKEEPING | {"prepared_phase_supply"}

# Plus the experiment fragment's own identity and free-English fields.
EXPERIMENT_BOOKKEEPING = {
    "cells",
    "date",
    "failure_policy",
    "fragment_kind",
    "generation_budget",
    "population",
    "purpose",
}

#: Everything a request is built from. Byte-identical, or the resume is not a resume: the 378 kept
#: rows were produced under these values and the 702 flown rows must be too.
MODEL_FACING_KEYS = (
    "arm",
    "evidence_mismatch",
    "evidence_source",
    "knowledge_stores",
    "phase_material",
    "phase_tools",
    "policy",
    "populations",
    "preparation_source_receipts",
    "preserve_wire_responses",
    "scorers",
    "service_session",
    "serving_slot_tokens",
    "serving_slots",
    "speech_feature_key_representation_id",
    "speech_feature_matcher_policy_id",
    "speech_packet_promotion_receipt",
    "speech_packet_promotion_receipt_sha256",
    "split_id",
    "task_instruction_fill",
    "task_instruction_template",
    "task_instruction_template_active",
)


def _load(directory: Path, name: str) -> dict:
    return json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))


def test_the_resume_cell_loads_with_a_valid_resume_declaration():
    cells = load_campaign_cells(REPO_ROOT, RESUME_EXPERIMENT)
    assert len(cells) == 1
    cell = cells[0]

    assert cell.document["cell_id"] == RESUME_EXPERIMENT
    # The run id is the aborted run's; the attempt id is new and is not the predecessor's.
    assert cell.run_id == RUN
    assert cell.attempt_id == RESUME_ATTEMPT
    assert cell.attempt_id != ABORTED_ATTEMPT

    assert cell.resume_from == {
        "attempt_id": ABORTED_ATTEMPT,
        "trace_sha256": TRACE_SHA256,
    }
    # The aborted cell declares no resume_from at all.
    aborted = load_campaign_cells(REPO_ROOT, ABORTED_EXPERIMENT)[0]
    assert aborted.resume_from is None
    assert aborted.run_id == cell.run_id

    # The model and dataset fragments are the aborted cell's, unchanged.
    assert cell.document["model_fragment"] == aborted.document["model_fragment"] == MODEL_FRAGMENT
    assert (
        cell.document["dataset_fragment"]
        == aborted.document["dataset_fragment"]
        == DATASET_FRAGMENT
    )
    assert cell.document["baseline_fragment"] == RESUME_BASELINE
    assert (
        cell.document["allowed_execution_stages"]
        == aborted.document["allowed_execution_stages"]
    )

    # Readiness is a lifecycle field: `held` with the preparation requirement as registered, or
    # `ready` once the coordinator's re-pin tool has pinned the root decision receipt beside it.
    readiness = cell.document["readiness"]
    assert readiness["state"] in {"held", "ready"}
    kinds = sorted(requirement["kind"] for requirement in readiness["requirements"])
    assert kinds == (
        ["preparation"] if readiness["state"] == "held" else ["decision", "preparation"]
    )
    preparation = [r for r in readiness["requirements"] if r["kind"] == "preparation"][0]
    assert preparation["relpath"].startswith(f"prepared/{RUN}/phase-supply-v")


def test_the_resume_baseline_moves_the_fit_attempt_and_nothing_a_model_can_see():
    aborted = _load(BASELINE_DIR, ABORTED_BASELINE)
    resume = _load(BASELINE_DIR, RESUME_BASELINE)

    differing = {
        key for key in set(aborted) | set(resume) if aborted.get(key) != resume.get(key)
    }
    assert BASELINE_BOOKKEEPING <= differing <= BASELINE_BOOKKEEPING_AFTER_REPIN

    # The FIT RUN id does not move, so the run keeps its existing exposure row; only the ATTEMPT
    # moves, because the fit receipt root is prepared/<fit run>/<fit attempt>/ and
    # core.preparation_fit refuses a receipt path that already exists -- which every re-flown
    # partial row's first contacts would hit.
    assert (
        resume["native_contact_fit"]["run_id"]
        == aborted["native_contact_fit"]["run_id"]
        == FIT_RUN
    )
    assert aborted["native_contact_fit"]["attempt_id"] == ABORTED_FIT_ATTEMPT
    assert resume["native_contact_fit"]["attempt_id"] == RESUME_FIT_ATTEMPT
    # The cap is derived from the WHOLE registered roster, never from the flown subset.
    assert resume["native_contact_fit"]["contact_cap"] == CONTACT_CAP
    assert CONTACT_CAP == ROSTER_ROWS * PROGRAM_MAX_CONTACTS * (1 + 3)
    assert (
        resume["native_contact_fit"]["max_speech_packets"]
        == aborted["native_contact_fit"]["max_speech_packets"]
    )

    # Held, deliberately: both speech-feature identity strings ride the audited payload as
    # ORG/CONTROL provenance and the kept rows already carry the predecessor's values.
    for key in (
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
        "knowledge_stores",
        "policy",
        "native_episode",
        "phase_material",
        "phase_tools",
        "scorers",
        "arm",
        "task_instruction_template",
    ):
        assert resume[key] == aborted[key], key


def test_both_failure_mode_keys_are_armed_and_the_one_factor_is_untouched():
    aborted = _load(BASELINE_DIR, ABORTED_BASELINE)["native_episode"]
    resume = _load(BASELINE_DIR, RESUME_BASELINE)["native_episode"]

    # Item E13 and item E22, the two failure-mode keys the gate demands of every live unflown
    # native cell. Neither renders a request byte.
    assert resume["finite_completion_policy"] == "deliver-latest-or-abstain"
    assert resume["react_exhaustion_policy"] == "continue-without-answer"

    # The ReAct-exhaustion key is the ONE declared repair of this recovery. It is armed on the
    # aborted cell's baseline too (item E22 re-pinned it on master at 97e90a9b), which is why the
    # whole native_episode block is byte-identical here -- the one factor included.
    assert resume == aborted
    assert resume["reviewer_audit"]["view"] == "slot-audit-v1"
    assert resume["roles"]["reviewer"]["max_iterations"] == 3
    assert resume["max_revisions"] == 1


def test_the_resume_experiment_keeps_every_registered_ceiling_and_the_roster():
    aborted = _load(EXPERIMENT_DIR, ABORTED_EXPERIMENT)
    resume = _load(EXPERIMENT_DIR, RESUME_EXPERIMENT)

    differing = {
        key for key in set(aborted) | set(resume) if aborted.get(key) != resume.get(key)
    }
    assert differing <= EXPERIMENT_BOOKKEEPING
    assert {"cells", "purpose"} <= differing

    for key in (
        "execution_plan",
        "execution_profile",
        "experiment_id",
        "family_budget",
        "populations",
        "preserve_wire_responses",
        "service_session",
        "split_id",
    ):
        assert resume[key] == aborted[key], key

    # generation_budget moves only in its free-English definition.
    assert (
        resume["generation_budget"]["cap"]
        == aborted["generation_budget"]["cap"]
        == PLANNED_MODEL_CALLS
    )
    assert resume["generation_budget"]["target"] == aborted["generation_budget"]["target"]
    assert resume["execution_plan"]["planned_model_calls"] == PLANNED_MODEL_CALLS
    assert resume["population"]["split_identity_hash"] == SPLIT_IDENTITY
    assert resume["population"]["count"] == aborted["population"]["count"] == ROSTER_ROWS
    assert len(resume["populations"][0]["ids"]) == ROSTER_ROWS


def test_the_run_cumulative_budget_covers_the_predecessor_plus_this_attempts_worst_case():
    resume = _load(EXPERIMENT_DIR, RESUME_EXPERIMENT)
    worst_case = FLOWN_ROWS * PROGRAM_MAX_CONTACTS
    assert worst_case == 7722
    assert PREDECESSOR_CONTACTS + worst_case == 9738
    assert PREDECESSOR_CONTACTS + worst_case <= resume["execution_plan"]["planned_model_calls"]
    assert KEPT_ROWS + FLOWN_ROWS == ROSTER_ROWS


def test_the_composed_configurations_differ_only_in_bookkeeping():
    aborted = compose(
        REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, ABORTED_BASELINE, ABORTED_EXPERIMENT
    )
    resume = compose(
        REPO_ROOT, MODEL_FRAGMENT, DATASET_FRAGMENT, RESUME_BASELINE, RESUME_EXPERIMENT
    )

    keys = set(aborted.values) | set(resume.values)
    differing = {key for key in keys if aborted.values.get(key) != resume.values.get(key)}
    assert differing <= BASELINE_BOOKKEEPING_AFTER_REPIN | EXPERIMENT_BOOKKEEPING

    for key in MODEL_FACING_KEYS:
        assert resume.values[key] == aborted.values[key], key
    # The whole native episode -- the one factor and both failure-mode keys -- is held.
    assert resume.values["native_episode"] == aborted.values["native_episode"]

    # The composed hash and therefore the protocol hash necessarily move, since compose() hashes
    # the complete merged fragment set including the attempt identity. The arm -- what
    # protocol_hash binds beside the config -- does not.
    assert aborted.values["arm"] == resume.values["arm"]
    assert resume.config_hash != aborted.config_hash
    assert protocol_hash(
        resume.config_hash, resume.values["arm"], SPLIT_IDENTITY
    ) != protocol_hash(aborted.config_hash, aborted.values["arm"], SPLIT_IDENTITY)


def test_the_resume_campaign_plan_resolves_to_the_resume_cell():
    plan = json.loads(
        (CAMPAIGN_DIR / f"{RESUME_EXPERIMENT}.json").read_text(encoding="utf-8")
    )
    assert plan["schema"] == "saea-campaign-plan-v1"
    assert plan["cells"] == [{"cell": RESUME_EXPERIMENT, "experiment": RESUME_EXPERIMENT}]


def _attempt_dir() -> Path | None:
    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_root:
        return None
    attempt_dir = Path(data_root) / "runs" / RUN / ABORTED_ATTEMPT
    return attempt_dir if (attempt_dir / f"{RUN}.trace.jsonl").is_file() else None


@pytest.mark.skipif(
    _attempt_dir() is None,
    reason="the aborted B8b-anchor attempt is not present under SPEECHRL_DATA_DIR",
)
def test_the_declared_trace_sha256_is_the_real_files_and_partitions_this_roster():
    from speech_aware_evidence_acquisition.core.flight.resume import (
        kept_sample_ids_sha256,
        read_predecessor_attempt,
    )

    attempt_dir = _attempt_dir()
    assert attempt_dir is not None  # narrowed by the skip above

    digest = hashlib.sha256()
    with (attempt_dir / f"{RUN}.trace.jsonl").open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    cell = load_campaign_cells(REPO_ROOT, RESUME_EXPERIMENT)[0]
    assert cell.resume_from["trace_sha256"] == digest.hexdigest()

    # read_predecessor_attempt refuses a declaration whose bytes moved; passing the declared value
    # is therefore itself the assertion, and the counts below are what the flown roster is fixed
    # from at preflight.
    scan = read_predecessor_attempt(
        run_id=RUN,
        attempt_id=cell.resume_from["attempt_id"],
        attempt_dir=attempt_dir,
        expected_trace_sha256=cell.resume_from["trace_sha256"],
        program_id=PROGRAM_ID,
    )
    assert scan.contact_count() == PREDECESSOR_CONTACTS
    assert len(scan.started_sample_ids) == STARTED_ROWS
    assert len(scan.complete_sample_ids) == KEPT_ROWS
    assert scan.incomplete_sample_ids == tuple(sorted(PARTIAL_SAMPLE_IDS))
    assert kept_sample_ids_sha256(scan.complete_sample_ids) == KEPT_IDS_SHA256

    roster = _load(EXPERIMENT_DIR, RESUME_EXPERIMENT)["populations"][0]["ids"]
    assert len(roster) == ROSTER_ROWS
    # Every started row is in this flight's own roster: a resume requires the SAME split.
    assert set(scan.started_sample_ids) <= set(roster)
    kept = set(scan.complete_sample_ids)
    flown = [sample_id for sample_id in roster if sample_id not in kept]
    assert len(flown) == FLOWN_ROWS
    assert len([s for s in flown if s in scan.incomplete]) == PARTIAL_ROWS
    assert len(flown) - PARTIAL_ROWS == 700
