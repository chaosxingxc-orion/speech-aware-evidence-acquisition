"""The offline end-to-end dry run of one EVO-A1 round (track E3c).

This is the "4-row dry run" the study's own iteration rule requires before a
loop flight: a synthetic registry, a synthetic exemplar and fold state, a
HAND-WRITTEN sealed proposer manifest (one valid answer, one refused) and
fake per-sample score files, driven through a whole round by
``rails.evolution``'s pure step functions. It produces deterministic
receipts, ``replay_selection`` reproduces every stage-one decision from the
sealed score files alone, and a second run over the same inputs is
BYTE-IDENTICAL.

Zero model contacts, zero carrier reads, zero network. Every construction
row here is synthetic: no real Audio2Tool query text or gold call appears in
this repository.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.rails.evolution import (
    ROUND_STEPS,
    CarrierMaterial,
    EvolutionError,
    EvolutionState,
    LoopConfig,
    check_ledger_budget,
    plan_round,
    replay_selection,
    run_candidates_step,
    run_confirm_step,
    run_propose_step,
    run_select_step,
)
from speech_aware_evidence_acquisition.rails.evolution_carrier import (
    _split_fold_rows,
    rows_of_target_from_roster,
    sentinel_rows_from_roster,
)
from speech_aware_evidence_acquisition.rails.proposer import (
    NULL_REWRITE_GATE,
    CandidateArtifact,
)

CARRIER = "audio2tool"
TARGETS = {"castContent": ["castContent", "playMedia"]}
TOOLS = ("castContent", "playMedia")
SCORER = "a2t-toolcall-official"
METRIC = "tool_correct"
#: Four fold-A rows per tool: the smallest roster on which the count gates
#: below can separate a save from a harm at all.
FOLD_A_ROWS = {
    "castContent": [f"foldA:{index:06d}" for index in range(1, 5)],
    "playMedia": [f"foldA:{index:06d}" for index in range(5, 9)],
}
FOLD_B_TARGETED = tuple(f"foldB:{index:06d}" for index in range(1, 9))
FOLD_B_BACKGROUND = tuple(f"foldB:{index:06d}" for index in range(9, 17))


def _loop_config_document() -> dict:
    return {
        "carrier_lock_key": CARRIER,
        "targets": TARGETS,
        "proposer_run_id": "SAEA-TEST-EVO-PROPOSER",
        "fold_a_run_id": "SAEA-TEST-EVO-FOLD-A",
        "fold_b_run_id": "SAEA-TEST-EVO-FOLD-B",
        "base_fragment": "evo-dry-run-base",
        "model_fragment": "m",
        "fold_a_dataset_fragment": "fold-a",
        "fold_b_dataset_fragment": "fold-b",
        "metric": METRIC,
        "scorer_id": SCORER,
        "proposer_slots": [1, 2],
        "placebo_slot": 3,
        "deterministic_slot": 4,
        "exemplars_per_tool": 2,
        "seed": 20260903,
        "max_rounds": 4,
        # Scaled to a four-row-per-tool dry run; the flight's own gates
        # are the preregistered 4/1/3 and live in the committed loop
        # config, never here.
        "gates": {"saves": 2, "harms": 1, "net": 1},
        "n_replicates": 200,
        "receipts_reldir": "docs/checks/dry-run",
        "rosters_reldir": "docs/receipts/rosters",
        "experiments_reldir": "configs/experiment",
        "fragment_reldir": "configs/baseline",
        "artifact_reldir": "configs/knowledge/evo-dry-run",
        "slug": "evo-dry-run",
    }


def _loop_config() -> LoopConfig:
    return LoopConfig.from_json(_loop_config_document())


def _registry_rows() -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "tool_id": str(index),
            "tool_name": tool,
            "signature": f"{tool}(deviceId: str)",
            "description": f"Synthetic description for {tool}.",
            "domain": "media",
            "category": "playback",
            "argument_constraints": "",
            "argument_defaults": "",
        }
        for index, tool in enumerate(TOOLS, start=1)
    )


def _pool_ids(tool: str) -> list[str]:
    base = 100 if tool == "castContent" else 200
    return [f"tier1_direct:{base + offset:06d}" for offset in range(3)]


def _carrier() -> CarrierMaterial:
    pool = {tool: tuple(_pool_ids(tool)) for tool in TOOLS}
    rows: dict[str, dict[str, str]] = {}
    media: dict[str, dict[str, object]] = {}
    for tool in TOOLS:
        for sample_id in _pool_ids(tool):
            rows[sample_id] = {
                "query": f"synthetic request for {tool} {sample_id[-3:]}",
                "gold_call": f"{tool}(deviceId='synthetic')",
                "tool_name": tool,
            }
            media[sample_id] = {
                "media_relpath": f"datasets/{CARRIER}/public/{sample_id}.wav",
                "audio_sha256": "0" * 64,
                "audio_seconds": 2.0,
                "sample_rate_hz": 16000,
            }
    return CarrierMaterial(
        registry_rows=_registry_rows(),
        exemplar_pool=pool,
        media_facts=media,
        exemplar_rows=rows,
        fold_a_rows_of_target={
            "castContent": tuple(FOLD_A_ROWS["castContent"] + FOLD_A_ROWS["playMedia"])
        },
        fold_b_targeted_rows=FOLD_B_TARGETED,
        fold_b_background_rows=FOLD_B_BACKGROUND,
    )


def _write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _repo(root: Path, config: LoopConfig) -> Path:
    """A synthetic repository carrying only the base fragment the driver
    copies. Nothing else about a real checkout is needed: every step is a
    function of its inputs."""

    _write(
        root / "configs" / "baseline" / f"{config.base_fragment}.json",
        {
            "arm": "bare-core",
            "policy": "fixed",
            "evidence_source": "none",
            "scorers": ["cost"],
            "task_instruction_template": "probes/synthetic.txt",
        },
    )
    return root




def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sealed_trace(path: Path, rows, questions) -> str:
    """The three files a real arm seals beside its scores: the run manifest,
    the raw trace whose ``MODEL_REQUEST`` payloads carry the QUESTION, and the
    ``.outputs.jsonl`` whose per-row response digest goes with it. The round
    receipt's noise floor is computed from exactly these.

    ``request_id`` and ``decoding_params.id_slot`` are made DIFFERENT in every
    arm on purpose: they are transport (an ordinal and a server slot), and an
    instrument that counted them as a new question would report every row of
    every round as changed. ``rails.evolution.question_sha256`` drops them.

    Everything is referenced RELATIVELY, exactly as ``sealed_question_digests``
    resolves it, so the synthetic bundle carries no absolute path and two runs
    of this dry run stay byte-identical.
    """

    stem = path.name.split(".", 1)[0]
    trace, outputs = [], []
    for index, sample_id in enumerate(sorted(rows)):
        question, response = questions.get(
            sample_id, (f"ask|{sample_id}", _sha(f"answer|{sample_id}"))
        )
        request_id = f"{stem}-{index:04d}"
        trace.append(
            json.dumps(
                {
                    "channel": "MODEL_REQUEST",
                    "record_id": f"{request_id}/request",
                    "payload": {
                        "arm": stem,
                        "payload": {
                            "request_id": request_id,
                            "sample_id": sample_id,
                            "decoding_params": {
                                "id_slot": (index + len(stem)) % 4,
                                "temperature": 0,
                            },
                            "history": [{"content": question}],
                        },
                    },
                }
            )
        )
        outputs.append(
            json.dumps({"sample_id": sample_id, "response_text_sha256": response})
        )
    named = {}
    for suffix, lines in (("trace.jsonl", trace), ("outputs.jsonl", outputs)):
        file = path.parent / f"{stem}.{suffix}"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(
            "".join(line + "\n" for line in lines), encoding="utf-8", newline="\n"
        )
        named[suffix] = {
            "path": file.name,
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
        }
    _write(
        path.parent / f"{stem}.run-manifest.json",
        {
            "schema": "saea-run-manifest-v1",
            "status": "COMPLETED",
            "raw_trace": named["trace.jsonl"],
            "outputs": named["outputs.jsonl"],
        },
    )
    return f"{stem}.run-manifest.json"


def _score_file(
    path: Path, rows: Mapping[str, bool], questions: Mapping[str, tuple] | None = None
) -> str:
    """One ``<job_id>.score.json`` as ``core.scoring_batch`` writes it, beside
    the run manifest and sealed outputs it names."""

    manifest = _sealed_trace(path, rows, questions or {})
    _write(
        path,
        {
            "manifest": manifest,
            "verified": True,
            "scores": {
                SCORER: {
                    "aggregate": {METRIC: sum(rows.values()) / len(rows)},
                    "per_sample": [
                        {"sample_id": sample_id, METRIC: value}
                        for sample_id, value in sorted(rows.items())
                    ],
                }
            },
        },
    )
    return str(path)


def _valid_response(cue: str = "what the request is cast TO") -> str:
    return json.dumps(
        {
            "cue": cue,
            "descriptions": {
                "castContent": "Send media that is already playing to another screen.",
                "playMedia": "Start playing a named track or show on this device.",
            },
        }
    )


def _placebo_response() -> str:
    return json.dumps(
        {
            "cue": "none",
            "descriptions": {
                "castContent": "Handles content for a device in the media area.",
                "playMedia": "Handles media for a device in the media area.",
            },
        }
    )


def _run_round(root: Path, *, refuse_second_slot: bool = True) -> dict[str, object]:
    """One whole round, step by step, over the synthetic world. Returns the
    confirm step's summary."""

    config = _loop_config()
    repo_root = _repo(root, config)
    carrier = _carrier()
    receipts_dir = repo_root / config.receipts_reldir
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    paths = config.round_paths(1)

    def exists(relpath: str) -> bool:
        return (repo_root / relpath).exists()

    # -- (a) propose ------------------------------------------------------
    plan = plan_round(state, 1, paths=paths, exists=exists)
    assert plan.next_step == "propose"
    propose = run_propose_step(state, 1, config=config, carrier=carrier)
    for relpath, document in propose.documents.items():
        _write(repo_root / relpath, document)
    # The next step now WAITS: its input is a flight's product, and the
    # driver never contacts the model.
    waiting = plan_round(state, 1, paths=paths, exists=exists)
    assert waiting.next_step is None
    assert waiting.blocked_on

    # -- the flight's own product, hand-written ---------------------------
    receipt = json.loads(
        (repo_root / paths["propose"]["writes"][2]).read_text(encoding="utf-8")
    )
    stem = f"{config.receipts_reldir}/round-01"
    responses = {}
    for index, contact in enumerate(receipt["contacts"]):
        if contact["family"] == "placebo":
            responses[contact["sample_id"]] = _placebo_response()
        elif refuse_second_slot and contact["k"] == 2:
            # A refused candidate is RECORDED, never repaired: this answer is
            # prose, which the strict parser rejects, and that slot then flies
            # the incumbent's descriptions for its target.
            responses[contact["sample_id"]] = "Sure! Here are my rewrites: ..."
        else:
            responses[contact["sample_id"]] = _valid_response()
    (repo_root / stem).mkdir(parents=True, exist_ok=True)
    (repo_root / f"{stem}/proposer-outputs.jsonl").write_text(
        "".join(
            json.dumps({"sample_id": sample_id, "text": text}) + "\n"
            for sample_id, text in sorted(responses.items())
        ),
        encoding="utf-8",
        newline="\n",
    )

    # -- (b) candidates ---------------------------------------------------
    assert plan_round(state, 1, paths=paths, exists=exists).next_step == "candidates"
    candidates = run_candidates_step(
        state,
        1,
        config=config,
        carrier=carrier,
        propose_receipt=receipt,
        responses=responses,
        repo_root=repo_root,
        fold_a_rows=len(carrier.fold_a_rows_of_target["castContent"]),
        fold_a_speech_seconds=16.0,
    )
    for relpath, document in candidates.documents.items():
        _write(repo_root / relpath, document)

    # -- the fold-A scores, hand-written ----------------------------------
    candidates_receipt = json.loads(
        (repo_root / paths["candidates"]["writes"][0]).read_text(encoding="utf-8")
    )
    fold_a_rows = carrier.fold_a_rows_of_target["castContent"]
    incumbent_rows = {row: index >= 3 for index, row in enumerate(fold_a_rows)}
    fold_a_scores = {
        "incumbent": _score_file(repo_root / f"{stem}/scores/foldA-incumbent.score.json", incumbent_rows)
    }
    for slot in sorted(candidates_receipt["portfolios"]):
        # k=1 (the proposer rewrite) saves the three rows the incumbent
        # missed; k=4 (the deterministic control) saves one and harms one.
        if slot == "1":
            rows = {row: True for row in fold_a_rows}
        else:
            rows = {row: index >= 2 for index, row in enumerate(fold_a_rows)}
        fold_a_scores[slot] = _score_file(
            repo_root / f"{stem}/scores/foldA-k{slot}.score.json", rows
        )
    _write(repo_root / f"{stem}/fold-a-scores.json", fold_a_scores)

    # -- (c) select -------------------------------------------------------
    assert plan_round(state, 1, paths=paths, exists=exists).next_step == "select"
    select = run_select_step(
        state,
        1,
        config=config,
        carrier=carrier,
        candidates_receipt=candidates_receipt,
        score_files=fold_a_scores,
        repo_root=repo_root,
        fold_b_rows=len(FOLD_B_TARGETED) + len(FOLD_B_BACKGROUND),
        fold_b_speech_seconds=32.0,
    )
    for relpath, document in select.documents.items():
        _write(repo_root / relpath, document)

    # -- the fold-B scores, hand-written ----------------------------------
    every_b = list(FOLD_B_TARGETED) + list(FOLD_B_BACKGROUND)
    incumbent_b = {row: row in FOLD_B_BACKGROUND for row in every_b}
    assembly_b = {row: True for row in every_b}
    fold_b_scores = {
        "incumbent": _score_file(
            repo_root / f"{stem}/scores/foldB-incumbent.score.json", incumbent_b
        ),
        "assembly": _score_file(
            repo_root / f"{stem}/scores/foldB-assembly.score.json", assembly_b
        ),
    }
    _write(repo_root / f"{stem}/fold-b-scores.json", fold_b_scores)

    # -- (d) confirm ------------------------------------------------------
    assert plan_round(state, 1, paths=paths, exists=exists).next_step == "confirm"
    selection_receipt = json.loads(
        (repo_root / paths["select"]["writes"][0]).read_text(encoding="utf-8")
    )
    confirm = run_confirm_step(
        state,
        1,
        config=config,
        carrier=carrier,
        selection_receipt=selection_receipt,
        score_files=fold_b_scores,
        receipts_dir=receipts_dir,
    )
    for relpath, document in confirm.documents.items():
        _write(repo_root / relpath, document)

    final = plan_round(state, 1, paths=paths, exists=exists)
    assert final.next_step is None and not final.blocked_on
    assert all(step.done for step in final.steps)
    return {
        "confirm": dict(confirm.summary),
        "state": confirm.state,
        "candidates_receipt": candidates_receipt,
        "selection_receipt": selection_receipt,
        "fold_a_scores": fold_a_scores,
        "repo_root": repo_root,
    }


