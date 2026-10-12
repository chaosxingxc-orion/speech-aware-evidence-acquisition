"""Measure the composition, relevance and counterfactual size of the four
knowledge-edit group contexts (owner decision 126).

Model-free and local. The script reads the prepared artifact, re-serialises each
model context with the same canonical rule the preparation rail uses, attributes
every canonical byte to exactly one category and to exactly one relevance class,
counts tokens with the local ``llama-tokenize`` binary (vocab only, no server, no
port, no GPU), and prices a retrieved-and-filtered counterfactual against the live
serving slot. It prints labels, ids, counts, byte sizes, token counts and hashes;
it never prints utterance text, transcripts, gold labels or model output.

Run:
    python -B scripts/analysis/knowledge_edit_context_composition.py \
        --out /tmp/knowledge-edit-context-composition.json
"""

from __future__ import annotations
import os

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from speech_aware_evidence_acquisition.analysis.shared_json import (
    restore_json,
    share_json,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash

DEFAULT_DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
PREPARED_RELPATH = (
    "coordination/slurp-system-knowledge-value001-group-v1/prepared-contexts-v1.json"
)
GGUF_RELPATH = (
    "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/"
    "Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf"
)
DEFAULT_TOKENIZE = Path("/home/chao/llama.cpp/build/bin/llama-tokenize")

# composition categories
ROLE = "role_contacts"
TOOL = "actual_tool_records"
KNOW = "supplied_knowledge_bodies"
CTRL = "control_and_delivery"
TERM = "terminal_feedback"
EDIT = "edit_surface"
SCAF = "json_scaffolding"
REFS = "reference_resolution"
CATEGORIES = (ROLE, TOOL, KNOW, CTRL, TERM, EDIT, SCAF, REFS)

# relevance classes
FRAME = "instruction_and_contract"
ON = "on_edit_surface"
MAY = "may_bear"
CANNOT = "cannot_bear"

# serving geometry of the pinned fragment q4km-mmproj-free-system-np1-ctx48k-...
SLOT_TOKENS = 49_152
UNDECLARED_SLOT_CEILING = 32_768  # rails.context_budget.PER_SLOT_LIMIT_TOKENS
REGISTERED_RESERVE = 8_192  # rails.context_budget.OPERATIONAL_RESERVE_TOKENS
ONE_EIGHTH_RESERVE = SLOT_TOKENS // 8
COMPLETION_RESERVE = 1_024
SPECIAL_RESERVE = 2  # rails.context_budget.REGISTERED_SPECIAL_TOKEN_RESERVE

HEX64 = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")


def canonical(value) -> str:
    """The exact serialisation ``rails.prepared_feedback._canonical_context`` uses."""
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def expand(node, pool):
    """Expand one fragment of a shared document so its own size can be priced."""
    if isinstance(node, dict):
        if set(node) == {"$ref"}:
            return expand(pool[node["$ref"]], pool)
        if set(node) == {"$object"}:
            return {key: expand(value, pool) for key, value in node["$object"]}
        return {key: expand(value, pool) for key, value in node.items()}
    if isinstance(node, list):
        return [expand(item, pool) for item in node]
    return node


class Emitter:
    """Re-emit canonical JSON, charging every byte to one label."""

    def __init__(self, labels, *, ref_label=None, pool=None):
        self.labels = labels
        self.ref_label = ref_label or {}
        self.pool = pool
        self.segments: list[tuple[str, str]] = []

    def put(self, label: str, text: str) -> None:
        if self.segments and self.segments[-1][0] == label:
            self.segments[-1] = (label, self.segments[-1][1] + text)
        else:
            self.segments.append((label, text))

    def dump(self, node, inherited: str) -> None:
        label = self.labels.get(id(node), inherited)
        if self.pool is not None and node is self.pool:
            self.put(label, "{")
            first = True
            for key in sorted(node):
                if not first:
                    self.put(label, ",")
                first = False
                self.put(label, canonical(key))
                self.put(label, ":")
                self.dump(node[key], self.ref_label.get(key, label))
            self.put(label, "}")
            return
        if isinstance(node, dict):
            self.put(label, "{")
            first = True
            for key in sorted(node):
                if not first:
                    self.put(label, ",")
                first = False
                self.put(label, canonical(key))
                self.put(label, ":")
                self.dump(node[key], label)
            self.put(label, "}")
        elif isinstance(node, list):
            self.put(label, "[")
            for index, item in enumerate(node):
                if index:
                    self.put(label, ",")
                self.dump(item, label)
            self.put(label, "]")
        else:
            self.put(label, canonical(node))


class Walk:
    """Structural walk of one shared group context, labelling every container."""

    def __init__(self, pool, *, mapping):
        self.pool = pool
        self.map = mapping
        self.labels: dict[int, str] = {}
        self.ref_labels: dict[str, Counter] = defaultdict(Counter)
        self.seen: set[tuple[int, str]] = set()
        self.conflicts = 0
        self.supply: list[tuple[str, str | None]] = []

    # ---- labelling primitives ------------------------------------------- #
    def assign(self, node, label) -> None:
        if not isinstance(node, (dict, list)):
            return
        prior = self.labels.get(id(node))
        if prior is None:
            self.labels[id(node)] = label
        elif prior != label:
            self.conflicts += 1

    def deref(self, node, label):
        if isinstance(node, dict) and set(node) == {"$ref"}:
            ref = node["$ref"]
            self.assign(node, REFS)
            self.ref_labels[ref][label] += 1
            return self.pool[ref], ref
        return node, None

    @staticmethod
    def as_map(node):
        if isinstance(node, dict) and set(node) == {"$object"}:
            return {pair[0]: pair[1] for pair in node["$object"]}, True
        return node, False

    def mark(self, node, label) -> None:
        node, ref = self.deref(node, label)
        if ref is not None:
            if (id(node), label) in self.seen:
                return
            self.seen.add((id(node), label))
        if isinstance(node, dict):
            self.assign(node, label)
            mapped, escaped = self.as_map(node)
            if escaped:
                self.assign(node["$object"], REFS)
                for pair in node["$object"]:
                    self.assign(pair, REFS)
            for value in mapped.values():
                self.mark(value, label)
        elif isinstance(node, list):
            self.assign(node, label)
            for item in node:
                self.mark(item, label)

    def resolved_ref_labels(self):
        """One label per pool entry: its most frequent referencing label."""
        chosen, ambiguous = {}, 0
        for ref, counts in self.ref_labels.items():
            if len(counts) > 1:
                ambiguous += 1
            chosen[ref] = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        return chosen, ambiguous

    def open(self, node, label):
        """Dereference, unescape and label one container in one step."""
        node, _ = self.deref(node, label)
        mapped, _ = self.as_map(node)
        self.assign(node, label)
        return mapped

    # ---- structure ------------------------------------------------------- #
    def context(self, ctx) -> None:
        self.assign(ctx, self.map["context"])
        for key, value in ctx.items():
            if key == "evidence":
                self.evidence(value)
            else:
                self.mark(value, self.map["top"][key])

    def evidence(self, ev) -> None:
        self.assign(ev, self.map["frame"])
        self.assign(ev["shared"], REFS)
        root = self.open(ev["episode"], self.map["frame"])
        self.cards(root["base_slot_rows"])
        groups = self.open_list(root["groups"])
        for group in groups:
            self.group(group)

    def open_list(self, node):
        node, _ = self.deref(node, self.map["frame"])
        self.assign(node, self.map["frame"])
        return node

    def cards(self, node) -> None:
        if self.map["card_fields"] is None:
            self.mark(node, self.map["edit"])
            return
        rows = self.open_list(node)
        for row in rows:
            card = self.open(row, self.map["card_other"])
            for key, value in card.items():
                self.mark(
                    value,
                    self.map["edit"]
                    if key in self.map["card_fields"]
                    else self.map["card_other"],
                )

    def group(self, node) -> None:
        mapped = self.open(node, self.map["frame"])
        for key, value in mapped.items():
            if key == "outcome_variation":
                self.mark(value, self.map["terminal"])
            elif key == "attempts":
                for attempt in self.open_list(value):
                    self.attempt(attempt)
            else:
                self.mark(value, self.map["frame"])

    def attempt(self, node) -> None:
        mapped = self.open(node, self.map["frame"])
        self.mark(mapped["terminal_feedback"], self.map["terminal"])
        self.episode(mapped["episode"])

    def episode(self, node) -> None:
        mapped = self.open(node, self.map["frame"])
        for key, value in mapped.items():
            if key == "actual_tool_records":
                self.tool_records(value)
            elif key == "delivered_text":
                self.mark(value, self.map["delivered"])
            elif key in ("control_receipt", "delivery", "timeline_record_ids"):
                self.mark(value, self.map["control"])
            elif key == "contacts":
                for contact in self.open_list(value):
                    self.contact(contact)
            else:
                self.mark(value, self.map["frame"])

    def tool_records(self, node) -> None:
        if self.map["tool_arguments"] is None:
            self.mark(node, self.map["tool"])
            return
        for record in self.open_list(node):
            mapped = self.open(record, self.map["tool"])
            for key, value in mapped.items():
                if key != "record":
                    self.mark(value, self.map["tool"])
                    continue
                body = self.open(value, self.map["tool"])
                for field, item in body.items():
                    self.mark(
                        item,
                        self.map["tool_arguments"]
                        if field == "use_arguments"
                        else self.map["tool"],
                    )

    def contact(self, node) -> None:
        mapped = self.open(node, self.map["role"])
        for key, value in mapped.items():
            if key == "recorded_request":
                self.request(value)
            else:
                self.mark(value, self.map["role"])

    def request(self, node) -> None:
        mapped = self.open(node, self.map["role"])
        for key, value in mapped.items():
            if key == "supplied_evidence":
                self.supplied(value)
            elif key == "history":
                node_list, _ = self.deref(value, self.map["role"])
                self.assign(node_list, self.map["role"])
                for state in node_list:
                    self.state(state)
            else:
                self.mark(value, self.map["role"])

    def state(self, node) -> None:
        resolved, _ = self.deref(node, self.map["role"])
        mapped, _ = self.as_map(resolved)
        role = mapped.get("role") if isinstance(mapped, dict) else None
        kind = mapped.get("state_kind") if isinstance(mapped, dict) else None
        control = role == "control" or kind == "tool-result"
        self.mark(node, self.map["control"] if control else self.map["role"])

    def supplied(self, node) -> None:
        items, _ = self.deref(node, self.map["supply_other"])
        self.assign(items, self.map["supply_other"])
        for item in items:
            resolved, ref = self.deref(item, self.map["supply_other"])
            evidence_id = expand(resolved, self.pool)["evidence_id"]
            self.supply.append((evidence_id, ref))
            editable = evidence_id.startswith(
                "slot-contracts::"
            ) and evidence_id.split(":")[-1] in self.map["editable_slots"]
            self.mark(
                item,
                self.map["supply_editable"] if editable else self.map["supply_other"],
            )


def composition_mapping(editable_slots):
    """Labels for the composition decomposition: one per evidence category."""
    return {
        "context": SCAF,
        "top": {
            "stage": SCAF,
            "context_view": SCAF,
            "reading_contract": SCAF,
            "edit_contract": EDIT,
            "feedback_definition": TERM,
        },
        "frame": SCAF,
        "edit": EDIT,
        "card_fields": None,
        "card_other": EDIT,
        "terminal": TERM,
        "control": CTRL,
        "delivered": CTRL,
        "tool": TOOL,
        "tool_arguments": None,
        "role": ROLE,
        "supply_editable": KNOW,
        "supply_other": KNOW,
        "editable_slots": set(editable_slots),
    }


def relevance_mapping(editable_slots, editable_fields):
    """Labels for the relevance split, generous towards the may-bear class."""
    return {
        "context": FRAME,
        "top": {
            "stage": FRAME,
            "context_view": FRAME,
            "reading_contract": FRAME,
            "edit_contract": FRAME,
            "feedback_definition": FRAME,
        },
        "frame": CANNOT,
        "edit": ON,
        "card_fields": set(editable_fields),
        "card_other": CANNOT,
        "terminal": MAY,
        "control": CANNOT,
        "delivered": MAY,
        "tool": CANNOT,
        "tool_arguments": MAY,
        "role": MAY,
        "supply_editable": MAY,
        "supply_other": CANNOT,
        "editable_slots": set(editable_slots),
    }


class Tokenizer:
    """The local llama.cpp tokenizer: one vocab-only process per measurement."""

    def __init__(self, binary: Path, model: Path, scratch: Path):
        self.binary, self.model, self.scratch = binary, model, scratch
        self.cache: dict[str, int] = {}
        self.invocations = 0

    def count(self, text: str, label: str, *, parse_special: bool = True) -> int:
        key = content_hash(text) + ("|special" if parse_special else "|literal")
        if key in self.cache:
            return self.cache[key]
        self.scratch.mkdir(parents=True, exist_ok=True)
        path = self.scratch / f"{label}.txt"
        path.write_bytes(text.encode("utf-8"))
        argv = [
            str(self.binary),
            "-m",
            str(self.model),
            "-f",
            str(path),
            "--no-bos",
            "--no-escape",
            "--show-count",
            "--log-disable",
            "--ids",
        ]
        if not parse_special:
            argv.append("--no-parse-special")
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.invocations += 1
        path.unlink()
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                count = int(line.split(":")[1].strip())
                self.cache[key] = count
                return count
        raise RuntimeError(f"local tokenizer produced no count for {label}")


def fit(total_tokens: int, slot: int, reserve: int) -> dict[str, int]:
    required = total_tokens + SPECIAL_RESERVE + COMPLETION_RESERVE
    physical = slot - required
    return {
        "required_window_tokens": required,
        "physical_margin_tokens": physical,
        "operational_margin_tokens": physical - reserve,
    }


def all_fits(total_tokens: int) -> dict[str, dict[str, int]]:
    return {
        "live_slot_49152_registered_reserve_8192": fit(
            total_tokens, SLOT_TOKENS, REGISTERED_RESERVE
        ),
        "live_slot_49152_one_eighth_reserve_6144": fit(
            total_tokens, SLOT_TOKENS, ONE_EIGHTH_RESERVE
        ),
        "undeclared_budget_ceiling_32768_reserve_8192": fit(
            total_tokens, UNDECLARED_SLOT_CEILING, REGISTERED_RESERVE
        ),
    }


def split(segments, total_bytes, tokenizer, label):
    """Bytes and tokens per label; tokens are measured on each label's own bytes."""
    by_bytes, by_text = Counter(), defaultdict(list)
    for name, chunk in segments:
        by_bytes[name] += len(chunk.encode("utf-8"))
        by_text[name].append(chunk)
    assert sum(by_bytes.values()) == total_bytes
    by_tokens = {
        name: tokenizer.count("".join(by_text[name]), f"{label}-{name}")
        for name in by_bytes
    }
    token_sum = sum(by_tokens.values())
    return {
        name: {
            "bytes": by_bytes[name],
            "bytes_share_percent": round(100.0 * by_bytes[name] / total_bytes, 2),
            "tokens": by_tokens[name],
            "tokens_share_percent": round(100.0 * by_tokens[name] / token_sum, 2),
        }
        for name in sorted(by_bytes)
    }, token_sum


def counterfactuals(ctx, group, cards, contract_editable, pool, supply_refs, slots):
    """Price the retrieved-matched-filtered contexts, and their components."""
    by_slot = {row["slot_id"]: row for row in cards}
    field_values = [
        {
            "slot_id": slot,
            "field": field,
            "previous_value_sha256": content_hash(by_slot[slot][field]),
            "current_value": by_slot[slot][field],
        }
        for slot, field in contract_editable
    ]
    retrieved = [
        {"retrieval_key": evidence_id, "unit": expand(pool[ref], pool)}
        for ref, evidence_id in sorted(supply_refs.items(), key=lambda kv: kv[1])
        if evidence_id.startswith("slot-contracts::")
        and evidence_id.split(":")[-1] in slots
    ]
    outcomes = [
        {
            key: attempt["terminal_feedback"][key]
            for key in (
                "attempt_id", "tp", "fp", "fn", "intent_exact", "format_ok",
                "utility", "episode_sha256",
            )
        }
        for attempt in group["attempts"]
    ]
    deliveries = [
        {
            "attempt_id": attempt["terminal_feedback"]["attempt_id"],
            "delivered_text": attempt["episode"]["delivered_text"],
            "terminal_reason": attempt["episode"]["delivery"]["terminal_reason"],
            "kind": attempt["episode"]["delivery"]["kind"],
        }
        for attempt in group["attempts"]
    ]
    per_unit, per_class = [], []
    for attempt in group["attempts"]:
        episode = attempt["episode"]
        aid = attempt["terminal_feedback"]["attempt_id"]
        for contact in episode["contacts"]:
            per_unit.append(
                {
                    "unit": "role-contact",
                    "attempt_id": aid,
                    "role_id": contact["role_id"],
                    "visit_index": contact["visit_index"],
                    "source_sha256": content_hash(contact),
                    "disposition": "not keyed to an editable field; source retained",
                }
            )
        for record in episode["actual_tool_records"]:
            per_unit.append(
                {
                    "unit": "actual-tool-record",
                    "attempt_id": aid,
                    "record_id": record["record_id"],
                    "source_sha256": record["source_record_sha256"],
                    "disposition": "not keyed to an editable field; source retained",
                }
            )
        custody = content_hash(
            {
                "control_receipt": episode["control_receipt"],
                "delivery": episode["delivery"],
                "timeline_record_ids": episode["timeline_record_ids"],
            }
        )
        per_unit.append(
            {
                "unit": "control-and-delivery",
                "attempt_id": aid,
                "fields": ["control_receipt", "delivery", "timeline_record_ids"],
                "source_sha256": custody,
                "disposition": "custody and route metadata; source retained",
            }
        )
        for name, units, digest in (
            ("role-contacts", len(episode["contacts"]),
             content_hash(episode["contacts"])),
            ("actual-tool-records", len(episode["actual_tool_records"]),
             content_hash(episode["actual_tool_records"])),
            ("control-and-delivery", 3, custody),
        ):
            per_class.append(
                {
                    "unit_class": name,
                    "attempt_id": aid,
                    "units": units,
                    "source_sha256": digest,
                    "disposition": "not keyed to an editable field; source retained",
                }
            )
    seen = set()
    for ref, evidence_id in sorted(supply_refs.items(), key=lambda kv: kv[1]):
        if evidence_id in seen:
            continue
        seen.add(evidence_id)
        if evidence_id.startswith("slot-contracts::") and evidence_id.split(":")[
            -1
        ] in slots:
            continue
        record = {
            "unit": "supplied-knowledge-body",
            "evidence_id": evidence_id,
            "source_sha256": content_hash(expand(pool[ref], pool)),
            "disposition": "ontology, intent binding or retrieval key; not editable",
        }
        per_unit.append(record)
        per_class.append(record)
    variants = {
        "CF-1-editable-fields-only": {
            "editable_field_values": field_values,
            "omitted_units": per_unit,
        },
        "CF-2-plus-keyed-supply": {
            "editable_field_values": field_values,
            "retrieved_units": retrieved,
            "omitted_units": per_unit,
        },
        "CF-3-plus-attempt-outcomes": {
            "editable_field_values": field_values,
            "retrieved_units": retrieved,
            "attempt_outcomes": outcomes,
            "attempt_deliveries": deliveries,
            "omitted_units": per_unit,
        },
        "CF-4-class-level-omission": {
            "editable_field_values": field_values,
            "retrieved_units": retrieved,
            "attempt_outcomes": outcomes,
            "attempt_deliveries": deliveries,
            "omitted_unit_classes": per_class,
        },
    }
    components = {
        "edit_contract": len(canonical(ctx["edit_contract"]).encode("utf-8")),
        "reading_contract": len(canonical(ctx["reading_contract"]).encode("utf-8")),
        "feedback_definition": len(
            canonical(ctx["feedback_definition"]).encode("utf-8")
        ),
        "editable_field_values": len(canonical(field_values).encode("utf-8")),
        "retrieved_units": len(canonical(retrieved).encode("utf-8")),
        "attempt_outcomes": len(canonical(outcomes).encode("utf-8")),
        "attempt_deliveries": len(canonical(deliveries).encode("utf-8")),
        "omitted_units_per_unit": len(canonical(per_unit).encode("utf-8")),
        "omitted_units_per_class": len(canonical(per_class).encode("utf-8")),
    }
    return variants, components, len(retrieved), len(per_unit), len(per_class)


def measure(data_root: Path, tokenizer: Tokenizer) -> dict:
    prepared = data_root / PREPARED_RELPATH
    wrapper = json.loads(prepared.read_text(encoding="utf-8"))
    document = wrapper["output"]
    contract = document["edit_contract"]
    contract_editable = [
        (row["slot_id"], row["field"]) for row in contract["editable"]
    ]
    slots = sorted({slot for slot, _ in contract_editable})
    fields = sorted({field for _, field in contract_editable})

    report = {
        "schema": "saea-knowledge-edit-context-composition-v1",
        "prepared": {
            "relpath": PREPARED_RELPATH,
            "output_sha256": wrapper["output_sha256"],
        },
        "edit_surface_contract": {
            "editable_targets": len(contract_editable),
            "editable_slots": slots,
            "editable_fields": fields,
            "max_edits": contract["max_edits"],
            "max_field_chars": contract["max_field_chars"],
        },
        "serving_geometry": {
            "slot_tokens": SLOT_TOKENS,
            "registered_reserve_tokens": REGISTERED_RESERVE,
            "one_eighth_reserve_tokens": ONE_EIGHTH_RESERVE,
            "undeclared_budget_ceiling_tokens": UNDECLARED_SLOT_CEILING,
            "completion_reserve_tokens": COMPLETION_RESERVE,
            "special_token_reserve": SPECIAL_RESERVE,
        },
        "tokenizer": {
            "binary": str(tokenizer.binary),
            "model": str(tokenizer.model),
            "kind": "local llama.cpp vocab-only process",
            "service_contacts": 0,
            "flags": "--no-bos --no-escape --show-count --log-disable --ids",
        },
        "contacts_added": {"model": 0, "tokenizer_service": 0, "encoder": 0,
                           "scorer": 0},
        "groups": [],
    }

    for index, entry in enumerate(document["contexts"]):
        ctx = entry["model_context"]
        pool = ctx["evidence"]["shared"]
        text = canonical(ctx)
        total_bytes = len(text.encode("utf-8"))
        restored = restore_json(ctx["evidence"])
        group = restored["groups"][0]
        label = group["source_group_id"]

        total_tokens = tokenizer.count(text, f"{label}-total")
        literal_tokens = tokenizer.count(
            text, f"{label}-total-literal", parse_special=False
        )

        comp = Walk(pool, mapping=composition_mapping(slots))
        comp.context(ctx)
        comp_refs, comp_ambiguous = comp.resolved_ref_labels()
        comp_emitter = Emitter(comp.labels, ref_label=comp_refs, pool=pool)
        comp_emitter.dump(ctx, SCAF)
        assert "".join(c for _, c in comp_emitter.segments) == text
        by_category, category_token_sum = split(
            comp_emitter.segments, total_bytes, tokenizer, f"{label}-cat"
        )

        rel = Walk(pool, mapping=relevance_mapping(slots, fields))
        rel.context(ctx)
        rel_refs, rel_ambiguous = rel.resolved_ref_labels()
        rel_emitter = Emitter(rel.labels, ref_label=rel_refs, pool=pool)
        rel_emitter.dump(ctx, FRAME)
        assert "".join(c for _, c in rel_emitter.segments) == text
        by_class, class_token_sum = split(
            rel_emitter.segments, total_bytes, tokenizer, f"{label}-rel"
        )
        unusable_bytes = by_class[CANNOT]["bytes"] + by_class[REFS]["bytes"]
        unusable_tokens = by_class[CANNOT]["tokens"] + by_class[REFS]["tokens"]

        supply_refs = {ref: eid for eid, ref in comp.supply if ref is not None}
        family_bytes, family_count = Counter(), Counter()
        editable_supply_bytes = noneditable_slot_bytes = 0
        for ref, evidence_id in supply_refs.items():
            size = len(canonical(expand(pool[ref], pool)).encode("utf-8"))
            family_bytes[evidence_id.split("::", 1)[0]] += size
            family_count[evidence_id.split("::", 1)[0]] += 1
            if not evidence_id.startswith("slot-contracts::"):
                continue
            if evidence_id.split(":")[-1] in set(slots):
                editable_supply_bytes += size
            else:
                noneditable_slot_bytes += size
        supplied_slots = sorted(
            {
                eid.split(":")[-1]
                for eid, _ in comp.supply
                if eid.startswith("slot-contracts::")
            }
        )
        editable_supplied = sorted(set(supplied_slots) & set(slots))

        episodes = []
        for position, attempt in enumerate(group["attempts"]):
            episode = attempt["episode"]
            ids = {
                item["evidence_id"]
                for contact in episode["contacts"]
                for item in contact["recorded_request"].get("supplied_evidence") or []
            }
            here = {
                eid.split(":")[-1]
                for eid in ids
                if eid.startswith("slot-contracts::")
            }
            episodes.append(
                {
                    "attempt_index": position,
                    "contacts": len(episode["contacts"]),
                    "tool_records": len(episode["actual_tool_records"]),
                    "distinct_supplied_bodies": len(ids),
                    "editable_slots_present": sorted(here & set(slots)),
                    "touches_an_editable_slot": bool(here & set(slots)),
                }
            )

        variants, components, retrieved_units, per_unit_n, per_class_n = (
            counterfactuals(
                ctx, group, restored["base_slot_rows"], contract_editable, pool,
                supply_refs, set(slots),
            )
        )
        priced = {}
        for name, payload in variants.items():
            candidate = {
                "stage": ctx["stage"],
                "context_view": "retrieved-matched-filtered-slot-value-edit-v1",
                "edit_contract": ctx["edit_contract"],
                "evidence": share_json(payload),
                "feedback_definition": ctx["feedback_definition"],
                "reading_contract": ctx["reading_contract"],
            }
            candidate_text = canonical(candidate)
            candidate_bytes = len(candidate_text.encode("utf-8"))
            candidate_tokens = tokenizer.count(candidate_text, f"{label}-{name}")
            priced[name] = {
                "bytes": candidate_bytes,
                "tokens": candidate_tokens,
                "byte_reduction_factor": round(total_bytes / candidate_bytes, 2),
                "token_reduction_factor": round(total_tokens / candidate_tokens, 2),
                "retrieved_units": retrieved_units,
                "omission_records": per_class_n
                if name == "CF-4-class-level-omission"
                else per_unit_n,
                "fit": all_fits(candidate_tokens),
            }

        digests = HEX64.findall(text)
        report["groups"].append(
            {
                "source_group_id": label,
                "source_sample_id": entry["source_sample_id"],
                "model_context_sha256": entry["model_context_sha256"],
                "total_bytes": total_bytes,
                "total_tokens": total_tokens,
                "total_tokens_literal_special": literal_tokens,
                "bytes_per_token": round(total_bytes / total_tokens, 3),
                "expanded_evidence_bytes": len(
                    canonical(restored).encode("utf-8")
                ),
                "shared_pool_entries": len(pool),
                "reference_wrappers": text.count('{"$ref":"'),
                "sha256_digest_occurrences": len(digests),
                "sha256_distinct_digests": len(set(digests)),
                "by_category": by_category,
                "category_token_sum": category_token_sum,
                "category_token_boundary_residual": category_token_sum - total_tokens,
                "category_ambiguous_pool_entries": comp_ambiguous,
                "category_container_conflicts": comp.conflicts,
                "by_relevance_class": by_class,
                "relevance_token_sum": class_token_sum,
                "relevance_token_boundary_residual": class_token_sum - total_tokens,
                "relevance_ambiguous_pool_entries": rel_ambiguous,
                "relevance_container_conflicts": rel.conflicts,
                "cannot_bear_plus_pointer_bytes": unusable_bytes,
                "cannot_bear_plus_pointer_bytes_percent": round(
                    100.0 * unusable_bytes / total_bytes, 2
                ),
                "cannot_bear_plus_pointer_tokens": unusable_tokens,
                "cannot_bear_plus_pointer_tokens_percent": round(
                    100.0 * unusable_tokens / class_token_sum, 2
                ),
                "supply": {
                    "occurrences": len(comp.supply),
                    "distinct_bodies": len(supply_refs),
                    "by_family_bytes": dict(family_bytes),
                    "by_family_distinct": dict(family_count),
                    "slot_contracts_supplied": supplied_slots,
                    "editable_slots_supplied": editable_supplied,
                    "editable_slots_absent": sorted(set(slots) - set(editable_supplied)),
                    "editable_slot_body_bytes": editable_supply_bytes,
                    "noneditable_slot_body_bytes": noneditable_slot_bytes,
                    "editable_targets_without_own_group_evidence": 3
                    * (len(slots) - len(editable_supplied)),
                },
                "episodes": episodes,
                "fit_as_flown": all_fits(total_tokens),
                "counterfactual": priced,
                "counterfactual_component_bytes": components,
            }
        )
    report["batch_total_bytes"] = sum(g["total_bytes"] for g in report["groups"])
    report["batch_total_tokens"] = sum(g["total_tokens"] for g in report["groups"])
    report["tokenizer"]["invocations"] = tokenizer.invocations
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--tokenizer", type=Path, default=DEFAULT_TOKENIZE)
    parser.add_argument("--scratch", type=Path, default=Path("/tmp/saea-kec-tokenize"))
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    tokenizer = Tokenizer(
        args.tokenizer, args.data_root / GGUF_RELPATH, args.scratch
    )
    report = measure(args.data_root, tokenizer)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")


if __name__ == "__main__":
    main()
