"""Panel lifecycle keeps per-flight records under one exclusive generation lease."""

import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import (
    CampaignCell,
    CampaignError,
    run_node_panel,
)
from speech_aware_evidence_acquisition.reproduction.ojw.panel import NativePanelMember


class Flight:
    def __init__(self, index, root, events, fail=None):
        self.run_id, self.attempt_id = f"run-{index}", f"attempt-{index}"
        self.root, self.events, self.fail = root, events, fail
        self.receipts = []
        self.execution_policy = None
        self.index = index

    def preflight(self):
        self.receipts.append("preflight")

    def verify_prepared_artifacts(self):
        self.events.append((self.index, "verify"))
        return ()

    def session_required_identity(self):
        return {"identity": "shared"}

    def serving_profile_fingerprint(self):
        return "shared"

    def preprocess(self):
        self.receipts.append("preprocess")

    def bind_execution_policy(self, policy):
        self.execution_policy = policy

    def bind_native_workflow_panel(self, panel):
        self.panel = panel

    def serve(self):
        self.execution_policy.assert_lease(
            self.root, run_id=self.run_id, attempt_id=self.attempt_id
        )
        self.receipts.append("serve")

    def run_phases(self):
        if self.fail == "before-join":
            raise RuntimeError("named entry failure")
        if self.fail == "bypass":
            return

        async def episode(state, contact, session, *, run_prepare):
            await run_prepare(lambda: state, prefix_family="solver")

            def model(slot):
                self.execution_policy.assert_lease(
                    self.root, run_id=self.run_id, attempt_id=self.attempt_id
                )
                if self.fail == "model":
                    raise RuntimeError("named model failure")
                self.events.append((self.index, "model"))

            await contact(model, prefix_family="solver")

        self.panel.execute(
            self.run_id,
            self.attempt_id,
            [object(), object()],
            job_keys=(("s0", None), ("s1", None)),
            episode_invoker=episode,
            branch_count=1,
            slot_count=2,
            queue_depth=2,
            workflow_timeout_seconds=5,
            node_pipeline_order=("solver",),
            node_pipeline_group_size=2,
            node_pipeline_prepare_workers=2,
            node_pipeline_max_jobs=4,
        )
        self.receipts.append("run_phases")
        self.events.append((self.index, "phases-complete"))

    def seal(self, **kwargs):
        assert kwargs in ({}, {"defer_scoring": True})
        assert sum(kind == "phases-complete" for _, kind in self.events) == 2
        self.events.append((self.index, "seal"))
        self.receipts.append("seal")
        if self.fail == "seal":
            raise RuntimeError("named seal failure")

    def score(self, **kwargs):
        assert not (self.root / "locks/flight.lock").exists()
        assert sum(kind == "seal" for _, kind in self.events) == 2
        assert kwargs == {"include_per_sample": True}
        self.events.append((self.index, "score"))
        if self.fail == "score":
            raise RuntimeError("named score failure")
        self.receipts.append("score")
        return {"official": True}

    def abort(self, reason):
        self.events.append((self.index, "abort"))


def world(tmp_path, monkeypatch, fail=None):
    from speech_aware_evidence_acquisition.core.flight import campaign

    events, saved = [], {}
    flights = [Flight(i, tmp_path, events, fail if i == 0 else None) for i in range(2)]
    cells = [
        CampaignCell.from_document(
            {
                "cell_id": f"cell-{i}",
                "model_fragment": "m",
                "dataset_fragment": "d",
                "baseline_fragment": "b",
                "run_id": f.run_id,
                "attempt_id": f.attempt_id,
                "readiness": {"state": "ready"},
                "allowed_execution_stages": ["node-panel"],
            }
        )
        for i, f in enumerate(flights)
    ]
    declared = tuple(
        NativePanelMember(f.run_id, f.attempt_id, (("s0", None), ("s1", None)))
        for f in flights
    )
    monkeypatch.setattr(campaign, "require_clean_study_repo", lambda root: "a" * 40)
    monkeypatch.setattr(campaign, "assert_identity_matches", lambda doc, required: None)

    def persist(root, *, run_id, attempt_id, receipts):
        saved[run_id] = list(receipts)
        return {"path": str(tmp_path / run_id), "sha256": "b" * 64}

    monkeypatch.setattr(campaign, "persist_flight_receipts", persist)
    return flights, cells, declared, events, saved


def run(tmp_path, flights, cells, declared, **kwargs):
    return run_node_panel(
        flights,
        cells=cells,
        members=declared,
        panel_id="panel",
        repo_root=tmp_path,
        data_root=tmp_path,
        owner="root",
        expected_session_id="resident",
        resident_finder=lambda root: (tmp_path, {"session_id": "resident"}),
        **kwargs,
    )


def test_one_lease_all_members_complete_before_seal_then_serial_scoring(
    tmp_path, monkeypatch
):
    flights, cells, declared, events, saved = world(tmp_path, monkeypatch)
    result = run(tmp_path, flights, cells, declared)
    assert result["completed"] == ["run-0", "run-1"]
    assert all(v["state"] == "scored" for v in result["states"].values())
    assert [i for i, k in events if k == "score"] == [0, 1]
    assert all(
        s == ["preflight", "preprocess", "serve", "run_phases", "seal", "score"]
        for s in saved.values()
    )
    assert not (tmp_path / "locks/flight.lock").exists()


