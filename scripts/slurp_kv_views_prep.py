#!/usr/bin/env python3
"""Model-free preparation of the SLURP slot knowledge-view family (KV).

Exposure row ``SAEA-SLURP-MF-KV-VIEWS-PREP-V1``, profile ``model-free-check``.
**Zero frozen-core, tokeniser, embedder, retriever, judge, network, GPU,
audio-decode and paid-API contacts.** No server is started, no model is
loaded, no waveform is decoded and no tokeniser is called: every token figure
is MF-10's STATED PROXY (whitespace tokens x 1.3, rounded up) and is labelled
as such wherever it appears.

What it does, in order.

1. **Pins the slot-class table.** MF-10's committed ``type-classes.json`` is
   re-hashed against that receipt's own ``MANIFEST.sha256`` and re-emitted as
   ``docs/receipts/knowledge/slurp-kv-slot-type-classes-v1.json``, the
   artifact ``rails.phase_material._kv_class_table`` loads by sha256. A
   flight therefore never recomputes MF-10's classification -- whose coverage
   statistic is itself read out of MF-9's receipt -- from whatever happens to
   be on disk.
2. **Renders every block the family can send**: 60 per-intent blocks plus the
   full-schema fallback, for each of the four views, arm and twin. Prices each
   on the proxy and measures the twin's character-level volume match.
3. **Runs the containment folds** the preregistration reports:
   * **C1** -- every view payload against the arm's own DIRECTIVE
     (``configs/probes/slurp_phase_slots.txt``). Every KV arm sends the same
     control bytes; the view lives only in the per-sample block. Must be 0.
   * **C2** -- every protected payload of the BOUND TRAIN knowledge snapshot
     (``size-full-label-prior-speaker``, the one KC-S1b's fragment already
     binds) against the directive and against all 61 renderable blocks, the
     fold ``rails.runner._assert_agent_control_excludes_knowledge_payloads``
     applies at contact time. Must be 0.
   * **C3** -- the MF-10 cross-channel number, reported and not hidden: how
     many of a view's own payloads occur inside the instruction that carries
     them. It is 100 % by construction for KV-1/2/3, because those views ARE
     the instruction-side block; it is the number KU-S3 (KV-4) has to keep at
     0, because its values are traced supply.
4. **Measures the exemplar material** KV-3 draws on: TRAIN utterances per
   intent, the share of each intent's listed types the k = 3 cover reaches,
   and the same for the twin's donor intent.

Reads: the governed ``train.jsonl`` (TRAIN only, through the governed
loaders); the frozen TRAIN knowledge snapshot named above; the committed
probe template; MF-10's committed receipt. **No devel or test record is
loaded, hashed or scored, and no gold annotation is opened.**

Usage::

    python scripts/slurp_kv_views_prep.py --out-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

ROW_ID = "SAEA-SLURP-MF-KV-VIEWS-PREP-V1"
MF10_RECEIPT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-08-mf10-slot-vocab-cards-normalized-slu"
)
CLASS_ARTIFACT_RELPATH = "docs/receipts/knowledge/slurp-kv-slot-type-classes-v1.json"
DIRECTIVE_RELPATH = "configs/probes/slurp_phase_slots.txt"
BOUND_SNAPSHOT_RELPATH = (
    "knowledge/slurp/saea-kb-distmodel-v1/size-full-label-prior-speaker/snapshot.json"
)
BOUND_SNAPSHOT_SHA256 = (
    "07f94807d173b2f2bdda9dcd95b21354e018234a208a76683d0ca4989d9ffa65"
)
#: The same eight-character floor ``rails.runner`` applies.
CONTAINMENT_MIN_LENGTH = 8


def contacts_block() -> dict[str, object]:
    return {
        "frozen_core_calls": 0,
        "tokenizer_calls": 0,
        "embedding_calls": 0,
        "retriever_calls": 0,
        "judge_calls": 0,
        "network_calls": 0,
        "audio_decode_calls": 0,
        "gpu_hours": 0.0,
        "paid_api_spend": 0.0,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "<unset>"),
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def load_mf10_classes() -> tuple[dict[str, str], dict[str, object]]:
    """MF-10's operative slot classes, verified against its own manifest."""

    manifest = (MF10_RECEIPT_DIR / "MANIFEST.sha256").read_text(encoding="utf-8")
    expected = {}
    for line in manifest.splitlines():
        if not line.strip():
            continue
        digest, name = line.split(" *", 1)
        expected[name.strip()] = digest.strip()
    path = MF10_RECEIPT_DIR / "type-classes.json"
    measured = sha256_file(path)
    if measured != expected.get("type-classes.json"):
        raise SystemExit(
            f"MF-10 type-classes.json hashes to {measured}, not the "
            f"{expected.get('type-classes.json')} its own MANIFEST.sha256 names"
        )
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("per_entity_type")
    if not isinstance(rows, list) or not rows:
        raise SystemExit(
            "MF-10 type-classes.json carries no 'per_entity_type' list; keys are "
            f"{sorted(document)}"
        )
    classes = {
        str(row["entity_type"]): str(row["slot_class"])
        for row in rows
        if isinstance(row, dict) and "entity_type" in row and "slot_class" in row
    }
    if not classes:
        raise SystemExit("MF-10 type-classes.json yielded no (type -> class) pair")
    return classes, {
        "path": str(path.relative_to(REPO)),
        "sha256": measured,
        "rule": (document.get("rules") or {}).get("operative"),
        "class_counts": document.get("class_counts"),
        "types": len(classes),
    }


