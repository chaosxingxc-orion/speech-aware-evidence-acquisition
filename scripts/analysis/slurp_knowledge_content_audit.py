#!/usr/bin/env python3
"""slurp_knowledge_content_audit.py -- the SLURP knowledge CONTENT audit (owner decision 163,
analysis track: "where the raw knowledge falls short, and what capability must be added").

Read id ``SAEA-SLURP-MF-KNOWLEDGE-CONTENT-AUDIT-V1``, recipe ``slurp-knowledge-content-audit-v1``.

What it audits: the three SLURP knowledge stores the current best arm (cell AGREE,
``SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1``, TRAIN Fold A 1,080 rows) actually consumed --
``intent-boundaries-v1`` (60 written boundary cards plus their encoded keys, and the centroid key
file KPROBE / COMP-1 pin beside them), the ``train-exemplars`` pool
``size-pool-annotated-exemplars`` (9,354 utterances with a frozen ``task_target``; its
R01-excluded sibling of 8,554 is counted beside it), and ``slot-contracts-v2`` (54 slot cards) --
against the AGREE arm's REMAINING errors, read per row from its sealed outputs, its sealed official
per-sample score and its sealed per-row consumption records.

Model-free. Zero model, server, tokenizer, encoder, embedder, scorer, ASR, network, GPU and paid-API
contacts. Every similarity is arithmetic (float64 dot products of unit rows) over sha256-verified
vector files the flights pinned; the boundary ranking is validated against the in-chain A/A arm's
sealed delivered set before a number is taken from it. Gold is read OFFLINE from the governed
``train.jsonl`` (and only the scenario/action fields of ``devel.jsonl`` for label coverage) through
this repository's own record helpers; ``test.jsonl`` is never opened.

Nothing textual is persisted: no utterance text, transcript, gold filler, predicted filler,
delivered answer or knowledge body leaves this process. Every value written is an intent id, a
slot TYPE name, a count, a rate, a cosine, a boolean or a hash. Fillers and sentences enter set
arithmetic in memory and leave it as integers.

Byte-reproducible: every container is sorted before it is consumed, floats are rounded, there is
no sampling, and the payload carries no timestamp -- the generation stamp is written to a separate
``run-stamp-v1.json`` so two runs produce a byte-identical ``audit-v1.json``.

A DIAGNOSTIC, never a gate: it admits no mechanism, releases or rebuilds no store, registers no
cell and authorises no flight. TRAIN Fold A numbers are development numbers (owner decisions 28
and 86), never a test claim. Every "ceiling" is an ORACLE -- the gain of a perfect repair of the
named rows or items -- and every "expected" figure multiplies a ceiling by a MEASURED conversion
rate (CONV 32/70, KPROBE 24/55) and is labelled as such.
"""

from __future__ import annotations

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "4")  # the brief's <= 4 worker cap, before numpy loads

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
from collections import Counter, defaultdict  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

_DRIVER = Path(__file__).resolve()
REPO_ROOT = _DRIVER.parents[2]
for _p in (str(REPO_ROOT / "src"), str(_DRIVER.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from speech_aware_evidence_acquisition.analysis.null_calibration import pooled_f1  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _SPLIT_FILES,
    _entity_filler,
    _entity_type,
    _governed_roots,
    _tokens_by_id,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_segment_vectors,
    load_sealed_vectors,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    SlotEntity,
    parse_slu_response,
)

# The bad-case bank's filler-shape helpers and its official-matcher decomposition, imported
# byte-unchanged so the per-type loss here is the bank's own decomposition.
from slurp_plan_bad_case_bank import (  # noqa: E402
    _edit_distance,
    _fold_punct,
    filler_shape,
    pair_shape,
    row_entity_view,
)

READ_ID = "SAEA-SLURP-MF-KNOWLEDGE-CONTENT-AUDIT-V1"
RECIPE = "slurp-knowledge-content-audit-v1"
SCHEMA = "saea-slurp-knowledge-content-audit-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ANALYSIS_DIR = "analysis/SAEA-SLURP-KNOWLEDGE-CONTENT-AUDIT-V1"

IB_DIM, POOL_DIM = "intent-boundary", "content"
FLOWN_BOUNDARY_WIDTH = 8
ROWS_EXPECTED = 1080
FOLD_A_SPLIT_IDENTITY = "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6"
SCORER = "slurp-slu-official-train"
CHARS_PER_TOKEN = 5.13  # measured, docs/results/2026-09-19-slurp-m1-exemplar-compression-analysis-v1.md

PINS = {
    "ib_snapshot": ("knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json",
                    "5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe"),
    "ib_written_keys": ("prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl",
                        "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"),
    "ib_centroid_keys": ("prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl",
                         "16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532"),
    "sc_snapshot": ("knowledge/slurp/semantic/slot-contracts-v2/snapshot.json",
                    "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec"),
    "pool": ("knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json",
             "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9"),
    "pool_minus_r01": ("knowledge/slurp/saea-kb-distmodel-v1/"
                       "size-pool-annotated-exemplars-minus-r01/snapshot.json",
                       "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63"),
    "pool_keys": ("vectors/slurp-kus3/facet-vectors.jsonl",
                  "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"),
    "fold_a_queries": ("vectors/slurp-intent-boundaries-train-fold-a-1080-v1/"
                       "query-vectors-speech-segments.jsonl",
                       "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b"),
    "train_gold": ("datasets/slurp/metadata/train.jsonl",
                   "4a05a3de6c7f028aff298c4a90196e6a3fecd1938d96fb1c125d6fd10d5e301e"),
    "devel_gold": ("datasets/slurp/metadata/devel.jsonl",
                   "00d346b183ecc2d160853cd3dc20e8ccd207d9e1809cf6e2c05182076bd0ecc9"),
}

ARM = {
    "run_id": "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
    "attempt": "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1",
}
AA = {
    "run_id": "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1",
    "attempt": "attempt-slurp-native-stage3-agree-aa-fold-a-generation-v1",
}
CONVERSION_READS = {
    "conv_agree": "analysis/SAEA-SLURP-STAGE3-CONV-FOLD-A-70-CONDITIONAL-RATE-V1/read-v1.json",
    "kprobe_centroid": "analysis/SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-CONDITIONAL-RATE-V1/read-v1.json",
}

IB_SECTIONS = ("Activation boundary", "Confusable exclusions", "Uncertainty behavior",
               "Limitations")
SC_SECTIONS = ("Intent bindings and semantic roles", "Extraction cues", "Admissible formats",
               "Missing behavior", "Ambiguity behavior", "Limitations")
FORMAT_FLAGS = {
    "mentions_digits_or_numbers": re.compile(r"\b(digit|digits|numeral|numerals|numeric|number|numbers)\b"),
    "mentions_spoken_or_words": re.compile(r"\b(spoken|spell|spelled|word|words|verbatim)\b"),
    "mentions_case": re.compile(r"\b(lowercase|lower case|uppercase|capitali[sz]\w*|casing)\b"),
    "mentions_meridiem": re.compile(r"(\bam\b|\bpm\b|a\.m\.|p\.m\.|meridiem|o'clock)"),
    "mentions_ordinal": re.compile(r"\b(ordinal|ordinals|first|second|third|\d+(st|nd|rd|th))\b"),
    "mentions_relative": re.compile(r"\b(relative|today|tomorrow|tonight|next|this|weekend|deictic)\b"),
    "mentions_normalisation_refusal": re.compile(r"\b(do not normali[sz]e|not normali[sz]ed|keep the spoken|as spoken|as said)\b"),
}
LOO_CLOSED, LOO_SEMI = 0.90, 0.60  # leave-one-utterance-out value coverage thresholds
NN_K = 10
ROUND = 6


class AuditError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# small utilities


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def rnd(value: float, places: int = ROUND) -> float:
    return round(float(value), places)


def pct(num: float, den: float) -> float:
    return rnd(100.0 * num / den, 4) if den else 0.0


def word_set(text: str) -> frozenset:
    out, run = set(), []
    for char in str(text).lower():
        if char.isalnum():
            run.append(char)
        elif run:
            out.add("".join(run))
            run = []
    if run:
        out.add("".join(run))
    return frozenset(out)


def jaccard(a: frozenset, b: frozenset) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def unit_rows(matrix) -> np.ndarray:
    work = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(work, axis=1, keepdims=True)
    return work / np.where(norms > 0.0, norms, 1.0)


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def utterance_of(sample_id: str) -> str:
    parts = sample_id.split(":")
    if len(parts) < 3 or not parts[2].isdigit():
        raise AuditError(f"sample id {sample_id!r} carries no utterance field")
    return str(int(parts[2]))


def token_key(surface: str) -> str:
    return "".join(ch for ch in surface.lower() if ch.isalnum() or ch == "'")


def sections(content: str, names) -> dict:
    """Split a card body into its named sections (header line ``Name:`` optionally followed by
    inline text).  Returns ``{name: text}``; text never leaves this process."""
    out = {name: [] for name in names}
    current = None
    for line in content.splitlines():
        matched = None
        for name in names:
            if line.startswith(name + ":"):
                matched = name
                break
        if matched is not None:
            current = matched
            rest = line[len(matched) + 1:].strip()
            if rest:
                out[current].append(rest)
            continue
        if current is not None:
            out[current].append(line)
    return {name: "\n".join(lines) for name, lines in out.items()}


def bullet_ids(text: str) -> list[str]:
    """Leading ids of ``- id: ...`` bullets (intent ids in bindings / exclusions)."""
    ids = []
    for line in text.splitlines():
        match = re.match(r"\s*-\s*([a-z_]+):", line)
        if match:
            ids.append(match.group(1))
    return ids


def gini(values) -> float:
    xs = sorted(float(v) for v in values)
    n = len(xs)
    if n == 0 or sum(xs) == 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(xs))
    return (2.0 * cum) / (n * sum(xs)) - (n + 1.0) / n


