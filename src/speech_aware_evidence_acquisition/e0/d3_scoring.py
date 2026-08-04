"""E0 D3: scoring-stack freeze — source hashes + executed golden vectors.

The frozen surface is the :mod:`speech_aware_evidence_acquisition.scoring` package:
normalization v1, deterministic WER alignment, entity multiset PRF, QA EM/F1 and
correct-to-wrong / wrong-to-correct transition accounting. The artifact records the
SHA-256 of every scoring source file and the executed results of a synthetic golden
vector suite (no carrier text is used). Any observed/expected mismatch fails the
generator closed; any later source edit breaks the receipt hash and re-closes the
model gate.
"""

from __future__ import annotations

from pathlib import Path

from ..contracts import SCORING_PACKAGE_RELPATH
from ..scoring import (
    SCORING_STACK_VERSION,
    align,
    normalize_text_v1,
    qa_exact_match,
    qa_token_f1,
    score_entities,
    token_transitions,
    tokens_v1,
)
from .artifacts import REPO_ROOT, ArtifactError, sha256_file, today


def scoring_sources(repo_root: Path) -> list[str]:
    """Every ``*.py`` in the scoring package, enumerated recursively — a module can
    never hide from the freeze in a subdirectory, and a non-source file fails
    closed here exactly as it does at the gate."""

    scoring_dir = repo_root / SCORING_PACKAGE_RELPATH
    if not scoring_dir.is_dir():
        raise ArtifactError(f"scoring package directory missing: {scoring_dir}")
    sources: list[str] = []
    for path in sorted(scoring_dir.rglob("*")):
        rel_parts = path.relative_to(scoring_dir).parts
        # Symlink refusal precedes the __pycache__ skip (a symlinked directory
        # named __pycache__ must not slip through by name) — mirrors the gate.
        if path.is_dir() and path.is_symlink():
            raise ArtifactError(
                f"scoring package contains a symlinked directory "
                f"{'/'.join(rel_parts)!r}; its contents would be importable yet "
                "invisible to the freeze (gate refuses the same)"
            )
        if "__pycache__" in rel_parts:
            continue
        if path.is_dir():
            continue
        if path.is_file() and path.name.endswith(".py"):
            sources.append(f"{SCORING_PACKAGE_RELPATH}/{'/'.join(rel_parts)}")
            continue
        raise ArtifactError(
            f"scoring package contains a non-source entry {'/'.join(rel_parts)!r}; "
            "only Python sources may live there (gate enforces the same rule)"
        )
    if not sources:
        raise ArtifactError(f"no scoring sources found under {scoring_dir}")
    return sources


def _round(value: float) -> float:
    return round(value, 12)


def _golden_vectors() -> list[dict[str, object]]:
    """Synthetic vectors executed at generation time; observed must equal expected."""

    vectors: list[dict[str, object]] = []

    text = "The CFO, Mr. O’Brien — said: ‘EBITDA up 12%’"
    vectors.append(
        {
            "case": "normalize/entity-rich",
            "input": text,
            "expected": "the cfo mr o'brien said ebitda up 12",
            "observed": normalize_text_v1(text),
        }
    )
    vectors.append(
        {
            "case": "normalize/tokens",
            "input": "Semi-annual  results…",
            "expected": ["semi", "annual", "results"],
            "observed": tokens_v1("Semi-annual  results…"),
        }
    )

    wer_result = align(["the", "quick", "brown", "fox"], ["the", "quik", "brown", "fox", "jumps"])
    vectors.append(
        {
            "case": "wer/sub+ins",
            "expected": {
                "hits": 3,
                "substitutions": 1,
                "deletions": 0,
                "insertions": 1,
                "wer": _round(0.5),
                "ref_hit_mask": [True, False, True, True],
            },
            "observed": {
                "hits": wer_result.hits,
                "substitutions": wer_result.substitutions,
                "deletions": wer_result.deletions,
                "insertions": wer_result.insertions,
                "wer": _round(wer_result.wer),
                "ref_hit_mask": list(wer_result.ref_hit_mask),
            },
        }
    )
    empty = align([], [])
    vectors.append(
        {
            "case": "wer/empty-empty",
            "expected": {"errors": 0, "wer": 0.0},
            "observed": {"errors": empty.errors, "wer": empty.wer},
        }
    )

    entity = score_entities(
        ["Q2 revenue", "O’Brien", "O’Brien"], ["o'brien", "q2 revenue", "acme"]
    )
    vectors.append(
        {
            "case": "entity/multiset",
            "expected": {
                "true_positives": 2,
                "precision": _round(2 / 3),
                "recall": _round(2 / 3),
                "f1": _round(2 / 3),
            },
            "observed": {
                "true_positives": entity.true_positives,
                "precision": _round(entity.precision),
                "recall": _round(entity.recall),
                "f1": _round(entity.f1),
            },
        }
    )

    vectors.append(
        {
            "case": "qa/exact-match",
            "expected": True,
            "observed": qa_exact_match("The CFO.", ["CFO", "the cfo"]),
        }
    )
    vectors.append(
        {
            "case": "qa/token-f1",
            "expected": _round(6 / 7),
            "observed": _round(qa_token_f1("revenue rose 12 percent", ["revenue rose 12"])),
        }
    )

    transitions = token_transitions(
        ["a", "b", "c", "d"], ["a", "x", "c", "d"], ["a", "b", "c", "x"]
    )
    vectors.append(
        {
            "case": "transitions/token-level",
            "expected": {
                "correct_to_correct": 2,
                "correct_to_wrong": 1,
                "wrong_to_correct": 1,
                "wrong_to_wrong": 0,
            },
            "observed": {
                "correct_to_correct": transitions.correct_to_correct,
                "correct_to_wrong": transitions.correct_to_wrong,
                "wrong_to_correct": transitions.wrong_to_correct,
                "wrong_to_wrong": transitions.wrong_to_wrong,
            },
        }
    )
    return vectors


