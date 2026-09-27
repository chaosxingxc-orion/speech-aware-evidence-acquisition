"""The three label-free preparations of the SLURP test SAMPLE, registered and runnable, never run.

Owner decision 156 of 2026-09-27 (row 156 of
``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``): the preparations of
``SLURP-TEST-SAMPLE-3010-V1`` may run ahead of the dev-admitted composed arm; the MILESTONE reads keep
row 151's gate. Plan ``docs/readiness/2026-09-27-slurp-test-sample-preparations-v1.md``.

What this module proves, all model-free, label-free and media-free:

* the derived runtime view and source inventory are byte-reproducible from committed bytes;
* the sample's configs are the FULL registration's with ONLY the roster-bound values swapped
  (a composed-config diff, a protocol diff and an alias-template diff);
* the registered numbers equal the roster receipt's own counts;
* the three exposure rows exist exactly once, unconsumed, pending countersignature;
* the runner's guard refuses them while pending, passes them once countersigned, and refuses every
  MILESTONE read id.

No model, encoder, tokenizer, scorer, server, GPU or network is contacted, and no media file is opened:
the preprocess driver's media read is a landmine that proves the allowance is accepted BEFORE it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SRC = str(REPO / "src")
_existing_pythonpath = os.environ.get("PYTHONPATH", "")
if _SRC not in _existing_pythonpath.split(":"):
    os.environ["PYTHONPATH"] = _SRC + (
        ":" + _existing_pythonpath if _existing_pythonpath else ""
    )
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    FINAL_REPORT_SPLIT_ROLE,
    ExecutionPlan,
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.core.preparation_speech_queries import (  # noqa: E402
    segment_plan,
)


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


derive = _load(
    "derive_test_sample_preparations_test",
    "scripts/flights/testsample/derive_test_sample_preparations.py",
)
steps = _load(
    "prep_test_sample_steps_test",
    "scripts/flights/testsample/prep_test_sample_steps.py",
)
driver = _load(
    "slurp_evo_fold_preprocess_test_sample", "scripts/slurp_evo_fold_preprocess.py"
)

SPLIT_IDENTITY = "0164dabf7b30f8e06f830ba28af849cef7459e8c8821cfbea7a56cabb32470f9"
FULL_IDENTITY = "7247647b8c8b37becd564b7031691565d4e6b09d8e124823054906d36372c95d"
ALLOWANCE_RELPATH = "docs/receipts/owner/2026-09-27-slurp-test-sample-allowance-v1.json"
ALLOWANCE_SHA256 = "c2ae2c4eb2142b5aef27d85c04c7dcd55952c105b469fd195592c71cb6bb331b"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-test-sample-3010-v1.json"
FULL_VIEW = "configs/dataset/slurp-speech-native-test-full.json"
SAMPLE_VIEW = "configs/dataset/slurp-speech-native-test-sample-3010.json"
FULL_PROTOCOL = (
    "configs/preparation/slurp-test-full-speech-query-encoding-protocol-v1.json"
)
SAMPLE_PROTOCOL = (
    "configs/preparation/slurp-test-sample-3010-speech-query-encoding-protocol-v1.json"
)
FULL_ALIAS = "configs/preparation/slurp-test-full-query-alias-v1.json"
SAMPLE_ALIAS = "configs/preparation/slurp-test-sample-3010-query-alias-v1.json"
FULL_EXPERIMENT = "configs/experiment/slurp-test-full-preprocess.json"
SAMPLE_EXPERIMENT = "configs/experiment/slurp-test-sample-3010-preprocess.json"
FULL_COMPOSED_HASH = "9312a112b789731088ef6627f785615acff615db17302b7dc8d27b4b7a70c079"
SAMPLE_COMPOSED_HASH = (
    "9a1814ad5aced59d6a7f5692ebaf9efd7909927a3799bbfdf8f7b6b7dfef0fbb"
)
INVENTORY_SHA256 = "77fce38e3825dff6f4bb409e2c4839c34a6bb41b55735feafab72ffc10e07a19"
ROWS = 3010
AUDIO_SECONDS = 8206.436875
RUN_IDS = (
    "SAEA-SN-TEST-SAMPLE-3010-PREPROCESS",
    "SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1",
)
MILESTONE_IDS = (
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1",
)
# The ONLY composed keys a roster swap may move (deliverable 1's diff proof).
ROSTER_BOUND_COMPOSED_KEYS = frozenset(
    {
        "experiment_id",
        "owner_allowance",
        "purpose",
        "items",
        "count",
        "audio_seconds_total",
        "split_identity_hash",
        "split_name",
        "seed",
        "source_binding_sha256",
        "runtime_view_sha256",
    }
)


def raw_sha256(relpath: str) -> str:
    return hashlib.sha256((REPO / relpath).read_bytes()).hexdigest()


def load_json(relpath: str):
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def compose(dataset: str, experiment: str):
    return driver.compose(
        REPO, driver.MODEL_FRAGMENT, dataset, driver.BASELINE_FRAGMENT, experiment
    )


# ------------------------------------------------------------------ derivation, byte for byte


def test_the_runtime_view_reproduces_from_the_committed_full_view_and_roster() -> None:
    assert derive.derive_view_bytes(REPO) == (REPO / SAMPLE_VIEW).read_bytes()


def test_the_runtime_view_is_the_label_free_restriction_of_the_full_view() -> None:
    full, sample, roster = (
        load_json(FULL_VIEW),
        load_json(SAMPLE_VIEW),
        load_json(ROSTER_RELPATH),
    )
    by_id = {item["sample_id"]: item for item in full["items"]}
    assert sample["count"] == len(sample["items"]) == ROWS
    assert {item["sample_id"] for item in sample["items"]} == {
        item["sample_id"] for item in roster["items"]
    }
    for item in sample["items"]:
        assert set(item) == derive.VIEW_ITEM_KEYS
        assert item == by_id[item["sample_id"]]
    assert (
        sample["split_identity_hash"] == SPLIT_IDENTITY == roster["split_identity_hash"]
    )
    assert sample["split_role"] == FINAL_REPORT_SPLIT_ROLE
    assert sample["split_name"] == roster["split_name"] == "TEST-SAMPLE"
    assert (
        sample["audio_seconds_total"] == AUDIO_SECONDS == roster["audio_seconds_total"]
    )
    for key in (
        "d1_media_supplement",
        "d1_media_supplement_sha256",
        "d1_manifest_sha256",
    ):
        assert sample[key] == full[key]
    unsigned = {
        key: value for key, value in sample.items() if key != "runtime_view_sha256"
    }
    assert sample["runtime_view_sha256"] == derive.canonical_sha256(unsigned)
    assert sample["source_binding_sha256"] == derive.canonical_sha256(roster)


def test_the_source_inventory_is_byte_reproducible_and_pinned() -> None:
    first, second = (
        derive.derive_inventory_bytes(REPO),
        derive.derive_inventory_bytes(REPO),
    )
    assert first == second
    assert hashlib.sha256(first).hexdigest() == INVENTORY_SHA256
    protocol = load_json(SAMPLE_PROTOCOL)
    assert protocol["sources"]["sha256"] == INVENTORY_SHA256 == steps.INVENTORY_SHA256
    document = json.loads(first)
    assert (
        document["roster_sha256"]
        == raw_sha256(ROSTER_RELPATH)
        == protocol["roster_sha256"]
    )
    assert document["split_identity_hash"] == SPLIT_IDENTITY
    assert document["media_bytes_opened"] == 0 and document["model_contacts"] == 0
    for row in document["rows"]:
        assert set(row) == {
            "id",
            "media_relpath",
            "audio_sha256",
            "source_frames",
            "source_sample_rate_hz",
        }
        assert isinstance(row["source_frames"], int) and row["source_frames"] > 0
    assert math.isclose(document["audio_seconds_total"], AUDIO_SECONDS, abs_tol=1e-6)


def test_the_inventory_reproduces_the_span_count_and_audio_budget() -> None:
    """The arithmetic ``run_preparation`` runs before its first contact."""

    protocol = load_json(SAMPLE_PROTOCOL)
    rows = json.loads(derive.derive_inventory_bytes(REPO))["rows"]
    spans = {
        (
            row["audio_sha256"],
            row["source_frames"],
            row["source_sample_rate_hz"],
            span["start_frame"],
            span["end_frame"],
        )
        for row in rows
        for span in segment_plan(
            row["source_frames"],
            row["source_sample_rate_hz"],
            max_seconds=protocol["max_seconds"],
            overlap_seconds=protocol["overlap_seconds"],
        )
    }
    seconds = sum((end - start) / rate for _sha, _frames, rate, start, end in spans)
    assert len(spans) == protocol["expected_unique_spans"] == ROWS
    assert seconds <= steps.PLANNED_SPEECH_SECONDS == math.ceil(AUDIO_SECONDS)


def test_a_non_integer_frame_count_is_refused() -> None:
    with pytest.raises(derive.DerivationError):
        derive.exact_frames("slurp:test:x", 1.00001, 16000)
    assert derive.exact_frames("slurp:test:x", 2.4316875, 16000) == 38907


# ------------------------------------------------------------------ the diff proof


def test_the_composed_config_differs_from_the_full_one_only_in_roster_bound_keys() -> (
    None
):
    full = compose("slurp-speech-native-test-full", "slurp-test-full-preprocess")
    sample = compose(
        "slurp-speech-native-test-sample-3010", "slurp-test-sample-3010-preprocess"
    )
    assert full.config_hash == FULL_COMPOSED_HASH  # the FULL registration is untouched
    assert (
        sample.config_hash == SAMPLE_COMPOSED_HASH
    )  # the value the exposure row quotes
    keys = set(full.values) | set(sample.values)
    differing = {key for key in keys if full.values.get(key) != sample.values.get(key)}
    assert differing == ROSTER_BOUND_COMPOSED_KEYS
    assert sample.values["owner_allowance"] == {
        "path": ALLOWANCE_RELPATH,
        "sha256": ALLOWANCE_SHA256,
    }
    assert sample.values["experiment_id"] == RUN_IDS[0]


def test_the_experiment_fragment_differs_only_in_run_id_allowance_and_prose() -> None:
    full, sample = load_json(FULL_EXPERIMENT), load_json(SAMPLE_EXPERIMENT)
    assert set(full) == set(sample)
    assert {key for key in full if full[key] != sample[key]} == {
        "experiment_id",
        "owner_allowance",
        "purpose",
    }


ROSTER_BOUND_PROTOCOL_KEYS = frozenset(
    {
        "cache_relpath",
        "expected_unique_spans",
        "isolation",
        "output_relpath",
        "query_rows_relpath",
        "roster_sha256",
        "sources",
    }
)


def test_the_protocol_differs_from_the_full_one_only_in_roster_bound_fields() -> None:
    full, sample = load_json(FULL_PROTOCOL), load_json(SAMPLE_PROTOCOL)
    assert set(full) == set(sample)
    assert {
        key for key in full if full[key] != sample[key]
    } == ROSTER_BOUND_PROTOCOL_KEYS
    assert sample["cpu_workers"] == 8 and sample["expected_unique_spans"] == ROWS
    assert set(full["sources"]) == set(sample["sources"])
    pinned = sample["sources"]["derived_from"]
    assert pinned["runtime_view"]["raw_sha256"] == raw_sha256(SAMPLE_VIEW)
    assert (
        pinned["runtime_view"]["canonical_runtime_view_sha256"]
        == load_json(SAMPLE_VIEW)["runtime_view_sha256"]
    )
    assert pinned["roster_receipt"] == {
        "path": ROSTER_RELPATH,
        "sha256": raw_sha256(ROSTER_RELPATH),
    }
    assert sample["sources"]["path"].endswith("/" + steps.INVENTORY_RELPATH)
    assert sample["output_relpath"] == "prepared/%s/index.json" % RUN_IDS[1]
    assert sample["query_rows_relpath"] == "prepared/%s/queries.jsonl" % RUN_IDS[1]


def test_the_alias_template_differs_from_the_full_one_only_in_roster_bound_fields() -> (
    None
):
    full, sample = load_json(FULL_ALIAS), load_json(SAMPLE_ALIAS)
    assert set(full) == set(sample)
    assert {key for key in full if full[key] != sample[key]} == {
        "expected_rows",
        "how_to_fill",
        "output_relpath",
        "receipt_relpath",
        "source",
        "source_receipts",
    }
    assert {
        key for key in full["source"] if full["source"][key] != sample["source"][key]
    } == {"relpath"}
    assert sample["source"]["sha256"] == "PENDING_STEP_2B_QUERIES_SHA256"
    assert sample["source_receipts"][0]["sha256"] == "PENDING_STEP_2B_RECEIPT_SHA256"
    assert sample["source_receipts"][1] == {
        "relpath": SAMPLE_VIEW,
        "root": "repository",
        "sha256": raw_sha256(SAMPLE_VIEW),
    }
    assert sample["source_receipts"][2] == {
        "relpath": ROSTER_RELPATH,
        "root": "repository",
        "sha256": raw_sha256(ROSTER_RELPATH),
    }
    generic = steps.load_generic(REPO)
    config = generic.materialise_alias_config(
        sample, queries_sha256="a" * 64, receipt_sha256="b" * 64
    )
    assert set(config) == generic.ALIAS_CONFIG_FIELDS


# ------------------------------------------------------------------ numbers and plans


def test_the_driver_roster_is_registered_from_the_roster_receipt_counts() -> None:
    spec = driver.PREPROCESS_ROSTERS["test-sample-3010"]
    assert list(driver.PREPROCESS_ROSTERS)[-1] == "test-sample-3010"
    assert spec.run_id == RUN_IDS[0]
    assert spec.split_role == FINAL_REPORT_SPLIT_ROLE
    assert spec.sidecar_fragment == driver.MODEL_FRAGMENT  # CPU-only, -np 4, port 8081
    assert spec.promotion_receipt_name == "TEST-SAMPLE-3010-promotion.json"
    roster = load_json(ROSTER_RELPATH)
    assert (
        spec.plan_calls
        == len(roster["items"])
        == roster["counts"]["recordings"]
        == ROWS
    )
    assert spec.plan_speech_seconds == math.ceil(roster["audio_seconds_total"]) == 8207
    assert spec.plan_gpu_hours == 1.0


@pytest.mark.skipif(
    not steps.UMBRELLA_LOCK.is_file(), reason="the umbrella lock is not mounted here"
)
def test_the_plans_validate_against_the_signed_allowance_without_contact() -> None:
    allowance = load_json(ALLOWANCE_RELPATH)
    assert raw_sha256(ALLOWANCE_RELPATH) == ALLOWANCE_SHA256
    assert allowance["status"] == "authorised"
    assert set(RUN_IDS) == set(allowance["preparation_run_ids"])
    assert not set(RUN_IDS) & set(allowance["read_run_ids"])
    generic = steps.load_generic(REPO)
    document = steps.runtime_plan_document(REPO, generic)
    assert document["plan"]["owner_allowance"] == {
        "path": ALLOWANCE_RELPATH,
        "sha256": ALLOWANCE_SHA256,
    }
    assert document["plan"]["split_role"] == FINAL_REPORT_SPLIT_ROLE
    assert document["protocol"] == {
        "path": SAMPLE_PROTOCOL,
        "sha256": raw_sha256(SAMPLE_PROTOCOL),
    }
    plan = ExecutionPlan(**document["plan"]).validate()
    assert (
        plan.planned_model_calls,
        plan.planned_speech_audio_seconds,
        plan.planned_gpu_hours,
    ) == (ROWS, 8207, 2.0)
    fresh = _load(
        "prep_generic_steps_untouched", "scripts/flights/batch/prep_generic_steps.py"
    )
    assert (
        "test-sample-3010" not in fresh.PREPARATION_SETS
    )  # the generic file is not edited


def _landmined(monkeypatch, tmp_path):
    def never(*args, **kwargs):
        raise AssertionError("roster_samples was reached")

    monkeypatch.setattr(driver, "roster_samples", never)
    monkeypatch.setattr(driver, "data_root", lambda: tmp_path)
    monkeypatch.setattr(
        driver, "umbrella_lock_path", lambda *a, **k: tmp_path / "lock.json"
    )
    monkeypatch.setattr(driver, "load_lock", lambda path: {})


def test_the_driver_accepts_the_allowance_before_it_would_open_media(
    monkeypatch, tmp_path
) -> None:
    """The allowance passes; the row's countersignature is the runner's gate, not the driver's."""

    _landmined(monkeypatch, tmp_path)
    with pytest.raises(AssertionError, match="roster_samples was reached"):
        driver.main(["--roster", "test-sample-3010", "--preflight-only"])


