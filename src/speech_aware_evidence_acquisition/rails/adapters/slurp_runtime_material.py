"""SLURP carrier material bindings reused by every config-driven flight."""
import json
from pathlib import Path
from typing import Mapping
from ...core.flight.runtime import FlightRuntime

def bind_runtime_material(
    runtime: FlightRuntime,
    values: Mapping[str, object],
    lock: Mapping[str, object],
    root: Path,
) -> dict[str, object]:
    """Bind the two pieces of carrier material the candidate-supply cells need, from
    CONFIG alone -- nothing here is a launcher and nothing here is per-cell
    code.

    A knowledge provider's own artifact and a judge's own carrier material are
    the two things ``core.flight.FlightRuntime`` documents as too large for a
    fragment (``bind_phase_supply_providers`` /
    ``bind_phase_review_material``). candidate-supply needs exactly one of each:

    * the sha256-pinned candidate bank behind
      ``rails.knowledge_provider.SlurpIntentCandidateProvider`` -- the
      per-row decision a cosine cannot express, because half of it is the
      comparator's own sealed response;
    * the 60-pair ``LegalIntentInventory`` ``slurp-legal-label-flag-v1``
      reads.

    Both are keyed off fragment keys, so a fragment that declares neither is
    byte-unaffected: this function returns an empty record and binds nothing.
    """

    bound: dict[str, object] = {}
    relpath = values.get("candidate_bank_relpath")
    if isinstance(relpath, str) and relpath:
        from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
        from speech_aware_evidence_acquisition.rails.knowledge_provider import (
            SlurpIntentCandidateProvider,
        )
        from speech_aware_evidence_acquisition.rails.slurp_intent_candidates import (
            load_candidate_bank,
        )

        supply = values.get("phase_supply")
        if not isinstance(supply, Mapping) or len(supply) != 1:
            raise SystemExit(
                "a fragment declaring candidate_bank_relpath must supply exactly one phase"
            )
        phase = next(iter(supply))
        bank = load_candidate_bank(
            root / relpath, expected_sha256=str(values["candidate_bank_sha256"])
        )
        selection = str(values.get("candidate_bank_selection", "candidates"))
        # The SAME load and the SAME hash check
        # ``FlightRuntime._load_knowledge_snapshot`` performs, done here
        # because ``_composed`` is not resolved until preflight and the
        # provider has to be bound before it: the frozen snapshot named by
        # ``knowledge_snapshot_relpath``, re-hashed against the fragment's
        # own ``knowledge_snapshot_sha256``. Both loads produce the same
        # content hash or neither runs.
        snapshot_document = json.loads(
            (root / str(values["knowledge_snapshot_relpath"])).read_text(encoding="utf-8")
        )
        snapshot = KnowledgeSnapshot.from_frozen_json(snapshot_document)
        if snapshot.content_hash() != str(values["knowledge_snapshot_sha256"]):
            raise SystemExit(
                "candidate snapshot content hash does not match the fragment's pin"
            )
        provider = SlurpIntentCandidateProvider(bank=bank, selection=selection)
        provider.adopt(
            snapshot,
            policy_id=f"frozen-snapshot:{phase}",
            source_ids=(),
            snapshot_sha256=snapshot.content_hash(),
        )
        runtime.bind_phase_supply_providers({phase: provider})
        bound["candidate_bank"] = {
            "relpath": relpath,
            "sha256": bank.sha256,
            "selection": selection,
            "rows": len(bank.selection(selection)),
            "k": bank.k,
            "phase": phase,
        }

    review = values.get("phase_review")
    if isinstance(review, Mapping) and review:
        from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
            load_legal_intent_inventory,
        )

        inventory = load_legal_intent_inventory(lock, root)
        material = {
            str(phase): {
                str(judge_id): {"inventory": inventory}
                for judge_id in (entry or {}).get("judges", ())
                if str(judge_id) == "slurp-legal-label-flag-v1"
            }
            for phase, entry in review.items()
        }
        material = {phase: entry for phase, entry in material.items() if entry}
        if material:
            runtime.bind_phase_review_material(material)
            bound["review_material"] = {
                phase: sorted(entry) for phase, entry in material.items()
            }
    return bound

