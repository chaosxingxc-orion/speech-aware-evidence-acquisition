"""The offline end-to-end dry run of one EVO-S1 round (track E3d).

The SLURP twin of ``test_a2t_evolution_round_driver``, and deliberately the
same shape: a synthetic slot schema (``A_0`` plus the unfloored TRAIN table
its numbers are re-derived from), synthetic exemplar and fold rosters, a
HAND-WRITTEN sealed proposer manifest (one valid block set, one refused) and
fake per-sample score files carrying ``slot_f1_exact_f1`` beside the Word-F1
that is reported next to it, driven through a whole round by
``rails.evolution``'s pure step functions.

What this run proves that the A2T one cannot: a target is ONE scenario (the
single-member relaxation), the artifact is a per-intent BLOCK consumed
through ``phase_material.slots.state_fill`` rather than a task-instruction
fill, one portfolio gets TWO fragment variants because each fold binds its
own sealed intent manifest, both controls are deterministic (the shares-only
floor and the token-matched form twin, neither of which makes a contact), and
stage two is bounded by the per-scenario harm bound instead of a background
population.

Zero model contacts, zero carrier reads, zero network. Every schema number,
every utterance and every filler here is synthetic: no real SLURP sentence,
gold entity or TRAIN count appears in this repository. The form twin is
priced with a WORD counter, which is exactly the estimator a registered
candidate is refused for using -- legal in a test, never in a flight.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.data.slurp import (
    SlurpIntentSlots,
    SlurpIntentSlotSchema,
)
from speech_aware_evidence_acquisition.rails.evolution import (
    A2T_FOLD_A_SPEECH_SECONDS,
    A2T_FOLD_B_SPEECH_SECONDS,
    A2T_FOLD_ROWS,
    ROUND_STEPS,
    CarrierMaterial,
    EvolutionError,
    EvolutionState,
    LoopConfig,
    fragment_stem,
    plan_round,
    replay_selection,
    run_candidates_step,
    run_confirm_step,
    run_propose_step,
    run_select_step,
)
from speech_aware_evidence_acquisition.rails.proposer import (
    NULL_REWRITE_GATE,
    slurp_block_texts,
)

CARRIER = "slurp"
SCORER = "slurp-slu-official"
METRIC = "slot_f1_exact_f1"
READ_METRIC = "slu_f1_word_f1"

#: Three synthetic scenarios, each its own target with ONE stratum member --
#: the relaxation this cell needs, and the normal case on SLURP.
SCENARIOS = ("alarm", "news", "weather")
TARGETS = {scenario: [scenario] for scenario in SCENARIOS}
#: The intents each scenario owns, in the order the proposer is shown them.
ARTIFACT_KEYS = {
    "alarm": ["alarm_set", "alarm_query", "alarm_remove"],
    "news": ["news_query"],
    "weather": ["weather_query"],
}
INTENTS = tuple(intent for keys in ARTIFACT_KEYS.values() for intent in keys)

#: ``intent -> (utterances, mentions, ((entity type, mentions, fillers), ...))``.
#: The unfloored table is the whole thing; ``A_0`` keeps the types at or above
#: a 0.15 share, exactly as the real mining does.
_TRAIN: Mapping[str, tuple[int, int, tuple[tuple[str, int, tuple[str, ...]], ...]]] = {
    "alarm_set": (
        40,
        30,
        (
            ("time", 18, ("seven am", "half past six")),
            ("date", 9, ("tomorrow",)),
            ("event_name", 3, ("stand up",)),
        ),
    ),
    "alarm_query": (20, 10, (("time", 7, ("morning",)), ("date", 3, ("today",)))),
    "alarm_remove": (15, 8, (("time", 5, ("eight am",)), ("date", 3, ("friday",)))),
    "news_query": (25, 12, (("news_topic", 9, ("local sport",)), ("place_name", 3, ("york",)))),
    "weather_query": (
        30,
        20,
        (("place_name", 12, ("boston",)), ("date", 8, ("this weekend",))),
    ),
}
_MIN_SHARE = 0.15
ENTITY_TYPES = ("date", "event_name", "news_topic", "place_name", "time")

FOLD_A_ROWS = {
    scenario: tuple(f"foldA:{scenario}:{index:03d}" for index in range(1, 5))
    for scenario in SCENARIOS
}
FOLD_B_ROWS = {
    scenario: tuple(f"foldB:{scenario}:{index:03d}" for index in range(1, 7))
    for scenario in SCENARIOS
}


# ---------------------------------------------------------------------------
# The synthetic world
# ---------------------------------------------------------------------------


def _schema(*, floored: bool) -> SlurpIntentSlotSchema:
    intents: dict[str, SlurpIntentSlots] = {}
    for intent, (n, mentions, rows) in _TRAIN.items():
        kept = [
            (entity_type, count, count / mentions)
            for entity_type, count, _fillers in rows
            if not floored or count / mentions >= _MIN_SHARE
        ]
        fillers = {
            entity_type: tuple(examples)
            for entity_type, _count, examples in rows
            if any(entity_type == name for name, _c, _s in kept)
        }
        intents[intent] = SlurpIntentSlots(
            intent=intent, n=n, mentions=mentions, types=tuple(kept), fillers=fillers
        )
    return SlurpIntentSlotSchema(
        schema_id="synthetic-slot-schema-v1",
        source_split="train",
        source_identity_hash="f" * 64,
        utterance_count=sum(n for n, _m, _rows in _TRAIN.values()),
        min_share=_MIN_SHARE if floored else 0.0,
        examples_per_type=5,
        intents=intents,
    )


def _pool_ids(scenario: str) -> list[str]:
    base = {"alarm": 100, "news": 200, "weather": 300}[scenario]
    return [f"slurp:train:{base + offset:06d}:synthetic-{offset}" for offset in range(3)]


def _exemplar_rows() -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for scenario in SCENARIOS:
        intents = ARTIFACT_KEYS[scenario]
        for offset, sample_id in enumerate(_pool_ids(scenario)):
            intent = intents[offset % len(intents)]
            entity_type = _TRAIN[intent][2][0][0]
            rows[sample_id] = {
                "utterance_id": sample_id.rsplit(":", 1)[0],
                "scenario": scenario,
                "action": intent.split("_", 1)[1],
                "intent": intent,
                "sentence": f"synthetic spoken command {offset} for {intent}",
                "entities": ((entity_type, f"synthetic filler {offset}"),),
                "media_relpath": f"datasets/slurp/audio/{sample_id.rsplit(':', 1)[1]}.flac",
                "audio_seconds": 2.0,
                "audio_sha256": "0" * 64,
            }
    return rows


def _carrier() -> CarrierMaterial:
    rows = _exemplar_rows()
    return CarrierMaterial(
        registry_rows=(),
        exemplar_pool={
            scenario: tuple(_pool_ids(scenario)) for scenario in SCENARIOS
        },
        media_facts={
            sample_id: {
                "media_relpath": row["media_relpath"],
                "audio_seconds": row["audio_seconds"],
                "audio_sha256": row["audio_sha256"],
            }
            for sample_id, row in rows.items()
        },
        exemplar_rows=rows,
        fold_a_rows_of_target={
            scenario: FOLD_A_ROWS[scenario] for scenario in SCENARIOS
        },
        fold_b_targeted_rows=tuple(
            row for scenario in SCENARIOS for row in FOLD_B_ROWS[scenario]
        ),
        fold_b_background_rows=(),
        slot_schema=_schema(floored=True),
        unfloored_schema=_schema(floored=False),
        entity_type_names=ENTITY_TYPES,
        fold_b_rows_of_target={
            scenario: FOLD_B_ROWS[scenario] for scenario in SCENARIOS
        },
    )


def _loop_config() -> LoopConfig:
    return LoopConfig.from_json(_loop_config_document())


def _loop_config_document() -> dict:
    return (
        {
            "carrier_lock_key": CARRIER,
            "target_kind": "scenario",
            "artifact_family": "slurp-slot-schema",
            "targets": TARGETS,
            "artifact_keys": ARTIFACT_KEYS,
            "arm": "speech-feature-query",
            "cell_label": "EVO-S1-DRY-RUN",
            "preregistration": "docs/readiness/synthetic.md",
            "state_fill": "slurp-evolved-slot-schema-for-state",
            "state_fill_phase": "slots",
            "deterministic_placebo": True,
            "fold_predecessors": {
                "fold-a": {
                    "manifest_relpath": "runs/SYNTH/attempt-intent-a/run-manifest.json",
                    "manifest_sha256": "a" * 64,
                    "producer_policy_id": "SYNTH-INTENT",
                },
                "fold-b": {
                    "manifest_relpath": "runs/SYNTH/attempt-intent-b/run-manifest.json",
                    "manifest_sha256": "b" * 64,
                    "producer_policy_id": "SYNTH-INTENT",
                },
            },
            "harm_bound": {"max_net_harm_rows": 1, "unadmitted_tolerance_pp": -1.0},
            "decontamination": {
                "row": "SAEA-TEST-EVOS-DECONTAMINATION",
                "evaluation_sentence_texts": "synthetic devel sentences",
                "baseline_filler_texts": "A_0's own fillers, exempt",
                "exemplar_texts": "counted, never gated",
            },
            "proposer_run_id": "SAEA-TEST-EVOS-PROPOSER",
            "fold_a_run_id": "SAEA-TEST-EVOS-FOLD-A",
            "fold_b_run_id": "SAEA-TEST-EVOS-FOLD-B",
            "base_fragment": "evos-dry-run-base",
            "model_fragment": "m",
            "fold_a_dataset_fragment": "fold-a",
            "fold_b_dataset_fragment": "fold-b",
            "metric": METRIC,
            "scorer_id": SCORER,
            "proposer_slots": [1, 2],
            "placebo_slot": 5,
            "deterministic_slot": 4,
            "exemplars_per_scenario": 2,
            "seed": 20260903,
            "max_rounds": 4,
            # Scaled to a four-row-per-scenario dry run; the flight's own
            # gates are the preregistered 4/1/3 and live in the committed loop
            # config, never here.
            "gates": {"saves": 2, "harms": 1, "net": 1},
            "n_replicates": 200,
            "receipts_reldir": "docs/checks/evos-dry-run",
            "rosters_reldir": "docs/receipts/rosters",
            "experiments_reldir": "configs/experiment",
            "fragment_reldir": "configs/baseline",
            "artifact_reldir": "configs/knowledge/evos-dry-run",
            "slug": "evos-dry-run",
        }
    )


def _word_counter(text: str) -> int:
    """The test's stand-in for the resident server's ``/tokenize``.

    A word count, which is precisely the class of estimator
    ``validate_slurp_candidate_artifact`` refuses for a registered candidate
    (``allow_estimator``). It is legal here because nothing this test prices
    ever flies, and it is a WORD count rather than a character count because
    the form twin pads by one word at a time: an exact match is reachable, so
    the padding loop is exercised rather than short-circuited.
    """

    return len(text.split())


def _write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _repo(root: Path, config: LoopConfig, *, fill_params: Mapping | None = None) -> Path:
    """A synthetic repository carrying only the base fragment the writer
    copies -- and it must already BE a state-fill arm bound to a sealed
    predecessor, because an evolved arm may differ from the admitted incumbent
    by the artifact and by nothing else."""

    _write(
        root / "configs" / "baseline" / f"{config.base_fragment}.json",
        {
            "arm": "speech-feature-query",
            "policy": "phase-slots-given-intent-v1",
            "evidence_source": "none",
            "scorers": ["slurp-slu-official"],
            "phase_material": {
                "slots": {
                    "phase": "slots",
                    "purpose": "slot-extraction-given-intent",
                    "instruction_template": "probes/slurp_phase_slots.txt",
                    "predecessor_binding": "sealed-manifest",
                    "state_fill": "slurp-intent-slot-schema-for-state",
                    **({"fill_params": dict(fill_params)} if fill_params else {}),
                }
            },
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
    path: Path, rows: Mapping[str, float], questions: Mapping[str, tuple] | None = None
) -> str:
    """One ``<job_id>.score.json`` as ``core.scoring_batch`` writes it, with
    the READ metric recorded beside the reward exactly as every round receipt
    must report it, and beside the run manifest and sealed outputs it names."""

    manifest = _sealed_trace(path, rows, questions or {})
    _write(
        path,
        {
            "manifest": manifest,
            "verified": True,
            "scores": {
                SCORER: {
                    "aggregate": {
                        METRIC: sum(rows.values()) / len(rows),
                        READ_METRIC: sum(rows.values()) / len(rows),
                    },
                    "per_sample": [
                        {
                            "sample_id": sample_id,
                            METRIC: float(value),
                            READ_METRIC: float(value),
                        }
                        for sample_id, value in sorted(rows.items())
                    ],
                }
            },
        },
    )
    return str(path)


# ---------------------------------------------------------------------------
# The hand-written sealed proposer manifest
# ---------------------------------------------------------------------------


def _block_lines(intent: str, fillers_of: Mapping[str, tuple[str, ...]]) -> list[str]:
    n, mentions, rows = _TRAIN[intent]
    lines = [f"== {intent} == {n} TRAIN utterances, {mentions} slot mentions"]
    for entity_type, count, _examples in rows:
        if entity_type not in fillers_of:
            continue
        share = count / mentions
        spoken = "; ".join(fillers_of[entity_type])
        lines.append(f"- {entity_type} ({share * 100:.1f} percent of slot mentions): {spoken}")
    return lines


def _rewritten(intents: tuple[str, ...]) -> str:
    """A legal answer: the incumbent types, kept in order, with one filler
    rewritten into a spoken form. The share the proposer writes here is
    discarded and re-derived from TRAIN, which is what makes a hallucinated
    percentage unable to reach a flight."""

    lines: list[str] = []
    for intent in intents:
        fillers = {
            entity_type: tuple(f"{filler} please" for filler in examples)
            for entity_type, count, examples in _TRAIN[intent][2]
            if count / _TRAIN[intent][1] >= _MIN_SHARE
        }
        lines.extend(_block_lines(intent, fillers))
    return "\n".join(lines) + "\n"


def _responses(receipt: Mapping[str, object], *, refuse_second_slot: bool) -> dict[str, str]:
    responses: dict[str, str] = {}
    for contact in receipt["contacts"]:  # type: ignore[index]
        intents = tuple(str(intent) for intent in contact["artifact_keys"])
        if refuse_second_slot and contact["k"] == 2:
            # A refused candidate is RECORDED, never repaired: prose is
            # outside the block grammar, so that slot flies the incumbent's
            # blocks for its scenario.
            responses[contact["sample_id"]] = "Sure! Here are the rewritten blocks:"
        else:
            responses[contact["sample_id"]] = _rewritten(intents)
    return responses


# ---------------------------------------------------------------------------
# One whole round
# ---------------------------------------------------------------------------


def _fold_a_scores(scenario_rows: Mapping[str, tuple[str, ...]], slot: str) -> dict[str, float]:
    """Fold-A per-row rewards. The proposer slot saves both misses on
    ``alarm`` and ``weather`` and moves nothing on ``news``; the shares-only
    floor harms one row; the form twin reproduces the incumbent."""

    rows: dict[str, float] = {}
    for scenario, ids in scenario_rows.items():
        for index, sample_id in enumerate(ids):
            if slot == "incumbent":
                value = 1.0 if index >= 2 else 0.0
            elif slot == "1":
                value = 0.0 if (scenario == "news" and index < 2) else 1.0
            elif slot == "4":
                value = 1.0 if index >= 3 else 0.0
            else:
                value = 1.0 if index >= 2 else 0.0
            rows[sample_id] = value
    return rows


def _fold_b_scores(*, arm: str, harm_case: bool) -> dict[str, float]:
    rows: dict[str, float] = {}
    for scenario, ids in FOLD_B_ROWS.items():
        for index, sample_id in enumerate(ids):
            incumbent = 1.0 if index >= 3 else 0.0
            if scenario == "news":
                value = incumbent
            elif arm == "incumbent":
                value = incumbent
            elif harm_case and scenario == "alarm":
                # The assembly breaks two rows the incumbent had right and
                # saves none: harms - saves = 2, over the bound of 1.
                value = 0.0 if index >= 4 else incumbent
            else:
                value = 1.0
            rows[sample_id] = value
    return rows


def _fold_b_digests(arm: str) -> dict[str, tuple[str, str]]:
    """One fold-B arm's sealed question and response, per row.

    The three cases the round receipt's noise floor has to separate, built by
    hand: ``alarm`` is the scenario the assembly rewrote, so its six rows were
    asked a DIFFERENT question; ``news`` and ``weather`` kept the incumbent's
    question byte for byte, and three rows of each answered differently anyway.
    That last group is the decoder noise floor -- the same phenomenon EVO-S1
    round 1 measured at 286 of 1,019 byte-identically asked rows.
    """

    digests: dict[str, tuple[str, str]] = {}
    for scenario, ids in FOLD_B_ROWS.items():
        for index, sample_id in enumerate(ids):
            changed = arm == "assembly" and scenario == "alarm"
            flipped = arm == "assembly" and (changed or index < 3)
            digests[sample_id] = (
                f"ask|assembly|{sample_id}" if changed else f"ask|{sample_id}",
                _sha(f"answer|assembly|{sample_id}" if flipped else f"answer|{sample_id}"),
            )
    return digests


def _run_round(
    root: Path,
    *,
    refuse_second_slot: bool = True,
    harm_case: bool = False,
    missing_trace: bool = False,
) -> dict[str, object]:
    config = _loop_config()
    repo_root = _repo(root, config)
    carrier = _carrier()
    receipts_dir = repo_root / config.receipts_reldir
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    paths = config.round_paths(1)

    def exists(relpath: str) -> bool:
        return (repo_root / relpath).exists()

    # -- (a) propose ------------------------------------------------------
    assert plan_round(state, 1, paths=paths, exists=exists).next_step == "propose"
    propose = run_propose_step(state, 1, config=config, carrier=carrier)
    for relpath, document in propose.documents.items():
        _write(repo_root / relpath, document)
    waiting = plan_round(state, 1, paths=paths, exists=exists)
    assert waiting.next_step is None and waiting.blocked_on

    # -- the flight's own product, hand-written ---------------------------
    receipt = json.loads((repo_root / paths["propose"]["writes"][2]).read_text("utf-8"))
    stem = f"{config.receipts_reldir}/round-01"
    responses = _responses(receipt, refuse_second_slot=refuse_second_slot)
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
        fold_a_rows=sum(len(rows) for rows in FOLD_A_ROWS.values()),
        fold_a_speech_seconds=24.0,
        token_counter=_word_counter,
    )
    for relpath, document in candidates.documents.items():
        _write(repo_root / relpath, document)

    # -- the fold-A scores, hand-written ----------------------------------
    candidates_receipt = json.loads(
        (repo_root / paths["candidates"]["writes"][0]).read_text("utf-8")
    )
    fold_a_scores = {
        "incumbent": _score_file(
            repo_root / f"{stem}/scores/foldA-incumbent.score.json",
            _fold_a_scores(FOLD_A_ROWS, "incumbent"),
        )
    }
    for slot in sorted(candidates_receipt["portfolios"]):
        fold_a_scores[slot] = _score_file(
            repo_root / f"{stem}/scores/foldA-k{slot}.score.json",
            _fold_a_scores(FOLD_A_ROWS, slot),
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
        fold_b_rows=sum(len(rows) for rows in FOLD_B_ROWS.values()),
        fold_b_speech_seconds=36.0,
    )
    for relpath, document in select.documents.items():
        _write(repo_root / relpath, document)

    # -- the fold-B scores, hand-written ----------------------------------
    fold_b_scores = {
        "incumbent": _score_file(
            repo_root / f"{stem}/scores/foldB-incumbent.score.json",
            _fold_b_scores(arm="incumbent", harm_case=harm_case),
            _fold_b_digests("incumbent"),
        ),
        "assembly": _score_file(
            repo_root / f"{stem}/scores/foldB-assembly.score.json",
            _fold_b_scores(arm="assembly", harm_case=harm_case),
            _fold_b_digests("assembly"),
        ),
    }
    if missing_trace:
        for name in ("foldB-incumbent", "foldB-assembly"):
            (repo_root / f"{stem}/scores/{name}.run-manifest.json").unlink()
    _write(repo_root / f"{stem}/fold-b-scores.json", fold_b_scores)

    # -- (d) confirm ------------------------------------------------------
    assert plan_round(state, 1, paths=paths, exists=exists).next_step == "confirm"
    selection_receipt = json.loads(
        (repo_root / paths["select"]["writes"][0]).read_text("utf-8")
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
        "config": config,
        "confirm": dict(confirm.summary),
        "state": confirm.state,
        "propose_receipt": receipt,
        "candidates_receipt": candidates_receipt,
        "selection_receipt": selection_receipt,
        "confirmation": json.loads(
            (repo_root / paths["confirm"]["writes"][0]).read_text("utf-8")
        ),
        "fold_a_scores": fold_a_scores,
        "repo_root": repo_root,
    }


# ---------------------------------------------------------------------------
# The dry run
# ---------------------------------------------------------------------------


def test_a_whole_slurp_round_runs_offline_and_accepts_the_assembly(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    summary = result["confirm"]
    assert summary["accepted"] is True
    assert summary["gain_pp"] > 0
    assert summary["stop"] is False
    state = result["state"]
    assert state.round == 1
    # A_1 carries the rewritten BLOCKS of the admitted scenarios' covered
    # intents -- objects, not text -- and leaves every other intent at A_0.
    overrides = set(state.incumbent_overrides)
    assert overrides <= set(INTENTS)
    assert "weather_query" in overrides
    assert "news_query" not in overrides, "news was not admitted at stage one"
    assert len(overrides & set(ARTIFACT_KEYS["alarm"])) == 2, (
        "M = 2 covers two of alarm's three intents, and the third keeps A_0"
    )
    assert all(
        set(block) == {"types"} for block in state.incumbent_overrides.values()
    )
    assert Path(summary["round_receipt"]).is_file()


def test_a_single_member_scenario_target_is_admitted(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    targets = result["propose_receipt"]["targets"]
    assert targets == {scenario: [scenario] for scenario in SCENARIOS}
    assert result["selection_receipt"]["admitted_targets"] == ["alarm", "weather"]


def test_each_contact_asks_only_for_the_intents_its_draw_covered(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    contacts = result["propose_receipt"]["contacts"]
    assert contacts
    for contact in contacts:
        target = contact["target_id"]
        keys = contact["artifact_keys"]
        assert keys, "a contact that covered no intent must not be planned"
        assert set(keys) <= set(ARTIFACT_KEYS[target])
        assert keys == [intent for intent in ARTIFACT_KEYS[target] if intent in keys]
    # M = 2 here against alarm's two intents, so at least one alarm draw
    # covers a single intent and leaves the other at the incumbent block.
    assert any(
        len(contact["artifact_keys"]) < len(ARTIFACT_KEYS[contact["target_id"]])
        for contact in contacts
    )


def test_both_controls_are_deterministic_and_cost_no_contact(tmp_path) -> None:
    """``K_1 = 5`` costs three contacts per scenario, not five: the
    shares-only floor and the form twin are string transformations of the
    incumbent, so neither is planned as a draw and neither is harvested."""

    result = _run_round(tmp_path / "run")
    contacts = result["propose_receipt"]["contacts"]
    assert {contact["family"] for contact in contacts} == {"proposer"}
    assert result["propose_receipt"]["placebo_slot"] is None
    assert len(contacts) == len(SCENARIOS) * 2, "two proposer slots per scenario"
    harvested = {
        candidate["family"]
        for candidate in result["candidates_receipt"]["harvest"]["candidates"]
    }
    assert harvested == {"proposer"}
    # The two control slots nevertheless fly, built with no contact at all.
    assert {"4", "5"} <= set(result["candidates_receipt"]["portfolios"])


def test_the_form_twin_matches_the_incumbent_block_token_for_token(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    portfolios = result["candidates_receipt"]["portfolios"]
    twin = portfolios["5"]["overrides"]
    incumbent_blocks = {
        intent: {
            "types": [
                {
                    "entity_type": entity_type,
                    "fillers": list(_TRAIN[intent][2][index][2]),
                }
                for index, (entity_type, count, _f) in enumerate(_TRAIN[intent][2])
                if count / _TRAIN[intent][1] >= _MIN_SHARE
            ]
        }
        for intent in INTENTS
    }
    for intent, block in twin.items():
        listed = [entry["entity_type"] for entry in block["types"]]
        expected = [entry["entity_type"] for entry in incumbent_blocks[intent]["types"]]
        assert listed == expected, "the twin keeps the type list and its order"
        assert [len(entry["fillers"]) for entry in block["types"]] == [
            len(entry["fillers"]) for entry in incumbent_blocks[intent]["types"]
        ]


def test_the_shares_only_control_deletes_every_filler(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    floor = result["candidates_receipt"]["portfolios"]["4"]["overrides"]
    assert floor
    for block in floor.values():
        assert block["types"]
        assert all(entry["fillers"] == [] for entry in block["types"])


def test_a_refused_block_set_is_recorded_and_never_repaired(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    refusals = result["candidates_receipt"]["harvest"]["refusals"]
    assert refusals, "the k=2 slot was answered with prose and must be refused"
    assert all(refusal["k"] == 2 for refusal in refusals)
    assert "outside the block grammar" in refusals[0]["reason"]
    assert "2" not in result["candidates_receipt"]["portfolios"]
    assert {"1", "4", "5"} == set(result["candidates_receipt"]["portfolios"])


def test_a_candidate_never_writes_a_number(tmp_path) -> None:
    """The proposer's rewrite carries no count and no share: the artifact is
    the ordered type list and the fillers, and every number in a rendered
    block comes back from the unfloored TRAIN table."""

    result = _run_round(tmp_path / "run")
    for candidate in result["candidates_receipt"]["harvest"]["candidates"]:
        for block in candidate["descriptions"].values():
            assert set(block) == {"types"}
            for entry in block["types"]:
                assert set(entry) == {"entity_type", "fillers"}


def test_one_portfolio_gets_one_fragment_per_fold(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    config = result["config"]
    repo_root = result["repo_root"]
    portfolios = result["candidates_receipt"]["portfolios"]
    for slot, portfolio in portfolios.items():
        sha = portfolio["portfolio_sha256"]
        variants = {
            fold: repo_root
            / config.fragment_reldir
            / f"{fragment_stem(sha, artifact_family=config.artifact_family, fold=fold)}.json"
            for fold in ("fold-a", "fold-b")
        }
        for fold, path in variants.items():
            assert path.is_file(), f"slot {slot} has no {fold} fragment"
            fragment = json.loads(path.read_text("utf-8"))
            phase = fragment["phase_material"]["slots"]
            assert phase["state_fill"] == "slurp-evolved-slot-schema-for-state"
            assert phase["predecessor_binding"] == "sealed-manifest"
            assert phase["predecessor_source"] == config.fold_predecessors[fold]
            assert phase["fill_params"]["artifact_sha256"]
            artifact = repo_root / phase["fill_params"]["artifact_relpath"]
            assert artifact.is_file()
            assert "task_instruction_fill" not in fragment
        assert (
            json.loads(variants["fold-a"].read_text("utf-8"))["phase_material"]["slots"][
                "fill_params"
            ]
            == json.loads(variants["fold-b"].read_text("utf-8"))["phase_material"][
                "slots"
            ]["fill_params"]
        ), "the two variants differ by the sealed predecessor and by nothing else"


def test_the_confirmation_reports_all_three_parts_of_the_harm_bound(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    confirmation = result["confirmation"]["confirmation"]
    assert confirmation["background"] is not None
    assert confirmation["harm_bound"] == {
        "max_net_harm_rows": 1,
        "unadmitted_tolerance_pp": -1.0,
        "harms_per_rows": 30,
    }
    per_target = {record["target_id"]: record for record in confirmation["per_target"]}
    assert set(per_target) == {"alarm", "weather", "(unadmitted, pooled)"}
    for scenario in ("alarm", "weather"):
        record = per_target[scenario]
        assert record["admitted"] is True
        assert record["n"] == len(FOLD_B_ROWS[scenario])
        # Six synthetic rows is under one 30-row unit, so the rate floors at
        # the base count and this world reads the old absolute bound.
        assert record["net_harm_rows_allowed"] == 1
        assert record["net_harm_rows"] <= 1
        assert record["ci90_low_pp"] is not None
        assert record["within_harm_bound"] is True
    pooled = per_target["(unadmitted, pooled)"]
    assert pooled["admitted"] is False
    assert pooled["n"] == len(FOLD_B_ROWS["news"])
    assert "pooled targeted CI90 lower bound" in confirmation["reason"]
    assert "unadmitted pooled delta" in confirmation["reason"]


def test_the_per_scenario_harm_bound_rejects_an_assembly_that_breaks_one(
    tmp_path,
) -> None:
    result = _run_round(tmp_path / "run", harm_case=True)
    summary = result["confirm"]
    assert summary["accepted"] is False
    confirmation = result["confirmation"]["confirmation"]
    assert "scenario(s) over the harm bound: alarm" in confirmation["reason"]
    per_target = {record["target_id"]: record for record in confirmation["per_target"]}
    assert per_target["alarm"]["within_harm_bound"] is False
    assert per_target["alarm"]["net_harm_rows"] > 1
    assert per_target["weather"]["within_harm_bound"] is True
    # A rejected round keeps A_0 whole.
    assert result["state"].incumbent_overrides == {}


def test_the_receipt_records_this_cell_s_own_decontamination_row(tmp_path) -> None:
    """A receipt that inherited EVO-A1's paragraph would describe a gate over
    a tool registry this cell does not have."""

    result = _run_round(tmp_path / "run")
    recorded = result["candidates_receipt"]["decontamination_inputs"]
    assert recorded["row"] == "SAEA-TEST-EVOS-DECONTAMINATION"
    assert recorded["ngram"] == 6
    assert "registry" not in json.dumps(recorded).lower()


def test_replay_selection_reproduces_stage_one_from_the_score_files_alone(
    tmp_path,
) -> None:
    result = _run_round(tmp_path / "run")
    receipt = json.loads(Path(result["confirm"]["round_receipt"]).read_text("utf-8"))
    replay = replay_selection(receipt, result["fold_a_scores"])
    assert replay.matches, replay.mismatches


def test_a_second_run_over_the_same_inputs_is_byte_identical(tmp_path) -> None:
    first = _run_round(tmp_path / "a")["repo_root"]
    second = _run_round(tmp_path / "b")["repo_root"]
    written = sorted(
        path.relative_to(first).as_posix() for path in first.rglob("*") if path.is_file()
    )
    assert written == sorted(
        path.relative_to(second).as_posix() for path in second.rglob("*") if path.is_file()
    )
    # The two score INDEXES are the flight agent's own fixtures here and name
    # absolute paths under this test's tmp_path, so they differ between the
    # runs by construction. Everything the DRIVER writes must not.
    fixtures = {
        "docs/checks/evos-dry-run/round-01/fold-a-scores.json",
        "docs/checks/evos-dry-run/round-01/fold-b-scores.json",
    }
    differing = [
        relpath
        for relpath in written
        if relpath not in fixtures
        and (first / relpath).read_bytes() != (second / relpath).read_bytes()
    ]
    assert differing == [], differing


def test_a_landed_step_is_never_redone(tmp_path) -> None:
    result = _run_round(tmp_path / "run")
    config = result["config"]
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


def test_no_sample_id_and_no_utterance_text_reaches_a_receipt(tmp_path) -> None:
    """Every sentence in this world is synthetic, but the RULE is real: the
    propose receipt pins prompt digests and exemplar ids, never the rendered
    instruction."""

    result = _run_round(tmp_path / "run")
    receipt = result["propose_receipt"]
    assert all(len(contact["prompt_sha256"]) == 64 for contact in receipt["contacts"])
    assert "synthetic spoken command" not in json.dumps(receipt)


def test_round_one_refuses_to_price_the_form_twin_without_a_tokenizer(tmp_path) -> None:
    """The form twin is a token-matched control, so a round that cannot
    measure tokens stops and names the prompt-fit row rather than pricing it
    with an estimator."""

    config = _loop_config()
    repo_root = _repo(tmp_path / "run", config)
    carrier = _carrier()
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    propose = run_propose_step(state, 1, config=config, carrier=carrier)
    receipt = propose.documents[config.round_paths(1)["propose"]["writes"][2]]
    responses = _responses(receipt, refuse_second_slot=False)
    with pytest.raises(EvolutionError, match="tokenizer"):
        run_candidates_step(
            state,
            1,
            config=config,
            carrier=carrier,
            propose_receipt=receipt,
            responses=responses,
            repo_root=repo_root,
            fold_a_rows=12,
            fold_a_speech_seconds=24.0,
        )


def test_the_a_0_pins_stop_the_cell_when_train_stops_reproducing_them() -> None:
    """`A_0`'s closure is executed, not transcribed.

    Round 0 of the curve is the admitted KC-S1b mechanism only if the loop
    starts from exactly the bytes KC-S1b flew, so the committed loop config
    pins the floored schema's content hash, the unfloored table's, and the
    TRAIN source identity both were mined from -- and `assert_a_0` raises
    rather than warns when a mining disagrees with any of them.
    """

    floored = _schema(floored=True)
    unfloored = _schema(floored=False)
    document = {
        **json.loads(json.dumps(_loop_config_document())),
        "a_0": {
            "receipt_relpath": "docs/receipts/knowledge/synthetic.json",
            "receipt_sha256": "c" * 64,
            "content_hash": floored.content_hash(),
            "unfloored_content_hash": unfloored.content_hash(),
            "source_identity_hash": floored.source_identity_hash,
            "utterance_count": floored.utterance_count,
        },
    }
    config = LoopConfig.from_json(document)
    # The measured tables reproduce every pin, and the receipt digest the
    # caller measured is checked beside them.
    assert config.assert_a_0(
        floored=floored, unfloored=unfloored, receipt_sha256="c" * 64
    ) is config

    for wrong in ("content_hash", "unfloored_content_hash", "source_identity_hash"):
        drifted = LoopConfig.from_json(
            {**document, "a_0": {**document["a_0"], wrong: "0" * 64}}
        )
        with pytest.raises(EvolutionError, match="does not reproduce the pinned"):
            drifted.assert_a_0(floored=floored, unfloored=unfloored)
    with pytest.raises(EvolutionError, match="does not reproduce the pinned"):
        config.assert_a_0(
            floored=floored, unfloored=unfloored, receipt_sha256="d" * 64
        )
    # A loop that declares no pins (EVO-A1) is untouched.
    assert LoopConfig.from_json(document | {"a_0": None}).assert_a_0(
        floored=floored, unfloored=unfloored
    )


def test_the_committed_loop_configs_declare_their_own_fold_sizes() -> None:
    """A cell's fragments are costed from its own folds, not a default.

    ``run_candidates_step`` and ``run_select_step`` write each emitted
    fragment's ``execution_plan`` from the fold size and charge it against the
    registered exposure row, so a SLURP round costed at EVO-A1's 404 rows
    would declare a plan its own 1,080-row flight exceeds. EVO-A1 declares
    nothing and keeps the defaults, which are its own measured V2 folds.
    """

    repo = Path(__file__).resolve().parents[2]
    slurp = LoopConfig.from_json(
        json.loads(
            (repo / "configs/knowledge/slurp-evo-s1/loop-v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    assert (slurp.fold_a_rows, slurp.fold_b_rows) == (1080, 1080)
    assert slurp.fold_a_speech_seconds == 3084.528438
    assert slurp.fold_b_speech_seconds == 3154.797375

    a2t = LoopConfig.from_json(
        json.loads(
            (repo / "configs/knowledge/a2t-evo-a1/loop-v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    assert (a2t.fold_a_rows, a2t.fold_b_rows) == (A2T_FOLD_ROWS, A2T_FOLD_ROWS)
    assert a2t.fold_a_speech_seconds == A2T_FOLD_A_SPEECH_SECONDS
    assert a2t.fold_b_speech_seconds == A2T_FOLD_B_SPEECH_SECONDS


def test_the_base_fragments_projection_reaches_every_candidate_unchanged(
    tmp_path,
) -> None:
    """One declaration of the projection, on the base, for every arm.

    The incumbent arm flies the base fragment itself and each candidate flies
    a copy of it, so declaring the projection once on the base is what makes
    a round's contrast single-factor: every arm of that fold selects its
    per-intent block from the same sealed label, and the only thing that
    differs is the artifact.
    """

    from speech_aware_evidence_acquisition.rails.evolution import (
        assemble_portfolio,
        write_candidate_fragments,
    )
    from speech_aware_evidence_acquisition.rails.proposer import (
        slurp_blocks_from_schema,
        slurp_shares_only_candidate,
    )

    config = _loop_config()
    projection = {"projection": "slurp-legal-label-projection-v2"}
    repo = _repo(tmp_path / "run", config, fill_params=projection)
    base = json.loads(
        (repo / "configs" / "baseline" / f"{config.base_fragment}.json").read_text(
            encoding="utf-8"
        )
    )
    incumbent = slurp_blocks_from_schema(_schema(floored=True), intents=INTENTS)
    target = SCENARIOS[0]
    candidate = slurp_shares_only_candidate(
        {intent: incumbent[intent] for intent in ARTIFACT_KEYS[target]},
        target_id=target,
        round=1,
        k=4,
    )
    portfolio = assemble_portfolio({}, {target: candidate})
    written = write_candidate_fragments(
        [portfolio],
        base_fragment=base,
        out_dir=repo / "configs" / "baseline",
        artifact_dir=repo / "configs" / "knowledge" / config.slug,
        artifact_relpath_base=repo,
        artifact_family="slurp-slot-schema",
        state_fill=config.state_fill,
        state_fill_phase=config.state_fill_phase,
        fold_variants=config.fold_predecessors,
    )
    assert len(written) == 2  # one fragment per fold
    for path in written:
        slots = json.loads(path.read_text(encoding="utf-8"))["phase_material"]["slots"]
        assert slots["fill_params"]["projection"] == projection["projection"]
        # and the writer's own keys are all still there
        assert {"artifact_relpath", "artifact_sha256", "portfolio_sha256"} <= set(
            slots["fill_params"]
        )

    # A base that tried to set a key the writer owns is refused rather than
    # silently overwritten.
    colliding = json.loads(json.dumps(base))
    colliding["phase_material"]["slots"]["fill_params"] = {"artifact_sha256": "0" * 64}
    with pytest.raises(EvolutionError, match="will not silently replace"):
        write_candidate_fragments(
            [portfolio],
            base_fragment=colliding,
            out_dir=repo / "configs" / "baseline",
            artifact_dir=repo / "configs" / "knowledge" / config.slug,
            artifact_relpath_base=repo,
            artifact_family="slurp-slot-schema",
            state_fill=config.state_fill,
            state_fill_phase=config.state_fill_phase,
            fold_variants=config.fold_predecessors,
        )


def test_the_incumbent_gets_one_fragment_per_fold_when_the_predecessor_does() -> None:
    """An incumbent bound to the other fold's sealed manifest is not a
    comparator.

    EVO-S1's slot cells bind their fold's own one-time intent manifest, so the
    fold-B incumbent cannot fly the fragment fold A's incumbent flies -- it
    would be paired against another population's sealed rows. EVO-A1's arm is
    fold-independent, declares no fold predecessors, and keeps one fragment
    for both folds.
    """

    config = _loop_config()
    assert config.incumbent_fragment("fold_a") == f"{config.base_fragment}-fold-a"
    assert config.incumbent_fragment("fold_b") == f"{config.base_fragment}-fold-b"

    repo = Path(__file__).resolve().parents[2]
    slurp = LoopConfig.from_json(
        json.loads(
            (repo / "configs/knowledge/slurp-evo-s1/loop-v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    for which in ("fold_a", "fold_b"):
        name = slurp.incumbent_fragment(which)
        assert (repo / "configs" / "baseline" / f"{name}.json").is_file(), name

    a2t = LoopConfig.from_json(
        json.loads(
            (repo / "configs/knowledge/a2t-evo-a1/loop-v1.json").read_text(
                encoding="utf-8"
            )
        )
    )
    assert a2t.incumbent_fragment("fold_a") == a2t.base_fragment
    assert a2t.incumbent_fragment("fold_b") == a2t.base_fragment


def test_the_proposer_half_may_declare_its_own_model_fragment(tmp_path) -> None:
    """The reward cells fly ``max_tokens`` 64 and a proposer contact returns a
    scenario's whole block set at the preregistered ceiling of 1,536.
    ``decoding_params`` lives in the model fragment and ``core.config.compose``
    refuses the same key from two fragments, so the two halves need two fragments
    and the propose step has to name the right one."""

    document = _loop_config_document()
    document["proposer_model_fragment"] = "a-text-only-fragment"
    config = LoopConfig.from_json(document)
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    result = run_propose_step(state, 1, config=config, carrier=_carrier())
    fragment = result.documents[
        f"{config.experiments_reldir}/{config.slug}-proposer-r01.json"
    ]
    assert {cell["model_fragment"] for cell in fragment["cells"]} == {
        "a-text-only-fragment"
    }


def test_a_loop_that_declares_no_proposer_fragment_keeps_flying_one(tmp_path) -> None:
    """EVO-A1 leaves the field absent, so its committed config and every fragment
    it emits are byte for byte what they were."""

    config = _loop_config()
    assert config.proposer_model_fragment is None
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    result = run_propose_step(state, 1, config=config, carrier=_carrier())
    fragment = result.documents[
        f"{config.experiments_reldir}/{config.slug}-proposer-r01.json"
    ]
    assert {cell["model_fragment"] for cell in fragment["cells"]} == {
        config.model_fragment
    }


def test_the_committed_evo_a1_config_declares_no_proposer_fragment() -> None:
    repo = Path(__file__).resolve().parents[2]
    a2t = LoopConfig.from_json(
        json.loads((repo / "configs/knowledge/a2t-evo-a1/loop-v1.json").read_text(encoding="utf-8"))
    )
    assert a2t.proposer_model_fragment is None
    slurp = LoopConfig.from_json(
        json.loads((repo / "configs/knowledge/slurp-evo-s1/loop-v1.json").read_text(encoding="utf-8"))
    )
    assert slurp.proposer_model_fragment == "q4km-mmproj-free-speech-native-np4-proposer-max1536"
    fragment = json.loads(
        (repo / "configs/model" / f"{slurp.proposer_model_fragment}.json").read_text(encoding="utf-8")
    )
    reward = json.loads(
        (repo / "configs/model" / f"{slurp.model_fragment}.json").read_text(encoding="utf-8")
    )
    assert fragment["decoding_params"]["max_tokens"] == 1536
    assert reward["decoding_params"]["max_tokens"] == 64
    # Same GGUF, same build, same runtime receipt, same geometry and cache flags.
    for key in ("model_lock_key", "server_args", "runtime_receipt", "base_url",
                "model_materialization_root", "transport"):
        assert fragment[key] == reward[key], key
    # TWO deliberate differences beyond max_tokens, both fail-closed rather than
    # cosmetic: the speech prompt orders route into the formal speech-feature request
    # path, which refuses a payload whose query_source is not "speech_features" and
    # requires a non-empty speech_feature_parts list. A text-only arm cannot satisfy
    # that contract, so it must not claim it -- and it has no packet root either.
    assert reward["prompt_order"] == "speech-query-prefix-v2"
    assert fragment["prompt_order"] == "evidence-first-system-v2"
    assert "speech_feature_root" not in fragment
    assert fragment["server_env"] == {}


def test_an_emitted_fragment_declares_the_split_id_the_flight_reads(tmp_path) -> None:
    """``core.flight.FlightRuntime._prepare`` reads ``values["split_id"]`` off the
    COMPOSED config; no emitted fragment carried one, so every fragment this loop
    wrote composed and then died at preflight."""

    document = _loop_config_document()
    document["split_ids"] = {
        "fold_a": "A-SPLIT",
        "fold_b": "B-SPLIT",
        "proposer": "POOL-SPLIT",
    }
    config = LoopConfig.from_json(document)
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    result = run_propose_step(state, 1, config=config, carrier=_carrier())
    fragment = result.documents[
        f"{config.experiments_reldir}/{config.slug}-proposer-r01.json"
    ]
    assert fragment["split_id"] == "POOL-SPLIT"


def test_a_loop_that_declares_no_split_ids_emits_no_split_id(tmp_path) -> None:
    """EVO-A1's committed fragments stay byte for byte what they are."""

    config = _loop_config()
    assert config.split_ids is None
    assert config.split_id_for("proposer") is None
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    result = run_propose_step(state, 1, config=config, carrier=_carrier())
    fragment = result.documents[
        f"{config.experiments_reldir}/{config.slug}-proposer-r01.json"
    ]
    assert "split_id" not in fragment


