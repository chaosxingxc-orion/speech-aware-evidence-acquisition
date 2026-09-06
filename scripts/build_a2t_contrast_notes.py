#!/usr/bin/env python3
"""Build KC-A1's contrast-note artifact and KC-A1c's category-only control.

Model-free, zero contacts. Reads ``tools_registry.csv`` through the umbrella
lock plus a committed target spec -- ``--targets-spec``, default
``configs/knowledge/a2t-kc-a1/targets-v1.json`` and, since the owner took
option B on 2026-09-06, ``configs/knowledge/a2t-kc-a1/targets-lighting-v1.json``
for the cell that flies (whose tool lists are re-verified against the MF-1
audit receipt), then
writes both override artifacts, both baseline fragments -- through
``rails.evolution.write_candidate_fragments``, official-protocol fragment as
base -- and one receipt with the per-tool deltas and each rendered block's
line, character and TOKEN totals. The note/control CONSTRUCTION rule is
``rails.proposer.contrast_note_records``; every prose statement recorded is
the spec's.

Tokens are MEASURED, never estimated, whenever an artifact is written: the
owner ruling of 2026-09-06 makes the resident server's ``/tokenize`` route
the only authority for this family, because the chars-per-token estimator
this script used to inject was 8 % wrong in the unsafe direction on short
appended phrases and left the control 14 tokens cheaper than its treatment.
``--write`` therefore REQUIRES ``--tokenizer-url``; the control is
token-matched per line on that tokenizer, and whole-block token equality
between the two arms is asserted by measurement before anything is written.
The same ruling makes the program's +40-token headroom advisory for a flown
cell: ``--token-budget`` is REPORTED (the slack a cap would have to grant),
never a gate, and the form cost is priced by the token-matched control
instead.

Usage (WSL2), with a resident llama-server at the flight's own geometry:
``python scripts/build_a2t_contrast_notes.py --targets-spec
configs/knowledge/a2t-kc-a1/targets-lighting-v1.json --tokenizer-url
http://127.0.0.1:8080 --write``.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import http.client
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "configs/knowledge/a2t-kc-a1/targets-v1.json"
ARTIFACTS = REPO / "configs/knowledge/a2t-kc-a1"
OUT_DIR = (
    REPO / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-a2t-kc-a1-contrast-notes-4000-v1"
)
BASE = REPO / "configs/baseline/a2t-direct-official-protocol.json"
#: ``(arm, record key, artifact file name, baseline fragment file name)``.
ARMS = (
    ("kc-a1", "kc_a1", "contrast-notes-v1.json", "a2t-kc-a1-contrast-notes.json"),
    ("kc-a1c", "kc_a1c", "category-only-v1.json", "a2t-kc-a1c-category-only.json"),
)
#: ORG-1's measured ratio. Retained for ``--targets`` PRICING only, where a
#: rough per-target figure orders candidate subsets before any server exists;
#: it may never reach a written artifact again (2026-09-06 ruling).
CHARS_PER_TOKEN = 347.0 / 87.0
#: The runtime receipt the flown model fragment pins, for the tokenizer
#: identity block: the GGUF files behind the ``/tokenize`` route.
RUNTIME_RECEIPT = REPO / "docs/receipts/runtime-q4km-featcache-04ccc72a.json"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def est(text: str) -> int:
    return round(len(text) / CHARS_PER_TOKEN)


class ServerTokens:
    """Token counts from a resident llama-server's ``/tokenize`` route.

    One HTTP connection, memoized per exact string, and a call counter, so
    the receipt can state what the measurement spent. ``/props`` is read once
    for the tokenizer identity: the chat template hash the prompt fit records
    and the model path the server actually loaded, beside the GGUF SHA-256
    the runtime receipt pins.
    """

    def __init__(self, url: str) -> None:
        host, _, port = url.split("//", 1)[-1].partition(":")
        if host not in {"127.0.0.1", "localhost"}:
            raise SystemExit(f"the tokenizer must be loopback, not {host!r}")
        self.connection = http.client.HTTPConnection(host, int(port or 80), timeout=180.0)
        self.cache: dict[str, int] = {}
        self.calls = 0
        self.props = self.request("GET", "/props", None)

    def request(self, method: str, path: str, payload: object) -> dict:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        self.connection.request(method, path, body=body, headers=headers)
        response = self.connection.getresponse()
        raw = response.read()
        if response.status != 200:
            raise SystemExit(f"{path} returned HTTP {response.status}: {raw[:300]!r}")
        return json.loads(raw)

    def __call__(self, text: str) -> int:
        if text not in self.cache:
            document = self.request(
                "POST",
                "/tokenize",
                {"content": text, "add_special": False, "parse_special": True},
            )
            tokens = document.get("tokens")
            if not isinstance(tokens, list):
                raise SystemExit("/tokenize returned no token list")
            self.calls += 1
            self.cache[text] = len(tokens)
        return self.cache[text]

    def identity(self) -> dict[str, object]:
        template = self.props.get("chat_template")
        receipt = json.loads(RUNTIME_RECEIPT.read_text(encoding="utf-8"))
        return {
            "route": "POST /tokenize (add_special=false, parse_special=true)",
            "chat_template_sha256": (
                digest(template.encode("utf-8")) if isinstance(template, str) else None
            ),
            "server_model_path": self.props.get("model_path"),
            "llama_cpp_build_commit": receipt["llama_cpp"]["build_commit"],
            "runtime_receipt": RUNTIME_RECEIPT.relative_to(REPO).as_posix(),
            "gguf_files": {
                str(entry["path"]): str(entry["sha256"])
                for entry in receipt["gguf_files"]
            },
        }


def verify_spec(spec) -> dict[str, dict[str, str]]:
    """The spec's ``{target_id: {tool: note}}``, refused unless every tool list
    is the MF-1 audit receipt's own."""
    source = spec["source_receipt"]
    receipt = REPO / str(source["path"])
    measured = digest(receipt.read_bytes())
    if measured != source["sha256"]:
        raise SystemExit(f"audit receipt hashes to {measured}, not {source['sha256']}")
    audited = {
        str(entry["target_id"]): sorted(str(tool) for tool in entry["tools"])
        for entry in json.loads(receipt.read_text(encoding="utf-8"))
        ["primary_population"]["targets"]["targets"]
    }
    targets: dict[str, dict[str, str]] = {}
    for target in spec["targets"]:
        target_id = str(target["target_id"])
        if audited.get(target_id) != sorted(target["tools"]):
            raise SystemExit(f"target {target_id} is not the audit receipt's")
        targets[target_id] = {
            tool: str(body["note"]) for tool, body in target["tools"].items()
        }
    return targets