@pytest.mark.parametrize("fail", ["before-join", "bypass", "model", "seal", "score"])
def test_failure_is_preserved_and_never_retried(tmp_path, monkeypatch, fail):
    flights, cells, declared, events, saved = world(tmp_path, monkeypatch, fail)
    with pytest.raises((RuntimeError, ValueError), match="named|panel"):
        run(tmp_path, flights, cells, declared)
    assert set(saved) == {"run-0", "run-1"}
    if fail == "score":
        assert [i for i, k in events if k == "score"] == [0]
        assert not any(k == "abort" for _, k in events)
        assert not (tmp_path / "locks/flight.lock").exists()
    else:
        assert not any(k == "score" for _, k in events)
        assert (tmp_path / "locks/flight.lock").exists()
        assert sorted(i for i, k in events if k == "abort") == [0, 1]


@pytest.mark.parametrize("defect", ["held", "mode", "attempt", "order", "dependent"])
def test_all_readiness_and_identity_checks_precede_lease(tmp_path, monkeypatch, defect):
    flights, cells, declared, events, saved = world(tmp_path, monkeypatch)
    doc = dict(cells[1].document)
    if defect == "held":
        doc["readiness"] = {"state": "held", "reason": "not admitted"}
    if defect == "mode":
        doc.pop("allowed_execution_stages")
    if defect == "attempt":
        doc["attempt_id"] = "wrong"
    if defect == "dependent":
        doc["readiness"] = {"state": "ready", "depends_on": [{"run_id": "run-0"}]}
    cells[1] = CampaignCell.from_document(doc)
    if defect == "order":
        declared = tuple(reversed(declared))
    with pytest.raises(CampaignError):
        run(tmp_path, flights, cells, declared)
    assert not (tmp_path / "locks/flight.lock").exists()
    assert not any(k in {"model", "seal", "score"} for _, k in events)


@pytest.mark.parametrize("fail", [None, "before-join", "bypass", "model", "seal"])
def test_explicit_worker_panel_materializes_generation_without_scoring(
    tmp_path, monkeypatch, fail
):
    flights, cells, declared, events, saved = world(tmp_path, monkeypatch, fail)
    for cell in cells:
        cell.document["allowed_execution_stages"] = ["node-panel-worker"]
    if fail:
        with pytest.raises((RuntimeError, ValueError), match="named|panel"):
            run(tmp_path, flights, cells, declared, mode="node-panel-worker")
        assert (tmp_path / "locks/flight.lock").exists()
        assert sorted(i for i, k in events if k == "abort") == [0, 1]
    else:
        result = run(tmp_path, flights, cells, declared, mode="node-panel-worker")
        assert all(s["state"] == "generated" for s in result["states"].values())
        assert result["mode"] == "node-panel-worker"
        assert result["completed"] == ["run-0", "run-1"]
        assert not (tmp_path / "locks/flight.lock").exists()
        assert all(
            s == ["preflight", "preprocess", "serve", "run_phases", "seal"]
            for s in saved.values()
        )
    assert set(saved) == {"run-0", "run-1"}
    assert not any(k == "score" for _, k in events)
    if fail and fail != "seal":
        assert not any(k == "seal" for _, k in events)


@pytest.mark.parametrize(
    "mode,allowed",
    [
        ("node-panel-worker", None),
        ("node-panel-worker", ["node-panel"]),
        ("node-panel", ["node-panel-worker"]),
        ("worker", ["worker"]),
    ],
)
def test_panel_lifecycle_requires_exact_explicit_mode(
    tmp_path, monkeypatch, mode, allowed
):
    flights, cells, declared, events, saved = world(tmp_path, monkeypatch)
    for cell in cells:
        cell.document["allowed_execution_stages"] = allowed
    with pytest.raises(CampaignError):
        run(tmp_path, flights, cells, declared, mode=mode)
    assert not events and not saved
    assert not (tmp_path / "locks/flight.lock").exists()


def test_worker_panel_writes_actual_runtime_outputs_manifest_and_score_spec(tmp_path, monkeypatch):
    """Exercise real worker materialization, not only a mocked seal call count."""
    import json
    from test_flight_runtime import _make_runtime
    from speech_aware_evidence_acquisition.core.flight.scoring import load_sealed_score_jobs

    flights, cells, declared, events, saved = world(tmp_path, monkeypatch)
    real = []
    for i, flight in enumerate(flights):
        rt = _make_runtime(tmp_path / f"actual-{i}", happy_path=True)
        rt.preflight()
        rt.preprocess()
        rt.serve()
        rt.run_phases()
        rt._execution_policy = object()
        real.append(rt)
        original_seal = flight.seal

        def seal(*, defer_scoring=False, runtime=rt, original=original_seal):
            original(defer_scoring=defer_scoring)
            return runtime.seal(defer_scoring=defer_scoring)

        flight.seal = seal
        cells[i].document["allowed_execution_stages"] = ["node-panel-worker"]
    run(tmp_path, flights, cells, declared, mode="node-panel-worker")
    for rt in real:
        directory = rt._run_dir()
        assert (directory / f"{rt.run_id}.outputs.jsonl").is_file()
        assert len((directory / f"{rt.run_id}.outputs.jsonl").read_text().splitlines()) == 2
        assert (directory / f"{rt.run_id}.run-manifest.json").is_file()
        assert (directory / f"{rt.run_id}.generation-manifest.json").is_file()
        assert rt._client.closed
        assert rt.receipts.has("seal") and not rt.receipts.has("score")
        seal_receipt = rt.receipts.require("seal")
        assert len(load_sealed_score_jobs(seal_receipt)) == 1
        assert seal_receipt["finalize"]["status"] == "deferred-to-score-worker"
        assert not list(directory.glob("*.scores.json"))
        spec = json.loads((directory / "score-jobs.jsonl").read_text())
        assert spec["job_id"] == rt.attempt_id