# ------------------------------------------------------------------ ledger rows and the guard


# The ledger AS REGISTERED, before the countersignature: aa69fca9 countersigned the three rows (owner decision
# 156) and a run of the preparations will later mark them consumed, so the working-tree ledger no longer carries
# the pending state these registration and guard proofs are about. The fixture is the committed ledger blob of
# a430011a (the merge that registered the rows; the parent of aa69fca9), materialised once per session -- the
# pattern of 643afc37.
_REGISTERED_COMMIT = "a430011a"
_REGISTERED_LEDGER: Path | None = None


def _registered_ledger() -> Path:
    global _REGISTERED_LEDGER
    if _REGISTERED_LEDGER is None:
        import tempfile

        blob = subprocess.run(
            ["git", "-C", str(REPO), "show", f"{_REGISTERED_COMMIT}:docs/exposure-ledger.md"],
            check=True, capture_output=True,
        ).stdout
        target = Path(tempfile.mkdtemp(prefix="saea-testsample-registered-")) / "exposure-ledger.md"
        target.write_bytes(blob)
        _REGISTERED_LEDGER = target
    return _REGISTERED_LEDGER


def _rows():
    return _parse_ledger_tables(_registered_ledger().read_text(encoding="utf-8"))


def test_the_three_rows_are_registered_once_unconsumed_and_pending() -> None:
    rows = _rows()
    for run_id in RUN_IDS:
        matched = [row for row in rows if row.get("run/experiment id") == run_id]
        assert len(matched) == 1, run_id
        row = matched[0]
        profile, calls, seconds, gpu_hours = steps.EXPECTED_ROWS[run_id]
        assert row["execution profile"] == profile
        assert row["split role"] == FINAL_REPORT_SPLIT_ROLE
        assert row["split identity hash"] == SPLIT_IDENTITY != FULL_IDENTITY
        assert row["consumed"].strip().lower() == "no"
        assert (
            int(row["calls"]),
            int(row["speech audio seconds"]),
            float(row["gpu hours"]),
        ) == (calls, seconds, gpu_hours)
        text = " ".join(row.values())
        assert (
            "REGISTERED BEFORE CONTACT (draft, root countersignature pending)"
            in row["notes"]
        )
        assert len(re.findall(r"\bdraft\b", text, re.IGNORECASE)) == 1
        assert "owner decision 156" in text and "reads_labels false" in text
        assert "DEVICE:" in row["model/tool"]
        assert "MILESTONE" not in text.replace("MILESTONE READ", "")
    devices = {
        run_id: [row for row in rows if row.get("run/experiment id") == run_id][0][
            "model/tool"
        ]
        for run_id in RUN_IDS
    }
    assert "CPU ONLY" in devices[RUN_IDS[0]] and "port 8081" in devices[RUN_IDS[0]]
    assert (
        "DEVICE: GPU" in devices[RUN_IDS[1]] and "QUEUED BEHIND" in devices[RUN_IDS[1]]
    )