def test_a_partial_split_id_mapping_is_refused() -> None:
    document = _loop_config_document()
    document["split_ids"] = {"fold_a": "A-SPLIT"}
    config = LoopConfig.from_json(document)
    assert config.split_id_for("fold_a") == "A-SPLIT"
    with pytest.raises(EvolutionError, match="declares no 'fold_b'"):
        config.split_id_for("fold_b")


def test_the_committed_evo_s1_split_ids_are_the_rosters_own_names() -> None:
    repo = Path(__file__).resolve().parents[2]
    config = LoopConfig.from_json(
        json.loads((repo / "configs/knowledge/slurp-evo-s1/loop-v1.json").read_text(encoding="utf-8"))
    )
    for which, relpath in (
        ("fold_a", config.fold_a_roster_relpath),
        ("fold_b", config.fold_b_roster_relpath),
        ("proposer", config.exemplar_roster_relpath),
    ):
        roster = json.loads((repo / relpath).read_text(encoding="utf-8"))
        assert config.split_id_for(which) == roster["roster_id"], which


def test_an_emitted_fragment_does_not_collide_with_a_runtime_view_dataset(tmp_path) -> None:
    """``core.config.compose`` refuses the same key from two fragments, and a SLURP
    dataset fragment is a ``saea-speech-native-runtime-view-v1`` document that
    declares ``schema`` itself -- so an emitted fragment that also declared
    ``schema`` could never be composed with one."""

    config = _loop_config()
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    result = run_propose_step(state, 1, config=config, carrier=_carrier())
    fragment = result.documents[
        f"{config.experiments_reldir}/{config.slug}-proposer-r01.json"
    ]
    assert "schema" not in fragment
    assert fragment["fragment_kind"] == "saea-a2t-direct-calibration-experiment-v1"


