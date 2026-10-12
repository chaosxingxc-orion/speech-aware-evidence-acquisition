"""Audit what the Reviewer and the Planner actually receive, class by class.

Owner question (2026-09-26): the Reviewer and the Planner are the two nodes that
need GLOBAL information, not local input, in order to judge and to route --
including the state of past errors and corrections. This script measures what
their rendered prompt carries today, whether the state of past errors and
corrections is in it, and what is not.

Model-free and local: reads sealed run traces and committed config fragments,
and counts tokens with the local ``llama-tokenize`` binary (vocab only -- no
server, no port, no GPU, no encoder, no scorer, zero model contacts). It prints
and persists ids, kinds, counts, token counts, ratios and hashes only; it never
prints an utterance, a transcript, a gold label, model output, a knowledge body
or a rendered instruction.

THE WIRE MODEL IT MEASURES AGAINST. One native-role contact is exactly two
messages (``reproduction.ojw.native_request``: ``len(messages) == 2``, one
system and one user), so every class below is a slice of those two. Each class
is rendered here with the SAME bytes the transport puts on the wire:

* ``system.task_instruction`` -- the composed task contract
  (``rails.runner._agent_messages``; ``payload["task_instruction"]``).
* ``user.supply.value.<store>`` -- one text part per visible value, rendered by
  ``core.model.transport`` as ``[evidence <evidence_id>] <content>``, attributed
  to the store its value id is namespaced by. The ``[evidence <id>] `` label is
  measured separately, because a 43-character namespaced id costs real tokens.
* ``user.state.<state_kind>`` -- one text part per exposed agent state, rendered
  by ``core.model.transport._speech_history_texts`` as
  ``[agent state <state_id> kind=<state_kind>] <content>``. These are the
  earlier role responses: the whole "global picture".
* ``user.role_query.instruction`` -- this node's own committed instruction
  template (``rails.phase_material``), the head of ``role_query``.
* ``user.role_query.episode_limits`` -- the ``Native episode limits: {...}``
  JSON tail ``rails.runner`` appends to every node's instruction (revision
  index, revision bound, remaining contacts, role iterations, the actions still
  open to the Planner).
* ``user.speech_query_packet`` -- the one speech-feature part. Not text, so it
  is reported as the residual of the sealed ``COST.prompt_tokens`` against the
  measured text, together with the chat-template frame and the per-part
  tokenizer boundary. The residual is the accounting's own check: it must be
  the SAME for every role of one arm, because every contact of a row carries
  the same single packet.
* ``sealed_only.control_envelope`` -- the ``history[-1]`` control record.
  Sealed custody, NOT prompt: ``core.model.native_framework_history.
  project_native_framework_history`` rebuilds the user turn from ``history[:-1]``
  and appends only ``framework[1]["content"]`` (the role query), so the
  envelope's bytes never reach the model. Measured so the difference between
  what is sealed and what is sent is a number rather than a claim.

GAP COSTS. Two absences are priced from the same traces: the value-id list no
state cites (upper bound = the row's whole supplied id list), and the typed
Reviewer findings form, priced against the arms that actually flew it.

Run (from a worktree, in WSL)::

    PYTHONDONTWRITEBYTECODE=1 python -B \
      scripts/analysis/slurp_reviewer_planner_global_state_audit.py \
      --out /tmp/saea-scope-audit/audit.json
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
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

#: The marker ``rails.runner`` appends the bounded episode limits under. Our own
#: committed control text, which is why splitting on it is exact.
LIMITS_MARKER = "\n\nNative episode limits: "

#: The sealed arms this audit reads in full. The first is the v2.0 lock geometry.
ARMS = (
    "SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1",
    "SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1",
    "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
)
PRIMARY = ARMS[0]

#: Arms read ONLY for the Reviewer-state class, to price the typed findings form
#: the locked plan does not fly.
REVIEWER_FORM_ARMS = (
    "SAEA-SLURP-NATIVE-NCP-L1-REVIEWER-FORMAT-ANCHOR-SMOKE-4-V1",
    "SAEA-SLURP-NATIVE-REVIEWER-AUDIT-ANCHOR-TRAIN-FOLD-A-V1",
)
ROLES = ("perception", "solver", "reviewer", "planner")
BASE_GRAPH_CONTACTS = len(ROLES)
EPISODE_SAMPLE = 25
WORKERS = 4


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stats(values):
    ordered = sorted(values)
    if not ordered:
        return None
    n = len(ordered)
    return {
        "n": n,
        "mean": round(sum(ordered) / n, 2),
        "median": ordered[n // 2],
        "min": ordered[0],
        "max": ordered[-1],
        "sum": sum(ordered),
    }


def store_of(evidence_id: str) -> str:
    return evidence_id.split("::")[0] if "::" in evidence_id else "<unnamespaced>"


def evidence_wire_text(item) -> str:
    """Exactly what ``core.model.transport`` puts on the wire for one item."""

    return "[evidence %s] %s" % (item["evidence_id"], item["content"])


def state_wire_text(item) -> str:
    """Exactly what ``_speech_history_texts`` puts on the wire for one state."""

    return "[agent state %s kind=%s] %s" % (
        item.get("state_id"), item.get("state_kind"), item["content"],
    )


# ---------------------------------------------------------------------------
# sealed traces
# ---------------------------------------------------------------------------
def read_trace(run_id: str, *, jobs, keep_roles=None):
    """``(episodes, trace_relpath)``, registering every wire text in ``jobs``.

    Texts are hashed into ``jobs`` and dropped; the returned per-contact record
    carries hashes, ids, kinds and counts only, so the whole audit holds no
    knowledge body, utterance or model output after this function returns.
    """

    trace = sorted((DATA / "runs" / run_id).glob("*/" + run_id + ".trace.jsonl"))[0]
    roles, payloads, costs = {}, {}, {}
    wanted = ('"MODEL_REQUEST"', 'native-role-contact"', '"COST"')
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            if not any(token in line for token in wanted):
                continue
            record = json.loads(line)
            channel, record_id = record["channel"], record["record_id"]
            flight = record_id.split("/")[0]
            if channel == "MODEL_REQUEST":
                payloads[flight] = record["payload"]["payload"]
            elif channel == "COST":
                costs[flight] = record["payload"].get("prompt_tokens")
            elif channel == "USE" and record_id.endswith("native-role-contact"):
                roles[flight] = record["payload"]["use_role_id"]

    episodes = defaultdict(list)
    for flight in sorted(payloads, key=lambda name: int(name.split("-")[1])):
        payload = payloads[flight]
        role = roles.get(flight)
        if keep_roles is not None and role not in keep_roles:
            continue
        episodes[payload["sample_id"]].append(
            contact_record(flight, role, payload, costs.get(flight), jobs=jobs)
        )
    return dict(episodes), str(trace.relative_to(DATA))


def contact_record(flight, role, payload, prompt_tokens, *, jobs):
    """One contact as hashes, ids, kinds and counts. No text is retained."""

    history = list(payload.get("history") or [])
    control = history[-1] if history and history[-1].get("role") == "control" else None
    prior = history[:-1] if control is not None else history

    classes: dict[str, str] = {}

    def register(name: str, text: str) -> None:
        digest = sha(text)
        jobs[digest] = text
        classes[name] = digest

    register("system.task_instruction", payload["task_instruction"])

    role_query = None
    if control is not None:
        envelope = json.loads(control["content"])
        message = envelope["messages"][1]
        if isinstance(message.get("content"), str):
            role_query = message["content"]
        register("sealed_only.control_envelope", control["content"])
    if role_query is not None:
        head, marker, tail = role_query.partition(LIMITS_MARKER)
        register("user.role_query.instruction", head)
        if marker:
            register("user.role_query.episode_limits", LIMITS_MARKER + tail)

    supplied = list(payload.get("supplied_evidence") or [])
    wire_by_store = defaultdict(list)
    label_by_store = defaultdict(list)
    for item in supplied:
        store = store_of(item["evidence_id"])
        wire_by_store[store].append(evidence_wire_text(item))
        label_by_store[store].append("[evidence %s] " % item["evidence_id"])
    for store, texts in sorted(wire_by_store.items()):
        register("user.supply.value." + store, "\n".join(texts))
        register("user.supply.label." + store, "\n".join(label_by_store[store]))
    if supplied:
        # Gap A's price: the whole supplied id list, as one comma-joined block.
        register(
            "gap.cited_value_ids_upper_bound",
            ", ".join(item["evidence_id"] for item in supplied),
        )

    states = []
    for item in prior:
        text = state_wire_text(item)
        digest = sha(text)
        jobs[digest] = text
        states.append({
            "state_kind": item.get("state_kind"),
            "sha256": digest,
            "declares_cited_value_ids": bool(item.get("cited_value_ids")),
        })

    return {
        "flight": flight,
        "role": role,
        "prompt_tokens": prompt_tokens,
        "n_supplied": len(supplied),
        "n_supplied_by_store": {
            store: len(texts) for store, texts in sorted(wire_by_store.items())
        },
        "knowledge_roles": dict(sorted(Counter(
            item.get("knowledge_role") for item in supplied
        ).items(), key=lambda pair: str(pair[0]))),
        "classes": classes,
        "states": states,
        "n_tool_schemas": len(payload.get("tool_schemas") or []),
        "n_speech_parts": len(payload.get("speech_feature_parts") or []),
        "limits_keys": sorted(json.loads(
            role_query.partition(LIMITS_MARKER)[2]
        )) if role_query and LIMITS_MARKER in role_query else [],
        "limits_numeric": {
            key: value
            for key, value in json.loads(
                role_query.partition(LIMITS_MARKER)[2]
            ).items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        } if role_query and LIMITS_MARKER in role_query else {},
        "n_available_planner_actions": len(json.loads(
            role_query.partition(LIMITS_MARKER)[2]
        ).get("available_planner_actions", ())) if (
            role_query and LIMITS_MARKER in role_query
        ) else None,
    }


# ---------------------------------------------------------------------------
# local tokenizer (vocab only)
# ---------------------------------------------------------------------------
class Tokenizer:
    def __init__(self, scratch: Path) -> None:
        self.scratch = scratch
        self.calls = 0

    def count(self, text: str, label: str) -> int:
        self.scratch.mkdir(parents=True, exist_ok=True)
        path = self.scratch / (label + ".txt")
        path.write_bytes(text.encode("utf-8"))
        argv = [
            str(TOKENIZE), "-m", str(GGUF), "-f", str(path), "--no-bos",
            "--no-escape", "--show-count", "--log-disable", "--ids",
        ]
        result = subprocess.run(argv, check=True, capture_output=True, text=True)
        self.calls += 1
        path.unlink()
        for line in result.stdout.splitlines():
            if line.startswith("Total number of tokens:"):
                return int(line.split(":")[1].strip())
        raise RuntimeError("local tokenizer produced no count for " + label)


def measure(jobs, scratch, cache_path: Path | None = None):
    """``{sha256: text}`` -> ``({sha256: tokens}, calls)``, order-independent.

    A token count is a pure function of the bytes and of the pinned vocab, so a
    sha256-keyed cache is safe and makes a second analysis pass over the same
    traces free. The cache holds counts only -- never a byte of the text it
    counted.
    """

    cached: dict[str, int] = {}
    if cache_path is not None and cache_path.exists():
        cached = {
            key: int(value)
            for key, value in json.loads(cache_path.read_text(encoding="utf-8")).items()
        }
    tokenizer = Tokenizer(scratch)
    keys = sorted(key for key in jobs if key not in cached)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        counts = list(pool.map(lambda key: tokenizer.count(jobs[key], key[:24]), keys))
    cached.update(zip(keys, counts))
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(cached, indent=0, sort_keys=True), encoding="utf-8",
        )
    return {key: cached[key] for key in jobs}, tokenizer.calls


# ---------------------------------------------------------------------------
def sampled_episode_ids(episodes, count):
    ordered = sorted(episodes)
    if len(ordered) <= count:
        return ordered
    stride = len(ordered) / count
    return [ordered[int(index * stride)] for index in range(count)]


#: Classes that are prompt text. Everything else measured is either sealed-only
#: custody, a priced gap, or a SUB-DECOMPOSITION of a class already counted, and
#: must not enter the prompt total. ``user.supply.label.<store>`` is the third
#: kind: the ``[evidence <id>] `` prefix is already inside
#: ``user.supply.value.<store>``, and it is measured on its own only so the cost
#: of the addressing can be named.
SUB_DECOMPOSITION_PREFIX = "user.supply.label."


def is_prompt_class(name: str) -> bool:
    if name.startswith(SUB_DECOMPOSITION_PREFIX):
        return False
    return name.startswith(("system.", "user."))


def is_second_pass(contact) -> bool:
    """Has a Planner already answered before this contact was composed?

    Read off the contact's own rendered states rather than its position: a
    ``phase:planner`` state can only exist after the Planner has routed once, so
    this is exact for an arm whose Solver visit spends five sampled contacts
    (ROLL-1) as well as for one that spends one.
    """

    return any(state["state_kind"] == "phase:planner" for state in contact["states"])


def class_table(episodes, sample_ids, tokens, *, stratum):
    """Per role, every content class in tokens, over one stratum of contacts.

    ``stratum`` is ``"first-pass"`` (before any Planner route), ``"second-pass"``
    (after one) or ``"all"``.
    """

    rows = defaultdict(lambda: defaultdict(list))
    prompt, residual, contacts_seen = defaultdict(list), defaultdict(list), Counter()
    for sample_id in sample_ids:
        for contact in episodes[sample_id]:
            first = not is_second_pass(contact)
            if stratum == "first-pass" and not first:
                continue
            if stratum == "second-pass" and first:
                continue
            role = contact["role"]
            contacts_seen[role] += 1
            text_total = 0
            for name, digest in contact["classes"].items():
                count = tokens[digest]
                rows[role][name].append(count)
                if is_prompt_class(name):
                    text_total += count
            per_kind = defaultdict(int)
            for state in contact["states"]:
                per_kind[state["state_kind"]] += tokens[state["sha256"]]
            for kind in ("phase:perception", "phase:solver", "phase:reviewer",
                         "phase:planner"):
                rows[role]["user.state." + kind].append(per_kind.get(kind, 0))
                text_total += per_kind.get(kind, 0)
            for kind, count in per_kind.items():
                if kind.startswith("phase:") and kind.split(":", 1)[1] in ROLES:
                    continue
                rows[role]["user.state." + kind].append(count)
                text_total += count
            rows[role]["ALL_PROMPT_TEXT_CLASSES"].append(text_total)
            if contact["prompt_tokens"] is not None:
                prompt[role].append(contact["prompt_tokens"])
                residual[role].append(contact["prompt_tokens"] - text_total)
    table = {}
    for role in ROLES:
        if not contacts_seen[role]:
            continue
        table[role] = {
            "contacts": contacts_seen[role],
            "classes": {
                name: stats(values) for name, values in sorted(rows[role].items())
            },
            "sealed_COST_prompt_tokens": stats(prompt[role]),
            "speech_packet_plus_template_residual": stats(residual[role]),
        }
    return table


def revision_survival(episodes):
    """Per revised row: what each later contact still carries, and what is not.

    ``sealed_before`` is how many role states this episode had sealed BEFORE
    this contact was composed (one per preceding contact); ``rendered`` is how
    many of them this contact's prompt actually carries. ``dropped`` is the
    difference -- the number a reader should read as "earlier steps this node
    cannot see".
    """

    revised = {
        sample_id: contacts
        for sample_id, contacts in episodes.items()
        if len(contacts) > BASE_GRAPH_CONTACTS
    }
    per_contact = []
    for sample_id, contacts in sorted(revised.items()):
        for index, contact in enumerate(contacts):
            kinds = Counter(state["state_kind"] for state in contact["states"])
            per_contact.append({
                "episode_sha256": sha(sample_id)[:16],
                "visit_index": index,
                "role": contact["role"],
                "sealed_before": index,
                "rendered": len(contact["states"]),
                "dropped": index - len(contact["states"]),
                "rendered_kinds": dict(sorted(kinds.items())),
                "limits": contact["limits_numeric"],
                "n_available_planner_actions": contact[
                    "n_available_planner_actions"
                ],
            })
    shapes = Counter(
        tuple(contact["role"] for contact in contacts)
        for contacts in episodes.values()
    )

    def later(role):
        return [
            row for row in per_contact
            if row["role"] == role
            and row["rendered_kinds"].get("phase:planner", 0) >= 1
        ]

    reviewer, planner = later("reviewer"), later("planner")
    return {
        "n_episodes": len(episodes),
        "n_revised_episodes": len(revised),
        "episode_shapes": sorted(
            ({"roles": list(shape), "episodes": n} for shape, n in shapes.items()),
            key=lambda row: -row["episodes"],
        ),
        "second_pass_reviewer": {
            "contacts": len(reviewer),
            "all_carry_own_earlier_review": all(
                row["rendered_kinds"].get("phase:reviewer", 0) >= 1
                for row in reviewer
            ),
            "all_carry_both_solver_drafts": all(
                row["rendered_kinds"].get("phase:solver", 0) >= 2
                for row in reviewer
            ),
            "all_carry_the_planner_route": all(
                row["rendered_kinds"].get("phase:planner", 0) >= 1
                for row in reviewer
            ),
            "rendered_state_counts": stats([row["rendered"] for row in reviewer]),
            "total_dropped": sum(row["dropped"] for row in reviewer),
        },
        "second_pass_planner": {
            "contacts": len(planner),
            "all_carry_own_earlier_route": all(
                row["rendered_kinds"].get("phase:planner", 0) >= 1
                for row in planner
            ),
            "all_carry_both_reviews": all(
                row["rendered_kinds"].get("phase:reviewer", 0) >= 2
                for row in planner
            ),
            "all_carry_both_solver_drafts": all(
                row["rendered_kinds"].get("phase:solver", 0) >= 2
                for row in planner
            ),
            "rendered_state_counts": stats([row["rendered"] for row in planner]),
            "total_dropped": sum(row["dropped"] for row in planner),
        },
        "contacts": per_contact,
    }


def structural_probes(episodes):
    """Named, countable absences and invariants -- no design, only what is."""

    states = citing = 0
    kinds, tool_schemas, limit_sets, actions = Counter(), Counter(), Counter(), Counter()
    for contacts in episodes.values():
        for contact in contacts:
            tool_schemas[contact["n_tool_schemas"]] += 1
            limit_sets[tuple(contact["limits_keys"])] += 1
            if contact["role"] == "planner":
                actions[contact["n_available_planner_actions"]] += 1
            for state in contact["states"]:
                states += 1
                kinds[state["state_kind"]] += 1
                citing += int(state["declares_cited_value_ids"])
    return {
        "rendered_states": states,
        "states_declaring_cited_value_ids": citing,
        "state_kinds_ever_rendered": dict(sorted(kinds.items())),
        "tool_schemas_per_contact": dict(sorted(tool_schemas.items())),
        "episode_limits_key_sets": sorted(
            ({"keys": list(keys), "contacts": n} for keys, n in limit_sets.items()),
            key=lambda row: -row["contacts"],
        ),
        "planner_available_action_counts": dict(sorted(actions.items())),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--scratch", default="/tmp/saea-scope-audit/tok")
    parser.add_argument("--token-cache", default="/tmp/saea-scope-audit/tokens.json")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)

    report = {
        "what_this_is": (
            "What the Reviewer and the Planner receive today, class by class, "
            "measured on sealed traces with the local vocab-only tokenizer. "
            "Zero model, server, GPU, encoder and scorer contacts."
        ),
        "wire_model": {
            "messages_per_contact": 2,
            "system": "payload.task_instruction",
            "user_parts_in_order": [
                "the one speech-feature query packet (speech-query-prefix-v2)",
                "[evidence <id>] <body>, one text part per visible value",
                "[agent state <id> kind=<kind>] <content>, one per exposed state",
                "the role query: instruction + 'Native episode limits: {...}'",
            ],
            "control_envelope": (
                "history[-1] is sealed custody only; "
                "project_native_framework_history rebuilds the user turn from "
                "history[:-1] and appends framework[1].content instead"
            ),
        },
        "arms": {},
        "reviewer_form_comparison": {},
        "reviewer_template_split": {},
    }

    jobs: dict[str, str] = {}
    per_arm = {}
    for run_id in ARMS:
        episodes, trace_relpath = read_trace(run_id, jobs=jobs)
        sample_ids = sampled_episode_ids(episodes, EPISODE_SAMPLE)
        if run_id == PRIMARY:
            sample_ids = sorted(set(sample_ids) | {
                sample_id for sample_id, contacts in episodes.items()
                if len(contacts) > BASE_GRAPH_CONTACTS
            })
        # Drop every text of a row this audit does not sample.
        keep = set()
        for sample_id in sample_ids:
            for contact in episodes[sample_id]:
                keep.update(contact["classes"].values())
                keep.update(state["sha256"] for state in contact["states"])
        per_arm[run_id] = (episodes, trace_relpath, sample_ids, keep)

    # The Reviewer's committed instruction template, split at the clause that
    # divides the order to call a task-contract tool from the order to review.
    # The tool half is priced because the toolkit it names is RETIRED (item E25,
    # harness-admission switch class ``phase_tools``, after the B1-notool read),
    # while every sealed contact of the locked plan renders 0 tool schemas.
    template_path = (
        Path(args.repo_root) / "configs" / "probes"
        / "slurp_native_role_reviewer_v1.txt"
    )
    template_split: dict[str, str] = {}
    if template_path.exists():
        text = template_path.read_text(encoding="utf-8")
        head, marker, tail = text.partition("Then review")
        template_split = {
            "gap.reviewer_template.retired_tool_order": head,
            "gap.reviewer_template.review_order": marker + tail,
            "gap.reviewer_template.whole": text,
        }
    # The typed-findings instruction the same Reviewer seat carries in the arms
    # that fly ``saea-review-findings-v1``: the other half of G2's price.
    findings_path = (
        Path(args.repo_root) / "configs" / "probes"
        / "slurp_native_role_reviewer_findings_v1.txt"
    )
    if findings_path.exists():
        template_split["gap.reviewer_findings_template.whole"] = (
            findings_path.read_text(encoding="utf-8")
        )
    for digest_text in template_split.values():
        jobs[sha(digest_text)] = digest_text

    form_arms = {}
    for run_id in REVIEWER_FORM_ARMS:
        try:
            episodes, trace_relpath = read_trace(
                run_id, jobs=jobs, keep_roles={"reviewer"},
            )
        except (IndexError, FileNotFoundError):
            continue
        keep = {
            state["sha256"]
            for contacts in episodes.values()
            for contact in contacts
            for state in contact["states"]
        }
        form_arms[run_id] = (episodes, trace_relpath, keep)

    wanted = set().union(*(entry[3] for entry in per_arm.values()))
    if form_arms:
        wanted |= set().union(*(entry[2] for entry in form_arms.values()))
    wanted |= {sha(text) for text in template_split.values()}
    jobs = {digest: text for digest, text in jobs.items() if digest in wanted}

    tokens, calls = measure(
        jobs, Path(args.scratch),
        None if not args.token_cache else Path(args.token_cache),
    )
    report["tokenizer"] = {
        "binary": str(TOKENIZE),
        "vocab_gguf_relpath": str(GGUF.relative_to(DATA)),
        "distinct_texts": len(jobs),
        "invocations": calls,
        "workers": WORKERS,
        "model_contacts": 0,
    }

    for run_id in ARMS:
        episodes, trace_relpath, sample_ids, _keep = per_arm[run_id]
        entry = {
            "trace_relpath": trace_relpath,
            "n_episodes": len(episodes),
            "n_contacts": sum(len(contacts) for contacts in episodes.values()),
            "contacts_by_role": dict(sorted(Counter(
                contact["role"]
                for contacts in episodes.values()
                for contact in contacts
            ).items())),
            "sampled_episodes": len(sample_ids),
            "content_classes_all": class_table(
                episodes, sample_ids, tokens, stratum="all",
            ),
            "content_classes_first_pass": class_table(
                episodes, sample_ids, tokens, stratum="first-pass",
            ),
            "content_classes_second_pass": class_table(
                episodes, sample_ids, tokens, stratum="second-pass",
            ),
            "structural_probes": structural_probes(episodes),
        }
        if run_id == PRIMARY:
            entry["revision_survival"] = revision_survival(episodes)
        report["arms"][run_id] = entry

    for run_id, (episodes, trace_relpath, _keep) in form_arms.items():
        counts = [
            tokens[state["sha256"]]
            for contacts in episodes.values()
            for contact in contacts
            for state in contact["states"]
            if state["state_kind"] == "phase:reviewer"
        ]
        report["reviewer_form_comparison"][run_id] = {
            "trace_relpath": trace_relpath,
            "reviewer_contacts": sum(len(c) for c in episodes.values()),
            "phase_reviewer_state_tokens": stats(counts),
        }

    report["reviewer_template_split"] = {
        "relpath": str(template_path.relative_to(Path(args.repo_root)))
        if template_split else None,
        "tokens": {
            name: tokens[sha(text)] for name, text in sorted(template_split.items())
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print("wrote", out, "sha256", sha(out.read_text(encoding="utf-8")))
    print("tokenizer invocations", calls, "distinct texts", len(jobs))
    for stratum in ("content_classes_all", "content_classes_first_pass",
                    "content_classes_second_pass"):
        print("\n########", stratum)
        for role in ROLES:
            table = report["arms"][PRIMARY][stratum].get(role)
            if table is None:
                continue
            print("-- %s  contacts=%d  sealed prompt mean=%s" % (
                role, table["contacts"],
                (table["sealed_COST_prompt_tokens"] or {}).get("mean")))
            for name, values in table["classes"].items():
                if values and values["sum"]:
                    print("   %-46s %9.1f" % (name, values["mean"]))
            print("   %-46s %9.1f" % (
                "(residual: speech packet + template)",
                (table["speech_packet_plus_template_residual"] or {}).get("mean", 0)))
    survival = report["arms"][PRIMARY]["revision_survival"]
    print("\nrevised episodes", survival["n_revised_episodes"], "of",
          survival["n_episodes"])
    for shape in survival["episode_shapes"]:
        print("  %4d episodes: %s" % (shape["episodes"], " -> ".join(shape["roles"])))
    for key in ("second_pass_reviewer", "second_pass_planner"):
        print(key, json.dumps(survival[key], sort_keys=True))
    print("\nprobes", json.dumps(
        report["arms"][PRIMARY]["structural_probes"], sort_keys=True))
    print("\nreviewer form comparison", json.dumps(
        report["reviewer_form_comparison"], indent=1, sort_keys=True))
    print("reviewer template split", json.dumps(
        report["reviewer_template_split"], sort_keys=True))
    for run_id in ARMS[1:]:
        print("\n######## corroboration", run_id)
        entry = report["arms"][run_id]
        print("  contacts", entry["contacts_by_role"], "episodes",
              entry["n_episodes"], "sampled", entry["sampled_episodes"])
        for role in ("reviewer", "planner"):
            table = entry["content_classes_first_pass"].get(role)
            if table is None:
                continue
            classes = table["classes"]
            state = sum(
                (classes[name] or {"sum": 0})["sum"]
                for name in classes if name.startswith("user.state.")
            )
            supply = sum(
                (classes[name] or {"sum": 0})["sum"]
                for name in classes if name.startswith("user.supply.value.")
            )
            print("  %-9s contacts %4d  prompt %8.1f  supply %8.1f  state %7.1f" % (
                role, table["contacts"],
                (table["sealed_COST_prompt_tokens"] or {}).get("mean", 0),
                supply / max(table["contacts"], 1),
                state / max(table["contacts"], 1)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