def test_the_guard_refuses_every_pending_row() -> None:
    refusals = steps.row_refusals(_rows(), RUN_IDS)
    assert len(refusals) == 3
    assert all(
        "marked draft (root countersignature pending)" in message
        for message in refusals
    )


def test_the_guard_passes_once_the_rows_are_countersigned() -> None:
    signed = []
    for row in _rows():
        if row.get("run/experiment id") in RUN_IDS:
            row = dict(row)
            row["notes"] = row["notes"].replace(
                "(draft, root countersignature pending)",
                "(root countersigned 2026-09-27 12:00 UTC by the coordinator, owner decision 156)",
            )
        signed.append(row)
    assert steps.row_refusals(signed, RUN_IDS) == []
    unsigned = [
        dict(row, notes="REGISTERED BEFORE CONTACT")
        if row.get("run/experiment id") == RUN_IDS[0]
        else row
        for row in signed
    ]
    assert steps.row_refusals(unsigned, RUN_IDS[:1]) == [
        "%s: the exposure row carries no root countersignature" % RUN_IDS[0]
    ]


@pytest.mark.parametrize("milestone", MILESTONE_IDS)
def test_every_milestone_read_id_is_refused(milestone) -> None:
    allowance = load_json(ALLOWANCE_RELPATH)
    with pytest.raises(steps.SampleRunRefusal, match="milestone read id"):
        steps.refuse_milestones(REPO, (RUN_IDS[0], milestone), allowance)
    steps.refuse_milestones(REPO, RUN_IDS, allowance)  # the three preparations pass


