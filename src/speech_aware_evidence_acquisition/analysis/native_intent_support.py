"""Measure initial intent-value support from verified C0 request evidence.

Consume existing verified native stage pairs. Never infer supply from retrieval
availability, later requests, answer text, or a union of candidates.
"""

from __future__ import annotations

from collections.abc import Mapping
import re

from ..rails.hashing import content_hash
from ..rails.knowledge import QueryState

SUPPORT_SCHEMA = "saea-initial-intent-support-projection-v1"
SUPPORT_POLICY = "initial-perception-request-intent-value-id-suffix-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class NativeIntentSupportError(ValueError):
    """The exact C0 request or declared intent-value mapping is unavailable."""


def validate_initial_intent_support_spec(specification):
    """Require an explicit versioned mapping, never guess label names from prose."""
    if (
        not isinstance(specification, Mapping)
        or set(specification) != {"schema", "policy_id", "store_id", "value_id_prefix"}
        or specification.get("schema") != SUPPORT_SCHEMA
        or specification.get("policy_id") != SUPPORT_POLICY
        or any(not isinstance(specification.get(k), str) or not specification[k].strip()
               for k in ("store_id", "value_id_prefix"))
        or "::" in specification["store_id"]
        or "::" in specification["value_id_prefix"]
    ):
        raise NativeIntentSupportError("initial intent support specification is invalid")
    return dict(specification)