# ---------------------------------------------------------------------------
# The null-rewrite form gate (track E3e, 2026-09-07)
# ---------------------------------------------------------------------------


def _incumbent_answer(intents: tuple[str, ...]) -> str:
    """The failure EVO-S1 round 1 produced on ``social``: the proposer hands
    the incumbent's own blocks straight back, byte for byte."""

    texts = slurp_block_texts(_schema(floored=True), intents=intents)
    return "\n".join(texts[intent] for intent in intents) + "\n"


def test_a_block_set_that_renders_to_the_incumbent_is_refused_as_a_null_rewrite(
    tmp_path,
) -> None:
    """``social``'s round-1 winner rendered to A_0's own ``social_post`` block:
    the old guard checked that a candidate EXISTED, not that it DIFFERED, so
    the round spent an admission on an arm identical to the incumbent on the
    wire. It is now refused at the candidates step, and its slot falls back to
    the existing "refused candidate flies no portfolio" path."""

    config = _loop_config()
    repo_root = _repo(tmp_path / "run", config)
    carrier = _carrier()
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    propose = run_propose_step(state, 1, config=config, carrier=carrier)
    receipt = propose.documents[config.round_paths(1)["propose"]["writes"][2]]

    responses: dict[str, str] = {}
    for contact in receipt["contacts"]:
        intents = tuple(str(intent) for intent in contact["artifact_keys"])
        responses[contact["sample_id"]] = (
            _incumbent_answer(intents)
            if contact["target_id"] == "news"
            else _rewritten(intents)
        )

    candidates = run_candidates_step(
        state,
        1,
        config=config,
        carrier=carrier,
        propose_receipt=receipt,
        responses=responses,
        repo_root=repo_root,
        fold_a_rows=sum(len(rows) for rows in FOLD_A_ROWS.values()),
        fold_a_speech_seconds=24.0,
        token_counter=_word_counter,
    )
    document = candidates.documents[config.round_paths(1)["candidates"]["writes"][0]]
    refused = [
        record
        for record in document["harvest"]["refusals"]
        if record.get("gate") == NULL_REWRITE_GATE
    ]
    assert {record["target_id"] for record in refused} == {"news"}
    assert all(
        record["reason"].startswith(f"{NULL_REWRITE_GATE}:") for record in refused
    )
    assert candidates.summary["null_rewrites_refused"] == len(refused)

    # Never admitted, and never flown: no ``news`` candidate survives, so every
    # proposer portfolio leaves ``news`` at the incumbent's blocks.
    assert all(
        candidate["target_id"] != "news"
        for candidate in document["harvest"]["candidates"]
    )
    for slot, portfolio in document["portfolios"].items():
        if int(slot) in config.proposer_slots:
            assert "news" not in portfolio["candidate_ids"], slot