def arm_block(arm, k, records, key, rows, compact, counter, budget):
    """``(candidate, receipt block)`` for one arm: its whole 152-line rendering
    measured against the compact baseline, then every form and decontamination
    gate ``rails.proposer`` owns.

    ``counter`` is the serving geometry's own tokenizer when an artifact is
    being written, and the retired estimator only when ``--targets`` is
    pricing a subset nothing will fly. The budget slack is REPORTED, never
    hidden and (since the 2026-09-06 ruling) never a gate: 0 means the
    artifact would have cleared the program's +40-token headroom unaided, and
    any other value is how far that advisory cap sits below this arm."""
    from speech_aware_evidence_acquisition.data.audio2tool_tools import (
        render_registry_compact_rows,
    )
    from speech_aware_evidence_acquisition.rails.proposer import (
        CandidateArtifact, validate_candidate_artifact,
    )

    overrides = {str(record["tool_name"]): str(record[key]) for record in records}
    rendered = render_registry_compact_rows(rows, description_overrides=overrides)
    added = counter(rendered) - counter(compact)
    slack = max(0, added - budget)
    shape = {
        "tools_overridden": len(overrides),
        "rendered_lines": len(rendered.split("\n")), "rendered_chars": len(rendered),
        "rendered_sha256": digest(rendered.encode("utf-8")),
        "rendered_tokens": counter(rendered),
        "compact_chars": len(compact), "compact_sha256": digest(compact.encode("utf-8")),
        "compact_tokens": counter(compact),
        "added_chars": len(rendered) - len(compact), "added_tokens": added,
        "token_method": "measured" if counter is not est else "estimated",
        "reported_token_budget": budget,
        "tokens_over_reported_budget": slack,
        "within_reported_token_budget": slack == 0,
    }
    draft = CandidateArtifact(
        candidate_id="", family="deterministic", target_id=arm, round=0, k=k,
        descriptions=dict(sorted(overrides.items())),
        cue=("the registry's own domain, category, argument names and constraints"
             if arm == "kc-a1" else None),
        proposer_prompt_sha256=None, exemplar_ids=(),
    )
    candidate = dataclasses.replace(
        draft, candidate_id=draft.expected_candidate_id()
    ).validate()
    validation = validate_candidate_artifact(
        candidate, registry_rows=rows, token_counter=counter,
        compact_baseline_tokens=counter(compact) + slack,
        evaluation_query_texts=(), registry_text=compact,
    )
    return candidate, {
        "measurement": shape, "candidate": candidate.as_json(),
        "validation": validation.as_json(), "token_headroom_slack_granted": slack,
    }