def test_the_guard_step_refuses_today(capsys) -> None:
    # "today" is the registration day: the guard reads the registered (pre-countersignature) ledger blob.
    assert steps.main(["--repo-root", str(REPO), "guard", "--stage", "all",
                       "--ledger", str(_registered_ledger())]) == 1
    printed = capsys.readouterr().out
    assert printed.count("REFUSED:") == 3


# ------------------------------------------------------------------ the runner


def test_the_runner_scripts_parse_and_respect_the_caps() -> None:
    for name in ("prep_test_sample.sh", "prep_test_sample_task_entry.sh"):
        path = REPO / "scripts" / "flights" / "testsample" / name
        subprocess.run(["bash", "-n", str(path)], check=True)
    runner = (REPO / "scripts/flights/testsample/prep_test_sample.sh").read_text(
        encoding="utf-8"
    )
    assert "PREP_WORKERS=4 PREP_PROMOTE_WORKERS=8" in runner
    assert "scripts/flights/batch/prep_generic_task_entry.sh" in runner
    assert "guard --stage" in runner
    # 8080 appears only as the exclusion of the resident service, never as a target.
    assert re.search(r"--port 8080'", runner)
    for line in runner.splitlines():
        if "8080" in line and not line.lstrip().startswith("#"):
            assert "--port 8080" in line or "port-8080" in line
