#!/usr/bin/env python3
"""Make KU-E1c a TOKEN twin of KC-E1, and pin the measurement.

``SAEA-E21-KU-E1C-TOKEN-MATCH-V1``, the repair of result 4 of
``SAEA-E21-KC-E1-PROMPT-FIT-V1``. That row certified the fit and the cap and
then reported the finding this script exists to close: the form twin holds the
brief's WHITESPACE-token count equal line for line, and on the FLIGHT tokenizer
it is 42 to 256 tokens SHORTER per window at ``brief_max_entries_per_class``
12, median 161. The owner ruling of 2026-09-06 locks a control to its treatment
on the flight tokenizer rather than on characters or whitespace, so a verdict
drawn against a 161-token-light twin would price content and volume together.

WHAT IS MEASURED, AND HOW
-------------------------
Both arms' evidence is rendered by the REAL evidence sources
(``core.evidence.conec-class-lists`` and ``conec-class-lists-placebo``) out of
the REAL composed configs, and every count comes from the resident server's own
``POST /tokenize`` -- the same non-generative route the prompt fit measured on,
on the same pinned chat template, which this script re-checks against the fit's
own recorded digest before it measures anything. Nothing decodes and zero
tokens are generated.

For each call, each cap and each of the two brief halves, the twin's line ``i``
is grown by whole repeats of one neutral one-token filler until the twin's
rendered PREFIX through line ``i`` measures exactly what the brief's does
(``core.class_lists.placebo_pad_repeats``). Matching on prefixes rather than on
isolated lines is what makes whole-block equality a consequence rather than a
hope: the prefix at the last index IS the whole block.

WHAT IS WRITTEN
---------------
1. ``configs/knowledge/e21-brief-placebo-v2/pad-plan-v1.json`` -- per cap, per
   call, per half: the source bytes' sha256, the per-line pad repeats, both
   arms' prefix counts and both arms' totals. The flight replays the repeats
   and needs no tokenizer of its own.
2. ``configs/baseline/e21-ku-e1c-brief-placebo.json`` -- repointed at the
   token-matched evidence source and at the plan above, by relpath and sha256.
   KC-E1's own baseline fragment is NOT touched, and the receipt proves that
   with git rather than asserting it: the arm's fragment is re-diffed against
   the prompt fit's own study commit. Its COMPOSED hash is reported beside the
   one the fit published, because the two already differ for a reason that
   predates this measurement -- ``configs/experiment/e21-kc-e1-brief-44-v1.json``
   gained a reporting note at fa357a24, which moves both cells' composed hashes
   and no cell's protocol.
3. The receipt under ``--out-dir``: per-call token totals for both arms at both
   caps, the per-window request-text distribution of both arms after padding,
   and the residual the padding cannot reach -- the evidence-block HEADER, a
   few tokens wide, because the arm and the twin must name different pinned
   transforms. The brief CONTENT is equal; that residual is reported rather
   than hidden.

After the fragment is rewritten the script re-composes KU-E1c and renders it
through the NEW source, so what is certified is the bytes the flight would
send, not a second spelling of them.

Usage::

    python scripts/build_e21_brief_placebo_token_match.py --out-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
RUNTIME_ROOT = Path("/home/chao")

CHECK = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e21-kc-e1-brief-44-v1"
)
ROSTER_RECEIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e21-full44-roster/flight-roster-receipt.json"
)
PROMPT_FIT = CHECK / "prompt-fit/prompt-fit.json"

EXPERIMENT = "e21-kc-e1-brief-44-v1"
RUN_ID = "SAEA-E21-KU-E1C-TOKEN-MATCH-V1"
FLIGHT_RUN_ID = "SAEA-E21-KC-E1-BRIEF-44-V1"

TWIN_CELL_ID = "E21-ku-e1c-brief-placebo"
TWIN_FRAGMENT = "e21-ku-e1c-brief-placebo"
TWIN_SOURCE = "conec-class-lists-placebo-token-matched"
BASE_TWIN_SOURCE = "conec-class-lists-placebo"

PAD_PLAN_RELPATH = "configs/knowledge/e21-brief-placebo-v2/pad-plan-v1.json"

#: The prompt fit's own budget convention, restated: the transport here is a
#: capture and the routes are non-generative, so nothing is drawn. The plan
#: exists because ``contracts.ExecutionPlan`` requires a positive budget to
#: gate a server, and ``contracts.gate_exposure`` refuses a plan larger than
#: the exposure row registered for this run id -- 12 calls, 12 speech-audio
#: seconds and 0.5 GPU-hours, all nominal, all drawn 0. Sized as the prompt
#: fit sized its own: comfortably inside the row, because a plan that spends
#: the whole registration leaves no room for a second attempt.
PLAN_CALLS = 2
PLAN_AUDIO_SECONDS = 2
PLAN_GPU_HOURS = 0.4

SPLIT_IDENTITY_HASH = (
    "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
)
SPEECH_TOKENS_PER_SECOND_WINDOW = 13
SPECIAL_TOKENS = 2

STAND_IN_RELPATH = "derived/prompt-fit/e21-ku-e1c-token-match/silence-100ms-16k.wav"
STAND_IN_SECONDS = 0.1
STAND_IN_RATE_HZ = 16000

#: The one key KU-E1c gains beside ``evidence_source``. Kept to ONE key, and
#: shaped as an object rather than two flat fields, so the one-factor statement
#: stays as short as it can honestly be: the cells differ in the source and in
#: the byte pin of the twin's own pad plan, and in nothing else.
PAD_PLAN_KEY = "evidence_pad_plan"


def git(*argv: str) -> str:
    return subprocess.run(
        ["git", *argv], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()


def log(message: str) -> None:
    print(
        "[%s] %s" % (datetime.now(tz=timezone.utc).strftime("%H:%M:%SZ"), message),
        flush=True,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: Path) -> Mapping[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def speech_tokens(audio_seconds: float) -> int:
    return SPEECH_TOKENS_PER_SECOND_WINDOW * math.ceil(float(audio_seconds))


def distribution(values: Sequence[int]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        raise SystemExit("a distribution needs at least one value")

    def percentile(fraction: float) -> int:
        index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
        return ordered[index]

    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": float(statistics.median(ordered)),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "max": ordered[-1],
    }


def prefix_counts(counter, text: str) -> list[int]:
    lines = text.splitlines()
    return [counter("\n".join(lines[: index + 1])) for index in range(len(lines))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--experiment", default=EXPERIMENT)
    parser.add_argument(
        "--caps",
        default="0,12",
        help=(
            "the caps to measure, comma separated. 0 is the whole brief; the "
            "committed cap must be among them or the flight would fly a cap nobody "
            "measured"
        ),
    )
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
        raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

    import speech_aware_evidence_acquisition as _pkg

    if (
        Path(_pkg.__file__ or "")
        != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py"
    ):
        raise SystemExit(
            "package resolves to %s, not the main checkout" % (_pkg.__file__,)
        )

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate
    from speech_aware_evidence_acquisition.core.base import EVIDENCE_SOURCES, TRANSPORTS
    from speech_aware_evidence_acquisition.core.class_lists import (
        PLACEBO_PAD_FILLER,
        PLACEBO_PAD_PLAN_SCHEMA,
        pad_placebo,
        placebo_pad_repeats,
        whitespace_token_count,
    )
    from speech_aware_evidence_acquisition.core.config import (
        compose,
        d1_evidence_supplement_relpath,
        d1_evidence_supplement_sha256,
        d1_media_supplement_relpath,
        d1_media_supplement_sha256,
        model_materialization_root,
    )
    from speech_aware_evidence_acquisition.core.driver.speech_native import (
        _LoopbackPromptAuditClient,
    )
    from speech_aware_evidence_acquisition.core.flight.runtime import merge_server_args
    from speech_aware_evidence_acquisition.core.policies import build_arm_payload
    from speech_aware_evidence_acquisition.core.session import (
        load_runtime_receipt,
        start_session,
        stop_session,
    )
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.loader import SampleRef
    from speech_aware_evidence_acquisition.reproduction.obs_audio import write_wav_bytes

    dirty = git("status", "--porcelain")
    if dirty and not args.allow_dirty:
        raise SystemExit(
            "the working tree is dirty; this measurement rewrites a committed "
            "fragment and must start from committed bytes:\n" + dirty
        )
    study_commit = git("rev-parse", "HEAD")
    log("clean tree at %s" % study_commit[:8])

    caps = [int(value) for value in str(args.caps).split(",") if value.strip()]
    if not caps:
        raise SystemExit("at least one cap must be measured")

    experiment_doc = load_json(REPO / "configs" / "experiment" / f"{args.experiment}.json")
    cells = list(experiment_doc["cells"])
    if len(cells) != 2:
        raise SystemExit("this measurement pairs exactly the experiment's two cells")
    dataset = str(cells[0]["dataset_fragment"])
    model = str(cells[0]["model_fragment"])
    cell_ids = [str(cell["cell_id"]) for cell in cells]
    if TWIN_CELL_ID not in cell_ids:
        raise SystemExit("the experiment does not name the twin cell " + TWIN_CELL_ID)
    arm_cell_id = next(cell_id for cell_id in cell_ids if cell_id != TWIN_CELL_ID)

    def composed(cell_id: str):
        fragment = next(
            str(cell["baseline_fragment"]) for cell in cells if str(cell["cell_id"]) == cell_id
        )
        return compose(REPO, model, dataset, fragment, args.experiment)

    arm_composed = composed(arm_cell_id)
    twin_composed_before = composed(TWIN_CELL_ID)
    values_a = dict(arm_composed.values)
    values_b = dict(twin_composed_before.values)
    differing = sorted(
        key for key in set(values_a) | set(values_b) if values_a.get(key) != values_b.get(key)
    )
    if differing not in (["evidence_source"], ["evidence_pad_plan", "evidence_source"]):
        raise SystemExit(
            "the two cells must differ in evidence_source alone, or in it plus the "
            "pad-plan pin; they differ in %r" % (differing,)
        )
    committed_cap = int(values_a.get("brief_max_entries_per_class", 0))
    if int(values_b.get("brief_max_entries_per_class", 0)) != committed_cap:
        raise SystemExit("the two fragments carry different caps; the twin is not a twin")
    if committed_cap not in caps:
        raise SystemExit(
            "the committed cap %d is not among the caps being measured %r"
            % (committed_cap, caps)
        )
    log("committed brief_max_entries_per_class = %d (both fragments)" % committed_cap)

    geometry = values_a["serving_geometry"]
    slots = int(geometry["slots"])
    slot_tokens = int(geometry["slot_tokens"])
    max_tokens = int(geometry["max_tokens"])

    fit = load_json(PROMPT_FIT)
    expected_template_sha256 = str(fit["geometry"]["chat_template_sha256"])
    fit_study_commit = str(fit["study_commit"])
    fit_config_hashes = {
        str(cell["cell_id"]): str(cell["config_hash"]) for cell in fit["cells"]
    }
    # The arm's BASELINE FRAGMENT must be byte-identical to what the fit
    # measured -- proved by git, not asserted in prose. Its COMPOSED hash is a
    # different question: the experiment fragment both cells share gained a
    # reporting note after the fit, which moves both composed hashes without
    # touching either protocol. Both numbers are reported.
    arm_fragment_relpath = "configs/baseline/%s.json" % next(
        str(cell["baseline_fragment"])
        for cell in cells
        if str(cell["cell_id"]) == arm_cell_id
    )
    arm_fragment_changed = bool(
        git("diff", "--name-only", fit_study_commit, "HEAD", "--", arm_fragment_relpath)
    )
    if arm_fragment_changed:
        raise SystemExit(
            "%s changed since the prompt fit measured it (%s); the twin can only be "
            "matched to the arm the fit certified"
            % (arm_fragment_relpath, fit_study_commit[:8])
        )

    roster = load_json(ROSTER_RECEIPT)
    sample_ids = [str(call["sample_id"]) for call in roster["calls"]]
    windows_by_call = {
        str(call["sample_id"]): int(call["fixed_90s_windows"]) for call in roster["calls"]
    }
    last_window_seconds = {
        str(call["sample_id"]): float(call["last_window_seconds"]) for call in roster["calls"]
    }
    total_windows = sum(windows_by_call.values())
    log("%d calls, %d fixed 90-second windows" % (len(sample_ids), total_windows))

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    carrier_lock_key = str(values_a["carrier_lock_key"])

    stand_in_path = root / STAND_IN_RELPATH
    stand_in_path.parent.mkdir(parents=True, exist_ok=True)
    stand_in_bytes = write_wav_bytes(
        [0] * int(round(STAND_IN_SECONDS * STAND_IN_RATE_HZ)), STAND_IN_RATE_HZ
    )
    stand_in_path.write_bytes(stand_in_bytes)

    plan = ExecutionPlan(
        run_id=args.run_id,
        execution_profile=str(values_a["execution_profile"]),
        carrier_lock_key=carrier_lock_key,
        split_role=str(experiment_doc["population"]["split_role"]),
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=PLAN_CALLS,
        planned_gpu_hours=PLAN_GPU_HOURS,
        planned_speech_audio_seconds=PLAN_AUDIO_SECONDS,
        protocol_hash=arm_composed.config_hash,
        attempt_id="attempt-%s-e21kue1ctm"
        % datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    ).validate()
    configured_model_root = model_materialization_root(values_a)
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=str(values_a["runtime_receipt"]),
        expected_model_lock_key=str(values_a["model_lock_key"]),
        model_root=(Path(configured_model_root) if configured_model_root else None),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values_a),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values_a),
        d1_evidence_supplement_relpath=d1_evidence_supplement_relpath(values_a),
        d1_evidence_supplement_sha256=d1_evidence_supplement_sha256(values_a),
    )
    lock_sha256 = gate.assert_model_touch_allowed(plan)
    log("frozen-core gate PASS (lock %s)" % lock_sha256[:12])

    runtime_receipt = load_runtime_receipt(REPO / "docs" / str(values_a["runtime_receipt"]))
    run_dir = root / "runs" / args.run_id / str(plan.attempt_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    extra_argv = merge_server_args(
        values_a["server_args"], slots=slots, context_tokens=slots * slot_tokens
    )
    port = int(str(values_a["base_url"]).rsplit(":", 1)[-1])
    log("spawning llama-server on %d: %s" % (port, " ".join(extra_argv)))
    server_started_at = datetime.now(tz=timezone.utc)
    started = time.time()
    session = start_session(
        runtime_root=RUNTIME_ROOT,
        data_root=root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=port,
        session_id="%s-%s" % (args.run_id, plan.attempt_id),
        extra_argv=extra_argv,
        extra_env=dict(values_a.get("server_env", {})),
        receipt_path=run_dir / "session.receipt.json",
        server_log_path=run_dir / "session.server.log",
        role=str(runtime_receipt.get("role", "legacy")),
        model_root=(Path(configured_model_root) if configured_model_root else None),
        ready_timeout_seconds=1800.0,
    )
    load_seconds = time.time() - started
    log("server up in %.1fs: pid=%s port=%s" % (load_seconds, session.pid, session.port))

    counts: Counter[str] = Counter()
    caps_document: dict[str, Any] = {}
    per_cap_summary: dict[str, Any] = {}
    request_rows: list[dict[str, Any]] = []
    media_marker = ""
    chat_template_sha256 = ""
    server_stopped_at = None

    try:
        client = _LoopbackPromptAuditClient(
            host="127.0.0.1", port=port, timeout_seconds=600.0
        )
        props = client.request_json("GET", "/props", None)
        counts["GET /props"] += 1
        media_marker = props.get("media_marker")
        if not isinstance(media_marker, str) or not media_marker:
            raise SystemExit("resident props lack a media marker")
        live_slot_ctx = (props.get("default_generation_settings") or {}).get("n_ctx")
        if int(live_slot_ctx) < slot_tokens:
            raise SystemExit(
                "resident slot n_ctx %s is smaller than the fragment's declared %d"
                % (live_slot_ctx, slot_tokens)
            )
        chat_template = props.get("chat_template")
        chat_template_sha256 = (
            sha256_text(chat_template) if isinstance(chat_template, str) else ""
        )
        if chat_template_sha256 != expected_template_sha256:
            raise SystemExit(
                "the resident chat template hashes to %s, the prompt fit measured on "
                "%s; a control matched on a different tokenizer is not matched"
                % (chat_template_sha256[:12], expected_template_sha256[:12])
            )
        log("props OK: slot n_ctx=%s, template pinned to the fit" % live_slot_ctx)

        def tokenize(text: str) -> int:
            response = client.request_json(
                "POST",
                "/tokenize",
                {"content": text, "add_special": False, "parse_special": True},
            )
            counts["POST /tokenize"] += 1
            tokens = response.get("tokens")
            if not isinstance(tokens, list):
                raise SystemExit("tokenize returned no token list")
            return len(tokens)

        def text_tokens(messages) -> tuple[int, str]:
            rendered = client.request_json(
                "POST", "/apply-template", {"messages": list(messages)}
            )
            counts["POST /apply-template"] += 1
            prompt = rendered.get("prompt")
            if not isinstance(prompt, str) or not prompt:
                raise SystemExit("apply-template returned no prompt")
            if prompt.count(media_marker) != 1:
                raise SystemExit(
                    "rendered prompt carries %d media markers, expected 1"
                    % prompt.count(media_marker)
                )
            return sum(tokenize(part) for part in prompt.split(media_marker) if part), prompt

        arm_source = EVIDENCE_SOURCES.resolve(str(values_a["evidence_source"]))
        base_twin_source = EVIDENCE_SOURCES.resolve(BASE_TWIN_SOURCE)

        # ------------------------------------------------------------------
        # The measurement, per cap.
        # ------------------------------------------------------------------
        padded_by_key: dict[tuple[int, str, str], str] = {}
        for cap in caps:
            log("cap %d: measuring %d calls x 2 halves" % (cap, len(sample_ids)))
            arm_values = dict(values_a)
            arm_values["brief_max_entries_per_class"] = cap
            twin_values = dict(values_b)
            twin_values["brief_max_entries_per_class"] = cap
            twin_values["evidence_source"] = BASE_TWIN_SOURCE
            twin_values.pop(PAD_PLAN_KEY, None)

            halves: list[dict[str, Any]] = []
            arm_call_tokens: list[int] = []
            twin_call_tokens: list[int] = []
            for sample_id in sample_ids:
                arm_items = arm_source(lock, root, sample_id, carrier_lock_key, arm_values)
                twin_items = base_twin_source(
                    lock, root, sample_id, carrier_lock_key, twin_values
                )
                if len(arm_items) != 2 or len(twin_items) != 2:
                    raise SystemExit("the brief must be two items, roster then document")
                arm_total = 0
                twin_total = 0
                for arm_item, twin_item in zip(arm_items, twin_items):
                    part = str(arm_item.provenance["brief_part"])
                    if str(twin_item.provenance["brief_part"]) != part:
                        raise SystemExit("the two halves arrived in different orders")
                    arm_text = arm_item.content
                    base_text = twin_item.content
                    repeats = placebo_pad_repeats(
                        arm_text, base_text, token_counter=tokenize
                    )
                    padded = pad_placebo(base_text, repeats)
                    arm_prefixes = prefix_counts(tokenize, arm_text)
                    padded_prefixes = prefix_counts(tokenize, padded)
                    if arm_prefixes != padded_prefixes:
                        raise SystemExit(
                            "cap %d call %s half %s: the padded twin's prefixes %r do "
                            "not equal the brief's %r"
                            % (cap, sample_id, part, padded_prefixes, arm_prefixes)
                        )
                    arm_tokens = arm_prefixes[-1]
                    padded_tokens = padded_prefixes[-1]
                    if arm_tokens != padded_tokens:
                        raise SystemExit("whole-half equality failed after per-line equality")
                    padded_by_key[(cap, sample_id, part)] = padded
                    arm_total += arm_tokens
                    twin_total += padded_tokens
                    halves.append(
                        {
                            "sample_id": sample_id,
                            "half": part,
                            "source_relpath": arm_item.derivation.source_relpath,
                            "source_sha256": arm_item.derivation.source_sha256,
                            "pad_repeats": repeats,
                            "arm_prefix_tokens": arm_prefixes,
                            "base_twin_prefix_tokens": prefix_counts(tokenize, base_text),
                            "twin_prefix_tokens": padded_prefixes,
                            "arm_tokens": arm_tokens,
                            "twin_tokens": padded_tokens,
                            "arm_whitespace_tokens": whitespace_token_count(arm_text),
                            "twin_whitespace_tokens": whitespace_token_count(padded),
                            "arm_derived_sha256": arm_item.derivation.derived_sha256,
                            "twin_derived_sha256": sha256_text(padded),
                        }
                    )
                arm_call_tokens.append(arm_total)
                twin_call_tokens.append(twin_total)
            if arm_call_tokens != twin_call_tokens:
                raise SystemExit("cap %d: per-call brief totals are not equal" % cap)
            caps_document[str(cap)] = {"halves": halves}
            per_cap_summary[str(cap)] = {
                "calls": len(sample_ids),
                "brief_tokens_equal_on_every_call": True,
                "arm_brief_token_distribution": distribution(arm_call_tokens),
                "twin_brief_token_distribution": distribution(twin_call_tokens),
                "pad_repeats_total": sum(
                    sum(half["pad_repeats"]) for half in halves
                ),
                "pad_repeats_per_line": distribution(
                    [count for half in halves for count in half["pad_repeats"]]
                ),
                "whitespace_tokens_after_padding": {
                    "arm": distribution([half["arm_whitespace_tokens"] for half in halves]),
                    "twin": distribution([half["twin_whitespace_tokens"] for half in halves]),
                    "note": (
                        "no longer equal, and that is the point: matching the flight "
                        "tokenizer costs more placeholder words than the arm has real "
                        "ones. The whitespace count was the PROXY the owner ruling "
                        "of 2026-09-06 replaced"
                    ),
                },
            }
            log(
                "  cap %d: brief tokens equal on all %d calls; arm median %.1f, pads %d"
                % (
                    cap,
                    len(sample_ids),
                    per_cap_summary[str(cap)]["arm_brief_token_distribution"]["median"],
                    per_cap_summary[str(cap)]["pad_repeats_total"],
                )
            )

        # ------------------------------------------------------------------
        # The artifact, then the fragment that pins it.
        # ------------------------------------------------------------------
        plan_document = {
            "schema": PLACEBO_PAD_PLAN_SCHEMA,
            "study": "speech-aware-evidence-acquisition",
            "run_id": args.run_id,
            "for_flight_run_id": FLIGHT_RUN_ID,
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "study_commit": study_commit,
            "filler": PLACEBO_PAD_FILLER,
            "what_this_is": (
                "the per-line pad plan that makes core.evidence's "
                "conec-class-lists-placebo-token-matched a FLIGHT-TOKEN twin of "
                "conec-class-lists. Line i of a twin half grows by pad_repeats[i] "
                "whole repeats of 'filler' and by nothing else, so the flight "
                "replays a measurement instead of taking one"
            ),
            "measured_on": {
                "route": "POST /tokenize (add_special false, parse_special true)",
                "chat_template_sha256": chat_template_sha256,
                "model_fragment": model,
                "server_args": [str(value) for value in values_a["server_args"]],
                "prompt_fit_receipt": str(PROMPT_FIT.relative_to(REPO)),
                "prompt_fit_receipt_sha256": sha256_file(PROMPT_FIT),
            },
            "keyed_by": (
                "source_sha256 -- the sha256 of the ConEC source file's UTF-8 bytes, "
                "which is exactly the DerivedEvidenceRecord.source_sha256 the D1 rail "
                "already verifies for that half"
            ),
            "caps": caps_document,
        }
        plan_path = REPO / PAD_PLAN_RELPATH
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_blob = (
            json.dumps(plan_document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        plan_path.write_bytes(plan_blob)
        plan_sha256 = hashlib.sha256(plan_blob).hexdigest()
        log("wrote %s (%d bytes, sha256 %s)" % (PAD_PLAN_RELPATH, len(plan_blob), plan_sha256[:12]))

        fragment_path = REPO / "configs" / "baseline" / f"{TWIN_FRAGMENT}.json"
        fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
        rebuilt: dict[str, Any] = {}
        for key, value in fragment.items():
            if key == "evidence_source":
                rebuilt[key] = TWIN_SOURCE
                rebuilt[PAD_PLAN_KEY] = {
                    "artifact_relpath": PAD_PLAN_RELPATH,
                    "artifact_sha256": plan_sha256,
                }
            elif key != PAD_PLAN_KEY:
                rebuilt[key] = value
        fragment_path.write_bytes(
            (json.dumps(rebuilt, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        )
        log("repointed %s at the plan" % fragment_path.relative_to(REPO))

        # ------------------------------------------------------------------
        # Certify the bytes the flight would actually send.
        # ------------------------------------------------------------------
        twin_composed_after = composed(TWIN_CELL_ID)
        values_after = dict(twin_composed_after.values)
        if str(values_after["evidence_source"]) != TWIN_SOURCE:
            raise SystemExit("the rewritten fragment did not compose to the new source")
        differing_after = sorted(
            key
            for key in set(values_a) | set(values_after)
            if values_a.get(key) != values_after.get(key)
        )
        if differing_after != [PAD_PLAN_KEY, "evidence_source"]:
            raise SystemExit(
                "after the rewrite the cells must differ in exactly %r; they differ in %r"
                % ([PAD_PLAN_KEY, "evidence_source"], differing_after)
            )
        twin_source = EVIDENCE_SOURCES.resolve(TWIN_SOURCE)

        replay_rows: list[dict[str, Any]] = []
        for cap in caps:
            values_cap = dict(values_after)
            values_cap["brief_max_entries_per_class"] = cap
            for sample_id in sample_ids:
                items = twin_source(lock, root, sample_id, carrier_lock_key, values_cap)
                for item in items:
                    part = str(item.provenance["brief_part"])
                    expected = padded_by_key[(cap, sample_id, part)]
                    if item.content != expected:
                        raise SystemExit(
                            "cap %d call %s half %s: the source replayed different bytes "
                            "than the measurement produced" % (cap, sample_id, part)
                        )
                    if sha256_text(item.content) != item.derivation.derived_sha256:
                        raise SystemExit("the derivation record does not hash its own content")
                replay_rows.append(
                    {"cap": cap, "sample_id": sample_id, "halves": len(items)}
                )
        log("replay OK: %d (cap, call) pairs render the measured bytes" % len(replay_rows))

        # The whole request, at the committed cap, one window per call. The
        # prompt fit proved the text envelope is window-independent at this
        # protocol over all 6,460 of its renders, so the per-window
        # distribution below is the per-call value weighted by the roster's
        # own window count -- stated rather than assumed.
        instruction = str(values_a["task_instruction"])
        for cell_id, values_cell, source in (
            (arm_cell_id, values_a, arm_source),
            (TWIN_CELL_ID, values_after, twin_source),
        ):
            values_cell = dict(values_cell)
            values_cell["brief_max_entries_per_class"] = committed_cap
            decoding_params = dict(values_cell["decoding_params"])
            decoding_params["id_slot"] = 0
            transport = TRANSPORTS.resolve(str(values_cell["transport"]))(
                values_cell,
                root,
                session=session,
                runtime_receipt=runtime_receipt,
                runtime_root=RUNTIME_ROOT,
            )
            captured: dict[str, Any] = {}

            def _capture(url, body, _captured=captured):
                _captured["body"] = json.loads(body.decode("utf-8"))
                return json.dumps(
                    {
                        "choices": [{"message": {"content": ""}}],
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                    }
                ).encode("utf-8")

            transport._post = _capture
            for sample_id in sample_ids:
                items = source(lock, root, sample_id, carrier_lock_key, values_cell)
                ref = SampleRef(
                    carrier_lock_key=carrier_lock_key,
                    sample_id=sample_id,
                    media_relpath=STAND_IN_RELPATH,
                    audio_seconds=90.0,
                    sample_rate_hz=STAND_IN_RATE_HZ,
                )
                payload = build_arm_payload(
                    str(values_cell["arm"]),
                    ref,
                    "e21kue1ctm-%s-%s" % (cell_id, sample_id),
                    instruction,
                    decoding_params,
                    evidence=list(items),
                )
                transport(json.dumps(payload).encode("utf-8"))
                tokens, _prompt = text_tokens(captured["body"]["messages"])
                request_rows.append(
                    {
                        "cell_id": cell_id,
                        "sample_id": sample_id,
                        "windows": windows_by_call[sample_id],
                        "text_tokens": tokens,
                        "brief_tokens": sum(
                            half["arm_tokens"] if cell_id == arm_cell_id else half["twin_tokens"]
                            for half in caps_document[str(committed_cap)]["halves"]
                            if half["sample_id"] == sample_id
                        ),
                        "evidence_ids": [item.evidence_id for item in items],
                    }
                )
    finally:
        stop_out = stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            receipt_path=run_dir / "session.stop-receipt.json",
            force_after_timeout=True,
        )
        server_stopped_at = datetime.now(tz=timezone.utc)
        log(
            "server stopped: %s forced=%s"
            % (stop_out.get("termination_signal"), stop_out.get("forced"))
        )

    by_cell: dict[str, dict[str, dict[str, Any]]] = {}
    for row in request_rows:
        by_cell.setdefault(str(row["cell_id"]), {})[str(row["sample_id"])] = row
    arm_rows = by_cell[arm_cell_id]
    twin_rows = by_cell[TWIN_CELL_ID]
    per_window_arm: list[int] = []
    per_window_twin: list[int] = []
    deltas: list[int] = []
    envelope_deltas: set[int] = set()
    for sample_id in sample_ids:
        arm_row = arm_rows[sample_id]
        twin_row = twin_rows[sample_id]
        per_window_arm.extend([int(arm_row["text_tokens"])] * int(arm_row["windows"]))
        per_window_twin.extend([int(twin_row["text_tokens"])] * int(twin_row["windows"]))
        deltas.extend(
            [int(twin_row["text_tokens"]) - int(arm_row["text_tokens"])] * int(arm_row["windows"])
        )
        envelope_deltas.add(
            (int(twin_row["text_tokens"]) - int(twin_row["brief_tokens"]))
            - (int(arm_row["text_tokens"]) - int(arm_row["brief_tokens"]))
        )
    worst_window_seconds = max(90.0, max(last_window_seconds.values()))
    worst_required = (
        speech_tokens(worst_window_seconds)
        + max(max(per_window_arm), max(per_window_twin))
        + max_tokens
        + SPECIAL_TOKENS
    )

    receipt = {
        "schema": "saea-e21-ku-e1c-token-match-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": args.run_id,
        "attempt_id": str(plan.attempt_id),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "study_commit": study_commit,
        "working_tree_clean_at_start": not dirty,
        "for_flight_run_id": FLIGHT_RUN_ID,
        "experiment_fragment": args.experiment,
        "preregistration": (
            "docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md"
        ),
        "what_this_is": (
            "the repair of result 4 of SAEA-E21-KC-E1-PROMPT-FIT-V1: KU-E1c's brief "
            "made token-equal to KC-E1's on the flight tokenizer, line by line, on "
            "every one of the 44 calls at every measured cap, and pinned as an "
            "artifact the flight replays without a tokenizer"
        ),
        "zero_contact": {
            "generated_tokens": 0,
            "completion_requests": 0,
            "audio_seconds_delivered": 0.0,
            "routes_called": dict(counts),
            "servers_started": 1,
            "server_started_at": server_started_at.isoformat(),
            "server_stopped_at": server_stopped_at.isoformat() if server_stopped_at else None,
            "server_resident_seconds": round(
                (server_stopped_at - server_started_at).total_seconds(), 3
            )
            if server_stopped_at
            else None,
            "server_load_seconds": round(load_seconds, 3),
            "media_stand_in": {
                "relpath": STAND_IN_RELPATH,
                "seconds": STAND_IN_SECONDS,
                "sample_rate_hz": STAND_IN_RATE_HZ,
                "sha256": hashlib.sha256(stand_in_bytes).hexdigest(),
            },
        },
        "geometry": {
            "slots": slots,
            "slot_tokens": slot_tokens,
            "max_tokens": max_tokens,
            "chat_template_sha256": chat_template_sha256,
            "chat_template_matches_the_prompt_fit": (
                chat_template_sha256 == expected_template_sha256
            ),
            "media_marker": media_marker,
        },
        "population": {
            "carrier_lock_key": carrier_lock_key,
            "split_role": str(experiment_doc["population"]["split_role"]),
            "split_identity_hash": SPLIT_IDENTITY_HASH,
            "calls": len(sample_ids),
            "windows": total_windows,
            "roster_receipt": str(ROSTER_RECEIPT.relative_to(REPO)),
            "roster_receipt_sha256": sha256_file(ROSTER_RECEIPT),
        },
        "caps_measured": caps,
        "committed_cap": committed_cap,
        "filler": PLACEBO_PAD_FILLER,
        "per_cap": per_cap_summary,
        "artifact": {
            "relpath": PAD_PLAN_RELPATH,
            "sha256": plan_sha256,
            "bytes": len(plan_blob),
        },
        "cells": {
            arm_cell_id: {
                "evidence_source": str(values_a["evidence_source"]),
                "config_hash": arm_composed.config_hash,
                "config_hash_published_by_the_prompt_fit": fit_config_hashes.get(
                    arm_cell_id
                ),
                "config_hash_unchanged_since_the_prompt_fit": (
                    arm_composed.config_hash == fit_config_hashes.get(arm_cell_id)
                ),
                "baseline_fragment_relpath": arm_fragment_relpath,
                "baseline_fragment_unchanged_since_the_prompt_fit": not arm_fragment_changed,
                "why_the_composed_hash_can_differ": (
                    "the two cells share configs/experiment/e21-kc-e1-brief-44-v1.json, "
                    "whose mandatory_slices note was rewritten at fa357a24 to point at "
                    "the prompt-fit receipt. That edit moves BOTH cells' composed "
                    "hashes and neither cell's protocol; the arm's own baseline "
                    "fragment is byte-identical to the one the fit measured, which is "
                    "checked with git diff above rather than asserted"
                ),
            },
            TWIN_CELL_ID: {
                "evidence_source": TWIN_SOURCE,
                "config_hash_before": twin_composed_before.config_hash,
                "config_hash": twin_composed_after.config_hash,
                "config_hash_published_by_the_prompt_fit": fit_config_hashes.get(
                    TWIN_CELL_ID
                ),
            },
        },
        "one_factor_check": {
            "differing_composed_keys": differing_after,
            "rule": (
                "exactly ['evidence_pad_plan', 'evidence_source'] after the rewrite. "
                "The pad-plan pin is the byte identity of the twin's own measurement: "
                "it names no call content, it changes nothing the arm renders, and it "
                "exists so the two cells' briefs measure the same on this very "
                "tokenizer. The arm's own baseline fragment is byte-identical to the "
                "one the prompt fit measured, checked with git; a third differing key "
                "would not be admitted"
            ),
        },
        "request_text": {
            "unit": (
                "one rendered request per call at the committed cap, expanded to the "
                "1,593 windows by the roster's own per-call window count. The prompt "
                "fit proved the text envelope is window-independent at this protocol "
                "over all 6,460 of its renders"
            ),
            "per_window_arm": distribution(per_window_arm),
            "per_window_twin": distribution(per_window_twin),
            "per_window_delta_twin_minus_arm": distribution(deltas),
            "residual_is_the_evidence_block_header": sorted(envelope_deltas),
            "why_a_residual_remains": (
                "the brief CONTENT is token-equal per line and per call. What is left "
                "is the '[evidence <id>] ' header of the two blocks: the arm names "
                "conec-class-lists-roster/-document and the twin names their "
                "-placebo-tm transforms, and a twin that named the arm's transforms "
                "would be indistinguishable from it in a sealed trace. The residual "
                "is a constant, it is reported here, and it is two orders of "
                "magnitude below the 161-token median gap it replaces"
            ),
            "rows": request_rows,
        },
        "worst_required_tokens_after_padding": worst_required,
        "fits_under_study_rule": slot_tokens >= 2 * worst_required,
        "not_certified_here": (
            "the flight's own go/no-go. This receipt certifies that the twin is a "
            "flight-token twin of the arm's brief and that the pinned artifact "
            "reproduces it; KC-E1 and KU-E1c still need SAEA-E21-KC-E1-BRIEF-44-V1 "
            "and the owner's own GO, and neither is granted here"
        ),
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "placebo-token-match.json"
    out_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    log("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    log(
        "RESULT: brief tokens equal on all %d calls at caps %r; per-window request "
        "delta twin-minus-arm min/median/max = %d / %.1f / %d (was -256 / -161.0 / -42)"
        % (
            len(sample_ids),
            caps,
            receipt["request_text"]["per_window_delta_twin_minus_arm"]["min"],
            receipt["request_text"]["per_window_delta_twin_minus_arm"]["median"],
            receipt["request_text"]["per_window_delta_twin_minus_arm"]["max"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
