"""Auditable proposal allocation, same-cohort Pareto search and isolated inputs."""
from __future__ import annotations

import json
import math
import hashlib
from pathlib import Path

from .hashing import content_hash
from .system_text_policy import PolicyError, TextPolicyUpdateProposal, canonical, require, sha, cumulative_sources

OBJECTIVES = {"slu_f1": 1, "intent": 1, "model_calls": -1, "tool_calls": -1}


def proposal_sources(packet, record):
    """Retain everything the proposer could inspect, including unused parents."""
    sources = []
    for record in packet.get("learning_history", []):
        sources.extend(record["cumulative_sources"])
    for policy in [packet["parent_policy"], *packet.get("complementary_policies", [])]:
        sources.extend(policy["cumulative_sources"])
    if "feedback" in packet:
        feedback = packet["feedback"]
        ids = {g["sample_id"] for g in feedback["feedback"]["groups"]}
        ids.update(feedback["reference"]["sample_ids"])
        sources.append({"kind": "feedback", "sha256": content_hash(feedback), "sample_ids": sorted(ids)})
    sources = cumulative_sources([], sources)
    sources.append({"kind": "proposal", "sha256": content_hash(record),
                    "sample_ids": sorted({sid for source in sources for sid in source["sample_ids"]})})
    return sources


def pareto_frontier(rows):
    """Preserve every truly non-dominated measured candidate, including ties."""
    require(bool(rows) and len({r["cohort_id"] for r in rows}) == 1,
            "frontier requires a single common cohort")
    require(len({r["bundle_id"] for r in rows}) == len(rows), "duplicate measured candidate")
    for row in rows:
        for key in OBJECTIVES:
            value = row[key]
            require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                    "actual finite measurements are required for every objective")
        require(row["slu_f1"] <= 1 and row["intent"] <= 1, "quality must be on zero-to-one scale")
    def dominates(a, b):
        deltas = [sign * (a[key] - b[key]) for key, sign in OBJECTIVES.items()]
        return all(v >= 0 for v in deltas) and any(v > 0 for v in deltas)
    return [dict(row) for row in rows if not any(dominates(other, row) for other in rows)]


def proposal_input(*, branch, round_index, slot, seed, parent, model_version, session_id,
                   input_token_cap, output_token_cap, feedback=None, complementary=()):
    """Produce a manifest for a fresh context, not a shared-chat prompt.

    A launcher must enforce this input allowlist and deny all other file/tools
    access. The packet alone is not proof of process/filesystem isolation.
    """
    require(branch in {"L", "B"} and round_index in (1, 2, 3) and slot in (1, 2), "invalid allocation")
    require(model_version and session_id and type(input_token_cap) is int and input_token_cap > 0
            and type(output_token_cap) is int and output_token_cap > 0, "pin the proposer and budgets")
    if branch == "B":
        require(feedback is None and not complementary, "blind proposer cannot receive feedback or selected history")
        require(parent.bundle_id == seed.bundle_id, "blind proposer must start from the seed")
    else:
        from .system_text_feedback import CompleteSystemFeedback
        require(isinstance(feedback, CompleteSystemFeedback), "learning proposer requires complete verified feedback")
        require(all(cid.startswith("L-") or cid in {"seed", "seed-aa"}
                    for cid in feedback.as_json()["summaries"]), "learning packet contains another branch's feedback")
    runtime_policy = parent.as_json()
    # Optimizer indexes are supplied separately only on the learning branch.
    if branch == "B":
        require(not runtime_policy["optimizer_experience"], "blind seed contains optimizer feedback")
    packet = {"schema": "saea-text-policy-proposer-input-v1", "branch": branch, "round": round_index,
              "slot": slot, "seed_bundle_id": seed.bundle_id, "parent_bundle_id": parent.bundle_id,
              "parent_policy": runtime_policy, "model_version": model_version, "session_id": session_id,
              "input_token_cap": input_token_cap, "output_token_cap": output_token_cap,
              "context": "fresh-isolated-no-shared-history", "tool_access": "manifest-only",
              "instructions": "Propose one joint English text/config revision. Keep frozen interfaces and evidence boundaries. Return the exact registered proposal schema, including an empty changes object for no change. Do not provide a task answer."}
    if branch == "L":
        packet["feedback"] = feedback.as_json()
        packet["complementary_policies"] = [b.as_json() for b in complementary]
    packet["input_sha256"] = content_hash(packet)
    return packet