def write_class_artifact(classes: Mapping[str, str], provenance: Mapping[str, object]) -> dict[str, object]:
    document = {
        "schema": "saea-slurp-kv-slot-type-classes-v1",
        "row_id": ROW_ID,
        "what_this_is": (
            "MF-10's operative CLOSED/MIXED/OPEN slot-type classification, re-emitted "
            "as the hash-pinned artifact rails.phase_material._kv_class_table loads. "
            "The classification is NOT recomputed here: it is copied out of MF-10's "
            "committed type-classes.json after that file is re-hashed against its own "
            "MANIFEST.sha256, so the KV family and MF-10 can never drift."
        ),
        "source": dict(provenance),
        "slot_class_by_type": dict(sorted(classes.items())),
    }
    path = REPO / CLASS_ARTIFACT_RELPATH
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8")
    path.write_bytes(raw + b"\n")
    return {
        "relpath": CLASS_ARTIFACT_RELPATH,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "closed": sorted(name for name, value in classes.items() if value.startswith("CLOSED")),
    }


def protected_payloads(snapshot_path: Path) -> tuple[tuple[str, ...], str]:
    """``rails.runner._protected_knowledge_material``'s own tuple, and the
    snapshot's CONTENT hash.

    Loaded through ``rails.knowledge.KnowledgeSnapshot.from_frozen_json`` and
    reduced by ``rails.runner._protected_knowledge_material`` itself rather
    than by a local re-implementation, so the fold this pass runs is the fold
    the flight runs. The identity the fragment pins is the snapshot's
    ``content_hash()``, NOT the file's sha256 -- the two are different
    quantities and ``core.flight.FlightRuntime._load_knowledge_snapshot``
    checks the former.
    """

    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
    from speech_aware_evidence_acquisition.rails.runner import (
        _protected_knowledge_material,
    )

    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(snapshot_path.read_text(encoding="utf-8"))
    )
    return _protected_knowledge_material(snapshot), snapshot.content_hash()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    from speech_aware_evidence_acquisition.analysis.slurp_slot_vocabulary import (
        SLOT_CLASS_CLOSED,
        build_vocabulary_card,
        containment_collisions,
        derange_card_mapping,
        token_proxy,
        twin_pool_types,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.slurp import (
        load_slurp_intent_slot_schema,
        load_slurp_train_material,
        render_slurp_intent_slot_schema,
    )
    from speech_aware_evidence_acquisition.rails.slurp_knowledge_views import (
        FEWSHOT_K,
        FEWSHOT_SEED,
        KV_CELL_IDS,
        KV_VIEWS,
        KV_VIEW_CARDS,
        KV_VIEW_DESCRIPTIONS,
        KV_VIEW_EXAMPLES_FREE,
        KV_VIEW_FEWSHOT,
        Exemplar,
        build_type_description,
        compose_view,
        derange_description_mapping,
        donor_intent_mapping,
        render_examples_free_block,
        select_exemplars,
        view_payloads,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    classes, class_provenance = load_mf10_classes()
    artifact = write_class_artifact(classes, class_provenance)

    lock_path = umbrella_lock_path()
    lock = load_lock(lock_path)
    root = Path(data_root())
    schema = load_slurp_intent_slot_schema(lock, root)
    train = load_slurp_train_material(lock, root)

    intents = tuple(schema.intent_ids)
    block_types = {i: tuple(schema.intents[i].entity_types) for i in intents}
    utterances = {i: schema.intents[i].n for i in intents}
    mentions = {i: schema.intents[i].mentions for i in intents}
    type_tables = {i: schema.intents[i].types for i in intents}
    fallback_types = tuple(sorted({n for t in block_types.values() for n in t}))

    forms: dict[str, Counter] = defaultdict(Counter)
    pool_by_intent: dict[str, list[Exemplar]] = defaultdict(list)
    whole_pool: list[Exemplar] = []
    for utterance in train:
        slots = []
        for entity in utterance.entities:
            name = str(entity.type).strip()
            filler = str(entity.filler).strip()
            if name and filler:
                forms[name][filler] += 1
                slots.append((name, filler))
        exemplar = Exemplar(
            utterance_id=utterance.utterance_id,
            sentence=utterance.sentence.strip(),
            slots=tuple(slots),
        )
        pool_by_intent[f"{utterance.scenario}_{utterance.action}"].append(exemplar)
        whole_pool.append(exemplar)

    cards = {
        name: build_vocabulary_card(name, dict(table))
        for name, table in sorted(forms.items())
        if classes.get(name) == SLOT_CLASS_CLOSED
    }
    descriptions = {
        name: build_type_description(name, dict(table), slot_class=classes[name])
        for name, table in sorted(forms.items())
        if name in classes
    }
    card_remap = derange_card_mapping(block_types, cards)
    description_remap = derange_description_mapping(block_types, descriptions)
    donors = donor_intent_mapping(
        {
            scenario: sorted({i for i in intents if i.startswith(f"{scenario}_")})
            for scenario in sorted({i.split("_", 1)[0] for i in intents})
        }
    )

    schema_by_intent = {
        i: render_examples_free_block(
            type_tables,
            intents=(i,),
            utterances=utterances,
            mentions=mentions,
            min_share=schema.min_share,
        )
        for i in intents
    }
    fallback_schema = render_examples_free_block(
        type_tables,
        intents=intents,
        utterances=utterances,
        mentions=mentions,
        min_share=schema.min_share,
    )
    admitted_by_intent = {
        i: render_slurp_intent_slot_schema(schema, intents=(i,)) for i in intents
    }
    admitted_fallback = render_slurp_intent_slot_schema(schema)

    exemplars_arm = {
        i: select_exemplars(pool_by_intent.get(i, ()), block_types[i], k=FEWSHOT_K, seed=FEWSHOT_SEED)
        for i in intents
    }
    exemplars_twin = {
        i: select_exemplars(
            pool_by_intent.get(donors[i], ()), block_types[i], k=FEWSHOT_K, seed=FEWSHOT_SEED
        )
        for i in intents
    }
    fallback_exemplars = select_exemplars(
        whole_pool, fallback_types, k=FEWSHOT_K, seed=FEWSHOT_SEED
    )

    def material(view: str, intent: str | None, twin: bool) -> dict[str, object]:
        types = fallback_types if intent is None else block_types[intent]
        if view == KV_VIEW_CARDS:
            remap = card_remap.get(intent, {}) if (twin and intent) else {}
            return {
                "cards": [
                    cards[remap.get(n, n)]
                    for n in types
                    if n in cards and remap.get(n, n) in cards
                ]
            }
        if view == KV_VIEW_DESCRIPTIONS:
            remap = description_remap.get(intent, {}) if (twin and intent) else {}
            return {
                "descriptions": [
                    descriptions[remap.get(n, n)]
                    for n in types
                    if n in descriptions and remap.get(n, n) in descriptions
                ]
            }
        if view == KV_VIEW_FEWSHOT:
            if intent is None:
                return {"exemplars": list(fallback_exemplars)}
            return {
                "exemplars": list(
                    (exemplars_twin if twin else exemplars_arm).get(intent, ())
                )
            }
        return {}

    rendered: dict[tuple[str, bool], dict[str | None, object]] = {}
    for view in KV_VIEWS:
        for twin in (False, True):
            if view == KV_VIEW_EXAMPLES_FREE and twin:
                continue
            per_intent: dict[str | None, object] = {}
            for intent in intents:
                stuff = material(view, intent, twin)
                if view != KV_VIEW_EXAMPLES_FREE and not any(stuff.values()):
                    # An intent whose block lists no carded/described type at
                    # all carries the base block alone; the view is absent by
                    # construction and the row count says so.
                    per_intent[intent] = compose_view(
                        intent=intent,
                        view=KV_VIEW_EXAMPLES_FREE,
                        twin=False,
                        schema_text=schema_by_intent[intent],
                    )
                    continue
                per_intent[intent] = compose_view(
                    intent=intent,
                    view=view,
                    twin=twin,
                    schema_text=schema_by_intent[intent],
                    **stuff,
                )
            per_intent[None] = compose_view(
                intent=None,
                view=view,
                twin=twin,
                schema_text=fallback_schema,
                **material(view, None, twin),
            )
            rendered[(view, twin)] = per_intent

    directive = (REPO / DIRECTIVE_RELPATH).read_text(encoding="utf-8")
    snapshot_path = root / BOUND_SNAPSHOT_RELPATH
    payloads, snapshot_content_hash = protected_payloads(snapshot_path)
    if snapshot_content_hash != BOUND_SNAPSHOT_SHA256:
        raise SystemExit(
            f"bound snapshot {BOUND_SNAPSHOT_RELPATH} has content hash "
            f"{snapshot_content_hash}, not the {BOUND_SNAPSHOT_SHA256} the KC-S1b "
            "fragment pins"
        )

    # C2: the flight-enforced fold, over every surface a KV arm's instruction
    # can carry EXCEPT the sealed predecessor state (which is a DEV-side model
    # output this row does not open; KC-S1b's own committed number for that
    # half is 78 of 1,000 and is cited, never recomputed).
    c2: dict[str, object] = {}
    for (view, twin), blocks in sorted(rendered.items(), key=lambda item: (item[0][0], item[0][1])):
        hits = 0
        examples: list[str] = []
        for key, block in blocks.items():
            instruction = f"{directive}\n\n{block.text}".casefold()
            found = [text for text in payloads if text in instruction]
            if found:
                hits += 1
                examples.extend(found[:3])
        c2[f"{view}{'-twin' if twin else ''}"] = {
            "blocks_checked": len(blocks),
            "blocks_colliding": hits,
            "examples": sorted(set(examples))[:5],
        }
    # The admitted KC-S1b block, measured through the SAME fold, as the anchor.
    c2["kc-s1b-admitted-block"] = {
        "blocks_checked": len(intents) + 1,
        "blocks_colliding": sum(
            1
            for text in (*admitted_by_intent.values(), admitted_fallback)
            if any(payload in f"{directive}\n\n{text}".casefold() for payload in payloads)
        ),
        "examples": [],
    }

    # C1 and C3.
    c1: dict[str, object] = {}
    c3: dict[str, object] = {}
    for (view, twin), blocks in sorted(rendered.items(), key=lambda item: (item[0][0], item[0][1])):
        name = f"{view}{'-twin' if twin else ''}"
        directive_hits = 0
        self_hits = 0
        payload_total = 0
        for block in blocks.values():
            items = view_payloads(block)
            payload_total += len(items)
            directive_hits += len(containment_collisions(items, directive))
            self_hits += len(
                containment_collisions(items, f"{directive}\n\n{block.text}")
            )
        c1[name] = {"payloads": payload_total, "inside_the_directive": directive_hits}
        c3[name] = {
            "payloads": payload_total,
            "inside_the_instruction_that_carries_them": self_hits,
        }

    # Cost.
    cost: dict[str, object] = {}
    for (view, twin), blocks in sorted(rendered.items(), key=lambda item: (item[0][0], item[0][1])):
        name = f"{view}{'-twin' if twin else ''}"
        per_intent = [blocks[i] for i in intents]
        proxies = sorted(block.token_proxy for block in per_intent)
        view_proxies = sorted(block.view_token_proxy for block in per_intent)
        worst = max(per_intent, key=lambda block: block.token_proxy)
        cost[name] = {
            "cell": KV_CELL_IDS[view],
            "intents": len(per_intent),
            "block_token_proxy_min": proxies[0],
            "block_token_proxy_median": proxies[len(proxies) // 2],
            "block_token_proxy_max": proxies[-1],
            "view_token_proxy_min": view_proxies[0],
            "view_token_proxy_median": view_proxies[len(view_proxies) // 2],
            "view_token_proxy_max": view_proxies[-1],
            "worst_intent": worst.intent,
            "intents_carrying_no_view_block": sum(
                1 for block in per_intent if not block.view_text
            ),
            "fallback_block_token_proxy": blocks[None].token_proxy,
        }
    cost["kc-s1b-admitted-block"] = {
        "cell": "KC-S1b",
        "intents": len(intents),
        "block_token_proxy_min": min(token_proxy(t) for t in admitted_by_intent.values()),
        "block_token_proxy_median": statistics.median(
            sorted(token_proxy(t) for t in admitted_by_intent.values())
        ),
        "block_token_proxy_max": max(token_proxy(t) for t in admitted_by_intent.values()),
        "fallback_block_token_proxy": token_proxy(admitted_fallback),
    }

    # Twin volume match, per intent, character exact.
    twin_match: dict[str, object] = {}
    for view in (KV_VIEW_DESCRIPTIONS, KV_VIEW_CARDS, KV_VIEW_FEWSHOT):
        arm = rendered[(view, False)]
        twin = rendered[(view, True)]
        deltas = []
        exact = 0
        rotating = 0
        for intent in intents:
            a, b = arm[intent], twin[intent]
            if not a.view_text and not b.view_text:
                continue
            rotating += 1
            delta = len(b.view_text) - len(a.view_text)
            deltas.append(delta)
            exact += int(delta == 0)
        pooled = sorted(
            intent
            for intent in intents
            if len(
                {
                    name
                    for name in block_types[intent]
                    if name in (cards if view == KV_VIEW_CARDS else descriptions)
                }
            )
            == 1
        ) if view in (KV_VIEW_CARDS, KV_VIEW_DESCRIPTIONS) else []
        twin_match[view] = {
            "matched_by": (
                "construction (per-intent rotation)"
                if view in (KV_VIEW_CARDS, KV_VIEW_DESCRIPTIONS)
                else "measurement (a donor intent's sentences are other sentences)"
            ),
            "intents_with_a_view_block": rotating,
            "intents_matching_to_the_character": exact,
            "intents_that_cannot_rotate_in_place": len(pooled),
            "pooled_intents": pooled,
            "abs_char_delta_max": max((abs(d) for d in deltas), default=0),
            "abs_char_delta_mean": (
                round(sum(abs(d) for d in deltas) / len(deltas), 3) if deltas else 0.0
            ),
            "abs_char_delta_max_over_rotating_intents": max(
                (
                    abs(len(twin[i].view_text) - len(arm[i].view_text))
                    for i in intents
                    if i not in set(pooled) and (arm[i].view_text or twin[i].view_text)
                ),
                default=0,
            ),
            "pooled_types": (
                list(twin_pool_types(block_types, cards))
                if view == KV_VIEW_CARDS
                else (
                    list(twin_pool_types(block_types, descriptions))
                    if view == KV_VIEW_DESCRIPTIONS
                    else None
                )
            ),
        }

    # KV-3 material.
    covers = []
    twin_covers = []
    for intent in intents:
        listed = set(block_types[intent])
        if not listed:
            continue
        covered = {n for e in exemplars_arm[intent] for n, _f in e.slots} & listed
        covers.append(len(covered) / len(listed))
        twin_covered = {n for e in exemplars_twin[intent] for n, _f in e.slots} & listed
        twin_covers.append(len(twin_covered) / len(listed))
    pool_sizes = sorted(len(pool_by_intent.get(i, ())) for i in intents)
    exemplar_material = {
        "k": FEWSHOT_K,
        "seed": FEWSHOT_SEED,
        "train_utterances_per_intent_min": pool_sizes[0],
        "train_utterances_per_intent_median": pool_sizes[len(pool_sizes) // 2],
        "train_utterances_per_intent_max": pool_sizes[-1],
        "intents_with_fewer_than_k": sum(1 for n in pool_sizes if n < FEWSHOT_K),
        "listed_type_coverage_mean_arm": round(sum(covers) / len(covers), 4),
        "listed_type_coverage_full_arm": sum(1 for c in covers if c >= 1.0),
        "listed_type_coverage_mean_twin": round(sum(twin_covers) / len(twin_covers), 4),
        "listed_type_coverage_full_twin": sum(1 for c in twin_covers if c >= 1.0),
        "intents_scored": len(covers),
        "donors_crossing_a_scenario": sorted(
            intent
            for intent in intents
            if intent.split("_", 1)[0] != donors[intent].split("_", 1)[0]
        ),
        "donor_never_self_donates": all(donors[i] != i for i in intents),
    }

    document = {
        "schema": "saea-slurp-kv-views-prep-v1",
        "row_id": ROW_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contacts": contacts_block(),
        "token_cost_basis": (
            "STATED PROXY: whitespace tokens x 1.3, rounded up "
            "(analysis.slurp_slot_vocabulary.token_proxy). No tokenizer was called. A "
            "cell that flies a view measures its own envelope through the serving "
            "/apply-template + /tokenize seam, as KC-S1b did."
        ),
        "sources": {
            "umbrella_lock": str(lock_path),
            "train_material": "data.slurp.load_slurp_train_material (TRAIN only)",
            "intent_slot_schema": {
                "schema_id": schema.schema_id,
                "source_split": schema.source_split,
                "source_identity_hash": schema.source_identity_hash,
                "utterance_count": schema.utterance_count,
                "min_share": schema.min_share,
                "content_hash": schema.content_hash(),
                "intents": len(intents),
            },
            "mf10_type_classes": class_provenance,
            "directive": {
                "relpath": DIRECTIVE_RELPATH,
                "sha256": sha256_file(REPO / DIRECTIVE_RELPATH),
            },
            "bound_snapshot": {
                "relpath": BOUND_SNAPSHOT_RELPATH,
                "declared_content_hash": BOUND_SNAPSHOT_SHA256,
                "measured_content_hash": snapshot_content_hash,
                "file_sha256": sha256_file(snapshot_path),
                "protected_payloads": len(payloads),
                "note": (
                    "The identity a fragment pins is the snapshot's content_hash(), "
                    "which core.flight.FlightRuntime._load_knowledge_snapshot checks; "
                    "the file sha256 is recorded beside it and is a different quantity."
                ),
            },
        },
        "class_artifact": artifact,
        "cost": cost,
        "twin_volume_match": twin_match,
        "containment": {
            "c1_view_payloads_inside_the_arms_directive": c1,
            "c2_bound_snapshot_payloads_inside_the_instruction": c2,
            "c2_state_half_cited_not_recomputed": {
                "source": "KC-S1b deviation 1, restated in the KU-S3 preregistration",
                "facet_representations_vs_the_1000_sealed_states": 78,
                "value_contents_vs_the_1000_sealed_states": 0,
                "note": (
                    "This row opens no sealed DEV output. The KV fragments bind the same "
                    "size-full-label-prior-speaker snapshot KC-S1b bound, whose content "
                    "dimension is excluded, so the 78 belongs to a snapshot no KV cell "
                    "binds and is quoted only to say which half of the instruction was "
                    "not re-measured here."
                ),
            },
            "c3_cross_channel_reported_not_hidden": c3,
        },
        "exemplar_material": exemplar_material,
        "mf10_identity_anchors": {
            "what_this_is": (
                "MF-10's own published card figures, RE-DERIVED here from the same TRAIN "
                "bytes through the same library. They must reproduce exactly, or this "
                "family is not built on the measurement it cites."
            ),
            "closed_types": {
                "published": 18,
                "reproduced": len(cards),
            },
            "card_surface_forms": {
                "published": 842,
                "reproduced": sum(len(card.forms) for card in cards.values()),
            },
            "per_intent_card_token_proxy_median": {
                "published": 1432,
                "reproduced": cost["cards"]["view_token_proxy_median"],
            },
            "worst_intent_card_token_proxy": {
                "published": 2010,
                "published_intent": "social_query",
                "reproduced": cost["cards"]["view_token_proxy_max"],
                "reproduced_intent": cost["cards"]["worst_intent"],
            },
            "intents_rotating_in_place_at_zero_delta": {
                "published": 39,
                "reproduced": twin_match[KV_VIEW_CARDS]["intents_matching_to_the_character"],
            },
            "intents_that_cannot_rotate_in_place": {
                "published": 14,
                "reproduced": twin_match[KV_VIEW_CARDS]["intents_that_cannot_rotate_in_place"],
            },
        },
        "worked_examples": {
            view: {
                "intent": "alarm_set",
                "arm": rendered[(view, False)]["alarm_set"].text,
                "twin": (
                    rendered[(view, True)]["alarm_set"].text
                    if (view, True) in rendered
                    else None
                ),
            }
            for view in (KV_VIEW_EXAMPLES_FREE, KV_VIEW_DESCRIPTIONS, KV_VIEW_CARDS, KV_VIEW_FEWSHOT)
            if "alarm_set" in rendered[(view, False)]
        },
        "kc_s1b_admitted_block_for_alarm_set": admitted_by_intent.get("alarm_set"),
    }
    (out_dir / "views.json").write_text(
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest_lines = [
        f"{sha256_file(path)} *{path.name}"
        for path in sorted(out_dir.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (out_dir / "MANIFEST.sha256").write_text(
        chr(10).join(manifest_lines) + chr(10), encoding="utf-8"
    )
    print(json.dumps({"cost": cost, "twin": twin_match, "exemplars": exemplar_material,
                      "c1": c1, "c2": c2, "c3": c3}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