def pinned(root: Path, key: str) -> Path:
    relpath, expected = PINS[key]
    path = root / relpath
    actual = digest(path)
    if actual != expected:
        raise AuditError(f"{relpath}: sha256 {actual} is not the pinned {expected}")
    return path


# ---------------------------------------------------------------------------
# gold (offline only)


def load_gold(lock: dict, root: Path, split: str, *, labels_only: bool = False) -> dict:
    metadata_dir = _governed_roots(lock, root)[2]
    path = metadata_dir / _SPLIT_FILES[split]
    key = "train_gold" if split == "train" else "devel_gold"
    if digest(path) != PINS[key][1]:
        raise AuditError(f"governed {split} metadata does not hash to the pin")
    utterances, sample_to_utt = {}, {}
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            slurp_id = raw["slurp_id"]
            intent = f"{raw['scenario']}_{raw['action']}"
            entry = {"intent": intent, "scenario": raw["scenario"]}
            if not labels_only:
                context = f"SLURP {split}.jsonl line {line_no}"
                tokens = _tokens_by_id(raw.get("tokens"), context)
                entry["entities"] = tuple(
                    SlotEntity(type=_entity_type(entity, context),
                               filler=_entity_filler(tokens, entity.get("span"), context))
                    for entity in raw["entities"])
                entry["token_set"] = frozenset(
                    k for k in (token_key(t) for t in tokens.values()) if k)
                for recording in raw["recordings"]:
                    name = recording["file"]
                    sample_to_utt[f"slurp:{split}:{slurp_id:06d}:{name[:-len('.flac')]}"] = str(slurp_id)
            utterances[str(slurp_id)] = entry
    return {"path": str(path), "sha256": digest(path), "utterances": utterances,
            "sample_to_utt": sample_to_utt}


# ---------------------------------------------------------------------------
# stores


def load_boundary_store(root: Path) -> dict:
    path = root / PINS["ib_snapshot"][0]  # pinned by its CONTENT hash, checked below
    snap = KnowledgeSnapshot.from_frozen_json(json.loads(path.read_text(encoding="utf-8")))
    if snap.content_hash() != PINS["ib_snapshot"][1]:
        raise AuditError("intent-boundaries content hash is not the flown pin")
    cards = {}
    for value in snap.values:
        intent = value.value_id.split("intent-boundary:", 1)[-1]
        parts = sections(value.content, IB_SECTIONS)
        cards[intent] = {
            "chars": len(value.content),
            "section_chars": {name: len(parts[name]) for name in IB_SECTIONS},
            "activation_items": sum(1 for ln in parts["Activation boundary"].splitlines()
                                    if ln.strip().startswith("-")),
            "excludes": sorted(set(bullet_ids(parts["Confusable exclusions"]))),
            "body_words": word_set(value.content),
            "discriminative_words": word_set(parts["Activation boundary"] + "\n"
                                             + parts["Confusable exclusions"]),
            "uncertainty_sha": hashlib.sha256(parts["Uncertainty behavior"].encode()).hexdigest(),
            "limitations_sha": hashlib.sha256(parts["Limitations"].encode()).hexdigest(),
        }
    reps = {}
    for facet in snap.facets:
        reps[facet.facet_id.split("intent-boundary:", 1)[-1]] = word_set(facet.representation)
    if set(cards) != set(reps) or len(cards) != 60:
        raise AuditError("intent-boundaries is not the 60-way 1:1 store")
    written = load_sealed_vectors(pinned(root, "ib_written_keys"),
                                  expected_sha256=PINS["ib_written_keys"][1], dimensions=(IB_DIM,))
    centroid = load_sealed_vectors(pinned(root, "ib_centroid_keys"),
                                   expected_sha256=PINS["ib_centroid_keys"][1], dimensions=(IB_DIM,))
    order = sorted(cards)
    fid = {i: "intent-boundary:" + i for i in order}
    if set(written) != set(fid.values()) or set(centroid) != set(fid.values()):
        raise AuditError("boundary key files do not cover the 60 facets exactly")
    return {
        "cards": cards, "reps": reps, "order": order,
        "written": unit_rows([written[fid[i]][IB_DIM] for i in order]),
        "centroid": unit_rows([centroid[fid[i]][IB_DIM] for i in order]),
    }


def load_slot_store(root: Path) -> dict:
    path = root / PINS["sc_snapshot"][0]  # pinned by its CONTENT hash, checked below
    snap = KnowledgeSnapshot.from_frozen_json(json.loads(path.read_text(encoding="utf-8")))
    if snap.content_hash() != PINS["sc_snapshot"][1]:
        raise AuditError("slot-contracts content hash is not the flown pin")
    cards = {}
    for value in snap.values:
        slot_type = value.value_id.split("slot-contract:", 1)[-1]
        parts = sections(value.content, SC_SECTIONS)
        lowered = value.content.lower()
        fmt_text = (parts["Admissible formats"] + "\n" + parts["Extraction cues"]).lower()
        cards[slot_type] = {
            "chars": len(value.content),
            "section_chars": {name: len(parts[name]) for name in SC_SECTIONS},
            "bound_intents": sorted(set(bullet_ids(parts["Intent bindings and semantic roles"]))),
            "cue_lines": sum(1 for ln in parts["Extraction cues"].splitlines() if ln.strip().startswith("-")),
            "format_lines": sum(1 for ln in parts["Admissible formats"].splitlines() if ln.strip().startswith("-")),
            "format_flags": {name: bool(rx.search(fmt_text)) for name, rx in sorted(FORMAT_FLAGS.items())},
            "missing_sha": hashlib.sha256(parts["Missing behavior"].encode()).hexdigest(),
            "_lower": lowered,  # in-process only; stripped before the payload is written
        }
    return {"cards": cards}


def parse_exemplar(content: str) -> tuple[str, list[tuple[str, str]]]:
    parts = [part.strip() for part in content.split("|")]
    intent = parts[1] if len(parts) > 1 else ""
    pairs = []
    if len(parts) > 2 and parts[2]:
        for chunk in parts[2].split(";"):
            if "=" in chunk:
                name, filler = chunk.split("=", 1)
                if name.strip():
                    pairs.append((name.strip(), filler.strip()))
    return intent, pairs


def load_pool(root: Path, key: str) -> dict:
    path = root / PINS[key][0]  # pinned by its CONTENT hash, checked below
    snap = KnowledgeSnapshot.from_frozen_json(json.loads(path.read_text(encoding="utf-8")))
    if snap.content_hash() != PINS[key][1]:
        raise AuditError(f"{key} content hash is not the flown pin")
    values = {}
    for value in snap.values:
        utt = value.value_id.split("value:", 1)[-1]
        if len(value.associated_facet_ids) != 1:
            raise AuditError(f"{key}: a value is not bound to one facet")
        label, pairs = parse_exemplar(value.content)
        if label != value.task_target:
            raise AuditError(f"{key}: rendered label disagrees with task_target on {value.value_id}")
        values[str(int(utt))] = {"intent": value.task_target, "facet": value.associated_facet_ids[0],
                                 "pairs": pairs, "chars": len(value.content)}
    return {"values": values, "recordings": len(snap.source_sample_ids)}


def load_pool_vectors(root: Path, facets: set) -> dict:
    path = pinned(root, "pool_keys")
    out, rows = {}, 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows += 1
            record = json.loads(line)
            if record["id"] in facets:
                out[record["id"]] = np.asarray(record["vectors"][POOL_DIM], dtype=np.float64)
    if set(out) != facets:
        raise AuditError("pool key vectors do not cover the released pool")
    return {"vectors": out, "file_rows": rows}


def load_queries(root: Path, sample_ids) -> dict:
    loaded = load_sealed_segment_vectors(pinned(root, "fold_a_queries"),
                                         expected_sha256=PINS["fold_a_queries"][1],
                                         dimensions=(IB_DIM,))
    out = {}
    for sample_id in sample_ids:
        record = loaded.get(sample_id)
        if record is None or len(record.segments) != 1:
            raise AuditError(f"{sample_id}: no single-segment boundary query vector")
        out[sample_id] = np.asarray(record.segments[0][IB_DIM], dtype=np.float64)
    return out


# ---------------------------------------------------------------------------
# the sealed arm


def arm_dir(root: Path, arm: dict) -> Path:
    return root / "runs" / arm["run_id"] / arm["attempt"]


def load_consumption(root: Path, arm: dict) -> dict:
    path = arm_dir(root, arm) / f"{arm['run_id']}.phases.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "saea-flight-phase-summaries-v1" or len(document["phases"]) != 1:
        raise AuditError(f"{arm['run_id']}: unexpected phase artefact")
    rows = {}
    for result in document["phases"][0]["results"]:
        boundary, exemplars, contracts = [], [], []
        for record in (result.get("consumption") or {}).get("records") or ():
            item = bare(str(record.get("supplied_item_id") or ""))
            if item.startswith("intent-boundary:"):
                boundary.append(item.split("intent-boundary:", 1)[-1])
            elif item.startswith("value:"):
                exemplars.append(str(int(item.split("value:", 1)[-1])))
            elif item.startswith("slot-contract:"):
                contracts.append(item.split("slot-contract:", 1)[-1])
        rows[result["sample_id"]] = {"boundary": boundary, "exemplars": exemplars,
                                     "contracts": contracts}
    del document
    return {"rows": rows, "relpath": str(path.relative_to(root)), "sha256": digest(path)}