def test_the_gate_leaves_a_real_rewrite_alone(tmp_path) -> None:
    """The dry run's own legal answer changes one filler per type, so no
    candidate of a normal round is refused by this gate: it costs a round
    nothing that a round should keep."""

    config = _loop_config()
    repo_root = _repo(tmp_path / "run", config)
    carrier = _carrier()
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    propose = run_propose_step(state, 1, config=config, carrier=carrier)
    receipt = propose.documents[config.round_paths(1)["propose"]["writes"][2]]
    candidates = run_candidates_step(
        state,
        1,
        config=config,
        carrier=carrier,
        propose_receipt=receipt,
        responses=_responses(receipt, refuse_second_slot=False),
        repo_root=repo_root,
        fold_a_rows=sum(len(rows) for rows in FOLD_A_ROWS.values()),
        fold_a_speech_seconds=24.0,
        token_counter=_word_counter,
    )
    document = candidates.documents[config.round_paths(1)["candidates"]["writes"][0]]
    assert candidates.summary["null_rewrites_refused"] == 0
    assert document["null_rewrite_checks"]
    assert not any(record["null_rewrite"] for record in document["null_rewrite_checks"])


# ---------------------------------------------------------------------------
# The landed round: replaying the gate over the committed round-1 receipt
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
A_0_RECEIPT = REPO_ROOT / "docs/receipts/knowledge/slurp-intent-slot-schema-v1.json"
ROUND_01 = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-s1/round-01"
)