def build_d3(repo_root: Path = REPO_ROOT) -> dict[str, object]:
    sources: dict[str, str] = {}
    for relpath in scoring_sources(repo_root):
        path = repo_root / relpath
        if not path.is_file():
            raise ArtifactError(f"frozen scoring source missing: {relpath}")
        sources[relpath] = sha256_file(path)

    vectors = _golden_vectors()
    for vector in vectors:
        if vector["observed"] != vector["expected"]:
            raise ArtifactError(
                f"golden vector {vector['case']!r} mismatch: "
                f"expected {vector['expected']!r}, observed {vector['observed']!r}"
            )

    return {
        "artifact_kind": "saea-e0-d3-scoring-v1",
        "generated": today(),
        "scoring_stack_version": SCORING_STACK_VERSION,
        "frozen_sources_sha256": sources,
        "semantics": {
            "normalization": (
                "NFKC + casefold; apostrophe variants -> ASCII; dashes and "
                "non-alphanumerics -> space; only intra-word apostrophes survive; "
                "whitespace collapsed; no number expansion (v1)"
            ),
            "wer": (
                "unit-cost Levenshtein over normalized tokens; deterministic backtrace "
                "preference match/substitution > deletion > insertion; per-reference-"
                "token hit mask is the transition substrate"
            ),
            "entity": "multiset precision/recall/F1 over normalized entity strings",
            "qa": "SQuAD-style best-over-answers exact match and token F1",
            "transitions": (
                "correct-to-wrong / wrong-to-correct at token level (ASR, via hit "
                "masks) and item level (QA/entity, via boolean flags)"
            ),
            "known_limits_v1": (
                "casefold expands Turkish dotted I (U+0130) into 'i'+combining dot, "
                "which rule 5 then splits ('İstanbul' -> 'i stanbul'), and strips "
                "combining marks from precomposed Greek; both apply symmetrically to "
                "reference and hypothesis. Entity PRF is corpus-level multiset "
                "counting: an item with no expected and no predicted entities "
                "contributes nothing (f1 of an all-empty comparison is 0.0, never "
                "used per-item). WER alignment is O(len(ref)*len(hyp)) and is frozen "
                "for per-segment scoring, not whole-call alignment."
            ),
        },
        "golden_vectors": {
            "executed": len(vectors),
            "all_matched": True,
            "vectors": vectors,
        },
        "freeze_rule": (
            "Machine-enforced: contracts.FrozenCoreGate re-hashes every source listed "
            "in frozen_sources_sha256 against the live tree at each model-touch "
            "attempt and refuses any scoring-package module this mapping does not "
            "name. Editing a frozen source therefore re-closes the gate at the next "
            "touch; a new scoring version requires regenerating this artifact and "
            "e0-closure.json, never an in-place edit."
        ),
    }
