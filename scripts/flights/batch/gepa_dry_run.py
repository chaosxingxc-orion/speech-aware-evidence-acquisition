#!/usr/bin/env python3
"""The offline rendering proof of ONE GEPA contact.

MODEL-FREE and OFFLINE. Zero frozen-core, tool, embedding, encoder, TOKENIZER,
scorer, GPU, server and network contacts: it opens no socket, constructs no
client, opens no attempt and writes nothing outside ``--out``. Every byte it
reads is committed or already sealed.

What it proves, for one chosen group of the prepared GEPA groups artifact:

1. ``rails.stage3_gepa_material.build_gepa_material`` renders that group's
   instruction from the REAL sealed ROLL-1 custody, the REAL ``pairs.json``
   trajectories, the REAL released delta statements and the REAL governed
   construction gold -- every pin verified, every rendered Solver answer proved
   equal to the digest ``pairs.json`` pinned.
2. The message list is exactly the one
   ``core.flight.runtime.FlightRuntime._run_construction_proposer`` builds: the
   instruction as the system message and an EMPTY user content list. It is
   handed to the client's own reverse parser
   (``rails.core_client._parse_rails_messages`` with ``text_only=True``), which
   is what refuses an audio part on this arm, and the parsed instruction is
   proved byte-identical to the rendered one.
3. The audited payload's field set is EXACTLY the D2-frozen field set of
   ``construction-advantage-text`` (``e0.d2_leakage.ARM_VISIBLE_FIELDS``) -- the
   same equality ``core.model.adapter`` asserts before a request is built.
4. The payload passes the TRANSPORT's own text-only construction gate
   (``core.model.transport._assert_text_only_construction_payload``), which is
   the function that fails closed on a construction payload carrying a speech
   field, a media part or an Agent history. No audio field and no audio marker
   appears anywhere in the serialised payload.
5. The contact's receipt (``GepaContact.as_json``) carries none of the rendered
   text.

Sizes are reported in CHARACTERS only. Measuring tokens needs a tokenizer
endpoint, which is a contact; the registered FIT pass is what measures them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.model.transport import (  # noqa: E402
    _assert_text_only_construction_payload,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS  # noqa: E402
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    _parse_rails_messages,
)
from speech_aware_evidence_acquisition.rails.stage3_gepa import (  # noqa: E402
    STAGE3_GEPA_ARM,
)
from speech_aware_evidence_acquisition.rails.stage3_gepa_material import (  # noqa: E402
    build_gepa_material,
)

AUDIO_MARKERS = ("input_audio", "input_speech_features", "audio_url", "media_relpath")


class _Sample:
    def __init__(self, sample_id: str) -> None:
        self.sample_id = sample_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--lock-path", required=True, type=Path)
    parser.add_argument(
        "--baseline",
        default="configs/baseline/slurp-native-stage3-gepa-baseline-v1.json",
    )
    parser.add_argument(
        "--group-id",
        default=None,
        help="which group to render; default: the artifact's first group",
    )
    parser.add_argument("--out", default=None, type=Path)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    data_root = Path(args.data_root)
    lock = json.loads(Path(args.lock_path).read_text(encoding="utf-8"))
    values = json.loads((repo_root / args.baseline).read_text(encoding="utf-8"))
    values.setdefault("carrier_lock_key", "slurp")

    groups_block = values["gepa_groups"]
    groups_document = json.loads(
        (data_root / groups_block["relpath"]).read_text(encoding="utf-8")
    )
    groups = groups_document["groups"]
    chosen = (
        next(group for group in groups if group["group_id"] == args.group_id)
        if args.group_id
        else groups[0]
    )
    carrier = chosen["carrier_sample_id"]

    material = build_gepa_material(
        values,
        lock=lock,
        data_root=data_root,
        repo_root=repo_root,
        samples=[_Sample(carrier)],
    )
    (contact,) = material.contacts

    problems: list[str] = []

    # (2) the message list the runtime builds, through the client's own parser
    messages = (
        {"role": "system", "content": contact.instruction},
        {"role": "user", "content": []},
    )
    parsed = _parse_rails_messages(messages, text_only=True)
    parsed_instruction = parsed[0] if isinstance(parsed, tuple) else parsed
    if parsed_instruction != contact.instruction:
        problems.append(
            "the client's reverse parse did not return the rendered instruction"
        )

    # (3) the audited payload's field set, the adapter's own equality
    arm_fields = sorted(ARM_VISIBLE_FIELDS[STAGE3_GEPA_ARM])
    payload = {
        "request_id": "gepa-dry-run-0001",
        "carrier_lock_key": "slurp",
        "sample_id": carrier,
        "speech_ref": f"dry-run:{carrier}",
        "media_relpath": None,
        "audio_seconds": 0.0,
        "sample_rate_hz": 16000,
        "task_instruction": contact.instruction,
        "history": [],
        "decoding_params": {"temperature": 0.0},
        "construction_targets": [
            {"sample_id": entry["sample_id"], "target": entry["target"]}
            for entry in material.bound_targets
            if entry["sample_id"] in set(contact.construction_target_ids)
        ],
    }
    missing = [field for field in arm_fields if field not in payload]
    extra = [field for field in payload if field not in arm_fields]
    if missing or extra:
        problems.append(
            f"payload field set differs from the D2 arm's: missing={missing} extra={extra}"
        )

    # (4) the transport's own text-only construction gate
    wire_payload = {key: value for key, value in payload.items() if value is not None}
    try:
        _assert_text_only_construction_payload(wire_payload, "system-instruction-v1")
    except Exception as error:  # noqa: BLE001 - reported, never swallowed
        problems.append(f"the transport refused the text-only payload: {error}")
    serialised = json.dumps(wire_payload, ensure_ascii=False)
    for marker in AUDIO_MARKERS:
        if marker in serialised:
            problems.append(f"the payload carries {marker!r}; this arm is text-only")

    # (5) the receipt carries no rendered text
    receipt = contact.as_json()
    blob = json.dumps(receipt, ensure_ascii=False)
    for needle in (contact.instruction[:64], "CORRECT ANSWER:"):
        if needle and needle in blob:
            problems.append("the contact receipt carries rendered instruction text")

    instruction = contact.instruction
    report = {
        "schema": "saea-stage3-gepa-dry-run-v1",
        "group_id": contact.group_id,
        "scenario": contact.scenario,
        "node": contact.node,
        "carrier_sample_id": contact.sample_id,
        "carrier_from": contact.carrier_from,
        "rows_shown": len(contact.construction_target_ids),
        "worst_rows": len(contact.worst_sample_ids),
        "best_rows": len(contact.best_sample_ids),
        "current_delta_count": len(contact.current_delta_value_ids),
        "bound_target_count": len(material.bound_targets),
        "declared_construction_targets": len(payload["construction_targets"]),
        "prompt_sha256": contact.prompt_sha256,
        "prompt_characters": len(instruction),
        "prompt_lines": instruction.count("\n") + 1,
        "row_block_markers": instruction.count("--- ROW "),
        "characters_note": (
            "CHARACTERS ONLY. Measuring tokens needs a tokenizer endpoint, which is a "
            "contact; the registered FIT pass measures them."
        ),
        "payload_field_set": arm_fields,
        "transport_gate": (
            "core.model.transport._assert_text_only_construction_payload passed"
            if not any("transport refused" in problem for problem in problems)
            else "REFUSED"
        ),
        "material_bindings": {
            "groups": material.groups_binding,
            "pairs": material.pairs_binding,
            "deltas": material.deltas_binding,
            "instruction_template": {
                "relpath": material.template_relpath,
                "sha256": material.template_sha256,
            },
        },
        "contact_receipt": receipt,
        "contacts": {
            "asr": 0,
            "encoder": 0,
            "model": 0,
            "network": 0,
            "scorer": 0,
            "server": 0,
            "tokenizer": 0,
        },
        "problems": problems,
        "passed": not problems,
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)  # noqa: T201 -- ids, counts and digests only
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