class SystemSearchArchive:
    """Create-only records. Proposal attempts consume allocation before validation."""
    def __init__(self, root):
        self.root = Path(root)

    def _write(self, relative, document):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        require(not path.exists(), "proposal allocation already consumed or record exists")
        try:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(canonical(document) + "\n")
        except FileExistsError as error:
            raise PolicyError("proposal allocation already consumed") from error

    def record_proposal(self, *, branch, round_index, slot, receipt):
        require(branch in {"L", "B"} and round_index in (1, 2, 3) and slot in (1, 2), "proposal quota exceeded")
        require(set(receipt) == {"raw_response", "session_id", "model_version", "input_sha256", "input_tokens", "output_tokens"},
                "proposal receipt fields differ")
        sha(receipt["input_sha256"])
        require(isinstance(receipt["raw_response"], str) and receipt["session_id"] and receipt["model_version"],
                "save exact response and proposer identity")
        allocation = f"proposals/{branch}-{round_index}-{slot}.json"
        require(not (self.root / allocation).exists(), "proposal allocation already consumed")
        prior = self.history()
        require(all(r["receipt"]["model_version"] == receipt["model_version"] for r in prior),
                "one search sequence cannot mix proposer models")
        require(all(r["receipt"]["session_id"] != receipt["session_id"] for r in prior),
                "each proposal requires a fresh isolated session")
        record = {"branch": branch, "round": round_index, "slot": slot, "receipt": receipt,
                  "status": "invalid", "error": None, "proposal": None}
        try:
            proposal = TextPolicyUpdateProposal.from_json(json.loads(receipt["raw_response"])).as_json()
            require((proposal["branch"], proposal["round"], proposal["slot"]) == (branch, round_index, slot),
                    "proposal allocation differs from request")
            signature = content_hash({"parent_ids": proposal["parent_ids"], "changes": proposal["changes"]})
            prior_signatures = {r.get("change_sha256") for r in prior}
            status = "no-change" if not proposal["changes"] else "duplicate" if signature in prior_signatures else "provisional"
            record.update(proposal=proposal, status=status, change_sha256=signature)
        except (ValueError, TypeError, KeyError) as error:
            record["error"] = str(error)
        self._write(allocation, record)
        return record

    def history(self):
        return [json.loads(p.read_text()) for p in sorted((self.root / "proposals").glob("*.json"))]

    def learning_history(self, *, before_round):
        """Index all earlier L evidence and failed proposals; never include B.

        The isolated proposer may fetch exactly these hash-bound files. This is
        an index with no hidden selection of positive cases, not a score summary.
        It does not authorize access to the archive directory as a whole.
        """
        require(before_round in (1, 2, 3), "invalid history boundary")
        records = []
        for round_index in range(1, before_round):
            for slot in (1, 2):
                key = f"L-{round_index}-{slot}"
                path = self.root / f"inputs/{key}.json"
                if not path.exists():
                    continue
                packet = json.loads(path.read_text())
                require(packet["input_sha256"] == content_hash({k: v for k, v in packet.items() if k != "input_sha256"}),
                        "history input changed after publication")
                require((packet["branch"], packet["round"], packet["slot"]) == ("L", round_index, slot),
                        "history allocation differs")
                def pin(relative):
                    raw = (self.root / relative).read_bytes()
                    return {"relpath": relative, "sha256": hashlib.sha256(raw).hexdigest()}
                disposition_path = self.root / f"imports/{key}.json"
                require(disposition_path.exists(), "earlier proposal has no recorded disposition")
                record = {"input": pin(f"inputs/{key}.json"), "response": pin(f"responses/{key}.json"),
                          "import": pin(f"imports/{key}.json"), "omissions": [],
                          "disposition": json.loads(disposition_path.read_text())["status"]}
                record["cumulative_sources"] = proposal_sources(packet, record)
                records.append(record)
        return records

    def store_policy(self, bundle):
        path = self.root / "policies" / (bundle.bundle_id + ".json")
        if path.exists():
            require(json.loads(path.read_text()) == bundle.as_json(), "archived policy bytes changed")
        else:
            self._write(f"policies/{bundle.bundle_id}.json", bundle.as_json())
        return bundle.bundle_id

    def load_policy(self, bundle_id, *, _seen=()):
        from .system_text_policy import SystemTextPolicyBundle
        sha(bundle_id)
        require(bundle_id not in _seen and len(_seen) < 100, "cyclic policy ancestry")
        d = json.loads((self.root / "policies" / (bundle_id + ".json")).read_text())
        require(content_hash(d) == bundle_id, "archived policy identity differs")
        parents = [self.load_policy(p, _seen=(*_seen, bundle_id)) for p in d["parent_ids"]]
        return SystemTextPolicyBundle.from_json(d, parents=parents)

    def store_input(self, packet):
        require(packet["input_sha256"] == content_hash({k: v for k, v in packet.items() if k != "input_sha256"}),
                "proposal input fingerprint differs")
        branch, round_index, slot = packet["branch"], packet["round"], packet["slot"]
        require(branch in {"L", "B"} and round_index in (1, 2, 3) and slot in (1, 2), "invalid input allocation")
        self._write(f"inputs/{branch}-{round_index}-{slot}.json", packet)

    def import_response(self, *, branch, round_index, slot, receipt):
        """Join an exact isolated-session response to its prepublished input manifest."""
        packet = json.loads((self.root / f"inputs/{branch}-{round_index}-{slot}.json").read_text())
        require(packet["input_sha256"] == content_hash({k: v for k, v in packet.items() if k != "input_sha256"}),
                "input changed after publication")
        # Burn the opportunity before validating the transport or model response.
        # A malformed/wrong-session receipt cannot become a free replacement call.
        self._write(f"responses/{branch}-{round_index}-{slot}.json", receipt)
        try:
            for field in ("input_sha256", "model_version", "session_id"):
                require(receipt[field] == packet[field], "response identity differs from frozen proposal input")
            record = self.record_proposal(branch=branch, round_index=round_index, slot=slot, receipt=receipt)
        except (KeyError, TypeError, ValueError) as error:
            result = {"proposal_allocation": [branch, round_index, slot], "errors": [str(error)],
                      "status": "invalid", "metering_complete": False, "activation": "none"}
            self._write(f"imports/{branch}-{round_index}-{slot}.json", result)
            return result
        # All exact responses, including over-budget and malformed ones, stay recorded.
        errors = []
        for field, cap in (("input_tokens", "input_token_cap"), ("output_tokens", "output_token_cap")):
            value = receipt[field]
            if value is not None and (type(value) is not int or value < 0 or value > packet[cap]):
                errors.append(f"{field} exceeds frozen limit or is malformed")
        proposal = record["proposal"]
        if proposal is not None:
            allowed = {packet["parent_bundle_id"]} | {content_hash(p) for p in packet.get("complementary_policies", [])}
            if not set(proposal["parent_ids"]) <= allowed or proposal["parent_ids"][0] != packet["parent_bundle_id"]:
                errors.append("proposal parents differ from frozen input")
        result = {"proposal_allocation": [branch, round_index, slot], "errors": errors,
                  "status": "invalid" if errors else record["status"],
                  "metering_complete": all(receipt[k] is not None for k in ("input_tokens", "output_tokens")),
                  "activation": "none"}
        self._write(f"imports/{branch}-{round_index}-{slot}.json", result)
        return result

    def retain(self, *, branch, cohort_id, measurements, selected_ids):
        require(branch in {"L", "B"} and 0 < len(selected_ids) <= 2 and len(set(selected_ids)) == len(selected_ids),
                "retain at most two distinct active search candidates")
        require(all(r["cohort_id"] == cohort_id for r in measurements), "selection cohort differs")
        frontier = pareto_frontier(measurements)
        require(set(selected_ids) <= {r["bundle_id"] for r in frontier}, "active selection must be non-dominated")
        record = {"branch": branch, "cohort_id": cohort_id, "measurements": measurements,
                  "frontier": frontier, "active_ids": selected_ids, "status": "search-only-not-adopted"}
        self._write(f"selections/{branch}-{content_hash(cohort_id)}.json", record)
        return record