# ---------------------------------------------------------------------------
# The dry run
# ---------------------------------------------------------------------------


def test_a_whole_round_runs_offline_and_accepts_the_assembly(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    summary = result["confirm"]
    assert summary["accepted"] is True
    assert summary["gain_pp"] > 0
    assert summary["stop"] is False
    state = result["state"]
    assert state.round == 1
    assert set(state.incumbent_overrides) == set(TOOLS)
    assert Path(summary["round_receipt"]).is_file()


def test_a_refused_candidate_is_recorded_and_never_repaired(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    harvest = result["candidates_receipt"]["harvest"]
    refusals = harvest["refusals"]
    assert refusals, "the k=2 slot was answered with prose and must be refused"
    assert all(refusal["k"] == 2 for refusal in refusals)
    assert "not strict JSON" in refusals[0]["reason"]
    # The refused slot flies no portfolio, and the surviving slots do.
    assert "2" not in result["candidates_receipt"]["portfolios"]
    assert {"1", "3", "4"} == set(result["candidates_receipt"]["portfolios"])


def test_the_placebo_slot_carries_no_cue(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    placebo = [
        candidate
        for candidate in result["candidates_receipt"]["harvest"]["candidates"]
        if candidate["family"] == "placebo"
    ]
    assert placebo and all(candidate["cue"] is None for candidate in placebo)


def test_replay_selection_reproduces_stage_one_from_the_score_files_alone(
    tmp_path,
) -> None:
    result = _run_round(tmp_path / "run")
    receipt = json.loads(
        Path(result["confirm"]["round_receipt"]).read_text(encoding="utf-8")
    )
    replay = replay_selection(receipt, result["fold_a_scores"])
    assert replay.matches, replay.mismatches


def test_a_second_run_over_the_same_inputs_is_byte_identical(tmp_path) -> None:
    first = _run_round(tmp_path / "a")["repo_root"]
    second = _run_round(tmp_path / "b")["repo_root"]
    written = sorted(
        path.relative_to(first).as_posix()
        for path in first.rglob("*")
        if path.is_file()
    )
    assert written == sorted(
        path.relative_to(second).as_posix() for path in second.rglob("*") if path.is_file()
    )
    # The two score INDEXES are the flight agent's own fixtures here and
    # name absolute score-file paths under this test's tmp_path, so they
    # differ between the two runs by construction. Everything the DRIVER
    # writes -- the roster, the three experiment fragments, the four step
    # receipts, the portfolio artifacts and fragments and the round receipt
    # -- must be byte-identical.
    fixtures = {
        "docs/checks/dry-run/round-01/fold-a-scores.json",
        "docs/checks/dry-run/round-01/fold-b-scores.json",
    }
    differing = [
        relpath
        for relpath in written
        if relpath not in fixtures
        and (first / relpath).read_bytes() != (second / relpath).read_bytes()
    ]
    assert differing == [], differing
    # And the round receipt's own digest -- the thing a reviewer cites -- is
    # the same on both runs.
    assert (first / "docs/checks/dry-run/evolution-round-01.json").read_bytes() == (
        second / "docs/checks/dry-run/evolution-round-01.json"
    ).read_bytes()


def test_a_landed_step_is_never_redone(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    config = _loop_config()
    repo_root = result["repo_root"]
    plan = plan_round(
        EvolutionState(round=0, incumbent_overrides={}).validate(),
        1,
        paths=config.round_paths(1),
        exists=lambda relpath: (repo_root / relpath).exists(),
    )
    assert plan.next_step is None
    assert [step.name for step in plan.steps] == list(ROUND_STEPS)
    assert all(step.done for step in plan.steps)


def test_a_missing_flight_product_blocks_rather_than_guesses(tmp_path) -> None:
    config = _loop_config()
    repo_root = _repo(tmp_path / "run", config)
    carrier = _carrier()
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    paths = config.round_paths(1)
    propose = run_propose_step(state, 1, config=config, carrier=carrier)
    for relpath, document in propose.documents.items():
        _write(repo_root / relpath, document)
    plan = plan_round(
        state, 1, paths=paths, exists=lambda relpath: (repo_root / relpath).exists()
    )
    assert plan.next_step is None
    assert plan.blocked_on == (
        f"{config.receipts_reldir}/round-01/proposer-outputs.jsonl",
    )


def test_the_propose_step_pins_a_prompt_digest_without_recording_any_text(
    tmp_path,
) -> None:
    config = _loop_config()
    _repo(tmp_path / "run", config)
    propose = run_propose_step(
        EvolutionState(round=0, incumbent_overrides={}).validate(),
        1,
        config=config,
        carrier=_carrier(),
    )
    receipt = propose.documents[config.round_paths(1)["propose"]["writes"][2]]
    assert receipt["contacts"]
    assert all(len(contact["prompt_sha256"]) == 64 for contact in receipt["contacts"])
    assert "synthetic request for" not in json.dumps(propose.documents)


def test_the_budget_check_refuses_a_flight_over_its_registered_ceiling() -> None:
    rows = [
        {
            "run/experiment id": "SAEA-TEST-EVO-FOLD-A",
            "consumed": "no",
            "calls": "100",
            "speech audio seconds": "1000",
        }
    ]
    assert check_ledger_budget(
        rows, run_id="SAEA-TEST-EVO-FOLD-A", calls=100, speech_seconds=1000
    )["within"]
    with pytest.raises(EvolutionError, match="over"):
        check_ledger_budget(
            rows, run_id="SAEA-TEST-EVO-FOLD-A", calls=101, speech_seconds=1000
        )
    with pytest.raises(EvolutionError, match="not consumed=no"):
        check_ledger_budget(
            [dict(rows[0], **{"consumed": "yes"})],
            run_id="SAEA-TEST-EVO-FOLD-A",
            calls=1,
            speech_seconds=1,
        )


# ---------------------------------------------------------------------------
# The sentinel line (owner decision, 2026-09-06)
# ---------------------------------------------------------------------------

SENTINEL_TARGETS = {"castContent": ["castContent", "playMedia"]}


def _sentinel_config() -> LoopConfig:
    document = json.loads(json.dumps(_loop_config_document()))
    document["sentinel_tools"] = {"castContent": ["playMedia"]}
    return LoopConfig.from_json(document)


def _deterministic_candidate(k: int) -> CandidateArtifact:
    artifact = CandidateArtifact(
        candidate_id="",
        family="deterministic",
        target_id="castContent",
        round=1,
        k=k,
        descriptions={
            "castContent": "Send media that is already playing to another screen.",
            "playMedia": "Start playing a named track or show on this device.",
        },
        cue=None,
        proposer_prompt_sha256=None,
        exemplar_ids=(),
    )
    return replace(artifact, candidate_id=artifact.expected_candidate_id()).validate()


def test_a_sentinel_row_is_reported_by_name_and_never_counted_as_a_reward(
    tmp_path,
) -> None:
    config = _sentinel_config()
    repo_root = _repo(tmp_path / "run", config)
    reward = tuple(FOLD_A_ROWS["castContent"])
    sentinel = tuple(FOLD_A_ROWS["playMedia"])
    carrier = CarrierMaterial(
        registry_rows=(),
        exemplar_pool={},
        media_facts={},
        exemplar_rows={},
        fold_a_rows_of_target={"castContent": reward},
        fold_b_targeted_rows=FOLD_B_TARGETED,
        fold_b_background_rows=FOLD_B_BACKGROUND,
        fold_a_sentinel_rows={"castContent": {"playMedia": sentinel}},
    )
    every = list(reward) + list(sentinel)
    # The incumbent misses one reward row and holds every sentinel row.
    incumbent = {row: row != reward[0] for row in every}
    # The candidate wins that reward row and BREAKS one sentinel row -- the
    # failure mode the sentinel exists to catch.
    arm = dict(incumbent)
    arm[reward[0]] = True
    arm[sentinel[0]] = False
    artifact = _deterministic_candidate(4)
    scores = {
        "incumbent": _score_file(repo_root / "scores/i.score.json", incumbent),
        "4": _score_file(repo_root / "scores/k4.score.json", arm),
    }
    result = run_select_step(
        EvolutionState(round=0, incumbent_overrides={}).validate(),
        1,
        config=config,
        carrier=carrier,
        candidates_receipt={
            "portfolios": {"4": {"k": 4}},
            "harvest": {"candidates": [artifact.as_json()]},
        },
        score_files=scores,
        repo_root=repo_root,
        fold_b_rows=len(FOLD_B_TARGETED) + len(FOLD_B_BACKGROUND),
        fold_b_speech_seconds=32.0,
    )
    receipt = result.documents[config.round_paths(1)["select"]["writes"][0]]

    # Stage one saw the reward rows only: four, not eight.
    assert receipt["selection"]["decisions"]["castContent"]["n_rows"] == len(reward)
    assert receipt["selection"]["rows_of_target"]["castContent"] == sorted(reward)

    # And the sentinel harm is reported by name, without changing the decision.
    line = receipt["sentinel_harms"]
    block = line["by_target"]["castContent"]["by_k"]["4"]
    assert block["harms"] == 1
    assert block["harmed"] == [{"sample_id": sentinel[0], "tool": "playMedia"}]
    assert result.summary["sentinel_harms"] == {"castContent": {"4": 1}}


def test_a_loop_with_no_sentinel_writes_the_line_as_null(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    assert result["selection_receipt"]["sentinel_harms"] is None


def _fold_document() -> dict:
    return {
        "items": [
            {"sample_id": row, "stratum": tool}
            for tool, rows in FOLD_A_ROWS.items()
            for row in rows
        ]
        + [
            {"sample_id": f"bg:{index:06d}", "stratum": "background:tier1_direct"}
            for index in range(3)
        ]
    }


def test_a_sentinel_tools_rows_leave_the_reward_slice_and_join_the_background() -> None:
    document = _fold_document()
    sentinels = {"castContent": ["playMedia"]}
    rewards = rows_of_target_from_roster(document, SENTINEL_TARGETS, sentinels)
    assert rewards == {"castContent": tuple(sorted(FOLD_A_ROWS["castContent"]))}
    targeted, background = _split_fold_rows(document, SENTINEL_TARGETS, sentinels)
    assert targeted == tuple(sorted(FOLD_A_ROWS["castContent"]))
    # Both the sentinel rows and the tier-stratified rows are background.
    assert set(FOLD_A_ROWS["playMedia"]) <= set(background)
    assert len(background) == len(FOLD_A_ROWS["playMedia"]) + 3
    assert sentinel_rows_from_roster(document, SENTINEL_TARGETS, sentinels) == {
        "castContent": {"playMedia": tuple(sorted(FOLD_A_ROWS["playMedia"]))}
    }


def test_without_sentinels_the_reward_slice_is_the_whole_target() -> None:
    document = _fold_document()
    rewards = rows_of_target_from_roster(document, SENTINEL_TARGETS)
    assert len(rewards["castContent"]) == 8


def test_a_sentinel_the_fold_never_drew_is_refused_rather_than_reported_empty() -> None:
    with pytest.raises(EvolutionError, match="disagree"):
        sentinel_rows_from_roster(
            _fold_document(), SENTINEL_TARGETS, {"castContent": ["absentTool"]}
        )


# ---------------------------------------------------------------------------
# The null-rewrite form gate (track E3e, 2026-09-07)
# ---------------------------------------------------------------------------


def _null_rewrite_response(carrier: CarrierMaterial) -> str:
    """The failure EVO-S1 round 1 actually produced, in A2T's family: the
    proposer hands back the incumbent's own descriptions, word for word."""

    incumbent = {
        str(row["tool_name"]): str(row["description"])
        for row in carrier.registry_rows
        if str(row["tool_name"]) in TOOLS
    }
    return json.dumps({"cue": "they already read differently", "descriptions": incumbent})


def test_a_candidate_that_renders_to_the_incumbent_is_refused_as_a_null_rewrite(
    tmp_path,
) -> None:
    """A rewrite that changes no rendered byte is not a rewrite. It is refused
    at the candidates step, never admitted and never flown, and its slot falls
    back to the existing "refused candidate flies no portfolio" path."""

    config = _loop_config()
    repo_root = _repo(tmp_path / "run", config)
    carrier = _carrier()
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    propose = run_propose_step(state, 1, config=config, carrier=carrier)
    receipt = propose.documents[config.round_paths(1)["propose"]["writes"][2]]

    responses = {}
    for contact in receipt["contacts"]:
        if contact["family"] == "placebo":
            responses[contact["sample_id"]] = _placebo_response()
        elif contact["k"] == 1:
            responses[contact["sample_id"]] = _null_rewrite_response(carrier)
        else:
            responses[contact["sample_id"]] = _valid_response()

    candidates = run_candidates_step(
        state,
        1,
        config=config,
        carrier=carrier,
        propose_receipt=receipt,
        responses=responses,
        repo_root=repo_root,
        fold_a_rows=len(carrier.fold_a_rows_of_target["castContent"]),
        fold_a_speech_seconds=16.0,
    )
    document = candidates.documents[config.round_paths(1)["candidates"]["writes"][0]]
    refused = [
        record
        for record in document["harvest"]["refusals"]
        if record.get("gate") == NULL_REWRITE_GATE
    ]
    assert len(refused) == 1
    assert refused[0]["k"] == 1 and refused[0]["target_id"] == "castContent"
    assert refused[0]["reason"].startswith(f"{NULL_REWRITE_GATE}:")
    assert candidates.summary["null_rewrites_refused"] == 1

    # Never admitted: no candidate at slot 1, and therefore no k=1 portfolio,
    # because that target is this dry run's only target.
    assert all(
        candidate["k"] != 1 for candidate in document["harvest"]["candidates"]
    )
    assert "1" not in document["portfolios"]

    # The check is recorded for every candidate that reached it, refused or
    # not, so a reviewer reads the digests rather than trusting the verdict.
    checks = {record["candidate_id"]: record for record in document["null_rewrite_checks"]}
    assert checks and any(record["null_rewrite"] for record in checks.values())
    for record in checks.values():
        assert (record["candidate_rendered_sha256"] == record["incumbent_rendered_sha256"]) is (
            record["null_rewrite"]
        )


def test_the_propose_receipt_names_this_familys_unchanged_instruction_revision(
    tmp_path,
) -> None:
    """EVO-A1's instruction did not move: its strict-JSON contract never lost a
    draw to the blank-line habit, so it stays ``proposer-instruction-v1`` and
    its candidate ids stay comparable across the E3e change."""

    config = _loop_config()
    _repo(tmp_path / "run", config)
    propose = run_propose_step(
        EvolutionState(round=0, incumbent_overrides={}).validate(),
        1,
        config=config,
        carrier=_carrier(),
    )
    receipt = propose.documents[config.round_paths(1)["propose"]["writes"][2]]
    assert receipt["proposer_instruction_version"] == "proposer-instruction-v1"