def load_arm(root: Path, arm: dict) -> dict:
    directory = arm_dir(root, arm)
    scores_path = directory / f"{arm['run_id']}.scores.json"
    block = json.loads(scores_path.read_text(encoding="utf-8"))[SCORER]
    per_sample = {str(s["sample_id"]): s for s in block["per_sample"]}
    outputs_path = directory / f"{arm['run_id']}.outputs.jsonl"
    delivered = {}
    with outputs_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            scenario, action, entities, parsed = parse_slu_response(record.get("text") or "")
            delivered[record["sample_id"]] = {
                "parsed": bool(parsed),
                "intent": (f"{scenario}_{action}" if parsed and isinstance(scenario, str)
                           and isinstance(action, str) else "<unparsed>"),
                "entities": list(entities),
            }
    if set(delivered) != set(per_sample) or len(delivered) != ROWS_EXPECTED:
        raise AuditError(f"{arm['run_id']}: outputs and per-sample scores do not cover one roster")
    identity = split_identity_hash(prefixed("slurp", sorted(delivered)))
    official = block["aggregate"]["official"]
    fields = (("slu_f1_word_tp", "slu_f1_char_tp"), ("slu_f1_word_fp", "slu_f1_char_fp"),
              ("slu_f1_word_fn", "slu_f1_char_fn"))
    pooled_slu = pooled_f1(per_sample, sorted(per_sample), fields)
    pooled_span = pooled_f1(per_sample, sorted(per_sample),
                            (("slot_f1_exact_tp",), ("slot_f1_exact_fp",), ("slot_f1_exact_fn",)))
    scale = 100.0 if float(official["slu_f1"]) > 1.0 else 1.0
    if abs(pooled_slu * scale - float(official["slu_f1"])) > 1e-6 * scale:
        raise AuditError(f"{arm['run_id']}: pooled SLU-F1 does not reproduce the official aggregate")
    return {
        "per_sample": per_sample, "delivered": delivered,
        "split_identity": identity,
        "official": {"intent_accuracy": official["intent_accuracy"], "slu_f1": official["slu_f1"],
                     "span_f1": official["span_f1"], "scale": scale},
        "pooled_slu_f1": pooled_slu, "pooled_span_f1": pooled_span,
        "scores_sha256": digest(scores_path), "outputs_sha256": digest(outputs_path),
    }


# ---------------------------------------------------------------------------
# per-row entity items (in-process pairing; mirrors row_entity_view's ordering)


def entity_items(gold_entities, predicted_entities) -> dict:
    """The official exact matcher, then the bank's same-type / type-swap / over / omission
    attribution, returning IN-PROCESS item tuples (fillers never leave this process)."""
    remaining = list(gold_entities)
    unmatched_pred = []
    for entity in predicted_entities:
        if entity in remaining:
            remaining.remove(entity)
        else:
            unmatched_pred.append(entity)
    by_pred, by_gold = defaultdict(list), defaultdict(list)
    for i, e in enumerate(unmatched_pred):
        by_pred[e.type].append((i, e))
    for i, e in enumerate(remaining):
        by_gold[e.type].append((i, e))
    used_p, used_g, same, swap = set(), set(), [], []
    for slot_type in sorted(set(by_pred) & set(by_gold)):
        options = []
        for pi, pe in by_pred[slot_type]:
            for gi, ge in by_gold[slot_type]:
                left, right = _fold_punct(pe.filler), _fold_punct(ge.filler)
                options.append((_edit_distance(left, right) / max(len(left), len(right), 1), pi, gi, pe, ge))
        for _, pi, gi, pe, ge in sorted(options, key=lambda o: o[:3]):
            if pi in used_p or gi in used_g:
                continue
            used_p.add(pi)
            used_g.add(gi)
            same.append((pe, ge))
    gold_by_filler = defaultdict(list)
    for gi, ge in enumerate(remaining):
        if gi not in used_g:
            gold_by_filler[_fold_punct(ge.filler)].append(gi)
    for pi, pe in enumerate(unmatched_pred):
        if pi in used_p:
            continue
        matches = [g for g in gold_by_filler.get(_fold_punct(pe.filler), ()) if g not in used_g]
        if matches:
            used_p.add(pi)
            used_g.add(matches[0])
            swap.append((pe, remaining[matches[0]]))
    over = [e for i, e in enumerate(unmatched_pred) if i not in used_p]
    omitted = [e for i, e in enumerate(remaining) if i not in used_g]
    return {"same": same, "swap": swap, "over": over, "omitted": omitted}


# ---------------------------------------------------------------------------
# section 1: intent boundaries


def boundary_ranks(keys: np.ndarray, order, query: np.ndarray) -> list[str]:
    scores = keys @ query
    return [order[i] for i in sorted(range(len(order)), key=lambda i: (-scores[i], order[i]))
            if scores[i] > 0.0]