def _ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def build_initial_intent_support_diagnostics(
    *, source, stage_pairs, reference_rows, legal_candidate_ids, specification,
):
    """Join actual C0 evidence to offline references; export flags and hashes only."""
    spec = validate_initial_intent_support_spec(specification)
    pairs, references = tuple(stage_pairs), tuple(reference_rows)
    ids = tuple(source.sample_ids)
    if (
        not ids or len(ids) != len(set(ids))
        or tuple(pair.sample_id for pair in pairs) != ids
        or tuple(row.sample_id for row in references) != ids
        or any(row.intent_id not in legal_candidate_ids for row in references)
    ):
        raise NativeIntentSupportError("support diagnostic requires the exact ordered cohort")
    stores = source.composed.values.get("knowledge_stores")
    store = stores.get(spec["store_id"]) if isinstance(stores, Mapping) else None
    if not isinstance(store, Mapping) or store.get("store_role") != "intent-boundaries":
        raise NativeIntentSupportError("support store is not a declared intent-boundaries store")
    routes = store.get("phase_supply")
    route = routes.get("perception") if isinstance(routes, Mapping) else None
    if not isinstance(route, Mapping) or route.get("expose_facets", False) is not False:
        raise NativeIntentSupportError("support store lacks a value-only Perception route")
    pins = {}
    for name in ("snapshot", "release"):
        pin = store.get(name)
        sha = pin.get("sha256") if isinstance(pin, Mapping) else None
        if not isinstance(sha, str) or _SHA256.fullmatch(sha) is None:
            raise NativeIntentSupportError("support store lacks its frozen source pins")
        pins[f"{name}_sha256"] = sha
    traces = source.bundle.trace_records
    store_prefix = spec["store_id"] + "::"
    value_prefix = store_prefix + spec["value_id_prefix"]
    samples = []
    counts = dict.fromkeys((
        "supplied_and_covered", "supplied_but_missed",
        "not_supplied_but_covered", "neither",
    ), 0)
    unavailable = 0
    for pair, reference in zip(pairs, references, strict=True):
        stage = pair.c0
        if stage is None:
            unavailable += 1
            samples.append({
                "sample_id": pair.sample_id,
                "support_available": False,
                "request_sha256": None,
                "candidate_set_sha256": None,
                "supplied_intent_value_ids_sha256": None,
                "intent_value_count": None,
                "gold_intent_value_supplied": None,
                "c0_gold_covered": None,
                "cell": None,
            })
            continue
        record = traces.get(stage.request_id + "/request")
        payload = record.get("payload") if isinstance(record, Mapping) else None
        if (
            not isinstance(payload, Mapping)
            or payload.get("sample_id") != pair.sample_id
            or payload.get("request_id") != stage.request_id
            or record.get("payload_sha256") != stage.request_sha256
            or content_hash(payload) != stage.request_sha256
        ):
            raise NativeIntentSupportError("C0 request payload differs from its verified contact")
        base = f"{pair.sample_id}/{source.composed.values['policy']}/agent-loop"
        try:
            org = traces[base + "/org"]
            supply = traces[base + "/supply"]
            runtime = traces[base + "/runtime-use"]
            initial = source.phase_results[pair.sample_id]["initial_query_state"]
            query = QueryState.from_json(initial)
            snapshot = org["org_knowledge_snapshot_sha256"]
            if (
                initial != org["org_initial_query_state"]
                or org["org_controller_policy_id"] != source.composed.values["policy"]
                or query.query_sample_id != pair.sample_id
                or query.content_hash() != stage.query_state_sha256
                or runtime["use_initial_query_state_sha256"] != stage.query_state_sha256
                or query.visible_facet_ids
                or supply["supply_bootstrap_value_ids"] != list(query.retrieved_value_ids)
                or not isinstance(snapshot, str) or _SHA256.fullmatch(snapshot) is None
            ):
                raise ValueError("initial state and supply traces disagree")
        except (KeyError, TypeError, ValueError) as error:
            raise NativeIntentSupportError(f"C0 bootstrap source mismatch: {error}") from error
        evidence = payload.get("supplied_evidence")
        if not isinstance(evidence, list):
            raise NativeIntentSupportError("C0 request lacks explicit supplied evidence")
        seen, selected_ids, intents = set(), [], set()
        for block in evidence:
            if not isinstance(block, Mapping):
                raise NativeIntentSupportError("C0 evidence block is malformed")
            evidence_id = block.get("evidence_id")
            if (
                not isinstance(evidence_id, str) or not evidence_id
                or evidence_id in seen
                or not isinstance(block.get("content"), str) or not block["content"].strip()
                or block.get("knowledge_role") != "value"
                or block.get("source_uri") != f"knowledge-snapshot://{snapshot}/{evidence_id}"
            ):
                raise NativeIntentSupportError("C0 evidence IDs/content are invalid or duplicate")
            seen.add(evidence_id)
            if not evidence_id.startswith(store_prefix):
                continue
            if not evidence_id.startswith(value_prefix):
                raise NativeIntentSupportError("intent store contains an unmapped evidence ID")
            intent_id = evidence_id[len(value_prefix):]
            if intent_id not in legal_candidate_ids:
                raise NativeIntentSupportError("intent value ID does not map to a legal intent")
            selected_ids.append(evidence_id)
            intents.add(intent_id)
        if [block["evidence_id"] for block in evidence] != list(query.retrieved_value_ids):
            raise NativeIntentSupportError("actual C0 supply differs from ordered bootstrap values")
        supported = reference.intent_id in intents
        covered = reference.intent_id in stage.candidate_ids
        cell = (
            "supplied_and_covered" if supported and covered else
            "supplied_but_missed" if supported else
            "not_supplied_but_covered" if covered else "neither"
        )
        counts[cell] += 1
        samples.append({
            "sample_id": pair.sample_id,
            "request_sha256": stage.request_sha256,
            "candidate_set_sha256": stage.candidate_set_sha256,
            "supplied_intent_value_ids_sha256": content_hash(selected_ids),
            "intent_value_count": len(selected_ids),
            "gold_intent_value_supplied": supported,
            "c0_gold_covered": covered,
            "cell": cell,
        })
    supplied = counts["supplied_and_covered"] + counts["supplied_but_missed"]
    return {
        "schema": "saea-initial-intent-support-diagnostics-v1",
        "projection": spec,
        "store_source": pins,
        "support_availability": {
            "available_count": len(ids) - unavailable,
            "unavailable_count": unavailable,
        },
        "semantics": {
            "support": "A nonempty own-intent value block is present in the actual initial Perception request.",
            "support_scope": "Own-intent card presence only; cross-intent contrasts in other cards are not counted.",
            "mapping": "Declared store-local value ID suffix; no label inferred from content.",
            "semantic_use_proven": False,
            "retrieval_availability_is_supply": False,
            "later_requests_included": False,
            "missing_c0_is_knowledge_absence": False,
            "gold_or_reference_strings_exported": False,
            "causal_claim": None,
        },
        "cell_counts": counts,
        "cell_proportions": {name: _ratio(count, len(ids)) for name, count in counts.items()},
        "aggregate": {
            "gold_intent_value_supplied": _ratio(supplied, len(ids)),
            "c0_coverage_given_supply": _ratio(counts["supplied_and_covered"], supplied),
            "c0_coverage_without_supply": _ratio(counts["not_supplied_but_covered"],
                                               len(ids) - unavailable - supplied),
        },
        "samples": samples,
    }
