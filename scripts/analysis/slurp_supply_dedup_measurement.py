"""Measure whether the flown SLURP supply path passes duplicated content to its
nodes, and what a dedup-then-rerank context-engineering stage would free.

Model-free and local: reads sealed run traces, released store snapshots and
config fragments, and counts tokens with the local ``llama-tokenize`` binary
(vocab only -- no server, no port, no GPU, no encoder, no scorer). It prints and
persists ids, counts, token counts, ratios and hashes only; it never prints
utterance text, transcripts, gold labels, model output or knowledge bodies.

Run:
    python -B scripts/analysis/slurp_supply_dedup_measurement.py \
        --out /tmp/saea-dedup/measurement.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
TOKENIZE = Path("/home/chao/llama.cpp/build/bin/llama-tokenize")
GGUF = DATA / (
    "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/"
    "Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf"
)

# Sealed arms, with the registered exemplar-store k each one flew.
ARMS = (
    ("SAEA-SLURP-STAGE3-VAR1-EX-K10-R01C-V1", "slurp-native-stage3-var1-ex-k10-r01c", 10),
    ("SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1", "slurp-native-stage3-var1-plan-r01c", 20),
    ("SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1", "slurp-native-stage3-var1-planr-r01c", 20),
    ("SAEA-SLURP-STAGE3-VAR1-EX-K30-R01C-V1", "slurp-native-stage3-var1-ex-k30-r01c", 30),
    ("SAEA-SLURP-STAGE3-VAR1-EX-DIV-R01C-V1", "slurp-native-stage3-var1-ex-div-r01c", 20),
    ("SAEA-SLURP-STAGE3-VAR1-PER-K16C5-R01C-V1", "slurp-native-stage3-var1-per-k16c5-r01c", 20),
    ("SAEA-SLURP-STAGE3-ROLLOUT-R01-V1", "slurp-native-stage3-rollout", 20),
)
STORES = (
    ("train-exemplars",
     "knowledge/slurp/saea-kb-distmodel-v1/"
     "size-pool-annotated-exemplars-minus-r01/snapshot.json"),
    ("intent-boundaries", "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json"),
    ("slot-contracts", "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"),
)
ROLES = ("perception", "solver", "reviewer", "planner")
EPISODE_SAMPLE = 25  # deterministic stride sample of episodes, per arm
WORKERS = 4
WS = re.compile(r"\s+")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm(text):
    return WS.sub(" ", text).strip().casefold()


def stats(values):
    ordered = sorted(values)
    if not ordered:
        return None
    n = len(ordered)
    return {
        "n": n,
        "mean": round(sum(ordered) / n, 4),
        "median": ordered[n // 2],
        "min": ordered[0],
        "max": ordered[-1],
        "sum": sum(ordered),
    }


def store_of(entity_id):
    return entity_id.split("::")[0] if "::" in entity_id else "<unnamespaced>"


def render(items):
    return "\n".join(
        "[value " + i["evidence_id"] + "] " + i["content"] for i in items)


# --------------------------------------------------------------------------
# released stores: key/value fan-in and fan-out, plus body duplication
# --------------------------------------------------------------------------
def read_stores():
    out, bodies, key_to_value = {}, {}, {}
    for role, relpath in STORES:
        document = json.loads((DATA / relpath).read_text(encoding="utf-8"))
        facets, values = document["facets"], document["values"]
        keys_per_value = Counter(len(v["associated_facet_ids"]) for v in values)
        values_per_key = Counter()
        for value in values:
            for facet_id in value["associated_facet_ids"]:
                values_per_key[facet_id] += 1
        for facet in facets:
            if facet["facet_id"] not in values_per_key:
                values_per_key[facet["facet_id"]] = 0
        body = Counter(sha(v["content"]) for v in values)
        normed = Counter(sha(norm(v["content"])) for v in values)
        for value in values:
            bodies[role + "::" + value["value_id"]] = value["content"]
            for facet_id in value["associated_facet_ids"]:
                key_to_value.setdefault(role + "::" + facet_id, []).append(
                    role + "::" + value["value_id"])
        out[role] = {
            "snapshot_relpath": relpath,
            "snapshot_sha256": document["snapshot_sha256"],
            "builder_policy_id": document["builder_policy_id"],
            "n_facets": len(facets),
            "n_values": len(values),
            "facet_dimensions": sorted(Counter(f["dimension"] for f in facets).items()),
            "keys_per_value_distribution": sorted(keys_per_value.items()),
            "values_per_key_distribution": sorted(
                Counter(values_per_key.values()).items()),
            "distinct_body_sha256": len(body),
            "exact_body_duplicate_groups": sum(1 for c in body.values() if c > 1),
            "values_in_exact_body_duplicate_groups": sum(
                c for c in body.values() if c > 1),
            "distinct_normalised_body_sha256": len(normed),
            "values_in_normalised_duplicate_groups": sum(
                c for c in normed.values() if c > 1),
            "values_with_task_target": sum(
                1 for v in values if v["task_target"] is not None),
            "distinct_task_targets": len(
                {v["task_target"] for v in values if v["task_target"] is not None}),
        }
    return out, bodies, key_to_value


def read_configs(repo):
    out = {}
    for _run_id, stem, _k in ARMS:
        path = repo / "configs" / "baseline" / (stem + "-baseline-v1.json")
        document = json.loads(path.read_text(encoding="utf-8"))
        entry = {}
        for name, store in sorted(document["knowledge_stores"].items()):
            for kind in ("phase_supply", "candidate_supply"):
                for phase, spec in sorted((store.get(kind) or {}).items()):
                    entry[name + "/" + kind + "/" + phase] = {
                        "provider": spec.get("provider"),
                        "k": spec.get("k"),
                        "rank_policy": spec.get("rank_policy"),
                        "rank_weights": spec.get("rank_weights"),
                        "fuse_policy": spec.get("fuse_policy"),
                        "fuse_coverage": spec.get("fuse_coverage"),
                        "tau": spec.get("tau"),
                        "expose_facets": spec.get("expose_facets"),
                        "query_relpath": (spec.get("query_source") or {}).get("relpath"),
                        "max_total_values": spec.get("max_total_values"),
                        "max_values_per_candidate": spec.get("max_values_per_candidate"),
                        "max_candidates": spec.get("max_candidates"),
                    }
        out[stem] = entry
    return out


# --------------------------------------------------------------------------
# sealed traces
# --------------------------------------------------------------------------
def dedup_items(items):
    """The same list with every repeated BODY supplied once, first kept."""
    seen, kept = set(), []
    for item in items:
        key = sha(item["content"])
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return kept


def episode_view(payload):
    waves = []
    for wave in payload["use_waves"]:
        rank, fuse = wave["rank_result"], wave["fusion_decision"]
        transition = wave["transition"]
        waves.append({
            "role": wave["batch_id"].split(":")[1],
            "ranking_policy_id": (rank or {}).get("ranking_policy_id"),
            "ranked_keys": [
                c["facet_id"] for c in ((rank or {}).get("candidates") or ())],
            "fusion_policy_id": (fuse or {}).get("fusion_policy_id"),
            "supporting_keys": list((fuse or {}).get("supporting_facet_ids") or ()),
            "selected_values": list((fuse or {}).get("selected_value_ids") or ()),
            "action_kind": transition["action_kind"],
        })
    return {
        "n_waves": len(waves),
        "waves": waves,
        "n_acquire": sum(1 for w in waves if w["action_kind"] == "acquire"),
    }


def scan(run_id):
    run_dir = DATA / "runs" / run_id
    trace = sorted(run_dir.glob("*/" + run_id + ".trace.jsonl"))[0]
    contacts, roles, costs, episodes = {}, {}, {}, {}
    wanted = ('"MODEL_REQUEST"', 'runtime-use"', 'native-role-contact"', '"COST"')
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            if not any(token in line for token in wanted):
                continue
            record = json.loads(line)
            rid, channel = record["record_id"], record["channel"]
            flight = rid.split("/")[0]
            if channel == "MODEL_REQUEST":
                request = record["payload"]["payload"]
                items = request.get("supplied_evidence") or []
                block = render(items)
                contacts[flight] = {
                    "sample_id": request["sample_id"],
                    "evidence_ids": [i["evidence_id"] for i in items],
                    "body_sha256": [sha(i["content"]) for i in items],
                    "normalised_sha256": [sha(norm(i["content"])) for i in items],
                    "block": block,
                    "block_sha256": sha(block),
                    "dedup_block": render(dedup_items(items)),
                }
            elif channel == "COST":
                costs[flight] = record["payload"]["prompt_tokens"]
            elif channel == "USE" and rid.endswith("native-role-contact"):
                roles[flight] = record["payload"]["use_role_id"]
            elif channel == "USE" and rid.endswith("runtime-use"):
                episodes[rid] = episode_view(record["payload"])
    for flight, contact in contacts.items():
        contact["role"] = roles.get(flight)
        contact["prompt_tokens"] = costs.get(flight)
    return {
        "trace_relpath": str(trace.relative_to(DATA)),
        "contacts": contacts,
        "episodes": episodes,
    }


# --------------------------------------------------------------------------
# local tokenizer
# --------------------------------------------------------------------------
class Tokenizer:
    """The local llama.cpp tokenizer: one vocab-only process per measurement."""

    def __init__(self, scratch):
        self.scratch = scratch
        self.calls = 0

    def count(self, text, label):
        self.scratch.mkdir(parents=True, exist_ok=True)
        path = self.scratch / (label + ".txt")
        path.write_bytes(text.encode("utf-8"))
        argv = [str(TOKENIZE), "-m", str(GGUF), "-f", str(path), "--no-bos",
                "--no-escape", "--show-count", "--log-disable", "--ids"]
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.calls += 1
        path.unlink()
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                return int(line.split(":")[1].strip())
        raise RuntimeError("local tokenizer produced no count for " + label)


def measure_tokens(jobs, scratch):
    """jobs: {sha256(text): text}. Keyed output, so the 4-way pool cannot
    change the result bytes."""
    tokenizer = Tokenizer(scratch)
    keys = sorted(jobs)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        counts = list(pool.map(lambda k: tokenizer.count(jobs[k], k[:24]), keys))
    return dict(zip(keys, counts)), tokenizer.calls


# --------------------------------------------------------------------------
def role_row(rows):
    supplied = [len(r["evidence_ids"]) for r in rows]
    distinct_id = [len(set(r["evidence_ids"])) for r in rows]
    distinct_body = [len(set(r["body_sha256"])) for r in rows]
    distinct_norm = [len(set(r["normalised_sha256"])) for r in rows]
    per_store = Counter()
    for row in rows:
        for evidence_id in row["evidence_ids"]:
            per_store[store_of(evidence_id)] += 1
    return {
        "n_contacts": len(rows),
        "supplied_items": stats(supplied),
        "distinct_evidence_ids": stats(distinct_id),
        "distinct_bodies": stats(distinct_body),
        "distinct_normalised_bodies": stats(distinct_norm),
        "contacts_with_repeated_evidence_id": sum(
            1 for a, b in zip(supplied, distinct_id) if a != b),
        "contacts_with_repeated_body": sum(
            1 for a, b in zip(supplied, distinct_body) if a != b),
        "contacts_with_repeated_normalised_body": sum(
            1 for a, b in zip(supplied, distinct_norm) if a != b),
        "repeated_body_items_total": sum(
            a - b for a, b in zip(supplied, distinct_body)),
        "items_by_store": sorted(per_store.items()),
        "prompt_tokens": stats(
            [r["prompt_tokens"] for r in rows if r["prompt_tokens"] is not None]),
        "distinct_supply_blocks": len({r["block_sha256"] for r in rows}),
    }


def cut_waste(ranked_keys, key_to_value, bodies):
    """The budget cut falls on KEYS before any value-level dedup (kb_policy.py
    line 713 for the supplyfilter fuser, line 833 for the associated-values
    fuser). Resolve every ranked key to its value and count the slots a
    dedup-BEFORE-cut stage could have reclaimed."""
    seen_values, seen_bodies = set(), set()
    repeat_value = repeat_body = unresolved = 0
    for key in ranked_keys:
        mapped = key_to_value.get(key)
        if not mapped:
            unresolved += 1
            continue
        value_id = mapped[0]
        if value_id in seen_values:
            repeat_value += 1
        seen_values.add(value_id)
        body = bodies.get(value_id)
        if body is None:
            continue
        digest = sha(body)
        if digest in seen_bodies:
            repeat_body += 1
        seen_bodies.add(digest)
    return {
        "ranked_keys": len(ranked_keys),
        "keys_resolving_to_a_repeated_value": repeat_value,
        "keys_resolving_to_a_repeated_body": repeat_body,
        "keys_with_no_value_in_a_released_store": unresolved,
        "distinct_values_behind_the_ranked_keys": len(seen_values),
    }


def acquisition_rows(episodes, bodies, key_to_value):
    out = []
    for episode in sorted(episodes):
        for wave in episodes[episode]["waves"]:
            if wave["fusion_policy_id"] is None:
                continue
            keys, values = wave["supporting_keys"], wave["selected_values"]
            out.append({
                "settling_role": wave["role"],
                "ranking_policy_id": wave["ranking_policy_id"],
                "fusion_policy_id": wave["fusion_policy_id"],
                "n_ranked_keys": len(wave["ranked_keys"]),
                "ranked_by_store": Counter(store_of(k) for k in wave["ranked_keys"]),
                "top5_ranked_by_store": Counter(
                    store_of(k) for k in wave["ranked_keys"][:5]),
                "top10_ranked_by_store": Counter(
                    store_of(k) for k in wave["ranked_keys"][:10]),
                "n_keys": len(keys),
                "n_values": len(values),
                "keys_by_store": Counter(store_of(k) for k in keys),
                "values_by_store": Counter(store_of(v) for v in values),
                "cut_waste": cut_waste(wave["ranked_keys"], key_to_value, bodies),
                "bodies": [sha(bodies[v]) for v in values if v in bodies],
                "value_order": values,
            })
    return out


def top_set_changes(acquisitions, bodies):
    """Does collapsing repeated bodies change the top-5/top-10 distinct-value
    SET taken off the ranked list?"""
    top5 = top10 = 0
    for acquisition in acquisitions:
        raw = [v for v in acquisition["value_order"] if v in bodies]
        seen, deduped = set(), []
        for value_id in raw:
            key = sha(bodies[value_id])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(value_id)
        if set(raw[:5]) != set(deduped[:5]):
            top5 += 1
        if set(raw[:10]) != set(deduped[:10]):
            top10 += 1
    return top5, top10


def episode_item_transmission(contacts):
    """Exact, over every episode: how many supply ITEMS the episode sent in
    total across its node contacts, versus how many distinct bodies it ever
    needed to send once."""
    by_sample = defaultdict(list)
    for flight in sorted(contacts):
        by_sample[contacts[flight]["sample_id"]].append(contacts[flight])
    sent, unique_bodies, ratios = [], [], []
    for sample_id in sorted(by_sample):
        rows = by_sample[sample_id]
        total = sum(len(r["evidence_ids"]) for r in rows)
        seen = set()
        for row in rows:
            seen.update(row["body_sha256"])
        sent.append(total)
        unique_bodies.append(len(seen))
        if seen:
            ratios.append(round(total / len(seen), 4))
    return {
        "n_episodes": len(by_sample),
        "items_sent_per_episode": stats(sent),
        "distinct_bodies_per_episode": stats(unique_bodies),
        "sent_over_distinct_ratio": stats(ratios),
    }


def round_robin(candidate_ids, mapped, *, per_candidate, total, dedup):
    """``select_candidate_semantic_values`` (knowledge_provider.py:1341) with its
    value-level dedup either on (as flown) or off (the counterfactual)."""
    positions = [0] * len(candidate_ids)
    taken = [[] for _ in candidate_ids]
    selected, seen = [], set()
    while len(selected) < total:
        progressed = False
        for index, candidate_id in enumerate(candidate_ids):
            if len(selected) >= total or len(taken[index]) >= per_candidate:
                continue
            values = mapped.get(candidate_id) or []
            while positions[index] < len(values):
                value_id = values[positions[index]]
                positions[index] += 1
                progressed = True
                if dedup and value_id in seen:
                    continue
                selected.append(value_id)
                seen.add(value_id)
                taken[index].append(value_id)
                break
        if not progressed:
            break
        if all(positions[i] >= len(mapped.get(c) or [])
               or len(taken[i]) >= per_candidate
               for i, c in enumerate(candidate_ids)):
            break
    return selected


def candidate_route(run_id, bodies, jobs, sampled_sample_ids):
    """The slot-contract candidate route, read off the sealed selection audits
    in ``flight-receipts.json``: the one place the key -> value fan-in and the
    dedup that collapses it are both recorded."""
    run_dir = DATA / "runs" / run_id
    receipts = sorted(run_dir.glob("*/flight-receipts.json"))[0]
    document = json.loads(receipts.read_text(encoding="utf-8"))
    audits = (document["stages"]["run_phases"]["phase_supply"]
              .get("candidate_selections") or {})
    mapped_slots = selected = 0
    reasons, within_row_fanin, per_value_candidates = Counter(), Counter(), defaultdict(set)
    flown_counts, nodedup_counts, store_roles, policies = [], [], Counter(), Counter()
    pairs = {}
    for key in sorted(audits):
        audit = audits[key]
        store_roles[audit["store_role"]] += 1
        policies[audit["selection_policy_id"]] += 1
        candidate_ids = list(audit["candidate_ids"])
        mapped = {m["candidate_id"]: list(m["mapped_value_ids"])
                  for m in audit["mappings"]}
        row = Counter()
        for candidate_id in candidate_ids:
            for value_id in mapped.get(candidate_id) or []:
                mapped_slots += 1
                row[value_id] += 1
                per_value_candidates[value_id].add(candidate_id)
        within_row_fanin.update(row.values())
        for mapping in audit["mappings"]:
            for ignored in mapping["ignored_mappings"]:
                reasons[ignored["reason"]] += 1
        flown = list(audit["selected_value_ids"])
        selected += len(flown)
        counterfactual = round_robin(
            candidate_ids, mapped,
            per_candidate=audit["max_values_per_candidate"],
            total=audit["max_total_values"], dedup=False)
        flown_counts.append(len(flown))
        nodedup_counts.append(len(counterfactual))
        sample_id = audit["sample_id"]
        if sample_id in sampled_sample_ids and sample_id not in pairs:
            flown_block = "\n".join(
                "[value " + v + "] " + bodies["slot-contracts::" + v]
                for v in flown if "slot-contracts::" + v in bodies)
            nodedup_block = "\n".join(
                "[value " + v + "] " + bodies["slot-contracts::" + v]
                for v in counterfactual if "slot-contracts::" + v in bodies)
            jobs[sha(flown_block)] = flown_block
            jobs[sha(nodedup_block)] = nodedup_block
            pairs[sample_id] = {
                "flown_block_sha256": sha(flown_block),
                "nodedup_block_sha256": sha(nodedup_block),
                "flown_items": len(flown),
                "nodedup_items": len(counterfactual),
            }
    return {
        "receipts_relpath": str(receipts.relative_to(DATA)),
        "n_audits": len(audits),
        "store_roles": sorted(store_roles.items()),
        "selection_policy_ids": sorted(policies.items()),
        "mapped_key_slots_total": mapped_slots,
        "values_selected_total": selected,
        "mapped_over_selected_ratio": (
            None if not selected else round(mapped_slots / selected, 4)),
        "ignored_reasons": sorted(reasons.items()),
        "within_row_candidates_per_mapped_value": sorted(within_row_fanin.items()),
        "distinct_values_ever_mapped": len(per_value_candidates),
        "global_candidates_per_value": sorted(
            Counter(len(v) for v in per_value_candidates.values()).items()),
        "flown_values_per_row": stats(flown_counts),
        "no_dedup_values_per_row": stats(nodedup_counts),
    }, pairs


def episode_token_sample(contacts, jobs):
    """Deterministic stride sample of episodes; register every contact block
    and the episode's widest (union) block for tokenisation."""
    by_sample = defaultdict(list)
    for flight in sorted(contacts):
        by_sample[contacts[flight]["sample_id"]].append(contacts[flight])
    ordered = sorted(by_sample)
    stride = max(1, len(ordered) // EPISODE_SAMPLE)
    sample = {}
    for sample_id in ordered[::stride][:EPISODE_SAMPLE]:
        rows = by_sample[sample_id]
        entry = {"contacts": []}
        for row in rows:
            jobs[row["block_sha256"]] = row["block"]
            jobs[sha(row["dedup_block"])] = row["dedup_block"]
            entry["contacts"].append({
                "role": row["role"],
                "block_sha256": row["block_sha256"],
                "dedup_block_sha256": sha(row["dedup_block"]),
            })
        widest = max(rows, key=lambda r: len(r["evidence_ids"]))
        entry["union_block_sha256"] = widest["block_sha256"]
        entry["union_items"] = len(set().union(
            *[set(r["evidence_ids"]) for r in rows]))
        sample[sample_id] = entry
    return sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repo", type=Path,
                        default=Path(__file__).resolve().parents[2])
    parser.add_argument("--scratch", type=Path, default=Path("/tmp/saea-dedup-tok"))
    args = parser.parse_args()

    stores, bodies, key_to_value = read_stores()
    configs = read_configs(args.repo)

    per_arm, samples, changed, route_pairs, jobs = {}, {}, {}, {}, {}
    for run_id, stem, exemplar_k in ARMS:
        scanned = scan(run_id)
        contacts, episodes = scanned["contacts"], scanned["episodes"]
        by_role = defaultdict(list)
        for flight in sorted(contacts):
            by_role[contacts[flight]["role"]].append(contacts[flight])

        roles = {}
        for role in ROLES:
            rows = by_role.get(role) or []
            roles[role] = role_row(rows) if rows else {"n_contacts": 0}

        acquisitions = acquisition_rows(episodes, bodies, key_to_value)
        ranked_store, keys_store, values_store = Counter(), Counter(), Counter()
        top5_store, top10_store = Counter(), Counter()
        for acquisition in acquisitions:
            ranked_store.update(acquisition["ranked_by_store"])
            keys_store.update(acquisition["keys_by_store"])
            values_store.update(acquisition["values_by_store"])
            top5_store.update(acquisition["top5_ranked_by_store"])
            top10_store.update(acquisition["top10_ranked_by_store"])
        top5, top10 = top_set_changes(acquisitions, bodies)

        samples[run_id] = episode_token_sample(contacts, jobs)
        route, route_pairs[run_id] = candidate_route(
            run_id, bodies, jobs, set(samples[run_id]))
        changed[run_id] = []
        for flight in sorted(contacts):
            row = contacts[flight]
            if row["dedup_block"] == row["block"]:
                continue
            jobs[row["block_sha256"]] = row["block"]
            jobs[sha(row["dedup_block"])] = row["dedup_block"]
            changed[run_id].append({
                "role": row["role"],
                "items": len(row["evidence_ids"]),
                "distinct_bodies": len(set(row["body_sha256"])),
                "block_sha256": row["block_sha256"],
                "dedup_block_sha256": sha(row["dedup_block"]),
            })

        per_arm[run_id] = {
            "config_fragment": stem,
            "exemplar_store_k": exemplar_k,
            "trace_relpath": scanned["trace_relpath"],
            "n_episodes": len(episodes),
            "n_contacts": len(contacts),
            "waves_per_episode": sorted(Counter(
                episodes[e]["n_waves"] for e in episodes).items()),
            "acquire_transitions_per_episode": sorted(Counter(
                episodes[e]["n_acquire"] for e in episodes).items()),
            "roles": roles,
            "candidate_route": route,
            "episode_item_transmission": episode_item_transmission(contacts),
            "acquisitions": {
                "n": len(acquisitions),
                "settling_roles": sorted(Counter(
                    a["settling_role"] for a in acquisitions).items()),
                "ranking_policy_ids": sorted(Counter(
                    a["ranking_policy_id"] for a in acquisitions).items()),
                "fusion_policy_ids": sorted(Counter(
                    a["fusion_policy_id"] for a in acquisitions).items()),
                "n_ranked_keys": stats([a["n_ranked_keys"] for a in acquisitions]),
                "n_keys_after_cut": stats([a["n_keys"] for a in acquisitions]),
                "n_values": stats([a["n_values"] for a in acquisitions]),
                "keys_gt_values": sum(
                    1 for a in acquisitions if a["n_keys"] > a["n_values"]),
                "values_gt_keys": sum(
                    1 for a in acquisitions if a["n_values"] > a["n_keys"]),
                "keys_eq_values": sum(
                    1 for a in acquisitions if a["n_keys"] == a["n_values"]),
                "keys_resolving_to_a_repeated_value": stats(
                    [a["cut_waste"]["keys_resolving_to_a_repeated_value"]
                     for a in acquisitions]),
                "keys_resolving_to_a_repeated_body": stats(
                    [a["cut_waste"]["keys_resolving_to_a_repeated_body"]
                     for a in acquisitions]),
                "keys_with_no_value_in_a_released_store": stats(
                    [a["cut_waste"]["keys_with_no_value_in_a_released_store"]
                     for a in acquisitions]),
                "distinct_values_behind_the_ranked_keys": stats(
                    [a["cut_waste"]["distinct_values_behind_the_ranked_keys"]
                     for a in acquisitions]),
                "distinct_bodies": stats(
                    [len(set(a["bodies"])) for a in acquisitions]),
                "ranked_keys_by_store": sorted(ranked_store.items()),
                "composite_top5_keys_by_store": sorted(top5_store.items()),
                "composite_top10_keys_by_store": sorted(top10_store.items()),
                "keys_after_cut_by_store": sorted(keys_store.items()),
                "values_by_store": sorted(values_store.items()),
                "top5_set_changed_by_body_dedup": top5,
                "top10_set_changed_by_body_dedup": top10,
            },
        }

    tokens, calls = measure_tokens(jobs, args.scratch)

    budget = {}
    for run_id, _stem, _k in ARMS:
        by_role_blocks = defaultdict(list)
        episode_sent, episode_union, episode_repeat = [], [], []
        for sample_id in sorted(samples[run_id]):
            entry = samples[run_id][sample_id]
            total = 0
            for contact in entry["contacts"]:
                flown = tokens[contact["block_sha256"]]
                by_role_blocks[contact["role"]].append(flown)
                total += flown
            union = tokens[entry["union_block_sha256"]]
            episode_sent.append(total)
            episode_union.append(union)
            episode_repeat.append(total - union)
        exhaustive = [
            {
                "role": entry["role"],
                "items": entry["items"],
                "distinct_bodies": entry["distinct_bodies"],
                "flown_block_tokens": tokens[entry["block_sha256"]],
                "dedup_block_tokens": tokens[entry["dedup_block_sha256"]],
                "freed_tokens": (tokens[entry["block_sha256"]]
                                 - tokens[entry["dedup_block_sha256"]]),
            }
            for entry in changed[run_id]
        ]
        route_flown, route_nodedup, route_freed = [], [], []
        for sample_id in sorted(route_pairs[run_id]):
            pair = route_pairs[run_id][sample_id]
            flown = tokens[pair["flown_block_sha256"]]
            nodedup = tokens[pair["nodedup_block_sha256"]]
            route_flown.append(flown)
            route_nodedup.append(nodedup)
            route_freed.append(nodedup - flown)
        budget[run_id] = {
            "sampled_episodes": len(samples[run_id]),
            "candidate_route_sampled_rows": len(route_pairs[run_id]),
            "candidate_route_flown_block_tokens": stats(route_flown),
            "candidate_route_no_dedup_block_tokens": stats(route_nodedup),
            "candidate_route_tokens_the_existing_dedup_already_frees": stats(route_freed),
            "per_role_block_tokens": {
                role: stats(values)
                for role, values in sorted(by_role_blocks.items())},
            "episode_supply_tokens_sent": stats(episode_sent),
            "episode_union_supply_tokens": stats(episode_union),
            "episode_retransmitted_tokens": stats(episode_repeat),
            "episode_retransmitted_fraction": (
                None if not episode_sent
                else round(sum(episode_repeat) / sum(episode_sent), 6)),
            "contacts_body_dedup_would_change": len(exhaustive),
            "body_dedup_changed_contacts": sorted(
                exhaustive, key=lambda e: (e["role"], e["freed_tokens"])),
            "body_dedup_freed_tokens_total": sum(
                e["freed_tokens"] for e in exhaustive),
        }

    report = {
        "schema": "saea-slurp-supply-dedup-and-rerank-measurement-v1",
        "contact_class": "model-free",
        "tools": {
            "tokenizer_binary": str(TOKENIZE),
            "tokenizer_model_relpath": str(GGUF.relative_to(DATA)),
            "tokenizer_mode": "vocab-only local process: no server, no port, no GPU",
            "tokenizer_invocations": calls,
            "workers": WORKERS,
            "episode_sample_per_arm": EPISODE_SAMPLE,
        },
        "released_stores": stores,
        "registered_supply_configuration": configs,
        "sealed_arms": per_arm,
        "budget": budget,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8")
    print("wrote " + str(args.out) + " sha256="
          + sha(args.out.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()