def audit_boundaries(ib: dict, rows: dict, queries: dict, aa_boundary: dict, gold_train: dict,
                     gold_devel: dict, pool: dict, pool_geo: dict) -> dict:
    cards, order = ib["cards"], ib["order"]
    # coverage
    train_intents = Counter(u["intent"] for u in gold_train["utterances"].values())
    devel_intents = Counter(u["intent"] for u in gold_devel["utterances"].values())
    coverage = {
        "store_entries": len(order),
        "train_intents": len(train_intents),
        "devel_intents": len(devel_intents),
        "train_intents_without_entry": sorted(set(train_intents) - set(order)),
        "devel_intents_without_entry": sorted(set(devel_intents) - set(order)),
        "entries_without_train_intent": sorted(set(order) - set(train_intents)),
    }
    # overlaps
    pairs = [(a, b) for i, a in enumerate(order) for b in order[i + 1:]]
    body_j = [jaccard(cards[a]["body_words"], cards[b]["body_words"]) for a, b in pairs]
    disc_j = [jaccard(cards[a]["discriminative_words"], cards[b]["discriminative_words"]) for a, b in pairs]
    rep_j = [jaccard(ib["reps"][a], ib["reps"][b]) for a, b in pairs]
    wk, ck = ib["written"], ib["centroid"]
    wcos = wk @ wk.T
    ccos = ck @ ck.T
    iu = np.triu_indices(len(order), 1)
    total_chars = sum(c["chars"] for c in cards.values())
    section_totals = {name: sum(c["section_chars"][name] for c in cards.values()) for name in IB_SECTIONS}
    overlap = {
        "pairs": len(pairs),
        "delivered_body_word_jaccard_mean": rnd(np.mean(body_j)),
        "delivered_body_word_jaccard_max": rnd(max(body_j)),
        "discriminative_sections_word_jaccard_mean": rnd(np.mean(disc_j)),
        "encoded_representation_word_jaccard_mean": rnd(np.mean(rep_j)),
        "encoded_representation_word_jaccard_max": rnd(max(rep_j)),
        "written_key_cosine_mean": rnd(wcos[iu].mean()),
        "written_key_cosine_max": rnd(wcos[iu].max()),
        "centroid_key_cosine_mean": rnd(ccos[iu].mean()),
        "card_chars_total": total_chars,
        "card_chars_mean": rnd(total_chars / len(cards), 2),
        "section_chars_total": section_totals,
        "section_share_of_body_pct": {k: pct(v, total_chars) for k, v in section_totals.items()},
        "distinct_uncertainty_sections": len({c["uncertainty_sha"] for c in cards.values()}),
        "distinct_limitations_sections": len({c["limitations_sha"] for c in cards.values()}),
        "activation_items_mean": rnd(np.mean([c["activation_items"] for c in cards.values()]), 3),
        "exclusions_per_card_mean": rnd(np.mean([len(c["excludes"]) for c in cards.values()]), 3),
        "exclusions_per_card_distribution": dict(sorted(Counter(len(c["excludes"]) for c in cards.values()).items())),
        "cards_with_zero_exclusions": sorted(i for i in order if not cards[i]["excludes"]),
    }
    # validation: cosine-only top-8 reproduces the in-chain A/A arm's sealed delivered set
    exact = 0
    for sample_id, query in sorted(queries.items()):
        top = boundary_ranks(wk, order, query)[:FLOWN_BOUNDARY_WIDTH]
        if set(top) == set(aa_boundary[sample_id]):
            exact += 1
    validation = {"rows": len(queries), "aa_delivered_set_reproduced": exact}
    if exact != len(queries):
        raise AuditError(f"written-key recomputation reproduces the A/A delivered set on {exact}/{len(queries)} rows only")

    # the AGREE arm's remaining intent errors
    wrong = {sid: r for sid, r in rows.items() if not r["intent_correct"]}
    pair_counts = Counter((r["gold_intent"], r["pred_intent"]) for r in wrong.values())
    per_row = {}
    for sid, r in sorted(wrong.items()):
        g, p = r["gold_intent"], r["pred_intent"]
        q = queries[sid]
        w_rank = boundary_ranks(wk, order, q)
        c_rank = boundary_ranks(ck, order, q)
        rank = lambda lst, x: (lst.index(x) + 1) if x in lst else 61  # noqa: E731
        delivered = set(r["boundary"])
        per_row[sid] = {
            "gold_delivered": g in delivered,
            "pred_delivered": p in delivered,
            "pred_valid_intent": p in cards,
            "gold_card_excludes_pred": p in cards.get(g, {}).get("excludes", ()),
            "pred_card_excludes_gold": g in cards.get(p, {}).get("excludes", ()),
            "written_gold_rank": rank(w_rank, g), "written_pred_rank": rank(w_rank, p),
            "centroid_gold_rank": rank(c_rank, g), "centroid_pred_rank": rank(c_rank, p),
            "centroid_delivers_gold": rank(c_rank, g) <= FLOWN_BOUNDARY_WIDTH,
            "pair_body_jaccard": rnd(jaccard(cards[g]["body_words"], cards[p]["body_words"])) if p in cards else None,
            "pair_written_cos": rnd(wk[order.index(g)] @ wk[order.index(p)]) if p in cards else None,
        }
    n_wrong = len(wrong)
    agg = Counter()
    for sid, v in per_row.items():
        agg["gold_delivered"] += v["gold_delivered"]
        agg["pred_delivered"] += v["pred_delivered"]
        agg["both_delivered"] += v["gold_delivered"] and v["pred_delivered"]
        agg["either_card_names_other"] += v["gold_card_excludes_pred"] or v["pred_card_excludes_gold"]
        agg["gold_card_names_pred"] += v["gold_card_excludes_pred"]
        agg["pred_card_names_gold"] += v["pred_card_excludes_gold"]
        agg["written_key_prefers_pred"] += v["written_pred_rank"] < v["written_gold_rank"]
        agg["centroid_key_prefers_pred"] += v["centroid_pred_rank"] < v["centroid_gold_rank"]
        agg["not_delivered_centroid_would"] += (not v["gold_delivered"]) and v["centroid_delivers_gold"]
        agg["not_delivered_centroid_would_not"] += (not v["gold_delivered"]) and not v["centroid_delivers_gold"]
        agg["delivered_both_no_exclusion"] += (v["gold_delivered"] and v["pred_delivered"]
                                             and not (v["gold_card_excludes_pred"] or v["pred_card_excludes_gold"]))
        agg["delivered_both_with_exclusion"] += (v["gold_delivered"] and v["pred_delivered"]
                                               and (v["gold_card_excludes_pred"] or v["pred_card_excludes_gold"]))
        agg["gold_delivered_pred_not"] += v["gold_delivered"] and not v["pred_delivered"]
        agg["unparsed_or_invalid_pred"] += not v["pred_valid_intent"]
    top_pairs = []
    for (g, p), n in sorted(pair_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        members = [sid for sid, r in wrong.items() if (r["gold_intent"], r["pred_intent"]) == (g, p)]
        top_pairs.append({
            "gold": g, "pred": p, "rows": n,
            "gold_delivered": sum(per_row[s]["gold_delivered"] for s in members),
            "gold_card_names_pred": p in cards.get(g, {}).get("excludes", ()),
            "pred_card_names_gold": g in cards.get(p, {}).get("excludes", ()),
            "written_key_prefers_pred": sum(per_row[s]["written_pred_rank"] < per_row[s]["written_gold_rank"] for s in members),
            "centroid_key_prefers_pred": sum(per_row[s]["centroid_pred_rank"] < per_row[s]["centroid_gold_rank"] for s in members),
            "body_word_jaccard": per_row[members[0]]["pair_body_jaccard"],
            "written_key_cosine": per_row[members[0]]["pair_written_cos"],
            "pool_gold_exemplars_nearer_pred_centroid": pool_geo["pair_crossing"].get(f"{g}->{p}", 0),
            "pool_pred_exemplars_nearer_gold_centroid": pool_geo["pair_crossing"].get(f"{p}->{g}", 0),
        })
    named_delivered = Counter()
    for sid, r in rows.items():
        flag = bool(set(cards[r["gold_intent"]]["excludes"]) & set(r["boundary"]))
        named_delivered[("named-confuser-delivered" if flag else "named-confuser-absent", r["intent_correct"])] += 1
    exclusion_vs_accuracy = {}
    for label in ("named-confuser-delivered", "named-confuser-absent"):
        right, wrong_n = named_delivered[(label, True)], named_delivered[(label, False)]
        exclusion_vs_accuracy[label] = {"rows": right + wrong_n, "intent_accuracy_pct": pct(right, right + wrong_n)}
    per_gold = Counter(r["gold_intent"] for r in wrong.values())
    gold_rows = Counter(r["gold_intent"] for r in rows.values())
    per_gold_table = [{"intent": i, "gold_rows": gold_rows[i], "wrong": n,
                       "distinct_confusers": len({r["pred_intent"] for r in wrong.values() if r["gold_intent"] == i}),
                       "exclusions_on_card": len(cards[i]["excludes"]),
                       "confusers_named_on_card": len({r["pred_intent"] for r in wrong.values()
                                                       if r["gold_intent"] == i} & set(cards[i]["excludes"]))}
                      for i, n in sorted(per_gold.items(), key=lambda kv: (-kv[1], kv[0]))]
    # general_quirky
    gq = "general_quirky"
    gq_rows = [sid for sid, r in rows.items() if r["gold_intent"] == gq]
    gq_wrong = [sid for sid in gq_rows if not rows[sid]["intent_correct"]]
    gq_fp = [sid for sid, r in rows.items() if r["pred_intent"] == gq and r["gold_intent"] != gq]
    quirky = {
        "gold_rows": len(gq_rows), "correct": len(gq_rows) - len(gq_wrong), "wrong": len(gq_wrong),
        "wrong_gold_boundary_delivered": sum(gq in rows[s]["boundary"] for s in gq_wrong),
        "wrong_centroid_would_deliver": sum(per_row[s]["centroid_delivers_gold"] for s in gq_wrong),
        "wrong_predicted_as": dict(sorted(Counter(rows[s]["pred_intent"] for s in gq_wrong).items(),
                                          key=lambda kv: (-kv[1], kv[0]))),
        "distinct_predicted_on_wrong": len({rows[s]["pred_intent"] for s in gq_wrong}),
        "over_predicted_rows": len(gq_fp),
        "card_activation_items": cards[gq]["activation_items"],
        "card_exclusions": len(cards[gq]["excludes"]),
        "card_chars": cards[gq]["chars"],
        "card_activation_chars": cards[gq]["section_chars"]["Activation boundary"],
        "cards_naming_quirky_in_exclusions": sum(gq in c["excludes"] for c in cards.values()),
        "wrong_rows_exemplar_gold_count_mean": rnd(np.mean([rows[s]["ex_gold"] for s in gq_wrong]), 3) if gq_wrong else 0.0,
        "pool_exemplars": pool_geo["per_intent"][gq]["pool_utterances"],
        "pool_knn_label_agreement_mean": pool_geo["per_intent"][gq]["knn_agreement_mean"],
        "pool_knn_label_agreement_all_intents_mean": pool_geo["knn_agreement_mean_all"],
        "pool_nearer_other_centroid_pct": pool_geo["per_intent"][gq]["nearer_other_pct"],
        "pool_nearer_other_centroid_pct_all": pool_geo["nearer_other_pct_all"],
        "pool_own_centroid_cos_mean": pool_geo["per_intent"][gq]["own_centroid_cos_mean"],
        "pool_own_centroid_cos_mean_all": pool_geo["own_centroid_cos_mean_all"],
    }
    return {"coverage": coverage, "overlap": overlap, "validation": validation,
            "remaining_errors": {"rows": n_wrong, "distinct_pairs": len(pair_counts),
                                 "counts": dict(sorted(agg.items()))},
            "top_pairs": top_pairs[:25], "pairs_all": len(top_pairs),
            "pairs_with_2_or_more_rows": sum(1 for p in top_pairs if p["rows"] >= 2),
            "rows_in_singleton_pairs": sum(p["rows"] for p in top_pairs if p["rows"] == 1),
            "gold_card_named_confuser_vs_accuracy": exclusion_vs_accuracy,
            "per_gold_intent": per_gold_table, "general_quirky": quirky,
            "_per_row": per_row}


# ---------------------------------------------------------------------------
# section 2: the exemplar pool


def pool_geometry(pool: dict, vectors: dict, gold_train: dict) -> dict:
    ids = sorted(pool["values"], key=int)
    labels = [pool["values"][u]["intent"] for u in ids]
    matrix = unit_rows([vectors[pool["values"][u]["facet"]] for u in ids])
    n = len(ids)
    intents = sorted(set(labels))
    index = {i: k for k, i in enumerate(intents)}
    lab = np.array([index[x] for x in labels])
    sums = np.zeros((len(intents), matrix.shape[1]))
    counts = np.zeros(len(intents))
    for row, k in enumerate(lab):
        sums[k] += matrix[row]
        counts[k] += 1
    centroids = unit_rows(sums / counts[:, None])
    # nearest neighbours, blockwise
    nn_cos = np.zeros(n)
    nn_same = np.zeros(n, dtype=bool)
    knn_agree = np.zeros(n)
    block = 512
    for start in range(0, n, block):
        stop = min(n, start + block)
        sims = matrix[start:stop] @ matrix.T
        for r in range(stop - start):
            sims[r, start + r] = -np.inf
        top = np.argpartition(-sims, NN_K, axis=1)[:, :NN_K]
        for r in range(stop - start):
            order = sorted(top[r], key=lambda c: (-sims[r, c], c))
            nn_cos[start + r] = sims[r, order[0]]
            nn_same[start + r] = lab[order[0]] == lab[start + r]
            knn_agree[start + r] = sum(lab[c] == lab[start + r] for c in order)
    # leave-one-out own centroid vs nearest other centroid
    own_loo = np.zeros(n)
    best_other = np.zeros(n)
    best_other_label = np.zeros(n, dtype=int)
    all_c = matrix @ centroids.T
    for row in range(n):
        k = lab[row]
        if counts[k] > 1:
            loo = (sums[k] - matrix[row]) / (counts[k] - 1)
            loo = loo / (np.linalg.norm(loo) or 1.0)
            own_loo[row] = matrix[row] @ loo
        else:
            own_loo[row] = -1.0
        others = all_c[row].copy()
        others[k] = -np.inf
        j = int(np.argmax(others))
        best_other[row], best_other_label[row] = others[j], j
    nearer_other = best_other > own_loo
    cc = centroids @ centroids.T
    centroid_neighbours = {}
    for k, intent in enumerate(intents):
        order = sorted((j for j in range(len(intents)) if j != k), key=lambda j: (-cc[k, j], intents[j]))
        centroid_neighbours[intent] = [intents[j] for j in order[:8]]
    pair_crossing = Counter()
    for row in range(n):
        if nearer_other[row]:
            pair_crossing[f"{intents[lab[row]]}->{intents[best_other_label[row]]}"] += 1
    # label-noise cross-check: nearer-other exemplars with a near-identical sentence of the other intent
    by_intent_tokens = defaultdict(list)
    for utt, entry in gold_train["utterances"].items():
        by_intent_tokens[entry["intent"]].append(entry["token_set"])
    near_identical = Counter()
    for row in range(n):
        if not nearer_other[row]:
            continue
        own_tokens = gold_train["utterances"][ids[row]]["token_set"]
        other = intents[best_other_label[row]]
        best = max((jaccard(own_tokens, t) for t in by_intent_tokens[other]), default=0.0)
        for threshold in (1.0, 0.9, 0.8):
            if best >= threshold:
                near_identical[f"J>={threshold}"] += 1
    # text-level exact duplicates in the pool (normalised sentence, in-process)
    sent = Counter(" ".join(sorted(gold_train["utterances"][u]["token_set"])) for u in ids)
    dup_groups = sum(1 for c in sent.values() if c > 1)
    per_intent = {}
    for k, intent in enumerate(intents):
        mask = lab == k
        per_intent[intent] = {
            "pool_utterances": int(mask.sum()),
            "knn_agreement_mean": rnd(knn_agree[mask].mean() / NN_K, 4),
            "nearer_other_pct": pct(int(nearer_other[mask].sum()), int(mask.sum())),
            "own_centroid_cos_mean": rnd(own_loo[mask].mean(), 4),
            "nn_cross_intent_pct": pct(int((~nn_same[mask]).sum()), int(mask.sum())),
        }
    near_dup = {}
    for threshold in (0.99, 0.97, 0.95, 0.90):
        hit = nn_cos >= threshold
        near_dup[str(threshold)] = {"items": int(hit.sum()), "pct": pct(int(hit.sum()), n),
                                    "cross_intent_items": int((hit & ~nn_same).sum())}
    return {
        "items": n, "intents": len(intents),
        "nn_cos_mean": rnd(nn_cos.mean(), 4), "nn_cos_median": rnd(np.median(nn_cos), 4),
        "near_duplicates": near_dup,
        "normalised_sentence_duplicate_groups": dup_groups,
        "normalised_sentence_duplicate_items": sum(c for c in sent.values() if c > 1),
        "knn_agreement_mean_all": rnd(knn_agree.mean() / NN_K, 4),
        "knn_majority_other_items": int((knn_agree < NN_K / 2).sum()),
        "nearer_other_items": int(nearer_other.sum()),
        "nearer_other_pct_all": pct(int(nearer_other.sum()), n),
        "nearer_other_near_identical_sentence": dict(sorted(near_identical.items())),
        "own_centroid_cos_mean_all": rnd(own_loo.mean(), 4),
        "pair_crossing": dict(sorted(pair_crossing.items())),
        "top_crossings": [{"from": k.split("->")[0], "to": k.split("->")[1], "items": v}
                          for k, v in sorted(pair_crossing.items(), key=lambda kv: (-kv[1], kv[0]))[:15]],
        "per_intent": per_intent,
        "centroid_neighbours": centroid_neighbours,
    }


def audit_exemplars(pool: dict, pool_m: dict, gold_train: dict, fold_a_utts: set, rows: dict,
                    geo: dict) -> dict:
    train_counts = Counter(u["intent"] for u in gold_train["utterances"].values())
    pool_counts = Counter(v["intent"] for v in pool["values"].values())
    pool_m_counts = Counter(v["intent"] for v in pool_m["values"].values())
    intents = sorted(train_counts)

    def spread(counter):
        vals = [counter.get(i, 0) for i in intents]
        return {"min": min(vals), "median": float(np.median(vals)), "max": max(vals),
                "max_over_min": rnd(max(vals) / min(vals), 2) if min(vals) else None,
                "gini": rnd(gini(vals), 4), "cv": rnd(np.std(vals) / np.mean(vals), 4),
                "intents_below_50": sum(v < 50 for v in vals),
                "smallest": sorted(((counter.get(i, 0), i) for i in intents))[:6],
                "largest": sorted(((counter.get(i, 0), i) for i in intents), reverse=True)[:6]}

    # (intent, type) coverage: TRAIN outside Fold A vs the pool
    train_pairs, pool_pairs = Counter(), Counter()
    for utt, entry in gold_train["utterances"].items():
        if utt in fold_a_utts:
            continue
        for t in {e.type for e in entry["entities"]}:
            train_pairs[(entry["intent"], t)] += 1
    for value in pool["values"].values():
        for t in {name for name, _ in value["pairs"]}:
            pool_pairs[(value["intent"], t)] += 1
    fold_pairs = Counter()
    for sid, r in rows.items():
        for t in {e.type for e in r["gold_entities"]}:
            fold_pairs[(r["gold_intent"], t)] += 1
    pair_cov = {
        "train_pairs": len(train_pairs),
        "pool_pairs": len(pool_pairs),
        "train_pairs_absent_from_pool": len([p for p in train_pairs if p not in pool_pairs]),
        "train_pairs_with_1_2_pool_exemplars": len([p for p in train_pairs if 1 <= pool_pairs.get(p, 0) <= 2]),
        "fold_a_pairs": len(fold_pairs),
        "fold_a_pairs_absent_from_pool": sorted(f"{i}/{t}" for (i, t) in fold_pairs if (i, t) not in pool_pairs),
        "fold_a_pairs_with_le2_pool_exemplars": len([p for p in fold_pairs if pool_pairs.get(p, 0) <= 2]),
    }
    # pool annotation vs governed gold (label and entity consistency, in-process)
    label_mismatch = entity_mismatch = 0
    for utt, value in pool["values"].items():
        gold = gold_train["utterances"][utt]
        if value["intent"] != gold["intent"]:
            label_mismatch += 1
        if sorted(value["pairs"]) != sorted((e.type, e.filler) for e in gold["entities"]):
            entity_mismatch += 1
    # exemplar selection on the AGREE rows
    buckets = lambda n: "0" if n == 0 else ("1-4" if n < 5 else ("5-9" if n < 10 else "10-20"))  # noqa: E731
    sel = {"wrong": Counter(), "correct": Counter()}
    majority = Counter()
    wrong_rows = [s for s, r in rows.items() if not r["intent_correct"]]
    for sid, r in rows.items():
        klass = "correct" if r["intent_correct"] else "wrong"
        sel[klass][buckets(r["ex_gold"])] += 1
        if klass == "wrong":
            majority["majority_is_gold"] += r["ex_majority"] == r["gold_intent"]
            majority["majority_is_pred"] += r["ex_majority"] == r["pred_intent"]
            majority["pred_has_any_exemplar"] += r["ex_pred"] > 0
            majority["gold_count_gt_pred_count"] += r["ex_gold"] > r["ex_pred"]
    return {
        "counts": {"train_utterances": sum(train_counts.values()), "pool": sum(pool_counts.values()),
                   "pool_minus_r01": sum(pool_m_counts.values()), "pool_recordings": pool["recordings"],
                   "pool_minus_r01_recordings": pool_m["recordings"],
                   "pool_intents": len(pool_counts), "pool_minus_r01_intents": len(pool_m_counts),
                   "pool_minus_r01_missing_intents": sorted(set(intents) - set(pool_m_counts))},
        "imbalance": {"train": spread(train_counts), "pool": spread(pool_counts),
                      "pool_minus_r01": spread(pool_m_counts)},
        "per_intent_counts": {i: {"train": train_counts[i], "pool": pool_counts.get(i, 0),
                                  "pool_minus_r01": pool_m_counts.get(i, 0)} for i in intents},
        "intent_type_coverage": pair_cov,
        "pool_vs_governed_gold": {"label_mismatch": label_mismatch, "entity_list_mismatch": entity_mismatch},
        "geometry": {k: v for k, v in geo.items() if k not in ("pair_crossing", "centroid_neighbours")},
        "selection": {
            "k_delivered_per_row": dict(sorted(Counter(len(r["exemplars"]) for r in rows.values()).items())),
            "gold_exemplars_in_20_wrong_rows": dict(sorted(sel["wrong"].items())),
            "gold_exemplars_in_20_correct_rows": dict(sorted(sel["correct"].items())),
            "wrong_rows": len(wrong_rows),
            "wrong_rows_gold_mean": rnd(np.mean([rows[s]["ex_gold"] for s in wrong_rows]), 3),
            "wrong_rows_pred_mean": rnd(np.mean([rows[s]["ex_pred"] for s in wrong_rows]), 3),
            "correct_rows_gold_mean": rnd(np.mean([r["ex_gold"] for r in rows.values() if r["intent_correct"]]), 3),
            "wrong_rows_majority": dict(sorted(majority.items())),
        },
    }


# ---------------------------------------------------------------------------
# section 3: slot contracts


def audit_slots(sc: dict, gold_train: dict, fold_a_utts: set, rows: dict, pool: dict) -> dict:
    cards = sc["cards"]
    # TRAIN (outside Fold A) value sets per type, and leave-one-utterance-out coverage
    values_by_type = defaultdict(Counter)       # folded filler -> number of utterances
    mentions_by_type = Counter()
    shape_by_type = defaultdict(Counter)
    train_types = Counter()
    for utt, entry in gold_train["utterances"].items():
        for e in entry["entities"]:
            train_types[e.type] += 1
        if utt in fold_a_utts:
            continue
        seen = set()
        for e in entry["entities"]:
            f = _fold_punct(e.filler)
            mentions_by_type[e.type] += 1
            shape = filler_shape(e.filler)
            for flag in ("has_digit", "has_ordinal", "has_relative", "has_meridiem"):
                shape_by_type[e.type][flag] += bool(shape[flag])
            if (e.type, f) not in seen:
                values_by_type[e.type][f] += 1
                seen.add((e.type, f))
    pool_values = defaultdict(set)
    for value in pool["values"].values():
        for name, filler in value["pairs"]:
            pool_values[name].add(_fold_punct(filler))
    type_class, loo_cov = {}, {}
    for t, counter in values_by_type.items():
        # leave-one-utterance-out: a mention is covered if its filler occurs in another utterance
        # (utterance-level counts: n_utts(filler) >= 2)
        # computed per mention via the utterance counts
        total = sum(counter.values())  # utterance-mentions (deduplicated per utterance)
        covered = sum(c for f, c in counter.items() if c >= 2)
        loo_cov[t] = covered / total if total else 0.0
        type_class[t] = ("closed" if loo_cov[t] >= LOO_CLOSED else
                         ("semi-closed" if loo_cov[t] >= LOO_SEMI else "open"))
    # card coverage of the value list (how many distinct TRAIN values the card names verbatim)
    card_rows = {}
    for t in sorted(set(cards) | set(train_types)):
        card = cards.get(t)
        distinct = values_by_type.get(t, Counter())
        named = 0
        if card is not None:
            for f in distinct:
                if len(f) >= 3 and re.search(r"(?<![a-z0-9])" + re.escape(f) + r"(?![a-z0-9])", card["_lower"]):
                    named += 1
        m = mentions_by_type.get(t, 0)
        card_rows[t] = {
            "has_card": card is not None,
            "card_chars": card["chars"] if card else 0,
            "bound_intents": len(card["bound_intents"]) if card else 0,
            "cue_lines": card["cue_lines"] if card else 0,
            "format_lines": card["format_lines"] if card else 0,
            "format_flags": card["format_flags"] if card else {},
            "train_mentions_outside_fold_a": m,
            "train_distinct_values": len(distinct),
            "loo_value_coverage": rnd(loo_cov.get(t, 0.0), 4),
            "vocabulary_class": type_class.get(t, "absent"),
            "values_named_on_card": named,
            "pool_distinct_values": len(pool_values.get(t, ())),
            "gold_share_has_digit": pct(shape_by_type[t]["has_digit"], m),
            "gold_share_has_meridiem": pct(shape_by_type[t]["has_meridiem"], m),
            "gold_share_has_ordinal": pct(shape_by_type[t]["has_ordinal"], m),
            "gold_share_has_relative": pct(shape_by_type[t]["has_relative"], m),
        }
    # per-type loss on the AGREE arm, decomposition and value-set membership of the error items
    per_type = defaultdict(lambda: Counter())
    rung = Counter()
    rung_by_type = defaultdict(Counter)
    swap_pairs = Counter()
    item_classes = Counter()
    items_by_class_type = defaultdict(Counter)
    repair_sets = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # deficit -> sid -> [gold_items, pred_items]
    over_legality = Counter()
    train_pair_set = set()
    for utt, entry in gold_train["utterances"].items():
        if utt not in fold_a_utts:
            for e in entry["entities"]:
                train_pair_set.add((entry["intent"], e.type))
    containment = Counter()
    containment_by_type = defaultdict(Counter)
    swap_card_mentions = Counter()
    pred_filler_stats = Counter()
    cards_offered = chars_offered = chars_unused = cards_used = 0
    rows_all_delivered_types_carded = rows_all_gold_types_carded = rows_with_gold = 0
    for sid, r in sorted(rows.items()):
        view = row_entity_view(r["gold_entities"], r["pred_entities"])
        items = entity_items(r["gold_entities"], r["pred_entities"])
        side = "intent_right" if r["intent_correct"] else "intent_wrong"
        for name in ("tp", "fp", "fn"):
            for t, v in view["per_type"][name].items():
                per_type[t][name] += v
                per_type[t][f"{name}_{side}"] += v
        # same check the bank asserts: our pairing reproduces the bank's per-type decomposition
        if Counter(g.type for _, g in items["same"]) != Counter(s["slot_type"] for s in view["same_type"]):
            raise AuditError(f"{sid}: in-process pairing disagrees with row_entity_view")
        for pe, ge in items["same"]:
            shape = pair_shape(pe.filler, ge.filler)
            rung[shape["repair_rung"]] += 1
            rung_by_type[ge.type][shape["repair_rung"]] += 1
            per_type[ge.type]["same_type_wrong_filler"] += 1
            vset = values_by_type.get(ge.type, Counter())
            g_in, p_in = _fold_punct(ge.filler) in vset, _fold_punct(pe.filler) in vset
            if shape["repair_rung"] in ("case-whitespace", "punctuation", "meridiem"):
                klass = "same-type:format-only"
                repair_sets["format"][sid][0] += 1
                repair_sets["format"][sid][1] += 1
            elif g_in and not p_in:
                klass = "same-type:gold-in-train-values,pred-outside"
                repair_sets["value_list_snap"][sid][0] += 1
                repair_sets["value_list_snap"][sid][1] += 1
            elif g_in and p_in:
                klass = "same-type:both-in-train-values"
            else:
                klass = "same-type:gold-outside-train-values"
            item_classes[klass] += 1
            items_by_class_type[klass][type_class.get(ge.type, "absent")] += 1
            if shape["boundary_containment"]:
                item_classes["same-type:span-boundary-containment(subset)"] += 1
                direction = "pred-longer" if shape["token_delta"] > 0 else (
                    "pred-shorter" if shape["token_delta"] < 0 else "same-length")
                containment[direction] += 1
                containment_by_type[ge.type][direction] += 1
                repair_sets["span_extent"][sid][0] += 1
                repair_sets["span_extent"][sid][1] += 1
            vclass = type_class.get(ge.type, "absent")
            if klass == "same-type:gold-in-train-values,pred-outside" and vclass in ("closed", "semi-closed"):
                repair_sets["value_list_snap_closed_semi"][sid][0] += 1
                repair_sets["value_list_snap_closed_semi"][sid][1] += 1
                repair_sets["value_lists_closed_semi_combined"][sid][0] += 1
                repair_sets["value_lists_closed_semi_combined"][sid][1] += 1
                if shape["boundary_containment"]:
                    item_classes["overlap:value-list-snap-and-span-containment"] += 1
        for pe, ge in items["swap"]:
            swap_pairs[f"{pe.type}->{ge.type}"] += 1
            gold_card = cards.get(ge.type, {}).get("_lower", "")
            pred_card = cards.get(pe.type, {}).get("_lower", "")
            named = (re.search(r"(?<![a-z_])" + re.escape(pe.type) + r"(?![a-z_])", gold_card) is not None
                     or re.search(r"(?<![a-z_])" + re.escape(ge.type) + r"(?![a-z_])", pred_card) is not None)
            swap_card_mentions["either_card_names_the_other_type" if named else "neither_card_names_the_other_type"] += 1
            per_type[ge.type]["type_swap_in"] += 1
            item_classes["type-swap"] += 1
            repair_sets["type_boundary"][sid][0] += 1
            repair_sets["type_boundary"][sid][1] += 1
        for e in items["omitted"]:
            per_type[e.type]["omission"] += 1
            vset = values_by_type.get(e.type, Counter())
            klass = ("omission:gold-in-train-values" if _fold_punct(e.filler) in vset
                     else "omission:gold-outside-train-values")
            item_classes[klass] += 1
            items_by_class_type[klass][type_class.get(e.type, "absent")] += 1
            eclass = type_class.get(e.type, "absent")
            if klass == "omission:gold-in-train-values" and eclass in ("closed", "semi-closed"):
                repair_sets[f"omission_in_values_{eclass}"][sid][0] += 1
                repair_sets["value_lists_closed_semi_combined"][sid][0] += 1
            if (r["gold_intent"], e.type) not in r["pool_pairs_present"]:
                repair_sets["intent_type_uncovered"][sid][0] += 1
            if e.type not in cards:
                repair_sets["missing_card"][sid][0] += 1
        for e in items["over"]:
            legal = (r["gold_intent"], e.type) in train_pair_set
            over_legality[("intent-right" if r["intent_correct"] else "intent-wrong",
                           "type-seen-with-gold-intent" if legal else "type-never-seen-with-gold-intent")] += 1
            if r["intent_correct"] and not legal:
                repair_sets["over_emission_schema_illegal_intent_right"][sid][1] += 1
            per_type[e.type]["over_emission"] += 1
            item_classes["over-emission"] += 1
            repair_sets["over_emission_all"][sid][1] += 1
            if r["intent_correct"]:
                repair_sets["over_emission_intent_right"][sid][1] += 1
        for e in r["pred_entities"]:
            pred_filler_stats["pred_fillers"] += 1
            pred_filler_stats["pred_fillers_with_digit"] += bool(re.search(r"\d", e.filler))
            pred_filler_stats["pred_fillers_with_uppercase"] += e.filler != e.filler.lower()
        for e in r["gold_entities"]:
            pred_filler_stats["gold_fillers"] += 1
            pred_filler_stats["gold_fillers_with_digit"] += bool(re.search(r"\d", e.filler))
        # card usage (the 90.6 % measurement, on this arm)
        delivered_types = {e.type for e in r["pred_entities"]}
        gold_types = {e.type for e in r["gold_entities"]}
        offered = list(dict.fromkeys(r["contracts"]))
        cards_offered += len(offered)
        for t in offered:
            chars = cards[t]["chars"] if t in cards else 0
            chars_offered += chars
            if t in delivered_types or t in gold_types:
                cards_used += 1
            else:
                chars_unused += chars
        rows_all_delivered_types_carded += delivered_types <= set(offered)
        if gold_types:
            rows_with_gold += 1
            rows_all_gold_types_carded += gold_types <= set(offered)
    per_type_rows = []
    for t in sorted(per_type, key=lambda t: (-(per_type[t]["fn"] + per_type[t]["fp"]), t)):
        c = per_type[t]
        per_type_rows.append({
            "type": t, "tp": c["tp"], "fp": c["fp"], "fn": c["fn"],
            "fn_intent_wrong": c["fn_intent_wrong"], "fp_intent_wrong": c["fp_intent_wrong"],
            "same_type_wrong_filler": c["same_type_wrong_filler"], "type_swap_in": c["type_swap_in"],
            "omission": c["omission"], "over_emission": c["over_emission"],
            "f1": rnd(2 * c["tp"] / (2 * c["tp"] + c["fp"] + c["fn"]), 4) if (2 * c["tp"] + c["fp"] + c["fn"]) else 0.0,
            "vocabulary_class": type_class.get(t, "absent"),
            "has_card": t in cards,
        })
    return {
        "store": {"cards": len(cards), "train_types": len(train_types),
                  "train_types_without_card": sorted(set(train_types) - set(cards)),
                  "cards_without_train_type": sorted(set(cards) - set(train_types)),
                  "card_chars_total": sum(c["chars"] for c in cards.values()),
                  "distinct_missing_behavior_sections": len({c["missing_sha"] for c in cards.values()}),
                  "cards_flagging": {flag: sum(c["format_flags"][flag] for c in cards.values())
                                     for flag in sorted(FORMAT_FLAGS)}},
        "per_type_card": card_rows,
        "vocabulary_classes": dict(sorted(Counter(type_class.values()).items())),
        "vocabulary_rule": f"leave-one-utterance-out value coverage over TRAIN outside Fold A: closed >= {LOO_CLOSED}, semi-closed >= {LOO_SEMI}, else open",
        "card_usage": {"cards_offered": cards_offered, "cards_used_by_delivered_or_gold": cards_used,
                       "card_chars_offered": chars_offered, "card_chars_serving_unused_types": chars_unused,
                       "unused_char_pct": pct(chars_unused, chars_offered),
                       "cards_per_row_mean": rnd(cards_offered / len(rows), 3),
                       "card_chars_per_row_mean": rnd(chars_offered / len(rows), 1),
                       "card_tokens_per_row_est": rnd(chars_offered / len(rows) / CHARS_PER_TOKEN, 1),
                       "rows_all_delivered_types_carded": rows_all_delivered_types_carded,
                       "rows_with_gold_entities": rows_with_gold,
                       "rows_all_gold_types_carded": rows_all_gold_types_carded},
        "per_type_loss": per_type_rows,
        "same_type_repair_rungs": dict(sorted(rung.items())),
        "same_type_repair_rungs_by_type": {t: dict(sorted(v.items())) for t, v in sorted(rung_by_type.items())},
        "type_swaps": [{"pred_type": k.split("->")[0], "gold_type": k.split("->")[1], "items": v}
                       for k, v in sorted(swap_pairs.items(), key=lambda kv: (-kv[1], kv[0]))[:20]],
        "error_item_classes": dict(sorted(item_classes.items())),
        "span_containment_direction": dict(sorted(containment.items())),
        "span_containment_by_type": {t: dict(sorted(v.items())) for t, v in sorted(containment_by_type.items(),
                                                                                   key=lambda kv: (-sum(kv[1].values()), kv[0]))[:12]},
        "type_swap_card_mentions": dict(sorted(swap_card_mentions.items())),
        "over_emission_legality": {f"{a}/{b}": v for (a, b), v in sorted(over_legality.items())},
        "filler_surface": dict(sorted(pred_filler_stats.items())),
        "error_item_classes_by_vocabulary": {k: dict(sorted(v.items())) for k, v in sorted(items_by_class_type.items())},
        "_repair_sets": repair_sets,
    }


# ---------------------------------------------------------------------------
# ceilings


def span_and_slu_ceiling(per_sample: dict, repair: dict) -> dict:
    """Exact span-F1 ceiling of repairing the named items, and the proportional SLU-F1
    approximation (a row's soft word/char counts moved by the repaired share of its exact items)."""
    base = {"span": [0.0, 0.0, 0.0], "slu": [0.0, 0.0, 0.0]}
    fixed = {"span": [0.0, 0.0, 0.0], "slu": [0.0, 0.0, 0.0]}
    for sid, s in per_sample.items():
        tp, fp, fn = s["slot_f1_exact_tp"], s["slot_f1_exact_fp"], s["slot_f1_exact_fn"]
        wtp = s["slu_f1_word_tp"] + s["slu_f1_char_tp"]
        wfp = s["slu_f1_word_fp"] + s["slu_f1_char_fp"]
        wfn = s["slu_f1_word_fn"] + s["slu_f1_char_fn"]
        base["span"] = [a + b for a, b in zip(base["span"], (tp, fp, fn))]
        base["slu"] = [a + b for a, b in zip(base["slu"], (wtp, wfp, wfn))]
        g_items, p_items = repair.get(sid, (0, 0))
        g_items, p_items = min(g_items, fn), min(p_items, fp)
        fixed["span"] = [a + b for a, b in zip(fixed["span"], (tp + g_items, fp - p_items, fn - g_items))]
        fg = g_items / fn if fn else 0.0
        fpf = p_items / fp if fp else 0.0
        fixed["slu"] = [a + b for a, b in zip(fixed["slu"], (wtp + fg * wfn, wfp * (1 - fpf), wfn * (1 - fg)))]
    f1 = lambda t: 2 * t[0] / (2 * t[0] + t[1] + t[2]) if (2 * t[0] + t[1] + t[2]) else 0.0  # noqa: E731
    return {"span_f1_now": rnd(100 * f1(base["span"]), 4), "span_f1_repaired": rnd(100 * f1(fixed["span"]), 4),
            "span_pp": rnd(100 * (f1(fixed["span"]) - f1(base["span"])), 4),
            "slu_f1_now": rnd(100 * f1(base["slu"]), 4), "slu_f1_repaired_approx": rnd(100 * f1(fixed["slu"]), 4),
            "slu_pp_approx": rnd(100 * (f1(fixed["slu"]) - f1(base["slu"])), 4),
            "rows": len(repair), "gold_items": sum(v[0] for v in repair.values()),
            "pred_items": sum(v[1] for v in repair.values())}


def row_ceiling_slu(per_sample: dict, members: set) -> float:
    """Exact pooled SLU-F1 gain if every entity of the member rows were repaired (the bank's rule)."""
    base, fixed = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    for sid, s in per_sample.items():
        tp = s["slu_f1_word_tp"] + s["slu_f1_char_tp"]
        fp = s["slu_f1_word_fp"] + s["slu_f1_char_fp"]
        fn = s["slu_f1_word_fn"] + s["slu_f1_char_fn"]
        base = [base[0] + tp, base[1] + fp, base[2] + fn]
        fixed = ([fixed[0] + tp + fn, fixed[1], fixed[2]] if sid in members
                 else [fixed[0] + tp, fixed[1] + fp, fixed[2] + fn])
    f1 = lambda t: 2 * t[0] / (2 * t[0] + t[1] + t[2])  # noqa: E731
    return rnd(100 * (f1(fixed) - f1(base)), 4)


def conversion(root: Path) -> dict:
    out = {}
    for key, rel in sorted(CONVERSION_READS.items()):
        path = root / rel
        document = json.loads(path.read_text(encoding="utf-8"))
        rate = document.get("rate") or {}
        m, n = rate.get("m"), rate.get("n")
        if not isinstance(m, int) or not isinstance(n, int) or not n:
            # the CONV read predates the 'rate' block; walk for m / n
            def walk(o):
                if isinstance(o, dict):
                    if isinstance(o.get("m"), int) and isinstance(o.get("n"), int):
                        return o["m"], o["n"]
                    for v in o.values():
                        got = walk(v)
                        if got:
                            return got
                return None
            got = walk(document)
            if not got:
                raise AuditError(f"{rel}: no m / n")
            m, n = got
        out[key] = {"relpath": rel, "sha256": digest(path), "m": m, "n": n, "rate": rnd(m / n, 6)}
    return out


# ---------------------------------------------------------------------------
# main measurement


def measure(lock_path: Path, root: Path) -> dict:
    lock = load_lock(lock_path)
    gold_train = load_gold(lock, root, "train")
    gold_devel = load_gold(lock, root, "devel", labels_only=True)
    ib = load_boundary_store(root)
    sc = load_slot_store(root)
    pool = load_pool(root, "pool")
    pool_m = load_pool(root, "pool_minus_r01")
    arm = load_arm(root, ARM)
    if arm["split_identity"] != FOLD_A_SPLIT_IDENTITY:
        raise AuditError("the AGREE roster is not TRAIN Fold A 1,080")
    consumption = load_consumption(root, ARM)
    aa_consumption = load_consumption(root, AA)
    aa_boundary = {sid: r["boundary"] for sid, r in aa_consumption["rows"].items()}
    del aa_consumption
    queries = load_queries(root, sorted(arm["delivered"]))
    pool_vec = load_pool_vectors(root, {v["facet"] for v in pool["values"].values()})

    pool_pairs_present = set()
    for value in pool["values"].values():
        for name, _ in value["pairs"]:
            pool_pairs_present.add((value["intent"], name))

    rows, fold_a_utts = {}, set()
    for sid in sorted(arm["delivered"]):
        utt = gold_train["sample_to_utt"].get(sid)
        if utt is None:
            raise AuditError(f"{sid}: not a governed TRAIN recording")
        fold_a_utts.add(utt)
        gold = gold_train["utterances"][utt]
        d = arm["delivered"][sid]
        s = arm["per_sample"][sid]
        correct = bool(s["scenario_action_exact"] >= 0.5)
        if correct != (d["parsed"] and d["intent"] == gold["intent"]):
            raise AuditError(f"{sid}: parsed intent disagrees with the sealed official flag")
        view = row_entity_view(gold["entities"], d["entities"])
        for name, key in (("tp", "slot_f1_exact_tp"), ("fp", "slot_f1_exact_fp"), ("fn", "slot_f1_exact_fn")):
            if abs(sum(view["per_type"][name].values()) - s[key]) > 1e-9:
                raise AuditError(f"{sid}: derived {name} does not reproduce the sealed {key}")
        c = consumption["rows"][sid]
        ex_labels = [pool["values"][u]["intent"] for u in c["exemplars"]]
        tally = Counter(ex_labels)
        majority = sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] if tally else None
        rows[sid] = {
            "gold_intent": gold["intent"], "pred_intent": d["intent"], "intent_correct": correct,
            "gold_entities": gold["entities"], "pred_entities": d["entities"],
            "boundary": c["boundary"], "exemplars": c["exemplars"], "contracts": c["contracts"],
            "ex_gold": tally.get(gold["intent"], 0), "ex_pred": tally.get(d["intent"], 0),
            "ex_majority": majority, "pool_pairs_present": pool_pairs_present,
        }
    if fold_a_utts & set(pool["values"]):
        raise AuditError("the Fold A utterances overlap the released pool")

    geo = pool_geometry(pool, pool_vec["vectors"], gold_train)
    boundaries = audit_boundaries(ib, rows, queries, aa_boundary, gold_train, gold_devel, pool, geo)
    exemplars = audit_exemplars(pool, pool_m, gold_train, fold_a_utts, rows, geo)
    slots = audit_slots(sc, gold_train, fold_a_utts, rows, pool)
    conv = conversion(root)

    # ---- deficit ceilings
    n = len(rows)
    per_row_b = boundaries.pop("_per_row")
    wrong = [s for s, r in rows.items() if not r["intent_correct"]]
    gq = "general_quirky"
    sets = {
        "D1_boundary_key_not_delivering_gold": [s for s in wrong if not per_row_b[s]["gold_delivered"]],
        "D1a_of_which_centroid_key_delivers": [s for s in wrong if not per_row_b[s]["gold_delivered"]
                                               and per_row_b[s]["centroid_delivers_gold"]],
        "D2_delivered_both_no_confusable_exclusion": [s for s in wrong if per_row_b[s]["gold_delivered"]
                                                      and per_row_b[s]["pred_delivered"]
                                                      and not (per_row_b[s]["gold_card_excludes_pred"]
                                                               or per_row_b[s]["pred_card_excludes_gold"])],
        "D2b_delivered_both_exclusion_present": [s for s in wrong if per_row_b[s]["gold_delivered"]
                                                 and per_row_b[s]["pred_delivered"]
                                                 and (per_row_b[s]["gold_card_excludes_pred"]
                                                      or per_row_b[s]["pred_card_excludes_gold"])],
        "D3_general_quirky_gold_missed": [s for s in wrong if rows[s]["gold_intent"] == gq],
        "D4_zero_gold_exemplars_in_20": [s for s in wrong if rows[s]["ex_gold"] == 0],
        "D4b_gold_majority_exemplars_still_wrong": [s for s in wrong if rows[s]["ex_majority"] == rows[s]["gold_intent"]],
    }
    neighbours = geo["centroid_neighbours"]
    contrast = {}
    for label, members in (("all_wrong", wrong), ("D2", sets["D2_delivered_both_no_confusable_exclusion"])):
        entry = {"rows": len(members)}
        for k in (1, 3, 5, 8):
            entry[f"pred_in_gold_top{k}_centroid_neighbours"] = sum(
                rows[s]["pred_intent"] in neighbours.get(rows[s]["gold_intent"], [])[:k] for s in members)
        entry["distinct_pairs"] = len({(rows[s]["gold_intent"], rows[s]["pred_intent"]) for s in members})
        contrast[label] = entry
    boundaries["contrast_set_coverage_by_train_centroid_neighbours"] = contrast
    pool_count = Counter(v["intent"] for v in pool["values"].values())
    quartile = sorted(pool_count.values())[len(pool_count) // 4]
    d4 = sets["D4_zero_gold_exemplars_in_20"]
    d4_detail = {"gold_intent_pool_count_median": float(np.median([pool_count[rows[s]["gold_intent"]] for s in d4])) if d4 else 0.0,
                 "rows_whose_gold_intent_is_in_pool_bottom_quartile": sum(pool_count[rows[s]["gold_intent"]] <= quartile for s in d4),
                 "pool_bottom_quartile_cut": quartile,
                 "gold_intents": dict(sorted(Counter(rows[s]["gold_intent"] for s in d4).items(), key=lambda kv: (-kv[1], kv[0]))),
                 "of_which_general_quirky": sum(rows[s]["gold_intent"] == gq for s in d4),
                 "of_which_gold_boundary_delivered": sum(per_row_b[s]["gold_delivered"] for s in d4)}
    intent_ceilings = {"D4_detail": d4_detail}
    for key, members in sets.items():
        intent_ceilings[key] = {
            "overlaps": {other: len(set(members) & set(o)) for other, o in sorted(sets.items()) if other != key},
            "rows": len(members),
            "intent_pp_ceiling": pct(len(members), n),
            "slu_pp_ceiling_if_rows_fully_repaired": row_ceiling_slu(arm["per_sample"], set(members)),
            "rows_with_entity_error": sum(1 for s in members
                                          if arm["per_sample"][s]["slot_f1_exact_fp"] or arm["per_sample"][s]["slot_f1_exact_fn"]),
        }
    kp = conv["kprobe_centroid"]["rate"]
    cv = conv["conv_agree"]["rate"]
    intent_ceilings["D1a_of_which_centroid_key_delivers"]["intent_pp_expected_at_kprobe_rate"] = rnd(
        intent_ceilings["D1a_of_which_centroid_key_delivers"]["intent_pp_ceiling"] * kp, 4)
    for key in ("D2_delivered_both_no_confusable_exclusion", "D3_general_quirky_gold_missed",
                "D4_zero_gold_exemplars_in_20"):
        intent_ceilings[key]["intent_pp_at_conv_rate_if_supply_fixed"] = rnd(
            intent_ceilings[key]["intent_pp_ceiling"] * cv, 4)
    repair_sets = slots.pop("_repair_sets")
    entity_ceilings = {k: span_and_slu_ceiling(arm["per_sample"], {s: tuple(v) for s, v in d.items()})
                       for k, d in sorted(repair_sets.items())}

    tokens = json.loads((arm_dir(root, ARM) / f"{ARM['run_id']}.generation-manifest.json").read_text(encoding="utf-8"))["cost"]
    cost = {"calls": tokens["calls_used"], "prompt_tokens_total": tokens["prompt_tokens_total"],
            "prompt_tokens_per_call": rnd(tokens["prompt_tokens_total"] / tokens["calls_used"], 1),
            "prompt_tokens_per_row": rnd(tokens["prompt_tokens_total"] / n, 1)}

    for card in sc["cards"].values():
        card.pop("_lower", None)
    return {
        "schema": SCHEMA, "read_id": READ_ID, "recipe": RECIPE,
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "scorer": 0, "asr": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "inputs": {
            **{k: {"relpath": v[0], "sha256": v[1]} for k, v in sorted(PINS.items())},
            "agree_scores": {"relpath": str((arm_dir(root, ARM) / f"{ARM['run_id']}.scores.json").relative_to(root)), "sha256": arm["scores_sha256"]},
            "agree_outputs": {"relpath": str((arm_dir(root, ARM) / f"{ARM['run_id']}.outputs.jsonl").relative_to(root)), "sha256": arm["outputs_sha256"]},
            "agree_phases": {"relpath": consumption["relpath"], "sha256": consumption["sha256"]},
            "conversion_reads": conv,
        },
        "arm": {"run_id": ARM["run_id"], "rows": n, "fold_a_utterances": len(fold_a_utts),
                "split_identity": arm["split_identity"],
                "official_intent_accuracy": arm["official"]["intent_accuracy"],
                "official_slu_f1": arm["official"]["slu_f1"], "official_span_f1": arm["official"]["span_f1"],
                "pooled_slu_f1_reproduced": rnd(arm["pooled_slu_f1"] * arm["official"]["scale"], 6),
                "intent_wrong_rows": len(wrong),
                "rows_with_entity_error": sum(1 for s in arm["per_sample"].values()
                                              if s["slot_f1_exact_fp"] or s["slot_f1_exact_fn"]),
                "prompt_cost": cost},
        "boundaries": boundaries,
        "exemplars": exemplars,
        "slots": slots,
        "ceilings": {"intent": intent_ceilings, "entity": entity_ceilings,
                     "conversion_rates": {"conv_agree": cv, "kprobe_centroid": kp}},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", DEFAULT_DATA_ROOT))
    parser.add_argument("--out-dir", default=None,
                        help="default: <data-root>/" + ANALYSIS_DIR)
    args = parser.parse_args(argv)
    root = Path(args.data_root)
    out = Path(args.out_dir) if args.out_dir else root / ANALYSIS_DIR
    payload = measure(Path(args.lock), root)
    payload["driver"] = {"relpath": "scripts/analysis/" + _DRIVER.name, "sha256": digest(_DRIVER)}
    out.mkdir(parents=True, exist_ok=True)
    body = json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=True) + "\n"
    target = out / "audit-v1.json"
    target.write_text(body, encoding="utf-8")
    stamp = {"read_id": READ_ID, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "audit_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
             "driver_sha256": payload["driver"]["sha256"]}
    (out / "run-stamp-v1.json").write_text(json.dumps(stamp, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(stamp, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