def _a_0_block_texts() -> dict[str, str]:
    """A_0's own rendered blocks, rebuilt from the COMMITTED schema receipt the
    loop config pins -- no data root, no TRAIN file, no flight."""

    document = json.loads(A_0_RECEIPT.read_text(encoding="utf-8"))
    construction = document["construction"]
    schema = SlurpIntentSlotSchema(
        schema_id=construction["schema_id"],
        source_split=construction["source_split"],
        source_identity_hash=construction["source_identity_hash"],
        utterance_count=construction["utterance_count"],
        min_share=construction["min_share"],
        examples_per_type=construction["examples_per_type"],
        intents={
            record["intent"]: SlurpIntentSlots(
                intent=record["intent"],
                n=record["utterances"],
                mentions=record["slot_mentions"],
                types=tuple(
                    (row["entity_type"], row["count"], row["share"])
                    for row in record["types"]
                ),
                fillers={
                    row["entity_type"]: tuple(row["fillers"]) for row in record["types"]
                },
            )
            for record in document["intents"]
        },
    )
    return slurp_block_texts(schema)


@pytest.mark.skipif(
    not (A_0_RECEIPT.exists() and (ROUND_01 / "candidates.json").exists()),
    reason="the landed EVO-S1 round-1 receipts are not in this checkout",
)
def test_the_landed_round_one_candidates_replay_through_the_gate() -> None:
    """Round 1's own ``candidates.json``, replayed through the new gate.

    The candidate side is the receipt's committed ``rendered_sha256``; the
    incumbent side is A_0's blocks over the SAME intents, rebuilt from the
    committed schema receipt. Round 1's incumbent state IS A_0, so no override
    enters. FIVE of the 29 candidates render to the incumbent, one of which is
    ``social``'s admitted winner ``bb02b5f3`` -- the finding this gate exists
    for, and the reason the round's confirmation carried 60 rows of noise.
    """

    blocks = _a_0_block_texts()
    document = json.loads((ROUND_01 / "candidates.json").read_text(encoding="utf-8"))
    by_id = {
        record["candidate_id"]: record for record in document["harvest"]["candidates"]
    }
    null_rewrites = []
    for validation in document["validations"]:
        intents = sorted(str(record["intent"]) for record in validation["per_key"])
        whole = "\n".join(blocks[intent] for intent in intents)
        digest = hashlib.sha256(whole.encode("utf-8")).hexdigest()
        if digest == validation["rendered_sha256"]:
            null_rewrites.append(validation["candidate_id"])

    selection = json.loads((ROUND_01 / "selection.json").read_text(encoding="utf-8"))
    winners = set(selection["winners"].values())
    refused_winners = sorted(set(null_rewrites) & winners)
    assert len(refused_winners) == 1
    assert refused_winners[0].startswith("bb02b5f3")
    assert by_id[refused_winners[0]]["target_id"] == "social"
    assert sorted(by_id[candidate_id]["target_id"] for candidate_id in null_rewrites) == [
        "calendar",
        "calendar",
        "general",
        "iot",
        "social",
    ]


