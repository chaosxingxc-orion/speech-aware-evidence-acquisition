#!/usr/bin/env python3
"""Freeze the coverage-guaranteed SLURP test SAMPLE and its CLOSURE complement.

Owner decision 141 of 2026-09-27
(``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``): the
programme's absolute 95 per cent intent target of decision 137 is a TEST-SET
number; dev sampling comes first for iteration, and a coverage-guaranteed
sample of the test split is PERMITTED for comparison, superseding decisions
99 / 107 / 108 to that extent and no further. The recorded cost of that
permission is the design this script implements:

1. the sample is drawn ONCE and its COMPLEMENT is sealed at the same moment
   as the closure roster for the final read (``SLURP-TEST-SAMPLE-<n>-V1`` and
   ``SLURP-TEST-CLOSURE-<13078-n>-V1`` are written by one invocation);
2. the size keeps the complement's power (the size table below is computed
   from the instrument, and both receipts carry it);
3. coverage means every scored intent present with a floor per stratum,
   reported in natural-mixture and equal-stratum weightings;
4. the sample serves MILESTONE checks, never per-round iteration;
5. test gold is read for stratification, offline, exactly here, and is
   recorded as exactly that;
6. every contact with either roster stays behind the committed owner
   allowance the fail-closed ``final-report`` split role already requires.

**This script registers nothing, authorises nothing and contacts nothing.**
No model, tokenizer, encoder, ASR, scorer, server, network or GPU is reached;
the offline guard is armed before the first input is opened; no audio file is
opened (durations are copied from the frozen parent receipt); no worker pool
is used at all.

The unit of the draw is the UTTERANCE, not the recording
--------------------------------------------------------
The one design that satisfies BOTH "sample + complement = the frozen 13,078"
AND "the closure read stays independent of the roster that was compared
against" is a partition by test prompt: every recording of a selected
utterance goes to the sample, every recording of every other utterance goes to
the closure roster. A recording-level draw (the ``SLURP-DEV-2000-ADDED-V1``
precedent) would leave the other 3.4 recordings of every sampled SENTENCE
inside the closure roster, so a milestone read of the sample would expose text
the final read is later scored on. The sample is therefore sized in prompts
(``round(n * 2974 / 13078)`` for a target of ``n`` recordings) and the
realised recording count names the receipts.

Stratification (the rule, stated once)
--------------------------------------
Stratum = the gold intent ``scenario_action`` of the prompt, read offline from
the governed ``test.jsonl`` (decision 141 item 5). Capacities are test prompt
counts per intent. Per intent:

* capacity >= SAMPLE_FLOOR + CLOSURE_FLOOR: the sample takes a floor of
  SAMPLE_FLOOR prompts and CLOSURE_FLOOR prompts are reserved for the closure
  roster; the remainder is apportioned by ``core.roster.mixture_quotas``
  against test's own natural prompt mixture, capped by what is left after
  both floors;
* 2 <= capacity < SAMPLE_FLOOR + CLOSURE_FLOOR: split as evenly as possible,
  the CLOSURE roster taking the larger half -- both rosters keep the intent;
* capacity == 1: the single prompt goes to the CLOSURE roster. The final read
  must cover every scored intent; the sample cannot cover an intent whose
  whole test presence is one prompt without emptying it from the final read.
  This deviates deliberately from "take all of them" and is recorded.

The seeded draw is ``core.roster.freeze_roster`` over prompt candidates (one
shared ``random.Random(SEED)`` advanced across intents in ascending name
order; the module docstring of ``core.roster`` states the rule). The stratum
is WITHHELD per item: the receipts publish per-intent counts as aggregates
and never a label beside a sample id.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>:<repo>/src \\
      python scripts/build_slurp_test_sample_roster.py --table-only
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>:<repo>/src \\
      python scripts/build_slurp_test_sample_roster.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    EVALUATION_ROSTER_ROLE,
    RosterError,
    RosterItem,
    canonical_receipt_bytes,
    freeze_roster,
    mixture_quotas,
    read_roster,
    verify_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _governed_roots,
    _read_jsonl,
    _validate_recording_filename,
    load_slurp_construction_utterances,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.rails.proposer import (  # noqa: E402
    DECONTAMINATION_NGRAM,
    ngram_digest,
    word_ngrams,
)

CARRIER = "slurp"
SPLIT = "test"
#: Both rosters are TEST rosters and both stay behind the fail-closed owner
#: allowance (decision 141 item 6); the role is the one contracts.plan admits
#: for a final-reporting split and nothing else.
SPLIT_ROLE = "final-report"
SEED = 20260927
SAMPLE_FLOOR = 5
CLOSURE_FLOOR = 5
#: The design target in RECORDINGS; the draw is sized in prompts
#: (round(target * test_prompts / test_recordings)) and the realised recording
#: count names the receipts. Chosen from the size table (design note
#: docs/readiness/2026-09-27-slurp-test-sample-design-v1.md).
DESIGN_TARGET_RECORDINGS = 3000
TABLE_TARGETS = (1000, 1500, 2000, 3000)

PARENT_RELPATH = "docs/receipts/rosters/slurp-test-full-13078-v1.json"
PARENT_ROSTER_ID = "SLURP-TEST-FULL-13078-V1"
PARENT_SPLIT_IDENTITY_HASH = (
    "7247647b8c8b37becd564b7031691565d4e6b09d8e124823054906d36372c95d"
)
PARENT_CARRIER_IDENTITY_HASH = (
    "3f7063cb8b1e60d69c383d2215b5f244bbd7164d484010193a093a5e879389bd"
)
EXPECTED_RECORDINGS = 13078
EXPECTED_UTTERANCES = 2974
SPLIT_IDENTITY_RELPATH = "docs/receipts/knowledge/slurp-split-identity.json"
FULL_BUILDER_RELPATH = "scripts/build_slurp_test_full_roster.py"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-27-slurp-test-sample-roster"
)
DISJOINTNESS_NAME = "disjointness.json"
SIZE_TABLE_NAME = "size-table.json"
DESIGN_NOTE_RELPATH = "docs/readiness/2026-09-27-slurp-test-sample-design-v1.md"
AUTHORITY = (
    "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md owner decision "
    "141 (2026-09-27): a coverage-guaranteed sample of the test split is permitted for "
    "comparison; drawn once, complement sealed at the same moment as the closure roster; "
    "test gold read for stratification offline only; every contact behind the "
    "final-report owner allowance"
)
GENERATOR = "scripts/build_slurp_test_sample_roster.py"

#: The instrument the size table is scaled from: the DEV-2000-ADDED own null
#: (PLAN vs PLANr, utterance-clustered CI95 bootstrap, 1,000 recordings over
#: 913 prompts), read 2026-09-24 as
#: SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1.
DEV_OWN_NULL = {
    "source": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-OWN-NULL-V1 (2026-09-24)",
    "h_intent_pp": 1.1520,
    "h_slu_pp": 1.2525,
    "recordings": 1000,
    "utterances": 913,
    "clustering": "utterance-clustered CI95 bootstrap",
}
#: Measured per-row costs of the locked system: protocol draft section 7.3
#: (B4b replicate merged manifest, 5.021 contacts/row, 3.4651 GPU-h per 1,080
#: rows at the September geometry) and the DEV-2000-ADDED replicate
#: (4,090 contacts / 1.649 GPU-h for 1,000 rows at np4, 2026-09-24).
COST_MODEL = {
    "protocol_7_3": {"contacts_per_row": 5.021, "gpu_hours_per_row": 3.4651 / 1080},
    "dev2000_added_replicate_np4": {"contacts_per_row": 4.090, "gpu_hours_per_row": 1.649 / 1000},
    "direct_arm_contacts_per_row": 1.0,
}
TARGET_ACCURACY = 0.95
TODAY_ACCURACY = 0.8222  # v2.0 lock arm on TRAIN Fold A (decision 137)
Z95 = 1.959964


class SampleBuildError(RuntimeError):
    """The rosters cannot be frozen from these inputs -- fail closed."""


# --------------------------------------------------------------------------- #
# reuse of the full-test builder (one base, no second implementation)
# --------------------------------------------------------------------------- #


def load_full_builder():
    """Import ``scripts/build_slurp_test_full_roster.py`` by file path.

    By path, not by ``import scripts.…``: the shared venv carries a regular
    top-level ``scripts`` package (verl 0.8.0) that shadows this repository's
    namespace directory. Its source enumerators, governed-metadata check and
    exposure-closure pass are the ONE implementation of those steps.
    """

    path = REPO_ROOT / FULL_BUILDER_RELPATH
    spec = importlib.util.spec_from_file_location("saea_build_slurp_test_full_roster", path)
    if spec is None or spec.loader is None:
        raise SampleBuildError(f"cannot load {FULL_BUILDER_RELPATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utterance_id_of(sample_id: str) -> str:
    parts = sample_id.split(":")
    if len(parts) != 4:
        raise SampleBuildError(f"malformed SLURP sample id {sample_id!r}")
    return ":".join(parts[:3])


def prompt_number_of(sample_id_or_utterance: str) -> str:
    return sample_id_or_utterance.split(":")[2]


def recording_filename_of(sample_id: str) -> str:
    return sample_id.split(":")[3] + ".flac"


# --------------------------------------------------------------------------- #
# the offline gold read (decision 141 item 5)
# --------------------------------------------------------------------------- #


def read_test_strata(
    metadata_dir: Path,
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """``utterance_id -> intent`` and ``utterance_id -> [recording sample ids]``.

    Reads ``slurp_id``, ``scenario``, ``action`` and ``recordings[].file`` of the
    governed ``test.jsonl`` and nothing else. The intent is the stratum; it is
    published only as per-intent aggregate counts. No sentence, token, entity,
    WER or status field is touched here.
    """

    path = metadata_dir / "test.jsonl"
    if not path.is_file():
        raise SampleBuildError(f"SLURP test metadata file missing: {path}")
    intent_by_utterance: dict[str, str] = {}
    recordings_by_utterance: dict[str, list[str]] = {}
    for line_no, raw in enumerate(_read_jsonl(path), start=1):
        context = f"SLURP test.jsonl line {line_no} (stratification pass)"
        slurp_id = raw.get("slurp_id")
        if isinstance(slurp_id, bool) or not isinstance(slurp_id, int):
            raise SampleBuildError(f"{context}: slurp_id must be an int")
        scenario = raw.get("scenario")
        action = raw.get("action")
        if not isinstance(scenario, str) or not scenario:
            raise SampleBuildError(f"{context}: scenario must be a non-empty string")
        if not isinstance(action, str) or not action:
            raise SampleBuildError(f"{context}: action must be a non-empty string")
        recordings = raw.get("recordings")
        if not isinstance(recordings, list) or not recordings:
            raise SampleBuildError(f"{context}: recordings must be a non-empty list")
        utterance = f"slurp:{SPLIT}:{slurp_id:06d}"
        if utterance in intent_by_utterance:
            raise SampleBuildError(f"{context}: duplicate slurp_id")
        intent_by_utterance[utterance] = f"{scenario}_{action}"
        ids: list[str] = []
        for recording in recordings:
            if not isinstance(recording, Mapping):
                raise SampleBuildError(f"{context}: recording entry must be an object")
            filename = _validate_recording_filename(recording.get("file"), context)
            ids.append(f"{utterance}:{filename[: -len('.flac')]}")
        if len(set(ids)) != len(ids):
            raise SampleBuildError(f"{context}: duplicate recording file")
        recordings_by_utterance[utterance] = sorted(ids)
    if not intent_by_utterance:
        raise SampleBuildError("the SLURP test split resolved to zero prompts")
    return intent_by_utterance, recordings_by_utterance


def test_sentences(metadata_dir: Path, wanted_numbers: Sequence[str]) -> Iterator[str]:
    """The ``sentence`` field of exactly the wanted test prompts, as a generator.

    Carried from ``scripts/build_slurp_dev2000_roster.py`` (which carried it
    from ``scripts/build_slurp_evo_decontamination.py``): no caller holds the
    corpus, and what leaves this module is digests and counts. This is the
    only place a test ``sentence`` is touched, and it is touched for the
    TRAIN text-overlap count alone.
    """

    remaining = set(wanted_numbers)
    path = metadata_dir / "test.jsonl"
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            key = f"{int(raw['slurp_id']):06d}"
            if key not in remaining:
                continue
            remaining.discard(key)
            sentence = raw.get("sentence")
            if not isinstance(sentence, str) or not sentence.strip():
                raise SampleBuildError(f"test prompt {key} carries no sentence")
            yield sentence.strip()
    if remaining:
        raise SampleBuildError(f"{len(remaining)} wanted test prompt(s) absent from test.jsonl")


def sentence_digest(text: str) -> str:
    return hashlib.sha256(" ".join(text.lower().split()).encode("utf-8")).hexdigest()


def digest_set_hash(digests: set[str]) -> str:
    return hashlib.sha256("\n".join(sorted(digests)).encode("utf-8")).hexdigest()


def text_profile(
    metadata_dir: Path,
    wanted_numbers: Sequence[str],
    train_sentence_digests: frozenset[str],
    train_gram_digests: frozenset[str],
) -> tuple[dict[str, object], set[str]]:
    """Digest-only text profile of one test population against TRAIN.

    Returns the profile and the population's sentence-digest set (kept in
    memory only, to count sample-vs-closure duplicate sentences).
    """

    sentence_digests: set[str] = set()
    gram_digests: set[str] = set()
    exact_hits = 0
    sharing_gram = 0
    utterances = 0
    for sentence in test_sentences(metadata_dir, wanted_numbers):
        utterances += 1
        digest = sentence_digest(sentence)
        sentence_digests.add(digest)
        if digest in train_sentence_digests:
            exact_hits += 1
        grams = {ngram_digest(gram) for gram in word_ngrams(sentence, DECONTAMINATION_NGRAM)}
        gram_digests |= grams
        if grams & train_gram_digests:
            sharing_gram += 1
    profile = {
        "utterances_read": utterances,
        "distinct_sentence_digests": len(sentence_digests),
        "exact_sentence_matches_in_train_construction_pool": exact_hits,
        f"utterances_sharing_a_train_{DECONTAMINATION_NGRAM}gram": sharing_gram,
        "sentence_digest_set_sha256": digest_set_hash(sentence_digests),
        "gram_digest_set_sha256": digest_set_hash(gram_digests),
    }
    return profile, sentence_digests


def read_speaker_index(metadata_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    """``recording filename -> speaker id`` and ``recording filename -> prompt
    author id`` from the governed ``metadata.json``. The ids stay in memory;
    only counts leave this module."""

    path = metadata_dir / "metadata.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise SampleBuildError("SLURP metadata.json must be an object")
    speaker_by_file: dict[str, str] = {}
    author_by_file: dict[str, str] = {}
    for entry in document.values():
        if not isinstance(entry, Mapping):
            continue
        author = entry.get("userid_amt")
        recordings = entry.get("recordings")
        if not isinstance(recordings, Mapping):
            continue
        for filename, recording in recordings.items():
            if not isinstance(filename, str) or not isinstance(recording, Mapping):
                continue
            speaker = recording.get("usrid")
            if isinstance(speaker, str) and speaker:
                previous = speaker_by_file.get(filename)
                if previous is not None and previous != speaker:
                    raise SampleBuildError(f"conflicting speaker identity for {filename!r}")
                speaker_by_file[filename] = speaker
            if isinstance(author, str) and author:
                author_by_file[filename] = author
    if not speaker_by_file:
        raise SampleBuildError("SLURP metadata.json resolved no speaker identity")
    return speaker_by_file, author_by_file


# --------------------------------------------------------------------------- #
# the stratification rule (pure; unit-tested)
# --------------------------------------------------------------------------- #


def partition_quotas(
    capacity: Mapping[str, int],
    total_utterances: int,
    *,
    sample_floor: int = SAMPLE_FLOOR,
    closure_floor: int = CLOSURE_FLOOR,
    weights: Mapping[str, int] | None = None,
) -> tuple[dict[str, int], dict[str, object]]:
    """Per-intent SAMPLE quotas in prompts, and the accounting behind them.

    See the module docstring for the rule. ``weights`` default to the
    capacities themselves (test's natural prompt mixture).
    """

    if isinstance(total_utterances, bool) or not isinstance(total_utterances, int):
        raise SampleBuildError("total_utterances must be an int")
    if sample_floor < 1 or closure_floor < 1:
        raise SampleBuildError("floors must be positive")
    weights = dict(weights) if weights is not None else dict(capacity)
    base: dict[str, int] = {}
    available: dict[str, int] = {}
    even_split: list[dict[str, int | str]] = []
    single: list[str] = []
    for intent in sorted(capacity):
        cap = int(capacity[intent])
        if cap < 1:
            raise SampleBuildError(f"intent {intent!r} has no test prompt")
        if cap >= sample_floor + closure_floor:
            base[intent] = sample_floor
            available[intent] = cap - sample_floor - closure_floor
        elif cap >= 2:
            base[intent] = cap // 2
            available[intent] = 0
            even_split.append(
                {"intent": intent, "test_utterances": cap, "sample": cap // 2, "closure": cap - cap // 2}
            )
        else:
            base[intent] = 0
            available[intent] = 0
            single.append(intent)
    floor_total = sum(base.values())
    remainder = total_utterances - floor_total
    if remainder < 0:
        raise SampleBuildError(
            f"total_utterances {total_utterances} is below the floor-driven minimum {floor_total}"
        )
    if remainder > 0:
        extra = mixture_quotas(remainder, weights, available)
    else:
        extra = {intent: 0 for intent in capacity}
    quotas = {intent: base[intent] + int(extra.get(intent, 0)) for intent in sorted(capacity)}
    for intent, quota in quotas.items():
        cap = int(capacity[intent])
        if quota > cap:
            raise SampleBuildError(f"quota for {intent!r} exceeds its capacity")
        if cap >= 2 and (quota < 1 or cap - quota < 1):
            raise SampleBuildError(f"intent {intent!r} would be absent from one roster")
    accounting = {
        "sample_floor_utterances": sample_floor,
        "closure_floor_utterances": closure_floor,
        "floor_driven_utterances": floor_total,
        "remainder_utterances": remainder,
        "remainder_rule": (
            "core.roster.mixture_quotas against test's natural prompt mixture, capped by "
            "capacity minus both floors"
        ),
        "even_split_intents": even_split,
        "single_prompt_intents_to_closure": single,
        "intents": len(capacity),
    }
    return quotas, accounting


def verify_partition(
    parent_ids: Sequence[str], sample_ids: Sequence[str], closure_ids: Sequence[str]
) -> dict[str, object]:
    """Prove sample ∩ closure = ∅ and sample ∪ closure = parent, at three levels."""

    parent = set(parent_ids)
    sample = set(sample_ids)
    closure = set(closure_ids)
    if len(sample) != len(sample_ids) or len(closure) != len(closure_ids):
        raise SampleBuildError("a roster repeats a sample id")
    intersection = sample & closure
    union = sample | closure
    sample_utt = {utterance_id_of(value) for value in sample}
    closure_utt = {utterance_id_of(value) for value in closure}
    sample_num = {prompt_number_of(value) for value in sample}
    closure_num = {prompt_number_of(value) for value in closure}
    proof = {
        "intersection_recordings": len(intersection),
        "intersection_utterances": len(sample_utt & closure_utt),
        "intersection_prompt_numbers": len(sample_num & closure_num),
        "union_recordings": len(union),
        "union_equals_parent": union == parent,
        "union_split_identity_hash": split_identity_hash(prefixed(CARRIER, sorted(union))),
        "parent_recordings": len(parent),
        "sample_recordings": len(sample),
        "closure_recordings": len(closure),
        "sample_utterances": len(sample_utt),
        "closure_utterances": len(closure_utt),
    }
    if intersection or union != parent or (sample_utt & closure_utt):
        raise SampleBuildError(f"partition proof failed: {json.dumps(proof, sort_keys=True)}")
    return proof


# --------------------------------------------------------------------------- #
# the size table (decision 141 item 2)
# --------------------------------------------------------------------------- #


def half_width_pp(p: float, n: int) -> float:
    return round(100.0 * Z95 * math.sqrt(p * (1.0 - p) / n), 3)


def paired_half_width_pp(utterances: int) -> float:
    return round(
        float(DEV_OWN_NULL["h_intent_pp"]) * math.sqrt(int(DEV_OWN_NULL["utterances"]) / utterances),
        3,
    )


def utterances_for_target(target_recordings: int, total_utterances: int, total_recordings: int) -> int:
    return int(round(target_recordings * total_utterances / total_recordings))


def weighted_half_width_pp(
    p: float, weights: Mapping[str, float], counts: Mapping[str, float]
) -> float:
    """CI95 half-width of a stratum-weighted accuracy: 1.96*sqrt(sum w_i^2 p(1-p)/n_i).

    Strata with no rows in the roster are dropped and the remaining weights are
    renormalised, which is exactly what a post-stratified read of that roster
    has to do.
    """

    active = {key: float(weights[key]) for key in weights if float(counts.get(key, 0)) > 0}
    total = sum(active.values())
    if total <= 0:
        raise SampleBuildError("weighted_half_width_pp: no stratum carries weight")
    variance = sum(
        (weight / total) ** 2 * p * (1.0 - p) / float(counts[key]) for key, weight in active.items()
    )
    return round(100.0 * Z95 * math.sqrt(variance), 3)


def size_table(
    capacity: Mapping[str, int],
    recording_capacity: Mapping[str, int],
    total_recordings: int,
    targets: Sequence[int],
) -> dict[str, object]:
    total_utterances = sum(capacity.values())
    natural_weights = {key: recording_capacity[key] / total_recordings for key in capacity}
    equal_weights = {key: 1.0 for key in capacity}
    rows = []
    floors = {}
    for floor in (3, 5, 8):
        floors[str(floor)] = sum(
            floor if cap >= 2 * floor else (cap // 2 if cap >= 2 else 0)
            for cap in capacity.values()
        )
    design_minimum = floors[str(SAMPLE_FLOOR)]
    for target in targets:
        u = utterances_for_target(target, total_utterances, total_recordings)
        m = total_recordings - target
        u_c = total_utterances - u
        feasible = u >= design_minimum
        weighted: dict[str, object] = {}
        capacity_note = None
        if feasible:
            try:
                quotas, accounting = partition_quotas(capacity, u)
            except (SampleBuildError, RosterError) as error:
                # A target so large that the remainder exceeds what survives both
                # floors is infeasible for the opposite reason; say so, do not raise.
                feasible = False
                capacity_note = f"the remainder exceeds the capacity left after both floors: {error}"
        if feasible:
            floor_driven = int(accounting["floor_driven_utterances"])
            remainder = int(accounting["remainder_utterances"])
            rec_per_prompt = {key: recording_capacity[key] / capacity[key] for key in capacity}
            sample_prompts = {key: quotas[key] for key in capacity}
            sample_expected_rec = {key: quotas[key] * rec_per_prompt[key] for key in capacity}
            closure_prompts = {key: capacity[key] - quotas[key] for key in capacity}
            closure_expected_rec = {
                key: (capacity[key] - quotas[key]) * rec_per_prompt[key] for key in capacity
            }
            weighted = {
                "sample_natural_mixture_poststratified_h_pp_at_p95": {
                    "rho1_prompts": weighted_half_width_pp(TARGET_ACCURACY, natural_weights, sample_prompts),
                    "rho0_expected_recordings": weighted_half_width_pp(
                        TARGET_ACCURACY, natural_weights, sample_expected_rec
                    ),
                },
                "sample_equal_stratum_h_pp_at_p95": {
                    "rho1_prompts": weighted_half_width_pp(TARGET_ACCURACY, equal_weights, sample_prompts),
                    "rho0_expected_recordings": weighted_half_width_pp(
                        TARGET_ACCURACY, equal_weights, sample_expected_rec
                    ),
                },
                "closure_natural_mixture_poststratified_h_pp_at_p95": {
                    "rho1_prompts": weighted_half_width_pp(TARGET_ACCURACY, natural_weights, closure_prompts),
                    "rho0_expected_recordings": weighted_half_width_pp(
                        TARGET_ACCURACY, natural_weights, closure_expected_rec
                    ),
                },
                "closure_equal_stratum_h_pp_at_p95": {
                    "rho1_prompts": weighted_half_width_pp(TARGET_ACCURACY, equal_weights, closure_prompts),
                    "rho0_expected_recordings": weighted_half_width_pp(
                        TARGET_ACCURACY, equal_weights, closure_expected_rec
                    ),
                },
                "intents_absent_from_sample": sorted(key for key in capacity if quotas[key] == 0),
            }
        else:
            floor_driven = design_minimum
            remainder = u - design_minimum  # negative: the floors alone exceed the prompt count
        rows.append(
            {
                "target_recordings": target,
                "sample_utterances": u,
                "closure_recordings": m,
                "closure_utterances": u_c,
                "feasible_at_design_floor": feasible,
                **weighted,
                "infeasibility_note": (
                    None
                    if feasible
                    else capacity_note
                    or (
                        f"the floor rule alone needs {design_minimum} prompts (about "
                        f"{round(design_minimum * total_recordings / total_utterances)} recordings); "
                        f"a {target}-recording sample cannot carry every intent at floor {SAMPLE_FLOOR}"
                    )
                ),
                "floor_driven_utterances_at_design_floor": floor_driven,
                "floor_driven_share_of_sample": round(floor_driven / u, 3),
                "remainder_utterances": remainder,
                "floor_driven_utterances_by_floor": floors,
                "sample_h_abs_pp_at_p95": {
                    "rho0_recordings": half_width_pp(TARGET_ACCURACY, target),
                    "rho1_utterances": half_width_pp(TARGET_ACCURACY, u),
                },
                "sample_h_abs_pp_at_p82": {
                    "rho0_recordings": half_width_pp(TODAY_ACCURACY, target),
                    "rho1_utterances": half_width_pp(TODAY_ACCURACY, u),
                },
                "closure_h_abs_pp_at_p95": {
                    "rho0_recordings": half_width_pp(TARGET_ACCURACY, m),
                    "rho1_utterances": half_width_pp(TARGET_ACCURACY, u_c),
                },
                "closure_h_abs_pp_at_p82": {
                    "rho0_recordings": half_width_pp(TODAY_ACCURACY, m),
                    "rho1_utterances": half_width_pp(TODAY_ACCURACY, u_c),
                },
                "sample_h_paired_pp_scaled_from_dev_null": paired_half_width_pp(u),
                "closure_h_paired_pp_scaled_from_dev_null": paired_half_width_pp(u_c),
                "cost_per_milestone_system_arm": {
                    "contacts_protocol_7_3": round(
                        target * COST_MODEL["protocol_7_3"]["contacts_per_row"]
                    ),
                    "gpu_hours_protocol_7_3": round(
                        target * COST_MODEL["protocol_7_3"]["gpu_hours_per_row"], 2
                    ),
                    "contacts_np4_replicate": round(
                        target * COST_MODEL["dev2000_added_replicate_np4"]["contacts_per_row"]
                    ),
                    "gpu_hours_np4_replicate": round(
                        target * COST_MODEL["dev2000_added_replicate_np4"]["gpu_hours_per_row"], 2
                    ),
                    "direct_arm_contacts": target,
                },
            }
        )
    full = {
        "recordings": total_recordings,
        "utterances": total_utterances,
        "h_abs_pp_at_p95": {
            "rho0_recordings": half_width_pp(TARGET_ACCURACY, total_recordings),
            "rho1_utterances": half_width_pp(TARGET_ACCURACY, total_utterances),
        },
        "h_paired_pp_scaled_from_dev_null": paired_half_width_pp(total_utterances),
    }
    return {
        "schema": "saea-test-sample-size-table-v1",
        "study": "speech-aware-evidence-acquisition",
        "authority": AUTHORITY,
        "generator": GENERATOR,
        "unit_note": (
            "The draw is a partition by test PROMPT, so the conservative n is the prompt "
            "count: rho is the within-prompt correlation of intent correctness across a "
            "prompt's recordings (about 4.4 per prompt). rho=0 treats recordings as "
            "independent; rho=1 treats every recording of a prompt as one observation. "
            "The truth lies between and is closer to rho=1 for a text-driven intent error."
        ),
        "instrument": {
            "absolute": (
                "CI95 half-width of a proportion, 1.96*sqrt(p(1-p)/n_eff), at the target "
                "p=0.95 (decision 137) and at today's p=0.8222 (v2.0 lock, TRAIN Fold A)"
            ),
            "paired": (
                "the DEV-2000-ADDED own-null intent half-width scaled by "
                "sqrt(913 / prompts); the PLAN-vs-PLANr null is the programme's own paired "
                "instrument"
            ),
            "weighted": (
                "the natural-mixture number of a floored roster is POST-STRATIFIED (per-intent "
                "accuracy weighted by full-test recording shares) and the equal-stratum number "
                "weights every intent 1/K; their half-widths are 1.96*sqrt(sum w_i^2 p(1-p)/n_i) "
                "over the per-intent prompt counts (rho=1) or expected recordings (rho=0) the "
                "floor rule leaves in each roster, at p=0.95; an intent absent from a roster is "
                "dropped and the weights renormalised"
            ),
            "dev_own_null": DEV_OWN_NULL,
            "cost_model": COST_MODEL,
        },
        "design_floor": {"sample": SAMPLE_FLOOR, "closure": CLOSURE_FLOOR},
        "full_test_reference": full,
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #


def _print(document: object) -> None:
    print(json.dumps(document, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the two receipts and the proof")
    parser.add_argument(
        "--table-only", action="store_true", help="print the intent census and the size table, then exit"
    )
    parser.add_argument("--target-recordings", type=int, default=DESIGN_TARGET_RECORDINGS)
    args = parser.parse_args(argv)
    if args.target_recordings < 100 or args.target_recordings >= EXPECTED_RECORDINGS:
        raise SystemExit("--target-recordings must lie strictly inside (100, 13078)")

    attempts = arm_offline_guard()
    full = load_full_builder()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    governed = full._verify_governed_metadata(lock, root)  # bytes vs the lock pin, before any parse
    _audio_relpath, _audio_root, metadata_dir = _governed_roots(lock, root)

    # ---- the frozen parent ---------------------------------------------------
    parent = read_roster(REPO_ROOT / PARENT_RELPATH)
    if parent.get("roster_id") != PARENT_ROSTER_ID:
        raise SystemExit("the parent receipt is not SLURP-TEST-FULL-13078-V1")
    if parent["split_identity_hash"] != PARENT_SPLIT_IDENTITY_HASH:
        raise SystemExit("the parent receipt's split identity hash is not the frozen one")
    parent_items = {str(item["sample_id"]): dict(item) for item in parent["items"]}
    parent_ids = sorted(parent_items)
    if len(parent_ids) != EXPECTED_RECORDINGS:
        raise SystemExit(f"the parent carries {len(parent_ids)} recordings, expected {EXPECTED_RECORDINGS}")
    parent_file_sha256 = sha256_file(REPO_ROOT / PARENT_RELPATH)

    frozen = json.loads((REPO_ROOT / SPLIT_IDENTITY_RELPATH).read_text(encoding="utf-8"))
    frozen_block = frozen["splits"][SPLIT]
    if list(frozen_block["ids"]) != parent_ids:
        raise SystemExit("the parent's ids disagree with the frozen split identity receipt")
    if frozen_block["identity_hash"] != PARENT_CARRIER_IDENTITY_HASH:
        raise SystemExit("the frozen split identity receipt's test hash moved")

    # ---- the offline gold read -----------------------------------------------
    intent_by_utterance, recordings_by_utterance = read_test_strata(metadata_dir)
    live_ids = sorted(sid for ids in recordings_by_utterance.values() for sid in ids)
    if live_ids != parent_ids:
        raise SystemExit("the stratification pass enumerated a different recording set than the parent")
    if len(intent_by_utterance) != EXPECTED_UTTERANCES:
        raise SystemExit(f"{len(intent_by_utterance)} test prompts, expected {EXPECTED_UTTERANCES}")
    capacity = dict(sorted(Counter(intent_by_utterance.values()).items()))
    recording_capacity: dict[str, int] = defaultdict(int)
    for utterance, intent in intent_by_utterance.items():
        recording_capacity[intent] += len(recordings_by_utterance[utterance])
    recording_capacity = dict(sorted(recording_capacity.items()))
    per_utterance_counts = Counter(len(ids) for ids in recordings_by_utterance.values())

    table = size_table(capacity, recording_capacity, EXPECTED_RECORDINGS, TABLE_TARGETS)
    census = {
        "intents_present": len(capacity),
        "test_utterances": len(intent_by_utterance),
        "test_recordings": len(parent_ids),
        "recordings_per_utterance_distribution": dict(sorted(per_utterance_counts.items())),
        "test_utterances_by_intent": capacity,
        "test_recordings_by_intent": recording_capacity,
    }
    if args.table_only:
        _print({"census": census, "size_table": table})
        return 0

    # ---- the draw --------------------------------------------------------------
    total_u = utterances_for_target(args.target_recordings, EXPECTED_UTTERANCES, EXPECTED_RECORDINGS)
    quotas, accounting = partition_quotas(capacity, total_u)
    candidates = [
        RosterItem(sample_id=utterance, stratum=intent, extra={})
        for utterance, intent in sorted(intent_by_utterance.items())
    ]
    draw = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=candidates,
        per_stratum=quotas,
        seed=SEED,
        split_role=SPLIT_ROLE,
        roster_id="SLURP-TEST-SAMPLE-PROMPT-DRAW",
        roster_role=EVALUATION_ROSTER_ROLE,
    )
    sample_utterances = sorted(str(item["sample_id"]) for item in draw["items"])
    if len(sample_utterances) != total_u:
        raise SystemExit("the prompt draw did not fill its quotas")
    sample_utterance_set = set(sample_utterances)
    sample_ids = sorted(
        sid for utterance in sample_utterances for sid in recordings_by_utterance[utterance]
    )
    closure_ids = sorted(
        sid
        for utterance, ids in recordings_by_utterance.items()
        if utterance not in sample_utterance_set
        for sid in ids
    )
    partition = verify_partition(parent_ids, sample_ids, closure_ids)
    if partition["union_split_identity_hash"] != PARENT_SPLIT_IDENTITY_HASH:
        raise SystemExit("the union of the two rosters does not hash to the parent")
    n_sample = len(sample_ids)
    n_closure = len(closure_ids)
    sample_roster_id = f"SLURP-TEST-SAMPLE-{n_sample}-V1"
    closure_roster_id = f"SLURP-TEST-CLOSURE-{n_closure}-V1"
    sample_relpath = f"docs/receipts/rosters/slurp-test-sample-{n_sample}-v1.json"
    closure_relpath = f"docs/receipts/rosters/slurp-test-closure-{n_closure}-v1.json"

    def items_for(ids: Sequence[str]) -> list[dict[str, object]]:
        rows = []
        for sid in ids:
            source = parent_items[sid]
            rows.append(
                {
                    "sample_id": sid,
                    "utterance_id": utterance_id_of(sid),
                    "headset": bool(source["headset"]),
                    "audio_seconds": source["audio_seconds"],
                }
            )
        return rows

    sample_items = items_for(sample_ids)
    closure_items = items_for(closure_ids)
    sample_hash = split_identity_hash(prefixed(CARRIER, sample_ids))
    closure_hash = split_identity_hash(prefixed(CARRIER, closure_ids))
    sample_bare_hash = hashlib.sha256("\n".join(sample_ids).encode("utf-8")).hexdigest()
    closure_bare_hash = hashlib.sha256("\n".join(closure_ids).encode("utf-8")).hexdigest()

    # ---- per-intent tables (aggregates only) ---------------------------------
    sample_u_by_intent: Counter[str] = Counter(intent_by_utterance[u] for u in sample_utterances)
    sample_r_by_intent: Counter[str] = Counter(intent_by_utterance[utterance_id_of(s)] for s in sample_ids)
    closure_r_by_intent: Counter[str] = Counter(intent_by_utterance[utterance_id_of(s)] for s in closure_ids)
    per_intent = {}
    for intent in capacity:
        per_intent[intent] = {
            "test_utterances": capacity[intent],
            "test_recordings": recording_capacity[intent],
            "sample_utterances": int(sample_u_by_intent.get(intent, 0)),
            "sample_recordings": int(sample_r_by_intent.get(intent, 0)),
            "closure_utterances": capacity[intent] - int(sample_u_by_intent.get(intent, 0)),
            "closure_recordings": recording_capacity[intent] - int(sample_r_by_intent.get(intent, 0)),
        }
    for intent, row in per_intent.items():
        if row["sample_utterances"] != quotas[intent]:
            raise SystemExit(f"the draw disagrees with its quota for one intent")
        if row["closure_utterances"] < 1:
            raise SystemExit("an intent is absent from the closure roster")
    intents_absent_from_sample = sorted(i for i, r in per_intent.items() if r["sample_utterances"] == 0)
    weights_recordings = {
        intent: round(recording_capacity[intent] / EXPECTED_RECORDINGS, 6) for intent in capacity
    }
    weights_utterances = {
        intent: round(capacity[intent] / EXPECTED_UTTERANCES, 6) for intent in capacity
    }

    # ---- speaker and prompt-author overlap (counts only) ---------------------
    speaker_by_file, author_by_file = read_speaker_index(metadata_dir)

    def speakers_of(ids: Sequence[str]) -> set[str]:
        out = set()
        for sid in ids:
            value = speaker_by_file.get(recording_filename_of(sid))
            if value is None:
                raise SystemExit("a test recording has no speaker identity in metadata.json")
            out.add(value)
        return out

    def authors_of(ids: Sequence[str]) -> tuple[set[str], int]:
        """Prompt authors of the rows, and how many rows have no author id at all
        (``userid_amt`` is absent for part of the corpus; that is a fact of the
        release, counted rather than refused)."""

        out = set()
        unknown = 0
        for sid in ids:
            value = author_by_file.get(recording_filename_of(sid))
            if value is None:
                unknown += 1
            else:
                out.add(value)
        return out, unknown

    sample_speakers = speakers_of(sample_ids)
    closure_speakers = speakers_of(closure_ids)
    sample_authors, sample_author_unknown = authors_of(sample_ids)
    closure_authors, closure_author_unknown = authors_of(closure_ids)
    shared_speakers = sample_speakers & closure_speakers
    shared_authors = sample_authors & closure_authors
    closure_rows_with_sample_speaker = sum(
        1 for sid in closure_ids if speaker_by_file[recording_filename_of(sid)] in sample_speakers
    )
    closure_rows_with_sample_author = sum(
        1
        for sid in closure_ids
        if author_by_file.get(recording_filename_of(sid)) in sample_authors
    )
    overlap = {
        "statement": (
            "Speaker and prompt-author disjointness between the sample and the closure "
            "roster is IMPOSSIBLE inside one SLURP split: the same speakers recorded prompts "
            "across the whole split and the same authors wrote prompts across it. The "
            "partition is by PROMPT, which is what makes the closure roster independent of "
            "the sample at the sentence level; the speaker and author overlap below is "
            "reported so a reader knows exactly what is and is not shared. Ids are counted "
            "in memory and never written."
        ),
        "speakers": {
            "sample": len(sample_speakers),
            "closure": len(closure_speakers),
            "shared": len(shared_speakers),
            "sample_only": len(sample_speakers - closure_speakers),
            "closure_only": len(closure_speakers - sample_speakers),
            "closure_recordings_by_a_speaker_also_in_sample": closure_rows_with_sample_speaker,
            "closure_recordings_by_a_speaker_also_in_sample_share": round(
                closure_rows_with_sample_speaker / n_closure, 4
            ),
        },
        "prompt_authors": {
            "sample": len(sample_authors),
            "closure": len(closure_authors),
            "shared": len(shared_authors),
            "sample_only": len(sample_authors - closure_authors),
            "closure_only": len(closure_authors - sample_authors),
            "sample_recordings_with_no_author_id": sample_author_unknown,
            "closure_recordings_with_no_author_id": closure_author_unknown,
            "closure_recordings_by_an_author_also_in_sample": closure_rows_with_sample_author,
            "closure_recordings_by_an_author_also_in_sample_share": round(
                closure_rows_with_sample_author / n_closure, 4
            ),
        },
        "source": "governed datasets/slurp/metadata/metadata.json (recordings[].usrid, userid_amt)",
    }

    # ---- sentence-level overlap with TRAIN (digest only) ---------------------
    pool = load_slurp_construction_utterances(lock, root)
    train_sentence_digests: set[str] = set()
    train_gram_digests: set[str] = set()
    for row in pool.utterances:
        text = " ".join(row.tokens)
        if not text:
            continue
        train_sentence_digests.add(sentence_digest(text))
        train_gram_digests |= {
            ngram_digest(gram) for gram in word_ngrams(text, DECONTAMINATION_NGRAM)
        }
    sample_profile, sample_digests = text_profile(
        metadata_dir,
        sorted({prompt_number_of(u) for u in sample_utterances}),
        frozenset(train_sentence_digests),
        frozenset(train_gram_digests),
    )
    closure_profile, closure_digests = text_profile(
        metadata_dir,
        sorted(
            {prompt_number_of(u) for u in recordings_by_utterance if u not in sample_utterance_set}
        ),
        frozenset(train_sentence_digests),
        frozenset(train_gram_digests),
    )
    text_block = {
        "method": (
            "Digest only, the scripts/build_slurp_dev2000_roster.py method: test sentences are "
            "read inside one generator, compared as whole-sentence SHA-256 digests and as word "
            f"{DECONTAMINATION_NGRAM}-gram digests (rails.proposer.word_ngrams / ngram_digest) "
            "against the TRAIN construction text pool, and only counts and digest-set hashes "
            "are written. No sentence and no gram is written anywhere. This is the first time "
            "a test 'sentence' field has been touched in this repository; it was touched for "
            "this count alone, under owner decision 141 item 5 (offline test gold for the "
            "sample's construction), and it does not edit the NOT-RUN record of the frozen "
            "parent's text pass (protocol section 9 item 3), which stands as written."
        ),
        "train_construction_pool": {
            "pool_id": pool.pool_id,
            "utterance_count": pool.utterance_count,
            "source_identity_hash": pool.source_identity_hash,
            "sentence_digests": len(train_sentence_digests),
            "gram_digests": len(train_gram_digests),
        },
        "sample": sample_profile,
        "closure": closure_profile,
        "sample_closure_shared_sentence_digests": len(sample_digests & closure_digests),
        "dev_reference": {
            "note": "the same method on devel gave 1 exact match and 113 6-gram-sharing prompts of 913 (DEV-2000-ADDED) and 1 / 111 of 1,000 (DEV-1000)",
            "relpath": "docs/receipts/rosters/slurp-dev-2000-added-v1.json",
        },
        "reading": (
            "The construction-versus-knowledge guard compares ids, not sentences; these counts "
            "say how much of each test roster's TEXT a TRAIN-built knowledge store could "
            "already contain. Any non-zero exact match is a property of the corpus, not of "
            "the draw, and is reported rather than acted on."
        ),
    }

    # ---- disjointness against every other source ------------------------------
    sources = (
        full._roster_receipt_sources()
        + full._probe_sample_sources()
        + full._probe_binding_sources()
        + full._knowledge_snapshot_sources(root)
    )
    sample_set = set(sample_ids)
    closure_set = set(closure_ids)
    sample_utt = {utterance_id_of(v) for v in sample_ids}
    closure_utt = {utterance_id_of(v) for v in closure_ids}
    sample_num = {prompt_number_of(v) for v in sample_ids}
    closure_num = {prompt_number_of(v) for v in closure_ids}
    checked = []
    violations = []
    for source in sources:
        ids = source.pop("ids")
        if source.get("relpath") in {sample_relpath, closure_relpath}:
            continue  # a re-run after the write sees the rosters themselves
        other_utt = {utterance_id_of(v) for v in ids}
        other_num = {prompt_number_of(v) for v in ids}
        is_parent = source.get("relpath") == PARENT_RELPATH
        row = {
            **source,
            "items": len(ids),
            "relation": "parent (overlap is the roster itself, by construction)" if is_parent else "other",
            "sample": {
                "shared_recording_ids": len(sample_set & ids),
                "shared_utterance_ids": len(sample_utt & other_utt),
                "shared_prompt_numbers": len(sample_num & other_num),
            },
            "closure": {
                "shared_recording_ids": len(closure_set & ids),
                "shared_utterance_ids": len(closure_utt & other_utt),
                "shared_prompt_numbers": len(closure_num & other_num),
            },
        }
        checked.append(row)
        expected_sample = (n_sample, len(sample_utt), len(sample_num)) if is_parent else (0, 0, 0)
        expected_closure = (n_closure, len(closure_utt), len(closure_num)) if is_parent else (0, 0, 0)
        got_sample = tuple(row["sample"].values())
        got_closure = tuple(row["closure"].values())
        if got_sample != expected_sample or got_closure != expected_closure:
            violations.append({"relpath": source.get("relpath"), "sample": row["sample"], "closure": row["closure"]})

    closure_new = full._exposure_closure((sample_hash, closure_hash, sample_bare_hash, closure_bare_hash))
    closure_parent = full._exposure_closure((PARENT_SPLIT_IDENTITY_HASH, PARENT_CARRIER_IDENTITY_HASH))
    verdict = (
        "CLEAN"
        if not violations and not closure_new["consumed_rows"] and not closure_parent["consumed_rows"]
        else "STOP"
    )

    proof: dict[str, object] = {
        "schema": "saea-test-sample-partition-proof-v1",
        "study": "speech-aware-evidence-acquisition",
        "authority": AUTHORITY,
        "generator": GENERATOR,
        "parent": {
            "roster_id": PARENT_ROSTER_ID,
            "relpath": PARENT_RELPATH,
            "receipt_file_sha256": parent_file_sha256,
            "split_identity_hash": PARENT_SPLIT_IDENTITY_HASH,
            "carrier_split_identity_hash": PARENT_CARRIER_IDENTITY_HASH,
        },
        "rosters": {
            sample_roster_id: {
                "relpath": sample_relpath,
                "split_identity_hash": sample_hash,
                "carrier_split_identity_hash": sample_bare_hash,
                "recordings": n_sample,
                "utterances": len(sample_utt),
            },
            closure_roster_id: {
                "relpath": closure_relpath,
                "split_identity_hash": closure_hash,
                "carrier_split_identity_hash": closure_bare_hash,
                "recordings": n_closure,
                "utterances": len(closure_utt),
            },
        },
        "partition_proof": partition,
        "stratification": {**accounting, "seed": SEED, "quotas_utterances": quotas},
        "per_intent": per_intent,
        "intents_absent_from_sample": intents_absent_from_sample,
        "speaker_prompt_author_overlap": overlap,
        "text_overlap_with_train": text_block,
        "passes": {
            "1_by_recording_id": {"sources_checked": len(checked)},
            "2_by_utterance_id_and_prompt_number": {"sources_checked": len(checked)},
            "3_by_text": {"status": "RUN, digest only, against the TRAIN construction pool", "see": "text_overlap_with_train"},
            "4_exposure_closure_new_rosters": closure_new,
            "4_exposure_closure_parent": closure_parent,
        },
        "sources": checked,
        "violations": violations,
        "verdict": verdict,
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    }
    proof["proof_sha256"] = canonical_sha256(proof)
    proof_bytes = (json.dumps(proof, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    proof_sha256 = hashlib.sha256(proof_bytes).hexdigest()
    table_bytes = (json.dumps(table, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    table_sha256 = hashlib.sha256(table_bytes).hexdigest()
    if verdict != "CLEAN":
        _print({"verdict": verdict, "violations": violations[:5]})
        raise SystemExit("the partition is NOT clean; nothing is frozen")

    # ---- the two receipts --------------------------------------------------------
    def receipt(
        *,
        roster_id: str,
        split_name: str,
        ids: Sequence[str],
        items: Sequence[Mapping[str, object]],
        identity_hash: str,
        bare_hash: str,
        sibling_id: str,
        sibling_relpath: str,
        sibling_hash: str,
        sibling_n: int,
        own_quotas: Mapping[str, int],
        design: str,
        purpose: str,
    ) -> dict[str, object]:
        r_by_intent = Counter(intent_by_utterance[utterance_id_of(s)] for s in ids)
        u_by_intent = Counter(intent_by_utterance[u] for u in {utterance_id_of(s) for s in ids})
        headset = sum(1 for item in items if item["headset"])
        document = {
            "schema": "saea-roster-receipt-v1",
            "roster_id": roster_id,
            "carrier_lock_key": CARRIER,
            "split_role": SPLIT_ROLE,
            "roster_role": EVALUATION_ROSTER_ROLE,
            "seed": SEED,
            "per_stratum": dict(sorted(own_quotas.items())),
            "per_stratum_unit": "test PROMPTS (utterances) per gold intent; items are the recordings of those prompts",
            "strata_counts": {intent: int(r_by_intent.get(intent, 0)) for intent in capacity},
            "strata_utterance_counts": {intent: int(u_by_intent.get(intent, 0)) for intent in capacity},
            "stratum_withheld_per_item": True,
            "items": list(items),
            "item_fields": ["audio_seconds", "headset", "sample_id", "utterance_id"],
            "excluded_count": EXPECTED_RECORDINGS - len(ids),
            "excluded_count_meaning": "the parent's recordings that belong to the sibling roster",
            "split_identity_hash": identity_hash,
            "split_identity_hash_basis": (
                "sha256 over the LF-joined sorted carrier-prefixed 'slurp/<sample_id>' ids -- "
                "the core.roster / data.splits convention an ExecutionPlan declares"
            ),
            "carrier_split_identity_hash": bare_hash,
            "carrier_split_identity_hash_basis": (
                "sha256 over the LF-joined sorted BARE sample ids -- the "
                "rails.knowledge_build.freeze_slurp_split_identity convention"
            ),
            "split_name": split_name,
            "authority": AUTHORITY,
            "generator": GENERATOR,
            "design_note": DESIGN_NOTE_RELPATH,
            "status": "FROZEN; MODEL-FREE, ZERO CONTACTS; TEST GOLD READ OFFLINE FOR STRATIFICATION",
            "design": design,
            "purpose": purpose,
            "selection_rule": (
                "A partition of SLURP-TEST-FULL-13078-V1 by test PROMPT. Prompts are stratified "
                "by gold intent (scenario_action, read offline from the governed test.jsonl); "
                f"per intent the sample takes a floor of {SAMPLE_FLOOR} prompts where the intent has "
                f"at least {SAMPLE_FLOOR + CLOSURE_FLOOR}, an even split (closure taking the larger "
                "half) where it has 2 to "
                f"{SAMPLE_FLOOR + CLOSURE_FLOOR - 1}, and nothing where it has exactly 1 (that prompt "
                "goes to the closure roster); the remainder is apportioned by "
                "core.roster.mixture_quotas against test's natural prompt mixture, capped by "
                "capacity minus both floors. core.roster.freeze_roster draws the prompts (seed "
                f"{SEED}, one shared rng advanced across intents in ascending name order); EVERY "
                "recording of a selected prompt goes to the sample and every recording of every "
                "other prompt goes to the closure roster. Both receipts are written by one "
                "invocation and together they are exactly the parent."
            ),
            "seed_note": (
                f"seed {SEED} drives the prompt draw inside each intent; the floors and the "
                "mixture apportionment are deterministic arithmetic over the committed capacities"
            ),
            "strata_definition": (
                "GOLD INTENT scenario_action of the prompt, read offline for stratification "
                "(owner decision 141 item 5) and published as per-intent AGGREGATES only; no "
                "item carries its stratum (stratum_withheld_per_item)"
            ),
            "stratification": {**accounting, "target_recordings": args.target_recordings, "target_prompts": total_u},
            "per_intent": per_intent,
            "intents_present": len(capacity),
            "intents_absent_from_sample": intents_absent_from_sample,
            "weightings": {
                "natural_mixture": {
                    "basis": "full-test per-intent shares (recordings and prompts); the natural-mixture number is the POST-STRATIFIED sum of per-intent accuracies weighted by these shares, because the floors over-represent small intents and the raw roster mean is not the natural-mixture number",
                    "weights_recordings": weights_recordings,
                    "weights_utterances": weights_utterances,
                },
                "equal_stratum": {"basis": f"1/{len(capacity)} per scored intent present in the test split"},
            },
            "channel_counts": {"headset": headset, "far_field": len(items) - headset},
            "counts": {
                "recordings": len(ids),
                "distinct_utterances": len({utterance_id_of(s) for s in ids}),
                "audio_seconds_total": round(sum(float(item["audio_seconds"]) for item in items), 9),
            },
            "audio_seconds_total": round(sum(float(item["audio_seconds"]) for item in items), 9),
            "audio_seconds_source": "copied from the parent receipt; no audio file was opened by this build",
            "derived_from": {
                "source_roster": {
                    "repo_relpath": PARENT_RELPATH,
                    "roster_id": PARENT_ROSTER_ID,
                    "sha256": parent_file_sha256,
                    "split_identity_hash": PARENT_SPLIT_IDENTITY_HASH,
                    "carrier_split_identity_hash": PARENT_CARRIER_IDENTITY_HASH,
                    "recordings": EXPECTED_RECORDINGS,
                    "utterances": EXPECTED_UTTERANCES,
                },
                "sibling_roster": {
                    "roster_id": sibling_id,
                    "repo_relpath": sibling_relpath,
                    "split_identity_hash": sibling_hash,
                    "recordings": sibling_n,
                },
                "partition_proof": partition,
                "stratum_source": {
                    "relpath": governed["metadata_relpath"],
                    "sha256": governed["sha256"],
                    "lock_revision": governed["lock_revision"],
                    "fields_read": ["slurp_id", "scenario", "action", "recordings[].file"],
                    "fields_read_digest_only": ["sentence"],
                    "fields_never_read": ["tokens", "entities", "sentence_annotation", "intent", "recordings[].wer", "recordings[].ent_wer", "recordings[].status"],
                },
                "selection": "one seeded prompt draw; whole-prompt expansion; the sibling is the set difference",
            },
            "governed_metadata": governed,
            "split_identity_receipt": {
                "relpath": SPLIT_IDENTITY_RELPATH,
                "file_sha256": sha256_file(REPO_ROOT / SPLIT_IDENTITY_RELPATH),
                "test_ids": int(frozen_block["count"]),
                "test_identity_hash": str(frozen_block["identity_hash"]),
            },
            "gold_access": {
                "test_gold_opened": True,
                "opened_for": "stratification of the prompt draw (owner decision 141 item 5) and the TRAIN text-overlap count",
                "where": "offline, once, inside this sealed model-free freeze process; never at runtime",
                "published_as": "per-intent aggregate counts only; no label beside a sample id",
                "runtime_surfaces_written": [],
                "audio_opened": False,
            },
            "target_gold_opened_before_receipt": True,
            "target_gold_opened_before_receipt_note": (
                "TRUE, and deliberately: this receipt is a stratified draw of a gold field, "
                "which decision 141 item 5 permits offline and requires to be recorded as "
                "exactly that. No score, transcript, answer or model output of any test row "
                "exists; the answer surface of both rosters is unread."
            ),
            "speaker_prompt_author_overlap": overlap,
            "text_overlap_with_train": text_block,
            "size_table": {"relpath": f"{CHECK_DIR}/{SIZE_TABLE_NAME}", "sha256": table_sha256},
            "disjointness": {
                "relpath": f"{CHECK_DIR}/{DISJOINTNESS_NAME}",
                "sha256": proof_sha256,
                "verdict": verdict,
                "sources_checked": len(checked),
            },
            "allowance": (
                "No owner allowance names this roster. contracts.plan.require_owner_split_allowance "
                "binds ONE split identity hash per receipt under docs/receipts/owner/, so a "
                "contact with this roster needs its own authorised saea-owner-split-allowance-v1 "
                "receipt naming THIS split_identity_hash and its permitted run ids; and "
                "contracts.gate_exposure._require_final_report_disjointness, as built, refuses "
                "any final-report roster that shares an id with another committed roster of the "
                "carrier, which a partition of the frozen parent does by construction. What "
                "would have to change is stated in the design note; nothing was changed here."
            ),
            "one_read_rule": (
                "The closure roster is read ONCE as the final read. The sample serves MILESTONE "
                "checks only (decision 141 item 4), never per-round iteration; every milestone "
                "is its own owner-named read run id with one attempt, and a roster compared "
                "against repeatedly stops being an unbiased final read of itself, which is why "
                "its complement -- not the full split -- is the closure roster."
            ),
            "media_identity": (
                "No runtime view exists for this roster. One would be the label-free "
                "saea-speech-native-runtime-view-v1 restriction of "
                "configs/dataset/slurp-speech-native-test-full.json to these ids, built only "
                "under the roster's own allowance; this receipt is the identity statement."
            ),
            "offline_guard": {
                "outbound_connection_attempts": attempts.count,
                "attempted_targets": list(attempts.targets),
            },
        }
        verify_roster(document)
        if document["split_identity_hash"] != identity_hash:
            raise SystemExit("identity mismatch")
        return document

    closure_quotas = {intent: capacity[intent] - quotas[intent] for intent in capacity}
    sample_receipt = receipt(
        roster_id=sample_roster_id,
        split_name="TEST-SAMPLE",
        ids=sample_ids,
        items=sample_items,
        identity_hash=sample_hash,
        bare_hash=sample_bare_hash,
        sibling_id=closure_roster_id,
        sibling_relpath=closure_relpath,
        sibling_hash=closure_hash,
        sibling_n=n_closure,
        own_quotas=quotas,
        design=(
            f"The coverage-guaranteed SAMPLE of the official SLURP test split permitted by owner "
            f"decision 141: {len(sample_utt)} test prompts drawn once, stratified by gold intent "
            f"with a floor per intent, expanded to all {n_sample} of their recordings. Its complement "
            f"{closure_roster_id} is the closure roster for the final read, sealed at the same moment."
        ),
        purpose="MILESTONE checks of the programme's absolute 95 per cent intent target on test-distribution rows, behind the final-report owner allowance; never per-round iteration",
    )
    closure_receipt = receipt(
        roster_id=closure_roster_id,
        split_name="TEST-CLOSURE",
        ids=closure_ids,
        items=closure_items,
        identity_hash=closure_hash,
        bare_hash=closure_bare_hash,
        sibling_id=sample_roster_id,
        sibling_relpath=sample_relpath,
        sibling_hash=sample_hash,
        sibling_n=n_sample,
        own_quotas=closure_quotas,
        design=(
            f"The CLOSURE roster: every test prompt NOT in {sample_roster_id}, with all "
            f"{n_closure} of their recordings ({len(closure_utt)} prompts). Sealed at the same "
            "moment as the sample (owner decision 141 item 1) as the roster of the ONE final read; "
            "it supersedes SLURP-TEST-FULL-13078-V1 as the final-read roster to the extent of "
            "decision 141 and no further."
        ),
        purpose="the ONE final read of decision 99 as amended by decision 141: read once, never compared against before that read",
    )

    summary = {
        "sample": {
            "roster_id": sample_roster_id,
            "relpath": sample_relpath,
            "split_identity_hash": sample_hash,
            "carrier_split_identity_hash": sample_bare_hash,
            "recordings": n_sample,
            "utterances": len(sample_utt),
            "receipt_sha256": hashlib.sha256(canonical_receipt_bytes(sample_receipt)).hexdigest(),
            "channel_counts": sample_receipt["channel_counts"],
            "audio_seconds_total": sample_receipt["audio_seconds_total"],
        },
        "closure": {
            "roster_id": closure_roster_id,
            "relpath": closure_relpath,
            "split_identity_hash": closure_hash,
            "carrier_split_identity_hash": closure_bare_hash,
            "recordings": n_closure,
            "utterances": len(closure_utt),
            "receipt_sha256": hashlib.sha256(canonical_receipt_bytes(closure_receipt)).hexdigest(),
            "channel_counts": closure_receipt["channel_counts"],
            "audio_seconds_total": closure_receipt["audio_seconds_total"],
        },
        "partition_proof": partition,
        "stratification": {**accounting, "target_recordings": args.target_recordings, "target_prompts": total_u},
        "intents_absent_from_sample": intents_absent_from_sample,
        "speaker_prompt_author_overlap": {k: v for k, v in overlap.items() if k != "statement"},
        "text_overlap_with_train": {"sample": sample_profile, "closure": closure_profile, "sample_closure_shared_sentence_digests": text_block["sample_closure_shared_sentence_digests"], "train_pool": text_block["train_construction_pool"]},
        "disjointness": {"verdict": verdict, "sources_checked": len(checked), "sha256": proof_sha256},
        "exposure_closure": {"new_rosters": closure_new["verdict"], "parent": closure_parent["verdict"], "parent_matching_rows": len(closure_parent["matching_rows"])},
        "census": census,
        "size_table_rows": table["rows"],
        "offline_guard": proof["offline_guard"],
        "written": bool(args.write),
    }
    _print(summary)

    if args.write:
        check_dir = REPO_ROOT / CHECK_DIR
        check_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in ((DISJOINTNESS_NAME, proof_bytes), (SIZE_TABLE_NAME, table_bytes)):
            target = check_dir / name
            if target.exists():
                raise SystemExit(f"refusing to overwrite {target}")
            with target.open("wb") as handle:
                handle.write(payload)
        write_roster(sample_receipt, REPO_ROOT / sample_relpath)
        write_roster(closure_receipt, REPO_ROOT / closure_relpath)
        print(f"wrote {sample_relpath}")
        print(f"wrote {closure_relpath}")
        print(f"wrote {CHECK_DIR}/{DISJOINTNESS_NAME}")
        print(f"wrote {CHECK_DIR}/{SIZE_TABLE_NAME}")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
