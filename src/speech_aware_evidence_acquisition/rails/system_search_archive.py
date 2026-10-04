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
    for historical in packet.get("learning_history", []):
        sources.extend(historical["cumulative_sources"])
    if packet.get("selection") is not None:
        sources.extend(packet["selection"]["cumulative_sources"])
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


def pareto_frontier(rows, *, identity_key="bundle_id"):
    """Preserve non-dominated measurements, including ties and explicit replicate identities."""
    require(bool(rows) and len({r["cohort_id"] for r in rows}) == 1,
            "frontier requires a single common cohort")
    require(len({r[identity_key] for r in rows}) == len(rows), "duplicate measured candidate")
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
                   input_token_cap, output_token_cap, feedback=None, complementary=(), allocation_extension=None):
    """Produce a manifest for a fresh context, not a shared-chat prompt.

    A launcher must enforce this input allowlist and deny all other file/tools
    access. The packet alone is not proof of process/filesystem isolation.
    """
    from .system_search_allocations import require_round
    require_round(round_index, allocation_extension)
    require(branch in {"L", "B"} and type(slot) is int and slot in (1, 2), "invalid allocation")
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
    if allocation_extension is not None:
        from .system_search_allocations import require_packet_allocation
        packet["allocation_extension_sha256"] = content_hash(allocation_extension)
        require_packet_allocation(packet, {"allocation_extension": allocation_extension})
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

    def allocation_extension(self, round_index):
        """Resolve an existing prospective allowance, never infer one from input."""
        from .system_search_allocations import require_round, validate_extension
        if type(round_index) is int and 1 <= round_index <= 3:
            return None
        path = self.root / f"allocations/round-{round_index}.json"
        require(path.is_file(), "registered round extension required")
        extension = json.loads(path.read_text())
        require_round(round_index, extension)
        return validate_extension(self, extension)

    def require_packet_allocation(self, packet):
        from .system_search_allocations import require_packet_allocation
        require_packet_allocation(packet, {"allocation_extension": self.allocation_extension(packet["round"])})

    def record_proposal(self, *, branch, round_index, slot, receipt):
        extension = self.allocation_extension(round_index)
        require(branch in {"L", "B"} and type(slot) is int and slot in (1, 2), "proposal quota exceeded")
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
            proposal = TextPolicyUpdateProposal.from_json(json.loads(receipt["raw_response"]), allocation_extension=extension).as_json()
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
        self.allocation_extension(before_round)
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
        self.require_packet_allocation(packet)
        require(branch in {"L", "B"} and type(slot) is int and slot in (1, 2), "invalid input allocation")
        self._write(f"inputs/{branch}-{round_index}-{slot}.json", packet)

    def import_response(self, *, branch, round_index, slot, receipt):
        """Join an exact isolated-session response to its prepublished input manifest."""
        packet = json.loads((self.root / f"inputs/{branch}-{round_index}-{slot}.json").read_text())
        self.require_packet_allocation(packet)
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
            result.update(input_sha256=packet["input_sha256"], receipt_sha256=content_hash(receipt))
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
            try:
                require(proposal["schema"] == TextPolicyUpdateProposal.schema_for_packet(packet),
                        "proposal schema differs from frozen input scope")
            except ValueError as error:
                errors.append(str(error))
            if "optimization_scope" in packet:
                from .system_optimization import require_optimization_scope
                try:
                    require_optimization_scope(packet)
                    require(set(proposal["changes"]) <= set(packet["optimization_scope"]["editable"]),
                            "proposal changes exceed the frozen optimization scope")
                except ValueError as error:
                    errors.append(str(error))
            allowed = {packet["parent_bundle_id"]} | {content_hash(p) for p in packet.get("complementary_policies", [])}
            if not set(proposal["parent_ids"]) <= allowed or proposal["parent_ids"][0] != packet["parent_bundle_id"]:
                errors.append("proposal parents differ from frozen input")
        result = {"proposal_allocation": [branch, round_index, slot], "errors": errors,
                  "status": "invalid" if errors else record["status"],
                  "metering_complete": all(receipt[k] is not None for k in ("input_tokens", "output_tokens")),
                  "activation": "none"}
        result.update(input_sha256=packet["input_sha256"], receipt_sha256=content_hash(receipt))
        self._write(f"imports/{branch}-{round_index}-{slot}.json", result)
        return result

    def record_compilation(self, *, branch, round_index, slot, bundle, configuration):
        """Bind a completed compiler output to its spent proposal slot; no admission."""
        self.allocation_extension(round_index)
        require(branch in {"L", "B"} and type(slot) is int and slot in (1, 2), "invalid compilation allocation")
        key = f"{branch}-{round_index}-{slot}"
        packet = json.loads((self.root / f"inputs/{key}.json").read_text())
        imported = json.loads((self.root / f"imports/{key}.json").read_text())
        proposal = json.loads((self.root / f"proposals/{key}.json").read_text())
        require(imported["status"] in {"provisional", "no-change", "duplicate"}, "invalid proposal cannot compile")
        require(imported["input_sha256"] == packet["input_sha256"]
                and imported["receipt_sha256"] == content_hash(proposal["receipt"]), "compilation input differs")
        d = bundle.as_json()
        require(d["parent_ids"] == proposal["proposal"]["parent_ids"]
                and any(s["kind"] == "proposal" and s["sha256"] == content_hash(proposal)
                        for s in d["cumulative_sources"]), "compiled policy lost proposal custody")
        self.load_policy(bundle.bundle_id)
        record = {"schema": "saea-system-search-compilation-v1", "allocation": [branch, round_index, slot],
            "bundle_id": bundle.bundle_id, "input_sha256": packet["input_sha256"],
            "import_sha256": content_hash(imported), "configuration_sha256": content_hash(configuration),
            "runtime_admission": "separate-required"}
        self._write(f"compilations/{key}.json", record)
        return record

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

    def retain_feedback(self, *, protocol, stage_name, feedback, evaluation, branch, selected_ids,
                        retain_parent=False):
        """Record root's choice using verified official measurements, never manual scores.

        The CLI binds evaluation to the countersigned READ recipe. Root applies
        its registered own-A/A protection and tie-breaks before calling this
        method. This custody layer does not invent a statistical guard or adopt
        a policy. The first selected ID is the next quality parent/finalist.
        """
        from .system_search_protocol import require_stage_feedback, stage_for
        from .system_text_feedback import CompleteSystemFeedback, learning_read_authority
        from .system_text_policy import assert_roster_disjoint

        require(branch in {"L", "B"} and stage_name in {"update-1", "update-2", "update-3", "selection"},
                "selection requires a registered TRAIN update or common selection stage")
        require(isinstance(feedback, CompleteSystemFeedback), "complete verified feedback is required")
        require_stage_feedback(protocol, stage_name, feedback)
        d = feedback.as_json()
        require(d["family_id"] == stage_name and bool(d.get("read_authority")), "selection family/read authority differs")
        require(set(evaluation) == {"schema", "stage", "protocol_sha256", "member_bindings"}
                and evaluation["schema"] == "saea-system-search-evaluation-binding-v1"
                and evaluation["stage"] == stage_name
                and evaluation["protocol_sha256"] == content_hash(protocol), "selection protocol binding differs")
        bindings = evaluation["member_bindings"]
        require(set(bindings) == set(d["summaries"]), "selection must bind every admitted member")
        sources = d["feedback"]["sources"]
        require(len(sources) == len(bindings) and {s["candidate_id"] for s in sources} == set(bindings),
                "selection source family differs")
        ids = stage_for(protocol, stage_name)["sample_ids"]
        policies = {}
        for source in sources:
            cid = source["candidate_id"]
            binding = bindings[cid]
            require(set(binding) == {"bundle_id", "run_id", "config_hash"}
                    and all(binding[key] == source[key] for key in ("run_id", "config_hash")),
                    "measured run/config differs from preregistered policy binding")
            sha(binding["config_hash"])
            policies[cid] = self.load_policy(binding["bundle_id"])
            assert_roster_disjoint(policies[cid].as_json()["cumulative_sources"], ids)
        seed_id = protocol["seed_bundle"]["bundle_id"]
        pairs = [("seed", "seed-aa")] if stage_name == "selection" else [
            (b + "-parent", b + "-parent-aa") for b in ("L", "B")]
        for parent, aa in pairs:
            require(bindings[parent]["bundle_id"] == bindings[aa]["bundle_id"], "same-chain A/A policy differs")
        seed_member = "seed" if stage_name == "selection" else "B-parent"
        require(bindings[seed_member]["bundle_id"] == seed_id, "blind evaluation parent must remain the frozen seed")
        parent = "seed" if stage_name == "selection" else branch + "-parent"
        aa = "seed-aa" if stage_name == "selection" else branch + "-parent-aa"
        members = [parent, *sorted(cid for cid in bindings if cid.startswith(branch + "-") and cid not in {parent, aa})]
        profile = protocol.get("measurement_profile")
        require(d.get("measurement_profile") == profile, "feedback measurement profile differs")
        if profile is None:
            all_measurements = [{"candidate_id": cid, "bundle_id": bindings[cid]["bundle_id"],
                "cohort_id": content_hash(ids), **{k: d["summaries"][cid][k] for k in OBJECTIVES}}
                for cid in members]
        else:
            from .system_search_measurement import measured_rows
            all_measurements = measured_rows(d, members, bindings, profile=profile)
        # A repeated identical bundle is a replicate, not another selectable
        # policy. Use the designated comparator first, then fixed slot order;
        # preserve all repeats without choosing their most favorable draw.
        measurements, repeats, seen = [], [], set()
        for row in all_measurements:
            (repeats if row["bundle_id"] in seen else measurements).append(row)
            seen.add(row["bundle_id"])
        if profile is None:
            frontier = pareto_frontier(measurements)
        else:
            from .system_search_measurement import measured_frontier
            frontier = measured_frontier(measurements, profile=profile)
        require(0 < len(selected_ids) <= 2 and len(set(selected_ids)) == len(selected_ids),
                "retain at most two distinct active search candidates")
        require(type(retain_parent) is bool, "parent fallback must be explicit")
        if retain_parent:
            require(selected_ids == [bindings[parent]["bundle_id"]], "fallback must keep only the measured parent")
        else:
            require(set(selected_ids) <= {r["bundle_id"] for r in frontier}, "active selection must be non-dominated")
        # Losing and unused same-branch policies influenced selection too.
        ancestry = cumulative_sources([policies[cid] for cid in [*members, aa]])
        registration = d["read_authority"].get("stage_registration")
        if stage_name == "selection" and registration is not None:
            # Nominating a historical survivor inspected every prior branch
            # retention, including losing or unused policies and earlier cohorts.
            ancestry = cumulative_sources([], [*ancestry, *registration["cumulative_sources"][branch]])
        ancestry = cumulative_sources([], [*ancestry, {"kind": "feedback", "sha256": content_hash(d["reference"]),
            "sample_ids": d["reference"]["sample_ids"]}])
        record = {"schema": "saea-system-search-retention-v1", "branch": branch, "stage": stage_name,
            "protocol_sha256": content_hash(protocol), "feedback_sha256": content_hash(d),
            "read_authority": learning_read_authority(d["read_authority"]), "cohort_id": content_hash(ids),
            "member_bindings": {cid: bindings[cid] for cid in [*members, aa]},
            "measurements": measurements, "frontier": frontier, "active_ids": list(selected_ids),
            "duplicate_bundle_replicates": repeats,
            "same_chain_aa": {"candidate_id": aa, **d["summaries"][aa]},
            "parent_fallback": retain_parent, "status": "search-only-not-adopted",
            "statistical_review": "Root applies the registered own-A/A guard and tie-breaks; no automatic verdict."}
        ancestry.append({"kind": "selection", "sha256": content_hash(record), "sample_ids": list(ids)})
        record["cumulative_sources"] = cumulative_sources([], ancestry)
        if profile is not None:
            record.update(schema="saea-system-search-retention-v2", measurement_profile=profile)
        record["selection_sha256"] = content_hash(record)
        self._write(f"retentions/{stage_name}/{branch}.json", record)
        return record

    def _selection(self, *, protocol, stage_name, feedback, branch):
        require(stage_name in {"update-1", "update-2", "update-3", "selection"} and branch in {"L", "B"},
                "invalid selection identity")
        path = self.root / f"retentions/{stage_name}/{branch}.json"
        require(path.exists(), "complete same-stage selection is missing")
        record = json.loads(path.read_text())
        require(record.get("selection_sha256") == content_hash({k: v for k, v in record.items() if k != "selection_sha256"})
                and (record["stage"], record["branch"]) == (stage_name, branch), "selection identity changed")
        require(record["protocol_sha256"] == content_hash(protocol)
                and record["feedback_sha256"] == content_hash(feedback.as_json()), "selection protocol/feedback changed")
        for identity in record["active_ids"]:
            self.load_policy(identity)
        return record

    def learning_selection(self, *, protocol, round_index, feedback, parent_id, complementary_ids):
        """Bind later L inputs to the earlier recorded choice; never call for B."""
        require(round_index in (1, 2, 3), "invalid learning round")
        if round_index == 1:
            require(parent_id == protocol["seed_bundle"]["bundle_id"] and not complementary_ids,
                    "first learning round must use the frozen seed")
            return None
        record = self._selection(protocol=protocol, stage_name=f"update-{round_index - 1}", feedback=feedback, branch="L")
        require(parent_id == record["active_ids"][0], "learning parent differs from recorded selection")
        require(len(complementary_ids) == len(set(complementary_ids))
                and set(complementary_ids) <= set(record["active_ids"][1:]), "complementary policy was not retained")
        return record

    def finalists_document(self, *, protocol, feedback):
        """Reconstruct common-cohort choices and exposure without publishing or choosing."""
        from .system_search_protocol import require_stage_feedback, stage_for
        from .system_text_policy import assert_roster_disjoint
        require_stage_feedback(protocol, "selection", feedback)
        require(feedback.as_json()["family_id"] == "selection", "finalists require the common selection family")
        selections = {b: self._selection(protocol=protocol, stage_name="selection", feedback=feedback, branch=b)
                      for b in ("L", "B")}
        sources = cumulative_sources([], [s for r in selections.values() for s in r["cumulative_sources"]])
        assert_roster_disjoint(sources, stage_for(protocol, "dev")["sample_ids"])
        seed_id = protocol["seed_bundle"]["bundle_id"]
        record = {"schema": "saea-system-search-finalists-v1", "protocol_sha256": content_hash(protocol),
            "feedback_sha256": content_hash(feedback.as_json()),
            "selections": {b: r["selection_sha256"] for b, r in selections.items()},
            "members": {"seed": seed_id, "seed-aa": seed_id,
                        **{b + "-frozen": r["active_ids"][0] for b, r in selections.items()}},
            "dev_roster_sha256": content_hash(stage_for(protocol, "dev")["sample_ids"]),
            "cumulative_sources": sources, "status": "frozen-for-dev-not-adopted", "runtime_admission": "separate-required"}
        record["freeze_sha256"] = content_hash(record)
        return record

    def freeze_finalists(self, *, protocol, feedback):
        """Freeze common-cohort choices and all selection exposure before DEV."""
        record = self.finalists_document(protocol=protocol, feedback=feedback)
        self._write("finalists.json", record)
        return record
