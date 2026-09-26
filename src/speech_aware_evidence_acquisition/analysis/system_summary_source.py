"""Join finalized text summaries to the exact complete actor inputs they saw."""
from dataclasses import dataclass
from collections.abc import Mapping

from .prepared_text_source import PreparedTextSourceError, verify_prepared_text_source
from ..core.bundle.verify import verify_bundle
from ..rails.system_summary_context import build_system_summary_contexts, PREPARED_SUMMARY_SCHEMA

SummarySourceError = PreparedTextSourceError


@dataclass(frozen=True)
class VerifiedSystemSummaries:
    manifest: Mapping
    manifest_sha256: str
    actor_binding: Mapping
    prepared_document: Mapping
    rows: Mapping


def verify_system_summaries(manifest_pin, *, repo_root, data_root):
    """Preserve the historical summary result shape on the shared stage verifier."""
    result = verify_prepared_text_source(
        manifest_pin, repo_root=repo_root, data_root=data_root,
        input_schema=PREPARED_SUMMARY_SCHEMA, artifact_kind="system-summary-contexts",
        rebuild_contexts=build_system_summary_contexts, bundle_reader=verify_bundle)
    rows = {sid: {
        "sample_id": sid, "summary": row["text"], "status": row["status"],
        "episode_sha256": row["source_context_sha256"],
        "summary_manifest_sha256": row["manifest_sha256"], "summary_request_id": row["request_id"],
        "summary_response_sha256": row["response_text_sha256"],
    } for sid, row in result.rows.items()}
    return VerifiedSystemSummaries(result.manifest, result.manifest_sha256,
                                   result.source_binding, result.prepared_document, rows)
