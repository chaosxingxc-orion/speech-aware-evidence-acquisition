"""Complete-family official feedback for external, parameter-free text updates."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .group_relative_feedback import build_group_relative_feedback
from .hashing import content_hash
from .native_episode_receipt import validate_native_episode_delivery_receipt
from .system_text_policy import PolicyError, canonical, require


def _number(value):
    require(type(value) in (int, float) and math.isfinite(value), "feedback must be finite numeric data")
    return float(value)


def _counts(counts):
    values = [_number(counts[f"slu_f1_{axis}_{kind}"]) for kind in ("tp", "fp", "fn")
              for axis in ("word", "char")]
    require(all(v >= 0 for v in values), "entity counts must be nonnegative")
    return tuple(values[i] + values[i + 1] for i in (0, 2, 4))


def feedback_utility(counts, reference_f1):
    """Linearized pooled-F1 utility; not a replacement official metric or gradient."""
    reference = _number(reference_f1)
    require(0 <= reference <= 1, "reference F1 must be frozen on the zero-to-one scale")
    tp, fp, fn = _counts(counts)
    return 2 * tp - reference * (2 * tp + fp + fn)


def paired_relative_returns(values):
    require(len(values) >= 2, "relative feedback needs at least two complete trajectories")
    values = [_number(v) for v in values]
    mean = math.fsum(values) / len(values)
    std = math.sqrt(math.fsum((v - mean) ** 2 for v in values) / len(values))
    return [(v - mean) / std if std else 0.0 for v in values]


def _absolute_json(pin):
    path = Path(pin["path"])
    require(path.is_absolute(), "feedback source path must be absolute")
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == pin["sha256"], "feedback source hash differs")
    return json.loads(raw)


def preflight_family(bindings, expected_members):
    """Inspect ALL members' operational metadata before opening any task result.

    expected_members is the preregistered candidate-to-run mapping, not inferred
    from the sources that happen to exist. Verified seals are checked next by the
    shared reward-link reader; a COMPLETED manifest flag alone is insufficient.
    """
    ids = [b.get("candidate_id") for b in bindings]
    require(len(ids) >= 2 and len(set(ids)) == len(ids) and set(ids) == set(expected_members),
            "all members of the complete family are required")
    manifests = []
    for binding in bindings:
        config = binding["config"]
        manifest = _absolute_json(config["manifest"])
        run = expected_members[binding["candidate_id"]]
        require(manifest.get("status") == "COMPLETED" and manifest.get("run_id") == run,
                "complete family member identity/status differs")
        require(manifest.get("plan", {}).get("split_role") == "discovery", "only TRAIN feedback is allowed")
        roster = _absolute_json(config["construction_roster"])
        sample_ids = [r["sample_id"] for r in roster["items"]]
        require(sample_ids and all(s.startswith("slurp:train:") for s in sample_ids),
                "only TRAIN feedback is allowed")
        attempt = manifest["attempt"]
        state = json.loads(Path(attempt["state_path"]).read_text())
        require(state.get("state") == "FINALIZED" and state.get("run_id") == run
                and state.get("attempt_id") == attempt["attempt_id"], "attempt is not finalized")
        job_path = Path(config["manifest"]["path"]).parent / "score-jobs.jsonl"
        jobs = [json.loads(line) for line in job_path.read_text().splitlines() if line.strip()]
        require(len(jobs) == 1 and Path(jobs[0]["manifest"]).resolve() == Path(config["manifest"]["path"]).resolve(),
                "exactly one official score job per complete member is required")
        manifests.append((manifest, jobs[0]))
    return manifests


def _row_cost_and_terminal(manifest):
    """Use attributed role/tool records, including failed contacts; never service totals."""
    # The caller already verified this bundle via reward links. Reopen its pinned
    # output/trace bytes here so this view cannot silently substitute loose files.
    raw = Path(manifest["raw_trace"]["path"]).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == manifest["raw_trace"]["sha256"], "trace bytes changed")
    out = Path(manifest["outputs"]["path"]).read_bytes()
    require(hashlib.sha256(out).hexdigest() == manifest["outputs"]["sha256"], "terminal bytes changed")
    outputs = {r["sample_id"]: r for r in map(json.loads, out.splitlines()) if r}
    records = [json.loads(line) for line in raw.splitlines() if line]
    result = {}
    for sid, output in outputs.items():
        receipt = output.get("native_episode_receipt")
        require(isinstance(receipt, dict), "complete system terminal receipt is missing")
        terminal = validate_native_episode_delivery_receipt(receipt, error_type=PolicyError)
        requests = {r["payload"]["payload"]["request_id"]: r for r in records
                    if r["channel"] == "MODEL_REQUEST" and r["payload"].get("payload", {}).get("sample_id") == sid}
        require(bool(requests), "terminal row has no attributed model requests")
        role_counts = {}
        for visit in receipt["role_visits"]:
            contacts = visit.get("execution_receipt", {}).get("contacts", [])
            role_counts[visit["role_id"]] = role_counts.get(visit["role_id"], 0) + len(contacts)
        tools = [r for r in records if r["payload"].get("use_sample_id") == sid
                 and isinstance(r["payload"].get("use_tool_invocation"), dict)]
        usage = [r["payload"].get("usage", {}) for r in records
                 if r["channel"] == "MODEL_RESPONSE" and r["payload"].get("request_id") in requests]
        tokens = {}
        for key in ("prompt_tokens", "completion_tokens"):
            tokens[key] = (sum(u[key] for u in usage) if len(usage) == len(requests)
                           and all(type(u.get(key)) is int and u[key] >= 0 for u in usage) else None)
        result[sid] = {"model_calls": len(requests), "tool_calls": len(tools), "role_contacts": role_counts,
                       **tokens, "delivery_kind": terminal.kind,
                       "reliable_completion": terminal.kind in {"accepted", "terminal"},
                       "abstained": terminal.kind in {"abstention", "context-abstention"},
                       "trace": manifest["raw_trace"], "terminal_output": manifest["outputs"],
                       "omissions": [], "wall_time_seconds": None}
    return result


@dataclass(frozen=True)
class CompleteSystemFeedback:
    document_json: str

    def as_json(self):
        return json.loads(self.document_json)

    def learning_view(self, candidate_ids):
        """Project own-branch evidence after the entire round passes its read gate."""
        d = self.as_json()
        require(len(candidate_ids) >= 2 and len(set(candidate_ids)) == len(candidate_ids)
                and set(candidate_ids) <= set(d["summaries"])
                and all(cid.startswith("L-") or cid in {"seed", "seed-aa"} for cid in candidate_ids),
                "learning feedback must contain only the learning branch or initial seed pair")
        family_sha = content_hash(d)
        d["summaries"] = {k: v for k, v in d["summaries"].items() if k in candidate_ids}
        feedback = d["feedback"]
        feedback["candidate_ids"] = list(candidate_ids)
        feedback["sources"] = [s for s in feedback["sources"] if s["candidate_id"] in candidate_ids]
        for group in feedback["groups"]:
            group["members"] = [m for m in group["members"] if m["candidate_id"] in candidate_ids]
            # Recompute rather than leaking blind scores through group normalization.
            relative = paired_relative_returns([m["utility"] for m in group["members"]])
            for member, advantage in zip(group["members"], relative, strict=True):
                member["relative_return"] = advantage
                # Old multi-metric centering used the entire round too.
                member.pop("quality", None)
        d["read_gate_family_sha256"] = family_sha
        return CompleteSystemFeedback(canonical(d))

    @classmethod
    def from_family(cls, bindings, *, expected_members, family_id, reference=None, initial_reference_member=None):
        metadata = preflight_family(bindings, expected_members)
        from ..core.bundle.verify import verify_bundle
        for binding in bindings:
            verified = verify_bundle(Path(binding["config"]["manifest"]["path"]))
            require(verified.attempt_state == "FINALIZED", "family seal verification failed")
        grouped = build_group_relative_feedback(bindings)
        require(grouped["carrier_lock_key"] == "slurp" and len(grouped["groups"]) >= 400,
                "system search feedback requires the entire registered cohort of at least 400 rows")
        by_candidate, summaries = {}, {}
        for binding, (manifest, job) in zip(bindings, metadata, strict=True):
            cid = binding["candidate_id"]
            require(binding["config"]["projection"]["scorer"] == "slurp-slu-official-train",
                    "system updates require the official TRAIN scorer")
            receipt = _absolute_json(binding["config"]["complete_score_receipt"])
            require(receipt["job_id"] == job["job_id"], "official score identity differs from sole job")
            score = _absolute_json(receipt["score_result"])["scores"]["slurp-slu-official-train"]
            aggregate = score["aggregate"]
            require(aggregate["identity_check"]["passed"] is True, "official sufficient-count identity failed")
            rows = _row_cost_and_terminal(manifest)
            require(set(rows) == {g["sample_id"] for g in grouped["groups"]}, "terminal cohort differs")
            by_candidate[cid] = rows
            summaries[cid] = {"slu_f1": aggregate["official"]["slu_f1"],
                              "intent": aggregate["port_micro"]["intent_accuracy"],
                              "model_calls": sum(r["model_calls"] for r in rows.values()),
                              "tool_calls": sum(r["tool_calls"] for r in rows.values()),
                              "reliable_completion_rate": sum(r["reliable_completion"] for r in rows.values()) / len(rows)}
        if reference is None:
            require(initial_reference_member in summaries, "initial reference member must be preregistered")
            reference = {"family_id": family_id, "candidate_id": initial_reference_member,
                         "source_sha256": content_hash(grouped["sources"]),
                         "sample_ids": [g["sample_id"] for g in grouped["groups"]],
                         "f1": summaries[initial_reference_member]["slu_f1"]}
        else:
            require(initial_reference_member is None and isinstance(reference, CompleteSystemFeedback),
                    "freeze the original reference instead of recomputing it")
            reference = reference.as_json()["reference"]
        for group in grouped["groups"]:
            utilities = [feedback_utility(m["native_counts"], reference["f1"]) for m in group["members"]]
            relative = paired_relative_returns(utilities)
            for member, utility, advantage in zip(group["members"], utilities, relative, strict=True):
                member.update(utility=utility, relative_return=advantage,
                              execution=by_candidate[member["candidate_id"]][group["sample_id"]])
        result = {"schema": "saea-complete-system-feedback-v1", "family_id": family_id,
                  "reference": reference, "summaries": summaries, "feedback": grouped,
                  "interpretation": "Whole-system realized return; no node causal credit or policy gradient.",
                  "model_contacts_added": 0, "scorer_contacts_added": 0}
        return cls(canonical(result))
