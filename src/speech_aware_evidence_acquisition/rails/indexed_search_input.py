"""Prospective indexed search presentation; no source or contact admission.

Keep every original aggregate record and comparator in content-addressed detail
objects. Present the same predeclared metrics for every historical candidate,
including rejected and inactive ones. Never rank/filter rows by their results.
The caller must register the new presentation and actual capsule byte hashes;
original draft actor hashes cannot authorize this different model-visible input.
"""
from copy import deepcopy
import json

from .hashing import content_hash
from .system_text_policy import require

PRIMARY_RATES = (
    "review_valid", "draft_parsed", "final_parsed", "review_error_detection",
    "review_alarm_precision", "review_false_alarm", "handoff_visibility_given_valid_review",
    "entity_repair_given_revision", "entity_harm_given_revision", "empty_gold_false_fill",
)


def _process(value, encoding, vectors, vector_ids):
    if value is None:
        return None
    def vector(rate):
        key = content_hash(rate)
        if key not in vector_ids:
            vector_ids[key] = len(vectors)
            vectors.append(deepcopy(rate))
        return vector_ids[key]
    return {
        "rates": {name: vector(rate) for name, rate in
                  zip(encoding["metric_order"], value["rates"], strict=True)
                  if name in PRIMARY_RATES},
        "support": {name: vector(rate) for name, rate in
                    zip(encoding["support_order"], value["support"], strict=True)},
    }


def _primary(actor, detail_documents):
    primary = deepcopy(actor)
    feedback = primary["feedback"]
    records = []
    vectors, vector_ids = [], {}
    for original in actor["feedback"]["records"]:
        ref = content_hash(original)
        detail_documents[ref] = deepcopy(original)
        row = {k: deepcopy(v) for k, v in original.items()
               if k not in {"template", "terminal", "node_statistics", "process"}}
        row["detail_ref"] = ref
        row["template_bundle_id"] = original["template"].get("bundle_id")
        row["utility_statistics"] = deepcopy(original["terminal"].get("utility"))
        row["process_summary"] = _process(original["process"], feedback["process_encoding"], vectors, vector_ids)
        row["node_summary"] = {
            node: [stats.get("visits"), stats.get("interrupted"), stats.get("samples_missing_role"),
                   deepcopy(stats.get("output_features", {}).get("strict_schema")),
                   deepcopy(stats.get("output_features", {}).get("strict_action"))]
            for node, stats in original["node_statistics"].items()}
        records.append(row)
    controls = []
    for original in actor["feedback"]["comparators"]:
        ref = content_hash(original)
        detail_documents[ref] = deepcopy(original)
        controls.append({"id": original["id"], "business": deepcopy(original["business"]), "detail_ref": ref})
    feedback["records"], feedback["comparators"] = records, controls
    feedback["rate_vectors"] = vectors
    feedback["node_summary_columns"] = ["visits", "interrupted", "samples_missing_role", "strict_schema", "strict_action"]
    primary["indexed_presentation"] = {
        "schema": "saea-indexed-aggregate-search-presentation-v1",
        "original_actor_sha256": content_hash(actor),
        "primary_rates": list(PRIMARY_RATES),
        "read_policy": "Read every primary row. Inspect indexed detail objects as needed within the registered cumulative input budget. Record accessed references and omitted detail reads.",
        "primary_omissions": ["Historical full templates", "Detailed node timing and structural distributions",
                              "Terminal distributions other than update utility", "Unlisted process rates and transition tables",
                              "Comparator process detail"],
        "custody": "All omitted primary fields remain verbatim in detail objects; no historical record, numeric precision, missingness, interval or template is deleted. Current assigned parent templates remain inline.",
        "interpretation": "Rates and support are zero-based indexes into feedback.rate_vectors. Each vector retains every original field in process_encoding.rate_fields. Missing process is null, not zero. This index is optimization history, not independent validation."
    }
    return primary


def prepare_indexed_search_input(draft, *, max_primary_bytes):
    """Build a non-admitted index and preserve exact reversible source custody."""
    require(draft.get("schema") == "saea-search-input-draft-v1"
            and draft.get("draft_sha256") == content_hash({k:v for k,v in draft.items() if k != "draft_sha256"})
            and draft["registration_draft"]["status"] == "DRAFT"
            and all(draft.get(k) is False for k in ("learner_exported", "runtime_admission", "proposal_allocation_granted")),
            "unmodified non-admitted draft required")
    require(type(max_primary_bytes) is int and max_primary_bytes > 0, "positive byte budget required")
    actor = draft["actor_view"]
    rows = actor["feedback"]["records"]
    require(bool(rows) and len({r["record_id"] for r in rows}) == len(rows), "unique complete records required")
    require(all(r["record_id"] == content_hash({k:v for k,v in r.items() if k != "record_id"}) for r in rows),
            "original aggregate record changed")
    details = {}
    primary = _primary(actor, details)
    raw = json.dumps(primary, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()
    require(len(raw) <= max_primary_bytes, "primary byte budget exceeded; do not truncate")
    package = {"schema": "saea-indexed-search-input-package-v1", "original_actor_sha256": content_hash(actor),
               "source_draft_sha256": draft["draft_sha256"], "primary": primary, "detail_documents": details,
               "primary_bytes": len(raw), "max_primary_bytes": max_primary_bytes,
               "runtime_admission": False, "learner_exported": False, "proposal_allocation_granted": False}
    package["package_sha256"] = content_hash(package)
    require(verify_indexed_search_input(package) == actor, "source reconstruction differs")
    return package


def verify_indexed_search_input(package):
    """Reconstruct exact original actor; this verifies custody, not READ rights."""
    require(package.get("schema") == "saea-indexed-search-input-package-v1"
            and package.get("package_sha256") == content_hash({k:v for k,v in package.items() if k != "package_sha256"}),
            "indexed package changed")
    details = package["detail_documents"]
    require(all(content_hash(value) == ref for ref, value in details.items()), "detail content changed")
    actor = deepcopy(package["primary"])
    actor.pop("indexed_presentation")
    actor["feedback"].pop("rate_vectors")
    actor["feedback"].pop("node_summary_columns")
    used = set()
    for field in ("records", "comparators"):
        refs = [r["detail_ref"] for r in actor["feedback"][field]]
        require(all(ref in details for ref in refs), "missing indexed detail")
        used.update(refs)
        actor["feedback"][field] = [deepcopy(details[ref]) for ref in refs]
    require(used == set(details) and content_hash(actor) == package["original_actor_sha256"], "source reconstruction differs")
    require(_primary(actor, {}) == package["primary"], "primary summaries differ from source")
    return actor