def test_the_propose_receipt_names_the_instruction_revision_it_rendered(
    tmp_path,
) -> None:
    """The instruction bytes are inside every candidate id, so the round that
    flew them has to say which revision they were."""

    config = _loop_config()
    _repo(tmp_path / "run", config)
    propose = run_propose_step(
        EvolutionState(round=0, incumbent_overrides={}).validate(),
        1,
        config=config,
        carrier=_carrier(),
    )
    receipt = propose.documents[config.round_paths(1)["propose"]["writes"][2]]
    assert receipt["proposer_instruction_version"] == "proposer-instruction-v2"


# ---------------------------------------------------------------------------
# The round receipt's noise floor (track E3e, 2026-09-07)
# ---------------------------------------------------------------------------


def test_the_round_receipt_reports_the_prompt_noise_floor(tmp_path) -> None:
    """How much of a round's movement the DECODER can account for, per target
    and pooled -- computed from the sealed traces the confirm step's own score
    files name, and gating nothing.

    This dry run's fold B is 18 rows: ``alarm``'s six were asked a different
    question, ``news``'s and ``weather``'s twelve were asked the incumbent's
    own, and six of those twelve answered differently anyway. Three of the six
    saves are on changed prompts and three on unchanged ones -- which is the
    whole reason the number is now in the receipt.
    """

    result = _run_round(tmp_path / "run")
    receipt = json.loads(
        Path(result["confirm"]["round_receipt"]).read_text(encoding="utf-8")
    )
    floor = receipt["extra"]["noise_floor"]
    assert floor["measured"] is True
    assert floor["metric"] == METRIC
    assert floor["rows"] == 18
    assert floor["changed_prompt_rows"] == 6
    assert floor["unchanged_prompt_rows"] == 12
    assert floor["unchanged_prompt_flips"] == 6
    assert floor["changed_prompt"] == {"saves": 3, "harms": 0}
    assert floor["unchanged_prompt"] == {"saves": 3, "harms": 0}
    assert result["confirm"]["unchanged_prompt_flips"] == 6

    # Per target, because a scenario the assembly never touched is all noise
    # floor by construction and has to be readable as such.
    by_target = floor["by_target"]
    assert sorted(by_target) == sorted(SCENARIOS)
    assert by_target["alarm"]["changed_prompt_rows"] == 6
    assert by_target["alarm"]["unchanged_prompt_flips"] == 0
    assert by_target["news"]["unchanged_prompt_rows"] == 6
    assert by_target["news"]["unchanged_prompt_flips"] == 3
    assert by_target["news"]["unchanged_prompt"] == {"saves": 0, "harms": 0}
    assert by_target["weather"]["unchanged_prompt_flips"] == 3
    assert by_target["weather"]["unchanged_prompt"] == {"saves": 3, "harms": 0}


