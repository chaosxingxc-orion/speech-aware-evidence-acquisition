#!/usr/bin/env python3
"""Drive ONE step of ONE evolution round, on any carrier. No model contact.

Renamed from ``run_a2t_evolution_round.py`` on 2026-09-06 (track E3d): the
script never held any Audio2Tool knowledge -- the carrier, the targets, the
rosters, the artifact family and the fragment names all come from the loop
config -- so serving EVO-S1 needed a carrier branch in
``rails.evolution_carrier`` and this rename, and NOT a second driver. A
SLURP-specific copy would have duplicated 130 lines to change one function
call, which is exactly the per-experiment fork the engineering-base rule
forbids. The old path is gone rather than aliased: two entry points to one
loop is how a receipt ends up naming a file nobody ran.

Resumable by construction: every step reads its predecessor's sealed receipt
and refuses to redo it (``rails.evolution.plan_round``), so re-running this
command after an interruption re-enters at exactly the first step that has
not landed. The decisions live in ``rails.evolution``; this file only
resolves paths, loads inputs and writes what a step returns.

    python scripts/run_evolution_round.py --config configs/knowledge/a2t-evo-a1/loop-v1.json --round 1
    python scripts/run_evolution_round.py --config configs/knowledge/slurp-evo-s1/loop-v1.json --round 1
    python scripts/run_evolution_round.py --config ... --round 1 --plan-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    _parse_ledger_tables,
)
from speech_aware_evidence_acquisition.rails.evolution import (  # noqa: E402
    ROUND_STEP_RUNNERS,
    EvolutionState,
    LoopConfig,
    RoundOutcome,
    plan_round,
)
from speech_aware_evidence_acquisition.rails.evolution_carrier import (  # noqa: E402
    load_carrier_material,
    load_state,
    slurp_candidate_validator,
)


def _read(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return str(path)


def _token_counter(base_url: str):
    """The SERVING geometry's own tokenizer, as a callable.

    ``rails.evolution.run_candidates_step`` leaves ``token_counter`` optional and
    unsupplied BY DEFAULT because pricing a candidate is a model-adjacent contact
    that belongs to the prompt-fit row, never to a driver that must make none
    (``rails.proposer.SERVING_TOKENIZER_ID``; a candidate an estimator alone
    admits is refused). ``--token-counter-url`` is how the flight agent hands the
    resident server in AFTER that row has run and published its binding, which is
    the only way round 1's F3 token-matched form twin can be built at all.
    """

    import urllib.request  # noqa: PLC0415 -- one call site, kept off the import surface

    endpoint = base_url.rstrip("/") + "/tokenize"

    def count(text: str) -> int:
        body = json.dumps(
            {"content": text, "add_special": False, "parse_special": True}
        ).encode("utf-8")
        request = urllib.request.Request(
            endpoint, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=180.0) as reply:  # noqa: S310
            tokens = json.loads(reply.read().decode("utf-8")).get("tokens")
        if not isinstance(tokens, list):
            raise SystemExit(f"{endpoint} returned no token list")
        return len(tokens)

    return count


def _exemplar_texts(repo_root: Path, config, propose_receipt) -> tuple[str, ...]:
    """The construction utterances this round's proposer was actually shown.

    Overlap with them is MEASURED and reported, never gated (preregistration
    section 8), so the count is only meaningful if the texts are the rendered
    ones. ``ProposerContact.as_json`` records ``exemplar_ids`` (a placebo's is
    empty by construction, which is exactly right: it renders no exemplar), and
    they are resolved through the same TRAIN-locked construction reader the
    propose step used. No text is written to a receipt.
    """

    shown = {
        str(sample_id)
        for contact in propose_receipt.get("contacts", ())
        for sample_id in contact.get("exemplar_ids", ())
    }
    if not shown:
        return ()
    material = load_carrier_material(repo_root, config, step="propose")
    return tuple(
        str(row["sentence"])
        for sample_id, row in sorted(material.exemplar_rows.items())
        if sample_id in shown
    )


def _responses(path: Path) -> dict[str, str]:
    """``{sample_id: text}`` from a sealed ``*.outputs.jsonl``."""

    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows[str(row["sample_id"])] = str(row.get("text", ""))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="the committed loop config")
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--repo-root", default=str(REPO))
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="report which step is next and why, and write nothing",
    )
    parser.add_argument(
        "--token-counter-url",
        default=None,
        help=(
            "base URL of the RESIDENT server at the flight's own serving geometry "
            "(rails.proposer.SERVING_TOKENIZER_ID). The candidates step needs it for "
            "round 1's token-matched form twin and for the relative token budget; "
            "without it a round-1 candidates step stops and names the prompt-fit row"
        ),
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    config = LoopConfig.from_json(_read(repo_root / args.config))
    paths = config.round_paths(args.round)
    state = load_state(repo_root, config, args.round)
    plan = plan_round(
        state,
        args.round,
        paths=paths,
        exists=lambda relpath: (repo_root / relpath).exists(),
    )
    print(json.dumps(plan.as_json(), indent=2, sort_keys=True))
    if args.plan_only:
        return 0
    if plan.next_step is None:
        if plan.blocked_on:
            print(f"BLOCKED: waiting for {list(plan.blocked_on)}", file=sys.stderr)
            return 2
        print("round complete: every step has landed")
        return 0

    step = plan.next_step
    stem = f"{config.receipts_reldir}/round-{args.round:02d}"
    ledger_rows = _parse_ledger_tables(
        (repo_root / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    )
    carrier = load_carrier_material(repo_root, config, step=step)
    kwargs: dict[str, object] = {"config": config, "carrier": carrier}
    if step == "propose":
        kwargs["ledger_rows"] = ledger_rows
    elif step == "candidates":
        propose_receipt = _read(repo_root / f"{stem}/propose.json")
        kwargs["propose_receipt"] = propose_receipt
        kwargs["responses"] = _responses(repo_root / f"{stem}/proposer-outputs.jsonl")
        kwargs["repo_root"] = repo_root
        kwargs["ledger_rows"] = ledger_rows
        if args.token_counter_url:
            counter = _token_counter(args.token_counter_url)
            kwargs["token_counter"] = counter
            if config.artifact_family == "slurp-slot-schema":
                kwargs["validator"] = slurp_candidate_validator(
                    repo_root,
                    config,
                    carrier,
                    state,
                    token_counter=counter,
                    exemplar_texts=_exemplar_texts(repo_root, config, propose_receipt),
                )
    elif step == "select":
        kwargs["candidates_receipt"] = _read(repo_root / f"{stem}/candidates.json")
        kwargs["score_files"] = _read(repo_root / f"{stem}/fold-a-scores.json")
        kwargs["repo_root"] = repo_root
        kwargs["ledger_rows"] = ledger_rows
    else:
        kwargs["selection_receipt"] = _read(repo_root / f"{stem}/selection.json")
        kwargs["score_files"] = _read(repo_root / f"{stem}/fold-b-scores.json")
        kwargs["receipts_dir"] = repo_root / config.receipts_reldir

    result = ROUND_STEP_RUNNERS[step](state, args.round, **kwargs)
    written = [_write(repo_root / relpath, doc) for relpath, doc in result.documents.items()]
    print(
        json.dumps(
            {"step": step, "round": args.round, "written": sorted(written),
             "summary": result.summary},
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    if isinstance(result.state, EvolutionState) and result.state.history:
        last: RoundOutcome = result.state.history[-1]
        print(f"round {last.round}: accepted={last.accepted} gain={last.gain_pp:.3f} pp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
