#!/usr/bin/env python3
"""CLI: the EVO-A1 decontamination artifact (MODEL-FREE, text only, zero contacts).

Exposure row ``SAEA-A2T-MF-EVO-DECONTAMINATION-V1``; authority
``docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md``
section 8 and section 12 item 7, which require the row to exist before the
first candidate is validated.

Two artifacts, one rule each.

**The evaluation 6-gram set.** ``rails.proposer.validate_candidate_artifact``
refuses a candidate that shares a word 6-gram with any evaluation query unless
that 6-gram already occurs in the released registry. This script derives the
set once from the sealed ``A2T-ORG1-UNION-4000`` population, records its size
and its SET PIN -- one SHA-256 over the LF-joined sorted grams -- and NEVER
writes a gram of it to disk. Evaluation query text does not enter this
repository, and a 6-gram is six verbatim words of an evaluation query, so a
committed list of them would be exactly the leak this gate exists to prevent.
The pin is what a reviewer checks, and :func:`evaluation_invocation_texts` is
the single function every later caller re-derives the set from, so the gate at
prompt fit and the gate audited here cannot drift.

**A_0's exemption list.** The released compact registry's own 6-grams ARE
committed, verbatim, in ``registry-6grams.json``: the registry is public
released text, it is the legal source of shared phrasing, and a reviewer has to
be able to see exactly which overlaps the gate forgives.

Identity anchors, reproduced rather than asserted -- a disagreement is a
refusal, not a new number:

* ``A_0``'s rendered block is 15,854 characters over 152 lines and hashes to
  ``752dd381...0de8a605``, the value the preregistration's section 3 pins;
* the evaluation set has **77,899** grams and the registry set **2,005**, the
  two counts ``SAEA-A2T-MF-KC-A1-DECONTAMINATION-V1`` recorded on the same
  population on 2026-09-06.

A DEFECT IN THE INHERITED RULE, recorded rather than silently fixed. KC-A1's
gate collected every string value of a ``chat_history`` turn, which is the
turn's ``content`` plus its ``path`` and its ``role`` -- so 9,252 of the 77,899
grams come from WAV PATH strings rather than from anything a speaker said. The
speaker-only core is 68,647 grams. This script keeps the inherited superset as
the GATE set, because it is strictly stricter (it can only cause a refusal, never
admit a candidate the speaker-only set would refuse) and because keeping it is
what lets the KC-A1 anchor reproduce exactly; it records the speaker-only pin
beside it so the next cell can choose knowingly.

ZERO CONTACTS: a pure text pass over the released tier manifests' invocation
fields and ``tools_registry.csv``. No frozen core, tokenizer, embedder,
retriever, scorer, network, audio decode, GPU or paid API. NO GOLD: the fields
opened are ``query``, ``user_request`` and the ``chat_history`` turns; a row's
``tool_name``, ``expected_tool_call``, ``extracted_params``,
``additional_tool_calls``, ``reasoning``, ``tool_id``, ``functions`` and
``instruction`` are never opened.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.audio2tool_tools import (  # noqa: E402
    render_registry_compact,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.proposer import (  # noqa: E402
    DECONTAMINATION_NGRAM,
    word_ngrams,
)

EXPOSURE_ROW_ID = "SAEA-A2T-MF-EVO-DECONTAMINATION-V1"
AUTHORITY = (
    "docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md"
)
POPULATION_RECEIPT = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-a2t-org1-domain-grouped-roster/flight-roster-receipt.json"
)
POPULATION_RECEIPT_SHA256 = (
    "e5a81b71e1253ff866262991f79d132b89f4bfb47e7c8a0c0cf0aa04857b8736"
)
CHECK_DIR = REPO_ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-decontamination"
)

#: The row-level invocation fields. ``query`` is what the speaker says on every
#: tier; ``user_request`` and ``chat_history`` exist only on tier 7.
ROW_TEXT_FIELDS = ("query", "user_request")

#: Fields of an evaluation row this script never opens. Named rather than
#: implied, because "no gold was read" is the claim the row makes.
GOLD_FIELDS_NEVER_OPENED = (
    "additional_tool_calls",
    "background_tool_call",
    "background_tool_name",
    "expected_tool_call",
    "extracted_params",
    "functions",
    "instruction",
    "original_tool_call",
    "reasoning",
    "tool_id",
    "tool_name",
)

KC_A1_EVALUATION_GRAMS = 77899
KC_A1_REGISTRY_GRAMS = 2005
KC_A1_INVOCATION_TEXTS = 9930
COMPACT_SHA256 = "752dd381a02028dc7345a6ac826109bdcc879d82547a9029a43d559d0de8a605"
COMPACT_CHARS = 15854
COMPACT_LINES = 152
KC_A1_ROWS = (
    "SAEA-A2T-MF-KC-A1-DECONTAMINATION-V1",
    "SAEA-A2T-MF-KC-A1C-DECONTAMINATION-V2",
)

TEXT_RULE = (
    "for every row of the population: its 'query', its 'user_request' when it has "
    "one, and EVERY string value of every 'chat_history' turn (the turn's 'content', "
    "its 'path' and its 'role'). Inherited verbatim from KC-A1's gate so the two "
    "counts reproduce; the path and role strings are a defect of that rule and are "
    "reported separately rather than silently dropped"
)
SPEAKER_RULE = (
    "the same rows, but only 'query', 'user_request' and each chat turn's 'content' "
    "-- what the SPEAKER actually says, with no wav path and no role token"
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def gram_set_pin(grams: Iterable[tuple[str, ...]]) -> str:
    """One SHA-256 that pins a 6-gram SET without recording a gram of it.

    The digest is over the LF-joined, sorted, space-joined grams: the same
    bytes any re-derivation produces, so a reviewer who re-runs this script
    gets the same value and a set that has drifted by one gram cannot pass.
    """

    return _sha256_text("\n".join(sorted(" ".join(gram) for gram in grams)))


def population_ids(repo_root: Path) -> dict[str, set[int]]:
    """``tier -> manifest ids`` of the sealed union, hash-pinned before use."""

    path = repo_root / POPULATION_RECEIPT
    measured = _sha256_file(path)
    if measured != POPULATION_RECEIPT_SHA256:
        raise SystemExit(
            f"{POPULATION_RECEIPT} hashes to {measured}, not the pinned "
            f"{POPULATION_RECEIPT_SHA256}"
        )
    receipt = json.loads(path.read_text(encoding="utf-8"))
    wanted: dict[str, set[int]] = collections.defaultdict(set)
    for item in receipt["items"]:
        wanted[str(item["tier"])].add(int(item["id"]))
    if sum(len(ids) for ids in wanted.values()) != int(receipt["count"]):
        raise SystemExit(f"{POPULATION_RECEIPT} carries a duplicate id")
    return dict(wanted)


def evaluation_invocation_texts(
    lock: Mapping[str, object],
    root: Path,
    wanted: Mapping[str, set[int]],
    *,
    speaker_only: bool = False,
) -> list[str]:
    """The evaluation-side texts the decontamination gate compares against.

    THE one place this cell opens evaluation query text. Every later caller --
    the prompt-fit step that runs ``validate_candidate_artifact`` with the
    serving tokenizer -- calls this function rather than re-implementing the
    rule, so the gate that flies and the gate audited here cannot drift.

    ``speaker_only`` selects the narrower, correct rule (see the module
    docstring): row text plus each chat turn's ``content``, without the wav
    ``path`` and ``role`` strings KC-A1's rule swept in.
    """

    public = Path(asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)) / "public"
    texts: list[str] = []
    for tier in sorted(wanted):
        entries = json.loads(
            (public / f"{tier}_data" / f"{tier}.json").read_text(encoding="utf-8")
        )
        for entry in entries:
            if int(entry["id"]) not in wanted[tier]:
                continue
            for field in ROW_TEXT_FIELDS:
                value = entry.get(field)
                if isinstance(value, str) and value.strip():
                    texts.append(value)
            history = entry.get("chat_history")
            if not isinstance(history, list):
                continue
            for turn in history:
                if not isinstance(turn, Mapping):
                    continue
                if speaker_only:
                    value = turn.get("content")
                    if isinstance(value, str) and value.strip():
                        texts.append(value)
                    continue
                texts.extend(
                    value
                    for value in turn.values()
                    if isinstance(value, str) and value.strip()
                )
    return texts


def _grams(texts: Sequence[str]) -> set[tuple[str, ...]]:
    out: set[tuple[str, ...]] = set()
    for text in texts:
        out |= word_ngrams(text)
    return out


def build(*, repo_root: Path, lock: Mapping[str, object], root: Path) -> dict[str, object]:
    wanted = population_ids(repo_root)

    compact = render_registry_compact(lock, root)
    if (
        _sha256_text(compact) != COMPACT_SHA256
        or len(compact) != COMPACT_CHARS
        or len(compact.splitlines()) != COMPACT_LINES
    ):
        raise SystemExit(
            "A_0 does not reproduce: the compact registry renders to "
            f"{len(compact)} chars / {len(compact.splitlines())} lines / "
            f"{_sha256_text(compact)}"
        )
    registry_grams = word_ngrams(compact)
    if len(registry_grams) != KC_A1_REGISTRY_GRAMS:
        raise SystemExit(
            f"the registry exemption list is {len(registry_grams)} grams, not the "
            f"{KC_A1_REGISTRY_GRAMS} KC-A1 recorded"
        )

    texts = evaluation_invocation_texts(lock, root, wanted)
    if len(texts) != KC_A1_INVOCATION_TEXTS:
        raise SystemExit(
            f"the population yields {len(texts)} invocation texts, not the "
            f"{KC_A1_INVOCATION_TEXTS} KC-A1 recorded"
        )
    evaluation_grams = _grams(texts)
    if len(evaluation_grams) != KC_A1_EVALUATION_GRAMS:
        raise SystemExit(
            f"the population yields {len(evaluation_grams)} word "
            f"{DECONTAMINATION_NGRAM}-grams, not the {KC_A1_EVALUATION_GRAMS} KC-A1 "
            "recorded"
        )
    speaker_texts = evaluation_invocation_texts(lock, root, wanted, speaker_only=True)
    speaker_grams = _grams(speaker_texts)

    per_tier: dict[str, dict[str, int]] = {}
    for tier in sorted(wanted):
        tier_texts = evaluation_invocation_texts(lock, root, {tier: wanted[tier]})
        per_tier[tier] = {
            "rows": len(wanted[tier]),
            "invocation_texts": len(tier_texts),
            "distinct_word_6grams": len(_grams(tier_texts)),
        }

    shared_now = sorted(
        " ".join(gram) for gram in (evaluation_grams & registry_grams)
    )
    document = {
        "schema": "saea-a2t-evo-decontamination-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": AUDIO2TOOL_LOCK_KEY,
        "authority": AUTHORITY,
        "generator": "scripts/build_a2t_evo_decontamination.py",
        "exposure_row": EXPOSURE_ROW_ID,
        "n": DECONTAMINATION_NGRAM,
        "tokenizer": (
            "rails.proposer.word_ngrams: lower-cased alphanumeric word n-grams, one "
            "tokenizer for the candidate side, the evaluation side and the registry side"
        ),
        "population": {
            "split_name": "A2T-ORG1-UNION-4000",
            "roster_receipt": POPULATION_RECEIPT,
            "roster_receipt_sha256": POPULATION_RECEIPT_SHA256,
            "count": sum(len(ids) for ids in wanted.values()),
            "rows_per_tier": {tier: len(ids) for tier, ids in sorted(wanted.items())},
            "per_tier": per_tier,
        },
        "evaluation_grams": {
            "rule": TEXT_RULE,
            "invocation_texts": len(texts),
            "distinct_word_6grams": len(evaluation_grams),
            "set_sha256": gram_set_pin(evaluation_grams),
            "set_sha256_convention": (
                "sha256 over the LF-joined sorted space-joined grams, UTF-8, no "
                "trailing newline. The SET is pinned and never written: a 6-gram is six "
                "verbatim words of an evaluation query, so a committed list of them "
                "would be the leak this gate exists to prevent"
            ),
            "grams_are_committed": False,
        },
        "evaluation_grams_speaker_only": {
            "rule": SPEAKER_RULE,
            "invocation_texts": len(speaker_texts),
            "distinct_word_6grams": len(speaker_grams),
            "set_sha256": gram_set_pin(speaker_grams),
            "grams_are_committed": False,
        },
        "inherited_rule_defect": {
            "what": (
                "KC-A1's gate collected EVERY string value of a chat_history turn, which "
                "is the turn's content plus its wav 'path' and its 'role'. "
                f"{len(evaluation_grams) - len(speaker_grams)} of the "
                f"{len(evaluation_grams)} grams therefore come from path and role "
                "strings rather than from anything a speaker said"
            ),
            "decision": (
                "KEEP the inherited superset as the GATE set. It is strictly stricter -- "
                "it can only cause a refusal, never admit a candidate the speaker-only "
                "set would refuse -- and keeping it is what lets KC-A1's two anchors "
                "reproduce exactly. The speaker-only pin is recorded beside it so a later "
                "cell can narrow the rule knowingly rather than by accident"
            ),
            "affects_kc_a1_verdict": False,
            "why_not": (
                "both KC-A1 arms passed with ZERO shared grams, and a strictly larger "
                "refusal set cannot turn a pass into a different pass"
            ),
        },
        "a_0_exemption": {
            "what": (
                "A_0's own word 6-grams: the released compact registry is the legal "
                "source of shared phrasing, so a gram of the candidate that is also a "
                "gram of an evaluation query is forgiven when the registry already "
                "carries it. illegal = (candidate & evaluation) - registry"
            ),
            "artifact": "registry-6grams.json",
            "rendered_sha256": COMPACT_SHA256,
            "rendered_characters": len(compact),
            "rendered_lines": len(compact.splitlines()),
            "distinct_word_6grams": len(registry_grams),
            "set_sha256": gram_set_pin(registry_grams),
            "grams_are_committed": True,
            "why_committable": (
                "the compact registry is public released text of the Audio2Tool "
                "distribution, not evaluation speech; a reviewer has to see exactly "
                "which overlaps the gate forgives"
            ),
            "grams_already_shared_with_the_evaluation_set": len(shared_now),
        },
        "identity_anchors": {
            "kc_a1_rows": list(KC_A1_ROWS),
            "invocation_texts": KC_A1_INVOCATION_TEXTS,
            "evaluation_word_6grams": KC_A1_EVALUATION_GRAMS,
            "registry_word_6grams": KC_A1_REGISTRY_GRAMS,
            "compact_registry_sha256": COMPACT_SHA256,
            "all_reproduced": True,
            "on_disagreement": "SystemExit before a byte is written",
        },
        "how_the_gate_is_run": (
            "rails.proposer.validate_candidate_artifact(candidate, registry_rows=..., "
            "token_counter=<the resident server's /tokenize route>, "
            "compact_baseline_tokens=3581, evaluation_query_texts="
            "scripts.build_a2t_evo_decontamination.evaluation_invocation_texts(...), "
            "registry_text=render_registry_compact(...), exemplar_texts=<the "
            "construction rows the draw showed>). The token counter is the ONLY part "
            "that needs a server, which is why candidate pricing is a separate "
            "bounded-discovery-probe row and this one is model-free"
        ),
        "gold_not_read": {
            "fields_opened": ["query", "user_request", "chat_history"],
            "fields_never_opened": list(GOLD_FIELDS_NEVER_OPENED),
            "why": (
                "the gate compares candidate text against what the SPEAKER says, which "
                "is the only leakage channel a rewritten description could have. No "
                "answer field of any evaluation row is opened"
            ),
        },
        "boundary": (
            "zero model, GPU, tokenizer, embedder, retriever, scorer, network, "
            "audio-decode and paid-API contacts. Pure text over the released tier "
            "manifests' invocation fields and tools_registry.csv"
        ),
        "status": "PREPARED_NOT_CONTACT_AUTHORITY",
    }
    registry_document = {
        "schema": "saea-a2t-evo-registry-6grams-v1",
        "study": "speech-aware-evidence-acquisition",
        "authority": AUTHORITY,
        "exposure_row": EXPOSURE_ROW_ID,
        "what": (
            "A_0's exemption list: every word 6-gram of the released compact registry "
            "block, the legal source of shared phrasing the decontamination gate "
            "subtracts before it refuses a candidate"
        ),
        "n": DECONTAMINATION_NGRAM,
        "source": "data.audio2tool_tools.render_registry_compact() with no overrides",
        "rendered_sha256": COMPACT_SHA256,
        "rendered_characters": len(compact),
        "rendered_lines": len(compact.splitlines()),
        "count": len(registry_grams),
        "set_sha256": gram_set_pin(registry_grams),
        "grams": sorted(" ".join(gram) for gram in registry_grams),
    }
    return {"decontamination": document, "registry": registry_document}


def _write(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return _sha256_text(text)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    built = build(repo_root=REPO_ROOT, lock=lock, root=data_root())
    document = built["decontamination"]
    summary = {
        "evaluation": document["evaluation_grams"],  # type: ignore[index]
        "evaluation_speaker_only": document["evaluation_grams_speaker_only"],  # type: ignore[index]
        "registry": {
            key: document["a_0_exemption"][key]  # type: ignore[index]
            for key in (
                "distinct_word_6grams",
                "set_sha256",
                "rendered_sha256",
                "grams_already_shared_with_the_evaluation_set",
            )
        },
        "anchors_reproduced": document["identity_anchors"],  # type: ignore[index]
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    }
    if args.write:
        summary["decontamination_sha256"] = _write(
            CHECK_DIR / "decontamination.json", document
        )
        summary["registry_6grams_sha256"] = _write(
            CHECK_DIR / "registry-6grams.json", built["registry"]
        )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