def test_the_noise_floor_changes_no_rule(tmp_path) -> None:
    """The admission rule is the owner's and is unchanged: the round receipt
    reports the floor beside the confirmation, and the confirmation does not
    read it."""

    result = _run_round(tmp_path / "run")
    receipt = json.loads(
        Path(result["confirm"]["round_receipt"]).read_text(encoding="utf-8")
    )
    assert "never gated" in receipt["extra"]["noise_floor"]["rule"]
    confirmation = receipt["extra"]["confirmation"]
    assert json.dumps(confirmation).find("noise") == -1
    assert json.dumps(receipt["extra"]["selection"]).find("noise") == -1


def test_an_unreadable_sealed_trace_is_recorded_rather_than_raised(tmp_path) -> None:
    """A diagnostic must never stop a round: a score file whose manifest chain
    cannot be resolved leaves the floor unmeasured, with the reason in the
    receipt, and the confirmation lands unchanged."""

    measured = _run_round(tmp_path / "whole")
    blind = _run_round(tmp_path / "blind", missing_trace=True)
    receipt = json.loads(
        Path(blind["confirm"]["round_receipt"]).read_text(encoding="utf-8")
    )
    assert receipt["extra"]["noise_floor"]["measured"] is False
    assert "could not be read" in receipt["extra"]["noise_floor"]["reason"]
    # The round itself is unaffected: same verdict, same gain.
    assert blind["confirm"]["accepted"] == measured["confirm"]["accepted"]
    assert blind["confirm"]["gain_pp"] == measured["confirm"]["gain_pp"]