def write_arms(portfolios, manipulation: str) -> dict[str, dict[str, str]]:
    """The two artifacts and the two baseline fragments, then renamed.
    ``write_candidate_fragments`` names both files after the portfolio digest,
    and that digest is over the override MAPPING, so renaming an artifact to
    its cell-facing name leaves the recorded ``artifact_sha256`` exactly right
    and only ``artifact_relpath`` has to follow it."""
    from speech_aware_evidence_acquisition.rails.evolution import (
        write_candidate_fragments,
    )

    base = json.loads(BASE.read_text(encoding="utf-8"))
    base.pop("task_instruction_fill")
    staged = OUT_DIR / "staged-fragments"
    emitted = write_candidate_fragments(
        portfolios, base_fragment=base, out_dir=staged, artifact_dir=ARTIFACTS,
        artifact_relpath_base=REPO,
    )
    written: dict[str, dict[str, str]] = {}
    for (arm, _, artifact_name, fragment_name), path in zip(ARMS, emitted, strict=True):
        fragment = json.loads(path.read_text(encoding="utf-8"))
        params = fragment["task_instruction_fill_params"]
        (REPO / str(params["artifact_relpath"])).replace(ARTIFACTS / artifact_name)
        params["artifact_relpath"] = f"configs/knowledge/a2t-kc-a1/{artifact_name}"
        fragment["manipulation"] = manipulation.format(artifact=params["artifact_relpath"])
        (REPO / "configs/baseline" / fragment_name).write_text(
            json.dumps(fragment, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        path.unlink()
        written[arm] = {
            "baseline_fragment": f"configs/baseline/{fragment_name}",
            "artifact_relpath": str(params["artifact_relpath"]),
            "artifact_sha256": str(params["artifact_sha256"]),
            "portfolio_sha256": str(params["portfolio_sha256"]),
        }
    staged.rmdir()
    return written


def main() -> int:
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry
    from speech_aware_evidence_acquisition.data.audio2tool_tools import (
        render_registry_compact_rows,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        data_root, load_lock, umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.rails.evolution import assemble_portfolio
    from speech_aware_evidence_acquisition.rails.proposer import (
        TOKEN_HEADROOM, contrast_note_records,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--targets", default=None, help="price a SUBSET; writes nothing")
    parser.add_argument(
        "--targets-spec",
        type=Path,
        default=SPEC,
        help=(
            "the COMMITTED target spec to build from. A spec may carry any subset of "
            "the MF-1 targets -- every tool list it does carry is still re-verified "
            "against the audit receipt -- so the owner's option-B lighting-only cell "
            "is a committed file rather than a command-line filter. --targets stays "
            "what it was: an ad-hoc pricing filter that writes nothing"
        ),
    )
    parser.add_argument(
        "--tokenizer-url",
        default=None,
        help=(
            "loopback base url of the resident llama-server whose /tokenize route is "
            "the token AUTHORITY for this build. Required by --write since the "
            "2026-09-06 owner ruling: the retired chars-per-token estimator priced "
            "these notes 8 %% low and left the control 14 tokens cheaper than its "
            "treatment, and both mistakes are invisible without a measurement"
        ),
    )
    parser.add_argument(
        "--token-budget",
        type=int,
        default=None,
        help=(
            "the token headroom REPORTED against (default: the program's advisory "
            "rails.proposer.TOKEN_HEADROOM). It is reported, never enforced: the "
            "2026-09-06 ruling prices form with the token-matched control instead"
        ),
    )
    args = parser.parse_args()
    if args.targets and args.write:
        raise SystemExit("--targets prices a subset; it never writes the committed arms")
    if args.write and not args.tokenizer_url:
        raise SystemExit(
            "--write needs --tokenizer-url: an artifact registered on the estimator "
            "is refused (2026-09-06 owner ruling; preregistration section 8.1)"
        )
    spec_path = Path(args.targets_spec)
    if not spec_path.is_absolute():
        spec_path = REPO / spec_path
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    targets = verify_spec(spec)
    if args.targets:
        wanted = {part.strip() for part in args.targets.split(",") if part.strip()}
        if not wanted <= set(targets):
            raise SystemExit(f"unknown target(s) {sorted(wanted - set(targets))}")
        targets = {key: value for key, value in targets.items() if key in wanted}
    rows = list(load_tool_registry(load_lock(umbrella_lock_path(REPO)), data_root()))
    compact = render_registry_compact_rows(rows)
    counter = ServerTokens(args.tokenizer_url) if args.tokenizer_url else est
    budget = args.token_budget if args.token_budget is not None else TOKEN_HEADROOM
    records = contrast_note_records(
        rows, targets,
        function_words=spec["note_rules"]["function_words"],
        prefix=str(spec["note_rules"]["prefix"]),
        filler=str(spec["control_rules"]["filler"]),
        token_counter=None if counter is est else counter,
    )
    if counter is not est:
        # the per-LINE cost of each arm, on the rendering the flight sends:
        # "- {signature}: {description}" is the compact block's own row shape.
        by_name = {str(row["tool_name"]): row for row in rows}
        for record in records:
            row = by_name[str(record["tool_name"])]
            line = "- %s: %%s" % row["signature"]
            base = counter(line % row["description"])
            record["released_line_tokens"] = base
            for key in ("kc_a1", "kc_a1c"):
                record[f"{key}_line_tokens"] = counter(line % record[key])
                record[f"{key}_added_line_tokens"] = record[f"{key}_line_tokens"] - base

    arms: dict[str, object] = {}
    portfolios = []
    for index, (arm, key, _, _) in enumerate(ARMS):
        candidate, block = arm_block(arm, index, records, key, rows, compact, counter, budget)
        arms[arm] = block
        portfolios.append(assemble_portfolio({}, {arm: candidate}))
        print("%-6s %s" % (arm, json.dumps(block["measurement"], sort_keys=True)))
    equality = {
        "rule": "the two arms' whole rendered blocks must measure the same token count",
        "kc_a1_tokens": arms["kc-a1"]["measurement"]["rendered_tokens"],
        "kc_a1c_tokens": arms["kc-a1c"]["measurement"]["rendered_tokens"],
        "token_matched": (
            arms["kc-a1"]["measurement"]["rendered_tokens"]
            == arms["kc-a1c"]["measurement"]["rendered_tokens"]
        ),
        "measured_on": "estimator" if counter is est else "server /tokenize",
    }
    if args.write and not equality["token_matched"]:
        raise SystemExit(
            "the arms are not token-matched whole-block (%d vs %d); a control that "
            "does not cost what its treatment costs cannot price the treatment's form"
            % (equality["kc_a1_tokens"], equality["kc_a1c_tokens"])
        )

    per_target: dict[str, dict[str, int]] = {}
    for record in records:
        block = per_target.setdefault(
            str(record["target_id"]), {"tools": 0, "added_chars": 0}
        )
        block["tools"] += 1
        block["added_chars"] += int(record["note_chars"])
    for target, block in sorted(per_target.items()):
        block["estimated_added_tokens"] = round(block["added_chars"] / CHARS_PER_TOKEN)
        print("  %-18s %s" % (target, json.dumps(block, sort_keys=True)))

    receipt = {
        "schema": "saea-a2t-kc-a1-artifact-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "builder": "scripts/build_a2t_contrast_notes.py", "model_contacts": 0,
        "target_spec": {
            "path": spec_path.resolve().relative_to(REPO).as_posix(),
            "sha256": digest(spec_path.read_bytes()),
            "audit_receipt": spec["source_receipt"],
            "target_ids": sorted(targets),
        },
        "registry": {"rows": len(rows), "lock_key": "audio2tool"},
        "token_method": spec["statements"]["token_method"],
        "decontamination": spec["statements"]["decontamination"],
        "whole_block_token_equality": equality,
        "tokenizer": counter.identity() if counter is not est else None,
        "tokenize_calls": 0 if counter is est else counter.calls,
        "per_tool": records, "per_target": per_target, "arms": arms,
    }
    if args.write:
        receipt["files"] = write_arms(portfolios, str(spec["statements"]["manipulation"]))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUT_DIR / "artifact-receipt.json"
        path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        print("written: %s (sha256 %s)" % (path, digest(path.read_bytes())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
